"""Historical campaign-failure corpus.

Turns raw news into labelled incidents that the comparison panels can query:
*has something like this blown up before, and what set it off?*

**The honest caveat, stated here rather than buried.** Outcome labels mined from
news are *journalist narrative*, not measured outcomes. A headline saying a brand
"faced backlash" tells you a story was written, not that sales moved. Every
entry therefore carries ``label_confidence`` and ``label_source``, and the
comparison panels must surface those rather than presenting a mined incident as
established fact. A similarity model built on confident-but-wrong labels will
tell a marketer their campaign resembles a disaster when it does not, which is
worse than having no corpus at all.

Storage is JSONL on disk. Deliberately boring: the corpus is append-mostly, a
few thousand rows at most before this needs Postgres, and a file keeps the
repo runnable with no infrastructure.
"""

from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

DEFAULT_CORPUS_PATH = Path(__file__).parent / "data" / "incidents.jsonl"

IncidentKind = Literal[
    "cultural_religious",
    "representation",
    "tone_deaf_timing",
    "greenwashing",
    "misleading_claim",
    "political",
    "sexualisation",
    "ableism",
    "unclassified",
]

LabelSource = Literal["mined", "curated", "customer"]

# Signals that a story is about a campaign failing, not just marketing news.
# Deliberately tight: a loose filter fills the corpus with press releases, and a
# corpus of noise is worse than an empty one.
_BACKLASH_SIGNALS = (
    "backlash",
    "pulled the ad",
    "pulls ad",
    "ad pulled",
    "withdrew",
    "withdrawn",
    "apologis",
    "apologiz",
    "outrage",
    "offensive",
    "boycott",
    "criticis",
    "criticiz",
    "slammed",
    "under fire",
    "sparked anger",
    "tone deaf",
    "tone-deaf",
    "accused of",
    "controversy",
    "controversial",
    "row over",
)

# Regex fragments, not bare words: plurals and variants must match. "Ads" in
# "Converse Apologizes ... With Ads That Evoke" was being missed by \bad\b,
# which rejected a textbook backlash story.
_CAMPAIGN_SIGNALS = (
    r"ads?",
    r"advert(s|ising|isement s?)?",
    r"campaigns?",
    r"commercials?",
    r"marketing",
    r"billboards?",
    r"slogans?",
    r"branding",
    r"rebrand(ed|ing)?",
    r"brand",
    r"tvcs?",
    r"creatives?",
    r"spots?",
)

# Terms that mark an article as trade/industry coverage rather than an incident:
# hires, results, awards, conferences. These veto a match outright.
_NOT_INCIDENT_SIGNALS = (
    "appoints",
    "appointed",
    "names new",
    "joins as",
    "promoted to",
    "departs",
    "steps down",
    "hires",
    "study finds",
    "report finds",
    "data shows",
    "survey",
    "festival",
    "awards",
    "shortlist",
    "webinar",
    "podcast",
    "q1 results",
    "q2 results",
    "q3 results",
    "q4 results",
    "full-year results",
)

_KIND_PATTERNS: dict[IncidentKind, tuple[str, ...]] = {
    "cultural_religious": (
        "religio",
        "muslim",
        "islam",
        "hindu",
        "christian",
        "jewish",
        "sikh",
        "halal",
        "kosher",
        "beef",
        "pork",
        "ramadan",
        "diwali",
        "sacred",
        "temple",
        "mosque",
        "church",
        "caste",
        "ethnic",
    ),
    "representation": (
        "racist",
        "racism",
        "blackface",
        "whitewash",
        "diversity",
        "stereotyp",
        "appropriat",
        "colonial",
        "indigenous",
        "minority",
    ),
    "tone_deaf_timing": (
        "tone deaf",
        "tone-deaf",
        "insensitive",
        "during the crisis",
        "amid the",
        "disaster",
        "tragedy",
        "war",
        "recession",
        "layoffs",
    ),
    "greenwashing": (
        "greenwash",
        "climate",
        "sustainab",
        "eco-friendly",
        "carbon",
        "emissions",
        "environmental claim",
        "recyclab",
    ),
    "misleading_claim": (
        "misleading",
        "false advertising",
        "asa ruling",
        "ftc",
        "banned the ad",
        "unsubstantiated",
        "deceptive",
    ),
    "political": (
        "political",
        "election",
        "partisan",
        "government",
        "boycott over",
        "sanction",
        "activis",
    ),
    "sexualisation": (
        "sexualis",
        "sexualiz",
        "objectif",
        "explicit",
        "sexist",
        "misogyn",
    ),
    "ableism": ("ableist", "disabilit", "disabled", "neurodiver", "mental health"),
}

_STOPWORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "to",
    "of",
    "and",
    "or",
    "that",
    "this",
    "it",
    "in",
    "on",
    "for",
    "with",
    "as",
    "at",
    "be",
    "was",
    "were",
    "after",
    "over",
    "its",
    "has",
    "have",
    "had",
    "from",
    "by",
    "said",
    "says",
    "new",
    "ad",
    "ads",
}


@dataclass
class Incident:
    """One documented campaign failure."""

    id: str
    title: str
    url: str
    source: str
    published: str

    kind: IncidentKind = "unclassified"
    brand: str | None = None
    summary: str = ""

    # What we think happened, and how much to trust that.
    outcome: str = ""
    triggers: list[str] = field(default_factory=list)
    label_source: LabelSource = "mined"
    label_confidence: float = 0.0

    # Cohort assignment, filled by ``cohort_incidents``.
    cohort_id: str | None = None

    ingested_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def is_reliable(self) -> bool:
        """Curated and customer-supplied labels are trustworthy; mined ones are
        a lead, and the panels must say so."""
        return self.label_source in ("curated", "customer") or self.label_confidence >= 0.7


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z']+", (text or "").lower())
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def classify_kind(text: str) -> tuple[IncidentKind, float]:
    """Assign an incident kind by keyword density.

    Crude on purpose: this is a first-pass router, and an LLM classification pass
    (``enrich_incident``) refines the entries that matter. Returns the kind plus
    a confidence so weak assignments can be filtered.
    """
    low = (text or "").lower()
    scores: dict[IncidentKind, int] = {}
    for kind, patterns in _KIND_PATTERNS.items():
        hits = sum(1 for p in patterns if p in low)
        if hits:
            scores[kind] = hits

    if not scores:
        return "unclassified", 0.0

    best = max(scores.items(), key=lambda kv: kv[1])
    total = sum(scores.values())
    return best[0], round(best[1] / total, 3)


def looks_like_backlash(title: str, summary: str = "", body: str = "") -> tuple[bool, float]:
    """Does this article describe a campaign failing?

    Requires BOTH a campaign signal and a backlash signal. Marketing news is
    overwhelmingly product launches and hires; without the conjunction the corpus
    fills with press releases.
    """
    text = f"{title} {summary} {body[:2000]}".lower()
    title_low = title.lower()

    # Industry trade coverage is not an incident, however many keywords it hits.
    if any(s in title_low for s in _NOT_INCIDENT_SIGNALS):
        return False, 0.0

    backlash_hits = sum(1 for s in _BACKLASH_SIGNALS if s in text)
    campaign_hits = sum(1 for s in _CAMPAIGN_SIGNALS if re.search(rf"\b{s}\b", text))

    if not backlash_hits:
        return False, 0.0

    title_backlash = sum(1 for s in _BACKLASH_SIGNALS if s in title_low)

    # A strong backlash verb in the HEADLINE is sufficient on its own. Requiring
    # a campaign keyword too rejected "Converse Apologizes After Roiling Social
    # Media With Ads..." — the story is in the verb, and the object may be
    # phrased any number of ways.
    if title_backlash and not campaign_hits:
        campaign_hits = 1

    if not campaign_hits:
        return False, 0.0

    # Title hits weigh most: a headline states the story, a body may merely
    # mention it in passing.
    confidence = min(
        1.0,
        0.2 * backlash_hits + 0.08 * campaign_hits + 0.35 * min(title_backlash, 2),
    )
    return confidence >= 0.4, round(confidence, 3)


def extract_brand(title: str) -> str | None:
    """Best-effort brand extraction from a headline.

    Takes leading capitalised tokens, then strips the verb and filler that
    follow. Naive leading-capitals grabbing produced "Converse Apologizes",
    "Why", "Boycott" and "Factbox" on real headlines, so verbs, question words
    and wire-service markers are excluded explicitly.

    Advisory only — never used as a join key, because it is wrong often enough
    that matching on it would silently merge unrelated incidents.
    """
    # Words that are never part of a brand name, even when capitalised.
    NOT_BRAND = {
        "why",
        "how",
        "what",
        "when",
        "who",
        "where",
        "factbox",
        "exclusive",
        "update",
        "analysis",
        "opinion",
        "video",
        "watch",
        "breaking",
        "the",
        "boycott",
        "calls",
        "row",
        "backlash",
        "outrage",
        "after",
        "amid",
        "over",
        "as",
        "is",
        "was",
        "in",
        "on",
        "at",
        "to",
        "for",
        "and",
    }
    # Verb stems that mark the end of the subject.
    VERB_MARKERS = (
        "apolog",
        "pull",
        "withdraw",
        "face",
        "slam",
        "criticis",
        "criticiz",
        "brand",
        "accus",
        "defend",
        "respond",
        "say",
        "admit",
        "deni",
        "halt",
        "drop",
        "axe",
        "scrap",
        "spark",
        "under",
        "hit",
    )

    words = title.replace("'s", "").split()
    caps: list[str] = []

    for w in words[:5]:
        clean = w.strip(".,:;'\"?!()[]")
        if not clean:
            continue
        low = clean.lower()

        if low in NOT_BRAND:
            break
        if any(low.startswith(v) for v in VERB_MARKERS):
            break
        if clean[0].isupper():
            caps.append(clean)
        elif caps:
            break
        else:
            # Lowercase word before any capital: no brand at the head.
            break

    if not caps:
        return None

    brand = " ".join(caps[:3])
    return brand if 2 <= len(brand) <= 40 else None


class CorpusStore:
    """JSONL-backed incident store with deduplication by URL."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_CORPUS_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: list[Incident] | None = None

    def load(self) -> list[Incident]:
        if self._cache is not None:
            return self._cache

        incidents: list[Incident] = []
        if self.path.exists():
            for line_no, line in enumerate(self.path.read_text().splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    incidents.append(Incident(**json.loads(line)))
                except (json.JSONDecodeError, TypeError) as exc:
                    logger.warning("Corpus line %d unreadable, skipping: %s", line_no, exc)

        self._cache = incidents
        return incidents

    def urls(self) -> set[str]:
        return {i.url for i in self.load()}

    def add(self, incidents: list[Incident]) -> int:
        """Append, skipping URLs already present. Returns the number added."""
        existing = self.urls()
        fresh = [i for i in incidents if i.url and i.url not in existing]
        if not fresh:
            return 0

        with self.path.open("a") as fh:
            for inc in fresh:
                if not inc.ingested_at:
                    inc.ingested_at = datetime.now(UTC).isoformat()
                fh.write(json.dumps(inc.as_dict()) + "\n")

        if self._cache is not None:
            self._cache.extend(fresh)
        logger.info(
            "Corpus: added %d incidents (%d duplicates skipped)",
            len(fresh),
            len(incidents) - len(fresh),
        )
        return len(fresh)

    def replace_all(self, incidents: list[Incident]) -> None:
        """Rewrite the file — used after cohorting assigns cohort ids."""
        with self.path.open("w") as fh:
            for inc in incidents:
                fh.write(json.dumps(inc.as_dict()) + "\n")
        self._cache = list(incidents)

    def stats(self) -> dict[str, Any]:
        incidents = self.load()
        return {
            "total": len(incidents),
            "by_kind": dict(Counter(i.kind for i in incidents)),
            "by_label_source": dict(Counter(i.label_source for i in incidents)),
            "reliable": sum(1 for i in incidents if i.is_reliable),
            "cohorts": len({i.cohort_id for i in incidents if i.cohort_id}),
            "oldest": min((i.published for i in incidents), default=None),
            "newest": max((i.published for i in incidents), default=None),
        }


# --------------------------------------------------------------------------
# Cohorting
# --------------------------------------------------------------------------


def _similarity(a: Incident, b: Incident) -> float:
    """Shared-token similarity, weighted up when the incident kind matches.

    Token overlap alone groups by vocabulary; kind agreement is the stronger
    signal about whether two failures are the *same sort* of failure.
    """
    ta = _tokens(f"{a.title} {a.summary}")
    tb = _tokens(f"{b.title} {b.summary}")
    if not ta or not tb:
        return 0.0

    jaccard = len(ta & tb) / len(ta | tb)
    kind_bonus = 0.35 if a.kind == b.kind and a.kind != "unclassified" else 0.0
    return min(1.0, jaccard + kind_bonus)


def cohort_incidents(incidents: list[Incident], threshold: float = 0.4) -> list[Incident]:
    """Group incidents into cohorts of like failures.

    Agglomerative with a distance threshold, matching the interpretation
    clustering in ``analysis/graph.py`` — cohort count is data-driven, never
    fixed. Assigns ``cohort_id`` in place and returns the same list.
    """
    if len(incidents) < 2:
        return incidents

    clusters: list[list[int]] = [[i] for i in range(len(incidents))]

    while len(clusters) > 1:
        best: tuple[float, int, int] | None = None
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                sim = sum(
                    _similarity(incidents[a], incidents[b])
                    for a in clusters[i]
                    for b in clusters[j]
                ) / (len(clusters[i]) * len(clusters[j]))
                if best is None or sim > best[0]:
                    best = (sim, i, j)

        if best is None or best[0] < threshold:
            break

        _, i, j = best
        clusters[i].extend(clusters[j])
        clusters.pop(j)

    for idx, cluster in enumerate(clusters):
        # Name the cohort after its dominant kind, so the id is readable.
        kinds = Counter(incidents[i].kind for i in cluster)
        dominant = kinds.most_common(1)[0][0]
        cohort_id = f"{dominant}_{idx:03d}"
        for i in cluster:
            incidents[i].cohort_id = cohort_id

    logger.info("Cohorting: %d incidents -> %d cohorts", len(incidents), len(clusters))
    return incidents


def cohort_summary(incidents: list[Incident]) -> list[dict[str, Any]]:
    """Per-cohort rollup for the comparison panels."""
    by_cohort: dict[str, list[Incident]] = {}
    for inc in incidents:
        if inc.cohort_id:
            by_cohort.setdefault(inc.cohort_id, []).append(inc)

    out: list[dict[str, Any]] = []
    for cohort_id, members in by_cohort.items():
        shared = Counter()
        for m in members:
            shared.update(_tokens(m.title))

        reliable = sum(1 for m in members if m.is_reliable)
        out.append(
            {
                "cohort_id": cohort_id,
                "kind": Counter(m.kind for m in members).most_common(1)[0][0],
                "size": len(members),
                "reliable_count": reliable,
                # A cohort built entirely from mined labels is a lead, not
                # evidence, and the panel must say so.
                "reliability": round(reliable / len(members), 3),
                "shared_terms": [w for w, n in shared.most_common(8) if n > 1],
                "examples": [
                    {"title": m.title, "url": m.url, "published": m.published}
                    for m in sorted(members, key=lambda x: x.published, reverse=True)[:3]
                ],
                "brands": sorted({m.brand for m in members if m.brand}),
            }
        )

    return sorted(out, key=lambda c: c["size"], reverse=True)


def find_similar(
    incidents: list[Incident],
    copy: str,
    activated_axes: dict[str, float] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve incidents resembling a piece of copy.

    Token overlap plus an axis-affinity boost: copy activating
    ``dietary_practice`` should surface cultural/religious incidents even when
    the vocabulary differs.
    """
    if not incidents:
        return []

    copy_tokens = _tokens(copy)
    if not copy_tokens:
        return []

    axis_to_kind: dict[str, IncidentKind] = {
        "dietary_practice": "cultural_religious",
        "religious_symbols": "cultural_religious",
        "race_and_ethnicity": "representation",
        "gender_representation": "representation",
        "environmental_claims": "greenwashing",
        "political_alignment": "political",
        "disability": "ableism",
        "sexual_content": "sexualisation",
    }
    boosted_kinds = {
        axis_to_kind[a] for a, v in (activated_axes or {}).items() if v >= 0.4 and a in axis_to_kind
    }

    scored: list[tuple[float, Incident]] = []
    for inc in incidents:
        inc_tokens = _tokens(f"{inc.title} {inc.summary}")
        if not inc_tokens:
            continue
        overlap = len(copy_tokens & inc_tokens)
        if not overlap and inc.kind not in boosted_kinds:
            continue

        # Normalise by the smaller set so a long article does not dominate.
        sim = overlap / math.sqrt(len(copy_tokens) * len(inc_tokens))
        if inc.kind in boosted_kinds:
            sim += 0.25
        scored.append((sim, inc))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {
            "similarity": round(sim, 4),
            "title": inc.title,
            "url": inc.url,
            "source": inc.source,
            "published": inc.published,
            "kind": inc.kind,
            "brand": inc.brand,
            "cohort_id": inc.cohort_id,
            "label_source": inc.label_source,
            "label_confidence": inc.label_confidence,
            "is_reliable": inc.is_reliable,
            "caveat": (
                None
                if inc.is_reliable
                else "Outcome mined from news coverage — a lead to check, not a measured result."
            ),
        }
        for sim, inc in scored[:limit]
    ]
