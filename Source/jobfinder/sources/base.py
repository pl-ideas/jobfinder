from __future__ import annotations

from typing import Protocol

from jobfinder.models import JobPosting


class JobSource(Protocol):
    """Adapter interface for job sources."""

    name: str

    def fetch(self, query: str | None = None, limit: int | None = None) -> list[JobPosting]:
        """Fetch normalized job postings from this source."""
        ...
