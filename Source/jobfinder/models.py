from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class RemoteStatus(StrEnum):
    """Normalized remote-work status across job sources."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class JobPosting:
    """A normalized job posting from any supported source."""

    title: str
    company: str
    location: str
    source_name: str
    source_url: str
    description: str = ""
    remote_status: RemoteStatus = RemoteStatus.UNKNOWN
    salary_min: int | None = None
    salary_max: int | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    date_discovered: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def searchable_text(self) -> str:
        return " ".join(
            [
                self.title,
                self.company,
                self.location,
                self.description,
                " ".join(self.tags),
            ]
        ).lower()

    @property
    def stable_key(self) -> str:
        return self.source_url.strip().lower()
