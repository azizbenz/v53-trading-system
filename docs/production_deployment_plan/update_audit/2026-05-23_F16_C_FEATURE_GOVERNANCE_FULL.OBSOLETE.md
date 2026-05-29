# SENTINEL : 2026-05-23_F16_C_FEATURE_GOVERNANCE_FULL.md est OBSOLÈTE

**Date sentinel** : 2026-05-23
**Statut** : `DO_NOT_EXECUTE — WORK_ALREADY_LANDED`

## Pourquoi ce sentinel

Le spec voisin `2026-05-23_F16_C_FEATURE_GOVERNANCE_FULL.md` a été produit le 2026-05-23 sans vérification préalable du code existant. **Tous les claims du spec sont déjà implémentés et testés** dans la branche `codex/full-solution-runtime-2026-05-17`.

## Preuves factuelles (vérification 2026-05-23)

### Pilier 1 — Validator + label_store v3 + helpers

| Claim spec | Réalité code |
|---|---|
| `EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES` | ✅ `strategy_ladder_expected_edge_training.py:65` + `strategy_ladder_expected_edge_feature_contracts.py:18` (module dédié) |
| `BUILD14_OBSERVED_EXPECTED_EDGE_FEATURE_NAMES` | ✅ ligne 71 et contracts:24 |
| `ENGINE_D_GOVERNANCE_EXPECTED_EDGE_FEATURE_NAMES` | ✅ ligne 75 et contracts:28 |
| `ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES` | ✅ ligne 81 et contracts:34 |
| `_ANTI_REVENGE_STATE_ONE_HOT_SET` validator | ✅ ligne 96 |
| Schema row v3 + `kyle_lambda: float \| None` | ✅ `strategy_ladder_b2_label_store_builder.py:414-415` |

### Pilier 2 — Promotion registry + ablation

| Module spec | Fichier livré | Taille |
|---|---|---|
| `expected_edge_feature_promotion_registry.py` | ✅ même nom | 4.7 KB |
| `expected_edge_feature_ablation_orchestrator.py` | ✅ même nom | 7.3 KB |
| (bonus) `artifact_ablation_study.py` | ✅ ajouté | 8.4 KB |
| (bonus) `local_lab_promotion_readiness.py` | ✅ ajouté | 5.0 KB |
| (bonus) `promotion_artifact_builder.py` | ✅ ajouté | **54.6 KB** |

### Pilier 3 — UI Lab feature picker

| Claim spec | Réalité code |
|---|---|
| `LabMlHandoffFormState.selected_features` | ✅ `form_state_support.py:39, 109` |
| `discovered_feature_governance` | ✅ ligne 110 |
| `discover_lab_feature_governance` | ✅ `strategy_ladder_ml_handoff_support.py:599` |
| Template Lab multi-select + badges | ✅ `lab.html:219-239` |
| **Bonus non prévu** : feature picker AUSSI sur page backtest | ✅ `backtest.html:488-497` |
| **Bonus non prévu** : `BacktestFormState.selected_features` | ✅ `backtest_state_support.py:94, 153, 216` |
| JS handling sélection | ✅ lab.html:1272-1275 + backtest.html:3837-3840 |

## Preuve tests

```
rtk pytest tests/test_local_replay_runtime/test_feature_promotion_registry.py \
            tests/test_local_replay_runtime/test_feature_ablation_orchestrator.py \
            tests/cockpit/test_lab_feature_picker.py \
            tests/cockpit/test_backtest_feature_picker_chain.py
→ 46 passed
```

Autres tests F16-C présents (non runnés ici mais artifacts `.pyc` présents → exécutés au moins une fois) :
- `tests/test_local_replay_runtime/test_artifact_ablation_study.py`
- `tests/test_local_replay_runtime/test_local_lab_promotion_readiness.py`
- `tests/test_local_replay_runtime/test_promotion_artifact_builder.py`
- `tests/test_protocols/test_promotion_gates.py`
- `tests/test_protocols/test_promotion_gates_bs_sequential_regression.py`

## Erreur méthodologique reconnue

Anti-pattern documenté dans [feedback_worktree_vs_real_repo.md](../../../memory/feedback_worktree_vs_real_repo.md) :
> *« ne JAMAIS auditer un worktree obsolète sans vérifier vs repo parent. Réflexe : `git status` + `git worktree list` + question utilisateur avant tout audit »*

Étendu 2026-05-23 :
> **Avant de produire un spec md basé sur la mémoire pré-existante, TOUJOURS grep le code actuel pour les symboles cités comme manquants. La mémoire est un journal historique, pas une source de vérité sur l'état présent du code.**

## Conservation du spec voisin

Le spec md `2026-05-23_F16_C_FEATURE_GOVERNANCE_FULL.md` est **conservé** car :
1. Il documente les 4 décisions architecturales user-validées (SHAP+Ablation P&L / Multi-select+badges / One-hot anti_revenge / Backward-compat v3 nullable) — utile pour audit doctrinal post-hoc
2. Il contient la spec test (56 tests prévus) — utile pour vérifier coverage actuel vs prévu
3. Suppression pure perdrait l'archive des choix architecturaux

**Mais le spec NE DOIT PAS être exécuté.** Ce fichier sentinel est la garde.

## Next safe step

Si tu veux pousser F16-C plus loin, options :

1. **Audit coverage F16-C** : comparer les 56 tests prévus dans le spec vs les ~46+ tests réellement présents. Identifier gaps si applicable.
2. **Lancer le full test suite F16-C** pour confirmer green sur les 9 fichiers tests (pas juste les 4 vérifiés ici).
3. **F16-D (auto-application verdict)** : seul scope mentionné comme "deferred" dans le spec original. Vérifier si déjà livré aussi avant de spec.
4. **Calibration thresholds promotion** (toujours `TO_CALIBRATE` ?) — chantier séparé annoncé dans le spec.
