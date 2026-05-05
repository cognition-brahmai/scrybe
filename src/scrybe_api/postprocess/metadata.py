from __future__ import annotations

from math import ceil

from bs4 import BeautifulSoup

try:
    from langdetect import LangDetectException, detect
except ModuleNotFoundError:
    LangDetectException = Exception
    detect = None

from scrybe_api.config import Settings
from scrybe_api.core.utils import utcnow
from scrybe_api.schemas.common import ParseMetadata


def extract_metadata(
    soup: BeautifulSoup | None,
    source_url: str,
    content_type: str,
    markdown: str,
    image_count: int,
    settings: Settings,
) -> ParseMetadata:
    title = None
    description = None
    author = None
    published_date = None

    if soup is not None:
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(" ", strip=True) or None
        description = _meta_content(soup, "description") or _meta_property(soup, "og:description")
        author = _meta_content(soup, "author")
        published_date = _meta_property(soup, "article:published_time") or _meta_content(soup, "pubdate")

    raw_text = markdown.replace("#", " ").replace("|", " ")
    words = [word for word in raw_text.split() if word.strip()]
    language = None
    if words and detect is not None:
        try:
            language = detect(" ".join(words[:500]))
        except LangDetectException:
            language = None

    word_count = len(words)
    reading_time_minutes = round(word_count / 200, 2) if word_count else 0.0

    return ParseMetadata(
        title=title,
        description=description,
        author=author,
        published_date=published_date,
        source_url=source_url,
        content_type=content_type,
        language=language,
        word_count=word_count,
        image_count=image_count,
        reading_time_minutes=reading_time_minutes,
        scrybe_version=settings.version,
        scraped_at=utcnow(),
    )


def _meta_content(soup: BeautifulSoup, name: str) -> str | None:
    tag = soup.find("meta", attrs={"name": name})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def _meta_property(soup: BeautifulSoup, prop: str) -> str | None:
    tag = soup.find("meta", attrs={"property": prop})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None
