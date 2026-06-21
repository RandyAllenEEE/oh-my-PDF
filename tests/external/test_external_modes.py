from __future__ import annotations

import re
from pathlib import Path

import pytest
from PIL import Image, ImageDraw
from pypdf import PdfWriter

from src.plugins.deepseek import DeepSeekAdapter
from src.plugins.paddle import PaddleAdapter
from src.services.llm_service import LLMService
from src.utils.mineru_api import MinerUClient


def write_png(path: Path) -> None:
    image = Image.new("RGB", (900, 300), "white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 120), "External OCR smoke test", fill="black")
    image.save(path)


def write_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=200)
    with path.open("wb") as output:
        writer.write(output)


def assert_hocr_has_words(hocr: str) -> None:
    assert "ocr_page" in hocr
    assert re.search(r"<span class=[\"']ocrx_word[\"']", hocr), hocr[:500]


@pytest.mark.external
@pytest.mark.slow
def test_external_paddle_all_configured_models(runtime_config, tmp_path):
    paddle_config = runtime_config["engines"]["paddle"]
    api = paddle_config["api"]
    if not api.get("key"):
        pytest.skip("Paddle token is not configured")

    image_path = tmp_path / "paddle.png"
    write_png(image_path)

    for model_name, model_data in api.get("models", {}).items():
        if not model_data.get("url"):
            pytest.skip(f"Paddle model {model_name} has no endpoint")
        config = {
            **paddle_config,
            "api": {
                **api,
                "selected_model": model_name,
            },
        }
        hocr = PaddleAdapter(config).get_hocr(image_path)
        assert_hocr_has_words(hocr)


@pytest.mark.external
@pytest.mark.slow
def test_external_deepseek_ollama(runtime_config, tmp_path, monkeypatch):
    monkeypatch.setenv("OH_MY_PDF_OLLAMA_TIMEOUT_SEC", "900")
    deepseek_config = runtime_config["engines"]["deepseek"]
    if not deepseek_config.get("ollama", {}).get("model"):
        pytest.skip("DeepSeek/Ollama model is not configured")

    image_path = tmp_path / "deepseek.png"
    write_png(image_path)

    hocr = DeepSeekAdapter(deepseek_config).get_hocr(image_path)
    assert_hocr_has_words(hocr)


@pytest.mark.external
@pytest.mark.slow
def test_external_bookmark_llm_ollama(runtime_config, monkeypatch):
    monkeypatch.setenv("OH_MY_PDF_LLM_TIMEOUT_SEC", "900")
    config = runtime_config["bookmark_models"]["llm"]
    if not config.get("enabled"):
        pytest.skip("Bookmark LLM is disabled")

    result = LLMService().call_llm("Intro 1\nChapter 2", config)

    assert result.strip()


@pytest.mark.external
@pytest.mark.slow
def test_external_bookmark_vlm_ollama(runtime_config, tmp_path, monkeypatch):
    monkeypatch.setenv("OH_MY_PDF_LLM_TIMEOUT_SEC", "900")
    config = runtime_config["bookmark_models"]["vlm"]
    if not config.get("enabled"):
        pytest.skip("Bookmark VLM is disabled")

    pdf_path = tmp_path / "vlm.pdf"
    write_pdf(pdf_path)

    result = LLMService().call_vlm(pdf_path, 1, 1, config)

    assert result.strip()


@pytest.mark.external
@pytest.mark.slow
def test_external_mineru_pipeline(runtime_config, tmp_path, monkeypatch):
    monkeypatch.setenv("OH_MY_PDF_MINERU_POLL_TIMEOUT_SEC", "1200")
    mineru_api = runtime_config["engines"]["mineru"]["api"]
    if not mineru_api.get("key") or not mineru_api.get("url"):
        pytest.skip("MinerU API key or endpoint is not configured")

    pdf_path = tmp_path / "mineru.pdf"
    write_pdf(pdf_path)

    result = MinerUClient(mineru_api["url"], mineru_api["key"]).process_file(
        pdf_path,
        model=mineru_api.get("model", "pipeline"),
        is_ocr=mineru_api.get("is_ocr", True),
        enable_formula=mineru_api.get("enable_formula", True),
        enable_table=mineru_api.get("enable_table", True),
        language=mineru_api.get("language", "ch"),
    )

    assert result.get("state") == "done"
    assert (
        result.get("full_zip_url") or result.get("full_md_url") or result.get("data_id")
    )
