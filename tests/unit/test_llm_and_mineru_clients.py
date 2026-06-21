from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter

from src.services.llm_service import LLMService
from src.utils.mineru_api import MinerUClient


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self.payload = payload
        self.status_code = status_code
        self.content = b""
        self.text = str(payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self.payload


def write_blank_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as output:
        writer.write(output)


def test_call_llm_builds_openai_compatible_payload(monkeypatch):
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse({"choices": [{"message": {"content": "Clean @ 1"}}]})

    monkeypatch.setattr("src.services.llm_service.requests.post", fake_post)

    result = LLMService().call_llm(
        "raw text",
        {
            "provider": "openai",
            "base_url": "https://api.example.test/v1",
            "api_key": "sk-test",
            "model_name": "model-a",
            "prompt": "Fix:\n{text}",
        },
    )

    assert result == "Clean @ 1"
    assert calls[0]["url"] == "https://api.example.test/v1/chat/completions"
    assert calls[0]["headers"]["Authorization"] == "Bearer sk-test"
    assert calls[0]["json"]["messages"][0]["content"] == "Fix:\nraw text"


def test_call_vlm_builds_ollama_payload(monkeypatch, tmp_path):
    pdf_path = tmp_path / "page.pdf"
    write_blank_pdf(pdf_path)
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse({"message": {"content": "Visual TOC @ 1"}})

    monkeypatch.setattr("src.services.llm_service.requests.post", fake_post)

    result = LLMService().call_vlm(
        pdf_path,
        1,
        1,
        {
            "provider": "ollama",
            "base_url": "http://localhost:11434",
            "model_name": "deepseek-ocr:latest",
            "prompt": "Extract TOC",
            "timeout_seconds": 5,
        },
    )

    assert result == "Visual TOC @ 1"
    assert calls[0]["url"] == "http://localhost:11434/api/chat"
    assert calls[0]["json"]["messages"][0]["images"]
    assert calls[0]["json"]["think"] is False
    assert calls[0]["timeout"] == 5


def test_call_llm_disables_ollama_thinking_by_default(monkeypatch):
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse({"message": {"content": "Clean @ 1"}})

    monkeypatch.setattr("src.services.llm_service.requests.post", fake_post)

    result = LLMService().call_llm(
        "raw text",
        {
            "provider": "ollama",
            "base_url": "http://localhost:11434",
            "model_name": "glm-4.7-flash:latest",
            "prompt": "Fix:\n{text}",
        },
    )

    assert result == "Clean @ 1"
    assert calls[0]["url"] == "http://localhost:11434/api/chat"
    assert calls[0]["json"]["think"] is False


def test_call_llm_allows_ollama_thinking_when_enabled(monkeypatch):
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse({"message": {"content": "Clean @ 1"}})

    monkeypatch.setattr("src.services.llm_service.requests.post", fake_post)

    LLMService().call_llm(
        "raw text",
        {
            "provider": "ollama",
            "base_url": "http://localhost:11434",
            "model_name": "glm-4.7-flash:latest",
            "think": True,
        },
    )

    assert calls[0]["json"]["think"] is True


def test_mineru_poll_respects_timeout(monkeypatch):
    client = MinerUClient(
        "https://mineru.net/api/v4/file-urls/batch",
        "key",
        poll_interval=0,
        poll_timeout=0,
    )

    def fake_get(url, headers):
        return FakeResponse({"code": 0, "data": {"extract_result": []}})

    monkeypatch.setattr("src.utils.mineru_api.requests.get", fake_get)

    try:
        client._poll_batch("batch-id")
    except TimeoutError as exc:
        assert "MinerU task timed out" in str(exc)
    else:
        raise AssertionError("Expected MinerU polling to time out")
