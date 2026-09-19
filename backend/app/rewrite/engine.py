"""Rewrite engine (§16.21, §16.22).

Anyone can ask an LLM to "make this less offensive". The result is bland,
voice-destroying mush that no marketer will ship. A rewrite that kills the
copy's impact has not solved the problem — it has moved it.

So the rewriter produces three variants at different points on the
risk/impact trade-off and makes the trade-off legible, rather than silently
optimizing one side. Every variant is then RE-SCORED through the persona set:
we do not claim an improvement, we demonstrate it.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.config import settings
from app.llm.client import LLMClient
from app.orchestrator.run import RunResult, run_persona
from app.personas.schema import PersonaNode, ReactionObject
from app.scoring.model import build_scored, compute_score, intent_alignment_score
from app.scoring.uncertainty import compute_interval

logger = logging.getLogger(__name__)

VariantKind = Literal["clarify", "safer", "preserve_edge"]

_STRATEGY: dict[VariantKind, str] = {
    "clarify": (
        "CLARIFY — close the interpretation gaps. Keep the edge and the voice. "
        "Your target is that personas who MISREAD the copy now understand it. "
        "You are not making it safer; you are making it unambiguous."
    ),
    "safer": (
        "SAFER — reduce risk substantially. You may let the voice drift if you "
        "must, but do not produce generic corporate mush: it still has to be "
        "copy someone would run."
    ),
    "preserve_edge": (
        "PRESERVE EDGE — change as little as possible. Fix the specific span "
        "that is causing harm and leave everything else intact. Whatever makes "
        "this copy work must survive."
    ),
}


class RewriteVariant(BaseModel):
    kind: VariantKind
    text: str = Field(description="The rewritten copy")
    rationale: str = Field(description="What changed and why")
    preserved: str = Field(default="", description="What was deliberately kept")
    sacrificed: str = Field(default="", description="What was given up, honestly stated")


class RewriteSet(BaseModel):
    variants: list[RewriteVariant] = Field(default_factory=list)


@dataclass
class ScoredVariant:
    kind: VariantKind
    text: str
    rationale: str
    preserved: str
    sacrificed: str
    risk_index: float
    band: str
    interval: dict[str, Any]
    intent_alignment: float
    resolved_triggers: list[str]
    new_triggers: list[str]
    improved: bool
    reactions: list[ReactionObject]

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "text": self.text,
            "rationale": self.rationale,
            "preserved": self.preserved,
            "sacrificed": self.sacrificed,
            "risk_index": self.risk_index,
            "band": self.band,
            "interval": self.interval,
            "intent_alignment": self.intent_alignment,
            "resolved_triggers": self.resolved_triggers,
            "new_triggers": self.new_triggers,
            "improved": self.improved,
        }


_SYSTEM = """\
You are a senior copywriter revising marketing copy that has been tested against
a simulated audience.

You are NOT a content moderator, and you are not here to sand off everything
interesting. A rewrite that destroys the copy's impact has not solved the
problem — it has moved it. Your job is to produce three genuinely different
options so a marketer can choose their own trade-off.

You will be given the exact objections, in the audience's own words, with the
specific spans that triggered them. Use the REASONS, not just the spans: "avoid
the word beef" produces a worse rewrite than "this treats a religious boundary
as a casual food preference", because the second lets you find solutions the
first forecloses.

Produce exactly three variants:

1. {clarify}

2. {safer}

3. {preserve_edge}

Be honest in `sacrificed`. If a variant gives something up, say so plainly — a
marketer who is told the cost can accept it. One who discovers it later cannot.

Return JSON only:
{{
  "variants": [
    {{
      "kind": "clarify" | "safer" | "preserve_edge",
      "text": "<the rewritten copy, complete and ready to run>",
      "rationale": "<what you changed and why>",
      "preserved": "<what you deliberately kept>",
      "sacrificed": "<what this variant gives up — say 'nothing material' only if true>"
    }},
    ...
  ]
}}
"""


def _build_brief(result: RunResult, registry: dict[str, PersonaNode]) -> str:
    """The rewriter sees WHY each persona objected, not just that they did."""
    lines: list[str] = []

    ranked = sorted(result.scored, key=lambda p: p.severity, reverse=True)
    for p in ranked[:6]:
        if p.severity < 0.2 and p.reaction.interpretation.comprehension == "understood":
            continue
        node = registry.get(p.reaction.persona_id)
        label = node.label if node else p.reaction.persona_id
        lines.append(f"\n--- {label} (severity {p.severity:.2f}) ---")
        lines.append(f"  They think you said: {p.reaction.interpretation.paraphrase}")
        lines.append(f"  Comprehension: {p.reaction.interpretation.comprehension}")
        if p.reaction.triggers:
            for t in p.reaction.triggers:
                lines.append(f'  Trigger "{t.span}" ({t.modality}): {t.why}')
        lines.append(f"  Would post: “{p.reaction.likely_comment.text}”")

    if not lines:
        lines.append("\nNo persona raised a significant objection.")
    return "\n".join(lines)


async def generate_variants(
    client: LLMClient,
    result: RunResult,
    registry: dict[str, PersonaNode],
    constraints: str | None = None,
) -> RewriteSet:
    system = _SYSTEM.format(
        clarify=_STRATEGY["clarify"],
        safer=_STRATEGY["safer"],
        preserve_edge=_STRATEGY["preserve_edge"],
    )

    user_parts = [
        "═══ ORIGINAL COPY ═══",
        result.copy,
        "",
    ]
    if result.brand_intent:
        user_parts += ["═══ WHAT THE BRAND MEANT ═══", result.brand_intent, ""]
    user_parts += ["═══ AUDIENCE OBJECTIONS ═══", _build_brief(result, registry), ""]
    if constraints:
        user_parts += [
            "═══ HARD CONSTRAINTS ═══",
            constraints,
            "(These are non-negotiable — character limits, mandatory claims, "
            "legally required language.)",
            "",
        ]
    user_parts.append("Write the three variants now. JSON only.")

    rewrite = await client.complete_json(
        system=system,
        user="\n".join(user_parts),
        model=settings.synthesis_model,
        max_tokens=settings.max_tokens_synthesis,
        schema=RewriteSet,
        temperature=0.7,
    )
    assert isinstance(rewrite, RewriteSet)
    return rewrite


def select_rescore_personas(
    result: RunResult,
    registry: dict[str, PersonaNode],
    controls: int = 3,
) -> list[PersonaNode]:
    """Personas that flagged the original, plus controls.

    Controls catch a rewrite that fixes one problem and creates another — a real
    failure mode: sanitizing a dietary reference by introducing a gendered
    metaphor. Without them, the re-score only looks where it already knows to.
    """
    flagged_ids = {
        p.reaction.persona_id
        for p in result.scored
        if p.severity >= 0.3 or p.reaction.interpretation.comprehension != "understood"
    }
    flagged = [registry[i] for i in flagged_ids if i in registry]

    # Controls: highest-prevalence personas that did NOT flag, plus any mandatory
    # node (the canary must run on every variant too).
    others = sorted(
        (n for n in registry.values() if n.id not in flagged_ids),
        key=lambda n: (n.mandatory, n.prevalence_weight),
        reverse=True,
    )
    return flagged + others[:controls]


async def score_variant(
    client: LLMClient,
    variant: RewriteVariant,
    personas: list[PersonaNode],
    original: RunResult,
    registry: dict[str, PersonaNode],
    context_block: str,
    kappa: float,
) -> ScoredVariant:
    tasks = [
        run_persona(client, node, variant.text, original.brand_intent, context_block)
        for node in personas
    ]
    settled = await asyncio.gather(*tasks, return_exceptions=True)

    reactions = [r for r in settled if not isinstance(r, BaseException)]
    if not reactions:
        raise RuntimeError(f"Variant {variant.kind}: every persona failed")

    scored = build_scored(reactions, registry)
    score = compute_score(scored, kappa)
    interval = compute_interval(scored, kappa, seed=42)

    original_spans = {t.span.lower() for p in original.scored for t in p.reaction.triggers}
    new_spans = {t.span.lower() for p in scored for t in p.reaction.triggers}

    original_score = compute_score(original.scored, kappa)

    return ScoredVariant(
        kind=variant.kind,
        text=variant.text,
        rationale=variant.rationale,
        preserved=variant.preserved,
        sacrificed=variant.sacrificed,
        risk_index=score.index,
        band=score.band,
        interval=interval.as_dict(),
        intent_alignment=intent_alignment_score(scored),
        resolved_triggers=sorted(original_spans - new_spans),
        new_triggers=sorted(new_spans - original_spans),
        improved=score.index < original_score.index,
        reactions=reactions,
    )


async def rewrite_and_rescore(
    client: LLMClient,
    result: RunResult,
    registry: dict[str, PersonaNode],
    constraints: str | None = None,
) -> dict[str, Any]:
    """Generate variants and prove whether they work.

    If a variant does not improve, we say so. A rewriter that always reports
    success is one nobody believes after the third use.
    """
    variants = await generate_variants(client, result, registry, constraints)
    if not variants.variants:
        return {"variants": [], "note": "No variants generated."}

    personas = select_rescore_personas(result, registry)
    kappa = result.context.multiplier_for(result.selection.triage.activated_axes)
    context_block = result.context.as_prompt_block()

    scored_variants = await asyncio.gather(
        *(
            score_variant(client, v, personas, result, registry, context_block, kappa)
            for v in variants.variants
        ),
        return_exceptions=True,
    )

    ok = [v for v in scored_variants if not isinstance(v, BaseException)]
    failures = [str(v) for v in scored_variants if isinstance(v, BaseException)]

    original_score = compute_score(result.scored, kappa)
    original_ias = intent_alignment_score(result.scored)

    best = min(ok, key=lambda v: v.risk_index) if ok else None
    any_improved = any(v.improved for v in ok)

    return {
        "original": {
            "text": result.copy,
            "risk_index": original_score.index,
            "band": original_score.band,
            "intent_alignment": original_ias,
        },
        "variants": [v.as_dict() for v in sorted(ok, key=lambda v: v.risk_index)],
        "best_variant": best.kind if best else None,
        "any_improved": any_improved,
        "rescored_against": [n.id for n in personas],
        "note": (
            None
            if any_improved
            else "No variant improved on the original. The objection may be "
            "structural rather than phrasal — consider whether the concept "
            "itself carries the risk."
        ),
        "failures": failures,
    }
