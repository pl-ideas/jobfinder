from __future__ import annotations

import argparse
from pathlib import Path

from jobfinder.filters import JobFilter, filter_jobs
from jobfinder.models import JobPosting
from jobfinder.sources import RemotiveSource
from jobfinder.sources.base import JobSource
from jobfinder.storage import JobStore


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "fetch":
        run_fetch(args)
        return

    parser.print_help()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Find jobs that match your filters.")
    subparsers = parser.add_subparsers(dest="command")

    fetch = subparsers.add_parser("fetch", help="Fetch, store, filter, and print jobs.")
    fetch.add_argument("--source", choices=["remotive"], default="remotive")
    fetch.add_argument("--query", help="Search query sent to the source.")
    fetch.add_argument("--db", type=Path, default=Path("jobfinder.sqlite3"))
    fetch.add_argument("--limit", type=int, default=25)
    fetch.add_argument("--include-keyword", action="append", default=[])
    fetch.add_argument("--exclude-keyword", action="append", default=[])
    fetch.add_argument("--location")
    fetch.add_argument("--remote-only", action="store_true")
    fetch.add_argument("--min-salary", type=int)
    fetch.add_argument("--allow-company", action="append", default=[])
    fetch.add_argument("--block-company", action="append", default=[])

    return parser


def run_fetch(args: argparse.Namespace) -> None:
    source = build_source(args.source)
    store = JobStore(args.db)
    store.initialize()

    fetched_jobs = source.fetch(query=args.query, limit=args.limit)
    saved_count = store.upsert_many(fetched_jobs)

    job_filter = JobFilter.from_raw(
        include_keywords=args.include_keyword,
        exclude_keywords=args.exclude_keyword,
        location=args.location,
        remote_only=args.remote_only,
        min_salary=args.min_salary,
        allow_companies=args.allow_company,
        block_companies=args.block_company,
    )
    matches = filter_jobs(store.list_jobs(), job_filter)

    print(f"Fetched {len(fetched_jobs)} jobs from {source.name}. Saved {saved_count} records.")
    print(f"Found {len(matches)} matching jobs.\n")
    print_jobs(matches)


def build_source(name: str) -> JobSource:
    if name == "remotive":
        return RemotiveSource()
    raise ValueError(f"Unsupported source: {name}")


def print_jobs(jobs: list[JobPosting]) -> None:
    for index, job in enumerate(jobs, start=1):
        salary = format_salary(job)
        print(f"{index}. {job.title} at {job.company}")
        print(f"   Location: {job.location} | Remote: {job.remote_status.value} | Salary: {salary}")
        print(f"   Source: {job.source_url}")
        if job.tags:
            print(f"   Tags: {', '.join(job.tags[:8])}")
        print()


def format_salary(job: JobPosting) -> str:
    if job.salary_min is None and job.salary_max is None:
        return "unknown"
    if job.salary_min == job.salary_max:
        return f"${job.salary_min:,}"
    if job.salary_min is None:
        return f"up to ${job.salary_max:,}"
    if job.salary_max is None:
        return f"from ${job.salary_min:,}"
    return f"${job.salary_min:,} - ${job.salary_max:,}"


if __name__ == "__main__":
    main()
