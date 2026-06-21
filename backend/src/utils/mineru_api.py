import requests
import time
import os
from pathlib import Path
import logging

logger = logging.getLogger("pdf_toolbox.mineru_api")


class MinerUClient:
    def __init__(self, api_url, api_key, poll_interval=None, poll_timeout=None):
        # Base API URL from environment usually ends in /v4/extract/task
        # But we need /v4/file-urls/batch for upload
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        # Detect base version URL
        if "/v4/" in api_url:
            self.api_base = api_url.split("/v4/")[0] + "/v4"
        else:
            self.api_base = "https://mineru.net/api/v4"
        self.poll_interval = float(
            poll_interval
            if poll_interval is not None
            else os.environ.get("OH_MY_PDF_MINERU_POLL_INTERVAL_SEC", "10")
        )
        self.poll_timeout = float(
            poll_timeout
            if poll_timeout is not None
            else os.environ.get("OH_MY_PDF_MINERU_POLL_TIMEOUT_SEC", "1200")
        )

    def process_file(self, file_path: Path, **params) -> dict:
        """
        Uploads file via batch API, polls for completion, returns result data.
        """
        try:
            # 1. Apply for upload URL
            batch_url = f"{self.api_base}/file-urls/batch"

            # Prepare payload for batch submission
            file_meta = {"name": file_path.name, "data_id": f"task_{int(time.time())}"}

            # Map parameters from config
            model_version = params.get("model", "vlm")
            if model_version not in ["pipeline", "vlm", "MinerU-HTML"]:
                model_version = "vlm"  # default

            payload = {
                "files": [file_meta],
                "model_version": model_version,
                "is_ocr": params.get("is_ocr", False),
                "enable_formula": params.get("enable_formula", True),
                "enable_table": params.get("enable_table", True),
                "language": params.get("language", "ch"),
            }

            logger.info(
                f"Requesting batch upload for {file_path.name} (Model: {model_version})"
            )
            resp = requests.post(batch_url, headers=self.headers, json=payload)
            resp.raise_for_status()
            res_data = resp.json()

            if res_data.get("code") != 0:
                raise RuntimeError(f"Batch URL request failed: {res_data.get('msg')}")

            batch_id = res_data["data"]["batch_id"]
            upload_url = res_data["data"]["file_urls"][0]

            # 2. Upload file (PUT)
            logger.info(f"Uploading file to {upload_url[:60]}...")
            with open(file_path, "rb") as f:
                # PUT request should NOT have standard headers like Auth or Content-Type: json
                up_resp = requests.put(upload_url, data=f)
                up_resp.raise_for_status()

            logger.info("Upload successful. Polling for results...")

            # 3. Poll batch results
            return self._poll_batch(batch_id)

        except Exception as e:
            logger.error(f"MinerU API Flow failed: {e}")
            raise

    def _poll_batch(self, batch_id):
        # Result endpoint: GET /api/v4/extract-results/batch/{batch_id}
        poll_url = f"{self.api_base}/extract-results/batch/{batch_id}"
        deadline = time.monotonic() + self.poll_timeout

        # We also need GET /api/v4/extract/task/{task_id} for individual results if batch doesn't give JSON URL
        # But batch results response sample shows full_zip_url

        while True:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"MinerU task timed out after {self.poll_timeout:.0f}s"
                )

            resp = requests.get(poll_url, headers=self.headers)
            if resp.status_code != 200:
                logger.warning(f"Poll failed ({resp.status_code}), retrying...")
                time.sleep(self.poll_interval)
                continue

            data = resp.json()
            if data.get("code") != 0:
                logger.error(f"Poll error: {data}")
                raise RuntimeError(f"Poll returned error: {data.get('msg')}")

            # Batch result contains a list of extract_result
            results = data.get("data", {}).get("extract_result", [])
            if not results:
                logger.warning("No results in batch data yet.")
                time.sleep(self.poll_interval)
                continue

            # Get the first result (we only uploaded one file)
            res = results[0]
            state = res.get("state")

            logger.info(f"Task state: {state}")

            if state == "done":
                # We have the zip URL. For the "Smart Plugin", we need the JSON.
                # If we want to be very robust, we should download the zip and extract the json.
                # However, for now, we will return the result data which contains full_zip_url.
                # The OCRService or the Plugin will need to decide how to handle the zip.
                # Note: If there's an err_msg, log it.
                return res
            elif state == "failed":
                err = res.get("err_msg", "Unknown error")
                raise RuntimeError(f"MinerU Task failed: {err}")

            time.sleep(self.poll_interval)
