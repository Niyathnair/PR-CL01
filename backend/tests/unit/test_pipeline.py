"""End-to-end pipeline test with a stubbed LLM.

Exercises selection, fan-out, composition, aggregation, and every panel without
making a network call, so CI can prove the wiring holds.
"""

from __future__ import annotations

import json

import pytest

from app.analysis import projections
from app.llm.auth import Credential
from app.orchestrator.run import build_report, execute_run
from app.personas.registry import get_registry
from app.personas.schema import LLMReaction


class StubLLM:
    """Returns deterministic, schema-valid reactions keyed off the persona prompt."""

    def __init__(self) -> None:
        self.calls: list[str] = []

        class _Usage:
            def snapshot(self) -> dict:
                return {"calls": 0, "estimated_cost_usd": 0.0}

        self.usage = _Usage()
        self.credential = Credential(kind="api_key", value="stub", source_env_var="TEST")

    async def complete_json(self, *, system, user, model, max_tokens, schema, temperature=0.3):
        self.calls.append(system[:80])

        if schema.__name__ == "TriageResult":
            return schema(
                activated_axes={"dietary_practice": 0.95, "religious_symbols": 0.6},
                entities=["beef", "cow"],
                implicit_claims=["animal consumption treated casually"],
                topics=["food", "protein"],
            )

        if schema.__name__ == "AdversarialPick":
            return schema(persona_ids=[], reasoning="no blind spot")

        # A persona reaction. Make the Hindu persona react severely so the
        # override and tail-risk paths are exercised.
        severe = "Observant Hindu" in system
        is_composite = "YOU ARE AN INTERSECTION" in system

        return LLMReaction(
            interpretation={
                "literal_reading": "A beef protein bar advert.",
                "paraphrase": "They think my beliefs are a punchline."
                if severe
                else "They're selling a protein bar.",
                "perceived_intent": "Humour" if not severe else "Mockery",
                "intent_alignment": 0.2 if severe else 0.85,
                "comprehension": "misread" if severe else "understood",
            },
            emotion="offended" if severe else "neutral",
            emotion_intensity=0.9 if severe else 0.2,
            sentiment="opposed" if severe else "indifferent",
            triggers=(
                [
                    {
                        "span": "beef bar",
                        "char_start": 40,
                        "char_end": 48,
                        "modality": "phrase",
                        "why": "Treats a religious boundary as a casual food choice.",
                        "valence": "negative",
                    }
                ]
                if severe
                else []
            ),
            risk_flags={
                "misinterpretation": 0.3,
                "cultural": 0.9 if severe else 0.05,
                "religious": 0.95 if severe else 0.0,
                "tone_mismatch": 0.4 if severe else 0.1,
                "confusion": 0.1,
                "meme_potential": 0.6 if severe else 0.1,
                "polarization": 0.7 if severe else 0.05,
            },
            severity=0.92 if severe else 0.12,
            likely_behavior="criticize" if severe else "ignore",
            likely_comment={
                "text": "This is not a joke to me." if severe else "Fine, I guess.",
                "tone": "critical" if severe else "confused",
            },
            confidence=0.9,
            charitable_reading="They did not think about it.",
            hostile_reading="They knew and did it anyway.",
            distinct_reaction=True if is_composite else None,
        )


COPY = "Our new protein bar - finally, a beef bar that doesn't taste like a cow."
INTENT = "Position our protein bar as great-tasting and high-protein."


@pytest.fixture
def registry():
    return get_registry()


async def test_full_pipeline(registry):
    client = StubLLM()
    result = await execute_run(
        client=client,  # type: ignore[arg-type]
        registry=registry,
        copy=COPY,
        brand_intent=INTENT,
        context_scenario="quiet",
    )

    assert result.reactions, "no reactions returned"
    assert not result.failed_personas
    # Composites are produced but must never appear in the scored set.
    assert all(p.reaction.tier == 1 for p in result.scored)


async def test_report_contains_every_panel(registry):
    client = StubLLM()
    result = await execute_run(
        client=client,  # type: ignore[arg-type]
        registry=registry,
        copy=COPY,
        brand_intent=INTENT,
    )
    report = build_report(result, registry)

    # Headline
    assert report["risk_index"]["band"] in ("Clear", "Low", "Elevated", "High", "Severe")
    assert report["risk_index"]["label"] == "Risk Index"
    assert "not a probability" in report["risk_index"]["disclaimer"]
    assert report["risk_index"]["interval"]["lower"] <= report["risk_index"]["value"]

    # The eight questions
    for section in ("understanding", "feeling", "risk", "who", "cause"):
        assert section in report, f"missing section {section}"

    assert report["understanding"]["intent_vs_interpretation"]
    assert report["feeling"]["emotional_response"]["distribution"]
    assert report["feeling"]["simulated_comments"]
    assert report["risk"]["risk_anatomy"]
    assert len(report["risk"]["severity_likelihood"]) == 7
    assert report["risk"]["controversial_vs_misunderstood"]["prescriptions"]
    assert report["who"]["region_heatmap"]
    assert report["cause"]["trigger_index"]

    # Provenance must always be present (§17.3).
    assert report["context"]["provenance"] == "mock"

    # The whole report must be JSON-serializable for the API.
    json.dumps(report)


async def test_severe_persona_forces_high_band(registry):
    """The beef case: the weighted mean says 'fine', the tail term catches it."""
    client = StubLLM()
    result = await execute_run(
        client=client,  # type: ignore[arg-type]
        registry=registry,
        copy=COPY,
        brand_intent=INTENT,
    )
    report = build_report(result, registry)

    assert report["risk_index"]["override_fired"], "override should fire on s=0.92, c=0.9"
    assert report["risk_index"]["band"] in ("High", "Severe")


async def test_composites_never_enter_score(registry):
    """Structural guarantee, tested end to end (§7.2)."""
    client = StubLLM()
    result = await execute_run(
        client=client,  # type: ignore[arg-type]
        registry=registry,
        copy=COPY,
        brand_intent=INTENT,
        enable_composites=True,
    )

    scored_ids = {p.reaction.persona_id for p in result.scored}
    composite_ids = {c.persona_id for c in result.composites}
    assert not (scored_ids & composite_ids)

    findings = projections.blind_spot_findings(result.composites)
    for f in findings:
        assert f["not_scored"] is True


async def test_context_scenario_changes_score(registry):
    """Same copy, different news cycle, different risk (§18.4)."""
    quiet = build_report(
        await execute_run(
            client=StubLLM(),  # type: ignore[arg-type]
            registry=registry,
            copy=COPY,
            brand_intent=INTENT,
            context_scenario="quiet",
        ),
        registry,
    )
    hot = build_report(
        await execute_run(
            client=StubLLM(),  # type: ignore[arg-type]
            registry=registry,
            copy=COPY,
            brand_intent=INTENT,
            context_scenario="dietary_controversy_india",
        ),
        registry,
    )

    assert hot["risk_index"]["value"] > quiet["risk_index"]["value"]
    assert hot["context"]["scenario"] == "dietary_controversy_india"
