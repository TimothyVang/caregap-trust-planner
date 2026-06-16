-- ============================================================================
-- CareGap Trust Planner — Lakebase (managed Postgres) app-state schema
-- ============================================================================
-- Lakebase is Databricks' managed Postgres. Databricks Apps injects the
-- database credentials at runtime (host / db / user / password via the app's
-- resource binding), so no secrets are hardcoded here. For local development
-- src/db.py falls back to an identical SQLite schema at data/app_state.db.
--
-- These tables hold *planner actions only* — scenarios, shortlists, notes,
-- overrides, review decisions, and an audit trail. The heavy analytics (trust
-- scores, regional gaps) live in Databricks SQL / Delta — see
-- sql/databricks_tables.sql.
--
-- This schema is the Postgres-typed mirror of the SCHEMA constant in
-- src/db.py. Column names and primary keys match exactly; created_at uses
-- TIMESTAMPTZ here (Postgres) where src/db.py stores ISO-8601 TEXT in SQLite.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- saved_scenarios — a saved planner scenario (filters / selections) as JSON.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS saved_scenarios (
  scenario_id   TEXT PRIMARY KEY,
  user_id       TEXT,
  scenario_name TEXT,
  payload       TEXT,
  created_at    TIMESTAMPTZ
);

-- ----------------------------------------------------------------------------
-- saved_shortlists — facilities shortlisted under a named scenario, ranked.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS saved_shortlists (
  shortlist_id    TEXT PRIMARY KEY,
  user_id         TEXT,
  scenario_name   TEXT,
  facility_id     TEXT,
  capability_type TEXT,
  rank            INTEGER,
  note            TEXT,
  created_at      TIMESTAMPTZ
);

-- ----------------------------------------------------------------------------
-- planner_notes — free-text notes a planner attaches to a facility.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS planner_notes (
  note_id     TEXT PRIMARY KEY,
  user_id     TEXT,
  facility_id TEXT,
  note        TEXT,
  created_at  TIMESTAMPTZ
);

-- ----------------------------------------------------------------------------
-- facility_overrides — manual relabel of a facility's capability trust label.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS facility_overrides (
  override_id     TEXT PRIMARY KEY,
  user_id         TEXT,
  facility_id     TEXT,
  capability_type TEXT,
  old_label       TEXT,
  new_label       TEXT,
  reason          TEXT,
  created_at      TIMESTAMPTZ
);

-- ----------------------------------------------------------------------------
-- review_decisions — outcomes from the human review queue (accept/relabel/etc).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS review_decisions (
  review_id       TEXT PRIMARY KEY,
  user_id         TEXT,
  facility_id     TEXT,
  capability_type TEXT,
  decision        TEXT,
  note            TEXT,
  old_label       TEXT,
  new_label       TEXT,
  created_at      TIMESTAMPTZ
);

-- ----------------------------------------------------------------------------
-- audit_events — append-only audit trail for every planner action.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_events (
  event_id   TEXT PRIMARY KEY,
  user_id    TEXT,
  action     TEXT,
  target     TEXT,
  detail     TEXT,
  created_at TIMESTAMPTZ
);
