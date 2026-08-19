# JobFinder Goal

JobFinder helps discover open positions that match a user's career filters by gathering job postings from known sources, normalizing them into a consistent format, and ranking or filtering them locally.

## MVP Goal

The first version should prove the core workflow:

1. Fetch job postings from job-board or API-style sources.
2. Normalize each posting into a shared `JobPosting` shape.
3. Store discovered jobs locally.
4. Filter jobs by keywords, location, remote preference, salary, and company rules.
5. Display matching jobs through a simple command-line interface.

## Long-Term Vision

After the MVP works reliably, JobFinder can expand into direct company career-site crawlers, scheduled scans, notifications, a richer web interface, and smarter matching based on skills, resume context, or saved searches.

## Non-Goals For The MVP

- Crawling the open web without a curated source list.
- Bypassing anti-bot controls or login-protected pages.
- Applying to jobs automatically.
- Posting, submitting, or mutating data in any third-party service.
