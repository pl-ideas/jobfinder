# Company Careers Discovery

Company careers discovery is implemented separately from the board scanner in `Source\jobfinder\company_careers.py`.

## Purpose

This job reads the latest daily JSON database, uses each saved job as a seed, and attempts to find matching postings on the employer's corporate careers site or known applicant tracking system.

The goal is to save more direct company career URLs that can be used later for manual applications.

## Behavior

The command:

1. Finds the latest `Job Database\jobs-YYYY-MM-DD.json` file unless `--input-file` is provided.
2. Extracts unique companies from the seed jobs.
3. Derives corporate career entry URLs from existing `applicationUrl` and `jobUrl` values.
4. If no corporate URL is available, searches the public web for official company career pages.
5. If public search does not find an official careers URL, checks likely corporate homepages such as `{company}.com`, `{company}.net`, `{company}.org`, `{company}.io`, and `{company}.co`.
6. Scans verified homepage HTML for career-like links such as jobs, careers, work for us, join us, open roles, and open positions.
7. If a careers page exposes a job-search form, follows the form `action` without filling keyword, location, or other search fields.
8. If no listings or search form are present, follows role/category links that look relevant, such as software engineering, engineering, technology, developer, development, consulting, professional services, or experienced professionals.
9. Navigates discovered career and pagination links and scans career/job pages up to `--limit-pages-per-company`.
10. Reuses the existing job relevance, skill/exclusion, remote, and ranking logic.
11. Merges matching jobs into `Job Database\verified-jobs-YYYY-MM-DD.json`.

The source `jobs-YYYY-MM-DD.json` file is used as input and is not rewritten by this job. If the verified file already exists for the same date, new corporate-careers results are merged into it and deduplicated.

## Review Statuses

The command reports a review status for each company:

* `FULLY_REVIEWED`: no additional career/job links were discovered before the scan ended.
* `LIMIT_REACHED`: `--limit-pages-per-company` was reached before all discovered career links were reviewed.
* `POSSIBLE_JS_PAGINATION`: the page contained load-more, next-page, or pagination markers that may require browser interaction.
* `NO_ENTRY_URL`: no corporate or ATS career URL could be derived from the seed job.
* `NO_HOMEPAGE`: no likely corporate homepage could be verified.
* `HOMEPAGE_FOUND_NO_CAREER_LINKS`: a likely corporate homepage loaded, but no career-like links were detected.
* `EXCLUDED_EMPLOYER`: the company appears to be a recruiting, staffing, placement, or consulting firm and was skipped.
* `MANUAL_VERIFICATION`: the company is an acceptable recruiting agency, but no careers URL was derived.
* `FAILED`: the company careers scan failed, but other companies can continue.

Use these statuses to distinguish companies that were fully reviewed from companies that may have additional unreviewed jobs.

## Running

From `Source`:

```powershell
python -m jobfinder.cli discover-company-careers
```

Useful development options:

```powershell
python -m jobfinder.cli discover-company-careers --limit-companies 5 --limit-pages-per-company 10
```

Public search and homepage guessing are enabled by default. To disable guessed search/homepage checks:

```powershell
python -m jobfinder.cli discover-company-careers --no-domain-guessing
```

This job reads public career pages only. It must not submit applications, authenticate, save jobs in remote accounts, or mutate third-party systems.
