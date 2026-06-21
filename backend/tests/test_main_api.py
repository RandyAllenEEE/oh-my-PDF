from fastapi.testclient import TestClient
import pytest
import socket

from src import main


def configure_workspace(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    monkeypatch.setattr(main, "WORKSPACE_DIR", workspace)
    monkeypatch.setattr(main, "UPLOAD_DIR", workspace / "uploads")
    monkeypatch.setattr(main, "OUTPUT_DIR", workspace / "outputs")
    main.ensure_workspace_dirs()
    return workspace


def test_upload_and_download_pdf(monkeypatch, tmp_path):
    configure_workspace(monkeypatch, tmp_path)

    with TestClient(main.app) as client:
        upload = client.post(
            "/api/files/upload",
            files={"file": ("sample.pdf", b"%PDF-1.4\n%%EOF\n", "application/pdf")},
        )
        assert upload.status_code == 200
        payload = upload.json()
        assert payload["filename"] == "sample.pdf"
        assert payload["path"].endswith(".pdf")

        download = client.get("/api/files/download", params={"path": payload["path"]})
        assert download.status_code == 200
        assert download.content == b"%PDF-1.4\n%%EOF\n"


def test_download_rejects_files_outside_workspace(monkeypatch, tmp_path):
    configure_workspace(monkeypatch, tmp_path)
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"%PDF-1.4\n%%EOF\n")

    with TestClient(main.app) as client:
        response = client.get("/api/files/download", params={"path": str(outside)})

    assert response.status_code == 403


def test_ocr_rejects_input_outside_workspace(monkeypatch, tmp_path):
    configure_workspace(monkeypatch, tmp_path)
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"%PDF-1.4\n%%EOF\n")

    with TestClient(main.app) as client:
        response = client.post(
            "/api/ocr",
            json={"input_path": str(outside), "engine": "tesseract"},
        )

    assert response.status_code == 403


def test_ocr_rejects_output_outside_workspace(monkeypatch, tmp_path):
    configure_workspace(monkeypatch, tmp_path)
    source = main.UPLOAD_DIR / "source.pdf"
    source.write_bytes(b"%PDF-1.4\n%%EOF\n")
    outside = tmp_path / "outside.pdf"

    with TestClient(main.app) as client:
        response = client.post(
            "/api/ocr",
            json={
                "input_path": str(source),
                "output_path": str(outside),
                "engine": "tesseract",
            },
        )

    assert response.status_code == 403


def test_bookmark_extract_rejects_input_outside_workspace(monkeypatch, tmp_path):
    configure_workspace(monkeypatch, tmp_path)
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"%PDF-1.4\n%%EOF\n")

    with TestClient(main.app) as client:
        response = client.post(
            "/api/bookmarks/extract",
            json={"input_path": str(outside)},
        )

    assert response.status_code == 403


def test_task_status_includes_download_url(monkeypatch, tmp_path):
    configure_workspace(monkeypatch, tmp_path)
    output = main.OUTPUT_DIR / "result.pdf"
    output.write_bytes(b"%PDF-1.4\n%%EOF\n")
    main.task_registry.clear()
    main.task_registry["task-1"] = main.TaskInfo(
        task_id="task-1",
        status=main.TaskStatus.SUCCESS,
        task_type="bookmark",
        input_path=str(main.UPLOAD_DIR / "source.pdf"),
        output_path=str(output),
        progress=100,
    )

    with TestClient(main.app) as client:
        response = client.get("/api/tasks/task-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["download_url"].startswith("/api/files/download?path=")


def test_cors_allows_localhost_on_custom_ports():
    with TestClient(main.app) as client:
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://127.0.0.1:18124",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:18124"


def test_health_reports_version():
    with TestClient(main.app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["version"] == main.APP_VERSION


def test_cors_rejects_nonlocal_origins():
    with TestClient(main.app) as client:
        response = client.options(
            "/api/health",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_maybe_open_browser_uses_start_url(monkeypatch):
    calls = []
    monkeypatch.delenv("PDF_TOOLBOX_NO_BROWSER", raising=False)
    monkeypatch.setattr(main.webbrowser, "open", lambda url: calls.append(url) or True)

    assert main.maybe_open_browser() is True
    assert calls == [main.START_URL]


def test_maybe_open_browser_can_be_disabled(monkeypatch):
    calls = []
    monkeypatch.setenv("PDF_TOOLBOX_NO_BROWSER", "1")
    monkeypatch.setattr(main.webbrowser, "open", lambda url: calls.append(url) or True)

    assert main.maybe_open_browser() is False
    assert calls == []


def test_start_url_uses_uncommon_default_port():
    assert main.DEFAULT_BACKEND_PORT == 17654
    assert main.DEFAULT_FRONTEND_DEV_PORT == 17655
    assert main.START_URL == "http://127.0.0.1:17654"


def test_requested_server_port_accepts_env_override(monkeypatch):
    monkeypatch.setenv("PDF_TOOLBOX_PORT", "18123")

    assert main.requested_server_port() == 18123


def test_requested_server_port_rejects_invalid_env(monkeypatch):
    monkeypatch.setenv("PDF_TOOLBOX_PORT", "70000")

    with pytest.raises(ValueError):
        main.requested_server_port()


def test_choose_server_port_avoids_occupied_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((main.DEFAULT_HOST, 0))
        occupied_port = int(sock.getsockname()[1])

        chosen_port = main.choose_server_port(main.DEFAULT_HOST, occupied_port)

    assert chosen_port != occupied_port
    assert 1 <= chosen_port <= 65535
