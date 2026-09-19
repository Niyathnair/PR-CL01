"""Rewrite engine tests with a stubbed LLM."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from test_pipeline import COPY, INTENT, StubLLM  # noqa: E402

from app.orchestrator.run import execute_run  # noqa: E402
from app.personas.registry import get_registry  # noqa: E402
from app.rewrite.engine import (  # noqa: E402
    RewriteSet,
    rewrite_and_rescore,
    select_rescore_personas,
)


class RewriteStub(StubLLM):
    """Adds rewrite generation; variants score progressively lower."""

    def __init__(self, improve: bool = True) -> None:
        super().__init__()
        self.improve = improve
        self._variant_mode = False

    async def complete_json(self, *, system, user, model, max_tokens, schema, temperature=0.3):
        if schema.__name__ == "RewriteSet":
            self._variant_mode = self.improve
            return RewriteSet(
                variants=[
                    {
                        "kind": "clarify",
                        "text": "Our new protein bar - high protein, great taste.",
                        "rationale": "Removed the animal reference entirely.",
                        "preserved": "The taste claim.",
                        "sacrificed": "The joke.",
                    },
                    {
                        "kind": "safer",
                        "text": "Our new protein bar. Simply good protein.",
                        "rationale": "Neutral phrasing.",
                        "preserved": "Nothing distinctive.",
                        "sacrificed": "Voice.",
                    },
                    {
                        "kind": "preserve_edge",
                        "text": (
                            "Our new protein bar - finally, one that doesn't taste like cardboard."
                        ),
                        "rationale": "Kept the joke, changed its target.",
                        "preserved": "The comedic structure.",
                        "sacrificed": "Nothing material.",
                    },
                ]
            )

        # Once rewriting, personas react calmly (the fix worked).
        if self._variant_mode and schema.__name__ == "LLMReaction":
            system = system.replace("Observant Hindu", "Calm Reader")

        return await super().complete_json(
            system=system,
            user=user,
            model=model,
            max_tokens=max_tokens,
            schema=schema,
            temperature=temperature,
        )


@pytest.fixture
def registry():
    return get_registry()


async def test_rescore_set_includes_flaggers_and_controls(registry):
    result = await execute_run(
        client=StubLLM(),
        registry=registry,
        copy=COPY,
        brand_intent=INTENT,  # type: ignore[arg-type]
    )
    personas = select_rescore_personas(result, registry)
    ids = {n.id for n in personas}

    assert "in_hindu_observant_urban" in ids, "the persona that flagged must be re-scored"
    # Controls guard against a rewrite that fixes one problem and creates another.
    assert len(ids) > 1


async def test_rewrite_demonstrates_improvement(registry):
    client = RewriteStub(improve=True)
    result = await execute_run(
        client=client,
        registry=registry,
        copy=COPY,
        brand_intent=INTENT,  # type: ignore[arg-type]
    )
    out = await rewrite_and_rescore(client, result, registry)  # type: ignore[arg-type]

    assert len(out["variants"]) == 3
    assert out["any_improved"], "variants should beat the original here"
    assert out["best_variant"] in ("clarify", "safer", "preserve_edge")
    # Variants are sorted by risk, and each carries proof rather than a claim.
    for v in out["variants"]:
        assert "risk_index" in v and "interval" in v
        assert isinstance(v["improved"], bool)


async def test_rewrite_reports_honest_failure(registry):
    """A rewriter that always reports success is one nobody believes."""
    client = RewriteStub(improve=False)
    result = await execute_run(
        client=client,
        registry=registry,
        copy=COPY,
        brand_intent=INTENT,  # type: ignore[arg-type]
    )
    out = await rewrite_and_rescore(client, result, registry)  # type: ignore[arg-type]

    assert not out["any_improved"]
    assert out["note"] is not None
    assert "structural" in out["note"]


async def test_variants_declare_what_they_sacrifice(registry):
    client = RewriteStub(improve=True)
    result = await execute_run(
        client=client,
        registry=registry,
        copy=COPY,
        brand_intent=INTENT,  # type: ignore[arg-type]
    )
    out = await rewrite_and_rescore(client, result, registry)  # type: ignore[arg-type]

    for v in out["variants"]:
        assert v["sacrificed"], f"variant {v['kind']} must state its cost"
