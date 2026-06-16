"""Tests for the facility trust + regional planning scoring engine."""

from src.scoring import score_facility, score_region

STRONG = {
    "facility_id": "F1", "capability": "emergency obstetric; maternity",
    "procedure": "caesarean", "equipment": "fetal monitor; operation theatre",
    "specialties": "obstetrics", "description": "24x7 emergency obstetric care",
    "source_urls": "https://x", "numberDoctors": "40",
    "latitude": "19.0", "longitude": "72.8",
}
SUBSTANTIATED_CLAIM = {  # public source URL but zero supporting procedure/equipment
    "facility_id": "F2", "capability": "NICU", "procedure": "", "equipment": "",
    "specialties": "", "description": "NICU available", "source_urls": "https://x",
    "numberDoctors": "20", "latitude": "19.0", "longitude": "72.8",
}
SPARSE_CLAIM = {  # thin rural record: claims a capability with no detail and no source
    "facility_id": "F4", "capability": "NICU", "procedure": "", "equipment": "",
    "specialties": "", "description": "", "source_urls": "",
}
EMPTY = {
    "facility_id": "F3", "capability": "", "procedure": "", "equipment": "",
    "specialties": "", "description": "", "source_urls": "",
}


def test_strong_facility_scores_high():
    s = score_facility(STRONG, "emergency_maternity")
    assert s["trust_label"] == "Strong evidence"
    assert s["trust_score"] >= 80
    assert s["contradiction_flag"] is False


def test_substantiated_claim_without_support_is_contradictory():
    s = score_facility(SUBSTANTIATED_CLAIM, "nicu")
    assert s["contradiction_flag"] is True
    assert s["trust_label"] == "Contradictory evidence"


def test_sparse_claim_is_data_poor_not_contradictory():
    # The core thesis: a thin record claiming a capability is data-poor, NOT a
    # contradiction. It must not be labeled "Contradictory evidence".
    s = score_facility(SPARSE_CLAIM, "nicu")
    assert s["contradiction_flag"] is False
    assert s["trust_label"] in ("No usable evidence", "Very weak evidence", "Weak evidence")


def test_no_evidence_scores_zero():
    s = score_facility(EMPTY, "icu")
    assert s["trust_score"] == 0
    assert s["trust_label"] == "No usable evidence"


def test_score_is_clamped_0_100():
    s = score_facility(STRONG, "emergency_maternity")
    assert 0 <= s["trust_score"] <= 100


def test_region_sufficient_vs_data_poor():
    strong = [score_facility(STRONG, "emergency_maternity") for _ in range(3)]
    assert score_region(strong, [STRONG] * 3)["desert_label"] == "Sufficient evidence"
    empty = [score_facility(EMPTY, "icu")]
    assert score_region(empty, [EMPTY])["desert_label"] == "Data-poor area"


def test_confidence_mode_changes_verdict():
    # One strong facility = supply 1.0. Strict needs >=2.0 for "sufficient".
    scores = [score_facility(STRONG, "emergency_maternity")]
    facs = [STRONG]
    assert score_region(scores, facs, "strict")["desert_label"] != "Sufficient evidence"
    assert score_region(scores, facs, "exploratory")["desert_label"] == "Sufficient evidence"
