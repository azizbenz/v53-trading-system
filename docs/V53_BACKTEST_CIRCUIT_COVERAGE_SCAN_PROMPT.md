# Prompt Codex — V5.3 Backtest Circuit Coverage Matrix avec scan préalable du code

## Mission

Tu travailles sur le projet `v53_trading_system`.

Objectif : reconstruire une **Backtest Circuit Coverage Matrix** fiable pour V5.3, mais cette fois **à partir d’un scan réel du code**, pas seulement d’une liste manuelle.

Le but est de répondre à une question précise :

> Quand je lance un backtest V5.3, quelles couches du système sont réellement attendues, invoquées, consommées, prouvées, proxy, scratch-only, ou absentes ?

Cette matrice doit permettre de distinguer :

- ce que le backtest utilise réellement ;
- ce qu’il devrait utiliser selon le code et les contrats ;
- ce qui est normal car hors run-class ;
- ce qui est configuré OFF ;
- ce qui est shadow/live only ;
- ce qui est manquant ou mal câblé ;
- ce qui produit seulement des artefacts scratch ;
- ce qui peut ou non compter comme preuve backtest.

---

## Contraintes globales

Respecte strictement ces invariants :

- Ne change pas les gates de promotion.
- N’active pas le ML.
- Ne supprime pas `EXPECTED_EDGE_PROXY_BLOCKED`.
- Ne supprime pas les blockers de fidélité d’exécution.
- Ne marque aucun gap W3 / W5 / W6 / CD comme résolu.
- Ne marque rien comme `promotion-ready`, `shadow-ready`, `micro-live-ready`, ou `live-ready`.
- Ne transforme aucun artefact `SCRATCH_ONLY` en preuve auditée.
- Ne crée aucun faux `READY`.
- Ne masque pas les composants proxy.
- Ne considère pas “fichier généré” comme “preuve backtest”.

Le résultat doit rester fail-closed.

---

## Source de vérité

Fais d’abord :

```text
MemPalace check.
```

Si MemPalace n’est pas disponible, utilise :

```text
current codebase + real workflow artifacts on K:
```

Workflow réel prioritaire à inspecter :

```text
strategy_ladder_workflow-f5b38cb2f2bc56f2
```

---

# Phase 0 — Scan préalable obligatoire du code

Avant de créer la matrice, tu dois scanner le code pour identifier automatiquement les composants qui devraient apparaître dans la couverture backtest.

Ne commence pas par une table manuelle.

Tu dois explorer au minimum :

```text
src/local_replay_runtime
src/data_backbone
src/complete_enablers
src/engines
src/scoring_backbone
src/execution_backbone
src/risk_backbone
src/portfolio_minimal
src/meta_minimal
src/meta_learning
src/calibration_methods
src/protocols
src/monitoring
src/cockpit
src/backtest_artifact_import
src/venue_adapters
src/interface_contracts
src/manifest_registry
src/dag_validator
```

## Ce que le scan doit identifier

Pour chaque module / composant candidat, identifie :

```text
component_id
layer
module_path
public functions/classes importantes
imports entrants
imports sortants
artifacts produits
artifacts consommés
run classes où il est attendu
run classes où il est hors périmètre
liens avec Strategy Ladder / B1 / B2 / cockpit / promotion
```

Tu dois construire une première table appelée :

```text
backtest_circuit_discovered_components.json
```

Chaque entrée doit indiquer :

```json
{
  "component_id": "...",
  "layer": "...",
  "module_path": "...",
  "discovery_source": "STATIC_SCAN | IMPORT_GRAPH | ARTIFACT_TRACE | MANUAL_OVERRIDE",
  "public_symbols": [],
  "imports_from": [],
  "imports_to": [],
  "artifact_inputs": [],
  "artifact_outputs": [],
  "candidate_run_classes": [],
  "notes": "..."
}
```

## Interdiction

Ne te contente pas d’une liste codée en dur.

Tu peux garder une registry canonique, mais elle doit être comparée au scan réel du code.

---

# Phase 1 — Comparaison registry attendue vs code réel

Après le scan, compare :

```text
A. composants découverts dans le code
B. composants déjà présents dans une éventuelle registry run-class/component-coverage
C. composants réellement présents dans les artefacts du workflow K:
```

Produis :

```text
backtest_circuit_registry_diff.json
```

Avec ces catégories :

```text
DISCOVERED_AND_REGISTERED
DISCOVERED_NOT_REGISTERED
REGISTERED_NOT_FOUND_IN_CODE
REGISTERED_BUT_NOT_EXPECTED_IN_THIS_RUN_CLASS
EXPECTED_BUT_NOT_ARTIFACTED
ARTIFACTED_BUT_NOT_REGISTERED
ARTIFACTED_BUT_SCRATCH_ONLY
```

Si un composant existe dans le code mais n’est pas dans la matrice, ajoute-le ou explique pourquoi il est hors run-class.

---

# Phase 2 — Run-class semantics

La matrice doit dépendre du type de run.

Gère au minimum ces run classes :

```text
A1_PREVIEW
A2_DATA_FACTORY
B1_CANDIDATE_DISCOVERY
B2_DETAILED_REPLAY
FULL_DIAGNOSTIC
SHADOW_LIVE
MICRO_LIVE
LIVE_LIGHT
```

## A1_PREVIEW

Attendu :

```text
source scope
request validation
raw-root validation
pair/date inference
storage estimate
preview manifest
```

Non attendu :

```text
engines
replay
promotion
ML
live venue adapters
capital proof
```

## A2_DATA_FACTORY

Attendu :

```text
raw source validation
silver materialization
gold materialization
silver_index
gold_feature_manifest
compression/storage reports
```

Non attendu :

```text
engine decisions
detailed replay
promotion proof
live execution
```

## B1_CANDIDATE_DISCOVERY

Attendu :

```text
feature store loading
candidate discovery
engine-native candidate materialization when requested
candidate_events export
candidate_summary
candidate count semantics
scoring prefilters where wired
```

Non attendu :

```text
detailed replay proof
capital bucket proof
promotion readiness
live execution
```

## B2_DETAILED_REPLAY

Attendu :

```text
raw window extraction
detailed replay
execution backbone components
scoring gates
refusal ledger
trade detail ledger
loss analysis ledger
promotion artifacts
capital bucket profiles
sample-size survival artifacts
governed audit evidence index
```

Attendu mais peut rester bloqué :

```text
expected-edge governance
fill realism
replay/shadow/live cost parity
promotion-grade evidence
```

## FULL_DIAGNOSTIC

Attendu :

```text
A2 + B1 + B2 full diagnostic chain
```

Non attendu :

```text
live submission
micro-live reconciliation
ML unless ML_MODE_ON
```

## SHADOW_LIVE / MICRO_LIVE / LIVE_LIGHT

Ces classes doivent marquer certains composants comme :

```text
SHADOW_LIVE_ONLY
LIVE_ONLY
NOT_APPLICABLE_TO_OFFLINE_BACKTEST
```

---

# Phase 3 — Composants minimum à suivre

Le scan peut en trouver plus, mais la matrice finale doit suivre au minimum les familles suivantes.

## Data / replay

```text
local_replay_runtime.strategy_ladder_data_factory
local_replay_runtime.strategy_ladder_candidate_discovery
local_replay_runtime.strategy_ladder_raw_window_extractor
local_replay_runtime.strategy_ladder_detailed_replay
local_replay_runtime.strategy_ladder_runner
local_replay_runtime.strategy_ladder_count_semantics
data_backbone.microstructure
data_backbone.orderbook_reconstruction si présent
data_backbone.ohlcv / silver / gold feature-store components si présents
```

## Complete enablers

```text
complete_enablers.ml_confidence
complete_enablers.market_toxicity
complete_enablers.lob_deep_filter
complete_enablers.execution_fragility
```

## Engines

```text
engines.engine_a
engines.engine_b
engines.engine_c
engines.engine_d
```

## Scoring

```text
scoring_backbone.forecast_normalizer
scoring_backbone.break_even_filter
scoring_backbone.hard_block_gate
scoring_backbone.fee_aware_edge_gate si présent ici ou dans execution_backbone
```

## Execution

```text
execution_backbone.execution_cost_meter
execution_backbone.spread_guard
execution_backbone.slippage_model
execution_backbone.venue_constraints_provider
execution_backbone.order_decider
execution_backbone.fill_tracker
execution_backbone.partial_fill_cost_meter
execution_backbone.adverse_selection_meter
execution_backbone.reconciliation_layer
```

## Risk / portfolio

```text
risk_backbone.risk_runtime
risk_backbone.true_drawdown
portfolio_minimal.opportunity_selector
portfolio_minimal.allocation_router
portfolio_minimal.capital_viability
```

## Meta / journals

```text
meta_minimal.refusal_journal
protocols.closed_episode_journal
meta_learning.post_trade_review
```

## Calibration / validation

```text
calibration_methods.psr
calibration_methods.dsr si présent
calibration_methods.energy_distance
calibration_methods.hansen_spa
calibration_methods.walkforward
```

## Promotion / artifacts

```text
local_replay_runtime.promotion_artifact_builder
local_replay_runtime.capital_profile_builder
local_replay_runtime.governed_audit_evidence_index
interface_contracts.promotion_artifact_contracts
interface_contracts.capital_profile_contracts
```

## Runtime / protocols / live

```text
protocols.shadow_runtime
protocols.micro_live_runtime
protocols.live_light_runtime
venue_adapters.binance_spot.live_submission
```

## Dashboard / monitoring

```text
monitoring.dashboard
cockpit.backtest_dashboard
cockpit.runtime_support
cockpit.backtest_preflight
```

---

# Phase 4 — Matrice finale

Produis :

```text
backtest_circuit_coverage.json
backtest_circuit_coverage.md
```

Chaque ligne doit contenir :

```text
component_id
layer
module_path
run_class_expectation
expected_in_run_class
invoked
consumed
produced_artifact
consumed_by
proof_artifact_ref
evidence_class
status
blocker_codes
criticality
notes
```

## Status autorisés

```text
USED
USED_BUT_PROXY
USED_BUT_SCRATCH_ONLY
USED_BUT_NOT_PROMOTION_GRADE
CONFIGURED_OFF
NOT_APPLICABLE_TO_RUN_CLASS
SHADOW_LIVE_ONLY
LIVE_ONLY
MISSING_WIRING
BLOCKED_BY_EXPECTED_EDGE_PROXY
BLOCKED_BY_EXECUTION_FIDELITY
BLOCKED_BY_RAW_WINDOW
BLOCKED_BY_NO_EXECUTED_TRADES
REQUIRED_BUT_NOT_INVOKED
INVOKED_BUT_NOT_CONSUMED
CONSUMED_WITHOUT_PROOF
PROOF_ARTIFACT_MISSING
EVIDENCE_AUDIT_NOT_CONFIRMED
```

## Criticality

```text
CRITICAL = 3
IMPORTANT = 2
SUPPORT = 1
```

---

# Phase 5 — Calculs obligatoires

Ajoute ces compteurs :

```text
expected_component_count
invoked_component_count
consumed_component_count
produced_artifact_count
proof_artifact_count
proxy_component_count
scratch_only_component_count
promotion_grade_component_count
critical_missing_count
configured_off_count
not_applicable_count
shadow_live_only_count
live_only_count
```

Calcule :

```text
invocation_coverage_pct = invoked_component_count / expected_component_count
consumption_coverage_pct = consumed_component_count / expected_component_count
proof_coverage_pct = proof_artifact_count / expected_component_count
critical_gap_pct = critical_missing_count / expected_component_count
promotion_grade_evidence_pct = promotion_grade_component_count / expected_component_count
proxy_or_scratch_pct = (proxy_component_count + scratch_only_component_count) / expected_component_count
```

Ajoute des scores pondérés :

```text
weighted_coverage_score = sum(weight for expected and invoked and consumed) / sum(weight for expected)
weighted_proof_score = sum(weight for expected and proof_artifact_exists) / sum(weight for expected)
weighted_critical_gap_score = sum(weight for critical_missing) / sum(weight for expected)
```

---

# Phase 6 — Verdicts circuit

Ajoute un verdict global :

```text
BACKTEST_CIRCUIT_MINIMAL
BACKTEST_CIRCUIT_PARTIAL
BACKTEST_CIRCUIT_DIAGNOSTIC_READY
BACKTEST_CIRCUIT_PROOF_BLOCKED
BACKTEST_CIRCUIT_PROMOTION_BLOCKED
BACKTEST_CIRCUIT_SHADOW_LIVE_ONLY_BLOCKED
```

Règles :

```text
Si raw windows ou detailed replay manquent : BACKTEST_CIRCUIT_PARTIAL.
Si B1/B2 tournent mais expected edge reste proxy : BACKTEST_CIRCUIT_DIAGNOSTIC_READY + BACKTEST_PROOF_BLOCKED.
Si execution fidelity a des proxy gaps : BACKTEST_CIRCUIT_PROMOTION_BLOCKED.
Si SCRATCH_ONLY domine : BACKTEST_CIRCUIT_PROOF_BLOCKED.
Ne jamais émettre promotion-ready si les preuves restent scratch/proxy.
```

---

# Phase 7 — Cockpit / report

Ajoute un panneau cockpit :

```text
Backtest Circuit Coverage
```

Il doit afficher :

```text
overall_circuit_verdict
invocation_coverage_pct
consumption_coverage_pct
proof_coverage_pct
weighted_coverage_score
weighted_proof_score
critical_missing_count
proxy_or_scratch_pct
top_10_missing_or_blocked_components
components_shadow_live_only
components_configured_off
components_expected_but_not_invoked
components_invoked_but_not_consumed
components_consumed_without_proof
```

Ajoute aussi le rapport Markdown :

```text
backtest_circuit_coverage.md
```

Ce Markdown doit être lisible par un opérateur, pas seulement une sortie machine.

---

# Phase 8 — Tests

Ajoute ou étends les tests :

```text
1. Le scan détecte les modules attendus dans src/.
2. Les composants découverts mais non enregistrés sont listés.
3. B2 FULL_DIAGNOSTIC marque raw_window_extractor et detailed_replay comme expected.
4. B2 marque live venue adapters comme SHADOW_LIVE_ONLY, pas MISSING_WIRING.
5. B2 marque ML comme CONFIGURED_OFF quand ML_MODE_OFF.
6. Un composant attendu mais non invoqué devient REQUIRED_BUT_NOT_INVOKED ou MISSING_WIRING.
7. Un composant invoqué mais non consommé devient INVOKED_BUT_NOT_CONSUMED.
8. Un artefact SCRATCH_ONLY augmente scratch_only_component_count.
9. Les pourcentages de couverture sont corrects.
10. Les scores pondérés sont corrects.
11. Le dashboard rend le panneau Backtest Circuit Coverage.
12. Aucun gate promotion/shadow/live n’est changé.
13. DAG reste PASS.
```

Commande de vérification minimale :

```text
pytest tests/test_local_replay_runtime tests/cockpit tests/test_manifest_registry -q
python scripts/run_dag_check.py
```

---

# Phase 9 — Inspection workflow réel

Après patch, inspecte :

```text
strategy_ladder_workflow-f5b38cb2f2bc56f2
```

Le résultat attendu après les derniers fixes est :

```text
candidate_discovery = USED
raw_window_extractor = USED
detailed_replay = USED
execution_backbone components = USED or USED_BUT_PROXY
ML = CONFIGURED_OFF
live venue adapters = SHADOW_LIVE_ONLY
governed evidence = SCRATCH_ONLY / EVIDENCE_AUDIT_NOT_CONFIRMED
final circuit verdict = DIAGNOSTIC_READY / PROOF_BLOCKED / PROMOTION_BLOCKED
pas promotion-ready
pas live-ready
```

Tu dois rapporter :

```text
- fichiers créés/modifiés
- nombre de composants scannés
- nombre de composants retenus dans la matrice
- top missing components
- coverage percentages
- verdict final
- tests passés
- DAG status
```

---

# Résultat attendu

À la fin, l’opérateur doit pouvoir lire :

```text
Le backtest a utilisé quoi ?
Ce qui devrait être utilisé mais ne l’est pas ?
Ce qui est hors run-class ?
Ce qui est proxy ?
Ce qui est scratch-only ?
Ce qui bloque la preuve ?
Ce qui bloque la promotion ?
Ce qui relève seulement du shadow/live ?
```

Le tableau doit empêcher l’erreur suivante :

```text
"Le backtest a tourné, donc toute V5.3 a été testée."
```

La vérité attendue est plus nuancée :

```text
Le backtest peut être diagnostic-ready tout en restant proof-blocked et promotion-blocked.
```
