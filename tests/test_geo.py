"""Tests for geo distance + referral ranking."""

from src.geo import haversine_km, rank_referrals
from src.scoring import score_facility

ICU_STRONG = {
    "facility_id": "A", "name": "A", "latitude": 19.07, "longitude": 72.87,
    "capability": "icu", "procedure": "mechanical ventilation",
    "equipment": "ventilator; icu bed", "specialties": "critical care",
    "description": "icu", "source_urls": "https://x",
}


def test_haversine_known_distance_mumbai_pune():
    d = haversine_km(19.0760, 72.8777, 18.5204, 73.8567)
    assert 100 < d < 160


def test_haversine_zero_for_same_point():
    assert haversine_km(1, 1, 1, 1) == 0


def test_haversine_invalid_returns_inf():
    assert haversine_km(None, 1, 1, 1) == float("inf")


def test_rank_referrals_orders_and_filters():
    far = {**ICU_STRONG, "facility_id": "B", "name": "B", "latitude": 28.6, "longitude": 77.2}
    near_weak = {
        "facility_id": "C", "name": "C", "latitude": 19.08, "longitude": 72.88,
        "capability": "icu", "procedure": "", "equipment": "",
        "specialties": "", "description": "icu", "source_urls": "",
    }
    scored = [{"facility": f, "score": score_facility(f, "icu")}
              for f in (ICU_STRONG, far, near_weak)]
    ranked = rank_referrals(scored, 19.07, 72.87, max_km=50, min_label_rank=1)
    ids = [r["facility_id"] for r in ranked]

    assert "B" not in ids          # filtered: too far
    assert "C" not in ids          # filtered: contradictory (claim w/o support)
    assert ids[0] == "A"           # strong + near ranks first
    assert ranked[0]["rank"] == 1
