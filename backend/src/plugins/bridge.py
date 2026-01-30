import os
import json
from pathlib import Path
from ocrmypdf import hookimpl
from ocrmypdf.builtin_plugins.tesseract_ocr import TesseractOcrEngine # For type hinting if needed, or just follow protocol

from .paddle import PaddleAdapter
from .deepseek import DeepSeekAdapter
from .mineru import MinerUPlugin

# Map names to classes
ADAPTERS = {
    "paddle": PaddleAdapter,
    "deepseek": DeepSeekAdapter,
    "mineru": MinerUPlugin
}

class CustomOcrEngine:
    def __init__(self, engine_name: str, config: dict):
        adapter_cls = ADAPTERS.get(engine_name)
        if not adapter_cls:
            raise ValueError(f"Unknown OCR engine: {engine_name}")
        self.adapter = adapter_cls(config)

    def languages(self, options):
        # We generally return the languages supported by the adapter.
        # For our bridge, we can just return what the user requested or what we support.
        # Most of our adapters handle multiple languages or have their own defaults.
        # If the adapter has a languages method, use it. Otherwise, return a default.
        if hasattr(self.adapter, 'languages'):
            # Assuming the adapter's languages method might return a string like Tesseract's
            # or a list. We'll ensure it's a list and filter 'equ'.
            adapter_langs = self.adapter.languages(options)
            if isinstance(adapter_langs, str):
                lang_list = [l.strip() for l in adapter_langs.split(";") if l.strip()]
            else: # Assume it's already a list or iterable
                lang_list = [str(l).strip() for l in adapter_langs if str(l).strip()]
            
            # Filter out internal 'equ' if present
            lang_list = [l for l in lang_list if l != "equ"]
            return lang_list if lang_list else ['eng'] # Fallback to 'eng' if filtering results in empty list
        
        return ['chi_sim', 'eng'] # Default fallback if adapter doesn't define languages

    def get_deskew(self, input_file: Path, options):
        # Return 0 if not implemented/supported by adapter
        if hasattr(self.adapter, 'get_deskew'):
             return self.adapter.get_deskew(input_file)
        return 0

    def get_orientation(self, input_file: Path, options):
        # Return 0 (no rotation) if not implemented
        if hasattr(self.adapter, 'get_orientation'):
             return self.adapter.get_orientation(input_file)
        return 0

    def creator_tag(self, options):
        return f"pdf-toolbox-{self.adapter.name}"

    def version(self):
        return "0.1.0"

    def generate_hocr(self, input_file: Path, output_hocr: Path, output_text: Path, options):
        # Delegate to adapter
        try:
            print(f"[BridgePlugin] Generating hOCR for {input_file.name} using {self.adapter.name}")
            hocr_content = self.adapter.get_hocr(input_file)
            
            if not hocr_content or len(hocr_content) < 100:
                print(f"[BridgePlugin] WARNING: hOCR content is suspiciously short or empty ({len(hocr_content)} chars)")
            else:
                 print(f"[BridgePlugin] Successfully generated hOCR ({len(hocr_content)} chars)")

            output_hocr.write_text(hocr_content, encoding="utf-8")
            
            # Simple text extraction from hOCR for the .txt file
            # ocrmypdf creates this sidecar file
            import re
            text_content = re.sub(r'<[^>]+>', '', hocr_content)
            output_text.write_text(text_content.strip(), encoding="utf-8")
        except Exception as e:
            print(f"[BridgePlugin] FAILED: {e}")
            raise

    def generate_pdf(self, input_file: Path, output_pdf: Path, hocr_file: Path, options):
        # We generally rely on OCRmyPDF to do the PDF generation from hOCR.
        # But if the engine supports direct PDF, we could use it.
        # For this roadmap, we output hOCR, so we don't strictly need to implement generate_pdf 
        # unless we wanna bypass OCRmyPDF's renderer.
        pass

@hookimpl
def get_ocr_engine():
    # Read config from environment variable
    config_json = os.environ.get("PDF_TOOLBOX_OCR_CONFIG")
    if not config_json:
        # Fallback or error
        return None
        
    config = json.loads(config_json)
    engine_name = config.get("selected_engine")
    engine_config = config.get("engines", {}).get(engine_name, {})
    
    return CustomOcrEngine(engine_name, engine_config)
