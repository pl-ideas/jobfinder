---
name: windapi-investigation-playbook
description: >-
  Generates or updates the WindAPI Investigation Playbook by analyzing the
  windapi repository. Use when creating the investigation playbook, documenting
  WindAPI debugging workflows, or when the user asks for the playbook, investigation
  manual, WindAPI debugging guide, or account value/withdrawal/credit investigation.
---

# WindAPI Investigation Playbook Generator

Generates a complete **WindAPI Investigation Playbook** — a practical debugging manual for engineers. **Investigation only**: no code changes, migrations, schema changes, or test execution.

## Output Location

Write the playbook to: `Documentation/Projects/windapi/WindAPI-Investigation-Playbook.md`

## Repository Path

WindAPI source: `Source/windapi/` (Django app root: `Source/windapi/django/`)

---

## Generation Workflow

### Phase 1: Analysis (parallel where possible)

Use `SemanticSearch` and `Grep` across `Source/windapi/` to find:

| Area | Search targets |
|------|----------------|
| Account values | AccountValues class, PolicyValue types P/B/C/D/A |
| Policy value writes | add_premium, add_premium_policy_values, issue_policy |
| Withdrawals | Withdrawals model, systematic, ChargesLedger, NetCalculator |
| Free withdrawal | FreeWithdrawalCalculator, get_free_withdrawal |
| Credits/deposits | interest_credits, add_premium_json |
| Riders | PolicyToAnnuityRider, AnnuityIssuedPoliciesToAnnuityRiderConfig, add_rider_benefits |
| Config | PlanConfig.get_data, get_config_data |
| Migrations | migrations folder, RunSQL/RunPython for seed data |
| URL routes | app/urls.py, annuity_policies/urls.py |

### Phase 2: Document

Produce a single markdown file with exactly **14 sections** below. For detailed prompts, see [TEMPLATE.md](TEMPLATE.md).

---

## Required 14 Sections

### 1. System Architecture

- Main layers (route → view → serializer → service → model)
- Request lifecycle
- Important modules and where business logic lives
- Where DB queries originate

### 2. Core Business Domains

For each domain (accounts, policies, products, riders, withdrawals, credits/deposits, configuration, migrations):

- Key files
- Key models
- Important methods
- Relationships to other domains

### 3. Account Lifecycle

- Where accounts originate
- How policies create accounts
- How transactions affect accounts
- How account data is returned to APIs
- Step-by-step trace with real file paths

### 4. Account Value Calculation Flow

- All components: deposits, credits, withdrawals, interest, fees, rider adjustments
- Where each value originates
- Where transformations occur
- Where final values are aggregated/returned
- Most important calculation files

### 5. Withdrawal System

- Data models, validation, calculation effects
- Aggregation logic, serialization, API responses
- Where withdrawals affect account value

### 6. Credit and Deposit System

- Deposit storage, credit calculations, interest credits
- Aggregation logic

### 7. Policy / Product / Rider Relationships

- Product configuration
- Rider configuration and attachment
- Rider effects on calculations

### 8. Migration and Configuration System

- How config values are introduced
- Product/rider config seeding
- How config affects calculations
- Important migration files

### 9. Investigation SQL Toolkit

Read-only, short, practical queries. Group by: Account, Withdrawal, Credit, Policy, Rider, Configuration, Transaction History.

Each query: SQL, purpose, required inputs, interpretation guidance.

### 10. Top 15 Investigation Queries to Memorize

The 15 most important SQL queries developers should memorize.

### 11. High-Risk Bug Zones

Areas where calculation/policy bugs may occur. Rank most → least likely. Include exact file paths.

### 12. Developer Memorization Guide

- Top 20 files to memorize
- Top 10 calculation methods
- Top 10 debugging entry points

### 13. Rapid Investigation Workflow

Step-by-step for: account value mismatch, withdrawal discrepancy, missing credits, rider miscalculations, configuration problems.

### 14. WindAPI Quick Reference

Concise reference: architecture, account lifecycle, calculation flow, investigation SQL, debugging starting points.

---

## Key File Discovery

Start exploration with:

- `annuity_policies/account_values.py` — AccountValues
- `annuity_policies/policy_value.py` — PolicyValue writes
- `annuity_policies/helper.py` — MVA, withdrawal charge, bonus recovery
- `annuity_withdrawals/free_withdrawal_calculator.py`
- `annuity_withdrawals/net_calculator.py`
- `annuity_config/models/plan_config.py`
- `app/urls.py` — main routes
- `annuity_policies/tasks.py` — generate_approved_policy

---

## Additional Resources

- For detailed section content prompts, see [TEMPLATE.md](TEMPLATE.md)

## Constraints

- **Investigation only** — no code modifications
- Queries must be **read-only**
- Output optimized for developer learning and troubleshooting
- Use real file paths from the codebase
- Add a note in Section 9 that table names may vary (check model `Meta.db_table`)
