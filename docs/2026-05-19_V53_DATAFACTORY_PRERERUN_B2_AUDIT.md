# V5.3 DataFactory Pre-Rerun B2 Audit

Date: 2026-05-19

## Objet

Ce document fige trois choses pour le workflow frais:

- l'audit verifie des constats `A2 datafactory` avant un nouveau rerun reel `B2`
- la correction deja codee sur le chemin `engine_a` qui doit etre incluse dans le prochain rerun
- le prochain pas exact avant de relancer `B2`

Workflow de reference:

- `K:\v5.3 backtest\output2\runs\strategy_ladder_workflow-20260519-113403`

Sources de verite principales:

- A2: [data_factory_manifest.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_a2_data_factory/data_factory_manifest.json:1>)
- A2: [raw_source_report.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_a2_data_factory/raw_source_report.json:1>)
- A2: [silver_quality_report.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_a2_data_factory/silver_quality_report.json:1>)
- A2: [expected_edge_feature_manifest.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_a2_data_factory/expected_edge_feature_manifest.json:1>)
- A2: [runtime_feature_parity_manifest.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_a2_data_factory/runtime_feature_parity_manifest.json:1>)
- B2: [strategy_ladder_summary.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/reports/strategy_ladder_summary.json:1>)
- B2: [run_manifest.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/run_manifest.json:1>)
- B2: [expected_edge_readiness_audit.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/reports/expected_edge_readiness_audit.json:1>)

## Resume executif

Verdict court:

- l'audit externe contient plusieurs points corrects
- un point est faux tel qu'ecrit
- plusieurs points sont reels mais ne bloquent pas mecaniquement un rerun `B2`
- deux points meritent une action avant un rerun `B2` propre:
  - l'ambiguite de `run_manifest.json` zombie en `phase_b2_detailed_replay`
  - la non-propagation des blockers `silver` vers le top-level `data_factory_manifest.json` si un consommateur aval ne lit que le manifest top-level

Verdict operationnel:

- un rerun `B2` est possible techniquement
- mais il n'est pas encore propre audit-ready tant que le consommateur peut lire le mauvais `run_manifest` ou croire que `A2` est clean en lisant seulement le manifest top-level

## Correction deja codee a embarquer dans le prochain rerun

Correction sauvegardee:

- [strategy_ladder_engine_a_input_builder.py](/E:/claude%20%20v5.3/v53_trading_system/src/local_replay_runtime/strategy_ladder_engine_a_input_builder.py:1)
- test: [test_strategy_ladder_engine_a_input_builder.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_local_replay_runtime/test_strategy_ladder_engine_a_input_builder.py:1)

Probleme corrige:

- le builder `engine_a` diluait un breakout recent propre dans un `lookback` trop long
- consequence: faux negatif `structure_unfavorable` dans `B2`

Preuve reelle sur le candidat:

- [e839d2f6ec86b86d934b26f4.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/detailed_replay/shared/e839d2f6ec86b86d934b26f4.json:1>)

Avant patch:

- `direction_score = 0.1349`
- `continuation_score = 0.0`

Apres patch sur ce meme cas reel:

- `direction_score = 0.5108`
- `continuation_score = 0.7`
- verdict moteur `engine_a = emit`

Conclusion:

- le prochain rerun `B2` doit inclure ce patch `engine_a`

## Verification point par point de l'audit DataFactory

### #2 Raw source venue INFERRED, pas VERIFIED

Verdict: `CORRECT`

Preuve:

- [raw_source_report.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_a2_data_factory/raw_source_report.json:1>) contient `RAW_SOURCE_TYPE_INFERRED`
- [data_factory_manifest.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_a2_data_factory/data_factory_manifest.json:1>) contient `raw_source_manifest_path = ""`

Impact rerun B2:

- `NON_BLOQUANT_POUR_RERUN_B2`
- `BLOQUANT_POUR_PREUVE_DE_PROVENANCE`

### #3 Bronze gaps masques par l'agregateur

Verdict: `CORRECT`

Preuve:

- [silver_quality_report.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_a2_data_factory/silver_quality_report.json:1>) expose:
  - `silver_sync_status = SILVER_SYNC_PARTIAL`
  - `bronze_gap_count = 20`
  - `blocker_codes = ["BRONZE_GAPS_PRESENT", "BRONZE_SCHEMA_BLOCKER"]`
- mais [data_factory_manifest.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_a2_data_factory/data_factory_manifest.json:1>) a `blocker_codes = []`

Impact rerun B2:

- `CONDITIONNELLEMENT_BLOQUANT_AVANT_RERUN_B2`
- si le rerun est pilote par un consommateur qui lit seulement le top-level manifest, il peut croire a tort que `A2` est sans blockers
- si l'operateur lit les sous-rapports, le rerun reste possible

### #4 Metadata anachronique

Verdict: `CORRECT`

Preuve:

- [data_factory_manifest.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_a2_data_factory/data_factory_manifest.json:1>) contient `metadata_temporal_status = CURRENT_METADATA_PROXY`

Impact rerun B2:

- `NON_BLOQUANT_POUR_RERUN_B2`
- `BLOQUANT_POUR_FIDELITE_ECONOMIQUE_STRICTE`

### #5 Purge/embargo = 0 dans le manifest A2 mais 1/1 dans l'audit B2

Verdict: `CORRECT`

Preuve:

- [expected_edge_feature_manifest.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_a2_data_factory/expected_edge_feature_manifest.json:1>) contient:
  - `purge_window_minutes = 0`
  - `embargo_window_minutes = 0`
- [expected_edge_readiness_audit.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/reports/expected_edge_readiness_audit.json:1>) contient:
  - `purge_window_minutes = 1`
  - `embargo_window_minutes = 1`

Impact rerun B2:

- `NON_BLOQUANT_POUR_RERUN_B2`
- `BLOQUANT_POUR_DOCTRINE_ML_ANTI_LEAKAGE`

### #6 Features training-time decorellees des features engines

Verdict: `MATERIELLEMENT_CORRECT`

Preuve:

- [expected_edge_feature_manifest.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_a2_data_factory/expected_edge_feature_manifest.json:1>) expose:
  - `feature_names = ["close_return", "high_low_range", "volume"]`
  - `feature_groups_generated` avec microstructure, cost context, fragility, etc.

Impact rerun B2:

- `NON_BLOQUANT_POUR_RERUN_B2`
- `BLOQUANT_POUR_P0_A_EXPECTED_EDGE_GOVERNED_TRUTH`

### #7 runtime_feature_parity_manifest = RUNTIME_PARITY_NOT_PROVEN

Verdict: `CORRECT`

Preuve:

- [runtime_feature_parity_manifest.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_a2_data_factory/runtime_feature_parity_manifest.json:1>) expose `RUNTIME_PARITY_NOT_PROVEN`

Impact rerun B2:

- `NON_BLOQUANT_POUR_RERUN_B2`
- `BLOQUANT_POUR_PREUVE_TRAINING_VS_RUNTIME`

### #8 Single-pair sur un systeme doctrine multi-pair

Verdict: `CORRECT_AVEC_NUANCE`

Preuve:

- [raw_source_report.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_a2_data_factory/raw_source_report.json:1>) montre:
  - `requested_pairs = ["BTCUSDT"]`
  - `detected_pairs` metadata plus large
  - `ignored_source_pairs` multiples

Impact rerun B2:

- `NON_BLOQUANT_POUR_RERUN_B2_SUR_BTC`
- `BLOQUANT_POUR_CLAIM_DE_GENERALISATION_MULTI_PAIR`

### #9 raw_source_manifest_path vide

Verdict: `CORRECT`

Preuve:

- [data_factory_manifest.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_a2_data_factory/data_factory_manifest.json:1>) expose `raw_source_manifest_path = ""`

Impact rerun B2:

- `NON_BLOQUANT_POUR_RERUN_B2`
- `BLOQUANT_POUR_REPRODUCTIBILITE_FORTE`

### #10 A1 a silver_synchronized_market_manifest.json mais A2 ne l'a pas

Verdict: `FALSE_SUR_CE_WORKFLOW`

Preuve:

- `phase_a1_preview` contient `silver_synchronized_market_manifest.json`
- `phase_a2_data_factory` contient aussi `silver_synchronized_market_manifest.json`

Rewrite correct:

- il reste pertinent de verifier la coherence de contenu entre `A1` et `A2`
- mais l'affirmation `A2 ne l'a pas` est fausse

Impact rerun B2:

- `NON_BLOQUANT`

### #11 run_manifest zombie contradictoire

Verdict: `CORRECT_ET_CRITIQUE`

Preuve:

- [run_manifest.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/run_manifest.json:1>) dit:
  - `final_status = STRATEGY_LADDER_BLOCKED_BY_RAW_WINDOWS`
  - `raw_window_count = 0`
  - `candidate_source_status = CANDIDATE_SOURCE_NOT_PROVEN`
  - `phase_run_id = ""`
- [strategy_ladder_summary.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/reports/strategy_ladder_summary.json:1>) dit:
  - `final_status = STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES`
  - `raw_window_count = 493`
  - `candidate_source_status = CANDIDATE_SOURCE_ENGINE_NATIVE`
  - `phase_run_id = manual_phase_b2_fresh_20260519_113403`

Impact rerun B2:

- `BLOQUANT_AVANT_RERUN_B2_PROPRE`
- un consommateur downstream peut lire le zombie et conclure faux

### #12 detailed_replay_count = 1972 mais 2958 fichiers .json

Verdict: `PARTIELLEMENT_CORRECT`

Preuve:

- [strategy_ladder_summary.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/reports/strategy_ladder_summary.json:1>) dit `detailed_replay_count = 1972`
- le filesystem contient `2958` fichiers `.json` dans `detailed_replay`
- dont `493` dans `detailed_replay/shared`

Interpretation:

- il y a visiblement plusieurs classes de fichiers artifact dans `detailed_replay`
- l'audit a raison de demander une semantique explicite
- mais il ne prouve pas a lui seul une corruption du count replay

Impact rerun B2:

- `NON_BLOQUANT_POUR_RERUN_B2`
- `BLOQUANT_POUR_LISIBILITE_AUDIT`

### #13 raw_windows B1 = 2906 fichiers, B2 = 1722 fichiers

Verdict: `CORRECT_MAIS_EXPLICABLE`

Preuve:

- B1 raw windows total files = `2906`
- B2 raw windows total files = `1722`
- B1 travaille sur `1000` candidats
- B2 travaille sur `493` candidats

Interpretation:

- l'asymetrie existe
- elle est partiellement explainable par la reduction `1000 -> 493`
- il manque quand meme un manifest explicite de passage de sous-ensemble

Impact rerun B2:

- `NON_BLOQUANT_POUR_RERUN_B2`
- `BLOQUANT_POUR_TRAIT_D_UNION_EXPLICITE_B1_VERS_B2`

### #14 Duplication ml_label_store B1 et B2 avec naming "b2"

Verdict: `CORRECT`

Preuve:

- B1: `strategy_ladder_b2_label_store.jsonl` existe mais `Length = 0`
- B2: `strategy_ladder_b2_label_store.jsonl` existe et `Length = 3561868`

Impact rerun B2:

- `NON_BLOQUANT_POUR_RERUN_B2`
- `BLOQUANT_POUR_SOURCE_OF_TRUTH_LABEL_STORE`

### #15 Fichiers ledger presents mais vides

Verdict: `CORRECT`

Preuve:

- `closed_episodes.jsonl = 0 bytes`
- `trade_detail_ledger.jsonl = 0 bytes`
- `loss_analysis_ledger.jsonl = 0 bytes`

Impact rerun B2:

- `NON_BLOQUANT_POUR_RERUN_B2`
- `BLOQUANT_POUR_EVIDENCE_HYGIENE`

### #16 Gold storage non-compresse

Verdict: `CORRECT`

Preuve:

- les fichiers `gold` sont en `.jsonl`
- pas en `.jsonl.gz`

Impact rerun B2:

- `NON_BLOQUANT_POUR_RERUN_B2`
- `BLOQUANT_POUR_SCALABILITE`

### #17 Pas de partition mensuelle agregee

Verdict: `PROBABLEMENT_CORRECT`

Preuve:

- layout observe par jour sous `year/month/day`
- pas de partition mensuelle agregee visible

Impact rerun B2:

- `NON_BLOQUANT_POUR_RERUN_B2`
- `BLOQUANT_POUR_SCALABILITE_LONGUE_FENETRE`

## Ce qui bloque reellement avant un rerun B2 propre

### P0 - a fermer avant rerun reel

1. `run_manifest` zombie en `phase_b2_detailed_replay`
- il faut soit le supprimer
- soit l'ecraser par le run canonique
- soit imposer un selecteur canonique par `phase_run_id` non vide

2. Propagation des blockers `silver` vers le top-level `data_factory_manifest`
- tant que `BRONZE_GAPS_PRESENT` et `BRONZE_SCHEMA_BLOCKER` sont visibles seulement en sous-rapport, un orchestrateur peut relancer `B2` sur une lecture faussement verte

### P1 - ne bloque pas le rerun, mais bloque la lecture economique serieuse

- `CURRENT_METADATA_PROXY`
- `RAW_SOURCE_TYPE_INFERRED`
- `RUNTIME_PARITY_NOT_PROVEN`
- mismatch purge/embargo
- features training-time trop pauvres vs moteurs
- label-store naming ambigu
- ledgers vides sans header de statut

## Prochain pas exact

Avant de relancer `B2` reel:

1. corriger la canonicalisation `run_manifest` B2 pour eliminer l'artifact zombie
2. corriger la propagation des blockers `silver` vers le top-level manifest `A2`
3. garder la correction `engine_a` dans le rerun
4. seulement ensuite relancer un `B2 ML_MODE_OFF` frais sur le workflow `20260519-113403`

## Position finale

Le diagnostic externe n'est ni totalement faux ni totalement exploitable en brut.

La lecture correcte est:

- plusieurs points sont justes et utiles
- un point au moins est faux tel qu'ecrit
- la plupart des gaps sont des gaps de preuve, de gouvernance ou de scalabilite
- les vrais prealables immediats avant un rerun `B2` propre sont surtout:
  - la canonicalisation du `run_manifest` B2
  - la propagation des blockers `A2`
  - l'inclusion du patch `engine_a`
