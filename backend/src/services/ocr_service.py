from pathlib import Path
from typing import Optional, Dict, Any
import ocrmypdf
from ..plugins.base import BasePlugin
from ..plugins.paddle import PaddleAdapter
from ..plugins.deepseek import DeepSeekAdapter
import logging

logger = logging.getLogger("pdf_toolbox.ocr_service")

class OCRService:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.engines = {
            "paddle": PaddleAdapter,
            "deepseek": DeepSeekAdapter
        }

    def _get_plugin(self, engine_name: str, engine_config: Dict[str, Any]) -> Optional[BasePlugin]:
        plugin_cls = self.engines.get(engine_name)
        if plugin_cls:
            return plugin_cls(engine_config)
        return None

    def run_ocr(self, input_pdf: Path, output_pdf: Path, engine_name: str, task_language: Optional[str] = None, deskew: bool = False, optimize: int = 1):
        """
        Run OCR on PDF.
        If engine_name is 'tesseract', runs native ocrmypdf.
        Otherwise, injects the custom plugin.
        """
        import os
        import json
        
        # 1. Handle Tesseract Custom Path
        # OCRmyPDF relies on 'tesseract' being in PATH.
        # We temporarily prepend the user-configured path to PATH.
        tesseract_config = self.config.get("engines", {}).get("tesseract", {})
        bin_path = tesseract_config.get("bin_path")
        
        original_path_env = os.environ.get("PATH", "")
        
        if bin_path and os.path.exists(bin_path):
            # If user provided a file path (e.g. .../tesseract.exe), get dir.
            # If dir, use as is.
            p = Path(bin_path)
            if p.is_file():
                dir_to_add = str(p.parent)
            else:
                dir_to_add = str(p)
                
            logger.info(f"Adding Tesseract path to env: {dir_to_add}")
            os.environ["PATH"] = dir_to_add + os.pathsep + original_path_env
        
        # Prepare configuration for the bridge
        runtime_config = {
            "selected_engine": engine_name,
            "engines": self.config.get("engines", {})
        }
        
        # Set environment variable for the bridge process
        env = os.environ.copy()
        env["PDF_TOOLBOX_OCR_CONFIG"] = json.dumps(runtime_config)
        
        # Define arguments
        args = {
            "input_file": input_pdf,
            "output_file": output_pdf,
            "env": env
        }
        
        if engine_name != "tesseract":
            # Inject our bridge plugin
            # plugins arg expects a list of paths or module names
            # We use the module name of our bridge
            args["plugins"] = ["src.plugins.bridge"]
        
        # Run OCRmyPDF
        # Note: calling ocrmypdf.ocr directly in process might use the SAME process environment.
        # So setting os.environ momentarily involves thread safety if concurrent.
        # Ideally we use subprocess, or we rely on the fact that ocrmypdf forking 
        # might copy current env.
        # Safe approach: update os.environ temporarily.
        
        original_env_val = os.environ.get("PDF_TOOLBOX_OCR_CONFIG")
        original_json_path = os.environ.get("MINERU_JSON_PATH")

        os.environ["PDF_TOOLBOX_OCR_CONFIG"] = json.dumps(runtime_config)
        
        # MinerU Specific: Orchestrate API if needed
        if engine_name == "mineru":
             # 1. Check for existing JSON (Smart Plugin)
             parent = input_pdf.parent
             stem = input_pdf.stem
             candidates = list(parent.glob(f"MinerU_{stem}*.json"))
             
             best_json = None
             if candidates:
                 candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                 best_json = candidates[0]
                 logger.info(f"[OCRService] Found local MinerU JSON: {best_json}")
             
             # 2. If no JSON and Provider is API, call the API
             mineru_config = self.config.get("engines", {}).get("mineru", {})
             provider = mineru_config.get("provider", "api") # Default to api if not set? Or check UI defaults
             
             if not best_json and provider == 'api':
                 logger.info("[OCRService] No local JSON found. Initiating MinerU API task...")
                 api_config = mineru_config.get("api", {})
                 api_url = api_config.get("url")
                 api_key = api_config.get("key")
                 
                 if api_url and api_key:
                     try:
                        from ..utils.mineru_api import MinerUClient
                        client = MinerUClient(api_url, api_key)
                        
                        # Map standard language codes to MinerU's expected format
                        lang_map = {"chi_sim": "ch", "eng": "en", "en": "en", "ch": "ch"}
                        mapped_lang = lang_map.get(task_language, task_language or "ch")

                        # Pass extra parameters from config
                        params = {
                            "model": api_config.get("model", "pipeline"),
                            "is_ocr": api_config.get("is_ocr", True),
                            "enable_formula": api_config.get("enable_formula", True),
                            "enable_table": api_config.get("enable_table", True),
                            "language": mapped_lang
                        }
                        
                        result_data = client.process_file(input_pdf, **params)
                        
                        # result_data contains 'full_zip_url'
                        full_zip_url = result_data.get("full_zip_url")
                        if full_zip_url:
                            logger.info(f"[OCRService] Downloading results zip from {full_zip_url[:60]}...")
                            import requests
                            import zipfile
                            import io
                            
                            zip_resp = requests.get(full_zip_url)
                            zip_resp.raise_for_status()
                            
                            with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as z:
                                # Find the first .json file in the zip
                                json_files = [f for f in z.namelist() if f.endswith('.json')]
                                if not json_files:
                                    raise ValueError("No JSON file found in MinerU result zip")
                                
                                json_content = z.read(json_files[0])
                                
                                # Save result to file so the plugin can pick it up
                                # Format: MinerU_{stem}_{timestamp}.json
                                import time
                                timestamp = int(time.time())
                                output_json_path = parent / f"MinerU_{stem}_{timestamp}.json"
                                
                                output_json_path.write_bytes(json_content)
                                best_json = output_json_path
                                logger.info(f"[OCRService] API Task Complete. Extracted to {best_json}")
                        else:
                            logger.warning(f"[OCRService] MinerU task done but no zip URL found? {result_data}")
                            # Fallback to saving raw result data if zip not found?
                        
                     except Exception as e:
                         logger.error(f"[OCRService] MinerU API failed: {e}")
                         # We might want to re-raise or let it fall through to 'no json' warning
                         raise
                 else:
                     logger.warning("[OCRService] MinerU API provider selected but URL/Key missing.")

             if best_json:
                 os.environ["MINERU_JSON_PATH"] = str(best_json)
             else:
                 logger.warning(f"[OCRService] Warning: No MinerU JSON found and API execution skipped/failed for {input_pdf}")
        
        try:
             # Depending on how we import ocrmypdf, we might need to conform to its API.
             # ocrmypdf.ocr(input_file, output_pdf, plugins=...)
             
             ocr_args = {
                 "input_file": input_pdf,
                 "output_file": output_pdf,
                 "plugins": args.get("plugins"),
                 "deskew": deskew,
                 "optimize": optimize
             }
             
             # If engine is Tesseract, use the configured languages
             if engine_name == "tesseract":
                 tess_langs = tesseract_config.get("languages", "eng")
                 # Split by semicolon and strip whitespace, filter out internal 'equ'
                 lang_list = [l.strip() for l in tess_langs.split(";") if l.strip()]
                 lang_list = [l for l in lang_list if l != "equ"]
                 if lang_list:
                     ocr_args["language"] = lang_list
             
             ocrmypdf.ocr(**ocr_args)
        finally:
            # Restore environment
            if original_env_val is None:
                del os.environ["PDF_TOOLBOX_OCR_CONFIG"]
            else:
                os.environ["PDF_TOOLBOX_OCR_CONFIG"] = original_env_val
            
            if original_json_path is None:
                if "MINERU_JSON_PATH" in os.environ:
                    del os.environ["MINERU_JSON_PATH"]
            else:
                os.environ["MINERU_JSON_PATH"] = original_json_path

            # Restore PATH
            if bin_path: # Only restore if we modified it
                os.environ["PATH"] = original_path_env

