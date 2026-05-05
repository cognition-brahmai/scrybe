from __future__ import annotations

import json
from pathlib import Path

from scrybe_api.config import Settings
from scrybe_api.core.utils import sha256_text, utcnow


class FileCache:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _path(self, namespace: str, key: str) -> Path:
        hashed = sha256_text(key)
        return self.settings.cache_dir / namespace / f"{hashed}.json"

    def get(self, namespace: str, key: str, ttl_seconds: int) -> dict | None:
        path = self._path(namespace, key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if (utcnow().timestamp() - payload["created_at"]) > ttl_seconds:
                path.unlink(missing_ok=True)
                return None
            return payload["value"]
        except OSError:
            return None

    def set(self, namespace: str, key: str, value: dict) -> None:
        path = self._path(namespace, key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "created_at": utcnow().timestamp(),
                "value": value,
            }
            path.write_text(json.dumps(payload, ensure_ascii=True, default=str), encoding="utf-8")
        except OSError:
            return
