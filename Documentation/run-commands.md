# Run Commands

Run commands from the `Source` directory:

```powershell
cd "c:\Development\Personal Dev\JobFinder\Source"
```

## Quick Full Pipeline

Run all four stages in order:

```powershell
python -m jobfinder.cli discover-job-boards --limit-per-query 100
python -m jobfinder.cli discover-job-boards-auth
python -m jobfinder.cli verify-company-sites --limit-companies 100
python -m jobfinder.cli discover-career-pages
python -m jobfinder.cli discover-verified-jobs --limit-pages-per-company 100
```

Each stage automatically uses the latest JSON file from the previous stage unless `--input-file` is provided.

## Stage 1A: No-Auth Job Board Scan

Scan supported no-auth job boards and merge results into the stage 1 JSON file:

```powershell
python -m jobfinder.cli discover-job-boards --limit-per-query 100
```

This command uses:

```text
Documentation\job-board-sites-no-auth.md
```

`discover-daily` is an alias for the same no-auth scan.

## Stage 1B: Auth-Required Job Board Scan

Print the next browser-session checkpoint from the auth list:

```powershell
python -m jobfinder.cli discover-job-boards-auth
```

This command uses:

```text
Documentation\job-board-sites-auth.md
```

This command does not perform a background HTTP scan. It prints the stored URL and asks you to have the Cursor agent open that URL in Cursor's browser. You log in manually, then tell the agent authentication is complete so it can use the open browser session read-only.

Print checkpoints for all auth-required boards:

```powershell
python -m jobfinder.cli discover-job-boards-auth --continue-after-auth-checkpoint
```

Output:

```text
..\Job Database\01-job-board-results\jobs.json
```

Suppress progress output:

```powershell
python -m jobfinder.cli discover-job-boards --quiet
```

## Stage 2: Verify Company Sites

Find and verify official company homepages from the latest stage 1 job-board file:

```powershell
python -m jobfinder.cli verify-company-sites
```

Input:

```text
..\Job Database\01-job-board-results\jobs.json
```

Output:

```text
..\Job Database\02-verified-company-sites\company-sites.json
```

Review up to 100 companies:

```powershell
python -m jobfinder.cli verify-company-sites --limit-companies 100
```

Use a specific stage 1 file:

```powershell
python -m jobfinder.cli verify-company-sites --input-file "..\Job Database\01-job-board-results\jobs.json"
```

## Stage 3: Discover Career Pages

Scan verified company homepages for career and job page links:

```powershell
python -m jobfinder.cli discover-career-pages
```

Input:

```text
..\Job Database\02-verified-company-sites\company-sites.json
```

Output:

```text
..\Job Database\03-verified-career-pages\career-pages.json
```

Use a specific stage 2 file:

```powershell
python -m jobfinder.cli discover-career-pages --input-file "..\Job Database\02-verified-company-sites\company-sites.json"
```

## Stage 4: Discover Verified Jobs

Scan verified career pages for matching remote software-development jobs:

```powershell
python -m jobfinder.cli discover-verified-jobs
```

Input:

```text
..\Job Database\03-verified-career-pages\career-pages.json
```

Output:

```text
..\Job Database\04-matched-company-jobs\verified-jobs.json
```

Limit per-company page traversal:

```powershell
python -m jobfinder.cli discover-verified-jobs --limit-pages-per-company 100
```

## Output Location

Stage outputs are stored under numbered folders:

```text
Job Database\01-job-board-results\jobs.json
Job Database\02-verified-company-sites\company-sites.json
Job Database\03-verified-career-pages\career-pages.json
Job Database\04-matched-company-jobs\verified-jobs.json
```

Each stage appends into its single output file by loading existing records, merging new results, and avoiding duplicates. All commands print progress unless `--quiet` is provided. Stage 2 uses public search results to verify official homepages and does not guess domains from company names.

## Authentication-Blocked Sites

If a job board requires authentication, stage 1 saves the accessible results collected so far and prints a browser-login checkpoint:

```text
BROWSER LOGIN REQUIRED: <site name>.
```

At that point:

1. Open the site normally in a browser.
2. Log in manually yourself.
3. Do not provide credentials to the agent.
4. After login is complete, request a browser-session scan for that specific site.

The scanner must not enter credentials, bypass CAPTCHA/MFA, submit applications, save jobs, message recruiters, or store cookies/tokens/session data.

Stage 1 also updates the local board lists:

```text
Documentation\job-board-sites-no-auth.md
Documentation\job-board-sites-auth.md
```

When a site requires authentication, it is removed from the no-auth list and added to the auth-required list.

To skip authentication-blocked sources and keep scanning later sources during a terminal run:

```powershell
python -m jobfinder.cli discover-job-boards --continue-after-auth-checkpoint
```

## Status Signals

Stage 2 company statuses include:

```text
VERIFIED
NO_SEARCH_RESULTS
MANUAL_VERIFICATION
EXCLUDED_EMPLOYER
FAILED
```

Stage 3 career-page statuses include:

```text
CAREER_PAGE_FOUND
HOMEPAGE_FOUND_NO_CAREER_LINKS
FAILED
```

Stage 4 review statuses include:

```text
FULLY_REVIEWED
LIMIT_REACHED
POSSIBLE_JS_PAGINATION
FAILED
```
