"""Persona selection: N -> K (§6).

Score against the personas most likely to DETECT something, not a demographic
cross-section. This is what lets the registry grow to 40-60 authored personas
while per-run cost stays flat.

Stage 2 (axis activation) is the workhorse: it catches
beef -> dietary_practice -> in_hindu_observant_urban with no LLM reasoning about
personas at all. Stage 3 (adversarial) is the most important for correctness:
stages 1-2 select for agreement, which is a filter bubble, and a filter bubble
is how you get a confident, narrow, wrong answer.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.config import settings
from app.llm.client import LLMClient
from app.personas.schema import PersonaNode, SensitivityProfile

logger = logging.getLogger(__name__)

SelectionStage = Literal["mandatory", "axis", "adversarial", "fallback"]


class TriageResult(BaseModel):
    """Output of the Haiku triage call (§6.1 stage 2)."""

    activated_axes: dict[str, float] = Field(default_factory=dict)
    entities: list[str] = Field(default_factory=list)
    implicit_claims: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)


class AdversarialPick(BaseModel):
    persona_ids: list[str] = Field(default_factory=list)
    reasoning: str = ""


@dataclass
class SelectedPersona:
    node: PersonaNode
    relevance: float
    stage: SelectionStage
    reason: str = ""


@dataclass
class SelectionResult:
    selected: list[SelectedPersona]
    triage: TriageResult
    candidate_pool: list[str] = field(default_factory=list)

    @property
    def nodes(self) -> list[PersonaNode]:
        return [s.node for s in self.selected]

    def as_dict(self) -> dict[str, Any]:
        return {
            "selected": [
                {
                    "persona_id": s.node.id,
                    "label": s.node.label,
                    "relevance": round(s.relevance, 4),
                    "stage": s.stage,
                    "reason": s.reason,
                }
                for s in self.selected
            ],
            "activated_axes": self.triage.activated_axes,
            "entities": self.triage.entities,
            "topics": self.triage.topics,
            "candidate_pool_size": len(self.candidate_pool),
        }


_TRIAGE_SYSTEM = """\
You extract structured signals from marketing copy for an audience-simulation
system. You are not judging the copy. You are labelling what it touches.

Return JSON only:
{
  "activated_axes": {"<axis>": <0.0-1.0 intensity>, ...},
  "entities": ["<named things the copy references>"],
  "implicit_claims": ["<what the copy implies without stating>"],
  "topics": ["<short topic labels>"]
}

Valid axes (use only these keys, omit any that do not apply):
  religious_symbols, dietary_practice, gender_representation, caste_and_class,
  national_identity, body_and_appearance, sexual_content, political_alignment,
  disability, race_and_ethnicity, environmental_claims, formality_and_respect

Intensity means "how strongly does this copy engage this axis", not "how bad is
it". Neutral copy engaging an axis still scores on that axis. Most copy
activates one or two axes weakly, or none. Do not pad the list.
"""

_ADVERSARIAL_SYSTEM = """\
You are auditing a persona selection for blind spots.

An audience-simulation system has picked a set of personas to react to a piece
of marketing copy. The picks were made by topical similarity, which selects for
AGREEMENT — personas that obviously match. That is a filter bubble.

Your job: from the REMAINING pool, name the personas most likely to react in a
way the selected set would MISS. Prefer personas whose objection would come from
an unexpected direction, not ones that merely reinforce what is already covered.

Return JSON only:
{"persona_ids": ["<id>", ...], "reasoning": "<one or two sentences>"}

Pick at most the number requested. If the selected set genuinely has no blind
spot worth filling, return fewer — an honest empty answer is better than padding.
"""


async def triage(client: LLMClient, copy: str, brand_intent: str | None = None) -> TriageResult:
    """Stage 2: extract activated sensitivity axes with a cheap Haiku call."""
    user = f"COPY:\n{copy}"
    if brand_intent:
        user += f"\n\nSTATED BRAND INTENT:\n{brand_intent}"

    try:
        result = await client.complete_json(
            system=_TRIAGE_SYSTEM,
            user=user,
            model=settings.triage_model,
            max_tokens=800,
            schema=TriageResult,
            temperature=0.0,
        )
        assert isinstance(result, TriageResult)
        # Drop any hallucinated axis names.
        valid = set(SensitivityProfile.axis_names())
        result.activated_axes = {
            k: max(0.0, min(1.0, v)) for k, v in result.activated_axes.items() if k in valid
        }
        return result
    except Exception as exc:  # noqa: BLE001 - triage must never break a run
        logger.warning("Triage failed, falling back to uniform axes: %s", exc)
        return TriageResult()


def axis_relevance(node: PersonaNode, activated: dict[str, float]) -> float:
    """r_j = cosine(persona sensitivity profile, activated axes).

    Zero activated axes means no topical signal, so every persona is equally
    (ir)relevant and we return a flat score — selection then falls through to
    prevalence weighting.
    """
    if not activated:
        return 0.0

    profile = node.sensitivity_profile
    dot = 0.0
    prof_norm = 0.0
    act_norm = 0.0

    for axis in SensitivityProfile.axis_names():
        p = getattr(profile, axis)
        a = activated.get(axis, 0.0)
        dot += p * a
        prof_norm += p * p
        act_norm += a * a

    if prof_norm <= 0 or act_norm <= 0:
        return 0.0
    return dot / (math.sqrt(prof_norm) * math.sqrt(act_norm))


def profile_similarity(a: PersonaNode, b: PersonaNode) -> float:
    """Cosine similarity between two personas' sensitivity profiles."""
    va, vb = a.sensitivity_profile.as_vector(), b.sensitivity_profile.as_vector()
    dot = sum(x * y for x, y in zip(va, vb, strict=True))
    na = math.sqrt(sum(x * x for x in va))
    nb = math.sqrt(sum(y * y for y in vb))
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (na * nb)


def mmr_select(
    candidates: list[tuple[PersonaNode, float]],
    k: int,
    already: list[PersonaNode],
    mu: float | None = None,
) -> list[tuple[PersonaNode, float]]:
    """Maximal marginal relevance (§6.3).

    Greedy relevance alone picks near-identical personas and mistakes their
    agreement for consensus. That is load-bearing for the CI: artificially
    agreeing personas produce artificially narrow intervals.
    """
    mu = settings.diversity_mu if mu is None else mu
    chosen: list[tuple[PersonaNode, float]] = []
    pool = list(candidates)
    context = list(already)

    while pool and len(chosen) < k:
        best_idx, best_score = 0, float("-inf")
        for i, (node, rel) in enumerate(pool):
            penalty = max((profile_similarity(node, c) for c in context), default=0.0)
            score = rel - mu * penalty
            if score > best_score:
                best_idx, best_score = i, score
        node, rel = pool.pop(best_idx)
        chosen.append((node, rel))
        context.append(node)

    return chosen


async def adversarial_fill(
    client: LLMClient,
    copy: str,
    selected: list[PersonaNode],
    remaining: list[PersonaNode],
    slots: int,
) -> AdversarialPick:
    """Stage 3: ask the model to find its own blind spot.

    Imperfect — a model cannot reliably enumerate what it does not represent —
    but strictly better than not asking (§22.1).
    """
    if not remaining or slots <= 0:
        return AdversarialPick()

    sel_desc = "\n".join(f"- {n.id}: {n.label}" for n in selected)
    rem_desc = "\n".join(f"- {n.id}: {n.label}" for n in remaining)
    user = (
        f"COPY:\n{copy}\n\n"
        f"ALREADY SELECTED:\n{sel_desc}\n\n"
        f"REMAINING POOL:\n{rem_desc}\n\n"
        f"Name at most {slots} persona ids from the remaining pool."
    )

    try:
        pick = await client.complete_json(
            system=_ADVERSARIAL_SYSTEM,
            user=user,
            model=settings.persona_model,
            max_tokens=500,
            schema=AdversarialPick,
            temperature=0.5,
        )
        assert isinstance(pick, AdversarialPick)
        valid_ids = {n.id for n in remaining}
        pick.persona_ids = [pid for pid in pick.persona_ids if pid in valid_ids][:slots]
        return pick
    except Exception as exc:  # noqa: BLE001 - adversarial fill is best-effort
        logger.warning("Adversarial fill failed: %s", exc)
        return AdversarialPick()


async def select_personas(
    client: LLMClient,
    registry: dict[str, PersonaNode],
    copy: str,
    brand_intent: str | None = None,
    k: int | None = None,
) -> SelectionResult:
    """Full N -> K selection pipeline."""
    k = k or settings.target_k
    triage_result = await triage(client, copy, brand_intent)

    selected: list[SelectedPersona] = []
    taken: set[str] = set()

    # --- Mandatory nodes (§6.2) ---
    for node in registry.values():
        if node.mandatory:
            selected.append(SelectedPersona(node, 1.0, "mandatory", "Always included"))
            taken.add(node.id)

    # --- Axis-activation ranking with MMR diversity ---
    remaining_slots = max(0, k - len(selected) - settings.adversarial_slots)
    scored_candidates = [
        (n, axis_relevance(n, triage_result.activated_axes))
        for n in registry.values()
        if n.id not in taken
    ]
    # With no topical signal, fall back to prevalence so we still cover the
    # largest audience segments rather than picking arbitrarily.
    if not triage_result.activated_axes:
        scored_candidates = [(n, n.prevalence_weight) for n, _ in scored_candidates]

    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    pool = scored_candidates[:25]

    for node, rel in mmr_select(pool, remaining_slots, [s.node for s in selected]):
        selected.append(SelectedPersona(node, rel, "axis", f"Axis match {rel:.2f}"))
        taken.add(node.id)

    # --- Adversarial slots (§6.1 stage 3) ---
    remaining = [n for n in registry.values() if n.id not in taken]
    pick = await adversarial_fill(
        client, copy, [s.node for s in selected], remaining, settings.adversarial_slots
    )
    for pid in pick.persona_ids:
        node = registry[pid]
        selected.append(SelectedPersona(node, 0.0, "adversarial", pick.reasoning))
        taken.add(pid)

    # --- Fallback: top up to k by prevalence if adversarial returned fewer ---
    if len(selected) < k:
        leftovers = sorted(
            (n for n in registry.values() if n.id not in taken),
            key=lambda n: n.prevalence_weight,
            reverse=True,
        )
        for node in leftovers[: k - len(selected)]:
            selected.append(
                SelectedPersona(node, node.prevalence_weight, "fallback", "Prevalence top-up")
            )
            taken.add(node.id)

    logger.info(
        "Selected %d/%d personas (axes: %s)",
        len(selected),
        len(registry),
        ", ".join(f"{k_}={v:.2f}" for k_, v in triage_result.activated_axes.items()) or "none",
    )

    return SelectionResult(
        selected=selected,
        triage=triage_result,
        candidate_pool=[n.id for n in registry.values()],
    )
