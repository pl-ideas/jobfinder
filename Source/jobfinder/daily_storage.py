from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from jobfinder.daily_jobs import DailyJobRecord, deduplicate_jobs


def default_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def daily_database_path(output_dir: Path | None = None, generated_on: date | None = None) -> Path:
    generated = generated_on or date.today()
    directory = output_dir or default_project_root() / "Job Database"
    return directory / f"jobs-{generated.isoformat()}.json"


def load_daily_jobs(path: Path) -> list[DailyJobRecord]:
    if not path.exists():
        return []

    payload = json.loads(path.read_text(encoding="utf-8"))
    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        raise ValueError(f"Expected 'jobs' to be a list in {path}")

    return [_job_from_json(item) for item in jobs if isinstance(item, dict)]


def merge_and_save_daily_jobs(
    new_jobs: list[DailyJobRecord],
    *,
    output_dir: Path | None = None,
    generated_on: date | None = None,
) -> Path:
    generated = generated_on or date.today()
    output_path = daily_database_path(output_dir=output_dir, generated_on=generated)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    existing_jobs = load_daily_jobs(output_path)
    jobs = deduplicate_jobs(existing_jobs + new_jobs)
    payload = {
        "generatedDate": generated.isoformat(),
        "jobs": [job.normalized(generated).to_json_dict() for job in jobs],
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def parse_daily_database(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _job_from_json(item: dict[str, Any]) -> DailyJobRecord:
    return DailyJobRecord(
        companyName=str(item.get("companyName") or ""),
        jobTitle=str(item.get("jobTitle") or ""),
        jobUrl=str(item.get("jobUrl") or ""),
        applicationUrl=str(item.get("applicationUrl") or item.get("jobUrl") or ""),
        source=str(item.get("source") or ""),
        location=_optional_string(item.get("location")),
        remote=item.get("remote") if isinstance(item.get("remote"), bool) else None,
        salary=_optional_string(item.get("salary")),
        datePosted=_optional_string(item.get("datePosted")),
        dateDiscovered=_optional_string(item.get("dateDiscovered")),
        workMode=str(item.get("workMode") or "unknown"),
        workModeEvidence=_optional_string(item.get("workModeEvidence")),
        classification=str(item.get("classification") or "REVIEW"),
        matchedSkills=_string_tuple(item.get("matchedSkills")),
        excludedSkillsFound=_string_tuple(item.get("excludedSkillsFound")),
        exclusionReason=_optional_string(item.get("exclusionReason")),
    )


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(text for item in value if (text := str(item).strip()))
