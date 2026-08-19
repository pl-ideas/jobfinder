---
name: ticket-info
description: Look up local Silac ticket documentation and summarize what is known. Use when the user says "ticket-info" or asks to run ticket-info for a ticket.
disable-model-invocation: true
---

# Ticket Info

## Workflow

1. First respond by asking the user for the ticket number.

2. After the user provides the ticket number, first look for local ticket documentation before searching code, Jira, browser tabs, transcripts, or other sources.

3. Use workspace-relative paths only.

4. First try reading the ticket doc at the repository-root path:

```text
./Documentation/Tickets/{ticket-number}/{ticket-number}.md
```

5. If that fails, try the common parent-workspace path used when Cursor is opened at `/home/silac`:

```text
./Silac/Documentation/Tickets/{ticket-number}/{ticket-number}.md
```

6. If both direct reads fail, search from the workspace root using Glob with no `target_directory`:

```text
Documentation/Tickets/**/{ticket-number}*
Silac/Documentation/Tickets/**/{ticket-number}*
```

7. If the Glob search finds matching documentation files, prefer the primary `{ticket-number}.md`, then read useful sibling files such as options, testing, summary, notes, or README files before summarizing.

8. Avoid absolute WSL, Windows, or UNC paths for the initial lookup because workspace-relative paths are the most reliable in Cursor file tools.

9. If no ticket documentation exists, request the Jira ticket URL before creating documentation:

   - Ask the user for the Jira URL for `{ticket-number}`.
   - Open that Jira URL in a browser tab.
   - Jira is READ ONLY. Do not create, update, delete, submit, post, transition, assign, link, unlink, attach, remove, react to, or otherwise mutate anything in Jira.
   - Do not edit Jira fields, statuses, assignees, labels, descriptions, comments, links, attachments, subtasks, related work, watchers, priorities, due dates, components, or metadata.
   - Do not use browser automation, MCP tools, REST APIs, forms, buttons, keyboard input, scripts, or generated code to perform Jira writes.
   - Allowed Jira actions are reading ticket title, description, status, metadata, comments, linked work, development metadata, and attachments.
   - If Jira requires login, authentication, permissions, captcha, or manual user interaction, stop and ask the user to handle it before continuing.
   - Take all reliable information available from the Jira ticket and use it to start the local ticket documentation.

10. After reading Jira, create the missing local documentation before responding:

   - Create the ticket folder at `./Documentation/Tickets/{ticket-number}/` when the repository root is the workspace, or `./Silac/Documentation/Tickets/{ticket-number}/` when Cursor is opened at the parent workspace.
   - Create the primary doc at `{ticket-number}.md`.
   - Use the typical ticket documentation format below.
   - Populate the new document first from the Jira ticket evidence.
   - Then search available local sources for more viable ticket information, including prior conversation transcripts, existing documentation indexes, related ticket docs, local source file names, commit/checkpoint text, and other local workspace evidence.
   - Add reliable local findings to the new documentation after the Jira-derived information.
   - Cite the evidence source in prose when possible.
   - Do not invent unknown facts. Use `Not documented.` or `Unknown from local evidence.` for gaps.

11. Summarize what is known from the local documentation using the response format below. Keep each section compact by default, usually one short paragraph or 1-3 bullets.

## Missing Documentation Format

When creating a new primary ticket doc, use this structure:

```markdown
# {ticket-number} Investigation

## Purpose

Not documented.

## Current Scenario

Not documented.

## Business Goal

Not documented.

## Findings So Far

Not documented.

## Likely Implementation Areas

Not documented.

## Testing And Validation

Not documented.

## Open Questions

- Not documented.

## Evidence Sources

- Local evidence used to create this document.
```

## Response Format

Use this structure for every completed ticket lookup:

```markdown
## Ticket Info: {ticket-number}

### Documentation Location
Path to the primary ticket documentation. State whether it already existed or was created during this lookup.

### Summary
One short paragraph explaining the ticket's purpose and current known outcome.

### Business Context
What problem the ticket was trying to solve in Silac terms.

### Systems And Files
- Repositories, systems, files, tables, APIs, or services mentioned in the docs.

### Findings
- Confirmed facts from the ticket docs.
- Investigation notes.
- Root cause if documented.

### Implementation Notes
- What was changed or proposed.
- Important design decisions.
- Options considered, if any.

### Testing And Validation
- Tests that were run.
- Manual validation steps.
- Known regression checks.

### Caveats Or Open Questions
- Stale docs.
- Source/docs mismatch.
- Unanswered business questions.
- Anything that needs confirmation before implementation.
```

If no information exists for a section, write `Not documented.` rather than inventing details.

If the documentation conflicts with the checked-out source or appears stale, call that out under `Caveats Or Open Questions`.
