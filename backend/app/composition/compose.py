"""Tier 2 — composite personas (§7).

Composites fuse selected base nodes into intersectional identities no single
node covers. They are a HYPOTHESIS GENERATOR, not a measurement.

They never enter the score. A composite A(+)B is a deterministic function of A
and B, mechanically correlated with both; resampling a pool containing all three
counts the same signal up to three times, variance shrinks, and the tool would
report higher confidence while adding zero information (§7.2). That is enforced
structurally in ``scoring.model.compute_score``, which rejects tier-2 input.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.config import settings
from app.llm.client import LLMClient
from app.personas.compile import compile_system_prompt, compile_user_prompt
from app.personas.schema import (
    Demographics,
    LLMReaction,
    PersonaNode,
    ReactionObject,
    SensitivityProfile,
)
from app.router.select import profile_similarity
from app.scoring.model import ScoredPersona

logger = logging.getLogger(__name__)

# Coarse co-occurrence priors: does this intersection describe a real population
# in meaningful numbers? Hand-estimated from region/language/migration overlap.
# Refine from engagement data once the promotion loop (§7.4) has signal.
_REGION_AFFINITY: dict[frozenset[str], float] = {
    frozenset({"IN", "US"}): 0.40,  # large diaspora
    frozenset({"IN", "GLOBAL"}): 0.50,
    frozenset({"MENA", "SEA"}): 0.35,  # shared faith, distinct culture
    frozenset({"MENA", "US"}): 0.30,
    frozenset({"MENA", "GLOBAL"}): 0.45,
    frozenset({"LATAM", "US"}): 0.45,  # large diaspora
    frozenset({"AF", "US"}): 0.30,
    frozenset({"AF", "GLOBAL"}): 0.40,
    frozenset({"CN", "US"}): 0.25,
    frozenset({"JP", "US"}): 0.20,
    frozenset({"EU", "US"}): 0.35,
    frozenset({"SEA", "GLOBAL"}): 0.40,
}
_DEFAULT_AFFINITY = 0.10
_SAME_REGION_AFFINITY = 0.65


@dataclass
class CompositeSpec:
    """A planned composite, before it has reacted."""

    composite_id: str
    parents: tuple[PersonaNode, PersonaNode]
    dominant: PersonaNode
    eig: float
    rationale: str = ""
    node: PersonaNode = field(init=False)

    def __post_init__(self) -> None:
        self.node = _derive_node(self)


def plausibility(a: PersonaNode, b: PersonaNode) -> float:
    """pi(A,B) — does this person exist in meaningful numbers?

    Kills implausible intersections (jp_urban_professional (+) africa_west_anglophone,
    pi ~ 0.02) while keeping real diaspora populations.
    """
    ra, rb = a.demographics.region, b.demographics.region
    if ra == rb:
        return _SAME_REGION_AFFINITY
    affinity = _REGION_AFFINITY.get(frozenset({ra, rb}), _DEFAULT_AFFINITY)

    # Shared language raises plausibility: these people can read the same copy.
    langs_a, langs_b = set(a.demographics.languages), set(b.demographics.languages)
    if langs_a & langs_b:
        affinity = min(1.0, affinity * 1.3)

    # Age-band overlap; disjoint bands describe different generations.
    lo = max(a.demographics.age_band[0], b.demographics.age_band[0])
    hi = min(a.demographics.age_band[1], b.demographics.age_band[1])
    if hi <= lo:
        affinity *= 0.4

    return round(min(1.0, affinity), 4)


def expected_information_gain(a: ScoredPersona, b: ScoredPersona) -> float:
    """EIG = |s_A - s_B| * (1 - sim(A,B)) * pi(A,B)  (§7.3).

    A composite of two nodes that already agree is worthless — it will agree too,
    and cost a call to do so.
    """
    disagreement = abs(a.severity - b.severity)
    distance = 1.0 - profile_similarity(_node_of(a), _node_of(b))
    pi = plausibility(_node_of(a), _node_of(b))
    return disagreement * distance * pi


_node_cache: dict[str, PersonaNode] = {}


def _node_of(p: ScoredPersona) -> PersonaNode:
    node = _node_cache.get(p.reaction.persona_id)
    if node is None:
        raise KeyError(f"Persona node not registered for {p.reaction.persona_id}")
    return node


def _derive_profile(dominant: PersonaNode, other: PersonaNode) -> SensitivityProfile:
    """max(), not mean().

    Intersectional identity is a UNION of sensitivities, not an average. Someone
    who is both observant Hindu and progressive is not *half* as sensitive to
    dietary practice.
    """
    dom_axes = sorted(
        SensitivityProfile.axis_names(),
        key=lambda ax: getattr(dominant.sensitivity_profile, ax),
        reverse=True,
    )[:3]

    values: dict[str, float] = {}
    for axis in SensitivityProfile.axis_names():
        merged = max(
            getattr(dominant.sensitivity_profile, axis),
            getattr(other.sensitivity_profile, axis),
        )
        lam = 1.0 if axis in dom_axes else 0.85
        values[axis] = round(min(1.0, merged * lam), 4)

    return SensitivityProfile(**values)


def _derive_node(spec: CompositeSpec) -> PersonaNode:
    dominant = spec.dominant
    other = spec.parents[1] if spec.parents[0].id == dominant.id else spec.parents[0]

    label = f"{dominant.label} × {other.label}"
    notes = (
        f"You hold both of these identities at once, with "
        f"{dominant.label.lower()} leading.\n\n"
        f"--- {dominant.label} ---\n{dominant.persona_notes.strip()}\n\n"
        f"--- {other.label} ---\n{other.persona_notes.strip()}\n\n"
        "You are not an average of these two. You are a specific person for whom "
        "both are true simultaneously, and the combination may produce a reading "
        "neither identity would reach alone — or it may not."
    )
    failure = (
        f"{dominant.failure_modes.strip()}\n\n{other.failure_modes.strip()}\n\n"
        "Additionally: do not manufacture a distinct intersectional reaction that "
        "is not there. If either identity alone would produce the same response, "
        "return distinct_reaction: false. An honest null is more useful than an "
        "invented nuance."
    )

    return PersonaNode(
        id=spec.composite_id,
        version=1,
        label=label,
        demographics=Demographics(
            region=dominant.demographics.region,
            sub_region=dominant.demographics.sub_region,
            age_band=(
                max(dominant.demographics.age_band[0], other.demographics.age_band[0]),
                min(dominant.demographics.age_band[1], other.demographics.age_band[1]),
            ),
            urbanicity=dominant.demographics.urbanicity,
            languages=sorted(
                set(dominant.demographics.languages) | set(other.demographics.languages)
            ),
            audience_type="secondary",
        ),
        sensitivity_profile=_derive_profile(dominant, other),
        # Composites carry zero prevalence weight: they must never contribute
        # audience mass anywhere, even by accident.
        prevalence_weight=0.0,
        vocality=max(dominant.vocality, other.vocality),
        is_target=False,
        persona_notes=notes,
        failure_modes=failure,
        source=f"Derived composite of {dominant.id} and {other.id} — NOT authored, NOT validated",
    )


def build_composites(
    scored: list[ScoredPersona],
    registry: dict[str, PersonaNode],
    limit: int = 12,
) -> list[CompositeSpec]:
    """Select the top-EIG pairs. Generation 1 only — never composites of composites."""
    _node_cache.clear()
    for p in scored:
        node = registry.get(p.reaction.persona_id)
        if node:
            _node_cache[p.reaction.persona_id] = node

    eligible = [p for p in scored if p.reaction.persona_id in _node_cache]
    # Control and amplifier nodes are instruments, not identities to fuse.
    eligible = [
        p
        for p in eligible
        if _node_cache[p.reaction.persona_id].demographics.audience_type
        not in {"control", "amplifier"}
    ]

    candidates: list[CompositeSpec] = []
    for i in range(len(eligible)):
        for j in range(i + 1, len(eligible)):
            a, b = eligible[i], eligible[j]
            eig = expected_information_gain(a, b)
            if eig <= 0.01:
                continue
            na, nb = _node_of(a), _node_of(b)
            # The higher-severity parent leads: its sensitivity is what made this
            # intersection interesting in the first place.
            dominant = na if a.severity >= b.severity else nb
            candidates.append(
                CompositeSpec(
                    composite_id=f"cmp_{na.id[:8]}_{nb.id[:8]}",
                    parents=(na, nb),
                    dominant=dominant,
                    eig=round(eig, 4),
                    rationale=(
                        f"Parents disagree ({a.severity:.2f} vs {b.severity:.2f}); "
                        f"plausibility {plausibility(na, nb):.2f}"
                    ),
                )
            )

    candidates.sort(key=lambda c: c.eig, reverse=True)
    selected = candidates[:limit]
    logger.info("Composition: %d candidates, %d selected", len(candidates), len(selected))
    return selected


async def run_composite(
    client: LLMClient,
    spec: CompositeSpec,
    copy: str,
    brand_intent: str | None,
    context_block: str,
) -> ReactionObject:
    reaction = await client.complete_json(
        system=compile_system_prompt(spec.node, context_block, is_composite=True),
        user=compile_user_prompt(copy, brand_intent),
        model=settings.persona_model,
        max_tokens=2000,
        schema=LLMReaction,
    )
    assert isinstance(reaction, LLMReaction)

    data = reaction.model_dump()
    # A composite that does not declare itself distinct is treated as an echo of
    # its parents and discarded downstream.
    if data.get("distinct_reaction") is None:
        data["distinct_reaction"] = False

    return ReactionObject(
        persona_id=spec.composite_id,
        persona_version=1,
        tier=2,
        **data,
    )
