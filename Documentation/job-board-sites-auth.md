# Auth-Required Job Board Sites

These job boards should be handled through the browser-login checkpoint flow when background scanning cannot access useful search results.

Format: `Site Name | URL | Notes`

## Active Sites

* LinkedIn Jobs | <https://www.linkedin.com/jobs/> | Huge volume; essential source.
* Indeed | <https://www.indeed.com/> | Huge volume; useful for discovery, but verify listings.
* Wellfound | <https://wellfound.com/jobs> | Excellent startup/technology positions.

## Browser-Login Flow

1. Open the site normally in a browser.
2. Log in manually.
3. Do not provide credentials to the agent.
4. After login is complete, request a browser-session scan for that specific site.

Credentials, cookies, tokens, and session data must not be stored in the repository or Job Database.
