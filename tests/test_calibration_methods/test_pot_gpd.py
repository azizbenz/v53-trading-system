from __future__ import annotations

import pytest

from calibration_methods import PotGpdConfig, PotGpdError, fit_pot_gpd_tail_risk


def test_fit_pot_gpd_tail_risk_returns_a_stable_fit_for_ordered_tail_losses():
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


def test_fit_pot_gpd_tail_risk_rejects_insufficient_exceedances():
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


def test_fit_pot_gpd_tail_risk_rejects_when_all_losses_are_zero():
    with pytest.raises(PotGpdError, match="strictly positive loss observation"):
        fit_pot_gpd_tail_risk(
            (0.0, 0.0, 0.0, 0.0),
            config=PotGpdConfig(min_exceedances=3, bootstrap_samples=20),
        )
