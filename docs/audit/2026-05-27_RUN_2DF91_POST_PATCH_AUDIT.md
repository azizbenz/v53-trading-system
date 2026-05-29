# Audit post-patch du run `strategy_ladder_workflow-2df91d9d5c48dfbf`

Date: 2026-05-27  
Run root: `L:\output backtest\runs\strategy_ladder_workflow-2df91d9d5c48dfbf`

## Verdict court

Le run est techniquement complet jusqu'a B2: A1, A2, B1 et B2 ont produit leurs artifacts. Le patch a donc ameliore le pipeline: B2 n'est plus vide, le label store existe, les rapports decision/cost/threshold sont produits.

Mais le run reste `research-only`, non promotion-ready, et ne peut pas repondre "V5.3 est rentable" de maniere defendable.

Verdicts principaux:

- `BACKTEST_DECISION_REPORT_PARTIAL`
- `PROFITABILITY_VERDICT_BLOCKED_PROXY`
- `profitability_claim_allowed=false`
- `B2_LABEL_STORE_BLOCKED_BY_TARGET_POLICY_MISMATCH`
- `CALIBRATION_PREMATURE_COST_FILL_NOT_READY`

## Statut workflow

`workflow_manifest.json` indique une sequence complete:

- `PHASE_A1`
- `PHASE_A2`
- `PHASE_B1`
- `PHASE_B2`

Statuts phase:

- A1: `PHASE_A1_PREVIEW_READY`
- A2: `PHASE_A2_DATA_FACTORY_READY`
- B1: `PHASE_B1_CANDIDATE_DISCOVERY_READY`
- B2: `PHASE_B2_DETAILED_REPLAY_READY`

Scope:

- pair: `BTCUSDT`
- timeframe: `15m`
- periode: `2025-07-25 -> 2025-07-26`
- ML mode: `ML_MODE_OFF`
- candidate discovery: `TEMPORAL_STRATIFIED`

## Resultat A2/B1/B2

### A2

A2 est utilisable pour recherche:

- `DATA_FACTORY_READY`
- `SILVER_INDEX_READY`
- `FEATURE_STORE_READY`
- storage effectif: `jsonl_gz`

Blockers A2 conserves:

- `RAW_SOURCE_TYPE_INFERRED`
- `CURRENT_METADATA_PROXY`
- `SINGLE_PAIR_RESEARCH_ONLY`

Donc A2 est bon pour continuer le diagnostic, mais pas encore prod-safe.

### B1

B1 a produit:

- `candidate_count=200`
- `engine_native_candidate_count=200`
- 50 candidats par engine A/B/C/D
- `engine_native_preselected_count=97`
- `preselection_hard_rejected_count=103`

Point important: B1 reste large. Il propose des pre-candidats/candidats natifs, mais B2 revalide ensuite la decision engine reelle. C'est normal dans le nouveau workflow, mais cela explique pourquoi beaucoup de lignes B1 tombent en `no_trade` dans B2.

### B2

B2 a produit:

- `b2_replay_candidate_count=97`
- `raw_window_count=200`
- `trade_windows_found=200`
- `book_windows_found=200`
- `ohlcv_windows_found=200`
- `depth20_found=104`
- `depth20_missing=96`
- `replay_record_count=388`
- `capital_bucket_record_count=388`
- `label_store row_count=388`

Le replay est donc reellement materialise. Le probleme n'est plus "B2 ne produit rien"; le probleme est la fidelite/proxy et l'insuffisance statistique.

## Trades et selection

Les compteurs ont deux granularites:

- niveau capital bucket / matrices: `selected_count=4`, `executed_count=4`
- niveau decision report consolide: `selected_count=1`, `executed_count=1`

Ce n'est pas une contradiction: une selection candidate peut etre expandue en 4 buckets de capital (`400`, `500`, `1500`, `4000`). Les matrices comptent les records bucketises; le decision report consolide la decision operateur.

Resultat:

- 1 candidat reellement selectionne au niveau operateur
- 4 executions bucketisees
- les 4 executions sont perdantes dans la matrice timeframe
- `win_count=0`
- `loss_count=4`
- `net_pnl_bps=-46.04`
- `avg_loss_bps=-11.51`

Ce resultat est insuffisant pour conclure. Ce n'est pas une preuve de non-rentabilite, c'est un echantillon trop petit et encore partiellement proxy.

## Pourquoi les blockers restent presents malgre le calcul des features

### 1. Les features existent, mais l'expected edge n'est pas encore gouverne

Le summary dit:

- `expected_edge_proxy_count=200`
- `expected_edge_governed_count=0`
- `expected_edge_model_status=EXPECTED_EDGE_MODEL_NOT_REQUESTED`
- `expected_edge_label_source=PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE`
- `expected_edge_label_fidelity=EXPECTED_EDGE_PROXY_DISCOVERY_ONLY`

Donc meme si A2/B2 calculent des features, il n'y a pas encore d'artifact ML expected-edge OOS gouverne branche dans ce run. Le blocker `EXPECTED_EDGE_PROXY_BLOCKED` est donc normal.

### 2. Cost/fill reste partiel

`execution_realism_summary.json`:

- spread mesure depuis book: 196 / 388
- spread bloque par book manquant: 192 / 388
- slippage estime depth20: 196 / 388
- slippage bloque depth20 manquant: 192 / 388
- fill realism proven: 0
- `FILL_REALISM_PARTIAL_REPLAY`: 4
- `FILL_REALISM_NOT_PROVEN`: 384

Donc `PARTIALLY_MEASURED`, `SPREAD_MODEL_PROXY`, `SLIPPAGE_MODEL_PROXY` et `ADVERSE_SELECTION_PROXY` restent legitimes. On a une moitie de replay avec book/depth, mais pas une chaine complete promotion-grade.

### 3. Label store B2 existe, mais pas training-ready

`b2_label_store_ml_training_audit.json`:

- `row_count=388`
- `feature_count=25`
- `label_count=10`
- `training_row_eligible_count=0`
- `training_row_research_only_count=384`
- `training_row_blocked_count=4`
- `target_policy_mismatch_count=388`
- `replay_grounded_label_count=4`
- `proxy_label_count=384`
- `cost_aware_label_count=0`
- `fill_realism_proven_count=0`
- `scientifically_valid_for_training=false`
- `scientifically_valid_for_promotion=false`

Le label store n'est donc pas utilisable pour produire un artifact expected-edge promotion-ready. Il peut servir a l'audit/recherche, mais pas a entrainer un modele "truth" pour live/shadow.

### 4. F16 progresse mais reste incomplet

`ml_label_store/f16_feature_coverage_report.json`:

- `row_count=388`
- `full_feature_row_count=0`
- `full_feature_coverage_rate=0.0`
- statut: `F16_FEATURE_COVERAGE_BLOCKED`

Features full:

- `close_return`
- `high_low_range`
- `volume`
- `spread_bps`
- `slippage_bps`
- `book_depth_levels`
- `break_even_bps`
- `fragility_score`
- `false_breakout_context`
- `vpin`
- `kyle_lambda`
- `realized_vol_current`
- `realized_vol_at_break`
- `latency_penalty_bps`

Features partielles:

- `cumulative_ofi`: 196 / 388
- `queue_pressure`: 196 / 388
- `micro_edge_exit_governor_observed`: 200 / 388
- `micro_edge_entry_timing_observed`: 200 / 388
- `history_score`: 200 / 388
- `marginal_value_score`: 200 / 388
- `reentry_lateness`: 200 / 388
- `concentration_headroom`: 200 / 388

Features absentes:

- `anti_revenge_state__active`: 0 / 388
- `anti_revenge_state__cooling`: 0 / 388
- `anti_revenge_state__idle`: 0 / 388

Conclusion F16: le patch a propage beaucoup de microstructure, mais le full F16 reste bloque surtout par anti-revenge et par couverture partielle book/depth/engine-D.

## Analyse engine

Engines dans les matrices B2:

- `engine_a`: 50 candidats, 4 executes bucketises, 4 pertes, promotion bloquee.
- `engine_b`: 50 candidats, 0 execute, 120 hard blocked.
- `engine_c`: absent des matrices promotion finales, car aucun replay executable retenu.
- `engine_d`: 50 candidats, 0 execute, 200 hard blocked; artifacts Engine D non prouves.

`candidate_trade_semantics_audit.json` montre:

- `ENGINE_NATIVE_CANDIDATE`: 1
- `ENGINE_NATIVE_NO_TRADE`: 196
- `HARD_BLOCKED_CANDIDATE`: 3
- dominant gate: `adverse_selection_layer`
- `no_trade_rate=0.98`

Donc le vrai enseignement B2: la majorite des candidats B1 ne deviennent pas des trades natifs apres revalidation B2.

## No-shadow threshold challenge

Verdict:

- `CALIBRATION_PREMATURE_COST_FILL_NOT_READY`
- `shadow_used=false`
- `trading_decisions_modified=false`
- `selected_count_after_counterfactual=0`
- `executed_count_after_counterfactual=0`

Dominant blockers en governance-preserving:

- `EXPECTED_EDGE_PROXY_BLOCKED`
- `EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH`
- `FEE_AWARE_EDGE_PROXY_BLOCKED`
- `BREAK_EVEN_PROXY_BLOCKED`
- `break_even_not_cleared`

Conclusion: ce run ne justifie pas de patch threshold. Meme si on challenge les seuils offline, les candidats ne survivent pas aux blockers gouvernes.

## Performance du run

`replay_performance_profile.json`:

- total wall time: `2041.84s` environ 34 minutes
- total CPU time: `1958.91s`
- rows processed: `1,840,984`
- files scanned: `11`
- replay workers: `0`
- parquet fast path: `PARQUET_REPLAY_NOT_PROVEN`

Principaux couts:

- `raw_window_extraction`: `928.72s`
- `jsonl_parsing`: `926.73s`
- `no_shadow_threshold_challenge_generation`: `189.08s`
- `replay_orchestration`: `122.49s`

Le patch d'index/cache aide:

- `fallback_scan_count=0`
- `duplicate_scan_detected_count=0`
- `query_cache_hit_count=850`
- `cache_reuse_ratio=0.657895`

Mais la lecture/parsing JSONL et l'extraction de raw windows restent les vrais goulets.

## Qualite des fichiers

Artifacts attendus presents:

- `strategy_ladder_summary.json`
- `profitability_truth_verdict.json`
- `backtest_decision_report.json`
- `backtest_decision_report_final_verdict.json`
- `execution_realism_summary.json`
- `measured_spread_report.json`
- `measured_slippage_report.json`
- `fill_realism_report.json`
- `b2_label_store_ml_training_audit.json`
- `no_shadow_threshold_challenge_final_verdict.json`
- `ml_label_store/strategy_ladder_replay_label_store.jsonl`
- `ml_label_store/f16_feature_coverage_report.json`

Qualite fichier: bonne pour audit et diagnostic.  
Qualite resultat: insuffisante pour training/promotion/live.

## Decision avant B_ML / IA Lab

Ne pas lancer IA Lab pour produire un artifact promotion-ready a partir de ce label store.

Autorise:

- B_ML research-only pour verifier le plumbing dataset.
- Analyse feature availability.
- Analyse des 4 executions bucketisees comme echantillon diagnostic.

Bloque:

- Training expected-edge promotion-ready.
- ML frozen pour verdict rentabilite.
- Threshold patch.
- Shadow/live.

## Prochaine action chirurgicale

Priorite 1: corriger la source des proxies cost/fill et labels:

1. Forcer B2 truth cible sur une fenetre ou `depth20` est complet, pas 104/200.
2. Exiger que spread/slippage soient mesures pour chaque replay row selectionnee.
3. Produire un target policy unique: soit `B2_REPLAY_EXECUTION_AWARE_NET_EDGE.v1`, soit marquer toutes les rows non conformes comme research-only sans mismatch global.
4. Brancher un artifact expected-edge OOS seulement apres label store eligible.
5. Ajouter un mode B2 rapide sans regeneration raw-window complete quand A2 silver/gold est deja fige.

Priorite 2: performance:

1. Activer le fast path Parquet pour replay au lieu de reparsing JSONL.
2. Remplacer l'extraction raw-window materialisee par refs/cache pour B2 exploratoire.
3. Paralleliser B2 par candidat ou par bucket avec 4 workers.
4. Rendre le no-shadow threshold challenge optionnel ou incremental; il coute 189s sur ce run.

## Verdict final

Le patch a reussi a rendre le pipeline plus observable et a produire B2 complet.  
Le run reste un diagnostic research-only:

`RUN_COMPLETE_BUT_NOT_PROFITABILITY_READY`

La cause n'est plus "features non calculees". La cause est:

- expected-edge non gouverne;
- cost/fill/adverse selection partiels;
- label store non eligible;
- F16 encore incomplet;
- echantillon execute trop petit;
- B1 encore trop large par rapport aux decisions natives B2.

## Addendum correctif B2 du 2026-05-27

Un correctif B2 reporting/label-store a ete applique apres cet audit.

Objectif: ne plus confondre deux problemes differents:

- vrai `TARGET_POLICY_MISMATCH`: la row porte un autre target, par exemple forward-return pur;
- target execution-aware declare mais non satisfait: row proxy ou execution partielle.

Resultat apres regeneration du label store et des rapports decision:

- `target_policy_mismatch_count=0`
- `target_policy_unsatisfied_count=388`
- `final_verdict=B2_LABEL_STORE_BLOCKED_BY_PROXY_LABELS`
- `training_row_eligible_count=0`
- `training_row_research_only_count=384`
- `training_row_blocked_count=4`
- `replay_grounded_label_count=4`
- `proxy_label_count=384`

Donc le diagnostic est maintenant plus exact: le probleme principal n'est pas un mauvais target policy declare. Le probleme est que le target policy attendu `B2_REPLAY_EXECUTION_AWARE_NET_EDGE.v1` n'est satisfait par aucune row training-ready, car la majorite des rows restent proxy et les rares rows executees ne sont pas cost/fill promotion-grade.

F16 a aussi ete enrichi avec une lecture `engine_applicable_rows`, pour separer les champs Engine D-only des rows A/B/C:

- `engine_a`: champs D-only exclus; restent manquants `cumulative_ofi`, `queue_pressure`, `micro_edge_exit_governor_observed`, `micro_edge_entry_timing_observed`.
- `engine_b`: champs D-only exclus; memes familles manquantes que A.
- `engine_d`: champs D requis; restent manquants `cumulative_ofi`, `queue_pressure`, et les trois `anti_revenge_state__*`.

Le verdict global ne change pas:

`BACKTEST_DECISION_REPORT_PARTIAL`  
`profitability_backtest_ready=false`  
`research_only=true`
