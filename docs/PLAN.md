# CareGap Trust Planner — Win Plan

> The #1 message, repeated everywhere:
> **We do not turn weak data into confident recommendations. We turn weak data
> into visible uncertainty and human review.** A blank spot on the map is not
> automatically a medical desert — it may be a data desert.

## Positioning

One Databricks App that separates **medical deserts** from **data deserts**,
with evidence-backed referral/planning decisions and saved human-review actions.
Pitch it as **one planner workflow that turns facility trust into planning and
referral action** — not "we built all four tracks."

| Track | Role in the app |
|---|---|
| Medical Desert Planner (T2) | Main story — `Plan Care Gaps` tab |
| Referral Copilot (T3) | Demo action — `Refer Patient` tab |
| Facility Trust Desk (T1) | Evidence layer — trust scores + citations |
| Data Readiness Desk (T4) | Review queue — `Review Data` tab |

## Architecture decision (key risk: Lakebase on Free Edition)

Databricks Free Edition does **not** support Lakebase database instances. So use
Lakebase **only for user actions / app state**, and do heavy analytics in
Databricks SQL / Delta. App compute renders UI + persists actions only.

- **Lakebase (Postgres):** `saved_scenarios`, `saved_shortlists`, `planner_notes`,
  `facility_overrides`, `review_decisions`, `audit_events`
- **Databricks SQL / Delta:** `facility_raw`, `facility_claims`, `facility_evidence`,
  `facility_scores`, `regional_gap_scores`, `referral_candidates`
- Local dev falls back to SQLite with an identical schema (`src/db.py`).

## Three tabs

1. **Plan Care Gaps** — capability + geography + confidence mode → region card
   (desert label / planning confidence / facility counts / missing fields /
   recommended action) + a *map with humility* (red = likely gap, yellow =
   data-poor, blue = sufficient, purple = contradictory).
2. **Refer Patient** — location + need + distance + urgency → ranked candidates
   with evidence, missing fields, risk; add-to-shortlist / flag-for-review.
   Labeled "decision support, not medical advice."
3. **Review Data** — high-impact review queue (contradictions, unsupported
   claims, sparse regions) with persisted override/note/verify/suspicious.

## Scoring model (explainable on purpose)

```
trust_score = 25*capability + 20*procedure + 20*equipment + 15*specialty
            + 15*description + 5*source_url
            - 20*contradiction - 10*vague - 10*missing_critical   (clamp 0..100)
```
Labels: 80-100 Strong · 55-79 Partial · 30-54 Weak · 1-29 Very weak · 0 None ·
contradiction → Contradictory. Regional `planning_confidence` from evidence
coverage + completeness + source coverage − contradiction/sparse rates →
desert label {Likely care desert · Data-poor area · Sufficient evidence ·
Contradictory region}. See `docs/scoring_methodology.md`.

## Build order

1. Facility scoring table → 2. Regional gap table → 3. Streamlit Plan tab →
4. Evidence drawer → 5. Referral shortlist → 6. Lakebase persistence →
7. Review queue → 8. Architecture diagram → 9. README + Devpost → 10. Video.
(Do NOT start with the video; record after the seeded demo cases are stable.)

## Three seeded demo cases (see docs/demo_script.md)

1. **Strong referral** — Mumbai / emergency maternity → Sufficient evidence; KEM #1.
2. **Data desert** — Gadchiroli / NICU → Data-poor area (not medical desert).
3. **Suspicious claim** — Sunrise (Pune) claims NICU, no equipment → Contradictory + override.

## Devpost / submission

- Name: **CareGap Trust Planner**. Pitch (159 chars): "Evidence-backed Databricks
  App that separates medical deserts from data deserts and helps planners rank
  referral options with citations and uncertainty."
- Built-with: Databricks Apps, Lakebase, Databricks SQL, Databricks Free Edition,
  Python, Streamlit, PostgreSQL, Healthcare, Geospatial Analysis, Data Quality.
- Repo: https://github.com/TimothyVang/caregap-trust-planner (Apache-2.0).
- Full paste-ready copy: `docs/devpost.md`. Compliance checklist there too.

## Video (open-source tools)

Record Screenity → cut silence Auto-Editor → trim LosslessCut → edit Shotcut →
captions whisper.cpp. Target 2:20–2:40 (never 3:00). Script in `docs/demo_script.md`.

## Team split

- **Data/scoring:** ingest, normalize, trust + regional scoring, seed demo cases.
- **App/backend:** Databricks App, Lakebase tables, persistence, deploy.
- **Product/submission:** UI copy, README, Devpost, architecture diagram, video;
  keep the compliance checklist open the whole time.
