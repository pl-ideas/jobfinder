from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from jobfinder.models import JobPosting, RemoteStatus


class JobStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    stable_key TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    description TEXT NOT NULL,
                    remote_status TEXT NOT NULL,
                    salary_min INTEGER,
                    salary_max INTEGER,
                    tags TEXT NOT NULL,
                    date_discovered TEXT NOT NULL,
                    last_seen TEXT NOT NULL
                )
                """
            )

    def upsert_many(self, jobs: Iterable[JobPosting]) -> int:
        now = datetime.now().isoformat()
        rows = [
            (
                job.stable_key,
                job.title,
                job.company,
                job.location,
                job.source_name,
                job.source_url,
                job.description,
                job.remote_status.value,
                job.salary_min,
                job.salary_max,
                ",".join(job.tags),
                job.date_discovered.isoformat(),
                now,
            )
            for job in jobs
        ]

        if not rows:
            return 0

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO jobs (
                    stable_key, title, company, location, source_name, source_url,
                    description, remote_status, salary_min, salary_max, tags,
                    date_discovered, last_seen
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(stable_key) DO UPDATE SET
                    title = excluded.title,
                    company = excluded.company,
                    location = excluded.location,
                    source_name = excluded.source_name,
                    source_url = excluded.source_url,
                    description = excluded.description,
                    remote_status = excluded.remote_status,
                    salary_min = excluded.salary_min,
                    salary_max = excluded.salary_max,
                    tags = excluded.tags,
                    last_seen = excluded.last_seen
                """,
                rows,
            )
        return len(rows)

    def list_jobs(self) -> list[JobPosting]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT title, company, location, source_name, source_url, description,
                       remote_status, salary_min, salary_max, tags, date_discovered
                FROM jobs
                ORDER BY last_seen DESC
                """
            ).fetchall()

        return [
            JobPosting(
                title=row["title"],
                company=row["company"],
                location=row["location"],
                source_name=row["source_name"],
                source_url=row["source_url"],
                description=row["description"],
                remote_status=RemoteStatus(row["remote_status"]),
                salary_min=row["salary_min"],
                salary_max=row["salary_max"],
                tags=tuple(tag for tag in row["tags"].split(",") if tag),
                date_discovered=datetime.fromisoformat(row["date_discovered"]),
            )
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection
