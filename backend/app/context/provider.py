"""Current-context provider (§8 of the plan).

The same copy is not equally risky in every week of the year. A dietary joke is
harmless in a quiet month and inflammatory during an active religious-dietary
news cycle. This module supplies the news/current-events layer that produces
kappa, the context multiplier consumed by ``app.scoring.model.compute_score``.

Three decisions carry weight in here:

1. **Context never breaks a run.** A missing fixture, an unparseable file, or a
   future live feed returning nothing all degrade to the quiet baseline with a
   logged warning. A failed news lookup must never cost a marketer their
   analysis — unlike the persona registry, which fails loudly because a missing
   persona is a silent blind spot.
2. **kappa is clamped to [0.8, 1.5].** Context adjusts a score; it must never
   dominate it. The evidence here is the weakest in the system (headline
   salience is a heuristic), so it gets the narrowest authority.
3. **Provenance is a first-class field, not metadata.** ``as_dict`` surfaces it
   prominently because the UI renders a provenance badge: a marketer must never
   be unable to tell whether the context that moved their score was a real news
   signal or a local fixture.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal, Protocol

from app.personas.schema import SensitivityProfile

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).parent / "fixtures"

QUIET_SCENARIO = "quiet"

Provenance = Literal["mock", "gdelt", "rss", "newsapi", "x_api"]
Stance = Literal["critical", "neutral", "supportive"]

# kappa bounds (§8.2). Context is an adjustment, never the verdict.
KAPPA_FLOOR = 0.8
KAPPA_CEILING = 1.5

# How far a fully-activated, fully-hot axis can push kappa above baseline.
# 0.5 means maximum overlap lands exactly on the ceiling, so the clamp is a
# guard rail rather than the normal operating point.
KAPPA_GAIN = 0.5

_PROMPT_HEADER = "═══ CURRENT CONTEXT ═══"

_WHY_IT_MATTERS = (
    "Why this matters: identical copy can be unremarkable in a quiet month and "
    "inflammatory during an active news cycle. Read the copy as someone who has "
    "been seeing the stories above in their feed all week."
)


@dataclass(frozen=True)
class ContextItem:
    """One news signal. ``salience`` is how loudly it is being discussed, 0-1."""

    headline: str
    source: str
    date: str
    stance: Stance
    salience: float

    def as_dict(self) -> dict:
        return {
            "headline": self.headline,
            "source": self.source,
            "date": self.date,
            "stance": self.stance,
            "salience": self.salience,
        }


@dataclass(frozen=True)
class ContextBundle:
    """The current-events picture for one run."""

    scenario: str
    items: list[ContextItem] = field(default_factory=list)
    heat_by_topic: dict[str, float] = field(default_factory=dict)
    heat_by_axis: dict[str, float] = field(default_factory=dict)
    active_controversies: list[str] = field(default_factory=list)
    as_of: str = ""
    provenance: Provenance = "mock"

    # -- kappa ------------------------------------------------------------

    def multiplier_for(self, activated_axes: dict[str, float]) -> float:
        """Compute kappa, the context multiplier, clamped to [0.8, 1.5].

        The intuition: risk rises when the copy touches an axis that the news
        cycle has *already made salient*. Touching a cold axis costs nothing;
        touching a hot one costs in proportion to both how hard the copy leans
        on it and how hot it currently is.

        Formula::

            overlap = sum_a(activation[a] * heat[a]) / sum_a(activation[a])
            kappa   = clamp(1.0 + KAPPA_GAIN * overlap, 0.8, 1.5)

        The sum runs over the axes the copy activates. Normalizing by total
        activation makes this an *activation-weighted mean heat* rather than a
        raw sum, so a copy that activates six axes is not penalised merely for
        being broad — only for being broad across hot ground.

        Consequences worth stating explicitly:

        - No overlap, no activation, or an all-quiet bundle gives exactly 1.0.
          The quiet fixture is therefore the kappa=1.0 reference, and a run
          against it scores identically to a run with no context layer at all.
        - kappa never drops below 1.0 from this formula. A quiet news cycle is
          an absence of aggravation, not evidence that copy is safe; the 0.8
          floor exists for future providers that can positively establish a
          calmer-than-usual environment, and for defensive clamping.
        - Maximum (activation 1.0 on an axis at heat 1.0) is 1.5, the ceiling.

        Unknown axis names in either mapping are ignored rather than raising:
        an upstream feed inventing a topic label must not break a run.
        """
        if not activated_axes or not self.heat_by_axis:
            return 1.0

        known = set(SensitivityProfile.axis_names())

        weighted_heat = 0.0
        total_activation = 0.0
        for axis, activation in activated_axes.items():
            if axis not in known:
                logger.debug("Ignoring unknown sensitivity axis %r in activated_axes", axis)
                continue
            activation = _clamp01(activation)
            if activation <= 0:
                continue
            heat = _clamp01(self.heat_by_axis.get(axis, 0.0))
            weighted_heat += activation * heat
            total_activation += activation

        if total_activation <= 0:
            return 1.0

        overlap = weighted_heat / total_activation
        kappa = 1.0 + KAPPA_GAIN * overlap
        return round(min(KAPPA_CEILING, max(KAPPA_FLOOR, kappa)), 4)

    # -- prompt rendering --------------------------------------------------

    @property
    def is_quiet(self) -> bool:
        """True when there is nothing here worth putting in a persona prompt."""
        if self.items or self.active_controversies:
            return False
        return max(self.heat_by_axis.values(), default=0.0) < 0.1

    def as_prompt_block(self) -> str:
        """Render the context for injection into a persona system prompt.

        Deliberately plain text rather than JSON: this is read by a persona in
        character, not parsed. The 'why this matters' line is load-bearing — a
        persona given a bare headline list tends to treat it as trivia, whereas
        naming the mechanism makes it read the copy through the news cycle.
        """
        if self.is_quiet:
            return (
                f"{_PROMPT_HEADER}\n"
                f"As of {self.as_of or 'today'}, nothing notable is happening on the "
                "topics this copy touches. No active controversy, no elevated news "
                "cycle. React as you would in an ordinary week."
            )

        lines = [_PROMPT_HEADER, f"As of {self.as_of or 'today'}:", ""]

        if self.active_controversies:
            lines.append("Active controversies right now:")
            lines.extend(f"  - {c}" for c in self.active_controversies)
            lines.append("")

        if self.items:
            lines.append("In the news:")
            for item in sorted(self.items, key=lambda i: i.salience, reverse=True):
                lines.append(
                    f"  - [{item.date}] {item.headline} "
                    f"({item.source}; {item.stance} framing, salience {item.salience:.2f})"
                )
            lines.append("")

        hot_topics = _hot_entries(self.heat_by_topic)
        if hot_topics:
            lines.append(
                "Topics with elevated attention: "
                + ", ".join(f"{k} ({v:.0%})" for k, v in hot_topics)
            )

        hot_axes = _hot_entries(self.heat_by_axis)
        if hot_axes:
            lines.append(
                "Sensitivities running hot: " + ", ".join(f"{k} ({v:.0%})" for k, v in hot_axes)
            )

        lines.append("")
        lines.append(_WHY_IT_MATTERS)
        return "\n".join(lines)

    # -- serialization -----------------------------------------------------

    def as_dict(self) -> dict:
        """Serialize for the API response.

        ``provenance`` is emitted first and duplicated into a ``badge`` block
        the UI renders unconditionally. This is not cosmetic: a score moved by
        context is only defensible if the reader can see at a glance whether
        that context was a live feed or a local fixture. Silent fixture data
        presented as real news is the one failure this layer must not have.
        """
        is_live = self.provenance != "mock"
        return {
            "provenance": self.provenance,
            "provenance_badge": {
                "value": self.provenance,
                "is_live": is_live,
                "label": "Live context" if is_live else "Mock context (fixture)",
            },
            "scenario": self.scenario,
            "as_of": self.as_of,
            "is_quiet": self.is_quiet,
            "items": [i.as_dict() for i in self.items],
            "heat_by_topic": dict(self.heat_by_topic),
            "heat_by_axis": dict(self.heat_by_axis),
            "active_controversies": list(self.active_controversies),
        }


def _clamp01(value: float) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, max(0.0, v))


def _hot_entries(heat: dict[str, float], threshold: float = 0.2) -> list[tuple[str, float]]:
    return sorted(
        ((k, v) for k, v in heat.items() if v >= threshold),
        key=lambda kv: kv[1],
        reverse=True,
    )


def quiet_bundle(scenario: str = QUIET_SCENARIO, as_of: str = "") -> ContextBundle:
    """The kappa=1.0 reference bundle. Also the universal fallback."""
    return ContextBundle(
        scenario=scenario,
        items=[],
        heat_by_topic={},
        heat_by_axis={},
        active_controversies=[],
        as_of=as_of,
        provenance="mock",
    )


class ContextProvider(Protocol):
    """Source of the current-events layer.

    Implementations MUST NOT raise from ``fetch``. Live providers (GDELT, RSS,
    NewsAPI, X) will fail intermittently by nature; every such failure degrades
    to ``quiet_bundle()`` so that a network problem costs accuracy, never a run.
    """

    def fetch(self, scenario: str = QUIET_SCENARIO) -> ContextBundle: ...

    def list_scenarios(self) -> list[str]: ...


class MockContextProvider:
    """Fixture-backed provider. Reads ``app/context/fixtures/*.json``.

    Every bundle it returns carries ``provenance="mock"``, whatever the file
    claims, so a fixture can never masquerade as a live feed downstream.
    """

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        self.fixtures_dir = fixtures_dir or FIXTURES_DIR

    def list_scenarios(self) -> list[str]:
        if not self.fixtures_dir.is_dir():
            logger.warning("Context fixtures directory not found: %s", self.fixtures_dir)
            return []
        return sorted(p.stem for p in self.fixtures_dir.glob("*.json"))

    def fetch(self, scenario: str = QUIET_SCENARIO) -> ContextBundle:
        """Load a scenario, falling back to the quiet baseline on any problem.

        Never raises. A context lookup that fails is a degraded run, not a
        failed one.
        """
        path = self.fixtures_dir / f"{scenario}.json"
        if not path.is_file():
            logger.warning(
                "Context scenario %r not found at %s; falling back to the quiet "
                "baseline (kappa=1.0). Available: %s",
                scenario,
                path,
                ", ".join(self.list_scenarios()) or "none",
            )
            return quiet_bundle()

        try:
            raw = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Context scenario %r failed to load (%s); falling back to the quiet "
                "baseline (kappa=1.0).",
                scenario,
                exc,
            )
            return quiet_bundle()

        try:
            return _bundle_from_raw(raw, fallback_scenario=scenario)
        except Exception as exc:  # noqa: BLE001 - context must never break a run
            logger.warning(
                "Context scenario %r is malformed (%s); falling back to the quiet "
                "baseline (kappa=1.0).",
                scenario,
                exc,
            )
            return quiet_bundle()


def _bundle_from_raw(raw: object, fallback_scenario: str) -> ContextBundle:
    """Build a bundle from parsed JSON, dropping anything unusable.

    Lenient by design: an unknown axis name or a malformed item is skipped with
    a warning rather than failing the bundle, because a partly-usable context
    signal still beats no context at all.
    """
    if not isinstance(raw, dict):
        raise ValueError("expected a JSON object at the top level")

    items: list[ContextItem] = []
    for entry in raw.get("items") or []:
        if not isinstance(entry, dict):
            logger.warning("Skipping non-object context item in %r", fallback_scenario)
            continue
        stance = entry.get("stance", "neutral")
        if stance not in ("critical", "neutral", "supportive"):
            logger.warning("Context item has unknown stance %r; treating as neutral", stance)
            stance = "neutral"
        items.append(
            ContextItem(
                headline=str(entry.get("headline", "")),
                source=str(entry.get("source", "")),
                date=str(entry.get("date", "")),
                stance=stance,
                salience=_clamp01(entry.get("salience", 0.0)),
            )
        )

    known_axes = set(SensitivityProfile.axis_names())
    heat_by_axis: dict[str, float] = {}
    for axis, value in (raw.get("heat_by_axis") or {}).items():
        if axis not in known_axes:
            logger.warning(
                "Context scenario %r references unknown sensitivity axis %r; ignoring it.",
                fallback_scenario,
                axis,
            )
            continue
        heat_by_axis[axis] = _clamp01(value)

    heat_by_topic = {str(k): _clamp01(v) for k, v in (raw.get("heat_by_topic") or {}).items()}

    controversies = [str(c) for c in (raw.get("active_controversies") or [])]

    return ContextBundle(
        scenario=str(raw.get("scenario") or fallback_scenario),
        items=items,
        heat_by_topic=heat_by_topic,
        heat_by_axis=heat_by_axis,
        active_controversies=controversies,
        as_of=str(raw.get("as_of") or ""),
        # Hard-coded, not read from the file: a fixture must never be able to
        # claim it came from a live feed.
        provenance="mock",
    )


@lru_cache(maxsize=1)
def get_context_provider() -> ContextProvider:
    """The process-wide provider singleton.

    Returns the mock provider today. When a live provider lands, swap it here —
    every call site reads ``provenance`` off the bundle, so nothing downstream
    needs to know which one it got.
    """
    return MockContextProvider()


def list_scenarios() -> list[str]:
    """Scenario names the current provider can serve."""
    return get_context_provider().list_scenarios()


def reload_context_provider() -> ContextProvider:
    get_context_provider.cache_clear()
    return get_context_provider()
