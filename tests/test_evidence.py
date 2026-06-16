"""Tests for evidence matching + contradiction detection (regression guards)."""

from src.evidence import matched_keywords
from src.scoring import score_facility

GREENFIELD = {
    "facility_id": "G", "capability": "ICU; maternity",
    "procedure": "assisted delivery", "equipment": "labour table",
    "specialties": "obstetrics",
    "description": "ICU not functional currently; maternity ward operational",
    "source_urls": "",
}


def test_word_boundary_icu_not_in_nicu():
    assert matched_keywords("advanced nicu unit", ["icu"]) == []
    assert matched_keywords("icu bed available", ["icu"]) == ["icu"]


def test_negation_is_clause_scoped():
    # ICU is explicitly negated -> contradictory
    assert score_facility(GREENFIELD, "icu")["contradiction_flag"] is True
    # maternity is operational AND supported -> NOT contradictory
    assert score_facility(GREENFIELD, "emergency_maternity")["contradiction_flag"] is False


def test_nicu_facility_not_flagged_as_icu():
    nicu_fac = {
        "facility_id": "N", "capability": "maternity; NICU",
        "procedure": "neonatal resuscitation", "equipment": "incubator; radiant warmer",
        "specialties": "neonatology", "description": "neonatal intensive care unit",
        "source_urls": "https://x",
    }
    # "icu" must not match inside "nicu" -> no false ICU claim/contradiction
    assert score_facility(nicu_fac, "icu")["components"]["capability"] == 0
    assert score_facility(nicu_fac, "nicu")["trust_label"] in ("Strong evidence", "Partial evidence")
