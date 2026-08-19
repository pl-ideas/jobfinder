from __future__ import annotations

import re
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from jobfinder.daily_jobs import DailyJobRecord, is_relevant_remote_development_job
from jobfinder.daily_storage import default_project_root, load_daily_jobs, merge_and_save_verified_jobs
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


def latest_daily_database_path(output_dir: Path | None = None) -> Path:
    directory = output_dir or default_project_root() / "Job Database"
    files = sorted(directory.glob("jobs-*.json"), reverse=True)
    if not files:
        raise FileNotFoundError(f"No daily job database files found in {directory}")
    return files[0]


def run_company_careers_discovery(
    *,
    input_path: Path | None = None,
    output_dir: Path | None = None,
    limit_companies: int | None = None,
    limit_pages_per_company: int = 25,
    allow_domain_guessing: bool = True,
    progress: ProgressCallback | None = None,
    fetcher: HtmlFetcher = fetch_html,
) -> CompanyCareersResult:
    source_path = input_path or latest_daily_database_path(output_dir)
    seed_jobs = load_daily_jobs(source_path)
    companies_reviewed: list[str] = []
    failed_companies: dict[str, str] = {}
    discovered_jobs: list[DailyJobRecord] = []
    review_statuses: list[CompanyReviewStatus] = []

    _report(progress, f"Company careers discovery input: {source_path}")
    for seed_job in _unique_company_seed_jobs(seed_jobs, limit_companies):
        companies_reviewed.append(seed_job.companyName)
        employer_reason = employer_exclusion_reason(seed_job.companyName)
        if employer_reason:
            review_statuses.append(CompanyReviewStatus(seed_job.companyName, "EXCLUDED_EMPLOYER", reason=employer_reason))
            _report(progress, f"{seed_job.companyName}: excluded employer; {employer_reason}")
            continue

        _report(progress, f"{seed_job.companyName}: locating corporate career pages.")
        entry_urls = career_entry_urls(seed_job, allow_domain_guessing=allow_domain_guessing)
        if not entry_urls:
            if allow_domain_guessing:
                search_result = discover_career_urls_from_search(seed_job.companyName, progress=progress, fetcher=fetcher)
                if search_result.career_urls:
                    entry_urls = search_result.career_urls

            if not entry_urls and allow_domain_guessing:
                homepage_result = discover_career_urls_from_homepage(seed_job.companyName, progress=progress, fetcher=fetcher)
                if homepage_result.career_urls:
                    entry_urls = homepage_result.career_urls
                else:
                    status = homepage_result.status
                    reason = homepage_result.reason or "No corporate careers URL could be derived from the company homepage."
                    if is_acceptable_recruiting_agency(seed_job.companyName):
                        status = "MANUAL_VERIFICATION"
                        reason = (
                            "Acceptable recruiting agency; no corporate careers URL was found, "
                            "so manual verification is recommended."
                        )
                    review_statuses.append(CompanyReviewStatus(seed_job.companyName, status, reason=reason))
                    _report(progress, f"{seed_job.companyName}: {status}; {reason}")
                    continue

        if not entry_urls:
            reason = "No corporate or ATS career URL could be derived."
            if is_acceptable_recruiting_agency(seed_job.companyName):
                reason = "Acceptable recruiting agency; no careers URL was derived, so manual verification is recommended."
                review_statuses.append(CompanyReviewStatus(seed_job.companyName, "MANUAL_VERIFICATION", reason=reason))
                _report(progress, f"{seed_job.companyName}: manual verification recommended; {reason}")
                continue
            failed_companies[seed_job.companyName] = reason
            review_statuses.append(CompanyReviewStatus(seed_job.companyName, "NO_ENTRY_URL", reason=reason))
            _report(progress, f"{seed_job.companyName}: no corporate or ATS career URL derived.")
            continue

        try:
            company_result = scan_company_careers(
                seed_job,
                entry_urls,
                limit_pages=limit_pages_per_company,
                progress=progress,
                fetcher=fetcher,
            )
        except Exception as error:  # noqa: BLE001 - one company must not stop the whole company-careers job.
            failed_companies[seed_job.companyName] = str(error)
            review_statuses.append(CompanyReviewStatus(seed_job.companyName, "FAILED", reason=str(error)))
            _report(progress, f"{seed_job.companyName}: failed: {error}")
            continue

        company_jobs = company_result.jobs
        review_statuses.append(
            CompanyReviewStatus(
                seed_job.companyName,
                company_result.status,
                pagesReviewed=company_result.pages_reviewed,
                jobsFound=len(company_jobs),
                reason=company_result.reason,
            )
        )
        _report(
            progress,
            f"{seed_job.companyName}: {company_result.status}; reviewed {company_result.pages_reviewed} pages; "
            f"found {len(company_jobs)} matching corporate jobs.",
        )
        discovered_jobs.extend(company_jobs)

    output_path = merge_and_save_verified_jobs(
        discovered_jobs,
        output_dir=output_dir,
        generated_on=_date_from_daily_path(source_path),
    )
    _report(progress, f"Company careers discovery saved: {output_path}")

    return CompanyCareersResult(
        input_path=source_path,
        output_path=output_path,
        companies_reviewed=companies_reviewed,
        jobs_added=discovered_jobs,
        failed_companies=failed_companies,
        review_statuses=review_statuses,
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


def discover_career_urls_from_search(
    company_name: str,
    *,
    progress: ProgressCallback | None = None,
    fetcher: HtmlFetcher = fetch_html,
) -> HomepageDiscoveryResult:
    for search_url in company_search_urls(company_name):
        try:
            _report(progress, f"{company_name}: searching public web for careers page.")
            search_html = fetcher(search_url)
        except Exception:
            continue

        career_urls = [
            url
            for link in LinkParser.collect(search_html, search_url)
            if (url := _unwrap_search_result_url(link.href))
            and _is_probable_official_company_url(company_name, url)
            and (_is_career_link(url) or _has_career_link_text(link.text))
        ]
        career_urls = _dedupe_urls(career_urls)
        if career_urls:
            _report(progress, f"{company_name}: found {len(career_urls)} career links from public search.")
            return HomepageDiscoveryResult("SEARCH_CAREERS_FOUND", search_url, career_urls)

    return HomepageDiscoveryResult("NO_SEARCH_RESULTS", reason="No official company career links were found in public search results.")


def company_search_urls(company_name: str) -> list[str]:
    queries = [f"{company_name} careers", f"{company_name} jobs", f"{company_name} open positions"]
    return ["https://duckduckgo.com/html/?" + urlencode({"q": query}) for query in queries]


def company_homepage_candidates(company_name: str) -> list[str]:
    slug = _company_slug(company_name)
    if not slug:
        return []
    urls: list[str] = []
    for tld in HOMEPAGE_TLDS:
        urls.append(f"https://{slug}.{tld}")
        urls.append(f"https://www.{slug}.{tld}")
    return urls


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
    if parsed.scheme in {"http", "https"}:
        return url
    return None


def _is_probable_official_company_url(company_name: str, url: str) -> bool:
    host = _host(url)
    slug = _company_slug(company_name)
    if not slug or any(marker in host for marker in SEARCH_RESULT_EXCLUDED_HOST_MARKERS):
        return False
    compact_host = re.sub(r"[^a-z0-9]+", "", host)
    return slug in compact_host or compact_host in slug


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


def _date_from_daily_path(path: Path):
    match = re.search(r"jobs-(\d{4}-\d{2}-\d{2})\.json$", path.name)
    if not match:
        return None
    from datetime import date

    return date.fromisoformat(match.group(1))


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
