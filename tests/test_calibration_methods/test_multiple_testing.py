from __future__ import annotations

import pytest

from calibration_methods import MultipleTestingError, apply_holm_bonferroni


def test_apply_holm_bonferroni_applies_step_down_thresholds():
    result = apply_holm_bonferroni(
        (
            ("h1", 0.01),
            ("h2", 0.03),
            ("h3", 0.20),
        ),
        family_alpha=0.05,
    )

    assert result.hypothesis_count == 3
    assert result.any_rejected is True
    assert result.all_rejected is False
    assert result.adjusted_hypotheses[0].adjusted_alpha == pytest.approx(0.05 / 3.0)
    assert result.adjusted_hypotheses[0].rejected is True
    assert result.adjusted_hypotheses[1].adjusted_alpha == pytest.approx(0.05 / 2.0)
    assert result.adjusted_hypotheses[1].rejected is False
    assert result.adjusted_hypotheses[2].rejected is False


def test_apply_holm_bonferroni_rejects_duplicate_hypothesis_ids():
    with pytest.raises(MultipleTestingError, match="hypothesis_id values must be unique"):
        apply_holm_bonferroni((("h1", 0.01), ("h1", 0.02)))
