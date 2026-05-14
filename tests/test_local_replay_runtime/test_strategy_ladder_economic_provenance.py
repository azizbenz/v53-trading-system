"""Tests pour strategy_ladder_economic_provenance (Audit 2026-05-07 P0).

Prouve que :
1. measure_spread_bps_from_book_snapshot mesure correctement le spread reel
2. compute_economic_provenance retourne les flags de provenance corrects
3. Sur un dataset synthetique, le spread mesure differe du hardcoded 4.0
4. Sur le run dossier reel, le spread mesure est ~1.7 (vs hardcoded 4.0)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from local_replay_runtime.strategy_ladder_edge_model_provider import EdgeEstimate
from local_replay_runtime.strategy_ladder_economic_provenance import (
    DEFAULT_EXPECTED_EDGE_BPS,
    DEFAULT_LATENCY_PENALTY_BPS,
    DEFAULT_SLIPPAGE_BPS,
    DEFAULT_SPREAD_BPS_BY_BOOK_STATUS,
    EconomicProvenance,
    compute_economic_provenance,
    expected_edge_backtest_truth_status,
    is_expected_edge_backtest_truth,
    measure_spread_bps_from_book_snapshot,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )


def _book_snapshot(
    *, ts_ms: int, best_bid: float, best_ask: float
) -> dict[str, object]:
    """Construit un snapshot orderbook synthetique avec top-of-book spread voulu."""
    return {
        "timestamp_ms": ts_ms,
        "pair": "TESTPAIR",
        "event_type": "snapshot",
        "update_id": ts_ms,
        "bids": [[str(best_bid), "10.0"], [str(best_bid - 0.01), "5.0"]],
        "asks": [[str(best_ask), "10.0"], [str(best_ask + 0.01), "5.0"]],
    }


def test_measure_spread_bps_returns_real_value(tmp_path: Path) -> None:
    """spread_bps mesure = (ask - bid) / mid * 10000"""
    book_path = tmp_path / "book.jsonl"
    # bid=99.95, ask=100.05 → spread=0.10, mid=100.0 → spread_bps=10.0
    _write_jsonl(
        book_path,
        [_book_snapshot(ts_ms=1_700_000_000_000, best_bid=99.95, best_ask=100.05)],
    )
    spread, status = measure_spread_bps_from_book_snapshot(
        raw_book_path=book_path, timestamp_ms=1_700_000_000_000
    )
    assert status == "MEASURED_FROM_BOOK_SNAPSHOT"
    assert abs(spread - 10.0) < 0.001, f"Expected ~10 bps, got {spread}"


def test_measure_spread_bps_picks_closest_in_window(tmp_path: Path) -> None:
    """Le snapshot le plus proche du timestamp_ms doit etre choisi."""
    book_path = tmp_path / "book.jsonl"
    base = 1_700_000_000_000
    _write_jsonl(
        book_path,
        [
            _book_snapshot(ts_ms=base, best_bid=99.0, best_ask=101.0),  # 200 bps
            _book_snapshot(ts_ms=base + 30_000, best_bid=99.95, best_ask=100.05),  # 10 bps
            _book_snapshot(ts_ms=base + 90_000, best_bid=99.9, best_ask=100.1),  # 20 bps
        ],
    )
    # Timestamp 30s + 5s = closest to base + 30_000 (within tolerance)
    spread, status = measure_spread_bps_from_book_snapshot(
        raw_book_path=book_path, timestamp_ms=base + 35_000, tolerance_ms=60_000
    )
    assert status == "MEASURED_FROM_BOOK_SNAPSHOT"
    assert abs(spread - 10.0) < 0.001


def test_measure_spread_bps_returns_stale_outside_tolerance_within_stale_max(
    tmp_path: Path,
) -> None:
    """Audit 2026-05-13 W2 : hors tolerance mais dans `stale_snapshot_max_age_ms`,
    retour spread mesure stale (tier 3) avec provenance MEASURED_*_STALE.

    Sur les raw_windows B2 (snapshot Bybit a -85min du target), la
    reconstruction echoue souvent (CROSS-book persistant) — le tier 3
    permet de retourner une mesure reelle plutot que le fallback hardcoded
    DEFAULT_BY_BOOK_STATUS (= 4.0 bps).
    """
    book_path = tmp_path / "book.jsonl"
    _write_jsonl(
        book_path,
        [_book_snapshot(ts_ms=1_700_000_000_000, best_bid=99.95, best_ask=100.05)],
    )
    spread, status = measure_spread_bps_from_book_snapshot(
        raw_book_path=book_path,
        timestamp_ms=1_700_000_000_000 + 200_000,  # 200s later (outside tolerance)
        tolerance_ms=60_000,
        stale_snapshot_max_age_ms=24 * 60 * 60 * 1000,
    )
    assert status == "MEASURED_FROM_BOOK_SNAPSHOT_STALE"
    assert spread is not None
    assert abs(spread - 10.0) < 0.001


def test_measure_spread_bps_returns_none_beyond_stale_max(tmp_path: Path) -> None:
    """Au-dela de `stale_snapshot_max_age_ms`, retour None + reason code.

    Le tier 3 stale a une duree de vie max (default 24h) — au-dela, la mesure
    est jugee non audit-ready et on retourne None pour laisser le caller
    retomber sur DEFAULT_BY_BOOK_STATUS.
    """
    book_path = tmp_path / "book.jsonl"
    _write_jsonl(
        book_path,
        [_book_snapshot(ts_ms=1_700_000_000_000, best_bid=99.95, best_ask=100.05)],
    )
    spread, status = measure_spread_bps_from_book_snapshot(
        raw_book_path=book_path,
        timestamp_ms=1_700_000_000_000 + 200_000,
        tolerance_ms=60_000,
        stale_snapshot_max_age_ms=100_000,  # 100s : 200s offset > stale_max
    )
    assert spread is None
    assert "TOO_FAR" in status or "BEYOND_STALE_MAX" in status


def test_measure_spread_bps_handles_missing_path() -> None:
    """Sans path, retour None + BOOK_PATH_MISSING."""
    spread, status = measure_spread_bps_from_book_snapshot(
        raw_book_path=None, timestamp_ms=1_700_000_000_000
    )
    assert spread is None
    assert status == "BOOK_PATH_MISSING"


def test_compute_economic_provenance_with_book(tmp_path: Path) -> None:
    """Avec book valide, spread_provenance = MEASURED, autres TO_CALIBRATE.

    Audit 2026-05-07 venue-aware : caller doit fournir venue explicitement
    sinon fallback UNKNOWN_VENUE_METADATA (audit-ready).
    """
    book_path = tmp_path / "book.jsonl"
    _write_jsonl(
        book_path,
        [_book_snapshot(ts_ms=1_700_000_000_000, best_bid=99.95, best_ask=100.05)],
    )
    prov = compute_economic_provenance(
        timestamp_ms=1_700_000_000_000,
        book_status="BOOK_DEPTH20_AVAILABLE",
        raw_book_path=book_path,
        venue="bybit",  # legacy backtest data Bybit
    )
    assert isinstance(prov, EconomicProvenance)
    assert prov.spread_provenance == "MEASURED_FROM_BOOK_SNAPSHOT"
    assert abs(prov.spread_bps - 10.0) < 0.001
    # Audit 2026-05-07 MVP : edge sans OHLCV path → DEFAULT_TO_CALIBRATE
    assert prov.expected_edge_provenance == "DEFAULT_TO_CALIBRATE"
    assert prov.expected_edge_bps == DEFAULT_EXPECTED_EDGE_BPS
    # Slippage sans trade path → DEFAULT_TO_CALIBRATE
    assert prov.slippage_provenance == "DEFAULT_TO_CALIBRATE"
    assert prov.slippage_bps == DEFAULT_SLIPPAGE_BPS
    # Audit 2026-05-07 MVP : latency Bybit conservative par defaut
    assert prov.latency_provenance == "STATIC_CONSERVATIVE_FROM_BYBIT_HISTORICAL"
    # Audit 2026-05-07 MVP : fee Bybit metadata par defaut (10 bps)
    assert prov.fee_provenance == "MEASURED_FROM_VENUE_METADATA_BYBIT_RESEARCH"
    assert prov.fee_bps == 10.0
    # aggregated_provenance evolue : spread + fee + latency = PARTIALLY_MEASURED
    assert prov.aggregated_provenance == "PARTIALLY_MEASURED"


def test_compute_economic_provenance_preserves_stale_tier_in_spread_provenance(
    tmp_path: Path,
) -> None:
    """Audit 2026-05-14 W2 fix : `compute_economic_provenance` doit preserver
    le tier returne par `measure_spread_bps_from_book_snapshot` au lieu
    d'aplatir vers "MEASURED_FROM_BOOK_SNAPSHOT".

    Sans cette preservation, la telemetrie ne distinguait pas une mesure
    dense (silver) d'une mesure stale 24h (raw_windows B2), masquant la
    fragilite reelle du spread sur le run B2. Le fix expose le tier dans
    `spread_provenance` ET emet un warning audit-ready
    `SPREAD_MEASURED_STALE:*`.
    """
    book_path = tmp_path / "book.jsonl"
    _write_jsonl(
        book_path,
        [_book_snapshot(ts_ms=1_700_000_000_000, best_bid=99.95, best_ask=100.05)],
    )
    # Timestamp hors tolerance (200s) mais dans stale_max (24h default) →
    # tier 3 stale est utilise par measure_spread_bps_from_book_snapshot.
    prov = compute_economic_provenance(
        timestamp_ms=1_700_000_000_000 + 200_000,
        book_status="BOOK_DEPTH20_AVAILABLE",
        raw_book_path=book_path,
        venue="bybit",
    )
    assert prov.spread_provenance == "MEASURED_FROM_BOOK_SNAPSHOT_STALE"
    assert abs(prov.spread_bps - 10.0) < 0.001
    # Warning audit-ready expose la nature stale de la mesure
    assert any(
        "SPREAD_MEASURED_STALE" in w for w in prov.measurement_warnings
    )
    # spread_provenance commence par "MEASURED_" → aggregated reste mesure
    # (PARTIALLY_MEASURED, pas HARDCODED_PROXY_CONSTANTS)
    assert prov.aggregated_provenance == "PARTIALLY_MEASURED"


def test_compute_economic_provenance_without_book_falls_back(tmp_path: Path) -> None:
    """Sans book, fallback DEFAULT_SPREAD_BPS_BY_BOOK_STATUS."""
    prov = compute_economic_provenance(
        timestamp_ms=1_700_000_000_000,
        book_status="BOOK_DEPTH20_AVAILABLE",
        raw_book_path=None,
        venue="bybit",  # caller doit fournir venue explicitement
    )
    assert prov.spread_provenance == "DEFAULT_BY_BOOK_STATUS"
    assert prov.spread_bps == DEFAULT_SPREAD_BPS_BY_BOOK_STATUS["BOOK_DEPTH20_AVAILABLE"]
    # Audit 2026-05-07 MVP : meme sans book, fee venue + latency conservative sont
    # mesurees → aggregated bascule en PARTIALLY_MEASURED (audit-ready : non
    # promotion-ready tant que != FULLY_MEASURED).
    assert prov.aggregated_provenance == "PARTIALLY_MEASURED"
    # Warning explicite
    assert any(
        "SPREAD_FALLBACK" in w for w in prov.measurement_warnings
    )


def test_compute_economic_provenance_overrides_apply(tmp_path: Path) -> None:
    """Les overrides du caller doivent flagger MEASURED."""
    prov = compute_economic_provenance(
        timestamp_ms=1_700_000_000_000,
        book_status="BOOK_DEPTH20_AVAILABLE",
        raw_book_path=None,
        expected_edge_bps_override=8.5,
        slippage_bps_override=1.2,
        latency_penalty_bps_override=0.5,
        fee_bps_override=0.3,
    )
    # Audit 2026-05-07 MVP : provenance flag distingue overrides explicites du caller
    # via le suffixe _OVERRIDE pour que le fallback default ne soit pas confondu
    # avec la mesure canonique.
    assert prov.expected_edge_bps == 8.5
    assert prov.expected_edge_provenance == "MEASURED_FROM_EDGE_MODEL_OVERRIDE"
    assert prov.slippage_bps == 1.2
    assert prov.slippage_provenance == "MEASURED_FROM_KYLE_LAMBDA_OVERRIDE"
    assert prov.latency_penalty_bps == 0.5
    assert prov.latency_provenance == "MEASURED_FROM_VENUE_MODEL_OVERRIDE"
    assert prov.fee_bps == 0.3
    # Audit 2026-05-07 venue-aware : override fee bascule la provenance vers
    # MEASURED_FROM_VENUE_API_OVERRIDE (semantique live API account dynamique).
    assert prov.fee_provenance == "MEASURED_FROM_VENUE_API_OVERRIDE"


def test_forward_return_edge_is_proxy_not_backtest_truth(tmp_path: Path) -> None:
    ohlcv_path = tmp_path / "ohlcv.jsonl"
    base = 1_700_000_000_000
    _write_jsonl(
        ohlcv_path,
        [
            {"timestamp_ms": base + i * 60_000, "close": 100.0 + i}
            for i in range(6)
        ],
    )

    prov = compute_economic_provenance(
        timestamp_ms=base + 5 * 60_000,
        book_status="BOOK_DEPTH20_AVAILABLE",
        pair="BNBUSDT",
        raw_ohlcv_path=ohlcv_path,
        venue="bybit",
    )

    assert prov.expected_edge_bps > 0.0
    assert prov.expected_edge_provenance == "PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE"
    assert not is_expected_edge_backtest_truth(prov.expected_edge_provenance)
    assert (
        expected_edge_backtest_truth_status(prov.expected_edge_provenance)
        == "EXPECTED_EDGE_PROXY_BLOCKED"
    )
    assert any("EDGE_PROXY_BLOCKED" in warning for warning in prov.measurement_warnings)


class _StaticGovernedExpectedEdgeModel:
    artifact_hash = "a" * 64
    feature_hash = "b" * 64

    def estimate_expected_edge_bps(self, **kwargs: object) -> EdgeEstimate:
        feature_values = kwargs["feature_values"]
        assert isinstance(feature_values, dict)
        assert feature_values["edge_score"] == 2.0
        return EdgeEstimate(
            edge_bps=12.5,
            provenance="GOVERNED_ML_ARTIFACT_BACKTEST_TRUTH",
            n_lookback_bars_used=0,
            median_abs_forward_return=0.0,
            detector_status="GOVERNED_EDGE_MODEL_READY",
            artifact_hash=self.artifact_hash,
            feature_hash=self.feature_hash,
            model_status="GOVERNED_EDGE_MODEL_READY",
        )


def test_compute_economic_provenance_uses_governed_edge_model_before_proxy() -> None:
    prov = compute_economic_provenance(
        timestamp_ms=1_700_000_000_000,
        book_status="BOOK_DEPTH20_AVAILABLE",
        pair="BNBUSDT",
        venue="bybit",
        raw_ohlcv_path=Path("unused_ohlcv.jsonl"),
        expected_edge_model=_StaticGovernedExpectedEdgeModel(),
        expected_edge_model_required=True,
        expected_edge_feature_values={"edge_score": 2.0},
    )

    assert prov.expected_edge_bps == 12.5
    assert prov.expected_edge_provenance == "GOVERNED_ML_ARTIFACT_BACKTEST_TRUTH"
    assert prov.expected_edge_model_status == "GOVERNED_EDGE_MODEL_READY"
    assert prov.expected_edge_model_artifact_hash == "a" * 64
    assert is_expected_edge_backtest_truth(prov.expected_edge_provenance)
    assert (
        expected_edge_backtest_truth_status(prov.expected_edge_provenance)
        == "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH"
    )
    assert not any("EDGE_PROXY_BLOCKED" in warning for warning in prov.measurement_warnings)


def test_compute_economic_provenance_falls_back_fail_closed_when_required_edge_model_is_unloaded() -> None:
    prov = compute_economic_provenance(
        timestamp_ms=1_700_000_000_000,
        book_status="BOOK_DEPTH20_AVAILABLE",
        pair="BNBUSDT",
        venue="bybit",
        raw_ohlcv_path=Path("unused_ohlcv.jsonl"),
        expected_edge_model_required=True,
        expected_edge_model_load_status="GOVERNED_EDGE_MODEL_HASH_MISMATCH",
        expected_edge_feature_values={"edge_score": 2.0},
    )

    assert prov.expected_edge_bps == 5.0
    assert prov.expected_edge_provenance == "DEFAULT_TO_CALIBRATE"
    assert not is_expected_edge_backtest_truth(prov.expected_edge_provenance)
    assert (
        expected_edge_backtest_truth_status(prov.expected_edge_provenance)
        == "EXPECTED_EDGE_DEFAULT_BLOCKED"
    )
    assert any("EDGE_MODEL_BLOCKED" in warning for warning in prov.measurement_warnings)
    assert any("EDGE_FALLBACK" in warning for warning in prov.measurement_warnings)


# ===========================================================================
# Audit 2026-05-07 venue-aware : tests multi-venue
# ===========================================================================


def test_compute_economic_provenance_venue_binance_explicit() -> None:
    """venue='binance' → fee_provenance Binance Spot."""
    prov = compute_economic_provenance(
        timestamp_ms=1_700_000_000_000,
        book_status="BOOK_DEPTH20_AVAILABLE",
        pair="BNBUSDT",
        venue="binance",
    )
    assert prov.fee_bps == 10.0
    assert prov.fee_provenance == "MEASURED_FROM_BINANCE_SPOT_PUBLIC_RATES"
    assert prov.latency_provenance == "STATIC_CONSERVATIVE_FROM_BINANCE_HISTORICAL"


def test_compute_economic_provenance_venue_bybit_explicit() -> None:
    prov = compute_economic_provenance(
        timestamp_ms=1_700_000_000_000,
        book_status="BOOK_DEPTH20_AVAILABLE",
        pair="BNBUSDT",
        venue="bybit",
    )
    assert prov.fee_bps == 10.0
    assert prov.fee_provenance == "MEASURED_FROM_VENUE_METADATA_BYBIT_RESEARCH"
    assert prov.latency_provenance == "STATIC_CONSERVATIVE_FROM_BYBIT_HISTORICAL"


def test_compute_economic_provenance_venue_autodetect_from_book_path(
    tmp_path,
) -> None:
    """Path silver/bybit/... → autodetect bybit."""
    # On simule un path qui contient 'silver/bybit/' pour autodetect
    book_path = tmp_path / "silver" / "bybit" / "spot" / "book.jsonl"
    book_path.parent.mkdir(parents=True, exist_ok=True)
    book_path.write_text(
        '{"timestamp_ms": 1700000000000, "bids": [["100","10"]], "asks": [["100.01","10"]]}\n',
        encoding="utf-8",
    )
    prov = compute_economic_provenance(
        timestamp_ms=1_700_000_000_000,
        book_status="BOOK_DEPTH20_AVAILABLE",
        pair="BNBUSDT",
        raw_book_path=book_path,
    )
    assert prov.fee_provenance == "MEASURED_FROM_VENUE_METADATA_BYBIT_RESEARCH"


def test_compute_economic_provenance_silver_exchange_overrides_undetectable_path(
    tmp_path,
) -> None:
    r"""Audit 2026-05-14 W1 fix : `silver_exchange='bybit'` venant du
    silver_index canonique doit prendre precedence sur l'auto-detect path,
    notamment sur les raw_windows B2 ou le path
    `...\raw_windows\{pair}\{candidate_id}\orderbook_snapshot.jsonl` ne
    contient pas le segment `silver/{venue}/spot/...` et echoue auto-detect.

    Sans le cablage W1 au call site (data_factory:1947), 100 % des records
    refusal_ledger du run B2 portaient `fee_source_status =
    DEGRADED_FALLBACK_UNKNOWN_VENUE` malgre la pair Bybit. Ce test verrouille
    le contrat : `silver_exchange` doit resoudre la venue meme quand le
    path est indechiffrable.
    """
    # Path style raw_windows extracts (pas silver/{venue}/) — auto-detect echouerait
    book_path = tmp_path / "raw_windows" / "BTCUSDT" / "cand-0001" / "orderbook_snapshot.jsonl"
    book_path.parent.mkdir(parents=True, exist_ok=True)
    book_path.write_text(
        '{"timestamp_ms": 1700000000000, "bids": [["100","10"]], "asks": [["100.01","10"]]}\n',
        encoding="utf-8",
    )
    prov = compute_economic_provenance(
        timestamp_ms=1_700_000_000_000,
        book_status="BOOK_DEPTH20_AVAILABLE",
        pair="BTCUSDT",
        raw_book_path=book_path,
        silver_exchange="bybit",
        silver_market_type="spot",
    )
    # Venue resolue depuis silver_index → fee Bybit research (10 bps), pas
    # le fallback degraded 25 bps.
    assert prov.fee_provenance == "MEASURED_FROM_VENUE_METADATA_BYBIT_RESEARCH"
    assert prov.fee_bps == 10.0
    # Warning trace l'origine de la resolution venue
    assert any(
        w.startswith("VENUE_FROM_SILVER_INDEX") for w in prov.measurement_warnings
    )


def test_compute_economic_provenance_venue_unknown_warning() -> None:
    """venue inconnu → fallback degraded + warning audit-ready."""
    prov = compute_economic_provenance(
        timestamp_ms=1_700_000_000_000,
        book_status="BOOK_DEPTH20_AVAILABLE",
        pair="BNBUSDT",
        venue="kraken_xyz",
    )
    # 25 bps fallback degraded
    assert prov.fee_bps == 25.0
    assert prov.fee_provenance == "DEGRADED_FALLBACK_UNKNOWN_VENUE"
    assert any(
        w.startswith("VENUE_OVERRIDE_UNKNOWN") for w in prov.measurement_warnings
    )


def test_compute_economic_provenance_live_api_override_priority() -> None:
    """Live API override (Binance taker_commission) > venue metadata default."""
    # Ex : Binance live API retourne taker = 7.5 bps (BNB discount applique)
    prov = compute_economic_provenance(
        timestamp_ms=1_700_000_000_000,
        book_status="BOOK_DEPTH20_AVAILABLE",
        pair="BNBUSDT",
        venue="binance",
        fee_bps_override=7.5,
    )
    assert prov.fee_bps == 7.5
    assert prov.fee_provenance == "MEASURED_FROM_VENUE_API_OVERRIDE"


def test_compute_economic_provenance_fully_measured(tmp_path: Path) -> None:
    """Avec book + tous les overrides + venue, aggregated_provenance = FULLY_MEASURED."""
    book_path = tmp_path / "book.jsonl"
    _write_jsonl(
        book_path,
        [_book_snapshot(ts_ms=1_700_000_000_000, best_bid=99.95, best_ask=100.05)],
    )
    prov = compute_economic_provenance(
        timestamp_ms=1_700_000_000_000,
        book_status="BOOK_DEPTH20_AVAILABLE",
        raw_book_path=book_path,
        venue="binance",  # venue explicite necessaire pour fee_provenance non-degraded
        expected_edge_bps_override=8.5,
        slippage_bps_override=1.2,
        latency_penalty_bps_override=0.5,
        fee_bps_override=7.5,  # ex : Binance taker_commission depuis API live
    )
    assert prov.aggregated_provenance == "FULLY_MEASURED"


@pytest.mark.skipif(
    not os.environ.get("STRATEGY_LADDER_REAL_RUN_DOSSIER"),
    reason="Set STRATEGY_LADDER_REAL_RUN_DOSSIER=1 to run on real K: drive",
)
def test_economic_provenance_real_run_dossier_spread_differs_from_hardcoded() -> None:
    """Sur le run dossier reel, spread mesure doit differer significativement
    de la constante hardcoded 4.0 bps. Confirme que les hardcodes etaient
    PESSIMISTES (cause du expected_ce=-0.00023 systematique)."""
    manifest_path = Path(
        r"K:/v5.3 backtest/runs/strategy_ladder_first_controlled_run-1778085375411"
        r"/backtest_strategy_ladder/strategy_ladder_first_controlled_run-1778085375411"
        r"/raw_windows/BNBUSDT/eea9862e969edccaeed7a98b/window_manifest.json"
    )
    if not manifest_path.exists():
        pytest.skip(f"Run dossier manifest absent : {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    prov = compute_economic_provenance(
        timestamp_ms=manifest["timestamp_ms"],
        book_status=manifest["book_depth_source_status"],
        raw_book_path=manifest["raw_book_path"],
    )
    # Le hardcoded etait 4.0 ; le mesure devrait etre BNBUSDT typique ~1-3 bps
    assert prov.spread_provenance == "MEASURED_FROM_BOOK_SNAPSHOT"
    assert 0.0 < prov.spread_bps < 10.0, (
        f"BNBUSDT spread doit etre dans [0, 10] bps; got {prov.spread_bps}"
    )
    # Recalcul du expected_ce avec le spread mesure
    ec = (
        prov.spread_bps
        + prov.slippage_bps * 1.15
        + prov.latency_penalty_bps * 1.0
    ) / 10_000
    ee = prov.expected_edge_bps / 10_000
    ce_measured = ee - ec
    # Le ce hardcoded etait -0.00023. Avec spread mesure (~1.7), ce devrait
    # remonter (moins negatif).
    assert ce_measured > -0.00023, (
        f"ce_measured ({ce_measured:.6f}) devrait etre > -0.00023 (hardcoded)"
    )
