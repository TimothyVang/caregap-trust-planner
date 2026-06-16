"""Capability registry for CareGap Trust Planner.

Each capability defines the keyword sets used to detect supporting evidence in
the different facility text fields (capability / procedure / equipment /
specialties / description). Keeping this as data keeps the scoring engine
explainable: judges can read exactly what counts as evidence for each claim.
"""

from __future__ import annotations

# key -> display label + per-field keyword evidence
CAPABILITIES: dict[str, dict] = {
    "emergency_maternity": {
        "label": "Emergency Maternity",
        "capability": ["maternity", "obstetric", "obstetrics", "emergency obstetric", "labour", "delivery", "cemonc", "bemonc"],
        "procedure": ["caesarean", "c-section", "cesarean", "assisted delivery", "emergency delivery", "obstetric surgery"],
        "equipment": ["labour table", "delivery kit", "neonatal resuscitation", "fetal monitor", "operation theatre"],
        "specialty": ["obstetrics", "gynaecology", "gynecology", "obstetrician"],
    },
    "icu": {
        "label": "ICU",
        "capability": ["icu", "intensive care", "critical care"],
        "procedure": ["mechanical ventilation", "intubation", "central line", "critical care monitoring"],
        "equipment": ["ventilator", "icu bed", "multipara monitor", "infusion pump", "defibrillator"],
        "specialty": ["intensivist", "critical care", "anaesthesia", "anesthesia"],
    },
    "dialysis": {
        "label": "Dialysis",
        "capability": ["dialysis", "haemodialysis", "hemodialysis", "renal replacement"],
        "procedure": ["haemodialysis", "hemodialysis", "peritoneal dialysis", "av fistula"],
        "equipment": ["dialysis machine", "dialyzer", "ro plant", "reverse osmosis"],
        "specialty": ["nephrology", "nephrologist"],
    },
    "trauma": {
        "label": "Trauma",
        "capability": ["trauma", "emergency", "casualty", "accident"],
        "procedure": ["trauma surgery", "fracture fixation", "emergency laparotomy", "wound debridement"],
        "equipment": ["ct scan", "x-ray", "operation theatre", "blood bank", "ambulance"],
        "specialty": ["orthopaedics", "orthopedics", "general surgery", "emergency medicine"],
    },
    "oncology": {
        "label": "Oncology",
        "capability": ["oncology", "cancer", "tumour", "tumor"],
        "procedure": ["chemotherapy", "radiotherapy", "tumour resection", "biopsy"],
        "equipment": ["linear accelerator", "linac", "chemo daycare", "pet ct"],
        "specialty": ["oncology", "oncologist", "haematology", "radiation oncology"],
    },
    "nicu": {
        "label": "NICU",
        "capability": ["nicu", "neonatal intensive care", "newborn care", "sncu"],
        "procedure": ["neonatal ventilation", "surfactant", "phototherapy", "neonatal resuscitation"],
        "equipment": ["incubator", "neonatal ventilator", "radiant warmer", "phototherapy unit", "cpap"],
        "specialty": ["neonatology", "paediatrics", "pediatrics", "neonatologist"],
    },
}

# Words that signal a claim is hedged / non-committal.
VAGUE_TERMS = [
    "may", "might", "sometimes", "occasionally", "limited", "basic", "general",
    "planned", "proposed", "upcoming", "if available", "on request", "referral only",
]

# Negation cues used for contradiction detection.
NEGATION_TERMS = [
    "no ", "not ", "non-", "without", "unavailable", "absent", "lacks", "lacking",
    "closed", "out of service", "not functional", "non functional", "defunct",
]

# Critical fields whose absence undermines a capability claim the most.
CRITICAL_FIELDS = ["procedure", "equipment"]

# Fields used to measure record completeness for the data-desert signal.
COMPLETENESS_FIELDS = [
    "description", "capability", "procedure", "equipment", "specialties",
    "source_urls", "numberDoctors", "latitude", "longitude",
]


def capability_keys() -> list[str]:
    return list(CAPABILITIES.keys())


def capability_label(key: str) -> str:
    return CAPABILITIES.get(key, {}).get("label", key)
