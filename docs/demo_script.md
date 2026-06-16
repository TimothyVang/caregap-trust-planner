# Demo Script — CareGap Trust Planner

Three seeded demo cases that show the full story: a **strong, well-evidenced referral**, a **data desert (not a medical desert)**, and a **suspicious claim caught and corrected by a human**.

Dataset: `data/facilities_sample.csv` (synthetic, local placeholder for the real Databricks dataset).
App tabs: **Plan**, **Refer**, **Review**.

> The one-line message to land: **We do not turn weak data into confident recommendations. We turn weak data into visible uncertainty and human review.**

---

## Seeded facilities used in the demo

| Facility ID | Name | City | Role in demo |
|-------------|------|------|--------------|
| `MH-MUM-001` | KEM Hospital | Mumbai | Strong `emergency_maternity` — top referral |
| `MH-MUM-003` | Wadia | Mumbai | NICU coverage |
| `MH-MUM-002` | Sion | Mumbai | ICU coverage |
| `MH-GAD-001..004` | Gadchiroli facilities | Gadchiroli | Sparse / data-poor region |
| `MH-PUN-001` | Sunrise Multispeciality | Pune | Contradictory — claims NICU/ICU/oncology, no procedure/equipment |
| `MH-PUN-002` | Greenfield | Pune | Negation contradiction — "ICU not functional currently" |

---

## Case 1 — Strong Referral (Mumbai, emergency_maternity)

**Goal:** show a confident, well-evidenced recommendation and the evidence behind it.

### Steps

1. Open the **Plan** tab.
2. Region: **Mumbai**. Capability: **emergency_maternity**.
3. Read the regional summary.
4. Open the **Refer** tab, source region **Mumbai**, capability **emergency_maternity**.
5. Open the evidence drawer on the top-ranked facility.

### Expected output

- **Plan tab:** Mumbai / emergency_maternity shows desert label **"Sufficient evidence"** with a **High** planning-confidence band. The region has enough Strong/Partial facilities and decent confidence.
- **Refer tab:** **KEM Hospital (`MH-MUM-001`) ranked #1** with label **Strong evidence**.
- **Evidence drawer (KEM):** shows the decomposed score — capability match, procedure match, equipment match, specialty/description support, and source URL present. No contradiction flag, no missing critical fields.

**Talking point:** when the data is good, the app says so clearly and shows its work. The recommendation is backed by visible, per-signal evidence, not a black-box number.

---

## Case 2 — Data Desert, not Medical Desert (Gadchiroli, nicu)

**Goal:** show the core distinction — a region we **cannot judge** is labeled honestly, not declared empty.

### Steps

1. Open the **Plan** tab.
2. Region: **Gadchiroli**. Capability: **nicu**.
3. Read the desert label and the planning-confidence band.

### Expected output

- **Plan tab:** Gadchiroli / nicu shows **"Data-poor area, not medical desert"** with a **Low** planning-confidence band.
- The facilities `MH-GAD-001..004` are sparse — thin records, missing fields, little or no usable evidence — so supply is low **and** confidence is low.
- Because confidence is low, the app deliberately **does not** call this a "Likely care desert."

**Talking point:** low supply alone is not proof that care is missing. Gadchiroli is **under-documented**, so the honest action is **"go collect data here,"** not **"there is no NICU care here."** This is exactly the failure mode the project is built to prevent — turning missing data into a false confident claim.

---

## Case 3 — Suspicious Claim, Caught and Corrected (Pune)

**Goal:** show contradiction detection plus a persisted human review decision.

### Steps

1. Open the **Review** tab.
2. Locate **Sunrise Multispeciality (`MH-PUN-001`)**, capability **nicu**.
3. Inspect the contradiction explanation.
4. Apply an **override** and add a note.
5. (Optional) Show **Greenfield (`MH-PUN-002`)** as a second, different kind of contradiction.

### Expected output

- **Review tab:** Sunrise (`MH-PUN-001`) NICU is flagged **Contradictory evidence** — it claims NICU/ICU/oncology but lists **no supporting procedure or equipment** (unsupported-capability contradiction).
- The planner applies an **override** (e.g., relabels or rejects the NICU claim) and adds a **note** explaining the decision.
- The decision is **persisted**: a `review_decisions` row is written (with `old_label`, `new_label`, `decision`, `note`) and an `audit_events` entry is appended. On Free Edition / local dev this persists to the SQLite fallback via `src/db.py`; in a workspace it persists to Lakebase.
- **Greenfield (`MH-PUN-002`)** demonstrates the second contradiction type: the description **"ICU not functional currently"** negates the ICU claim, so ICU is flagged **Contradictory evidence**.

**Talking point:** the app does not silently down-weight a bad claim. It flags the conflict, routes it to a human, and records the human's decision with a full audit trail.

---

## Demo arc summary

1. **Case 1** — good data → confident, evidence-backed referral (KEM #1, "Sufficient evidence").
2. **Case 2** — missing data → honest "Data-poor area," never a fake medical desert.
3. **Case 3** — conflicting data → contradiction flagged, human overrides, decision persisted.

Together they prove the thesis: weak data becomes **visible uncertainty and human review**, never false confidence.
