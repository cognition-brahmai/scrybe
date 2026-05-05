from __future__ import annotations

import tempfile
import pytest
from bs4 import BeautifulSoup

try:
    import fitz
except ModuleNotFoundError:
    fitz = None

from scrybe_api.adapters.liteparse import LiteParseAdapter
from scrybe_api.config import get_settings
from scrybe_api.core.pipeline import ParsePipeline
from scrybe_api.fetchers.base import FetchResult
from scrybe_api.fetchers.dynamic import DynamicFetcher
from scrybe_api.fetchers.static import StaticFetcher
from scrybe_api.llm.openai_enricher import OpenAIEnricher
from scrybe_api.parsers.html import HtmlParser
from scrybe_api.parsers.misc import MiscParser
from scrybe_api.parsers.pdf import PdfParser
from scrybe_api.parsers.router import ParserRouter
from scrybe_api.postprocess.html_cleaner import clean_html
from scrybe_api.schemas.common import ChunkStrategy, ParseRequest
from scrybe_api.storage.cache import FileCache


class StubStaticFetcher(StaticFetcher):
    async def fetch(self, url: str, timeout_seconds: int):
        html = "<html><body><h1>Title</h1><p>One two three four five.</p></body></html>"
        return FetchResult(
            source_url=url,
            final_url=url,
            status_code=200,
            content_type="text/html",
            text=html,
            content=html.encode(),
            headers={},
            fetched_via="static",
        )


class StubDynamicFetcher(DynamicFetcher):
    def __init__(self):
        pass

    @staticmethod
    def is_available() -> bool:
        return True

    async def fetch(self, url: str, timeout_seconds: int):
        html = "<html><body><h1>Browser Title</h1><p>Dynamic text.</p></body></html>"
        return FetchResult(
            source_url=url,
            final_url=url,
            status_code=200,
            content_type="text/html",
            text=html,
            content=html.encode(),
            headers={},
            fetched_via="dynamic",
        )


class StubEnricher(OpenAIEnricher):
    def __init__(self):
        pass

    def is_configured(self) -> bool:
        return False

    async def caption_images(self, images):
        return list(images)

    async def summarize(self, markdown: str):
        return "summary"


@pytest.fixture()
def pipeline():
    settings = get_settings()
    return ParsePipeline(
        settings=settings,
        static_fetcher=StubStaticFetcher(),
        dynamic_fetcher=StubDynamicFetcher(),
        parser_router=ParserRouter(
            html_parser=HtmlParser(),
            pdf_parser=PdfParser(LiteParseAdapter(settings)),
            misc_parser=MiscParser(LiteParseAdapter(settings)),
        ),
        cache=FileCache(settings),
        enricher=StubEnricher(),
    )


@pytest.mark.asyncio
async def test_pipeline_builds_chunks(pipeline):
    request = ParseRequest(
        url="https://example.com/page",
        chunk=True,
        chunk_strategy=ChunkStrategy.paragraph,
        max_chunk_tokens=5,
    )
    document = await pipeline.parse_url(request)
    assert document.content_type == "webpage"
    assert document.chunks


@pytest.mark.asyncio
async def test_pipeline_escalates_to_dynamic_when_low_signal(pipeline):
    request = ParseRequest(url="https://example.com/page", use_browser=True, force_refresh=True)
    document = await pipeline.parse_url(request)
    assert document.metadata.title == "Browser Title"
    assert any("escalated" in warning.lower() for warning in document.warnings)


@pytest.mark.asyncio
async def test_pdf_parser_extracts_text_without_ocr():
    if fitz is None:
        pytest.skip("PyMuPDF is not installed.")
    settings = get_settings()
    parser = PdfParser(LiteParseAdapter(settings))
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello PDF")
    pdf_bytes = doc.tobytes()
    markdown, raw_text, _, _, warnings = await parser.parse(pdf_bytes, "https://example.com/file.pdf")
    assert "Hello PDF" in markdown
    assert not warnings


def test_html_parser_builds_semantic_markdown():
    html = """
    <html>
      <body>
        <nav>Navigation</nav>
        <main>
          <section>
            <p>01 // FOUNDATION MODELS</p>
            <h2>The bodh architectures.</h2>
            <p>Native foundation models structured for deployment.</p>
          </section>
          <section>
            <h3>BODH-B0</h3>
            <p>A highly distilled architecture.</p>
            <a href="/briefing">Request briefing</a>
          </section>
        </main>
      </body>
    </html>
    """
    markdown, raw_text, _, _ = HtmlParser().parse(html, "https://example.com")
    assert "Navigation" not in markdown
    assert "## The bodh architectures." in markdown
    assert "A highly distilled architecture." in markdown
    assert "[Request briefing](https://example.com/briefing)" in markdown


def test_clean_html_handles_tags_with_none_attrs(monkeypatch: pytest.MonkeyPatch):
    soup = BeautifulSoup("<html><body><main><section>hello</section></main></body></html>", "lxml")
    section = soup.find("section")
    assert section is not None
    section.attrs = None

    from scrybe_api.postprocess import html_cleaner

    monkeypatch.setattr(html_cleaner, "BeautifulSoup", lambda html, parser: soup)
    cleaned = clean_html("<html></html>")
    assert cleaned.find("section") is not None
