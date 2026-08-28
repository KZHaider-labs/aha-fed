"""Proposition 1 of Section 3.8: AHA-Fed weights never collapse to zero.

The convergence argument rests entirely on the softmax weights staying
bounded away from zero, so the bound is asserted here rather than left as a
claim in the text. If someone changes the scoring rule, these fail.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from src.federated.aggregators.adaptive import AdaptiveAggregator


def analytic_floor(k: int, alpha: float, beta: float, gamma: float,
                   size_ratio: float, d_max: float, q_min: float) -> float:
    """w_min >= 1 / (1 + (K-1) e^S), with S the maximum log-score spread."""
    spread = alpha * math.log(size_ratio) + beta * d_max + gamma * math.log(1 / q_min)
    return 1.0 / (1.0 + (k - 1) * math.exp(spread))


@pytest.mark.parametrize("alpha,beta,gamma", [(1, 4, 4), (1, 2, 2), (1, 8, 8)])
def test_weights_respect_the_analytic_floor(alpha, beta, gamma):
    k, n_lo, n_hi, q_min = 4, 100, 2000, 0.05
    floor = analytic_floor(k, alpha, beta, gamma, n_hi / n_lo, 1.0, q_min)
    agg = AdaptiveAggregator(alpha=alpha, beta=beta, gamma=gamma)
    rng = np.random.default_rng(0)

    for _ in range(2000):
        sizes = [int(x) for x in rng.integers(n_lo, n_hi, k)]
        distances = list(rng.random(k))                 # TV distance in [0, 1]
        quality = list(rng.uniform(q_min, 1.0, k))
        w = agg.compute_weights(sizes, distances, quality)

        assert min(w) >= floor, f"weight {min(w)} fell below the bound {floor}"
        assert math.isclose(sum(w), 1.0, rel_tol=1e-9)
        assert all(x > 0 for x in w)


def test_reduces_to_fedavg_when_beta_and_gamma_are_zero():
    """The special case the convergence statement leans on."""
    sizes = [100, 250, 400, 900]
    agg = AdaptiveAggregator(alpha=1.0, beta=0.0, gamma=0.0)
    w = agg.compute_weights(sizes, [0.4, 0.9, 0.1, 0.7], [0.2, 0.9, 0.5, 0.3])

    total = sum(sizes)
    for got, n in zip(w, sizes):
        assert math.isclose(got, n / total, rel_tol=1e-9)


def test_quality_floor_is_what_keeps_the_bound_finite():
    """Assumption (A4): without a positive q_min the floor degenerates."""
    tight = analytic_floor(4, 1, 4, 4, 20, 1.0, q_min=0.22)   # observed range
    loose = analytic_floor(4, 1, 4, 4, 20, 1.0, q_min=0.01)   # near-diverged
    assert tight > loose
    assert loose > 0                                          # still positive
