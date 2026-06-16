# Limitations — CareGap Trust Planner

CareGap Trust Planner is built around an honest premise: **we do not turn weak data into confident recommendations; we turn weak data into visible uncertainty and human review.** That same honesty applies to the tool's own limits. This document states them plainly.

---

## 1. Decision support, not medical advice

CareGap Trust Planner is a **planning and decision-support tool**. It scores how well a facility's record **evidences** a capability — not the clinical quality, safety, or current operational status of any facility.

- A trust score is a measure of **evidence strength in the data**, not a clinical endorsement.
- Outputs must **not** be used for individual patient care, triage, or treatment decisions.
- Referral rankings are a starting point for human planning, not a directive.

All outputs require professional judgment before any real-world action.

---

## 2. Sparse data is not proof of absence

A low score or thin record means we **lack evidence**, not that care is **absent**.

- This is the central reason the tool distinguishes **Data-poor area** from **Likely care desert**: low supply with low confidence is labeled "Data-poor area," explicitly **not** a medical desert.
- Absence of evidence is treated as a prompt to **collect more data**, never as confirmation that a capability does not exist.
- Planners must not interpret a sparse region as an empty region.

---

## 3. The shipped sample is a subset of the real dataset

`data/facilities_sample.csv` is a **2,032-facility sample of the provided Virtue Foundation Dataset (DAIS 2026)**, density-weighted toward dense regions (Mumbai, Hyderabad, Ahmedabad, Chennai, Pune, Kolkata).

- It is a **subset**, taken to fit the Databricks Apps 10 MB file limit — the full 10,088-record table is installed in the workspace and queryable live via `DATABRICKS_DATASET_TABLE`.
- Because it is a subset, regional gap calls reflect only the included regions; conclusions about regions **not** in the sample cannot be drawn from the shipped file.
- Scores are computed from real but **uneven, self-reported** facility text — they are evidence signals to verify, not ground truth about what a facility can actually do.

---

## 4. Databricks Free Edition / Lakebase caveat

**Databricks Free Edition does not support Lakebase database instances.**

- Lakebase is used **only** for user actions and app state (saved scenarios, shortlists, notes, overrides, review decisions, audit events).
- On Free Edition or local dev, the app **falls back to SQLite** with an **identical schema** via `src/db.py`. App-state persistence still works, but it is local rather than a managed Lakebase instance.
- Multi-user, durable, and centrally managed persistence requires Lakebase in a paid workspace. The SQLite fallback is for portability and demos, not production-grade shared state.

---

## 5. Human verification is required

The tool is designed to **route uncertainty and conflict to a human**, and it depends on a human acting on that signal.

- **Contradictions are flagged, not resolved.** A claim marked "Contradictory evidence" requires a person to review it in the Review tab.
- **Overrides and relabels are human decisions.** The system records who decided what (`review_decisions`, `audit_events`) but does not make the call itself.
- **Confidence bands and desert labels are inputs to judgment,** not conclusions. Before any resource is committed, a qualified planner must verify the underlying evidence.

The tool is most valuable when its outputs are treated as **questions to investigate**, not answers to act on blindly.

---

## Summary

| Limitation | What it means in practice |
|------------|---------------------------|
| Decision support, not medical advice | Never use for patient-level clinical decisions. |
| Sparse data is not absence | Low evidence triggers data collection, not a desert verdict. |
| Synthetic dataset | `facilities_sample.csv` is a placeholder; results are not real. |
| Free Edition / Lakebase | App state falls back to identical-schema SQLite locally. |
| Human verification required | Contradictions and labels demand human review before action. |
