"""Explainable trust + regional planning scoring.

Two levels:
  * score_facility  — capability trust for one facility (the exact additive
    formula from the product spec; transparent and judge-friendly).
  * score_region    — aggregates facility scores into a planning-confidence and
    a desert label that separates *medical deserts* from *data deserts*.
"""

from __future__ import annotations

from .capabilities import CAPABILITIES, COMPLETENESS_FIELDS, CRITICAL_FIELDS
from .evidence import (
    extract_claims,
    has_negation_contradiction,
    has_vague_language,
    matched_keywords,
)

# Component weights — keep these visible; they ARE the model.
WEIGHTS = {
    "capability": 25,
    "procedure": 20,
    "equipment": 20,
    "specialty": 15,
    "description": 15,
    "source_url": 5,
}
PENALTIES = {
    "contradiction": 20,
    "vague": 10,
    "missing_critical": 10,
}

# Confidence mode tunes how many *trustworthy* (strong/partial-evidence)
# facilities a region needs before it is called "sufficient" vs a likely desert.
# A COUNT (not summed weak supply) keeps the label robust to region size -- a
# city with 300 weak-evidence facilities is NOT "sufficient". Strict demands more
# trusted facilities + higher confidence; exploratory is more permissive.
MODE_THRESHOLDS = {
    "strict": {"min_trusted": 3, "conf_ok": 55},
    "balanced": {"min_trusted": 2, "conf_ok": 40},
    "exploratory": {"min_trusted": 1, "conf_ok": 30},
}

TRUST_LABELS = [
    (80, 100, "Strong evidence"),
    (55, 79, "Partial evidence"),
    (30, 54, "Weak evidence"),
    (1, 29, "Very weak evidence"),
    (0, 0, "No usable evidence"),
]

# Trust weight applied to each label when computing regional supply.
LABEL_SUPPLY_WEIGHT = {
    "Strong evidence": 1.0,
    "Partial evidence": 0.6,
    "Weak evidence": 0.3,
    "Very weak evidence": 0.1,
    "No usable evidence": 0.0,
    "Contradictory evidence": 0.0,
}


def _is_present(value) -> bool:
    return bool(str(value).strip()) if value is not None else False


def _component_match(facility: dict, capability_key: str) -> dict[str, int]:
    """Return 0/1 for each evidence component, based on keyword presence."""
    spec = CAPABILITIES[capability_key]
    return {
        "capability": int(bool(matched_keywords(facility.get("capability", ""), spec["capability"]))),
        "procedure": int(bool(matched_keywords(facility.get("procedure", ""), spec["procedure"]))),
        "equipment": int(bool(matched_keywords(facility.get("equipment", ""), spec["equipment"]))),
        "specialty": int(bool(matched_keywords(facility.get("specialties", ""), spec["specialty"]))),
        "description": int(bool(matched_keywords(facility.get("description", ""), spec["capability"]))),
    }


def _label_for(score: int) -> str:
    for lo, hi, label in TRUST_LABELS:
        if lo <= score <= hi:
            return label
    return "No usable evidence"


def _missing_fields(facility: dict) -> list[str]:
    return [f for f in CRITICAL_FIELDS if not _is_present(facility.get(f))]


def score_facility(facility: dict, capability_key: str) -> dict:
    """Compute capability trust for a single facility.

    trust_score =
        25*capability + 20*procedure + 20*equipment + 15*specialty
      + 15*description + 5*source_url_present
      - 20*contradiction - 10*vague - 10*missing_critical_field
    """
    match = _component_match(facility, capability_key)
    source_url_present = int(_is_present(facility.get("source_urls")))

    contradiction = has_negation_contradiction(facility, capability_key)
    # A claim with no supporting procedure/equipment is a *contradiction* only when
    # the record is otherwise substantiated — a public source URL or a reasonably
    # complete record makes the missing support suspicious. For sparse records it is
    # data-poorness, not conflict, so we do NOT call it contradictory (that is the
    # whole point of separating data deserts from medical deserts).
    claims_without_support = bool(match["capability"]) and not (match["procedure"] or match["equipment"])
    # "Substantiated" must mean *clinical* depth, not admin fields like lat/lon:
    # a public source URL, or the capability echoed in the description/specialties.
    # A bare capability tag with nothing else is data-poor, not a contradiction.
    record_substantiated = bool(source_url_present or match["description"] or match["specialty"])
    contradiction_flag = contradiction or (claims_without_support and record_substantiated)

    vague = has_vague_language(facility, capability_key)
    missing = _missing_fields(facility)
    missing_critical = bool(missing) and bool(match["capability"])

    score = (
        WEIGHTS["capability"] * match["capability"]
        + WEIGHTS["procedure"] * match["procedure"]
        + WEIGHTS["equipment"] * match["equipment"]
        + WEIGHTS["specialty"] * match["specialty"]
        + WEIGHTS["description"] * match["description"]
        + WEIGHTS["source_url"] * source_url_present
        - PENALTIES["contradiction"] * int(contradiction_flag)
        - PENALTIES["vague"] * int(vague)
        - PENALTIES["missing_critical"] * int(missing_critical)
    )
    score = max(0, min(100, score))

    label = "Contradictory evidence" if contradiction_flag else _label_for(score)

    explanation = _explain(match, source_url_present, contradiction_flag, vague, missing, label)

    return {
        "facility_id": facility.get("facility_id"),
        "capability_type": capability_key,
        "trust_score": score,
        "trust_label": label,
        "contradiction_flag": contradiction_flag,
        "missing_fields": missing,
        "components": match,
        "source_url_present": bool(source_url_present),
        "vague_language": vague,
        "claims": extract_claims(facility, capability_key),
        "explanation": explanation,
    }


def _explain(match, url, contradiction, vague, missing, label) -> str:
    parts = []
    hit = [k for k, v in match.items() if v]
    if hit:
        parts.append("supported by: " + ", ".join(hit))
    if url:
        parts.append("source URL present")
    if contradiction:
        parts.append("CONTRADICTION: claim lacks procedure/equipment support or is negated")
    if vague:
        parts.append("hedged/vague language")
    if missing:
        parts.append("missing critical field(s): " + ", ".join(missing))
    if not parts:
        parts.append("no supporting evidence found")
    return f"{label} — " + "; ".join(parts)


def field_completeness(facility: dict) -> float:
    present = sum(1 for f in COMPLETENESS_FIELDS if _is_present(facility.get(f)))
    return present / len(COMPLETENESS_FIELDS)


def score_region(facility_scores: list[dict], facilities: list[dict], mode: str = "balanced") -> dict:
    """Aggregate facility capability scores into a regional planning verdict.

    facility_scores: list of score_facility() dicts (all same capability/region)
    facilities:      the raw facility dicts (for completeness measurement)
    mode:            confidence mode (strict | balanced | exploratory)
    """
    total = len(facility_scores)
    counts = {
        "strong": 0, "partial": 0, "weak": 0,
        "very_weak": 0, "none": 0, "contradictory": 0,
    }
    key = {
        "Strong evidence": "strong",
        "Partial evidence": "partial",
        "Weak evidence": "weak",
        "Very weak evidence": "very_weak",
        "No usable evidence": "none",
        "Contradictory evidence": "contradictory",
    }
    supply = 0.0
    for s in facility_scores:
        counts[key[s["trust_label"]]] += 1
        supply += LABEL_SUPPLY_WEIGHT.get(s["trust_label"], 0.0)

    completeness = (
        sum(field_completeness(f) for f in facilities) / len(facilities)
        if facilities else 0.0
    )
    url_coverage = (
        sum(1 for s in facility_scores if s["source_url_present"]) / total if total else 0.0
    )
    evidence_coverage = (
        (counts["strong"] + counts["partial"]) / total if total else 0.0
    )
    contradiction_rate = counts["contradictory"] / total if total else 0.0
    sparse_rate = (
        sum(1 for f in facilities if field_completeness(f) < 0.5) / len(facilities)
        if facilities else 1.0
    )

    # planning_confidence in 0..100
    confidence = 100 * (
        0.35 * evidence_coverage
        + 0.25 * completeness
        + 0.20 * url_coverage
        - 0.10 * contradiction_rate
        - 0.30 * sparse_rate
        + 0.30  # base so a fully-covered region lands high
    )
    confidence = max(0, min(100, confidence))
    confidence_band = "High" if confidence >= 66 else "Medium" if confidence >= 40 else "Low"

    trusted = counts["strong"] + counts["partial"]
    desert_label = _desert_label(trusted, confidence, contradiction_rate, total, mode)

    return {
        "mode": mode,
        "facilities_total": total,
        "strong_facilities": counts["strong"],
        "partial_facilities": counts["partial"],
        "weak_facilities": counts["weak"] + counts["very_weak"],
        "contradictory_facilities": counts["contradictory"],
        "trust_weighted_supply": round(supply, 2),
        "data_completeness_score": round(completeness, 2),
        "source_url_coverage": round(url_coverage, 2),
        "contradiction_rate": round(contradiction_rate, 2),
        "sparse_record_rate": round(sparse_rate, 2),
        "planning_confidence": round(confidence, 1),
        "planning_confidence_band": confidence_band,
        "desert_label": desert_label,
        "recommended_action": _recommend(desert_label),
    }


def _desert_label(trusted: int, confidence: float, contradiction_rate: float,
                  total: int, mode: str = "balanced") -> str:
    """Classify a region. `trusted` = count of strong+partial-evidence facilities.

    The point: many facilities that merely *claim* a capability with weak evidence
    do NOT make a region 'sufficient' -- that is the data-desert vs medical-desert
    distinction applied at the regional level.
    """
    if total == 0:
        return "Data-poor area"
    if contradiction_rate >= 0.34:
        return "Contradictory region"
    th = MODE_THRESHOLDS.get(mode, MODE_THRESHOLDS["balanced"])
    conf_ok = confidence >= th["conf_ok"]
    if trusted >= th["min_trusted"] and conf_ok:
        return "Sufficient evidence"
    if not conf_ok:
        return "Data-poor area"          # can't trust the data well enough to judge
    return "Likely care desert"          # confident, but too few trustworthy facilities


def _recommend(desert_label: str) -> str:
    return {
        "Likely care desert": "Prioritise capacity planning / new facility siting; supply is genuinely thin.",
        "Data-poor area": "Do NOT overinterpret. Send records to the review queue before any planning decision.",
        "Sufficient evidence": "Coverage looks adequate; use referral tab to route patients to evidenced facilities.",
        "Contradictory region": "Investigate conflicting records; flag suspicious facilities for human verification.",
    }.get(desert_label, "Review data before acting.")
