# C1 Multi-Pair Training Doctrine — Documentation finale

**Date :** 2026-05-21
**Statut :** ✅ COMPLET — 4 sous-phases livrées (C1.3.A → C1.3.D), 89/89 tests PASS
**Quote user fondatrice :** *« passer au multipaire training dans ialab et backtest multipaire »* + *« le nom de la paire il peut etre mm xx ne hard code pas le nom de la paire : on code le processe la »*

---

## Résumé exécutif

V5.3 supporte maintenant le **training multi-pair** avec pair embedding categorical. L'admin choisit runtime quel subset de paires entraîner (1 à N), le système discovery filesystem, valide capability per pair, train 1 modèle LightGBM par timeframe (au lieu de N), inférence prend pair_name + features → expected_edge.

**Coexistence MP3 mono-pair atomic** : les deux APIs cohabitent — admin choisit selon besoin.

---

## Architecture data-driven (ZERO hardcoded pair name)

```
┌─────────────────────────────────────────────────────────────────┐
│  Admin runtime choice : pairs=("XYZ", "MMXX", "FUTURE_42")     │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│  StrategyLadderMultiPairExpectedEdgeTrainingRequest (C1.3.C)   │
│  - validator : pairs non-empty + dedupliqué + pair_id required │
│  - ZERO hardcode pair name in validators                        │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│  pair_capability_discovery (C1.3.A) — filesystem-driven        │
│  - discover_pair_capabilities(klines_root, trades_root, ...)   │
│  - filter_pairs_for_training(require_microstructure)           │
│  - reject pairs sans capability avec hints actionable           │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│  _build_multi_pair_pair_assignment (C1.3.C)                    │
│  - pair_to_id = sorted alphabetical (déterministe)             │
│  - pair_to_weight = inverse-frequency balance imbalance        │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│  build_multi_pair_training_rows (C1.3.C)                       │
│  - concat sorted by (pair_id, timestamp) déterministe          │
│  - inject pair_id float feature per row                         │
│  - sample_weights aligned with rows by index                    │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│  build_multi_pair_ml_trainer_request (C1.3.C → C1.3.B)         │
│  - MlTrainerRequest(categorical_feature_names=("pair_id",))    │
│  - sample_weights propagated (only if non-uniform)             │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│  train_lightgbm_ml_artifact + C1.3.B propagation chain         │
│  - walk-forward split aligne weights par row identity           │
│  - bagging sub-set weights per bag indices                      │
│  - LightGBM Dataset(categorical_feature=["pair_id"], weight=)  │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│  1 artifact : expected_edge_multipair_<tf>.lgb (covers N pairs)│
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│  Inference (C1.3.D)                                             │
│  - load_multi_pair_inference_artifact(path, encoding, features) │
│  - predict_expected_edge_for_pair(artifact, pair, features)     │
│  - predict_expected_edge_batch (perf optimization)              │
│  - fail-close si pair unknown OU features incomplets            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Code C1 livré (4 sous-phases, ~530 lignes total)

| Sous-phase | Module | Lignes | Tests |
|---|---|---|---|
| **C1.3.A** | `pair_capability_discovery.py` (nouveau) | ~170 | 10 |
| **C1.3.B** | `ml_trainer.py` (étendu) | ~80 | 7 |
| **C1.3.C** | `strategy_ladder_multi_pair_expected_edge_training.py` (nouveau) | ~280 | 14 |
| **C1.3.D** | `strategy_ladder_multi_pair_expected_edge_training.py` (extension) | +130 | 12 (inc Phase 4) |
| **TOTAL** | 3 modules touchés | **~660** | **43** |

---

## API publique multi-pair

### Discovery (C1.3.A)
```python
from local_replay_runtime.pair_capability_discovery import (
    discover_pair_capabilities,
    filter_pairs_for_training,
    build_pair_rejection_message,
    PairCapability,
)

caps = discover_pair_capabilities(
    klines_root=Path("L:/klines"),
    trades_root=Path("L:/trades"),
    orderbook_root=Path("L:/ordrebookpart1"),
    metadata_pairs=("PAIR_A", "PAIR_B", ...),  # from metadata cache
)
# caps["PAIR_A"].capability_tier() == "FULL_MICROSTRUCTURE" | "LEGACY_OHLCV_ONLY" | "INSUFFICIENT_FOR_TRAINING"

accepted, rejected = filter_pairs_for_training(
    requested_pairs=("PAIR_A", "PAIR_B", "PAIR_C"),
    capabilities=caps,
    require_microstructure=True,
)
```

### Training Request (C1.3.C)
```python
from local_replay_runtime.strategy_ladder_multi_pair_expected_edge_training import (
    StrategyLadderMultiPairExpectedEdgeTrainingRequest,
    build_multi_pair_training_rows,
    build_multi_pair_ml_trainer_request,
    _build_multi_pair_pair_assignment,
    PAIR_ID_FEATURE_KEY,
)

request = StrategyLadderMultiPairExpectedEdgeTrainingRequest(
    artifact_id="multipair_15m_v1",
    calibration_version="v1",
    pairs=accepted,  # from filter
    timeframe="15m",
    label_store_dataset_paths={p: Path(...) for p in accepted},
    output_dir=Path("artifacts/"),
    train_start="2025-01-01",
    train_end="2025-06-30",
    feature_names=("close_return", "high_low_range", "volume", PAIR_ID_FEATURE_KEY),
    apply_inverse_frequency_pair_weighting=True,
    use_categorical_pair_id=True,
)
```

### Inference (C1.3.D)
```python
from local_replay_runtime.strategy_ladder_multi_pair_expected_edge_training import (
    load_multi_pair_inference_artifact,
    predict_expected_edge_for_pair,
    predict_expected_edge_batch,
)

artifact = load_multi_pair_inference_artifact(
    booster_path=Path("artifacts/expected_edge_multipair_15m.lgb"),
    pair_id_encoding={"PAIR_A": 0, "PAIR_B": 1, "PAIR_C": 2},
    feature_names=("close_return", "high_low_range", "volume", PAIR_ID_FEATURE_KEY),
)

edge_bps = predict_expected_edge_for_pair(
    artifact=artifact,
    pair="PAIR_B",  # must be in encoding
    features={"close_return": 0.001, "high_low_range": 0.002, "volume": 100.0},
)
# → fail-close si pair unknown ou features incomplets
```

---

## Doctrine V5.3 — invariants respectés

| Invariant | Statut |
|---|---|
| ✅ **MP3 mono-pair atomic intact** | Coexiste — pas modifié |
| ✅ **ZERO hardcoded pair names** | Méta-test prouve, parametrized tests valident |
| ✅ **Filesystem-driven discovery** | Admin ajoute pair = create dir, auto-discoverable |
| ✅ **Fail-closed strict** | Pair unknown → ValueError actionable, pas silent default |
| ✅ **Deterministic encoding** | sorted alphabetical, pas hash() ni random |
| ✅ **Inverse-frequency balance** | Balance auto BTC 10x ETH → ETH ÷10 |
| ✅ **Backward-compat ml_trainer** | Defaults `()` → mono-pair runs inchangés |
| ✅ **Audit-ready** | Report expose pair_scope, sample_distribution, weights |

---

## Risques mitigés

| Risque | Mitigation |
|---|---|
| Pair imbalance biaise modèle | `apply_inverse_frequency_pair_weighting=True` (defaut) |
| LightGBM ignore categorical | `categorical_feature=["pair_id"]` passé explicitement à Dataset |
| Encoding non-déterministe | sorted alphabetical (pas hash, pas random) |
| Cross-pair contamination walk-forward | Purge/embargo cross-pair temporel (héritée de MP3 strict 180+30) |
| Inference encode mauvais pair_id | Override user-provided pair_id → use encoding (test_predict_overrides_user_provided_pair_id) |
| Manifest pair_id_encoding perdu | TODO Phase 5+ — persistence via manifest companion (currently caller responsibility) |

---

## Tests dédiés (43 nouveaux, 89/89 sprint régression PASS)

| Suite | Nb |
|---|---|
| `test_c1_pair_capability_discovery.py` (C1.3.A) | 10 |
| `test_c1_ml_trainer_categorical_weights.py` (C1.3.B) | 7 |
| `test_c1_multi_pair_training_orchestrator.py` (C1.3.C) | 14 |
| `test_c1_phase3d_phase4_inference_integration.py` (C1.3.D + Phase 4) | 12 |
| **Total nouveau** | **43** |

**Régression sprint complète : 89/89 PASS** incluant P1+P2+P3+F16-B+F2+F2-A+MP3+C1.*

---

## Comparaison MP3 vs C1 (coexistence)

| Aspect | MP3 (mono-pair atomic) | C1 (multi-pair) |
|---|---|---|
| Request class | `StrategyLadderExpectedEdgeTrainingRequest` | `StrategyLadderMultiPairExpectedEdgeTrainingRequest` |
| pair scope | `pair: str` (singular, strict validator) | `pairs: tuple[str, ...]` (1 à N) |
| Artifacts per training | 1 par (pair, tf) → N×M total | 1 par tf → M total |
| Feature pair_id | Absent (pas nécessaire mono-pair) | Required (`PAIR_ID_FEATURE_KEY`) |
| Sample weighting | Uniform | Inverse-frequency par pair |
| Cross-pair learning | Aucun | Oui (catégorical) |
| Best for | Validation atomique 1 pair | Production multi-pair avec balance |
| Doctrine | V5.3 P6 verrouillage features | V5.3 C1 multi-pair flexibility |

**Coexistence** : MP3 et C1 sont indépendants. Admin choisit selon besoin :
- 1 paire → MP3 (simpler, atomic)
- N paires → C1 (one model, balanced)

---

## Roadmap restante (post-C1)

| # | Action | Effort | Statut |
|---|---|---|---|
| C1 doctrine livrée | — | — | ✅ DONE (this doc) |
| Wire C1 dans cockpit IA Lab UI (multi-select pairs) | 0.5j | Pending |
| Persistence manifest companion (.lgb + .json with encoding) | 0.3j | Pending (currently caller responsibility) |
| Wire C1 dans `strategy_ladder_edge_model_provider` (governed mode) | 0.5j | Pending |
| Validation comparative C1 vs N mono-pair (qualité modèle) | 1-2j | Future research |
| F4 metadata switch | 0.5j | Pending |
| F1 venue VERIFIED par hash | 0.5-1j | Pending |
| P6 fail-close A2→B1/B2 | 1j | Pending |
| Engines calibration thresholds | 3-5j | Pending |

---

## Sprint global 2026-05-21 — 11 patches livrés

| # | Patch | Lignes | Tests |
|---|---|---|---|
| 1 | P1 OHLCV severity classifier | 55 | 2 |
| 2 | P2 Metadata JSONL detection | 30 | 1 |
| 3 | P3 ZIP/extracted dedup | 30 | 1 |
| 4 | F16-B VPIN/OFI/queue persistence | 120 | 12 |
| 5 | F2 Bronze gap severity classifier | 80 | 11 |
| 6 | F2-A Indexer gap detection root cause | 95 | 11 |
| 7 | MP3 Mono-pair doctrine | 25 | 7 |
| 8 | C1.3.A pair_capability_discovery | 170 | 10 |
| 9 | C1.3.B MlTrainerRequest categorical+weights | 80 | 7 |
| 10 | C1.3.C multi_pair_training_orchestrator | 280 | 14 |
| 11 | **C1.3.D + Phase 4 inference + integration** | **130** | **12** |
| **TOTAL** | **~1095 lignes** | **89 PASS** |

---

## Quote user vérifiée

> *« le nom de la paire il peut etre mm xx ne hard code pas le nom de la paire : cad la on a l historique de btc.. d ici 2 mois j peux chosir une autre pair qui n est pas listé ici tu as compris : on code le processe la »*

**✅ Respecté à 100%** : tests prouvent que des noms arbitraires (MMXX, XYZ123, ARBITRARY_A, FUTURE_PAIR_42) fonctionnent identiquement à BTCUSDT/ETHUSDT/etc. Admin peut ajouter une paire AVAX en mettant `L:/klines/AVAX/` → auto-discovery sans code change.

---

## NEXT — décisions admin pending

1. **Wire C1 dans cockpit IA Lab UI** : multi-select pairs in lab.html
2. **Manifest persistence** : auto-save pair_id_encoding + feature_hash dans `.manifest.json` companion à chaque artifact
3. **Provider wiring** : intégrer `predict_expected_edge_for_pair` dans `strategy_ladder_edge_model_provider.py` pour debug/prod inference
4. **Validation comparative** : run training C1 multi-pair vs N mono-pair, comparer qualité modèle (RMSE, Sharpe, etc.)
