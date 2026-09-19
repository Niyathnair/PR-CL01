"""Uncertainty quantification (§13).

Two independent sources of uncertainty, combined:

1. **Sampling** — how the K selected personas happened to score. Bootstrap.
2. **Selection** — which K of N personas were selected at all. Jackknife.

A flat design reports only the first, which silently assumes the persona set is
the whole population. It is not, and the interval should say so.

The interval is the most important number the product emits. A 62 with [58,66]
is a finding; a 62 with [21,89] means the personas fundamentally disagree — the
copy will split the audience, and the marketer must decide which half they are
willing to lose.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.config import settings
from app.scoring.model import ScoredPersona, compute_score


@dataclass(frozen=True)
class Interval:
    point: float
    lower: float
    upper: float
    persona_count: int
    bootstrap_sd: float
    jackknife_sd: float

    @property
    def width(self) -> float:
        return round(self.upper - self.lower, 1)

    @property
    def is_wide(self) -> bool:
        """A wide interval means the personas disagree — surfaced as prominently
        as a high score (§17.3)."""
        return self.width > 30.0

    def as_dict(self) -> dict[str, float | int | bool]:
        return {
            "point": self.point,
            "lower": self.lower,
            "upper": self.upper,
            "width": self.width,
            "persona_count": self.persona_count,
            "is_wide": self.is_wide,
            "bootstrap_sd": self.bootstrap_sd,
            "jackknife_sd": self.jackknife_sd,
        }


def _quantile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _sd(vals: list[float]) -> float:
    n = len(vals)
    if n < 2:
        return 0.0
    mean = sum(vals) / n
    return (sum((v - mean) ** 2 for v in vals) / (n - 1)) ** 0.5


def bootstrap_interval(
    scored: list[ScoredPersona],
    context_multiplier: float = 1.0,
    iterations: int | None = None,
    seed: int | None = None,
) -> tuple[list[float], float]:
    """Resample personas with replacement; recompute the index each time.

    Bootstrap rather than a normal approximation: with 12-30 personas and a
    skewed severity distribution, normal-approximation bounds fall outside
    [0,100]. Bootstrap is assumption-free.
    """
    iterations = iterations or settings.bootstrap_iterations
    if len(scored) < 2:
        return [], 0.0

    rng = random.Random(seed)
    n = len(scored)
    samples: list[float] = []
    for _ in range(iterations):
        resampled = [scored[rng.randrange(n)] for _ in range(n)]
        samples.append(compute_score(resampled, context_multiplier).index)

    return samples, _sd(samples)


def jackknife_sd(
    scored: list[ScoredPersona],
    context_multiplier: float = 1.0,
) -> float:
    """Leave-one-out spread — the uncertainty from *which* personas were selected.

    sigma^2 = (K-1)/K * sum((Index_(-i) - mean)^2)
    """
    n = len(scored)
    if n < 3:
        return 0.0

    loo: list[float] = []
    for i in range(n):
        subset = scored[:i] + scored[i + 1 :]
        loo.append(compute_score(subset, context_multiplier).index)

    mean = sum(loo) / n
    variance = ((n - 1) / n) * sum((v - mean) ** 2 for v in loo)
    return variance**0.5


def compute_interval(
    scored: list[ScoredPersona],
    context_multiplier: float = 1.0,
    seed: int | None = None,
) -> Interval:
    """Combined interval: bootstrap quantiles widened by selection uncertainty."""
    point = compute_score(scored, context_multiplier).index

    if len(scored) < 2:
        return Interval(point, point, point, len(scored), 0.0, 0.0)

    samples, boot_sd = bootstrap_interval(scored, context_multiplier, seed=seed)
    jack_sd = jackknife_sd(scored, context_multiplier)

    samples.sort()
    lower = _quantile(samples, settings.ci_lower_quantile)
    upper = _quantile(samples, settings.ci_upper_quantile)

    # Widen by the part of selection uncertainty the bootstrap does not already
    # capture.
    #
    # Naively adding the full jackknife sd double-counts: resampling with
    # replacement ALREADY drops personas (a given persona is absent from ~37% of
    # resamples at K=10), so leave-one-out sensitivity is largely reflected in
    # the bootstrap spread. Adding it again produced intervals pinned to [0,100]
    # whenever the tail term made one persona pivotal — which is exactly the case
    # the product cares about most.
    #
    # We widen only by the excess, when leave-one-out is more volatile than
    # resampling suggests. In the common case the bootstrap dominates and no
    # widening is applied.
    z = 1.2816
    excess = max(0.0, jack_sd - boot_sd)
    widen = z * excess

    # Floor: a small panel of simulated personas can never justify a point
    # estimate. When they all agree, the bootstrap resamples identical values and
    # reports zero spread — an artifact of the panel being small and fixed, not
    # evidence that the answer is certain. Reporting [52.3, 52.3] from 10
    # simulated reactions would be the precision illusion the plan warns about
    # (§22.6), and it is worse than reporting nothing.
    #
    # The floor scales as 1/sqrt(K): a panel of 8 deserves a visibly weaker
    # interval than one of 30. It is a statement about the method's resolution,
    # not about this particular copy.
    resolution_floor = 12.0 / (len(scored) ** 0.5)

    half_width = max((upper - lower) / 2.0 + widen, resolution_floor)
    lower = max(0.0, point - half_width)
    upper = min(100.0, point + half_width)

    return Interval(
        point=round(point, 1),
        lower=round(lower, 1),
        upper=round(upper, 1),
        persona_count=len(scored),
        bootstrap_sd=round(boot_sd, 2),
        jackknife_sd=round(jack_sd, 2),
    )
