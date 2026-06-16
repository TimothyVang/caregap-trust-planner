"""Persistence layer for planner actions (the Lakebase-backed part of the app).

Lakebase is a managed Postgres, so the schema here is plain Postgres-compatible
SQL. For local development (and CI / the Free Edition gap where Lakebase
instances aren't available) we fall back to an identical SQLite schema, so the
app runs end-to-end without a Databricks workspace.

Backend selection:
  * If LAKEBASE_DSN (or DATABRICKS_LAKEBASE_*) env vars are set -> Postgres via psycopg.
  * Otherwise -> local SQLite at data/app_state.db.

Tables (planner state only — heavy analytics live in Databricks SQL/Delta):
  saved_scenarios, saved_shortlists, planner_notes,
  facility_overrides, review_decisions, audit_events
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SQLITE_PATH = DATA_DIR / "app_state.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS saved_scenarios (
  scenario_id   TEXT PRIMARY KEY,
  user_id       TEXT,
  scenario_name TEXT,
  payload       TEXT,
  created_at    TEXT
);
CREATE TABLE IF NOT EXISTS saved_shortlists (
  shortlist_id  TEXT PRIMARY KEY,
  user_id       TEXT,
  scenario_name TEXT,
  facility_id   TEXT,
  capability_type TEXT,
  rank          INTEGER,
  note          TEXT,
  created_at    TEXT
);
CREATE TABLE IF NOT EXISTS planner_notes (
  note_id     TEXT PRIMARY KEY,
  user_id     TEXT,
  facility_id TEXT,
  note        TEXT,
  created_at  TEXT
);
CREATE TABLE IF NOT EXISTS facility_overrides (
  override_id   TEXT PRIMARY KEY,
  user_id       TEXT,
  facility_id   TEXT,
  capability_type TEXT,
  old_label     TEXT,
  new_label     TEXT,
  reason        TEXT,
  created_at    TEXT
);
CREATE TABLE IF NOT EXISTS review_decisions (
  review_id     TEXT PRIMARY KEY,
  user_id       TEXT,
  facility_id   TEXT,
  capability_type TEXT,
  decision      TEXT,
  note          TEXT,
  old_label     TEXT,
  new_label     TEXT,
  created_at    TEXT
);
CREATE TABLE IF NOT EXISTS audit_events (
  event_id   TEXT PRIMARY KEY,
  user_id    TEXT,
  action     TEXT,
  target     TEXT,
  detail     TEXT,
  created_at TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    # monotonic-ish id without external deps; fine for app state rows
    return _now().replace(":", "").replace(".", "").replace("-", "").replace("+", "") + os.urandom(3).hex()


def using_lakebase() -> bool:
    return bool(os.environ.get("LAKEBASE_DSN") or os.environ.get("DATABRICKS_LAKEBASE_HOST"))


def _connect():
    if using_lakebase():
        import psycopg  # only required when actually using Lakebase

        dsn = os.environ.get("LAKEBASE_DSN") or (
            f"host={os.environ['DATABRICKS_LAKEBASE_HOST']} "
            f"dbname={os.environ.get('DATABRICKS_LAKEBASE_DB', 'databricks_postgres')} "
            f"user={os.environ.get('DATABRICKS_LAKEBASE_USER', '')} "
            f"password={os.environ.get('DATABRICKS_LAKEBASE_PASSWORD', '')} "
            f"sslmode=require"
        )
        return psycopg.connect(dsn)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _ph() -> str:
    return "%s" if using_lakebase() else "?"


def init_db() -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        for stmt in filter(str.strip, SCHEMA.split(";")):
            cur.execute(stmt)
        conn.commit()
    finally:
        conn.close()


def _insert(table: str, row: dict) -> None:
    cols = ",".join(row.keys())
    marks = ",".join(_ph() for _ in row)
    conn = _connect()
    try:
        conn.cursor().execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(row.values()))
        conn.commit()
    finally:
        conn.close()


def _select(query: str, params: tuple = ()) -> list[dict]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        if using_lakebase():
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]
        return [dict(r) for r in rows]
    finally:
        conn.close()


def log_audit(user_id: str, action: str, target: str, detail: str = "") -> None:
    _insert("audit_events", {
        "event_id": _uid(), "user_id": user_id, "action": action,
        "target": target, "detail": detail, "created_at": _now(),
    })


def add_shortlist(user_id, scenario_name, facility_id, capability_type, rank, note="") -> None:
    _insert("saved_shortlists", {
        "shortlist_id": _uid(), "user_id": user_id, "scenario_name": scenario_name,
        "facility_id": facility_id, "capability_type": capability_type,
        "rank": rank, "note": note, "created_at": _now(),
    })
    log_audit(user_id, "add_shortlist", facility_id, scenario_name)


def add_note(user_id, facility_id, note) -> None:
    _insert("planner_notes", {
        "note_id": _uid(), "user_id": user_id, "facility_id": facility_id,
        "note": note, "created_at": _now(),
    })
    log_audit(user_id, "add_note", facility_id, note[:80])


def add_review_decision(user_id, facility_id, capability_type, decision, note="", old_label="", new_label="") -> None:
    _insert("review_decisions", {
        "review_id": _uid(), "user_id": user_id, "facility_id": facility_id,
        "capability_type": capability_type, "decision": decision, "note": note,
        "old_label": old_label, "new_label": new_label, "created_at": _now(),
    })
    log_audit(user_id, "review_decision", facility_id, f"{decision}:{old_label}->{new_label}")


def add_override(user_id, facility_id, capability_type, old_label, new_label, reason="") -> None:
    _insert("facility_overrides", {
        "override_id": _uid(), "user_id": user_id, "facility_id": facility_id,
        "capability_type": capability_type, "old_label": old_label,
        "new_label": new_label, "reason": reason, "created_at": _now(),
    })
    log_audit(user_id, "override", facility_id, f"{old_label}->{new_label}")


def save_scenario(user_id, scenario_name, payload) -> None:
    _insert("saved_scenarios", {
        "scenario_id": _uid(), "user_id": user_id, "scenario_name": scenario_name,
        "payload": payload, "created_at": _now(),
    })
    log_audit(user_id, "save_scenario", scenario_name)


def list_shortlists(user_id) -> list[dict]:
    return _select(f"SELECT * FROM saved_shortlists WHERE user_id={_ph()} ORDER BY created_at DESC", (user_id,))


def list_review_decisions(user_id) -> list[dict]:
    return _select(f"SELECT * FROM review_decisions WHERE user_id={_ph()} ORDER BY created_at DESC", (user_id,))


def list_notes(facility_id) -> list[dict]:
    return _select(f"SELECT * FROM planner_notes WHERE facility_id={_ph()} ORDER BY created_at DESC", (facility_id,))


def list_overrides(user_id) -> list[dict]:
    return _select(f"SELECT * FROM facility_overrides WHERE user_id={_ph()} ORDER BY created_at DESC", (user_id,))


def list_scenarios(user_id) -> list[dict]:
    return _select(f"SELECT * FROM saved_scenarios WHERE user_id={_ph()} ORDER BY created_at DESC", (user_id,))
