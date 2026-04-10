"""Tests for execution_backbone.reconciliation_layer — Build-3."""
import logging

import pytest

from execution_backbone.reconciliation_layer.order_reconciler import (
    OrderDivergenceType,
    reconcile_orders,
)
from execution_backbone.reconciliation_layer.fill_reconciler import (
    FillReconciliationPolicy,
    reconcile_fills,
)
from execution_backbone.reconciliation_layer.position_reconciler import (
    PositionReconciliationPolicy,
    reconcile_positions,
)
from execution_backbone.reconciliation_layer.divergence_classifier import (
    DivergenceSeverity,
    classify_divergence,
    classify_all,
    resolve_divergence_threshold_policy,
)
from execution_backbone.reconciliation_layer.recovery_trigger import (
    RecoveryAction,
    RecoveryTrigger,
)


pytestmark = pytest.mark.build3


# --- Order Reconciler ---

class TestOrderReconciler:
    def test_aligned(self):
        result = reconcile_orders(
            {"o1": "filled", "o2": "acked"},
            {"o1": "filled", "o2": "acked"},
        )
        assert result.aligned is True
        assert result.order_diff == 0

    def test_local_only(self):
        result = reconcile_orders({"o1": "acked"}, {})
        assert result.aligned is False
        assert result.divergences[0].divergence_type == OrderDivergenceType.LOCAL_ONLY

    def test_remote_only(self):
        result = reconcile_orders({}, {"o1": "filled"})
        assert result.aligned is False
        assert result.divergences[0].divergence_type == OrderDivergenceType.REMOTE_ONLY

    def test_state_mismatch(self):
        result = reconcile_orders({"o1": "acked"}, {"o1": "filled"})
        assert result.aligned is False
        assert result.divergences[0].divergence_type == OrderDivergenceType.STATE_MISMATCH


# --- Fill Reconciler ---

class TestFillReconciler:
    def test_aligned(self):
        result = reconcile_fills({"o1": 1.0}, {"o1": 1.0})
        assert result.aligned is True

    def test_qty_diff(self):
        result = reconcile_fills({"o1": 1.0}, {"o1": 0.5})
        assert result.aligned is False
        assert result.divergences[0].qty_diff == pytest.approx(0.5)
        assert result.policy_id == "fill_reconciliation.tolerance.v1"

    def test_missing_order(self):
        result = reconcile_fills({"o1": 1.0}, {})
        assert result.aligned is False
        assert len(result.divergences) == 1

    def test_tolerance(self):
        result = reconcile_fills(
            {"o1": 1.0},
            {"o1": 1.0 + 1e-10},
            policy=FillReconciliationPolicy(
                policy_id="fill_reconciliation.test.v1",
                quantity_tolerance=1e-8,
            ),
        )
        assert result.aligned is True
        assert result.policy_id == "fill_reconciliation.test.v1"


# --- Position Reconciler ---

class TestPositionReconciler:
    def test_aligned(self):
        result = reconcile_positions({"BTC": 1.5}, {"BTC": 1.5})
        assert result.aligned is True

    def test_divergence(self):
        result = reconcile_positions({"BTC": 1.5}, {"BTC": 1.0})
        assert result.aligned is False
        assert result.divergences[0].abs_diff == pytest.approx(0.5)
        assert result.policy_id == "position_reconciliation.tolerance.v1"

    def test_missing_asset(self):
        result = reconcile_positions({"BTC": 1.0, "ETH": 5.0}, {"BTC": 1.0})
        assert result.aligned is False
        assert len(result.divergences) == 1  # ETH diverges

    def test_relative_diff(self):
        result = reconcile_positions({"BTC": 1.5}, {"BTC": 1.0})
        assert result.divergences[0].relative_diff == pytest.approx(0.5)
        assert result.divergences[0].relative_scale == pytest.approx(1.0)

    def test_relative_diff_uses_scale_floor_for_dust_positions(self):
        result = reconcile_positions(
            {"BTC": 1e-6},
            {"BTC": 0.0},
            policy=PositionReconciliationPolicy(
                policy_id="position_reconciliation.test.v1",
                absolute_tolerance=1e-9,
                relative_scale_floor=1e-6,
            ),
        )
        assert result.aligned is False
        assert result.policy_id == "position_reconciliation.test.v1"
        assert result.divergences[0].relative_scale == pytest.approx(1e-6)
        assert result.divergences[0].relative_diff == pytest.approx(1.0)


# --- Divergence Classifier ---

class TestDivergenceClassifier:
    def test_info(self):
        c = classify_divergence("order", "small", abs_diff=0.005)
        assert c.severity == DivergenceSeverity.INFO
        assert c.policy_id == "order_divergence.thresholds.v1"
        assert c.unit == "order_divergence_count"

    def test_warning(self):
        c = classify_divergence("order", "medium", abs_diff=1.0)
        assert c.severity == DivergenceSeverity.WARNING
        assert c.warning_threshold == pytest.approx(1.0)
        assert c.blocking_threshold == pytest.approx(2.0)
        assert c.critical_threshold == pytest.approx(5.0)

    def test_blocking(self):
        c = classify_divergence("position", "large", abs_diff=0.5)
        assert c.severity == DivergenceSeverity.BLOCKING
        assert c.policy_id == "position_divergence.thresholds.v1"
        assert c.unit == "position_quantity_units"

    def test_critical(self):
        c = classify_divergence("position", "huge", abs_diff=2.0)
        assert c.severity == DivergenceSeverity.CRITICAL

    def test_fill_thresholds_are_source_scoped(self):
        c = classify_divergence("fill", "fill mismatch", abs_diff=0.2)
        assert c.severity == DivergenceSeverity.BLOCKING
        assert c.policy_id == "fill_divergence.thresholds.v1"
        assert c.unit == "filled_quantity_units"

    def test_resolve_threshold_policy_invalid_source_raises(self):
        with pytest.raises(ValueError):
            resolve_divergence_threshold_policy("cash")

    def test_classify_all_max_severity(self):
        d1 = classify_divergence("order", "small", 0.005)
        d2 = classify_divergence("position", "big", 1.5)
        result = classify_all((d1, d2))
        assert result.max_severity == DivergenceSeverity.CRITICAL
        assert result.is_critical is True
        assert result.is_blocking is True

    def test_classify_all_empty(self):
        result = classify_all(())
        assert result.max_severity == DivergenceSeverity.INFO
        assert result.is_blocking is False


# --- Recovery Trigger ---

class TestRecoveryTrigger:
    def test_no_recovery_needed(self):
        rt = RecoveryTrigger(max_recon_age_s=60.0)
        rt.record_reconciliation(100.0)
        d = rt.evaluate(DivergenceSeverity.INFO, now=110.0)
        assert d.action == RecoveryAction.NONE

    def test_soft_resync_on_warning(self):
        rt = RecoveryTrigger()
        rt.record_reconciliation(100.0)
        d = rt.evaluate(DivergenceSeverity.WARNING, now=110.0)
        assert d.action == RecoveryAction.SOFT_RESYNC

    def test_hard_resync_on_blocking(self):
        rt = RecoveryTrigger()
        rt.record_reconciliation(100.0)
        d = rt.evaluate(DivergenceSeverity.BLOCKING, now=110.0)
        assert d.action == RecoveryAction.HARD_RESYNC

    def test_halt_on_critical(self):
        rt = RecoveryTrigger()
        rt.record_reconciliation(100.0)
        d = rt.evaluate(DivergenceSeverity.CRITICAL, now=110.0)
        assert d.action == RecoveryAction.HALT_TRADING

    def test_stale_recon_triggers_soft_resync(self):
        rt = RecoveryTrigger(max_recon_age_s=60.0)
        rt.record_reconciliation(100.0)
        d = rt.evaluate(DivergenceSeverity.INFO, now=200.0)  # 100s > 60s
        assert d.action == RecoveryAction.SOFT_RESYNC
        assert d.stale_reconciliation is True

    def test_never_reconciled_is_stale(self):
        rt = RecoveryTrigger()
        d = rt.evaluate(DivergenceSeverity.INFO, now=100.0)
        assert d.stale_reconciliation is True
        assert d.action == RecoveryAction.SOFT_RESYNC

    def test_history(self):
        rt = RecoveryTrigger()
        rt.record_reconciliation(100.0)
        rt.evaluate(DivergenceSeverity.INFO, now=110.0)
        rt.evaluate(DivergenceSeverity.CRITICAL, now=120.0)
        assert len(rt.get_history()) == 2

    def test_recovery_trigger_emits_structured_logs(self, caplog: pytest.LogCaptureFixture):
        caplog.set_level(logging.INFO)
        rt = RecoveryTrigger()
        rt.record_reconciliation(100.0)
        rt.evaluate(DivergenceSeverity.WARNING, now=110.0)
        messages = {record.message for record in caplog.records}
        assert "execution_reconciliation_recorded" in messages
        assert "execution_recovery_decision" in messages
