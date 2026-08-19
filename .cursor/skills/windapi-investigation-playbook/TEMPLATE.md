# WindAPI Investigation Playbook — Section Template

Use this template when generating the playbook. Replace placeholders with analysis results.

**Output path:** `Documentation/Projects/windapi/WindAPI-Investigation-Playbook.md`

---

## Required Sections (14 total)

### SECTION 1 — System Architecture
- Main architectural layers (routes, views, serializers, services, models)
- Request lifecycle: route → view → serializer → service → model → query → response
- Important modules with paths
- Where business logic lives
- Where database queries originate

### SECTION 2 — Core Business Domains
For each domain (accounts, policies, products, riders, withdrawals, credits/deposits, configuration, migrations):
- Key files
- Key models
- Important methods
- Relationships to other domains

### SECTION 3 — Account Lifecycle
- Where accounts originate
- How policies create accounts
- How accounts are stored
- How transactions affect accounts
- How account data is returned to APIs
- Step-by-step execution trace with real file paths

### SECTION 4 — Account Value Calculation Flow
- Deposits, credits, withdrawals, interest, fees
- Rider adjustments, policy adjustments, rollup calculations
- Where each value originates
- Where transformations occur
- Where final values are aggregated
- Most important calculation files

### SECTION 5 — Withdrawal System
- Withdrawal data models
- Validation logic
- Calculation effects
- Aggregation logic
- Serialization
- Where withdrawals affect account value

### SECTION 6 — Credit and Deposit System
- Deposit storage
- Credit calculations
- Interest credits
- Aggregation logic

### SECTION 7 — Policy / Product / Rider Relationships
- Product configuration
- Rider configuration
- Rider attachment
- Rider effects on calculations

### SECTION 8 — Migration and Configuration System
- How configuration values are introduced
- Product config seeding
- Rider config seeding
- How configuration affects calculations
- Important migration files

### SECTION 9 — Investigation SQL Toolkit
Read-only queries by scenario:
- Account Investigation
- Withdrawal Investigation
- Credit Investigation
- Policy Investigation
- Rider Investigation
- Configuration Investigation
- Transaction History

Each query: SQL, purpose, required inputs, interpretation guidance.

### SECTION 10 — Top 15 Investigation Queries to Memorize
15 most important SQL queries.

### SECTION 11 — High-Risk Bug Zones
Areas where calculation/policy bugs may occur, ranked most-to-least likely.
Include exact file paths.

### SECTION 12 — Developer Memorization Guide
- Top 20 files to memorize
- Top 10 calculation methods
- Top 10 debugging entry points

### SECTION 13 — Rapid Investigation Workflow
Step-by-step process for:
- Account value mismatch
- Withdrawal discrepancy
- Missing credits
- Rider miscalculations
- Configuration problems

### SECTION 14 — WindAPI Quick Reference
Concise reference for pair programming:
- System architecture
- Account lifecycle
- Calculation flow
- Investigation SQL
- Debugging starting points

---

## Constraints
- Investigation only — no code modifications
- No migrations or schema changes
- No test execution
- Optimized for developer learning and troubleshooting
