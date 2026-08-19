---
name: do-ticket-work
description: Run the saved ticket implementation workflow. Use when the user says "do-ticket-work", "do ticket work", or asks to implement a ticket from prior research.
disable-model-invocation: true
---

────────────────────────
CONTEXT VERIFICATION
────────────────────────

Before doing any implementation work, verify the ticket context with the user.

Ask whether the current chat context is scoped to the prior `ticket-research` and ask what ticket to do the work against.

If the user confirms yes and identifies the ticket, continue using the prior `ticket-research` context for that ticket.

If the user says no, the context is unclear, or the ticket is not identified, ask what ticket should be worked on.

Do not assume the immediately previous research belongs to the requested implementation until the user confirms the context and ticket number.

────────────────────────
TICKET METADATA
────────────────────────

After context verification, use the ticket metadata, repository selection, investigation findings, proposed solution, and documentation generated from the confirmed prior research task.

Populate all ticket-specific and repository-specific information from that previous response and its generated documentation.

Do not ask the user to re-enter:

- Ticket number
- Ticket title
- Repository name
- Project root
- Root cause
- Proposed solution
- Impacted files
- Investigation findings

Mode: IMPLEMENTATION

────────────────────────
PREVIOUS RESEARCH FALLBACK
────────────────────────

If the immediately previous research response is not available in chat context, read:

\Documentation\Tickets\<ticket-number>\<ticket-number>.md

If the ticket number is unknown:

- Read the ticket number from the open Jira ticket.

If neither previous research context nor ticket documentation is available:

- Stop implementation.

- Respond with:

  IMPLEMENTATION BLOCKED

- Explain that implementation cannot begin because no verified research context is available.

────────────────────────
GOAL
────────────────────────

Determine whether the previous investigation provides enough verified information to safely implement the proposed fix.

Before modifying any code, verify that the research phase established:

- A clearly identified root cause.
- Root-cause confidence.
- The correct repository and project root.
- The relevant files, components, services, APIs, or database objects.
- Sufficient business requirements.
- Sufficient acceptance criteria.
- A clear proposed solution.
- Relevant edge cases.
- Enough repository evidence to implement the change safely.
- A reasonable validation and testing strategy.

Root-cause confidence rules:

- Confirmed: implementation may proceed if all other requirements are satisfied.
- Probable: implementation may proceed only if no material business-rule, repository-ownership, or expected-behavior questions remain open.
- Unknown: implementation is blocked.

If sufficient information exists, begin implementing the fix.

If sufficient information does NOT exist, do not modify code. Stop and provide a clear explanation of what additional information is required.

────────────────────────
CONSTRAINTS
────────────────────────

- Do NOT run any git commands unless explicitly requested by the user.
- Do NOT perform git operations (commit, push, merge, rebase, cherry-pick, checkout, branch creation, branch deletion, branch manipulation, status, diff, log, or blame).

- Do NOT run the application locally.
- Do NOT run tests locally, including unit tests, integration tests, Cypress tests, component tests, lint-as-test commands, or test watcher commands.
- Do NOT run local commands that start the app, build a running app environment, execute tests, or validate through a test runner.
- When validation is needed, make code changes only and state neutrally that validation is pending external results.
- Provide exact local validation commands only if the user asks for them.

- This project runs in WSL. If a shell command is necessary and permitted, use only WSL/Linux commands and paths from the WSL filesystem.
- Use the workspace path `/home/silac/Silac` and Linux-style paths such as `/home/silac/Silac/Source/admin`.
- Do NOT run project commands from Windows `cmd.exe`, PowerShell, or Windows UNC working directories.
- WSL command permission does not override the local execution restriction: do not run the application locally or run tests locally.

- Do NOT create, update, or delete any remote resources.
- Do NOT post Jira comments.
- Do NOT update Jira fields, statuses, assignees, labels, links, or attachments.
- Do NOT create or update pull requests.
- Do NOT create or update GitHub, Bitbucket, GitLab, or other source-control comments, reviews, branches, tags, releases, or metadata.

- Remote systems are read-only for this task.
- Jira and remote repository hosting systems may only be read.
- Local repository files may be read and modified only as required for the implementation, tests, validation, and ticket documentation.

- Do not modify unrelated local files.
- Do not rename, move, or delete files unless required by the implementation and supported by repository evidence.
- Do not intentionally update generated artifacts, lockfiles, snapshots, or formatting-only files unless required by the implementation or validation.

- Do NOT deploy applications or modify deployment pipelines.
- Do NOT modify infrastructure or configuration unrelated to this ticket.
- Do NOT expand the scope beyond the reported defect unless required to safely implement the fix.
- Base all conclusions on repository evidence and validation.
- Do NOT assume runtime behavior that cannot be verified.
- Preserve existing behavior for unrelated products and workflows.
- Complete investigation, implementation, validation, testing, and documentation before considering the ticket complete.
- Do NOT invent missing business rules.
- Do NOT guess expected behavior.
- Do NOT infer unsupported acceptance criteria.
- Do NOT proceed with implementation when a material requirement is ambiguous.
- Keep changes focused on the smallest safe solution that resolves the documented issue.

- For data-correction tickets, assume no production access, no database access, no deployment access, and no environment access.
- For data-correction tickets, generate artifacts only. The user executes all correction activities manually.
- Do NOT run data-correction scripts locally from this machine.
- Data-correction scripts are one-time scripts, not recurring jobs.

────────────────────────
EXECUTION REQUIREMENTS
────────────────────────

Previous Research Review

Use the immediately previous research response and generated ticket documentation to populate:

- Ticket number
- Ticket title
- Selected repository
- Project root
- Root cause
- Root-cause confidence
- Impacted files
- Business requirements
- Acceptance criteria
- Proposed solution
- Edge cases
- Recommended tests
- Known risks
- Open questions

Do not restart the investigation from scratch unless additional repository verification is required before implementation.

Implementation Readiness Review

Before making any source-code changes, verify that all material implementation questions have been answered.

Confirm:

- The reported behavior is understood.
- The expected behavior is understood.
- The root cause is supported by repository evidence.
- The root-cause confidence allows implementation.
- The repository containing the fix has been identified.
- The affected code path has been identified.
- The proposed solution is technically viable.
- The proposed solution does not conflict with existing business rules.
- Required edge cases are understood.
- A testing strategy exists.

Root-cause confidence requirements:

- Do not implement if root-cause confidence is Unknown.
- If root-cause confidence is Probable, implement only if no material business-rule, repository-ownership, or expected-behavior questions remain open.
- Otherwise, implementation is blocked.

Repository Ownership Rule

Use the repository documented as the proposed fix location.

If the research documentation identifies a primary Jira Development repository and a different secondary repository where the fix likely belongs:

- Verify that ownership decision before editing files.
- Confirm that the affected execution path exists in the selected repository.
- Confirm that the proposed implementation belongs in that repository.

If repository ownership remains ambiguous:

- Stop implementation.
- Respond with IMPLEMENTATION BLOCKED.
- Ask for clarification before modifying code.

Implementation Readiness Decision

Before modifying source files or tests, document one of:

READY TO IMPLEMENT

or

IMPLEMENTATION BLOCKED

If READY TO IMPLEMENT is selected:

- Proceed with implementation.

If IMPLEMENTATION BLOCKED is selected:

- Follow the Implementation Blocker Rule.

If any material item cannot be verified, implementation is blocked.

────────────────────────
IMPLEMENTATION BLOCKER RULE
────────────────────────

If there is NOT enough information to safely implement the fix:

- Do NOT modify source code.
- Do NOT modify tests.
- Do NOT make speculative changes.
- Do NOT guess at missing requirements.
- Stop implementation.

Respond with:

IMPLEMENTATION BLOCKED

Reason:

<concise explanation of why implementation cannot safely begin>

Missing information:

- <missing item>
- <missing item>
- <missing item>

Questions requiring clarification:

- <specific question>
- <specific question>
- <specific question>

Recommendation:

<clearly state what information, business decision, reproduction detail, or technical clarification is required before continuing>

Also update the ticket documentation with the blocker and outstanding questions.

────────────────────────
IMPLEMENTATION
────────────────────────

If enough verified information exists, begin implementing the proposed solution.

Implementation must:

- Follow the solution established during the previous research task.
- Modify only files required to resolve the issue.
- Preserve unrelated behavior.
- Follow existing repository architecture and coding conventions.
- Reuse existing patterns and utilities where appropriate.
- Avoid unnecessary refactoring.
- Handle documented edge cases safely.
- Maintain backward compatibility where required.
- Update error handling or validation only where relevant to the ticket.

Before changing a file, confirm why the file is part of the affected execution path.

If implementation reveals information that contradicts the previous research:

- Stop that portion of the implementation.
- Re-evaluate the root cause.
- Update the documentation.
- Do not force the original proposed solution if repository evidence demonstrates it was incorrect.

────────────────────────
DATA-CORRECTION TICKETS
────────────────────────

When the confirmed ticket is a data-correction ticket, follow the project data-correction rules in addition to this skill.

Use data-correction workflow only when existing data must be corrected, repaired, backfilled, normalized, migrated, or validated. Do not use it for feature work, UI fixes, API changes, refactors, or general bug fixes that do not require correcting existing data.

Before creating or editing data-correction artifacts:

- Read `Documentation/Projects/data-corrections/dc-truth.md`.
- Read `Documentation/Projects/data-corrections/data-corrections-patterns.md`.
- Review existing scripts under `Source/data-corrections/WindAPI/Script`.
- Search for similar correction examples before creating anything new.
- Reuse existing script structure, conventions, guards, naming, and style when a similar script exists.
- Document if no matching script was found and why a new pattern is required.

For data corrections, produce applicable artifacts without running them locally:

- Discovery artifact.
- Validation artifact.
- Correction artifact.
- Rollback artifact.
- Verification artifact.

Data-correction safety rules:

- Corrections must be reversible.
- Never perform correction planning without rollback planning.
- Minimize correction scope.
- Validate before correction and after correction through generated artifacts or external results.
- Document expected record counts, edge cases, risks, confirmed findings, and assumptions.
- Never create correction scripts without guarded `WHERE` clauses and expected row counts.
- Never run data-correction scripts locally from this machine.

────────────────────────
TESTING
────────────────────────

Locate the existing automated tests associated with the affected functionality.

Update or add test code or test artifacts covering:

- The reported defect.
- The expected corrected behavior.
- Relevant acceptance criteria.
- Documented edge cases.
- Existing behavior that must remain unchanged.
- Failure or validation scenarios where applicable.

Follow the existing testing patterns used by the repository.

Do not create unnecessary or unrelated tests.

Do not run tests locally. Local test execution is restricted by project rule.

For user-facing UI changes, also provide UI-level testing steps for QA.

QA steps should be written so a tester can follow them without reading the code. Include:

- Target application or environment.
- Required user role or permissions.
- Navigation path.
- Test data, policy number, ticket scenario, product, state, or configuration needed.
- Step-by-step UI actions.
- Expected visible result after each important step.
- Regression checks for nearby or previously working UI behavior.
- Any known setup, data, or environment limitations.

────────────────────────
VALIDATION
────────────────────────

Do not execute local validation commands for this project.

Do not run:

- The application locally.
- Unit tests.
- Integration tests.
- Cypress tests.
- Component tests.
- Lint-as-test commands.
- Test watcher commands.
- Commands that build a running app environment.
- Commands that validate through a test runner.

When validation is needed:

- Review modified files for unintended regressions.
- State neutrally that validation is pending external results.
- Document the relevant validation that should be performed externally.
- Provide exact validation commands only if the user asks for them.

Clearly distinguish:

- Validation that was not run because local execution is restricted by project rule.
- Static review or editor diagnostics that were actually performed.
- External validation that remains pending.
- Any known blocker that prevents validation.

Do not claim validation passed unless it was actually executed and verified.

────────────────────────
DOCUMENTATION REQUIREMENTS
────────────────────────

Use the ticket documentation file created during the previous research task:

\Documentation\Tickets\<ticket-number>\<ticket-number>.md

Populate <ticket-number> from the previous research response.

If the documentation directory does not exist, create it.

If the documentation file already exists:

- Do not overwrite prior content.
- Preserve all existing content.
- Append a dated implementation update section.

Include:

- Issue summary
- Investigation findings
- Root cause
- Root-cause confidence
- Repository evidence supporting the diagnosis
- Implementation readiness decision (READY TO IMPLEMENT or IMPLEMENTATION BLOCKED)
- Files modified
- Before/after implementation summary
- Final implementation logic
- Tests added or modified
- UI-level QA testing steps when the change is user-facing
- Validation status, including local execution restrictions and pending external validation
- External validation recommended
- Edge cases considered
- Risks or follow-up recommendations
- Final implementation time estimate
- Final implementation status
- Remaining blockers, if any

If implementation is blocked, document:

- Why implementation is blocked
- Missing information
- Outstanding questions
- Recommended next steps

────────────────────────
OUTPUT RULES
────────────────────────

Output only the required implementation artifacts and status information.

Do NOT restate this prompt.

Do NOT include unnecessary commentary.

If implementation is blocked, include:

- Ticket number and title
- Repository
- IMPLEMENTATION BLOCKED status
- Reason
- Missing information
- Questions requiring clarification
- Documentation created or updated
- Recommended next step

If implementation proceeds, include:

- Ticket number and title
- Repository
- READY TO IMPLEMENT status
- Root cause summary
- Root-cause confidence
- Files modified
- Before/after implementation summary
- Tests modified or created
- UI-level QA testing steps when the change is user-facing
- Validation status, including local execution restrictions and pending external validation
- External validation recommended
- Documentation created or updated
- Remaining risks or blockers
- Final implementation time estimate
- Final readiness determination
- One-line commit message suggestion

The one-line commit message suggestion must:

- Follow the project format `SCH-####: concise technical summary`.
- Describe only the actual code behavior modified or added for the ticket.
- Avoid agent interactions, private workflow details, documentation commands, validation logistics, generated project rules, or conversation context.
- Be exactly one line.

────────────────────────
COMPLETION CRITERIA
────────────────────────

If implementation proceeds, complete only when:

- Root cause has been identified and documented.
- Root-cause confidence is Confirmed, or Probable with no unresolved material questions.
- A READY TO IMPLEMENT decision has been documented before source edits began.
- Existing behavior for unrelated products and workflows has been preserved.
- Repository ownership has been verified.
- All documented edge cases have been handled safely.
- Relevant automated tests have been updated or added.
- Validation has been documented with local execution restrictions, verified blockers, or external results.
- Documentation has been saved to:

  \Documentation\Tickets\<ticket-number>\<ticket-number>.md

- Repository evidence supporting the diagnosis has been documented.
- No unintended regressions have been identified.
- A final implementation summary and readiness determination have been provided.
- A final implementation time estimate has been documented.
- A one-line commit message suggestion has been provided.

If implementation is blocked, complete only when:

- An IMPLEMENTATION BLOCKED decision has been documented.
- The blocker has been identified and documented.
- Missing information has been documented.
- Required clarification questions have been provided.
- No speculative code changes have been made.
- The ticket documentation has been updated with the blocker and recommended next steps.
