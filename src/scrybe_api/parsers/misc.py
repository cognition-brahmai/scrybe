from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from xml.dom import minidom

from scrybe_api.adapters.liteparse import LiteParseAdapter
from scrybe_api.core.exceptions import ExternalDependencyUnavailable, ParserError
from scrybe_api.schemas.common import ImageRecord

try:
    import feedparser
except ModuleNotFoundError:
    feedparser = None


class MiscParser:
    def __init__(self, liteparse: LiteParseAdapter) -> None:
        self.liteparse = liteparse

    def parse_json(self, content: bytes) -> tuple[str, str, None, list[ImageRecord]]:
        parsed = json.loads(content.decode("utf-8"))
        pretty = json.dumps(parsed, indent=2, ensure_ascii=True)
        fenced = f"```json\n{pretty}\n```"
        return fenced, pretty, None, []

    def parse_xml(self, content: bytes) -> tuple[str, str, None, list[ImageRecord]]:
        raw = content.decode("utf-8", errors="ignore")
        pretty = minidom.parseString(raw.encode("utf-8")).toprettyxml(indent="  ")
        return f"```xml\n{pretty}\n```", pretty, None, []

    def parse_feed(self, content: bytes) -> tuple[str, str, None, list[ImageRecord]]:
        if feedparser is None:
            text = content.decode("utf-8", errors="ignore")
            return text, text, None, []
        feed = feedparser.parse(content)
        lines = []
        for entry in feed.entries:
            lines.append(f"## {entry.get('title', 'Untitled')}")
            if entry.get("link"):
                lines.append(entry["link"])
            if entry.get("summary"):
                lines.append(entry["summary"])
            lines.append("")
        markdown = "\n".join(lines).strip()
        return markdown, markdown, None, []

    def parse_text(self, content: bytes) -> tuple[str, str, None, list[ImageRecord]]:
        text = content.decode("utf-8", errors="ignore")
        return text, text, None, []

    def parse_csv(self, content: bytes) -> tuple[str, str, None, list[ImageRecord]]:
        text = content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return "", "", None, []
        header = rows[0]
        divider = ["---"] * len(header)
        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(divider) + " |",
        ]
        for row in rows[1:]:
            padded = row + [""] * (len(header) - len(row))
            lines.append("| " + " | ".join(padded[: len(header)]) + " |")
        markdown = "\n".join(lines)
        return markdown, text, None, []

    async def parse_office_document(
        self,
        content: bytes,
        suffix: str,
        source_url: str,
    ) -> tuple[str, str, None, list[ImageRecord], list[str]]:
        warnings: list[str] = []
        try:
            parsed = await self.liteparse.parse_bytes(content, suffix=suffix)
        except ExternalDependencyUnavailable:
            warnings.append(f"LiteParse is unavailable for {suffix} parsing.")
            return "", "", None, [], warnings
        except ParserError as exc:
            warnings.append(str(exc))
            return "", "", None, [], warnings

        raw_text = parsed.get("text", "") or parsed.get("content", "") or ""
        markdown = raw_text or f"Unable to extract text from {Path(source_url).name}."
        return markdown, raw_text, None, [], warnings

    def parse_image(self, source_url: str) -> tuple[str, str, None, list[ImageRecord]]:
        image = ImageRecord(url=source_url)
        markdown = f"![Image]({source_url})"
        return markdown, "", None, [image]
