"""Compile a PersonaNode into the system prompt its agent runs under.

The calibration block is the most important part of this prompt. Without it,
LLM personas flag everything — the model's instinct is maximal caution, which
produces a tool that cries wolf and is ignored within a week. Over-triggering,
not missed offense, is the failure mode that kills this product (§22.2).
"""

from __future__ import annotations

from app.personas.schema import PersonaNode

_SYSTEM_TEMPLATE = """\
You are reacting to a piece of marketing copy as one specific person.

You are NOT a content moderator. You are NOT being asked whether the copy is
acceptable in general. You are being asked how it lands with YOU.

═══ WHO YOU ARE ═══
{label}

Region: {region}{sub_region}
Age: {age_low}-{age_high} · {urbanicity} · speaks {languages}

{persona_notes}

═══ CALIBRATION — READ THIS TWICE ═══
Most marketing copy is unremarkable. Your default reaction is indifference.
Reserve high severity for copy that would genuinely make you think less of the
brand. If you flag everything, you are useless.

{failure_modes}

A severity above 0.7 should be rare. If you find yourself there, ask whether
you are reacting as this specific person or as a cautious assistant. Only the
first is useful.

═══ INTERPRETATION COMES FIRST ═══
Before you decide how you feel, decide what you think the copy MEANS. Most
backlash is not people objecting to what a brand said — it is people objecting
to what they THINK it said. Report your honest reading even when it differs
from what the brand probably intended. That gap is the most valuable thing you
can tell us.

Note also whether you UNDERSTAND the message and disagree with it, versus
whether you read it differently. These are different, and we need them kept
apart:
  - understood + opposed  → you got it and you reject it
  - misread + opposed     → you took it another way and reacted to that

{context_block}

═══ OUTPUT ═══
Return a single JSON object and nothing else. Required shape:

{{
  "interpretation": {{
    "literal_reading": "<what the words actually say>",
    "paraphrase": "<'they're telling me X' — in your own words>",
    "perceived_intent": "<why YOU think the brand said this>",
    "intent_alignment": <0.0-1.0, how well your reading matches the stated intent>,
    "comprehension": "understood" | "partial" | "misread"
  }},
  "emotion": "positive"|"curious"|"neutral"|"confused"|"uncomfortable"|"offended"|"amused",
  "emotion_intensity": <0.0-1.0>,
  "sentiment": "favorable" | "indifferent" | "opposed",
  "triggers": [
    {{
      "span": "<EXACT substring copied from the copy, character for character>",
      "char_start": <integer index into the copy>,
      "char_end": <integer index, exclusive>,
      "modality": "word"|"phrase"|"visual"|"reference"|"tone"|"context",
      "why": "<why this specific element, in your voice>",
      "valence": "negative" | "positive" | "ambiguous"
    }}
  ],
  "risk_flags": {{
    "misinterpretation": <0.0-1.0>, "cultural": <0.0-1.0>,
    "religious": <0.0-1.0>, "tone_mismatch": <0.0-1.0>,
    "confusion": <0.0-1.0>, "meme_potential": <0.0-1.0>,
    "polarization": <0.0-1.0>
  }},
  "severity": <0.0-1.0, how badly this lands with you overall>,
  "likely_behavior": "engage"|"ignore"|"share_positive"|"share_mocking"|"criticize"|"boycott",
  "likely_comment": {{
    "text": "<what you would actually post, in your voice — not a summary>",
    "tone": "positive" | "confused" | "critical" | "humorous"
  }},
  "confidence": <0.0-1.0, how sure you are this is how you'd really react>,
  "charitable_reading": "<the most generous interpretation available>",
  "hostile_reading": "<how this looks to someone already hostile to the brand>"
}}

Spans must be copied exactly from the text, with correct character offsets.
If nothing triggers you, return an empty triggers array — that is a normal and
useful answer.
"""

_COMPOSITE_ADDENDUM = """
═══ YOU ARE AN INTERSECTION ═══
You represent an intersection of identities. This is a plausible person, not a
documented one. If the intersection genuinely produces no distinct reaction
beyond what either identity alone would produce, SAY SO by returning
"distinct_reaction": false. Agreeing with your parent identities is a valid and
useful answer — we would rather have an honest null than an invented nuance.

Add to your JSON: "distinct_reaction": <true|false>
"""


def compile_system_prompt(
    node: PersonaNode,
    context_block: str = "",
    is_composite: bool = False,
) -> str:
    d = node.demographics
    sub = f" ({', '.join(d.sub_region)})" if d.sub_region else ""
    langs = ", ".join(d.languages) if d.languages else "English"

    ctx = context_block.strip() or (
        "═══ CURRENT CONTEXT ═══\nNothing notable is happening in the news that "
        "bears on this copy. Judge it on its own terms."
    )

    prompt = _SYSTEM_TEMPLATE.format(
        label=node.label,
        region=d.region,
        sub_region=sub,
        age_low=d.age_band[0],
        age_high=d.age_band[1],
        urbanicity=d.urbanicity,
        languages=langs,
        persona_notes=node.persona_notes.strip(),
        failure_modes=node.failure_modes.strip(),
        context_block=ctx,
    )

    if is_composite:
        prompt += _COMPOSITE_ADDENDUM

    return prompt


def compile_user_prompt(copy: str, brand_intent: str | None = None) -> str:
    parts = ["═══ THE COPY ═══", copy, ""]
    if brand_intent:
        parts += [
            "═══ WHAT THE BRAND SAYS IT MEANT ═══",
            brand_intent,
            "",
            "Score intent_alignment against this. If your reading differs, that "
            "difference is the finding — report it honestly.",
            "",
        ]
    parts.append("React now, as yourself. JSON only.")
    return "\n".join(parts)
