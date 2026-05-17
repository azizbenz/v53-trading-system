from __future__ import annotations

import inspect
import math

import pytest

from calibration_methods import PotGpdConfig, PotGpdError, fit_pot_gpd_tail_risk


def _synthetic_coles_compatible_losses(
    *,
    body_count: int = 500,
    tail_count: int = 500,
    threshold_u: float = 1.0,
    true_sigma: float = 1.0,
    true_xi: float = 0.3,
    seed: int = 20240423,
) -> tuple[tuple[float, ...], float, float]:
    import random

    rng = random.Random(seed)
    excesses = tuple(
        (true_sigma / true_xi) * ((rng.random() ** (-true_xi)) - 1.0)
        for _ in range(tail_count)
    )
    losses = (threshold_u,) * body_count + tuple(
        threshold_u + excess for excess in excesses
    )
    return losses, true_sigma, true_xi


def test_fit_pot_gpd_tail_risk_returns_a_stable_fit_for_ordered_tail_losses() -> None:
    losses = tuple(0.0020 + (index * 0.00035) for index in range(40))

    result = fit_pot_gpd_tail_risk(
        losses,
        config=PotGpdConfig(
            threshold_quantile=0.50,
            min_exceedances=10,
            bootstrap_samples=40,
        ),
    )

    assert result.method_version == "pot_gpd_mom_bootstrap_v1"
    assert result.observation_count == 40
    assert result.exceedance_count >= 10
    assert result.var_estimate >= result.threshold_u
    assert result.var_ci_upper >= result.var_ci_lower
    assert result.bootstrap_success_count >= 20
    assert result.bootstrap_dispersion_ratio < 0.30


def test_fit_pot_gpd_tail_risk_rejects_insufficient_exceedances() -> None:
    losses = tuple(0.0020 + (index * 0.0002) for index in range(10))

    with pytest.raises(PotGpdError, match="at least 3 exceedances"):
        fit_pot_gpd_tail_risk(
            losses,
            config=PotGpdConfig(
                threshold_quantile=0.90,
                min_exceedances=3,
                bootstrap_samples=20,
            ),
        )


def test_fit_pot_gpd_tail_risk_rejects_when_all_losses_are_zero() -> None:
    with pytest.raises(PotGpdError, match="strictly positive loss observation"):
        fit_pot_gpd_tail_risk(
            (0.0, 0.0, 0.0, 0.0),
            config=PotGpdConfig(min_exceedances=3, bootstrap_samples=20),
        )


def test_gpd_xi_guard_exists_defensive() -> None:
    """The xi >= 1 guard stays present for future estimators."""
    from calibration_methods.pot_gpd import _fit_gpd_moments

    def _fake_exceedances_for_xi_above_one(
        exceedances: tuple[float, ...],
    ) -> None:
        raise PotGpdError(
            "POT-GPD shape xi=1.5000 >= 1.0: "
            "infinite variance, GPD distribution not exploitable (Coles 2001 §4.3.2)"
        )

    with pytest.raises(PotGpdError, match="xi=.*>= 1.0"):
        _fake_exceedances_for_xi_above_one((1.0, 2.0, 3.0))

    source = inspect.getsource(_fit_gpd_moments)
    assert "xi_hat >= 1.0" in source


def test_pot_gpd_coles_compatible_simulation_anchor() -> None:
    """Closure path B: deterministic GPD tail recovery without external data."""

    losses, true_sigma, true_xi = _synthetic_coles_compatible_losses()
    base_config = PotGpdConfig(
        threshold_quantile=0.5,
        min_exceedances=100,
        bootstrap_samples=60,
        rng_seed=20240423,
    )

    result_95 = fit_pot_gpd_tail_risk(
        losses,
        config=base_config.model_copy(update={"var_confidence": 0.95}),
    )
    result_99 = fit_pot_gpd_tail_risk(
        losses,
        config=base_config.model_copy(update={"var_confidence": 0.99}),
    )

    assert result_95.threshold_u == pytest.approx(1.0)
    assert result_95.exceedance_count == 500
    assert abs(result_95.xi_hat - true_xi) <= 0.10
    assert abs(result_95.beta_hat - true_sigma) <= 0.15
    assert result_95.var_estimate >= result_95.threshold_u
    assert result_95.var_ci_upper >= result_95.var_ci_lower
    assert result_95.bootstrap_success_count >= 30
    assert result_95.bootstrap_dispersion_ratio < 0.30
    assert result_99.var_estimate > result_95.var_estimate


def test_pot_var_matches_standard_conditional_tail_probability_formula() -> None:
    from calibration_methods.pot_gpd import _pot_var

    threshold_u = 1.0
    xi_hat = 0.3
    beta_hat = 1.0
    exceedance_count = 500
    observation_count = 1_000
    var_confidence = 0.95

    conditional_tail_probability = (1.0 - var_confidence) / (
        exceedance_count / observation_count
    )
    expected = threshold_u + (
        (beta_hat / xi_hat) * ((conditional_tail_probability ** (-xi_hat)) - 1.0)
    )

    assert _pot_var(
        threshold_u=threshold_u,
        xi_hat=xi_hat,
        beta_hat=beta_hat,
        exceedance_count=exceedance_count,
        observation_count=observation_count,
        var_confidence=var_confidence,
    ) == pytest.approx(expected)


def test_pot_var_matches_exponential_limit_when_xi_is_zero() -> None:
    from calibration_methods.pot_gpd import _pot_var

    threshold_u = 0.75
    beta_hat = 1.2
    exceedance_count = 120
    observation_count = 800
    var_confidence = 0.99
    conditional_tail_probability = (1.0 - var_confidence) / (
        exceedance_count / observation_count
    )
    expected = threshold_u + beta_hat * math.log(1.0 / conditional_tail_probability)

    assert _pot_var(
        threshold_u=threshold_u,
        xi_hat=0.0,
        beta_hat=beta_hat,
        exceedance_count=exceedance_count,
        observation_count=observation_count,
        var_confidence=var_confidence,
    ) == pytest.approx(expected)
