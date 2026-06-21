import PyInstaller.__main__
import os
import shutil
from pathlib import Path


def on_rm_error(func, path, exc_info):
    import stat

    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_tree(path: Path, label: str) -> None:
    if not path.exists():
        return
    try:
        shutil.rmtree(path, onerror=on_rm_error)
    except Exception:
        print(f"Warning: Could not fully clean {label} at {path}, proceeding anyway...")


def copy_runtime_dependencies(backend_dir: Path, dist_dir: Path) -> Path | None:
    source = backend_dir / "dependencies"
    target = dist_dir / "dependencies"

    if not source.exists():
        print(
            f"Warning: runtime dependencies not found at {source}; "
            "pngquant/unpaper will need to be installed on PATH."
        )
        return None

    dist_dir.mkdir(parents=True, exist_ok=True)
    remove_tree(target, "runtime dependencies")
    shutil.copytree(source, target)
    print(f"Copied runtime dependencies to: {target}")
    return target


def build():
    backend_dir = Path(__file__).parent
    root_dir = backend_dir.parent
    frontend_dist = root_dir / "frontend" / "dist"
    dist_dir = backend_dir / "dist_py"
    build_dir = backend_dir / "build_py"
    spec_path = backend_dir / "pdf-toolbox-server.spec"

    # Clean up previous builds
    remove_tree(dist_dir, "dist directory")
    remove_tree(build_dir, "build directory")
    if spec_path.exists():
        spec_path.unlink()

    print("Building Backend with PyInstaller...")

    args = [
        "src/main.py",
        "--name=pdf-toolbox-server",
        "--onefile",
        "--clean",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        # Add ocrmypdf data files
        "--collect-data=ocrmypdf",
        # Hidden imports for FastAPI and Uvicorn
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=src.plugins.bridge",
        "--hidden-import=src.plugins.paddle",
        "--hidden-import=src.plugins.deepseek",
        "--hidden-import=src.plugins.mineru",
        # Add src as a data path or ensure it's in path
        "--paths=src",
    ]

    if frontend_dist.exists():
        sep = ";" if os.name == "nt" else ":"
        args.append(f"--add-data={frontend_dist}{sep}frontend/dist")
    else:
        print(
            f"Warning: frontend dist not found at {frontend_dist}; server will expose API only."
        )

    PyInstaller.__main__.run(args)
    copy_runtime_dependencies(backend_dir, dist_dir)
    remove_tree(build_dir, "build directory")
    if spec_path.exists():
        spec_path.unlink()

    print(f"Backend build completed. Executable at: {dist_dir}/pdf-toolbox-server.exe")


if __name__ == "__main__":
    build()
