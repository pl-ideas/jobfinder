# Company Careers Discovery

Company careers discovery is implemented separately from the board scanner in `Source\jobfinder\company_careers.py`.

## Purpose

The company-careers flow is split into three jobs after the job-board scan. Each job reads the previous stage's JSON output and writes to its own numbered folder.

The goal is to save more direct company career URLs that can be used later for manual applications.

## Behavior

The stages are:

1. `verify-company-sites` reads `Job Database\01-job-board-results\jobs.json`, extracts unique companies, searches Bing result pages for official company homepages, verifies returned homepage URLs, and writes `Job Database\02-verified-company-sites\company-sites.json`.
2. `discover-career-pages` reads verified company homepages, scans them for careers/job links, and writes `Job Database\03-verified-career-pages\career-pages.json`.
3. `discover-verified-jobs` reads verified career pages, follows job-search form actions, pagination links, and relevant role/category links up to `--limit-pages-per-company`, reuses the job relevance, skill/exclusion, remote, and ranking logic, and writes `Job Database\04-matched-company-jobs\verified-jobs.json`.

Stage 2 does not guess domains such as `{company}.com`; it only uses Bing search results and verifies the returned official homepage. The source job-board file is used as input and is not rewritten by downstream stages. Each stage has one stable output file. If the output file already exists, new results are merged into it and deduplicated.

## Review Statuses

The command reports a review status for each company:

* `FULLY_REVIEWED`: no additional career/job links were discovered before the scan ended.
* `LIMIT_REACHED`: `--limit-pages-per-company` was reached before all discovered career links were reviewed.
* `POSSIBLE_JS_PAGINATION`: the page contained load-more, next-page, or pagination markers that may require browser interaction.
* `NO_SEARCH_RESULTS`: public search did not find and verify an official company homepage.
* `EXCLUDED_EMPLOYER`: the company appears to be a recruiting, staffing, placement, or consulting firm and was skipped.
* `MANUAL_VERIFICATION`: the company is an acceptable recruiting agency, or public search found likely homepage candidates that the background fetch could not verify.
* `FAILED`: the company careers scan failed, but other companies can continue.

Use these statuses to distinguish companies that were fully reviewed from companies that may have additional unreviewed jobs.

## Running

From `Source`:

```powershell
python -m jobfinder.cli verify-company-sites
python -m jobfinder.cli discover-career-pages
python -m jobfinder.cli discover-verified-jobs
```

Useful development options:

```powershell
python -m jobfinder.cli verify-company-sites --limit-companies 100
python -m jobfinder.cli discover-verified-jobs --limit-pages-per-company 100
```

This job reads public career pages only. It must not submit applications, authenticate, save jobs in remote accounts, or mutate third-party systems.
