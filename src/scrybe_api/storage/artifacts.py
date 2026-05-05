from __future__ import annotations

from pathlib import Path

from scrybe_api.config import Settings
from scrybe_api.core.utils import sanitize_filename


class ArtifactStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def write_text(self, subdir: str, name: str, content: str) -> Path:
        path = self.settings.artifacts_dir / subdir / sanitize_filename(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

