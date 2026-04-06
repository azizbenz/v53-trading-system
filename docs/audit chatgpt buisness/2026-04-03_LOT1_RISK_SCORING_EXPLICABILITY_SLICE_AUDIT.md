# 2026-04-03 - Lot 1 risk/scoring explicability slice audit

## Objet

Ce document fige la **premiere tranche codee** du `Lot 1` du backlog
`V53_STRATEGY_ENRICHMENT_BACKLOG_CODE_FIRST.md`.

But de cette tranche:
- rendre `risk_backbone` plus explicable via des **codes stables**
- rendre `scoring_backbone` plus racontable via une **lecture dominante**
- pousser cette lecture jusque dans:
  - les artefacts `LOCAL_REPLAY -> SHADOW`
  - les cartes `Engines` du dashboard technique

## Scope livre

### 1. Build-4 risk_backbone

Le contrat `RiskEvaluation` expose maintenant:
- `reason_details`
- `dominant_reason_code`
- `explain_summary`

Les codes stables couverts par cette tranche sont:
- `RISK_POSITION_CAP`
- `RISK_GROSS_CAP`
- `RISK_NO_LOSS_ESTIMATE`
- `RISK_LOSS_CAP`
- `RISK_BETA_CAP`
- `RISK_CLUSTER_CAP`
- `RISK_CLUSTER_MAPPING_MISSING`
- `RISK_DRAWDOWN_REDUCE`
- `RISK_DRAWDOWN_OBSERVE`

Ces codes sont derives a partir des verdicts canoniques deja existants, sans creer une
nouvelle logique de risque parallele.

### 2. Build-5 scoring_backbone

Le contrat `ScoringCandidateAudit` expose maintenant:
- `explainability.dominant_feature_keys`
- `explainability.dominant_score_penalty_ids`
- `explainability.dominant_size_penalty_ids`
- `explainability.hard_block_codes`
- `explainability.portfolio_verdict_code`
- `explainability.selection_outcome_code`
- `explainability.summary`

Cette tranche permet donc de raconter, candidat par candidat:
- quelles features ont le plus pese
- quelles penalites dominent
- si un hard block a coupe le flux
- si le portefeuille a rejete
- comment la selection finale a tranche

### 3. Artifacts LOCAL_REPLAY -> SHADOW

Le sidecar:
- `local_replay_shadow.engine_shadow_evidence.json`

embarque maintenant aussi:
- `scoring_summary`
- `risk_summary`
- `scoring_reason_codes`
- `risk_reason_codes`

Le payload technique genere depuis `run_local_replay_shadow.py` transporte aussi ces
resumes au niveau `engines`.

### 4. UI / monitoring

`EngineMetrics` transporte maintenant:
- `scoring_summary`
- `risk_summary`
- `scoring_reason_codes`
- `risk_reason_codes`

Le dashboard technique les rend visibles dans les cartes `Engines`.

## Fichiers touches

### Code
- `src/risk_backbone/risk_runtime.py`
- `src/scoring_backbone/scoring_runtime.py`
- `src/monitoring/contracts.py`
- `src/monitoring/metrics_collector.py`
- `src/ui/technical_dashboard_view.py`
- `scripts/run_local_replay_shadow.py`

### Tests
- `tests/test_risk_backbone/test_risk_runtime.py`
- `tests/test_scoring_backbone/test_scoring_runtime.py`
- `tests/test_protocols/test_local_replay_shadow_runner.py`
- `tests/test_ui/test_technical_dashboard.py`

## Ce que la tranche rend possible

On peut maintenant voir plus explicitement:
- pourquoi un candidat a ete refuse par le risque
- quelle contrainte risque a domine
- quelles features ont porte le score
- quelles penalites ont le plus pese
- si le rejet final vient du hard block, du portefeuille ou du ranking

Cela reduit le risque d'enrichir V5.3 "au hasard", en confondant:
- probleme d'alpha
- probleme de cout
- probleme de penalites
- probleme portefeuille
- probleme de risque dur

## Ce qui reste ouvert

Cette tranche ne clot pas tout le `Lot 1`.

Reste notamment a faire:
- pousser ces raisons de facon plus directe dans `meta_learning`
- etendre les exports replay sous une forme plus analytique que le simple payload moteur
- agreger les motifs dominants au niveau `Build-9X`
- projeter ces raisons au niveau `Pairs` / `Risk` / `Replay & Import`, pas seulement `Engines`

## Verification

Verification ciblee:
- `tests/test_risk_backbone/test_risk_runtime.py`
- `tests/test_scoring_backbone/test_scoring_runtime.py`
- `tests/test_protocols/test_local_replay_shadow_runner.py`
- `tests/test_ui/test_technical_dashboard.py`
- `tests/test_ui/test_technical_dashboard_launcher.py`
- `tests/test_manifest_registry/test_runtime_surface.py`

Verification elargie:
- `tests/test_risk_backbone/test_risk_integration.py`
- `tests/test_scoring_backbone/test_scoring_integration.py`
- `tests/test_engines/test_engine_a/test_engine_a_runtime.py`
- `tests/test_engines/test_engine_b/test_engine_b_runtime.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py`

## Verdict

Verdict honnête:
- **tranche Lot 1 livree et observable**
- **canon preserve**
- **aucun nouveau moteur**
- **aucun bypass Shadow/Micro-live/Live**

Mais:
- `Lot 1` complet reste **ouvert**
- cette livraison est une **premiere tranche explicabilite runtime + UI + artifacts**
