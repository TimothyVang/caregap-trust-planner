# Scoring Methodology — CareGap Trust Planner

This document defines how the planner scores **facility-level trust** and **regional planning confidence**. The scoring is fully explainable and matches the implementation in `src/scoring.py`.

> Guiding principle: **We do not turn weak data into confident recommendations. We turn weak data into visible uncertainty and human review.**

A trust score is a measure of **how well-evidenced a claim is**, not a measure of clinical quality. A high score means "this capability is well supported by the record," not "this is a good hospital."

---

## 1. Capabilities Scored

Each facility is scored independently per capability:

```
emergency_maternity, icu, dialysis, trauma, oncology, nicu
```

A facility can be Strong on one capability and Very weak on another. Scores are never averaged across capabilities into a single facility grade.

---

## 2. Facility Trust Score Formula

For a given facility and capability:

```
trust_score =
      25 * capability_match
    + 20 * procedure_match
    + 20 * equipment_match
    + 15 * specialty_match
    + 15 * description_match
    +  5 * source_url_present
    - 20 * contradiction_penalty
    - 10 * vague_language_penalty
    - 10 * missing_critical_field_penalty

trust_score = clamp(trust_score, 0, 100)
```

### 2.1 Positive evidence weights

| Signal | Weight | Meaning |
|--------|--------|---------|
| `capability_match` | +25 | The capability is explicitly claimed in the capability field. |
| `procedure_match` | +20 | A procedure consistent with the capability is listed. |
| `equipment_match` | +20 | Equipment consistent with the capability is listed. |
| `specialty_match` | +15 | A relevant specialty supports the capability. |
| `description_match` | +15 | The free-text description supports the capability. |
| `source_url_present` | +5 | A source URL is present (verifiability bonus). |

Procedure and equipment carry the most corroborating weight (20 each) because they are the hardest signals to fabricate accidentally — a capability claim alone (25) is necessary but not sufficient for high confidence.

### 2.2 Penalties

| Penalty | Weight | Meaning |
|---------|--------|---------|
| `contradiction_penalty` | -20 | Evidence contradicts the claim (see §4). |
| `vague_language_penalty` | -10 | Hedging / non-committal language ("may offer", "planned", "limited"). |
| `missing_critical_field_penalty` | -10 | A critical field needed to judge the capability is empty. |

The result is clamped to the range `0..100`.

---

## 3. Label Bands

The numeric score maps to a human-readable label:

| Score range | Label |
|-------------|-------|
| 80 – 100 | **Strong evidence** |
| 55 – 79 | **Partial evidence** |
| 30 – 54 | **Weak evidence** |
| 1 – 29 | **Very weak evidence** |
| 0 | **No usable evidence** |

**Override:** if the contradiction flag is set, the label becomes **Contradictory evidence** regardless of the numeric score. A contradiction is a quality signal that the planner must see, so it is never hidden behind a band.

---

## 4. Contradiction Logic

A claim is flagged **Contradictory** when either condition holds:

1. **Unsupported capability** — the capability is **claimed**, but **neither a procedure nor equipment** supports it.
   - Example: a facility claims NICU but lists no NICU procedure and no NICU equipment.
2. **Negated claim** — the **description negates** the claim.
   - Example: capability lists ICU, but the description says *"ICU not functional currently."*

When flagged:
- `contradiction_flag = true`
- the `-20 * contradiction_penalty` applies
- the label is forced to **Contradictory evidence**

Contradictions are surfaced to planners in the Review tab, not silently down-weighted. The point is to **route conflicts to a human**, not to auto-resolve them.

---

## 5. Regional Aggregation

Facility scores roll up into `regional_gap_scores` per region and capability.

### 5.1 Trust-weighted supply

Facilities are counted by label weight, so a region with three Strong facilities scores higher than a region with three Weak ones:

| Label | Supply weight |
|-------|---------------|
| Strong evidence | 1.0 |
| Partial evidence | 0.6 |
| Weak evidence | 0.3 |

```
trust_weighted_supply = sum(weight(label) for each facility in region)
```

Very weak / No usable / Contradictory facilities contribute no positive supply.

### 5.2 Planning confidence (0..100)

Planning confidence answers: **"How much should a planner trust this region's coverage picture?"**

It is built up from:
- `evidence_coverage` — how many facilities have usable evidence,
- `completeness` — how complete the records are,
- source-url coverage — verifiability across the region,

and reduced by:
- `contradiction_rate` — share of facilities with contradictions,
- `sparse_record_rate` — share of records too thin to judge.

```
planning_confidence =
    f(evidence_coverage, completeness, source_url_coverage)
    - contradiction_rate
    - sparse_record_rate     (result in 0..100)
```

Confidence bands:

| Band | Threshold |
|------|-----------|
| High | `planning_confidence >= 66` |
| Medium | `planning_confidence >= 40` |
| Low | `planning_confidence < 40` |

### 5.3 Desert label

The desert label is the headline output and is the heart of the **medical desert vs data desert** distinction:

| `desert_label` | Condition |
|----------------|-----------|
| **Likely care desert** | Low supply **and** decent confidence — we are reasonably sure care is genuinely absent. |
| **Data-poor area** | Low supply **but** low confidence — we cannot tell whether care is absent or just undocumented. |
| **Sufficient evidence** | Enough strong/partial facilities **and** decent confidence — coverage is adequately evidenced. |
| **Contradictory region** | High contradiction rate — claims conflict and the region needs review before planning. |

The critical pairing: **low supply alone is never enough to call a medical desert.** Only low supply *with* decent confidence produces "Likely care desert." Low supply with low confidence produces "Data-poor area" — a call to **collect data**, not a call to **build a hospital in the wrong place**.

---

## 6. Why Explainable Scoring Beats an Opaque LLM Score

For hackathon judges and for real planners, explainability is the differentiator:

- **Every number decomposes.** A trust score can be read back as a list of weighted signals (+25 capability, +20 procedure, -20 contradiction...). Judges can audit any single recommendation by hand.
- **Uncertainty is a first-class output, not a side effect.** The system reports confidence and desert labels explicitly. An opaque LLM "confidence" is a vibe; here it is a formula with named inputs.
- **Contradictions are routed to humans, not smoothed away.** A black-box model can average a contradiction into a middling score. This system flags it and forces review.
- **Reproducible and stable.** The same record always yields the same score. There is no temperature, no drift, no hidden prompt. Re-runs are diffable.
- **Defensible in a healthcare context.** Decision support that affects referrals and resource allocation must be explainable and auditable. A scoring formula plus an audit trail meets that bar; a single opaque LLM score does not.

The LLM (if used) belongs in **extraction** — pulling claims and evidence spans from messy text (pipeline steps 3–4). The **scoring** stays deterministic and inspectable.
