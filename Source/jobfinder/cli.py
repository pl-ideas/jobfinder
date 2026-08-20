from __future__ import annotations

import argparse
from pathlib import Path

from jobfinder.company_careers import (
    discover_company_career_pages,
    discover_verified_jobs,
    verify_company_sites,
)
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

    if args.command in {"discover-daily", "discover-job-boards"}:
        run_discover_daily(args)
        return

    if args.command == "verify-company-sites":
        run_verify_company_sites(args)
        return

    if args.command == "discover-career-pages":
        run_discover_career_pages(args)
        return

    if args.command == "discover-verified-jobs":
        run_discover_verified_jobs(args)
        return

    parser.print_help()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Find jobs that match your filters.")
    subparsers = parser.add_subparsers(dest="command")

    fetch = subparsers.add_parser("fetch", help="Fetch, store, filter, and print jobs.")
    fetch.add_argument("--source", choices=["remotive"], default="remotive")
    fetch.add_argument("--query", help="Search query sent to the source.")
    fetch.add_argument("--db", type=Path, default=Path("jobfinder.sqlite3"))
    fetch.add_argument("--limit", type=int, default=100)
    fetch.add_argument("--include-keyword", action="append", default=[])
    fetch.add_argument("--exclude-keyword", action="append", default=[])
    fetch.add_argument("--location")
    fetch.add_argument("--remote-only", action="store_true")
    fetch.add_argument("--min-salary", type=int)
    fetch.add_argument("--allow-company", action="append", default=[])
    fetch.add_argument("--block-company", action="append", default=[])

    discover = subparsers.add_parser(
        "discover-daily",
        help="Scan supported job boards and write Job Database/01-job-board-results/jobs.json.",
    )
    discover.add_argument("--output-dir", type=Path, help="Directory for the daily JSON database.")
    discover.add_argument("--limit-per-query", type=int, default=100)
    discover.add_argument(
        "--continue-after-auth-checkpoint",
        action="store_true",
        help="Record login-required sites and continue to later sources instead of stopping.",
    )
    discover.add_argument("--quiet", action="store_true", help="Suppress progress messages during discovery.")
    discover_alias = subparsers.add_parser(
        "discover-job-boards",
        help="Alias for discover-daily; writes stage 1 job-board results.",
    )
    discover_alias.add_argument("--output-dir", type=Path, help="Root Job Database directory.")
    discover_alias.add_argument("--limit-per-query", type=int, default=100)
    discover_alias.add_argument(
        "--continue-after-auth-checkpoint",
        action="store_true",
        help="Record login-required sites and continue to later sources instead of stopping.",
    )
    discover_alias.add_argument("--quiet", action="store_true", help="Suppress progress messages during discovery.")

    verify_sites = subparsers.add_parser(
        "verify-company-sites",
        help="Stage 2: verify official company homepages from stage 1 results.",
    )
    verify_sites.add_argument("--input-file", type=Path, help="Stage 1 jobs JSON file to use as seed jobs.")
    verify_sites.add_argument("--output-dir", type=Path, help="Root Job Database directory.")
    verify_sites.add_argument("--limit-companies", type=int, default=100, help="Maximum number of companies to verify.")
    verify_sites.add_argument("--quiet", action="store_true", help="Suppress progress messages during verification.")

    career_pages = subparsers.add_parser(
        "discover-career-pages",
        help="Stage 3: discover career page URLs from verified company homepages.",
    )
    career_pages.add_argument("--input-file", type=Path, help="Stage 2 company-sites JSON file.")
    career_pages.add_argument("--output-dir", type=Path, help="Root Job Database directory.")
    career_pages.add_argument("--quiet", action="store_true", help="Suppress progress messages during discovery.")

    verified_jobs = subparsers.add_parser(
        "discover-verified-jobs",
        help="Stage 4: scan verified career pages and write matched corporate jobs.",
    )
    verified_jobs.add_argument("--input-file", type=Path, help="Stage 3 career-pages JSON file.")
    verified_jobs.add_argument("--seed-jobs-file", type=Path, help="Stage 1 jobs JSON file for matching context.")
    verified_jobs.add_argument("--output-dir", type=Path, help="Root Job Database directory.")
    verified_jobs.add_argument("--limit-pages-per-company", type=int, default=100)
    verified_jobs.add_argument("--quiet", action="store_true", help="Suppress progress messages during discovery.")

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


def run_verify_company_sites(args: argparse.Namespace) -> None:
    result = verify_company_sites(
        input_path=args.input_file,
        output_dir=args.output_dir,
        limit_companies=args.limit_companies,
        progress=None if args.quiet else print_progress,
    )

    print(f"Input JSON path: {result.input_path}")
    print(f"Company sites JSON path: {result.output_path}")
    print(f"Companies reviewed: {len(result.companies)}")
    verified = [site for site in result.companies if site.status == "VERIFIED"]
    print(f"Verified company homepages: {len(verified)}")
    _print_company_site_statuses(result.companies)


def run_discover_career_pages(args: argparse.Namespace) -> None:
    result = discover_company_career_pages(
        input_path=args.input_file,
        output_dir=args.output_dir,
        progress=None if args.quiet else print_progress,
    )

    print(f"Input JSON path: {result.input_path}")
    print(f"Career pages JSON path: {result.output_path}")
    found = [page for page in result.career_pages if page.status == "CAREER_PAGE_FOUND"]
    print(f"Career pages found: {len(found)}")
    if result.career_pages:
        print("Career page statuses:")
        for page in result.career_pages:
            reason = f" - {page.reason}" if page.reason else ""
            url = page.careerPageUrl or "none"
            print(f"  - {page.companyName}: {page.status}, url {url}{reason}")


def run_discover_verified_jobs(args: argparse.Namespace) -> None:
    result = discover_verified_jobs(
        career_pages_path=args.input_file,
        seed_jobs_path=args.seed_jobs_file,
        output_dir=args.output_dir,
        limit_pages_per_company=args.limit_pages_per_company,
        progress=None if args.quiet else print_progress,
    )

    print(f"Input JSON path: {result.input_path}")
    print(f"Verified jobs JSON path: {result.output_path}")
    print(f"Companies reviewed: {len(result.companies_reviewed)}")
    print(f"Corporate jobs added: {len(result.jobs_added)}")
    _print_company_review_statuses(result.review_statuses)
    _print_failed_companies(result.failed_companies)


def _print_company_site_statuses(company_sites) -> None:
    if company_sites:
        print("Company site statuses:")
        for site in company_sites:
            reason = f" - {site.reason}" if site.reason else ""
            url = site.homepageUrl or "none"
            print(f"  - {site.companyName}: {site.status}, homepage {url}{reason}")


def _print_company_review_statuses(review_statuses) -> None:
    if review_statuses:
        print("Company review statuses:")
        for status in review_statuses:
            reason = f" - {status.reason}" if status.reason else ""
            print(
                f"  - {status.companyName}: {status.status}, "
                f"reviewed {status.pagesReviewed} pages, found {status.jobsFound} jobs{reason}"
            )


def _print_failed_companies(failed_companies) -> None:
    if failed_companies:
        print("Companies that failed:")
        for company, reason in failed_companies.items():
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
