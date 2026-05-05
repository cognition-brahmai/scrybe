from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from scrybe_api.schemas.common import JobStatus, OutputFormat, ParseRequest, ScrybedDocument


class ParseEnvelope(BaseModel):
    format: OutputFormat
    document: ScrybedDocument


class MarkdownEnvelope(BaseModel):
    format: OutputFormat = OutputFormat.markdown
    source: str
    content_type: str
    title: str | None
    markdown: str
    warnings: list[str]
    timings: dict[str, float]


class JobSubmitRequest(ParseRequest):
    output_format: OutputFormat = OutputFormat.json


class JobRecordResponse(BaseModel):
    job_id: str
    status: JobStatus
    output_format: OutputFormat
    request: dict[str, Any]
    result: ScrybedDocument | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime

