from __future__ import annotations

from bs4 import BeautifulSoup, Tag


NOISE_TAGS = {"nav", "header", "footer", "aside", "script", "style", "iframe", "noscript", "form"}
NOISE_HINTS = ("cookie", "gdpr", "banner", "advert", "comment", "share", "subscribe", "popup")


def clean_html(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "lxml")
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    for tag in soup.find_all(True):
        if not isinstance(tag, Tag):
            continue
        attrs = " ".join(
            str(value)
            for key, value in tag.attrs.items()
            if key in {"id", "class", "aria-label", "role"}
        ).lower()
        if any(hint in attrs for hint in NOISE_HINTS):
            tag.decompose()
    return soup

