from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from scrybe_api.core.utils import utcnow
from scrybe_api.schemas.api import JobRecordResponse, JobSubmitRequest
from scrybe_api.schemas.common import JobStatus, OutputFormat
from scrybe_api.storage.repository import JobRepository


class JobManager:
    def __init__(self, repository: JobRepository, pipeline) -> None:
        self.repository = repository
        self.pipeline = pipeline
        self._tasks: dict[str, asyncio.Task] = {}

    async def submit(self, request: JobSubmitRequest) -> JobRecordResponse:
        now = utcnow()
        job_id = str(uuid.uuid4())
        record = JobRecordResponse(
            job_id=job_id,
            status=JobStatus.queued,
            output_format=request.output_format,
            request=request.model_dump(mode="json"),
            created_at=now,
            updated_at=now,
        )
        await self.repository.create(record)
        self._tasks[job_id] = asyncio.create_task(self._run_job(job_id, request))
        return record

    async def _run_job(self, job_id: str, request: JobSubmitRequest) -> None:
        await self.repository.update(
            job_id,
            status=JobStatus.running,
            updated_at=utcnow().isoformat(),
        )
        try:
            document = await self.pipeline.parse_url(request)
            status = JobStatus.succeeded if document.success else JobStatus.partial
            await self.repository.update(
                job_id,
                status=status,
                updated_at=utcnow().isoformat(),
                result=document,
            )
        except Exception as exc:
            await self.repository.update(
                job_id,
                status=JobStatus.failed,
                updated_at=utcnow().isoformat(),
                error=str(exc),
            )
        finally:
            self._tasks.pop(job_id, None)

    async def get(self, job_id: str) -> JobRecordResponse | None:
        return await self.repository.get(job_id)

