# V5.3 A2 Microstructure Performance Patch Plan

## 1. Mission

Ce document décrit le patch à faire couche par couche pour réduire fortement le temps d'exécution des backtests V5.3, surtout quand A2 calcule des features microstructure comme `spread_bps`, `book_depth_levels`, `cumulative_ofi`, `vpin`, `queue_pressure` et `realized_vol_current`.

Le but n'est pas d'obtenir plus de trades. Le but est de rendre le pipeline A1/A2/B1/B2/B_ML plus rapide, plus observable et plus fiable, sans modifier la doctrine trading.

## 2. Invariants non négociables

- Ne pas modifier Engine A/B/C/D.
- Ne pas modifier `SignalCandidate`.
- Ne pas modifier les thresholds.
- Ne pas supprimer `EXPECTED_EDGE_PROXY_BLOCKED`, `BREAK_EVEN_PROXY_BLOCKED`, `FILL_REALISM_NOT_PROVEN` ou les blockers de gouvernance.
- Ne pas forcer `selected_count > 0`.
- Ne pas créer de fake executed trade.
- Ne pas transformer un cache microstructure en vérité d'exécution si la profondeur/slippage/fill ne sont pas réellement mesurés.
- Ne pas utiliser des labels post-décision comme features runtime.
- Ne pas créer de nouveau profil hors doctrine V5.3; utiliser les modes et artifacts existants.

## 3. Constat vérifié

Run problématique observé:

- Workflow: `strategy_ladder_workflow-702c4638a492d72d`
- Dossier: `L:\output backtest\runs\strategy_ladder_workflow-702c4638a492d72d`
- Phase bloquée longtemps: A2 Data Factory
- Symptôme cockpit: progression à `95%` pendant longtemps
- Statut système observé: process Python vivant, mémoire élevée, CPU actif
- Artifacts A2 partiels: silver déjà écrit, gold vide ou non finalisé, manifest final absent pendant l'attente

Le `95%` cockpit n'est pas une vraie progression métier. C'est une estimation temps qui plafonne les jobs actifs à 95%. Il faut donc ajouter une progression A2 réelle par étape: scan raw, silver, cache microstructure, gold, reports.

Cause technique probable:

- A2 construit certaines features microstructure via un pont engine-native.
- Pour chaque ligne ou timestamp, le code peut relire ou rescanner des fichiers gzip orderbook/trades.
- Les fichiers raw/silver sont gros, donc une lecture répétée par row provoque un coût explosif.
- Le run lancé par un ancien processus cockpit peut aussi ignorer des options récentes comme `--timeframes 1m`, même si l'UI affiche la sélection.

## 4. Guidance technique externe vérifiée

Les optimisations à appliquer sont cohérentes avec les pratiques analytics standards:

- Apache Arrow recommande un format colonne efficace pour l'analytics: <https://arrow.apache.org/docs/format/Intro.html>
- DuckDB exploite projection/filter pushdown sur Parquet pour ne lire que les colonnes et groupes nécessaires: <https://duckdb.org/docs/lts/data/parquet/overview.html>
- Polars Lazy applique notamment predicate pushdown, projection pushdown et common subplan elimination: <https://docs.pola.rs/user-guide/lazy/optimizations/>

Décision V5.3: ne pas basculer directement toute la vérité A2 en Parquet/Arrow. Le premier patch doit rester compatible avec les artifacts actuels, puis ajouter un cache audité. Le backend colonne peut devenir une couche optionnelle après tests d'équivalence.

## 5. Architecture cible

Pipeline cible:

```text
A1 raw validation
  -> A2 silver normalized windows
  -> A2 microstructure day cache
  -> A2 gold features
  -> B1 candidate discovery
  -> B2 detailed replay / labels
  -> B_ML label factory / training
```

Nouveaux artifacts A2 proposés:

```text
phase_a2_data_factory/cache/microstructure/<pair>/<date>/microstructure_rows.jsonl.gz
phase_a2_data_factory/reports/a2_microstructure_cache_manifest.json
phase_a2_data_factory/reports/a2_microstructure_performance_report.json
phase_a2_data_factory/reports/a2_gold_progress_report.json
phase_a2_data_factory/reports/a2_feature_equivalence_report.json
```

Schéma minimal du cache:

```json
{
  "schema_version": "v53.a2_microstructure_cache_row.v1",
  "pair": "BTCUSDT",
  "date": "2025-07-07",
  "timeframe": "1m",
  "timestamp_ms": 0,
  "spread_bps": null,
  "spread_source_status": "MEASURED|MISSING|STALE|INSUFFICIENT_DATA",
  "book_depth_levels": null,
  "book_depth_source_status": "DEPTH20_WALK|MISSING|STALE|INSUFFICIENT_DATA",
  "cumulative_ofi": null,
  "queue_pressure": null,
  "vpin": null,
  "realized_vol_current": null,
  "feature_status_by_name": {},
  "raw_snapshot_ref": null,
  "raw_delta_ref": null,
  "raw_trade_ref": null,
  "source_hashes": {},
  "cache_build_status": "OK|PARTIAL|BLOCKED"
}
```

Règle critique: `book_depth_levels=20` ne doit être rempli que si la profondeur 20 a réellement été utilisée ou prouvée disponible au timestamp. Sinon, statut explicite `MISSING`, `STALE` ou `INSUFFICIENT_DATA`.

## 5.1 Correctif immédiat de fenêtre A2

Décision opérateur: quand une fenêtre commence à `T0`, A2 doit garder au maximum le contexte utile `T0 - 1h -> end`, pas toute la journée précédente.

Règles à implémenter:

- `requested_window`: fenêtre demandée par l'opérateur.
- `context_window`: `requested_start - 1h` jusqu'à `requested_end`.
- Silver peut contenir des rows de contexte, mais uniquement dans `context_window`.
- Silver ne doit pas écrire toute la journée précédente juste parce que le fichier raw chevauche `context_window`.
- Pour les klines, silver ne doit matérialiser que les timeframes explicitement sélectionnés.
- Gold doit rester limité à la fenêtre demandée pour les rows de décision; le contexte sert seulement au calcul amont.
- Les audits OHLCV ne doivent pas bloquer à cause d'une journée de contexte partielle hors `requested_window`.
- Les manifests doivent rendre cette séparation visible pour éviter toute confusion opérateur.

## 6. Plan couche par couche

### Couche 0 - Instrumentation et sécurité

Objectif: comprendre précisément où A2 passe son temps, sans changer les valeurs produites.

Statut d'exécution:

- Implémentation démarrée.
- Artifacts ajoutés:
  - `a2_gold_progress_report.json`
  - `a2_microstructure_performance_report.json`
- Ces artifacts sont reporting-only et ne changent aucune décision A2/B1/B2/B_ML.

Travail:

- Ajouter un rapport de progression A2 réel.
- Mesurer temps par phase: scan raw, silver write, cache build, gold feature write, reports.
- Compter lectures de fichiers orderbook/trades/klines.
- Compter cache hit/miss quand le cache sera activé.
- Écrire un heartbeat JSON pendant les longues phases.

Tests:

- Un run A2 court produit `a2_gold_progress_report.json`.
- Le rapport contient phase courante, timestamp dernier update, compteurs de rows et fichiers.
- Les valeurs gold ne changent pas entre avant/après instrumentation.

Risque:

- Trop de writes de progression peuvent ralentir le job.

Mitigation:

- Écrire le heartbeat toutes les N secondes ou toutes les N rows, pas à chaque row.

### Couche 1 - Commande cockpit et hygiène runtime

Objectif: éviter qu'un run lancé depuis un ancien processus cockpit ignore les sélections modernes.

Travail:

- Vérifier que la commande A2 émet toujours `--timeframes` quand l'utilisateur sélectionne un timeframe.
- Vérifier que les features sélectionnées sont persistées dans le request manifest.
- Ajouter un signal cockpit si le serveur actif est antérieur au patch courant ou si la commande preview ne contient pas les timeframes sélectionnés.
- Conserver la séparation: Backtest ne réentraîne pas ML silencieusement.

Tests:

- Preview A2 avec `1m` produit une commande contenant `--timeframes 1m`.
- Preview multi-timeframe produit une CSV stable.
- Les features sélectionnées restent cochées après preview.
- A1/A2/B1/B2 relisent la même sélection depuis le manifest.

Risque:

- Ancien serveur cockpit encore actif après patch.

Mitigation:

- Afficher clairement `server_build_hash` ou `command_contract_version` dans le job preview.

### Couche 2 - Cache loader microstructure par jour

Objectif: lire chaque fichier raw/silver une fois par `pair/date/source`, pas une fois par feature row.

Travail:

- Ajouter un module dédié de cache microstructure A2.
- Charger snapshots, deltas et trades par jour avec tri timestamp.
- Appliquer le filtre row-level `context_window`: ne pas écrire toute la journée du fichier raw quand seules les 60 minutes avant `start` sont utiles.
- Pruner les fichiers klines dont le timeframe n'est pas demandé avant normalisation complète.
- Construire des index temporels en mémoire ou en streaming chunké.
- Conserver les refs de provenance par fichier source.
- Ne pas changer les fonctions de calcul métier tant que l'équivalence n'est pas prouvée.

Tests:

- Le loader lit chaque gzip une seule fois sur fixture.
- Les données sont triées par timestamp.
- Les fenêtres timestamp respectent les bornes inclusives/exclusives attendues.
- Un run `start=2025-07-07,end=2025-07-07` écrit au plus `2025-07-06 23:00 -> 2025-07-07 23:59:59.999`, pas toute la journée du 6.
- Un run `timeframes=("1m",)` n'écrit pas de silver `5m/10m/15m`.
- Si une source manque, le statut est `MISSING_IN_ARTIFACT` ou `INSUFFICIENT_DATA`, jamais une valeur par défaut.

Risque:

- Charger un jour complet depth20 peut dépasser la mémoire.

Mitigation:

- Prévoir un mode streaming par chunks et une limite mémoire configurable.

Statut d'exécution 2026-05-25:

- Implémenté dans `strategy_ladder_engine_native_adapter.py` sans modifier les engines.
- Ajout d'un cache fichier JSONL-GZ par signature `(path, mtime_ns, size)`.
- Ajout d'un index timestamp par fichier pour éviter de rescanner toutes les rows trades/orderbook par feature row.
- Ajout du rapport `a2_microstructure_cache_manifest.json`.
- Ajout des compteurs `file_cache_*` et `time_index_*` dans `a2_microstructure_performance_report.json`.
- Contrôle réel `BTCUSDT`, `2025-07-07`, `1m`, `realized_vol_current`: A2 termine en 49.35s, `gold_feature_build=24.41s`, `gold_feature_row_count=1500`, `time_index_hit_count=1498`.
- Contrôle silver: seulement `2025-07-06 23:00` contextuel et `2025-07-07`; aucune sortie `2025-07-08`.
- Limite restante: le calcul orderbook depth20 complet peut encore nécessiter une couche streaming plus forte si les deltas sont très volumineux.

### Couche 3 - Builder de features streaming

Objectif: calculer toutes les features microstructure demandées en un passage par jour/pair/timeframe.

Travail:

- Pour chaque timestamp kline, regarder les fenêtres microstructure via l'index/cache.
- Produire spread, depth status, OFI, VPIN, queue pressure, realized volatility et autres features disponibles.
- Garder les mêmes noms de features que le label store et le cockpit.
- Marquer explicitement les features absentes ou stales.
- Ne pas utiliser de données post-décision.

Tests:

- Fixture petite: l'ancien calcul row-by-row et le nouveau calcul cache donnent les mêmes valeurs à tolérance définie.
- Une feature sans source reste missing.
- Une donnée après décision est bloquée.
- `realized_vol_current` utilise seulement le passé.

Risque:

- Décalage off-by-one sur les fenêtres temporelles.

Mitigation:

- Tests avec timestamps bord de fenêtre: début, fin, exact decision timestamp.

Statut d'exécution 2026-05-25:

- Implémenté en mode requested-only: A2 ne calcule plus Kyle/VPIN/OFI/queue quand seule une autre micro-feature est sélectionnée.
- Le builder batch par entrée gold utilise les calculateurs canoniques `data_backbone.microstructure`; aucune formule engine n'est modifiée.
- Ajout du rapport `a2_feature_equivalence_report.json`.
- Ajout des champs `microstructure_streaming_*` dans le manifest gold et `a2_microstructure_performance_report.json`.
- Contrôle réel `BTCUSDT`, `2025-07-07`, `1m`, `realized_vol_current`: `gold_feature_build=18.63s` contre `24.41s` après Couche 2, `overlay_row_count=1498/1500`, `missing_row_count=2`, `A2_FEATURE_EQUIVALENCE_READY`.
- Les 2 rows manquantes correspondent aux premières fenêtres sans assez d'événements pour `realized_vol_current`; elles restent missing, sans défaut inventé.
- Limite restante: un vrai builder streaming multi-feature pour orderbook depth20 peut encore être nécessaire sur fenêtres larges avec deltas volumineux.

### Couche 4 - Intégration A2 gold

Objectif: remplacer le calcul microstructure répétitif par une lookup cache contrôlée.

Travail:

- A2 silver reste la base canonique.
- A2 gold enrichit les rows avec cache microstructure.
- A2 gold ne doit générer des decision rows que dans `requested_window`.
- Le contexte `T0 - 1h` est autorisé uniquement comme input de calcul, pas comme décision backtest hors fenêtre.
- Le manifest gold indique `microstructure_cache_used=true/false`.
- Le rapport d'équivalence indique quelles features sont strictement équivalentes, approximées ou non calculables.

Tests:

- A2 gold non vide sur un run court avec microstructure.
- `data_factory_manifest.json`, `silver_index.json`, `data_quality_report.json` et manifest gold sont écrits.
- Le cache est invalidé si raw file hash, feature set, timeframe ou version méthode change.
- Les entries OHLCV de contexte hors fenêtre demandée ne déclenchent pas `OHLCV_TEMPORAL_COMPLETENESS_BLOCKED`.

Risque:

- Cache stale réutilisé sur mauvaise fenêtre.

Mitigation:

- Clé de cache = pair/date/timeframe/source hashes/feature method version.

Statut d'exécution 2026-05-25:

- Implémenté: A2 gold n'écrit plus les rows de contexte comme rows de décision.
- Silver conserve la fenêtre `requested_start - 1h -> requested_end`; gold filtre sur `requested_window`.
- Ajout des champs manifest/report:
  - `gold_decision_window_status`
  - `gold_context_row_count`
  - `gold_context_rows_suppressed_count`
  - `microstructure_cache_used`
  - `feature_equivalence_status`
- `a2_feature_equivalence_report.json` expose aussi le statut de filtre fenêtre.
- Contrôle réel `BTCUSDT`, `2025-07-07`, `1m`, `realized_vol_current`:
  - total A2 `35.18s`
  - `gold_feature_build=13.59s`
  - silver OHLCV rows `1500`
  - gold decision rows `1440`
  - context rows suppressed `60`
  - min/max timestamps gold strictement dans `2025-07-07`
  - `A2_FEATURE_EQUIVALENCE_READY`
- Limite restante: le contexte cross-day est préservé en silver et supprimé du gold décisionnel; la consommation cross-day multi-file pour certaines features longues peut être renforcée dans Couche 5 si B1/B2/B_ML en ont besoin.

### Couche 5 - B1/B2/B_ML consommation contrôlée

Objectif: que B1/B2/B_ML bénéficient des features A2 sans dégrader la vérité replay.

Travail:

- B1 consomme les features A2 gold comme avant, mais avec provenance enrichie.
- B2 peut référencer le cache pour expliquer disponibilité microstructure.
- B2 slippage/fill truth reste basé sur book walk/fill realism, pas sur une simple feature gold.
- B_ML lit les features ex-ante et les labels post-décision séparément.
- Les labels restent `RESEARCH_ONLY` si coût/fill/adverse selection ne sont pas mesurés.

Tests:

- Le label store B_ML garde `feature_timestamp <= decision_timestamp`.
- Les labels gardent `label_timestamp > decision_timestamp`.
- Aucune feature post-décision n'entre dans `feature_values`.
- B2 ne transforme pas `spread_bps` cache en label net-edge promotion-ready.

Risque:

- Confusion entre feature microstructure et label exécution.

Mitigation:

- Provenir chaque champ avec `feature_source_status` ou `label_truth_status`.

### Couche 6 - Backend colonne optionnel

Objectif: préparer une optimisation plus forte sans casser les artifacts actuels.

Travail:

- Évaluer Parquet/Arrow/DuckDB/Polars après validation du cache JSONL-GZ.
- Utiliser projection/filter pushdown pour gros runs.
- Garder le format existant comme source de vérité tant que l'équivalence n'est pas validée.

Tests:

- Même sortie JSON finale entre backend actuel et backend colonne sur fixture.
- Même nombre de rows, mêmes timestamps, mêmes statuses.

Risque:

- Dépendance externe ou format non disponible sur la machine opérateur.

Mitigation:

- Backend colonne derrière flag explicite, fallback vers JSONL-GZ.

### Couche 7 - Cockpit et run control

Objectif: que l'opérateur voie la vraie progression et les vrais blockers.

Travail:

- Afficher progression A2 réelle: silver, cache, gold, reports.
- Afficher dernier fichier traité et dernière activité utile.
- Afficher si un run est lancé sans `--timeframes`.
- Ajouter liens vers les rapports A2 performance/cache/equivalence.
- Ne pas surcharger l'écran: seulement status, prochaine action et liens.

Tests:

- Cockpit affiche les liens A2 performance.
- Le run ne reste pas seulement à 95% sans information métier.
- Un job ancien ou incompatible montre une alerte claire.

Risque:

- UI trop bavarde.

Mitigation:

- Résumé court + liens artifacts.

## 7. Tests globaux à exécuter

Compilation:

```powershell
python -m compileall -q src tests
```

Tests unitaires à ajouter ou renforcer:

```powershell
python -m pytest tests/test_local_replay_runtime/test_a2_microstructure_cache.py -q --tb=short
python -m pytest tests/test_local_replay_runtime/test_a2_microstructure_feature_equivalence.py -q --tb=short
python -m pytest tests/test_local_replay_runtime/test_strategy_ladder_data_factory.py -q --tb=short
```

Tests B_ML / label safety:

```powershell
python -m pytest tests/test_local_replay_runtime/test_b_ml_label_factory.py -q --tb=short
python -m pytest tests/test_local_replay_runtime/test_b2_label_store_ml_training_audit.py -q --tb=short
python -m pytest tests/test_local_replay_runtime/test_ml_label_leakage_guards.py -q --tb=short
```

Tests cockpit:

```powershell
python -m pytest tests/cockpit/test_backtest_command_preview.py -q --tb=short
python -m pytest tests/cockpit/test_backtest_feature_picker.py -q --tb=short
```

Tests de non-régression trading:

```powershell
python -m pytest tests/engine_canary -q --tb=short
python -m pytest tests/test_local_replay_runtime/test_no_shadow_threshold_challenge.py -q --tb=short
```

## 8. Run de contrôle

Après patch couche 0 à 4, lancer un run court contrôlé.

Configuration recommandée:

- Pair: `BTCUSDT`
- Fenêtre: `2025-07-07` à `2025-07-08`
- Timeframe: `1m`
- Mode: ML off pour le test pipeline
- Features minimales: `close_return`, `high_low_range`, `volume`, `spread_bps`, `book_depth_levels`
- Features microstructure additionnelles: `cumulative_ofi`, `vpin`, `realized_vol_current`
- Output: nouveau dossier sous `L:\output backtest\runs\`

Commande attendue depuis cockpit:

```text
A1 -> A2 -> B1 -> B2
avec --timeframes 1m
avec features sélectionnées persistées
sans training ML silencieux
```

Critères de succès:

- A2 termine et écrit le manifest final.
- Gold features non vide.
- `a2_microstructure_performance_report.json` indique que les fichiers microstructure ne sont pas rescannés par row.
- `a2_microstructure_cache_manifest.json` liste sources, hashes et statuts.
- `a2_feature_equivalence_report.json` est `PASS` ou liste explicitement les écarts.
- B1/B2 peuvent consommer A2 sans perte de pair/timeframe.
- Si `selected_count=0`, le rapport explique les vrais blockers sans accuser le cache.
- `profitability_backtest_ready` reste `false` tant que coût/fill/labels/executions ne sont pas gouvernés.

## 9. Critères d'acceptation finale

Le patch est accepté si:

- Le temps A2 sur un run court microstructure baisse nettement.
- Le temps A2 ne croît plus de façon explosive avec le nombre de rows.
- Les outputs A2 restent auditables.
- Les features microstructure sont calculées quand les sources existent.
- Les features manquantes restent explicitement missing.
- Aucun trade n'est forcé.
- Aucun blocker de gouvernance n'est supprimé.
- B_ML peut consommer les features ex-ante sans fuite temporelle.
- Les tests unitaires, cockpit et canary passent.

## 10. Risques principaux

| Risque | Impact | Mitigation |
| --- | --- | --- |
| Cache trop gros en mémoire | A2 peut rester lent ou planter | Streaming par jour/chunk, limites mémoire |
| Off-by-one temporel | Leakage ou features fausses | Tests de bornes timestamp |
| Cache stale | Mauvaises features réutilisées | Hash raw + method version + feature set |
| Confusion feature vs label | ML peut apprendre une vérité non prouvée | Statuts séparés feature/label |
| Ancien cockpit actif | Commandes sans `--timeframes` | Contract version visible et alerte UI |
| Backend colonne prématuré | Nouveau risque de compatibilité | Garder optionnel après équivalence |

## 11. Ordre d'exécution proposé

1. Valider ce plan.
2. Implémenter Couche 0: instrumentation A2.
3. Tester Couche 0.
4. Implémenter Couche 1: cockpit command/runtime hygiene.
5. Tester Couche 1 depuis preview.
6. Implémenter Couche 2: cache loader.
7. Implémenter Couche 3: builder streaming.
8. Tester équivalence sur fixtures.
9. Implémenter Couche 4: intégration gold.
10. Run de contrôle A1/A2/B1/B2.
11. Implémenter Couche 5: B2/B_ML provenance/reuse si nécessaire.
12. Ajouter UI reports couche 7.
13. Évaluer Couche 6 Parquet/Arrow seulement si le cache JSONL-GZ ne suffit pas.

## 12. Décision attendue avant patch

Ne pas lancer un gros run tant que Couche 0 à 4 ne sont pas terminées et vérifiées.

Le prochain patch concret doit commencer par l'instrumentation A2, car elle est faible risque et permettra de prouver exactement où le temps est consommé avant d'optimiser.
