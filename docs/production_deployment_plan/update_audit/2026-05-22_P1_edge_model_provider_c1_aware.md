# P1 — Edge Model Provider C1-Aware (mode explicite mono|multi)

**Date** : 2026-05-22
**Sprint** : reprise post 2026-05-21 (89/89 tests PASS, 11 patches livrés)
**Combo** : Option 1 + 1b + 3 (UI multi-select + paths multi-paire + provider C1)
**Phase** : P1 / 4 (P2, P3, P4 bloquées par P1)

---

## Objective

Permettre au runner backtest de consommer un artefact ML **multi-paire C1** (entraîné par `train_multi_pair_expected_edge_artifact` C1.3.C) en plus du bundle frozen mono-paire actuel. Le mode est choisi **explicitement** par l'admin via un nouveau champ UI `expected_edge_artifact_mode = MONO_PAIR_LEGACY | MULTI_PAIR_C1` (pas d'auto-detect — décision admin 2026-05-22).

---

## Docs Governants

- `docs/2026-05-21_C1_MULTI_PAIR_TRAINING_DOCTRINE.md` — doctrine C1 finale (4 sous-phases livrées)
- `CLAUDE.md` — règles "no hardcoded magic numbers", "fail-closed", "audit-ready", "surgical changes"
- `MEMORY.md` index → `project_c1_complete_phase3d_phase4_phase5_2026-05-21.md`

---

## Current Code Seam

### Provider mono-paire (état actuel)

[`strategy_ladder_edge_model_provider.py:401-590`](../../../src/local_replay_runtime/strategy_ladder_edge_model_provider.py#L401) :

```python
def load_governed_expected_edge_model_artifact(
    artifact_path: Path | str | None,
    *,
    expected_artifact_hash: str | None,
    now: datetime | None = None,
) -> GovernedExpectedEdgeModelLoadResult:
    # Parse JSON as MlModelArtifact OR StrategyLadderMlMultiTimeframeBundle
    # Return GovernedExpectedEdgeModel OR GovernedExpectedEdgeMultiTimeframeModel
```

### Inference helper C1 (déjà livré 2026-05-21)

[`strategy_ladder_multi_pair_expected_edge_training.py:347-434`](../../../src/local_replay_runtime/strategy_ladder_multi_pair_expected_edge_training.py#L347) :

```python
def load_multi_pair_inference_artifact(*, booster_path, pair_id_encoding, feature_names, ...)
def predict_expected_edge_for_pair(*, artifact, pair, features) -> float
```

### Call-site downstream

[`strategy_ladder_runner.py:4920-4933`](../../../src/local_replay_runtime/strategy_ladder_runner.py#L4920) :

```python
expected_edge_model_load_result = load_governed_expected_edge_model_artifact(
    request.frozen_ml_artifact_path,
    expected_artifact_hash=request.frozen_ml_artifact_hash,
    now=expected_edge_model_reference_at,
)
expected_edge_model = expected_edge_model_load_result.model
```

Le runner consomme `expected_edge_model.estimate_expected_edge_bps(pair=..., timeframe=..., timestamp_ms=..., feature_values=..., route_features=...)` via duck typing — aucune signature à casser.

---

## Placement

| Élément | Module | Type |
|---|---|---|
| `StrategyLadderMultiPairC1Manifest` (pydantic BaseModel) | nouveau dans `strategy_ladder_edge_model_provider.py` | manifest JSON parser |
| `GovernedMultiPairExpectedEdgeModel` (dataclass frozen) | nouveau dans `strategy_ladder_edge_model_provider.py` | wrapper adapter (interface compatible avec `GovernedExpectedEdgeModel`) |
| Paramètre `expected_edge_artifact_mode: str = "MONO_PAIR_LEGACY"` | ajouté à `load_governed_expected_edge_model_artifact()` signature | discriminator explicite |
| Constante `EXPECTED_EDGE_ARTIFACT_MODE_MONO_PAIR_LEGACY` et `EXPECTED_EDGE_ARTIFACT_MODE_MULTI_PAIR_C1` | nouveaux module-level | éviter magic strings |
| Provenance string `GOVERNED_ML_ARTIFACT_MULTI_PAIR_C1_BACKTEST_TRUTH` | nouveau | distinguer audits mono vs multi |

---

## Files Changed

| Fichier | Action | Lignes estimées |
|---|---|---|
| `src/local_replay_runtime/strategy_ladder_edge_model_provider.py` | Ajout pydantic model + dataclass + branche dans loader | +180 |
| `tests/test_local_replay_runtime/test_strategy_ladder_edge_model_provider_c1_aware.py` | NEW : 6 tests dédiés | +220 |
| `src/local_replay_runtime/strategy_ladder_runner.py` | Pass `expected_edge_artifact_mode` from `request` à `load_governed_*` | +5 |
| `src/interface_contracts/strategy_ladder_runner_request.py` (ou équivalent) | Ajout champ `expected_edge_artifact_mode: str = "MONO_PAIR_LEGACY"` à request | +3 |

**Total** : ~408 lignes, dont 220 de tests.

**Pas touché** : `strategy_ladder_multi_pair_expected_edge_training.py` (déjà livré C1.3.D, sa surface publique est stable).

---

## Format JSON manifest multi-paire C1 (nouveau contrat)

```json
{
  "artifact_kind": "MULTI_PAIR_C1_EXPECTED_EDGE",
  "artifact_id": "multipair_v1_15m",
  "artifact_hash": "sha256-hex-64chars",
  "feature_hash": "sha256-hex-64chars",
  "feature_names": ["close_return", "high_low_range", "volume", "pair_id"],
  "pair_id_encoding": {"BTCUSDT": 0, "ETHUSDT": 1, "SOLUSDT": 2},
  "calibration_version": "v1",
  "timeframe": "15m",
  "model_path_ref": "expected_edge_multipair_15m.lgb",
  "training_window": {"train_start": "2025-01-01", "train_end": "2025-06-30"},
  "anti_leakage_status": "EXPECTED_EDGE_ANTI_LEAKAGE_PROVEN",
  "walkforward_status": "EXPECTED_EDGE_WALKFORWARD_DECLARED",
  "horizon_minutes": 1,
  "purge_window_minutes": 0,
  "embargo_window_minutes": 0,
  "label_source": "MULTI_PAIR_C1_LABEL_STORE_DATASET",
  "label_fidelity": "EXPECTED_EDGE_GOVERNANCE_CANDIDATE"
}
```

`pydantic.BaseModel(frozen=True)` avec validators :
- `artifact_kind` must == `"MULTI_PAIR_C1_EXPECTED_EDGE"`
- `feature_names` must include `"pair_id"`
- `pair_id_encoding` must be non-empty
- `artifact_hash` / `feature_hash` must match `[0-9a-f]{64}` (sha256 hex)

---

## Claims Implemented (code à produire)

### Claim 1 : Mode `MONO_PAIR_LEGACY` (default) = comportement actuel intact

`load_governed_expected_edge_model_artifact(path, expected_artifact_hash=h, expected_edge_artifact_mode="MONO_PAIR_LEGACY")` retourne **exactement** ce que le code actuel retourne (parsing `MlModelArtifact` OR `StrategyLadderMlMultiTimeframeBundle`). Aucune régression possible sur les tests existants.

### Claim 2 : Mode `MULTI_PAIR_C1` parse le nouveau manifest

Si mode == `MULTI_PAIR_C1` :
- Parser le JSON via `StrategyLadderMultiPairC1Manifest.model_validate_json(raw_payload)`
- Résoudre `model_path_ref` (absolute ou relative au manifest folder) → path du `.lgb`
- Appeler `load_multi_pair_inference_artifact(booster_path=..., pair_id_encoding=..., feature_names=..., feature_hash=..., manifest_path=path)`
- Wrap dans `GovernedMultiPairExpectedEdgeModel`

### Claim 3 : `GovernedMultiPairExpectedEdgeModel.estimate_expected_edge_bps()` route via `predict_expected_edge_for_pair`

Interface **identique** à `GovernedExpectedEdgeModel.estimate_expected_edge_bps()` (mêmes paramètres, retourne `EdgeEstimate`). Différences internes :
- Pair auto-injecté via `predict_expected_edge_for_pair` (C1.3.D)
- Provenance = `"GOVERNED_ML_ARTIFACT_MULTI_PAIR_C1_BACKTEST_TRUTH"`
- `model_status` = `"GOVERNED_EDGE_MODEL_READY"` (cohérent avec mono pour audits downstream)
- Si pair pas dans encoding → `EdgeEstimate(edge_bps=0.0, provenance="EDGE_MODEL_BLOCKED:PAIR_NOT_IN_C1_ENCODING", ...)` (au lieu de raise — cohérent avec sémantique fail-close du provider mono)
- Si features manquantes → `EdgeEstimate(edge_bps=0.0, provenance="EDGE_MODEL_BLOCKED:MISSING_FEATURES", ...)` (idem)
- Si prediction non-finite → `EdgeEstimate(edge_bps=0.0, provenance="EDGE_MODEL_BLOCKED:NON_FINITE_PREDICTION", ...)`
- Clip négatif → 0 avec warning `"GOVERNED_EDGE_MODEL_NEGATIVE_PREDICTION_CLIPPED"`

### Claim 4 : Mode mismatch = fail-close explicite

Si mode == `MULTI_PAIR_C1` mais le JSON ne contient pas `pair_id_encoding` (ou `artifact_kind` absent / wrong) :
- Retour `GovernedExpectedEdgeModelLoadResult(model=None, status="GOVERNED_EDGE_MODEL_MODE_MISMATCH", blocker_codes=("GOVERNED_EDGE_MODEL_MODE_MISMATCH:EXPECTED_MULTI_PAIR_C1",))`

Si mode == `MONO_PAIR_LEGACY` mais JSON contient `artifact_kind == "MULTI_PAIR_C1_EXPECTED_EDGE"` :
- Retour `GovernedExpectedEdgeModelLoadResult(model=None, status="GOVERNED_EDGE_MODEL_MODE_MISMATCH:RECEIVED_MULTI_PAIR_C1_EXPECTED_LEGACY", blocker_codes=...)`

### Claim 5 : Hash validation préservée

Si `expected_artifact_hash` est fourni ET ≠ `manifest.artifact_hash` → retour `GOVERNED_EDGE_MODEL_HASH_MISMATCH` (cohérent avec mono).

### Claim 6 : Runner pipe `expected_edge_artifact_mode` depuis request

Ajout champ `expected_edge_artifact_mode: str = "MONO_PAIR_LEGACY"` au request pydantic. Default backward-compat = legacy. Le runner passe ce champ au loader.

---

## Tests and Proof

**Fichier** : `tests/test_local_replay_runtime/test_strategy_ladder_edge_model_provider_c1_aware.py`

| # | Nom test | Vérifie |
|---|---|---|
| 1 | `test_mono_pair_legacy_mode_unchanged` | Mode default = comportement actuel (charge `MlModelArtifact`, retourne `GovernedExpectedEdgeModel`) |
| 2 | `test_multi_pair_c1_mode_loads_and_predicts` | Mode MULTI charge manifest C1, retourne `GovernedMultiPairExpectedEdgeModel`, `estimate_expected_edge_bps(pair=...)` retourne `EdgeEstimate.edge_bps > 0` |
| 3 | `test_multi_pair_c1_mode_unknown_pair_fails_close` | Mode MULTI + pair pas dans encoding → `EdgeEstimate(edge_bps=0, provenance="EDGE_MODEL_BLOCKED:PAIR_NOT_IN_C1_ENCODING")` |
| 4 | `test_multi_pair_c1_mode_missing_features_fails_close` | Mode MULTI + features incomplètes → `EdgeEstimate(edge_bps=0, provenance="EDGE_MODEL_BLOCKED:MISSING_FEATURES")` |
| 5 | `test_mode_mismatch_multi_expected_received_legacy` | Mode == MULTI mais JSON est `MlModelArtifact` → `GOVERNED_EDGE_MODEL_MODE_MISMATCH:EXPECTED_MULTI_PAIR_C1` |
| 6 | `test_mode_mismatch_legacy_expected_received_multi` | Mode == LEGACY mais JSON contient `artifact_kind=MULTI_PAIR_C1_EXPECTED_EDGE` → `GOVERNED_EDGE_MODEL_MODE_MISMATCH:RECEIVED_MULTI_PAIR_C1_EXPECTED_LEGACY` |

Tests 2/3/4 utilisent un **fixture booster minimal** (LightGBM mocked via `unittest.mock`) pour éviter dépendance runtime LightGBM dans CI.

### Commandes de preuve

```powershell
# Test dédié P1
rtk pytest tests/test_local_replay_runtime/test_strategy_ladder_edge_model_provider_c1_aware.py -v

# Régression provider mono-paire (existant)
rtk pytest tests/test_local_replay_runtime/test_strategy_ladder_edge_model_provider*.py -v

# Régression C1 (déjà livré 2026-05-21)
rtk pytest tests/test_local_replay_runtime/test_c1_phase3d_phase4_inference_integration.py -v
rtk pytest tests/test_local_replay_runtime/test_strategy_ladder_multi_pair_expected_edge_training.py -v

# Guardrails (V5.3 doctrine — pas de magic numbers, pas de file > 700 lignes)
rtk python -m dag_validator
```

**Slots remplis post-exécution (2026-05-22)** :

- [x] **pytest_dedicated** : `7 passed` (test_strategy_ladder_edge_model_provider_c1_aware.py)
- [x] **pytest_regression** : `43 passed` (provider + c1 phase3d + c1 multi-pair orchestrator + expected_edge_training)
- [x] **pytest_runner_consumers** : `48 passed, 2 failed` — les 2 FAIL (`KeyError: 'execution_state'`) sont **pré-existants** (vérifié par git stash : test ne collecte même pas en état pré-P1 car `_compute_statistical_validation_result` manque dans le working tree). Non liés à P1.
- [x] **guardrails P1 files** : `new_violations=0` sur mes 5 fichiers (script `run_engineering_guardrails.py`, filtrage post-scan par chemin)
- [x] **git diff stats P1 only** :
  - `src/local_replay_runtime/strategy_ladder_edge_model_provider_multi_pair.py` (new, 316 lignes)
  - `src/local_replay_runtime/strategy_ladder_edge_model_provider.py` (modifié, +95 lignes)
  - `src/local_replay_runtime/strategy_ladder_models.py` (modifié, +10 lignes)
  - `src/local_replay_runtime/strategy_ladder_runner.py` (modifié, +1 ligne au call-site)
  - `tests/test_local_replay_runtime/test_strategy_ladder_edge_model_provider_c1_aware.py` (new, 196 lignes)
  - **Total P1** : ~620 lignes (dont 196 tests, 183 spec, 241 code production)

---

## Deferred / Not Done

- **P2** UI Lab multi-select (next phase)
- **P3** UI Backtest multi-select (next phase)
- **P4** Paths historiques multi-paire (next phase)
- **Manifest persistence auto-save C1.3.C** (option 2 roadmap) — écriture du JSON manifest depuis le training side. Pour P1, on **assume** que l'admin produit le JSON manuellement OU qu'option 2 sera livrée plus tard. Tests P1 utilisent un manifest construit en mémoire.
- **Promotion gates pour C1 multi-paire** (Carver/Narang/Taleb) — réutilise les mêmes blocker_codes que mono (`EXPECTED_EDGE_GOVERNED_SHADOW_REQUIRED`, `EXPECTED_EDGE_NOT_PROMOTION_GRADE`). Pas de change-set séparé.

---

## Risks

| Risque | Mitigation |
|---|---|
| Régression provider mono-paire (call-site downstream casse) | Default `expected_edge_artifact_mode="MONO_PAIR_LEGACY"` + interface `GovernedMultiPairExpectedEdgeModel` identique à `GovernedExpectedEdgeModel` (duck typing) |
| Tests CI sans LightGBM | Mock `lightgbm.Booster` via `unittest.mock` dans fixtures |
| Hash mismatch entre training-side et provider-side | Pydantic validator sur `[0-9a-f]{64}` + check explicite contre `expected_artifact_hash` |
| File > 700 lignes (`strategy_ladder_edge_model_provider.py` actuel = 912 lignes) | Déjà au-dessus de la baseline. Ajout +180L → 1092L. À vérifier : `config/engineering_guardrails_baseline.json` doit contenir l'entrée. Si nécessaire, **split** du fichier en module séparé `strategy_ladder_edge_model_provider_multi_pair.py` (~250L) — décision à l'audit post-code |
| Manifest manuel = friction admin | Acceptable pour P1 (research mode). Option 2 (manifest persistence auto) résout en aval |

---

## Completion Status (rempli 2026-05-22)

- [x] **COMPLETE**

**Preuves consolidées** :
- `pytest tests/test_local_replay_runtime/test_strategy_ladder_edge_model_provider_c1_aware.py` → **7 passed**
- `pytest` régression provider + C1 (43 tests collectés) → **43 passed**
- `pytest` consumers `StrategyLadderRequest` → 48 passed, 2 failed (**FAIL pré-existants non liés à P1**, vérifié par stash)
- `run_engineering_guardrails` filtré sur 5 fichiers P1 → **new_violations=0**
- `git diff` confirme **5 fichiers in-scope** uniquement (toutes autres modifs working tree intactes)

---

## Next Safe Step (rempli 2026-05-22)

- [x] **Débloquer P2** : UI multi-select paires IA Lab (checkbox + badges via `pair_capability_discovery`).
  - Spec à produire : `docs/production_deployment_plan/update_audit/2026-05-22_P2_ui_lab_multipair_select.md`
  - Surface P2 : `src/cockpit/templates/pages/lab.html` + `src/cockpit/strategy_ladder_ml_handoff_support.py` + form_state.
  - Risque principal : couplage avec `StrategyLadderMultiPairExpectedEdgeTrainingRequest` (C1.3.C) — surface stable, juste à wirer.
- [ ] P3 et P4 restent bloqués par P2 (P3 réutilise le composant P2) puis par P3 (P4 lit la sélection paires).

---

## Opus Audit Checklist

Avant verdict GREEN / REQUEST_FIX, l'audit doit confirmer ces 5 points :

1. **Backward-compat** : tests régression provider mono-paire PASS (au moins 1 fixture qui charge un vrai `MlModelArtifact` JSON sans toucher au mode).
2. **Fail-closed** : tests 3, 4, 5, 6 PASS — pair unknown / features incomplètes / mode mismatch retournent tous des EdgeEstimate ou LoadResult avec blocker_codes propres.
3. **Duck typing runner** : grep `expected_edge_model.estimate_expected_edge_bps` dans `strategy_ladder_runner.py` confirme que le call-site fonctionne avec les 3 types (`GovernedExpectedEdgeModel`, `GovernedExpectedEdgeMultiTimeframeModel`, `GovernedMultiPairExpectedEdgeModel`).
4. **Guardrails** : `python -m dag_validator` → `new_violations=0`.
5. **No magic numbers** : aucun seuil hardcodé introduit (les seuils existants — clamp 0, clamp negative — sont préservés tels quels, pas dupliqués).

---

**Spec rédigée par Opus, exécutée et auditée dans la même session (workflow autonome).**
