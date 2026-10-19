from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB = Path("runtime/test_synccart.db")
TEST_DB.parent.mkdir(parents=True, exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["APP_ENV"] = "test"
os.environ["ENABLE_RECONCILIATION_WORKER"] = "false"
os.environ["ENABLE_SIMULATOR"] = "true"
os.environ["SIMULATOR_API_KEY"] = "test-simulator-key"
os.environ["STORE_OPS_API_KEY"] = "test-store-key"
os.environ["MONITORING_API_KEY"] = "test-monitor-key"
os.environ["VISION_API_KEY"] = "test-vision-key"
os.environ["SCAN_GRACE_PERIOD_MS"] = "100"
os.environ["NUDGE_TO_REVIEW_MS"] = "500"
os.environ["EVENT_MATCH_WINDOW_MS"] = "5000"
os.environ["MIN_VISION_CONFIDENCE"] = "0.55"

from app.core.config import get_settings  # noqa: E402
get_settings.cache_clear()

from app.db.base import Base  # noqa: E402
from app.db import session as db_session_module  # noqa: E402
from app.main import app  # noqa: E402

engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})
TestSessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
db_session_module.engine = engine
db_session_module.SessionFactory = TestSessionFactory


@pytest.fixture(autouse=True)
def database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
