from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from jobfinder.skill_matching import default_documentation_dir


@dataclass(frozen=True)
class RankingProfile:
    primary_skills: tuple[str, ...] = field(default_factory=tuple)
    secondary_skills: tuple[str, ...] = field(default_factory=tuple)
    specialized_skills: tuple[str, ...] = field(default_factory=tuple)
    resume_terms: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class JobRankResult:
    rank: int
    evidence: tuple[str, ...] = field(default_factory=tuple)


def load_default_ranking_profile(documentation_dir: Path | None = None) -> RankingProfile:
    docs_dir = documentation_dir or default_documentation_dir()
    skills_markdown = (docs_dir / "current-skills.md").read_text(encoding="utf-8")
    resume_markdown = (docs_dir / "current-resume.md").read_text(encoding="utf-8")

    return RankingProfile(
        primary_skills=_dedupe_terms(_bullet_terms(_section_between(skills_markdown, "## Primary Skills", "## Secondary Skills"))),
        secondary_skills=_dedupe_terms(
            _bullet_terms(_section_between(skills_markdown, "## Secondary Skills", "## Specialized / High-Value Skills"))
        ),
        specialized_skills=_dedupe_terms(
            _bullet_terms(_section_between(skills_markdown, "## Specialized / High-Value Skills", "# Job Matching Guidance"))
        ),
        resume_terms=_dedupe_terms(_resume_terms_from_markdown(resume_markdown)),
    )


def rank_job_text(text: str, profile: RankingProfile) -> JobRankResult:
    primary_matches = _find_terms(text, profile.primary_skills)
    secondary_matches = _find_terms(text, profile.secondary_skills)
    specialized_matches = _find_terms(text, profile.specialized_skills)
    resume_matches = _find_terms(text, profile.resume_terms)

    score = len(primary_matches) * 3 + len(secondary_matches) * 2 + len(specialized_matches) * 2 + len(resume_matches)
    rank = max(1, min(10, round(1 + (min(score, 12) / 12) * 9)))
    evidence = _dedupe_terms([*primary_matches, *secondary_matches, *specialized_matches, *resume_matches])[:12]

    return JobRankResult(rank=rank, evidence=evidence)


def _resume_terms_from_markdown(markdown: str) -> list[str]:
    terms = _bullet_terms(markdown)
    summary = _section_between(markdown, "# Executive Summary", "# Core Competencies")
    summary_phrases = (
        "Platform Architecture",
        "Cloud Systems",
        "Identity",
        "enterprise-scale web platforms",
        "platform architecture",
        "system design",
        "large-scale modernization",
        "headless architectures",
        "Azure",
        "AWS",
        "identity",
        "access management",
        "distributed systems",
        "AI-assisted development",
    )
    return [*terms, *(phrase for phrase in summary_phrases if phrase.casefold() in summary.casefold())]


def _section_between(markdown: str, start_heading: str, end_heading: str) -> str:
    start = markdown.find(start_heading)
    if start == -1:
        return ""
    end = markdown.find(end_heading, start + len(start_heading))
    if end == -1:
        return markdown[start:]
    return markdown[start:end]


def _bullet_terms(markdown: str) -> list[str]:
    terms: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("* "):
            terms.append(stripped[2:].strip())
    return [term for term in terms if term]


def _dedupe_terms(terms: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for term in terms:
        key = term.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(term)
    return tuple(deduped)


def _find_terms(text: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(term for term in terms if _term_pattern(term).search(text))


def _term_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![A-Za-z0-9+#]){escaped}(?![A-Za-z0-9+#])", flags=re.IGNORECASE)
