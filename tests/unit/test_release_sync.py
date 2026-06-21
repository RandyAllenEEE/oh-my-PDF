from __future__ import annotations

from pathlib import Path

from build_all import VERSION, sync_release_artifacts


def test_sync_release_artifacts_preserves_config_and_replaces_old_payload(tmp_path):
    root = tmp_path
    backend_dist = root / "backend" / "dist_py"
    dependencies = backend_dist / "dependencies"
    dependencies.mkdir(parents=True)
    (backend_dist / "pdf-toolbox-server.exe").write_text("new exe", encoding="utf-8")
    (dependencies / "tool.exe").write_text("tool", encoding="utf-8")
    (root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")

    release = root / "release"
    win_unpacked = release / "win-unpacked"
    stale_dir = win_unpacked / "resources"
    stale_dir.mkdir(parents=True)
    (release / "oh-my-PDF 0.1.0.exe").write_text("old installer", encoding="utf-8")
    (release / "builder-debug.yml").write_text("old debug", encoding="utf-8")
    (win_unpacked / "oh-my-PDF.exe").write_text("old electron", encoding="utf-8")
    (win_unpacked / "config.json").write_text("private config", encoding="utf-8")
    (stale_dir / "app.asar").write_text("old app", encoding="utf-8")

    target = sync_release_artifacts(root)

    assert target == win_unpacked
    assert not (release / "oh-my-PDF 0.1.0.exe").exists()
    assert not (release / "builder-debug.yml").exists()
    assert not (win_unpacked / "oh-my-PDF.exe").exists()
    assert not stale_dir.exists()
    assert (win_unpacked / "config.json").read_text(
        encoding="utf-8"
    ) == "private config"
    assert (win_unpacked / "pdf-toolbox-server.exe").read_text(
        encoding="utf-8"
    ) == "new exe"
    assert (win_unpacked / "dependencies" / "tool.exe").read_text(
        encoding="utf-8"
    ) == "tool"
    assert (win_unpacked / "CHANGELOG.md").exists()
    assert VERSION in (release / "VERSION.txt").read_text(encoding="utf-8")
    assert VERSION in (win_unpacked / "VERSION.txt").read_text(encoding="utf-8")
