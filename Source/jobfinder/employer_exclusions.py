from __future__ import annotations


EXCLUDED_EMPLOYER_NAMES = (
    "Synersys Technologies",
)

ACCEPTABLE_RECRUITING_AGENCIES = (
    "Apex Systems",
    "TEKsystems",
    "Kforce Technology Staffing",
)

EXCLUDED_EMPLOYER_INDICATORS = (
    "consulting and staffing",
    "consulting firm",
    "technology consulting",
    "technology consulting and staffing",
    "staffing agency",
    "staffing firm",
    "staffing services",
    "technology staffing",
    "it staffing",
    "recruiting agency",
    "recruiting firm",
    "recruitment agency",
    "recruitment firm",
    "talent agency",
    "talent solutions",
    "workforce solutions",
    "staff augmentation",
    "contract staffing",
    "placement services",
    "professional staffing",
)

EXCLUDED_EMPLOYER_NAME_TERMS = (
    "staffing",
    "recruiting",
    "recruitment",
    "workforce",
    "consulting",
)


def is_excluded_employer(company_name: str, employer_text: str | None = None) -> bool:
    normalized_name = _normalize(company_name)
    normalized_text = _normalize(" ".join([company_name, employer_text or ""]))

    if is_acceptable_recruiting_agency(company_name):
        return False

    if any(normalized_name == _normalize(name) for name in EXCLUDED_EMPLOYER_NAMES):
        return True

    if any(term in normalized_name for term in EXCLUDED_EMPLOYER_NAME_TERMS):
        return True

    return any(indicator in normalized_text for indicator in EXCLUDED_EMPLOYER_INDICATORS)


def is_acceptable_recruiting_agency(company_name: str) -> bool:
    normalized_name = _normalize(company_name)
    return any(normalized_name == _normalize(name) for name in ACCEPTABLE_RECRUITING_AGENCIES)


def employer_exclusion_reason(company_name: str, employer_text: str | None = None) -> str | None:
    if not is_excluded_employer(company_name, employer_text):
        return None
    return "Employer appears to be a recruiting, staffing, or consulting firm rather than the direct hiring company."


def _normalize(value: str) -> str:
    return " ".join(value.casefold().replace("&", "and").split())
