from __future__ import annotations

import time
from typing import Any

from scrybe_api.config import Settings
from scrybe_api.core.exceptions import ExternalDependencyUnavailable
from scrybe_api.fetchers.dynamic import DynamicFetcher
from scrybe_api.fetchers.static import StaticFetcher
from scrybe_api.llm.openai_enricher import OpenAIEnricher
from scrybe_api.parsers.router import ParserRouter
from scrybe_api.postprocess.chunking import build_chunks
from scrybe_api.postprocess.metadata import extract_metadata
from scrybe_api.schemas.common import ParseRequest, ParseTimings, ScrybedDocument
from scrybe_api.storage.cache import FileCache


class ParsePipeline:
    def __init__(
        self,
        settings: Settings,
        static_fetcher: StaticFetcher,
        dynamic_fetcher: DynamicFetcher,
        parser_router: ParserRouter,
        cache: FileCache,
        enricher: OpenAIEnricher,
    ) -> None:
        self.settings = settings
        self.static_fetcher = static_fetcher
        self.dynamic_fetcher = dynamic_fetcher
        self.parser_router = parser_router
        self.cache = cache
        self.enricher = enricher

    async def parse_url(self, request: ParseRequest) -> ScrybedDocument:
        cache_key = request.model_dump_json()
        if not request.force_refresh:
            cached = self.cache.get("parse_results", cache_key, self.settings.cache_ttl_seconds)
            if cached:
                return ScrybedDocument.model_validate(cached)

        total_start = time.perf_counter()
        warnings: list[str] = []

        fetch_start = time.perf_counter()
        fetch_result = await self.static_fetcher.fetch(
            str(request.url),
            request.timeout_seconds or self.settings.request_timeout_seconds,
        )
        if self._should_escalate(
            text=fetch_result.text or "",
            content_type=fetch_result.content_type,
            request=request,
        ):
            warnings.append("Static fetch looked low-signal; escalated to browser rendering.")
            try:
                fetch_result = await self.dynamic_fetcher.fetch(
                    str(request.url),
                    request.timeout_seconds or self.settings.request_timeout_seconds,
                )
            except ExternalDependencyUnavailable:
                warnings.append("Browser rendering unavailable; continuing with static fetch output.")
            except Exception as exc:
                warnings.append(
                    "Browser rendering failed; continuing with static fetch output. "
                    f"Reason: {exc}"
                )
        fetch_ms = (time.perf_counter() - fetch_start) * 1000

        parse_start = time.perf_counter()
        markdown, raw_text, soup, images, content_type, parser_warnings = await self.parser_router.parse(fetch_result)
        warnings.extend(fetch_result.warnings)
        warnings.extend(parser_warnings)
        parse_ms = (time.perf_counter() - parse_start) * 1000

        enrich_start = time.perf_counter()
        if request.caption_images:
            images = await self.enricher.caption_images(images)
        summary = await self.enricher.summarize(markdown) if request.summarize else None
        enrich_ms = (time.perf_counter() - enrich_start) * 1000

        metadata = extract_metadata(
            soup=soup if hasattr(soup, "find") else None,
            source_url=fetch_result.final_url,
            content_type=content_type,
            markdown=markdown,
            image_count=len(images),
            settings=self.settings,
        )
        chunks = build_chunks(markdown, request.chunk_strategy, request.max_chunk_tokens) if request.chunk else None
        document = ScrybedDocument(
            source=fetch_result.final_url,
            content_type=content_type,
            markdown=self._format_markdown_document(
                source_url=str(request.url),
                content_markdown=self._inject_image_captions(markdown, images),
                metadata=metadata,
            ),
            raw_text=raw_text,
            metadata=metadata,
            images=images,
            chunks=chunks,
            summary=summary,
            success=True,
            warnings=warnings,
            timings=ParseTimings(
                fetch_ms=round(fetch_ms, 2),
                parse_ms=round(parse_ms, 2),
                enrich_ms=round(enrich_ms, 2),
                total_ms=round((time.perf_counter() - total_start) * 1000, 2),
            ),
        )
        self.cache.set("parse_results", cache_key, document.model_dump(mode="json"))
        return document

    def _should_escalate(self, text: str, content_type: str, request: ParseRequest) -> bool:
        normalized_content_type = (content_type or "").lower()
        is_html_like = any(
            marker in normalized_content_type
            for marker in ("text/html", "application/xhtml+xml")
        )
        if request.use_browser:
            return is_html_like
        if not is_html_like:
            return False
        stripped = " ".join(text.split())
        if len(stripped) >= self.settings.dynamic_threshold_chars:
            return False

        lowered = text.lower()
        shell_markers = (
            "__next",
            "id=\"root\"",
            "id='root'",
            "data-reactroot",
            "ng-version",
            "application/json",
        )
        has_shell_marker = any(marker in lowered for marker in shell_markers)
        visible_signal = any(tag in lowered for tag in ("<article", "<main", "<p", "<h1", "<h2"))
        return has_shell_marker or not visible_signal

    @staticmethod
    def _inject_image_captions(markdown: str, images: list[Any]) -> str:
        if not images:
            return markdown
        lines = [markdown.strip(), "", "## Images", ""]
        for image in images:
            alt = image.caption or image.alt_text or "Image"
            lines.append(f"![{alt}]({image.url})")
        return "\n".join(line for line in lines if line is not None).strip()

    @staticmethod
    def _format_markdown_document(source_url: str, content_markdown: str, metadata) -> str:
        lines = [
            f"Title: {metadata.title or ''}",
            "",
            f"Meta Description: {metadata.description or ''}",
            "",
            f"Author: {metadata.author or ''}",
            "",
            f"Published Date: {metadata.published_date or ''}",
            "",
            f"Content Type: {metadata.content_type or ''}",
            "",
            f"Language: {metadata.language or ''}",
            "",
            f"URL Source: {source_url}",
            "",
            "Markdown Content:",
            content_markdown.strip(),
        ]
        return "\n".join(lines).strip()
