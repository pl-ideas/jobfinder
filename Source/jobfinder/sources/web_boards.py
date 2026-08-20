from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from jobfinder.daily_jobs import DailyJobRecord, classify_work_mode, is_relevant_remote_development_job
from jobfinder.job_ranking import RankingProfile, load_default_ranking_profile, rank_job_text
from jobfinder.skill_matching import SkillProfile, evaluate_job_skills, load_default_skill_profile


SEARCH_TERMS = (
    "Software Engineer",
    "Full Stack Developer",
    "Full Stack Engineer",
    ".NET Developer",
    ".NET Software Engineer",
    "C# Developer",
)

ProgressCallback = Callable[[str], None]


@dataclass(frozen=True)
class SourceScanResult:
    source: str
    jobs: list[DailyJobRecord] = field(default_factory=list)
    authentication_required: bool = False
    failed_reason: str | None = None


class PublicJobBoardSource:
    display_name: str
    login_gated: bool = False

    def scan(self, *, limit_per_query: int = 100, progress: ProgressCallback | None = None) -> SourceScanResult:
        jobs: list[DailyJobRecord] = []
        seen_urls: set[str] = set()
        skill_profile = load_default_skill_profile()
        ranking_profile = load_default_ranking_profile()

        for term in SEARCH_TERMS:
            search_url = self.search_url(term)
            _report(progress, f"{self.display_name}: searching \"{term}\" remote jobs.")
            try:
                search_html = fetch_html(search_url)
            except FetchAuthenticationRequired:
                return SourceScanResult(self.display_name, jobs, authentication_required=True)
            except FetchError as error:
                _report(progress, f"{self.display_name}: failed while searching \"{term}\": {error}")
                return SourceScanResult(self.display_name, jobs, failed_reason=str(error))

            if self.requires_authentication(search_html):
                return SourceScanResult(self.display_name, jobs, authentication_required=True)

            detail_urls = self.extract_detail_urls(search_html, search_url)[:limit_per_query]
            total_detail_urls = len(detail_urls)
            _report(
                progress,
                f"{self.display_name}: found {total_detail_urls} candidate listing URLs for \"{term}\".",
            )
            for reviewed_count, detail_url in enumerate(detail_urls, start=1):
                if detail_url in seen_urls:
                    continue
                seen_urls.add(detail_url)
                try:
                    detail_html = fetch_html(detail_url)
                except (FetchError, FetchAuthenticationRequired):
                    _report(
                        progress,
                        f"{self.display_name}: reviewed {reviewed_count}/{total_detail_urls} detail pages for "
                        f"\"{term}\"; skipped an inaccessible listing.",
                    )
                    continue

                extracted_jobs = self.extract_jobs(detail_html, detail_url, skill_profile, ranking_profile)
                jobs.extend(extracted_jobs)
                _report(
                    progress,
                    f"{self.display_name}: reviewed {reviewed_count}/{total_detail_urls} detail pages for "
                    f"\"{term}\"; {len(jobs)} extracted jobs so far.",
                )

        relevant_jobs = [job for job in jobs if is_relevant_remote_development_job(job)]
        _report(
            progress,
            f"{self.display_name}: kept {len(relevant_jobs)} relevant remote development jobs "
            f"from {len(jobs)} extracted jobs.",
        )
        return SourceScanResult(self.display_name, relevant_jobs)

    def search_url(self, term: str) -> str:
        raise NotImplementedError

    def extract_detail_urls(self, page_html: str, base_url: str) -> list[str]:
        links = LinkParser.collect(page_html, base_url)
        detail_urls: list[str] = []
        for link in links:
            parsed = urlparse(link.href)
            if parsed.scheme not in {"http", "https"}:
                continue
            if not self.is_probable_job_url(link.href):
                continue
            if link.href not in detail_urls:
                detail_urls.append(link.href)
        return detail_urls

    def extract_jobs(
        self,
        page_html: str,
        page_url: str,
        skill_profile: SkillProfile,
        ranking_profile: RankingProfile,
    ) -> list[DailyJobRecord]:
        jobs = extract_json_ld_jobs(
            page_html,
            source=self.display_name,
            fallback_url=page_url,
            skill_profile=skill_profile,
            ranking_profile=ranking_profile,
        )
        if jobs:
            return [job.normalized() for job in jobs]

        title = extract_meta_content(page_html, ("og:title", "twitter:title"))
        company = extract_meta_content(page_html, ("author",))
        if title and company:
            description = html_to_text(page_html[:50000])
            work_mode, work_mode_evidence = classify_work_mode(description)
            match_text = _job_match_text(title, company, extract_location_text(page_html), description)
            skill_match = evaluate_job_skills(match_text, skill_profile)
            rank_result = rank_job_text(match_text, ranking_profile)
            return [
                DailyJobRecord(
                    companyName=company,
                    jobTitle=clean_title(title),
                    jobUrl=page_url,
                    applicationUrl=extract_application_url(page_html, page_url, self.display_name),
                    source=self.display_name,
                    location=extract_location_text(page_html),
                    remote=True if work_mode == "remote" else False if work_mode in {"hybrid", "onsite"} else None,
                    workMode=work_mode,
                    workModeEvidence=work_mode_evidence,
                    classification=skill_match.classification,
                    matchedSkills=skill_match.matched_skills,
                    excludedSkillsFound=skill_match.excluded_skills_found,
                    exclusionReason=skill_match.exclusion_reason,
                    rank=rank_result.rank,
                    rankEvidence=rank_result.evidence,
                ).normalized()
            ]
        return []

    def is_probable_job_url(self, url: str) -> bool:
        return any(marker in url.lower() for marker in ("/job", "/jobs", "viewjob", "jk="))

    def requires_authentication(self, page_html: str) -> bool:
        text = page_html[:20000].lower()
        auth_markers = (
            "sign in to view",
            "login to view",
            "log in to view",
            "please sign in",
            "authentication required",
        )
        return any(marker in text for marker in auth_markers)


class BuiltInSource(PublicJobBoardSource):
    display_name = "Built In"

    def search_url(self, term: str) -> str:
        return "https://builtin.com/jobs/remote/dev-engineering?" + urlencode({"search": term})

    def is_probable_job_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return "builtin.com" in parsed.netloc and "/job/" in parsed.path


class DiceSource(PublicJobBoardSource):
    display_name = "Dice"

    def search_url(self, term: str) -> str:
        return "https://www.dice.com/jobs?" + urlencode({"q": term, "location": "Remote"})

    def is_probable_job_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return "dice.com" in parsed.netloc and ("/job-detail/" in parsed.path or "/jobs/detail/" in parsed.path)


class IndeedSource(PublicJobBoardSource):
    display_name = "Indeed"

    def search_url(self, term: str) -> str:
        return "https://www.indeed.com/jobs?" + urlencode({"q": term, "l": "Remote"})

    def is_probable_job_url(self, url: str) -> bool:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        return "indeed.com" in parsed.netloc and ("/viewjob" in parsed.path or "jk" in query)


class LinkedInJobsSource(PublicJobBoardSource):
    display_name = "LinkedIn Jobs"
    login_gated = True

    def search_url(self, term: str) -> str:
        return "https://www.linkedin.com/jobs/search/?" + urlencode({"keywords": term, "location": "Remote"})

    def is_probable_job_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return "linkedin.com" in parsed.netloc and "/jobs/view/" in parsed.path

    def requires_authentication(self, page_html: str) -> bool:
        text = page_html[:30000].lower()
        return super().requires_authentication(page_html) or "join linkedin" in text or "authwall" in text


class WellfoundSource(PublicJobBoardSource):
    display_name = "Wellfound"
    login_gated = True

    def search_url(self, term: str) -> str:
        return "https://wellfound.com/jobs?" + urlencode({"remote": "true", "keyword": term})

    def is_probable_job_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return "wellfound.com" in parsed.netloc and "/jobs/" in parsed.path

    def requires_authentication(self, page_html: str) -> bool:
        text = page_html[:30000].lower()
        return super().requires_authentication(page_html) or "sign up to apply" in text or "continue with google" in text


class FetchError(RuntimeError):
    pass


class FetchAuthenticationRequired(RuntimeError):
    pass


def fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; JobFinder/0.1; +https://local.invalid/jobfinder)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as error:
        if error.code in {401, 403}:
            raise FetchAuthenticationRequired(f"Authentication required for {url}") from error
        raise FetchError(f"HTTP {error.code} while fetching {url}") from error
    except URLError as error:
        raise FetchError(f"Could not fetch {url}: {error.reason}") from error


def _report(progress: ProgressCallback | None, message: str) -> None:
    if progress is not None:
        progress(message)


def extract_json_ld_jobs(
    page_html: str,
    *,
    source: str,
    fallback_url: str,
    skill_profile: SkillProfile | None = None,
    ranking_profile: RankingProfile | None = None,
) -> list[DailyJobRecord]:
    jobs: list[DailyJobRecord] = []
    profile = skill_profile or load_default_skill_profile()
    rank_profile = ranking_profile or load_default_ranking_profile()
    for raw_json in JsonLdParser.collect(page_html):
        for item in _flatten_json_ld(raw_json):
            if item.get("@type") != "JobPosting":
                continue
            company = _json_ld_company(item)
            title = _string_value(item.get("title"))
            if not company or not title:
                continue
            job_url = _string_value(item.get("url")) or fallback_url
            description = html_to_text(_string_value(item.get("description")) or "")
            metadata_remote = _json_ld_remote(item) is True
            location = _json_ld_location(item)
            match_text = _job_match_text(title, company, location, description)
            skill_match = evaluate_job_skills(match_text, profile)
            rank_result = rank_job_text(match_text, rank_profile)
            work_mode, work_mode_evidence = classify_work_mode(
                description,
                metadata_remote=metadata_remote,
                metadata_evidence="Structured metadata indicates remote or telecommute work.",
            )
            jobs.append(
                DailyJobRecord(
                    companyName=company,
                    jobTitle=title,
                    jobUrl=urljoin(fallback_url, job_url),
                    applicationUrl=extract_application_url(page_html, fallback_url, source),
                    source=source,
                    location=location,
                    remote=True if work_mode == "remote" else False if work_mode in {"hybrid", "onsite"} else metadata_remote,
                    salary=_json_ld_salary(item),
                    datePosted=_string_value(item.get("datePosted")),
                    workMode=work_mode,
                    workModeEvidence=work_mode_evidence,
                    classification=skill_match.classification,
                    matchedSkills=skill_match.matched_skills,
                    excludedSkillsFound=skill_match.excluded_skills_found,
                    exclusionReason=skill_match.exclusion_reason,
                    rank=rank_result.rank,
                    rankEvidence=rank_result.evidence,
                ).normalized()
            )
    return jobs


def extract_application_url(page_html: str, page_url: str, source: str) -> str:
    links = LinkParser.collect(page_html, page_url)
    source_host = _source_host(source)
    candidates: list[str] = []
    for link in links:
        label = f"{link.text} {link.href}".lower()
        if not any(marker in label for marker in ("apply", "application", "greenhouse", "lever", "workday", "ashbyhq")):
            continue
        if source_host and source_host in urlparse(link.href).netloc.lower() and "apply" not in label:
            continue
        candidates.append(link.href)

    return candidates[0] if candidates else page_url


def extract_meta_content(page_html: str, names: tuple[str, ...]) -> str | None:
    for name in names:
        pattern = rf'<meta[^>]+(?:property|name)=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']'
        match = re.search(pattern, page_html, flags=re.IGNORECASE)
        if match:
            return html.unescape(match.group(1)).strip()
    return None


def extract_location_text(page_html: str) -> str | None:
    match = re.search(r"\b(Remote(?:\s*[-,]\s*[A-Za-z ]+)?)\b", page_html, flags=re.IGNORECASE)
    if not match:
        return None
    return html.unescape(match.group(1)).strip()


def clean_title(value: str) -> str:
    title = html.unescape(value)
    for separator in (" | ", " - "):
        if separator in title:
            title = title.split(separator, 1)[0]
    return " ".join(title.split())


def html_to_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(without_tags).split())


def _job_match_text(title: str, company: str, location: str | None, description: str) -> str:
    return " ".join(part for part in [title, company, location or "", description] if part)


@dataclass(frozen=True)
class Link:
    href: str
    text: str


class LinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[Link] = []
        self._href: str | None = None
        self._text: list[str] = []

    @classmethod
    def collect(cls, page_html: str, base_url: str) -> list[Link]:
        parser = cls(base_url)
        parser.feed(page_html)
        return parser.links

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href:
            self._href = urljoin(self.base_url, html.unescape(href))
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href:
            self.links.append(Link(self._href, " ".join(" ".join(self._text).split())))
            self._href = None
            self._text = []


class JsonLdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[dict[str, object]] = []
        self._collecting = False
        self._buffer: list[str] = []

    @classmethod
    def collect(cls, page_html: str) -> list[dict[str, object]]:
        parser = cls()
        parser.feed(page_html)
        return parser.items

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "script":
            return
        attrs_dict = dict(attrs)
        if attrs_dict.get("type") == "application/ld+json":
            self._collecting = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._collecting:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "script" or not self._collecting:
            return
        self._collecting = False
        raw = "".join(self._buffer).strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return
        if isinstance(payload, dict):
            self.items.append(payload)
        elif isinstance(payload, list):
            self.items.extend(item for item in payload if isinstance(item, dict))


def _flatten_json_ld(item: dict[str, object]) -> list[dict[str, object]]:
    graph = item.get("@graph")
    if isinstance(graph, list):
        return [entry for entry in graph if isinstance(entry, dict)]
    return [item]


def _json_ld_company(item: dict[str, object]) -> str | None:
    organization = item.get("hiringOrganization")
    if isinstance(organization, dict):
        return _string_value(organization.get("name"))
    return _string_value(organization)


def _json_ld_location(item: dict[str, object]) -> str | None:
    location = item.get("jobLocation")
    if isinstance(location, list):
        values = [_json_ld_location({"jobLocation": entry}) for entry in location]
        return "; ".join(value for value in values if value) or None
    if isinstance(location, dict):
        address = location.get("address")
        if isinstance(address, dict):
            parts = [
                _string_value(address.get("addressLocality")),
                _string_value(address.get("addressRegion")),
                _string_value(address.get("addressCountry")),
            ]
            return ", ".join(part for part in parts if part) or None
    applicant_location = item.get("applicantLocationRequirements")
    if applicant_location:
        return "Remote"
    return None


def _json_ld_remote(item: dict[str, object]) -> bool | None:
    value = _string_value(item.get("jobLocationType"))
    if value and "telecommute" in value.lower():
        return True
    location = _json_ld_location(item)
    if location and "remote" in location.lower():
        return True
    return None


def _json_ld_salary(item: dict[str, object]) -> str | None:
    salary = item.get("baseSalary")
    if not isinstance(salary, dict):
        return None
    value = salary.get("value")
    currency = _string_value(salary.get("currency")) or ""
    if isinstance(value, dict):
        min_value = _string_value(value.get("minValue"))
        max_value = _string_value(value.get("maxValue"))
        unit = _string_value(value.get("unitText")) or ""
        if min_value and max_value:
            return " ".join(part for part in [currency, f"{min_value} - {max_value}", unit] if part)
    return None


def _string_value(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _source_host(source: str) -> str:
    hosts = {
        "Built In": "builtin.com",
        "Dice": "dice.com",
        "Indeed": "indeed.com",
        "LinkedIn Jobs": "linkedin.com",
        "Wellfound": "wellfound.com",
    }
    return hosts.get(source, "")
