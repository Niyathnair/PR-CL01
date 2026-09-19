"""Core risk model (§9 of the plan).

Pure functions over reactions and persona weights. No LLM calls, no I/O — which
makes every claim in here unit-testable, and makes the weights tunable against
the golden set without touching the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.config import settings
from app.personas.schema import PersonaNode, ReactionObject

Band = Literal["Clear", "Low", "Elevated", "High", "Severe"]

_BAND_BOUNDS: list[tuple[float, Band]] = [
    (20, "Clear"),
    (40, "Low"),
    (60, "Elevated"),
    (80, "High"),
    (100, "Severe"),
]
_BAND_ORDER: list[Band] = ["Clear", "Low", "Elevated", "High", "Severe"]


@dataclass(frozen=True)
class ScoredPersona:
    """One persona's reaction paired with its registry weights."""

    reaction: ReactionObject
    weight: float  # w_i, prevalence
    vocality: float  # v_i

    @property
    def severity(self) -> float:
        return self.reaction.severity

    @property
    def confidence(self) -> float:
        return self.reaction.confidence

    @property
    def is_vocal(self) -> float:
        return 1.0 if self.reaction.is_vocal else 0.0

    @property
    def ambiguity(self) -> float:
        """g_i — gap between the charitable and hostile reading.

        Proxied by how far apart the two readings are in length-normalized
        character terms when both exist; the model is asked for both, and a
        persona that produces a very different hostile reading is signalling
        that the copy is genuinely ambiguous. Falls back to the
        misinterpretation risk flag, which measures the same thing more
        directly but less sensitively.
        """
        charitable = self.reaction.charitable_reading.strip()
        hostile = self.reaction.hostile_reading.strip()
        if not charitable or not hostile:
            return self.reaction.risk_flags.misinterpretation

        # Token-level Jaccard distance: cheap, no embeddings needed at this layer.
        a = set(charitable.lower().split())
        b = set(hostile.lower().split())
        if not a or not b:
            return self.reaction.risk_flags.misinterpretation
        jaccard = len(a & b) / len(a | b)
        return max(1.0 - jaccard, self.reaction.risk_flags.misinterpretation)


@dataclass(frozen=True)
class ScoreComponents:
    offense_mass: float  # M
    amplification: float  # A (normalized)
    tail_risk: float  # T
    ambiguity: float  # G
    context_multiplier: float  # kappa
    raw: float


@dataclass(frozen=True)
class RiskScore:
    index: float
    band: Band
    components: ScoreComponents
    override_fired: bool
    override_persona_id: str | None
    persona_count: int


def offense_mass(scored: list[ScoredPersona]) -> float:
    """M = sum(w_i c_i s_i) / sum(w_i c_i) — audience- and confidence-weighted mean."""
    denom = sum(p.weight * p.confidence for p in scored)
    if denom <= 0:
        return 0.0
    return sum(p.weight * p.confidence * p.severity for p in scored) / denom


def amplification(scored: list[ScoredPersona]) -> float:
    """A = sum(w_i v_i p_i s_i), normalized to [0,1].

    Separates "some customers quietly dislike this" from "this becomes a story".
    A small vocal segment at high severity amplifies more than a large quiet one.
    """
    raw = sum(p.weight * p.vocality * p.is_vocal * p.severity for p in scored)
    # Normalize by the maximum achievable given this persona set, so the term is
    # comparable across runs with different K.
    max_possible = sum(p.weight * p.vocality for p in scored)
    if max_possible <= 0:
        return 0.0
    return min(1.0, raw / max_possible)


def tail_risk(scored: list[ScoredPersona]) -> float:
    """T = max(s_i * c_i).

    Averages hide catastrophes: eleven personas at 0.1 and one at 1.0 gives a
    mean of 0.175 and a campaign on fire. This is why the model is not a
    weighted mean, and why gamma is the largest weight.
    """
    if not scored:
        return 0.0
    return max(p.severity * p.confidence for p in scored)


def ambiguity(scored: list[ScoredPersona]) -> float:
    """G = mean(g_i). Copy that can be read two ways will be read the worse way."""
    if not scored:
        return 0.0
    return sum(p.ambiguity for p in scored) / len(scored)


def band_for(index: float) -> Band:
    for bound, band in _BAND_BOUNDS:
        if index <= bound:
            return band
    return "Severe"


def _raise_band(band: Band, floor: Band) -> Band:
    return band if _BAND_ORDER.index(band) >= _BAND_ORDER.index(floor) else floor


def check_override(scored: list[ScoredPersona]) -> ScoredPersona | None:
    """Any persona at s>=0.9 and c>=0.7 forces a floor of High (§9.4).

    A deliberate asymmetry: one credible severe reaction is not averaged away,
    because the cost of a false negative here vastly exceeds a false positive.
    """
    for p in scored:
        if (
            p.severity >= settings.override_severity
            and p.confidence >= settings.override_confidence
        ):
            return p
    return None


def compute_score(
    scored: list[ScoredPersona],
    context_multiplier: float = 1.0,
) -> RiskScore:
    """The composite risk index (§9.3).

    Only Tier-1 personas may be passed here. Tier-2 composites are correlated
    with their parents by construction; including them would narrow the
    confidence interval through redundancy rather than evidence (§7.2).
    """
    for p in scored:
        if p.reaction.tier != 1:
            raise ValueError(
                f"Tier-{p.reaction.tier} persona {p.reaction.persona_id} passed to "
                "compute_score. Composites must never enter the score (plan §7.2)."
            )

    if not scored:
        return RiskScore(
            index=0.0,
            band="Clear",
            components=ScoreComponents(0, 0, 0, 0, context_multiplier, 0),
            override_fired=False,
            override_persona_id=None,
            persona_count=0,
        )

    m = offense_mass(scored)
    a = amplification(scored)
    t = tail_risk(scored)
    g = ambiguity(scored)

    raw = context_multiplier * (
        settings.weight_alpha * m
        + settings.weight_beta * a
        + settings.weight_gamma * t
        + settings.weight_delta * g
    )
    index = min(100.0, 100.0 * raw)

    band = band_for(index)
    override = check_override(scored)
    if override is not None:
        band = _raise_band(band, "High")

    return RiskScore(
        index=round(index, 1),
        band=band,
        components=ScoreComponents(
            offense_mass=round(m, 4),
            amplification=round(a, 4),
            tail_risk=round(t, 4),
            ambiguity=round(g, 4),
            context_multiplier=context_multiplier,
            raw=round(raw, 4),
        ),
        override_fired=override is not None,
        override_persona_id=override.reaction.persona_id if override else None,
        persona_count=len(scored),
    )


def intent_alignment_score(scored: list[ScoredPersona]) -> float:
    """IAS (§10.1) — weighted share of the audience that understood the intent.

    Reported alongside the risk index, never subordinate to it: a campaign can be
    perfectly safe and still fail here. This is the metric that catches "nobody
    was offended, nobody understood it either."
    """
    denom = sum(p.weight * p.confidence for p in scored)
    if denom <= 0:
        return 0.0
    num = sum(p.weight * p.confidence * p.reaction.interpretation.intent_alignment for p in scored)
    return round(100.0 * num / denom, 1)


def build_scored(
    reactions: list[ReactionObject],
    registry: dict[str, PersonaNode],
    include_control: bool = False,
) -> list[ScoredPersona]:
    """Pair reactions with their persona registry weights.

    Control nodes are excluded by default: they are diagnostic instruments, not
    audience, and counting their prevalence mass would let the canary vote on
    the score it exists to monitor. Pass ``include_control=True`` only when
    reading the canary itself (see ``control_canary``).
    """
    out: list[ScoredPersona] = []
    for r in reactions:
        node = registry.get(r.persona_id)
        if node is None:
            continue
        if node.is_control and not include_control:
            continue
        out.append(ScoredPersona(reaction=r, weight=node.prevalence_weight, vocality=node.vocality))
    return out


@dataclass(frozen=True)
class ControlCanary:
    """Reading of the hard-negative control node (§6.2, §19.2)."""

    fired: bool
    severity: float
    persona_id: str
    message: str | None


def control_canary(
    reactions: list[ReactionObject],
    registry: dict[str, PersonaNode],
    threshold: float = 0.2,
) -> ControlCanary | None:
    """Check whether the over-triggering canary fired.

    A firing canary is a SIGNAL OF SYSTEM MALFUNCTION, not a finding about the
    copy. It must be surfaced to operators as a calibration defect and never
    presented to the user as a risk.
    """
    for r in reactions:
        node = registry.get(r.persona_id)
        if node is None or not node.is_control:
            continue
        fired = r.severity > threshold
        return ControlCanary(
            fired=fired,
            severity=r.severity,
            persona_id=r.persona_id,
            message=(
                f"Control persona {r.persona_id!r} returned severity {r.severity:.2f} "
                f"(threshold {threshold}). Persona calibration may have drifted — "
                "treat this as a pipeline defect, not a finding about the copy."
            )
            if fired
            else None,
        )
    return None
