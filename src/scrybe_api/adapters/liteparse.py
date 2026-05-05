from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from anyio import run_process

from scrybe_api.config import Settings
from scrybe_api.core.exceptions import ExternalDependencyUnavailable, ParserError


class LiteParseAdapter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_available(self) -> bool:
        return shutil.which(self.settings.liteparse_cmd) is not None

    async def parse_file(self, file_path: Path) -> dict:
        if not self.is_available():
            raise ExternalDependencyUnavailable(
                f"LiteParse CLI '{self.settings.liteparse_cmd}' is not available."
            )

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_output:
            output_path = Path(temp_output.name)

        try:
            result = await run_process(
                [
                    self.settings.liteparse_cmd,
                    "parse",
                    str(file_path),
                    "--format",
                    "json",
                    "-o",
                    str(output_path),
                    "-q",
                ],
                stderr=-1,
                stdout=-1,
                check=False,
            )
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="ignore").strip()
                raise ParserError(f"LiteParse failed: {stderr or 'unknown error'}")
            return json.loads(output_path.read_text(encoding="utf-8"))
        finally:
            output_path.unlink(missing_ok=True)

    async def parse_bytes(self, payload: bytes, suffix: str) -> dict:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(payload)
        try:
            return await self.parse_file(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)
