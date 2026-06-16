"""Evidence extraction: find the exact text that supports (or undermines) a
capability claim for a facility.

This is the "show your work" layer. Every trust score can point back to the
field and snippet that produced it, which is what lets the app say *why* a
facility was ranked the way it was.
"""

from __future__ import annotations

import re

from .capabilities import (
    CAPABILITIES,
    NEGATION_TERMS,
    VAGUE_TERMS,
)

# Map a scoring component to the facility field it reads and the keyword set
# inside the capability registry.
FIELD_FOR_COMPONENT = {
    "capability": ("capability", "capability"),
    "procedure": ("procedure", "procedure"),
    "equipment": ("equipment", "equipment"),
    "specialty": ("specialties", "specialty"),
    "description": ("description", "capability"),  # description scanned with the primary terms
}


def _norm(text) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def matched_keywords(text: str, keywords: list[str]) -> list[str]:
    """Return the keywords that appear in text (case-insensitive)."""
    t = _norm(text)
    return [kw for kw in keywords if kw.lower() in t]


def snippet_for(text: str, keyword: str, width: int = 60) -> str:
    """Return a short snippet of the original text around the matched keyword."""
    raw = str(text or "")
    idx = raw.lower().find(keyword.lower())
    if idx < 0:
        return ""
    start = max(0, idx - width // 2)
    end = min(len(raw), idx + len(keyword) + width // 2)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(raw) else ""
    return f"{prefix}{raw[start:end].strip()}{suffix}"


def extract_claims(facility: dict, capability_key: str) -> list[dict]:
    """Extract evidence claims for a capability from all relevant fields.

    Returns a list of {component, field, keyword, snippet} dicts.
    """
    spec = CAPABILITIES.get(capability_key)
    if not spec:
        return []
    claims: list[dict] = []
    for component, (field, kw_key) in FIELD_FOR_COMPONENT.items():
        keywords = spec.get(kw_key, [])
        text = facility.get(field, "")
        for kw in matched_keywords(text, keywords):
            claims.append({
                "component": component,
                "field": field,
                "keyword": kw,
                "snippet": snippet_for(text, kw),
            })
    return claims


def has_vague_language(facility: dict, capability_key: str) -> bool:
    """True if the supporting text hedges the claim (may / limited / planned…)."""
    spec = CAPABILITIES.get(capability_key, {})
    blob = " ".join(_norm(facility.get(f, "")) for f in ("description", "capability", "procedure"))
    # Only count vagueness when there is at least a primary capability mention.
    if not matched_keywords(blob, spec.get("capability", [])):
        return False
    return any(term in blob for term in VAGUE_TERMS)


def has_negation_contradiction(facility: dict, capability_key: str) -> bool:
    """True if the description explicitly negates a claimed capability.

    e.g. capability field lists "ICU" but description says "ICU not functional".
    """
    spec = CAPABILITIES.get(capability_key, {})
    desc = _norm(facility.get("description", ""))
    cap_terms = spec.get("capability", [])
    for term in cap_terms:
        t = term.lower()
        if t in desc:
            for neg in NEGATION_TERMS:
                # negation appearing within ~40 chars before/after the term
                window = desc
                i = window.find(t)
                around = window[max(0, i - 40): i + len(t) + 40]
                if neg in around:
                    return True
    return False
