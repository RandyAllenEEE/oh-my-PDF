import requests
import base64
import re
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from .base import BasePlugin

try:
    from ..utils.hocr import create_hocr_page, bbox_to_hocr_line
except ImportError:
    from utils.hocr import create_hocr_page, bbox_to_hocr_line

logger = logging.getLogger("pdf_toolbox.deepseek")


def _validate_bbox(bbox: List[int]) -> Optional[List[int]]:
    if len(bbox) != 4:
        return None
    x1, y1, x2, y2 = bbox
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = max(0, x2), max(0, y2)
    if x1 == x2 or y1 == y2:
        return None
    return [x1, y1, x2, y2]


class DeepSeekAdapter(BasePlugin):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        ollama_config = config.get("ollama", {})
        self.host = ollama_config.get("url") or config.get(
            "host", "http://localhost:11434"
        )
        self.model = ollama_config.get("model") or config.get("model", "deepseek-vl2")
        self.think = bool(ollama_config.get("think", config.get("think", False)))
        self.timeout_seconds = int(
            config.get("timeout_seconds")
            or ollama_config.get("timeout_seconds")
            or os.environ.get("OH_MY_PDF_OLLAMA_TIMEOUT_SEC", "180")
        )
        logger.info(
            f"[DeepSeekAdapter] Initialized with model: {self.model} at {self.host}"
        )

    @property
    def name(self) -> str:
        return "deepseek"

    def get_hocr(self, image_path: Path) -> str:
        with open(image_path, "rb") as f:
            file_bytes = f.read()
            file_b64 = base64.b64encode(file_bytes).decode("utf-8")

        prompt = "<image>\n<|grounding|>Convert the document to markdown."

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [file_b64],
            "stream": False,
            "think": self.think,
            "options": {
                "temperature": 0.0,  # Deterministic
                "num_ctx": 4096,
                "num_predict": 4096,
            },
        }

        try:
            from PIL import Image

            with Image.open(image_path) as img:
                width, height = img.size

            url = f"{self.host.rstrip('/')}/api/generate"
            logger.info(f"[DeepSeekAdapter] Calling generate API at {url}...")
            response = requests.post(url, json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()

            resp_json = response.json()
            content = resp_json.get("response", "")
            # Ensure we include the prefix for parsing if the model continued from it
            stripped = content.lstrip()
            if not stripped.startswith(("<|ref|>", "<|det|>", "text[[", "[[", "[")):
                content = "<|ref|>" + content

            logger.debug(
                f"[DeepSeekAdapter] Raw content preview: {repr(content[:500])}"
            )
            lines = self._parse_deepseek_output(content, width, height)

            return create_hocr_page(
                image_path.name, lines, width=int(width), height=int(height)
            )

        except Exception as e:
            logger.error(f"[DeepSeekAdapter] OCR Error: {e}")
            return self._create_empty_hocr(image_path)

    def _parse_deepseek_output(
        self, text: str, width: float, height: float
    ) -> List[Dict[str, Any]]:
        """
        Parse text containing <|ref|>...<|det|> tags.
        Coordinates are assumed to be 0-1000 normalized.
        Fallback to line-by-line if no tags are found.
        """
        # Reverting to the logic that extracts text from WITHIN the <|ref|> tags
        # regex to handle <|ref|>text<|/ref|><|det|>[[x1,y1,x2,y2]]
        pattern = r"<\|ref\|>(.*?)<\|(?:/ref\|)?det\|>(\[\[?.*?\]\]?)"
        matches = re.findall(pattern, text, re.DOTALL)

        lines = []
        if matches:
            for text_content, bbox_content in matches:
                try:
                    text_content = text_content.replace("<|/ref|>", "").strip()
                    if text_content == "text" or not text_content:
                        # If the model still outputs "text" placeholder,
                        # we might need to look for text AFTER the tag as a fallback
                        potential_after = (
                            text.split(bbox_content)[1].split("<|ref|>")[0].strip()
                        )
                        if potential_after and not potential_after.startswith(
                            "<|/det|>"
                        ):
                            text_content = potential_after.replace(
                                "<|/det|>", ""
                            ).strip()

                    content_clean = bbox_content.strip()
                    bbox = (
                        json.loads(content_clean)[0]
                        if content_clean.startswith("[[")
                        else json.loads(content_clean)
                    )

                    if len(bbox) == 4:
                        denorm_bbox = [
                            round(bbox[0] * width / 1000),
                            round(bbox[1] * height / 1000),
                            round(bbox[2] * width / 1000),
                            round(bbox[3] * height / 1000),
                        ]
                        validated = _validate_bbox(denorm_bbox)
                        if validated:
                            lines.append(
                                {
                                    "text": text_content,
                                    "bbox": validated,
                                    "confidence": 0.9,
                                }
                            )
                except Exception as e:
                    continue

        if not lines:
            grounding_pattern = r"(?:^|\n)\s*(?:text)?(\[\[?.*?\]\]?)\s*\n(.*?)(?=\n\s*(?:text)?\[\[|\Z)"
            grounding_matches = re.findall(grounding_pattern, text, re.DOTALL)

            for bbox_content, text_content in grounding_matches:
                try:
                    cleaned_text = self._clean_grounding_text(text_content)
                    if not cleaned_text:
                        continue

                    content_clean = bbox_content.strip()
                    bbox = (
                        json.loads(content_clean)[0]
                        if content_clean.startswith("[[")
                        else json.loads(content_clean)
                    )

                    if len(bbox) == 4:
                        denorm_bbox = [
                            round(bbox[0] * width / 1000),
                            round(bbox[1] * height / 1000),
                            round(bbox[2] * width / 1000),
                            round(bbox[3] * height / 1000),
                        ]
                        validated = _validate_bbox(denorm_bbox)
                        if validated:
                            lines.append(
                                {
                                    "text": cleaned_text,
                                    "bbox": validated,
                                    "confidence": 0.9,
                                }
                            )
                except Exception:
                    continue

        if not lines:
            # Fallback: Just take lines and place them centered?
            # This is not ideal for searchability but better than nothing.
            raw_lines = [l.strip() for l in text.split("\n") if l.strip()]
            for idx, r_line in enumerate(raw_lines):
                # Spread them out vertically as a placeholder
                y_offset = int((idx + 1) * height / (len(raw_lines) + 1))
                fallback_bbox = _validate_bbox(
                    [50, y_offset, int(width - 50), y_offset + 20]
                )
                if fallback_bbox:
                    lines.append(
                        {
                            "text": r_line,
                            "bbox": fallback_bbox,
                            "confidence": 0.5,
                        }
                    )

        return lines

    def _clean_grounding_text(self, text: str) -> str:
        cleaned_lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            line = re.sub(r"^[#*\-\s]+", "", line).strip()
            if line and line.lower() != "text":
                cleaned_lines.append(line)
        return " ".join(cleaned_lines).strip()

    def _create_empty_hocr(self, image_path: Path) -> str:
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                width, height = img.size
        except Exception:
            width, height = 1, 1
        return create_hocr_page(
            image_path.name, [], width=int(width), height=int(height)
        )
