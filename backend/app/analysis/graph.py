"""Backlash Pathway — the causal chain from creative to wider discussion (§16.20).

This is the highest CREDIBILITY risk in the product. A plausible-sounding causal
chain is the panel most likely to be wrong while looking authoritative, because
narrative is persuasive in a way a bar chart is not.

So the model never invents nodes. Every node in the graph is built from
something a persona actually produced — a trigger span they flagged, a
paraphrase they wrote, a comment in their own voice, a behaviour they declared.
The chain terminates where the grounding runs out and says so, rather than
narrating its way to a satisfying conclusion.

Transition likelihoods come from persona behaviour distributions and prevalence
weights, not from asking a model "how likely is this?" — the same discipline as
the Severity x Likelihood matrix (§12.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.personas.schema import PersonaNode
from app.scoring.model import ScoredPersona

StageKind = Literal["creative", "misinterpretation", "reaction", "amplification", "discussion"]

# Behaviours that carry a reaction outward to a wider audience.
_AMPLIFYING = frozenset({"share_mocking", "criticize", "boycott"})


@dataclass
class PathNode:
    id: str
    stage: StageKind
    label: str
    detail: str
    # Every node cites the persona(s) and evidence it was built from. A node with
    # an empty `grounded_in` is a bug, not a finding.
    grounded_in: list[str] = field(default_factory=list)
    evidence: str = ""
    audience_mass: float = 0.0
    severity: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "stage": self.stage,
            "label": self.label,
            "detail": self.detail,
            "grounded_in": self.grounded_in,
            "evidence": self.evidence,
            "audience_mass": round(self.audience_mass, 4),
            "severity": round(self.severity, 4),
        }


@dataclass
class PathEdge:
    source: str
    target: str
    likelihood: float
    basis: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "likelihood": round(self.likelihood, 4),
            "basis": self.basis,
        }


@dataclass
class BacklashPathway:
    nodes: list[PathNode]
    edges: list[PathEdge]
    terminated_at: StageKind | None
    termination_reason: str | None
    overall_likelihood: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.as_dict() for n in self.nodes],
            "edges": [e.as_dict() for e in self.edges],
            "terminated_at": self.terminated_at,
            "termination_reason": self.termination_reason,
            "overall_likelihood": round(self.overall_likelihood, 4),
            "grounding_note": (
                "Every node is built from a persona's own trigger, paraphrase, or "
                "comment. Transition likelihoods come from behaviour distributions "
                "weighted by audience prevalence, not from a model's estimate."
            ),
        }


def build_pathway(
    scored: list[ScoredPersona],
    registry: dict[str, PersonaNode],
    copy: str,
) -> BacklashPathway:
    """Construct the chain, terminating wherever the evidence stops."""
    nodes: list[PathNode] = []
    edges: list[PathEdge] = []
    total_mass = sum(p.weight for p in scored) or 1.0

    # ── Stage 1: the creative ────────────────────────────────────────
    root = PathNode(
        id="creative",
        stage="creative",
        label="The copy as published",
        detail=copy[:200] + ("..." if len(copy) > 200 else ""),
        grounded_in=[],
        evidence="The input itself.",
        audience_mass=1.0,
    )
    nodes.append(root)

    # ── Stage 2: misinterpretation ───────────────────────────────────
    # Grounded in personas who actually misread it, using THEIR paraphrase.
    misreaders = [
        p for p in scored if p.reaction.interpretation.comprehension in ("misread", "partial")
    ]
    if not misreaders:
        return BacklashPathway(
            nodes=nodes,
            edges=edges,
            terminated_at="creative",
            termination_reason=(
                "No persona misread the copy, and none reacted with opposition. "
                "There is no misinterpretation to chain from — the pathway stops "
                "here rather than inventing one."
            ),
            overall_likelihood=0.0,
        )

    worst = max(misreaders, key=lambda p: p.severity)
    misread_mass = sum(p.weight for p in misreaders)
    misread_node = PathNode(
        id="misread",
        stage="misinterpretation",
        label="What they think it says",
        detail=worst.reaction.interpretation.paraphrase,
        grounded_in=[p.reaction.persona_id for p in misreaders],
        evidence=f"{len(misreaders)} persona(s) returned comprehension != understood",
        audience_mass=misread_mass / total_mass,
        severity=max(p.severity for p in misreaders),
    )
    nodes.append(misread_node)
    edges.append(
        PathEdge(
            source="creative",
            target="misread",
            likelihood=misread_mass / total_mass,
            basis=(
                "Prevalence-weighted share of personas who misread: "
                f"{misread_mass / total_mass:.0%}"
            ),
        )
    )

    # ── Stage 3: reaction (a real comment, in a real persona's voice) ─
    opposed = [p for p in scored if p.reaction.is_opposed]
    if not opposed:
        return BacklashPathway(
            nodes=nodes,
            edges=edges,
            terminated_at="misinterpretation",
            termination_reason=(
                "The copy is misread, but no persona opposed it. Misunderstanding "
                "without opposition does not become backlash — it becomes a "
                "clarity problem. The chain stops here."
            ),
            overall_likelihood=round(misread_mass / total_mass, 4),
        )

    loudest = max(opposed, key=lambda p: p.severity)
    opposed_mass = sum(p.weight for p in opposed)
    node = registry.get(loudest.reaction.persona_id)
    reaction_node = PathNode(
        id="reaction",
        stage="reaction",
        label="What they post",
        detail=loudest.reaction.likely_comment.text,
        grounded_in=[p.reaction.persona_id for p in opposed],
        evidence=(
            f"Verbatim likely_comment from {node.label if node else loudest.reaction.persona_id}"
        ),
        audience_mass=opposed_mass / total_mass,
        severity=loudest.severity,
    )
    nodes.append(reaction_node)
    edges.append(
        PathEdge(
            source="misread",
            target="reaction",
            likelihood=opposed_mass / max(misread_mass, 1e-9) if misread_mass > 0 else 0.0,
            basis=f"{len(opposed)} persona(s) returned sentiment=opposed",
        )
    )

    # ── Stage 4: amplification ───────────────────────────────────────
    amplifiers = [p for p in scored if p.reaction.likely_behavior in _AMPLIFYING]
    if not amplifiers:
        return BacklashPathway(
            nodes=nodes,
            edges=edges,
            terminated_at="reaction",
            termination_reason=(
                "Personas object, but none declared a behaviour that carries the "
                "objection outward (criticize, share_mocking, boycott). Quiet "
                "dislike costs sales, not a news cycle. The chain stops here."
            ),
            overall_likelihood=round(opposed_mass / total_mass, 4),
        )

    # Vocality is the registry parameter that says how readily this segment
    # amplifies — a population property, not a model opinion.
    amp_weight = sum(p.weight * p.vocality for p in amplifiers)
    amp_mass = sum(p.weight for p in amplifiers)

    meme_spans = sorted(
        (
            (t.span, p.reaction.risk_flags.meme_potential, p.reaction.persona_id)
            for p in amplifiers
            for t in p.reaction.triggers
        ),
        key=lambda x: x[1],
        reverse=True,
    )
    span_detail = (
        f'The screenshot-able element is "{meme_spans[0][0]}"'
        if meme_spans
        else "No single span dominates; the objection is to the whole framing."
    )

    amp_node = PathNode(
        id="amplify",
        stage="amplification",
        label="How it travels",
        detail=span_detail,
        grounded_in=[p.reaction.persona_id for p in amplifiers],
        evidence=(
            f"{len(amplifiers)} persona(s) declared an amplifying behaviour; "
            f"vocality-weighted mass {amp_weight:.3f}"
        ),
        audience_mass=amp_mass / total_mass,
        severity=max(p.severity for p in amplifiers),
    )
    nodes.append(amp_node)
    edges.append(
        PathEdge(
            source="reaction",
            target="amplify",
            likelihood=min(1.0, amp_weight / max(opposed_mass, 1e-9)),
            basis="Vocality-weighted share of opposed personas who would share or criticize",
        )
    )

    # ── Stage 5: wider discussion ────────────────────────────────────
    # Only reachable when the amplifier persona itself fires. That node exists
    # precisely to model the journalist / quote-tweeter, so we require its
    # evidence rather than extrapolating from ordinary audience reactions.
    amplifier_personas = [
        p
        for p in scored
        if (n := registry.get(p.reaction.persona_id))
        and n.demographics.audience_type == "amplifier"
        and p.severity >= 0.4
    ]

    if not amplifier_personas:
        return BacklashPathway(
            nodes=nodes,
            edges=edges,
            terminated_at="amplification",
            termination_reason=(
                "Individuals would share this, but the amplifier persona (the "
                "journalist / quote-tweeter who turns a complaint into a story) "
                "did not react strongly. Without that, the chain to wider "
                "discussion is speculation, so it stops here."
            ),
            overall_likelihood=round(min(1.0, amp_weight / total_mass), 4),
        )

    top_amp = max(amplifier_personas, key=lambda p: p.severity)
    disc_node = PathNode(
        id="discussion",
        stage="discussion",
        label="Wider discussion",
        detail=top_amp.reaction.likely_comment.text,
        grounded_in=[p.reaction.persona_id for p in amplifier_personas],
        evidence=(
            f"Amplifier persona returned severity {top_amp.severity:.2f} "
            f"with behaviour '{top_amp.reaction.likely_behavior}'"
        ),
        audience_mass=sum(p.weight for p in amplifier_personas) / total_mass,
        severity=top_amp.severity,
    )
    nodes.append(disc_node)
    edges.append(
        PathEdge(
            source="amplify",
            target="discussion",
            likelihood=top_amp.severity * top_amp.confidence,
            basis="Amplifier persona severity x its own confidence",
        )
    )

    # Overall likelihood is the product of the chain — a long chain is less
    # likely than any single link, which is the honest way to read it.
    overall = 1.0
    for e in edges:
        overall *= e.likelihood

    return BacklashPathway(
        nodes=nodes,
        edges=edges,
        terminated_at=None,
        termination_reason=None,
        overall_likelihood=round(overall, 4),
    )


def interpretation_clusters(
    scored: list[ScoredPersona],
    threshold: float = 0.35,
) -> list[dict[str, Any]]:
    """'What They Think You're Saying' (§11.1) — agglomerative clustering of
    paraphrases by token overlap.

    Uses a DISTANCE THRESHOLD, not a fixed k: cluster count must be data-driven.
    Fixing k=3 manufactures three interpretations whether or not three exist,
    which is exactly the fabrication risk this panel must avoid.

    Token-level Jaccard stands in for embeddings at this stage. It is cruder but
    has no network dependency; swap in embeddings when the vector store lands.
    """
    if not scored:
        return []

    items = [
        (p.reaction.persona_id, p.reaction.interpretation.paraphrase, p.weight)
        for p in scored
        if p.reaction.interpretation.paraphrase.strip()
    ]
    if not items:
        return []

    def tokens(s: str) -> set[str]:
        stop = {
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
            "they",
            "you",
            "your",
            "me",
            "my",
            "i",
            "in",
            "on",
            "for",
            "with",
            "as",
            "at",
            "be",
            "was",
            "were",
        }
        return {w.strip(".,!?\"'").lower() for w in s.split()} - stop

    def distance(a: str, b: str) -> float:
        """Blend of Jaccard and overlap coefficient.

        Raw Jaccard punishes length differences: "they think my religion is a
        joke" vs "...a joke worth mocking" scores 0.40 apart despite one fully
        containing the other, which splits readings that are plainly the same.
        The overlap coefficient (intersection over the SMALLER set) handles that
        subsumption correctly but treats any subset as identical, so a short
        vague paraphrase would absorb everything.

        Weighting toward overlap keeps near-duplicates together while still
        separating genuinely different readings, which score 1.0 under both.
        """
        ta, tb = tokens(a), tokens(b)
        if not ta or not tb:
            return 1.0
        inter = len(ta & tb)
        jaccard_sim = inter / len(ta | tb)
        overlap_sim = inter / min(len(ta), len(tb))
        return 1.0 - (0.4 * jaccard_sim + 0.6 * overlap_sim)

    # Agglomerative: start with singletons, merge the closest pair until the
    # closest pair exceeds the threshold.
    clusters: list[list[int]] = [[i] for i in range(len(items))]

    while len(clusters) > 1:
        best: tuple[float, int, int] | None = None
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                # Average linkage.
                d = sum(
                    distance(items[a][1], items[b][1]) for a in clusters[i] for b in clusters[j]
                ) / (len(clusters[i]) * len(clusters[j]))
                if best is None or d < best[0]:
                    best = (d, i, j)

        if best is None or best[0] > threshold:
            break

        _, i, j = best
        clusters[i].extend(clusters[j])
        clusters.pop(j)

    out: list[dict[str, Any]] = []
    for cluster in clusters:
        mass = sum(items[i][2] for i in cluster)
        # Label with the MEDOID — a real persona's actual words, never a
        # synthesized summary that no one said.
        medoid = min(
            cluster,
            key=lambda i: sum(distance(items[i][1], items[j][1]) for j in cluster),
        )
        out.append(
            {
                "label": items[medoid][1],
                "label_from_persona": items[medoid][0],
                "personas": [items[i][0] for i in cluster],
                "audience_mass": round(mass, 4),
                "size": len(cluster),
            }
        )

    total = sum(c["audience_mass"] for c in out) or 1.0
    for c in out:
        c["share"] = round(c["audience_mass"] / total, 4)

    return sorted(out, key=lambda c: c["audience_mass"], reverse=True)
