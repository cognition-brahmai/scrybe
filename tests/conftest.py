from __future__ import annotations

from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scrybe_api.api.app import create_app
from scrybe_api.config import get_settings


@pytest.fixture(autouse=True)
def _reset_settings_cache(monkeypatch: pytest.MonkeyPatch):
    runtime_root = ROOT / "tests_runtime"
    monkeypatch.setenv("SCRYBE_DATA_DIR", str(runtime_root / "data"))
    monkeypatch.setenv("SCRYBE_SQLITE_PATH", ":memory:")
    monkeypatch.setenv("SCRYBE_ARTIFACTS_DIR", str(runtime_root / "artifacts"))
    monkeypatch.setenv("SCRYBE_CACHE_DIR", str(runtime_root / "cache"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
