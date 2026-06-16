"""Load facility data and turn it into scored facilities / regional verdicts.

Local mode reads the synthetic CSV. In Databricks, swap load_facilities() for a
Databricks SQL query against the precomputed facility_raw / facility_scores
tables — the rest of the pipeline is identical because it only consumes dicts.
"""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path

from .scoring import score_facility, score_region

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "data" / "facilities_sample.csv"

# Map our internal facility keys to likely source-table column names. The real
# 10k hackathon dataset has 51 columns and different names (e.g. city vs
# district); confirm/adjust these once the dataset is in the workspace.
_SOURCE_ALIASES = {
    "facility_id": ["facility_id", "id", "uuid"],
    "name": ["name", "facility_name"],
    "address": ["address", "addr"],
    "state": ["state"],
    "district": ["district", "city", "pincode", "postcode"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lon", "lng"],
    "description": ["description", "desc"],
    "capability": ["capability", "capabilities"],
    "procedure": ["procedure", "procedures"],
    "equipment": ["equipment"],
    "specialties": ["specialties", "controlled_specialties", "speciality"],
    "source_urls": ["source_urls", "source_url", "sources"],
    "numberDoctors": ["numberDoctors", "number_doctors", "doctors"],
    "capacity": ["capacity", "beds"],
    "yearEstablished": ["yearEstablished", "year_established", "established"],
}


def load_facilities(path: str | Path = DEFAULT_CSV) -> list[dict]:
    """Load facilities.

    On Databricks (DATABRICKS_DATASET_TABLE set) read the provided dataset via
    Databricks SQL; otherwise read the local synthetic CSV. Any Databricks error
    falls back to the CSV so the app never hard-fails.
    """
    table = os.environ.get("DATABRICKS_DATASET_TABLE")
    if table:
        try:
            rows = _load_from_databricks(table)
            if rows:
                return rows
        except Exception as exc:  # pragma: no cover - needs a live workspace
            print(f"[data_loader] Databricks load failed: {exc}; using local CSV")
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _map_source_row(row: dict) -> dict:
    """Map a raw dataset row (lowercased keys) onto the internal facility schema."""
    mapped = {}
    for key, aliases in _SOURCE_ALIASES.items():
        value = ""
        for alias in aliases:
            if alias.lower() in row and row[alias.lower()] not in (None, ""):
                value = row[alias.lower()]
                break
        mapped[key] = value
    if not mapped["facility_id"]:
        mapped["facility_id"] = str(mapped.get("name", ""))[:40]
    return mapped


def _load_from_databricks(table: str, limit: int = 10000) -> list[dict]:  # pragma: no cover
    """Read facility_raw-style rows from a Databricks SQL table.

    Needs DATABRICKS_SERVER_HOSTNAME + DATABRICKS_HTTP_PATH and either
    DATABRICKS_TOKEN or Apps-injected OAuth. NOTE: not yet run against the live
    dataset — verify column names against the real table.
    """
    if not re.match(r"^[\w.`]+$", table):
        raise ValueError(f"unsafe table identifier: {table!r}")
    from databricks import sql  # databricks-sql-connector

    conn = sql.connect(
        server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ.get("DATABRICKS_TOKEN"),
    )
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table} LIMIT {int(limit)}")
        cols = [d[0].lower() for d in cur.description]
        return [_map_source_row(dict(zip(cols, raw))) for raw in cur.fetchall()]
    finally:
        conn.close()


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


def regional_verdict(facilities: list[dict], capability_key: str, mode: str = "balanced") -> dict:
    """Score a region for a capability and return the planning verdict."""
    scored = score_facilities(facilities, capability_key)
    summary = score_region([s["score"] for s in scored], facilities, mode)
    return {"scored": scored, "summary": summary}


# A human review queue is only useful if it is short enough for a human to work
# through. We surface the highest-impact records and cap the list; the regional
# verdict (not this queue) is what summarises whole-region data quality.
MAX_REVIEW_QUEUE = 60


def review_queue(
    facilities: list[dict],
    capability_keys: list[str],
    limit: int = MAX_REVIEW_QUEUE,
) -> list[dict]:
    """Build the high-impact, length-capped human-review queue.

    Surfaces records where review matters most: contradictory claims first
    (highest-scoring — i.e. most credible-looking conflicts — at the top), then
    capability claims with no real supporting evidence. The list is capped so it
    stays actionable; `total_flagged` on each item reports the true count behind
    the cap so nothing is silently hidden.
    """
    items: list[dict] = []
    for f in facilities:
        for cap in capability_keys:
            s = score_facility(f, cap)
            kind = s.get("contradiction_kind")
            reason = None
            # priority: 0 = explicit conflict, 1 = unsupported claim, 2 = weak-no-evidence
            if kind == "negated":
                reason, priority = "The description negates the claimed capability — a direct conflict.", 0
            elif kind == "unsupported":
                reason, priority = "Claims the capability but no procedure, equipment, or specialty backs it.", 1
            elif s["components"]["capability"] and s["trust_label"] in ("Very weak evidence", "No usable evidence"):
                reason, priority = "Capability mentioned with no real supporting evidence.", 2
            if reason:
                items.append({
                    "facility_id": f.get("facility_id"),
                    "name": f.get("name"),
                    "state": f.get("state"),
                    "district": f.get("district"),
                    "capability_type": cap,
                    "trust_label": s["trust_label"],
                    "priority": priority,
                    "reason": reason,
                    "missing": s["missing_fields"],
                    "score": s,
                    "facility": f,
                })
    # Conflicts first, then unsupported claims, then weak; within a tier the
    # highest trust_score first (the most credible-looking flags are the costliest
    # to leave unreviewed).
    items.sort(key=lambda i: (i["priority"], -i["score"]["trust_score"], str(i["facility_id"])))
    total_flagged = len(items)
    capped = items[:limit]
    for i in capped:
        i["total_flagged"] = total_flagged
    return capped
