import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# Ensure `app` package is importable when running tests from repo root
SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    return TestClient(app)
