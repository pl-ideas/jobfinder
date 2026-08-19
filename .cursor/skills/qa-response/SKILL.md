---
name: qa-response
description: Investigate failed QA feedback from a Jira ticket and return either suggested fixes or clarification questions. Use when the user says "qa-response" or asks to understand a failed QA result from Jira.
disable-model-invocation: true
---

# QA Response

## Workflow

1. First respond by asking the user for the Jira ticket URL.

2. After the user provides the Jira URL, open that Jira URL in a browser tab and inspect the loaded page.

3. Jira is READ ONLY.

   - Do not create, update, delete, submit, post, transition, assign, link, unlink, attach, remove, react to, or otherwise mutate anything in Jira.
   - Do not edit Jira fields, statuses, assignees, labels, descriptions, comments, links, attachments, subtasks, related work, watchers, priorities, due dates, components, or metadata.
   - Do not use browser automation, MCP tools, REST APIs, forms, buttons, keyboard input, scripts, or generated code to perform Jira writes.
   - Allowed Jira actions are reading ticket title, description, status, metadata, comments, linked work, development metadata, and attachments.
   - Preview screenshots and image attachments in the browser when needed. Do not download attachments unless the user explicitly requests downloading.

4. If the ticket does not load, the browser shows an authentication page, or Jira requires login, permissions, captcha, or manual interaction:

   - Stop the QA investigation.
   - Ask the user to log in or finish loading the ticket manually in the browser.
   - After the user confirms the ticket is loaded, inspect the currently loaded browser tab and resume.

5. Use the Jira ticket to identify the ticket number for the QA failure.

   - Prefer the Jira issue key shown on the page, such as `SCH-####`.
   - If the ticket number cannot be found or the page contains multiple plausible ticket numbers, stop and ask the user which ticket number to use.

6. Read the Jira ticket for QA context.

   - Read the title, description, status, labels/components if visible, linked work, development metadata, and all visible comments.
   - Pay special attention to comments from QA or comments describing failed QA results.
   - Review screenshots or image attachments referenced by QA comments.
   - Extract exact observed behavior, expected behavior, policy numbers, account numbers, user roles, environment, dates, steps to reproduce, error messages, URLs, screenshots, and any affected files or PR references.

7. Build a QA failure understanding.

   - Identify what failed in QA.
   - Identify where the failure appears to live: UI, API, database/data correction, permissions/access, calculation, integration, test data, deployment/environment, or unclear.
   - Compare QA evidence against any ticket documentation or local repository evidence only as needed to understand likely root cause.
   - Do not implement code changes in this skill.
   - Do not update Jira.

8. If there is enough information to suggest fixes, respond using the Suggested Fixes format.

9. If there is not enough information to suggest fixes safely, respond using the Clarification Questions format.

## Suggested Fixes Format

```markdown
## QA Response: {ticket-number}

### QA Failure Summary
Briefly state what failed in QA and where the evidence came from.

### Evidence Reviewed
- Jira title/description/comments reviewed.
- QA comments reviewed.
- Screenshots or attachments reviewed.
- Relevant local docs or source files reviewed, if any.

### Likely Root Cause
State the likely root cause and confidence level: confirmed, probable, or uncertain.

### Suggested Fixes
- Specific fix suggestion 1.
- Specific fix suggestion 2, if needed.

### Validation Plan
- How to verify the fix locally or in QA.
- Regression checks that should be run.

### Risks Or Caveats
- Any uncertainty, missing context, or behavior that needs care.
```

## Clarification Questions Format

```markdown
## QA Response: {ticket-number}

### QA Failure Summary
Briefly state what appears to have failed based on the available evidence.

### Evidence Reviewed
- Jira title/description/comments reviewed.
- QA comments reviewed.
- Screenshots or attachments reviewed.
- Relevant local docs or source files reviewed, if any.

### Why Fix Suggestions Are Blocked
Explain what key information is missing or contradictory.

### Questions For QA Or Product
- Focused question 1.
- Focused question 2.

### Best Next Step
State the most useful next action for the user.
```

If no information exists for a section, write `Not documented.` or `Not visible in Jira.` rather than inventing details.
