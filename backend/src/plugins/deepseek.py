import requests
import base64
import re
import json
from pathlib import Path
from typing import Dict, Any, List
from .base import BasePlugin
from ..utils.hocr import create_hocr_page, bbox_to_hocr_line

class DeepSeekAdapter(BasePlugin):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = config.get("host", "http://localhost:11434")
        # Check for model in 'ollama' sub-dict first, then top level
        self.model = config.get("ollama", {}).get("model") or config.get("model", "deepseek-vl2")
        print(f"[DeepSeekAdapter] Initialized with model: {self.model} at {self.host}")

    @property
    def name(self) -> str:
        return "deepseek"

    def get_hocr(self, image_path: Path) -> str:
        with open(image_path, "rb") as f:
            file_bytes = f.read()
            file_b64 = base64.b64encode(file_bytes).decode("utf-8")

        # Prompt that worked in the segmented test
        prompt = (
            "Please identify every line of text in the image. For each line, output its content "
            "and bounding box using the format <|ref|>text content<|/ref|><|det|>[[x1,y1,x2,y2]].\n<|ref|>"
        )
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [file_b64],
            "stream": False,
            "options": {
                "temperature": 0.0, # Deterministic
                "num_ctx": 4096,
                "num_predict": 4096
            }
        }

        try:
            from PIL import Image
            with Image.open(image_path) as img:
                width, height = img.size

            url = f"{self.host.rstrip('/')}/api/generate"
            print(f"[DeepSeekAdapter] Calling generate API at {url}...")
            response = requests.post(url, json=payload, timeout=180)
            response.raise_for_status()
            
            resp_json = response.json()
            content = resp_json.get("response", "")
            # Ensure we include the prefix for parsing if the model continued from it
            if not content.startswith("<|ref|>") and not content.startswith("<|det|>"):
                content = "<|ref|>" + content
                
            print(f"[DeepSeekAdapter] Raw content preview: {repr(content[:500])}")
            lines = self._parse_deepseek_output(content, width, height)
            
            return create_hocr_page(image_path.name, lines, width=int(width), height=int(height))

        except Exception as e:
            print(f"DeepSeek OCR Error: {e}")
            return ""

    def _parse_deepseek_output(self, text: str, width: float, height: float) -> List[Dict[str, Any]]:
        """
        Parse text containing <|ref|>...<|det|> tags.
        Coordinates are assumed to be 0-1000 normalized.
        Fallback to line-by-line if no tags are found.
        """
        # Reverting to the logic that extracts text from WITHIN the <|ref|> tags
        # regex to handle <|ref|>text<|/ref|><|det|>[[x1,y1,x2,y2]]
        pattern = r'<\|ref\|>(.*?)<\|(?:/ref\|)?det\|>(\[\[?.*?\]\]?)'
        matches = re.findall(pattern, text, re.DOTALL)
        
        lines = []
        if matches:
            for text_content, bbox_content in matches:
                try:
                    text_content = text_content.strip()
                    if text_content == "text" or not text_content:
                        # If the model still outputs "text" placeholder, 
                        # we might need to look for text AFTER the tag as a fallback
                        potential_after = text.split(bbox_content)[1].split('<|ref|>')[0].strip()
                        if potential_after and not potential_after.startswith('<|/det|>'):
                            text_content = potential_after.replace('<|/det|>', '').strip()

                    content_clean = bbox_content.strip()
                    bbox = json.loads(content_clean)[0] if content_clean.startswith('[[') else json.loads(content_clean)
                    
                    if len(bbox) == 4:
                        denorm_bbox = [
                            int(bbox[0] * width / 1000),
                            int(bbox[1] * height / 1000),
                            int(bbox[2] * width / 1000),
                            int(bbox[3] * height / 1000)
                        ]
                        lines.append({
                            "text": text_content,
                            "bbox": [denorm_bbox[0], denorm_bbox[1], denorm_bbox[2], denorm_bbox[3]],
                            "confidence": 0.9
                        })
                except Exception as e:
                    continue
        
        if not lines:
            # Fallback: Just take lines and place them centered? 
            # This is not ideal for searchability but better than nothing.
            raw_lines = [l.strip() for l in text.split('\n') if l.strip()]
            for idx, r_line in enumerate(raw_lines):
                # Spread them out vertically as a placeholder
                y_offset = int((idx + 1) * height / (len(raw_lines) + 1))
                lines.append({
                    "text": r_line,
                    "bbox": [50, y_offset, int(width-50), y_offset + 20],
                    "confidence": 0.5
                })
                
        return lines
