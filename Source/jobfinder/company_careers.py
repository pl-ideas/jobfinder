from __future__ import annotations

import re
import json
import base64
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from jobfinder.daily_jobs import DailyJobRecord, is_relevant_remote_development_job
from jobfinder.daily_storage import (
    COMPANY_SITE_STAGE_DIR,
    CAREER_PAGE_STAGE_DIR,
    JOB_BOARD_STAGE_DIR,
    career_pages_database_path,
    company_sites_database_path,
    default_project_root,
    latest_dated_database_path,
    load_daily_jobs,
    merge_and_save_verified_jobs,
)
from jobfinder.employer_exclusions import employer_exclusion_reason, is_acceptable_recruiting_agency
from jobfinder.sources.web_boards import LinkParser, extract_json_ld_jobs, fetch_html


ProgressCallback = Callable[[str], None]
HtmlFetcher = Callable[[str], str]

JOB_BOARD_HOST_MARKERS = (
    "builtin.com",
    "dice.com",
    "indeed.com",
    "linkedin.com",
    "wellfound.com",
)

ATS_HOST_MARKERS = (
    "greenhouse.io",
    "lever.co",
    "workdayjobs.com",
    "myworkdayjobs.com",
    "ashbyhq.com",
    "smartrecruiters.com",
    "jobvite.com",
    "icims.com",
)

SEARCH_RESULT_EXCLUDED_HOST_MARKERS = (
    "duckduckgo.com",
    "google.com",
    "bing.com",
    "linkedin.com",
    "indeed.com",
    "builtin.com",
    "dice.com",
    "wellfound.com",
    "glassdoor.com",
    "facebook.com",
)

HOMEPAGE_TLDS = ("com", "net", "org", "io", "co")

CAREER_LINK_TEXT_MARKERS = (
    "career",
    "careers",
    "jobs",
    "work for us",
    "join us",
    "open roles",
    "open positions",
    "opportunities",
)

ROLE_CATEGORY_LINK_MARKERS = (
    "software engineering",
    "software engineer",
    "engineering",
    "technology",
    "developer",
    "development",
    "consulting",
    "professional services",
    "experienced professionals",
)


@dataclass(frozen=True)
class CompanyCareersResult:
    input_path: Path
    output_path: Path
    companies_reviewed: list[str] = field(default_factory=list)
    jobs_added: list[DailyJobRecord] = field(default_factory=list)
    failed_companies: dict[str, str] = field(default_factory=dict)
    review_statuses: list["CompanyReviewStatus"] = field(default_factory=list)


@dataclass(frozen=True)
class CompanyReviewStatus:
    companyName: str
    status: str
    pagesReviewed: int = 0
    jobsFound: int = 0
    reason: str | None = None


@dataclass(frozen=True)
class CompanyScanResult:
    jobs: list[DailyJobRecord] = field(default_factory=list)
    pages_reviewed: int = 0
    status: str = "FULLY_REVIEWED"
    reason: str | None = None


@dataclass(frozen=True)
class HomepageDiscoveryResult:
    status: str
    homepage_url: str | None = None
    career_urls: list[str] = field(default_factory=list)
    reason: str | None = None


@dataclass(frozen=True)
class VerifiedCompanySite:
    companyName: str
    homepageUrl: str | None
    status: str
    sourceSeed: dict[str, object]
    reason: str | None = None
    dateVerified: str | None = None

    def to_json_dict(self, generated_on: date) -> dict[str, object]:
        return {
            "companyName": self.companyName,
            "sourceSeed": self.sourceSeed,
            "homepageUrl": self.homepageUrl,
            "status": self.status,
            "reason": self.reason,
            "dateVerified": self.dateVerified or generated_on.isoformat(),
        }


@dataclass(frozen=True)
class VerifiedCareerPage:
    companyName: str
    homepageUrl: str
    careerPageUrl: str | None
    status: str
    pagesReviewed: int = 0
    reason: str | None = None
    dateDiscovered: str | None = None

    def to_json_dict(self, generated_on: date) -> dict[str, object]:
        return {
            "companyName": self.companyName,
            "homepageUrl": self.homepageUrl,
            "careerPageUrl": self.careerPageUrl,
            "status": self.status,
            "pagesReviewed": self.pagesReviewed,
            "reason": self.reason,
            "dateDiscovered": self.dateDiscovered or generated_on.isoformat(),
        }


@dataclass(frozen=True)
class CompanySitesResult:
    input_path: Path
    output_path: Path
    companies: list[VerifiedCompanySite] = field(default_factory=list)


@dataclass(frozen=True)
class CareerPagesResult:
    input_path: Path
    output_path: Path
    career_pages: list[VerifiedCareerPage] = field(default_factory=list)


def latest_daily_database_path(output_dir: Path | None = None) -> Path:
    return latest_dated_database_path("jobs", output_dir=output_dir, stage_dir=JOB_BOARD_STAGE_DIR)


def latest_company_sites_database_path(output_dir: Path | None = None) -> Path:
    return latest_dated_database_path("company-sites", output_dir=output_dir, stage_dir=COMPANY_SITE_STAGE_DIR)


def latest_career_pages_database_path(output_dir: Path | None = None) -> Path:
    return latest_dated_database_path("career-pages", output_dir=output_dir, stage_dir=CAREER_PAGE_STAGE_DIR)


def verify_company_sites(
    *,
    input_path: Path | None = None,
    output_dir: Path | None = None,
    limit_companies: int | None = 100,
    use_public_search: bool = True,
    progress: ProgressCallback | None = None,
    fetcher: HtmlFetcher = fetch_html,
) -> CompanySitesResult:
    source_path = input_path or latest_daily_database_path(output_dir)
    seed_jobs = load_daily_jobs(source_path)
    generated = _date_from_stage_path(source_path) or date.today()
    company_sites: list[VerifiedCompanySite] = []

    _report(progress, f"Company site verification input: {source_path}")
    for seed_job in _unique_company_seed_jobs(seed_jobs, limit_companies):
        employer_reason = employer_exclusion_reason(seed_job.companyName)
        if employer_reason:
            company_sites.append(
                _company_site_record(seed_job, None, "EXCLUDED_EMPLOYER", employer_reason, generated)
            )
            _report(progress, f"{seed_job.companyName}: excluded employer; {employer_reason}")
            continue

        if is_acceptable_recruiting_agency(seed_job.companyName):
            reason = "Acceptable recruiting agency; manual homepage verification is recommended."
            company_sites.append(_company_site_record(seed_job, None, "MANUAL_VERIFICATION", reason, generated))
            _report(progress, f"{seed_job.companyName}: manual verification recommended; {reason}")
            continue

        if not use_public_search:
            reason = "Public homepage search is disabled; no verified homepage was produced."
            company_sites.append(_company_site_record(seed_job, None, "NO_SEARCH_RESULTS", reason, generated))
            _report(progress, f"{seed_job.companyName}: NO_SEARCH_RESULTS; {reason}")
            continue

        _report(progress, f"{seed_job.companyName}: locating official corporate homepage via public search.")
        homepage_result = discover_homepage_from_search(seed_job.companyName, progress=progress, fetcher=fetcher)
        if homepage_result.status == "SEARCH_HOMEPAGE_FOUND" and homepage_result.homepage_url:
            company_sites.append(
                _company_site_record(seed_job, homepage_result.homepage_url, "VERIFIED", None, generated)
            )
            continue

        status = homepage_result.status
        reason = homepage_result.reason or "No official company homepage was found by public search."
        if status == "SEARCH_RESULT_UNVERIFIED":
            status = "MANUAL_VERIFICATION"
        company_sites.append(_company_site_record(seed_job, homepage_result.homepage_url, status, reason, generated))
        _report(progress, f"{seed_job.companyName}: {status}; {reason}")

    output_path = save_company_sites(company_sites, output_dir=output_dir, generated_on=generated)
    _report(progress, f"Company site verification saved: {output_path}")
    return CompanySitesResult(source_path, output_path, company_sites)


def discover_company_career_pages(
    *,
    input_path: Path | None = None,
    output_dir: Path | None = None,
    progress: ProgressCallback | None = None,
    fetcher: HtmlFetcher = fetch_html,
) -> CareerPagesResult:
    source_path = input_path or latest_company_sites_database_path(output_dir)
    company_sites = load_company_sites(source_path)
    generated = _date_from_stage_path(source_path) or date.today()
    career_pages: list[VerifiedCareerPage] = []

    _report(progress, f"Career page discovery input: {source_path}")
    for company_site in company_sites:
        if company_site.status != "VERIFIED" or not company_site.homepageUrl:
            reason = company_site.reason or f"Company site status is {company_site.status}, not VERIFIED."
            career_pages.append(
                VerifiedCareerPage(
                    company_site.companyName,
                    company_site.homepageUrl or "",
                    None,
                    company_site.status,
                    reason=reason,
                    dateDiscovered=generated.isoformat(),
                )
            )
            continue

        result = discover_career_urls_from_verified_homepage(
            company_site.companyName,
            company_site.homepageUrl,
            progress=progress,
            fetcher=fetcher,
        )
        if result.career_urls:
            for career_url in result.career_urls:
                career_pages.append(
                    VerifiedCareerPage(
                        company_site.companyName,
                        company_site.homepageUrl,
                        career_url,
                        "CAREER_PAGE_FOUND",
                        pagesReviewed=1,
                        dateDiscovered=generated.isoformat(),
                    )
                )
            continue

        career_pages.append(
            VerifiedCareerPage(
                company_site.companyName,
                company_site.homepageUrl,
                None,
                result.status,
                pagesReviewed=1 if result.status != "FAILED" else 0,
                reason=result.reason,
                dateDiscovered=generated.isoformat(),
            )
        )

    output_path = save_career_pages(career_pages, output_dir=output_dir, generated_on=generated)
    _report(progress, f"Career page discovery saved: {output_path}")
    return CareerPagesResult(source_path, output_path, career_pages)


def discover_verified_jobs(
    *,
    career_pages_path: Path | None = None,
    seed_jobs_path: Path | None = None,
    output_dir: Path | None = None,
    limit_pages_per_company: int = 100,
    progress: ProgressCallback | None = None,
    fetcher: HtmlFetcher = fetch_html,
) -> CompanyCareersResult:
    source_path = career_pages_path or latest_career_pages_database_path(output_dir)
    seed_path = seed_jobs_path or latest_daily_database_path(output_dir)
    career_pages = load_career_pages(source_path)
    seed_jobs = load_daily_jobs(seed_path)
    seed_by_company = {job.companyName.casefold(): job for job in _unique_company_seed_jobs(seed_jobs, None)}
    generated = _date_from_stage_path(source_path) or date.today()
    discovered_jobs: list[DailyJobRecord] = []
    review_statuses: list[CompanyReviewStatus] = []
    failed_companies: dict[str, str] = {}

    _report(progress, f"Verified job discovery input: {source_path}")
    for career_page in career_pages:
        if career_page.status != "CAREER_PAGE_FOUND" or not career_page.careerPageUrl:
            review_statuses.append(
                CompanyReviewStatus(career_page.companyName, career_page.status, reason=career_page.reason)
            )
            continue

        seed_job = seed_by_company.get(career_page.companyName.casefold()) or DailyJobRecord(
            companyName=career_page.companyName,
            jobTitle="Software Engineer",
            jobUrl=career_page.homepageUrl,
            applicationUrl=career_page.homepageUrl,
            source="Verified Company Site",
        )
        try:
            scan_result = scan_company_careers(
                seed_job,
                [career_page.careerPageUrl],
                limit_pages=limit_pages_per_company,
                progress=progress,
                fetcher=fetcher,
            )
        except Exception as error:  # noqa: BLE001 - one company must not stop the stage.
            failed_companies[career_page.companyName] = str(error)
            review_statuses.append(CompanyReviewStatus(career_page.companyName, "FAILED", reason=str(error)))
            continue

        discovered_jobs.extend(scan_result.jobs)
        review_statuses.append(
            CompanyReviewStatus(
                career_page.companyName,
                scan_result.status,
                pagesReviewed=scan_result.pages_reviewed,
                jobsFound=len(scan_result.jobs),
                reason=scan_result.reason,
            )
        )

    output_path = merge_and_save_verified_jobs(discovered_jobs, output_dir=output_dir, generated_on=generated)
    _report(progress, f"Verified job discovery saved: {output_path}")
    return CompanyCareersResult(source_path, output_path, list({page.companyName for page in career_pages}), discovered_jobs, failed_companies, review_statuses)


def run_company_careers_discovery(
    *,
    input_path: Path | None = None,
    output_dir: Path | None = None,
    limit_companies: int | None = 100,
    limit_pages_per_company: int = 100,
    allow_domain_guessing: bool = True,
    progress: ProgressCallback | None = None,
    fetcher: HtmlFetcher = fetch_html,
) -> CompanyCareersResult:
    if not allow_domain_guessing:
        _report(progress, "Public homepage search is disabled; downstream company-career stages may produce no matches.")
    company_sites = verify_company_sites(
        input_path=input_path,
        output_dir=output_dir,
        limit_companies=limit_companies,
        use_public_search=allow_domain_guessing,
        progress=progress,
        fetcher=fetcher,
    )
    career_pages = discover_company_career_pages(
        input_path=company_sites.output_path,
        output_dir=output_dir,
        progress=progress,
        fetcher=fetcher,
    )
    return discover_verified_jobs(
        career_pages_path=career_pages.output_path,
        seed_jobs_path=company_sites.input_path,
        output_dir=output_dir,
        limit_pages_per_company=limit_pages_per_company,
        progress=progress,
        fetcher=fetcher,
    )


def scan_company_careers(
    seed_job: DailyJobRecord,
    entry_urls: list[str],
    *,
    limit_pages: int,
    progress: ProgressCallback | None = None,
    fetcher: HtmlFetcher = fetch_html,
) -> CompanyScanResult:
    queue: deque[str] = deque(entry_urls)
    seen: set[str] = set()
    discovered_jobs: list[DailyJobRecord] = []
    allowed_hosts = {_host(url) for url in entry_urls}
    possible_js_pagination = False
    limit_reached = False

    while queue and len(seen) < limit_pages:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        _report(progress, f"{seed_job.companyName}: scanning career page {len(seen)}/{limit_pages}.")

        page_html = fetcher(url)
        form_action_urls = _job_search_form_action_urls(page_html, url)
        possible_js_pagination = possible_js_pagination or (
            _has_possible_js_pagination(page_html) and not form_action_urls
        )
        extracted_jobs = [
            _as_company_careers_job(job, seed_job.companyName)
            for job in extract_json_ld_jobs(page_html, source=f"Company Careers: {seed_job.companyName}", fallback_url=url)
        ]
        for job in extracted_jobs:
            if is_relevant_remote_development_job(job) and _is_similar_to_seed(seed_job, job):
                discovered_jobs.append(job)

        candidate_urls = [
            link.href
            for link in LinkParser.collect(page_html, url)
            if _is_career_link(link.href) or _is_pagination_link(link) or _is_role_category_link(link)
        ]
        candidate_urls.extend(form_action_urls)
        for candidate_url in _dedupe_urls(candidate_urls):
            if len(seen) + len(queue) >= limit_pages:
                limit_reached = True
                break
            if _host(candidate_url) not in allowed_hosts and not _is_known_ats_host(candidate_url):
                continue
            if candidate_url not in seen and candidate_url not in queue:
                queue.append(candidate_url)

    if queue or limit_reached:
        return CompanyScanResult(
            jobs=discovered_jobs,
            pages_reviewed=len(seen),
            status="LIMIT_REACHED",
            reason="The page limit was reached before all discovered career links were reviewed.",
        )

    if possible_js_pagination:
        return CompanyScanResult(
            jobs=discovered_jobs,
            pages_reviewed=len(seen),
            status="POSSIBLE_JS_PAGINATION",
            reason="The page contained load-more, next-page, or pagination markers that may require browser interaction.",
        )

    return CompanyScanResult(jobs=discovered_jobs, pages_reviewed=len(seen), status="FULLY_REVIEWED")


def career_entry_urls(seed_job: DailyJobRecord, *, allow_domain_guessing: bool = False) -> list[str]:
    urls: list[str] = []
    for value in (seed_job.applicationUrl, seed_job.jobUrl):
        if not value:
            continue
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"}:
            continue
        if _is_job_board_host(value):
            continue
        if _is_known_ats_host(value):
            continue
        urls.append(_career_root_url(value))

    return _dedupe_urls(urls)


def discover_career_urls_from_homepage(
    company_name: str,
    *,
    progress: ProgressCallback | None = None,
    fetcher: HtmlFetcher = fetch_html,
) -> HomepageDiscoveryResult:
    attempted_urls = company_homepage_candidates(company_name)
    for homepage_url in attempted_urls:
        try:
            _report(progress, f"{company_name}: checking corporate homepage {homepage_url}.")
            page_html = fetcher(homepage_url)
        except Exception:
            continue

        career_urls = [
            link.href
            for link in LinkParser.collect(page_html, homepage_url)
            if _is_career_link(link.href) or _has_career_link_text(link.text)
        ]
        career_urls = _dedupe_urls(career_urls)
        if career_urls:
            _report(progress, f"{company_name}: found {len(career_urls)} career links on {homepage_url}.")
            return HomepageDiscoveryResult("HOMEPAGE_CAREERS_FOUND", homepage_url, career_urls)

        return HomepageDiscoveryResult(
            "HOMEPAGE_FOUND_NO_CAREER_LINKS",
            homepage_url,
            reason=f"Corporate homepage was found at {homepage_url}, but no career-like links were detected.",
        )

    return HomepageDiscoveryResult(
        "NO_HOMEPAGE",
        reason=f"No corporate homepage could be verified from candidates: {', '.join(attempted_urls)}",
    )


def discover_homepage_from_search(
    company_name: str,
    *,
    progress: ProgressCallback | None = None,
    fetcher: HtmlFetcher = fetch_html,
) -> HomepageDiscoveryResult:
    unverified_homepages: list[str] = []
    for search_url in company_search_urls(company_name):
        try:
            _report(progress, f"{company_name}: searching {_search_url_description(search_url)}.")
            search_html = fetcher(search_url)
        except Exception:
            _report(progress, f"{company_name}: search request failed for {_search_url_description(search_url)}.")
            continue

        homepage_urls: list[str] = []
        reviewed_links = 0
        for link in LinkParser.collect(search_html, search_url):
            url = _unwrap_search_result_url(link.href)
            if not url:
                continue
            reviewed_links += 1
            if _is_probable_official_company_url(company_name, url):
                homepage_urls.append(_homepage_url(url))

        _report(
            progress,
            f"{company_name}: reviewed {reviewed_links} search result links; "
            f"found {len(_dedupe_urls(homepage_urls))} official homepage candidates.",
        )
        for homepage_url in _dedupe_urls(homepage_urls):
            try:
                _report(progress, f"{company_name}: verifying homepage candidate {homepage_url}.")
                fetcher(homepage_url)
            except Exception:
                unverified_homepages.append(homepage_url)
                continue
            _report(progress, f"{company_name}: verified corporate homepage {homepage_url}.")
            return HomepageDiscoveryResult("SEARCH_HOMEPAGE_FOUND", homepage_url=homepage_url)

    if unverified_homepages:
        return HomepageDiscoveryResult(
            "SEARCH_RESULT_UNVERIFIED",
            homepage_url=unverified_homepages[0],
            reason=(
                "Public search found possible official homepage candidates, but the background fetch could not "
                f"verify them: {', '.join(_dedupe_urls(unverified_homepages))}"
            ),
        )

    return HomepageDiscoveryResult("NO_SEARCH_RESULTS", reason="No official company homepage was found in public search results.")


def discover_career_urls_from_verified_homepage(
    company_name: str,
    homepage_url: str,
    *,
    progress: ProgressCallback | None = None,
    fetcher: HtmlFetcher = fetch_html,
) -> HomepageDiscoveryResult:
    try:
        _report(progress, f"{company_name}: scanning verified homepage for careers links.")
        page_html = fetcher(homepage_url)
    except Exception as error:
        return HomepageDiscoveryResult("FAILED", homepage_url=homepage_url, reason=str(error))

    career_urls = [
        link.href
        for link in LinkParser.collect(page_html, homepage_url)
        if _is_career_link(link.href) or _has_career_link_text(link.text)
    ]
    career_urls = _dedupe_urls(career_urls)
    if career_urls:
        _report(progress, f"{company_name}: found {len(career_urls)} career links on verified homepage.")
        return HomepageDiscoveryResult("HOMEPAGE_CAREERS_FOUND", homepage_url, career_urls)

    return HomepageDiscoveryResult(
        "HOMEPAGE_FOUND_NO_CAREER_LINKS",
        homepage_url,
        reason=f"Corporate homepage was verified at {homepage_url}, but no career-like links were detected.",
    )


def company_search_urls(company_name: str) -> list[str]:
    queries = [company_name, f"{company_name} official site", f"{company_name} company"]
    return ["https://www.bing.com/search?" + urlencode({"q": query}) for query in queries]


def company_homepage_candidates(company_name: str) -> list[str]:
    slug = _company_slug(company_name)
    if not slug:
        return []
    urls: list[str] = []
    for tld in HOMEPAGE_TLDS:
        urls.append(f"https://{slug}.{tld}")
        urls.append(f"https://www.{slug}.{tld}")
    return urls


def save_company_sites(
    company_sites: list[VerifiedCompanySite],
    *,
    output_dir: Path | None = None,
    generated_on: date | None = None,
) -> Path:
    generated = generated_on or date.today()
    output_path = company_sites_database_path(output_dir=output_dir, generated_on=generated)
    existing = load_company_sites(output_path)
    merged = _merge_company_sites(existing + company_sites)
    payload = {
        "generatedDate": generated.isoformat(),
        "companies": [site.to_json_dict(generated) for site in merged],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def load_company_sites(path: Path) -> list[VerifiedCompanySite]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("companies", [])
    if not isinstance(records, list):
        raise ValueError(f"Expected 'companies' to be a list in {path}")
    return [_company_site_from_json(item) for item in records if isinstance(item, dict)]


def save_career_pages(
    career_pages: list[VerifiedCareerPage],
    *,
    output_dir: Path | None = None,
    generated_on: date | None = None,
) -> Path:
    generated = generated_on or date.today()
    output_path = career_pages_database_path(output_dir=output_dir, generated_on=generated)
    existing = load_career_pages(output_path)
    merged = _merge_career_pages(existing + career_pages)
    payload = {
        "generatedDate": generated.isoformat(),
        "careerPages": [page.to_json_dict(generated) for page in merged],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def load_career_pages(path: Path) -> list[VerifiedCareerPage]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("careerPages", [])
    if not isinstance(records, list):
        raise ValueError(f"Expected 'careerPages' to be a list in {path}")
    return [_career_page_from_json(item) for item in records if isinstance(item, dict)]


def _company_site_record(
    seed_job: DailyJobRecord,
    homepage_url: str | None,
    status: str,
    reason: str | None,
    generated_on: date,
) -> VerifiedCompanySite:
    return VerifiedCompanySite(
        companyName=seed_job.companyName,
        homepageUrl=homepage_url,
        status=status,
        sourceSeed=seed_job.normalized(generated_on).to_json_dict(),
        reason=reason,
        dateVerified=generated_on.isoformat(),
    )


def _merge_company_sites(company_sites: list[VerifiedCompanySite]) -> list[VerifiedCompanySite]:
    merged: dict[str, VerifiedCompanySite] = {}
    for company_site in company_sites:
        key = company_site.companyName.casefold()
        existing = merged.get(key)
        if existing is None or _company_site_score(company_site) >= _company_site_score(existing):
            merged[key] = company_site
    return sorted(merged.values(), key=lambda item: item.companyName.lower())


def _merge_career_pages(career_pages: list[VerifiedCareerPage]) -> list[VerifiedCareerPage]:
    merged: dict[tuple[str, str], VerifiedCareerPage] = {}
    for career_page in career_pages:
        key = (career_page.companyName.casefold(), career_page.careerPageUrl or career_page.status)
        existing = merged.get(key)
        if existing is None or _career_page_score(career_page) >= _career_page_score(existing):
            merged[key] = career_page
    return sorted(merged.values(), key=lambda item: (item.companyName.lower(), item.careerPageUrl or ""))


def _company_site_score(company_site: VerifiedCompanySite) -> int:
    scores = {"VERIFIED": 4, "MANUAL_VERIFICATION": 3, "SEARCH_RESULT_UNVERIFIED": 2}
    return scores.get(company_site.status, 1)


def _career_page_score(career_page: VerifiedCareerPage) -> int:
    scores = {"CAREER_PAGE_FOUND": 4, "HOMEPAGE_CAREERS_FOUND": 3, "POSSIBLE_JS_PAGINATION": 2}
    return scores.get(career_page.status, 1)


def _company_site_from_json(item: dict[str, object]) -> VerifiedCompanySite:
    source_seed = item.get("sourceSeed")
    return VerifiedCompanySite(
        companyName=str(item.get("companyName") or ""),
        sourceSeed=source_seed if isinstance(source_seed, dict) else {},
        homepageUrl=_optional_string(item.get("homepageUrl")),
        status=str(item.get("status") or "FAILED"),
        reason=_optional_string(item.get("reason")),
        dateVerified=_optional_string(item.get("dateVerified")),
    )


def _career_page_from_json(item: dict[str, object]) -> VerifiedCareerPage:
    return VerifiedCareerPage(
        companyName=str(item.get("companyName") or ""),
        homepageUrl=str(item.get("homepageUrl") or ""),
        careerPageUrl=_optional_string(item.get("careerPageUrl")),
        status=str(item.get("status") or "FAILED"),
        pagesReviewed=_int_or_default(item.get("pagesReviewed"), 0),
        reason=_optional_string(item.get("reason")),
        dateDiscovered=_optional_string(item.get("dateDiscovered")),
    )


def _unique_company_seed_jobs(jobs: list[DailyJobRecord], limit: int | None) -> list[DailyJobRecord]:
    seeds: dict[str, DailyJobRecord] = {}
    for job in jobs:
        key = job.companyName.casefold()
        existing = seeds.get(key)
        if existing is None or job.rank > existing.rank:
            seeds[key] = job
    values = sorted(seeds.values(), key=lambda item: (-item.rank, item.companyName.lower()))
    return values[:limit] if limit is not None else values


def _as_company_careers_job(job: DailyJobRecord, company_name: str) -> DailyJobRecord:
    return DailyJobRecord(
        companyName=job.companyName or company_name,
        jobTitle=job.jobTitle,
        jobUrl=job.jobUrl,
        applicationUrl=job.applicationUrl,
        source=f"Company Careers: {company_name}",
        location=job.location,
        remote=job.remote,
        salary=job.salary,
        datePosted=job.datePosted,
        workMode=job.workMode,
        workModeEvidence=job.workModeEvidence,
        classification=job.classification,
        matchedSkills=job.matchedSkills,
        excludedSkillsFound=job.excludedSkillsFound,
        exclusionReason=job.exclusionReason,
        rank=job.rank,
        rankEvidence=job.rankEvidence,
    ).normalized()


def _is_similar_to_seed(seed_job: DailyJobRecord, candidate: DailyJobRecord) -> bool:
    if seed_job.companyName.casefold() != candidate.companyName.casefold():
        return False

    seed_skills = set(seed_job.matchedSkills) | set(seed_job.rankEvidence)
    candidate_skills = set(candidate.matchedSkills) | set(candidate.rankEvidence)
    if seed_skills and candidate_skills and seed_skills.intersection(candidate_skills):
        return True

    seed_title_terms = _title_terms(seed_job.jobTitle)
    candidate_title_terms = _title_terms(candidate.jobTitle)
    return bool(seed_title_terms.intersection(candidate_title_terms))


def _title_terms(value: str) -> set[str]:
    ignored = {"senior", "staff", "principal", "software", "engineer", "developer"}
    return {term for term in re.findall(r"[a-z0-9+#.]+", value.lower()) if len(term) > 2 and term not in ignored}


def _is_career_link(url: str) -> bool:
    text = url.lower()
    return any(marker in text for marker in ("/job", "/jobs", "/career", "/careers", "/position", "/opening"))


def _is_pagination_link(link) -> bool:
    href = link.href.lower()
    text = link.text.strip().lower()
    if text in {"next", ">", "»"} or "next page" in text:
        return True
    return any(marker in href for marker in ("?page=", "&page=", "?p=", "&p=", "/page/"))


def _job_search_form_action_urls(page_html: str, base_url: str) -> list[str]:
    urls: list[str] = []
    for match in re.finditer(r"<form\b(?P<attrs>[^>]*)>(?P<body>.*?)</form>", page_html, flags=re.IGNORECASE | re.DOTALL):
        attrs = match.group("attrs")
        body = match.group("body")
        text = re.sub(r"<[^>]+>", " ", body).lower()
        if not any(marker in text for marker in ("search jobs", "find jobs", "job openings", "open positions", "search openings")):
            continue
        action_match = re.search(r"action=[\"'](?P<action>[^\"']*)[\"']", attrs, flags=re.IGNORECASE)
        if not action_match:
            continue
        action = action_match.group("action").strip()
        urls.append(urljoin(base_url, action or "."))
    return _dedupe_urls(urls)


def _has_career_link_text(value: str) -> bool:
    text = value.lower()
    return any(marker in text for marker in CAREER_LINK_TEXT_MARKERS)


def _is_role_category_link(link) -> bool:
    text = f"{link.text} {link.href}".lower().replace("-", " ")
    return any(marker in text for marker in ROLE_CATEGORY_LINK_MARKERS)


def _unwrap_search_result_url(url: str) -> str | None:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "uddg" in query:
        return query["uddg"][0]
    if parsed.netloc.endswith("bing.com") and "u" in query:
        return _decode_bing_redirect_url(query["u"][0])
    if parsed.scheme in {"http", "https"}:
        return url
    return None


def _decode_bing_redirect_url(value: str) -> str | None:
    encoded = value[2:] if value.startswith("a1") else value
    padding = "=" * (-len(encoded) % 4)
    try:
        decoded = base64.urlsafe_b64decode(encoded + padding).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    return decoded if decoded.startswith(("http://", "https://")) else None


def _homepage_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _search_url_description(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query).get("q", [""])[0]
    return f"{parsed.netloc} query \"{query}\""


def _is_probable_official_company_url(company_name: str, url: str) -> bool:
    host = _host(url)
    slug = _company_slug(company_name)
    if not slug or any(marker in host for marker in SEARCH_RESULT_EXCLUDED_HOST_MARKERS):
        return False
    compact_host = re.sub(r"[^a-z0-9]+", "", host)
    if slug in compact_host or compact_host in slug:
        return True

    return any(token in compact_host for token in _company_match_tokens(company_name))


def _company_match_tokens(company_name: str) -> tuple[str, ...]:
    ignored = {
        "and",
        "company",
        "corporation",
        "corp",
        "inc",
        "insurance",
        "llc",
        "ltd",
        "the",
    }
    tokens = [token for token in re.findall(r"[a-z0-9]+", company_name.lower()) if token not in ignored]
    return tuple(token for token in tokens if len(token) >= 5)


def _has_possible_js_pagination(page_html: str) -> bool:
    text = page_html[:50000].lower()
    markers = (
        "load more",
        "show more",
        "view more",
        "next page",
        "aria-label=\"next",
        "data-next",
        "infinite scroll",
        "pagination",
        "search jobs",
        "find jobs",
    )
    return any(marker in text for marker in markers)


def _career_root_url(url: str) -> str:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if _is_known_ats_host(url):
        return url
    return urljoin(base, "/careers")


def _company_slug(company_name: str) -> str:
    value = company_name.lower()
    value = re.sub(r"\b(inc|llc|ltd|corp|corporation|company|co)\b", "", value)
    return re.sub(r"[^a-z0-9]+", "", value)


def _date_from_stage_path(path: Path) -> date | None:
    match = re.search(r"-(\d{4}-\d{2}-\d{2})\.json$", path.name)
    if not match:
        return None

    return date.fromisoformat(match.group(1))


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_or_default(value: object, default: int) -> int:
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _is_job_board_host(url: str) -> bool:
    host = _host(url)
    return any(marker in host for marker in JOB_BOARD_HOST_MARKERS)


def _is_known_ats_host(url: str) -> bool:
    host = _host(url)
    return any(marker in host for marker in ATS_HOST_MARKERS)


def _host(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _dedupe_urls(urls: list[str]) -> list[str]:
    deduped: list[str] = []
    for url in urls:
        if url not in deduped:
            deduped.append(url)
    return deduped


def _report(progress: ProgressCallback | None, message: str) -> None:
    if progress is not None:
        progress(message)
