"""Tests for data loading + the high-level region/review pipeline on sample data."""

from src.capabilities import capability_keys
from src.data_loader import load_facilities, regional_verdict, review_queue


def test_sample_dataset_loads():
    facs = load_facilities()
    assert len(facs) >= 20
    assert "facility_id" in facs[0]


def test_mumbai_is_sufficient_for_maternity():
    mum = [f for f in load_facilities() if f["district"] == "Mumbai"]
    v = regional_verdict(mum, "emergency_maternity")["summary"]
    assert v["desert_label"] == "Sufficient evidence"


def test_gadchiroli_is_data_poor_for_nicu():
    gad = [f for f in load_facilities() if f["district"] == "Gadchiroli"]
    v = regional_verdict(gad, "nicu")["summary"]
    assert v["desert_label"] == "Data-poor area"


def test_review_queue_flags_suspicious_facility():
    q = review_queue(load_facilities(), capability_keys())
    assert any(i["facility_id"] == "MH-PUN-001" for i in q)


def test_source_row_mapping_handles_aliases():
    from src.data_loader import _map_source_row
    row = {"facility_name": "X Hospital", "state": "Bihar", "city": "Patna",
           "lat": 25.6, "lon": 85.1, "description": "icu",
           "controlled_specialties": "critical care"}
    m = _map_source_row(row)
    assert m["name"] == "X Hospital"
    assert m["district"] == "Patna"           # city -> district alias
    assert m["latitude"] == 25.6              # lat -> latitude alias
    assert m["specialties"] == "critical care"
    assert m["facility_id"] == "X Hospital"   # falls back to name when no id
