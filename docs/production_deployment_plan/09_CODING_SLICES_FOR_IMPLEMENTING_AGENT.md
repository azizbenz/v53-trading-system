# Coding Slices — Découpage pour l'agent codeur

> **Important — recadrage du rôle Opus** :
> Ce dossier a été initialement nommé "Opus coding sessions". Après clarification du workflow (voir `00_README.md` § 0), **Opus ne code pas le projet**. Opus produit les MD de cadrage (= ce dossier). L'**agent codeur** (Sonnet en session locale dans le repo) lit ces MD et code les tranches.
>
> Ce fichier liste donc les **tranches de code à exécuter par l'agent codeur**, pas des "sessions Opus". Le découpage en tranches est conçu pour :
> 1. Tenir dans la fenêtre d'une session de code raisonnable
> 2. Produire un état mergeable (tests verts) à la fin de chaque tranche
> 3. Permettre rollback partiel si une tranche échoue

> **Règle d'or** : à chaque début de tranche, l'agent codeur **vérifie l'état réel du repo** (le repo gagne contre le MD). Toute contradiction est remontée, pas résolue silencieusement.

---

## 1. Découpage par phase

### Phase 1 (P0) — 6 à 10 tranches
### Phase 1bis (P1) — 3 tranches
### Phase 2 (V37 bricks) — 1 à 2 tranches

**Total** : **10 à 15 tranches code** pour atteindre le niveau de prêt-pour-MICRO_LIVE.

---

## 1bis. Tranches intermédiaires historiques `W1/W2/W3`, toujours valides après `12`

`12_LOCAL_LAB_VS_VPS_SEPARATION.md` est maintenant publié. Les tranches `W1/W2/W3` restent valides comme historique et comme base de travail, mais leur ownership n'est plus "à fixer plus tard" :
- `12_...` fixe la frontière Local IA Lab / VPS
- `13_...` fixe la méthode de calibration
- `14_...` fixe la math des gates Shadow

### Tranche W1 — Inventaire des consommateurs de seuils dynamiques

**Statut repo réel au 2026-04-09** — fait via `11A_DYNAMIC_THRESHOLDS_REPO_CROSSCHECK.md`.

**Objectif** — Mapper, depuis `11_DYNAMIC_THRESHOLDS_CATALOG.md`, tous les modules du repo qui devront consommer un seuil calibré.

**Périmètre** :
- lecture du catalogue `11_DYNAMIC_THRESHOLDS_CATALOG.md`
- cross-check contre le repo réel
- table de mapping `threshold_id -> source_module -> état réel du code`

**Invariants** :
- pas de changement de comportement runtime
- pas de hardcoding de valeurs issues du catalogue
- si un module du catalogue n'existe pas encore dans le repo, le tracer comme `future target`, pas comme bug du repo

**Critères d'acceptation** :
- [ ] chaque seuil du catalogue a un statut `exists / partial / future target`
- [ ] les contradictions doc/code sont tracées explicitement
- [ ] aucun code runtime modifié

### Tranche W2 — Contrat partagé de calibration dynamique

**Statut repo réel au 2026-04-09** — tranche codée en shared core via `src/calibration_loader/`.

**Objectif** — Préparer la couche shared core minimale pour lire des artefacts de calibration signés, avec ownership désormais fixé par `12_...`.

**Périmètre** :
- contrats typés de calibration
- loader/validator partagé
- tests de parsing/validation

**Invariants** :
- `src/calibration_loader/` reste shared core ; il ne doit être dupliqué ni côté VPS ni côté Local IA Lab
- pas de valeur seuil hardcodée en fallback silencieux
- le repo réel gagne si le catalogue pointe vers des modules encore absents

**Critères d'acceptation** :
- [x] format d'artefact de calibration lisible et validable
- [x] erreurs explicites si artefact manquant / invalide / non signé
- [x] tests ciblés verts

**Preuve repo** :
- `src/calibration_loader/contracts.py`
- `src/calibration_loader/loader.py`
- `tests/test_calibration_loader/test_contracts.py`
- `tests/test_calibration_loader/test_loader.py`
- `pytest tests/test_calibration_loader/test_contracts.py tests/test_calibration_loader/test_loader.py -q --basetemp=build/pytest-calibration-loader-proof`

### Tranche W3 — Durcissement du rail IA Lab réel déjà existant

**Statut repo réel au 2026-04-09** — en cours, avec nouvelles garanties sur la reprise metadata/chunk session et sur la cohérence sémantique des sidecars gouvernés.

**Objectif** — Continuer à sécuriser le rail déjà présent dans le repo :
`local_replay_runtime -> governed export -> backtest_artifact_import -> VPS Shadow`

**Périmètre** :
- persistance fail-safe
- reprise / resume metadata
- evidence stores
- supervision/monitoring de ce rail

**Invariants** :
- ne pas ouvrir de faux package `src/local_ai_lab`
- ne pas contourner `SHADOW`
- ne pas contredire la séparation fixée par `12_...`

**Critères d'acceptation** :
- [ ] slices bornés
- [ ] tests ciblés verts
- [ ] tracker + mémoire mis à jour

**Preuve repo déjà fermée sur le slice courant** :
- `src/local_replay_runtime/replay_orchestrator.py`
- `tests/test_local_replay_runtime/test_replay_orchestrator.py`
- `pytest tests/test_local_replay_runtime/test_replay_orchestrator.py tests/test_local_replay_runtime/test_local_replay_export_launcher.py -q --basetemp=build/pytest-local-replay-resume-proof`
- résultat: `20 passed`

**Comportement obtenu** :
- backup `.corrupted` + fail-close explicite si `replay_session_config.json` est corrompu
- backup `.corrupted` + fail-close explicite si `replay_run_manifest.json` est corrompu
- backup `.corrupted` + fail-close explicite si `replay_chunk_session.json` est corrompu
- même politique pour les sidecars relus pendant un resume (`performance_mode_guard`, `run_consistency_guard`, `replay_metrics`)
- `src/backtest_artifact_import/export_dir_bridge.py` applique désormais la même discipline sur le pont export→import
- `replay_run_manifest.json` et `feature_bridge.json` sont backupés en `.corrupted` puis rejetés explicitement si corrompus
- `parity_diagnostics.json`, `replay_metrics.json`, et `replay_dtr.jsonl` sont maintenant aussi validés explicitement sur le vrai chemin `export_dir`
- cette validation est maintenant typée quand le repo a déjà un contrat:
  - `parity_diagnostics.json` via un schéma minimal `ReplayParityDiagnosticsSummary`
  - `replay_metrics.json` via `ReplayMetricsSummary`
  - `replay_dtr.jsonl` / `replay_dtr.json` via `DTRRecord`
- la validation du vrai `export_dir` rejette maintenant aussi les contradictions sémantiques entre `replay_run_manifest` et les sidecars typés
  - `review_export.md` doit contenir une provenance cohérente avec le manifest et les sidecars
  - `run_id / strategy_id / strategy_version / lineage_version / profile_scope / runtime_mode / performance_mode` doivent matcher le manifest
  - `total_opportunities / total_records / dtr_coverage` doivent matcher `replay_metrics`
  - `status / decision_match_rate` doivent matcher `parity_diagnostics`
  - `feature_bridge.dataset_id` doit matcher `replay_run_manifest.dataset_manifest_id`
  - `feature_bridge.feature_set_version` doit matcher `replay_run_manifest.feature_set_version`
  - `feature_bridge.transform_set_version` doit matcher `replay_run_manifest.transform_set_version`
  - `feature_bridge.pairs` / `feature_bridge.engines` doivent matcher `tested_pairs` / `engine_scope`
  - `parity_diagnostics.dataset_id` doit matcher `replay_run_manifest.dataset_manifest_id`
  - `replay_metrics.total_records` doit matcher le nombre réel de `DTRRecord`
  - `pair_aggregates` et `engine_aggregates` doivent sommer à `total_records`
  - les pairs / engines portés par `replay_metrics` et `replay_dtr` doivent rester dans `tested_pairs` / `engine_scope`
  - les `DTRRecord.runtime_mode` doivent rester `local_replay`
  - les timestamps DTR doivent rester dans la fenêtre horloge du manifest
  - `replay_metrics` doit rester exactement recalculable depuis les `DTRRecord` exportés
  - aucun sidecar gouverné d'un vrai `export_dir` ne peut se résoudre hors de ce dossier, même via une référence détournée
  - un vrai `export_dir` ne peut plus contenir plusieurs fichiers candidats pour le même sidecar gouverné; l'ambiguïté est maintenant fail-close
  - un `ArtifactUploadRequest` gouverné est maintenant rejeté dès sa construction si `manifest.review_export_ref / feature_bridge_ref / parity_diagnostics_ref / replay_metrics_ref / replay_dtr_ref` divergent du `payload_bundle`
  - un `ArtifactPayloadRefBundle` gouverné est maintenant rejeté s'il contient des doublons, y compris via `supplementary_refs`
- preuve la plus récente:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_replay_executor.py tests/test_local_replay_runtime/test_replay_session_state.py tests/test_local_replay_runtime/test_artifact_exporter.py -q`
  - résultat: `104 passed`
- les refs symboliques non-file du chemin démo (`feature_bridge:<id>`) restent admises comme métadonnées non export-dir, sans desserrer la politique sur les vrais sidecars gouvernés

Ces tranches intermédiaires existent pour éviter un arrêt total du travail. Elles préparent Phase 0/1 et restent compatibles avec la séparation désormais figée par `12_...`.

### 1ter. Piste future optionnelle — vue flotte multi-VPS read-only

Cette piste n'est **pas** une tranche runtime immédiate. Elle est mémorisée ici pour multi-session, conformément à `12_...` :

- objectif : lister plusieurs VPS par `vps_id` avec seulement `health_status / runtime_mode / artifact_version / heartbeat_age / alert_state`
- invariant : aucun pilotage multi-VPS, aucun failover, aucune promotion croisée
- drill-down : pour le détail complet, l'opérateur se connecte à la VPS choisie
- statut : `M0` fermé sur contrats typés read-only dans `src/monitoring/contracts.py`; `M1/M2` restent futurs et non bloquants pour P0/P1
- preuve `M0` :
  - `tests/test_monitoring/test_monitoring_contracts.py`
  - `rtk pytest tests/test_monitoring/test_monitoring_contracts.py tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_monitoring_runtime.py tests/test_ui/test_technical_dashboard.py -q`
  - résultat : `73 passed`

---

## 2. Phase 1 — Tranches P0

### Tranche T1 — P0-1.A : Squelette adapter Binance + REST client read-only

**Statut repo réel au 2026-04-09** — tranche codée et prouvée localement.

- `src/interface_contracts/binance_contracts.py` existe
- `src/venue_adapters/binance_spot/{__init__,rest_client,time_sync,credential_loader}.py` existe
- `config/binance_adapter.yml` existe
- `tests/test_venue_adapters/test_binance_spot/test_*.py` existe
- preuve locale:
  - `PYTHONPATH=src python -m pytest tests/test_venue_adapters/test_binance_spot/test_credential_loader.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_execution_backbone/test_venue_constraints_provider.py -q`
  - résultat: `15 passed`
- résidu honnête:
  - le critère Binance Testnet reste `manuel / humain`
  - `credential_loader.py` reste un stub explicite jusqu'à `T2`

**Objectif** — Créer la structure du dossier `src/venue_adapters/binance_spot/` avec les modules vides + le REST client en read-only (account snapshot, exchange info, time sync).

**Périmètre** :
- Création du dossier `binance_spot/` et de ses modules vides
- `rest_client.py` : query `/api/v3/account`, `/api/v3/exchangeInfo`, `/api/v3/time` (read-only, pas de signed POST)
- `time_sync.py` : sync horloge locale vs Binance, alerter si drift > 500 ms
- Config loader pour les credentials (sealed via P0-4 — voir T2)

**Invariants** :
- Aucun code de soumission d'order dans cette tranche
- Aucun seuil hardcodé (les seuils de drift, retry, etc. viennent de `config/binance_adapter.yml` chargé via `calibration_loader/`)
- Tests unitaires pour chaque module

**Modules touchés** :
- Nouveau : `src/venue_adapters/binance_spot/{__init__,rest_client,time_sync,credential_loader}.py`
- Nouveau : `tests/test_venue_adapters/test_binance_spot/test_*.py`
- Config : `config/binance_adapter.yml` (template)

**Interfaces I/O** :
- Entrée : credentials sealed (P0-4) → `credential_loader.load()` → `BinanceCredentials` pydantic frozen
- Sortie : `AccountSnapshot`, `ExchangeInfo`, `ServerTime` (pydantic models avec frozen=True)

**Ce qu'il ne faut PAS faire** :
- Pas de POST/PUT/DELETE
- Pas d'utilisation de `requests` directement — utiliser `httpx` async
- Pas de retry automatique caché dans la lib HTTP
- Pas de logger qui sérialize les credentials

**Critères d'acceptation** :
- [ ] `rest_client.get_account_snapshot()` retourne un `AccountSnapshot` valide depuis Binance Testnet
- [ ] `time_sync.sync()` retourne le drift en ms, alerte si > 500ms
- [ ] `tests/` ≥ 80 % coverage sur les nouveaux modules
- [ ] Aucun secret loggé (vérifié via test unitaire)
- [ ] `pytest -xvs tests/venue_adapters/binance_spot/` vert

**Ordre de réalisation** :
1. Définir les pydantic models I/O dans `interface_contracts/binance_contracts.py`
2. Coder `time_sync.py` (le plus simple)
3. Coder `credential_loader.py` (avec stub pour P0-4)
4. Coder `rest_client.py` méthodes read-only
5. Tests unitaires
6. Test intégration testnet (manuel, à valider par humain)

**Preuves attendues** :
- Logs `rest_client_test_<date>.log` propres (pas de credential leak)
- Snapshot pydantic d'un account testnet avec balance ≠ 0
- Diff coverage tracker

**LOC estimées** : 600-900

---

### Tranche T2 — P0-4 : Sealed secrets

**Statut repo réel au 2026-04-09** — tranche codée en backend borné local/dev, avec résidu de portabilité VPS.

- `src/secrets_manager/{__init__,__main__,_dpapi,loader,sealer,cli}.py` existe
- `src/secrets_manager/README.md` existe
- `src/venue_adapters/binance_spot/credential_loader.py` sait maintenant charger un fichier scellé `.sealed.json`
- preuve locale:
  - `PYTHONPATH=src python -m pytest tests/test_secrets_manager/test_loader.py tests/test_venue_adapters/test_binance_spot/test_credential_loader.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py -q`
  - résultat: `12 passed`
- résidu honnête:
  - backend implémenté: `windows_dpapi_user` + `master.key` comme entropie obligatoire
  - `age` / `sops` / backend Linux VPS ne sont pas encore codés
  - la tranche est donc fermée pour l'environnement local Windows actuel, pas comme story finale cross-platform

**Objectif** — Système de chargement des credentials sans clé en clair sur disque.

**Périmètre** :
- Choix de la primitive : `age` (recommandé pour la simplicité) ou `sops`
- `src/secrets_manager/` avec encrypt/decrypt
- CLI helper `python -m secrets_manager seal config/api.yml` → produit `config/api.yml.age`
- Loader runtime : `secrets_manager.load("config/api.yml.age", key_path="~/.config/v53/master.key")`
- Documentation `secrets_manager/README.md` pour le workflow humain

**Invariants** :
- Jamais de clé dans le repo, jamais en clair sur disque hors mémoire
- Master key chargée depuis `~/.config/v53/master.key` (mode 0600), pas dans le repo
- Permissions VPS : `chmod 600` sur tous les `.age`

**Modules touchés** :
- Nouveau : `src/secrets_manager/{__init__,sealer,loader,cli}.py`
- Nouveau : `tests/secrets_manager/test_*.py`
- Doc : `src/secrets_manager/README.md`

**Critères d'acceptation** :
- [ ] Encrypt/decrypt round-trip OK
- [ ] CLI fonctionnel
- [ ] Aucune clé en clair après seal
- [ ] Tests verts

**LOC estimées** : 200-400

---

### Tranche T3 — P0-1.B : WebSocket client + gap recovery

**Statut repo réel au 2026-04-09** — noyau borné codé et prouvé localement, mais tranche pas encore totalement terminée au sens live/testnet.

- `src/venue_adapters/binance_spot/ws_client.py` existe
- `src/venue_adapters/binance_spot/orderbook_manager.py` existe
- `src/venue_adapters/binance_spot/rest_client.py` sait maintenant produire un vrai `depth snapshot` REST typé
- `build_rest_depth_snapshot_provider()` existe pour brancher explicitement le bootstrap `snapshot REST -> WS deltas`
- `src/data_backbone/freshness_checker/venue_stream_freshness.py` existe
- `src/protocols/shadow_live_websocket.py` exporte maintenant aussi `first_update_id / final_update_id` sur les payloads depth
- preuve locale:
  - `PYTHONPATH=src python -m pytest tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_venue_adapters/test_binance_spot/test_orderbook_manager.py tests/test_venue_adapters/test_binance_spot/test_ws_client.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_protocols/test_shadow_live_websocket.py -q`
  - résultat: `19 passed`
- cross-check couplé `T1 + T2 + T3`:
  - `PYTHONPATH=src python -m pytest tests/test_secrets_manager/test_loader.py tests/test_venue_adapters/test_binance_spot/test_credential_loader.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_venue_adapters/test_binance_spot/test_orderbook_manager.py tests/test_venue_adapters/test_binance_spot/test_ws_client.py tests/test_execution_backbone/test_venue_constraints_provider.py tests/test_protocols/test_shadow_live_websocket.py -q`
  - résultat: `33 passed`
- résidu honnête:
  - pas encore de validation live Binance/testnet
  - pas encore de preuve 24h RAM leak
  - branchement live complet et soak-test restent à faire

**Objectif** — WebSocket Binance avec reconnect protocol officiel + gap recovery.

**Périmètre** :
- `ws_client.py` : connect / subscribe / handle / reconnect
- Application du protocole officiel Binance "How to manage a local order book" (snapshot REST + replay deltas)
- Gap detector : si gap > 5 secondes → blocage des nouveaux trades
- Heartbeat monitoring : si silent > 30 sec → force reconnect
- Intégration avec `data_backbone/freshness_checker/`

**Invariants** :
- Au boot : snapshot REST puis WS, jamais l'inverse
- En cas de reconnect : nouveau snapshot REST avant de reprendre
- En cas de gap détecté : refus de trader jusqu'à resync OK

**Modules touchés** :
- Nouveau : `src/venue_adapters/binance_spot/ws_client.py`
- Nouveau : `src/venue_adapters/binance_spot/orderbook_manager.py`
- Modifié : `src/data_backbone/freshness_checker/` (ajout d'un hook)

**Critères d'acceptation** :
- [ ] Reconnect automatique OK sur coupure simulée
- [ ] Gap > 5s → état `STALE`, refus de trader
- [ ] Snapshot REST + replay correct (testé via mock)
- [ ] Aucune RAM leak sur 24h de run continu

**Preuves attendues** :
- Test 24h en testnet sans crash mémoire
- Logs reconnects + gap detect

**LOC estimées** : 700-1000

---

### Tranche T4 — P0-1.C : Order translator + signed POST

**Statut repo réel au 2026-04-09** — socle borné codé et prouvé localement, mais tranche pas encore totalement terminée au sens live/testnet.

- `src/venue_adapters/binance_spot/order_translator.py` existe
- `src/venue_adapters/binance_spot/error_classifier.py` existe
- `src/venue_adapters/binance_spot/execution_adapter.py` existe
- `src/venue_adapters/binance_spot/user_data_events.py` existe
- `src/venue_adapters/binance_spot/user_data_ws_client.py` existe
- `src/venue_adapters/binance_spot/bootstrap.py` existe
- `src/protocols/execution_runtime_bootstrap.py` sait maintenant construire un `ExecutionRuntime` Binance via ce builder
- `scripts/run_build9_core_smoke.py` consomme maintenant ce bootstrap sur un smoke borné local
- `src/venue_adapters/binance_spot/rest_client.py` supporte maintenant le signed `POST /api/v3/order`
- `src/venue_adapters/binance_spot/rest_client.py` supporte maintenant le signed `GET /api/v3/openOrders`
- `src/venue_adapters/binance_spot/rest_client.py` supporte maintenant le signed `DELETE /api/v3/order`
- `BinanceSpotExecutionAdapter` satisfait maintenant le protocole `ExecutionVenueAdapter` avec :
  - submit borné
  - replace borné via cancel + submit
  - cancel borné
  - remote state minimal via `openOrders + account snapshot`
  - `poll_order_events()` draine maintenant une source user-data authentifiée bornée quand elle est injectée
  - le parser local couvre déjà `executionReport -> ACK/FILL/CANCELLED/EXPIRED/REJECTED`
  - un client websocket user-data borné sait maintenant faire `subscribe.signature -> poll payloads`
  - un builder borné sait maintenant construire l'adapter depuis `BinanceAdapterConfig + credentials`, avec injection optionnelle du user-data websocket
  - le bootstrap runtime sait maintenant consommer ce builder sur le rail `protocols`
  - un vrai script caller local existe maintenant via `run_build9_core_smoke.py`
- le `clientOrderId` déterministe est maintenant basé sur `engine_id + intent_id`, parce que le repo réel gouverné porte `engine_id` dans `ExecutionIntent`, pas `strategy_id`
- preuve locale ciblée:
  - `rtk pytest tests/test_execution_backbone/test_build9_core_smoke_script.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_venue_adapters/test_binance_spot/test_bootstrap.py tests/test_venue_adapters/test_binance_spot/test_user_data_ws_client.py tests/test_venue_adapters/test_binance_spot/test_execution_adapter.py tests/test_execution_backbone/test_execution_runtime.py -q`
  - résultat: `28 passed`
- cross-check plus large:
  - `rtk pytest tests/test_venue_adapters/test_binance_spot tests/test_execution_backbone tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q`
  - résultat: `193 passed`
- résidu honnête:
  - pas encore de soumission order testnet réelle
  - pas encore de fills/positions live complets via flux événementiel Binance

**Objectif** — Traduction des décisions internes en orders Binance + soumission signée.

**Périmètre** :
- `order_translator.py` : decision → BinanceOrder pydantic
- Validation contre `venue_constraints` (LOT_SIZE, MIN_NOTIONAL, PRICE_FILTER) **avant soumission**
- Signed POST `/api/v3/order` avec HMAC-SHA256
- `clientOrderId` déterministe : `f"v53_{engine_id}_{intent_id}"` (max 36 chars) dans le repo réel actuel
- Pas de retry HTTP : retry explicite après vérif `/openOrders`
- Error classifier (`error_classifier.py`) : mapper les codes Binance vers `OrderRejected`, `InsufficientBalance`, `InvalidLotSize`, etc.

**Invariants** :
- Pre-trade simulation : si `venue_constraints` rejette → pas de submit
- Idempotency : un `intent_id` ne peut produire qu'un seul order accepté
- En cas de timeout : pas de retry automatique, query `/openOrders` pour vérifier

**Modules touchés** :
- Nouveau : `src/venue_adapters/binance_spot/{order_translator,error_classifier}.py`
- Nouveau : signed POST handlers
- Modifié : `src/execution_backbone/` (point de connexion)

**Critères d'acceptation** :
- [ ] Soumission order testnet OK
- [ ] Rejet pré-soumission sur LOT_SIZE invalide
- [ ] Pas de double soumission lors d'un timeout simulé
- [ ] Tous les codes d'erreur Binance documentés sont mappés

**LOC estimées** : 800-1200

---

### Tranche T5 — P0-2 : Halal compliance layer

**Statut repo réel au 2026-04-09** — tranche bornée avancée et prouvée localement, mais pas encore totalement terminée.

- `src/sharia_compliance/contracts.py` existe
- `src/sharia_compliance/policy_loader.py` existe
- `src/sharia_compliance/asset_whitelist.py` existe
- `src/sharia_compliance/asset_blacklist.py` existe
- `src/sharia_compliance/stablecoin_policy.py` existe
- `src/sharia_compliance/trade_type_guard.py` existe
- `src/sharia_compliance/pair_screening.py` existe
- `src/sharia_compliance/pair_screening_registry.py` existe
- `src/sharia_compliance/pair_screening_audit.py` existe
- `src/sharia_compliance/purification_calculator.py` existe
- `src/sharia_compliance/policy_audit_logger.py` existe
- `src/sharia_compliance/account_features_audit.py` existe
- `src/sharia_compliance/sharia_runtime.py` existe
- `src/venue_adapters/binance_spot/account_feature_provider.py` existe
- `scripts/run_sharia_account_audit.py` existe
- `scripts/run_sharia_pair_screening_audit.py` existe
- `src/sharia_compliance/sharia_alerts.py` existe
- `config/sharia/policy_v1.yml` existe
- `src/execution_backbone/execution_runtime.py` appelle maintenant `sharia_trade_authorizer.authorize_trade()` avant toute soumission venue
- `NoTradeReason.SHARIA_BLOCKED` existe maintenant dans le runtime d'exécution
- preuves locales ciblées:
  - `rtk pytest tests/test_sharia_compliance/test_purification_calculator.py tests/test_sharia_compliance/test_account_features_audit.py -q`
  - résultat: `6 passed`
  - `rtk pytest tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_venue_adapters/test_binance_spot/test_account_feature_provider.py tests/test_sharia_compliance/test_account_features_audit.py tests/test_sharia_compliance/test_account_features_audit_launcher.py -q`
  - résultat: `13 passed`
  - `rtk pytest tests/test_sharia_compliance/test_sharia_alerts.py tests/test_sharia_compliance/test_account_features_audit_launcher.py tests/test_venue_adapters/test_binance_spot/test_account_feature_provider.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py -q`
  - résultat: `11 passed`
  - `python -m pytest tests/test_sharia_compliance/test_pair_screening.py tests/test_sharia_compliance/test_trade_type_guard.py tests/test_execution_backbone/test_execution_runtime.py -q`
  - résultat: `31 passed`
  - `python -m pytest tests/test_sharia_compliance/test_pair_screening_registry.py tests/test_sharia_compliance/test_pair_screening_audit.py tests/test_sharia_compliance/test_pair_screening_audit_launcher.py tests/test_sharia_compliance/test_pair_screening.py tests/test_sharia_compliance/test_trade_type_guard.py tests/test_execution_backbone/test_execution_runtime.py -q`
  - résultat: `37 passed`
  - `rtk pytest tests/test_sharia_compliance tests/test_execution_backbone/test_execution_runtime.py -q`
  - résultat: `39 passed`
  - `rtk pytest tests/test_sharia_compliance tests/test_execution_backbone/test_execution_runtime.py -q`
  - résultat: `29 passed`
- cross-check élargi:
  - `rtk pytest tests/test_sharia_compliance tests/test_execution_backbone/test_execution_runtime.py tests/test_venue_adapters/test_binance_spot tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q`
  - résultat: `82 passed`
  - `rtk pytest tests/test_sharia_compliance tests/test_execution_backbone tests/test_venue_adapters/test_binance_spot tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q`
  - résultat: `208 passed`
- résidu honnête:
  - pas encore de preuve Testnet réelle du launcher d'audit hebdomadaire
  - pas encore de kill switch ou d'alerte externe branchés depuis ces `AlertRecord`
  - pas encore de provider live/externe branché pour alimenter automatiquement le pair screening AAOIFI
  - la version courante couvre le veto halal avant submit, le pair screening AAOIFI déterministe via metadata, le registre dataset local versionné, l'audit HC-4 des paires tradées, la purification bornée, le provider Binance read-only, le launcher d'audit hebdomadaire et la projection `AlertRecord` critique, pas encore toute la story complète T5

**Objectif** — Module `sharia_compliance/` qui enforce les règles halal de manière non-contournable.

**Périmètre** :
- `asset_whitelist.py` + `asset_blacklist.py` (chargés depuis YAML versionné)
- `stablecoin_policy.py` (selon décision Phase 0)
- `trade_type_guard.py` : refuse tout trade type ≠ SPOT (pas de margin, pas de futures, pas de borrow)
- `purification_calculator.py`
- `policy_audit_logger.py` : log de chaque autorisation/refus avec versioning
- `sharia_runtime.py` : façade `authorize_trade(decision) -> ShariaPermit | ShariaRejection`
- Audit hebdomadaire `account_features_audit.py` : query Binance et alerte si Earn/Margin/Futures détectés

**Invariants** :
- Aucun trade ne peut être soumis sans passer par `sharia_runtime.authorize_trade()`
- Refus loggué = trade jamais soumis
- Versioning des policies : si la policy change, on peut retracer les trades sous v1 vs v2

**Modules touchés** :
- Nouveau : `src/sharia_compliance/` (full module)
- Nouveau : `tests/sharia_compliance/`
- Config : `config/sharia/policy_v1.yml`
- Hook : `execution_backbone/order_decider/` doit appeler `sharia_runtime.authorize_trade()` avant tout submit

**Critères d'acceptation** :
- [ ] 100 % des décisions passent par sharia_runtime
- [ ] Tests : asset blacklisté → refus
- [ ] Tests : asset OK + stablecoin OK → permit
- [ ] Audit hebdomadaire détecte un Simple Earn activé en < 24h
- [ ] Policy versioning fonctionne

**LOC estimées** : 800-1200

---

### Tranche T6 — P0-3 : Fee-aware minimum-edge filter

**Statut repo réel au 2026-04-10** — tranche partiellement codée sur le vrai coeur Local IA Lab + shared core, avec premier consommateur runtime réel.

- `src/local_replay_runtime/edge_gate_calibration.py` existe
- `src/scoring_backbone/fee_aware_edge_gate.py` existe
- `tests/test_local_replay_runtime/test_edge_gate_calibration.py` existe
- `tests/test_scoring_backbone/test_fee_aware_edge_gate.py` existe
- preuve locale:
  - `rtk pytest tests/test_local_replay_runtime/test_edge_gate_calibration.py tests/test_scoring_backbone/test_fee_aware_edge_gate.py -q`
  - résultat: `6 passed`
  - `rtk pytest tests/test_calibration_loader/test_contracts.py tests/test_calibration_loader/test_loader.py tests/test_local_replay_runtime/test_replay_executor.py tests/test_scoring_backbone/test_scoring_runtime.py -q`
  - résultat: `22 passed`
- closure obtenue:
  - le premier producteur `13-A EDGE` existe maintenant côté Local IA Lab
  - `THR-E01` et `THR-E02` peuvent être calibrés depuis des `DTRRecord` replay exécutés
  - la publication est conservative: borne haute d'IC bootstrap + floor humain
  - un artefact partagé `CalibrationArtifact` peut maintenant être produit pour `THR-E01` / `THR-E02`
  - `scripts/run_edge_gate_calibration.py` lit maintenant soit un `replay_dtr.jsonl` gouverné, soit un `export_dir` gouverné complet, puis écrit un `edge_gate.yml` signé
  - le même launcher émet maintenant `edge_gate.input_summary.json` comme sortie future-facing d'audit / dashboard
  - `scripts/run_local_lab_analysis_bundle.py` peut maintenant enchaîner le même `export_dir` vers post-trade review + edge calibration avec une sortie unique `local_lab_analysis_summary.json`
  - `scripts/run_local_lab_post_trade_review.py` émet maintenant aussi `trade_loss_attribution.json` comme sidecar typé par trade
  - ce sidecar explique pourquoi un trade perd (`cost_drift / sterilization / edge_degraded / trace_coverage / unclassified_loss`) et propose une action préventive gouvernée
  - `scripts/run_local_lab_analysis_bundle.py` remonte maintenant aussi ce sidecar dans son résumé future-facing
  - `src/local_replay_runtime/walk_forward_review.py` existe maintenant comme gate humain typé pour anti-fuite / anti-overlap
  - `scripts/run_local_lab_analysis_bundle.py` émet désormais `walk_forward_review.template.json` et `walk_forward_review.summary.json`
  - par défaut, le walk-forward reste `pending`; il faut un review humain approuvé pour faire passer `walk_forward_pass`
  - `src/local_replay_runtime/artifact_proof_summary_builder.py` existe maintenant comme builder conservatif du `ArtifactProofSummary` canonique côté Local IA Lab
  - `scripts/run_local_lab_analysis_bundle.py` émet désormais aussi `artifact_proof_summary.json` et `artifact_proof_assessment.json`
  - doctrine now reflected in code:
    - les dimensions prouvables aujourd'hui sont dérivées depuis `MetaRuntimeResult`, `trade_loss_attribution.json`, et `walk_forward_review.summary.json`
    - les dimensions non encore closes par une vraie étude d'ablation restent fail-close, pas remplies par des valeurs flatteuses
    - en pratique, le bundle Lab sait maintenant dire explicitement `not ready for VPS import yet` au lieu d'échouer implicitement
  - `src/local_replay_runtime/artifact_ablation_study.py` existe maintenant comme étude baseline-vs-candidate gouvernée
  - `scripts/run_local_lab_analysis_bundle.py` accepte maintenant `--baseline-export-dir`
  - le bundle Lab émet désormais aussi `artifact_ablation_study.json`
  - si un baseline export gouverné aligné est fourni:
    - `ablation_delta_net_pnl`
    - `ablation_delta_ce`
    - `block_rate_delta`
    sont calculés à partir de DTR alignés par `dtr_id`, pas simulés
  - si aucun baseline n'est fourni, l'étude d'ablation reste explicitement `not ready`
  - `src/local_replay_runtime/local_lab_scope_matrix.py` existe maintenant comme projection multi-scope typée `pair x engine`
  - `scripts/run_local_lab_analysis_bundle.py` accepte maintenant `--all-scopes`
  - sur un export gouverné multi-scope, le bundle peut maintenant émettre une matrice `local_lab_scope_matrix.json` sans review manuelle scope par scope
  - chaque scope écrit désormais sous `output-root/scopes/<pair>__<engine>/`:
    - `post_trade_review/`
    - `artifact_ablation_study.json`
    - `artifact_proof_summary.json`
    - `artifact_proof_assessment.json`
  - la matrice future-facing expose par scope:
    - `artifact_ablation_ready`
    - `artifact_proof_ready`
    - `artifact_proof_validation_reasons`
    - les chemins de sidecars gouvernés
  - la preuve multi-scope reste fail-close:
    - `total_opportunities` est maintenant recalculé par scope, pas hérité silencieusement du manifest global
    - aucun scope ne passe en `ready` sans walk-forward humain approuvé et baseline aligné
  - `src/local_replay_runtime/artifact_release_candidate.py` existe maintenant comme sidecar de packaging Local IA Lab -> VPS
  - `scripts/run_local_lab_analysis_bundle.py` émet désormais aussi `artifact_release_candidate.json`
  - ce sidecar ne construit pas encore un `ArtifactImportRequest`; il borne le pré-packaging Lab avec:
    - `release_status`
    - `ready_for_shadow_import`
    - `blocking_reasons`
    - `release_scopes` quand une matrice multi-scope existe
  - `src/local_replay_runtime/artifact_upload_bridge_candidate.py` existe maintenant comme pont dry-run borné `release_candidate -> ArtifactUploadRequest / ArtifactImportRequest`
  - `scripts/run_local_lab_analysis_bundle.py` émet désormais aussi:
    - `artifact_import_dry_run_bridge.json`
    - `artifact_upload_request.dry_run.json`
    - `artifact_import_request.dry_run.json`
    - `artifact_import_decision.dry_run.json`
    - `artifact_upload_decision.dry_run.json`
  - ce pont reste strictement fail-close:
    - aucun `date.today()` caché pour la gouvernance
    - `artifact_class`, `artifact_scope`, `training_end`, `governance_reference_date`, `lifecycle`, `drift_score_threshold` doivent être explicites
    - sans preuve prête ou sans inputs de gouvernance explicites, le bridge reste bloqué avec raisons typées
  - ce pont expose maintenant explicitement la sémantique actuelle:
    - l'artefact source Local IA Lab reste l'artefact calibration (`edge_gate.yml`)
    - le handoff dry-run transporté aujourd'hui reste un packet gouverné dérivé du replay export (`review_packet`)
    - les sidecars n'assimilent plus implicitement ces deux identités
  - vérité importante:
    - le sidecar de release garde l'artefact Local IA Lab (`edge_gate.yml`)
    - le pont sec matérialise aujourd'hui le rail gouverné existant de `backtest_artifact_import` autour du replay/export packet
    - ce n'est pas encore un upload live ni une promotion VPS
  - `scripts/run_local_replay_export.py` peut maintenant aussi émettre cet artefact EDGE en option explicite au moment de l'export gouverné
  - le futur consommateur `src/scoring_backbone/fee_aware_edge_gate.py` existe maintenant comme helper pur résolvant `THR-E01` / `THR-E02` via `calibration_loader`
  - `src/execution_backbone/execution_runtime.py` peut maintenant bloquer un trade avant submit quand le gate fee-aware échoue
  - `src/protocols/execution_runtime_bootstrap.py` sait maintenant passer une `FeeAwareEdgeGateConfig` aux builders runtime d'exécution
  - `src/venue_adapters/binance_spot/time_sync.py` et `config/binance_adapter.yml` portent maintenant un enable flag gouverné `fee_aware_edge_gate_enabled`
  - `build_binance_execution_runtime(...)` peut maintenant dériver un config EDGE standard depuis `calibration_root/calibration_version` quand ce flag est activé
  - la sortie future-facing minimale existe maintenant aussi:
    - `NoTradeDecision.context`
    - `DecisionEvent.no_trade_reason`
    - `DecisionEvent.context`
  - le blocage fee-aware n'est donc plus seulement un `detail` texte; il expose aussi un payload structuré pour audit/monitoring futur
- résidu honnête:
  - pas encore de source standard unique injectant ce gate partout hors rail runtime Binance / builder borné
  - pas encore de consommation plus haute dans scoring / engines
  - pas encore de preuve replay réelle humaine sur un dataset de calibration signé
  - le mapping `walk_forward_review.summary.json -> ArtifactProofSummary` est maintenant ouvert et câblé côté Local IA Lab
  - le `ArtifactProofSummary` reste fail-close si aucun baseline export gouverné n'est fourni
  - le slice d'ablation baseline-vs-candidate est maintenant réellement ouvert et câblé
  - le prochain slice cœur Local IA Lab est maintenant explicite: faire évoluer ce pont sec en packaging plus complet vers le vrai handoff VPS, notamment sur la sémantique finale `artifact_id / artifact_kind`

**Objectif** — Refuser tout trade dont l'edge attendu n'est pas suffisamment supérieur aux fees + slippage.

**Périmètre** :
- `FeeAwareEdgeGate` dans `scoring_backbone/` ou `execution_backbone/`
- Formule : `accept ⇔ expected_edge_bps ≥ edge_multiplier × (fee_round_trip_bps + slippage_estimate_bps)`
- `edge_multiplier` chargé depuis l'artefact de calibration (typiquement 2.0)
- Intégration avec `execution_cost_meter/fee_meter.py` existant

**Invariants** :
- Aucun trade soumis ne peut violer cette règle
- `edge_multiplier` jamais hardcodé

**Critères d'acceptation** :
- [ ] Test : edge 10 bps, fee 5 bps, slippage 2 bps, multiplier 2 → refus (10 < 14)
- [ ] Test : edge 20 bps, fee 5 bps, slippage 2 bps, multiplier 2 → permit (20 ≥ 14)
- [ ] Hook dans le path d'exécution

**LOC estimées** : 150-300

---

### Tranche T7 — P0-5.A : Engine C tests rattrapage (Option A : feature flag)

**Objectif** — Option A simple : marquer Engine C comme `experimental` avec feature flag, ne le mettre actif que si `engines.c.enabled = True` (false par défaut). Engine C ne tournera donc PAS en MICRO_LIVE Phase 3.

**Périmètre** :
- Feature flag dans `config/engines.yml`
- Modification minimale du runtime pour skip Engine C si disabled
- Tests pour vérifier le skip

**Critères d'acceptation** :
- [ ] Engine C disabled par défaut
- [ ] Aucune décision Engine C en MICRO_LIVE
- [ ] Tests existants restent verts

**LOC estimées** : 50-100

> **Note** : Option B (refactor complet engine C) reportée à post-LIVE Phase 4. Décision à confirmer en Phase 0.

---

### Tranche T8 — P0-5.B : Engine D tests rattrapage (Option A : feature flag)

Identique à T7 mais pour Engine D.

**LOC estimées** : 50-100

---

## 3. Phase 1bis — Tranches P1

### Tranche T9 — P1-1 : Regime awareness lite (3 états)

**Objectif** — Détecteur de régime à 3 états (CALM / STRESSED / EXTREME) avec hystérésis, basé sur indicateurs simples (BTC realized vol 24h, dispersion rendements, gap-down counter).

**Périmètre** :
- `src/regime_classifier/regime_lite.py`
- Indicateurs : realized vol BTC 24h, max drawdown intraday, dispersion entre engines
- Hystérésis : remonter d'un état nécessite 2 heures de stabilité dans l'état inférieur
- Hooks dans `risk_backbone/` : EXTREME → exit toutes positions + plus d'entries 24h

**Invariants** :
- Seuils chargés depuis calibration artefact
- Pas de skip d'état (un passage CALM → EXTREME passe par STRESSED si lent, ou direct si event soudain avec trace explicite)

**Critères d'acceptation** :
- [ ] Replay sur mars 2020, mai 2021, novembre 2022 : état EXTREME détecté en < 2h après le début du crash
- [ ] Replay sur sideways 2024 : état CALM dominant
- [ ] Hooks dans `risk_backbone/exposure_budgeter/` actifs

**LOC estimées** : 400-600

---

### Tranche T10 — P1-2 + P1-3 : Reconciliation périodique + Daily P&L breaker

**Objectif** — Forcer une reconciliation au boot et toutes les 60 min. Câbler le daily P&L breaker au kill switch existant.

**Périmètre** :
- Schedule task `reconciliation_scheduler.py` (boot + 60 min)
- `daily_pnl_breaker.py` qui consomme l'équity tracker existant
- Seuils dynamiques : −2 % intraday → SHADOW automatique, −10 % week → kill switch (à calibrer)

**Critères d'acceptation** :
- [ ] Reconciliation au boot bloque le trading si divergence
- [ ] Daily breaker SHADOW automatique en cas de DD intraday > seuil
- [ ] Pas de réactivation automatique le jour même

**LOC estimées** : 300-500

---

### Tranche T11 — P1-4 + P1-5 : Telegram alerter + Disk monitor + Log rotation

**Objectif** — Push notifications pour les events critiques + monitoring disque + rotation logs.

**Périmètre** :
- `src/alerting/telegram_alerter.py` : send via bot token (sealed)
- `src/monitoring/disk_monitor.py` : check free space, alerte à 70 % et 90 %
- `src/monitoring/log_rotation.py` : gzip + retention 90j

**Critères d'acceptation** :
- [ ] Alerte Telegram reçue end-to-end pour un kill switch
- [ ] Disque monitor alerte au seuil
- [ ] Logs rotated et compressés

**LOC estimées** : 400-600

---

## 4. Phase 2 — Tranches V37 bricks (à incorporer en simplifié)

### Tranche T12 — V37-2 : Execution Gatekeeper central wrapper

**Objectif** — Wrapper non-destructif `authorize()` qui chaîne les guards V5.3 existants en une décision unique auditable.

**Périmètre** :
- `src/execution_backbone/gatekeeper/gatekeeper.py`
- `GateChain` qui itère sur les guards existants (sharia, fee_edge, regime, btc_factor, exposure, kill_switch, freshness, ...)
- `ExecutionPermit` ou `ExecutionRefusal` en sortie, avec trace de tous les gates traversés
- Le code existant continue de fonctionner — le gatekeeper est un point de convergence, pas un remplaçant

**Invariants** :
- Non-destructif : aucun guard existant n'est supprimé
- Audit trail : chaque permit/refusal logge les N gates traversés et leur verdict

**Critères d'acceptation** :
- [ ] Toutes les décisions de trade passent par `gatekeeper.authorize()`
- [ ] Trace audit complète dans `artifacts/gatekeeper/`
- [ ] Aucune régression : tests verts

**LOC estimées** : 400-700

---

### Tranche T13 — V37-3 : Information Stress Monitor (lite)

**Objectif** — Détecteur "le marché ment" en temps réel, 5 indicateurs simples, veto sur entries en cas de stress information.

**Périmètre** :
- `src/risk_backbone/info_stress_monitor.py`
- Indicateurs : spread bid-ask explosion, depth ratio collapse, order cancellation rate spike, taker imbalance saturation, micro-vol divergence
- Sortie : `InfoStressLevel` (NORMAL / ELEVATED / EXTREME)
- Hook : EXTREME → veto entries pendant cooldown

**Critères d'acceptation** :
- [ ] Replay sur les 3 windows de capitulation : ELEVATED ou EXTREME détecté
- [ ] Replay sur sideways : NORMAL dominant
- [ ] Veto fonctionnel

**LOC estimées** : 400-600

---

## 5. Tableau de synthèse — toutes les tranches

| # | Tranche | Phase | Nature | LOC | Bloque quoi si fail |
|---|---|---|---|---|---|
| T1 | P0-1.A REST + time sync | 1 | P0 | 600-900 | Tout |
| T2 | P0-4 sealed secrets | 1 | P0 | 200-400 | T1 |
| T3 | P0-1.B WS + gap recovery | 1 | P0 | 700-1000 | Live trading |
| T4 | P0-1.C Order translator | 1 | P0 | 800-1200 | Live trading |
| T5 | P0-2 Halal compliance | 1 | P0 | 800-1200 | Halal compliance |
| T6 | P0-3 Fee-aware edge gate | 1 | P0 | 150-300 | Profitabilité |
| T7 | P0-5.A Engine C feature flag | 1 | P0 | 50-100 | Risk MICRO_LIVE |
| T8 | P0-5.B Engine D feature flag | 1 | P0 | 50-100 | Risk MICRO_LIVE |
| T9 | P1-1 Regime lite | 1bis | P1 | 400-600 | Phase 4 LIVE |
| T10 | P1-2 + P1-3 Recon + Daily breaker | 1bis | P1 | 300-500 | Phase 4 LIVE |
| T11 | P1-4 + P1-5 Telegram + Disk | 1bis | P1 | 400-600 | Phase 4 LIVE |
| T12 | V37-2 Gatekeeper central | 2 | Optionnel | 400-700 | Audit / robustesse |
| T13 | V37-3 Info stress monitor | 2 | Optionnel | 400-600 | Phase 4 LIVE |
| **Total** | | | | **5250-8200** | |

**13 tranches** au total. Si on regroupe T7+T8 et T10+T11 et T12+T13 : **10 tranches effectives**.

---

## 5bis. Latest bounded bridge semantics

- the current Local IA Lab source artifact remains the calibration artifact `edge_gate.yml`
- the current dry-run transport artifact still remains the governed replay-derived `review_packet`
- `scripts/run_local_lab_analysis_bundle.py` now also emits `artifact_source_summary.json`
- this new sidecar exposes a stable future-dashboard summary of the real source artifact:
  - `artifact_id`
  - `artifact_family`
  - `schema_version`
  - `version`
  - `threshold_count`
- the dry-run transport packet now carries both:
  - the source artifact ref
  - the `artifact_source_summary.json` ref
  - via `ArtifactPayloadRefBundle.supplementary_refs`
- `src/local_replay_runtime/artifact_upload_bridge_candidate.py` now reports this explicitly as:
  - `semantic_status = transport_packet_with_source_artifact_refs`
- important invariant:
  - do not invent a new artifact kind or a parallel import rail for this slice

## 5ter. Latest bounded recalibration planning slice

- the Local IA Lab bundle now also emits `local_lab_recalibration_plan.json`
- this sidecar is the first bounded answer to:
  - what should be recalibrated locally from governed loss evidence
  - what must stay blocked before any new artifact is exported toward the VPS rail
- current inputs:
  - `trade_loss_attribution.json`
  - optional `local_lab_scope_matrix.json`
- current outputs:
  - `recommended_threshold_ids`
  - `calibration_candidate_ready`
  - `blocking_reasons`
  - typed recalibration actions such as:
    - `recalibrate_edge_gate`
    - `review_scope_sterilization`
    - `improve_trace_capture`
- important invariant:
  - this slice still plans recalibration locally; it does not mutate runtime or bypass the governed export/import rail

## 5quater. Latest bounded EDGE provenance slice

- `scripts/run_edge_gate_calibration.py` now accepts an optional `--recalibration-plan-path`
- `edge_gate.input_summary.json` can now carry:
  - `recalibration_plan_ref`
  - `recalibration_candidate_ready`
  - `recalibration_blocking_reasons`
  - `recalibration_recommended_threshold_ids`
- `scripts/run_local_lab_analysis_bundle.py` now builds the Local IA Lab recalibration plan first, then runs EDGE calibration with that plan attached
- important invariant:
  - this only enriches audit/provenance of the Local IA Lab artifact producer
  - it does not alter the governed VPS import rail or runtime mode semantics

## 5quinquies. Latest bounded packaging gate refinement

- `src/local_replay_runtime/artifact_release_candidate.py` now consumes the Local IA Lab recalibration plan explicitly
- a release candidate now requires:
  - `local_lab_recalibration_plan_path`
  - recalibration blockers that are coherent with the intended export
- current conservative rule:
  - `NO_LOSING_TRADES_TO_RECALIBRATE` is treated as benign
  - other recalibration blockers remain release blockers
- important invariant:
  - `shadow_candidate` can no longer emerge from proof sidecars alone without a coherent local recalibration plan

## 5sexies. Latest bounded release-gate projection refinement

- `src/local_replay_runtime/artifact_upload_bridge_candidate.py` now exposes the packaging verdict explicitly instead of forcing future tooling to re-derive it from multiple sidecars
- the dry-run bridge now carries:
  - `release_ready_for_shadow`
  - `release_artifact_proof_ready`
  - `release_artifact_proof_validation_reasons`
  - `release_recalibration_candidate_ready`
  - `release_recalibration_blocking_reasons`
  - `release_gate_status`
  - `release_gate_reasons`
- `scripts/run_local_lab_analysis_bundle.py` now forwards the same release-gate projection into `local_lab_analysis_summary.json`
- current bounded statuses:
  - `proof_and_recalibration_backed`
  - `proof_backed_no_recalibration_required`
  - `proof_gate_blocked`
  - `recalibration_gate_blocked`
  - `release_candidate_blocked`
- important invariant:
  - the handoff remains dry-run only
  - the projection must stay fail-close and must reflect the full proof blocker set, not a truncated reason list

## 5septies. Latest bounded release-gate sidecar transport refinement

- `scripts/run_local_lab_analysis_bundle.py` now emits `artifact_release_gate_summary.json`
- `src/local_replay_runtime/artifact_upload_bridge_candidate.py` now requires `release_gate_summary_ref` for a fully governed dry-run handoff
- the dry-run transport packet now carries, in `supplementary_refs`:
  - the source artifact ref
  - the source artifact summary ref
  - the release-gate summary ref
- important invariant:
  - the existing governed import rail is preserved
  - the transport packet becomes more audit-complete without inventing a new artifact kind or mutating VPS behavior

## 5octies. Latest bounded multi-scope release drill-down refinement

- `src/local_replay_runtime/artifact_release_candidate.py` now carries richer per-scope release rows
- each release scope now preserves drill-down refs already known to the Local IA Lab:
  - `review_bundle_path`
  - `trade_loss_attribution_path`
  - `artifact_proof_summary_path`
  - `artifact_proof_assessment_path`
  - `executed_records`
  - `losing_trade_count`
- `scripts/run_local_lab_analysis_bundle.py` now also exposes:
  - `release_ready_scope_slugs`
  - `release_blocked_scope_slugs`
- important invariant:
  - this is still a projection-only refinement
  - it improves future dashboard and operator drill-down without creating per-scope VPS mutation semantics

## 5novies. Latest bounded per-scope release-sidecar refinement

- `scripts/run_local_lab_analysis_bundle.py` now emits `artifact_release_scope_summary.json` under each `scopes/<slug>/` directory when multi-scope review is active
- each scope sidecar links:
  - the shared artifact path
  - the shared release-gate summary
  - the shared dry-run bridge
  - the scope-specific proof/review sidecars
- the top-level summary now also exposes:
  - `release_scope_summary_count`
  - `release_scope_summary_paths`
- important invariant:
  - these scope sidecars remain descriptive packaging/handoff views
  - they do not imply a separate per-scope upload or import protocol

## 5decies. Latest bounded scope-matrix packaging projection

- `src/local_replay_runtime/local_lab_scope_matrix.py` now distinguishes:
  - proof-ready scope counts
  - release-ready scope counts
- each `LocalLabScopeAnalysisRow` can now carry:
  - `release_ready`
  - `release_blocking_reasons`
  - `release_scope_summary_path`
- `scripts/run_local_lab_analysis_bundle.py` now rewrites `local_lab_scope_matrix.json` after packaging so the matrix reflects the later release-side truth, not only the earlier proof-side truth
- the top-level summary now also exposes:
  - `release_scope_ready_count`
  - `release_scope_blocked_count`
- important invariant:
  - the scope matrix remains descriptive and typed
  - no new per-scope import rail is introduced by this refinement

## 5undecies. Latest bounded promotion-readiness projection

- `src/local_replay_runtime/local_lab_promotion_readiness.py` now translates the Local IA Lab packaging/dry-run truth into canonical promotion vocabulary
- `scripts/run_local_lab_analysis_bundle.py` now emits `artifact_promotion_readiness_summary.json`
- this summary uses shared-core canonical values instead of inventing new labels:
  - `ArtifactActivationStage`
  - `PromotionState`
  - `ReviewState`
- current bounded readiness statuses:
  - `local_only`
  - `shadow_candidate_pending_dry_run`
  - `shadow_candidate_dry_run_ready`
- important invariant:
  - this remains descriptive packaging state only
  - no auto-promotion or live VPS mutation is introduced by this summary

## 5terdecies. Latest bounded Local IA Lab monitoring projection

- `src/local_replay_runtime/local_lab_monitoring_projection.py` now emits one compact future-dashboard-ready projection over the real Local IA Lab packaging rail
- `scripts/run_local_lab_analysis_bundle.py` now writes `local_lab_monitoring_projection.json`
- `local_lab_analysis_summary.json` now also exposes:
  - `local_lab_monitoring_projection_path`
  - `monitoring_projection_status`
  - `monitoring_projection_detail`
- this projection normalizes:
  - core Local IA Lab readiness (`review / trade_loss / walk_forward / ablation / proof / edge`)
  - packaging/handoff truth (`release_status`, `bridge_status`, `release_gate_status`, `semantic_status`)
  - canonical promotion truth already projected by `artifact_promotion_readiness_summary.json`
  - scope and release counts for future Local IA Lab dashboards
- bounded status mapping:
  - `healthy` only when the dry-run handoff is ready
  - `critical` only when core Local IA Lab outputs are incomplete
  - otherwise `warning/info` as descriptive audit state
- important invariant:
  - this is still projection only
  - no UI rail, no new runtime rail, and no promotion behavior are introduced

## 5quaterdecies. Latest bounded Local IA Lab observability export

- `src/local_replay_runtime/local_lab_observability.py` now emits a standard `ObservabilityExport` over the compact Local IA Lab monitoring projection
- `scripts/run_local_lab_analysis_bundle.py` now writes `local_lab_observability_export.json`
- the top-level summary now also exposes:
  - `local_lab_observability_export_path`
  - `local_lab_observability_sample_count`
- current export content:
  - stable metric samples for review/proof/recalibration/release/dry-run truth
  - scope and release counts
  - Prometheus-like `text_payload` for later monitoring ingestion
- important invariant:
  - this remains local, descriptive, and non-UI
  - it does not change any runtime or promotion semantics

## 5quindecies. Latest bounded Local IA Lab monitoring backend payload

- `src/local_replay_runtime/local_lab_monitoring_backend.py` now adapts the Local IA Lab monitoring projection plus the standard observability export into one backend-consumable typed payload
- `src/monitoring/contracts.py` now defines `LocalLabMonitoringBackendPayload`
- `scripts/run_local_lab_analysis_bundle.py` now writes `local_lab_monitoring_backend_payload.json`
- the top-level summary now also exposes:
  - `local_lab_monitoring_backend_payload_path`
  - `local_lab_monitoring_backend_status`
- current payload content is intentionally descriptive only:
  - normalized run/export/artifact identifiers
  - current review/proof/recalibration/release/dry-run truth
  - scope and release counts
  - refs back to the detailed sidecars and the observability export
- important invariant:
  - this is a future monitoring/backend surface only
  - it does not introduce a new runtime rail
  - it does not introduce UI coupling
  - it does not mutate VPS state or promotion behavior

## 5sexdecies. Latest bounded Local IA Lab monitoring ingestion summary

- `src/monitoring/local_lab_ingestion.py` now exists as the monitoring-side ingestion adapter for the Local IA Lab pair:
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- `src/monitoring/contracts.py` now defines `LocalLabMonitoringIngestionSummary`
- `scripts/run_local_lab_analysis_bundle.py` now writes `local_lab_monitoring_ingestion_summary.json`
- the top-level summary now also exposes:
  - `local_lab_monitoring_ingestion_summary_path`
  - `local_lab_monitoring_ingestion_ready`
- current builder behavior:
  - validates `correlation_id`
  - validates `profile`
  - validates `runtime_mode`
  - validates `timestamp_ms`
  - computes an ingestion-ready boolean plus a short detail
- important invariant:
  - this is still descriptive-only Local IA Lab plumbing
  - it does not create Build-10 runtime coupling
  - it does not create UI semantics
  - it does not modify promotion or VPS behavior

## 5septdecies. Latest bounded Local IA Lab monitoring bundle loader

- `src/monitoring/local_lab_bundle_loader.py` now exists as the file-based loader for the Local IA Lab monitoring trio:
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
  - `local_lab_monitoring_ingestion_summary.json`
- it returns a typed `LocalLabMonitoringBundle`
- current loader checks remain bounded:
  - all three files exist
  - all three files validate against typed contracts
  - `correlation_id/profile/runtime_mode/timestamp_ms` stay aligned across the trio
- important invariant:
  - this is still local, descriptive, future-backend plumbing only
  - it does not create Build-10 runtime coupling
  - it does not create new promotion or VPS behavior

## 6. Estimation effort agent codeur

**Hypothèse session agent codeur** : 1 session = 1500-2500 LOC, ~2-4 heures de coding focalisé, doit produire un état mergeable.

| Tranche | Sessions estimées |
|---|---|
| T1 | 0.5 |
| T2 | 0.25 |
| T3 | 0.75 |
| T4 | 0.5 |
| T5 | 0.75 |
| T6 | 0.25 |
| T7+T8 | 0.25 |
| T9 | 0.5 |
| T10 | 0.5 |
| T11 | 0.5 |
| T12 | 0.5 |
| T13 | 0.5 |
| **Total estimé** | **6 sessions code mergeables** |

**Avec marge pour debug, tests, integration testnet** : **8-12 sessions code agent**.

> **Important** : ces sessions sont des **sessions de l'agent codeur Sonnet**, pas des sessions Opus. Opus produit les MD (= ce qu'on est en train de faire). Le ratio attendu est ~1 session Opus pour ~3 sessions code agent.

---

## 7. Ordre de réalisation recommandé

```
T2 (sealed secrets) → bloquant pour T1
↓
T1 (REST + time sync) → bloquant pour T3, T4
↓
T6 (fee gate) → indépendant, peut être fait en parallèle
T7+T8 (engine feature flags) → indépendant, peut être fait en parallèle
↓
T3 (WS + gap) → bloquant pour T4
↓
T4 (Order translator) → bloquant pour le go-live MICRO_LIVE
↓
T5 (Halal compliance) → bloquant pour le go-live MICRO_LIVE
↓
═══ Fin Phase 1 (P0). LOCAL_REPLAY validé. Gate G1 humain. ═══
↓
T9 (Regime lite)
↓
T10 (Recon + Daily breaker)
↓
T11 (Telegram + Disk)
↓
═══ Fin Phase 1bis (P1). Prêt pour SHADOW. ═══
↓
T12 (Gatekeeper central) ← optionnel mais recommandé avant SHADOW
↓
T13 (Info stress monitor) ← optionnel mais recommandé avant SHADOW
↓
═══ Phase 2 (SHADOW) commence sur le VPS. ═══
```

---

## 8. Conditions pour qu'une tranche soit mergeable

Chaque tranche, à la fin :
1. **Tous les tests existants verts** (1026 + nouveaux tests de la tranche)
2. **Coverage des nouveaux fichiers ≥ 80 %**
3. **Aucun seuil hardcodé** (audit grep à faire)
4. **Aucun secret dans le repo** (audit grep avec `git diff`)
5. **Documentation à jour** : README du module modifié si pertinent
6. **Tracker mis à jour** : `2026-04-07_V53_MASTER_DEVELOPMENT_TRACKER.md`
7. **Mémoire mise à jour** si nouvelle convention introduite

Si un de ces critères échoue → la tranche n'est pas mergeable, on continue sur la même branche jusqu'à ce que ça passe.

---

**Suite logique** : `10_DECISIONS_REQUIRED.md` — décisions à prendre par l'humain avant de démarrer.
