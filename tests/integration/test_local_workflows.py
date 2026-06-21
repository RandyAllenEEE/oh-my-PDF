from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from pypdf import PdfReader

from src import main
from src.services.ocr_service import OCRService


def write_text_pdf(path: Path) -> None:
    image = Image.new("RGB", (900, 300), "white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 120), "Oh My PDF OCR smoke test", fill="black")
    image.save(path, "PDF", resolution=150.0)


def configure_workspace(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    monkeypatch.setattr(main, "WORKSPACE_DIR", workspace)
    monkeypatch.setattr(main, "UPLOAD_DIR", workspace / "uploads")
    monkeypatch.setattr(main, "OUTPUT_DIR", workspace / "outputs")
    main.ensure_workspace_dirs()
    return workspace


def test_runtime_config_copy_contains_all_modes(runtime_config):
    assert runtime_config["engines"]["tesseract"]["bin_path"]
    assert runtime_config["engines"]["paddle"]["api"]["key"]
    assert runtime_config["engines"]["paddle"]["api"]["models"]["PP-OCRv5"]["url"]
    assert runtime_config["engines"]["mineru"]["api"]["key"]
    assert runtime_config["engines"]["deepseek"]["ollama"]["model"]
    assert runtime_config["bookmark_models"]["vlm"]["enabled"] is True
    assert runtime_config["bookmark_models"]["llm"]["enabled"] is True


def test_fastapi_upload_task_and_download_flow(monkeypatch, tmp_path):
    configure_workspace(monkeypatch, tmp_path)

    with TestClient(main.app) as client:
        upload = client.post(
            "/api/files/upload",
            files={"file": ("sample.pdf", b"%PDF-1.4\n%%EOF\n", "application/pdf")},
        )
        assert upload.status_code == 200
        uploaded = upload.json()

        output = main.OUTPUT_DIR / "result.pdf"
        output.write_bytes(b"%PDF-1.4\n%%EOF\n")
        main.task_registry.clear()
        main.task_registry["done"] = main.TaskInfo(
            task_id="done",
            status=main.TaskStatus.SUCCESS,
            task_type="ocr",
            input_path=uploaded["path"],
            output_path=str(output),
            progress=100,
        )

        status = client.get("/api/tasks/done")
        assert status.status_code == 200
        download_url = status.json()["download_url"]
        download = client.get(download_url)
        assert download.status_code == 200
        assert download.content == b"%PDF-1.4\n%%EOF\n"


@pytest.mark.local_ocr
@pytest.mark.slow
def test_local_tesseract_ocr_smoke(runtime_config, tmp_path):
    tesseract_path = runtime_config["engines"]["tesseract"].get("bin_path")
    if tesseract_path and not Path(tesseract_path).exists():
        pytest.skip(f"Configured Tesseract path does not exist: {tesseract_path}")
    if not (shutil.which("gswin64c") or shutil.which("gswin32c") or shutil.which("gs")):
        pytest.skip("Ghostscript command is not available on PATH")

    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "output.pdf"
    write_text_pdf(input_pdf)

    OCRService(runtime_config).run_ocr(input_pdf, output_pdf, "tesseract", optimize=0)

    assert output_pdf.exists()
    assert len(PdfReader(str(output_pdf)).pages) == 1
