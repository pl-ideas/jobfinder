from __future__ import annotations

from dataclasses import dataclass, field

from jobfinder.models import JobPosting, RemoteStatus


def _normalize_terms(terms: list[str] | None) -> tuple[str, ...]:
    return tuple(term.strip().lower() for term in terms or [] if term.strip())


@dataclass(frozen=True)
class JobFilter:
    include_keywords: tuple[str, ...] = field(default_factory=tuple)
    exclude_keywords: tuple[str, ...] = field(default_factory=tuple)
    location: str | None = None
    remote_only: bool = False
    min_salary: int | None = None
    allow_companies: tuple[str, ...] = field(default_factory=tuple)
    block_companies: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_raw(
        cls,
        *,
        include_keywords: list[str] | None = None,
        exclude_keywords: list[str] | None = None,
        location: str | None = None,
        remote_only: bool = False,
        min_salary: int | None = None,
        allow_companies: list[str] | None = None,
        block_companies: list[str] | None = None,
    ) -> "JobFilter":
        return cls(
            include_keywords=_normalize_terms(include_keywords),
            exclude_keywords=_normalize_terms(exclude_keywords),
            location=location.strip().lower() if location else None,
            remote_only=remote_only,
            min_salary=min_salary,
            allow_companies=_normalize_terms(allow_companies),
            block_companies=_normalize_terms(block_companies),
        )

    def matches(self, job: JobPosting) -> bool:
        text = job.searchable_text
        company = job.company.lower()

        if self.include_keywords and not all(term in text for term in self.include_keywords):
            return False

        if self.exclude_keywords and any(term in text for term in self.exclude_keywords):
            return False

        if self.location and self.location not in job.location.lower():
            return False

        if self.remote_only and job.remote_status != RemoteStatus.REMOTE:
            return False

        if self.min_salary is not None:
            salary = job.salary_max or job.salary_min
            if salary is None or salary < self.min_salary:
                return False

        if self.allow_companies and not any(term in company for term in self.allow_companies):
            return False

        if self.block_companies and any(term in company for term in self.block_companies):
            return False

        return True


def filter_jobs(jobs: list[JobPosting], job_filter: JobFilter) -> list[JobPosting]:
    return [job for job in jobs if job_filter.matches(job)]
