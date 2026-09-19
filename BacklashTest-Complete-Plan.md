# BacklashTest — Complete Product & Implementation Plan

**A proactive simulation environment for marketers**

**Date:** 2026-09-19
**Status:** Consolidated plan — supersedes `Brand-Risk-Persona-Scoring-MVP-Plan.md` and `Brand-Risk-Persona-Graph-Addendum.md`
**Scope:** Product framing, persona graph architecture, full mathematical specification, all 24 dashboard analyses, build sequencing

---

## Table of Contents

**Part I — Product**
1. The Problem and the Bet
2. What This Is: A Simulation Environment
3. The Eight Questions

**Part II — Engine**
4. Persona Graph Architecture
5. The Reaction Object — the load-bearing schema
6. Persona Selection (N→K)
7. Composition and the Two-Tier Split

**Part III — Mathematics**
8. Notation and Inputs
9. Core Risk Model
10. Interpretation Mathematics
11. Clustering and Grouping
12. Matrix Placement Mathematics
13. Uncertainty Quantification
14. Comparison Mathematics

**Part IV — Dashboard**
15. Dependency Structure of the 24 Analyses
16. Panel Specifications
17. Information Architecture

**Part V — Delivery**
18. Technical Architecture
19. Validation
20. Build Phases
21. Cost Model
22. Risks
23. Open Questions

---

# PART I — PRODUCT

## 1. The Problem and the Bet

### 1.1 The problem

Marketing teams ship copy and discover the offense afterward, when unwinding it is expensive. The failure mode is almost never malice — it is **blind spots**. A copywriter in one cultural context does not know that a phrase, image, or food metaphor reads as an insult somewhere else.

The canonical case: **animals as food**. "Our new beef-packed protein bar" is neutral in Chicago, a live religious offense across much of India, and irrelevant in Sweden. Nobody was careless. They simply were not the audience that reacts.

Existing mitigations fail in specific ways:

| Mitigation | Why it fails |
|---|---|
| Legal/compliance review | Catches regulatory risk, not cultural risk. Slow. |
| Toxicity classifiers (Perspective, moderation APIs) | Score "beef" at 0.001. They measure *whether text is abusive*, not *who will be upset by it*. Wrong instrument entirely. |
| Human focus groups | Correct but cost thousands and take a week. Unusable at social tempo. |
| Internal gut-check | The blind spot is definitionally invisible to the people who have it. |

### 1.2 The bet

> **Offense is not a property of text. It is a relationship between text and an audience.**

So the primitive is not a classifier. It is a **population of simulated audiences**, each with distinct values, sensitivities, and readings of context. Score by simulating reactions across that population and aggregating with statistics that respect what simulation can and cannot tell you.

An LLM is a reasonable — imperfect, see §22 — simulator of *"how would a 34-year-old observant Hindu small-business owner in Pune read this line?"* That is the core technical bet.

### 1.3 The critical reframe: interpretation before offense

The most important design decision in this document, and the thing that separates BacklashTest from a content-safety tool:

**Most backlash is not caused by people being offended by what you said. It is caused by people being offended by what they think you said.**

These are different failures with different fixes:

- **Misunderstood** → the copy is ambiguous → *clarify it*
- **Controversial** → the copy is understood and rejected → *decide whether you accept that cost*

A tool that reports only "risk: 62" cannot distinguish these, and therefore cannot tell a marketer what to do. Every analysis in this plan is built on a schema that models **interpretation first and reaction second**. That is why §5 separates `comprehension` from `sentiment` as independent axes, and why "What They Think You're Saying" (§16.4) is arguably the product's most valuable panel.

---

## 2. What This Is: A Simulation Environment

The framing the user asked for, and it changes the product's shape:

BacklashTest is not a checker that returns a verdict. It is an **environment marketers work inside**, proactively, while the campaign is still malleable.

| Checker | Simulation environment |
|---|---|
| Run once before publish | Run continuously during creation |
| Returns a score | Returns a *world model* you can interrogate |
| Pass/fail | "What happens if…" |
| Output is a number | Output is understanding |

Consequences for the design:

1. **Everything is re-runnable.** Edit the copy, re-simulate, see what moved. §16.22.
2. **Everything is interrogable.** Every number drills to the persona reactions that produced it. No opaque aggregates.
3. **Counterfactuals are first-class.** "What if we target a different region?" is a re-run with different persona weights, not a new product.
4. **State persists.** Campaigns, versions, and reaction histories are stored — which is what makes comparison (§14) and learning (§7.4) possible.

---

## 3. The Eight Questions

The entire dashboard reduces to eight questions. This is the information architecture, and every one of the 24 analyses hangs off one of them.

| | Question | Panels |
|---|---|---|
| 🧠 | **What did they understand?** | Intent vs Interpretation · What They Think You're Saying · Intent Alignment Score |
| ❤️ | **How did they feel?** | Emotional Response · Persona Reactions · Simulated Comments |
| ⚠️ | **Why might they react badly?** | Why Is It Risky · Risk Anatomy · Severity × Likelihood · Controversial vs Misunderstood |
| 🎯 | **Who is affected?** | Audience Heatmap · Region Heatmap · Target vs Unintended · Who Might Misunderstand |
| 🔍 | **What exactly caused it?** | Trigger Detection · Meme Potential · Backlash Pathway |
| 📊 | **How does it compare?** | Campaign Comparison · Campaign × Persona · Historical Similarity |
| ✏️ | **How can we fix it?** | Rewrite Suggestions |
| 🔄 | **Did the fix work?** | Before vs After |

---

# PART II — ENGINE

## 4. Persona Graph Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│  PERSONA REGISTRY — N = 40–60 authored nodes                      │
│  Hand-authored · source-anchored · versioned · calibrated         │
└───────────────────────────┬───────────────────────────────────────┘
                            │  ROUTER (§6): N → K ≈ 11
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│  TIER 1 — MEASUREMENT                                             │
│  K selected base nodes react independently                        │
│  → Reaction Objects (§5)                                          │
│  → Feeds: risk score, CI, and ALL 24 panels                       │
└───────────────────────────┬───────────────────────────────────────┘
                            │  COMPOSITION (§7): EIG-selected pairs
                            ▼
┌───────────────────────────────────────────────────────────────────┐
│  TIER 2 — DISCOVERY                                               │
│  M ≈ 12 composite personas (intersectional)                       │
│  → Blind Spot Findings, reported separately                       │
│  → NEVER enters the score (§7.2)                                  │
└───────────────────────────────────────────────────────────────────┘
```

### 4.1 Why multi-agent rather than one prompt

A single prompt asking "score this for offensiveness" produces a hedged 5/10 with generic caveats, and hides its reasoning where it cannot be audited. Separate persona agents give four things a monolith cannot:

1. **Independence** — each reasons without seeing others' verdicts, producing genuine variance to compute statistics over. Converged agents carry no information in their spread.
2. **Auditability** — *"Persona P7 rated this 8/10 because…"* is actionable. "The model says 6.2" is not.
3. **Calibration surface** — per-persona weights tune against outcome data. A monolith has no tunable internals.
4. **Parallelism** — 12 concurrent Sonnet calls finish in the time of the slowest (~6s).

---

## 5. The Reaction Object

**This schema is the most important artifact in the plan.** 14 of the 24 dashboard analyses are pure projections over it — zero additional LLM calls. Get it right and the dashboard is largely SQL. Get it wrong and each panel becomes its own pipeline, and the panels will disagree with each other.

```typescript
interface ReactionObject {
  persona_id: string
  persona_version: number
  tier: 1 | 2

  // ═══ COMPREHENSION — powers Q1 (🧠) ═══
  interpretation: {
    literal_reading: string       // what the words say
    paraphrase: string            // "they're telling me X" — clustered in §11
    perceived_intent: string      // why they think the brand said it
    intent_alignment: number      // 0–1, match to stated brand intent
    comprehension: "understood" | "partial" | "misread"
  }

  // ═══ AFFECT — powers Q2 (❤️) ═══
  emotion: "positive" | "curious" | "neutral" | "confused"
         | "uncomfortable" | "offended" | "amused"     // CLOSED ENUM
  emotion_intensity: number       // 0–1
  sentiment: "favorable" | "indifferent" | "opposed"   // INDEPENDENT of comprehension

  // ═══ CAUSAL ATTRIBUTION — powers Q5 (🔍) ═══
  triggers: Array<{
    span: string                  // exact substring of the copy
    char_start: number            // offset — enables highlight + cross-persona join
    char_end: number
    modality: "word" | "phrase" | "visual" | "reference" | "tone" | "context"
    why: string
    valence: "negative" | "positive" | "ambiguous"
  }>

  // ═══ RISK DIMENSIONS — powers Q3 (⚠️). FIXED KEYS ═══
  risk_flags: {
    misinterpretation: number     // all 0–1
    cultural: number
    religious: number
    tone_mismatch: number
    confusion: number
    meme_potential: number
    polarization: number
  }
  severity: number                // 0–1

  // ═══ BEHAVIOR — powers Q2, Q5 ═══
  likely_behavior: "engage" | "ignore" | "share_positive"
                 | "share_mocking" | "criticize" | "boycott"
  likely_comment: {
    text: string                  // in the persona's own voice
    tone: "positive" | "confused" | "critical" | "humorous"
  }

  // ═══ META ═══
  confidence: number              // 0–1, persona's own certainty
  charitable_reading: string
  hostile_reading: string
  distinct_reaction?: boolean     // Tier 2 only (§7.3)
}
```

### 5.1 Five design decisions that carry the weight

**1. Closed enums for `emotion`, `sentiment`, `likely_behavior`.**
Free-text emotion labels would require an LLM normalization pass before any grouping — turning three free panels (Emotional Response, Audience Heatmap, Target vs Unintended) into extra LLM calls. Enums make them `GROUP BY`.

**2. `sentiment` separated from `comprehension`.**
These are routinely conflated and conflating them destroys the Controversial-vs-Misunderstood panel. *Understood perfectly and objects* is a fundamentally different business problem from *misread it entirely*: one needs a decision, the other needs a rewrite. Two independent fields make the 2×2 fall out for free.

**3. Character offsets on triggers.**
`char_start`/`char_end` make Trigger Detection an exact inverted index rather than fuzzy string matching, and let Backlash Pathway chain a specific span → specific comment → specific meme.

**4. `likely_comment` generated inline, in character.**
Generated during the base call where the persona's framing already exists in context. Generating comments later from aggregate data loses the voice and costs an extra call.

**5. Prevalence lives on the registry, not the reaction.**
`prevalence_weight` and `is_target` are persona-registry attributes. **Likelihood in the Severity × Likelihood matrix must come from how much of the real audience a persona represents — never from asking an LLM how likely something is.** A model's self-estimated likelihood is an opinion; a prevalence weight is a population parameter you control and can defend to a client.

---

## 6. Persona Selection (N→K)

Score against personas most likely to **detect something**, not a demographic cross-section. This is what lets N grow to 40–60 while per-run cost stays flat.

### 6.1 Three-stage hybrid router

**Stage 1 — Cheap recall (no LLM).** Embed the copy; cosine similarity against precomputed embeddings of each node's `persona_notes` + sensitivity axes. Take top 25.

**Stage 2 — Axis activation (Haiku, 1 call).** Extract activated sensitivity axes with intensity:

```json
{ "activated_axes": { "dietary_practice": 0.95, "religious_symbols": 0.60 },
  "entities": ["beef", "cow"],
  "implicit_claims": ["animal consumption treated casually"] }
```

Score each candidate as the dot product of its `sensitivity_profile` against `activated_axes`:

$$r_j = \frac{\mathbf{p}_j \cdot \mathbf{a}}{\|\mathbf{p}_j\| \, \|\mathbf{a}\|}$$

This is the workhorse — it catches beef → `dietary_practice` → Hindu persona with no LLM reasoning about personas at all.

**Stage 3 — Adversarial slots (Sonnet, 1 call).** Stages 1–2 select for *agreement* — a filter bubble, which is how you get a confident, narrow, wrong answer. Reserve **3 of K slots** and fill them adversarially:

> "Which personas from the remaining pool are most likely to react in a way the selected set would MISS?"

This is a structural defense against shared model priors (§22.1). Imperfect — a model cannot reliably enumerate what it does not represent — but strictly better than not asking.

### 6.2 Mandatory nodes

Always in K regardless of relevance:

- `brand_safety_analyst` — models the *amplifier* (journalist, quote-tweeter), not a member of the public. Most crises are caused by amplifiers, not by the offended party.
- `hard_negative_control` — a deliberately unflappable persona that should flag almost nothing. **A live over-triggering canary**: if it starts firing, calibration has drifted. Catches in production what CI only catches at build time.

### 6.3 Diversity constraint

Greedy selection by relevance alone picks twelve near-identical personas and mistakes their agreement for consensus. Apply a diversity penalty:

$$\text{score}_j = r_j - \mu \max_{i \in S} \text{sim}(\mathbf{p}_j, \mathbf{p}_i), \qquad \mu = 0.3$$

where $S$ is the already-selected set. This is MMR (maximal marginal relevance) and it is load-bearing for the CI in §13 — artificially agreeing personas produce artificially narrow intervals.

### 6.4 Selection is logged

Every run persists selected K, per-node relevance, selecting stage, and full candidate pool. Two reasons: **selection bias is silent** (a node never selected has a permanently invisible blind spot), and the log is training data for replacing Stage 3 with something cheaper.

---

## 7. Composition and the Two-Tier Split

### 7.1 The idea

Fuse selected nodes into **composite personas** representing intersectional identities no single node covers: `in_hindu_observant_urban` ⊕ `us_progressive_urban_young` → a diaspora reading neither parent captures.

### 7.2 Why composites cannot enter the score

**This is the central statistical decision in the plan.**

The bootstrap CI (§13) resamples personas, assuming they are **exchangeable draws** — each an independent piece of evidence. A composite A⊕B is not. It is a **deterministic function of A and B**, mechanically correlated with both.

Put A, B, and A⊕B in one pool and resample: the same signal is counted up to three times. Variance shrinks because derived elements agree with their parents by construction. **The tool reports higher confidence while adding zero information.**

That is the one outcome that makes the statistics actively misleading rather than merely imperfect. A marketer trusts a narrow interval, and the narrowness would be an artifact of the architecture.

Compounding it: composites have **no ground truth**. A base node is authored against census data and regional reporting — challengeable, but anchored. A composite is the model's interpolation between two costumes, and intersectional identity is exactly where training data is thinnest. So composites are simultaneously the most *fluent-sounding* and least *grounded* output the system produces.

**Resolution:** composites are a **hypothesis generator**, not a measurement.

- Tier 1 → the score, the CI, and all quantitative panels
- Tier 2 → "Blind Spot Findings", surfaced separately, never in the math

This is stronger, not weaker: the score becomes defensible, and Tier 2 becomes *free to be speculative* precisely because nothing downstream depends on its calibration.

### 7.3 Generation by expected information gain

Do not enumerate — with K=10, pairs alone are 45 and triples 120. Generate the composites most likely to say something neither parent said:

$$\text{EIG}(A,B) = \underbrace{|s_A - s_B|}_{\text{disagreement}} \cdot \underbrace{\big(1 - \text{sim}(A,B)\big)}_{\text{profile distance}} \cdot \underbrace{\pi(A,B)}_{\text{plausibility}}$$

- **Disagreement** — parents at 9 and 1 make a genuinely uncertain intersection. Both at 2: skip.
- **Profile distance** — near-duplicate parents produce a near-duplicate child.
- **Plausibility $\pi$** — *does this person exist in meaningful numbers?* From co-occurrence priors (region, language, migration corridors). Kills `jp_urban_professional ⊕ africa_west_anglophone` (π≈0.02); keeps the Hindu × urban-progressive diaspora (π≈0.4).

Take top 10–15. **Ordering:** composites are unordered sets plus one `dominant` field naming which parent's profile leads — that captures the real asymmetry ("primarily Hindu, secondarily progressive" ≠ the reverse) as one bit of structure rather than a full permutation space.

Composite sensitivity profile uses **max, not mean**:

$$\text{profile}_{A \oplus B}[\text{axis}] = \max\big(A[\text{axis}],\, B[\text{axis}]\big) \cdot \lambda_{\text{axis}}$$

$\lambda = 1.0$ for the dominant parent's top-3 axes, $0.85$ otherwise. **Intersectional identity is a union of sensitivities, not an average** — someone both observant Hindu and progressive is not *half* as sensitive to dietary practice.

**Depth limit: generation 1 only.** Composites are never built from composites — error compounds and grounding vanishes. The only path deeper is promotion (§7.4).

### 7.4 Promotion — how the graph learns

Composites returning `distinct_reaction: false` (they merely echo parents) are **discarded, not displayed**. Expect 40–60% discard; a low rate means EIG selection is too permissive.

Surviving patterns accumulate promotion signal:

| Signal | Weight |
|---|---|
| User clicks **Investigate** | +3 |
| User accepts a rewrite addressing the finding | +5 |
| Pattern recurs with `distinct_reaction: true` across ≥5 runs | +2 each |
| User clicks **Dismiss** | −2 |
| Returns `distinct_reaction: false` | −1 |

At +15, flagged for **human authoring**: a person writes real `persona_notes`, sources `prevalence_weight` from data, sets `vocality` and `failure_modes`. It then enters Tier 1 as a first-class node.

**No automatic promotion.** What makes a node trustworthy is a human supplying a source, which no volume of model output substitutes for. This makes human authoring the rate limiter on graph depth — the correct constraint, since grounding is exactly what Tier 2 lacks.

### 7.5 The one exception — Severe Discovery Alert

A composite **cannot move the score**. It **can** raise an alert.

If a composite returns `severity ≥ 0.9`, `confidence ≥ 0.8`, and `distinct_reaction: true`, the UI shows a blocking **Severe Discovery Alert** — prominent, requiring acknowledgement — without altering the numeric score or band.

A composite finding a severe issue no base node caught is exactly what this architecture exists to surface. Suppressing it wastes the tier. Letting it move the number reintroduces ungrounded input into measurement.

**It interrupts. It does not compute.**

---

# PART III — MATHEMATICS

## 8. Notation and Inputs

For persona $i \in \{1 \dots K\}$ (Tier 1 only unless stated):

| Symbol | Source | Range |
|---|---|---|
| $s_i$ | `severity` | [0,1] |
| $c_i$ | `confidence` | [0,1] |
| $w_i$ | registry `prevalence_weight` | [0,1] |
| $v_i$ | registry `vocality` | [0,1] |
| $a_i$ | `interpretation.intent_alignment` | [0,1] |
| $p_i$ | $\mathbb{1}[\texttt{likely\_behavior} \in \{\text{criticize, share\_mocking, boycott}\}]$ | {0,1} |
| $b_i$ | $\mathbb{1}[\texttt{likely\_behavior} = \text{boycott}]$ | {0,1} |
| $\mathbf{f}_i$ | `risk_flags` vector | [0,1]⁷ |
| $g_i$ | charitable/hostile reading gap | [0,1] |
| $\mathbf{e}_i$ | embedding of `interpretation.paraphrase` | ℝᵈ |
| $\mathbf{q}_i$ | embedding of `perceived_intent` | ℝᵈ |
| $\mathbf{q}^*$ | embedding of brand's stated intent | ℝᵈ |

---

## 9. Core Risk Model

### 9.1 What the score represents

> **Brand Risk Index = the expected reputational cost of publishing this copy, as a 0–100 ordinal index.**

Explicitly **not** "probability of a PR crisis" — we have no outcome data to calibrate a probability against, and claiming one would be dishonest. It is comparable across pieces of copy; it is not interpretable as a frequency. Shipping a number that *looks* like a probability but isn't is the fastest way to lose trust the first time a "12% risk" post blows up. The UI enforces this (§17.3).

### 9.2 Component terms

**Offense mass** — audience- and confidence-weighted mean:

$$M = \frac{\sum_i w_i c_i s_i}{\sum_i w_i c_i}$$

**Amplification** — will it travel?

$$A = \sum_i w_i \, v_i \, p_i \, s_i$$

This separates "some customers quietly dislike this" from "this becomes a story". A small vocal segment at $s=0.9$ amplifies more than a large quiet segment at $s=0.5$ — which matches how crises actually work.

**Tail risk** — the worst credible reaction, not the average:

$$T = \max_i \left( s_i \, c_i \right)$$

**Averages hide catastrophes.** Eleven personas at 0.1 and one at 1.0 gives $M = 0.175$ and a campaign on fire. $T$ is why this model is not just a weighted mean, and it carries the largest weight.

**Ambiguity penalty:**

$$G = \frac{1}{K}\sum_i g_i$$

Copy that can be read two ways will be read the worse way by someone.

**Context multiplier** $\kappa \in [0.8, 1.5]$ (§18.4) — identical copy is fine in a quiet month and inflammatory during an active news cycle.

### 9.3 Composite

$$\text{Raw} = \kappa \left( \alpha M + \beta \hat{A} + \gamma T + \delta G \right)$$

with $\hat{A}$ the normalized amplification, and **initial weights — priors to be calibrated, not truths**:

$$\alpha = 0.30, \quad \beta = 0.25, \quad \gamma = 0.35, \quad \delta = 0.10$$

$\gamma$ is largest by design: **for reputational risk the tail matters more than the average.**

$$\boxed{\text{Risk Index} = \min\left(100,\ 100 \cdot \text{Raw}\right)}$$

### 9.4 Bands and override

| Index | Band | Action |
|---|---|---|
| 0–20 | **Clear** | Ship |
| 21–40 | **Low** | Ship; note the flag |
| 41–60 | **Elevated** | Review rewrites |
| 61–80 | **High** | Rewrite before publishing |
| 81–100 | **Severe** | Do not publish as written |

**Override:** any persona with $s_i \geq 0.9 \wedge c_i \geq 0.7$ forces a floor of **High**, regardless of composite. One credible severe reaction is not averaged away — a deliberate asymmetry, because the cost of a false negative here vastly exceeds a false positive.

### 9.5 Worked example — the beef case

*"Our new protein bar — finally, a beef bar that doesn't taste like a cow."*

| Persona | $s_i$ | $c_i$ | $w_i$ | $v_i$ | $p_i$ |
|---|---|---|---|---|---|
| `in_hindu_observant_urban` | 0.90 | 0.90 | 0.14 | 0.72 | 1 |
| `mena_muslim_practicing` | 0.40 | 0.70 | 0.09 | 0.60 | 0 |
| `us_progressive_urban_young` | 0.30 | 0.55 | 0.18 | 0.85 | 0 |
| `eu_secular_nordic` | 0.50 | 0.65 | 0.07 | 0.50 | 0 |
| `brand_safety_analyst` | 0.80 | 0.85 | 0.05 | 1.00 | 1 |
| *(7 others)* | ≤0.20 | — | — | — | 0 |

$M \approx 0.34$ · $\hat A \approx 0.44$ · $T = 0.81$ · $G \approx 0.30$ · $\kappa = 1.0$

$$\text{Raw} = 0.30(0.34) + 0.25(0.44) + 0.35(0.81) + 0.10(0.30) = 0.524$$

**Risk Index ≈ 52 (Elevated)**, CI₈₀ ≈ [38, 71] → **override fires** (persona 1: $s=0.90$, $c=0.90$) → **band forced to High**.

Note what happened: the weighted mean alone said 0.34 — "fine". **The tail term plus the override caught it.** The wide CI correctly signals the copy *splits* the audience rather than uniformly annoying it. This is golden test case #1 (§19.1).

---

## 10. Interpretation Mathematics

The maths behind the 🧠 questions — and the part that makes this more than a safety scanner.

### 10.1 Intent Alignment Score

$$\text{IAS} = \frac{\sum_i w_i c_i a_i}{\sum_i w_i c_i} \times 100$$

Reported with the same bootstrap CI as the risk index. A campaign can be perfectly safe and still fail here — **IAS is the panel that catches "nobody was offended, nobody understood it either."**

### 10.2 Interpretation gap

Per persona, cosine distance between their perceived intent and the brand's stated intent:

$$g^{\text{int}}_i = 1 - \frac{\mathbf{q}_i \cdot \mathbf{q}^*}{\|\mathbf{q}_i\| \|\mathbf{q}^*\|}$$

Drives "Who Might Misunderstand?" — sort descending by $g^{\text{int}}_i$.

### 10.3 Interpretation dispersion — the divergence signal

How much do personas disagree *about what the copy means* (independent of whether they like it)?

$$D = \frac{1}{K}\sum_i \left\| \mathbf{e}_i - \bar{\mathbf{e}} \right\|_2, \qquad \bar{\mathbf{e}} = \frac{1}{K}\sum_i \mathbf{e}_i$$

**High $D$ with low risk is a distinct and under-appreciated failure mode:** nobody is offended, but everyone read something different. The message is not landing. No safety tool detects this. It is a genuine differentiator for the product.

### 10.4 Controversial vs Misunderstood placement

The 2×2 that tells a marketer *which problem they have*:

- **x-axis (comprehension):** $x_i = a_i$ — did they get it?
- **y-axis (opposition):** $y_i = \mathbb{1}[\texttt{sentiment} = \text{opposed}] \cdot s_i$

| Quadrant | Condition | Diagnosis | Fix |
|---|---|---|---|
| **Controversial** | high $x$, high $y$ | Understood and rejected | *Decide* whether you accept the cost |
| **Misunderstood** | low $x$, high $y$ | Misread and reacted | *Clarify* — this is fixable |
| **Aligned** | high $x$, low $y$ | Landed as intended | Ship |
| **Invisible** | low $x$, low $y$ | Didn't land at all | *Rewrite for clarity*, not safety |

These four quadrants require four *different* responses. A single risk number cannot distinguish them, which is the core argument for interpretation-first design.

---

## 11. Clustering and Grouping

### 11.1 "What They Think You're Saying"

Embed each persona's `paraphrase` → $\mathbf{e}_i$. Cluster with **agglomerative clustering, average linkage, cosine distance, threshold $\tau = 0.35$**.

**Use a distance threshold, not k-means with fixed $k$** — cluster count must be data-driven. Fixing $k=3$ manufactures three interpretations whether or not three exist, which is exactly the fabrication risk this panel must avoid.

Each cluster reports:
- **Label** — the medoid paraphrase (a real persona's actual words, never a synthesized summary)
- **Mass** — $\sum_{i \in C} w_i$, the audience share holding this reading
- **Divergence** — cosine distance from cluster centroid to brand intent $\mathbf{q}^*$

Sort by mass. **The largest cluster that is not the intended reading is the single most important output in the product** — it is literally "what most of your audience thinks you said."

### 11.2 Emotion aggregation

Direct `GROUP BY` on the closed enum — free:

$$P(\text{emotion} = e) = \frac{\sum_{i : \text{emotion}_i = e} w_i}{\sum_i w_i}$$

Weighted by prevalence, not raw counts, so the distribution reflects the audience rather than the persona roster.

### 11.3 Emotional polarization

$$\Pi = \frac{\sum_{e \in E^+} w_i \cdot \iota_i \;\cdot\; \sum_{e \in E^-} w_i \cdot \iota_i}{\left(\sum_i w_i \iota_i / 2\right)^2}$$

with $E^+ = \{\text{positive, amused, curious}\}$, $E^- = \{\text{offended, uncomfortable}\}$, and $\iota_i$ = `emotion_intensity`.

Maximized when the audience splits evenly into strong love and strong hate. **This is the "Bud Light number"** — polarizing campaigns often score moderately on mean risk while being existentially dangerous, because the danger is the split, not the average.

---

## 12. Matrix Placement Mathematics

### 12.1 Severity × Likelihood

For each of the 7 risk dimensions $d$:

$$\text{Likelihood}_d = \sum_{i : f_{i,d} > \theta} w_i \qquad (\theta = 0.3)$$

$$\text{Severity}_d = \frac{\sum_i w_i c_i f_{i,d} \cdot s_i}{\sum_i w_i c_i f_{i,d}}$$

**Likelihood comes from prevalence weights, never from an LLM's self-estimate.** A model asked "how likely is this?" returns an opinion. A prevalence weight is a population parameter you control and can defend to a client. This distinction is what makes the matrix defensible in a room.

Quadrants: **Monitor** (low/low) · **Contain** (high likelihood, low severity) · **Prepare** (low likelihood, high severity) · **Fix Now** (high/high).

### 12.2 Risk Anatomy

Per dimension, the audience-weighted mass:

$$R_d = \frac{\sum_i w_i c_i f_{i,d}}{\sum_i w_i c_i}$$

Rendered as a radar or horizontal bars. The *shape* is diagnostic: a spike on `confusion` with flat `cultural` means a clarity problem, not a sensitivity problem — and sends the marketer to a completely different rewrite strategy.

---

## 13. Uncertainty Quantification

### 13.1 Bootstrap CI

Resample the $K$ Tier-1 personas with replacement, $B = 1000$ times; recompute the full composite each time:

$$\text{CI}_{80} = \left[ Q_{0.10}(\text{Index}^*),\ Q_{0.90}(\text{Index}^*) \right]$$

**Use bootstrap, not a normal approximation.** With 12–30 personas and a skewed severity distribution, normal-approximation intervals produce bounds outside [0,100]. Bootstrap is assumption-free and trivial.

### 13.2 Jackknife selection uncertainty

We score $K$ of $N$ personas, so there is uncertainty from *which* were selected, not just how they scored. Recompute the index $K$ times, dropping one persona each time:

$$\sigma^2_{\text{jack}} = \frac{K-1}{K} \sum_{i} \left( \text{Index}_{(-i)} - \overline{\text{Index}_{(\cdot)}} \right)^2$$

Combine:

$$\text{CI}_{\text{final}} = \text{Index} \pm \sqrt{\sigma^2_{\text{boot}} + \sigma^2_{\text{jack}}} \cdot z_{0.90}$$

This is a genuine honesty improvement over a flat design, whose CI silently assumes the persona set is the whole population. It is not, and now the interval says so.

### 13.3 Why the interval is the most important number

A 62 with [58, 66] is a finding. A 62 with [21, 89] means **the personas fundamentally disagree** — the copy will split the audience, and the marketer must decide which half they are willing to lose.

**Wide CI is surfaced as prominently as a high score**, with explicit language: *"Your audience is split on this."* Always display persona count alongside — a CI over 8 personas should visibly look weaker than one over 20.

---

## 14. Comparison Mathematics

### 14.1 Reaction vector

Represent a campaign's simulated response as a single vector for comparison:

$$\mathbf{V}(c) = \big[\, \bar{s},\ \bar{a},\ R_1 \dots R_7,\ P(e_1) \dots P(e_7),\ \Pi,\ D \,\big] \in \mathbb{R}^{18}$$

Z-normalized per component across the corpus.

### 14.2 Historical similarity

$$\text{sim}(c_1, c_2) = \omega \cdot \cos\big(\mathbf{t}_1, \mathbf{t}_2\big) + (1-\omega) \cdot \cos\big(\mathbf{V}_1, \mathbf{V}_2\big), \qquad \omega = 0.4$$

where $\mathbf{t}$ is the creative-text embedding. Two-part deliberately: campaigns can be **thematically similar but reaction-different** (the interesting case — "this looks like Pepsi/Jenner but personas react differently, here's why"), or **thematically different but reaction-similar** (a shared structural risk, often more valuable).

### 14.3 Campaign × Persona comparison — the cost trap

The naive implementation re-runs $K$ personas against $M$ historical campaigns: $O(K \times M)$ LLM calls per comparison. Quadratic, and it dominates the entire cost model.

**Do not re-simulate.** Store every historical campaign's reaction objects once, at ingest. Comparison then reads stored vectors:

$$\Delta_{i} = s_i^{(\text{current})} - s_i^{(\text{historical})}$$

$O(1)$ LLM calls. The only constraint is that persona versions must match; where they don't, re-simulate **only that persona** on the historical creative and cache it. This turns the most expensive panel on the list into one of the cheapest.

---

# PART IV — DASHBOARD

## 15. Dependency Structure of the 24 Analyses

**The 24 analyses are not 24 features.** Most are views over one shared computation. Planning them as 24 pipelines would produce 24 subsystems whose numbers disagree across panels — the classic dashboard failure.

Categories: **A** = pure projection over the Reaction Object (zero extra LLM calls) · **B** = needs additional LLM call · **C** = needs new data infrastructure · **D** = needs aggregation math

| # | Panel | Cat | Extra cost |
|---|---|---|---|
| 1 | Intent vs Interpretation | A + D | embeddings |
| 2 | Persona Reactions | **A** | free |
| 3 | Why Is It Risky? | **A** | free |
| 4 | What They Think You're Saying | A + D | clustering |
| 5 | Emotional Response | **A** | free |
| 6 | Who Might Misunderstand? | A + D | embeddings |
| 7 | Risk Anatomy | **A** | free |
| 8 | Severity × Likelihood | A + D | arithmetic |
| 9 | Trigger Detection | **A** | free |
| 10 | Intent Alignment Score | A + D | arithmetic |
| 11 | Audience Heatmap | **A** | free |
| 12 | Region Heatmap | A + C | registry coverage |
| 13 | Campaign Comparison | C | corpus |
| 14 | Campaign × Persona | C + D | corpus (§14.3) |
| 15 | Historical Similarity | C + D | corpus + kNN |
| 16 | Target vs Unintended | **A** | free |
| 17 | Controversial vs Misunderstood | **A** | free |
| 18 | Simulated Comments | **A** | free |
| 19 | Meme / Virality Potential | A + B | 1 synthesis call |
| 20 | Backlash Pathway | B | 1 synthesis call |
| 21 | Rewrite Suggestions | B | generation |
| 22 | Before vs After | B | full re-run |
| 23 | Risk Index + CI | D | bootstrap |
| 24 | Persona Selection | D + B | router |

**Tally: A = 14 · B = 5 · C = 4 · D = 9.**

> **The fulcrum:** trigger spans must be emitted by the persona *at reaction time*, not recovered afterward. With them, panels 3, 9, 19, 20 collapse into projections. Without them, each becomes a separate LLM pass that has *lost the causal link* between who reacted and why. This single schema decision determines whether the dashboard is cheap or expensive.

---

## 16. Panel Specifications

### 16.1 Intent vs. Interpretation 🧠
**Input:** `interpretation.perceived_intent` per persona · brand's stated intent
**Math:** §10.2 gap $g^{\text{int}}_i$
**Render:** Two-column. Left: stated intent (pinned). Right: each persona's perceived intent, sorted by gap descending, gap rendered as a bar.
**Insight:** the top row is the biggest misreading in your audience.

### 16.2 Persona Reactions ❤️
**Input:** full Reaction Object · **Math:** none · **Render:** cards — label, emotion chip, severity, reaction in first person, triggers, behavior, charitable vs hostile reading side by side. Sortable, filterable by axis.
**Why it matters:** first-person voice is what changes behavior. *"I'd unfollow a brand that talks about my religion this way"* lands; "religious sensitivity: 8.2" does not.

### 16.3 Why Is It Risky? ⚠️
**Input:** `triggers[]` + `risk_flags` · **Math:** group by `modality`
**Render:** grouped list — word / phrase / visual / reference / tone / context — each with the `why` and affected personas.

### 16.4 What They Think You're Saying 🧠
**Input:** `paraphrase` embeddings · **Math:** §11.1 agglomerative clustering
**Render:** clusters as cards sized by audience mass; medoid paraphrase as label; intended reading highlighted; divergence bar.
**This is arguably the product's most valuable panel.** The largest cluster that is not the intended reading is literally what most of your audience thinks you said.

### 16.5 Emotional Response ❤️
**Input:** `emotion` + `emotion_intensity` · **Math:** §11.2, §11.3
**Render:** stacked bar (overall, prevalence-weighted) + per-persona chips. Polarization index $\Pi$ shown separately with explicit callout above threshold.

### 16.6 Who Might Misunderstand? 🎯
**Input:** gap $g^{\text{int}}_i$ · **Math:** sort descending
**Render:** ranked personas with gap magnitude and the specific triggers driving their divergent reading.

### 16.7 Risk Anatomy ⚠️
**Input:** `risk_flags` · **Math:** §12.2 · **Render:** radar chart, 7 axes. Shape is diagnostic — the spike tells you *which kind* of problem you have.

### 16.8 Severity × Likelihood ⚠️
**Math:** §12.1 · **Render:** 2×2 scatter, one point per risk dimension, bubble size = affected audience mass. Quadrant labels: Monitor / Contain / Prepare / Fix Now.

### 16.9 Trigger Detection 🔍
**Input:** `triggers[].char_start/char_end` · **Math:** inverted index span → personas
**Render:** the copy itself, inline-highlighted by severity. Hover a span → the personas it triggered and why. **This is the composer's primary surface** — the marketer edits directly here.

### 16.10 Intent Alignment Score 🧠
**Math:** §10.1 + bootstrap CI · **Render:** large percentage, CI band, per-persona breakdown beneath. Displayed *beside* the Risk Index, never subordinate to it — a campaign can be safe and still fail here.

### 16.11 Audience Heatmap 🎯
**Input:** reactions × registry demographics · **Math:** pivot
**Render:** matrix, persona rows × emotion columns, cells colored by intensity. Facetable by age band / region / language / audience type.

### 16.12 Region Heatmap 🎯
**Input:** reactions grouped by `demographics.region` · **Render:** choropleth (India state-level where sub-region coverage exists, global otherwise). Click a region → the personas there and the reason for divergence.
**Requires:** registry with genuine regional coverage — this is a persona-authoring dependency, not an engineering one.

### 16.13 Campaign Comparison 📊
**Requires:** historical corpus · **Math:** §14.2 · **Render:** side-by-side reaction vectors, shared triggers highlighted, delta table.

### 16.14 Campaign × Persona Comparison 📊
**Math:** §14.3 — **stored vectors, never re-simulation**
**Render:** matrix, personas × campaigns, cells = severity, current campaign as a highlighted column.

### 16.15 Historical Campaign Similarity 📊
**Math:** §14.2 kNN over pgvector · **Render:** ranked similar campaigns with outcome labels ("what happened"), shared risk dimensions, and the trigger that caused the historical backlash.

### 16.16 Target vs Unintended Audience 🎯
**Input:** `is_target` flag · **Math:** group-by
**Render:** two panels side by side, same metrics.
**Insight:** the gap between them is the overlap risk — copy that works on your target and fails on everyone else is still a crisis, because everyone else is who screenshots it.

### 16.17 Controversial vs Misunderstood ⚠️
**Math:** §10.4 · **Render:** 2×2, personas as points, quadrants labelled with their *prescription* not just their name.
**This panel answers "what kind of problem do I have?"** — and each quadrant demands a different action.

### 16.18 Simulated Comment Section ❤️
**Input:** `likely_comment` · **Math:** group by tone
**Render:** a mock social feed, comments in persona voice, tone-colored. Prevalence-weighted ordering so the feed *reads* like the real distribution.
**Why it lands:** this is the panel that makes risk viscerally legible to a non-technical stakeholder. A CMO who reads twelve simulated comments understands the problem instantly.

### 16.19 Meme / Virality Potential 🔍
**Input:** `risk_flags.meme_potential` + `share_mocking` behavior + triggers · **Plus:** one Sonnet synthesis call for the actual meme formats
**Render:** ranked screenshot-able elements, each with the specific trigger and the format it would take (quote-tweet / caption / out-of-context crop).

### 16.20 Backlash Pathway 🔍
**Input:** triggers + comments + share behavior · **Plus:** one Opus synthesis call
**Render:** a directed chain — Creative → Misinterpretation → Comment → Meme/Share → Wider discussion — with per-stage transition likelihood from persona behavior distributions.
**⚠️ Highest credibility risk in the product.** A plausible causal chain is the panel most likely to be *wrong while looking authoritative*. **Every node must cite a real trigger span and a real persona comment** — the model narrates the links, never invents the nodes. If a stage has no grounding, the chain terminates there and says so.

### 16.21 Rewrite Suggestions ✏️
Three variants at different points on the risk/impact trade-off:

| Variant | Strategy | Target |
|---|---|---|
| **Clarify** | Fix interpretation gaps; keep the edge | IAS ↑, risk ~flat |
| **Safer** | Reduce risk; accept voice drift | Risk ↓↓, IAS ↑ |
| **Preserve Edge** | Minimal change; keep what makes it work | Risk ↓, voice intact |

The rewriter sees **why** each persona objected, not just that they did. "Avoid the word beef" produces a worse rewrite than "this persona's objection is that the copy treats a religious boundary as a casual food preference" — the second lets the model find solutions the first forecloses.

**A rewrite that kills the copy's impact has not solved the problem; it has moved it.** The tool makes the trade-off legible and lets the marketer choose.

### 16.22 Before vs After 🔄
**Math:** re-run on reduced persona set — the personas that flagged the original, plus 3 random controls (to catch a rewrite that fixes one problem and creates another: sanitizing a dietary reference by introducing a gendered metaphor is a real failure mode).

**Pin persona temperature and seeds** so the comparison measures the *copy change*, not sampling noise. Without this the panel shows differences that aren't real.

**Render:** paired before/after for Risk Index, IAS, emotion distribution, risk anatomy, and unresolved triggers.

**If a variant does not improve, say so.** A rewriter that always reports success is one nobody believes after the third use.

---

## 17. Information Architecture

### 17.1 Three screens

1. **Composer** — editor with inline trigger highlighting (16.9), live Risk Index + IAS, top-3 persona reactions. Where the work happens.
2. **Analysis** — the full 24-panel dashboard, organized by the eight questions (§3), progressive disclosure.
3. **Compare** — before/after and historical comparison.

### 17.2 Progressive disclosure

Nobody reads 24 panels. Default view is the eight question-cards, each showing its single headline number and expanding to its panels on click. Power users pin favorites.

### 17.3 Honesty requirements — acceptance criteria, not polish

- Score displays as **"Risk Index"**, never "% chance of backlash"
- **CI always shown**, never collapsed to a point estimate
- Wide CI triggers explicit callout: *"Your audience is split on this"*
- Persona count always visible alongside any aggregate
- **Tier-2 findings visually separated**, labelled `not scored`, dismissible in one click
- Context provenance badge (`MOCK DATA` in MVP) unmissable
- Persistent disclaimer: *simulated reactions, not survey data*

**Test §17.3 with real users early.** If a user cannot articulate the Tier-1/Tier-2 difference unprompted, the UI has failed — users skim, and a fluent quote inside a warning box is still a fluent quote.

---

# PART V — DELIVERY

## 18. Technical Architecture

### 18.1 Stack

**Python + FastAPI · Next.js · Postgres + pgvector · Redis**

- **Python** — the scrapers, NLP, calibration, and classifier layers all live here. A TypeScript backend means reimplementing within two months.
- **FastAPI** — async-native, and the hot path is `asyncio.gather` over 12–30 concurrent LLM calls. Pydantic gives schema-validated LLM output for free.
- **Next.js** — the UI is an editor with an annotation layer plus a panel grid. Keep it thin; this is not where the value is.
- **Postgres + pgvector** — personas, runs, reactions, campaigns are relational; embeddings for §11 clustering and §14 similarity live in the same database. One store, not two.
- **Redis** — `arq` job queue (async-native) + LLM response cache keyed on `(persona_version, text_hash, context_hash)`. The cache is cost control, not optimization: identical pairs are extremely common during iterative rewriting.

### 18.2 Models

| Role | Model | Why |
|---|---|---|
| Persona reactions | `claude-sonnet-5` | 12–30 calls/run — cost-per-call dominates, quality sufficient |
| Aggregation, rewrite, pathway | `claude-opus-5` | Once per run, needs the reasoning |
| Triage, axis activation | `claude-haiku-4-5-20251001` | Cheap pre-filter |

> Verify pricing against current Anthropic documentation before committing to §21.

### 18.3 Reliability

- **Schema-constrained JSON** with per-persona Pydantic validation
- **Partial-response salvage** — one truncated response must not void a whole run
- **Graceful degradation** — a run returning 10/12 personas is valid; record which failed and widen the CI accordingly
- **Bounded concurrency** + per-call timeout

### 18.4 Context layer

Ships with **fixture data behind a real interface** — `ContextProvider` protocol with `MockContextProvider` reading 8–10 hand-built scenarios (`quiet`, `dietary_controversy_india`, `ramadan_active`, `election_season_us`, …). Scenario is **user-selectable**, which doubles as a demo feature ("your copy in a quiet month vs. an active news cycle") and as the manual test harness for $\kappa$.

`provenance` field is mandatory and surfaced — a marketer must never be unable to tell whether the context driving a score was real or fixture.

**Phase 4 live providers:** GDELT (free, 15-min updates — build first), RSS (free, ~50 outlets), NewsAPI (~$450/mo), X API Basic+ ($200+/mo).

**On scraping:** I would not build headless-browser scrapers of X or news sites. ToS violation, constant breakage under anti-bot measures, and legal exposure disproportionate to the marginal data. GDELT + RSS is free and covers most of the signal. Recorded as a considered-and-rejected option, not an oversight.

### 18.5 Repository layout

```
backlashtest/
├── backend/app/
│   ├── personas/      # schema, registry, compile, definitions/*.yaml
│   ├── router/        # recall, axis activation, adversarial, MMR
│   ├── orchestrator/  # fan-out, concurrency, degradation
│   ├── scoring/       # core model, bootstrap, jackknife, bands
│   ├── analysis/      # clustering, matrices, heatmaps, comparison
│   ├── composition/   # EIG, profile derivation, promotion
│   ├── rewrite/       # variants, constraints, re-loop
│   ├── context/       # protocol, mock, (gdelt, rss)
│   ├── corpus/        # historical campaigns (Phase 5)
│   └── llm/           # client, cache, retry, salvage
├── frontend/
├── fixtures/
└── tests/{golden,calibration,unit}/
```

---

## 19. Validation

Without this the product is a random number generator with good typography. It is the section most likely to be cut under time pressure and the one that must not be.

### 19.1 Golden set — 60 hand-labelled examples

- **20 known incidents** — documented backlash (Pepsi/Jenner, Dove, H&M, Gucci, Bud Light). Expected: High/Severe.
- **20 known-clean** — same brands/period, no incident. Expected: Clear/Low.
- **20 hard negatives** — *looks* risky, isn't: reclaimed language used correctly, region-appropriate terms, dead metaphors ("killer deal", "crazy good"). Expected: Clear/Low.

**The hard negatives are the most important twenty.** Over-triggering is the failure mode that kills this product — a tool that flags "killer deal" gets closed and never reopened.

**Primary metric is false-positive rate on hard negatives, not accuracy on incidents.**

Targets: ≥70% band-accuracy on incidents · ≤15% FP on hard negatives · ≥90% router recall on incidents.

### 19.2 Persona calibration
Per persona, fixtures asserting it fires on its own axis and stays quiet elsewhere. Cross-firing means the persona has collapsed into generic-cautious-LLM. Runs in CI; a persona edit that breaks calibration fails the build.

### 19.3 Stability
Same input × 5 runs at `temperature=0.3`. Persona severity varies ≤0.15; Risk Index ≤5 points. Exceeding this means personas aren't stable enough to trust.

### 19.4 CI integrity test — the guardrail
Run the golden set with composites **excluded** from scoring (correct) and **included** (incorrect). **Assert the included-variant CI is measurably narrower.** This makes §7.2's bug visible as a number and fails the build if anyone later "simplifies" the tiers together.

### 19.5 Selection bias audit
Weekly: selection frequency per node. Any node selected <2% of runs is badly written, redundant, or mis-embedded. Investigate rather than let it rot invisibly.

### 19.6 Composite discard rate
Track `distinct_reaction: false`. Healthy band 40–60%. Below 30% means composites are rubber-stamping parents.

### 19.7 Human agreement — the one that tests the core bet
Recruit 3–5 people matching a persona profile; have them score 10 pieces of copy; correlate with the simulated persona.

**This is the only real test of §1.2.** Even a small sample is worth more than any amount of internal reasoning. If correlation is poor, we need to know before building further on the assumption.

---

## 20. Build Phases

| Phase | Work | Days |
|---|---|---|
| **0** | Repo, FastAPI, Postgres+pgvector, Anthropic client w/ retry + salvage, CI | 2–3 |
| **1a** | Persona schema + **40 base nodes** | 6–7 |
| **1b** | Router: recall, axis activation, adversarial slots, MMR, logging | 3–4 |
| **2** | Reaction Object, fan-out, validation, degradation | 3–4 |
| **3a** | Core risk model, bootstrap, jackknife, bands, override | 3–4 |
| **3b** | Analysis math: clustering, matrices, heatmaps, IAS, polarization | 4–5 |
| **4** | Context layer (mocked), κ, triage | 2 |
| **5a** | **The 14 projection panels** — this is a demonstrable product | 6–7 |
| **5b** | Composer with inline trigger highlighting + SSE streaming | 4–5 |
| **6** | Composition, Tier-2 findings, Severe Discovery Alert, §19.4 test | 3–4 |
| **7** | Rewrite engine + Before/After | 4–5 |
| **8** | Synthesis panels: Meme Potential, Backlash Pathway | 2–3 |
| **9** | Golden set, stability, calibration, cost instrumentation | 4–5 |
| **10** | *(v2)* Historical corpus, comparison panels | 8–10 |

**MVP (Phases 0–9): ~47–56 working days ≈ 10–12 weeks solo.**
**With corpus (Phase 10): ~13–14 weeks.**

### 20.1 Build order rationale

**Ship the Reaction Object plus the 14 projection panels first.** That is a complete, demonstrable product from a single LLM call per persona — and it proves the schema before anything expensive is built on it.

Then aggregation math (no new calls). Then the rewrite engine, because it converts diagnosis into action and is what clients actually pay for. Defer all corpus-dependent panels (13, 14, 15) behind a v2 gate — they are a *data acquisition and licensing* problem, not an engineering one, and should not block the core product.

Phase 1a is the largest single block and the least glamorous. It also most determines output quality: **40 well-sourced nodes beat 100 hastily written ones, and no amount of graph architecture rescues a badly authored persona set.**

---

## 21. Cost Model

Per full run, K=11, M=12 composites:

| Stage | Model | Calls | Cost |
|---|---|---|---|
| Triage + axis activation | Haiku | 1 | ~$0.001 |
| Embedding recall | — | 0 | ~$0.000 |
| Adversarial slots | Sonnet | 1 | ~$0.003 |
| Tier-1 reactions | Sonnet | 11 | ~$0.033 |
| Tier-2 composites | Sonnet | 12 | ~$0.036 |
| Aggregation synthesis | Opus | 1 | ~$0.020 |
| Backlash pathway | Opus | 1 | ~$0.015 |
| **Total** | | **27** | **~$0.108** |

**All 24 panels come from these 27 calls** — because 14 are projections and the comparison panels read stored vectors (§14.3).

Rewrite cycle: +3 generation + ~18 re-score ≈ **$0.07**.

**Cost controls:** Redis cache on `(persona_version, text_hash, context_hash)` (hits often during iterative editing) · debounced scoring at 800ms idle, never per-keystroke · reduced persona set for re-scoring · **stored reaction vectors instead of re-simulation for comparison.**

Latency: Tier 1 and Tier 2 fan out in parallel; wall-clock ≈ slowest call ≈ 6–8s. Results **stream via SSE** as personas return — this matters more for perceived quality than almost anything else in the UI.

---

## 22. Risks

### 22.1 Shared model priors ⚠️ **Most serious**

Every persona is the same base model in a different costume. Their "independent" judgments share its cultural priors — skewed Western, English-language, internet-liberal. A blind spot appears in **all personas simultaneously**, and the bootstrap will report *high confidence* precisely because they agree.

**The statistics look best exactly where the model is most uniformly wrong.**

Mitigations: explicit `failure_modes` per persona · adversarial slot-filling (§6.1) · MMR diversity (§6.3) · hard negatives (§19.1) · §19.7 human validation · stating the limitation plainly in the UI.

This is **structural**, not a bug to engineer around. The two-tier split prevents it from producing *false confidence in the score*; it does not make the simulation truer. Only §19.7 tests that, and it remains the highest-value open item in the plan.

### 22.2 Over-triggering
The product-killing failure mode. Calibration blocks in every persona prompt, hard negatives as the primary metric, `hard_negative_control` as a live canary.

### 22.3 Backlash Pathway fabrication
Highest credibility risk among panels — a plausible causal chain that is wrong while looking authoritative. Mitigation: every node cites a real trigger span and a real persona comment; the model narrates links, never invents nodes; chains terminate where grounding runs out.

### 22.4 Composites read as authoritative despite labelling
Users skim. Mitigation: visual separation, `not scored` always visible, one-click dismiss, and early user testing on §17.3.

### 22.5 Router misses a persona that would have caught the issue
**Silent failure** — a miss produces no signal. Bounded, never eliminated, by §19.1 recall targets, mandatory nodes, adversarial slots, §19.5 audit.

### 22.6 Precision illusion
A 0–100 number implies precision we lack. Mitigated by always showing CI, leading with bands, and §17.3 language rules.

### 22.7 Metric gaming
A marketer running 20 rewrites to get 61→59 has optimized the metric, not the risk. Mitigation: lead with band, de-emphasize the exact number, consider rate-limiting rewrite cycles.

### 22.8 Historical corpus is a legal problem, not a technical one
Campaign creative, outcome labels, and backlash documentation all need licensing, and outcome labels need to be defensible. The embedding kNN is easy; the acquisition is not. This is why Phase 10 sits behind a v2 gate.

---

## 23. Open Questions

1. **Prevalence weights $w_i$** — global, or per-campaign from target market? Per-campaign is more correct and more work; global is the MVP default, but the data model should permit per-campaign from day one.
2. **Brand intent capture** — how does the marketer state intended meaning? IAS and every interpretation metric depend on it. A required one-line field is the minimum; structured brief is better.
3. **Brand voice input** — freeform, structured guide, or past-copy examples? Examples are strongest for the rewriter, heaviest for UI.
4. **Buyer** — in-house marketing, agency, or brand-safety/compliance? Determines whether the audit trail is a nice-to-have or the main sell.
5. **§19.7 human validation timing** — during MVP or after? My inclination is to attempt even a tiny version during, because it tests the load-bearing assumption.
6. **Corpus sourcing** — licensed dataset, manual curation of public incidents, or customer's own campaign history? The third is the most defensible and the easiest to license: it is their data.

---

## 24. The One-Paragraph Version

*Simulate a diverse population of readers with LLM personas selected for relevance from a large authored registry. Have each return one rich structured object capturing what they understood, how they felt, what exactly triggered them, and how they would behave. Aggregate with statistics that weight the worst reaction above the average, that separate misunderstanding from disagreement, and that report an honest interval reflecting both sampling and selection uncertainty. Project that single computation into twenty-four views answering eight questions. Generate intersectional composite personas to find blind spots no authored persona covers — but never let them touch the score, because they are correlated with their parents by construction and would narrow the confidence interval through redundancy rather than evidence. Prove every rewrite by re-simulating it.*

---

*Consolidated 2026-09-19. Scoring weights (§9.3) are priors to be calibrated against the golden set (§19.1), not validated constants. §19.4 is the regression test protecting the two-tier decision — if the tiers are ever merged, that test should be what stops it. Model pricing requires verification against current Anthropic documentation.*
