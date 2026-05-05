from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class OutputFormat(StrEnum):
    markdown = "markdown"
    json = "json"


class JobStatus(StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    partial = "partial"


class ChunkStrategy(StrEnum):
    fixed = "fixed"
    semantic = "semantic"
    paragraph = "paragraph"


class ImageRecord(BaseModel):
    url: str
    alt_text: str | None = None
    caption: str | None = None


class ParseMetadata(BaseModel):
    title: str | None = None
    description: str | None = None
    author: str | None = None
    published_date: str | None = None
    source_url: str
    content_type: str
    language: str | None = None
    word_count: int = 0
    image_count: int = 0
    reading_time_minutes: float = 0.0
    scrybe_version: str
    scraped_at: datetime


class ParseTimings(BaseModel):
    fetch_ms: float = 0
    parse_ms: float = 0
    enrich_ms: float = 0
    total_ms: float = 0


class ParseRequest(BaseModel):
    url: HttpUrl
    use_browser: bool = False
    chunk: bool = False
    chunk_strategy: ChunkStrategy = ChunkStrategy.semantic
    max_chunk_tokens: int = 512
    summarize: bool = False
    caption_images: bool = False
    timeout_seconds: int | None = None
    force_refresh: bool = False


class ScrybedDocument(BaseModel):
    source: str
    content_type: str
    markdown: str
    raw_text: str
    metadata: ParseMetadata
    images: list[ImageRecord] = Field(default_factory=list)
    chunks: list[str] | None = None
    summary: str | None = None
    success: bool = True
    warnings: list[str] = Field(default_factory=list)
    timings: ParseTimings = Field(default_factory=ParseTimings)
    extra: dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    status_url: str
    result_url: str | None = None
    created_at: datetime
    updated_at: datetime

