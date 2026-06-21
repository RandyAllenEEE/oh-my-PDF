import os
import json
import re
import logging
import sys
from pathlib import Path
from ocrmypdf import hookimpl

try:
    from .paddle import PaddleAdapter
    from .deepseek import DeepSeekAdapter
    from .mineru import MinerUPlugin
except ImportError:
    src_root = Path(__file__).resolve().parent.parent
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    from plugins.paddle import PaddleAdapter
    from plugins.deepseek import DeepSeekAdapter
    from plugins.mineru import MinerUPlugin

logger = logging.getLogger("pdf_toolbox.bridge")

PLUGIN_BRIDGE_VERSION = "0.2.0"

ADAPTERS = {
    "paddle": PaddleAdapter,
    "deepseek": DeepSeekAdapter,
    "mineru": MinerUPlugin,
}


class CustomOcrEngine:
    def __init__(self, engine_name: str, config: dict):
        logger.info(f"[Bridge] Initializing CustomOcrEngine for: {engine_name}")
        adapter_cls = ADAPTERS.get(engine_name)
        if not adapter_cls:
            raise ValueError(f"Unknown OCR engine: {engine_name}")
        self.adapter = adapter_cls(config)
        self.engine_name = engine_name

    def languages(self, options):
        if hasattr(self.adapter, "languages"):
            adapter_langs = self.adapter.languages(options)
            if isinstance(adapter_langs, str):
                lang_list = [l.strip() for l in adapter_langs.split(";") if l.strip()]
            else:
                lang_list = [str(l).strip() for l in adapter_langs if str(l).strip()]

            lang_list = [l for l in lang_list if l != "equ"]
            return lang_list if lang_list else ["eng"]

        return ["chi_sim", "eng"]

    def get_deskew(self, input_file: Path, options):
        if hasattr(self.adapter, "get_deskew"):
            return self.adapter.get_deskew(input_file)
        return 0

    def get_orientation(self, input_file: Path, options):
        if hasattr(self.adapter, "get_orientation"):
            return self.adapter.get_orientation(input_file)
        return 0

    def creator_tag(self, options):
        return f"pdf-toolbox-{self.adapter.name}"

    def version(self):
        return PLUGIN_BRIDGE_VERSION

    def supports_generate_ocr(self) -> bool:
        return False

    def generate_hocr(
        self, input_file: Path, output_hocr: Path, output_text: Path, options
    ):
        logger.info(
            f"[Bridge] generate_hocr called for {input_file.name} using {self.engine_name}"
        )

        try:
            hocr_content = self.adapter.get_hocr(input_file)

            if not hocr_content:
                logger.error(f"[Bridge] Adapter returned empty hOCR content")
                hocr_content = self._create_empty_hocr(input_file.name)
            elif len(hocr_content) < 100:
                logger.warning(
                    f"[Bridge] hOCR content suspiciously short ({len(hocr_content)} chars)"
                )
            else:
                logger.info(
                    f"[Bridge] Successfully generated hOCR ({len(hocr_content)} chars)"
                )

            output_hocr.write_text(hocr_content, encoding="utf-8")

            text_content = re.sub(r"<[^>]+>", "", hocr_content)
            output_text.write_text(text_content.strip(), encoding="utf-8")

            logger.info(f"[Bridge] hOCR written to {output_hocr}")

        except Exception as e:
            logger.error(
                f"[Bridge] generate_hocr FAILED: {type(e).__name__}: {e}", exc_info=True
            )
            raise

    def _create_empty_hocr(self, filename: str) -> str:
        return f"""<?xml version="1.0" encoding="UTF-8"?>
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
  <div class='ocr_page' id='page_1' title='image "{filename}"; bbox 0 0 1 1'>
  </div>
 </body>
</html>
"""

    def generate_pdf(
        self, input_file: Path, output_pdf: Path, hocr_file: Path, options
    ):
        pass


@hookimpl
def get_ocr_engine():
    config_json = os.environ.get("PDF_TOOLBOX_OCR_CONFIG")

    if not config_json:
        logger.error("[Bridge] PDF_TOOLBOX_OCR_CONFIG environment variable not set!")
        logger.error(f"[Bridge] Current env keys: {list(os.environ.keys())[:20]}...")
        return None

    logger.info(f"[Bridge] Found config, length={len(config_json)}")

    try:
        config = json.loads(config_json)
        engine_name = config.get("selected_engine")
        engine_config = config.get("engines", {}).get(engine_name, {})

        logger.info(f"[Bridge] Creating engine: {engine_name}")
        return CustomOcrEngine(engine_name, engine_config)

    except json.JSONDecodeError as e:
        logger.error(f"[Bridge] Failed to parse config JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"[Bridge] Failed to create OCR engine: {e}", exc_info=True)
        return None
