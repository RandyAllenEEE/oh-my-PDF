from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
LOCAL = ROOT / "tests" / "local"
RESULTS = ROOT / "tests" / "results"


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"\n$ {' '.join(command)}  (cwd={cwd})")
    subprocess.run(command, cwd=cwd, env=env, check=True)


def exe(name: str) -> str:
    return shutil.which(name) or shutil.which(f"{name}.cmd") or name


def prepare_local_config() -> Path | None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    explicit = os.environ.get("OH_MY_PDF_TEST_CONFIG")
    candidates = [
        Path(explicit) if explicit else None,
        ROOT / "release" / "win-unpacked" / "config.json",
        BACKEND / "config.json",
    ]

    for candidate in candidates:
        if candidate and candidate.exists():
            target = LOCAL / "config.runtime.json"
            shutil.copy2(candidate, target)
            print(f"Prepared runtime config: {target}")
            return target

    print("No runtime config found; tests that need it will skip.")
    return None


def pytest_command(marker: str) -> list[str]:
    return [
        exe("poetry"),
        "run",
        "pytest",
        str(ROOT / "tests"),
        str(BACKEND / "tests"),
        "-m",
        marker,
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="oh-my-PDF test runner")
    parser.add_argument(
        "suite",
        choices=["quick", "local", "external", "all"],
        help="Test suite to run",
    )
    args = parser.parse_args()

    prepare_local_config()

    env = os.environ.copy()
    env.setdefault("OH_MY_PDF_OLLAMA_TIMEOUT_SEC", "900")
    env.setdefault("OH_MY_PDF_LLM_TIMEOUT_SEC", "900")
    env.setdefault("OH_MY_PDF_MINERU_POLL_TIMEOUT_SEC", "1200")

    if args.suite == "quick":
        run(
            pytest_command("not external and not local_ocr and not packaging"),
            BACKEND,
            env,
        )
        run([exe("npm"), "test"], FRONTEND, env)
        return 0

    if args.suite == "local":
        run(pytest_command("not external and not packaging"), BACKEND, env)
        run([exe("npm"), "test"], FRONTEND, env)
        return 0

    if args.suite == "external":
        env["OH_MY_PDF_RUN_EXTERNAL"] = "1"
        run(pytest_command("external"), BACKEND, env)
        return 0

    env["OH_MY_PDF_RUN_EXTERNAL"] = "1"
    run(pytest_command("not packaging"), BACKEND, env)
    run([exe("npm"), "test"], FRONTEND, env)
    run([exe("npm"), "run", "build"], FRONTEND, env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
