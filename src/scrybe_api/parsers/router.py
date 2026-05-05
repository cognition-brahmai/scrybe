from __future__ import annotations

from urllib.parse import urlparse

from scrybe_api.fetchers.base import FetchResult
from scrybe_api.parsers.html import HtmlParser
from scrybe_api.parsers.misc import MiscParser
from scrybe_api.parsers.pdf import PdfParser
from scrybe_api.schemas.common import ImageRecord


class ParserRouter:
    def __init__(self, html_parser: HtmlParser, pdf_parser: PdfParser, misc_parser: MiscParser) -> None:
        self.html_parser = html_parser
        self.pdf_parser = pdf_parser
        self.misc_parser = misc_parser

    async def parse(
        self,
        fetch_result: FetchResult,
    ) -> tuple[str, str, object | None, list[ImageRecord], str, list[str]]:
        content_type = fetch_result.content_type.lower()
        path = urlparse(fetch_result.final_url).path.lower()

        if "html" in content_type:
            markdown, raw_text, soup, images = self.html_parser.parse(
                fetch_result.text or fetch_result.content.decode("utf-8", errors="ignore"),
                fetch_result.final_url,
            )
            return markdown, raw_text, soup, images, "webpage", []

        if "pdf" in content_type or path.endswith(".pdf"):
            markdown, raw_text, soup, images, warnings = await self.pdf_parser.parse(
                fetch_result.content,
                fetch_result.final_url,
            )
            return markdown, raw_text, soup, images, "pdf", warnings

        if "json" in content_type or path.endswith(".json"):
            markdown, raw_text, soup, images = self.misc_parser.parse_json(fetch_result.content)
            return markdown, raw_text, soup, images, "json", []

        if "xml" in content_type or path.endswith(".xml"):
            markdown, raw_text, soup, images = self.misc_parser.parse_xml(fetch_result.content)
            return markdown, raw_text, soup, images, "xml", []

        if "rss" in content_type or "atom" in content_type or path.endswith(".rss"):
            markdown, raw_text, soup, images = self.misc_parser.parse_feed(fetch_result.content)
            return markdown, raw_text, soup, images, "rss", []

        if "csv" in content_type or path.endswith(".csv") or path.endswith(".tsv"):
            markdown, raw_text, soup, images = self.misc_parser.parse_csv(fetch_result.content)
            return markdown, raw_text, soup, images, "spreadsheet", []

        if any(path.endswith(ext) for ext in (".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".odt", ".ods")):
            markdown, raw_text, soup, images, warnings = await self.misc_parser.parse_office_document(
                fetch_result.content,
                suffix=path[path.rfind("."):],
                source_url=fetch_result.final_url,
            )
            return markdown, raw_text, soup, images, "office_document", warnings

        if any(path.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".svg")) or content_type.startswith("image/"):
            markdown, raw_text, soup, images = self.misc_parser.parse_image(fetch_result.final_url)
            return markdown, raw_text, soup, images, "image", []

        markdown, raw_text, soup, images = self.misc_parser.parse_text(fetch_result.content)
        return markdown, raw_text, soup, images, "text", []
