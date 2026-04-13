"""Shared Local IA Lab POT-GPD tail-risk helpers."""

from __future__ import annotations

import math
import random
from typing import Iterable

from pydantic import BaseModel, Field


class PotGpdError(ValueError):
    """Raised when POT-GPD inputs are mathematically unusable."""


class PotGpdConfig(BaseModel, frozen=True):
    """Bounded POT-GPD fit configuration for Local IA Lab only."""

    threshold_quantile: float = Field(default=0.90, gt=0.0, lt=1.0)
    var_confidence: float = Field(default=0.995, gt=0.90, lt=1.0)
    min_exceedances: int = Field(default=30, ge=3)
    bootstrap_samples: int = Field(default=100, ge=10)
    rng_seed: int = Field(default=53, ge=0)


class PotGpdResult(BaseModel, frozen=True):
    """Audit-ready POT-GPD tail-risk fit."""

    method_version: str = "pot_gpd_mom_bootstrap_v1"
    observation_count: int = Field(..., ge=3)
    threshold_quantile: float = Field(..., gt=0.0, lt=1.0)
    threshold_u: float = Field(..., ge=0.0)
    exceedance_count: int = Field(..., ge=3)
    xi_hat: float
    beta_hat: float = Field(..., gt=0.0)
    var_confidence: float = Field(..., gt=0.90, lt=1.0)
    var_estimate: float = Field(..., ge=0.0)
    bootstrap_samples: int = Field(..., ge=10)
    bootstrap_success_count: int = Field(..., ge=1)
    var_ci_lower: float = Field(..., ge=0.0)
    var_ci_upper: float = Field(..., ge=0.0)
    bootstrap_dispersion_ratio: float = Field(..., ge=0.0)
    passes_dispersion: bool


def fit_pot_gpd_tail_risk(
    losses: Iterable[float],
    *,
    config: PotGpdConfig | None = None,
) -> PotGpdResult:
    """Fit a bounded POT-GPD tail-risk model over non-negative loss magnitudes."""

    cfg = PotGpdConfig() if config is None else config
    values = _validated_losses(losses)
    threshold_u = _empirical_quantile(values, cfg.threshold_quantile)
    exceedances = tuple(value - threshold_u for value in values if value > threshold_u)
    if len(exceedances) < cfg.min_exceedances:
        raise PotGpdError(
            f"POT-GPD requires at least {cfg.min_exceedances} exceedances above the threshold"
        )

    xi_hat, beta_hat = _fit_gpd_moments(exceedances)
    var_estimate = _pot_var(
        threshold_u=threshold_u,
        xi_hat=xi_hat,
        beta_hat=beta_hat,
        exceedance_count=len(exceedances),
        observation_count=len(values),
        var_confidence=cfg.var_confidence,
    )

    rng = random.Random(cfg.rng_seed)
    bootstrap_vars: list[float] = []
    for _ in range(cfg.bootstrap_samples):
        sample = tuple(exceedances[rng.randrange(len(exceedances))] for _ in exceedances)
        try:
            xi_boot, beta_boot = _fit_gpd_moments(sample)
            bootstrap_vars.append(
                _pot_var(
                    threshold_u=threshold_u,
                    xi_hat=xi_boot,
                    beta_hat=beta_boot,
                    exceedance_count=len(exceedances),
                    observation_count=len(values),
                    var_confidence=cfg.var_confidence,
                )
            )
        except PotGpdError:
            continue

    if len(bootstrap_vars) < max(10, cfg.bootstrap_samples // 2):
        raise PotGpdError("POT-GPD bootstrap did not produce enough valid tail-risk replicas")

    bootstrap_sorted = tuple(sorted(bootstrap_vars))
    var_ci_lower = _empirical_quantile(bootstrap_sorted, 0.025)
    var_ci_upper = _empirical_quantile(bootstrap_sorted, 0.975)
    dispersion_ratio = (
        0.0
        if var_estimate <= 0.0
        else max(0.0, (var_ci_upper - var_ci_lower) / var_estimate)
    )

    return PotGpdResult(
        observation_count=len(values),
        threshold_quantile=cfg.threshold_quantile,
        threshold_u=threshold_u,
        exceedance_count=len(exceedances),
        xi_hat=xi_hat,
        beta_hat=beta_hat,
        var_confidence=cfg.var_confidence,
        var_estimate=var_estimate,
        bootstrap_samples=cfg.bootstrap_samples,
        bootstrap_success_count=len(bootstrap_sorted),
        var_ci_lower=var_ci_lower,
        var_ci_upper=var_ci_upper,
        bootstrap_dispersion_ratio=dispersion_ratio,
        passes_dispersion=dispersion_ratio < 0.20,
    )


def _validated_losses(losses: Iterable[float]) -> tuple[float, ...]:
    values = tuple(float(value) for value in losses)
    if len(values) < 3:
        raise PotGpdError("POT-GPD requires at least three loss observations")
    if not all(math.isfinite(value) and value >= 0.0 for value in values):
        raise PotGpdError("POT-GPD requires only finite non-negative loss observations")
    if max(values) <= 0.0:
        raise PotGpdError("POT-GPD requires at least one strictly positive loss observation")
    return tuple(sorted(values))


def _empirical_quantile(values: tuple[float, ...], probability: float) -> float:
    if not values:
        raise PotGpdError("POT-GPD quantile requires non-empty observations")
    index = int(math.floor((len(values) - 1) * probability))
    index = max(0, min(index, len(values) - 1))
    return values[index]


def _fit_gpd_moments(exceedances: tuple[float, ...]) -> tuple[float, float]:
    if len(exceedances) < 3:
        raise PotGpdError("POT-GPD requires at least three exceedances")
    mean_excess = sum(exceedances) / len(exceedances)
    if mean_excess <= 0.0:
        raise PotGpdError("POT-GPD exceedance mean must be > 0")
    variance = sum((value - mean_excess) ** 2 for value in exceedances) / (len(exceedances) - 1)
    if variance <= 0.0:
        raise PotGpdError("POT-GPD exceedance variance must be > 0")

    ratio = (mean_excess * mean_excess) / variance
    xi_hat = 0.5 * (1.0 - ratio)
    if xi_hat >= 1.0:
        raise PotGpdError(
            f"POT-GPD shape xi={xi_hat:.4f} >= 1.0: "
            "infinite variance, GPD distribution not exploitable (Coles 2001 §4.3.2)"
        )
    beta_hat = mean_excess * (1.0 - xi_hat)

    if not math.isfinite(xi_hat) or not math.isfinite(beta_hat):
        raise PotGpdError("POT-GPD fit produced non-finite parameters")
    if beta_hat <= 0.0:
        raise PotGpdError("POT-GPD scale parameter must be > 0")
    return xi_hat, beta_hat


def _pot_var(
    *,
    threshold_u: float,
    xi_hat: float,
    beta_hat: float,
    exceedance_count: int,
    observation_count: int,
    var_confidence: float,
) -> float:
    tail_probability = (exceedance_count / observation_count) * (1.0 - var_confidence)
    if tail_probability <= 0.0 or tail_probability >= 1.0:
        raise PotGpdError("POT-GPD tail probability must be in (0, 1)")
    if abs(xi_hat) < 1e-9:
        return threshold_u + (beta_hat * math.log(1.0 / tail_probability))
    return threshold_u + ((beta_hat / xi_hat) * ((tail_probability ** (-xi_hat)) - 1.0))


__all__ = [
    "PotGpdConfig",
    "PotGpdError",
    "PotGpdResult",
    "fit_pot_gpd_tail_risk",
]
