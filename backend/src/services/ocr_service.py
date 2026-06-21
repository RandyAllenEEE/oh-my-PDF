from pathlib import Path
from typing import Optional, Dict, Any
import threading
import ocrmypdf
from ..plugins.base import BasePlugin
from ..plugins.paddle import PaddleAdapter
from ..plugins.deepseek import DeepSeekAdapter
import logging
import os
import json
import sys
import importlib.util

logger = logging.getLogger("pdf_toolbox.ocr_service")

_env_lock = threading.Lock()


class OCRService:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.engines = {"paddle": PaddleAdapter, "deepseek": DeepSeekAdapter}

    def _get_plugin(
        self, engine_name: str, engine_config: Dict[str, Any]
    ) -> Optional[BasePlugin]:
        plugin_cls = self.engines.get(engine_name)
        if plugin_cls:
            return plugin_cls(engine_config)
        return None

    def _get_plugin_module_path(self) -> str:
        try:
            bridge_spec = importlib.util.find_spec("src.plugins.bridge")
        except ModuleNotFoundError:
            bridge_spec = None

        if bridge_spec is not None:
            return "src.plugins.bridge"
        bridge_path = Path(__file__).resolve().parent.parent / "plugins" / "bridge.py"
        if bridge_path.exists():
            return str(bridge_path)
        if getattr(sys, "frozen", False):
            return "src.plugins.bridge"
        src_dir = Path(__file__).parent.parent
        if str(src_dir.parent) not in sys.path:
            sys.path.insert(0, str(src_dir.parent))
        return "src.plugins.bridge"

    def run_ocr(
        self,
        input_pdf: Path,
        output_pdf: Path,
        engine_name: str,
        task_language: Optional[str] = None,
        ocr_mode: str = "normal",
        deskew: bool = False,
        optimize: int = 1,
    ):
        if ocr_mode not in {"normal", "force", "skip"}:
            raise ValueError(f"Unsupported OCR mode: {ocr_mode}")

        tesseract_config = self.config.get("engines", {}).get("tesseract", {})
        bin_path = tesseract_config.get("bin_path")

        original_path_env = os.environ.get("PATH", "")

        if bin_path and os.path.exists(bin_path):
            p = Path(bin_path)
            if p.is_file():
                dir_to_add = str(p.parent)
            else:
                dir_to_add = str(p)

            logger.info(f"Adding Tesseract path to env: {dir_to_add}")
            os.environ["PATH"] = dir_to_add + os.pathsep + original_path_env

        runtime_config = {
            "selected_engine": engine_name,
            "engines": self.config.get("engines", {}),
        }

        best_json: Optional[Path] = None
        if engine_name == "mineru":
            best_json = self._prepare_mineru(input_pdf, task_language)

        with _env_lock:
            original_env_val = os.environ.get("PDF_TOOLBOX_OCR_CONFIG")
            original_json_path = os.environ.get("MINERU_JSON_PATH")

            try:
                os.environ["PDF_TOOLBOX_OCR_CONFIG"] = json.dumps(runtime_config)
                logger.info(
                    f"[OCRService] Set PDF_TOOLBOX_OCR_CONFIG for engine: {engine_name}"
                )

                if best_json:
                    os.environ["MINERU_JSON_PATH"] = str(best_json)
                    logger.info(f"[OCRService] Set MINERU_JSON_PATH: {best_json}")

                ocr_args: Dict[str, Any] = {
                    "deskew": deskew,
                    "optimize": optimize,
                    "pdf_renderer": "hocr",
                }
                if ocr_mode == "force":
                    ocr_args["force_ocr"] = True
                elif ocr_mode == "skip":
                    ocr_args["skip_text"] = True

                if engine_name != "tesseract":
                    plugin_path = self._get_plugin_module_path()
                    ocr_args["plugins"] = [plugin_path]
                    logger.info(f"[OCRService] Using custom plugin: {plugin_path}")
                else:
                    tess_langs = tesseract_config.get("languages", "eng")
                    lang_list = [l.strip() for l in tess_langs.split(";") if l.strip()]
                    lang_list = [l for l in lang_list if l != "equ"]
                    if lang_list:
                        ocr_args["language"] = lang_list

                logger.info(
                    f"[OCRService] Calling ocrmypdf.ocr with args: {list(ocr_args.keys())}"
                )
                logger.debug(f"[OCRService] Full args: {ocr_args}")

                exit_code = ocrmypdf.ocr(input_pdf, output_pdf, **ocr_args)

                if exit_code != 0:
                    raise RuntimeError(
                        f"OCRmyPDF returned non-zero exit code: {exit_code}"
                    )

                logger.info(f"[OCRService] OCR completed successfully: {output_pdf}")

            except ocrmypdf.PriorOcrFoundError:
                logger.warning(f"[OCRService] PDF already has OCR text: {input_pdf}")
                if input_pdf != output_pdf:
                    import shutil

                    shutil.copy2(input_pdf, output_pdf)

            except ocrmypdf.EncryptedPdfError:
                logger.error(f"[OCRService] PDF is encrypted: {input_pdf}")
                raise RuntimeError(f"Cannot process encrypted PDF: {input_pdf}")

            except Exception as e:
                logger.error(f"[OCRService] OCR failed: {type(e).__name__}: {e}")
                raise RuntimeError(f"OCR processing failed for {input_pdf}: {e}") from e

            finally:
                self._restore_env("PDF_TOOLBOX_OCR_CONFIG", original_env_val)
                self._restore_env("MINERU_JSON_PATH", original_json_path)

                if bin_path:
                    os.environ["PATH"] = original_path_env

    def _restore_env(self, key: str, original_value: Optional[str]):
        if original_value is None:
            if key in os.environ:
                del os.environ[key]
        else:
            os.environ[key] = original_value

    def _prepare_mineru(
        self, input_pdf: Path, task_language: Optional[str]
    ) -> Optional[Path]:
        parent = input_pdf.parent
        stem = input_pdf.stem
        candidates = list(parent.glob(f"MinerU_{stem}*.json"))

        if candidates:
            candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            best_json = candidates[0]
            logger.info(f"[OCRService] Found local MinerU JSON: {best_json}")
            return best_json

        mineru_config = self.config.get("engines", {}).get("mineru", {})
        provider = mineru_config.get("provider", "api")

        if provider != "api":
            logger.warning(
                f"[OCRService] MinerU provider is '{provider}', not 'api'. No JSON available."
            )
            return None

        logger.info("[OCRService] No local JSON found. Initiating MinerU API task...")
        api_config = mineru_config.get("api", {})
        api_url = api_config.get("url")
        api_key = api_config.get("key")

        if not api_url or not api_key:
            raise RuntimeError(
                "MinerU API URL and key are required when no local MinerU JSON is available."
            )

        try:
            from ..utils.mineru_api import MinerUClient
            import requests
            import zipfile
            import io
            import time

            client = MinerUClient(api_url, api_key)

            lang_map = {"chi_sim": "ch", "eng": "en", "en": "en", "ch": "ch"}
            mapped_lang = lang_map.get(task_language if task_language else "ch", "ch")

            params = {
                "model": api_config.get("model", "pipeline"),
                "is_ocr": api_config.get("is_ocr", True),
                "enable_formula": api_config.get("enable_formula", True),
                "enable_table": api_config.get("enable_table", True),
                "language": mapped_lang,
            }

            result_data = client.process_file(input_pdf, **params)

            full_zip_url = result_data.get("full_zip_url")
            if not full_zip_url:
                logger.warning(
                    f"[OCRService] MinerU task done but no zip URL found: {result_data}"
                )
                return None

            logger.info(
                f"[OCRService] Downloading results zip from {full_zip_url[:60]}..."
            )

            download_retries = int(
                os.environ.get("OH_MY_PDF_MINERU_DOWNLOAD_RETRIES", "3")
            )
            download_timeout = int(
                os.environ.get("OH_MY_PDF_MINERU_DOWNLOAD_TIMEOUT_SEC", "180")
            )
            allow_direct_fallback = (
                os.environ.get("OH_MY_PDF_MINERU_DOWNLOAD_DIRECT_FALLBACK", "1") != "0"
            )
            zip_resp = None
            last_error = None

            download_modes = [("environment proxy settings", True)]
            if allow_direct_fallback:
                download_modes.append(("direct connection", False))

            for mode_name, trust_env in download_modes:
                session = requests.Session()
                session.trust_env = trust_env
                for attempt in range(1, download_retries + 1):
                    try:
                        zip_resp = session.get(full_zip_url, timeout=download_timeout)
                        zip_resp.raise_for_status()
                        break
                    except requests.RequestException as e:
                        zip_resp = None
                        last_error = e
                        if attempt >= download_retries:
                            logger.warning(
                                "[OCRService] MinerU result download failed with "
                                f"{mode_name}: {e}"
                            )
                            break
                        wait_seconds = min(10, attempt * 2)
                        logger.warning(
                            "[OCRService] MinerU result download failed with "
                            f"{mode_name} (attempt {attempt}/{download_retries}): "
                            f"{e}. Retrying in {wait_seconds}s."
                        )
                        time.sleep(wait_seconds)
                if zip_resp is not None:
                    break

            if zip_resp is None:
                raise RuntimeError(f"MinerU result download failed: {last_error}")

            with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as z:
                json_files = [f for f in z.namelist() if f.endswith(".json")]
                if not json_files:
                    raise ValueError("No JSON file found in MinerU result zip")

                json_content = z.read(json_files[0])

                timestamp = int(time.time())
                output_json_path = parent / f"MinerU_{stem}_{timestamp}.json"

                output_json_path.write_bytes(json_content)
                logger.info(
                    f"[OCRService] API Task Complete. Extracted to {output_json_path}"
                )
                return output_json_path

        except Exception as e:
            logger.error(f"[OCRService] MinerU API failed: {e}")
            raise
