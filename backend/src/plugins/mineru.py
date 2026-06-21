import json
import logging
import os
import re
from pathlib import Path
from typing import Optional, Dict, List, Any
from PIL import Image
import html

from .base import BasePlugin

logger = logging.getLogger("pdf_toolbox.mineru")


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


class MinerUPlugin(BasePlugin):
    """
    MinerU "Smart Plugin" for OCRmyPDF.

    Architecture:
    1. Pre-fetch: Expects a pre-computed JSON file (from MinerU Cloud) to exist.
       (In full version, this class would trigger the Async Upload/Poll sequence on init).
    2. Serve: When get_hocr is called, it looks up the page in the JSON and generates hOCR.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.json_path = None
        self.pdf_data = None
        self.input_file = (
            None  # Will be set during check_options hopefully, or we infer it.
        )

        # We need a way to know the INPUT PDF path.
        # OCRmyPDF hooks usually don't pass the original PDF path to __init__.
        # But `check_options` might receive it.
        # Or we can pass it via config if we control the caller.

        # For this prototype, we rely on finding the JSON file
        # that matches the "current working PDF" which is hard because OCRmyPDF works in temp dirs.
        # HOWEVER, our `ocr_service.py` calls `ocrmypdf.ocr(input_path, ...)`
        # AND we can pass plugin config via `plugins` arg?? No, plugins are modules.
        # But we can set ENVIRONMENT VARIABLES.

        # We will use an Environment Variable to pass the JSON path.
        env_json = os.environ.get("MINERU_JSON_PATH")
        if env_json and os.path.exists(env_json):
            self.json_path = Path(env_json)
            self._load_json()
        else:
            logger.warning("[MinerU] MINERU_JSON_PATH not set or file not found.")

    def _load_json(self):
        if self.json_path is None:
            logger.error("[MinerU] json_path is None, cannot load")
            return
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                pages = data.get("pdf_info", [])
            elif isinstance(data, list):
                if all(isinstance(page, list) for page in data):
                    pages = [
                        {"page_idx": idx, "mineru_blocks": page}
                        for idx, page in enumerate(data)
                    ]
                elif all(
                    isinstance(item, dict)
                    and "bbox" in item
                    and ("text" in item or "content" in item)
                    for item in data
                ):
                    blocks_by_page: Dict[int, List[Dict[str, Any]]] = {}
                    for item in data:
                        page_idx = int(item.get("page_idx", 0) or 0)
                        blocks_by_page.setdefault(page_idx, []).append(item)
                    pages = [
                        {"page_idx": page_idx, "mineru_blocks": blocks}
                        for page_idx, blocks in sorted(blocks_by_page.items())
                    ]
                else:
                    pages = data
            else:
                logger.error(
                    f"[MinerU] Unexpected JSON root type: {type(data).__name__}"
                )
                return
            self.pdf_data = {}
            for idx, page in enumerate(pages):
                if not isinstance(page, dict):
                    continue
                page_info = page.get("page_info", {})
                page_idx = page.get("page_idx", page_info.get("page_no", idx))
                self.pdf_data[page_idx] = page
            logger.info(f"[MinerU] Loaded JSON for {len(self.pdf_data)} pages.")
        except Exception as e:
            logger.error(f"[MinerU] Failed to load JSON: {e}")

    @property
    def name(self) -> str:
        return "mineru"

    def get_hocr(self, image_path: Path) -> str:
        """
        Generate hOCR for a specific page image.
        Challenge: Knowing which page index this image corresponds to.
        OCRmyPDF processes pages in order (usually).
        But technically, `image_path` is a temp file like `.../000001.png`.
        We can try to parse the page number from the filename.
        OCRmyPDF standard temp filenames: 000001.jpg, 000002.jpg ... (1-based).
        """

        # 1. Determine Page Index (0-based)
        page_idx = self._extract_page_index(image_path.stem)

        # 2. Get Data for this page
        page_data = self.pdf_data.get(page_idx) if self.pdf_data else None
        if not page_data and self.pdf_data and len(self.pdf_data) == 1:
            page_data = next(iter(self.pdf_data.values()))

        if not page_data:
            logger.warning(f"[MinerU] No data found for page_idx {page_idx}.")
            return self._empty_hocr(image_path)

        # 3. Calculate Scaling Factors
        try:
            with Image.open(image_path) as img:
                img_w, img_h = img.size
        except Exception as e:
            logger.error(f"[MinerU] Failed to open image for scaling: {e}")
            return self._empty_hocr(image_path)

        page_info = page_data.get("page_info", {})
        default_size = [1000, 1000] if page_data.get("mineru_blocks") else [595, 842]
        json_w, json_h = page_data.get(
            "page_size",
            [
                page_info.get("width", default_size[0]),
                page_info.get("height", default_size[1]),
            ],
        )

        # Safety check for zero dimension
        if json_w == 0:
            json_w = 595
        if json_h == 0:
            json_h = 842

        scale_x = img_w / json_w
        scale_y = img_h / json_h

        # 4. Build hOCR
        lines_html = ""

        # Iterate Paragraphs/Blocks
        for block in page_data.get("para_blocks", []):
            if block["type"] not in ["text", "title", "table", "header", "footer"]:
                continue  # Skip images using OCR output? Or process them?
                # MinerU usually extracts text inside images too if OCR'd.
                # But let's stick to text types.

            # Iterate Lines
            for line in block.get("lines", []):
                # Calculate Line BBox
                l_bbox = self._scale_bbox(line["bbox"], scale_x, scale_y)
                l_bbox = _validate_bbox(l_bbox)
                if not l_bbox:
                    continue
                l_bbox_str = f"{l_bbox[0]} {l_bbox[1]} {l_bbox[2]} {l_bbox[3]}"

                spans_html = ""
                line_text = ""

                # Iterate Spans (Words/Phrases)
                for span in line.get("spans", []):
                    text = span.get("content", "")
                    if not text:
                        continue

                    line_text += text
                    s_bbox = self._scale_bbox(span["bbox"], scale_x, scale_y)
                    s_bbox = _validate_bbox(s_bbox)
                    if not s_bbox:
                        continue
                    s_bbox_str = f"{s_bbox[0]} {s_bbox[1]} {s_bbox[2]} {s_bbox[3]}"
                    escaped_text = html.escape(text)

                    # Generate ocrx_word
                    spans_html += f"<span class='ocrx_word' title='bbox {s_bbox_str}'>{escaped_text}</span> "

                # Generate ocr_line
                if spans_html:
                    lines_html += (
                        f"<span class='ocr_line' title='bbox {l_bbox_str}'>"
                        f"{spans_html}</span>\n"
                    )

        for det in page_data.get("layout_dets", []):
            if det.get("label") != "ocr_text":
                continue
            text = det.get("text", "")
            bbox = det.get("bbox")
            if not text or not bbox:
                continue

            scaled_bbox = self._scale_bbox(bbox, scale_x, scale_y)
            scaled_bbox = _validate_bbox(scaled_bbox)
            if not scaled_bbox:
                continue

            bbox_str = (
                f"{scaled_bbox[0]} {scaled_bbox[1]} "
                f"{scaled_bbox[2]} {scaled_bbox[3]}"
            )
            escaped_text = html.escape(text)
            lines_html += (
                f"<span class='ocr_line' title='bbox {bbox_str}'>"
                f"<span class='ocrx_word' title='bbox {bbox_str}'>"
                f"{escaped_text}</span></span>\n"
            )

        for block in page_data.get("mineru_blocks", []):
            if not isinstance(block, dict):
                continue
            text = self._extract_block_text(block)
            bbox = block.get("bbox")
            if not text or not bbox:
                continue

            scaled_bbox = self._scale_bbox(bbox, scale_x, scale_y)
            scaled_bbox = _validate_bbox(scaled_bbox)
            if not scaled_bbox:
                continue

            bbox_str = (
                f"{scaled_bbox[0]} {scaled_bbox[1]} "
                f"{scaled_bbox[2]} {scaled_bbox[3]}"
            )
            escaped_text = html.escape(text)
            lines_html += (
                f"<span class='ocr_line' title='bbox {bbox_str}'>"
                f"<span class='ocrx_word' title='bbox {bbox_str}'>"
                f"{escaped_text}</span></span>\n"
            )

        return self._wrap_hocr(image_path.name, lines_html, f"0 0 {img_w} {img_h}")

    def _extract_block_text(self, block: Dict[str, Any]) -> str:
        values = []

        for key in ("text", "block_content"):
            value = block.get(key)
            if isinstance(value, str) and value.strip():
                values.append(value.strip())

        def walk(node):
            if isinstance(node, str):
                if node.strip():
                    values.append(node.strip())
            elif isinstance(node, dict):
                content = node.get("content")
                if isinstance(content, str):
                    if content.strip():
                        values.append(content.strip())
                else:
                    walk(content)
                for key in ("paragraph_content", "spans", "lines"):
                    walk(node.get(key))
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(block.get("content"))
        return " ".join(values).strip()

    def _extract_page_index(self, stem: str) -> int:
        matches = re.findall(r"(\d+)", stem)
        if matches:
            page_num = int(matches[-1])
            return max(0, page_num - 1)
        logger.warning(
            f"[MinerU] Could not infer page number from '{stem}'. Defaulting to 0."
        )
        return 0

    def _scale_bbox(self, bbox: List[float], sx: float, sy: float) -> List[int]:
        # bbox: [x1, y1, x2, y2]
        # MinerU usually Top-Left origin (based on typical PDF parsers, but PDF native is Bottom-Left).
        # Inspecting the JSON:
        # "bbox": [101, 162, 464, 215] (Page 0, Title)
        # "page_size": [595, 842]
        # Coordinates look like Top-Left origin (y increases downwards).
        # 162 is fairly high up on the page. 215 is lower.
        # So yes, Top-Left is likely (Standard Computer Graphics).
        # hOCR also uses Top-Left. So direct scaling is correct.

        return [
            int(bbox[0] * sx),
            int(bbox[1] * sy),
            int(bbox[2] * sx),
            int(bbox[3] * sy),
        ]

    def _empty_hocr(self, image_path):
        try:
            with Image.open(image_path) as img:
                width, height = img.size
        except Exception:
            width, height = 1, 1
        return self._wrap_hocr(Path(image_path).name, "", f"0 0 {width} {height}")

    def _wrap_hocr(self, title, content, bbox_str):
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title></title>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='mineru-custom' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word'/>
 </head>
 <body>
  <div class='ocr_page' title='image "{title}"; bbox {bbox_str}'>
   <div class='ocr_carea'>
    <p class='ocr_par'>
     {content}
    </p>
   </div>
  </div>
 </body>
</html>
"""
