from __future__ import annotations

import tempfile
from pathlib import Path

from scrybe_api.adapters.liteparse import LiteParseAdapter
from scrybe_api.core.exceptions import ExternalDependencyUnavailable
from scrybe_api.schemas.common import ImageRecord

try:
    import fitz
except ModuleNotFoundError:
    fitz = None


class PdfParser:
    def __init__(self, liteparse: LiteParseAdapter) -> None:
        self.liteparse = liteparse

    async def parse(
        self,
        content: bytes,
        source_url: str,
        use_ocr_fallback: bool = True,
    ) -> tuple[str, str, None, list[ImageRecord], list[str]]:
        warnings: list[str] = []
        text = ""
        if fitz is not None:
            with fitz.open(stream=content, filetype="pdf") as document:
                pages = [page.get_text("text") for page in document]
                text = "\n\n".join(page.strip() for page in pages if page.strip()).strip()

        if text:
            markdown = text
            return markdown, text, None, [], warnings

        if not use_ocr_fallback:
            warnings.append("Native PDF extraction produced no text and OCR fallback is disabled.")
            return "", "", None, [], warnings

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(content)

        try:
            parsed = await self.liteparse.parse_file(temp_path)
        except ExternalDependencyUnavailable:
            warnings.append("Native PDF extraction produced no text and LiteParse is unavailable.")
            return "", "", None, [], warnings
        finally:
            temp_path.unlink(missing_ok=True)

        raw_text = parsed.get("text", "") or parsed.get("content", "") or ""
        warnings.append("Native PDF extraction produced no text; OCR fallback used.")
        return raw_text, raw_text, None, [], warnings
