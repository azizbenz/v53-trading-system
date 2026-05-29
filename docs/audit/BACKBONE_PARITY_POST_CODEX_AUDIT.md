# Backbone Parity — Post-Codex Audit

**Date** : 2026-05-27
**Run audité** : `strategy_ladder_workflow-33a8593aca39312f` (post-patches Codex)
**Doctrine** : `docs/audit/2026-05-27_BACKTEST_BACKBONE_PARITY_DIAGNOSTIC_PATCH_PLAN.md`
**Mode** : READ-ONLY validation
**Question utilisateur** : *« Le nouveau rail backbone est-il vraiment branché au backtest, ou le backtest reste-t-il sur local_replay ? »*

---

## TL;DR

**Réponse en 1 ligne** : `PARTIAL — 100% des records ont le rapport, mais seulement 43% des évaluations utilisent vraiment le backbone canonique ; les 12 reports top-level promis dans le MD ne sont PAS générés au runtime ; le cockpit dashboard ne consomme RIEN.`

**Verdict global** : `BACKBONE_PARITY_PARTIAL_RECORD_LEVEL_AGGREGATE_AND_DASHBOARD_NOT_WIRED`

---

## 1. Ce qui marche ✅

### Le wiring per-record est COMPLET

Chaîne d'appels confirmée par grep :

```
strategy_ladder_runner.py:104
  └─> imports run_strategy_ladder_detailed_replay
       └─> strategy_ladder_detailed_replay.py:580
            └─> evaluate_replay_execution(request)  per row
                 └─> replay_execution_runtime.py:69
                      └─> simulate_shadow_compatible_dtrs
                           └─> shadow_execution_simulator.py:2493
                                └─> build_backbone_parity_surface_report(...)
                                     └─> ReplayParityDiagnosticsSummary.backbone_surface_report
                                          └─> bucket_record.parity_payload.backbone_surface_report
                                               └─> atomic_write_json (line 824)
```

Évidence factuelle : **360/360 records (100%)** du run contiennent un `backbone_surface_report` complet avec 21 surfaces évaluées.

### Tests Codex confirmés verts

```
pytest tests/test_local_replay_runtime/test_shadow_execution_simulator.py
       tests/test_local_replay_runtime/test_replay_execution_runtime.py
       tests/test_local_replay_runtime/test_strategy_ladder_detailed_replay_fee_rates.py
       tests/test_local_replay_runtime/test_backbone_parity_adapter.py
       tests/test_local_replay_runtime/test_backtest_backbone_parity_audit.py
       tests/test_local_replay_runtime/test_strategy_ladder_runner.py
→ 137 passed
```

---

## 2. Surface-by-surface : qui utilise vraiment le nouveau rail ?

**360 records × 21 surfaces = 7560 évaluations** :

| Status | Count | % |
|---|---:|---:|
| `CANONICAL_BACKBONE_USED` | 3 264 | **43.2%** |
| `LOCAL_REPLAY_FALLBACK_USED` | 3 936 | **52.1%** |
| `NO_SURFACE_RESULT_AVAILABLE` | 360 | 4.8% |

### 7 surfaces utilisent 100% le backbone canonique ✅

| Surface | Status dominant | promotion_allowed |
|---|---|---|
| `complete_enablers_build14` | CANONICAL_BACKBONE_USED (360/360) | yes=360 |
| `cost_aggregation` | CANONICAL_BACKBONE_USED (360/360) | yes=360 |
| `fee_measurement` | CANONICAL_BACKBONE_USED (360/360) | yes=360 |
| `order_decision_reporting` | CANONICAL_BACKBONE_USED (360/360) | yes=360 |
| `order_type_selection` | CANONICAL_BACKBONE_USED (360/360) | yes=360 |
| `protocol_contracts` | CANONICAL_BACKBONE_USED (360/360) | yes=360 |
| `venue_constraints` | CANONICAL_BACKBONE_USED (360/360) | yes=360 |

### 4 surfaces sont MIXTES (~50% canonical, ~50% fallback) ⚠️

| Surface | Canonical | Local replay |
|---|---:|---:|
| `data_backbone_market_microstructure` | 184/360 (51%) | 176 (49%) |
| `execution_intent` | 192/360 (53%) | 168 (47%) |
| `slippage_measurement` | 184/360 (51%) | 176 (49%) |
| `spread_measurement` | 184/360 (51%) | 176 (49%) |

### 9 surfaces sont à 100% LOCAL_REPLAY_FALLBACK ❌

| Surface | Status | promotion_allowed |
|---|---|---|
| `adverse_selection` | LOCAL_REPLAY_FALLBACK_USED | no=360 |
| `fee_aware_edge_gate` | LOCAL_REPLAY_FALLBACK_USED | no=360 |
| `fill_terminal_state` | LOCAL_REPLAY_FALLBACK_USED | no=360 |
| `hard_block_gate` | LOCAL_REPLAY_FALLBACK_USED | no=360 |
| `meta_learning_expected_edge` | LOCAL_REPLAY_FALLBACK_USED | no=360 |
| `partial_fill_cost` | LOCAL_REPLAY_FALLBACK_USED | no=360 |
| `portfolio_state` | LOCAL_REPLAY_FALLBACK_USED | no=360 |
| `risk_filter` | LOCAL_REPLAY_FALLBACK_USED | no=360 |
| `scoring_ranking` | LOCAL_REPLAY_FALLBACK_USED | no=360 |

### 1 surface ne donne aucun résultat ❌

| Surface | Status |
|---|---|
| `regime_classification` | NO_SURFACE_RESULT_AVAILABLE (360/360) |

---

## 3. Ce qui NE marche PAS

### A. Module audit top-level non câblé au runner

Le module `backtest_backbone_parity_audit.py` (48 KB) existe, est testé, **MAIS** :

- `grep "from local_replay_runtime.backtest_backbone_parity_audit\\|write_backtest_backbone_parity_audit_reports"` → **0 match** hors du module lui-même et de ses tests
- Donc `write_backtest_backbone_parity_audit_reports` n'est jamais appelé en runtime
- **Les 12 fichiers reports listés dans le MD doctrine NE SONT PAS PRODUITS** par le run :

```
❌ reports/backtest_backbone_parity_audit.json
❌ reports/backtest_backbone_parity_final_report.json
❌ reports/backbone_module_usage_matrix.json
❌ reports/backtest_decision_source_matrix.json
❌ reports/backtest_local_replay_dependency_audit.json
❌ reports/parallel_logic_and_proxy_surface_audit.json
❌ reports/count_semantics_deep_audit.json
❌ reports/reason_code_taxonomy_audit.json
❌ reports/executed_reason_code_consistency_audit.json
❌ reports/engine_native_runner_invocation_audit.json
❌ reports/b2_cost_blocker_component_audit.json
❌ reports/engine_a_executed_candidate_autopsy.json
❌ reports/backtest_backbone_parity_patch_final_verdict.json
❌ docs/audit/BACKTEST_BACKBONE_PARITY_AUDIT.md
❌ docs/audit/BACKTEST_BACKBONE_PARITY_FINAL_REPORT.md
❌ docs/audit/BACKTEST_BACKBONE_PARITY_PATCH_FINAL_VERDICT.md
```

### B. Cockpit dashboard ne consomme RIEN

```
grep -r "backbone_surface_report|backbone_parity" src/cockpit/
→ 0 file
```

- Aucun template ne montre les % canonical vs local_replay
- Aucun state.py ne lit le backbone_surface_report
- L'opérateur doit ouvrir manuellement les bucket records JSON pour voir le rapport
- Sans wiring cockpit, pas de visibilité opérationnelle de la parité backbone

---

## 4. Réponse synthétique à la question utilisateur

| Aspect | Status |
|---|:---:|
| Le code Codex est-il déposé ? | ✅ OUI (8 fichiers modifiés/créés) |
| Les tests passent-ils ? | ✅ OUI (137 PASS) |
| Le shadow_simulator est-il appelé par le runner B2 ? | ✅ OUI (chaîne complète) |
| Le `backbone_surface_report` est-il dans les bucket records ? | ✅ OUI (360/360 = 100%) |
| Les 21 surfaces sont-elles évaluées ? | ✅ OUI (7560 évaluations) |
| **Le backbone canonique est-il utilisé majoritairement ?** | ⚠️ **NON — 43.2% canonical, 52.1% fallback** |
| Les rapports agrégés top-level sont-ils produits ? | ❌ NON (12 reports manquants) |
| Le cockpit dashboard affiche-t-il la parité ? | ❌ NON (0 référence) |

**Conclusion** : Codex a fait **la moitié du travail** :
- Per-record OK ✅
- Aggregate ❌
- Dashboard ❌
- 9 surfaces sont encore 100% local_replay

C'est cohérent avec le verdict que Codex a lui-même annoncé : `B2_PARTIAL_BACKBONE_ADAPTER_NOT_FULL_SHADOW_LIVE_PARITY`. Il faut le finir.

---

## 5. Prochaines étapes prioritaires

| Rank | Issue | Severity | Effort estimé |
|---:|---|:---:|:---:|
| 1 | Câbler `backtest_backbone_parity_audit.write_*` au runner B2 (12 reports manquants) | **P0 wiring** | ~50 lignes, 2 fichiers |
| 2 | Ajouter card "Backbone Parity" au cockpit backtest dashboard | **P0 reporting** | ~3 fichiers cockpit + template |
| 3 | Brancher les 9 surfaces encore 100% local_replay au backbone réel | P1 continuation | Long terme (multi-session) |
| 4 | Brancher `regime_classification` (NO_RESULT) | P2 continuation | ~1 module |

---

## 6. Artifacts livrés par cet audit

- JSON canonique : `L:/output backtest/runs/strategy_ladder_workflow-33a8593aca39312f/audit_outputs/backbone_parity_post_codex_audit.json`
- Ce MD : `docs/audit/BACKBONE_PARITY_POST_CODEX_AUDIT.md`

Aucune logique trading, threshold, gate ou engine n'a été modifiée.
