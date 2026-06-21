from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from src.services.ocr_service import OCRService
from tests.helpers.pdf_alignment import (
    assert_dual_layer_pdf_has_text_at,
    has_ghostscript,
    write_text_image_pdf,
)


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_") or "model"


def run_real_ocr_alignment(
    config: dict[str, Any],
    engine_name: str,
    tmp_path: Path,
    case_name: str,
    *,
    tolerance: float = 96.0,
) -> None:
    if not has_ghostscript():
        pytest.skip("Ghostscript command is not available on PATH")

    input_pdf = tmp_path / f"{case_name}_input.pdf"
    output_pdf = tmp_path / f"{case_name}_output.pdf"
    expected_boxes = write_text_image_pdf(input_pdf)

    OCRService(config).run_ocr(input_pdf, output_pdf, engine_name, optimize=0)

    assert_dual_layer_pdf_has_text_at(output_pdf, expected_boxes, tolerance=tolerance)


@pytest.mark.external
@pytest.mark.slow
def test_external_paddle_models_place_text_layer_near_source_text(
    runtime_config, tmp_path
):
    paddle_config = runtime_config["engines"]["paddle"]
    api = paddle_config["api"]
    if not api.get("key"):
        pytest.skip("Paddle token is not configured")

    models = api.get("models", {})
    if not models:
        pytest.skip("No Paddle models are configured")

    for model_name, model_data in models.items():
        if not model_data.get("url"):
            pytest.skip(f"Paddle model {model_name} has no endpoint")

        config = deepcopy(runtime_config)
        config["engines"]["paddle"]["api"]["selected_model"] = model_name

        run_real_ocr_alignment(
            config,
            "paddle",
            tmp_path,
            f"paddle_{safe_name(model_name)}",
            tolerance=120.0,
        )


@pytest.mark.external
@pytest.mark.slow
def test_external_deepseek_places_text_layer_near_source_text(
    runtime_config, tmp_path, monkeypatch
):
    monkeypatch.setenv("OH_MY_PDF_OLLAMA_TIMEOUT_SEC", "900")
    deepseek_config = runtime_config["engines"]["deepseek"]
    if not deepseek_config.get("ollama", {}).get("model"):
        pytest.skip("DeepSeek/Ollama model is not configured")

    run_real_ocr_alignment(
        runtime_config,
        "deepseek",
        tmp_path,
        "deepseek",
        tolerance=144.0,
    )


@pytest.mark.external
@pytest.mark.slow
def test_external_mineru_places_text_layer_near_source_text(
    runtime_config, tmp_path, monkeypatch
):
    monkeypatch.setenv("OH_MY_PDF_MINERU_POLL_TIMEOUT_SEC", "1200")
    mineru_api = runtime_config["engines"]["mineru"]["api"]
    if not mineru_api.get("key") or not mineru_api.get("url"):
        pytest.skip("MinerU API key or endpoint is not configured")

    run_real_ocr_alignment(
        runtime_config,
        "mineru",
        tmp_path,
        "mineru",
        tolerance=144.0,
    )
