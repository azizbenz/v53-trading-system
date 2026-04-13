from __future__ import annotations

from calibration_methods import apply_human_maximum_cap, apply_human_minimum_floor


def test_apply_human_minimum_floor_reports_binding_and_satisfaction():
    bound = apply_human_minimum_floor(1.80, 2.00)
    free = apply_human_minimum_floor(2.41, 2.00)

    assert bound.published_value == 2.00
    assert bound.hard_cap_satisfied is True
    assert bound.hard_cap_binding is True
    assert free.published_value == 2.41
    assert free.hard_cap_satisfied is True
    assert free.hard_cap_binding is False


def test_apply_human_maximum_cap_reports_binding_and_satisfaction():
    bound = apply_human_maximum_cap(0.024, 0.020)
    free = apply_human_maximum_cap(0.018, 0.020)

    assert bound.published_value == 0.020
    assert bound.hard_cap_satisfied is True
    assert bound.hard_cap_binding is True
    assert free.published_value == 0.018
    assert free.hard_cap_satisfied is True
    assert free.hard_cap_binding is False
