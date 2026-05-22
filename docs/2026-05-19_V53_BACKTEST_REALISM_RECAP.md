# V5.3 Backtest Realism Recap

Date: 2026-05-19

## Objet

Ce document résume:

- ce qui a été corrigé dans la chaîne backtest `A1 -> A2 -> B1 -> B2`
- ce qui est maintenant prouvé par les artifacts réels
- ce qui reste bloquant avant d’obtenir un backtest économiquement mesurable
- ce qu’il faut encore fermer avant de pouvoir répondre sérieusement:
  - `V5.3 est rentable`
  - ou
  - `V5.3 n'est pas rentable`

Ce document complète, sans le remplacer:

- [2026-05-18_V53_TRUE_BACKTEST_PROFITABILITY_EXECUTION_PLAN.md](/E:/claude%20%20v5.3/v53_trading_system/docs/2026-05-18_V53_TRUE_BACKTEST_PROFITABILITY_EXECUTION_PLAN.md:1)
- [2026-05-19_V53_EXPECTED_EDGE_PROXY_GATE_ADDENDUM.md](/E:/claude%20%20v5.3/v53_trading_system/docs/2026-05-19_V53_EXPECTED_EDGE_PROXY_GATE_ADDENDUM.md:1)
- [2026-05-19_V53_DATAFACTORY_PRERERUN_B2_AUDIT.md](/E:/claude%20%20v5.3/v53_trading_system/docs/2026-05-19_V53_DATAFACTORY_PRERERUN_B2_AUDIT.md:1)
- [2026-05-20_V53_A2_REUSE_BACKTEST_MANY_DOCTRINE.md](/E:/claude%20%20v5.3/v53_trading_system/docs/2026-05-20_V53_A2_REUSE_BACKTEST_MANY_DOCTRINE.md:1)

## Référence de vérité actuelle

### Workflow frais de référence

Workflow neuf rejoué depuis `A1`:

- `K:\v5.3 backtest\output2\runs\strategy_ladder_workflow-20260519-113403`

Phases:

- `phase_a1_preview`
- `phase_a2_data_factory`
- `phase_b1_candidate_discovery`
- `phase_b2_detailed_replay`

### Artifacts clés

- A2:
  - [data_factory_manifest.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_a2_data_factory/data_factory_manifest.json:1>)
- B1:
  - [preselection_summary.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b1_candidate_discovery/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/reports/preselection_summary.json:1>)
- B2:
  - [run_manifest.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/run_manifest.json:1>)
  - [strategy_ladder_summary.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/reports/strategy_ladder_summary.json:1>)
  - [engine_no_trade_diagnosis.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/reports/engine_no_trade_diagnosis.json:1>)
  - [execution_realism_summary.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/reports/execution_realism_summary.json:1>)

### Verdict actuel

Le workflow de référence est maintenant propre côté orchestration, mais il n’est pas encore économiquement concluant:

- `final_status = STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES`
- `candidate_count = 493`
- `selected_count = 0`
- `executed_count = 0`

Conséquence:

- on ne peut pas encore conclure sur la rentabilité
- on ne peut pas encore valider statistiquement `PSR/DSR/MinTRL`
- on ne peut pas encore promouvoir le backtest comme preuve économique

## Ce qui a été corrigé

## 1. Chaîne workflow `A1 -> A2 -> B1 -> B2`

### Problème initial

Le cockpit et la logique workflow mélangeaient plusieurs `workflow_run_id`.

Effets:

- `B1` repartait parfois sur un autre dossier que `A2`
- `B1` ne retrouvait plus les artifacts `A2`
- `B2` pouvait rejouer un contexte incohérent

### Correctif

La doctrine workflow a été stabilisée:

- un `A1` neuf crée un nouveau workflow
- `A2`, `B1`, `B2` restent dans ce même workflow
- `B1` n’emprunte plus les artifacts `A2` d’un workflow frère

### Ce que ça prouve

Sur le workflow frais `20260519-113403`, la chaîne complète existe sous un seul arbre:

- `phase_a1_preview`
- `phase_a2_data_factory`
- `phase_b1_candidate_discovery`
- `phase_b2_detailed_replay`

Ce faux blocker n’est donc plus le problème.

## 2. `B1 fast_only` ne matérialisait pas le vrai rail natif

### Problème initial

`B1` pouvait s’arrêter trop tôt et ne pas produire:

- `raw windows`
- matérialisation native A/B/C/D
- préselection `B1.5`

### Correctif

Le runner matérialise maintenant bien le rail natif en `B1` quand `engine_native_mode=True`.

### Ce que ça prouve

Sur le workflow frais:

- `engine_native_preselected_count = 493`
- `replay_input_mode_status = PRESELECTED_ONLY`
- `status = ENGINE_NATIVE_PRESELECTION_READY`

Donc `B1` nourrit maintenant un vrai `B2`.

## 3. `B2 detailed_only` ne consommait pas correctement le vrai output `B1.5`

### Problème initial

`B2` pouvait continuer à rejouer des candidats discovery/proxy au lieu du vrai rail `preselection_candidates.jsonl`.

### Correctif

`B2` consomme maintenant le vrai rail `B1.5` natif.

### Ce que ça prouve

Le `run_manifest.json` B2 montre:

- `candidate_source_status = CANDIDATE_SOURCE_ENGINE_NATIVE`
- `candidate_proxy_count = 0`

Donc le backtest ne rejoue plus le mauvais rail.

## 4. Warmup A2 insuffisant pour l’edge OHLCV

### Problème initial

Le slice A2/B2 ne donnait pas assez de contexte OHLCV causal avant `start`.

Effet:

- l’expected-edge tombait artificiellement en fallback
- certains candidats étaient ramenés vers `DEFAULT_TO_CALIBRATE 5.0`

### Correctif

Le data factory matérialise maintenant le contexte causal nécessaire avant la fenêtre logique.

### Ce que ça prouve

Le faux diagnostic de warmup a été retiré.  
Ce problème n’est plus le goulet principal du workflow frais.

## 5. Reconstruction du spread à partir `snapshot + delta`

### Problème initial

Certains candidats avaient:

- `raw_book_delta_path` présent
- mais `measured_spread_report` tombait quand même en snapshot stale

Cause réelle:

- le delta slice commençait à `window_start_ms`
- alors que la reconstruction du book était ancrée sur un snapshot plus ancien
- il manquait donc les deltas intermédiaires nécessaires entre le snapshot et la fenêtre logique

### Correctif

Le slice `orderbook_delta` démarre maintenant à l’ancre snapshot utile, pas seulement à `window_start_ms`.

### Exemple réel

Le candidat:

- [e839d2f6ec86b86d934b26f4.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/detailed_replay/shared/e839d2f6ec86b86d934b26f4.json:1>)

a servi à prouver que:

- le delta n’était pas ignoré
- il était utilisé avec un slice incomplet

### Ce que ça prouve

Le faux problème “book delta ignoré” a été retiré.  
La reconstruction spread est maintenant beaucoup plus fidèle.

## 6. `engine_c` recevait des fenêtres tronquées avant breakout

### Problème initial

`engine_c` voyait des breakouts “déjà tardifs” parce que ses fenêtres B2 n’embarquaient pas assez d’historique pré-break.

### Correctif

Le raw-window extractor ajoute maintenant le vrai lookback structurel nécessaire à `engine_c`.

### Ce que ça prouve

Le faux diagnostic “late breakout” causé uniquement par une fenêtre tronquée a été retiré.

## 7. Parité synthétique `direct -> builder -> B2`

### But

Éviter un diagnostic biaisé du type:

- “le moteur marche en direct”
- “donc s’il échoue en B2, le moteur est cassé”

### Résultat

Après harness de parité:

- `A`: direct = builder = B2
- `B`: direct = builder = B2
- `C`: passe aussi en B2 quand le cas synthétique est builder-compatible
- `D`: passe aussi en B2 quand le contexte builder est correctement fourni

### Ce que ça prouve

Le problème principal restant n’est plus:

- “B2 casse les moteurs”

Le problème principal est:

- qualité des fenêtres réelles
- qualité des coûts/provenances
- absence d’exécutions réelles

## 8. Post-window OHLCV manquant pour les labels replay-grounded

### Problème initial

Le candidat:

- [4698cb67485ea5a8a6a8f2fe.json](<K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-20260519-113403/phase_b2_detailed_replay/backtest_strategy_ladder/strategy_ladder_workflow-20260519-113403/detailed_replay/shared/4698cb67485ea5a8a6a8f2fe.json:1>)

montrait:

- `REPLAY_OUTCOME_BLOCKED_BY_MISSING_POST_WINDOW`
- `MFE_MAE_BLOCKED_BY_MISSING_POST_WINDOW`
- `forward_return_h1 = null`
- `forward_return_h5 = null`
- `forward_return_h10 = null`
- `mfe_bps = null`
- `mae_bps = null`

Cause réelle:

- le candidat est en `15m`
- la fenêtre logique ne laissait que `+5 min`
- le replay outcome demande des barres futures `h1/h5/h10`
- le slice OHLCV matérialisé s’arrêtait exactement sur la bougie de décision

### Correctif

Le raw-window extractor garde maintenant le `window_end_ms` logique dans le manifest, mais matérialise assez de bougies futures OHLCV pour couvrir les horizons replay.

### Ce que ça prouve

Le bug est fermé en code et en test unitaire.  
Le rerun réel du workflow doit finir pour que l’artifact `4698cb...` soit régénéré avec ce nouveau contrat.

## Ce qui est maintenant prouvé

## 1. L’orchestration backtest est saine

Sur le workflow frais:

- la chaîne `A1 -> A2 -> B1 -> B2` tient dans un seul workflow
- `B1` produit bien un vrai rail natif
- `B2` consomme bien ce rail natif

## 2. Le backtest `ML_MODE_OFF` sépare bien le problème canonique du problème ML

Le rerun sans ML overlay montre que:

- le faux blocage `TIMEFRAME_SLICE_NOT_READY` n’est pas le problème principal du cœur canonique
- même sans ML overlay, on reste à `0 executed trades`

Donc:

- le problème principal n’est plus le cockpit
- le problème principal n’est plus le wiring A2/B1/B2
- le problème principal n’est plus le multiframe bundle

## 3. Le verdict économique n’est pas encore possible

À ce stade, la vérité honnête est:

- le pipeline tourne
- plusieurs faux blockers ont été retirés
- mais le backtest ne produit encore aucun trade exécuté

Donc:

- rentabilité: `non prouvée`
- non-rentabilité: `non prouvée`
- vérité actuelle: `pipeline canonique encore bloqué avant exécution`

## Ce qui reste bloquant

## 1. `NO_EXECUTED_TRADES`

C’est le blocker principal.

Tant qu’on a:

- `selected_count = 0`
- `executed_count = 0`

on ne peut pas mesurer:

- PnL net exécuté
- adverse selection réelle
- validation statistique sérieuse

## 2. `EXPECTED_EDGE_PROXY_BLOCKED`

Le cœur canonique reste encore appuyé sur un expected-edge qui n’est pas promotion-grade backtest truth.

Effets:

- `EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH`
- `EXPECTED_EDGE_PROXY_BLOCKED`
- `FEE_AWARE_EDGE_PROXY_BLOCKED`
- `BREAK_EVEN_PROXY_BLOCKED`

Conséquence:

- même avec un pipeline propre, la décision économique reste en partie proxy

## 3. `SPREAD_MODEL_PROXY`

Le spread est mieux reconstruit qu’avant, mais pas encore totalement mesuré pour tous les cas.

Sur le workflow frais, le rapport realism montre encore un mélange de:

- `SPREAD_MEASURED_FROM_BOOK`
- `SPREAD_MEASURED_STALE_AUDIT_ONLY`
- et fallback/proxy selon les candidats

Conséquence:

- la chaîne coût n’est pas encore entièrement promotion-grade

## 4. `SLIPPAGE_MODEL_PROXY`

Le calcul et le câblage ont été améliorés, mais il reste encore des cas où:

- le slippage n’est pas suffisamment mesuré depuis la microstructure réelle
- ou retombe vers des fallback/calibration proxies

Conséquence:

- le coût d’exécution n’est pas encore entièrement mesuré

## 5. `ADVERSE_SELECTION_PROXY`

Tant qu’il n’y a pas de trades exécutés:

- pas d’adverse selection réellement mesurable
- seulement un blocage logique de preuve

Conséquence:

- la realism économique reste partielle

## 6. `engine_d history_weak`

Le journal d’épisodes clos reste vide ou insuffisant pour `engine_d`:

- `closed_episode_manifest.json` reste une surface critique

Conséquence:

- `engine_d` peut rester légitimement bloqué
- ce n’est pas forcément un bug, mais un manque de preuve historique exploitable

## 7. Validation statistique impossible

Sans trades exécutés:

- `PSR`
- `DSR`
- `MinTRL`
- `effective sample size`

ne peuvent pas produire un verdict utile.

Donc le blocage statistique est cohérent.

## État scientifique honnête

Ce que l’on peut dire aujourd’hui:

- le backtest V5.3 est maintenant beaucoup plus propre techniquement
- plusieurs faux blocages d’infrastructure ont été retirés
- plusieurs bugs de slicing/reader ont été corrigés
- mais le système n’a toujours pas produit de vérité économique exécutable

Ce que l’on ne peut pas encore dire:

- `V5.3 est rentable`
- `V5.3 n'est pas rentable`
- `le ML améliore réellement la performance`

## Définition de done pour un backtest économiquement mesurable

On considérera que le backtest devient économiquement mesurable seulement si:

1. `A1 -> A2 -> B1 -> B2` reste propre sur un workflow neuf
2. `B2 ML_MODE_OFF` produit `selected > 0`
3. `B2 ML_MODE_OFF` produit `executed > 0`
4. les coûts clés ne sont plus principalement proxy:
   - spread
   - slippage
   - adverse selection
5. `forward_return / MFE / MAE` sont réellement mesurés sur les fenêtres utiles
6. les reports deviennent statistiquement exploitables

## Priorités restantes

### Priorité P0

Obtenir les premiers `selected` puis `executed` sur le rail canonique `ML_MODE_OFF`.

### Priorité P1

Réduire les restes de:

- `EXPECTED_EDGE_PROXY_BLOCKED`
- `BREAK_EVEN_PROXY_BLOCKED`
- `FEE_AWARE_EDGE_PROXY_BLOCKED`

### Priorité P2

Finir la chaîne realism:

- spread
- slippage
- adverse selection

### Priorité P3

Une fois le rail canonique prouvé, revenir au ML overlay avec des labels replay-grounded promotion-grade.

## Résumé final

La situation actuelle n’est plus:

- `le backtest est cassé`

La situation actuelle est:

- `le backtest gouverné tourne`
- `les faux bugs d’orchestration majeurs ont été retirés`
- `plusieurs faux bugs de slicing/reader ont été retirés`
- `le système reste économiquement non concluant car il n’exécute encore aucun trade`

Le vrai chantier restant est maintenant:

- transformer un backtest techniquement propre
- en un backtest avec exécutions réelles
- puis en un backtest économiquement et statistiquement défendable
