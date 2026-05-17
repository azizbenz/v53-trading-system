# V5.3 — Chantier complet Codex : fermeture des gaps, preuves et promotion readiness

**Document cible :** prompt de pilotage Codex pour générer un plan d’exécution puis traiter le chantier lot par lot.  
**Date :** 2026-05-09  
**Scope :** V5.3 Trading System — `LOCAL_REPLAY`, Strategy Ladder, execution realism, capital buckets, Engine C/D, replay-shadow parity, ML governance, microstructure calibration, cockpit truth surface, gap register synchronization.

---

## 0. Rôle Codex

Tu es un ingénieur Python senior / quant tooling engineer intervenant sur le dépôt `v53_trading_system`.

Ta mission n’est pas de faire un patch massif. Ta mission est de :

1. Lire l’état réel du repo.
2. Lire le registre final des gaps.
3. Construire un **plan d’exécution lot par lot**.
4. Exécuter uniquement les lots autorisés, de manière chirurgicale.
5. Ne jamais fermer un gap par intention.
6. Ne jamais déclarer une preuve promotion-grade si la donnée ou la télémétrie manque.
7. Mettre à jour le registre de gaps uniquement avec preuve réelle.

---

## 1. Sources de vérité à lire avant toute modification

Lis d’abord ces documents / fichiers s’ils existent dans le repo :

```text
P0B_FINAL_GAP_REGISTER.md
docs/v53_backtest_wiring_audit_2026-05-09.md
docs/v53_backtest_wiring_execution_plan_2026-05-09.md
docs/audit/backtest_strategy_ladder_status/
docs/audit/post_build1_shadow_blockers/
docs/audit/p0b_formula_extraction/
docs/audit/ml_governance/
```

Puis inspecte le code réel :

```text
src/local_replay_runtime/
src/execution_backbone/
src/scoring_backbone/
src/risk_backbone/
src/portfolio_minimal/
src/meta_minimal/
src/complete_enablers/
src/backtest_artifact_import/
src/cockpit/
src/manifest_registry/
src/dag_validator/
tests/
```

Si MemPalace est disponible dans ce projet, vérifie-le au début. Mais le code actuel reste la source de vérité.

---

## 2. Invariants globaux non négociables

Respecte ces invariants dans tous les lots :

```text
- un seul codebase V5.3
- pas de nouveau runtime profile
- ne pas inventer BACKTEST_PROFILE, DEV_PROFILE, AI_LAB_PROFILE
- utiliser runtime_mode=LOCAL_REPLAY
- pas de bypass Shadow / Micro-live / Live
- pas de deuxième architecture backtest
- pas de nouveau moteur hors A/B/C/D
- pas de live venue side effect dans LOCAL_REPLAY
- pas d’import live protocols ou venue_adapters dans replay sauf preuve explicite side-effect free
- Build-14 reste additif, borné, non souverain
- ML reste non souverain et non positif
- pas de side="flat"
- pas de fake blocked trades
- pas de second canon
- pas de seuil critique hardcodé
- pas de green cockpit si la preuve est absente, partielle, stale ou insuffisante
```

---

## 3. Règles de fermeture des gaps

Le registre est cumulatif. Applique strictement ces règles :

```text
- OPEN reste visible tant que non résolu.
- IN_PROGRESS ne veut pas dire RESOLVED.
- NOT_BLOCKING ne veut pas dire RESOLVED.
- FUTURE_RESERVED ne veut pas dire oublié.
- RESOLVED exige patch, report ou test evidence.
- RESOLVED_DOC_ONLY ne ferme pas un gap de code ou de donnée.
- RESOLVED_TEST_ONLY ne ferme pas un gap de production si le producteur n’est pas corrigé.
- BLOCKED_BY_BACKTEST reste ouvert tant que les runs historiques gouvernés n’existent pas.
- BLOCKED_BY_LIVE_TELEMETRY reste ouvert tant que la télémétrie shadow/live n’existe pas.
- BLOCKED_BY_HUMAN_DECISION reste ouvert tant qu’une décision humaine explicite n’est pas enregistrée.
```

Chaque ligne modifiée dans le registre doit garder une date explicite :

```text
Last update
Resolved date
Date
```

Si la date exacte n’est pas prouvée :

```text
UNKNOWN_DATE
```

---

## 4. État connu avant ce chantier

Les Lots 0–3 du backtest wiring sont réputés faits, mais doivent être vérifiés contre le repo.

### Lot 0 — Architecture Truth Freeze

Travail annoncé :

```text
- rupture du cycle local_replay_runtime <-> backtest_artifact_import
- suppression du couplage cockpit -> local_replay_runtime
- officialisation de local_replay_runtime -> engine_a/b/c/d + portfolio
- DAG validator : 0 violation, 0 cycle, 0 layer error
```

### Lot 1 — Replay Execution Interface Extraction

Travail annoncé :

```text
- replay_execution_contracts.py
- replay_execution_runtime.py
- replay_orchestrator_execution passe par seam
- strategy_ladder_detailed_replay passe par seam
- shadow_execution_simulator reste provider par défaut
```

### Lot 2 — Canonical Execution Backbone Convergence, première partie

Travail annoncé :

```text
- execution_runtime_projection_path
- replay-safe loader THR-X04 spread / THR-X05 slippage
- diagnostics REPLAY_PROXY_ONLY / PARTIAL / ACTIVE
- pas de local_replay_runtime -> protocols
```

### Lot 3 — Complete Enablers Reintegration, première partie

Travail annoncé :

```text
- strategy_ladder_complete_enabler_support.py
- Build14ObservationInput déterministe
- evaluate_build14_shadow_activation
- influence bornée sur Engine C/D input composition
- provenance Build-14 dans candidates/replay/parity_payload
```

**Action Codex requise :** ne pas croire aveuglément ces annonces. Vérifie les fichiers, les tests, les imports et le DAG.

---

## 5. Objectif global du chantier

Fermer progressivement les gaps restants qui empêchent V5.3 d’être scientifiquement et opérationnellement crédible :

```text
1. Execution Fidelity
2. Capital Bucket Evidence
3. Engine C/D Promotion Evidence
4. Replay ↔ Shadow Parity
5. ML Governance / Anti-leakage / Drift
6. Microstructure Pair-Regime Calibration
7. Cockpit Truth Surface
8. Gap Register Synchronization
```

L’objectif n’est pas de rendre tout `LIVE_READY`.  
L’objectif est d’empêcher chaque rail de mentir sur son niveau de preuve.

---

# 6. Plan d’exécution demandé à Codex

## Phase 0 — Audit pré-exécution obligatoire

Avant tout patch, produire un bref rapport local :

```text
- état git / worktree
- fichiers non trackés liés aux lots 0–3
- DAG validator current result
- tests ciblés disponibles
- état des imports directs vers shadow_execution_simulator
- état des imports local_replay_runtime -> protocols / venue_adapters
- état du registre P0B
```

Ne pas modifier de code dans cette phase sauf si tu dois lire ou générer un rapport non destructif.

### Checks recommandés

```bash
rtk git status
rtk grep "shadow_execution_simulator" src/local_replay_runtime tests
rtk grep "venue_adapters" src/local_replay_runtime
rtk grep "protocols" src/local_replay_runtime
python -m pytest tests/test_manifest_registry tests/test_dag_validator -q
```

Si `rtk` échoue, utiliser `python -m pytest` ou commandes standards, et mentionner la raison.

---

# 7. Lot A — Execution Fidelity Canon + Gap Register Sync

## But

Fermer les gaps patchables d’execution realism sans prétendre fermer les gaps bloqués par live telemetry/backtest.

## Gaps ciblés

```text
W3-OPEN-001  fee provenance not promotion-grade
W3-OPEN-002  impact provenance not promotion-grade
W3-OPEN-003  fill realism measured-vs-model proof absent
W3-OPEN-006  replay/shadow/live cost parity proof absent
BLK-001      replay fee/impact provenance
BLK-002      fill realism doctrine circularity
```

## Mission

Ajouter ou durcir une matrice d’execution fidelity sur tous les artefacts replay pertinents :

```text
fee_source_status
impact_source_status
spread_source_status
slippage_source_status
fill_source_status
partial_fill_source_status
adverse_selection_source_status
routing_source_status
venue_constraints_source_status
```

Ajouter un statut global :

```text
REPLAY_PROXY_ONLY
PARTIAL_CANONICAL_EXECUTION
FULL_CANONICAL_REPLAY
SHADOW_OBSERVED
MICRO_LIVE_OBSERVED
```

## Règles

```text
- FULL_CANONICAL_REPLAY interdit si fill, routing, partial fill ou adverse selection restent proxy/missing.
- SHADOW_OBSERVED interdit sans telemetry shadow.
- MICRO_LIVE_OBSERVED interdit sans telemetry micro-live.
- Missing fee/impact/fill ne doit jamais devenir zéro mesuré.
- Model-only fill ne doit jamais devenir measured fill.
- Cost parity absent doit bloquer promotion-grade economics.
```

## Fichiers probables

```text
src/local_replay_runtime/replay_execution_contracts.py
src/local_replay_runtime/replay_execution_runtime.py
src/local_replay_runtime/shadow_execution_simulator.py
src/local_replay_runtime/replay_orchestrator_execution.py
src/local_replay_runtime/strategy_ladder_detailed_replay.py
src/local_replay_runtime/strategy_ladder_runner.py
src/local_replay_runtime/replay_metrics_collector.py
src/cockpit/state_replay_metrics.py
src/cockpit/state_system_flow.py
src/cockpit/state_economic_sterilization.py
src/interface_contracts/ml_backtest_training_contracts.py
src/local_replay_runtime/ml_backtest_projection.py
P0B_FINAL_GAP_REGISTER.md
```

## BLK-002 doctrine split

Corriger la circularité :

```text
Before Shadow telemetry collection:
- contracts/provenance/status carriage required
- no green promotion claim

Before Shadow sign-off:
- measured fill telemetry required
- replay/shadow fill parity required
- p_fill_proxy calibration required

Before Micro-live:
- measured/proxy calibration and non-green gating required
```

Ne pas marquer BLK-002 résolu si live/shadow telemetry n’existe pas.

## Tests attendus

```bash
python -m pytest tests/test_local_replay_runtime -q
python -m pytest tests/cockpit -q
python -m pytest tests/test_manifest_registry tests/test_dag_validator -q
```

Ajouter tests si nécessaires :

```text
- missing fee does not render measured
- model-only fill stays model-only
- partial execution fidelity blocks FULL_CANONICAL
- ML labels cannot be FULL_CANONICAL unless execution_fidelity_status is FULL_CANONICAL_REPLAY or stronger
- cockpit remains non-green when execution fidelity is partial/proxy
```

## Done criteria

```text
- execution fidelity matrix visible in replay artifacts
- cockpit cannot false-green partial execution realism
- ML label projection blocked from FULL_CANONICAL on partial execution
- register updated without false resolving telemetry/backtest-blocked gaps
```

---

# 8. Lot B — Capital Bucket Evidence

## But

Produire les preuves historiques gouvernées pour 400 / 500 / 1500 / 4000.

## Gaps ciblés

```text
W5-OPEN-002
W5-CAPITAL-003
W5-CAPITAL-006
W5-CAPITAL-007
BLK-008
BLK-009
CAL-010
CAL-011
```

## Mission

Le runner existe et peut produire des capital profiles. Il faut maintenant générer ou préparer la génération d’artefacts mesurés depuis des runs historiques gouvernés.

## Sorties attendues

```text
capital_profiles/400.json
capital_profiles/500.json
capital_profiles/1500.json
capital_profiles/4000.json
small_capital_viability_report.json
capital_fragmentation_report.json
min_notional_exclusion_report.json
```

## Chaque bucket doit porter

```text
bucket_capital
allowed_pairs
max_active_pairs
min_notional_rejections
fragmentation_rate
cost_rejection_rate
fill_quality_status
depth_quality_status
net_return_status
drawdown_status
sample_size_status
execution_fidelity_status
promotion_status
hash
freshness
source_run_id
```

## Règles

```text
- Si les runs historiques n’existent pas, ne pas inventer les artefacts.
- Produire un générateur ou un plan de run, puis laisser les gaps BLOCKED_BY_BACKTEST.
- Ne jamais déclarer 400/500/1500/4000 viable sans artefacts produits.
- Une paire config-visible n’est pas live-eligible sans bucket evidence.
```

## Fichiers probables

```text
src/local_replay_runtime/capital_profile_builder.py
src/backtest_artifact_import/capital_profile_builder.py
src/local_replay_runtime/strategy_ladder_runner.py
src/local_replay_runtime/promotion_artifact_builder.py
src/portfolio_minimal/allocation_router/capital_viability.py
src/local_replay_runtime/storage_budget_report.py
src/cockpit/state_replay_metrics.py
src/cockpit/state_system_flow.py
P0B_FINAL_GAP_REGISTER.md
```

## Done criteria

```text
- either measured artifacts exist with proof
- or runner/runbook explicitly says what data/run is missing
- cockpit remains non-green when bucket artifacts are missing/stale/non-proven
```

---

# 9. Lot C — Engine C/D Promotion Evidence

## But

Produire ou préparer les artefacts de promotion Engine C et Engine D avec sample-size survival.

## Gaps ciblés

```text
CD-OPEN-001
CD-OPEN-006
BLK-014
```

## Mission

Créer ou compléter les artefacts :

```text
engine_c_promotion_artifact.json
engine_d_promotion_artifact.json
engine_c_sample_size_survival.json
engine_d_sample_size_survival.json
```

## Chaque artifact doit porter

```text
engine_id
pair
strategy_id
n_candidates
n_executed
n_refused
n_blocked
refusal_categories
execution_rate
execution_fidelity_status
cost_completeness_status
fill_realism_status
depth_quality_status
net_return_status
drawdown_status
sample_size_status
build14_influence_status
promotion_status
shadow_required
micro_live_allowed
```

## Règles

```text
- Ne pas force-map C/D vers A/B shared physics.
- C/D restent local-math-only tant qu’équivalence non prouvée.
- Build-14 influence doit rester visible : base_value, adjusted_value, factor, enabler_id.
- Promotion status doit rester non-green sans sample size + execution evidence.
```

## Fichiers probables

```text
src/local_replay_runtime/strategy_ladder_runner.py
src/local_replay_runtime/strategy_ladder_detailed_replay.py
src/local_replay_runtime/promotion_artifact_builder.py
src/local_replay_runtime/strategy_ladder_complete_enabler_support.py
src/engines/engine_c/
src/engines/engine_d/
src/cockpit/state_engine_why.py
P0B_FINAL_GAP_REGISTER.md
```

## Done criteria

```text
- C/D artifacts exist or are explicitly blocked by missing historical run
- C/D cockpit status non-green until measured evidence exists
- no semantic force-mapping introduced
```

---

# 10. Lot D — Replay ↔ Shadow Parity Canon

## But

Créer le canon de parité replay/shadow avant toute promotion.

## Gaps ciblés

```text
W3-OPEN-006
CAL-007
CAL-008
CAL-009
Replay-shadow parity requirements from backtest wiring plan
```

## Mission

Créer ou préparer :

```text
replay_shadow_parity_report.json
```

Avec métriques :

```text
spread_distribution_drift
slippage_distribution_drift
fill_rate_drift
partial_fill_rate_drift
refusal_rate_drift
cost_drift
engine_activation_drift
decision_drift
net_ev_drift
regime_bucket_drift
pair_level_drift
```

## Règles

```text
- Si shadow telemetry absente, produire un status MISSING_SHADOW_TELEMETRY, pas un faux rapport.
- Si replay profitable mais shadow diverge, promotion_status = BLOCKED.
- Si coût shadow > coût replay + seuil, recalibration_required = true.
```

## Fichiers probables

```text
src/local_replay_runtime/
src/monitoring/
src/cockpit/
src/backtest_artifact_import/
P0B_FINAL_GAP_REGISTER.md
```

## Done criteria

```text
- parity artifact contract exists
- missing telemetry is explicit and non-green
- cockpit/operator surfaces show parity state
```

---

# 11. Lot E — ML Governance / Anti-Leakage / Drift

## But

Ne pas rendre ML actif. Rendre ML scientifiquement gouverné.

## Gaps ciblés

```text
W6-OPEN-001
W6-OPEN-002
W6-OPEN-003
W6-OPEN-004
BLK-010
BLK-011
BLK-012
BLK-013
```

## Mission

Implémenter ou préparer :

```text
ml_anti_leakage_proof_artifact.json
ml_live_drift_snapshot.json
ml_supplementary_refs_source_summary.json
```

## Anti-leakage proof doit porter

```text
model_id
feature_hash
label_hash
train_window
validation_window
test_window
purge_window
embargo_window
label_horizon
feature_max_timestamp
label_min_timestamp
leakage_check_status
execution_fidelity_requirement
promotion_allowed
```

## Règles

```text
- ML reste non-sovereign.
- ML reste non-positive.
- ML ne crée pas trades.
- ML ne modifie pas side.
- ML refs missing/stale/hash mismatch => neutral disabled.
- ml.formalism.unresolved reste blocker tant que décision humaine absente.
- Aucun modèle ML entraîné sur labels proxy ne peut être promotion-ready.
```

## Fichiers probables

```text
src/interface_contracts/ml_backtest_training_contracts.py
src/interface_contracts/ml_model_artifact.py
src/local_replay_runtime/ml_backtest_projection.py
src/local_replay_runtime/local_lab_ml_artifact_training.py
src/calibration_methods/ml_trainer.py
src/complete_enablers/ml_*
src/meta_learning/model_risk_registry/
src/cockpit/
P0B_FINAL_GAP_REGISTER.md
```

## Done criteria

```text
- anti-leakage artifact implemented or explicitly blocked
- ML promotion stays blocked without artifact
- ML label source and execution fidelity are connected
```

---

# 12. Lot F — Microstructure Pair/Regime Calibration

## But

Transformer les features microstructure de “science plausible” en seuils gouvernés pair/régime.

## Gaps ciblés

```text
W4-OPEN-001
W4-OPEN-005
CAL-001 à CAL-006
```

## Mission

Créer ou préparer :

```text
microstructure_thresholds/{pair}.json
walls_spoofing_validation/{pair}.json
ofi_kyle_calibration_report.json
vpin_calibration_report.json
```

## Règles

```text
- Pas de seuil global sans pair/regime evidence.
- Pas d’engine wiring normalized Kyle/OFI sans OOS improvement.
- Walls/spoofing reste heuristic tant que validation absente.
- Research-only estimators restent non-runtime-active.
```

## Fichiers probables

```text
src/data_backbone/microstructure/
src/local_replay_runtime/feature_threshold_manifest.py
src/calibration_methods/
src/cockpit/
P0B_FINAL_GAP_REGISTER.md
```

## Done criteria

```text
- artifacts pair/regime generated or blocked by missing feature store
- no runtime promotion by implication
- cockpit separates artifact-present from runtime-consumed
```

---

# 13. Lot G — Cockpit Truth Surface

## But

Empêcher les opérateurs de surinterpréter les artefacts.

## Gaps ciblés

```text
DB-009
W4-OPEN-008
W5-OPEN-005
Lot 6 from wiring plan
```

## Mission

Étendre la séparation :

```text
ARTIFACT_PRESENT_ONLY
RUNTIME_CONSUMED
RESEARCH_ONLY
FUTURE_RESERVED
PARTIAL_CANONICAL
PROXY_ONLY
MISSING_TELEMETRY
PROMOTION_BLOCKED
```

Aux pages downstream.

## Règles

```text
- Aucune page ne doit rendre green si source missing/stale/partial/proxy.
- Feature present != feature consumed.
- Artifact exists != promotion ready.
- Capital profile exists != capital bucket proven unless hash/freshness/measured statuses valid.
```

## Fichiers probables

```text
src/cockpit/state_*.py
src/cockpit/templates/
tests/cockpit/
```

## Done criteria

```text
- cockpit displays fidelity/provenance by layer
- no false-green tests pass
- operator sees why promotion is blocked
```

---

# 14. Lot H — Regression Net and Gap Register Lock

## But

Empêcher les régressions.

## Mission

Ajouter ou durcir les tests :

```text
- DAG validity
- no forbidden replay imports
- execution fidelity provenance
- Build-14 influence provenance
- promotion artifact fidelity
- cockpit false-green blockers
- ML label anti-leakage / label source
- capital bucket artifact non-green missing states
```

## Tests recommandés

```bash
python -m pytest tests/test_manifest_registry tests/test_dag_validator -q
python -m pytest tests/test_local_replay_runtime -q
python -m pytest tests/test_execution_backbone -q
python -m pytest tests/test_complete_enablers -q
python -m pytest tests/cockpit -q
python -m pytest tests/test_scoring_backbone tests/test_risk_backbone tests/test_portfolio_minimal -q
```

## Done criteria

```text
- targeted test bands green
- no new DAG/layer violations
- no gap moved to resolved without evidence
- register updated consistently
```

---

# 15. Ordre recommandé

Ne change pas cet ordre sans justification :

```text
0. Phase 0 — Audit pré-exécution
1. Lot A — Execution Fidelity Canon + Register Sync
2. Lot B — Capital Bucket Evidence
3. Lot C — Engine C/D Promotion Evidence
4. Lot D — Replay ↔ Shadow Parity Canon
5. Lot E — ML Governance / Anti-Leakage / Drift
6. Lot F — Microstructure Pair/Regime Calibration
7. Lot G — Cockpit Truth Surface
8. Lot H — Regression Net and Register Lock
```

---

# 16. Ce que Codex doit produire comme première réponse

Avant de coder, produire un plan local :

```text
1. Résumé de l’état repo observé.
2. Lots faisables immédiatement.
3. Lots bloqués par backtest / feature store / live telemetry / human decision.
4. Fichiers cibles par lot.
5. Tests par lot.
6. Risques.
7. Premier patch recommandé.
```

Ne pas prétendre que tout est exécutable immédiatement.

---

# 17. Critère final du chantier

Le chantier n’est pas fini quand les tests passent.  
Il est fini quand chaque résultat V5.3 peut déclarer son niveau de preuve :

```text
DATA_FIDELITY
FEATURE_FIDELITY
ENGINE_INPUT_FIDELITY
ENGINE_RUNTIME_FIDELITY
BUILD14_INFLUENCE_FIDELITY
SCORING_FIDELITY
RISK_FIDELITY
PORTFOLIO_FIDELITY
EXECUTION_FIDELITY
PROMOTION_FIDELITY
ML_LABEL_FIDELITY
REPLAY_SHADOW_PARITY
```

Phrase canonique à garder :

```text
Aucun résultat V5.3 ne peut être qualifié de scientifiquement crédible si son label source, son execution fidelity, sa provenance Build-14, sa validation multi-régime et sa parité replay→shadow ne sont pas explicitement déclarés.
```

---

# 18. Anti-patterns interdits

```text
- Fermer un gap bloqué par backtest sans artifact historique.
- Fermer un gap bloqué par live telemetry sans telemetry.
- Remplacer une preuve manquante par un statut vert.
- Ajouter un nouveau moteur.
- Ajouter un agent IA souverain.
- Créer un nouveau package local_ai_lab.
- Importer venue_adapters/live protocols dans LOCAL_REPLAY.
- Faire grossir les JSON bulk au lieu de Parquet/Arrow pour les datasets.
- Déclarer un capital bucket viable sans capital_profile mesuré.
- Déclarer ML ready sans anti-leakage proof.
- Déclarer C/D ready sans sample-size survival.
- Présenter cost model partial comme complete.
```

---

# 19. Résumé final pour Codex

Tu dois transformer V5.3 de :

```text
backtest fonctionnel mais partiellement proxy
```

vers :

```text
backtest/replay gouverné qui déclare explicitement ce qui est canonique, proxy, partiel, manquant, observé ou promotion-grade
```

Tu ne dois pas rendre V5.3 plus ambitieuse.  
Tu dois la rendre plus honnête.
