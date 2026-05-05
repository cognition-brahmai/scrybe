from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class FetchResult:
    source_url: str
    final_url: str
    status_code: int
    content_type: str
    text: str | None
    content: bytes
    headers: dict[str, str]
    fetched_via: str
    warnings: list[str] = field(default_factory=list)

