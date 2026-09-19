"""Property and behaviour tests for the risk model (§19)."""

from __future__ import annotations

import pytest

from app.personas.schema import (
    Demographics,
    Interpretation,
    LikelyComment,
    PersonaNode,
    ReactionObject,
    RiskFlags,
    SensitivityProfile,
)
from app.scoring.model import (
    ScoredPersona,
    build_scored,
    compute_score,
    control_canary,
    intent_alignment_score,
    tail_risk,
)
from app.scoring.uncertainty import compute_interval


def make_reaction(
    persona_id: str = "p",
    severity: float = 0.5,
    confidence: float = 0.8,
    tier: int = 1,
    behavior: str = "ignore",
    sentiment: str = "indifferent",
    intent_alignment: float = 0.8,
    comprehension: str = "understood",
) -> ReactionObject:
    return ReactionObject(
        persona_id=persona_id,
        tier=tier,  # type: ignore[arg-type]
        interpretation=Interpretation(
            literal_reading="x",
            paraphrase="x",
            perceived_intent="x",
            intent_alignment=intent_alignment,
            comprehension=comprehension,  # type: ignore[arg-type]
        ),
        emotion="neutral",
        emotion_intensity=0.3,
        sentiment=sentiment,  # type: ignore[arg-type]
        risk_flags=RiskFlags(),
        severity=severity,
        likely_behavior=behavior,  # type: ignore[arg-type]
        likely_comment=LikelyComment(text="x", tone="confused"),
        confidence=confidence,
    )


def sp(
    severity: float,
    confidence: float = 0.8,
    weight: float = 0.1,
    vocality: float = 0.5,
    persona_id: str = "p",
    behavior: str = "ignore",
) -> ScoredPersona:
    return ScoredPersona(
        reaction=make_reaction(
            persona_id=persona_id, severity=severity, confidence=confidence, behavior=behavior
        ),
        weight=weight,
        vocality=vocality,
    )


# ── bounds and monotonicity ──────────────────────────────────────────


def test_index_within_bounds():
    for sev in (0.0, 0.25, 0.5, 0.75, 1.0):
        score = compute_score([sp(sev, 1.0, 0.2) for _ in range(5)])
        assert 0.0 <= score.index <= 100.0


def test_index_monotonic_in_severity():
    lo = compute_score([sp(0.2, 0.9, 0.1, persona_id=f"p{i}") for i in range(5)]).index
    hi = compute_score([sp(0.8, 0.9, 0.1, persona_id=f"p{i}") for i in range(5)]).index
    assert hi > lo


def test_adding_zero_severity_persona_never_increases_score():
    base = [sp(0.7, 0.9, 0.1, persona_id=f"p{i}") for i in range(4)]
    before = compute_score(base).index
    after = compute_score([*base, sp(0.0, 0.9, 0.1, persona_id="calm")]).index
    assert after <= before + 1e-9


def test_empty_persona_set_is_clear():
    score = compute_score([])
    assert score.index == 0.0
    assert score.band == "Clear"


# ── the tail term: why this is not a weighted mean ──────────────────


def test_tail_risk_survives_averaging():
    """Eleven personas at 0.1 and one at 1.0 is a campaign on fire, not a 0.175."""
    scored = [sp(0.1, 0.9, 0.08, persona_id=f"p{i}") for i in range(11)]
    scored.append(sp(1.0, 0.95, 0.08, persona_id="severe"))

    assert tail_risk(scored) >= 0.9
    score = compute_score(scored)
    # Mean severity is ~0.17; the index must be far above what that alone implies.
    assert score.index > 35


def test_override_forces_high_band():
    """One credible severe reaction is not averaged away (§9.4)."""
    scored = [sp(0.05, 0.9, 0.1, persona_id=f"p{i}") for i in range(10)]
    scored.append(sp(0.95, 0.9, 0.05, persona_id="severe"))

    score = compute_score(scored)
    assert score.override_fired
    assert score.override_persona_id == "severe"
    assert score.band in ("High", "Severe")


def test_override_requires_both_severity_and_confidence():
    # High severity but low confidence must NOT fire the override.
    scored = [sp(0.95, 0.5, 0.1, persona_id="unsure")]
    assert not compute_score(scored).override_fired


# ── tier enforcement: the central design decision (§7.2) ────────────


def test_composites_rejected_from_scoring():
    """Tier-2 personas must never enter the score.

    They are correlated with their parents by construction; including them would
    narrow the CI through redundancy rather than evidence.
    """
    composite = ScoredPersona(
        reaction=make_reaction(persona_id="cmp_a_b", tier=2), weight=0.0, vocality=0.5
    )
    with pytest.raises(ValueError, match="must never enter the score"):
        compute_score([composite])


# ── §19.4 CI integrity: the guardrail for the two-tier split ─────────


def test_composites_would_narrow_the_interval():
    """Demonstrates WHY composites are excluded, as an executable argument.

    Composites echo their parents. Adding them to the pool shrinks the bootstrap
    interval without adding information — the tool would report more confidence
    for free. If someone ever merges the tiers, this test documents the cost.
    """
    parents = [
        sp(0.9, 0.9, 0.15, persona_id="a"),
        sp(0.1, 0.9, 0.15, persona_id="b"),
        sp(0.5, 0.9, 0.15, persona_id="c"),
        sp(0.2, 0.9, 0.15, persona_id="d"),
    ]
    correct = compute_interval(parents, seed=1)

    # Simulate the mistake: derived nodes that duplicate their parents' signal.
    echoes = [
        sp(0.9, 0.9, 0.15, persona_id="cmp_a_c"),
        sp(0.1, 0.9, 0.15, persona_id="cmp_b_d"),
        sp(0.5, 0.9, 0.15, persona_id="cmp_c_a"),
        sp(0.2, 0.9, 0.15, persona_id="cmp_d_b"),
    ]
    contaminated = compute_interval(parents + echoes, seed=1)

    assert contaminated.width < correct.width, (
        "Adding parent-correlated composites narrowed the interval, which is "
        "exactly the failure the two-tier split prevents."
    )


# ── intervals ────────────────────────────────────────────────────────


def test_interval_contains_point_estimate():
    scored = [sp(0.3 + i * 0.1, 0.8, 0.1, persona_id=f"p{i}") for i in range(6)]
    ci = compute_interval(scored, seed=7)
    assert ci.lower <= ci.point <= ci.upper


def test_disagreement_widens_interval():
    """A wide interval means the personas disagree — the copy splits the audience."""
    agreeing = [sp(0.5, 0.9, 0.1, persona_id=f"p{i}") for i in range(8)]
    split = [sp(0.95 if i % 2 else 0.05, 0.9, 0.1, persona_id=f"p{i}") for i in range(8)]

    assert compute_interval(split, seed=3).width > compute_interval(agreeing, seed=3).width


def test_interval_within_bounds():
    scored = [sp(0.99, 1.0, 0.2, persona_id=f"p{i}") for i in range(6)]
    ci = compute_interval(scored, seed=5)
    assert 0.0 <= ci.lower <= ci.upper <= 100.0


# ── amplification ────────────────────────────────────────────────────


def test_vocal_segment_amplifies_more_than_quiet_one():
    quiet = [sp(0.7, 0.9, 0.3, vocality=0.1, persona_id="quiet", behavior="ignore")]
    vocal = [sp(0.7, 0.9, 0.3, vocality=0.9, persona_id="vocal", behavior="criticize")]
    assert compute_score(vocal).index > compute_score(quiet).index


# ── intent alignment ─────────────────────────────────────────────────


def test_intent_alignment_independent_of_risk():
    """A campaign can be perfectly safe and still fail to communicate."""
    safe_but_unclear = [
        ScoredPersona(
            reaction=make_reaction(
                persona_id=f"p{i}", severity=0.05, intent_alignment=0.2, comprehension="misread"
            ),
            weight=0.1,
            vocality=0.5,
        )
        for i in range(5)
    ]
    assert compute_score(safe_but_unclear).band == "Clear"
    assert intent_alignment_score(safe_but_unclear) < 30


# ── control canary ───────────────────────────────────────────────────


def _node(persona_id: str, audience_type: str = "secondary") -> PersonaNode:
    return PersonaNode(
        id=persona_id,
        label=persona_id,
        demographics=Demographics(region="GLOBAL", audience_type=audience_type),  # type: ignore[arg-type]
        sensitivity_profile=SensitivityProfile(),
        prevalence_weight=0.1,
        vocality=0.1,
        persona_notes="x",
        failure_modes="x",
    )


def test_control_node_excluded_from_score():
    """The canary must not vote on the score it exists to monitor."""
    registry = {
        "normal": _node("normal"),
        "hard_negative_control": _node("hard_negative_control", "control"),
    }
    reactions = [
        make_reaction(persona_id="normal", severity=0.5),
        make_reaction(persona_id="hard_negative_control", severity=0.9),
    ]
    scored = build_scored(reactions, registry)
    assert [p.reaction.persona_id for p in scored] == ["normal"]


def test_canary_fires_on_high_control_severity():
    registry = {"hard_negative_control": _node("hard_negative_control", "control")}
    reactions = [make_reaction(persona_id="hard_negative_control", severity=0.8)]
    canary = control_canary(reactions, registry)
    assert canary is not None and canary.fired
    assert "calibration" in (canary.message or "").lower()


def test_canary_quiet_on_normal_copy():
    registry = {"hard_negative_control": _node("hard_negative_control", "control")}
    reactions = [make_reaction(persona_id="hard_negative_control", severity=0.05)]
    canary = control_canary(reactions, registry)
    assert canary is not None and not canary.fired


# ── interval calibration: guards against both failure directions ─────


def test_interval_never_claims_certainty():
    """A small panel of simulated personas cannot justify a point estimate.

    When every persona agrees, the bootstrap resamples identical values and
    reports zero spread. That is an artifact of a small fixed panel, not
    evidence — and shipping [52.3, 52.3] would be the precision illusion of
    §22.6.
    """
    unanimous = [sp(0.85, 0.9, 0.1, persona_id=f"p{i}") for i in range(10)]
    ci = compute_interval(unanimous, seed=42)
    assert ci.width > 0.0, "unanimous personas must not produce a zero-width interval"
    assert ci.width < 20.0, "agreement should still read as relatively confident"


def test_interval_not_pinned_to_rails():
    """A pivotal persona must widen the interval without saturating it.

    Adding the full jackknife sd on top of the bootstrap double-counts variance
    the bootstrap already captures (a persona is absent from ~37% of resamples),
    which produced [0, 100] for exactly the cases the product cares about most.
    """
    scored = [sp(0.12, 0.9, 0.1, persona_id=f"p{i}") for i in range(9)]
    scored.append(sp(0.92, 0.9, 0.14, persona_id="severe", behavior="criticize"))

    ci = compute_interval(scored, seed=42)
    assert ci.lower > 0.0 and ci.upper < 100.0, f"interval pinned to rails: {ci}"
    assert ci.is_wide, "a pivotal severe persona should read as genuine disagreement"


def test_larger_panel_gives_tighter_floor():
    """The resolution floor scales with panel size: n=30 beats n=4."""
    small = compute_interval([sp(0.5, 0.8, 0.15, persona_id=f"p{i}") for i in range(4)], seed=1)
    large = compute_interval([sp(0.5, 0.8, 0.03, persona_id=f"p{i}") for i in range(30)], seed=1)
    assert large.width < small.width
