"""Backlash Pathway and interpretation clustering tests.

The pathway is the highest credibility risk in the product: a plausible causal
chain is the panel most likely to be wrong while looking authoritative. These
tests exist to prove it terminates on missing evidence rather than narrating its
way to a satisfying conclusion.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_scoring import _node, make_reaction  # noqa: E402

from app.analysis.graph import build_pathway, interpretation_clusters  # noqa: E402
from app.scoring.model import ScoredPersona  # noqa: E402

COPY = "Our new protein bar - finally, a beef bar that doesn't taste like a cow."


def sp(
    persona_id: str,
    severity: float = 0.5,
    comprehension: str = "understood",
    sentiment: str = "indifferent",
    behavior: str = "ignore",
    paraphrase: str = "They are selling a protein bar",
    weight: float = 0.1,
    vocality: float = 0.5,
) -> ScoredPersona:
    r = make_reaction(
        persona_id=persona_id,
        severity=severity,
        comprehension=comprehension,
        sentiment=sentiment,
        behavior=behavior,
    )
    r.interpretation.paraphrase = paraphrase
    r.likely_comment.text = f"comment from {persona_id}"
    return ScoredPersona(reaction=r, weight=weight, vocality=vocality)


# ── termination: the chain must stop where evidence stops ────────────


def test_terminates_when_nobody_misread():
    """No misinterpretation means no chain. Do not invent one."""
    scored = [sp(f"p{i}", severity=0.1) for i in range(5)]
    path = build_pathway(scored, {}, COPY)

    assert path.terminated_at == "creative"
    assert len(path.nodes) == 1
    assert path.overall_likelihood == 0.0
    assert "inventing" in (path.termination_reason or "")


def test_terminates_when_misread_but_not_opposed():
    """Misunderstanding without opposition is a clarity problem, not backlash."""
    scored = [
        sp("confused", severity=0.3, comprehension="misread", sentiment="indifferent"),
        sp("fine", severity=0.1),
    ]
    path = build_pathway(scored, {}, COPY)

    assert path.terminated_at == "misinterpretation"
    assert "clarity problem" in (path.termination_reason or "")
    assert {n.stage for n in path.nodes} == {"creative", "misinterpretation"}


def test_terminates_when_opposed_but_silent():
    """Quiet dislike costs sales, not a news cycle."""
    scored = [
        sp(
            "quiet_objector",
            severity=0.8,
            comprehension="misread",
            sentiment="opposed",
            behavior="ignore",
        ),
    ]
    path = build_pathway(scored, {}, COPY)

    assert path.terminated_at == "reaction"
    assert "news cycle" in (path.termination_reason or "")


def test_terminates_before_wider_discussion_without_amplifier():
    """Individuals sharing is not the same as a story. Require the amplifier."""
    registry = {"loud": _node("loud", "secondary")}
    scored = [
        sp(
            "loud",
            severity=0.9,
            comprehension="misread",
            sentiment="opposed",
            behavior="criticize",
        ),
    ]
    path = build_pathway(scored, registry, COPY)

    assert path.terminated_at == "amplification"
    assert "speculation" in (path.termination_reason or "")


def test_full_chain_when_amplifier_fires():
    registry = {
        "loud": _node("loud", "secondary"),
        "analyst": _node("analyst", "amplifier"),
    }
    scored = [
        sp(
            "loud",
            severity=0.9,
            comprehension="misread",
            sentiment="opposed",
            behavior="criticize",
        ),
        sp(
            "analyst",
            severity=0.8,
            comprehension="misread",
            sentiment="opposed",
            behavior="share_mocking",
        ),
    ]
    path = build_pathway(scored, registry, COPY)

    assert path.terminated_at is None
    stages = [n.stage for n in path.nodes]
    assert stages == [
        "creative",
        "misinterpretation",
        "reaction",
        "amplification",
        "discussion",
    ]
    assert len(path.edges) == 4


# ── grounding: every node must cite real persona evidence ───────────


def test_every_node_beyond_root_is_grounded():
    """A node with empty grounding is a fabrication, not a finding."""
    registry = {
        "loud": _node("loud", "secondary"),
        "analyst": _node("analyst", "amplifier"),
    }
    scored = [
        sp("loud", 0.9, "misread", "opposed", "criticize"),
        sp("analyst", 0.8, "misread", "opposed", "share_mocking"),
    ]
    path = build_pathway(scored, registry, COPY)

    for node in path.nodes:
        if node.id == "creative":
            continue
        assert node.grounded_in, f"node {node.id} has no persona grounding"
        assert node.evidence, f"node {node.id} has no evidence string"


def test_node_details_are_verbatim_persona_output():
    """The model narrates links; it never invents node content."""
    registry = {"loud": _node("loud", "secondary")}
    scored = [
        sp(
            "loud",
            0.9,
            "misread",
            "opposed",
            "criticize",
            paraphrase="They think my beliefs are a punchline",
        )
    ]
    path = build_pathway(scored, registry, COPY)

    misread = next(n for n in path.nodes if n.stage == "misinterpretation")
    assert misread.detail == "They think my beliefs are a punchline"

    reaction = next(n for n in path.nodes if n.stage == "reaction")
    assert reaction.detail == "comment from loud"


def test_likelihood_decreases_along_the_chain():
    """A long chain is less likely than any single link — the honest reading."""
    registry = {
        "loud": _node("loud", "secondary"),
        "analyst": _node("analyst", "amplifier"),
    }
    scored = [
        sp("loud", 0.9, "misread", "opposed", "criticize"),
        sp("analyst", 0.8, "misread", "opposed", "share_mocking"),
        sp("calm1", 0.1),
        sp("calm2", 0.1),
    ]
    path = build_pathway(scored, registry, COPY)

    assert 0.0 <= path.overall_likelihood <= 1.0
    first_edge = path.edges[0].likelihood
    assert path.overall_likelihood <= first_edge


# ── interpretation clustering ────────────────────────────────────────


def test_clusters_are_data_driven_not_fixed_k():
    """Unanimous readings produce ONE cluster, not three.

    Fixing k manufactures interpretations that nobody held.
    """
    scored = [sp(f"p{i}", paraphrase="They are selling a high protein snack bar") for i in range(6)]
    clusters = interpretation_clusters(scored)
    assert len(clusters) == 1
    assert clusters[0]["size"] == 6


def test_distinct_readings_separate():
    scored = [
        sp("a", paraphrase="They are selling a high protein snack"),
        sp("b", paraphrase="They are selling a high protein snack bar"),
        sp("c", paraphrase="They think my religion is a joke worth mocking"),
        sp("d", paraphrase="They think my religion is a joke"),
    ]
    clusters = interpretation_clusters(scored)
    assert len(clusters) == 2

    labels = {c["label"] for c in clusters}
    # Label must be a real persona's words, never a synthesized summary.
    said = {i.reaction.interpretation.paraphrase for i in scored}
    assert labels <= said


def test_clusters_sorted_by_audience_mass():
    """The largest cluster that is not the intended reading is the key output."""
    scored = [
        sp("big1", paraphrase="A protein bar advert", weight=0.3),
        sp("big2", paraphrase="A protein bar advert here", weight=0.3),
        sp("small", paraphrase="Mockery of religious dietary practice", weight=0.05),
    ]
    clusters = interpretation_clusters(scored)
    masses = [c["audience_mass"] for c in clusters]
    assert masses == sorted(masses, reverse=True)
    assert abs(sum(c["share"] for c in clusters) - 1.0) < 1e-6


def test_empty_input_is_safe():
    assert interpretation_clusters([]) == []
    path = build_pathway([], {}, COPY)
    assert path.terminated_at == "creative"


# ── trigger offset repair: models miscount characters ───────────────


def test_trigger_offsets_repaired_against_copy():
    """Wrong offsets would silently highlight the wrong words in the composer."""
    from app.orchestrator.run import repair_trigger_offsets

    copy = "Our new protein bar - finally, a beef bar that doesn't taste like a cow."
    triggers = [
        # Model claimed 40:48, which is actually "r that d".
        {
            "span": "beef bar",
            "char_start": 40,
            "char_end": 48,
            "modality": "phrase",
            "why": "x",
            "valence": "negative",
        },
    ]
    out = repair_trigger_offsets(triggers, copy, "p")

    assert len(out) == 1
    assert copy[out[0]["char_start"] : out[0]["char_end"]] == "beef bar"


def test_correct_offsets_left_alone():
    from app.orchestrator.run import repair_trigger_offsets

    copy = "a beef bar here"
    t = [
        {
            "span": "beef bar",
            "char_start": 2,
            "char_end": 10,
            "modality": "phrase",
            "why": "x",
            "valence": "negative",
        }
    ]
    out = repair_trigger_offsets(t, copy, "p")
    assert out[0]["char_start"] == 2 and out[0]["char_end"] == 10


def test_hallucinated_span_dropped():
    """A span not in the copy cannot be shown, so it is discarded not guessed."""
    from app.orchestrator.run import repair_trigger_offsets

    copy = "Our new protein bar."
    t = [
        {
            "span": "pork sausage",
            "char_start": 0,
            "char_end": 12,
            "modality": "phrase",
            "why": "x",
            "valence": "negative",
        }
    ]
    assert repair_trigger_offsets(t, copy, "p") == []


def test_case_insensitive_span_recovered():
    from app.orchestrator.run import repair_trigger_offsets

    copy = "Our new Beef Bar is here."
    t = [
        {
            "span": "beef bar",
            "char_start": 99,
            "char_end": 107,
            "modality": "phrase",
            "why": "x",
            "valence": "negative",
        }
    ]
    out = repair_trigger_offsets(t, copy, "p")
    assert len(out) == 1
    assert copy[out[0]["char_start"] : out[0]["char_end"]] == "Beef Bar"
