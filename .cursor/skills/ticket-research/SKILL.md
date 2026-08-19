---
name: ticket-research
description: Run the Silac-specific ticket research workflow, including read-only Jira and Sentry review. Use when the user says "ticket-research", "ticket research", "read the ticket", or asks to read and interpret a Jira ticket from a browser URL.
disable-model-invocation: true
---

────────────────────────
TICKET URL AND BROWSER LOADING
────────────────────────

First request the URL of the ticket unless the user already provided it.

Open the ticket URL in a browser tab and inspect the loaded page.

If the ticket does not load, the browser shows an authentication page, or Jira requires login:

- Stop ticket research.
- Ask the user to log in or finish loading the ticket manually in the browser.
- Present a Continue option using the available structured question tool when possible.
- If no structured question tool is available, ask the user to reply with "continue" after the ticket page is loaded.
- After the user continues, inspect the currently loaded browser tab and resume the ticket reading workflow.

Do not attempt to bypass login, authentication, permissions, captchas, or manual user interaction.

────────────────────────
SILAC KNOWLEDGE DISCOVERY
────────────────────────

The goal of this skill is to interpret the Jira ticket request as it pertains to Silac as a business.

Use Silac-specific documentation and prior ticket history to understand business context, repository ownership, data-correction patterns, product behavior, and recurring workflows.

Use the Silac documentation root:

\Silac\Documentation

When available, read:

- \Silac\Documentation\DOCUMENTATION_MAP.md
- \Silac\Documentation\DOCUMENTATION_STRATEGY.md
- \Silac\Documentation\Knowledge\README.md
- \Silac\Documentation\Knowledge\Business-Context.md
- \Silac\Documentation\Knowledge\Systems-And-Repositories.md
- \Silac\Documentation\Knowledge\Glossary.md
- \Silac\Documentation\Tickets\_index.md
- \Silac\Documentation\Projects\_index.md
- \Silac\Documentation\Database\_index.md
- Relevant domain docs such as Data-Corrections.md, Death-Claims.md, APAS.md, Payments-And-Checks.md, or other docs referenced by the Knowledge index.

Always search prior ticket documentation for similar cases. Do not ask whether to do this.

Search:

\Silac\Documentation\Tickets

Start with \Silac\Documentation\Tickets\_index.md, then use ticket title terms, policy numbers, claim numbers, product names, labels, components, business terms, exception names, file names, and repository names to find related ticket documentation.

Use \Silac\Documentation\Projects\_index.md to identify likely repository ownership.

Use \Silac\Documentation\Database\_index.md when the ticket involves data correction, SQL, policy data, claims, payments, checks, withdrawals, account values, or table-level questions.

Always create or update reusable Knowledge docs from validated findings. Do not ask whether to do this.

Only add reusable Knowledge entries when the finding is supported by repository evidence, Jira evidence, prior ticket documentation, or validated implementation results. Cite or reference the supporting ticket documentation when possible.

Do not turn ticket-specific facts into general Silac knowledge unless they clearly apply beyond one ticket.

────────────────────────
DISCOVERY QUESTIONS
────────────────────────

Ask clarifying questions only when they help resolve ambiguity that cannot be resolved from Jira, repository evidence, existing ticket documentation, or Silac Knowledge docs.

Do NOT ask these questions because the answer is always yes:

- Should I search prior ticket documentation for similar cases?
- Should I create or update reusable Knowledge docs from validated findings?
- Jira references a branch/PR. May I inspect source-control metadata read-only?

When asking questions, prefer focused multiple-choice questions where possible.

Useful question areas:

- Which Silac business domain best fits the ticket, only if the evidence is ambiguous.
- Which repository owns the fix, only if Jira development metadata and repository evidence conflict.
- Which business rule is authoritative, only if prior docs or ticket evidence disagree.
- Whether an external visible page may be opened, only if read-only metadata cannot be gathered without visible external navigation.

────────────────────────
LOCAL IMPLEMENTATION READINESS
────────────────────────

Always produce implementation readiness, but only locally within the ticket documentation.

This skill does NOT implement the fix. Another skill will rely on this research phase to perform the work.

The research output must make the requirements and goal clear enough that implementation can proceed without restarting research.

Document one of:

READY TO IMPLEMENT

or

IMPLEMENTATION BLOCKED

Include the readiness decision in:

\Silac\Documentation\Tickets\<ticket-number>\<ticket-number>.md

The readiness section should include:

- Ticket number and title
- Issue summary
- Silac business interpretation
- Investigation findings
- Root cause
- Root-cause confidence
- Repository ownership and project root
- Impacted files, components, services, APIs, or database objects
- Business requirements
- Acceptance criteria
- Proposed solution
- Edge cases
- Recommended tests
- Validation strategy
- Known risks
- Open questions
- Final readiness decision

If implementation is blocked, document why, missing information, questions requiring clarification, and recommended next steps.

────────────────────────
JIRA READ ONLY
────────────────────────

Jira is READ ONLY for this skill.

Do NOT create, update, delete, submit, post, transition, assign, link, unlink, attach, remove, react to, or otherwise mutate anything in Jira.

Do NOT edit Jira fields, statuses, assignees, labels, descriptions, comments, links, attachments, subtasks, related work, watchers, priorities, due dates, components, or metadata.

Do NOT use browser automation, MCP tools, REST APIs, forms, buttons, keyboard input, scripts, or generated code to perform Jira writes.

Allowed Jira actions:

- Read ticket title, description, status, metadata, comments, linked work, development metadata, and attachments.
- Preview attachments in the browser without downloading unless the user explicitly requests downloading.

Mandatory Jira attachment review:

- If the Jira ticket has attachments, inspect each relevant attachment in the browser before finalizing research.
- For screenshots, document what screen or page is shown, visible policy numbers, agent numbers, statuses, dates, errors, duplicate rows, and any other fields that affect the root-cause hypothesis.
- For duplicate-row or display tickets, determine whether visible duplicates are identical or differ by any displayed field.
- If an attachment cannot be previewed, document that limitation, why it could not be previewed, and whether the missing attachment affects implementation readiness.

────────────────────────
SENTRY READ ONLY
────────────────────────

As part of ticket research, search the Jira ticket for Sentry links, Sentry issue IDs, Sentry sections, and Sentry integration panels.

If a Sentry link is found:

- Attempt to open it in a Cursor browser tab.
- Wait for it to load.
- If a login is needed, stop Sentry research.
- Ask the user to log in or finish loading the Sentry page manually in the browser.
- Present a Continue option using the available structured question tool when possible.
- If no structured question tool is available, ask the user to reply with "continue" after the Sentry page is loaded.
- After the user continues, inspect the currently loaded Sentry browser tab and resume Sentry review.

Do not attempt to bypass Sentry login, authentication, permissions, captchas, or manual user interaction.

Sentry is READ ONLY for this skill.

Do NOT create, update, delete, assign, resolve, ignore, archive, bookmark, comment on, link, unlink, tag, annotate, change priority, change status, react to, or otherwise mutate anything in Sentry.

Do NOT use browser automation, MCP tools, REST APIs, forms, buttons, keyboard input, scripts, or generated code to perform Sentry writes.

Allowed Sentry actions:

- Read issue title, exception type, message, stack trace, culprit, project, environment, release, event count, affected users, first seen, last seen, tags, breadcrumbs, request data, browser/device/runtime context, linked Jira issue metadata, suspect commits, and trace context when visible.
- Preview Sentry event details and stack frames in the browser without downloading attachments, artifacts, profiles, source maps, or event exports unless the user explicitly requests downloading.
- Summarize all important Sentry findings in the local ticket documentation.

────────────────────────
SOURCE CONTROL DISCOVERY READ ONLY
────────────────────────

As part of ticket research, check whether Jira exposes linked source-control development metadata for:

- Branches
- Commits
- Pull requests

All source-control discovery must be READ ONLY and must avoid visible interactions.

Allowed source-control actions:

- Read branch names, repository names, commit metadata, commit messages, pull request titles, pull request status, pull request checks, and pull request metadata when exposed by Jira or other read-only tools.
- Summarize discovered branches, commits, and pull requests in the ticket findings.
- Inspect Jira-linked branch, commit, and pull request metadata read-only without asking the user first.

Explicitly restricted source-control actions:

- Do NOT create, update, delete, push, merge, approve, close, reopen, comment on, react to, label, assign, review, request review, edit, or otherwise mutate branches, commits, pull requests, releases, tags, checks, comments, reviews, or repository metadata.
- Do NOT download patches, diffs, artifacts, archives, attachments, or generated files.
- Do NOT make visible interactions with GitHub, Bitbucket, GitLab, Azure DevOps, or other repository hosting pages unless the user explicitly approves that exact read-only navigation.
- Do NOT use browser automation, MCP tools, REST APIs, forms, buttons, keyboard input, scripts, or generated code to perform source-control writes.

If Jira does not expose enough development metadata, use non-mutating read-only metadata tools where available. If the only remaining option requires visible external repository navigation, stop and ask the user for explicit approval before opening it.

────────────────────────
CONSTRAINTS
────────────────────────
Do NOT implement code changes while running this skill.
Do NOT modify source files, tests, generated artifacts, lockfiles, deployment files, infrastructure files, or unrelated configuration.
The only allowed writes are local documentation updates under \Silac\Documentation.
Do NOT perform git operations (commit, push, merge, rebase, cherry-pick, or branch manipulation).
Do NOT deploy applications or modify deployment pipelines.
Do NOT modify infrastructure or configuration unrelated to this ticket.
Do NOT expand the scope beyond the reported defect unless required to safely implement the fix.
Base all conclusions on repository evidence and validation.
Do NOT assume runtime behavior that cannot be verified.
Preserve existing behavior for unrelated products and workflows.
Complete investigation, implementation, validation, testing, and documentation before considering the ticket complete.
