from __future__ import annotations

import json

from scrybe_api.schemas.api import JobRecordResponse
from scrybe_api.schemas.common import JobStatus, OutputFormat, ScrybedDocument
from scrybe_api.storage.db import Database


class JobRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def create(self, response: JobRecordResponse) -> None:
        await self.db.create_job(
            job_id=response.job_id,
            status=response.status,
            output_format=response.output_format,
            request_json=response.request,
            created_at=response.created_at.isoformat(),
            updated_at=response.updated_at.isoformat(),
        )

    async def update(
        self,
        job_id: str,
        *,
        status: JobStatus,
        updated_at: str,
        result: ScrybedDocument | None = None,
        error: str | None = None,
    ) -> None:
        await self.db.update_job(
            job_id,
            status=status,
            updated_at=updated_at,
            result=result,
            error=error,
        )

    async def get(self, job_id: str) -> JobRecordResponse | None:
        row = await self.db.get_job(job_id)
        if row is None:
            return None
        result = ScrybedDocument.model_validate_json(row["result_json"]) if row["result_json"] else None
        return JobRecordResponse(
            job_id=row["job_id"],
            status=JobStatus(row["status"]),
            output_format=OutputFormat(row["output_format"]),
            request=json.loads(row["request_json"]),
            result=result,
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

