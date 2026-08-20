# No-Auth Job Board Sites

These job boards are intended to be scanned by the background job-board discovery command without requiring a logged-in browser session.

Format: `Site Name | URL | Notes`

## Active Sites

* Built In | <https://builtin.com/jobs> | Excellent technology-company coverage.
* Dice | <https://www.dice.com/jobs> | Strong fit for .NET, cloud and enterprise engineering.
* We Work Remotely | <https://weworkremotely.com/> | Particularly valuable because remote work is the target.
* Remote OK | <https://remoteok.com/> | Remote-first and technology-heavy.
* Welcome to the Jungle | <https://www.welcometothejungle.com/> | Curated technology/startup jobs; incorporates the former Otta platform.
* Y Combinator - Work at a Startup | <https://www.workatastartup.com/jobs> | Direct access to jobs at YC-backed companies.
* Arc | <https://arc.dev/remote-jobs> | Developer-focused remote opportunities.
* Hacker News - Who Is Hiring? | <https://news.ycombinator.com/submitted?id=whoishiring> | Unusual but valuable; companies/founders frequently post engineering openings directly.
* Remote.co | <https://remote.co/remote-jobs/> | Remote-only employment.
* FlexJobs | <https://www.flexjobs.com/> | Curated remote/flexible jobs, although some functionality is paid.
* ZipRecruiter | <https://www.ziprecruiter.com/> | Large general-purpose source.
* Glassdoor | <https://www.glassdoor.com/Job/index.htm> | Jobs plus useful employer research.
* Himalayas | <https://himalayas.app/jobs> | Remote-focused with good filtering.
* Working Nomads | <https://www.workingnomads.com/jobs> | Curated remote positions.
* TechFetch | <https://www.techfetch.com/> | IT-specific job board, including enterprise technology positions.
* Levels.fyi Jobs | <https://www.levels.fyi/jobs> | Particularly useful when compensation is important.
* Monster | <https://www.monster.com/> | Older general-purpose board, but still another discovery source.

## Notes

If a site starts returning authentication, CAPTCHA, or anti-bot pages during background scanning, move it to `Documentation\job-board-sites-auth.md` and handle it through the browser-login checkpoint flow.
