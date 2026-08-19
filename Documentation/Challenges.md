# JobFinder Challenges

## Source Reliability

Job sources change formats, remove fields, rate limit traffic, or return stale postings. Adapters should isolate source-specific logic so failures do not spread through the system.

## Duplicate Jobs

The same role may appear across multiple sources or reposts. The MVP deduplicates primarily by source URL. Later versions may compare title, company, location, and description fingerprints.

## Stale Postings

Job posts often remain indexed after a role closes. JobFinder should track when postings were first and last seen so stale records can be hidden or rechecked.

## Robots.txt And Terms

Direct company-site crawling should respect robots.txt, terms of service, rate limits, and authentication boundaries. The MVP avoids broad crawling until the core workflow is proven.

## Anti-Bot Defenses

Many company sites use dynamic rendering, bot detection, or third-party applicant tracking systems. JobFinder should prefer public APIs, feeds, and lightweight pages before considering browser-based fetching.

## Matching Quality

Keyword matching is easy to understand but can miss relevant jobs or include false positives. Future versions may add scoring, saved profiles, skill extraction, and resume-aware matching.

## User Privacy

Filters, saved searches, and local results may contain sensitive career preferences. The MVP stores data locally and should avoid sending private filters to unnecessary external services.
