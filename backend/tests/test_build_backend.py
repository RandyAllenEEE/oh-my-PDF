from pathlib import Path

from build_backend import copy_runtime_dependencies


def test_copy_runtime_dependencies_places_tools_next_to_exe(tmp_path):
    backend_dir = tmp_path / "backend"
    source = backend_dir / "dependencies"
    (source / "pngquant").mkdir(parents=True)
    (source / "unpaper").mkdir(parents=True)
    (source / "pngquant" / "pngquant.exe").write_text("pngquant", encoding="utf-8")
    (source / "unpaper" / "unpaper.exe").write_text("unpaper", encoding="utf-8")

    dist_dir = tmp_path / "dist_py"
    stale = dist_dir / "dependencies" / "old.txt"
    stale.parent.mkdir(parents=True)
    stale.write_text("stale", encoding="utf-8")

    copied = copy_runtime_dependencies(backend_dir, dist_dir)

    assert copied == dist_dir / "dependencies"
    assert (copied / "pngquant" / "pngquant.exe").read_text(
        encoding="utf-8"
    ) == "pngquant"
    assert (copied / "unpaper" / "unpaper.exe").read_text(encoding="utf-8") == "unpaper"
    assert not stale.exists()


def test_copy_runtime_dependencies_warns_when_missing(tmp_path, capsys):
    copied = copy_runtime_dependencies(tmp_path / "backend", tmp_path / "dist_py")

    assert copied is None
    assert "runtime dependencies not found" in capsys.readouterr().out
