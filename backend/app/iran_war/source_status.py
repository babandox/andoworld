from __future__ import annotations

import socket
from urllib.parse import urlparse

from backend.app.iran_war.config import database_url, is_configured, load_env_file, qdrant_url
from backend.app.models import SourceHealth, SourceStatus


def build_source_status() -> SourceStatus:
    load_env_file()
    return SourceStatus(
        wikipedia=SourceHealth(configured=True, available=True, note="Public Wikipedia APIs require no local secret."),
        gdelt=SourceHealth(configured=True, available=True, note="Public GDELT access is treated as configured."),
        polymarket=SourceHealth(configured=True, available=True, note="Public Polymarket Gamma reads are treated as configured."),
        fred=SourceHealth(configured=is_configured("FRED_API_KEY"), available=is_configured("FRED_API_KEY"), note="FRED key loaded from environment when present."),
        openai=SourceHealth(configured=is_configured("OPENAI_API_KEY"), available=is_configured("OPENAI_API_KEY"), note="OpenAI key loaded from environment when present."),
        postgres=_service_status("DATABASE_URL", "Postgres"),
        qdrant=_service_status("QDRANT_URL", "Qdrant"),
    )


def _service_status(env_name: str, label: str) -> SourceHealth:
    configured = is_configured(env_name)
    url = database_url() if env_name == "DATABASE_URL" else qdrant_url()
    available = _can_connect_url(url)
    if configured:
        return SourceHealth(configured=True, available=available, note=f"{label} URL is configured.")
    note = f"{label} URL is not configured; trying the local development default."
    return SourceHealth(configured=False, available=available, note=note if available else f"{note} No local service was reachable.")


def _can_connect(env_name: str) -> bool:
    from os import getenv

    return _can_connect_url(getenv(env_name, ""))


def _can_connect_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port
    if not host or not port:
        return False
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False
