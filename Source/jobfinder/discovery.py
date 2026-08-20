from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable

from jobfinder.daily_jobs import DailyJobRecord, deduplicate_jobs
from jobfinder.daily_storage import daily_database_path, merge_and_save_daily_jobs
from jobfinder.sources.web_boards import (
    BuiltInSource,
    DiceSource,
    IndeedSource,
    LinkedInJobsSource,
    PublicJobBoardSource,
    SourceScanResult,
    WellfoundSource,
)

ProgressCallback = Callable[[str], None]


@dataclass(frozen=True)
class DailyDiscoveryResult:
    jobs: list[DailyJobRecord]
    output_path: Path
    scanned_sites: list[str] = field(default_factory=list)
    authentication_required_sites: list[str] = field(default_factory=list)
    failed_sites: dict[str, str] = field(default_factory=dict)


def default_sources() -> list[PublicJobBoardSource]:
    return [
        BuiltInSource(),
        DiceSource(),
        IndeedSource(),
        LinkedInJobsSource(),
        WellfoundSource(),
    ]


def run_daily_discovery(
    *,
    output_dir: Path | None = None,
    generated_on: date | None = None,
    limit_per_query: int = 100,
    source_names: list[str] | None = None,
    stop_on_authentication_required: bool = True,
    progress: ProgressCallback | None = None,
) -> DailyDiscoveryResult:
    scanned_sites: list[str] = []
    authentication_required_sites: list[str] = []
    failed_sites: dict[str, str] = {}
    all_jobs: list[DailyJobRecord] = []
    generated = generated_on or date.today()
    output_path = daily_database_path(output_dir=output_dir, generated_on=generated)

    _report(progress, "Starting daily job discovery.")
    _report(progress, f"Output target: {output_path}")

    for source in _selected_sources(source_names):
        _report(progress, f"Scanning {source.display_name}.")
        result = _scan_source(source, limit_per_query=limit_per_query, progress=progress)
        if result.authentication_required:
            authentication_required_sites.append(result.source)
            if stop_on_authentication_required:
                break
            continue

        if result.failed_reason:
            failed_sites[result.source] = result.failed_reason
            _report(progress, f"{result.source}: failed; continuing with remaining sites.")
            continue

        scanned_sites.append(result.source)
        all_jobs.extend(result.jobs)
        _report(progress, f"{result.source}: collected {len(result.jobs)} relevant jobs.")

    jobs = deduplicate_jobs(all_jobs)
    _report(progress, f"Merging and deduplicating {len(all_jobs)} collected jobs.")
    output_path = merge_and_save_daily_jobs(jobs, output_dir=output_dir, generated_on=generated)
    _report(progress, f"After dedupe: {len(jobs)} unique jobs.")
    _report(progress, f"Saved daily JSON database: {output_path}")

    return DailyDiscoveryResult(
        jobs=jobs,
        output_path=output_path,
        scanned_sites=scanned_sites,
        authentication_required_sites=authentication_required_sites,
        failed_sites=failed_sites,
    )


def _scan_source(
    source: PublicJobBoardSource,
    *,
    limit_per_query: int,
    progress: ProgressCallback | None = None,
) -> SourceScanResult:
    try:
        return source.scan(limit_per_query=limit_per_query, progress=progress)
    except Exception as error:  # noqa: BLE001 - source failures must not destroy other boards' results.
        return SourceScanResult(source.display_name, failed_reason=str(error))


def _selected_sources(source_names: list[str] | None = None) -> list[PublicJobBoardSource]:
    sources = default_sources()
    if source_names is None:
        return sources

    requested = {_source_key(name) for name in source_names}
    return [source for source in sources if _source_key(source.display_name) in requested]


def _source_key(value: str) -> str:
    return " ".join(value.casefold().split())


def _report(progress: ProgressCallback | None, message: str) -> None:
    if progress is not None:
        progress(message)
