from pathlib import Path

from src.plugins import bridge
from src.services import ocr_service as ocr_module
from src.services.ocr_service import OCRService


def test_run_ocr_passes_tesseract_languages_without_equ(monkeypatch, tmp_path):
    calls = {}

    def fake_ocr(input_file: Path, output_file: Path, **kwargs):
        calls["input_file"] = input_file
        calls["output_file"] = output_file
        calls["kwargs"] = kwargs
        return 0

    monkeypatch.setattr(ocr_module.ocrmypdf, "ocr", fake_ocr)
    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "output.pdf"
    input_pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")

    service = OCRService(
        {
            "engines": {
                "tesseract": {
                    "provider": "native",
                    "languages": "eng;chi_sim;equ",
                    "bin_path": "",
                }
            }
        }
    )

    service.run_ocr(input_pdf, output_pdf, "tesseract")

    assert calls["input_file"] == input_pdf
    assert calls["output_file"] == output_pdf
    assert calls["kwargs"]["language"] == ["eng", "chi_sim"]
    assert "plugins" not in calls["kwargs"]


def test_run_ocr_injects_bridge_for_custom_engine(monkeypatch, tmp_path):
    calls = {}

    def fake_ocr(input_file: Path, output_file: Path, **kwargs):
        calls["kwargs"] = kwargs
        return 0

    monkeypatch.setattr(ocr_module.ocrmypdf, "ocr", fake_ocr)
    monkeypatch.setattr(
        OCRService, "_get_plugin_module_path", lambda self: "src.plugins.bridge"
    )

    input_pdf = tmp_path / "input.pdf"
    output_pdf = tmp_path / "output.pdf"
    input_pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")

    service = OCRService(
        {
            "engines": {
                "tesseract": {"provider": "native", "languages": "eng"},
                "paddle": {"provider": "api", "api": {"key": "token"}},
            }
        }
    )

    service.run_ocr(input_pdf, output_pdf, "paddle")

    assert calls["kwargs"]["plugins"] == ["src.plugins.bridge"]
    assert calls["kwargs"]["pdf_renderer"] == "hocr"


def test_custom_ocr_engine_reports_current_bridge_version(monkeypatch):
    class FakeAdapter:
        name = "fake"

        def __init__(self, config):
            self.config = config

    monkeypatch.setitem(bridge.ADAPTERS, "fake", FakeAdapter)

    engine = bridge.CustomOcrEngine("fake", {"provider": "api"})

    assert engine.version() == bridge.PLUGIN_BRIDGE_VERSION


def test_run_ocr_passes_force_and_skip_modes(monkeypatch, tmp_path):
    calls = []

    def fake_ocr(input_file: Path, output_file: Path, **kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(ocr_module.ocrmypdf, "ocr", fake_ocr)
    input_pdf = tmp_path / "input.pdf"
    input_pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")

    service = OCRService(
        {"engines": {"tesseract": {"provider": "native", "languages": "eng"}}}
    )

    service.run_ocr(input_pdf, tmp_path / "force.pdf", "tesseract", ocr_mode="force")
    service.run_ocr(input_pdf, tmp_path / "skip.pdf", "tesseract", ocr_mode="skip")
    service.run_ocr(input_pdf, tmp_path / "normal.pdf", "tesseract")

    assert calls[0]["force_ocr"] is True
    assert "skip_text" not in calls[0]
    assert calls[1]["skip_text"] is True
    assert "force_ocr" not in calls[1]
    assert "force_ocr" not in calls[2]
    assert "skip_text" not in calls[2]


def test_run_ocr_rejects_unknown_mode(tmp_path):
    input_pdf = tmp_path / "input.pdf"
    input_pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
    service = OCRService({})

    try:
        service.run_ocr(input_pdf, tmp_path / "out.pdf", "tesseract", ocr_mode="bad")
    except ValueError as exc:
        assert "Unsupported OCR mode" in str(exc)
    else:
        raise AssertionError("Expected unsupported OCR mode to fail")
