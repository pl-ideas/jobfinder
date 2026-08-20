# Job Board Daily Discovery

Daily job-board scanning is implemented in `Source\jobfinder\discovery.py` and `Source\jobfinder\sources\web_boards.py`.

Stage 1 is split into two commands:

* `discover-job-boards`: scans supported boards listed in `Documentation\job-board-sites-no-auth.md`.
* `discover-job-boards-auth`: prints browser-session checkpoints for boards listed in `Documentation\job-board-sites-auth.md`.

## Supported Boards

The scan order is:

1. Built In
2. Dice
3. Indeed
4. LinkedIn Jobs
5. Wellfound

Public boards are processed before login-gated boards. If LinkedIn Jobs, Wellfound, or another source requires authentication, the scanner saves accessible results collected so far, returns an explicit browser-login checkpoint, and does not attempt to log in, bypass controls, save jobs, apply, or mutate account data.

Authentication-blocked sites should be handled as a manual browser-session follow-up:

1. The user opens the site in a browser.
2. The user logs in manually.
3. The agent may read the already-authenticated browser session only after the user confirms login is complete.
4. Credentials, cookies, tokens, and session data must not be stored in the repository or Job Database.

When `discover-job-boards` detects authentication for a site, it also updates the local board lists:

```text
Documentation\job-board-sites-no-auth.md
Documentation\job-board-sites-auth.md
```

The site is removed from the no-auth list and added to the auth-required list.

## Output

Daily results are written to:

```text
Job Database\01-job-board-results\jobs.json
```

The JSON schema is:

```json
{
  "generatedDate": "YYYY-MM-DD",
  "jobs": [
    {
      "companyName": "Example Company",
      "jobTitle": "Senior Software Engineer",
      "jobUrl": "https://example.com/job/123",
      "applicationUrl": "https://example.com/apply/123",
      "source": "Built In",
      "location": "Remote - United States",
      "remote": true,
      "workMode": "remote",
      "workModeEvidence": "Job description states this is a remote position.",
      "salary": null,
      "datePosted": null,
      "dateDiscovered": "YYYY-MM-DD"
    }
  ]
}
```

`workMode` is a compact classification from available job-description text and structured metadata: `remote`, `hybrid`, `onsite`, or `unknown`. `workModeEvidence` stores one short matched phrase or metadata explanation; the full job description is not saved by default.

If the stage file already exists, it is loaded and merged with new results. Duplicate detection uses a normalized company-and-title key and keeps the record with the most direct application URL.

## Adding A Board

Add a `PublicJobBoardSource` subclass in `Source\jobfinder\sources\web_boards.py`, implement `search_url`, and override `is_probable_job_url` or extraction methods when the site's markup requires it. Add the source to `default_sources()` in `Source\jobfinder\discovery.py`.

## Running

From `Source`, scan no-auth boards:

```powershell
python -m jobfinder.cli discover-job-boards
```

Print the next auth-required browser-session checkpoint separately:

```powershell
python -m jobfinder.cli discover-job-boards-auth
```

`discover-daily` is an alias for the no-auth stage 1 scan.

The command prints progress while it scans: output target, current site, current search term, candidate listing count, detail pages reviewed, collected job counts, dedupe count, and saved JSON path. Use `--quiet` to suppress progress messages, or `--limit-per-query` to cap detail pages reviewed per search term during development.

During extraction, the scanner reads available job-description text and compares it with `Documentation\current-skills.md` and `Documentation\job-exclusions.md`. Remote jobs with meaningful current-skill matches are kept. Jobs with only excluded-stack indicators are filtered out. Jobs that mention both current skills and excluded technologies are kept so incidental excluded technologies do not discard otherwise relevant matches.

Each saved job also receives a `rank` from 1 to 10 based on overlap between the job text, `Documentation\current-resume.md`, and `Documentation\current-skills.md`. Higher ranks indicate stronger fit. The daily JSON output is ordered by rank descending, then salary descending within each rank.
