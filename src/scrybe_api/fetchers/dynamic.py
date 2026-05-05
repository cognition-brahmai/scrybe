from __future__ import annotations

from importlib.util import find_spec

from scrybe_api.config import Settings
from scrybe_api.core.exceptions import ExternalDependencyUnavailable
from scrybe_api.fetchers.base import FetchResult


class DynamicFetcher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @staticmethod
    def is_available() -> bool:
        return find_spec("playwright") is not None

    async def fetch(self, url: str, timeout_seconds: int) -> FetchResult:
        if not self.is_available():
            raise ExternalDependencyUnavailable("Playwright is not installed.")

        from playwright.async_api import async_playwright

        async with async_playwright() as playwright:
            browser_factory = getattr(playwright, self.settings.playwright_browser)
            browser = await browser_factory.launch()
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=timeout_seconds * 1000)
            content = await page.content()
            final_url = page.url
            await browser.close()

        return FetchResult(
            source_url=url,
            final_url=final_url,
            status_code=200,
            content_type="text/html; charset=utf-8",
            text=content,
            content=content.encode("utf-8"),
            headers={},
            fetched_via="dynamic",
        )

