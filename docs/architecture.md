# Architecture — CareGap Trust Planner

A Databricks App for the **Databricks Apps & Agents for Good Hackathon 2026**.

CareGap Trust Planner helps healthcare planners distinguish **real care gaps** from **data uncertainty**, rank referral options with facility-level evidence, and persist human review decisions.

> Core principle: **We do not turn weak data into confident recommendations. We turn weak data into visible uncertainty and human review.**

The system explicitly separates **medical deserts** (places that genuinely lack a capability) from **data deserts** (places where we simply do not have enough evidence to know).

---

## 1. Overview

The application is split into three planes:

1. **Presentation plane** — a Streamlit app running on Databricks Apps. App compute renders the UI and persists planner actions. It does **not** run heavy scoring.
2. **Analytics plane** — Databricks SQL / Delta tables in Unity Catalog. All trust scoring, contradiction detection, and regional aggregation is **precomputed** here and served as app-ready tables.
3. **App-state plane** — Lakebase managed Postgres, used only for user actions and saved app state (scenarios, shortlists, notes, overrides, review decisions, audit trail).

The app reads scored, app-ready tables from the analytics plane and writes only lightweight user actions to the app-state plane.

---

## 2. Architecture Diagram

```
                          CareGap Trust Planner
                          =====================

   +-------------------------------------------------------------+
   |                   DATABRICKS APP (Streamlit)                |
   |   entry point: app.py / app.yaml                            |
   |                                                             |
   |   Tabs:  [ Plan ]   [ Refer ]   [ Review ]                  |
   |   Role:  render UI  +  persist planner actions only         |
   |          (no heavy scoring on app compute)                  |
   +----------------------+-----------------+--------------------+
                          |                 |
              read (scored, app-ready)      write (user actions)
                          |                 |
                          v                 v
   +-------------------------------+   +-----------------------------+
   |   DATABRICKS SQL / DELTA      |   |   LAKEBASE (managed Postgres) |
   |   Unity Catalog               |   |   app state only             |
   |                               |   |                             |
   |   ANALYTICS (precomputed):    |   |   APP STATE (user actions): |
   |    - facility_raw             |   |    - saved_scenarios        |
   |    - facility_claims          |   |    - saved_shortlists       |
   |    - facility_evidence        |   |    - planner_notes          |
   |    - facility_scores          |   |    - facility_overrides     |
   |    - regional_gap_scores      |   |    - review_decisions       |
   |    - referral_candidates      |   |    - audit_events           |
   +---------------+---------------+   +-----------------------------+
                   ^
                   | heavy work: scoring, contradiction detection,
                   | regional aggregation (SQL / Jobs / Model Serving)
                   |
   +---------------+-------------------------------------------+
   |   10-STEP PIPELINE (offline / scheduled)                  |
   |   ingest -> normalize -> extract claims -> attach         |
   |   evidence -> score -> detect contradictions -> aggregate |
   |   -> write app-ready tables                               |
   +----------------------------------------------------------+

   LOCAL DEV FALLBACK: src/db.py serves the same app-state schema
   from SQLite when no Databricks workspace / Lakebase is available.
```

Data flow direction:
**Databricks App → reads Databricks SQL/Delta scoring tables → writes Lakebase user actions.**

---

## 3. Analytics vs App-State Table Split

The split is deliberate. Analytics tables are **read-mostly, precomputed, and large**; app-state tables are **write-on-interaction, small, and user-scoped**.

### 3.1 Analytics tables — Databricks SQL / Delta / Unity Catalog

| Table | Purpose |
|-------|---------|
| `facility_raw` | Raw ingested facility records from the source dataset. |
| `facility_claims` | Capability claims extracted from each facility's fields. |
| `facility_evidence` | Evidence snippets attached to each claim. |
| `facility_scores` | Per-facility, per-capability trust score and label. |
| `regional_gap_scores` | Regional coverage, planning confidence, and desert label. |
| `referral_candidates` | Ranked referral options per region/capability. |

### 3.2 App-state tables — Lakebase managed Postgres

| Table | Purpose |
|-------|---------|
| `saved_scenarios` | Saved planning scenarios (region + capability + filters). |
| `saved_shortlists` | Ranked referral shortlists saved by a planner. |
| `planner_notes` | Free-text planner notes. |
| `facility_overrides` | Planner overrides of facility-level fields. |
| `review_decisions` | Human review decisions (accept / reject / relabel). |
| `audit_events` | Append-only audit trail of all planner actions. |

---

## 4. Data Model — Column Lists

### facility_raw
```
facility_id, name, address, state, district, latitude, longitude,
description, capability, procedure, equipment, specialties, source_urls,
numberDoctors, capacity, yearEstablished
```

### facility_claims
```
claim_id, facility_id, capability_type, claim_text, claim_source_field,
extracted_evidence_span, extraction_method, created_at
```

### facility_scores
```
facility_id, capability_type, trust_score, trust_label, contradiction_flag,
missing_fields, explanation
```

### regional_gap_scores
```
region_id, capability_type, facilities_total, strong_facilities,
partial_facilities, weak_facilities, contradictory_facilities,
data_completeness_score, planning_confidence, desert_label
```

### saved_shortlists
```
shortlist_id, user_id, scenario_name, facility_id, capability_type,
rank, note, created_at
```

### review_decisions
```
review_id, user_id, facility_id, capability_type, decision, note,
old_label, new_label, created_at
```

---

## 5. The 10-Step Pipeline

| # | Step | Output |
|---|------|--------|
| 1 | **Ingest dataset** | `facility_raw` populated from the source facility dataset. |
| 2 | **Normalize text** | Cleaned/normalized text fields ready for extraction. |
| 3 | **Extract capability claims** | `facility_claims` — one row per facility/capability claim. |
| 4 | **Attach evidence snippets** | `facility_evidence` — supporting spans for each claim. |
| 5 | **Score facility trust** | `facility_scores.trust_score` / `trust_label` per capability. |
| 6 | **Detect contradictions** | `contradiction_flag` set on scores where evidence conflicts. |
| 7 | **Aggregate to regional coverage** | `regional_gap_scores` + `referral_candidates`. |
| 8 | **Save app-ready tables** | App-ready Delta tables published for the app to read. |
| 9 | **Lakebase for user actions** | App-state tables provisioned for planner interactions. |
| 10 | **Render app** | Streamlit Plan / Refer / Review tabs surface results. |

Steps 1–8 run offline in the analytics plane (SQL / Jobs / optional Model Serving). Steps 9–10 are the app runtime path.

---

## 6. App Runtime Notes

- **Entry point:** `app.py`, configured via `app.yaml`.
- **Framework:** Streamlit on Databricks Apps.
- **Responsibility of app compute:** render the UI and persist planner actions only. No facility scoring, contradiction detection, or regional aggregation happens on app compute at request time — those are read from precomputed tables.
- **Reads:** `facility_scores`, `regional_gap_scores`, `referral_candidates` (and supporting analytics tables) from Databricks SQL/Delta.
- **Writes:** `saved_scenarios`, `saved_shortlists`, `planner_notes`, `facility_overrides`, `review_decisions`, `audit_events` to Lakebase.

---

## 7. Why This Architecture

- **App compute is optimized for UI, not batch math.** Databricks Apps compute is sized for interactive rendering and light I/O. Scoring 10k+ records, detecting contradictions, and aggregating regions is offloaded to the engine built for it.
- **Offload heavy work to Databricks SQL / Jobs / Model Serving.** Precomputing scores means the app stays responsive, results are reproducible, and the same scored tables can be reused by reports, dashboards, or downstream jobs.
- **Clean read/write separation.** Analytics tables are read-mostly and precomputed; app-state tables are write-on-interaction and user-scoped. This keeps the interactive path fast and the heavy path cacheable.
- **Auditability by design.** Every planner action is persisted, including overrides and relabels, with an append-only `audit_events` trail — essential for a decision-support tool in a healthcare context.

---

## 8. Free Edition Lakebase Risk + Mitigation

**Risk.** Databricks **Free Edition does not support Lakebase database instances.** A demo or local build that hard-depends on Lakebase will not start there.

**Mitigation.**

1. **Use Lakebase only for user actions / app state** — never for heavy analytics. The app-state footprint is small and isolated.
2. **Do heavy analytics in Databricks SQL / Delta** — independent of Lakebase availability, so scoring and regional aggregation work regardless.
3. **Local dev fallback to SQLite with an identical schema (`src/db.py`).** The app-state tables are mirrored 1:1 in SQLite so the app runs end-to-end **without a Databricks workspace or Lakebase instance**. The persistence interface is the same; only the backend connection changes.

This makes the app portable: full Lakebase persistence in a paid workspace, identical-schema SQLite persistence locally and on Free Edition.
