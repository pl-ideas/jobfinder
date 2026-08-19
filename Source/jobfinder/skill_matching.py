from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


ROLE_ONLY_TERMS = {
    "senior software engineer",
    "senior full stack developer",
    "15+ years of professional software-development experience",
}


@dataclass(frozen=True)
class SkillProfile:
    current_skills: tuple[str, ...] = field(default_factory=tuple)
    excluded_skills: tuple[str, ...] = field(default_factory=tuple)
    neutral_skills: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class JobSkillMatch:
    classification: str
    matched_skills: tuple[str, ...] = field(default_factory=tuple)
    excluded_skills_found: tuple[str, ...] = field(default_factory=tuple)
    exclusion_reason: str | None = None


def default_documentation_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "Documentation"


def load_default_skill_profile(documentation_dir: Path | None = None) -> SkillProfile:
    docs_dir = documentation_dir or default_documentation_dir()
    current_skills_path = _first_existing(docs_dir / "current-skills.md", docs_dir / "current-skill.md")
    exclusions_path = docs_dir / "job-exclusions.md"

    current_skills = _current_skills_from_markdown(current_skills_path.read_text(encoding="utf-8"))
    exclusions_markdown = exclusions_path.read_text(encoding="utf-8")
    excluded_skills = _excluded_skills_from_markdown(exclusions_markdown)
    neutral_skills = _neutral_skills_from_markdown(exclusions_markdown)

    return SkillProfile(
        current_skills=_dedupe_terms(current_skills),
        excluded_skills=_dedupe_terms(excluded_skills),
        neutral_skills=_dedupe_terms(neutral_skills),
    )


def evaluate_job_skills(text: str, profile: SkillProfile) -> JobSkillMatch:
    matched_skills = _find_terms(text, profile.current_skills)
    excluded_skills_found = _find_terms(text, profile.excluded_skills)
    neutral_matches = set(_find_terms(text, profile.neutral_skills))
    meaningful_matches = tuple(skill for skill in matched_skills if skill not in neutral_matches)

    if meaningful_matches:
        return JobSkillMatch(
            classification="INCLUDE",
            matched_skills=matched_skills,
            excluded_skills_found=excluded_skills_found,
        )

    if excluded_skills_found:
        return JobSkillMatch(
            classification="EXCLUDE",
            matched_skills=matched_skills,
            excluded_skills_found=excluded_skills_found,
            exclusion_reason="Only excluded-stack indicators were found in the job description.",
        )

    return JobSkillMatch(classification="REVIEW", matched_skills=matched_skills)


def _first_existing(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError(f"None of these documentation files exist: {', '.join(str(path) for path in paths)}")


def _current_skills_from_markdown(markdown: str) -> list[str]:
    skills_section = _section_between(markdown, "## Languages & Frameworks", "# Job Matching Guidance")
    terms = _bullet_terms(skills_section)
    return [term for term in terms if term.casefold() not in ROLE_ONLY_TERMS]


def _excluded_skills_from_markdown(markdown: str) -> list[str]:
    exclusions_section = _section_between(markdown, "## Java / JVM", "# Shared / Neutral Technologies")
    return _bullet_terms(exclusions_section)


def _neutral_skills_from_markdown(markdown: str) -> list[str]:
    neutral_section = _section_between(markdown, "# Shared / Neutral Technologies", "# Job Title Analysis")
    return _bullet_terms(neutral_section)


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
        if not stripped.startswith("* "):
            continue
        term = stripped[2:].strip()
        term = term.split(" when ", 1)[0].strip()
        if term:
            terms.append(term)
    return terms


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
