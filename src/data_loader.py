"""Load facility data and turn it into scored facilities / regional verdicts.

Local mode reads the synthetic CSV. In Databricks, swap load_facilities() for a
Databricks SQL query against the precomputed facility_raw / facility_scores
tables — the rest of the pipeline is identical because it only consumes dicts.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .scoring import score_facility, score_region

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "data" / "facilities_sample.csv"


def load_facilities(path: str | Path = DEFAULT_CSV) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def list_states(facilities: list[dict]) -> list[str]:
    return sorted({f.get("state", "") for f in facilities if f.get("state")})


def list_districts(facilities: list[dict], state: str | None = None) -> list[str]:
    return sorted({
        f.get("district", "")
        for f in facilities
        if f.get("district") and (state is None or f.get("state") == state)
    })


def filter_region(facilities, state=None, district=None) -> list[dict]:
    out = facilities
    if state:
        out = [f for f in out if f.get("state") == state]
    if district:
        out = [f for f in out if f.get("district") == district]
    return out


def score_facilities(facilities: list[dict], capability_key: str) -> list[dict]:
    """Return [{facility, score}] for a capability across the given facilities."""
    return [{"facility": f, "score": score_facility(f, capability_key)} for f in facilities]


def regional_verdict(facilities: list[dict], capability_key: str) -> dict:
    """Score a region for a capability and return the planning verdict."""
    scored = score_facilities(facilities, capability_key)
    summary = score_region([s["score"] for s in scored], facilities)
    return {"scored": scored, "summary": summary}


def review_queue(facilities: list[dict], capability_keys: list[str]) -> list[dict]:
    """Build the high-impact human-review queue.

    Surfaces records where review matters most: contradictory claims, claims with
    no supporting evidence, and very sparse records.
    """
    items: list[dict] = []
    for f in facilities:
        for cap in capability_keys:
            s = score_facility(f, cap)
            reason = None
            if s["contradiction_flag"]:
                reason = "Claims capability but evidence is missing or contradictory"
            elif s["components"]["capability"] and s["trust_label"] in ("Very weak evidence", "No usable evidence"):
                reason = "Capability mentioned with no real supporting evidence"
            if reason:
                items.append({
                    "facility_id": f.get("facility_id"),
                    "name": f.get("name"),
                    "state": f.get("state"),
                    "district": f.get("district"),
                    "capability_type": cap,
                    "trust_label": s["trust_label"],
                    "reason": reason,
                    "missing": s["missing_fields"],
                    "score": s,
                    "facility": f,
                })
    # Prioritise contradictions first.
    items.sort(key=lambda i: (0 if "contradict" in i["reason"].lower() else 1, i["facility_id"]))
    return items
