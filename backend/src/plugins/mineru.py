import json
import math
import os
from pathlib import Path
from typing import Optional, Dict, List, Any
from PIL import Image
import html

# BasePlugin would be: from .base import BasePlugin
# But for now I'll just replicate the minimal interface if I can't import it easily 
# or if I'm not sure where it is relative to execution.
# Based on file listing, it is in data/plugins/base.py relative to root? 
# No, it's inside `src/plugins/base.py`.
from .base import BasePlugin

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
        self.input_file = None # Will be set during check_options hopefully, or we infer it.
        
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
            print("[MinerU] Warning: MINERU_JSON_PATH not set or file not found.")

    def _load_json(self):
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # MinerU JSON structure: { "pdf_info": [ { "page_idx": 0, "para_blocks": ... } ] }
                self.pdf_data = { page['page_idx']: page for page in data.get('pdf_info', []) }
                print(f"[MinerU] Loaded JSON for {len(self.pdf_data)} pages.")
        except Exception as e:
            print(f"[MinerU] Failed to load JSON: {e}")

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
        try:
            # image_path.stem is usually '000001' -> 1
            page_num = int(image_path.stem)
            page_idx = page_num - 1
        except ValueError:
            print(f"[MinerU] Could not infer page number from {image_path.name}. Defaulting to 0.")
            page_idx = 0

        # 2. Get Data for this page
        page_data = self.pdf_data.get(page_idx) if self.pdf_data else None
        
        if not page_data:
            print(f"[MinerU] No data found for page_idx {page_idx}.")
            return self._empty_hocr(image_path)

        # 3. Calculate Scaling Factors
        # MinerU output is in PDF points (usually).
        # We need to map to the Image's pixels.
        try:
            with Image.open(image_path) as img:
                img_w, img_h = img.size
        except Exception as e:
            print(f"[MinerU] Failed to open image for scaling: {e}")
            return self._empty_hocr(image_path)
            
        json_w, json_h = page_data.get('page_size', [595, 842])
        
        # Safety check for zero dimension
        if json_w == 0: json_w = 595
        if json_h == 0: json_h = 842
            
        scale_x = img_w / json_w
        scale_y = img_h / json_h

        # 4. Build hOCR
        lines_html = ""
        
        # Iterate Paragraphs/Blocks
        for block in page_data.get('para_blocks', []):
            if block['type'] not in ['text', 'title', 'table', 'header', 'footer']: 
                continue # Skip images using OCR output? Or process them? 
                         # MinerU usually extracts text inside images too if OCR'd.
                         # But let's stick to text types.

            # Iterate Lines
            for line in block.get('lines', []):
                # Calculate Line BBox
                l_bbox = self._scale_bbox(line['bbox'], scale_x, scale_y)
                l_bbox_str = f"{l_bbox[0]} {l_bbox[1]} {l_bbox[2]} {l_bbox[3]}"
                
                spans_html = ""
                line_text = ""
                
                # Iterate Spans (Words/Phrases)
                for span in line.get('spans', []):
                    text = span.get('content', '')
                    if not text: continue
                    
                    line_text += text
                    s_bbox = self._scale_bbox(span['bbox'], scale_x, scale_y)
                    s_bbox_str = f"{s_bbox[0]} {s_bbox[1]} {s_bbox[2]} {s_bbox[3]}"
                    escaped_text = html.escape(text)
                    
                    # Generate ocrx_word
                    spans_html += f"<span class='ocrx_word' title='bbox {s_bbox_str}'>{escaped_text}</span> "

                # Generate ocr_line
                lines_html += f"<span class='ocr_line' title='bbox {l_bbox_str}'>{spans_html}</span>\n"

        return self._wrap_hocr(image_path.name, lines_html, f"0 0 {img_w} {img_h}")

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
            int(bbox[3] * sy)
        ]

    def _empty_hocr(self, image_name):
        return self._wrap_hocr(image_name, "", "0 0 0 0")

    def _wrap_hocr(self, title, content, bbox_str):
        return f'''<?xml version="1.0" encoding="UTF-8"?>
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
'''
