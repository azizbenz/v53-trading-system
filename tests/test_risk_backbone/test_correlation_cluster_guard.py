"""Tests for risk_backbone.correlation_cluster_guard — Build-4."""
import pytest

from risk_backbone.correlation_cluster_guard.cluster_registry import (
    CorrelationCluster,
    ClusterRegistry,
    DEFAULT_CLUSTERS,
)
from risk_backbone.correlation_cluster_guard.cluster_exposure_calculator import (
    ClusterExposure,
    AllClusterExposures,
    calculate_cluster_exposures,
)
from risk_backbone.correlation_cluster_guard.projected_cluster_checker import (
    ProjectedClusterExposure,
    check_projected_cluster,
)
from risk_backbone.correlation_cluster_guard.cluster_cap_guard import (
    ClusterCapVerdict,
    ClusterCapResult,
    evaluate_cluster_cap,
)
from risk_backbone.correlation_cluster_guard.cluster_reporter import (
    ClusterEvent,
    ClusterStats,
    ClusterReporter,
)


# ── cluster_registry ──


class TestClusterRegistry:
    def test_default_clusters_loaded(self):
        reg = ClusterRegistry()
        assert reg.cluster_count == 4

    def test_get_cluster(self):
        reg = ClusterRegistry()
        cluster = reg.get_cluster("btc_majors")
        assert cluster is not None
        assert "BTCUSDT" in cluster.members

    def test_get_cluster_not_found(self):
        reg = ClusterRegistry()
        assert reg.get_cluster("nonexistent") is None

    def test_get_clusters_for_pair(self):
        reg = ClusterRegistry()
        clusters = reg.get_clusters_for_pair("ETHUSDT")
        assert "eth_ecosystem" in clusters

    def test_pair_not_in_any_cluster(self):
        reg = ClusterRegistry()
        clusters = reg.get_clusters_for_pair("DOGEUSDT")
        assert clusters == ()

    def test_pair_has_cluster(self):
        reg = ClusterRegistry()
        assert reg.pair_has_cluster("BTCUSDT") is True
        assert reg.pair_has_cluster("DOGEUSDT") is False

    def test_get_all_clusters(self):
        reg = ClusterRegistry()
        all_c = reg.get_all_clusters()
        assert len(all_c) == 4

    def test_custom_clusters(self):
        custom = (
            CorrelationCluster(
                cluster_id="test", name="Test", members=frozenset({"AAA", "BBB"}),
            ),
        )
        reg = ClusterRegistry(clusters=custom)
        assert reg.cluster_count == 1
        assert reg.pair_has_cluster("AAA") is True


# ── cluster_exposure_calculator ──


class TestClusterExposureCalculator:
    def test_empty_positions(self):
        result = calculate_cluster_exposures(positions={}, pair_to_clusters={})
        assert result.clusters == ()
        assert result.dominant_cluster == ""

    def test_single_cluster(self):
        positions = {"BTCUSDT": 100.0}
        pair_to_clusters = {"BTCUSDT": ("btc_majors",)}
        result = calculate_cluster_exposures(positions, pair_to_clusters)
        assert len(result.clusters) == 1
        assert result.clusters[0].exposure == pytest.approx(100.0)
        assert result.dominant_cluster == "btc_majors"

    def test_two_pairs_same_cluster(self):
        """ClusterExp_c = Σ x_i for i in cluster c."""
        positions = {"ETHUSDT": 100.0, "LINKUSDT": 50.0}
        pair_to_clusters = {
            "ETHUSDT": ("eth_ecosystem",),
            "LINKUSDT": ("eth_ecosystem",),
        }
        result = calculate_cluster_exposures(positions, pair_to_clusters)
        assert len(result.clusters) == 1
        assert result.clusters[0].exposure == pytest.approx(150.0)

    def test_dominant_cluster(self):
        positions = {"BTCUSDT": 200.0, "ETHUSDT": 100.0}
        pair_to_clusters = {
            "BTCUSDT": ("btc_majors",),
            "ETHUSDT": ("eth_ecosystem",),
        }
        result = calculate_cluster_exposures(positions, pair_to_clusters)
        assert result.dominant_cluster == "btc_majors"
        assert result.dominant_exposure == pytest.approx(200.0)

    def test_pair_in_no_cluster(self):
        positions = {"DOGEUSDT": 100.0}
        pair_to_clusters = {}
        result = calculate_cluster_exposures(positions, pair_to_clusters)
        assert result.clusters == ()

    def test_position_count(self):
        positions = {"ETHUSDT": 100.0, "LINKUSDT": 50.0}
        pair_to_clusters = {
            "ETHUSDT": ("eth_ecosystem",),
            "LINKUSDT": ("eth_ecosystem",),
        }
        result = calculate_cluster_exposures(positions, pair_to_clusters)
        assert result.clusters[0].position_count == 2


# ── projected_cluster_checker ──


class TestProjectedClusterChecker:
    def test_within_cap(self):
        result = check_projected_cluster(
            cluster_id="btc_majors",
            current_exposure=100.0,
            candidate_size=50.0,
            cluster_cap=200.0,
        )
        assert result.within_cap is True
        assert result.projected_exposure == pytest.approx(150.0)

    def test_exactly_at_cap(self):
        result = check_projected_cluster(
            cluster_id="btc_majors",
            current_exposure=100.0,
            candidate_size=100.0,
            cluster_cap=200.0,
        )
        assert result.within_cap is True

    def test_exceeds_cap(self):
        result = check_projected_cluster(
            cluster_id="btc_majors",
            current_exposure=150.0,
            candidate_size=100.0,
            cluster_cap=200.0,
        )
        assert result.within_cap is False
        assert result.projected_exposure == pytest.approx(250.0)

    def test_cluster_id_stored(self):
        result = check_projected_cluster(
            cluster_id="eth_ecosystem",
            current_exposure=0.0,
            candidate_size=10.0,
            cluster_cap=100.0,
        )
        assert result.cluster_id == "eth_ecosystem"


# ── cluster_cap_guard ──


class TestClusterCapGuard:
    def test_accepted(self):
        result = evaluate_cluster_cap(
            pair="BTCUSDT",
            cluster_id="btc_majors",
            current_exposure=50.0,
            candidate_size=50.0,
            cluster_cap=200.0,
        )
        assert result.verdict == ClusterCapVerdict.ACCEPTED

    def test_rejected(self):
        result = evaluate_cluster_cap(
            pair="BTCUSDT",
            cluster_id="btc_majors",
            current_exposure=150.0,
            candidate_size=100.0,
            cluster_cap=200.0,
        )
        assert result.verdict == ClusterCapVerdict.REJECTED
        assert result.reason != ""

    def test_at_cap_boundary(self):
        result = evaluate_cluster_cap(
            pair="BTCUSDT",
            cluster_id="btc_majors",
            current_exposure=100.0,
            candidate_size=100.0,
            cluster_cap=200.0,
        )
        assert result.verdict == ClusterCapVerdict.ACCEPTED

    def test_result_fields(self):
        result = evaluate_cluster_cap(
            pair="ETHUSDT",
            cluster_id="eth_ecosystem",
            current_exposure=50.0,
            candidate_size=30.0,
            cluster_cap=200.0,
        )
        assert result.pair == "ETHUSDT"
        assert result.cluster_id == "eth_ecosystem"
        assert result.projected_exposure == pytest.approx(80.0)

    def test_no_cluster_rejected(self):
        """Pair without explicit cluster => fail-closed REJECTED_NO_CLUSTER."""
        result = evaluate_cluster_cap(
            pair="DOGEUSDT",
            cluster_id=None,
            current_exposure=0.0,
            candidate_size=50.0,
            cluster_cap=200.0,
        )
        assert result.verdict == ClusterCapVerdict.REJECTED_NO_CLUSTER
        assert "no explicit cluster" in result.reason
        assert "DOGEUSDT" in result.reason


# ── cluster_reporter ──


class TestClusterReporter:
    def test_initial_state(self):
        reporter = ClusterReporter()
        stats = reporter.get_stats()
        assert stats.total_accepted == 0
        assert stats.total_refused == 0

    def test_record_accepted(self):
        reporter = ClusterReporter()
        reporter.record_accepted(pair="BTCUSDT", cluster_id="btc_majors")
        stats = reporter.get_stats()
        assert stats.total_accepted == 1

    def test_record_refused(self):
        reporter = ClusterReporter()
        reporter.record_refused(pair="BTCUSDT", cluster_id="btc_majors", reason="over cap")
        stats = reporter.get_stats()
        assert stats.total_refused == 1

    def test_get_events_all(self):
        reporter = ClusterReporter()
        reporter.record_accepted(pair="BTCUSDT", cluster_id="btc_majors")
        reporter.record_refused(pair="ETHUSDT", cluster_id="eth_ecosystem", reason="cap")
        events = reporter.get_events()
        assert len(events) == 2

    def test_get_events_by_cluster(self):
        reporter = ClusterReporter()
        reporter.record_accepted(pair="BTCUSDT", cluster_id="btc_majors")
        reporter.record_accepted(pair="ETHUSDT", cluster_id="eth_ecosystem")
        events = reporter.get_events(cluster_id="btc_majors")
        assert len(events) == 1
        assert events[0].pair == "BTCUSDT"

    def test_stats_cluster_exposures_non_empty(self):
        """get_stats().cluster_exposures must be populated after accepted trades."""
        reporter = ClusterReporter()
        reporter.record_accepted(pair="BTCUSDT", cluster_id="btc_majors", size=200.0)
        reporter.record_accepted(pair="ETHUSDT", cluster_id="eth_ecosystem", size=100.0)
        stats = reporter.get_stats()
        assert len(stats.cluster_exposures) == 2
        assert stats.cluster_exposures["btc_majors"] == pytest.approx(200.0)
        assert stats.cluster_exposures["eth_ecosystem"] == pytest.approx(100.0)

    def test_stats_dominant_cluster(self):
        """get_stats().dominant_cluster must be the cluster with highest exposure."""
        reporter = ClusterReporter()
        reporter.record_accepted(pair="BTCUSDT", cluster_id="btc_majors", size=200.0)
        reporter.record_accepted(pair="ETHUSDT", cluster_id="eth_ecosystem", size=100.0)
        reporter.record_accepted(pair="LINKUSDT", cluster_id="eth_ecosystem", size=50.0)
        stats = reporter.get_stats()
        assert stats.dominant_cluster == "btc_majors"
        assert stats.cluster_exposures["eth_ecosystem"] == pytest.approx(150.0)

    def test_event_frozen(self):
        event = ClusterEvent(
            pair="BTCUSDT", cluster_id="btc_majors", accepted=True,
        )
        with pytest.raises(Exception):
            event.pair = "ETHUSDT"
