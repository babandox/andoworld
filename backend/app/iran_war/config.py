from __future__ import annotations

from pathlib import Path
import os


DEFAULT_LOCAL_DATABASE_URL = "postgresql://andoworld:andoworld@127.0.0.1:5432/andoworld"
DEFAULT_LOCAL_QDRANT_URL = "http://127.0.0.1:6333"


def load_env_file(path: Path | None = None) -> None:
    env_path = path or Path.cwd() / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def is_configured(name: str) -> bool:
    return bool(os.getenv(name))


def database_url() -> str:
    load_env_file()
    return os.getenv("DATABASE_URL") or DEFAULT_LOCAL_DATABASE_URL


def qdrant_url() -> str:
    load_env_file()
    return os.getenv("QDRANT_URL") or DEFAULT_LOCAL_QDRANT_URL
