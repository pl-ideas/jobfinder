from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jobfinder.daily_storage import default_project_root

NO_AUTH_FILENAME = "job-board-sites-no-auth.md"
AUTH_FILENAME = "job-board-sites-auth.md"
AUTH_EMPTY_LINE = (
    "None yet. Sites are moved here automatically when `discover-job-boards` detects that background scanning "
    "requires authentication."
)


@dataclass(frozen=True)
class SiteListUpdate:
    site_name: str
    no_auth_path: Path
    auth_path: Path
    moved: bool


@dataclass(frozen=True)
class JobBoardSite:
    name: str
    url: str | None = None
    notes: str | None = None


def load_no_auth_sites(*, documentation_dir: Path | None = None) -> list[JobBoardSite]:
    docs_dir = documentation_dir or default_project_root() / "Documentation"
    return _load_sites(docs_dir / NO_AUTH_FILENAME)


def load_auth_required_sites(*, documentation_dir: Path | None = None) -> list[JobBoardSite]:
    docs_dir = documentation_dir or default_project_root() / "Documentation"
    return _load_sites(docs_dir / AUTH_FILENAME)


def move_site_to_auth_required(site_name: str, *, documentation_dir: Path | None = None) -> SiteListUpdate:
    docs_dir = documentation_dir or default_project_root() / "Documentation"
    no_auth_path = docs_dir / NO_AUTH_FILENAME
    auth_path = docs_dir / AUTH_FILENAME

    no_auth_lines = _read_lines(no_auth_path)
    auth_lines = _read_lines(auth_path)

    removed_line, updated_no_auth_lines = _remove_site_bullet(no_auth_lines, site_name)
    auth_lines = _add_auth_site(auth_lines, site_name, removed_line)

    no_auth_path.write_text("\n".join(updated_no_auth_lines).rstrip() + "\n", encoding="utf-8")
    auth_path.write_text("\n".join(auth_lines).rstrip() + "\n", encoding="utf-8")

    return SiteListUpdate(site_name, no_auth_path, auth_path, moved=removed_line is not None)


def _load_sites(path: Path) -> list[JobBoardSite]:
    return [_site_from_bullet(line) for line in _read_lines(path) if _is_site_bullet(line)]


def _site_from_bullet(line: str) -> JobBoardSite:
    text = line.lstrip()[2:].strip()
    if " | " in text:
        name, url, *notes = [part.strip() for part in text.split(" | ")]
        return JobBoardSite(name=name, url=url.strip("<>") or None, notes=" | ".join(notes) or None)
    return JobBoardSite(name=_bullet_site_name(line), notes=text)


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _remove_site_bullet(lines: list[str], site_name: str) -> tuple[str | None, list[str]]:
    updated: list[str] = []
    removed_line: str | None = None
    target = _site_key(site_name)

    for line in lines:
        if _is_site_bullet(line) and _site_key(_bullet_site_name(line)) == target:
            removed_line = line
            continue
        updated.append(line)

    return removed_line, updated


def _add_auth_site(lines: list[str], site_name: str, removed_line: str | None) -> list[str]:
    if any(_is_site_bullet(line) and _site_key(_bullet_site_name(line)) == _site_key(site_name) for line in lines):
        return lines

    active_index = _active_sites_index(lines)
    if active_index is None:
        lines.extend(["", "## Active Sites", ""])
        active_index = len(lines) - 2

    insert_index = _active_sites_insert_index(lines, active_index)
    lines = [line for line in lines if line.strip() != AUTH_EMPTY_LINE]
    insert_index = min(insert_index, len(lines))
    auth_line = removed_line or f"* {site_name}"
    lines.insert(insert_index, auth_line)
    return lines


def _active_sites_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        if line.strip().lower() == "## active sites":
            return index
    return None


def _active_sites_insert_index(lines: list[str], active_index: int) -> int:
    index = active_index + 1
    while index < len(lines) and not lines[index].startswith("## "):
        index += 1
    while index > active_index + 1 and not lines[index - 1].strip():
        index -= 1
    return index


def _is_site_bullet(line: str) -> bool:
    return line.lstrip().startswith("* ")


def _bullet_site_name(line: str) -> str:
    text = line.lstrip()[2:].strip()
    if " | " in text:
        return text.split(" | ", 1)[0].strip()
    for separator in (" - ", " — "):
        if separator in text:
            return text.split(separator, 1)[0].strip()
    return text


def _site_key(value: str) -> str:
    return " ".join(value.casefold().split())
