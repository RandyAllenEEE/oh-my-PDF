from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from src.plugins import bridge as bridge_module
from src.services.ocr_service import OCRService
from src.utils.hocr import create_hocr_page
from tests.helpers.pdf_alignment import (
    CUSTOM_BOXES,
    assert_dual_layer_pdf_has_text_at,
    expected_custom_boxes_for_pdf,
    has_ghostscript,
    write_image_pdf,
    write_text_image_pdf,
)


class AlignmentAdapter:
    name = "alignment-test"

    def __init__(self, config):
        self.config = config

    def get_hocr(self, image_path: Path) -> str:
        with Image.open(image_path) as image:
            width, height = image.size

        lines = []
        for word, box in CUSTOM_BOXES.items():
            lines.append(
                {
                    "text": word,
                    "bbox": [
                        round(box[0] * width),
                        round(box[1] * height),
                        round(box[2] * width),
                        round(box[3] * height),
                    ],
                    "confidence": 0.99,
                }
            )

        return create_hocr_page(
            image_path.name, lines, width=int(width), height=int(height)
        )


@pytest.mark.local_ocr
@pytest.mark.slow
@pytest.mark.parametrize("engine_name", ["paddle", "deepseek", "mineru"])
@pytest.mark.parametrize("ocr_mode", ["normal", "force", "skip"])
def test_custom_ocr_modes_place_text_layer_in_expected_regions(
    monkeypatch, tmp_path, engine_name, ocr_mode
):
    if not has_ghostscript():
        pytest.skip("Ghostscript command is not available on PATH")

    input_pdf = tmp_path / f"{engine_name}_{ocr_mode}_input.pdf"
    output_pdf = tmp_path / f"{engine_name}_{ocr_mode}_output.pdf"
    write_image_pdf(input_pdf)
    monkeypatch.setitem(bridge_module.ADAPTERS, engine_name, AlignmentAdapter)

    service = OCRService(
        {
            "engines": {
                "tesseract": {"provider": "native", "languages": "eng"},
                "paddle": {"provider": "api", "api": {"key": "test-token"}},
                "deepseek": {
                    "provider": "ollama",
                    "ollama": {"url": "http://localhost:11434", "model": "test"},
                },
                "mineru": {"provider": "local"},
            }
        }
    )

    service.run_ocr(input_pdf, output_pdf, engine_name, ocr_mode=ocr_mode, optimize=0)

    assert_dual_layer_pdf_has_text_at(
        output_pdf, expected_custom_boxes_for_pdf(output_pdf)
    )


@pytest.mark.local_ocr
@pytest.mark.slow
@pytest.mark.parametrize("ocr_mode", ["normal", "force", "skip"])
def test_tesseract_mode_places_text_layer_near_source_text(
    runtime_config, tmp_path, ocr_mode
):
    if not has_ghostscript():
        pytest.skip("Ghostscript command is not available on PATH")

    tesseract_path = runtime_config["engines"]["tesseract"].get("bin_path")
    if tesseract_path and not Path(tesseract_path).exists():
        pytest.skip(f"Configured Tesseract path does not exist: {tesseract_path}")

    input_pdf = tmp_path / f"tesseract_{ocr_mode}_input.pdf"
    output_pdf = tmp_path / f"tesseract_{ocr_mode}_output.pdf"
    expected_boxes = write_text_image_pdf(input_pdf)

    OCRService(runtime_config).run_ocr(
        input_pdf, output_pdf, "tesseract", ocr_mode=ocr_mode, optimize=0
    )

    assert_dual_layer_pdf_has_text_at(output_pdf, expected_boxes, tolerance=72.0)
