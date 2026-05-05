from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, NavigableString, Tag

from scrybe_api.postprocess.html_cleaner import clean_html
from scrybe_api.schemas.common import ImageRecord


BLOCK_TAGS = {
    "article",
    "blockquote",
    "div",
    "main",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "ul",
}
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
SKIP_TAGS = {"button", "canvas", "figure", "figcaption", "input", "label", "svg", "video", "audio"}


class HtmlParser:
    def parse(self, html: str, base_url: str) -> tuple[str, str, BeautifulSoup, list[ImageRecord]]:
        soup = clean_html(html)
        images = self._extract_images(soup, base_url)
        content_root = self._select_content_root(soup)
        markdown = self._render_markdown(content_root, base_url).strip()
        raw_text = content_root.get_text("\n", strip=True)
        return markdown, raw_text, soup, images

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list[ImageRecord]:
        images: list[ImageRecord] = []
        seen: set[str] = set()
        for image in soup.find_all("img"):
            src = image.get("src")
            if not src:
                continue
            resolved = urljoin(base_url, src)
            if resolved in seen:
                continue
            seen.add(resolved)
            images.append(
                ImageRecord(
                    url=resolved,
                    alt_text=image.get("alt"),
                )
            )
        return images

    def _select_content_root(self, soup: BeautifulSoup) -> Tag:
        preferred = soup.select_one("main") or soup.select_one("article") or soup.find(attrs={"role": "main"})
        if isinstance(preferred, Tag):
            return preferred

        candidates = [tag for tag in soup.find_all(["main", "article", "section", "div", "body"]) if isinstance(tag, Tag)]
        if not candidates and soup.body:
            return soup.body
        best = max(candidates, key=self._content_score, default=soup.body or soup)
        return best if isinstance(best, Tag) else (soup.body or soup)

    def _content_score(self, node: Tag) -> float:
        text = self._normalize_whitespace(node.get_text(" ", strip=True))
        text_len = len(text)
        if text_len == 0:
            return -1.0
        heading_bonus = len(node.find_all(list(HEADING_TAGS))) * 40
        paragraph_bonus = len(node.find_all("p")) * 24
        section_bonus = len(node.find_all(["section", "article"])) * 18
        link_penalty = len(node.find_all("a")) * 5
        button_penalty = len(node.find_all(["button", "input"])) * 30
        return text_len + heading_bonus + paragraph_bonus + section_bonus - link_penalty - button_penalty

    def _render_markdown(self, root: Tag, base_url: str) -> str:
        blocks: list[str] = []
        seen_blocks: set[str] = set()
        for child in root.children:
            self._render_node(child, blocks, base_url, seen_blocks, list_stack=[])
        return self._normalize_blocks(blocks)

    def _render_node(
        self,
        node: NavigableString | Tag,
        blocks: list[str],
        base_url: str,
        seen_blocks: set[str],
        list_stack: list[tuple[str, int]],
    ) -> None:
        if isinstance(node, NavigableString):
            return
        if not isinstance(node, Tag):
            return
        if node.name in SKIP_TAGS:
            return
        if self._is_hidden(node):
            return

        if node.name in HEADING_TAGS:
            text = self._inline_text(node, base_url)
            if text:
                level = int(node.name[1])
                self._append_block(blocks, seen_blocks, f"{'#' * level} {text}")
            return

        if node.name == "p":
            text = self._inline_text(node, base_url)
            if text:
                self._append_block(blocks, seen_blocks, text)
            return

        if node.name in {"ul", "ol"}:
            ordered = node.name == "ol"
            next_stack = list_stack + [(node.name, 1)]
            for child in node.find_all("li", recursive=False):
                self._render_list_item(child, blocks, base_url, seen_blocks, next_stack, ordered)
            return

        if node.name == "blockquote":
            text = self._inline_text(node, base_url)
            if text:
                quoted = "\n".join(f"> {line}" for line in text.splitlines() if line.strip())
                self._append_block(blocks, seen_blocks, quoted)
            return

        if node.name == "pre":
            text = node.get_text("\n", strip=True)
            if text:
                self._append_block(blocks, seen_blocks, f"```\n{text}\n```")
            return

        if node.name == "table":
            table_markdown = self._render_table(node, base_url)
            if table_markdown:
                self._append_block(blocks, seen_blocks, table_markdown)
            return

        if node.name == "a" and not node.find(True):
            text = self._inline_text(node, base_url)
            if text:
                self._append_block(blocks, seen_blocks, text)
            return

        if node.name == "img":
            return

        if self._is_leaf_content(node):
            text = self._inline_text(node, base_url)
            if text and self._looks_meaningful(text):
                self._append_block(blocks, seen_blocks, text)
            return

        for child in node.children:
            self._render_node(child, blocks, base_url, seen_blocks, list_stack=list_stack)

    def _render_list_item(
        self,
        node: Tag,
        blocks: list[str],
        base_url: str,
        seen_blocks: set[str],
        list_stack: list[tuple[str, int]],
        ordered: bool,
    ) -> None:
        depth = max(len(list_stack) - 1, 0)
        prefix = f"{list_stack[-1][1]}." if ordered else "-"
        indent = "  " * depth
        inline_parts: list[str] = []
        nested_lists: list[Tag] = []

        for child in node.children:
            if isinstance(child, Tag) and child.name in {"ul", "ol"}:
                nested_lists.append(child)
                continue
            if isinstance(child, Tag) and child.name in BLOCK_TAGS and child.name not in {"pre"}:
                text = self._inline_text(child, base_url)
            else:
                text = self._inline_text(child, base_url) if isinstance(child, Tag) else self._normalize_whitespace(str(child))
            if text:
                inline_parts.append(text)

        line = self._normalize_whitespace(" ".join(part for part in inline_parts if part))
        if line:
            self._append_block(blocks, seen_blocks, f"{indent}{prefix} {line}", dedupe=False)

        for nested in nested_lists:
            next_stack = list_stack + [(nested.name, 1)]
            for child in nested.find_all("li", recursive=False):
                self._render_list_item(child, blocks, base_url, seen_blocks, next_stack, nested.name == "ol")

    def _render_table(self, table: Tag, base_url: str) -> str:
        rows = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            row = [self._inline_text(cell, base_url) for cell in cells]
            if any(cell for cell in row):
                rows.append(row)
        if not rows:
            return ""
        header = rows[0]
        body = rows[1:]
        divider = ["---"] * len(header)
        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(divider) + " |",
        ]
        for row in body:
            padded = row + [""] * max(0, len(header) - len(row))
            lines.append("| " + " | ".join(padded[: len(header)]) + " |")
        return "\n".join(lines)

    def _inline_text(self, node: NavigableString | Tag, base_url: str) -> str:
        if isinstance(node, NavigableString):
            return self._normalize_whitespace(str(node))
        if node.name == "a":
            href = urljoin(base_url, node.get("href", "")) if node.get("href") else ""
            label = self._normalize_whitespace(node.get_text(" ", strip=True))
            if label and href:
                return f"[{label}]({href})"
            return label
        parts: list[str] = []
        for child in node.children:
            if isinstance(child, NavigableString):
                text = self._normalize_whitespace(str(child))
                if text:
                    parts.append(text)
                continue
            if not isinstance(child, Tag):
                continue
            if self._is_hidden(child) or child.name in SKIP_TAGS or child.name == "img":
                continue
            if child.name == "br":
                parts.append("\n")
                continue
            if child.name == "a":
                href = urljoin(base_url, child.get("href", "")) if child.get("href") else ""
                label = self._normalize_whitespace(child.get_text(" ", strip=True))
                if label and href:
                    parts.append(f"[{label}]({href})")
                elif label:
                    parts.append(label)
                continue
            if child.name == "code":
                code = child.get_text(" ", strip=True)
                if code:
                    parts.append(f"`{code}`")
                continue
            nested = self._inline_text(child, base_url)
            if nested:
                parts.append(nested)

        if not parts:
            return self._normalize_whitespace(node.get_text(" ", strip=True))

        joined = " ".join(parts)
        joined = joined.replace(" \n ", "\n").replace(" \n", "\n").replace("\n ", "\n")
        return self._normalize_whitespace(joined, preserve_newlines=True)

    def _append_block(self, blocks: list[str], seen_blocks: set[str], text: str, dedupe: bool = True) -> None:
        normalized = self._normalize_whitespace(text, preserve_newlines=True).strip()
        if not normalized:
            return
        dedupe_key = re.sub(r"\s+", " ", normalized).strip().lower()
        if dedupe and dedupe_key in seen_blocks:
            return
        if dedupe:
            seen_blocks.add(dedupe_key)
        blocks.append(normalized)

    def _is_leaf_content(self, node: Tag) -> bool:
        meaningful_children = [
            child
            for child in node.children
            if isinstance(child, Tag) and not self._is_hidden(child) and child.name not in SKIP_TAGS
        ]
        if not meaningful_children:
            return True
        return all(child.name not in BLOCK_TAGS and child.name not in HEADING_TAGS for child in meaningful_children)

    def _looks_meaningful(self, text: str) -> bool:
        compact = self._normalize_whitespace(text)
        if len(compact) < 2:
            return False
        return True

    def _normalize_blocks(self, blocks: list[str]) -> str:
        merged: list[str] = []
        previous = ""
        for block in blocks:
            if not block:
                continue
            if block == previous:
                continue
            merged.append(block)
            previous = block
        return "\n\n".join(merged).strip()

    @staticmethod
    def _normalize_whitespace(value: str, preserve_newlines: bool = False) -> str:
        value = value.replace("\xa0", " ")
        if preserve_newlines:
            parts = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in value.splitlines()]
            return "\n".join(line for line in parts if line)
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _is_hidden(node: Tag) -> bool:
        if node.get("hidden") is not None:
            return True
        if node.get("aria-hidden") == "true":
            return True
        style = (node.get("style") or "").lower().replace(" ", "")
        return "display:none" in style or "visibility:hidden" in style
