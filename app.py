"""CareGap Trust Planner — Databricks App (Streamlit).

Three tabs:
  1. Plan Care Gaps  — separate medical deserts from data deserts
  2. Refer Patient   — evidence-ranked referral candidates
  3. Review Data     — high-impact human-in-the-loop review queue

Heavy scoring is precomputed in Databricks tables in production; this app layer
renders UI and persists planner actions (shortlists, notes, overrides, reviews)
to Lakebase (or local SQLite in dev).
"""

from __future__ import annotations

import streamlit as st

from src import db
from src.capabilities import CAPABILITIES, capability_keys, capability_label
from src.data_loader import (
    list_districts,
    list_states,
    load_facilities,
    regional_verdict,
    review_queue,
    score_facilities,
)
from src.geo import rank_referrals

st.set_page_config(page_title="CareGap Trust Planner", page_icon="🩺", layout="wide")

USER_ID = "planner"  # in Databricks, derive from the OAuth-forwarded user header

# Facility-trust colour map (point-level). Region-level uses the desert label.
LABEL_COLOR = {
    "Strong evidence": "#1f6feb",       # blue  = sufficient evidence
    "Partial evidence": "#388bfd",      # blue
    "Weak evidence": "#d29922",         # yellow = data-poor / weak
    "Very weak evidence": "#d29922",
    "No usable evidence": "#8b949e",    # grey
    "Contradictory evidence": "#8957e5",  # purple = contradictory
}
DESERT_COLOR = {
    "Likely care desert": "#da3633",     # red
    "Data-poor area": "#d29922",         # yellow
    "Sufficient evidence": "#1f6feb",    # blue
    "Contradictory region": "#8957e5",   # purple
}

CITY_PRESETS = {
    "Mumbai (19.07, 72.87)": (19.0760, 72.8777),
    "Pune (18.52, 73.85)": (18.5204, 73.8567),
    "Gadchiroli (20.18, 80.00)": (20.1800, 80.0030),
    "Patna (25.59, 85.13)": (25.5941, 85.1376),
    "Jaipur (26.91, 75.78)": (26.9124, 75.7873),
    "Malkangiri (18.36, 81.88)": (18.3600, 81.8800),
}


@st.cache_data
def get_facilities():
    return load_facilities()


def header():
    st.title("CareGap Trust Planner")
    st.caption("Evidence-backed healthcare planning for messy facility data")
    st.markdown(
        "Separate real care gaps from data uncertainty before making referral or planning decisions."
    )


def trust_legend():
    with st.expander("Trust legend", expanded=False):
        st.markdown(
            "- **Strong evidence**: multiple fields support the claim\n"
            "- **Partial evidence**: one clear source supports the claim\n"
            "- **Weak evidence**: vague or indirect support\n"
            "- **Contradictory evidence**: fields conflict\n"
            "- **No usable evidence**: no supporting claim found"
        )


def chip(text: str, color: str) -> str:
    return (
        f"<span style='background:{color};color:white;padding:2px 10px;"
        f"border-radius:12px;font-size:0.85em'>{text}</span>"
    )


def evidence_drawer(score: dict):
    """Expandable 'why' panel for a single facility/capability score."""
    st.markdown(f"_{score['explanation']}_")
    if score["claims"]:
        st.markdown("**Supporting evidence:**")
        for c in score["claims"]:
            st.markdown(f"- `{c['field']}` → **{c['keyword']}**: {c['snippet']}")
    else:
        st.markdown("**Supporting evidence:** none found in any field.")
    if score["missing_fields"]:
        st.markdown(f"**Missing critical fields:** {', '.join(score['missing_fields'])}")
    if score["contradiction_flag"]:
        st.warning("Contradiction: capability is claimed without supporting procedure/equipment, or is negated in the description.")


# ---------------------------------------------------------------- Plan tab
def tab_plan(facilities):
    st.subheader("Plan Care Gaps")
    col = st.columns(4)
    cap = col[0].selectbox("Capability", capability_keys(), format_func=capability_label)
    state = col[1].selectbox("State", list_states(facilities))
    districts = list_districts(facilities, state)
    district = col[2].selectbox("District", districts)
    mode = col[3].select_slider("Confidence mode", ["strict", "balanced", "exploratory"], value="balanced")

    region_facs = [f for f in facilities if f.get("state") == state and f.get("district") == district]
    verdict = regional_verdict(region_facs, cap)
    s = verdict["summary"]

    st.markdown("---")
    left, right = st.columns([1, 1])
    with left:
        st.markdown(
            f"### {chip(s['desert_label'], DESERT_COLOR.get(s['desert_label'], '#444'))}",
            unsafe_allow_html=True,
        )
        st.metric("Planning confidence", f"{s['planning_confidence']} ({s['planning_confidence_band']})")
        c1, c2, c3 = st.columns(3)
        c1.metric("Facilities", s["facilities_total"])
        c2.metric("Strong/Partial", s["strong_facilities"] + s["partial_facilities"])
        c3.metric("Contradictory", s["contradictory_facilities"])
        st.markdown(f"**Data completeness:** {s['data_completeness_score']}  |  "
                    f"**Source-URL coverage:** {s['source_url_coverage']}  |  "
                    f"**Sparse-record rate:** {s['sparse_record_rate']}")
        st.info(f"**Recommended next action:** {s['recommended_action']}")
    with right:
        _render_map(verdict["scored"])

    st.warning(
        "Sparse data is not proof that care is unavailable. Low-confidence regions are "
        "labeled as data-poor, not automatically as medical deserts."
    )

    st.markdown("#### Facilities & evidence")
    for item in verdict["scored"]:
        f, sc = item["facility"], item["score"]
        title = f"{f['name']} — {sc['trust_label']} ({sc['trust_score']})"
        with st.expander(title):
            evidence_drawer(sc)


def _render_map(scored):
    points = []
    for item in scored:
        f, sc = item["facility"], item["score"]
        try:
            lat, lon = float(f["latitude"]), float(f["longitude"])
        except (TypeError, ValueError):
            continue
        points.append({"lat": lat, "lon": lon, "name": f["name"], "label": sc["trust_label"]})
    if not points:
        st.caption("No mappable facilities in this region.")
        return
    try:
        import pydeck as pdk

        def rgb(hex_):
            hex_ = hex_.lstrip("#")
            return [int(hex_[i:i + 2], 16) for i in (0, 2, 4)]

        for p in points:
            p["color"] = rgb(LABEL_COLOR.get(p["label"], "#8b949e"))
        layer = pdk.Layer(
            "ScatterplotLayer", points, get_position="[lon, lat]",
            get_fill_color="color", get_radius=2500, pickable=True, opacity=0.8,
        )
        view = pdk.ViewState(
            latitude=sum(p["lat"] for p in points) / len(points),
            longitude=sum(p["lon"] for p in points) / len(points), zoom=6,
        )
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view,
                                 tooltip={"text": "{name}\n{label}"}))
    except Exception:
        st.map([{"latitude": p["lat"], "longitude": p["lon"]} for p in points])


# ---------------------------------------------------------------- Refer tab
def tab_refer(facilities):
    st.subheader("Refer Patient")
    st.caption("Decision support for planners and coordinators. Not medical advice.")
    col = st.columns(4)
    city = col[0].selectbox("Coordinator location", list(CITY_PRESETS.keys()))
    cap = col[1].selectbox("Care need", capability_keys(), format_func=capability_label, key="refer_cap")
    max_km = col[2].slider("Max distance (km)", 5, 500, 60)
    urgency = col[3].selectbox("Urgency", ["routine", "urgent", "emergency"])
    lat, lon = CITY_PRESETS[city]
    min_rank = {"strict": 3, "balanced": 1, "exploratory": 0}["balanced"]

    scored = score_facilities(facilities, cap)
    ranked = rank_referrals(scored, lat, lon, max_km, min_label_rank=min_rank)

    if not ranked:
        st.info("No referral candidates with usable evidence within range. Widen the radius or relax evidence requirements.")
        return

    for c in ranked[:10]:
        with st.container(border=True):
            top = st.columns([3, 1, 1])
            top[0].markdown(f"**#{c['rank']} {c['name']}**  \n"
                            f"{chip(c['trust_label'], LABEL_COLOR.get(c['trust_label'], '#444'))}",
                            unsafe_allow_html=True)
            top[1].metric("Distance", f"{c['distance_km']} km")
            top[2].metric("Trust", c["trust_score"])
            st.markdown(f"**Why matched:** {c['match_reason']}")
            if c["missing"]:
                st.markdown(f"**Missing:** {', '.join(c['missing'])}")
            st.markdown(f"**Risk:** {c['risk']}")
            b1, b2 = st.columns(2)
            if b1.button("Add to shortlist", key=f"sl_{c['facility_id']}"):
                db.add_shortlist(USER_ID, f"{city}/{cap}", c["facility_id"], cap, c["rank"])
                st.success(f"Added {c['name']} to shortlist.")
            if b2.button("Flag for review", key=f"fr_{c['facility_id']}"):
                db.add_review_decision(USER_ID, c["facility_id"], cap, "flagged",
                                       note=f"Flagged from referral ({urgency})",
                                       old_label=c["trust_label"])
                st.success(f"Flagged {c['name']} for review.")

    st.warning("This is planning and coordination support, not medical advice. "
               "Human verification is required before patient routing.")


# ---------------------------------------------------------------- Review tab
def tab_review(facilities):
    st.subheader("Review Data")
    st.caption("High-impact review queue — where human judgement matters most.")
    queue = review_queue(facilities, capability_keys())
    st.markdown(f"**{len(queue)} records** need attention.")

    labels = ["Strong evidence", "Partial evidence", "Weak evidence",
              "Contradictory evidence", "No usable evidence"]
    decisions = ["Override claim", "Add note", "Mark verified", "Mark suspicious", "Send to shortlist"]

    for q in queue[:25]:
        with st.expander(f"{q['name']} · {capability_label(q['capability_type'])} · {q['trust_label']}"):
            st.markdown(f"**Why flagged:** {q['reason']}")
            evidence_drawer(q["score"])
            act = st.columns(3)
            decision = act[0].selectbox("Action", decisions, key=f"d_{q['facility_id']}_{q['capability_type']}")
            new_label = act[1].selectbox("New label (if override)", labels, key=f"nl_{q['facility_id']}_{q['capability_type']}")
            note = act[2].text_input("Note", key=f"n_{q['facility_id']}_{q['capability_type']}")
            if st.button("Save decision", key=f"sv_{q['facility_id']}_{q['capability_type']}"):
                _save_review(q, decision, new_label, note)
                st.success(f"Saved: {decision} on {q['name']}.")

    st.markdown("---")
    st.markdown("#### Your persisted decisions")
    rows = db.list_review_decisions(USER_ID)
    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.caption("No decisions saved yet.")


def _save_review(q, decision, new_label, note):
    fid, cap, old = q["facility_id"], q["capability_type"], q["trust_label"]
    if decision == "Override claim":
        db.add_override(USER_ID, fid, cap, old, new_label, reason=note)
        db.add_review_decision(USER_ID, fid, cap, "override", note, old, new_label)
    elif decision == "Add note":
        db.add_note(USER_ID, fid, note)
        db.add_review_decision(USER_ID, fid, cap, "note", note, old, old)
    elif decision == "Send to shortlist":
        db.add_shortlist(USER_ID, "review", fid, cap, 0, note)
        db.add_review_decision(USER_ID, fid, cap, "shortlisted", note, old, old)
    else:  # verified / suspicious
        d = "verified" if decision == "Mark verified" else "suspicious"
        db.add_review_decision(USER_ID, fid, cap, d, note, old, old)


def main():
    db.init_db()
    header()
    trust_legend()
    facilities = get_facilities()
    if not facilities:
        st.error("No facility data found. Run `python data/generate_synthetic.py` first.")
        return
    plan, refer, review = st.tabs(["Plan Care Gaps", "Refer Patient", "Review Data"])
    with plan:
        tab_plan(facilities)
    with refer:
        tab_refer(facilities)
    with review:
        tab_review(facilities)


if __name__ == "__main__":
    main()
