# CareGap Trust Planner

A Databricks App (Streamlit) for the **Databricks Apps & Agents for Good Hackathon 2026**.
It helps healthcare planners **separate real care gaps (medical deserts) from data
uncertainty (data deserts)**, rank referral options with facility-level evidence,
and persist human-review decisions.

**Core message:** we do not turn weak data into confident recommendations — we turn
weak data into visible uncertainty and human review.

- **Full plan:** [docs/PLAN.md](docs/PLAN.md)
- **Architecture / scoring / demo / limitations:** see `docs/`
- **Submission copy + checklist:** [docs/devpost.md](docs/devpost.md)

**Architecture rule:** Lakebase (Postgres) holds *user actions only*
(shortlists, notes, overrides, review decisions, audit); heavy analytics live in
Databricks SQL / Delta (`facility_scores`, `regional_gap_scores`, ...). The app
only renders UI + persists actions. Local dev falls back to SQLite.

**Run locally:** `pip install -r requirements.txt && python data/generate_synthetic.py && streamlit run app.py`

---

<!-- seeds:start -->
## Issue Tracking (Seeds)
<!-- seeds-onboard:v0.5.10 -->
<!-- seeds-onboard-schema:7 -->

This project uses [Seeds](https://github.com/jayminwest/seeds) v0.5.10 for git-native issue tracking.

**At the start of every session**, run:
```
sd prime
```

This injects session context: rules, command reference, and workflows. Pass `--format json|compact|markdown|plain|ids` on any command for agent-friendly output.

**Quick reference:**
- `sd ready` — Find unblocked work
- `sd search <query>` — Full-text search across titles + descriptions
- `sd create --title "..." --type task --priority 2` — Create issue
- `sd update <id> --status in_progress` — Claim work
- `sd close <id>` — Complete work
- `sd dep add <id> <depends-on>` — Add dependency between issues
- `sd sync` — Sync with git (run before pushing)

### Planning
Use `sd plan` when work is large or ambiguous enough that an LLM benefits from structured decomposition. Submit spawns one child seed per step; `step.blocks` uses forward semantics (step i with `blocks: [j]` means step i blocks step j, and step j gets step i's id in its `blockedBy`).

- `sd plan templates` — List built-ins (`feature`, `bug`, `refactor`) plus custom templates
- `sd plan prompt <seed-id>` — Emit a structured prompt the LLM fills in
- `sd plan submit <seed-id> --plan <file>` — Validate + spawn child seeds
- `sd plan show <pl-id>` — View sections, children, sub-plans
- `sd plan edit <id> [--name | --section <name> <text> | --step <i> --title/--priority/--type]` — In-place field edits; bumps revision
- `sd plan outcome <pl-id> --result success|partial|failure` — Record outcome (storage-only)
- `sd plan review <pl-id> --by <name>` — Record reviewer (informational)

### Before You Finish
1. Close completed issues: `sd close <id>`
2. File issues for remaining work: `sd create --title "..."`
3. Sync and push: `sd sync && git push`
<!-- seeds:end -->
