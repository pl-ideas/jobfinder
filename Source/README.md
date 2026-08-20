# JobFinder Source

Python source code for the JobFinder MVP.

## Requirements

- Python 3.11 or newer

## Setup

From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Run

Fetch remote-friendly jobs from the first source and print matches:

```powershell
jobfinder fetch --query python --remote-only --include-keyword backend
```

Store results in a specific database:

```powershell
jobfinder fetch --query python --db .\jobfinder.sqlite3
```

You can also run the module without installing:

```powershell
python -m jobfinder.cli fetch --query python
```

Build the daily JSON job database from supported job boards:

```powershell
python -m jobfinder.cli discover-daily
```

The daily discovery command scans public boards first, then login-gated boards. If a site requires authentication, it prints a `BROWSER LOGIN REQUIRED` checkpoint, saves accessible results collected so far, and stops without attempting to authenticate. Output is merged into `..\Job Database\01-job-board-results\jobs.json`.

Progress messages are printed by default so long scans show the current site, search term, detail-page review count, dedupe count, and saved output path. Add `--quiet` to suppress them.

Run the company-site, career-page, and verified-job stages manually after reviewing each output file:

```powershell
python -m jobfinder.cli verify-company-sites
python -m jobfinder.cli discover-career-pages
python -m jobfinder.cli discover-verified-jobs
```

Use `--limit-companies` and `--limit-pages-per-company` during development to keep the scan bounded. Add `--allow-domain-guessing` only when you want the job to try guessed company career domains.
