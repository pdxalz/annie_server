"""Test setup: point the app at a throwaway data directory *before* it is imported."""
import os
import shutil
import tempfile
from pathlib import Path

import pytest

_tmp = tempfile.mkdtemp(prefix="sauviewind-test-")
os.environ["DATA_DIR"] = _tmp
os.environ["ROOSTER_DIR"] = str(Path(_tmp) / "rooster")
os.environ["MQTT_ENABLED"] = "0"
os.environ["COLLECTORS_ENABLED"] = "0"

from app import config, db  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(config.DATABASE) + suffix)
        if p.exists():
            p.unlink()
    if config.STATUS_FILE.exists():
        config.STATUS_FILE.unlink()
    if config.ROOSTER_ARCHIVE_DIR.exists():
        shutil.rmtree(config.ROOSTER_ARCHIVE_DIR)
    if config.ROOSTER_IMAGE.exists():
        config.ROOSTER_IMAGE.unlink()
    db.init_db()
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c
