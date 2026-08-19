# JobFinder Architecture

JobFinder is organized around source adapters, normalization, local persistence, and filtering.

```mermaid
flowchart TD
    Filters[User Filters] --> Matcher[Matching Engine]
    Sources[Job Sources] --> Fetchers[Source Fetchers]
    Fetchers --> Normalizer[Job Normalizer]
    Normalizer --> Store[SQLite Store]
    Store --> Matcher
    Matcher --> Results[Matched Jobs]
    Results --> CLI[Command Line Output]
```

## Components

### Source Adapters

Source adapters know how to fetch jobs from a specific job source. Each adapter returns normalized `JobPosting` records so the rest of the system does not depend on source-specific response formats.

The first adapter targets an API-style remote job board. Future adapters can support other job boards or specific company career pages.

Daily JSON discovery uses the same adapter boundary for public job-board pages. Site-specific behavior for Built In, Dice, Indeed, LinkedIn Jobs, and Wellfound lives in `Source\jobfinder\sources\web_boards.py`; orchestration lives in `Source\jobfinder\discovery.py`.

### Normalized Job Model

Every posting is represented with common fields:

- title
- company
- location
- remote status
- salary range
- source name
- source URL
- description
- tags
- date discovered

### Storage

SQLite is used for local storage in the MVP. It keeps the first version simple while still allowing deduplication, filtering, and later reporting.

The daily job-board scan also writes a JSON database under `Job Database\jobs-YYYY-MM-DD.json`. Existing same-day JSON is read, merged, deduplicated by normalized company and title, and then rewritten as parseable JSON.

### Filtering

Filters are applied to normalized jobs, not raw source payloads. This keeps matching behavior consistent across sources.

Initial filters include:

- required title or description keywords
- excluded keywords
- location text
- remote-only preference
- minimum salary
- company allow and block lists

### Interface

The MVP exposes a CLI command that can fetch postings, save them locally, filter them, and print matching results.
