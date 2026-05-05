from __future__ import annotations

import asyncio
from collections.abc import Mapping
import json
import sqlite3
from threading import Lock

from scrybe_api.config import Settings
from scrybe_api.schemas.common import JobStatus, OutputFormat, ScrybedDocument


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._memory_connection: sqlite3.Connection | None = None
        self._lock = Lock()

    def _is_memory(self) -> bool:
        return str(self.settings.sqlite_path) == ":memory:"

    def _get_connection(self) -> sqlite3.Connection:
        if self._is_memory():
            if self._memory_connection is None:
                self._memory_connection = sqlite3.connect(":memory:", check_same_thread=False)
                self._memory_connection.row_factory = sqlite3.Row
            return self._memory_connection
        connection = sqlite3.connect(self.settings.sqlite_path)
        connection.row_factory = sqlite3.Row
        return connection

    async def initialize(self) -> None:
        def _initialize() -> None:
            if self._is_memory():
                db = self._get_connection()
                with self._lock:
                    db.execute(
                        """
                        CREATE TABLE IF NOT EXISTS jobs (
                            job_id TEXT PRIMARY KEY,
                            status TEXT NOT NULL,
                            output_format TEXT NOT NULL,
                            request_json TEXT NOT NULL,
                            result_json TEXT,
                            error TEXT,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL
                        )
                        """
                    )
                    db.commit()
                return
            with self._get_connection() as db:
                db.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    output_format TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
                db.commit()
        await asyncio.to_thread(_initialize)

    async def create_job(
        self,
        job_id: str,
        status: JobStatus,
        output_format: OutputFormat,
        request_json: Mapping,
        created_at: str,
        updated_at: str,
    ) -> None:
        def _create() -> None:
            if self._is_memory():
                db = self._get_connection()
                with self._lock:
                    db.execute(
                        """
                        INSERT INTO jobs (job_id, status, output_format, request_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            job_id,
                            status.value,
                            output_format.value,
                            json.dumps(dict(request_json), ensure_ascii=True),
                            created_at,
                            updated_at,
                        ),
                    )
                    db.commit()
                return
            with self._get_connection() as db:
                db.execute(
                """
                INSERT INTO jobs (job_id, status, output_format, request_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    status.value,
                    output_format.value,
                    json.dumps(dict(request_json), ensure_ascii=True),
                    created_at,
                    updated_at,
                ),
            )
                db.commit()
        await asyncio.to_thread(_create)

    async def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus,
        updated_at: str,
        result: ScrybedDocument | None = None,
        error: str | None = None,
    ) -> None:
        def _update() -> None:
            if self._is_memory():
                db = self._get_connection()
                with self._lock:
                    db.execute(
                        """
                        UPDATE jobs
                        SET status = ?, updated_at = ?, result_json = COALESCE(?, result_json), error = ?
                        WHERE job_id = ?
                        """,
                        (
                            status.value,
                            updated_at,
                            result.model_dump_json() if result else None,
                            error,
                            job_id,
                        ),
                    )
                    db.commit()
                return
            with self._get_connection() as db:
                db.execute(
                """
                UPDATE jobs
                SET status = ?, updated_at = ?, result_json = COALESCE(?, result_json), error = ?
                WHERE job_id = ?
                """,
                (
                    status.value,
                    updated_at,
                    result.model_dump_json() if result else None,
                    error,
                    job_id,
                ),
            )
                db.commit()
        await asyncio.to_thread(_update)

    async def get_job(self, job_id: str) -> dict | None:
        def _get() -> dict | None:
            if self._is_memory():
                db = self._get_connection()
                with self._lock:
                    cursor = db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
                    row = cursor.fetchone()
                    if row is None:
                        return None
                    return dict(row)
            with self._get_connection() as db:
                cursor = db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
                row = cursor.fetchone()
                if row is None:
                    return None
                return dict(row)
        return await asyncio.to_thread(_get)
