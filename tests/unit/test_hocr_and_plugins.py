from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from src.plugins.deepseek import DeepSeekAdapter
from src.plugins.mineru import MinerUPlugin
from src.plugins.paddle import PaddleAdapter
from src.utils.hocr import create_hocr_page


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def write_png(path: Path, size: tuple[int, int] = (100, 80)) -> None:
    Image.new("RGB", size, "white").save(path)


def test_create_hocr_page_escapes_text():
    hocr = create_hocr_page(
        "page.png",
        [{"text": "A&B <C>", "bbox": [1, 2, 30, 40], "confidence": 0.88}],
        width=100,
        height=80,
    )

    assert "A&amp;B &lt;C&gt;" in hocr
    assert "bbox 1 2 30 40" in hocr
    assert 'class="ocrx_word"' in hocr


def test_deepseek_parser_denormalizes_ref_det_tags():
    adapter = DeepSeekAdapter(
        {"ollama": {"url": "http://localhost:11434", "model": "deepseek-ocr:latest"}}
    )

    lines = adapter._parse_deepseek_output(
        "<|ref|>Hello<|/ref|><|det|>[[100,200,400,300]]",
        width=1000,
        height=2000,
    )

    assert lines == [{"text": "Hello", "bbox": [100, 400, 400, 600], "confidence": 0.9}]


def test_deepseek_parser_handles_grounding_text_boxes():
    adapter = DeepSeekAdapter(
        {"ollama": {"url": "http://localhost:11434", "model": "deepseek-ocr:latest"}}
    )

    lines = adapter._parse_deepseek_output(
        "text[[175, 205, 383, 289]]\nALPHA \n\n" "text[[595, 666, 825, 749]]\nOMEGA",
        width=720,
        height=480,
    )

    assert lines == [
        {"text": "ALPHA", "bbox": [126, 98, 276, 139], "confidence": 0.9},
        {"text": "OMEGA", "bbox": [428, 320, 594, 360], "confidence": 0.9},
    ]


def test_deepseek_ollama_payload_disables_thinking(monkeypatch, tmp_path):
    image_path = tmp_path / "page.png"
    write_png(image_path, size=(100, 80))
    calls: list[dict] = []

    def fake_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse(
            {"response": "<|ref|>Hello<|/ref|><|det|>[[100,200,400,300]]"}
        )

    monkeypatch.setattr("src.plugins.deepseek.requests.post", fake_post)

    hocr = DeepSeekAdapter(
        {"ollama": {"url": "http://localhost:11434", "model": "deepseek-ocr:latest"}}
    ).get_hocr(image_path)

    assert "Hello" in hocr
    assert "bbox 10 16 40 24" in hocr
    assert calls[0]["url"] == "http://localhost:11434/api/generate"
    assert calls[0]["json"]["think"] is False


def test_paddle_payloads_and_hocr_for_each_model(monkeypatch, tmp_path):
    image_path = tmp_path / "page.png"
    write_png(image_path)
    calls: list[dict] = []

    def fake_post(url, json, headers):
        calls.append({"url": url, "json": json, "headers": headers})
        if url.endswith("/ocr"):
            payload = {
                "errorCode": 0,
                "result": {
                    "ocrResults": [
                        {
                            "prunedResult": {
                                "rec_texts": ["Hello Paddle"],
                                "rec_boxes": [[1, 2, 40, 2, 40, 20, 1, 20]],
                            }
                        }
                    ]
                },
            }
        else:
            payload = {
                "errorCode": 0,
                "result": {
                    "layoutParsingResults": [
                        {
                            "prunedResult": {
                                "parsing_res_list": [
                                    {
                                        "block_content": "Layout Block",
                                        "block_bbox": [1, 2, 50, 30],
                                    }
                                ]
                            }
                        }
                    ]
                },
            }
        return FakeResponse(payload)

    monkeypatch.setattr("src.plugins.paddle.requests.post", fake_post)

    models = {
        "PP-OCRv5": {"url": "https://example.test/ocr"},
        "PP-StructureV3": {"url": "https://example.test/layout-parsing"},
        "PaddleOCR-VL": {"url": "https://example.test/layout-parsing"},
        "PaddleOCR-VL-1.5": {
            "url": "https://example.test/layout-parsing",
            "temperature": 0.2,
            "topP": 0.8,
        },
    }

    for model in models:
        adapter = PaddleAdapter(
            {"api": {"selected_model": model, "key": "secret-token", "models": models}}
        )
        hocr = adapter.get_hocr(image_path)
        expected_text = "Hello Paddle" if model == "PP-OCRv5" else "Layout Block"
        expected_bbox = "bbox 1 2 40 20" if model == "PP-OCRv5" else "bbox 1 2 50 30"

        assert "ocr_page" in hocr
        assert expected_text in hocr
        assert expected_bbox in hocr

    assert len(calls) == 4
    assert calls[0]["headers"]["Authorization"] == "token secret-token"
    assert calls[1]["json"]["useTableRecognition"] is True
    assert calls[2]["json"]["useLayoutDetection"] is True
    assert calls[3]["json"]["temperature"] == 0.2


def test_mineru_json_generates_scaled_hocr(monkeypatch, tmp_path):
    image_path = tmp_path / "000001.png"
    write_png(image_path, size=(200, 200))
    json_path = tmp_path / "mineru.json"
    json_path.write_text(
        json.dumps(
            {
                "pdf_info": [
                    {
                        "page_idx": 0,
                        "page_size": [100, 100],
                        "para_blocks": [
                            {
                                "type": "text",
                                "lines": [
                                    {
                                        "bbox": [10, 10, 90, 20],
                                        "spans": [
                                            {
                                                "bbox": [10, 10, 40, 20],
                                                "content": "MinerU",
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("MINERU_JSON_PATH", str(json_path))

    hocr = MinerUPlugin({}).get_hocr(image_path)

    assert "MinerU" in hocr
    assert "bbox 20 20 180 40" in hocr
    assert "bbox 20 20 80 40" in hocr


def test_mineru_layout_dets_json_generates_scaled_hocr(monkeypatch, tmp_path):
    image_path = tmp_path / "000001.png"
    write_png(image_path, size=(200, 100))
    json_path = tmp_path / "mineru_layout_dets.json"
    json_path.write_text(
        json.dumps(
            [
                {
                    "layout_dets": [
                        {
                            "label": "text",
                            "bbox": [10, 20, 90, 40],
                        },
                        {
                            "label": "ocr_text",
                            "bbox": [100, 50, 180, 80],
                            "text": "Layout OCR",
                        },
                    ],
                    "page_info": {"page_no": 0, "width": 200, "height": 100},
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("MINERU_JSON_PATH", str(json_path))

    hocr = MinerUPlugin({}).get_hocr(image_path)

    assert "Layout OCR" in hocr
    assert "bbox 100 50 180 80" in hocr


def test_mineru_page_block_list_json_generates_scaled_hocr(monkeypatch, tmp_path):
    image_path = tmp_path / "000001.png"
    write_png(image_path, size=(720, 480))
    json_path = tmp_path / "mineru_page_blocks.json"
    json_path.write_text(
        json.dumps(
            [
                [
                    {
                        "type": "paragraph",
                        "content": {
                            "paragraph_content": [{"type": "text", "content": "ALPHA"}]
                        },
                        "bbox": [169, 197, 390, 295],
                    }
                ]
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("MINERU_JSON_PATH", str(json_path))

    hocr = MinerUPlugin({}).get_hocr(image_path)

    assert "ALPHA" in hocr
    assert "bbox 121 94 280 141" in hocr


def test_mineru_root_block_list_json_generates_scaled_hocr(monkeypatch, tmp_path):
    image_path = tmp_path / "000001.png"
    write_png(image_path, size=(720, 480))
    json_path = tmp_path / "mineru_root_blocks.json"
    json_path.write_text(
        json.dumps(
            [
                {
                    "type": "text",
                    "text": "ALPHA",
                    "bbox": [169, 197, 390, 295],
                    "page_idx": 0,
                },
                {
                    "type": "text",
                    "text": "OMEGA",
                    "bbox": [588, 658, 833, 756],
                    "page_idx": 0,
                },
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("MINERU_JSON_PATH", str(json_path))

    hocr = MinerUPlugin({}).get_hocr(image_path)

    assert "ALPHA" in hocr
    assert "OMEGA" in hocr
    assert "bbox 121 94 280 141" in hocr
    assert "bbox 423 315 599 362" in hocr
