from __future__ import annotations

import argparse
from pathlib import Path

from jobfinder.company_careers import run_company_careers_discovery
from jobfinder.discovery import run_daily_discovery
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

    if args.command == "discover-daily":
        run_discover_daily(args)
        return

    if args.command == "discover-company-careers":
        run_discover_company_careers(args)
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

    discover = subparsers.add_parser(
        "discover-daily",
        help="Scan supported job boards and write Job Database/jobs-{date}.json.",
    )
    discover.add_argument("--output-dir", type=Path, help="Directory for the daily JSON database.")
    discover.add_argument("--limit-per-query", type=int, default=10)
    discover.add_argument(
        "--continue-after-auth-checkpoint",
        action="store_true",
        help="Record login-required sites and continue to later sources instead of stopping.",
    )
    discover.add_argument("--quiet", action="store_true", help="Suppress progress messages during discovery.")

    company_careers = subparsers.add_parser(
        "discover-company-careers",
        help="Scan company career sites from the latest daily JSON database.",
    )
    company_careers.add_argument("--input-file", type=Path, help="Daily JSON file to use as seed jobs.")
    company_careers.add_argument("--output-dir", type=Path, help="Directory containing the daily JSON database.")
    company_careers.add_argument("--limit-companies", type=int, help="Maximum number of companies to review.")
    company_careers.add_argument("--limit-pages-per-company", type=int, default=25)
    company_careers.add_argument(
        "--allow-domain-guessing",
        action="store_true",
        default=True,
        help="Try guessed company homepages when no corporate URL is present. Enabled by default.",
    )
    company_careers.add_argument(
        "--no-domain-guessing",
        dest="allow_domain_guessing",
        action="store_false",
        help="Disable guessed company homepage checks.",
    )
    company_careers.add_argument("--quiet", action="store_true", help="Suppress progress messages during discovery.")

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


def run_discover_daily(args: argparse.Namespace) -> None:
    result = run_daily_discovery(
        output_dir=args.output_dir,
        limit_per_query=args.limit_per_query,
        stop_on_authentication_required=not args.continue_after_auth_checkpoint,
        progress=None if args.quiet else print_progress,
    )

    if result.authentication_required_sites and not args.continue_after_auth_checkpoint:
        site = result.authentication_required_sites[0]
        print(f"LOGIN REQUIRED: {site}. Please log in using the browser and tell me when authentication is complete.")
        return

    print(f"Sites successfully scanned: {', '.join(result.scanned_sites) or 'none'}")
    print(f"Sites requiring authentication: {', '.join(result.authentication_required_sites) or 'none'}")
    if result.failed_sites:
        print("Sites that failed:")
        for site, reason in result.failed_sites.items():
            print(f"  - {site}: {reason}")
    else:
        print("Sites that failed: none")
    print(f"Unique jobs collected: {len(result.jobs)}")
    print(f"JSON output path: {result.output_path}")


def print_progress(message: str) -> None:
    print(message, flush=True)


def run_discover_company_careers(args: argparse.Namespace) -> None:
    result = run_company_careers_discovery(
        input_path=args.input_file,
        output_dir=args.output_dir,
        limit_companies=args.limit_companies,
        limit_pages_per_company=args.limit_pages_per_company,
        allow_domain_guessing=args.allow_domain_guessing,
        progress=None if args.quiet else print_progress,
    )

    print(f"Input JSON path: {result.input_path}")
    print(f"Verified output JSON path: {result.output_path}")
    print(f"Companies reviewed: {len(result.companies_reviewed)}")
    print(f"Corporate jobs added: {len(result.jobs_added)}")
    if result.review_statuses:
        print("Company review statuses:")
        for status in result.review_statuses:
            reason = f" - {status.reason}" if status.reason else ""
            print(
                f"  - {status.companyName}: {status.status}, "
                f"reviewed {status.pagesReviewed} pages, found {status.jobsFound} jobs{reason}"
            )
    manual_statuses = [status for status in result.review_statuses if status.status == "MANUAL_VERIFICATION"]
    if manual_statuses:
        print("Manual verification recommended:")
        for status in manual_statuses:
            reason = f" - {status.reason}" if status.reason else ""
            print(f"  - {status.companyName}{reason}")
    if result.failed_companies:
        print("Companies that failed:")
        for company, reason in result.failed_companies.items():
            print(f"  - {company}: {reason}")
    else:
        print("Companies that failed: none")


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
