import os

import pytest


@pytest.fixture(autouse=True)
def disable_live_ingestion_by_default(monkeypatch):
    monkeypatch.setenv("IRAN_WAR_DISABLE_LIVE", "1")
    monkeypatch.setenv("IRAN_WAR_DISABLE_OPENAI_EXTRACTION", "1")
    yield
    os.environ.pop("IRAN_WAR_DISABLE_LIVE", None)
    os.environ.pop("IRAN_WAR_DISABLE_OPENAI_EXTRACTION", None)
