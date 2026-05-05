from __future__ import annotations

from scrybe_api.fetchers.base import FetchResult
from scrybe_api.schemas.common import ParseRequest, ScrybedDocument


class DummyStaticFetcher:
    async def fetch(self, url: str, timeout_seconds: int):
        html = """
        <html>
          <head>
            <title>Example Article</title>
            <meta name="description" content="Short summary" />
          </head>
          <body>
            <main>
              <h1>Example Article</h1>
              <p>Hello world from SCRYBE.</p>
              <img src="/cover.png" alt="Cover" />
            </main>
          </body>
        </html>
        """
        return FetchResult(
            source_url=url,
            final_url=url,
            status_code=200,
            content_type="text/html",
            text=html,
            content=html.encode("utf-8"),
            headers={},
            fetched_via="static",
        )


class DummyUnicodeTitleFetcher:
    async def fetch(self, url: str, timeout_seconds: int):
        html = """
        <html>
          <head>
            <title>Brahmai – Example</title>
          </head>
          <body>
            <main>
              <h1>Brahmai – Example</h1>
              <p>Unicode title content.</p>
            </main>
          </body>
        </html>
        """
        return FetchResult(
            source_url=url,
            final_url=url,
            status_code=200,
            content_type="text/html",
            text=html,
            content=html.encode("utf-8"),
            headers={},
            fetched_via="static",
        )


class DummyDynamicFetcher:
    @staticmethod
    def is_available() -> bool:
        return True

    async def fetch(self, url: str, timeout_seconds: int):
        html = "<html><body><h1>Dynamic</h1><p>Loaded in browser.</p></body></html>"
        return FetchResult(
            source_url=url,
            final_url=url,
            status_code=200,
            content_type="text/html",
            text=html,
            content=html.encode("utf-8"),
            headers={},
            fetched_via="dynamic",
        )


def test_health(client):
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "URLs in. Structured context out." in response.text
    assert "/assets/styles.css" in response.text
    assert "/assets/app.js" in response.text


def test_parse_json(client):
    client.app.state.pipeline.static_fetcher = DummyStaticFetcher()
    client.app.state.pipeline.dynamic_fetcher = DummyDynamicFetcher()
    response = client.get(
        "/v1/parse/json",
        params={"url": "https://example.com/article", "force_refresh": "true"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["format"] == "json"
    assert payload["document"]["metadata"]["title"] == "Example Article"
    assert payload["document"]["markdown"].startswith("Title: Example Article")
    assert "Meta Description: Short summary" in payload["document"]["markdown"]
    assert "URL Source: https://example.com/article" in payload["document"]["markdown"]
    assert "Markdown Content:" in payload["document"]["markdown"]
    assert "Hello world" in payload["document"]["markdown"]


def test_parse_markdown_headers(client):
    client.app.state.pipeline.static_fetcher = DummyStaticFetcher()
    client.app.state.pipeline.dynamic_fetcher = DummyDynamicFetcher()
    response = client.get(
        "/v1/parse/markdown",
        params={"url": "https://example.com/article", "force_refresh": "true"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["x-scrybe-title"] == "Example Article"
    assert response.text.startswith("Title: Example Article")
    assert "Meta Description: Short summary" in response.text
    assert "URL Source: https://example.com/article" in response.text
    assert "Markdown Content:" in response.text
    assert "Example Article" in response.text


def test_redirect_heavy_requests_to_job(client):
    response = client.get(
        "/v1/parse/json",
        params={"url": "https://example.com/report.pdf"},
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["status_url"].startswith("/v1/jobs/")


def test_markdown_response_handles_unicode_header_values(client):
    client.app.state.pipeline.static_fetcher = DummyUnicodeTitleFetcher()
    client.app.state.pipeline.dynamic_fetcher = DummyDynamicFetcher()
    response = client.get(
        "/v1/parse/markdown",
        params={"url": "https://brahmai.in", "force_refresh": "true"},
    )
    assert response.status_code == 200
    assert response.headers["x-scrybe-title"] == "Brahmai ? Example"
    assert "Brahmai" in response.text
