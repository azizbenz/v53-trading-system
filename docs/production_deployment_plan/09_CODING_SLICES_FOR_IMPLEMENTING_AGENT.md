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

## 47. Regime lite typed core now exists

- `src/regime_classifier/regime_lite.py` now exists with typed `CALM / STRESSED / EXTREME` state, explicit thresholds, hysteresis, cooldown, and transition trace.
- The first cut stays intentionally bounded:
  - no hidden runtime activation
  - no direct engine wiring
  - no bypass of Shadow / Micro-live / Live gates
- The helper is now registered in the manifest/DAG as `regime_classifier`, so `src/regime_classifier/` is no longer a phantom package.
- Remaining work for T9 stays explicit:
  - threshold loading from real calibration artifacts
  - provider/runtime/risk hooks
  - replay proof on stress windows

## 48. First governed risk consumer for `regime_lite` now exists

- `src/risk_backbone/regime_lite_entry_gate.py` now exists as the first opt-in risk consumer built from `RegimeLiteAssessment`.
- `src/risk_backbone/risk_runtime.py` now exposes a typed `regime_precheck_hook`, following the same governance pattern as the existing micro-friction hook:
  - opt-in only
  - fail-open by default
  - no hidden live activation
- The first bounded behavior is intentionally narrow:
  - block new entries while `EXTREME` or while `EXTREME` cooldown is still active
  - no automatic exit-all wiring yet
  - no direct engine-specific regime veto yet

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

## 5octodecies. Latest bounded Local IA Lab observability text export

- `src/monitoring/observability_io.py` now exists as a generic writer for persisted `ObservabilityExport.text_payload`
- `scripts/run_local_lab_analysis_bundle.py` now also writes `local_lab_observability.prom`
- the top-level bundle summary now also exposes:
  - `local_lab_observability_text_path`
- current behavior:
  - writes the exact `text_payload`
  - appends one trailing newline
  - stays generic, not Local-Lab-specific in implementation
- important invariant:
  - this remains descriptive export plumbing only
  - it does not introduce UI coupling
  - it does not introduce Prometheus runtime semantics by itself
  - it does not alter VPS behavior or promotion logic

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
## 5novodecies. Latest bounded Local IA Lab research-priority scorer

- `src/local_replay_runtime/local_lab_research_priority.py` now exists as the first bounded research-model-style component inside the Local IA Lab core
- it remains intentionally transparent:
  - `model_family=interpretable_priority_model_v1`
  - `model_kind=transparent_weighted_score`
  - no hidden training
  - no runtime coupling
- current inputs:
  - `trade_loss_attribution` sidecars
  - `scope_matrix` when present
  - current proof/release readiness
- current outputs:
  - `local_lab_research_priority.json`
  - summary fields on `local_lab_analysis_summary.json`
  - compact propagation into the Local IA Lab monitoring projection/backend/observability surfaces
- current ranking intent:
  - identify which `pair x engine` scope should get the next replay/recalibration cycle
  - keep trace-quality problems separate from true recalibration candidates
- important invariant:
  - local-only
  - descriptive and audit-ready
  - no VPS mutation
  - no promotion semantics by itself

## 5vicies. Latest bounded Local IA Lab loss-surrogate scorer

- `src/local_replay_runtime/local_lab_loss_surrogate.py` now exists as the first truly trained but still transparent Local IA Lab component
- the model remains strictly bounded:
  - `model_family=transparent_linear_loss_surrogate_v1`
  - `model_kind=diagonal_lda_linear_score`
  - local-only
  - no runtime/VPS coupling
- training inputs are decision-time / no-lookahead only:
  - `raw_score`
  - `penalized_score`
  - `final_score`
  - `expected_cost`
  - `ce_expected`
  - `candidate_size`
  - `final_size`
  - `ranking_position`
- current outputs:
  - `local_lab_loss_surrogate_report.json`
  - summary fields on `local_lab_analysis_summary.json`
  - compact propagation into the Local IA Lab monitoring projection/backend/observability surfaces
- current role:
  - estimate which scopes show the highest modeled loss pressure
  - stay research-only and audit-ready
  - never mutate VPS runtime or promotion semantics directly

## 5unvicies. Latest bounded Local IA Lab surrogate-guided prioritization

- the trained Local IA Lab loss surrogate is now consumed by:
  - `src/local_replay_runtime/local_lab_research_priority.py`
  - `src/local_replay_runtime/local_lab_recalibration_plan.py`
- bounded consequences only:
  - influence research ranking for the next replay cycle
  - add a local `replay_surrogate_high_risk_scope` action when justified
  - keep recalibration/publication gates unchanged
- important invariant:
  - the surrogate remains advisory only
  - no promotion authority
  - no runtime/VPS mutation
  - no bypass of proof/recalibration/release gates

## 5duovicies. Latest bounded Local IA Lab replay candidate queue

- `src/local_replay_runtime/local_lab_replay_candidate_queue.py` now exists as the first bounded queue of next local replay/research steps
- the queue is built from:
  - `local_lab_research_priority`
  - `local_lab_recalibration_plan`
  - current surrogate-guided planning truth
- current outputs:
  - `local_lab_replay_candidate_queue.json`
  - summary fields on `local_lab_analysis_summary.json`
  - compact propagation into the Local IA Lab monitoring projection/backend/observability surfaces
- important invariant:
  - local-only
  - descriptive and audit-ready
  - no VPS mutation
  - no promotion semantics by itself

## 5tervicies. Latest bounded Local IA Lab replay ticket index

- `src/local_replay_runtime/local_lab_replay_ticket_index.py` now exists as the governed ticket index over the Local IA Lab replay queue
- it reuses the canonical `LocalReplayRequest` contract instead of inventing a parallel runtime request type
- current outputs:
  - `local_lab_replay_ticket_index.json`
  - summary fields on `local_lab_analysis_summary.json`
  - compact propagation into the Local IA Lab monitoring projection/backend/observability surfaces
- important invariant:
  - tickets are local-only planning artifacts
  - they do not execute anything by themselves
  - they do not mutate VPS/runtime or promotion state

## 5quattuorvicies. Latest bounded Local IA Lab replay dispatch plan

- `src/local_replay_runtime/local_lab_replay_dispatch_plan.py` now exists as the local-only dispatch surface over governed replay tickets
- current outputs:
  - `local_lab_replay_dispatch_plan.json`
  - summary fields on `local_lab_analysis_summary.json`
  - compact propagation into the Local IA Lab monitoring projection/backend/observability surfaces
- important invariant:
  - dispatch stays local-only
  - it does not execute tickets
  - it does not mutate VPS/runtime or promotion state

## 5quinvicies. Latest bounded Local IA Lab replay workflow + monitoring bundle manifests

- `src/local_replay_runtime/local_lab_replay_workflow_manifest.py` now exists as the typed manifest over:
  - `local_lab_replay_candidate_queue.json`
  - `local_lab_replay_ticket_index.json`
  - `local_lab_replay_dispatch_plan.json`
- `src/monitoring/local_lab_replay_workflow_loader.py` now exists as the file-based loader for that workflow bundle
- `src/monitoring/local_lab_monitoring_bundle_manifest.py` now exists as the typed manifest over:
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
  - `local_lab_monitoring_ingestion_summary.json`
  - optional `local_lab_replay_workflow_manifest.json`
- `src/monitoring/local_lab_bundle_loader.py` now discovers monitoring sidecars through the manifest instead of hardcoded filenames
- future-dashboard propagation is now explicit:
  - `local_lab_monitoring_bundle_manifest.json`
  - `local_lab_replay_workflow_manifest.json`
  - compact refs in monitoring projection/backend/summary
- important invariant:
  - local-only discovery surface
  - no UI coupling
  - no VPS/runtime mutation
  - no promotion authority by itself

## 5sexvicies. Latest bounded Local IA Lab monitoring bundle discovery

- `src/monitoring/local_lab_bundle_discovery.py` now exists as the manifest-driven discovery layer for Local IA Lab monitoring bundles
- it can now:
  - scan a root for `local_lab_monitoring_bundle_manifest.json`
  - sort bundles by latest `timestamp_ms`
  - load the newest bundle through the existing loader
- purpose:
  - prepare future backend/Prometheus/dashboard ingestion over multiple Local IA Lab outputs
  - keep discovery manifest-first instead of hardcoded directory knowledge
- important invariant:
  - descriptive only
  - no UI coupling
  - no VPS/runtime mutation
  - no promotion authority

## 5septemvicies. Latest bounded Local IA Lab monitoring feed

- `src/monitoring/local_lab_monitoring_feed.py` now exists as the compact feed over discovered Local IA Lab monitoring bundles
- it now summarizes:
  - latest bundle identity/status
  - ingestion-ready bundle count
  - bundle counts by backend status
- purpose:
  - prepare future backend/dashboard ingestion over multiple Local IA Lab bundles
  - keep the first multi-bundle surface compact and audit-ready
- important invariant:
  - descriptive only
  - no UI coupling
  - no VPS/runtime mutation
  - no promotion authority

## 5octovicies. Latest bounded Local IA Lab calibration-methods core (`13-A`)

- `src/calibration_methods/` now exists as the first shared Local IA Lab math-core package
- bounded modules landed:
  - `bootstrap.py`
  - `walkforward.py`
  - `dsr.py`
- current scope is intentionally local-only and pure:
  - stationary block bootstrap confidence intervals
  - purged walk-forward fold planning with embargo and label purging
  - Deflated Sharpe Ratio computation
- current proofs landed:
  - `tests/test_calibration_methods/test_bootstrap.py`
  - `tests/test_calibration_methods/test_walkforward.py`
  - `tests/test_calibration_methods/test_dsr.py`
- the first live consumer is now real:
  - `src/local_replay_runtime/edge_gate_calibration.py` now consumes the shared stationary bootstrap helper instead of a private i.i.d. resample helper
  - EDGE calibration notes now expose the effective bootstrap block length for auditability
- important invariant:
  - this slice stays Local IA Lab only
  - no VPS/runtime promotion behavior changes
  - walk-forward human approval remains a separate hard gate
  - DSR and walk-forward helpers are available for later consumers but are not silently wired into promotion logic yet

## 5novemvicies. Latest bounded Local IA Lab calibration-methods review sidecar

- `src/local_replay_runtime/local_lab_calibration_methods_review.py` now exists as the first Local IA Lab proof-side consumer of:
  - `src/calibration_methods/walkforward.py`
  - `src/calibration_methods/dsr.py`
- the Local IA Lab bundle now emits:
  - `local_lab_calibration_methods_review.json`
  - summary fields on `local_lab_analysis_summary.json`
  - compact propagation into:
    - `local_lab_monitoring_projection.json`
    - `local_lab_monitoring_backend_payload.json`
    - `local_lab_observability_export.json`
- current semantics are conservative:
  - valid DSR below floor blocks Local IA Lab proof locally
  - insufficient history stays explicit as `partial`, never silent
  - human walk-forward approval remains a separate gate from auto-generated walk-forward geometry
- current proofs landed:
  - `tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py`
  - `tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py`
  - `tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py`
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_scope_matrix.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_local_lab_research_priority.py -q`
  - `25 passed`
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_monitoring/test_monitoring_contracts.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `18 passed`
  - `rtk pytest tests/test_calibration_methods/test_bootstrap.py tests/test_calibration_methods/test_walkforward.py tests/test_calibration_methods/test_dsr.py tests/test_local_replay_runtime/test_edge_gate_calibration.py tests/test_local_replay_runtime/test_walk_forward_review.py tests/test_local_replay_runtime/test_artifact_ablation_study.py tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_scoring_backbone/test_fee_aware_edge_gate.py tests/test_calibration_loader/test_contracts.py tests/test_calibration_loader/test_loader.py -q`
  - `37 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `314 passed`

## 5tricies. Latest bounded Local IA Lab release/dry-run calibration-methods propagation

- `src/local_replay_runtime/artifact_release_candidate.py` now carries explicit calibration-methods state on the Local IA Lab release verdict:
  - `local_lab_calibration_methods_review_path`
  - `calibration_methods_review_status`
  - `calibration_methods_review_ready`
  - `calibration_methods_dsr_pass`
  - `calibration_methods_walk_forward_plan_ready`
- `src/local_replay_runtime/artifact_upload_bridge_candidate.py` now propagates the same truth into:
  - `artifact_release_gate_summary.json`
  - `artifact_import_dry_run_bridge.json`
- purpose:
  - make the dry-run handoff explicitly `calibration-methods-backed` or not
  - keep the handoff audit-ready without changing any VPS/runtime semantics
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py -q`
  - `20 passed`
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_monitoring/test_monitoring_contracts.py -q`
  - `111 passed`

## 5untricies. Latest bounded Local IA Lab monitoring manifest/discovery/feed calibration-methods propagation

- `src/monitoring/local_lab_monitoring_bundle_manifest.py` now carries compact calibration-methods truth from the backend payload
- `src/monitoring/local_lab_bundle_discovery.py` now exposes the same fields per discovered bundle
- `src/monitoring/local_lab_monitoring_feed.py` now summarizes:
  - `calibration_ready_bundle_count`
  - `calibration_partial_bundle_count`
  - `calibration_blocked_bundle_count`
- purpose:
  - keep future multi-bundle backend ingestion manifest-first
  - make calibration-method readiness visible without opening every bundle manually
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_local_lab_monitoring_bundle_manifest.py tests/test_monitoring/test_local_lab_bundle_discovery.py tests/test_monitoring/test_local_lab_monitoring_feed.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py -q`
  - `18 passed`
  - `rtk pytest tests/test_monitoring tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py -q`
  - `203 passed`

## 5duotricies. Latest bounded Local IA Lab tail-risk review (`13-B`)

- `src/calibration_methods/pot_gpd.py` now exists as the bounded Local IA Lab POT-GPD helper:
  - method version stays explicit as `pot_gpd_mom_bootstrap_v1`
  - current scope is bounded to empirical-threshold POT-GPD + bootstrap CI, not a full opaque EVT stack
- `src/local_replay_runtime/local_lab_tail_risk_review.py` now exists as the first strategy-level tail-risk consumer of exported `DTRRecord` history
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_tail_risk_review.json`
- current breaker scope is intentionally top-level and local-only:
  - `THR-R01` over daily net-loss buckets
  - `THR-R02` over weekly net-loss buckets
  - `THR-R03` over monthly net-loss buckets
- current conservative semantics:
  - no positive-loss periods -> `partial`
  - insufficient exceedances -> `partial`
  - invalid fit or excessive bootstrap dispersion -> `blocked`
  - review becomes `ready` only when all three breakers are ready
- compact future-dashboard/backend truth now also propagates into:
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- important invariant:
  - still Local IA Lab only
  - still no UI coupling
  - still no VPS/runtime mutation
  - not yet part of release gating or dry-run import semantics
- latest proofs:
  - `rtk pytest tests/test_calibration_methods/test_pot_gpd.py tests/test_local_replay_runtime/test_local_lab_tail_risk_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py -q`
  - `16 passed`
  - `rtk pytest tests/test_calibration_methods tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_local_lab_tail_risk_review.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py -q`
  - `32 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `317 passed`

## 5tertricies. Latest bounded Local IA Lab stationarity gate (`MI-9` extension over `13-A/13-E`)

- `src/calibration_methods/stationarity.py` now exists as the bounded dual stationarity helper:
  - ADF level test with intercept
  - KPSS level stationarity test with Bartlett/Newey-West long-run variance
  - explicit audit-ready dual verdict `passes_dual_test`
- `src/local_replay_runtime/local_lab_calibration_methods_review.py` now consumes this helper over executed replay returns:
  - `stationarity_status`
  - `stationarity_ready`
  - `stationarity_pass`
  - `stationarity_result`
- new conservative semantics:
  - insufficient history stays explicit as `partial`
  - failing MI-9 blocks the Local IA Lab calibration-methods review
  - proof-side propagation now emits:
    - `LOCAL_LAB_STATIONARITY_REQUIRED`
    - `LOCAL_LAB_STATIONARITY_INVALID`
- the same truth now also propagates into:
  - `local_lab_calibration_normalized_report.json`
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- important invariant:
  - still Local IA Lab only
  - still no UI coupling
  - still no VPS/runtime mutation
  - dry-run/release semantics remain descriptive; this slice only hardens the local proof rail
- latest proofs:
  - `rtk pytest tests/test_calibration_methods/test_stationarity.py tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_local_lab_calibration_normalized_report.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `23 passed`
  - `rtk pytest tests/test_calibration_methods tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_local_lab_tail_risk_review.py tests/test_local_replay_runtime/test_local_lab_calibration_normalized_report.py tests/test_local_replay_runtime/test_edge_gate_calibration.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py -q`
  - `42 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `320 passed`

## 5quatertricies. Latest bounded shared human hard-cap helper (`MI-7` clarification)

- `src/calibration_methods/hard_cap_floor.py` now exists as the shared Local IA Lab hard-bound publication helper:
  - `apply_human_minimum_floor(...)`
  - `apply_human_maximum_cap(...)`
- purpose:
  - stop duplicating ad hoc floor/cap publication logic across EDGE and RISK slices
  - make the semantics explicit:
    - `hard_cap_satisfied` = published value respects the human bound
    - `hard_cap_binding` = the human bound actually clipped/floored the raw candidate
- current consumers:
  - `src/local_replay_runtime/edge_gate_calibration.py`
  - `src/local_replay_runtime/local_lab_tail_risk_review.py`
  - `src/local_replay_runtime/local_lab_calibration_normalized_report.py`
- important invariant:
  - still Local IA Lab only
  - still no UI coupling
  - still no VPS/runtime mutation
  - this slice clarifies audit semantics; it does not open a new promotion authority
- latest proofs:
  - `rtk pytest tests/test_calibration_methods/test_hard_cap_floor.py tests/test_local_replay_runtime/test_edge_gate_calibration.py tests/test_local_replay_runtime/test_local_lab_tail_risk_review.py tests/test_local_replay_runtime/test_local_lab_calibration_normalized_report.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `16 passed`
  - `rtk pytest tests/test_calibration_methods tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_local_lab_tail_risk_review.py tests/test_local_replay_runtime/test_local_lab_calibration_normalized_report.py tests/test_local_replay_runtime/test_edge_gate_calibration.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py -q`
  - `44 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `320 passed`

## 5quinquatracies. Latest bounded Local IA Lab multiple-testing review (`MI-12`)

- `src/calibration_methods/multiple_testing.py` now exists as the bounded shared MI-12 helper
  - current shared method: `holm_bonferroni_v1`
- `src/local_replay_runtime/local_lab_multiple_testing_review.py` now exists as the Local IA Lab MI-12 sidecar
- current conservative truth:
  - current EDGE and tail-risk publications are treated as `interval_publication`, not as simultaneous hypothesis-test promotion
  - therefore the current bounded MI-12 verdict is explicit `not_required_interval_publication`, not a fake corrected p-value pass
  - future hypothesis-test families can still consume the shared Holm-Bonferroni helper
- the same truth now propagates into:
  - `local_lab_calibration_normalized_report.json`
  - `artifact_proof_assessment.json`
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
  - `local_lab_monitoring_bundle_manifest.json`
  - `local_lab_monitoring_feed`
- important invariant:
  - still Local IA Lab only
  - still no UI coupling
  - still no VPS/runtime mutation
  - MI-12 remains honest: no hidden blocker when the current bounded artifact family is interval-publication only
- latest proofs:
  - `rtk pytest tests/test_calibration_methods/test_multiple_testing.py tests/test_local_replay_runtime/test_local_lab_multiple_testing_review.py tests/test_local_replay_runtime/test_local_lab_calibration_normalized_report.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_monitoring/test_local_lab_monitoring_bundle_manifest.py tests/test_monitoring/test_local_lab_bundle_discovery.py tests/test_monitoring/test_local_lab_monitoring_feed.py -q`
  - `22 passed`
  - `rtk pytest tests/test_calibration_methods tests/test_local_replay_runtime tests/test_monitoring tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_meta_learning tests/test_meta_minimal -q`
  - `524 passed`

## 5sextracies. Latest bounded Local IA Lab execution review (`13-C` first slice)

- `src/calibration_methods/execution.py` now exists as the bounded shared EXECUTION helper rail for:
  - `THR-X01` via Hampel-filtered absolute offset quantile + margin + human hard cap
  - `THR-X02` via bounded empirical gap quantile + human hard cap
- `src/local_replay_runtime/local_lab_execution_review.py` now exists as the Local IA Lab EXECUTION sidecar for `THR-X01` / `THR-X02`
- current conservative truth:
  - the review is `partial` when no dedicated execution telemetry sidecar is supplied
  - this slice does not invent replay-derived execution telemetry that the export dir does not actually contain
  - this slice does not alter the current EDGE proof gate or release gate semantics
- `scripts/run_local_lab_analysis_bundle.py` now emits:
  - `local_lab_execution_review.json`
  - summary fields for `execution_review_status / execution_review_ready / execution_*_threshold_count`
  - optional input `--execution-telemetry-path`
- the same truth now propagates into:
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
  - `local_lab_monitoring_bundle_manifest.json`
  - monitoring bundle discovery/feed
- important invariant:
  - still Local IA Lab only
  - still no UI coupling
  - still no VPS/runtime mutation
  - still no fake readiness when telemetry is absent
- latest proofs:
  - `rtk pytest tests/test_calibration_methods/test_execution.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_monitoring/test_local_lab_monitoring_bundle_manifest.py tests/test_monitoring/test_local_lab_bundle_discovery.py tests/test_monitoring/test_local_lab_monitoring_feed.py -q`
  - `23 passed`
  - `rtk pytest tests/test_calibration_methods tests/test_local_replay_runtime tests/test_monitoring tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_meta_learning tests/test_meta_minimal -q`
  - `529 passed`

## 5septentracies. Latest VPS -> local observability architecture anchor

- `16_VPS_LOCAL_OBSERVABILITY_ARCHITECTURE.md` now records the intended observability split:
  - VPS = runtime + lightweight collection + short retention
  - local PC = Prometheus + Grafana + heavy drill-down + long retention
- hard rule now explicit:
  - continuous export = compact typed metrics / summaries
  - on-demand retrieval = detailed logs / deep traces / incident bundles
  - no permanent raw-stream export from VPS to local
- immediate code consequence:
  - next observability coding should start with real VPS process metrics + stable app `.prom` export
  - not with richer UI work
- missing bounded code now explicitly tracked for future slices:
  - process/system metric producer on the real VPS path
  - VPS `.prom` writer on the live service path
  - `telegram_alerter`
  - `disk_monitor`
  - `daily_pnl_breaker`
  - `regime_classifier`
  - `gatekeeper`
  - `info_stress_monitor`
  - `spread_guard`
  - `slippage_model`
- current estimate of overall solution completion is now tracked as `~62%`

## 5octies. VPS process observability slice landed

- real Shadow VPS service-side observability is now wired on the canonical service rail:
  - `scripts/run_shadow_vps_service.py`
  - `src/monitoring/process_metrics.py`
  - `src/monitoring/shadow_vps_service_monitoring.py`
- new governed outputs written by the real service loop:
  - `shadow_vps_service_monitoring_backend_payload.json`
  - `shadow_vps_service_observability_export.json`
  - `shadow_vps_service_observability.prom`
- current scope of the slice:
  - real bounded process sampling without extra dependency install
  - real bounded disk usage sampling on the service volume
  - typed future-dashboard/backend payload for the Shadow VPS service
  - canonical `.prom` text export from real service state
- explicit residuals after this slice:
  - no `node_exporter` hookup yet
  - no bounded log retrieval path yet
  - execution telemetry for `13-C EXECUTION` is still missing on the VPS side
- latest proofs:
  - `python -m pytest tests/test_monitoring/test_process_metrics.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `9 passed`
  - `python -m pytest tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_disk_monitor.py tests/test_monitoring/test_process_metrics.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `19 passed`

## 5novies. VPS bounded log retrieval slice landed

- real Shadow VPS durable event retrieval is now coded on the monitoring rail:
  - `src/monitoring/shadow_vps_service_log_retrieval.py`
  - `src/monitoring/contracts.py`
  - `src/monitoring/__init__.py`
  - `scripts/run_shadow_vps_service.py`
- new typed retrieval surfaces now exist:
  - `ShadowVpsServiceLogQuery`
  - `ShadowVpsServiceLogQueryResult`
  - `ShadowVpsServiceLogEventProjection`
- current scope of the slice:
  - bounded full-scan query over the durable `shadow_vps_service.events.jsonl`
  - bounded recent-tail summary for the real service path
  - no new raw streaming bus
  - no UI coupling
- new governed output written by the real service loop:
  - `shadow_vps_service_recent_events.json`
- preserve the doctrine:
  - VPS keeps only compact recent-summary materialized continuously
  - deeper log drill-down stays on-demand
  - typed/audit-ready retrieval replaces manual raw JSONL parsing in the monitored seam
- explicit residuals after this slice:
  - no `node_exporter` hookup yet
  - no local Prometheus/Grafana scrape hookup yet
  - no compressed incident-bundle retrieval path yet
  - execution telemetry for `13-C EXECUTION` is still missing on the VPS side
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_shadow_vps_service_log_retrieval.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `11 passed`
  - `rtk pytest tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_disk_monitor.py tests/test_monitoring/test_process_metrics.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_monitoring/test_shadow_vps_service_log_retrieval.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `22 passed`

## 5decies. VPS node_exporter textfile collector hookup landed

- the real Shadow VPS service can now mirror its compact `.prom` export into a node_exporter textfile collector directory:
  - `src/monitoring/observability_io.py`
  - `src/monitoring/contracts.py`
  - `src/monitoring/shadow_vps_service_monitoring.py`
  - `scripts/run_shadow_vps_service.py`
- current scope of the slice:
  - optional service arg `--node-exporter-textfile-dir`
  - writes `v53_shadow_vps_service.prom` into the configured collector directory
  - preserves the canonical compact `ObservabilityExport` text payload; no second metrics format was introduced
- preserve the doctrine:
  - the VPS still only writes compact typed metrics
  - deployment of `node_exporter` and local Prometheus scraping remains a separate ops step
  - no UI coupling
- explicit residuals after this slice:
  - no actual `node_exporter` deployment in repo
  - no local Prometheus/Grafana scrape hookup yet
  - no compressed incident-bundle retrieval path yet
  - execution telemetry for `13-C EXECUTION` is still missing on the VPS side
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_observability_io.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `10 passed`
  - `rtk pytest tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_observability_io.py tests/test_monitoring/test_disk_monitor.py tests/test_monitoring/test_process_metrics.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_monitoring/test_shadow_vps_service_log_retrieval.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `24 passed`

## 5undecies. Local Prometheus scrape bundle hookup landed

- the VPS/local observability rail now has a typed handoff and a local-PC aggregator:
  - per-VPS handoff on the real service rail:
    - `src/monitoring/shadow_vps_service_scrape_manifest.py`
    - `scripts/run_shadow_vps_service.py`
  - local-PC aggregation:
    - `src/monitoring/shadow_vps_scrape_discovery.py`
    - `scripts/run_local_prometheus_scrape_bundle.py`
- new current artifacts:
  - per-VPS:
    - `shadow_vps_service_scrape_manifest.json`
    - `shadow_vps_service_prometheus_file_sd.json`
  - local-PC aggregate:
    - `shadow_vps_scrape_discovery.json`
    - `shadow_vps_prometheus_file_sd.json`
- current scope of the slice:
  - explicit `--scrape-host` / `--vps-id` handoff on the service rail
  - optional Prometheus `file_sd` sidecar per VPS
  - local discovery and de-duplication by latest target
  - one aggregated local Prometheus `file_sd` bundle
- preserve the doctrine:
  - the VPS still exports only compact typed artifacts
  - local PC owns the aggregation and future Prometheus/Grafana consumption
  - no UI coupling
- explicit residuals after this slice:
  - no actual `node_exporter` deployment in repo
  - no checked-in local Prometheus config yet
  - no Grafana dashboards yet
  - no compressed incident-bundle retrieval path yet
  - execution telemetry for `13-C EXECUTION` is still missing on the VPS side
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_shadow_vps_service_scrape_manifest.py tests/test_monitoring/test_shadow_vps_scrape_discovery.py tests/test_monitoring/test_local_prometheus_scrape_bundle_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `11 passed`
  - `rtk pytest tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_observability_io.py tests/test_monitoring/test_disk_monitor.py tests/test_monitoring/test_process_metrics.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_monitoring/test_shadow_vps_service_log_retrieval.py tests/test_monitoring/test_shadow_vps_service_scrape_manifest.py tests/test_monitoring/test_shadow_vps_scrape_discovery.py tests/test_monitoring/test_local_prometheus_scrape_bundle_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `29 passed`

## 5duodecies. Checked local Prometheus config generator landed

- the local-PC side now has a checked config generator above the aggregated file_sd bundle:
  - `src/monitoring/local_prometheus_config.py`
  - `scripts/run_local_prometheus_config.py`
- new current artifacts:
  - `prometheus.local.generated.yml`
  - `prometheus.local.config.summary.json`
- current scope of the slice:
  - consumes `shadow_vps_prometheus_file_sd.json`
  - generates a minimal checked local Prometheus config
  - optional local node_exporter target included by config generation for Unix-like hosts
  - optional local windows_exporter target included by config generation for Windows local PCs
- preserve the doctrine:
  - still no heavy UI coupling
  - still no direct mutation of VPS runtime
  - checked config generation stays local-PC side
- explicit residuals after this slice:
  - no actual Prometheus process launch/orchestration in repo
  - no Grafana dashboards yet
  - no compressed incident-bundle retrieval path yet
  - execution telemetry for `13-C EXECUTION` is still missing on the VPS side
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_local_prometheus_config.py tests/test_monitoring/test_local_prometheus_config_launcher.py tests/test_monitoring/test_shadow_vps_service_scrape_manifest.py tests/test_monitoring/test_shadow_vps_scrape_discovery.py tests/test_monitoring/test_local_prometheus_scrape_bundle_launcher.py -q`
  - `8 passed`
  - `rtk pytest tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_observability_io.py tests/test_monitoring/test_disk_monitor.py tests/test_monitoring/test_process_metrics.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_monitoring/test_shadow_vps_service_log_retrieval.py tests/test_monitoring/test_shadow_vps_service_scrape_manifest.py tests/test_monitoring/test_shadow_vps_scrape_discovery.py tests/test_monitoring/test_local_prometheus_scrape_bundle_launcher.py tests/test_monitoring/test_local_prometheus_config.py tests/test_monitoring/test_local_prometheus_config_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `32 passed`

## 5terdecies. Windows local Prometheus exporter support landed

- the checked local Prometheus config generator now supports both local-PC exporter families explicitly:
  - `src/monitoring/local_prometheus_config.py`
  - `scripts/run_local_prometheus_config.py`
- current scope of the slice:
  - `--local-node-exporter-target` remains available for Unix-like local hosts
  - `--local-windows-exporter-target` is now available for Windows local PCs
  - default config generation no longer assumes a local exporter when none was requested
- preserve the doctrine:
  - no Unix-only exporter assumption on Windows
  - generated config stays typed and local-only
  - no direct mutation of VPS runtime
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_local_prometheus_config.py tests/test_monitoring/test_local_prometheus_config_launcher.py -q`
  - `6 passed`

## 5quaterdecies. Dual-role dev local Prometheus HTTP bridge landed

- the local-PC dev path now has a bounded HTTP bridge for the current `.prom` payload when no real local exporter exists:
  - `src/monitoring/local_prometheus_metrics_bridge.py`
  - `scripts/run_local_prometheus_metrics_bridge.py`
- current scope of the slice:
  - serves the current V5.3 `.prom` payload over `/metrics`
  - exposes `/-/ready`
  - writes `local_prometheus_metrics_bridge.summary.json`
  - preserves the real VPS scrape model; this bridge is dev-only for dual-role local runs
- preserve the doctrine:
  - no manual Prometheus YAML editing
  - no change to the real VPS `node_exporter` assumption
  - no UI coupling
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_local_prometheus_metrics_bridge.py tests/test_monitoring/test_local_prometheus_metrics_bridge_launcher.py tests/test_monitoring/test_local_prometheus_config.py tests/test_monitoring/test_local_prometheus_config_launcher.py -q`
  - `8 passed`

## 5quindecies. Local Grafana dashboard bundle and bootstrap landed

- the local dev observability rail now has an importable Grafana dashboard bundle and a local API bootstrap:
  - `src/monitoring/local_grafana_dashboard.py`
  - `scripts/run_local_grafana_dashboard.py`
  - `src/monitoring/local_grafana_api.py`
  - `scripts/run_local_grafana_bootstrap.py`
- current scope of the slice:
  - builds an importable dashboard JSON over the currently observed `v53_shadow_vps_*` metrics
  - writes a typed dashboard summary with observed metric inventory
  - can create the local Prometheus datasource in Grafana and import the dashboard through the local Grafana HTTP API
- preserve the doctrine:
  - dashboard queries are constrained to current metric reality
  - no runtime mutation
  - no deviation from the real VPS handoff model
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_local_grafana_dashboard.py tests/test_monitoring/test_local_grafana_dashboard_launcher.py tests/test_monitoring/test_local_grafana_api.py tests/test_monitoring/test_local_grafana_bootstrap_launcher.py tests/test_monitoring/test_local_prometheus_metrics_bridge.py tests/test_monitoring/test_local_prometheus_metrics_bridge_launcher.py tests/test_monitoring/test_local_prometheus_config.py tests/test_monitoring/test_local_prometheus_config_launcher.py -q`
  - `13 passed`

## 5sexdecies. Local IA Lab Grafana rail landed on the dual-role dev path

- the local observability rail now covers both the Shadow VPS bridge and the Local IA Lab bridge:
  - `src/monitoring/local_lab_grafana_dashboard.py`
  - `scripts/run_local_lab_grafana_dashboard.py`
  - `src/monitoring/local_prometheus_metrics_bridge.py`
  - `scripts/run_local_prometheus_metrics_bridge.py`
  - `src/monitoring/local_prometheus_config.py`
  - `scripts/run_local_prometheus_config.py`
- current scope of the slice:
  - the dev-only metrics bridge can now serve either a raw `.prom` file or an observability export JSON carrying `text_payload`
  - the local Prometheus config can now add a dedicated `v53_local_lab` scrape job via `--local-lab-target`
  - an importable Local IA Lab Grafana dashboard is now generated from the real observed `v53_local_lab_*` metric surface
  - the generated Local IA Lab dashboard is detailed but still constrained to current metric reality, not imagined future panels
- current dev artifacts:
  - `build/dev_dual_role_demo/local_lab_grafana_dashboard/v53_local_lab_grafana.dashboard.json`
  - `build/dev_dual_role_demo/local_lab_grafana_dashboard/v53_local_lab_grafana.summary.json`
  - `build/dev_dual_role_demo/local_prometheus_config_with_lab/prometheus.local.generated.yml`
  - `build/dev_dual_role_demo/local_prometheus_config_with_lab/prometheus.local.config.summary.json`
- preserve the doctrine:
  - no new runtime profile
  - no VPS runtime mutation
  - no heavy UI coupling on the VPS side
  - Local IA Lab remains local-only, surfaced through typed sidecars and compact metrics
- latest proofs:
  - `python -m pytest tests/test_monitoring/test_local_prometheus_metrics_bridge.py tests/test_monitoring/test_local_prometheus_metrics_bridge_launcher.py tests/test_monitoring/test_local_prometheus_config.py tests/test_monitoring/test_local_prometheus_config_launcher.py tests/test_monitoring/test_local_lab_grafana_dashboard.py tests/test_monitoring/test_local_lab_grafana_dashboard_launcher.py -q`
  - `19 passed`

## 5septdecies. `13-C EXECUTION` now has a real service-owned telemetry producer

- new code:
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py`
  - `scripts/run_shadow_vps_service.py`
  - `scripts/run_local_lab_analysis_bundle.py`
- current slice truth:
  - the Shadow VPS service now writes a durable cumulative archive:
    - `shadow_vps_service_execution_telemetry.archive.json`
  - and a current service-owned handoff sidecar:
    - `shadow_vps_service_execution_telemetry.json`
  - the service sidecar is bindable by the Local IA Lab bundle without pre-baking a review `correlation_id`
  - `THR-X02` is now derived from real websocket timing sources already emitted by the service:
    - injected websocket stream -> inter-arrival series
    - native live capture snapshot batch -> accepted-event inter-arrival series
  - `THR-X01` stays explicit and optional through `--execution-time-sync-offsets-path`
  - the service state and monitoring payload now expose `last_execution_telemetry_ref` / `execution_telemetry_ref`
- preserve the doctrine:
  - no fake readiness
  - cumulative by `session_date`, not ad hoc per-run overwrite
  - service-owned artifact stays typed and audit-ready
  - Local IA Lab remains the consumer; the VPS service only collects and hands off
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `20 passed`

## 5octodecies. `13-C EXECUTION` now auto-harvests `THR-X01` from native live capture when available

- new code:
  - `src/protocols/shadow_live_websocket.py`
  - `src/protocols/shadow_vps_service.py`
  - `scripts/run_shadow_vps_service.py`
- current slice truth:
  - native live capture can now write a bounded passive sidecar:
    - `live_time_sync_offsets.json`
  - the sidecar is produced only when `time_sync_probe_enabled=true` on `ShadowLiveWebSocketConfig`
  - the Shadow VPS service now falls back to that service-owned sidecar for `THR-X01` when `--execution-time-sync-offsets-path` is not supplied
  - the ref is propagated through:
    - `ShadowLiveWebSocketCaptureResult`
    - `ShadowVpsServiceState.last_live_capture_time_sync_offsets_ref`
    - `ShadowVpsRuntimeEvidenceBundle.live_capture_time_sync_offsets_ref`
    - `ShadowVpsCampaignSummary.live_capture_time_sync_offsets_ref`
- preserve the doctrine:
  - passive only, no execution mutation
  - bounded probe, not an always-on heavy runtime loop
  - if the probe fails, live capture stays up and the sidecar remains honestly absent with explicit error text
- latest proofs:
  - `python -m pytest tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `26 passed`

## 5novemdecies. `13-C EXECUTION` now harvests service-owned `THR-X04/X05` samples and exposes a shared `THR-X04` calibrator

- new code:
  - `src/calibration_methods/execution.py`
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py`
  - `src/local_replay_runtime/local_lab_execution_review.py`
- current slice truth:
  - the service-owned execution telemetry artifact now carries:
    - `spread_bps`
    - `spread_observation_days`
    - `spread_session_dates`
    - `spread_source_refs`
    - `slippage_bps`
    - `slippage_observation_days`
    - `slippage_session_dates`
    - `slippage_source_refs`
  - those samples are harvested from existing service-owned market evidence:
    - snapshot/depth spreads from injected websocket streams or native snapshot batches
    - slippage samples from route hints when present
  - `src/calibration_methods/execution.py` now exposes `calibrate_spread_guard_threshold_bps(...)` for `THR-X04`
  - the global execution review contract is extended to carry the new sample families, but the review gating logic remains intentionally focused on `THR-X01/X02` on this slice
- preserve the doctrine:
  - no fake `THR-X05` model claim yet
  - no `THR-X03` green verdict without true REST/quota telemetry
  - service-owned evidence first, review consumption later
- latest proofs:
  - `python -m pytest tests/test_calibration_methods/test_execution.py tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `30 passed`

## 20. `13-C EXECUTION` now makes `THR-X04` a real Local IA Lab review threshold

- new code:
  - `src/local_replay_runtime/local_lab_execution_review.py`
  - `src/calibration_methods/__init__.py`
- current slice truth:
  - `THR-X04` is now consumed by the Local IA Lab execution review with explicit doctrine:
    - requires `spread_bps`
    - requires `spread_observation_days >= 30`
    - calibrates via `calibrate_spread_guard_threshold_bps(...)`
    - keeps the human hard cap at `50 bps`
  - the review now covers:
    - `THR-X01`
    - `THR-X02`
    - `THR-X04`
  - bundle summaries now expose the updated execution threshold counts automatically
- preserve the doctrine:
  - `THR-X03` still has no green verdict without real service quota telemetry
  - `THR-X05` still has no green verdict without a real slippage model
  - no fake readiness was added for either missing threshold family
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_calibration_methods/test_execution.py -q`
  - `17 passed`
  - `python -m pytest tests/test_calibration_methods/test_execution.py tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `31 passed`

## 21. `13-C EXECUTION` now exposes explicit `THR-X03/X05` review gaps instead of silently omitting them

- new code:
  - `src/local_replay_runtime/local_lab_execution_review.py`
- current slice truth:
  - the Local IA Lab execution review now enumerates the full bounded execution threshold set:
    - `THR-X01`
    - `THR-X02`
    - `THR-X03`
    - `THR-X04`
    - `THR-X05`
  - current honest review status is now:
    - `THR-X01` ready when bounded time-sync evidence exists
    - `THR-X02` ready when bounded websocket evidence exists
    - `THR-X04` ready when bounded spread evidence exists
    - `THR-X03` partial with `THR-X03_SERVICE_RATE_LIMIT_TELEMETRY_MISSING`
    - `THR-X05` partial with either missing telemetry or `THR-X05_MODEL_NOT_IMPLEMENTED`
  - bundle summaries now surface:
    - `execution_ready_threshold_count = 3`
    - `execution_partial_threshold_count = 2`
    - `execution_review_status = partial`
- preserve the doctrine:
  - no fake green verdict for `X03`
  - no fake green verdict for `X05`
  - release/shadow gates were not weakened or bypassed
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_calibration_methods/test_execution.py -q`
  - `17 passed`
  - `python -m pytest tests/test_calibration_methods/test_execution.py tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `31 passed`

## 22. `13-C EXECUTION` now carries service-owned size traces for the future `THR-X05` model

- new code:
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py`
  - `src/local_replay_runtime/local_lab_execution_review.py`
- current slice truth:
  - the service-owned execution telemetry artifact now also carries:
    - `candidate_sizes`
    - `candidate_size_observation_days`
    - `candidate_size_session_dates`
    - `candidate_size_source_refs`
    - `final_sizes`
    - `final_size_observation_days`
    - `final_size_session_dates`
    - `final_size_source_refs`
  - those traces are harvested directly from route hints already present in injected/live evidence
  - the review contract can now receive these future `X05` inputs without claiming a model exists
- preserve the doctrine:
  - no fake `THR-X05` model was introduced
  - this slice is evidence preparation only
  - release/shadow gates stay unchanged
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_calibration_methods/test_execution.py -q`
  - `17 passed`
  - `python -m pytest tests/test_calibration_methods/test_execution.py tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `31 passed`

## 23. `13-C EXECUTION` now persists service-owned `THR-X03` quota probe telemetry end-to-end

- new code:
  - `src/protocols/shadow_live_websocket.py`
  - `src/protocols/shadow_vps_service.py`
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py`
  - `src/local_replay_runtime/local_lab_execution_review.py`
- current slice truth:
  - the native live time-sync sidecar now also carries bounded quota probe metadata:
    - `rest_call_count`
    - `probe_duration_s`
    - `rest_quota_max_calls_per_minute`
    - `observed_calls_per_minute`
  - the service-owned execution telemetry artifact now preserves that metadata as:
    - `quota_call_counts`
    - `quota_probe_durations_s`
    - `quota_limit_calls_per_minute_values`
    - `quota_calls_per_minute_observed`
    - `quota_observation_days`
    - `quota_source_refs`
  - the Local IA Lab execution review now distinguishes:
    - telemetry missing -> `THR-X03_SERVICE_RATE_LIMIT_TELEMETRY_MISSING`
    - telemetry present but quota cap missing -> `THR-X03_SERVICE_RATE_LIMIT_CAP_MISSING`
    - telemetry present but `< 30d` -> `THR-X03_EXECUTION_HISTORY_LT_30D`
    - telemetry present and history sufficient -> still `partial` with `THR-X03_MODEL_NOT_IMPLEMENTED`
- preserve the doctrine:
  - no fake `THR-X03` green verdict was introduced
  - this slice adds evidence plumbing and honest review semantics only
  - release/shadow/live gates remain unchanged
- latest proofs:
  - `python -m pytest tests/test_protocols/test_shadow_live_websocket.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `20 passed`
  - `python -m pytest tests/test_calibration_methods/test_execution.py tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `32 passed`

## 24. `13-C EXECUTION` now has first bounded models for `THR-X03` and `THR-X05`

- new code:
  - `src/calibration_methods/execution.py`
  - `src/calibration_methods/__init__.py`
  - `src/local_replay_runtime/local_lab_execution_review.py`
- current slice truth:
  - `THR-X03` now calibrates a real throttle ratio from service-owned quota telemetry:
    - observed REST calls/minute
    - official quota cap
    - Little's-law-style burst margin
    - human hard cap at `0.80`
  - `THR-X05` now calibrates a first bounded slippage model from service-owned size/slippage evidence:
    - robust Huber linear fit on `sqrt(size)`
    - size proxy chosen from `final_size` first, else `candidate_size`
    - validation floor `R² >= 0.30`
    - reference prediction published at the `q95` observed size
  - on aligned 30d service-owned evidence, the Local IA Lab execution review can now become fully `ready`
- preserve the doctrine:
  - no live-runtime mutation was introduced
  - no opaque ML or hidden fallback was introduced
  - `THR-X05` is still a first bounded model, not the final execution backbone implementation
- latest proofs:
  - `python -m pytest tests/test_calibration_methods/test_execution.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py -q`
  - `21 passed`
  - `python -m pytest tests/test_calibration_methods/test_execution.py tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `35 passed`

## 25. `13-C EXECUTION` now projects `THR-X03/X05` into future runtime consumer contracts

- new code:
  - `src/local_replay_runtime/local_lab_execution_runtime_projection.py`
  - `src/local_replay_runtime/artifact_proof_summary_builder.py`
  - `src/local_replay_runtime/artifact_release_candidate.py`
  - `scripts/run_local_lab_analysis_bundle.py`
- current slice truth:
  - the Local IA Lab bundle now emits `local_lab_execution_runtime_projection.json`
  - the projection is typed and bounded for two future consumers only:
    - `rate_limiter` from `THR-X03`
    - `slippage_model` from `THR-X05`
  - proof assessment and release candidate now carry this projection as descriptive handoff evidence
  - no new runtime module was created and no Shadow/Micro-live/Live gate was bypassed
- preserve the doctrine:
  - projection is descriptive only
  - it does not mutate live runtime behavior
  - it does not become a new release blocker on this slice
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_execution_runtime_projection.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `18 passed`
  - `python -m pytest tests/test_calibration_methods/test_execution.py tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_execution_runtime_projection.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `46 passed`

## 26. `13-C EXECUTION` now has first canonical runtime consumers for `THR-X03/X05`

- new runtime truth:
  - `src/execution_backbone/rate_limiter.py` now defines the bounded canonical consumer for `THR-X03`
  - `src/execution_backbone/slippage_model.py` now defines the bounded canonical consumer for `THR-X05`
  - `src/execution_backbone/execution_runtime.py` can now consume those models only when they are injected explicitly
- current slice behavior:
  - `THR-X05` augments `expected_cost` conservatively before order selection and carries audit metadata into the submitted intent
  - `THR-X03` can veto submission when live metadata already exposes `rest_quota_ratio_current`
  - if the models are absent, or if `THR-X03` telemetry is absent/invalid, the runtime stays fail-open and unchanged
- preserve the doctrine:
  - no bootstrap auto-wiring yet
  - no live/runtime mutation unless a caller injects the models explicitly
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `python -m pytest tests/test_execution_backbone/test_rate_limiter.py tests/test_execution_backbone/test_slippage_model.py tests/test_execution_backbone/test_execution_runtime.py -q`
  - `30 passed`
  - `python -m pytest tests/test_execution_backbone/test_execution_integration.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `17 passed`

## 27. `13-C EXECUTION` runtime consumers now have an explicit bootstrap bridge

- new bridge truth:
  - `src/protocols/execution_runtime_projection_bridge.py` now loads `local_lab_execution_runtime_projection.json` fail-open
  - `src/protocols/execution_runtime_bootstrap.py` now accepts `execution_runtime_projection_path`
  - `build_execution_runtime(...)` and `build_binance_execution_runtime(...)` can now recover:
    - `rate_limit_model` from `THR-X03`
    - `slippage_model` from `THR-X05`
- preserve the doctrine:
  - activation stays explicit; default behavior remains unchanged when no projection path is provided
  - missing / partial / invalid projection artifacts still fail open
  - no gate bypass and no hidden live mutation
- latest proofs:
  - `python -m pytest tests/test_protocols/test_execution_runtime_projection_bridge.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_execution_runtime.py -q`
  - `36 passed`
  - `python -m pytest tests/test_execution_backbone/test_rate_limiter.py tests/test_execution_backbone/test_slippage_model.py tests/test_execution_backbone/test_execution_integration.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `14 passed`

## 28. `13-C EXECUTION` runtime projection bridge is now visible in Build-10 monitoring

- new bridge truth:
  - `src/protocols/execution_runtime_dashboard.py` now projects the bounded `execution_runtime_projection_path` seam into typed monitoring truth
  - `src/monitoring/contracts.py`, `src/monitoring/technical_dashboard_backend.py`, `src/ui/technical_dashboard_view.py`, and `src/monitoring/observability.py` now expose that seam separately from the older compiled `execution_no_trade_bridge`
- preserve the doctrine:
  - no hidden runtime activation
  - no replacement of the existing no-trade bridge
  - the new surface is descriptive only and reports whether `THR-X03/X05` consumers are loadable
- latest proofs:
  - `rtk pytest tests/test_protocols/test_execution_runtime_dashboard.py tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_observability.py tests/test_ui/test_technical_dashboard.py -q`
  - `91 passed`
  - `python -m pytest tests/test_protocols/test_execution_runtime_projection_bridge.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_execution_runtime.py -q`
  - `36 passed`

## 29. `13-C EXECUTION` technical dashboard launcher now auto-discovers the runtime projection bridge

- new launcher truth:
  - `scripts/run_technical_dashboard.py` now auto-loads `local_lab_execution_runtime_projection.json` from the demo output directory when present
  - the launcher can also accept an explicit `--execution-runtime-projection-path`
  - demo payloads now surface the bounded `THR-X03/X05` consumer bridge without test-only manual injection
- preserve the doctrine:
  - demo/operator surface only
  - no runtime activation
  - no Shadow/Micro-live/Live bypass
- latest proofs:
  - `rtk pytest tests/test_ui/test_technical_dashboard_launcher.py tests/test_ui/test_technical_dashboard.py tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_observability.py tests/test_protocols/test_execution_runtime_dashboard.py -q`
  - `90 passed`
  - `python -m pytest tests/test_monitoring/test_monitoring_runtime.py tests/test_protocols/test_execution_runtime_projection_bridge.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_execution_runtime.py -q`
  - `46 passed`

## 30. `13-C EXECUTION` local replay shadow runner now surfaces the runtime projection bridge

- new runner truth:
  - `scripts/run_local_replay_shadow.py` now accepts an explicit `--execution-runtime-projection-path`
  - the same runner now auto-discovers `local_lab_execution_runtime_projection.json` from its output directory when present
  - baseline and candidate technical payloads now surface the bounded `THR-X03/X05` runtime projection bridge through the existing Build-10 dashboard contract
- preserve the doctrine:
  - runner/operator surface only
  - no hidden runtime activation
  - no replacement of Shadow gating or execution bootstrap
- latest proofs:
  - `python -m pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_protocols/test_execution_runtime_dashboard.py tests/test_monitoring/test_monitoring_backend.py tests/test_ui/test_technical_dashboard.py -q`
  - `95 passed`
  - `python -m pytest tests/test_protocols/test_execution_runtime_projection_bridge.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_execution_runtime.py -q`
  - `36 passed`

## 31. `13-C EXECUTION` Shadow orchestrator and VPS service now persist the runtime projection seam

- new service truth:
  - `scripts/run_shadow_daily_orchestrator.py` now accepts `--execution-runtime-projection-path` and persists the projection ref plus readiness counts in `shadow_daily_orchestrator.last_run.json`
  - `scripts/run_shadow_vps_service.py` now forwards that path, persists `last_execution_runtime_projection_ref`, and carries the same seam into the runtime evidence bundle and campaign summary
  - `src/monitoring/shadow_vps_service_monitoring.py` and `src/monitoring/contracts.py` now expose this seam in the Shadow VPS monitoring payload and observability export
- preserve the doctrine:
  - descriptive persistence only
  - no hidden runtime activation
  - no Shadow/Micro-live/Live bypass
- latest proofs:
  - `python -m pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `24 passed`
  - `python -m pytest tests/test_protocols/test_execution_runtime_projection_bridge.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_execution_runtime.py tests/test_protocols/test_execution_runtime_dashboard.py tests/test_monitoring/test_monitoring_backend.py tests/test_ui/test_technical_dashboard.py -q`
  - `108 passed`

## 32. `13-C EXECUTION` Micro-live and Live-Light now carry the runtime projection seam through canonical contracts

- new protocol truth:
  - `src/protocols/contracts.py` now carries `execution_runtime_projection_*` fields in `MicroLiveInput`, `MicroLiveRunSummary`, `LiveLightInput`, and `LiveLightRunSummary`
  - `src/protocols/micro_live_runtime.py` now derives the seam from the governed `execution_runtime_projection_bridge` already present in the Shadow technical payload
  - `src/protocols/live_light_runtime.py` now propagates the same seam from governed Micro-live summaries into governed Live-Light inputs and summaries
  - `src/protocols/micro_live_dashboard.py`, `src/protocols/live_light_dashboard.py`, and `src/monitoring/contracts.py` now keep the normalized monitoring projections aligned with the canonical protocol chain
- preserve the doctrine:
  - descriptive seam propagation only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `python -m pytest tests/test_protocols/test_micro_live_runtime.py tests/test_protocols/test_live_light_runtime.py tests/test_protocols/test_micro_live_dashboard.py tests/test_protocols/test_live_light_dashboard.py -q`
  - `82 passed`
  - `python -m pytest tests/test_ui/test_technical_dashboard.py tests/test_monitoring/test_monitoring_backend.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `88 passed`

## 33. `13-C EXECUTION` Micro-live and Live dashboard cards now expose the runtime projection seam

- new operator truth:
  - `src/protocols/micro_live_dashboard.py` now exposes `exec_proj` status plus ready/partial/blocked consumer counts inside the Build-12 guardrails card detail
  - `src/protocols/live_light_dashboard.py` now exposes the same bounded seam inside the Build-13 readiness card detail
  - this makes the later-stage gate chain operator-visible without inventing a new card or changing gate semantics
- preserve the doctrine:
  - operator visibility only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `python -m pytest tests/test_protocols/test_micro_live_dashboard.py tests/test_protocols/test_live_light_dashboard.py tests/test_ui/test_technical_dashboard.py -q`
  - `33 passed`
  - `python -m pytest tests/test_protocols/test_micro_live_runtime.py tests/test_protocols/test_live_light_runtime.py -q`
  - `76 passed`

## 34. `13-C EXECUTION` Shadow live startup config can now carry the runtime projection seam

- new startup/config truth:
  - `src/protocols/shadow_vps_service.py` now lets `ShadowLiveWebSocketConfig` carry `execution_runtime_projection_path_ref`
  - `scripts/run_shadow_vps_service.py` now resolves that config-owned path at startup when the explicit CLI path is absent
  - explicit `--execution-runtime-projection-path` still wins over config and the seam remains descriptive only
- preserve the doctrine:
  - startup/config propagation only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `python -m pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_protocols/test_shadow_live_websocket.py -q`
  - `12 passed`
  - `python -m pytest tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
  - `18 passed`

## 35. `13-C EXECUTION` Shadow service now preserves runtime projection provenance

- new audit truth:
  - the Shadow service now persists `execution_runtime_projection_source` across state, runtime evidence bundle, campaign summary, and monitoring payloads
  - current governed values are `cli`, `live_websocket_config`, or `not_configured`
  - the existing `v53_shadow_vps_execution_runtime_projection_ready` metric now carries `projection_source` as a label
- preserve the doctrine:
  - provenance only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `python -m pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `8 passed`
  - `python -m pytest tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
  - `22 passed`

## 36. `13-C EXECUTION` Shadow local Grafana now renders the runtime projection seam

- new operator truth:
  - `src/monitoring/local_grafana_dashboard.py` now adds dedicated Shadow Grafana panels for `execution_runtime_projection_ready`, ready/partial/blocked consumer counts, and an instant label view exposing `projection_status` and `projection_source`
  - `scripts/run_local_grafana_dashboard.py` now generates a 12-panel Shadow dashboard bundle that can render the seam directly in Grafana, not only in the technical dashboard or raw Prometheus metrics
- preserve the doctrine:
  - observability only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `python -m pytest tests/test_monitoring/test_local_grafana_dashboard.py::test_build_local_shadow_vps_grafana_dashboard_contains_expected_queries tests/test_monitoring/test_local_grafana_dashboard_launcher.py::test_local_grafana_dashboard_launcher_writes_dashboard_and_summary -q`
  - `2 passed`

## 37. `13-C EXECUTION` Shadow service now keeps runtime projection observability on late telemetry failure

- new service truth:
  - `scripts/run_shadow_vps_service.py` now persists the written runtime evidence bundle ref plus the `execution_runtime_projection` seam into service state before attempting the durable execution telemetry sidecar write
  - if the later telemetry sidecar write fails, Build-10 monitoring and Prometheus still expose the already-produced runtime projection seam from the runtime evidence bundle instead of regressing to `not_configured`
- preserve the doctrine:
  - observability/persistence hardening only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `python -m pytest tests/test_protocols/test_shadow_vps_service_launcher.py::test_shadow_vps_service_preserves_execution_runtime_projection_when_telemetry_write_fails tests/test_protocols/test_shadow_vps_service_launcher.py::test_shadow_vps_service_captures_native_live_websocket_then_runs_shadow tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `4 passed`

## 38. `13-C EXECUTION` Shadow demo runs no longer degrade when telemetry sidecar has no governed export

- new service truth:
  - `scripts/run_shadow_vps_service.py` now recovers `last_run.export_dir_ref` from `auto_export_dir` when a governed auto-export exists but the orchestrator payload omitted the ref
  - true demo/replay runs with no governed export no longer degrade the whole Shadow service just because the Local IA Lab execution telemetry sidecar cannot be materialized
  - the service now emits `execution_telemetry_skipped` explicitly for that case, keeps `last_execution_telemetry_ref=""`, and still completes the governed Shadow day
- preserve the doctrine:
  - honest skip semantics only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `rtk pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `10 passed`
  - `rtk pytest tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
  - `16 passed`

## 39. `13-C EXECUTION` Shadow telemetry write/skip status is now observable in Build-10 and local Grafana

- new monitoring truth:
  - `src/protocols/shadow_vps_service.py` now persists `last_execution_telemetry_status`
  - `scripts/run_shadow_vps_service.py` now writes governed values `written`, `skipped`, and `failed` on the Shadow service state/campaign path
  - `src/monitoring/shadow_vps_service_monitoring.py` now projects `execution_telemetry_status` into the Build-10 payload detail string and emits bounded Prometheus metric `v53_shadow_vps_execution_telemetry_ready{telemetry_status=...}`
  - `src/monitoring/local_grafana_dashboard.py` now renders dedicated `Execution Telemetry Ready` and `Execution Telemetry Labels` panels in the local Shadow Grafana bundle
- preserve the doctrine:
  - observability only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `rtk pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `10 passed`
  - `python -m pytest tests/test_monitoring/test_local_grafana_dashboard.py::test_build_local_shadow_vps_grafana_dashboard_contains_expected_queries tests/test_monitoring/test_local_grafana_dashboard_launcher.py::test_local_grafana_dashboard_launcher_writes_dashboard_and_summary -q`
  - `2 passed`

## 40. `13-C EXECUTION` Build-10 technical dashboard now exposes Shadow execution telemetry status

- new dashboard truth:
  - `ShadowProjection` now carries `execution_telemetry_ref` and `execution_telemetry_status`
  - `scripts/run_technical_dashboard.py` now projects those service-owned fields from `shadow_vps_service.campaign_summary.json` into the canonical Build-10 Shadow section
  - `src/ui/technical_dashboard_view.py` now renders an explicit `Execution Telemetry` card under `Build-11 Shadow`
- preserve the doctrine:
  - dashboard/normalization only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_monitoring_backend.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `74 passed`
  - `rtk pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `10 passed`

## 41. `13-C EXECUTION` THR-X04 now lands as the third governed runtime consumer

- new runtime truth:
  - `src/execution_backbone/spread_guard.py` now defines the bounded runtime consumer for `THR-X04`
  - `src/local_replay_runtime/local_lab_execution_runtime_projection.py` now projects three consumers: `THR-X03 -> rate_limiter`, `THR-X04 -> spread_guard`, `THR-X05 -> slippage_model`
  - `src/protocols/execution_runtime_projection_bridge.py` and `src/protocols/execution_runtime_bootstrap.py` now load all three consumers in opt-in/fail-open mode
  - `src/execution_backbone/execution_runtime.py` now blocks on `spread_guard` only when the Lab projection explicitly loads that model
  - Build-10 monitoring, observability, technical dashboard, Shadow, Micro-live, and Live-light now all preserve the third consumer count and `spread_guard_model_loaded`
- preserve the doctrine:
  - opt-in only
  - no hidden live activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `python -m pytest tests/test_execution_backbone/test_spread_guard.py tests/test_execution_backbone/test_execution_runtime.py tests/test_local_replay_runtime/test_local_lab_execution_runtime_projection.py tests/test_protocols/test_execution_runtime_projection_bridge.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_protocols/test_execution_runtime_dashboard.py -q`
  - `50 passed`
  - `python -m pytest tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_observability.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_protocols/test_micro_live_runtime.py tests/test_protocols/test_micro_live_dashboard.py tests/test_protocols/test_live_light_runtime.py tests/test_protocols/test_live_light_dashboard.py -q`
  - `210 passed`

## 42. `13-C EXECUTION` Build-9 core smoke now accepts the governed execution projection seam

- new operated truth:
  - `scripts/run_build9_core_smoke.py` now accepts `--execution-runtime-projection-path`
  - the real non-test bootstrap path `_run_execution_bootstrap_smoke_with_projection(...)` now proves that `build_binance_execution_runtime(...)` can load the governed `THR-X03/X04/X05` consumer triplet on an operated launcher path
  - default smoke behavior stays unchanged when no projection is provided
- preserve the doctrine:
  - explicit opt-in only
  - no hidden live activation
  - no direct config bypass around the Lab projection
- latest proofs:
  - `python -m pytest tests/test_execution_backbone/test_build9_core_smoke_script.py tests/test_execution_backbone/test_spread_guard.py tests/test_execution_backbone/test_execution_runtime.py tests/test_protocols/test_execution_runtime_bootstrap.py -q`
  - `40 passed`

## 43. `13-C EXECUTION` the operated Shadow chain now preserves canonical bridge-load truth

- new operated truth:
  - `scripts/run_shadow_daily_orchestrator.py` no longer trusts only the top-level Lab artifact headline for `execution_runtime_projection`; it now derives the operated summary from the canonical bridge inspection
  - the Shadow daily last-run payload now persists whether the governed bridge is actually loadable plus the three model flags: `rate_limiter`, `spread_guard`, `slippage_model`
  - `scripts/run_shadow_vps_service.py`, `src/protocols/shadow_vps_service.py`, `src/monitoring/contracts.py`, and `src/monitoring/shadow_vps_service_monitoring.py` now carry that bridge truth through runtime-evidence, campaign summary, monitoring payload, and Prometheus export
  - `src/monitoring/local_grafana_dashboard.py` now exposes the same bridge-load truth in the local Shadow Grafana bundle through dedicated bridge/model-load panels
- preserve the doctrine:
  - no hidden runtime activation
  - no new launcher
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `rtk pytest tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `12 passed`
  - `rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `26 passed`
  - `python -m pytest tests/test_monitoring/test_local_grafana_dashboard.py::test_build_local_shadow_vps_grafana_dashboard_contains_expected_queries tests/test_monitoring/test_local_grafana_dashboard_launcher.py::test_local_grafana_dashboard_launcher_writes_dashboard_and_summary -q`
  - `2 passed`

## 44. `13-C EXECUTION` Build-10 Shadow cards now expose the operated projection bridge truth

- new operated truth:
  - `src/monitoring/contracts.py` now lets `ShadowProjection` carry the service-owned `execution_runtime_projection_*` bridge/load fields
  - `scripts/run_technical_dashboard.py` now projects those fields from `shadow_vps_service.campaign_summary.json` into the canonical Build-10 Shadow surface
  - `src/ui/technical_dashboard_view.py` now renders a dedicated `Execution Projection` card inside `Build-11 Shadow`, separate from the top-level bridge card and separate from `Execution Telemetry`
  - the local dev technical dashboard artifacts were regenerated under `build/dev_dual_role_demo/technical_dashboard`
- preserve the doctrine:
  - dashboard/normalization only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `rtk pytest tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_monitoring/test_monitoring_backend.py -q`
  - `74 passed`

## 45. `Build-14` bounded Opus entry-timing reader now exists on the governed enabler rail

- new code truth:
  - `src/complete_enablers/micro_edge_entry_timing_layer.py` now exists as the bounded Build-14 reader for the still-open Opus `entry timing` suggestion
  - it only uses existing `Build14ObservationInput` facts (`volume_support_ratio`, `adverse_obi_pressure`, `cra_sterilization_rate`, `queue_backlog`, `stale_pair_count`, `break_even_drift_alert`, `ce_net`)
  - `src/complete_enablers/limited_influence.py` now evaluates that reader beside the other Build-14 readers, so the entry-timing signal can appear in Shadow and post-Shadow bounded influence without opening a new runtime rail
  - `src/complete_enablers/__init__.py` now exports the new reader
- preserve the doctrine:
  - Build-14 enabler only
  - no autonomous trading behavior
  - no new runtime hook
  - no gate bypass around Shadow/Micro-live/Live
- latest proofs:
  - `rtk pytest tests/test_complete_enablers/test_contracts.py tests/test_protocols/test_live_light_runtime.py tests/test_protocols/test_shadow_runtime.py tests/test_smoke_bootstrap_recovery/test_shadow_readiness.py -q`
  - `97 passed`

## 46. `Build-14` bounded Opus exit-governor reader now exists on the governed enabler rail

- new code truth:
  - `src/complete_enablers/micro_edge_exit_governor.py` now exists as the bounded Build-14 reader for the still-open Opus `exit governor` suggestion
  - it only uses existing `Build14ObservationInput` facts (`break_even_drift_alert`, `cra_sterilization_rate`, `ce_net`, `dtr_loss_count`, `log_loss_count`, `breakout_failure_rate`, `ghost_liquidity_ratio`, `stale_pair_count`)
  - `src/complete_enablers/limited_influence.py` now evaluates that reader beside the other Build-14 readers, so the exit-quality signal can appear in Shadow and post-Shadow bounded influence without opening a new runtime rail
  - `src/complete_enablers/__init__.py` now exports the new reader
- preserve the doctrine:
  - Build-14 enabler only
  - no autonomous trading behavior
  - no new runtime hook
  - no gate bypass around Shadow/Micro-live/Live
- latest proofs:
  - `rtk pytest tests/test_complete_enablers/test_contracts.py tests/test_protocols/test_live_light_runtime.py tests/test_protocols/test_shadow_runtime.py tests/test_smoke_bootstrap_recovery/test_shadow_readiness.py -q`
  - `99 passed`

## 49. `T9 regime_lite` now loads the documented `THR-RG01..04` calibration seam

- new code truth:
  - `src/regime_classifier/regime_lite.py` now exposes `RegimeLiteCalibrationConfig` and `resolve_regime_lite_thresholds(...)`
  - the helper now consumes signed `calibration_loader` artifacts for `THR-RG01..04`
  - only the documented regime thresholds are artifact-governed in this slice; the secondary dimensions remain on bounded documented defaults until their own ids are promoted into the catalog
  - `calibration_loader` is now registered in the canonical manifest/build-order/dependency registry instead of remaining a shared-core ghost module
- preserve the doctrine:
  - opt-in loading only
  - no silent fallback when the artifact seam is requested
  - no hidden runtime activation
- latest proofs:
  - `rtk pytest tests/test_regime_classifier/test_regime_lite.py tests/test_manifest_registry/test_inventory.py tests/test_manifest_registry/test_build_order.py tests/test_manifest_registry/test_dependencies.py tests/test_dag_validator/test_layer_validator.py -q`
  - `128 passed`

## 50. `T9 regime_lite` now exposes an explicit governed `EXTREME -> safing recommendation` path

- new code truth:
  - `src/risk_backbone/regime_lite_safing.py` now exists
  - the helper emits a typed recommendation:
    - `ENTRY_BLOCK_ONLY` while cooldown is active
    - `HALT_RECOMMENDED` + `should_exit_all=True` while state=`EXTREME`
  - when explicitly requested, it can build a canonical `OperatorSafingRequest(action=set_halted)` using the existing governance dialect instead of inventing a new halt vocabulary
- preserve the doctrine:
  - recommendation only
  - no automatic kill switch trip
  - no hidden live activation
  - no gate bypass around Shadow/Micro-live/Live
- latest proofs:
  - `rtk pytest tests/test_risk_backbone/test_regime_lite_entry_gate.py tests/test_risk_backbone/test_regime_lite_safing.py tests/test_risk_backbone/test_risk_runtime.py -q`
  - `128 passed`

## 51. `T9 regime_lite` safing is now observable in canonical Build-10 supervision

- new code truth:
  - `src/monitoring/contracts.py` now exposes a typed `RegimeLiteSafingProjection` nested under `ShadowProjection`
  - `scripts/run_technical_dashboard.py` now hydrates this seam from `shadow_vps_service.campaign_summary.json` when the Shadow service emits it
  - `src/monitoring/technical_dashboard_backend.py` now elevates the Build-10 headline when the Shadow rail carries `entry_block_only` or `halt_recommended`
  - `src/ui/technical_dashboard_view.py` now renders an explicit `Build-11 Shadow -> Regime Safing` card
  - `src/monitoring/observability.py` now exports `v53_shadow_regime_lite_safing_status`
- preserve the doctrine:
  - recommendation only
  - no auto-`set_halted`
  - no hidden live activation
  - no dashboard-only raw seam
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_observability.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `85 passed`

## 52. `T9 regime_lite` now propagates explicit governance truth through `Shadow -> Micro-live -> Live-Light`

- new code truth:
  - `src/protocols/contracts.py` now exposes `RegimeLiteGovernanceSummary` as a protocol-local summary contract
  - `src/protocols/shadow_runtime.py` can now materialize that summary when explicit typed `RegimeLiteAssessment` / `RegimeLiteSafingRecommendation` inputs are supplied
  - `src/protocols/micro_live_runtime.py` and `src/protocols/live_light_runtime.py` now preserve the seam end-to-end without inventing classifier inputs
- preserve the doctrine:
  - explicit producer only
  - no synthetic regime inference from unrelated payload fields
  - recommendation only
  - no hidden live activation
- latest proofs:
  - `rtk pytest tests/test_protocols/test_contracts.py tests/test_protocols/test_shadow_runtime.py tests/test_protocols/test_micro_live_runtime.py tests/test_protocols/test_live_light_runtime.py -q`
  - `142 passed`

## 53. `T9 regime_lite` governance is now persisted on the operated `Shadow VPS service` rail

- new code truth:
  - `scripts/run_shadow_daily_orchestrator.py` now flattens `shadow_summary.regime_lite_governance` into the typed `last_run` sidecar instead of dropping the operated seam
  - `src/protocols/shadow_vps_service.py` now lets `ShadowVpsRuntimeEvidenceBundle` and `ShadowVpsCampaignSummary` carry the persisted `regime_lite` governance and safing fields
  - `scripts/run_shadow_vps_service.py` now copies that truth through `last_run -> runtime_evidence_bundle -> campaign_summary`
  - `src/monitoring/shadow_vps_service_monitoring.py` now surfaces the seam in the service payload/detail and exports bounded Prometheus symbols:
    - `v53_shadow_vps_regime_lite_safing_status`
    - `v53_shadow_vps_regime_lite_entries_blocked`
    - `v53_shadow_vps_regime_lite_should_exit_all`
- preserve the doctrine:
  - copy operated `Shadow` truth only
  - no synthetic regime inference inside the service
  - recommendation only
  - no hidden auto-halt / no bypass of `Shadow -> Micro-live -> Live`
- latest proofs:
  - `rtk pytest tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `13 passed`

## 54. `T9 regime_lite` now has an explicit operated producer on `run_local_replay_shadow -> daily orchestrator -> Shadow VPS service`

- new code truth:
  - `scripts/run_local_replay_shadow.py` now accepts:
    - `--regime-lite-assessment-path`
    - `--regime-lite-safing-recommendation-path`
  - the governed Shadow runner now forwards those typed JSON artifacts into both `run_shadow_validation(...)` calls instead of leaving the seam protocol-only
  - `scripts/run_shadow_daily_orchestrator.py` and `scripts/run_shadow_vps_service.py` now pass the same opt-in seam through the operated rail
  - when supplied, the real `shadow_summary`, `last_run`, `runtime_evidence_bundle`, `campaign_summary`, and service monitoring payload all carry `regime_lite_governance_status=ready`
- preserve the doctrine:
  - explicit opt-in only
  - no synthetic classifier inputs
  - recommendation only
  - no hidden auto-halt / no bypass of `Shadow -> Micro-live -> Live`
- latest proofs:
  - `rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py::test_export_local_replay_shadow_run_accepts_regime_lite_inputs tests/test_protocols/test_shadow_daily_orchestrator_launcher.py::test_shadow_daily_orchestrator_launcher_accepts_regime_lite_inputs tests/test_protocols/test_shadow_daily_orchestrator_launcher.py::test_read_regime_lite_governance_summary_projects_ready_shadow_summary tests/test_protocols/test_shadow_daily_orchestrator_launcher.py::test_shadow_daily_orchestrator_launcher_accepts_execution_runtime_projection_path tests/test_protocols/test_shadow_vps_service_launcher.py::test_shadow_vps_service_accepts_regime_lite_inputs tests/test_protocols/test_shadow_vps_service_launcher.py::test_shadow_vps_service_advances_to_next_dated_export_when_shadow_day_is_recorded tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `8 passed`

## 55. `T9 regime_lite` now auto-discovers governed sidecars on the `run_local_replay_shadow` rail

- new code truth:
  - `scripts/run_local_replay_shadow.py` now auto-discovers:
    - `regime_lite_assessment.json`
    - `regime_lite_safing_recommendation.json`
    in its governed `output_dir` when explicit CLI paths are omitted
  - this keeps the seam aligned with the existing `execution_runtime_projection` pattern instead of forcing manual CLI wiring on every run
  - the daily orchestrator can now pick up those sidecars automatically when they are staged inside the governed `shadow_output_dir`
- preserve the doctrine:
  - explicit path still wins
  - only typed sidecars are loaded
  - no synthetic classifier inputs
  - recommendation only / no hidden auto-halt
- latest proofs:
  - `python -m pytest tests/test_protocols/test_local_replay_shadow_runner.py::test_export_local_replay_shadow_run_autoloads_regime_lite_inputs tests/test_protocols/test_shadow_daily_orchestrator_launcher.py::test_shadow_daily_orchestrator_launcher_autoloads_regime_lite_inputs_from_shadow_output_dir -q`
  - `2 passed`

## 56. `T9 regime_lite` is now visible in the local Shadow Grafana dashboard

- new code truth:
  - `src/monitoring/local_grafana_dashboard.py` now includes dedicated Shadow panels for:
    - `Regime Lite Entries Blocked`
    - `Regime Lite Exit-All Recommended`
    - `Regime Lite Labels`
  - the dashboard now queries:
    - `v53_shadow_vps_regime_lite_entries_blocked`
    - `v53_shadow_vps_regime_lite_should_exit_all`
    - `v53_shadow_vps_regime_lite_safing_status`
  - the local dashboard summary/launcher tests no longer depend on the broken Windows `tmp_path` fixture on this machine
- preserve the doctrine:
  - dashboard reads only bounded Prometheus service metrics
  - no dashboard-only JSON seam
  - no hidden activation
- latest proofs:
  - `python -m pytest tests/test_monitoring/test_local_grafana_dashboard.py tests/test_monitoring/test_local_grafana_dashboard_launcher.py -q`
  - `4 passed`

## 57. `T9 regime_lite` now loads from `live_websocket_config` refs on the Shadow VPS service rail

- new code truth:
  - `src/protocols/shadow_vps_service.py` now lets `ShadowLiveWebSocketConfig` carry:
    - `regime_lite_assessment_path_ref`
    - `regime_lite_safing_recommendation_path_ref`
  - `scripts/run_shadow_vps_service.py` now resolves those refs with the same precedence as `execution_runtime_projection_path_ref`:
    - explicit CLI path wins
    - otherwise relative or absolute refs from `live_websocket_config` are loaded
  - the service now persists audit-ready provenance into state, runtime evidence bundle, campaign summary, and monitoring payload:
    - `regime_lite_assessment_ref/source`
    - `regime_lite_safing_recommendation_ref/source`
- preserve the doctrine:
  - no synthetic regime inference
  - no hidden auto-halt
  - typed artifact refs only
  - config loading stays recommendation-only
- latest proofs:
  - `python -m pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `12 passed`

## 58. `T9 regime_lite` provenance is now observable in Prometheus labels

- new code truth:
  - `src/monitoring/shadow_vps_service_monitoring.py` now emits `assessment_source` and `safing_source` labels on:
    - `v53_shadow_vps_regime_lite_safing_status`
    - `v53_shadow_vps_regime_lite_entries_blocked`
    - `v53_shadow_vps_regime_lite_should_exit_all`
  - the monitoring detail line now carries:
    - `regime_lite=<severity>@<state>@<assessment_source>/<safing_source>`
  - this makes `cli` vs `live_websocket_config` visible without opening JSON sidecars
- preserve the doctrine:
  - bounded labels only
  - no new dashboard-only seam
  - no runtime behavior change
- latest proofs:
  - `python -m pytest tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `2 passed`

## 59. `T9 regime_lite` ref/source provenance now reaches the canonical Build-10 technical dashboard

- new code truth:
  - `scripts/run_technical_dashboard.py` now hydrates the operated Shadow service provenance fields:
    - `regime_lite_assessment_ref/source`
    - `regime_lite_safing_recommendation_ref/source`
  - `src/ui/technical_dashboard_view.py` now renders those refs/sources directly in the Build-11 Shadow `Regime Safing` card detail
  - Build-10 therefore exposes the same operated truth already persisted by the Shadow service, instead of dropping the ref/source seam at the dashboard boundary
- preserve the doctrine:
  - dashboard reads typed operated artifacts only
  - no dashboard-only inference
  - recommendation only
  - no hidden activation
- latest proofs:
  - `python -m pytest tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `37 passed`

## 60. PowerShell Binance Shadow bootstrap now installs API env and launches a bounded governed live campaign

- new code truth:
  - `scripts/Install-BinanceApiEnv.ps1` now installs:
    - `BINANCE_API_KEY`
    - `BINANCE_API_SECRET`
    - `V53_BINANCE_API_KEY`
    - `V53_BINANCE_SECRET_KEY`
    - `V53_BINANCE_LABEL`
    in process scope, and optionally in user scope
  - `scripts/Start-BinanceShadowLiveCampaign.ps1` now:
    - materializes `live_websocket_config.json`
    - preserves existing governed route hints/config
    - launches one bounded `run_shadow_vps_service.py` cycle
    - regenerates the canonical Build-10 HTML dashboard from the resulting campaign root
  - `docs/production_deployment_plan/17A_BINANCE_SHADOW_POWERSHELL_BOOTSTRAP.md` documents the operator flow
- preserve the doctrine:
  - Shadow only
  - typed config / typed artifact refs only
  - no secrets persisted into repo JSON
  - dashboard remains read-only
- latest proofs:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-BinanceApiEnv.ps1`
  - `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-BinanceShadowLiveCampaign.ps1 -CampaignRoot .\build\build11_live_websocket_campaign -EnableTimeSyncProbe -StopOnError`

## 61. Native Binance live connect failures now preserve endpoint and root cause instead of a generic string

- new code truth:
  - `src/protocols/shadow_live_websocket.py` now raises:
    - `Native live_websocket adapter failed to connect to <endpoint>: <root cause>`
    when the gateway runtime returns a failed connect status with an error message
  - the operated Shadow service artifacts therefore now keep the actionable socket failure instead of only `failed to connect`
  - the previous `WinError 10013` observation was confirmed to be a Codex sandbox network artifact, not a host firewall failure
  - the same bounded PowerShell live campaign now succeeds when launched outside the sandbox on the real Windows host
- preserve the doctrine:
  - no runtime behavior change beyond diagnostics
  - typed operated artifacts remain the source of truth
  - no hidden retry policy change
- latest proofs:
  - `python -m pytest tests/test_protocols/test_shadow_live_websocket.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `44 passed`

## 62. The bounded Binance Shadow live campaign now succeeds on the real Windows host and regenerates Build-10 artifacts

- new code truth:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-BinanceShadowLiveCampaign.ps1 -CampaignRoot .\build\build11_live_websocket_campaign -EnableTimeSyncProbe -StopOnError`
    now completes successfully when run outside the Codex sandbox
  - the current operated campaign artifacts now show:
    - `service_status=stopped`
    - `last_error=""`
    - `last_completed_session_date="2026-04-12"`
    - `execution_telemetry_status="written"`
    - live capture pairs `BTCUSDT, ETHUSDT`
    - `live_user_data_authenticated=true`
  - the canonical HTML dashboard has been regenerated from the successful operated campaign root
- preserve the doctrine:
  - bounded `Shadow` only
  - no live order path
  - dashboard remains a read-only consumer of operated artifacts
- latest proofs:
  - operated campaign root:
    - `build/build11_live_websocket_campaign/service/shadow_vps_service.state.json`
    - `build/build11_live_websocket_campaign/service/shadow_vps_service.campaign_summary.json`
    - `build/build11_live_websocket_campaign/technical_dashboard/technical_dashboard.html`

## 63. `daily_pnl_breaker` now exists and the first governed `THR-R01 -> risk_runtime` consumer is open

- new code truth:
  - `src/risk_backbone/loss_budgeter/daily_pnl_breaker.py` now exists as the typed persistent daily Shadow-lock seam for `THR-R01`
  - the breaker loads governed `THR-R01` via `calibration_loader`, enforces the documented hard cap `2%`, persists same-day Shadow lock state, and can optionally trip the canonical circuit breaker when explicitly asked
  - `src/risk_backbone/daily_pnl_breaker_entry_gate.py` now exists as the first bounded runtime consumer
  - `src/risk_backbone/risk_runtime.py` now accepts a typed opt-in `daily_pnl_precheck_hook`, so Build-4 can reject new entries when the breaker has already forced the session into Shadow
- preserve the doctrine:
  - opt-in only
  - fail-open by default
  - no hidden live activation
  - no automatic same-day reactivation after a breach
- latest proofs:
  - `python -m pytest tests/test_risk_backbone/test_daily_pnl_breaker.py tests/test_risk_backbone/test_daily_pnl_breaker_entry_gate.py tests/test_risk_backbone/test_risk_runtime.py -q`
  - `34 passed`
  - `python -m pytest tests/test_risk_backbone/test_risk_integration.py tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime.py -q`
  - `42 passed`

## 64. `reconciliation_scheduler` now exists as the first bounded `THR-I04` operated control seam

- new code truth:
  - `src/execution_backbone/reconciliation_layer/scheduler.py` now exists
  - the scheduler loads governed `THR-I04`, enforces bounded interval limits, and exposes typed `boot_reconcile(...)` + `run_periodic_if_due(...)`
  - boot reconciliation now has a canonical blocking seam for unresolved divergences
  - periodic reconciliation now has a canonical due/not-due seam and can trip the existing circuit breaker on critical divergence
- preserve the doctrine:
  - no daemon thread or hidden loop in this slice
  - explicit caller ownership of timing
  - reuse the canonical `EmergencyCircuitBreaker`
  - no bypass of the existing reconciliation runtime
- latest proofs:
  - `python -m pytest tests/test_execution_backbone/test_reconciliation_scheduler.py tests/test_execution_backbone/test_reconciliation_layer.py -q`
  - `35 passed`
  - `python -m pytest tests/test_execution_backbone/test_execution_runtime.py -q`
  - `28 passed`

## 65. `execution_runtime_bootstrap` now executes the first real operated `THR-I04` boot seam through Build-9 smoke

- new code truth:
  - `src/protocols/execution_runtime_bootstrap.py` now exposes typed bootstrap bundles:
    - `ExecutionRuntimeBootstrapBundle`
    - `build_execution_runtime_bootstrap_bundle(...)`
    - `build_binance_execution_runtime_bootstrap_bundle(...)`
  - the existing `build_execution_runtime(...)` and `build_binance_execution_runtime(...)` stay backward-compatible and still return only `ExecutionRuntime`
  - the new bundle can now expose:
    - the built runtime
    - the optional bounded `ReconciliationScheduler`
    - the optional boot reconcile result
  - stale-only first boot with zero divergences is now treated canonically as initial baseline establishment, not as a false trading block
  - `scripts/run_build9_core_smoke.py` now executes this seam explicitly and can also load governed `THR-I04` from an optional calibration root
- preserve the doctrine:
  - opt-in only
  - no hidden scheduler loop
  - no fake Shadow integration before a real runtime call site exists
  - Build-9 smoke remains the first operated caller on this rail
- latest proofs:
  - `rtk pytest tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py tests/test_execution_backbone/test_reconciliation_scheduler.py -q`
  - `20 passed`
  - `rtk pytest tests/test_execution_backbone/test_execution_runtime.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py tests/test_execution_backbone/test_reconciliation_scheduler.py -q`
  - `48 passed`

## 66. The standalone Build-9 smoke script now aligns with the canonical engine + portfolio facades

- new code truth:
  - `scripts/run_build9_core_smoke.py` now imports the canonical engine facades through:
    - `engines.engine_a`
    - `engines.engine_b`
    instead of the stale top-level aliases
  - the same script now bootstraps the Build-8 portfolio chain with an explicit `freshness_policy`, matching the current `OrchestratorConfig` contract
  - the direct script run therefore now reports:
    - Build-2..9 `PASS`
    - engine chain `PASS`
    - portfolio chain `PASS`
    - execution bootstrap `PASS`
  - the remaining direct-run failure is outside this slice: Build-1 still reports pre-existing DAG violations
- preserve the doctrine:
  - no new launcher
  - no compatibility alias package invented
  - smoke script updated to current canonical facades and typed config only
- latest proofs:
  - `rtk pytest tests/test_execution_backbone/test_build9_core_smoke_script.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_reconciliation_scheduler.py -q`
  - `21 passed`
  - `python scripts/run_build9_core_smoke.py`
  - direct report now shows Build-2..9 `PASS`; only Build-1 DAG remains `FAIL`

## 67. Build-1 DAG now reflects mostly real cycle debt instead of mixed registry drift

- new code truth:
  - `src/manifest_registry/module_inventory.py` now registers the real on-disk packages:
    - `calibration_methods`
    - `secrets_manager`
    - `sharia_compliance`
    - `venue_adapters`
  - `src/manifest_registry/build_order_registry.py` now gives those modules explicit build ownership without changing the Build-1 count:
    - `sharia_compliance` in Build-3
    - `calibration_methods` in Build-10
    - `secrets_manager` and `venue_adapters` in Build-11
  - `src/manifest_registry/dependency_registry.py` now authorizes the non-cyclic imports already present on disk for:
    - `execution_backbone -> calibration_loader, sharia_compliance`
    - `risk_backbone -> calibration_loader`
    - `scoring_backbone -> data_backbone`
    - `local_replay_runtime -> calibration_methods, data_backbone, meta_learning`
    - `backtest_artifact_import -> meta, monitoring`
    - `protocols -> engine_a, engine_b, regime_classifier, venue_adapters`
    - `venue_adapters -> interface_contracts, calibration_loader, data_backbone, execution_backbone, secrets_manager, sharia_compliance`
  - the missing-manifest bucket is now closed, and the Build-1 DAG report has been reduced from `47` errors to `27`
  - the remaining Build-1 failures are now the real debt:
    - cycle cluster around `local_replay_runtime`, `backtest_artifact_import`, `monitoring`, `protocols`, `ui`
    - forward/late imports:
      - `execution_backbone -> risk_backbone, scoring_backbone`
      - `monitoring -> complete_enablers, protocols, local_replay_runtime`
      - `protocols -> complete_enablers, engine_c, engine_d`
- preserve the doctrine:
  - no validator weakening
  - no cycle authorization to fake a green Build-1
  - no Build-1 module-count inflation
  - registry drift fixed first, real refactor debt left explicit
- latest proofs:
  - `rtk pytest tests/test_manifest_registry/test_inventory.py tests/test_manifest_registry/test_build_order.py tests/test_manifest_registry/test_dependencies.py -q`
  - `83 passed`
  - `python -c "import sys; sys.path.insert(0, 'src'); from dag_validator import validate_architecture; report = validate_architecture(); print(report.passed, report.error_count, report.warning_count)"`
  - `False 27 0`
  - `python scripts/run_build9_core_smoke.py`
  - direct report still shows Build-2..9 `PASS`; only Build-1 `dag_validator` remains `FAIL (27 error(s))`

## 68. Build-1 dropped the local_replay_runtime -> monitoring cycle cluster

- new code truth:
  - the Local IA Lab monitoring builders now live under `src/monitoring/`:
    - `local_lab_monitoring_projection.py`
    - `local_lab_monitoring_backend.py`
    - `local_lab_observability.py`
  - `scripts/run_local_lab_analysis_bundle.py` now feeds those builders with primitive release/bridge/promotion facts instead of passing `local_replay_runtime` typed objects across the boundary
  - the old `src/local_replay_runtime/local_lab_monitoring_*` files were removed instead of leaving compatibility wrappers that would preserve the reverse edge
  - the validator no longer reports the `local_replay_runtime -> monitoring` unauthorized imports, and the prior cycle cluster through those modules is gone
  - Build-1 real DAG debt is now down to `23` blocking errors:
    - `4` cycles
    - `19` unauthorized imports
- preserve the doctrine:
  - no validator weakening
  - no wrapper alias that keeps the same dependency alive
  - COMPLETE-only runtime doctrine remains unchanged; this slice does not reintroduce `LIGHT`
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_local_lab_monitoring_feed.py tests/test_monitoring/test_local_lab_monitoring_bundle_manifest.py tests/test_monitoring/test_local_lab_ingestion.py tests/test_monitoring/test_local_lab_bundle_loader.py tests/test_monitoring/test_local_lab_bundle_discovery.py -q`
  - `23 passed`
  - direct `dag_validator` report now shows `23` blocking errors (`4` cycles + `19` unauthorized imports)
  - direct `python scripts/run_build9_core_smoke.py` still reaches Build-2..9 `PASS`; only Build-1 `dag_validator` remains `FAIL (23 error(s))`

## 69. Build-1 removed the replay-workflow loader and injected-stream back-edges

- new code truth:
  - `local_lab_replay_workflow_loader.py` now lives under `src/local_replay_runtime/`, not `src/monitoring/`
  - the old monitoring loader file was removed, so `monitoring -> local_replay_runtime` no longer exists through that replay workflow seam
  - shared injected stream loading now lives under `src/data_backbone/websocket_gateway/injected_stream_loader.py`
  - `protocols.shadow_websocket_ingest` and `local_replay_runtime.local_lab_execution_telemetry_artifact` both consume that lower loader instead of `local_replay_runtime -> protocols`
  - Build-1 blocking DAG debt is now down again to `19` real errors:
    - `3` cycles
    - `16` unauthorized imports
- preserve the doctrine:
  - no fake monitoring alias
  - no protocol wrapper kept only for Build-1 silence
  - COMPLETE-only runtime doctrine remains unchanged
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_local_lab_replay_workflow_loader.py tests/test_protocols/test_shadow_websocket_ingest.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_protocols/test_contracts.py -q`
  - `36 passed`
  - direct `dag_validator` report now shows `19` blocking errors (`3` cycles + `16` unauthorized imports)
  - direct `python scripts/run_build9_core_smoke.py` still reaches Build-2..9 `PASS`; only Build-1 `dag_validator` remains `FAIL (19 error(s))`

## 70. Build-1 is now green after lowering the last execution-owned helpers

- new code truth:
  - `src/execution_backbone/execution_runtime.py` now imports its fee-aware edge gate from `src/execution_backbone/fee_aware_edge_gate.py`, not from `scoring_backbone`
  - `src/execution_backbone/reconciliation_layer/scheduler.py` now imports its circuit breaker from `src/execution_backbone/emergency_circuit_breaker.py`, not from `risk_backbone`
  - `src/scoring_backbone/fee_aware_edge_gate.py` is now a compatibility surface over the canonical execution-owned implementation
  - `src/risk_backbone/emergency_kill_switch/circuit_breaker.py` is now a compatibility surface over the canonical execution-owned implementation
  - `src/manifest_registry/dependency_registry.py` no longer grants the temporary upward allowances `execution_backbone -> risk_backbone` and `execution_backbone -> scoring_backbone`
  - instead, the higher modules keep explicit downward compatibility dependencies on `execution_backbone`
- preserve the doctrine:
  - no validator weakening
  - no fake Build-1 green through broad registry allowances
  - COMPLETE-only runtime doctrine unchanged
- latest proofs:
  - `rtk pytest tests/test_execution_backbone/test_execution_runtime.py tests/test_execution_backbone/test_reconciliation_scheduler.py tests/test_scoring_backbone tests/test_risk_backbone/test_circuit_breaker.py -q`
  - `168 passed`
  - `rtk pytest tests/test_manifest_registry/test_inventory.py tests/test_manifest_registry/test_build_order.py tests/test_manifest_registry/test_dependencies.py tests/test_dag_validator/test_layer_validator.py -q`
  - `96 passed`
  - direct `dag_validator` report now shows `0` blocking errors
  - direct `python scripts/run_build9_core_smoke.py` now reaches Build-1 `PASS` and Build-2..9 `PASS`

## 71. T12 now has a real canonical gatekeeper wrapper on the Build-3 execution rail

- new code truth:
  - `src/execution_backbone/gatekeeper/gatekeeper.py` now exists as the execution-owned convergence wrapper
  - `ExecutionRuntime.submit_opportunity(...)` now routes the pre-submit decision chain through `ExecutionGatekeeper.authorize(...)`
  - the existing execution guards stay intact; the gatekeeper is a convergence surface, not a replacement path
  - refusals now preserve the real `pair` and `engine_id` in the emitted `NoTradeDecision`
  - `ExecutionSubmission` now carries `gate_trace`, and the same trace is emitted in structured submission logs
  - `src/execution_backbone/__init__.py` now exports the typed gatekeeper surface
- deliberate limit of this slice:
  - no persisted `artifacts/gatekeeper/` audit store yet
  - no new runtime path outside the canonical Build-3 rail
  - COMPLETE-only doctrine unchanged
- latest proofs:
  - `rtk pytest tests/test_execution_backbone/test_gatekeeper.py tests/test_execution_backbone/test_execution_runtime.py tests/test_protocols/test_execution_runtime_bootstrap.py -q`
  - `41 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 72. T13 now has a first bounded info-stress precheck on the Build-4 risk rail

- new code truth:
  - `src/risk_backbone/info_stress_monitor.py` now exists as the bounded V37-3 detector
  - the monitor classifies `NORMAL / ELEVATED / EXTREME` from five simple signals:
    - spread explosion
    - depth ratio collapse
    - cancellation spike
    - taker imbalance saturation
    - micro-vol divergence
  - `build_info_stress_entry_gate(...)` now exposes that detector as a typed `RiskInfoStressPrecheckHook`
  - `src/risk_backbone/risk_runtime.py` now supports a dedicated `info_stress_precheck_hook` and explicit candidate-side indicator fields
  - EXTREME now blocks new entries through a governed cooldown on the real Build-4 risk runtime rail
- deliberate limit of this slice:
  - opt-in only
  - no Shadow/Micro-live/Live auto-wiring yet
  - no ML-heavy MAS implementation; this is the bounded lite seam only
- latest proofs:
  - `rtk pytest tests/test_risk_backbone/test_info_stress_monitor.py tests/test_risk_backbone/test_risk_runtime.py -q`
  - `29 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 73. T13 info_stress now propagates through the late-stage protocol rails

- new code truth:
  - `src/protocols/contracts.py` now defines `InfoStressGovernanceSummary`
  - `src/protocols/shadow_runtime.py` now accepts an optional `info_stress_assessment` and projects it into typed `shadow_summary.info_stress_governance`
  - `src/protocols/micro_live_runtime.py` now preserves that summary from Shadow into both `MicroLiveInput` and `MicroLiveRunSummary`
  - `src/protocols/live_light_runtime.py` now preserves the same summary from Micro-live into both `LiveLightInput` and `LiveLightRunSummary`
  - `src/protocols/__init__.py` now exports the summary type as canonical protocol surface
- deliberate limit of this slice:
  - no launcher/service/config auto-loading yet
  - no monitoring/dashboard projection yet
  - no second recommendation layer invented; this stays assessment-only for now
- latest proofs:
  - `rtk pytest tests/test_protocols/test_contracts.py tests/test_protocols/test_shadow_runtime.py tests/test_protocols/test_micro_live_runtime.py tests/test_protocols/test_live_light_runtime.py -q`
  - `147 passed`
  - `rtk pytest tests/test_risk_backbone/test_info_stress_monitor.py tests/test_risk_backbone/test_risk_runtime.py -q`
  - `29 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 74. T13 info_stress now propagates on the operated Shadow rail

- new code truth:
  - `scripts/run_local_replay_shadow.py` now accepts and auto-discovers `info_stress_assessment.json` and forwards the typed assessment into both provisional and final `run_shadow_validation(...)`
  - `scripts/run_shadow_daily_orchestrator.py` now projects `shadow_summary.info_stress_governance` into `shadow_daily_orchestrator.last_run.json`
  - `src/protocols/shadow_vps_service.py` now lets `ShadowLiveWebSocketConfig` carry `info_stress_assessment_path_ref`
  - `scripts/run_shadow_vps_service.py` now resolves `info_stress_assessment` with the same precedence as other governed refs (`cli` first, then `live_websocket_config`)
  - the service now persists `info_stress` ref/source plus governance truth into state, runtime evidence bundle, campaign summary, monitoring payload, and Prometheus export
  - `src/monitoring/shadow_vps_service_monitoring.py` now exports:
    - `v53_shadow_vps_info_stress_status`
    - `v53_shadow_vps_info_stress_alert_count`
    - `v53_shadow_vps_info_stress_entries_blocked`
- deliberate limit of this slice:
  - assessment-only seam remains intact
  - no fake recommendation layer
  - no new auto-halt or late-stage hidden activation
- latest proofs:
  - `rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `39 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 75. T12 now persists a real append-only gatekeeper audit store on the canonical execution rail

- new code truth:
  - `src/execution_backbone/gatekeeper/audit_logger.py` now exists as the append-only JSONL audit logger for canonical gatekeeper decisions
  - `src/execution_backbone/execution_runtime.py` now accepts an optional `GatekeeperAuditLogger` and writes submitted / no-trade / blocked decisions on the existing `submit_opportunity(...)` path
  - `src/protocols/execution_runtime_bootstrap.py` now threads `gatekeeper_audit_path` through the canonical runtime bootstrap helpers
  - `scripts/run_build9_core_smoke.py` now accepts `--gatekeeper-audit-path` and can materialize a real `artifacts/gatekeeper/audit.jsonl` during the bounded bootstrap smoke
- deliberate limit of this slice:
  - no new runtime path outside the canonical Build-3 rail
  - no synthetic monitoring/dashboard layer added for this audit store
  - COMPLETE-only doctrine unchanged
- latest proofs:
  - `python -m pytest tests/test_execution_backbone/test_gatekeeper.py tests/test_execution_backbone/test_execution_runtime.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q`
  - `51 passed`
  - direct `python scripts/run_build9_core_smoke.py --gatekeeper-audit-path build/build9_core_smoke_run/artifacts/gatekeeper/audit.jsonl`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 76. T11 now has a bounded log rotation seam inside monitoring

- new code truth:
  - `src/monitoring/log_rotation.py` now exists as the bounded gzip + retention helper for operated logs
  - `rotate_log_file(...)` rotates one file into a timestamped `.gz`, truncates the active log, and prunes old archives by retention window
  - `src/monitoring/__init__.py` now exports `LogRotationResult` and `rotate_log_file`
- deliberate limit of this slice:
  - no Telegram integration yet
  - no automatic scheduler/daemon around rotation
  - no new package/profile semantics introduced
- latest proofs:
  - `python -m pytest tests/test_monitoring/test_log_rotation.py tests/test_monitoring/test_disk_monitor.py tests/test_execution_backbone/test_gatekeeper.py tests/test_execution_backbone/test_execution_runtime.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q`
  - `55 passed`

## 77. T11 now has a bounded `telegram_alerter` adapter over canonical `AlertRecord`

- new code truth:
  - `src/alerting/{__init__,telegram_alerter}.py` now exists as a bounded external delivery adapter package
  - `telegram_alerter.py` loads bot token + chat id from JSON/YAML or sealed mappings via `secrets_manager.load(...)`
  - the adapter stays typed on canonical `interface_contracts.AlertRecord`, with severity filtering and bounded urllib posting
  - `manifest_registry` now registers `alerting` as a canonical Build-11 module, so adding the package does not re-open Build-1 DAG drift
- deliberate limit of this slice:
  - no hidden `monitoring -> alerting` wiring yet
  - no daemon, retry loop, or background sender
  - COMPLETE-only doctrine unchanged
- latest proofs:
  - `$env:PYTHONPATH='src'; python -m pytest tests/test_alerting/test_telegram_alerter.py tests/test_manifest_registry/test_inventory.py tests/test_manifest_registry/test_build_order.py tests/test_manifest_registry/test_dependencies.py tests/test_manifest_registry/test_profiles.py tests/test_dag_validator/test_layer_validator.py -q`
  - `126 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 78. T11 now has an operated opt-in Telegram alert seam on `run_shadow_vps_service`

- new code truth:
  - `src/protocols/shadow_vps_service_telegram_alerting.py` now projects operated `ShadowVpsServiceEvent` values into canonical `AlertRecord`
  - `scripts/run_shadow_vps_service.py` now accepts `--telegram-alert-config-path` and `--telegram-alert-key-path`
  - when configured explicitly, the service sends bounded Telegram alerts for selected operated events (`service_started`, `shadow_day_completed`, `shadow_day_failed`, `service_stopped`)
  - every delivery attempt is audited in the existing `shadow_vps_service.events.jsonl` stream as `telegram_alert_sent` or `telegram_alert_failed`
- deliberate limit of this slice:
  - no hidden Build-10 `monitoring_runtime -> alerting` dependency
  - no daemon, retry loop, or background sender
  - Telegram failures do not crash the service
- latest proofs:
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_protocols/test_shadow_vps_service_telegram_alerting.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_manifest_registry/test_dependencies.py tests/test_dag_validator/test_layer_validator.py -q`
  - `43 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 79. T11 now projects operated Telegram delivery truth into Shadow monitoring and Prometheus

- new code truth:
  - `ShadowVpsServiceState`, `ShadowVpsCampaignSummary`, and `ShadowVpsServiceMonitoringPayload` now carry the last Telegram delivery truth as `status / event_type / error`
  - `scripts/run_shadow_vps_service.py` now persists that truth on each bounded delivery attempt and rewrites the final campaign summary + monitoring artifacts after `service_stopped`
  - `src/monitoring/shadow_vps_service_monitoring.py` now exposes the same seam in payload detail and Prometheus via `v53_shadow_vps_telegram_alert_delivery_status`
- deliberate limit of this slice:
  - no Build-10 dashboard/UI wiring yet
  - no historical counter/time-series store beyond the last service-backed truth
  - no daemon/retry semantics added
- latest proofs:
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_protocols/test_shadow_vps_service_telegram_alerting.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `17 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 80. T11 now projects Shadow Telegram delivery truth into the canonical Build-10 technical dashboard

- new code truth:
  - `scripts/run_technical_dashboard.py` now reads `telegram_alert_delivery_status / event_type / error` from `shadow_vps_service.campaign_summary.json`
  - `src/ui/technical_dashboard_view.py` now renders a dedicated Build-11 Shadow card `Telegram Alerts`
  - the rendered local artifact for `build11_live_websocket_campaign` now carries the same service-backed Telegram seam as monitoring/Prometheus
- deliberate limit of this slice:
  - no Grafana work here
  - no new alerting logic; Build-10 remains a pure projection surface
  - no historical aggregation beyond the last service-backed Telegram truth
- latest proofs:
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `77 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 81. T11 now exposes Telegram in local Shadow Grafana and persists Telegram config provenance on the operated service rail

- new code truth:
  - `src/monitoring/local_grafana_dashboard.py` now adds `Telegram Alerts` and `Telegram Alert Labels` to the local Shadow Grafana bundle
  - `ShadowLiveWebSocketConfig` now accepts `telegram_alert_config_path_ref` and `telegram_alert_key_path_ref`
  - `scripts/run_shadow_vps_service.py` now resolves Telegram config/key paths with the same precedence as other operated refs: CLI first, then `live_websocket_config`
  - `ShadowVpsServiceState`, `ShadowVpsRuntimeEvidenceBundle`, `ShadowVpsCampaignSummary`, and `ShadowVpsServiceMonitoringPayload` now carry Telegram config/key `ref/source`
  - `src/monitoring/shadow_vps_service_monitoring.py` now exposes `config_source` on `v53_shadow_vps_telegram_alert_delivery_status`
- deliberate limit of this slice:
  - no new Build-10 dashboard projection yet for Telegram config provenance
  - no hidden sender loop or retry daemon
  - local Grafana remains a Prometheus projection surface only
- latest proofs:
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_monitoring/test_local_grafana_dashboard.py tests/test_monitoring/test_local_grafana_dashboard_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `21 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 82. T13 now projects the operated execution runtime bootstrap seam into canonical Shadow monitoring and Build-10

- new code truth:
  - `scripts/run_shadow_vps_service.py` now persists the useful bootstrap reconcile truth, not just `ref/status/source`: `user_data_stream_enabled`, `reconciliation_boot_executed`, `reconciliation_boot_trading_blocked`, `reconciliation_boot_circuit_breaker_tripped`, `reconciliation_boot_recovery_action`, and `reconciliation_boot_divergence_count`
  - `src/monitoring/shadow_vps_service_monitoring.py` now exposes that seam in the canonical Shadow payload and Prometheus via `v53_shadow_vps_execution_runtime_bootstrap_status`, `..._divergence_count`, and `..._trading_blocked`
  - `scripts/run_technical_dashboard.py` and `src/ui/technical_dashboard_view.py` now project the same service-backed seam into a dedicated Build-11 Shadow card `Execution Bootstrap`
- deliberate limit of this slice:
  - no new bootstrap runtime behavior
  - no daemon, retry loop, or order-submit path
  - Build-10 remains a projection surface over service truth
- latest proofs:
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `56 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 83. Build-1 now enforces executable engineering guardrails with a baseline-aware repo-wide scan

- new code truth:
  - `src/smoke_bootstrap_recovery/engineering_guardrails.py` now materializes executable rules derived from `CODEX_PROMPT.md`: missing future annotations, file/function size, `print()`, bare `except`, missing annotations, and `Any`
  - `scripts/run_engineering_guardrails.py` now runs the repo-wide scan, writes an audit-ready report under `build/engineering_guardrails/`, and can refresh the accepted legacy baseline in `config/engineering_guardrails_baseline.json`
  - `run_build1_smoke()` now executes the guardrail scan as a real Build-1 sanity check through `smoke_bootstrap_recovery`, so new violations fail the foundation rail while existing legacy debt is grandfathered by baseline
- deliberate limit of this slice:
  - no repo-wide blind refactor
  - no fail-on-legacy without baseline
  - hotspots are reported, not auto-rewritten
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py --write-baseline`
  - repo-wide baseline generated over `826` Python files with `4363` accepted legacy violations
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_smoke_bootstrap_recovery/test_engineering_guardrails.py tests/test_smoke_bootstrap_recovery/test_state_sanity.py tests/test_smoke_bootstrap_recovery/test_smoke_reporter.py -q`
  - `41 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 84. The first operated guardrail hotspot reduction now hardens `run_shadow_vps_service.py` without changing service semantics

- new code truth:
  - `scripts/run_shadow_vps_service.py` now annotates the previously untyped helpers `_append_service_event(...)` and `_write_campaign_summary(...)`
  - the dynamic script loaders now share a typed `_load_script_module(...) -> ModuleType` helper instead of duplicated untyped loader code
  - the service final CLI output is now built by `_build_service_output_lines(...)` and emitted through `_emit_output_lines(...)`, removing direct `print()` calls from the operated service script
  - `main(...)` is now decomposed into typed parser helpers `_build_argument_parser(...)`, `_add_*_arguments(...)`, and `_validate_input_root_selection(...)`
  - the previous bare `except Exception:` on execution telemetry artifact write is now explicit and re-raises with a precise runtime error
  - `_write_monitoring_artifacts(...)` now uses `_resolve_monitoring_artifact_paths(...)`, bringing that helper under the executable guardrail threshold
- deliberate limit of this slice:
  - no semantic change to the Shadow service loop
  - no decomposition yet of the three remaining large monoliths: `_write_runtime_evidence_bundle(...)`, `_write_campaign_summary(...)`, and `run_shadow_vps_service(...)`
  - file-level length debt remains open
- latest proofs:
  - focused `shadow service + monitoring` slice: `19 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`
  - repo-wide guardrail total reduced from `4363` to `4341`
  - `scripts/run_shadow_vps_service.py` reduced from `26` guardrail violations to `4` residual violations (`FILE_TOO_LONG`, `_write_runtime_evidence_bundle`, `_write_campaign_summary`, `run_shadow_vps_service`)

## 85. The second operated hotspot reduction decomposes `campaign_summary` in `run_shadow_vps_service.py` without schema drift

- new code truth:
  - `scripts/run_shadow_vps_service.py` now builds the Shadow campaign summary through grouped typed helpers: core, live-capture, execution, regime, and info-stress fields
  - `_write_campaign_summary(...)` is now a thin orchestrator over those field-builders and no longer carries the full schema inline
  - the execution/regime/info builders were themselves split to stay below the executable guardrail threshold
- deliberate limit of this slice:
  - no change to `ShadowVpsCampaignSummary` field names, defaults, or persisted artifact paths
  - no change to service-loop control flow
  - `FILE_TOO_LONG`, `_write_runtime_evidence_bundle(...)`, and `run_shadow_vps_service(...)` remain explicit debt
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4340`, `new_violations=0`
- `$env:PYTHONPATH='src'; rtk pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
- `19 passed`
- direct `python scripts/run_build9_core_smoke.py`
- Build-1 `PASS`, Build-2..9 `PASS`

## 87. The fourth operated hotspot reduction collapses `run_shadow_vps_service(...)` under executable guardrails

- new code truth:
  - `scripts/run_shadow_vps_service.py` now routes the public service entrypoint through dedicated startup, loop, finalize, and output helpers instead of keeping the full operated loop inline
  - the remaining runtime-context builder debt was reduced with small extraction helpers only; no artifact schema or monitoring contract changed
  - `run_shadow_vps_service(...)` is now below the guardrail threshold and the repo is back to `new_violations=0`
- deliberate limit of this slice:
  - no service-loop semantic drift
  - no schema rename and no monitoring field loss
  - remaining debt on this file is now narrowed to `FILE_TOO_LONG`
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4338`, `new_violations=0`
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `19 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 86. The third operated hotspot reduction decomposes `runtime_evidence_bundle` in `run_shadow_vps_service.py` without schema drift

- new code truth:
  - `scripts/run_shadow_vps_service.py` now materializes `ShadowVpsRuntimeEvidenceBundle` through grouped typed builders for `input`, `execution`, `projection`, `regime_lite`, `info_stress`, and durable artifact refs
  - the service script now centralizes `last_run` conversions through `_last_run_str/_bool/_int/_str_tuple`, removing the previous long inline field mapping
  - `_write_runtime_evidence_bundle(...)` is now a thin orchestrator and no longer carries the durable runtime schema inline
- deliberate limit of this slice:
  - no change to `ShadowVpsRuntimeEvidenceBundle` field names, defaults, or persisted artifact paths
  - no change to service-loop control flow
  - remaining explicit guardrail debt on this file is now only `FILE_TOO_LONG` and `run_shadow_vps_service(...)`
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py --write-baseline`
  - baseline refreshed to the reduced repo-wide debt level
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4339`, `new_violations=0`
- `$env:PYTHONPATH='src'; rtk pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
- `19 passed`
- direct `python scripts/run_build9_core_smoke.py`
- Build-1 `PASS`, Build-2..9 `PASS`

## 88. The next operated hotspot reduction collapses `run_local_replay_shadow.py` under executable guardrails except for file split debt

- new code truth:
  - `scripts/run_local_replay_shadow.py` now routes `export_local_replay_shadow_run(...)` through typed import-context, import-bundle, runtime-bundle, day-recording, and session-materialization helpers instead of one monolithic runner body
  - the script now uses explicit typed helpers for `demo payload`, per-engine Shadow evaluations, and CLI artifact output, eliminating the prior inline `print()` and missing-annotation debt
  - the hotspot dropped from `22` file-local guardrail violations to `1`, with the only explicit residue now `FILE_TOO_LONG`
- deliberate limit of this slice:
  - no artifact schema rename
  - no LOCAL_REPLAY -> SHADOW control-flow drift
  - no change to governed sidecar names or session-summary contract
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4316`, `new_violations=0`
- `$env:PYTHONPATH='src'; rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py -q`
- `18 passed`
- direct `python scripts/run_build9_core_smoke.py`
- Build-1 `PASS`, Build-2..9 `PASS`

## 89. The next operated hotspot reduction fully splits `run_local_replay_shadow.py` into bounded support modules

- new code truth:
  - `scripts/run_local_replay_shadow.py` is now a thin public CLI/API facade over bounded support modules:
    - `scripts/local_replay_shadow_models.py`
    - `scripts/local_replay_shadow_engines.py`
    - `scripts/local_replay_shadow_payloads.py`
    - `scripts/local_replay_shadow_import_support.py`
    - `scripts/local_replay_shadow_session_support.py`
  - the governed `LOCAL_REPLAY -> VPS import -> SHADOW` flow kept the same exported API surface (`main`, `export_local_replay_shadow_run`, `LocalReplayShadowArtifacts`) while eliminating the last file-length debt on the original script
  - all six files are now at `0` local guardrail violations; the file-length debt is not merely moved elsewhere
- deliberate limit of this slice:
  - no artifact path rename
  - no contract drift on session summaries, runtime evidence, or upload/import sidecars
  - no behavior change on the governed Shadow rail
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4315`, `new_violations=0`
- `$env:PYTHONPATH='src'; rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py -q`
- `18 passed`
- direct `python scripts/run_build9_core_smoke.py`
- Build-1 `PASS`, Build-2..9 `PASS`

## 90. The next operated hotspot reduction removes CLI print debt from `run_local_lab_analysis_bundle.py`

- new code truth:
  - `scripts/run_local_lab_analysis_bundle.py` now routes all terminal emission through `_emit_local_lab_analysis_bundle_output(...)` and `_write_cli_output(...)` instead of inline `print()` calls
  - the change preserves the same operator-facing artifact paths and keeps the Local IA Lab bundle pipeline unchanged
  - file-local debt on this hotspot dropped from `30` to `2`; only `FILE_TOO_LONG` and `FUNCTION_TOO_LONG main` remain
- deliberate limit of this slice:
  - no change to Local IA Lab artifact schema
  - no change to the chained review/calibration/replay/monitoring pipeline
  - no broad refactor of the giant `main(...)` yet
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4287`, `new_violations=0`
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `7 passed`

## 91. The next operated hotspot reduction decomposes `run_local_lab_analysis_bundle.py` into bounded post-review phases

- new code truth:
  - `scripts/run_local_lab_analysis_bundle.py` no longer keeps the full Local IA Lab chain inside one giant `main(...)`
  - the launcher now orchestrates bounded helpers for review dispatch, secondary reviews, edge/proof, release/replay, monitoring, and summary emission
  - function-level guardrail debt on this hotspot is cleared; the remaining explicit debt is only `FILE_TOO_LONG`
- deliberate limit of this slice:
  - no Local IA Lab artifact/schema drift
  - no change to governed review/calibration/replay/monitoring outputs
  - no broad cleanup outside this launcher hotspot
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4286`, `new_violations=0`
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `7 passed`
- `python scripts/run_build9_core_smoke.py`
- Build-1 `PASS`, Build-2..9 `PASS`

## 92. The next operated hotspot reduction removes inline CLI print debt from `run_technical_dashboard.py`

- new code truth:
  - `scripts/run_technical_dashboard.py` now routes terminal output through `_emit_technical_dashboard_output(...)` instead of inline `print()` calls
  - the change preserves the same artifact paths and HTML payload outputs
- deliberate limit of this slice:
  - no dashboard schema change
  - no behavior change in the projection pipeline
  - no cleanup outside this launcher hotspot
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4279`, `new_violations=0`
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `10 passed`

## 93. The next operated hotspot reduction decomposes `_apply_shadow_service_metadata` in `run_technical_dashboard.py`

- new code truth:
  - `scripts/run_technical_dashboard.py` now routes the Shadow service metadata projection through bounded helpers (`_build_shadow_projection_*`)
  - no schema drift; the same `ShadowProjection` fields are populated
- deliberate limit of this slice:
  - no dashboard schema change
  - no behavior change in the projection pipeline
  - no cleanup outside this launcher hotspot
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4278`, `new_violations=0`
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `10 passed`

## 94. The next operated hotspot reduction splits `run_shadow_vps_service.py` into bounded support modules

- new code truth:
  - `scripts/shadow_vps_service_projection_support.py` now houses runtime evidence projection helpers
  - `scripts/shadow_vps_service_campaign_support.py` now houses campaign summary projection helpers
  - `scripts/shadow_vps_service_monitoring_support.py` now houses monitoring artifact helpers and file emission
  - `scripts/run_shadow_vps_service.py` now imports those helpers and adds `scripts/` to `sys.path`
- deliberate limit of this slice:
  - no service-loop semantic change
  - no artifact/schema drift
  - no cleanup outside this hotspot
- latest proofs:
  - `python scripts/run_engineering_guardrails.py`
  - `total_violations=4278`, `new_violations=0`

## 95. The next operated hotspot reduction extracts Shadow VPS service dataclass models

- new code truth:
  - `scripts/shadow_vps_service_models.py` now defines `ShadowVpsServiceMonitoringConfig`, `ShadowVpsServiceRuntimeContext`, and `ShadowVpsCycleSelection`
  - `scripts/run_shadow_vps_service.py` now imports those models
- deliberate limit of this slice:
  - no service-loop semantic change
  - no artifact/schema drift
  - no cleanup outside this hotspot
- latest proofs:
  - `python -m py_compile scripts/run_shadow_vps_service.py scripts/shadow_vps_service_projection_support.py scripts/shadow_vps_service_campaign_support.py scripts/shadow_vps_service_monitoring_support.py scripts/shadow_vps_service_models.py`

## 96. The next operated hotspot reduction extracts Shadow VPS runtime context helpers

- new code truth:
  - `scripts/shadow_vps_service_context_support.py` now hosts runtime dir resolution + context construction helpers
  - `scripts/run_shadow_vps_service.py` now imports those helpers and injects the launcher loader
- deliberate limit of this slice:
  - no service-loop semantic change
  - no artifact/schema drift
  - no cleanup outside this hotspot
- latest proofs:
  - `python -m py_compile scripts/run_shadow_vps_service.py scripts/shadow_vps_service_context_support.py`

## 97. The next operated hotspot reduction extracts Shadow VPS cycle selection helpers

- new code truth:
  - `scripts/shadow_vps_service_cycle_support.py` now hosts cycle selection + idle/prepare helpers
  - `scripts/run_shadow_vps_service.py` now imports those helpers and passes explicit hook callables
- deliberate limit of this slice:
  - no service-loop semantic change
  - no artifact/schema drift
  - no cleanup outside this hotspot
- latest proofs:
  - `python -m py_compile scripts/run_shadow_vps_service.py scripts/shadow_vps_service_cycle_support.py`

## 98. The next operated hotspot reduction extracts Shadow VPS execution helpers

- new code truth:
  - `scripts/shadow_vps_service_execution_support.py` now hosts daily orchestrator, state application, telemetry, success, and failure helpers
  - `scripts/run_shadow_vps_service.py` now imports those helpers and passes explicit hook callables
- deliberate limit of this slice:
  - no service-loop semantic change
  - no artifact/schema drift
  - no cleanup outside this hotspot
- latest proofs:
  - `python -m py_compile scripts/run_shadow_vps_service.py scripts/shadow_vps_service_execution_support.py`

## 99. The next operated hotspot reduction extracts Shadow VPS runtime loop helpers

- new code truth:
  - `scripts/shadow_vps_service_runtime_support.py` now hosts finalize + main loop helpers and output emission
  - `scripts/run_shadow_vps_service.py` now imports those helpers and injects callables
- deliberate limit of this slice:
  - no service-loop semantic change
  - no artifact/schema drift
  - no cleanup outside this hotspot
- latest proofs:
  - `python -m py_compile scripts/run_shadow_vps_service.py scripts/shadow_vps_service_runtime_support.py`
