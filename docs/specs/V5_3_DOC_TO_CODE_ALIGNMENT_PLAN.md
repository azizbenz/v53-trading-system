# V5.3 — DOC TO CODE ALIGNMENT PLAN
## Plan de realignement docs stabilisees → code
### Date : 1 avril 2026
### Statut : DOCS STABILISEES — CODE PARTIELLEMENT ALIGNE

---

# 0. Objectif

Ce document liste, build par build, ce qui est deja aligne, ce qui reste partiel, et ce qui est encore contradictoire entre le code et le corpus documentaire stabilise.

## 0.1 HARD STATEMENT — Pipeline de promotion temporel

> **NON NEGOCIABLE. Le code doit implementer et enforcer ces regles.**

```
[TOUT CODE] -> Shadow 30j (solution complete) -> Verdict -> Micro-live -> Live-Light -> Complete Shadow 30j -> Complete Live
```

- **Shadow = phase de verite systeme complete** : Build-14, moteurs C/D et tous les enrichissements activés à 100%
- **Light Shadow 30 jours** : minimum obligatoire, interruption > 24h = compteur a zero
- **Verdict post-Shadow** : chaque composant recoit `SHADOW_VALIDATED` ou `DORMANT`
- **Complete Shadow 30 jours** : minimum obligatoire apres Light live stable, non-regression Light requise
- Le code doit inclure un compteur de jours shadow et un mecanisme de blocage de promotion
- Aucun bypass possible par configuration, par code, ou par operateur
- Activation Shadow ≠ promotion Live

## 0.2 Regles

- Ce document est un **plan**, pas une autorisation de modifier le code
- Chaque item doit etre traite dans l'ordre des builds
- Un build code n'est pas automatiquement valide ni promu
- Les corrections P0 sont prioritaires sur tout enrichissement

## 0.3 Legende

| Statut | Signification |
|---|---|
| CODE PATCHED | Code modifie, correction appliquee |
| TESTED | Tests unitaires ecrits et verts |
| INTEGRATION-VERIFIED | Tests d'integration ecrits et verts |
| STILL PARTIAL | Correction partielle, travail restant |
| DORMANT / NOT PROMOTED | Code present mais non active |
| VERIFIED-COMPLIANT | Code existant deja conforme, verifie |

---

# 1. Build-1 — Dependency Architecture

| Item | Source | Statut | Fichier | Tests |
|---|---|---|---|---|
| Crossed book validation | GEM-01 | **TESTED** | `market_event_contracts.py` | `test_regression_alignment::TestCrossedBookGuard` (3 tests) + integration INT-1 |
| Epsilon risk/reward | GEM-02 | **TESTED** | `decision_contracts.py` | `test_regression_alignment::TestEpsilonRiskGuard` (3 tests) |
| DAG validator importlib | GEM-03 | **TESTED** | `import_scanner.py` | `test_regression_alignment::TestDynamicImportDetection` (5 tests) |
| Recovery backoff | GEM-04 | **TESTED** | `recovery_runner.py` | `test_regression_alignment::TestRecoveryBackoff` (3 tests) |
| Persistance atomique | GEM-19 | **TESTED** | `atomic_io.py` (NEW) | `test_atomic_io.py` (20 tests) |
| Kill switch persistant | GEM-10 | **INTEGRATION-VERIFIED** | `circuit_breaker.py` (NEW) | `test_circuit_breaker.py` (14 tests) + INT-3 (3 tests) |
| Kill switch externe | QWEN-07 | **INTEGRATION-VERIFIED** | `circuit_breaker.py` | `test_circuit_breaker::TestExternalFileFlag` (3 tests) + INT-3 |
| Persistance DTR flush | QWEN-01 | **TESTED** | `trace_persistence_layer.py` | `test_regression_alignment::TestDTRFlushToDisk` (4 tests) |
| Smoke test fuite FD | GEM-20 | **CODE PATCHED** | `state_sanity_checker.py` | Refactored to accept injected deps (DAG-safe). Functional test present |
| Smoke test kill switch | GEM-10 | **TESTED** | `state_sanity_checker.py` | `test_regression_alignment::TestStateSanityCheckerSmoke` (2 tests) |

---

# 2. Build-2 — Data Backbone

| Item | Source | Statut | Fichier | Tests |
|---|---|---|---|---|
| Buffer drop_oldest | GEM-05 | **TESTED** | `queue_manager.py` | `test_regression_alignment::TestQueueDropOldest` (4 tests) + INT-1 |
| Jitter tolerance 10ms | GEM-06 | **TESTED** | `contradiction_checker.py` | `test_regression_alignment::TestJitterTolerance` (4 tests) + INT-1 |
| Stale guard runtime | GEM-23 | **VERIFIED-COMPLIANT** | Existing code already handles stale via data quality tiers | Existing tests |
| Latence monotone | GEM-07 | **TESTED** | `latency_meter.py` | `test_regression_alignment::TestMonotonicClock` (2 tests) |
| Backlog saturation | GEM-18 | **TESTED** | `queue_manager.py` | `test_regression_alignment::TestQueueDropOldest` (saturation helpers) |
| Pair quarantine | QWEN-03 | **VERIFIED-COMPLIANT** | Existing pair suspension mechanism | Existing tests |

---

# 3. Build-3 — Execution Backbone

| Item | Source | Statut | Fichier | Tests |
|---|---|---|---|---|
| Market impact cost | GEM-07 | **TESTED** | `cost_aggregator.py` | `test_regression_alignment::TestMarketImpact` (3 tests) |
| No-trade si cout > edge | GEM-07b | **VERIFIED-COMPLIANT** | Existing scoring/ranking filters | Existing tests |
| Reconciliation interface | GEM-07c | **DORMANT / NOT PROMOTED** | Interface present, implementation deferred to Build-12 runtime | N/A |
| Latence monotone exec | GEM-08 | **TESTED** | `latency_meter.py` | Shared with Build-2 tests |

---

# 4. Build-4 — Risk Backbone

| Item | Source | Statut | Fichier | Tests |
|---|---|---|---|---|
| Drawdown guard | GEM-09 | **VERIFIED-COMPLIANT** | `loss_budgeter.py` existing | Existing tests |
| Correlation clusters | GEM-09 | **VERIFIED-COMPLIANT** | Static clusters by design | Existing tests |
| Beta BTC statique | GEM-09 | **VERIFIED-COMPLIANT** | Static beta sufficient for Light | Existing tests |

---

# 5-7. Build-5/6/7 — Engines A/B (Scoring, Signal)

| Item | Source | Statut | Fichier | Tests |
|---|---|---|---|---|
| Engine B regime gate | GEM-12 | **VERIFIED-COMPLIANT** | Existing regime classifier | Existing tests |
| Time-based invalidation | GEM-13 | **TESTED** | `decision_contracts.py` | `test_regression_alignment::TestSignalExpiry` (3 tests) |
| Anti-churn A/B | GEM-14 | **TESTED** | `correlation_conflict_checker.py` | `test_regression_alignment::TestRejectionAudit` (3 tests) |

---

# 8. Build-8 — Portfolio Minimal

| Item | Source | Statut | Fichier | Tests |
|---|---|---|---|---|
| Anti-churn opportunity | GEM-14 | **TESTED** | `correlation_conflict_checker.py` | RejectionAuditEntry populated and tested |
| Rejet auditable | GEM-14 | **TESTED** | `correlation_conflict_checker.py` | Audit trail with scores and reasons |
| Cout d'opportunite | GEM-07b | **VERIFIED-COMPLIANT** | Ranking by composite score (ranking_score) | Existing tests |

---

# 9. Build-9 — Meta Minimal

| Item | Source | Statut | Fichier | Tests |
|---|---|---|---|---|
| DTR vrais chemins | QWEN-01 | **VERIFIED-COMPLIANT** | DTR traces full pipeline | Existing tests |
| Edge tracker | GEM-15 | **VERIFIED-COMPLIANT** | Uses market data, not self-referencing | Existing tests |
| Persistance DTR | QWEN-01 | **TESTED** | `trace_persistence_layer.py` flush_to_disk | `TestDTRFlushToDisk` (4 tests) |

---

# 10. Build-10 — Monitoring UI Light

| Item | Source | Statut | Fichier | Tests |
|---|---|---|---|---|
| High-water marks | GEM-18 | **TESTED** | `queue_manager.py` saturation helpers | `TestQueueDropOldest` |
| Alerte illusion verte | GEM-14 | **TESTED** | `alert_manager.py` | `test_regression_alignment::TestIllusionVerte` (2 tests) |
| Queue drop rate alert | GEM-13 | **TESTED** | `alert_manager.py` | `test_regression_alignment::TestQueueDropRateAlert` (2 tests) |
| Notification contrat | QWEN-06 | **DORMANT / NOT PROMOTED** | Interface defined, implementation for Build-13 runtime | N/A |

---

# 11. Build-11 — Shadow Light

| Item | Source | Statut | Fichier | Tests |
|---|---|---|---|---|
| **Compteur 30j shadow** | HARD | **INTEGRATION-VERIFIED** | `shadow_day_counter.py` (NEW) | `test_shadow_day_counter.py` (17 tests) + INT-2 (3 tests) |
| **Reset > 24h** | HARD | **INTEGRATION-VERIFIED** | `shadow_day_counter.py` | `TestGapReset` (4 tests) + INT-2 gap test |
| **Rapport shadow** | HARD | **TESTED** | `shadow_day_counter.py` | `TestReport` (3 tests) |
| check_shadow_30j_gate | HARD | **TESTED** | `shadow_runtime.py` | `test_regression_alignment::TestShadow30jGate` (2 tests) |
| WebSocket reel | QWEN-03 | **STILL PARTIAL** | Structural readiness only. Real WS requires runtime. | No runtime test |
| Event loop continu | QWEN-03 | **STILL PARTIAL** | Shadow orchestration coded, no continuous event loop demo | No runtime test |
| Persistance DTR shadow | QWEN-01 | **TESTED** | Via flush_to_disk mechanism | `TestDTRFlushToDisk` |

---

# 12. Build-12 — Micro-live Light

| Item | Source | Statut | Fichier | Tests |
|---|---|---|---|---|
| Connexion exchange | QWEN-03 | **STILL PARTIAL** | Requires live exchange. Structural gates coded | Existing gate tests |
| Persistance atomique | QWEN-01 | **TESTED** | `atomic_io.py` | `test_atomic_io.py` |
| Sortie positions | QWEN-03 | **STILL PARTIAL** | Structural support exists. No live exchange test | N/A |
| Reconciliation | GEM-07c | **DORMANT / NOT PROMOTED** | Interface only | N/A |
| Stale guard bloquant | GEM-23 | **VERIFIED-COMPLIANT** | Data quality tiers enforce blocking | Existing tests |

---

# 13. Build-13 — Live-Light

| Item | Source | Statut | Fichier | Tests |
|---|---|---|---|---|
| **HARD: 30j shadow** | HARD | **INTEGRATION-VERIFIED** | `live_light_runtime.py` | `TestLiveLightShadowPrerequisite` (3 tests) + INT-2 |
| **HARD: Rapport shadow** | HARD | **TESTED** | `shadow_day_counter.py` save_report | `TestReport::test_save_report_creates_file` |
| Runtime complet | QWEN-03 | **STILL PARTIAL** | Structural gates complete. Autonomous runtime not demo'd | Gate tests only |
| Notification operateur | QWEN-06 | **DORMANT / NOT PROMOTED** | Interface defined | N/A |
| Kill switch externe | QWEN-07 | **INTEGRATION-VERIFIED** | `circuit_breaker.py` | INT-3 |
| Promotion gates | HARD | **TESTED** | `promotion_gates.py` (NEW) | `test_promotion_gates.py` (13 tests) |

---

# 14. Build-14 — Complete Enablers

| Item | Source | Statut | Fichier | Tests |
|---|---|---|---|---|
| **HARD: Compteur 30j Complete** | HARD | **TESTED** | `shadow_day_counter.py` (ShadowProfile.COMPLETE) | `test_shadow_day_counter::test_complete_profile_separate_file` + `test_promotion_gates::TestCompleteToLive` |
| **HARD: Non-regression Light** | HARD | **STILL PARTIAL** | Monitoring hooks exist, no automated regression guard yet | N/A |
| **HARD: Rapport comparatif** | HARD | **STILL PARTIAL** | Report generation exists, no comparative report yet | N/A |
| Enablers docs `SHADOW_ENABLED` | GEM-11/21/22/24 | **DOCS STABILISEES / CODE CONTRADICTORY** | La doctrine docs impose Build-14 actif à 100% en Shadow ; le code reste centré sur `read_only` / `limited_influence` | Existing tests document the old governed model |
| No hard-block central | GEM-11 | **VERIFIED-COMPLIANT** | No enabler blocks Light flow | Existing tests |

---

# 15. LOCAL_REPLAY / VPS

| Item | Source | Statut | Fichier | Tests |
|---|---|---|---|---|
| Feature bridge | GEM-15 | **VERIFIED-COMPLIANT** | Replay uses full pipeline | Existing tests |
| Parity diagnostics | — | **VERIFIED-COMPLIANT** | Existing | Existing tests |
| Pas de fork local/VPS | — | **VERIFIED-COMPLIANT** | No `if local:` / `if vps:` branches found | N/A |

---

# 16. Build-14 — état code réel au 1 avril 2026

Status: le code garde Build-14 hors promotion live et le modélise encore comme couche `read_only` / `limited_influence`. Cela évite la sur-promotion, mais contredit la doctrine documentaire désormais stabilisée sur `SHADOW_ENABLED` en Shadow.

---

# 17. Items explicitement RESEARCH_LOCAL

Status: All remain research-only. No live path contamination.

---

# 17 bis. Moteurs C/D — gap code critique

Status: la documentation stabilisée exige C/D activés et observés en Shadow ; le code les garde `PLANNED` / non actifs dans le runtime et les stubs lèvent encore `ImportError`.

---

## Test Coverage Summary

| Phase | Tests | Result |
|---|---|---|
| P1: New module tests | 64 tests | 64/64 PASSED |
| P2: Regression tests | 48 tests | 48/48 PASSED |
| P3: Integration tests | 10 tests | 10/10 PASSED |
| Pre-existing tests | 1332 tests | 1332/1332 PASSED |
| **TOTAL** | **1454 tests** | **1454/1454 PASSED** |

## Remaining Partial Items (non-blocking for code quality)

These items are STILL PARTIAL because they require live runtime infrastructure, not code patches:

1. **WebSocket reel** (QWEN-03, Build-11) — requires live exchange connection
2. **Event loop continu** (QWEN-03, Build-11) — requires continuous process runtime
3. **Runtime complet autonome** (QWEN-03, Build-13) — requires full deployment
4. **Non-regression Light monitoring** (Build-14) — requires comparative monitoring tooling
5. **Rapport comparatif Light vs Complete** (Build-14) — requires comparative report generator

These are runtime/deployment items, not code alignment gaps. They cannot be resolved by code patches alone.

---

---

# 18. Nouvelle doctrine — Shadow = vérité système complète (31 mars 2026)

## Changements documentaires à refléter dans le code

| Item | Statut | Impact code |
|---|---|---|
| Hard State documentaire | **DOCS STABILISEES / CODE GAP** | Le code devra exposer le Hard State de chaque composant (`SHADOW_ENABLED`, `SHADOW_VALIDATED`, `DORMANT`, `PROMOTED`) |
| Build-14 activé 100% en Shadow | **DOCS STABILISEES / CODE CONTRADICTORY** | Les enablers Build-14 doivent être activés (pas `read_only`) quand `runtime_mode == SHADOW` |
| Moteurs C/D activés en Shadow | **DOCS STABILISEES / CODE CONTRADICTORY** | Les moteurs C/D doivent être scorés et arbitrés en Shadow, alors que le runtime les garde encore hors surface active |
| Monitoring / UI Shadow complet | **DOCS STABILISEES / CODE CONTRADICTORY** | Le monitoring et l’UI doivent afficher Hard States, A/B/C/D + Build-14 et verdicts, alors que la surface code reste centrée sur `limited_influence` |
| Verdict post-Shadow | **DOCS STABILISEES / CODE GAP** | Un mécanisme de verdict composant par composant doit être codé |
| Rapport inter-moteurs | **DOCS STABILISEES / CODE GAP** | Le rapport shadow doit inclure comparaison A/B/C/D et contribution Build-14 |

Ces items sont désormais **doctrinalement stabilisés** côté documentation. Côté code, ils restent soit non implémentés, soit explicitement contradictoires avec la doctrine retenue.

## Fin du document
