import logging
import base64
import os
import requests
import io
import fitz  # pymupdf
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("pdf_toolbox.llm_service")


class LLMService:
    def __init__(self):
        # We don't store config here permanently to allow dynamic updates per request if needed,
        # but typically config comes from main.py's global config.
        pass

    def _timeout_seconds(self, config: Dict[str, Any], default: int) -> int:
        return int(
            config.get("timeout_seconds")
            or os.environ.get("OH_MY_PDF_LLM_TIMEOUT_SEC")
            or default
        )

    def _render_page_as_base64(self, pdf_path: Path, page_index: int) -> str:
        """
        Render a specific PDF page to an image and return base64 string.
        """
        try:
            doc = fitz.open(pdf_path)
            if page_index < 0 or page_index >= len(doc):
                raise ValueError(
                    f"Page index {page_index} out of range (0-{len(doc)-1})"
                )

            page = doc.load_page(page_index)
            # Zoom = 2.0 for better resolution (OCR quality)
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Convert to PNG bytes
            img_data = pix.tobytes("png")
            doc.close()

            return base64.b64encode(img_data).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to render page {page_index}: {e}")
            raise

    def call_vlm(
        self, input_path: Path, start_page: int, end_page: int, config: Dict[str, Any]
    ) -> str:
        """
        Call VLM for a range of pages.
        """
        if not config.get("base_url"):
            raise ValueError("Missing VLM configuration (base_url)")

        images_b64 = []
        for p in range(start_page, end_page + 1):
            img_b64 = self._render_page_as_base64(input_path, p - 1)
            images_b64.append(img_b64)

        model = config.get("model_name", "gpt-4o")
        prompt = config.get(
            "prompt",
            "Extract the table of contents from these images. Return the results in Title @ Page format.",
        )
        provider = config.get("provider", "openai")

        headers = {"Content-Type": "application/json"}
        if config.get("api_key"):
            headers["Authorization"] = f"Bearer {config['api_key']}"

        if provider == "ollama":
            # Native Ollama /api/chat
            url = f"{config['base_url'].rstrip('/')}/api/chat"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt, "images": images_b64}],
                "stream": False,
                "think": bool(config.get("think", False)),
                "options": {"temperature": 0.1},
            }
        else:
            # OpenAI Compatible /v1/chat/completions
            url = f"{config['base_url'].rstrip('/')}/v1/chat/completions"
            if "/v1/v1" in url:
                url = url.replace("/v1/v1", "/v1")  # simple fix for double v1

            messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
            for img in images_b64:
                messages[0]["content"].append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img}"},
                    }
                )

            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": 4096,
                "temperature": 0.1,
            }

        logger.info(
            f"Calling VLM ({provider}) at {url} with model {model} for pages {start_page}-{end_page}"
        )

        try:
            resp = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self._timeout_seconds(config, 120),
            )
            resp.raise_for_status()
            result = resp.json()

            if provider == "ollama":
                content = result["message"]["content"]
            else:
                content = result["choices"][0]["message"]["content"]
            return content
        except Exception as e:
            logger.error(f"VLM request failed: {e}")
            if hasattr(e, "response") and e.response:
                logger.error(f"Response: {e.response.text}")
            raise

    def call_llm(self, text: str, config: Dict[str, Any]) -> str:
        """
        Call LLM to clean text.
        """
        if not config.get("base_url"):
            raise ValueError("Missing LLM configuration (base_url)")

        model = config.get("model_name", "gpt-3.5-turbo")
        prompt_template = config.get(
            "prompt", "Fix the following Table of Contents text:\n\n{text}"
        )
        prompt = prompt_template.replace("{text}", text)
        provider = config.get("provider", "openai")

        headers = {"Content-Type": "application/json"}
        if config.get("api_key"):
            headers["Authorization"] = f"Bearer {config['api_key']}"

        if provider == "ollama":
            url = f"{config['base_url'].rstrip('/')}/api/chat"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "think": bool(config.get("think", False)),
                "options": {"temperature": 0.1},
            }
        else:
            url = f"{config['base_url'].rstrip('/')}/v1/chat/completions"
            if "/v1/v1" in url:
                url = url.replace("/v1/v1", "/v1")
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            }

        logger.info(f"Calling LLM ({provider}) at {url} with model {model}")

        try:
            resp = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self._timeout_seconds(config, 60),
            )
            resp.raise_for_status()
            result = resp.json()

            if provider == "ollama":
                content = result["message"]["content"]
            else:
                content = result["choices"][0]["message"]["content"]
            return content
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            if hasattr(e, "response") and e.response:
                logger.error(f"Response: {e.response.text}")
            raise
