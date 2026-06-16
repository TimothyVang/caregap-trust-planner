"""Tests for the persistence layer (SQLite fallback path)."""

from src import db


def test_db_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "SQLITE_PATH", tmp_path / "app_state.db")
    # ensure local sqlite path even if env vars exist
    monkeypatch.setattr(db, "using_lakebase", lambda: False)

    db.init_db()
    db.add_shortlist("u", "scn", "F1", "icu", 1)
    db.add_note("u", "F1", "a note")
    db.add_review_decision("u", "F2", "nicu", "suspicious", "n",
                           "Contradictory evidence", "Contradictory evidence")
    db.add_override("u", "F2", "nicu", "Contradictory evidence", "No usable evidence", "bad claim")

    assert len(db.list_shortlists("u")) == 1
    assert len(db.list_notes("F1")) == 1
    assert len(db.list_review_decisions("u")) == 1
    assert len(db.list_overrides("u")) == 1


def test_audit_events_logged(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "SQLITE_PATH", tmp_path / "audit.db")
    monkeypatch.setattr(db, "using_lakebase", lambda: False)
    db.init_db()
    db.add_shortlist("u", "scn", "F1", "icu", 1)
    rows = db._select("SELECT * FROM audit_events")
    assert any(r["action"] == "add_shortlist" for r in rows)
