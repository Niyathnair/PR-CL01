"""Run orchestration: selection -> fan-out -> composition -> aggregation.

Tier 1 and Tier 2 fan out concurrently; wall-clock is the slowest call, not the
sum. A run returning 10 of 12 personas is still a valid run — we record which
failed and let the interval widen accordingly (§18.3).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.analysis import projections
from app.composition.compose import build_composites, run_composite
from app.context.provider import ContextBundle, get_context_provider
from app.llm.client import LLMClient
from app.personas.compile import compile_system_prompt, compile_user_prompt
from app.personas.schema import LLMReaction, PersonaNode, ReactionObject
from app.router.select import SelectionResult, select_personas
from app.scoring.model import (
    ScoredPersona,
    build_scored,
    compute_score,
    control_canary,
    intent_alignment_score,
)
from app.scoring.uncertainty import compute_interval

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    run_id: str
    copy: str
    brand_intent: str | None
    created_at: str

    reactions: list[ReactionObject]
    composites: list[ReactionObject]
    scored: list[ScoredPersona]
    selection: SelectionResult
    context: ContextBundle

    failed_personas: list[dict[str, str]] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)


async def run_persona(
    client: LLMClient,
    node: PersonaNode,
    copy: str,
    brand_intent: str | None,
    context_block: str,
    is_composite: bool = False,
) -> ReactionObject:
    """One persona reaction. The orchestrator supplies identity, not the model."""
    reaction = await client.complete_json(
        system=compile_system_prompt(node, context_block, is_composite=is_composite),
        user=compile_user_prompt(copy, brand_intent),
        model=client_model(is_composite),
        max_tokens=2000,
        schema=LLMReaction,
    )
    assert isinstance(reaction, LLMReaction)

    return ReactionObject(
        persona_id=node.id,
        persona_version=node.version,
        tier=2 if is_composite else 1,
        **reaction.model_dump(),
    )


def client_model(is_composite: bool) -> str:
    from app.config import settings

    return settings.persona_model if not is_composite else settings.persona_model


async def execute_run(
    client: LLMClient,
    registry: dict[str, PersonaNode],
    copy: str,
    brand_intent: str | None = None,
    context_scenario: str = "quiet",
    k: int | None = None,
    enable_composites: bool = True,
) -> RunResult:
    """Full simulation run."""
    run_id = uuid.uuid4().hex[:12]
    logger.info("Run %s starting (%d chars)", run_id, len(copy))

    context = get_context_provider().fetch(context_scenario)
    selection = await select_personas(client, registry, copy, brand_intent, k=k)
    context_block = context.as_prompt_block()

    # --- Tier 1 fan-out ---
    tasks = [
        run_persona(client, s.node, copy, brand_intent, context_block) for s in selection.selected
    ]
    settled = await asyncio.gather(*tasks, return_exceptions=True)

    reactions: list[ReactionObject] = []
    failed: list[dict[str, str]] = []
    for sel, outcome in zip(selection.selected, settled, strict=True):
        if isinstance(outcome, BaseException):
            logger.warning("Persona %s failed: %s", sel.node.id, outcome)
            failed.append({"persona_id": sel.node.id, "error": str(outcome)})
        else:
            reactions.append(outcome)

    if not reactions:
        raise RuntimeError(f"Run {run_id}: every persona failed")

    scored = build_scored(reactions, registry)

    # --- Tier 2 composition (parallel, never enters the score) ---
    composites: list[ReactionObject] = []
    if enable_composites and len(scored) >= 2:
        specs = build_composites(scored, registry)
        if specs:
            comp_tasks = [
                run_composite(client, spec, copy, brand_intent, context_block) for spec in specs
            ]
            comp_settled = await asyncio.gather(*comp_tasks, return_exceptions=True)
            for spec, outcome in zip(specs, comp_settled, strict=True):
                if isinstance(outcome, BaseException):
                    logger.warning("Composite %s failed: %s", spec.composite_id, outcome)
                else:
                    composites.append(outcome)

    logger.info(
        "Run %s complete: %d reactions, %d composites, %d failures",
        run_id,
        len(reactions),
        len(composites),
        len(failed),
    )

    return RunResult(
        run_id=run_id,
        copy=copy,
        brand_intent=brand_intent,
        created_at=datetime.now(UTC).isoformat(),
        reactions=reactions,
        composites=composites,
        scored=scored,
        selection=selection,
        context=context,
        failed_personas=failed,
        usage=client.usage.snapshot(),
    )


def build_report(result: RunResult, registry: dict[str, PersonaNode]) -> dict[str, Any]:
    """Assemble every panel from the run. All 24 analyses, one computation."""
    scored = result.scored
    kappa = result.context.multiplier_for(result.selection.triage.activated_axes)

    score = compute_score(scored, kappa)
    interval = compute_interval(scored, kappa, seed=42)
    canary = control_canary(result.reactions, registry)

    return {
        "run_id": result.run_id,
        "created_at": result.created_at,
        "copy": result.copy,
        "brand_intent": result.brand_intent,
        # ── headline ──────────────────────────────────────────────
        "risk_index": {
            "value": score.index,
            "band": score.band,
            "interval": interval.as_dict(),
            "components": score.components.__dict__,
            "override_fired": score.override_fired,
            "override_persona_id": score.override_persona_id,
            # §17.3 — never present this as a probability.
            "label": "Risk Index",
            "disclaimer": (
                "An ordinal risk index from simulated reactions, not a probability "
                "and not survey data."
            ),
        },
        "intent_alignment": {
            "value": intent_alignment_score(scored),
            "label": "Intent Alignment Score",
        },
        # ── the eight questions ───────────────────────────────────
        "understanding": {
            "intent_vs_interpretation": _intent_vs_interpretation(scored, registry),
            "intent_alignment_breakdown": [
                {
                    "persona_id": p.reaction.persona_id,
                    "intent_alignment": p.reaction.interpretation.intent_alignment,
                    "comprehension": p.reaction.interpretation.comprehension,
                    "perceived_intent": p.reaction.interpretation.perceived_intent,
                }
                for p in scored
            ],
        },
        "feeling": {
            "emotional_response": projections.emotional_response(scored),
            "persona_reactions": projections.persona_reactions(scored, registry),
            "simulated_comments": projections.simulated_comments(scored, registry),
        },
        "risk": {
            "why_risky": projections.why_risky(scored),
            "risk_anatomy": projections.risk_anatomy(scored),
            "severity_likelihood": projections.severity_likelihood_matrix(scored),
            "controversial_vs_misunderstood": projections.controversial_vs_misunderstood(scored),
        },
        "who": {
            "audience_heatmap": projections.audience_heatmap(scored, registry),
            "region_heatmap": projections.region_heatmap(scored, registry),
            "target_vs_unintended": projections.target_vs_unintended(scored, registry),
            "who_might_misunderstand": _who_might_misunderstand(scored, registry),
        },
        "cause": {
            "trigger_index": projections.trigger_index(scored),
            "meme_potential": projections.meme_potential(scored),
        },
        # ── tier 2, reported separately and never in the score ────
        "blind_spot_findings": projections.blind_spot_findings(result.composites),
        "severe_discovery_alert": projections.severe_discovery_alert(result.composites),
        # ── provenance and diagnostics ────────────────────────────
        "selection": result.selection.as_dict(),
        "context": result.context.as_dict(),
        "failed_personas": result.failed_personas,
        "control_canary": (
            {"fired": canary.fired, "severity": canary.severity, "message": canary.message}
            if canary
            else None
        ),
        "usage": result.usage,
    }


def _intent_vs_interpretation(
    scored: list[ScoredPersona], registry: dict[str, PersonaNode]
) -> list[dict[str, Any]]:
    """Panel 1. Sorted by gap descending — the top row is the biggest misreading."""
    rows = []
    for p in scored:
        node = registry.get(p.reaction.persona_id)
        gap = 1.0 - p.reaction.interpretation.intent_alignment
        rows.append(
            {
                "persona_id": p.reaction.persona_id,
                "label": node.label if node else p.reaction.persona_id,
                "perceived_intent": p.reaction.interpretation.perceived_intent,
                "paraphrase": p.reaction.interpretation.paraphrase,
                "literal_reading": p.reaction.interpretation.literal_reading,
                "gap": round(gap, 4),
                "comprehension": p.reaction.interpretation.comprehension,
            }
        )
    return sorted(rows, key=lambda r: r["gap"], reverse=True)


def _who_might_misunderstand(
    scored: list[ScoredPersona], registry: dict[str, PersonaNode]
) -> list[dict[str, Any]]:
    """Panel 6. Only personas with a real gap — an empty list is a good answer."""
    rows = []
    for p in scored:
        if p.reaction.interpretation.comprehension == "understood":
            continue
        node = registry.get(p.reaction.persona_id)
        rows.append(
            {
                "persona_id": p.reaction.persona_id,
                "label": node.label if node else p.reaction.persona_id,
                "comprehension": p.reaction.interpretation.comprehension,
                "gap": round(1.0 - p.reaction.interpretation.intent_alignment, 4),
                "they_think_you_said": p.reaction.interpretation.paraphrase,
                "triggers": [t.span for t in p.reaction.triggers],
            }
        )
    return sorted(rows, key=lambda r: r["gap"], reverse=True)
