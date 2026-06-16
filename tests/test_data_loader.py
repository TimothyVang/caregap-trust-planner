"""Tests for data loading + the region/review pipeline (data-agnostic).

These run against whatever ships in data/facilities_sample.csv (a real Virtue
Foundation sample). Engine correctness is pinned with synthetic fixtures in
test_scoring / test_evidence / test_geo.
"""

from collections import Counter

from src.capabilities import capability_keys
from src.data_loader import list_states, load_facilities, regional_verdict, review_queue

VALID_LABELS = {
    "Sufficient evidence", "Likely care desert",
    "Data-poor area", "Contradictory region",
}


def test_sample_dataset_loads():
    facs = load_facilities()
    assert len(facs) >= 100
    assert {"facility_id", "capability", "state", "district"} <= set(facs[0])


def test_regional_verdict_is_valid_for_densest_region():
    facs = load_facilities()
    assert list_states(facs)
    (state, district), _ = Counter(
        (f.get("state"), f.get("district")) for f in facs
    ).most_common(1)[0]
    region = [f for f in facs if f.get("state") == state and f.get("district") == district]
    summary = regional_verdict(region, "icu")["summary"]
    assert summary["desert_label"] in VALID_LABELS
    assert 0 <= summary["planning_confidence"] <= 100


def test_review_queue_shape():
    q = review_queue(load_facilities()[:300], capability_keys())
    assert isinstance(q, list)
    for item in q[:5]:
        assert {"facility_id", "capability_type", "reason", "trust_label"} <= set(item)


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
