"""AHA-Fed: Adaptive Heterogeneity-Aware Aggregation.

Per-round client weights are computed in log-space:

    log w_k ∝ α · log(n_k) − β · D_k + γ · log(q_k + ε)

where
    n_k : client k's training-set size
    D_k : distributional distance from client k's label distribution to the
          across-client consensus (default: total-variation distance)
    q_k : client k's local quality signal in [0, 1] (e.g., 1 / (1 + train loss))
    ε   : small constant for numerical stability of the log

The vector ``w`` is normalized via numerically-stable softmax, so it always
defines a valid convex combination over clients.

Reduces to FedAvg when β = 0, γ = 0, α = 1: weights become softmax over
``log(n_k)``, which is identical (up to a constant) to ``n_k / Σ n_j``.
"""
from __future__ import annotations

import math
from typing import Sequence

import torch

from .fedavg import FedAvgAggregator


class AdaptiveAggregator(FedAvgAggregator):
    def __init__(
        self,
        alpha: float = 1.0,
        beta: float = 1.0,
        gamma: float = 1.0,
        log_eps: float = 1e-6,
        relative_quality: bool = False,
    ):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.log_eps = log_eps
        # Score each client against its own first-round quality rather than
        # against the other clients. See compute_weights.
        self.relative_quality = relative_quality
        self._quality_baseline: list[float] | None = None

    def compute_weights(
        self,
        client_sizes: Sequence[int],
        client_distances: Sequence[float],
        client_quality: Sequence[float],
    ) -> list[float]:
        n = len(client_sizes)
        if not (len(client_distances) == len(client_quality) == n):
            raise ValueError(
                "client_sizes, client_distances, client_quality must align"
            )

        quality = list(client_quality)
        if self.relative_quality:
            # A client's absolute loss reflects both how hard its data is and
            # how corrupted its labels are; only the second should move the
            # weights. Dividing by the client's own first-round quality
            # cancels the difficulty term, so a site that starts and stays
            # hard is not penalised, while one whose loss fails to fall as
            # training proceeds is.
            if self._quality_baseline is None:
                self._quality_baseline = [max(q, self.log_eps) for q in quality]
            quality = [
                max(q, self.log_eps) / self._quality_baseline[i]
                for i, q in enumerate(quality)
            ]

        log_scores = [
            self.alpha * math.log(max(client_sizes[i], 1))
            - self.beta * client_distances[i]
            + self.gamma * math.log(max(quality[i], self.log_eps))
            for i in range(n)
        ]
        max_score = max(log_scores)
        exps = [math.exp(s - max_score) for s in log_scores]
        z = sum(exps)
        return [e / z for e in exps]

    def aggregate(
        self,
        client_states: Sequence[dict[str, torch.Tensor]],
        client_sizes: Sequence[int],
        client_distances: Sequence[float] | None = None,
        client_quality: Sequence[float] | None = None,
    ) -> dict[str, torch.Tensor]:
        if client_distances is None or client_quality is None:
            return super().aggregate(client_states, client_sizes)

        weights = self.compute_weights(
            client_sizes, client_distances, client_quality
        )
        # Kept so the server can record per-round weights for analysis.
        self.last_weights = [float(w) for w in weights]
        aggregated: dict[str, torch.Tensor] = {}
        for key in client_states[0].keys():
            stacked = torch.stack(
                [
                    w * state[key].float()
                    for w, state in zip(weights, client_states)
                ],
                dim=0,
            )
            aggregated[key] = stacked.sum(dim=0)
        return aggregated
