from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
LOCAL = ROOT / "tests" / "local"
RESULTS = ROOT / "tests" / "results"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-external",
        action="store_true",
        default=False,
        help="Run tests that call configured external services.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    run_external = (
        config.getoption("--run-external")
        or os.environ.get("OH_MY_PDF_RUN_EXTERNAL") == "1"
    )
    if run_external:
        return

    skip_external = pytest.mark.skip(
        reason="external tests require --run-external or OH_MY_PDF_RUN_EXTERNAL=1"
    )
    for item in items:
        if "external" in item.keywords:
            item.add_marker(skip_external)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def results_dir() -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    return RESULTS


@pytest.fixture(scope="session")
def runtime_config_path() -> Path:
    LOCAL.mkdir(parents=True, exist_ok=True)
    explicit = os.environ.get("OH_MY_PDF_TEST_CONFIG")
    candidates = [
        Path(explicit) if explicit else None,
        ROOT / "tests" / "local" / "config.runtime.json",
        ROOT / "release" / "win-unpacked" / "config.json",
        BACKEND / "config.json",
    ]

    for candidate in candidates:
        if candidate and candidate.exists():
            target = LOCAL / "config.runtime.json"
            if candidate.resolve() != target.resolve():
                shutil.copy2(candidate, target)
            return target

    pytest.skip("No config.json available for runtime-config tests")


@pytest.fixture(scope="session")
def runtime_config(runtime_config_path: Path) -> dict[str, Any]:
    return json.loads(runtime_config_path.read_text(encoding="utf-8"))


@pytest.fixture()
def private_fixtures_dir() -> Path:
    path = LOCAL / "fixtures"
    path.mkdir(parents=True, exist_ok=True)
    return path


def has_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def redact(value: Any) -> str:
    text = "" if value is None else str(value)
    if not text:
        return "<empty>"
    if len(text) <= 4:
        return "*" * len(text)
    return f"{'*' * min(8, len(text) - 4)}{text[-4:]}"
