import os
import subprocess
import shutil
from pathlib import Path


VERSION = "0.2.0"


def run_command(command, cwd=None):
    print(f"Running: {command} in {cwd or os.getcwd()}")
    result = subprocess.run(command, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Command failed with return code {result.returncode}")
        exit(result.returncode)


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def clean_release_root(release_dir: Path) -> None:
    for child in release_dir.iterdir():
        if child.name == "win-unpacked":
            continue
        if child.name.lower() == "config.json":
            continue
        if child.is_file() or child.is_symlink():
            remove_path(child)


def clean_release_payload(target_dir: Path) -> None:
    for child in target_dir.iterdir():
        if child.name.lower() == "config.json":
            continue
        remove_path(child)


def sync_release_artifacts(root_dir: Path) -> Path:
    backend_dist = root_dir / "backend" / "dist_py"
    source_exe = backend_dist / "pdf-toolbox-server.exe"
    source_dependencies = backend_dist / "dependencies"
    changelog = root_dir / "CHANGELOG.md"

    if not source_exe.exists():
        raise FileNotFoundError(f"Backend executable not found: {source_exe}")
    if not source_dependencies.exists():
        raise FileNotFoundError(
            f"Runtime dependencies not found: {source_dependencies}"
        )

    release_dir = root_dir / "release"
    target_dir = release_dir / "win-unpacked"
    release_dir.mkdir(parents=True, exist_ok=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    clean_release_root(release_dir)
    clean_release_payload(target_dir)

    shutil.copy2(source_exe, target_dir / source_exe.name)
    shutil.copytree(source_dependencies, target_dir / "dependencies")
    if changelog.exists():
        shutil.copy2(changelog, target_dir / "CHANGELOG.md")

    version_text = (
        f"oh-my-PDF {VERSION}\n"
        "Run pdf-toolbox-server.exe and the local web UI will open automatically.\n"
    )
    (release_dir / "VERSION.txt").write_text(version_text, encoding="utf-8")
    (target_dir / "VERSION.txt").write_text(version_text, encoding="utf-8")

    return target_dir


def build():
    root_dir = Path(__file__).parent
    backend_dir = root_dir / "backend"
    frontend_dir = root_dir / "frontend"
    release_dir = root_dir / "release"

    if not release_dir.exists():
        release_dir.mkdir()

    # 1. Build Frontend static assets
    print("--- Step 1: Building Frontend ---")
    run_command("npm run build", cwd=str(frontend_dir))

    # 2. Build Backend and bundle frontend/dist
    print("\n--- Step 2: Building Backend ---")
    run_command("poetry run python build_backend.py", cwd=str(backend_dir))

    # 3. Sync release directory while preserving local config.json
    print("\n--- Step 3: Syncing Release Artifacts ---")
    release_target = sync_release_artifacts(root_dir)

    print("\n--- Build All Completed ---")
    print(f"Check '{backend_dir / 'dist_py'}' for the standalone server.")
    print(f"Release v{VERSION} is available at '{release_target}'.")


if __name__ == "__main__":
    build()
