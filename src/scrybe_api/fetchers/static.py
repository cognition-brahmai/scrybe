from __future__ import annotations

import httpx

from scrybe_api.fetchers.base import FetchResult


class StaticFetcher:
    async def fetch(self, url: str, timeout_seconds: int) -> FetchResult:
        timeout = httpx.Timeout(timeout_seconds)
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": "SCRYBE/0.1 (+https://example.invalid)"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
        return FetchResult(
            source_url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=response.headers.get("content-type", "application/octet-stream"),
            text=response.text if "text" in response.headers.get("content-type", "") or "html" in response.headers.get("content-type", "") or "json" in response.headers.get("content-type", "") or "xml" in response.headers.get("content-type", "") else None,
            content=response.content,
            headers=dict(response.headers),
            fetched_via="static",
        )

