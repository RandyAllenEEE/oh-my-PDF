import requests
import base64
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from .base import BasePlugin

try:
    from ..utils.hocr import create_hocr_page
except ImportError:
    from utils.hocr import create_hocr_page

logger = logging.getLogger("pdf_toolbox.paddle")


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


class PaddleAdapter(BasePlugin):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        api_config = config.get("api", {})
        self.selected_model = api_config.get("selected_model", "PP-OCRv5")
        self.token = api_config.get("key", "")  # Global Token
        models_config = api_config.get("models", {})

        # Fallback to standard api config if models dict is missing
        self.model_data = models_config.get(self.selected_model, {})
        if not self.model_data:
            self.model_data = {
                "url": api_config.get("url", ""),
                "useDocOrientationClassify": api_config.get(
                    "useDocOrientationClassify", False
                ),
                "useDocUnwarping": api_config.get("useDocUnwarping", False),
            }

        self.api_url = self.model_data.get("url", "")

    @property
    def name(self) -> str:
        return "paddle"

    def get_hocr(self, image_path: Path) -> str:
        if not self.api_url or not self.token:
            logger.error(
                f"[PaddlePlugin] API URL or Token missing for {self.selected_model}"
            )
            return self._create_empty_hocr(image_path)

        with open(image_path, "rb") as f:
            file_bytes = f.read()
            file_data = base64.b64encode(file_bytes).decode("ascii")

        headers = {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
        }

        # Build Payload based on model requirements
        payload = {
            "file": file_data,
            "fileType": 1,  # Image
            "useDocOrientationClassify": self.model_data.get(
                "useDocOrientationClassify", False
            ),
            "useDocUnwarping": self.model_data.get("useDocUnwarping", False),
            "useTextlineOrientation": self.model_data.get(
                "useTextlineOrientation", False
            ),
        }

        # Model specific overrides/additions
        if self.selected_model == "PP-StructureV3":
            payload.update(
                {
                    "useTableRecognition": self.model_data.get(
                        "useTableRecognition", True
                    ),
                    "useFormulaRecognition": self.model_data.get(
                        "useFormulaRecognition", True
                    ),
                    "useSealRecognition": self.model_data.get(
                        "useSealRecognition", False
                    ),
                    "useChartRecognition": self.model_data.get(
                        "useChartRecognition", False
                    ),
                    "useRegionDetection": self.model_data.get(
                        "useRegionDetection", True
                    ),
                }
            )
        elif "VL" in self.selected_model:
            payload.update(
                {
                    "useLayoutDetection": self.model_data.get(
                        "useLayoutDetection", True
                    ),
                }
            )
            if self.selected_model == "PaddleOCR-VL-1.5":
                payload.update(
                    {
                        "repetitionPenalty": self.model_data.get(
                            "repetitionPenalty", 1.0
                        ),
                        "temperature": self.model_data.get("temperature", 0.1),
                        "topP": self.model_data.get("topP", 0.7),
                    }
                )

        try:
            logger.info(
                f"[PaddlePlugin] Calling {self.selected_model} API: {self.api_url}"
            )
            response = requests.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            res_json = response.json()
            if not isinstance(res_json, dict):
                logger.error(
                    f"[PaddlePlugin] Unexpected response type: {type(res_json).__name__}"
                )
                return self._create_empty_hocr(image_path)

            error_code = res_json.get("errorCode")
            if error_code not in (None, 0):
                logger.error(f"[PaddlePlugin] API error code: {error_code}")
                return self._create_empty_hocr(image_path)

            result = res_json.get("result")
            if result is None:
                result = res_json.get("data", res_json)
            if not isinstance(result, dict):
                logger.error(
                    f"[PaddlePlugin] Unexpected result type: {type(result).__name__}"
                )
                return self._create_empty_hocr(image_path)
            # DEBUG: Log keys and a slice of result
            logger.debug(f"[PaddleAdapter] Result keys: {list(result.keys())}")
            lpr = result.get("layoutParsingResults")
            lpr_list = lpr if isinstance(lpr, list) else []
            if lpr_list:
                logger.debug(
                    f"[PaddleAdapter] layoutParsingResults length: {len(lpr_list)}"
                )
                first_item = lpr_list[0]
                if isinstance(first_item, dict):
                    logger.debug(
                        f"[PaddleAdapter] First item keys in lpr: {list(first_item.keys())}"
                    )

            lines = []

            # Determine response key based on model type
            # v5 uses ocrResults; Structure/VL uses layoutParsingResults
            if self.selected_model == "PP-OCRv5":
                ocr_pages = result.get("ocrResults", [])
            else:
                ocr_pages = result.get("layoutParsingResults", [])

            if not isinstance(ocr_pages, list):
                logger.warning(
                    f"[PaddlePlugin] OCR pages not a list for {self.selected_model}"
                )
                return self._create_empty_hocr(image_path)

            if not ocr_pages:
                logger.warning(
                    f"[PaddlePlugin] No OCR results found for {self.selected_model}"
                )
                return self._create_empty_hocr(image_path)

            # Standard pipeline only processes one image at a time via this plugin
            page_res = ocr_pages[0]
            if not isinstance(page_res, dict):
                logger.warning(
                    f"[PaddlePlugin] OCR page result not a dict for {self.selected_model}"
                )
                return self._create_empty_hocr(image_path)

            pruned = page_res.get("prunedResult")
            if pruned is None:
                pruned = {}
            # Parsing logic
            ocr_data = []
            if isinstance(pruned, list):
                ocr_data = pruned
            elif isinstance(pruned, dict):
                # Check pruned first
                if "rec_texts" in pruned and "rec_boxes" in pruned:
                    ocr_data = [pruned]
                elif "res" in pruned:
                    ocr_data = pruned["res"]
                elif "parsing_res_list" in pruned:
                    ocr_data = pruned["parsing_res_list"]

                # Check page_res directly (fallback)
                if not ocr_data:
                    if "rec_texts" in page_res and "rec_boxes" in page_res:
                        ocr_data = [page_res]
                    elif "res" in page_res:
                        ocr_data = page_res["res"]

            for item in ocr_data:
                # Format A: Standard OCR (list of [box, text, score])
                if isinstance(item, list) and len(item) >= 2:
                    pos = item[0]
                    text = str(item[1])
                    if isinstance(pos, list):
                        if len(pos) == 4 and isinstance(pos[0], list):  # [[x,y],...]
                            xs = [p[0] for p in pos]
                            ys = [p[1] for p in pos]
                            hocr_box = _validate_bbox(
                                [
                                    int(min(xs)),
                                    int(min(ys)),
                                    int(max(xs)),
                                    int(max(ys)),
                                ]
                            )
                            if hocr_box:
                                lines.append({"text": text, "bbox": hocr_box})
                        elif len(pos) >= 8:  # Flat [x1,y1,x2,y2,x3,y3,x4,y4]
                            hocr_box = _validate_bbox(
                                [
                                    int(min(pos[0::2])),
                                    int(min(pos[1::2])),
                                    int(max(pos[0::2])),
                                    int(max(pos[1::2])),
                                ]
                            )
                            if hocr_box:
                                lines.append({"text": text, "bbox": hocr_box})

                # Format B: Layout Parsing blocks
                elif isinstance(item, dict):
                    # Check for PP-OCRv5 specific nested results (rec_boxes/rec_texts)
                    rec_texts = item.get("rec_texts")
                    rec_boxes = item.get("rec_boxes")
                    if rec_texts and rec_boxes and len(rec_texts) == len(rec_boxes):
                        for t, b in zip(rec_texts, rec_boxes):
                            # rec_boxes is usually [x1,y1,x2,y2,x3,y3,x4,y4]
                            if len(b) >= 4:
                                hocr_box = _validate_bbox(
                                    [
                                        int(min(b[0::2])),
                                        int(min(b[1::2])),
                                        int(max(b[0::2])),
                                        int(max(b[1::2])),
                                    ]
                                )
                                if hocr_box:
                                    lines.append({"text": str(t), "bbox": hocr_box})
                    else:
                        text = item.get("block_content") or item.get("text")
                        box = (
                            item.get("block_bbox")
                            or item.get("bbox")
                            or item.get("pos")
                        )
                        if text and box:
                            if isinstance(box, list):
                                if len(box) == 4:
                                    hocr_box = _validate_bbox([int(v) for v in box])
                                    if hocr_box:
                                        lines.append(
                                            {
                                                "text": str(text),
                                                "bbox": hocr_box,
                                            }
                                        )
                                elif len(box) >= 8:
                                    hocr_box = _validate_bbox(
                                        [
                                            int(min(box[0::2])),
                                            int(min(box[1::2])),
                                            int(max(box[0::2])),
                                            int(max(box[1::2])),
                                        ]
                                    )
                                    if hocr_box:
                                        lines.append(
                                            {
                                                "text": str(text),
                                                "bbox": hocr_box,
                                            }
                                        )

            from PIL import Image

            with Image.open(image_path) as img:
                w, h = img.size

            return create_hocr_page(image_path.name, lines, width=int(w), height=int(h))

        except Exception as e:
            logger.error(
                f"[PaddlePlugin] Integration failed for {self.selected_model}: {e}"
            )
            return self._create_empty_hocr(image_path)

    def _create_empty_hocr(self, image_path: Path) -> str:
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                w, h = img.size
        except Exception:
            w, h = 1, 1
        return create_hocr_page(image_path.name, [], width=int(w), height=int(h))
