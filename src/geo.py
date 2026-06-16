"""Geo distance + referral ranking.

Pure stdlib (math only) so it stays testable without app dependencies.
"""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance between two lat/lon points, in kilometres."""
    try:
        lat1, lon1, lat2, lon2 = map(float, (lat1, lon1, lat2, lon2))
    except (TypeError, ValueError):
        return float("inf")
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(a))


def _match_reason(score: dict) -> str:
    hit = [k for k, v in score.get("components", {}).items() if v]
    return "capability + " + ", ".join(h for h in hit if h != "capability") if hit else "weak/indirect match"


def _risk_note(score: dict) -> str:
    if score["contradiction_flag"]:
        return "Claim conflicts with supporting fields — verify before routing."
    if score["vague_language"]:
        return "Source text is vague or hedged."
    if score["missing_fields"]:
        return "Missing: " + ", ".join(score["missing_fields"])
    if score["trust_label"] in ("Weak evidence", "Very weak evidence"):
        return "Thin supporting evidence."
    return "Evidence looks consistent."


def rank_referrals(
    scored_facilities: list[dict],
    origin_lat: float,
    origin_lon: float,
    max_km: float,
    min_label_rank: int = 0,
) -> list[dict]:
    """Rank facilities for referral by distance, gated by evidence quality.

    scored_facilities: list of dicts each holding 'facility' (raw) and 'score'
    (a score_facility() result). Returns ranked candidates with distance,
    match reason, missing evidence and a risk note.
    """
    label_rank = {
        "Strong evidence": 4, "Partial evidence": 3, "Weak evidence": 2,
        "Very weak evidence": 1, "No usable evidence": 0,
        "Unsupported claim": 0, "Contradictory evidence": 0,
    }
    candidates = []
    for item in scored_facilities:
        fac, score = item["facility"], item["score"]
        dist = haversine_km(origin_lat, origin_lon, fac.get("latitude"), fac.get("longitude"))
        if dist > max_km:
            continue
        if label_rank.get(score["trust_label"], 0) < min_label_rank:
            continue
        candidates.append({
            "facility_id": fac.get("facility_id"),
            "name": fac.get("name"),
            "distance_km": round(dist, 1),
            "trust_label": score["trust_label"],
            "trust_score": score["trust_score"],
            "match_reason": _match_reason(score),
            "missing": score["missing_fields"],
            "risk": _risk_note(score),
            "facility": fac,
            "score": score,
        })

    # Rank: evidence quality first, then proximity.
    candidates.sort(key=lambda c: (-label_rank.get(c["trust_label"], 0), c["distance_km"]))
    for i, c in enumerate(candidates, 1):
        c["rank"] = i
    return candidates
