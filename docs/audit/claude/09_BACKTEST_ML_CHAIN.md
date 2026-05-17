# Chaîne backtest + ML — flow réel + outputs + gap (selon code source)

**Date** : 2026-05-07
**Sources de vérité** :
- `src/local_replay_runtime/strategy_ladder_runner.py:run_backtest_strategy_ladder` (entry point ligne 1173)
- `src/calibration_methods/ml_trainer.py:train_lightgbm_ml_artifact` (trainer ligne 353)
- `src/complete_enablers/ml_confidence_enabler.py:_predict_probability` (predict pattern ligne 97)
- `src/complete_enablers/regime_detector_runtime.py:_predict_regime_signal` (predict pattern ligne 154)
- `src/local_replay_runtime/strategy_ladder_edge_model_provider.py` (edge model actuel — proxy)

## Section 1 — Chaîne backtest end-to-end (état actuel)

### 1.1 Entry point CLI
**Fichier** : `scripts/run_backtest_strategy_ladder.py:108`
```python
from local_replay_runtime.strategy_ladder_runner import run_backtest_strategy_ladder
result = run_backtest_strategy_ladder(request)
```

### 1.2 Pipeline orchestrator
**Fichier** : `src/local_replay_runtime/strategy_ladder_runner.py:1173`
```python
def run_backtest_strategy_ladder(
    request: StrategyLadderRequest,
    *,
    progress_callback: StrategyLadderProgressCallback | None = None,
) -> StrategyLadderRunResult:
    """Execute the canonical Strategy Ladder pipeline end to end."""
```

### 1.3 Stages (lignes du runner avec contenu)

| Stage | Ligne | Module | Output |
|---|---|---|---|
| **Stage 0 — Setup** | 1180-1188 | `request.run_dir` | crée `run_dir/{fast_candidates,raw_windows,detailed_replay,capital_profiles,reports}` |
| **Stage 1 — Data factory resolution** | 1191-1230 | `_resolve_data_factory_payloads` | charge `data_factory_manifest.json`, `raw_source_report.json`, `pair_universe_report.json`, `data_quality_report.json`, `gold_feature_manifest.json`, `silver_index.json` |
| **Stage 2 — Feature store load** | 1232-1239 | `load_strategy_ladder_feature_store` | `FeatureStoreResult.rows: tuple[StrategyLadderFeatureRow, ...]` lu depuis `gold/features_5m/{pair}/{date}.jsonl` |
| **Stage 3 — Candidate discovery** | 1259-1262 | `discover_strategy_ladder_candidates` | itère `for engine_id in row.resolved_engine_ids` → 1 candidat par row × 4 engines, label `COMPAT_FEATURE_DISCOVERY` |
| **Stage 3b — Candidate export** | 1264-1271 | `export_strategy_ladder_candidates` | écrit `fast_candidates/candidate_events.jsonl` |
| **Stage 4 — Raw window extraction** | ~1340-1430 | `extract_strategy_ladder_raw_windows` | écrit `raw_windows/{pair}/{candidate_id}/window_manifest.json` avec `raw_trade_path`, `raw_book_path`, `raw_book_delta_path`, `raw_ohlcv_path` |
| **Stage 5 — Detailed replay** | ~1450-1470 | `run_strategy_ladder_detailed_replay` | invoque `simulate_shadow_compatible_dtrs(dataset)` pour chaque (candidat, capital_bucket) → `detailed_replay/{candidate_id}.json` + `by_bucket/{bucket}/{candidate_id}.json` |
| **Stage 5b — Engine native bridge sample** | 1535 | `_invoke_engine_native_bridges_sample` | si `request.engine_native_mode=True`, invoque les 4 builders engine sur sample (default 10 candidats) |
| **Stage 6 — Capital profiles** | ~1480 | `_capital_profile_for_bucket` | écrit `capital_profiles/{bucket}.json` |
| **Stage 7 — Promotion artifacts** | ~1490 | `_write_promotion_payloads` | écrit `engine_promotion/`, `pair_promotion/`, `strategy_promotion/`, `sample_size_survival/` |
| **Stage 8 — Final manifest** | 1518-1599 | `StrategyLadderRunManifest(...)` | écrit `run_manifest.json` avec `final_status`, `executed_trade_count`, `economic_constants_provenance`, `engine_native_status`, etc. |
| **Stage 9 — Reports** | ~1600 | `_write_reports` | écrit `reports/strategy_ladder_summary.json` |

### 1.4 Path data flow réel

```
Raw exchange data (Bybit historical csv.gz)
    ↓ data_factory (silver/gold transformation)
silver/bybit/spot/
├── trades/{pair}/{date}.jsonl
├── orderbook_snapshot/{pair}/{date}.jsonl     (~2 snapshots/jour)
├── orderbook_delta/{pair}/{date}.jsonl        (~191k deltas/jour)
└── ohlcv/{tf}/{pair}/{date}.jsonl

gold/features_5m/{pair}/{date}.jsonl
└── StrategyLadderFeatureRow (4 features OHLCV bruts)

    ↓ runner
backtest_strategy_ladder/{run_id}/
├── fast_candidates/candidate_events.jsonl     (15460 candidates COMPAT_FEATURE_DISCOVERY)
├── raw_windows/{pair}/{candidate_id}/window_manifest.json
├── detailed_replay/{candidate_id}.json
├── detailed_replay/by_bucket/{400|500|1500|4000}/{candidate_id}.json
├── trade_detail_ledger.jsonl                  (0 lignes actuellement)
├── refusal_ledger.jsonl                       (61840 lignes economically_absurd)
├── capital_profiles/{bucket}.json
├── engine_promotion/engine_{a|b|c|d}/{run_id}.json
├── pair_promotion/{pair}/{run_id}.json
├── strategy_promotion/{strategy_id}/{run_id}.json
├── sample_size_survival/{scope}/{id}/{run_id}.json
├── reports/strategy_ladder_summary.json
└── run_manifest.json
```

### 1.5 Status final actuel sur run dossier `1778085375411`

```json
{
  "final_status": "BACKTEST_PROOF_BLOCKED",
  "executed_trade_count": 0,                         // 0 trade
  "candidate_count": 15460,
  "candidate_engine_native_count": 0,                // proxy COMPAT_FEATURE_DISCOVERY
  "candidate_proxy_count": 15460,
  "detailed_replay_count": 61840,                    // 15460 × 4 buckets
  "economic_constants_provenance": "HARDCODED_PROXY_CONSTANTS",
  "engine_native_status": "ENGINE_NATIVE_NOT_REQUESTED",
  "blocker_codes": [..., "NO_EXECUTED_TRADES"]
}
```

Tous les 61840 records detailed_replay refusent avec :
```json
{
  "execution_state": "phantom",
  "fill_status": "FILL_REALISM_MODEL_ONLY",
  "fee_source_status": "FEE_SOURCE_NOT_PROVEN",
  "cost_parity_status": "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
  "reason_codes": ["economically_absurd"]
}
```

---

## Section 2 — Pipeline ML (état actuel offline)

### 2.1 ML Trainer (offline, isolé du runtime backtest)
**Fichier** : `src/calibration_methods/ml_trainer.py:353`

```python
def train_lightgbm_ml_artifact(request: MlTrainerRequest) -> MlTrainerResult:
    """Train a deterministic Local-Lab-only LightGBM model and emit its artifact."""
    feature_names = _resolve_feature_names(request.rows)
    train_rows, validation_rows, train_window, validation_window = _split_walk_forward(...)
    best_params, optuna_trials_used = _resolve_best_params(...)  # Optuna HPO
    booster = _train_booster(lightgbm, params=best_params, ...)
    artifact = MlModelArtifact.create(
        model_family="lightgbm",
        feature_names=feature_names,
        oos_sharpe=_strategy_sharpe(validation_predictions, validation_targets),
        backtest_sharpe=_strategy_sharpe(train_predictions, train_targets),
        ks_test_features_pvalue=_evaluate_feature_drift(...),
        model_bytes_b64=base64.b64encode(booster.model_to_string().encode("utf-8")).decode("ascii"),
        ...
    )
    return MlTrainerResult(artifact=artifact, ...)
```

**Best practices vérifiées** :
- Walk-forward causal (pas de leakage)
- Bayesian bagging (bootstrap deterministic)
- Sharpe metric (pas MSE in-sample)
- KS-test feature drift detection
- Optuna HPO bornée
- 4 seeds LightGBM propagés
- Artifact serialized (model_bytes_b64) audit-ready

### 2.2 Artifact Pydantic — `MlModelArtifact`
**Fichier** : `src/interface_contracts/ml_model_artifact.py:56`

```python
class MlModelArtifact(BaseModel, frozen=True):
    artifact_hash: str
    model_family: str = "lightgbm"
    feature_names: tuple[str, ...]
    feature_hash: str
    pair_universe: tuple[str, ...]
    train_window: MlModelWindow
    validation_window: MlModelWindow
    oos_sharpe: float
    backtest_sharpe: float
    ks_test_features_pvalue: float
    shadow_diff_pct: float | None = None
    training_seed: int
    created_at: datetime
    calibration_version: str
    dataset_hash: str
    model_bytes_b64: str | None = None        # ← serialized booster
    model_path_ref: str | None = None
    shap_summary_ref: str | None = None
    training_metrics: dict
    drift_baseline: MlModelDriftBaseline
    stale_after: datetime
```

### 2.3 Pattern predict EXISTANT (mais non utilisé pour edge_bps)
**Fichier** : `src/complete_enablers/ml_confidence_enabler.py:97`

```python
def _predict_probability(artifact: MlModelArtifact, feature_values: dict[str, float]) -> float:
    lightgbm = _load_lightgbm_module()
    if lightgbm is None:
        raise ValueError("lightgbm_unavailable")
    model_string = _decode_model_string(artifact)  # base64 decode → utf-8
    if model_string is None and artifact.model_path_ref is None:
        raise ValueError("model_payload_missing")
    booster_kwargs: dict[str, Any] = {}
    if model_string is not None:
        booster_kwargs["model_str"] = model_string
    elif artifact.model_path_ref is not None:
        booster_kwargs["model_file"] = artifact.model_path_ref
    booster = lightgbm.Booster(**booster_kwargs)
    probability = float(booster.predict([_feature_vector(feature_values, artifact)])[0])
    return min(1.0, max(0.0, probability))
```

C'est **EXACTEMENT** le pattern qu'il faut réutiliser pour edge_bps. La fonction `MlConfidenceEnabler.score_candidate(...)` (ligne 130) montre l'usage runtime complet :
- Si artifact None → fallback neutre (`ml_confidence=0.5`, `MISSING`)
- Si artifact stale → fallback neutre (`STALE`)
- Si predict fail → fallback neutre (`INVALID`)
- Sinon → `ACTIVE` avec `ml_confidence` clipped [0, 1]

### 2.4 Path data ML actuel

```
Local Lab (offline historical):
silver/bybit/spot/...
    ↓
local_lab_ml_artifact_training.py
    ↓
ml_trainer.train_lightgbm_ml_artifact(request)
    ↓
MlModelArtifact (with model_bytes_b64)
    ↓
serialized to disk (calibration_version dir)
    ↓
CalibrationLoader.load(version) → CalibrationArtifactCollection
    ↓
**GAP** : aucun consommateur runtime backtest charge MlModelArtifact pour predict edge_bps
```

---

## Section 3 — Mon module actuel `strategy_ladder_edge_model_provider.py`

**Fichier** : `src/local_replay_runtime/strategy_ladder_edge_model_provider.py:119` (livré session 2026-05-07)

### Implémentation actuelle (PROXY)
```python
def estimate_forward_return_edge_bps(
    *,
    raw_ohlcv_path: Path | str | None,
    timestamp_ms: int,
    lookback_ms: int = 60 * 60 * 1000,  # 1h
    min_bars: int = 5,
) -> EdgeEstimate:
    # ... charge bars OHLCV causal (≤ timestamp_ms) ...
    # ... calcule forward_returns = (close[i+1] - close[i]) / close[i] ...
    abs_forward_returns = sorted(abs(fr) for fr in forward_returns)
    median_abs = abs_forward_returns[n // 2]
    edge_bps = median_abs * 10_000.0
    return EdgeEstimate(
        edge_bps=edge_bps,
        provenance="MEASURED_FROM_FORWARD_RETURN_MEDIAN_TO_CALIBRATE",
        ...
    )
```

### Pourquoi c'est un PROXY (pas production)
- **Pas de conditioning** : utilise tous les bars du lookback sans filtrage par regime / signal direction / breakout context
- **Pas de feature engineering** : juste `|forward_return|` median
- **Pas calibré** : le seuil "median" est arbitraire vs un quantile calibré
- **Provenance flag** `_TO_CALIBRATE` indique explicitement que ce n'est pas la version production

### Comment c'est utilisé actuellement
**Fichier** : `src/local_replay_runtime/strategy_ladder_economic_provenance.py:181-200`
```python
# 2. EXPECTED EDGE — forward return median rolling
elif raw_ohlcv_path is not None:
    edge_estimate = estimate_forward_return_edge_bps(
        raw_ohlcv_path=raw_ohlcv_path,
        timestamp_ms=timestamp_ms,
        lookback_ms=edge_lookback_ms,
    )
    if edge_estimate.detector_status == "MEASURED":
        # ... clamp avec bounds pair ...
        expected_edge_bps = clamped
        expected_edge_provenance = edge_estimate.provenance
```

→ Le proxy retourne ~6 bps sur le run dossier réel BNBUSDT, totalement insuffisant face au cost réel mesuré ~13-15 bps. **D'où 0 trade exécuté.**

---

## Section 4 — GAP précis : ML predict pas câblé dans backtest

### 4.1 Qui consomme `MlModelArtifact` dans le code source ?

```bash
grep -rln "MlModelArtifact" src/ | grep -v __pycache__
```

| Module | Usage |
|---|---|
| `src/calibration_methods/ml_trainer.py` | **Crée** l'artifact (offline trainer) |
| `src/interface_contracts/ml_model_artifact.py` | **Définition** du modèle Pydantic |
| `src/interface_contracts/ml_model_transport_contracts.py` | Transport supplementary refs |
| `src/backtest_artifact_import/ml_model_transport.py` | Validate / transport |
| `src/complete_enablers/ml_confidence_enabler.py` | **Predict** (mais pour `ml_confidence ∈ [0, 1]`, pas `edge_bps`) |
| `src/complete_enablers/ml_model_promotion_gate.py` | Promotion gate |
| `src/local_replay_runtime/local_lab_ml_artifact_training.py` | Training orchestrator local lab |
| `src/local_replay_runtime/ml_final_audit_report.py` | Audit report compiler |

### 4.2 Diagnostic du gap

✅ **CE QUI EXISTE** :
- Trainer offline LightGBM avec walk-forward + bagging + Optuna (`ml_trainer.py`)
- Artifact serializable + Pydantic frozen (`MlModelArtifact`)
- Pattern predict runtime déjà câblé pour `ml_confidence` (`ml_confidence_enabler.py`)
- Calibration loader + signature artifacts (`calibration_loader/loader.py`)

❌ **CE QUI MANQUE** :
1. **Aucun consommateur runtime du `MlModelArtifact` pour predict `edge_bps`** dans le pipeline backtest
2. `strategy_ladder_edge_model_provider.py` (mon module) utilise un proxy `forward_return_median` au lieu de `ml_artifact.predict()`
3. Pas de wiring entre `CalibrationLoader.load(version)` et `compute_economic_provenance(...)`
4. Pas de feature builder ex-ante qui produit le `feature_values: dict[str, float]` attendu par `MlModelArtifact.feature_names`

### 4.3 Conséquence

Sur le run dossier réel :
- `expected_edge_bps_provenance = "MEASURED_FROM_FORWARD_RETURN_MEDIAN_TO_CALIBRATE"`
- `expected_edge_bps ≈ 6.0` (mediane abs des forward returns)
- `total_cost ≈ 15.8 bps` (réalité mesurée)
- → `economically_absurd` → `phantom` → 0 trade

Pour qu'un trade s'exécute, il faut un edge > 16 bps **conditionnellement au setup** (breakout + microstructure). Un proxy median ne peut pas donner ça par construction.

---

## Section 5 — Sprint 1 priorité haute (DÉTAILLÉ)

### 5.1 Objectif
Remplacer dans `strategy_ladder_edge_model_provider.py` le proxy `forward_return_median` par `ml_artifact.predict()` en réutilisant le pattern existant de `ml_confidence_enabler.py`.

### 5.2 Architecture cible

```
strategy_ladder_economic_provenance.compute_economic_provenance(...)
    ↓ (au stade EXPECTED EDGE)
strategy_ladder_edge_model_provider.estimate_edge_bps_from_artifact(
    artifact: MlModelArtifact,
    raw_window_paths: { trade, book, ohlcv },
    timestamp_ms: int,
)
    ↓
1. _build_feature_vector_at_timestamp(...)
    → utilise les mêmes features que le trainer (causal, ≤ timestamp_ms)
    → ordre conforme à artifact.feature_names
    ↓
2. _predict_edge_bps(artifact, features)
    → réutilise le pattern de ml_confidence_enabler._predict_probability
    → booster = lightgbm.Booster(model_str=base64.b64decode(artifact.model_bytes_b64))
    → raw_prediction = booster.predict([feature_vector])[0]
    → edge_bps = raw_prediction × 10000  (si target était en raw return) OR direct si target en bps
    ↓
3. EdgeEstimate(
    edge_bps=edge_bps,
    provenance="MEASURED_FROM_LIGHTGBM_MODEL",
    artifact_hash=artifact.artifact_hash,
    artifact_status="ACTIVE" | "STALE" | "MISSING" | "INVALID",
    ...
)
```

### 5.3 Code à écrire (squelette)

#### 5.3.1 Nouveau module helper
**Fichier** : `src/local_replay_runtime/strategy_ladder_edge_model_provider.py` (extension du module existant)

```python
# -- AJOUTS À FAIRE -- #

import base64
from datetime import datetime, UTC
from typing import Any

from interface_contracts.ml_model_artifact import MlModelArtifact


def _load_lightgbm_module() -> Any:
    """Reuse pattern from ml_confidence_enabler._load_lightgbm_module."""
    try:
        import lightgbm  # type: ignore
        return lightgbm
    except ImportError:
        return None


def _decode_model_string(artifact: MlModelArtifact) -> str | None:
    """Reuse pattern from ml_confidence_enabler._decode_model_string."""
    if artifact.model_bytes_b64 is None:
        return None
    return base64.b64decode(artifact.model_bytes_b64.encode("ascii")).decode("utf-8")


def _is_artifact_stale(artifact: MlModelArtifact, as_of: datetime | None) -> bool:
    """Reuse pattern from ml_confidence_enabler._is_stale."""
    if artifact.stale_after is None:
        return False
    comparison_time = as_of or datetime.now(tz=UTC)
    if comparison_time.tzinfo is None:
        comparison_time = comparison_time.replace(tzinfo=UTC)
    return comparison_time > artifact.stale_after


def _build_feature_vector_at_timestamp(
    *,
    feature_names: tuple[str, ...],
    raw_window_paths: dict[str, Path | str | None],
    timestamp_ms: int,
    lookback_ms: int = 60 * 60 * 1000,
) -> dict[str, float]:
    """Build feature dict matching the trainer's feature_names.

    CRITICAL : doit utiliser les MEMES features que le trainer (causal,
    ≤ timestamp_ms). Si le trainer utilisait par exemple :
      - rolling_volatility_5m
      - cumulative_ofi_1h
      - vpin_current
      - kyle_lambda
      - book_imbalance_top5
      - ...

    On doit reproduire EXACTEMENT ces features ex-ante.
    """
    features: dict[str, float] = {}
    for name in feature_names:
        # 1. Map feature_name → computation strategy
        # 2. Charger raw window data appropriée (trade / book / ohlcv)
        # 3. Calculer le feature au timestamp_ms (causal)
        # ... (à implémenter selon les feature_names du trainer)
        features[name] = compute_feature_at_t(name, raw_window_paths, timestamp_ms)
    return features


def estimate_edge_bps_from_artifact(
    *,
    artifact: MlModelArtifact | None,
    raw_window_paths: dict[str, Path | str | None],
    timestamp_ms: int,
    as_of: datetime | None = None,
) -> EdgeEstimate:
    """Predict edge_bps via LightGBM artifact (replaces forward_return_median proxy).

    Reuse pattern de ml_confidence_enabler with proper fallbacks.
    """
    # Tier 3 fallbacks if artifact unavailable / stale / invalid
    if artifact is None:
        return EdgeEstimate(
            edge_bps=0.0,
            provenance="DEFAULT_TO_CALIBRATE",
            n_lookback_bars_used=0,
            median_abs_forward_return=0.0,
            detector_status="ML_ARTIFACT_MISSING",
            warnings=("ML_ARTIFACT_MISSING_USING_FALLBACK",),
        )
    if _is_artifact_stale(artifact, as_of):
        return EdgeEstimate(
            edge_bps=0.0,
            provenance="DEFAULT_TO_CALIBRATE",
            n_lookback_bars_used=0,
            median_abs_forward_return=0.0,
            detector_status="ML_ARTIFACT_STALE",
            warnings=(f"ML_ARTIFACT_STALE_AFTER:{artifact.stale_after.isoformat()}",),
        )

    lightgbm = _load_lightgbm_module()
    if lightgbm is None:
        return EdgeEstimate(
            edge_bps=0.0,
            provenance="DEFAULT_TO_CALIBRATE",
            n_lookback_bars_used=0,
            median_abs_forward_return=0.0,
            detector_status="LIGHTGBM_UNAVAILABLE",
            warnings=("LIGHTGBM_UNAVAILABLE_USING_FALLBACK",),
        )

    model_string = _decode_model_string(artifact)
    if model_string is None and artifact.model_path_ref is None:
        return EdgeEstimate(
            edge_bps=0.0,
            provenance="DEFAULT_TO_CALIBRATE",
            n_lookback_bars_used=0,
            median_abs_forward_return=0.0,
            detector_status="ML_MODEL_PAYLOAD_MISSING",
            warnings=("ML_MODEL_PAYLOAD_MISSING",),
        )

    # Build features ex-ante (causal at timestamp_ms)
    try:
        features = _build_feature_vector_at_timestamp(
            feature_names=artifact.feature_names,
            raw_window_paths=raw_window_paths,
            timestamp_ms=timestamp_ms,
        )
    except Exception as exc:
        return EdgeEstimate(
            edge_bps=0.0,
            provenance="DEFAULT_TO_CALIBRATE",
            n_lookback_bars_used=0,
            median_abs_forward_return=0.0,
            detector_status=f"FEATURE_BUILD_FAILED:{type(exc).__name__}",
            warnings=(f"FEATURE_BUILD_FAILED:{exc}",),
        )

    # Predict
    booster_kwargs = {}
    if model_string is not None:
        booster_kwargs["model_str"] = model_string
    elif artifact.model_path_ref is not None:
        booster_kwargs["model_file"] = artifact.model_path_ref
    try:
        booster = lightgbm.Booster(**booster_kwargs)
        feature_vector = [features[name] for name in artifact.feature_names]
        raw_prediction = float(booster.predict([feature_vector])[0])
    except Exception as exc:
        return EdgeEstimate(
            edge_bps=0.0,
            provenance="DEFAULT_TO_CALIBRATE",
            n_lookback_bars_used=0,
            median_abs_forward_return=0.0,
            detector_status=f"LIGHTGBM_PREDICT_FAILED:{type(exc).__name__}",
            warnings=(f"LIGHTGBM_PREDICT_FAILED:{exc}",),
        )

    # Convert prediction to bps (depends on training target convention)
    # Si target trainer était en raw_return (ex: 0.001 = 10 bps), multiplier par 10000
    # Si target était déjà en bps, prendre tel quel
    edge_bps = raw_prediction * 10_000.0  # à ajuster selon convention training
    edge_bps = max(0.0, edge_bps)  # clamp non-negative

    return EdgeEstimate(
        edge_bps=edge_bps,
        provenance="MEASURED_FROM_LIGHTGBM_MODEL",
        n_lookback_bars_used=0,  # not used in ML mode
        median_abs_forward_return=0.0,
        detector_status="MEASURED_LIGHTGBM",
        warnings=(f"ML_ARTIFACT_HASH:{artifact.artifact_hash}",),
    )
```

#### 5.3.2 Wirer dans `strategy_ladder_economic_provenance.compute_economic_provenance(...)`

Ajouter un nouveau paramètre :
```python
def compute_economic_provenance(
    *,
    timestamp_ms: int,
    book_status: str,
    pair: str = "",
    raw_book_path: Path | str | None = None,
    raw_trade_path: Path | str | None = None,
    raw_ohlcv_path: Path | str | None = None,
    expected_edge_bps_override: float | None = None,
    # ... autres params ...
    ml_edge_artifact: MlModelArtifact | None = None,  # NEW
    as_of: datetime | None = None,                     # NEW
) -> EconomicProvenance:
    ...
    # Section 2 (EXPECTED EDGE) — préférer ML artifact si fourni
    if expected_edge_bps_override is not None:
        # ... existant ...
    elif ml_edge_artifact is not None:
        edge_estimate = estimate_edge_bps_from_artifact(
            artifact=ml_edge_artifact,
            raw_window_paths={
                "trade": raw_trade_path,
                "book": raw_book_path,
                "ohlcv": raw_ohlcv_path,
            },
            timestamp_ms=timestamp_ms,
            as_of=as_of,
        )
        if edge_estimate.detector_status == "MEASURED_LIGHTGBM":
            # apply pair bounds
            expected_edge_bps, w, _ = clamp_with_warning(
                edge_estimate.edge_bps,
                field_name="edge_bps",
                pair=pair,
                bounds=bounds.edge_bps,
                reject_threshold=bounds.reject_threshold_multiplier,
            )
            if w:
                warnings.append(w)
            expected_edge_provenance = "MEASURED_FROM_LIGHTGBM_MODEL"
        else:
            # Fallback to forward_return_median proxy
            warnings.append(f"ML_FALLBACK:{edge_estimate.detector_status}")
            # ... existant forward_return_median ...
    elif raw_ohlcv_path is not None:
        # ... existant forward_return_median proxy ...
    else:
        # ... existant DEFAULT_TO_CALIBRATE ...
```

#### 5.3.3 Wirer dans le runner backtest

**Fichier** : `src/local_replay_runtime/strategy_ladder_runner.py:run_backtest_strategy_ladder`

Ajouter au début du runner :
```python
# Charger l'artifact ML si calibration_version fournie dans request
ml_edge_artifact: MlModelArtifact | None = None
if request.ml_mode == "ML_MODE_OVERLAY_FROZEN" and request.frozen_ml_artifact_path:
    try:
        artifact_payload = json.loads(
            Path(request.frozen_ml_artifact_path).read_text(encoding="utf-8")
        )
        candidate_artifact = MlModelArtifact.model_validate(artifact_payload)
        # Verify hash if provided
        if request.frozen_ml_artifact_hash:
            assert candidate_artifact.artifact_hash == request.frozen_ml_artifact_hash, (
                "frozen_ml_artifact_hash mismatch — artifact may be tampered"
            )
        ml_edge_artifact = candidate_artifact
    except Exception as exc:
        # log + fallback
        ml_edge_artifact = None
```

Et passer `ml_edge_artifact` à `compute_economic_provenance(...)` dans le data_factory + bridges.

### 5.4 Tests pytest à ajouter

`tests/test_local_replay_runtime/test_strategy_ladder_edge_model_provider.py` :

```python
def test_estimate_edge_bps_from_artifact_returns_lightgbm_prediction(tmp_path):
    """Avec un artifact LightGBM valide, edge_bps vient du booster predict."""
    # 1. Train un mini-LightGBM sur des données synthétiques (rows avec target=10 bps)
    # 2. Build le MlModelArtifact
    # 3. Call estimate_edge_bps_from_artifact(...) avec raw_paths synthetic
    # 4. Assert edge_bps ~ 10.0 bps (pas le proxy 0.0/forward_return_median)
    # 5. Assert detector_status == "MEASURED_LIGHTGBM"
    # 6. Assert provenance == "MEASURED_FROM_LIGHTGBM_MODEL"
    ...

def test_estimate_edge_bps_from_artifact_falls_back_when_stale(tmp_path):
    """Avec un artifact dont stale_after < now, fallback DEFAULT_TO_CALIBRATE."""
    ...

def test_estimate_edge_bps_from_artifact_falls_back_when_lightgbm_unavailable(tmp_path):
    """Mock _load_lightgbm_module → None, fallback proxy."""
    ...

def test_estimate_edge_bps_from_artifact_falls_back_when_features_missing(tmp_path):
    """Si _build_feature_vector raise, fallback DEFAULT_TO_CALIBRATE."""
    ...

def test_compute_economic_provenance_uses_ml_artifact_if_provided(tmp_path):
    """Wiring end-to-end : artifact fourni → MEASURED_FROM_LIGHTGBM_MODEL."""
    ...
```

### 5.5 Estimation effort Sprint 1

| Tâche | Effort | Dépendances |
|---|---|---|
| 5.5.1 — `_load_lightgbm_module` + `_decode_model_string` + `_is_artifact_stale` (refactor de `ml_confidence_enabler` en util commun) | 1h | aucune |
| 5.5.2 — `_build_feature_vector_at_timestamp` (mapping feature_name → computation au timestamp_ms causal) | 4-6h | dépend des feature_names du trainer |
| 5.5.3 — `estimate_edge_bps_from_artifact` avec fallbacks Tier 3 | 2h | 5.5.1 + 5.5.2 |
| 5.5.4 — Wiring dans `compute_economic_provenance` (param `ml_edge_artifact`) | 1h | 5.5.3 |
| 5.5.5 — Wiring dans `run_backtest_strategy_ladder` (load artifact depuis request.frozen_ml_artifact_path) | 1h | 5.5.4 |
| 5.5.6 — Tests pytest (5 cas minimum) | 3h | 5.5.5 |
| 5.5.7 — Run sur run dossier réel + verif edge_bps prédit > 16 bps sur setup pertinent | 1h | 5.5.6 |
| 5.5.8 — Doc + memory drawer | 30min | 5.5.7 |
| **Total** | **12-15h** | ≈ 2 jours dédiés |

### 5.6 Bloqueur critique : feature_names du trainer

Le code `_build_feature_vector_at_timestamp` doit reproduire EXACTEMENT les features utilisées par le trainer pour construire `MlModelArtifact.feature_names`. Cela demande :

1. **Audit des features actuelles** : quels noms exacts ?
   - Si le trainer utilise par exemple `["close_return_5m", "high_low_range_5m", "volume_5m", "trade_count_hint"]` (les 4 features actuels du gold feature store), c'est trivial → simple lookup dans le feature store
   - Si le trainer utilise des features dérivées (rolling vol, cumulative ofi, vpin, kyle lambda, etc.), il faut les reproduire causalement ex-ante

2. **Convention sur la cible** : qu'est-ce que le trainer prédit ?
   - `forward_return_5m` ? → `edge_bps = prediction * 10_000`
   - `forward_return_5m_normalized` ? → multiplier par σ historique
   - `prob_breakout` ? → ce n'est pas un edge directement, il faut une transformation

→ **Action préalable nécessaire** : auditer `local_lab_ml_artifact_training.py` pour comprendre la convention de target + features utilisée actuellement. Si la convention n'est pas claire, le sprint 1 doit inclure une définition de convention canonique.

---

## Section 6 — Synthèse exécutive

### Ce qui marche aujourd'hui dans la chaîne backtest
1. ✅ Data factory (silver/gold)
2. ✅ Feature store load
3. ✅ Candidate discovery (proxy COMPAT_FEATURE_DISCOVERY)
4. ✅ Raw window extraction (avec snapshot+deltas reconstruction livrée cette session)
5. ✅ Detailed replay (shadow simulator + Kyle/VPIN/OFI/RKV/QP)
6. ✅ Engine bridges A/B/C/D (livrés cette session, Pydantic-valide + run_engine_X invoqué)
7. ✅ Economic provenance service venue-aware (livré cette session)
8. ✅ Outputs : run_manifest, refusal_ledger, capital_profiles, etc.

### Ce qui ne marche pas (cause unique : edge_bps insuffisant)
- 0 trade exécuté → 0 Sharpe → promotion shadow impossible
- Cause : `expected_edge_bps ≈ 6` (proxy forward_return_median) vs `total_cost ≈ 15.8 bps` (mesures réelles)
- Solution : remplacer le proxy par `ml_artifact.predict()` (Sprint 1 ci-dessus)

### Ce qui existe pour ML mais n'est pas wiré
- ✅ `ml_trainer.train_lightgbm_ml_artifact` (offline trainer audit-ready)
- ✅ `MlModelArtifact` (Pydantic frozen + model_bytes_b64 serialized)
- ✅ Pattern `_predict_probability` dans `ml_confidence_enabler` (déjà câblé pour `ml_confidence`, pas pour `edge_bps`)
- ✅ `CalibrationLoader.load(version)` pour signed artifacts
- ❌ Aucun consumer runtime backtest qui charge `MlModelArtifact` pour predict `edge_bps`

### Verdict
Le système est **structurellement prêt** pour le ML edge. Il manque uniquement la **glu** : un nouveau path dans `strategy_ladder_edge_model_provider.py` qui réutilise le pattern de `ml_confidence_enabler.py` mais pour edge_bps. Le sprint 1 est circonscrit (~12-15h).

**Sans le wiring ML edge** : le backtest restera bloqué (0 trade) car les coûts réels mesurés (~15-16 bps) dépassent l'edge naïf (~6 bps).

**Avec le wiring ML edge** : à condition que le trainer offline produise un edge prédit calibré > coût (e.g. ≥ 18 bps sur setup premium), des trades s'exécuteront en backtest, les compteurs Sharpe / drawdown deviendront non-triviaux, et la promotion vers Shadow devient envisageable.
