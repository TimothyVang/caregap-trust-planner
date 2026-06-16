# Judging Alignment — CareGap Trust Planner

How CareGap Trust Planner maps to the **Databricks Apps & Agents for Good Hackathon 2026** judging criteria.

> Thesis: **We do not turn weak data into confident recommendations. We turn weak data into visible uncertainty and human review.** The project separates **medical deserts** (no care) from **data deserts** (no evidence).

---

## 1. Business Applicability

**Real decision for a real role.** Healthcare planners and public-health teams must decide where to invest, where to refer, and where to verify before acting. Getting this wrong wastes scarce resources or, worse, builds in the wrong place while a real gap goes unserved.

CareGap Trust Planner supports three concrete planner workflows:
- **Plan** — assess regional coverage and whether a gap is real or just undocumented.
- **Refer** — rank referral options with facility-level evidence.
- **Review** — inspect, override, and persist decisions about suspect claims.

Outputs are decision support with an audit trail, which is exactly what an accountable planning process needs — not a one-off model output.

---

## 2. Data Relevance

**Built on a real, large dataset and the full Databricks data stack.**

- **Scale:** designed around a **10,000-record facility dataset**, processed through a 10-step pipeline (ingest → normalize → extract claims → attach evidence → score → detect contradictions → aggregate → publish app-ready tables).
- **Databricks Apps:** the UI is a Streamlit app on Databricks Apps (`app.py` / `app.yaml`).
- **Databricks SQL / Delta / Unity Catalog:** all heavy analytics — scoring, contradiction detection, regional aggregation — live in Delta tables (`facility_raw`, `facility_claims`, `facility_evidence`, `facility_scores`, `regional_gap_scores`, `referral_candidates`).
- **Lakebase:** user actions and app state (`saved_scenarios`, `saved_shortlists`, `planner_notes`, `facility_overrides`, `review_decisions`, `audit_events`) persist to Lakebase managed Postgres.

The project uses each part of the platform for what it is good at, rather than forcing everything through one component.

---

## 3. Creativity

**A genuinely original framing: deserts vs data deserts.**

Most "find the gaps" tools treat *absence of data* as *absence of care*, and confidently declare deserts where there are simply thin records. CareGap inverts that mistake:

- **Likely care desert** = low supply **and** decent confidence (we are fairly sure care is absent).
- **Data-poor area** = low supply **and** low confidence (we cannot tell — go collect data).

This single distinction is the creative core. It reframes the problem from "where are the gaps?" to "where do we actually *know* there are gaps, and where do we just lack evidence?" — a more honest and more useful question for anyone allocating real resources.

---

## 4. Thoroughness

**Every recommendation shows its evidence, its gaps, and its uncertainty.**

- **Evidence:** each facility score decomposes into named, weighted signals (capability, procedure, equipment, specialty, description, source URL).
- **Missing:** missing critical fields are recorded (`missing_fields`) and penalized, and shown to the planner.
- **Uncertainty:** regional `planning_confidence` and confidence bands (High/Medium/Low) are explicit outputs, and contradictions are flagged rather than averaged away.
- **Human review:** suspect claims are routed to the Review tab; overrides and relabels are persisted with `old_label`/`new_label`, notes, and an append-only audit trail.

Nothing is presented as a bare number. The system always shows the basis for a recommendation and the limits of that basis.

---

## 5. Well-Architected

**Right work in the right place.**

- **Precompute in Databricks.** All heavy scoring and aggregation runs in Databricks SQL / Delta (and optionally Jobs / Model Serving), offline and reproducibly.
- **App only renders and persists.** Databricks Apps compute renders the UI and writes lightweight planner actions; it does not score at request time. This keeps the interactive path fast and the heavy path cacheable and auditable.
- **Clean plane separation.** Read-mostly analytics tables are separated from write-on-interaction app-state tables.
- **Resilient to Free Edition limits.** Because Lakebase is used only for app state, and analytics live in SQL/Delta, the local build falls back to an **identical-schema SQLite** store (`src/db.py`) so the app runs without a workspace or Lakebase instance.

The result is an architecture that is fast for users, reproducible for judges, and portable across paid and Free Edition environments.

---

## Summary mapping

| Criterion | How CareGap meets it |
|-----------|----------------------|
| Business Applicability | Supports real planner decisions (Plan / Refer / Review) with an audit trail. |
| Data Relevance | 10,000-record dataset across Databricks Apps + SQL/Delta + Lakebase. |
| Creativity | Distinguishes medical deserts from data deserts. |
| Thoroughness | Every recommendation shows evidence, missing fields, and uncertainty. |
| Well-Architected | Precompute in Databricks; app only renders and persists. |
