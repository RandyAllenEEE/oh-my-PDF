from typing import List, Tuple, Dict, Any
import html


def bbox_to_hocr_line(
    text: str, bbox: List[int], confidence: float, line_id: str
) -> str:
    """
    Generate an hOCR line element with nested ocrx_word.
    bbox format: [x0, y0, x1, y1]
    """
    bbox_str = f"bbox {' '.join(map(str, bbox))}"
    conf_str = f"x_wconf {int(confidence * 100)}"
    escaped_text = html.escape(text)

    # hOCR requires ocr_line and ocrx_word for best compatibility with ocrmypdf
    # If we don't have word-level bboxes, we use the line bbox for the word span
    line_html = f'<span class="ocr_line" id="{line_id}" title="{bbox_str}; {conf_str}">'
    word_id = line_id.replace("line", "word")
    line_html += f'<span class="ocrx_word" id="{word_id}" title="{bbox_str}; {conf_str}">{escaped_text}</span>'
    line_html += "</span>"

    return line_html


def create_hocr_page(
    image_file: str,
    lines: List[Dict[str, Any]],
    width: int = 0,
    height: int = 0,
    dpi: int = 300,
) -> str:
    """
    Create a full hOCR page.
    lines: List of dicts with 'text', 'bbox', 'confidence'
    """
    # Header
    hocr_header = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
 <head>
  <title></title>
  <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
  <meta name='ocr-system' content='pdf-toolbox-custom' />
  <meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word'/>
 </head>
 <body>
  <div class='ocr_page' id='page_1' title='image "{image_file}"; bbox 0 0 {width} {height}'>
   <div class='ocr_carea' id='block_1_1'>
    <p class='ocr_par' id='par_1_1'>
"""

    # Body
    hocr_body = ""
    for idx, line in enumerate(lines):
        line_id = f"line_1_{idx+1}"
        hocr_body += (
            bbox_to_hocr_line(
                line["text"], line["bbox"], line.get("confidence", 1.0), line_id
            )
            + "\n"
        )

    # Footer
    hocr_footer = """
    </p>
   </div>
  </div>
 </body>
</html>
"""
    return hocr_header + hocr_body + hocr_footer
