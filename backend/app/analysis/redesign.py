"""Extra projections for the redesigned dashboard.

Adds data the four-band layout needs on top of the existing report:

- L1 headline metrics as five comparable numbers (risk, alignment, context,
  meme/virality, target-vs-intention).
- India state-level geo intensity for the region heatmap.
- A target-audience Venn: target circle vs positive/negative reaction, with the
  neutral remainder inside the target only.

Everything here is a pure projection over reactions already in hand, plus the
persona registry's sub-region tags — no new LLM calls.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.personas.schema import PersonaNode
from app.scoring.model import ScoredPersona

# Indian states/UTs a persona's sub_region codes can map onto. The registry uses
# ISO 3166-2:IN style codes (MH, DL, ...); anything unmapped falls to "national".
IN_STATE_NAMES: dict[str, str] = {
    "MH": "Maharashtra",
    "DL": "Delhi",
    "UP": "Uttar Pradesh",
    "GJ": "Gujarat",
    "KA": "Karnataka",
    "TN": "Tamil Nadu",
    "WB": "West Bengal",
    "RJ": "Rajasthan",
    "PB": "Punjab",
    "KL": "Kerala",
    "TG": "Telangana",
    "AP": "Andhra Pradesh",
    "MP": "Madhya Pradesh",
    "BR": "Bihar",
    "HR": "Haryana",
    "AS": "Assam",
}


def l1_metrics(
    scored: list[ScoredPersona],
    risk_index: float,
    band: str,
    intent_alignment: float,
    context_multiplier: float,
    target_vs_unintended: dict[str, Any],
) -> list[dict[str, Any]]:
    """The five top-of-page numbers, in a uniform shape so the UI can lay them
    out identically side by side."""
    total = sum(p.weight for p in scored) or 1.0

    # Meme / virality: audience-weighted meme_potential x amplifying behaviour.
    meme = sum(p.weight * p.reaction.risk_flags.meme_potential for p in scored) / total
    would_amplify = sum(
        p.weight
        for p in scored
        if p.reaction.likely_behavior in ("share_mocking", "criticize", "boycott")
    )
    virality = min(1.0, 0.6 * meme + 0.4 * (would_amplify / total))

    # Target vs intention: gap between how the target audience reads it and how
    # everyone else does. A large gap is the "screenshot risk".
    t_sev = target_vs_unintended.get("target", {}).get("mean_severity")
    u_sev = target_vs_unintended.get("unintended", {}).get("mean_severity")
    tvi = abs((u_sev or 0) - (t_sev or 0)) if (t_sev is not None or u_sev is not None) else 0.0

    return [
        {
            "key": "risk",
            "label": "Risk Index",
            "value": round(risk_index),
            "unit": "",
            "sub": band,
            "tone": "band",
        },
        {
            "key": "alignment",
            "label": "Intent Alignment",
            "value": round(intent_alignment),
            "unit": "%",
            "sub": "understood the message",
            "tone": "neutral",
        },
        {
            "key": "context",
            "label": "Context",
            "value": round(context_multiplier, 2),
            "unit": "×",
            "sub": "news-cycle multiplier",
            "tone": "inverted",
        },
        {
            "key": "virality",
            "label": "Meme / Virality",
            "value": round(virality * 100),
            "unit": "",
            "sub": "screenshot-and-dunk risk",
            "tone": "neutral",
        },
        {
            "key": "target_vs_intention",
            "label": "Target vs. Intention",
            "value": round(tvi * 100),
            "unit": "",
            "sub": "reaction gap outside target",
            "tone": "neutral",
        },
    ]


def india_geo(scored: list[ScoredPersona], registry: dict[str, PersonaNode]) -> dict[str, Any]:
    """State-level intensity for the India heatmap.

    A persona tagged with sub-regions spreads its weighted severity across those
    states; an India persona with no sub-region contributes to "national". Each
    state gets a signed intensity in [-1, 1]: positive (green) means favourable
    reaction dominates, negative (red) means offence dominates.
    """
    by_state_sev: dict[str, float] = defaultdict(float)
    by_state_w: dict[str, float] = defaultdict(float)

    for p in scored:
        node = registry.get(p.reaction.persona_id)
        if node is None or node.demographics.region != "IN":
            continue
        states = [s for s in node.demographics.sub_region if s in IN_STATE_NAMES] or ["national"]
        # Signed reaction: opposed -> negative, favourable -> positive.
        signed = p.reaction.severity
        if p.reaction.sentiment == "favorable":
            signed = -abs(p.reaction.severity)
        elif p.reaction.sentiment == "opposed":
            signed = abs(p.reaction.severity)
        else:
            signed = p.reaction.severity * 0.3
        for s in states:
            by_state_sev[s] += p.weight * signed
            by_state_w[s] += p.weight

    states_out = []
    for code, w in by_state_w.items():
        if w <= 0:
            continue
        intensity = by_state_sev[code] / w
        states_out.append(
            {
                "code": code,
                "name": IN_STATE_NAMES.get(code, "National"),
                "intensity": round(max(-1.0, min(1.0, intensity)), 3),
                "tone": "negative"
                if intensity > 0.15
                else "positive"
                if intensity < -0.15
                else "neutral",
            }
        )

    states_out.sort(key=lambda s: s["intensity"], reverse=True)
    return {
        "available": bool(states_out),
        "states": states_out,
        "note": "Simulated regional response. Offence in red, favourable in green.",
    }


def target_venn(
    scored: list[ScoredPersona],
    registry: dict[str, PersonaNode],
    target_age: tuple[int, int] | None,
) -> dict[str, Any]:
    """Target-audience Venn: within the target age band, what share react
    positively vs negatively; neutral sits inside the target with no overlap.

    Buckets are audience-weighted. A persona is "in target" when its age band
    overlaps the requested target band.
    """
    if not target_age:
        return {"available": False, "reason": "No target audience specified."}

    lo, hi = target_age

    def in_target(node: PersonaNode) -> bool:
        a0, a1 = node.demographics.age_band
        return not (a1 < lo or a0 > hi)

    buckets = {
        "target_positive": 0.0,
        "target_negative": 0.0,
        "target_neutral": 0.0,
        "outside_positive": 0.0,
        "outside_negative": 0.0,
    }
    total_target = 0.0

    for p in scored:
        node = registry.get(p.reaction.persona_id)
        if node is None:
            continue
        tgt = in_target(node)
        sent = p.reaction.sentiment
        pole = "positive" if sent == "favorable" else "negative" if sent == "opposed" else "neutral"
        if tgt:
            total_target += p.weight
            buckets[f"target_{pole}"] += p.weight
        elif pole != "neutral":
            buckets[f"outside_{pole}"] += p.weight

    total = sum(buckets.values()) or 1.0
    pct = {k: round(v / total, 4) for k, v in buckets.items()}

    return {
        "available": True,
        "target_age": [lo, hi],
        "target_share": round(total_target / total, 4),
        "buckets": pct,
        "note": "Neutral target audience sits inside the target with no overlap.",
    }
