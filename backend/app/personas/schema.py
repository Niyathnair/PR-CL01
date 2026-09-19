"""The Reaction Object and the persona registry schema.

The Reaction Object (§5 of the plan) is the load-bearing artifact: 14 of the 24
dashboard analyses are pure projections over it, requiring zero additional LLM
calls. Five decisions in here carry that weight:

1. Closed enums for emotion / sentiment / behavior. Free-text labels would need
   an LLM normalization pass before any grouping, turning three free panels into
   paid ones.
2. ``sentiment`` is independent of ``comprehension``. Conflating them destroys
   the Controversial-vs-Misunderstood panel: "understood and objects" needs a
   decision, "misread it" needs a rewrite. Different problems, different fixes.
3. Triggers carry character offsets, so Trigger Detection is an exact inverted
   index rather than fuzzy string matching.
4. ``likely_comment`` is generated inline, in character, where the persona's
   framing is already in context.
5. Prevalence weights live on the PersonaNode, never on the reaction — see
   ``PersonaNode.prevalence_weight``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Emotion = Literal[
    "positive", "curious", "neutral", "confused", "uncomfortable", "offended", "amused"
]
Sentiment = Literal["favorable", "indifferent", "opposed"]
Comprehension = Literal["understood", "partial", "misread"]
Behavior = Literal["engage", "ignore", "share_positive", "share_mocking", "criticize", "boycott"]
TriggerModality = Literal["word", "phrase", "visual", "reference", "tone", "context"]
Valence = Literal["negative", "positive", "ambiguous"]

RISK_DIMENSIONS = (
    "misinterpretation",
    "cultural",
    "religious",
    "tone_mismatch",
    "confusion",
    "meme_potential",
    "polarization",
)

# Behaviors that constitute public criticism, feeding the amplification term (§9.2).
VOCAL_BEHAVIORS = frozenset({"criticize", "share_mocking", "boycott"})


class Interpretation(BaseModel):
    literal_reading: str = Field(description="What the words actually say")
    paraphrase: str = Field(description="'They're telling me X' — clustered in §11.1")
    perceived_intent: str = Field(description="Why this persona thinks the brand said it")
    intent_alignment: float = Field(ge=0, le=1, description="Match to the brand's stated intent")
    comprehension: Comprehension


class Trigger(BaseModel):
    span: str = Field(description="Exact substring of the copy")
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    modality: TriggerModality
    why: str
    valence: Valence

    @field_validator("char_end")
    @classmethod
    def _end_after_start(cls, v: int, info) -> int:
        start = info.data.get("char_start")
        if start is not None and v < start:
            raise ValueError("char_end must be >= char_start")
        return v


class RiskFlags(BaseModel):
    misinterpretation: float = Field(default=0.0, ge=0, le=1)
    cultural: float = Field(default=0.0, ge=0, le=1)
    religious: float = Field(default=0.0, ge=0, le=1)
    tone_mismatch: float = Field(default=0.0, ge=0, le=1)
    confusion: float = Field(default=0.0, ge=0, le=1)
    meme_potential: float = Field(default=0.0, ge=0, le=1)
    polarization: float = Field(default=0.0, ge=0, le=1)

    def as_dict(self) -> dict[str, float]:
        return {d: getattr(self, d) for d in RISK_DIMENSIONS}


class LikelyComment(BaseModel):
    text: str = Field(description="In the persona's own voice")
    tone: Literal["positive", "confused", "critical", "humorous"]


class ReactionObject(BaseModel):
    """One persona's complete reaction. See module docstring."""

    persona_id: str
    persona_version: int = 1
    tier: Literal[1, 2] = 1

    interpretation: Interpretation

    emotion: Emotion
    emotion_intensity: float = Field(ge=0, le=1)
    sentiment: Sentiment

    triggers: list[Trigger] = Field(default_factory=list)

    risk_flags: RiskFlags = Field(default_factory=RiskFlags)
    severity: float = Field(ge=0, le=1)

    likely_behavior: Behavior
    likely_comment: LikelyComment

    confidence: float = Field(ge=0, le=1)
    charitable_reading: str = ""
    hostile_reading: str = ""

    # Tier 2 only: whether this composite says anything its parents did not.
    distinct_reaction: bool | None = None

    @property
    def is_vocal(self) -> bool:
        """Feeds the amplification term (§9.2)."""
        return self.likely_behavior in VOCAL_BEHAVIORS

    @property
    def is_opposed(self) -> bool:
        return self.sentiment == "opposed"


class LLMReaction(BaseModel):
    """What the model is asked to return.

    Excludes persona_id / version / tier, which the orchestrator supplies — the
    model should not be able to misattribute a reaction.
    """

    interpretation: Interpretation
    emotion: Emotion
    emotion_intensity: float = Field(ge=0, le=1)
    sentiment: Sentiment
    triggers: list[Trigger] = Field(default_factory=list)
    risk_flags: RiskFlags = Field(default_factory=RiskFlags)
    severity: float = Field(ge=0, le=1)
    likely_behavior: Behavior
    likely_comment: LikelyComment
    confidence: float = Field(ge=0, le=1)
    charitable_reading: str = ""
    hostile_reading: str = ""
    distinct_reaction: bool | None = None


# --------------------------------------------------------------------------
# Persona registry
# --------------------------------------------------------------------------


class Demographics(BaseModel):
    region: str
    sub_region: list[str] = Field(default_factory=list)
    age_band: tuple[int, int] = (18, 99)
    urbanicity: Literal["urban", "suburban", "rural", "mixed"] = "mixed"
    languages: list[str] = Field(default_factory=list)
    audience_type: Literal["target", "secondary", "unintended", "amplifier", "control"] = (
        "secondary"
    )


class SensitivityProfile(BaseModel):
    """Per-axis sensitivity, 0-1. Drives both the prompt and router matching (§6.1)."""

    religious_symbols: float = Field(default=0.0, ge=0, le=1)
    dietary_practice: float = Field(default=0.0, ge=0, le=1)
    gender_representation: float = Field(default=0.0, ge=0, le=1)
    caste_and_class: float = Field(default=0.0, ge=0, le=1)
    national_identity: float = Field(default=0.0, ge=0, le=1)
    body_and_appearance: float = Field(default=0.0, ge=0, le=1)
    sexual_content: float = Field(default=0.0, ge=0, le=1)
    political_alignment: float = Field(default=0.0, ge=0, le=1)
    disability: float = Field(default=0.0, ge=0, le=1)
    race_and_ethnicity: float = Field(default=0.0, ge=0, le=1)
    environmental_claims: float = Field(default=0.0, ge=0, le=1)
    formality_and_respect: float = Field(default=0.0, ge=0, le=1)

    def as_vector(self) -> list[float]:
        return [getattr(self, k) for k in SensitivityProfile.axis_names()]

    @staticmethod
    def axis_names() -> list[str]:
        return sorted(SensitivityProfile.model_fields)


class PersonaNode(BaseModel):
    """An authored persona. Tier 1 — hand-written, source-anchored, versioned."""

    id: str
    version: int = 1
    label: str

    demographics: Demographics
    sensitivity_profile: SensitivityProfile

    # Population parameters. Likelihood in the Severity x Likelihood matrix
    # (§12.1) comes from prevalence_weight, NEVER from asking an LLM how likely
    # something is: a model's self-estimate is an opinion, a prevalence weight
    # is a parameter you control and can defend to a client.
    prevalence_weight: float = Field(ge=0, le=1)
    vocality: float = Field(ge=0, le=1)
    is_target: bool = False

    persona_notes: str
    # The calibration block. Without it, LLM personas flag everything — the
    # model's instinct is maximal caution, which produces a tool that cries wolf
    # and is ignored within a week (§22.2).
    failure_modes: str

    source: str = ""
    mandatory: bool = False

    @property
    def key(self) -> str:
        return f"{self.id}@v{self.version}"

    @property
    def is_control(self) -> bool:
        """Diagnostic instrument, not audience.

        ``hard_negative_control`` is a live over-triggering canary (§6.2): if it
        fires, calibration has drifted. It must never contribute prevalence mass
        to the score, or the canary would be counted as a member of the public
        it exists to monitor.
        """
        return self.demographics.audience_type == "control"
