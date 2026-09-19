"""Pure projections over the Reaction Object.

14 of the 24 dashboard analyses live here. Every function is a group-by, pivot,
filter, or sort over reactions already in hand — no LLM calls, no embeddings,
no extra cost. This is what the schema design in ``personas/schema.py`` buys.

Panel numbers refer to §16 of the plan.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.config import settings
from app.personas.schema import RISK_DIMENSIONS, PersonaNode, ReactionObject
from app.scoring.model import ScoredPersona

# --------------------------------------------------------------------------
# Panel 2 — Persona Reactions
# --------------------------------------------------------------------------


def persona_reactions(
    scored: list[ScoredPersona], registry: dict[str, PersonaNode]
) -> list[dict[str, Any]]:
    """The base object rendered per persona, sorted by severity."""
    rows = []
    for p in scored:
        node = registry.get(p.reaction.persona_id)
        r = p.reaction
        rows.append(
            {
                "persona_id": r.persona_id,
                "label": node.label if node else r.persona_id,
                "region": node.demographics.region if node else None,
                "severity": r.severity,
                "confidence": r.confidence,
                "emotion": r.emotion,
                "emotion_intensity": r.emotion_intensity,
                "sentiment": r.sentiment,
                "comprehension": r.interpretation.comprehension,
                "intent_alignment": r.interpretation.intent_alignment,
                "paraphrase": r.interpretation.paraphrase,
                "perceived_intent": r.interpretation.perceived_intent,
                "likely_behavior": r.likely_behavior,
                "likely_comment": r.likely_comment.model_dump(),
                "charitable_reading": r.charitable_reading,
                "hostile_reading": r.hostile_reading,
                "triggers": [t.model_dump() for t in r.triggers],
                "prevalence_weight": p.weight,
            }
        )
    return sorted(rows, key=lambda r: r["severity"], reverse=True)


# --------------------------------------------------------------------------
# Panel 3 — Why Is It Risky?
# --------------------------------------------------------------------------


def why_risky(scored: list[ScoredPersona]) -> dict[str, list[dict[str, Any]]]:
    """Triggers grouped by modality: word / phrase / visual / reference / tone / context."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in scored:
        for t in p.reaction.triggers:
            if t.valence == "positive":
                continue
            grouped[t.modality].append(
                {
                    "span": t.span,
                    "why": t.why,
                    "valence": t.valence,
                    "persona_id": p.reaction.persona_id,
                    "severity": p.reaction.severity,
                }
            )
    for items in grouped.values():
        items.sort(key=lambda x: x["severity"], reverse=True)
    return dict(grouped)


# --------------------------------------------------------------------------
# Panel 5 — Emotional Response  (+ §11.3 polarization)
# --------------------------------------------------------------------------

_POSITIVE_EMOTIONS = {"positive", "amused", "curious"}
_NEGATIVE_EMOTIONS = {"offended", "uncomfortable"}


def emotional_response(scored: list[ScoredPersona]) -> dict[str, Any]:
    """Prevalence-weighted emotion distribution, so it reflects the audience
    rather than the persona roster."""
    total_w = sum(p.weight for p in scored) or 1.0
    dist: dict[str, float] = defaultdict(float)
    for p in scored:
        dist[p.reaction.emotion] += p.weight / total_w

    by_persona = [
        {
            "persona_id": p.reaction.persona_id,
            "emotion": p.reaction.emotion,
            "intensity": p.reaction.emotion_intensity,
        }
        for p in scored
    ]

    return {
        "distribution": {k: round(v, 4) for k, v in sorted(dist.items())},
        "by_persona": by_persona,
        "polarization": polarization_index(scored),
    }


def polarization_index(scored: list[ScoredPersona]) -> float:
    """§11.3 — maximized when the audience splits into strong love and strong hate.

    The "Bud Light number": polarizing campaigns often score moderately on mean
    risk while being existentially dangerous, because the danger is the split,
    not the average.
    """
    pos = sum(
        p.weight * p.reaction.emotion_intensity
        for p in scored
        if p.reaction.emotion in _POSITIVE_EMOTIONS
    )
    neg = sum(
        p.weight * p.reaction.emotion_intensity
        for p in scored
        if p.reaction.emotion in _NEGATIVE_EMOTIONS
    )
    total = sum(p.weight * p.reaction.emotion_intensity for p in scored)
    if total <= 0:
        return 0.0
    denom = (total / 2) ** 2
    if denom <= 0:
        return 0.0
    return round(min(1.0, (pos * neg) / denom), 4)


# --------------------------------------------------------------------------
# Panel 7 — Risk Anatomy
# --------------------------------------------------------------------------


def risk_anatomy(scored: list[ScoredPersona]) -> dict[str, float]:
    """R_d = weighted mass per risk dimension (§12.2).

    The *shape* is diagnostic: a spike on `confusion` with flat `cultural` means
    a clarity problem, not a sensitivity problem — and sends the marketer to a
    completely different rewrite strategy.
    """
    denom = sum(p.weight * p.confidence for p in scored)
    if denom <= 0:
        return {d: 0.0 for d in RISK_DIMENSIONS}

    out: dict[str, float] = {}
    for d in RISK_DIMENSIONS:
        num = sum(p.weight * p.confidence * getattr(p.reaction.risk_flags, d) for p in scored)
        out[d] = round(num / denom, 4)
    return out


# --------------------------------------------------------------------------
# Panel 8 — Severity x Likelihood
# --------------------------------------------------------------------------


def severity_likelihood_matrix(scored: list[ScoredPersona]) -> list[dict[str, Any]]:
    """§12.1. Likelihood comes from prevalence weights, NEVER from an LLM's
    self-estimate: a model asked "how likely is this?" returns an opinion, while
    a prevalence weight is a population parameter you can defend to a client."""
    theta = settings.risk_flag_threshold
    rows = []

    for d in RISK_DIMENSIONS:
        firing = [p for p in scored if getattr(p.reaction.risk_flags, d) > theta]
        likelihood = sum(p.weight for p in firing)

        denom = sum(p.weight * p.confidence * getattr(p.reaction.risk_flags, d) for p in scored)
        if denom > 0:
            severity = (
                sum(
                    p.weight * p.confidence * getattr(p.reaction.risk_flags, d) * p.severity
                    for p in scored
                )
                / denom
            )
        else:
            severity = 0.0

        rows.append(
            {
                "dimension": d,
                "likelihood": round(min(1.0, likelihood), 4),
                "severity": round(severity, 4),
                "affected_personas": [p.reaction.persona_id for p in firing],
                "quadrant": _quadrant(min(1.0, likelihood), severity),
            }
        )
    return rows


def _quadrant(likelihood: float, severity: float) -> str:
    hi_l, hi_s = likelihood >= 0.35, severity >= 0.5
    if hi_l and hi_s:
        return "Fix Now"
    if hi_l:
        return "Contain"
    if hi_s:
        return "Prepare"
    return "Monitor"


# --------------------------------------------------------------------------
# Panel 9 — Trigger Detection
# --------------------------------------------------------------------------


def trigger_index(scored: list[ScoredPersona]) -> list[dict[str, Any]]:
    """Inverted index: span -> personas triggered. Exact, via character offsets.

    This is the composer's primary surface — the marketer edits directly here.
    """
    by_span: dict[tuple[int, int, str], dict[str, Any]] = {}

    for p in scored:
        for t in p.reaction.triggers:
            key = (t.char_start, t.char_end, t.span)
            entry = by_span.setdefault(
                key,
                {
                    "span": t.span,
                    "char_start": t.char_start,
                    "char_end": t.char_end,
                    "modality": t.modality,
                    "personas": [],
                    "max_severity": 0.0,
                    "audience_mass": 0.0,
                },
            )
            entry["personas"].append(
                {
                    "persona_id": p.reaction.persona_id,
                    "why": t.why,
                    "valence": t.valence,
                    "severity": p.reaction.severity,
                }
            )
            entry["max_severity"] = max(entry["max_severity"], p.reaction.severity)
            entry["audience_mass"] += p.weight

    rows = list(by_span.values())
    for r in rows:
        r["audience_mass"] = round(r["audience_mass"], 4)
        r["persona_count"] = len(r["personas"])
    return sorted(rows, key=lambda r: (r["max_severity"], r["audience_mass"]), reverse=True)


# --------------------------------------------------------------------------
# Panel 11 — Audience Heatmap
# --------------------------------------------------------------------------


def audience_heatmap(
    scored: list[ScoredPersona], registry: dict[str, PersonaNode], facet: str = "region"
) -> dict[str, Any]:
    """Persona x emotion pivot, facetable by a registry demographic attribute."""
    cells = []
    for p in scored:
        node = registry.get(p.reaction.persona_id)
        if node is None:
            continue
        facet_value: Any
        if facet == "region":
            facet_value = node.demographics.region
        elif facet == "age_band":
            facet_value = f"{node.demographics.age_band[0]}-{node.demographics.age_band[1]}"
        elif facet == "language":
            facet_value = node.demographics.languages[0] if node.demographics.languages else "—"
        elif facet == "audience_type":
            facet_value = node.demographics.audience_type
        else:
            facet_value = node.demographics.region

        cells.append(
            {
                "persona_id": p.reaction.persona_id,
                "label": node.label,
                "facet": facet_value,
                "emotion": p.reaction.emotion,
                "intensity": p.reaction.emotion_intensity,
                "severity": p.reaction.severity,
                "weight": p.weight,
            }
        )
    return {"facet": facet, "cells": cells}


# --------------------------------------------------------------------------
# Panel 12 — Region Heatmap
# --------------------------------------------------------------------------


def region_heatmap(
    scored: list[ScoredPersona], registry: dict[str, PersonaNode]
) -> list[dict[str, Any]]:
    by_region: dict[str, list[ScoredPersona]] = defaultdict(list)
    for p in scored:
        node = registry.get(p.reaction.persona_id)
        if node:
            by_region[node.demographics.region].append(p)

    rows = []
    for region, members in sorted(by_region.items()):
        w = sum(m.weight for m in members) or 1.0
        rows.append(
            {
                "region": region,
                "mean_severity": round(sum(m.severity * m.weight for m in members) / w, 4),
                "mean_intent_alignment": round(
                    sum(m.reaction.interpretation.intent_alignment * m.weight for m in members) / w,
                    4,
                ),
                "persona_count": len(members),
                "personas": [m.reaction.persona_id for m in members],
                "dominant_emotion": max(
                    {m.reaction.emotion for m in members},
                    key=lambda e: sum(m.weight for m in members if m.reaction.emotion == e),
                ),
            }
        )
    return sorted(rows, key=lambda r: r["mean_severity"], reverse=True)


# --------------------------------------------------------------------------
# Panel 16 — Target vs Unintended Audience
# --------------------------------------------------------------------------


def target_vs_unintended(
    scored: list[ScoredPersona], registry: dict[str, PersonaNode]
) -> dict[str, Any]:
    """The gap between these is the overlap risk: copy that works on your target
    and fails on everyone else is still a crisis, because everyone else is who
    screenshots it."""

    def summarize(group: list[ScoredPersona]) -> dict[str, Any]:
        if not group:
            return {"persona_count": 0}
        w = sum(p.weight for p in group) or 1.0
        return {
            "persona_count": len(group),
            "mean_severity": round(sum(p.severity * p.weight for p in group) / w, 4),
            "mean_intent_alignment": round(
                sum(p.reaction.interpretation.intent_alignment * p.weight for p in group) / w, 4
            ),
            "opposed_share": round(sum(p.weight for p in group if p.reaction.is_opposed) / w, 4),
            "personas": [p.reaction.persona_id for p in group],
        }

    target, unintended = [], []
    for p in scored:
        node = registry.get(p.reaction.persona_id)
        (target if node and node.is_target else unintended).append(p)

    t, u = summarize(target), summarize(unintended)
    gap = None
    if t.get("persona_count") and u.get("persona_count"):
        gap = round(u["mean_severity"] - t["mean_severity"], 4)

    return {"target": t, "unintended": u, "severity_gap": gap}


# --------------------------------------------------------------------------
# Panel 17 — Controversial vs Misunderstood
# --------------------------------------------------------------------------


def controversial_vs_misunderstood(scored: list[ScoredPersona]) -> dict[str, Any]:
    """§10.4 — the 2x2 that tells a marketer WHICH problem they have.

    Each quadrant demands a different response, and a single risk number cannot
    distinguish them. This is the core argument for interpretation-first design.
    """
    points = []
    counts: dict[str, float] = defaultdict(float)

    for p in scored:
        r = p.reaction
        x = r.interpretation.intent_alignment  # comprehension
        y = r.severity if r.is_opposed else 0.0  # opposition

        if x >= 0.5 and y >= 0.4:
            q = "Controversial"  # understood and rejected -> decide
        elif x < 0.5 and y >= 0.4:
            q = "Misunderstood"  # misread and reacted -> clarify
        elif x >= 0.5:
            q = "Aligned"  # landed as intended -> ship
        else:
            q = "Invisible"  # did not land -> rewrite for clarity

        points.append(
            {
                "persona_id": r.persona_id,
                "comprehension": round(x, 4),
                "opposition": round(y, 4),
                "quadrant": q,
                "weight": p.weight,
            }
        )
        counts[q] += p.weight

    total = sum(counts.values()) or 1.0
    return {
        "points": points,
        "mass": {k: round(v / total, 4) for k, v in sorted(counts.items())},
        "prescriptions": {
            "Controversial": "Understood and rejected — decide whether you accept the cost",
            "Misunderstood": "Misread and reacted — clarify; this is fixable",
            "Aligned": "Landed as intended — ship",
            "Invisible": "Did not land at all — rewrite for clarity, not safety",
        },
    }


# --------------------------------------------------------------------------
# Panel 18 — Simulated Comment Section
# --------------------------------------------------------------------------


def simulated_comments(
    scored: list[ScoredPersona], registry: dict[str, PersonaNode]
) -> list[dict[str, Any]]:
    """A mock feed, prevalence-ordered so it reads like the real distribution.

    This is the panel that makes risk viscerally legible to a non-technical
    stakeholder. A CMO who reads twelve simulated comments understands the
    problem instantly.
    """
    rows = []
    for p in scored:
        node = registry.get(p.reaction.persona_id)
        rows.append(
            {
                "persona_id": p.reaction.persona_id,
                "label": node.label if node else p.reaction.persona_id,
                "text": p.reaction.likely_comment.text,
                "tone": p.reaction.likely_comment.tone,
                "emotion": p.reaction.emotion,
                "weight": p.weight,
                "behavior": p.reaction.likely_behavior,
            }
        )
    return sorted(rows, key=lambda r: r["weight"], reverse=True)


# --------------------------------------------------------------------------
# Panel 19 — Meme / Virality Potential (projection part)
# --------------------------------------------------------------------------


def meme_potential(scored: list[ScoredPersona]) -> dict[str, Any]:
    denom = sum(p.weight for p in scored) or 1.0
    score = sum(p.reaction.risk_flags.meme_potential * p.weight for p in scored) / denom

    mocking = [p for p in scored if p.reaction.likely_behavior == "share_mocking"]
    candidates = []
    for p in scored:
        if p.reaction.risk_flags.meme_potential <= settings.risk_flag_threshold:
            continue
        for t in p.reaction.triggers:
            candidates.append(
                {
                    "span": t.span,
                    "char_start": t.char_start,
                    "char_end": t.char_end,
                    "persona_id": p.reaction.persona_id,
                    "meme_potential": p.reaction.risk_flags.meme_potential,
                    "why": t.why,
                }
            )

    return {
        "score": round(score, 4),
        "would_share_mocking": [p.reaction.persona_id for p in mocking],
        "mocking_audience_mass": round(sum(p.weight for p in mocking), 4),
        "candidate_spans": sorted(candidates, key=lambda c: c["meme_potential"], reverse=True)[:10],
    }


# --------------------------------------------------------------------------
# Composite view helpers
# --------------------------------------------------------------------------


def blind_spot_findings(composites: list[ReactionObject]) -> list[dict[str, Any]]:
    """Tier-2 output. Reported SEPARATELY from the score and never inside it (§7.2).

    Composites that merely echo their parents (`distinct_reaction: false`) are
    discarded, not displayed — a discovery panel full of noise gets ignored.
    """
    rows = []
    for r in composites:
        if r.distinct_reaction is False:
            continue
        rows.append(
            {
                "composite_id": r.persona_id,
                "severity": r.severity,
                "confidence": r.confidence,
                "emotion": r.emotion,
                "paraphrase": r.interpretation.paraphrase,
                "comment": r.likely_comment.text,
                "triggers": [t.model_dump() for t in r.triggers],
                "not_scored": True,
                "disclaimer": (
                    "Simulated intersection — not validated. No authored persona "
                    "covers this audience. Treat as a lead to investigate, not a "
                    "measurement."
                ),
            }
        )
    return sorted(rows, key=lambda r: r["severity"], reverse=True)[:5]


def severe_discovery_alert(composites: list[ReactionObject]) -> dict[str, Any] | None:
    """§7.5 — a composite can interrupt, but it cannot compute.

    A composite finding a severe issue no base node caught is exactly what the
    two-tier architecture exists to surface. It raises a blocking alert without
    altering the numeric score or band.
    """
    for r in composites:
        if r.distinct_reaction is False:
            continue
        if r.severity >= 0.9 and r.confidence >= 0.8:
            return {
                "composite_id": r.persona_id,
                "severity": r.severity,
                "confidence": r.confidence,
                "reaction": r.interpretation.paraphrase,
                "comment": r.likely_comment.text,
                "affects_score": False,
                "message": (
                    "A simulated intersectional audience reacted severely to this "
                    "copy, and no authored persona caught it. This does not change "
                    "your score — it is an unvalidated lead that warrants a human look."
                ),
            }
    return None
