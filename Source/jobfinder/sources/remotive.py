from __future__ import annotations

import html
import json
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from jobfinder.models import JobPosting, RemoteStatus


class RemotiveSource:
    name = "remotive"
    endpoint = "https://remotive.com/api/remote-jobs"

    def fetch(self, query: str | None = None, limit: int | None = None) -> list[JobPosting]:
        params = {}
        if query:
            params["search"] = query

        url = self.endpoint
        if params:
            url = f"{url}?{urlencode(params)}"

        request = Request(url, headers={"User-Agent": "JobFinder/0.1"})
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))

        jobs = [self._normalize(item) for item in payload.get("jobs", [])]
        if limit is not None:
            return jobs[:limit]
        return jobs

    def _normalize(self, item: dict) -> JobPosting:
        salary_min, salary_max = _parse_salary(item.get("salary", ""))
        return JobPosting(
            title=str(item.get("title") or "").strip(),
            company=str(item.get("company_name") or "").strip(),
            location=str(item.get("candidate_required_location") or "Remote").strip(),
            source_name=self.name,
            source_url=str(item.get("url") or "").strip(),
            description=_clean_description(str(item.get("description") or "")),
            remote_status=RemoteStatus.REMOTE,
            salary_min=salary_min,
            salary_max=salary_max,
            tags=tuple(str(tag).strip() for tag in item.get("tags", []) if str(tag).strip()),
        )


def _clean_description(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(without_tags).split())


def _parse_salary(value: str) -> tuple[int | None, int | None]:
    if not value:
        return None, None

    numbers = []
    for match in re.finditer(r"\$?\s*([0-9]{2,3}(?:,[0-9]{3})?)(k)?", value, re.IGNORECASE):
        amount = int(match.group(1).replace(",", ""))
        if match.group(2):
            amount *= 1000
        numbers.append(amount)

    if not numbers:
        return None, None

    return min(numbers), max(numbers)
