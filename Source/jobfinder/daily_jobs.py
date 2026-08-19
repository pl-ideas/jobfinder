from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse


RELEVANT_TITLE_TERMS = (
    "software engineer",
    "software developer",
    "full stack",
    "fullstack",
    ".net",
    "dotnet",
    "c#",
    "react developer",
    "react engineer",
    "backend",
    "front end",
    "frontend",
    "web developer",
    "api developer",
)

EXCLUDED_TITLE_TERMS = (
    "product manager",
    "project manager",
    "scrum master",
    "qa engineer",
    "quality assurance",
    "technical support",
    "help desk",
    "sales engineer",
    "recruiter",
)

WORK_MODE_VALUES = {"remote", "hybrid", "onsite", "unknown"}

WORK_MODE_PATTERNS = (
    (
        "hybrid",
        (
            r"\bhybrid\b",
            r"\bin[- ]office\s+\d+\s+days?\b",
            r"\d+\s+days?\s+(?:a week|per week)\s+in (?:the )?office\b",
        ),
    ),
    (
        "onsite",
        (
            r"\bon[- ]site\b",
            r"\bonsite\b",
            r"\bin[- ]person\b",
            r"\bnot\s+(?:a\s+)?remote\b",
            r"\bno\s+remote\b",
        ),
    ),
    (
        "remote",
        (
            r"\bremote\b",
            r"\bwork from home\b",
            r"\btelecommute\b",
            r"\bdistributed team\b",
        ),
    ),
)


@dataclass(frozen=True)
class DailyJobRecord:
    companyName: str
    jobTitle: str
    jobUrl: str
    applicationUrl: str
    source: str
    location: str | None = None
    remote: bool | None = None
    salary: str | None = None
    datePosted: str | None = None
    dateDiscovered: str | None = None
    workMode: str = "unknown"
    workModeEvidence: str | None = None
    classification: str = "REVIEW"
    matchedSkills: tuple[str, ...] = ()
    excludedSkillsFound: tuple[str, ...] = ()
    exclusionReason: str | None = None

    def normalized(self, discovered_on: date | None = None) -> "DailyJobRecord":
        discovered = discovered_on or date.today()
        work_mode = self.workMode if self.workMode in WORK_MODE_VALUES else "unknown"
        classification = self.classification if self.classification in {"INCLUDE", "EXCLUDE", "REVIEW"} else "REVIEW"
        return DailyJobRecord(
            companyName=_clean_text(self.companyName),
            jobTitle=_clean_text(self.jobTitle),
            jobUrl=self.jobUrl.strip(),
            applicationUrl=(self.applicationUrl or self.jobUrl).strip(),
            source=_clean_text(self.source),
            location=_optional_text(self.location),
            remote=self.remote,
            salary=_optional_text(self.salary),
            datePosted=_optional_text(self.datePosted),
            dateDiscovered=self.dateDiscovered or discovered.isoformat(),
            workMode=work_mode,
            workModeEvidence=_optional_text(self.workModeEvidence),
            classification=classification,
            matchedSkills=tuple(_clean_text(skill) for skill in self.matchedSkills if _clean_text(skill)),
            excludedSkillsFound=tuple(_clean_text(skill) for skill in self.excludedSkillsFound if _clean_text(skill)),
            exclusionReason=_optional_text(self.exclusionReason),
        )

    def to_json_dict(self) -> dict[str, object]:
        return {
            "companyName": self.companyName,
            "jobTitle": self.jobTitle,
            "jobUrl": self.jobUrl,
            "applicationUrl": self.applicationUrl,
            "source": self.source,
            "location": self.location,
            "remote": self.remote,
            "salary": self.salary,
            "datePosted": self.datePosted,
            "dateDiscovered": self.dateDiscovered,
            "workMode": self.workMode,
            "workModeEvidence": self.workModeEvidence,
            "classification": self.classification,
            "matchedSkills": list(self.matchedSkills),
            "excludedSkillsFound": list(self.excludedSkillsFound),
            "exclusionReason": self.exclusionReason,
        }


def is_relevant_remote_development_job(job: DailyJobRecord) -> bool:
    title = job.jobTitle.lower()
    searchable = " ".join(
        value
        for value in [
            job.jobTitle,
            job.companyName,
            job.location or "",
        ]
        if value
    ).lower()

    if any(term in title for term in EXCLUDED_TITLE_TERMS):
        return False

    if job.workMode in {"hybrid", "onsite"}:
        return False

    is_remote = job.workMode == "remote" or job.remote is True or "remote" in (job.location or "").lower()
    if not is_remote:
        return False

    if job.classification == "EXCLUDE":
        return False

    if job.matchedSkills:
        return True

    return any(term in searchable for term in RELEVANT_TITLE_TERMS)


def classify_work_mode(
    text: str | None,
    *,
    metadata_remote: bool = False,
    metadata_evidence: str | None = None,
) -> tuple[str, str | None]:
    cleaned = _clean_text(text or "")
    for work_mode, patterns in WORK_MODE_PATTERNS:
        for pattern in patterns:
            match = re.search(pattern, cleaned, flags=re.IGNORECASE)
            if match:
                return work_mode, _evidence_sentence(cleaned, match.start(), match.end())

    if metadata_remote:
        return "remote", metadata_evidence or "Structured metadata indicates remote work."

    return "unknown", None


def deduplicate_jobs(jobs: list[DailyJobRecord]) -> list[DailyJobRecord]:
    deduped: dict[str, DailyJobRecord] = {}
    for job in jobs:
        normalized = job.normalized()
        if not _has_required_fields(normalized):
            continue

        key = duplicate_key(normalized)
        existing = deduped.get(key)
        if existing is None or _directness_score(normalized) > _directness_score(existing):
            deduped[key] = normalized

    return sorted(deduped.values(), key=lambda item: (item.companyName.lower(), item.jobTitle.lower()))


def duplicate_key(job: DailyJobRecord) -> str:
    return "|".join([_company_fingerprint(job.companyName), _title_fingerprint(job.jobTitle)])


def _has_required_fields(job: DailyJobRecord) -> bool:
    return all([job.companyName, job.jobTitle, job.jobUrl, job.applicationUrl, job.source])


def _directness_score(job: DailyJobRecord) -> int:
    application_host = _host(job.applicationUrl)
    job_host = _host(job.jobUrl)
    source_host = _host_for_source(job.source)

    score = 0
    if application_host and application_host != job_host:
        score += 2
    if application_host and source_host and source_host not in application_host:
        score += 2
    if any(marker in job.applicationUrl.lower() for marker in ("apply", "application", "greenhouse", "lever", "workday")):
        score += 1
    return score


def _host(value: str) -> str:
    return urlparse(value).netloc.lower().removeprefix("www.")


def _host_for_source(source: str) -> str:
    source_key = source.strip().lower()
    hosts = {
        "built in": "builtin.com",
        "dice": "dice.com",
        "indeed": "indeed.com",
        "linkedin jobs": "linkedin.com",
        "wellfound": "wellfound.com",
    }
    return hosts.get(source_key, "")


def _company_fingerprint(value: str) -> str:
    value = value.lower().replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    parts = [part for part in value.split() if part not in {"inc", "llc", "ltd", "corp", "corporation", "co", "company"}]
    return " ".join(parts)


def _title_fingerprint(value: str) -> str:
    value = value.lower().replace("&", "and").replace(".net", "dotnet")
    value = re.sub(r"[^a-z0-9#+]+", " ", value)
    return " ".join(value.split())


def _clean_text(value: str) -> str:
    return " ".join(value.strip().split())


def _evidence_sentence(text: str, start: int, end: int) -> str:
    sentence_start = max(text.rfind(".", 0, start), text.rfind("!", 0, start), text.rfind("?", 0, start))
    sentence_end_candidates = [index for index in (text.find(".", end), text.find("!", end), text.find("?", end)) if index != -1]
    sentence_end = min(sentence_end_candidates) if sentence_end_candidates else min(len(text), end + 120)

    evidence = text[sentence_start + 1 : sentence_end + 1].strip()
    if len(evidence) <= 180:
        return evidence
    return f"{evidence[:177].rstrip()}..."


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _clean_text(value)
    return cleaned or None
