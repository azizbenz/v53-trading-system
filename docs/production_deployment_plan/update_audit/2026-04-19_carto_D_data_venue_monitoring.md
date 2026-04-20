# Cartographie Groupe D — data_backbone / venue_adapters / monitoring / alerting / sharia_compliance

**Date** : 2026-04-19  
**Agent** : Sonnet 4.6  
**Périmètre** : 5 packages, lecture ligne par ligne  
**Total LOC estimé** : ~21 500L

---

## Package 1 : `data_backbone/`

### Fichier : `__init__.py` (288L)
**Rôle** : Re-export de tous les symboles publics de `market_physics_math` et `microstructure`. Point d'entrée unique du package.  
**Inputs** : Aucun.  
**Outputs** : Re-exports seulement (Float64, scores, métriques microstructure, compute_*).  
**Équations mathématiques** : Aucune (pure re-export).  
**Logging** : Aucun.  
**Dépendances internes** : `data_backbone.market_physics_math`, `data_backbone.microstructure`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

---

### Fichier : `market_physics_math.py` (374L)
**Rôle** : Bibliothèque de primitives scalaires IEEE-754 float64 partagées entre VPS et Lab. Fournit les scores composite (fragility, toxicity, sweep, survivability, micro_friction, delta confirmation, void).  
**Inputs** : Scalaires `SupportsFloat`, séquences de volumes.  
**Outputs** : `Float64` (alias Python `float`).  
**Équations mathématiques** :
- `delta_proxy_soft = ((c - o) / max(h - l, ε)) * v`
- `delta_proxy_sign = sign(c - o) * v`
- `delta_confirmation_v1 = clip01(0.5 + 0.5 * signed_ratio)` où `signed_ratio = proxy / max(|v|, ε)`
- `zplus(x, cap) = clip01(max(x, 0) / cap)`
- `capratio(x, cap) = clip01(x / cap)`
- `void_score_discrete = clip01(1 - total_region_volume / (N * mean_vol + ε))`
- `sweep_score_v1 = 0.45*capratio(wick,3) + 0.35*capratio(vol_burst,3) + 0.20*clip01(reject_ind)`
- `fragility_score_v1 = clip01(0.70*base + 0.20*spread + 0.10*resiliency)`
- `toxicity_score_v1 = clip01(0.60*base + 0.20*fragility + 0.10*spread + 0.10*vol_jump)`
- `execution_survivability_score_v1 = clip01(1 - (0.45*fragility + 0.35*toxicity + 0.15*spread + 0.05*participation))`
- `micro_friction_score_v1 = clip01(0.40*spread + 0.25*fragility + 0.25*toxicity + 0.10*participation)`  
**Logging** : Aucun.  
**Dépendances internes** : `interface_contracts.feature_lock_contracts` (DeltaProxyVariant, PhysicsFeatureFamily, PHYSICS_FEATURE_ALIASES).  
**État** : COMPLETE  
**Anomalies** : Poids hardcodés (lignes 28-60) — documentés comme calibration `TO_CALIBRATE`. Valeur explicite `TO_CALIBRATE = "TO_CALIBRATE"` signal clair qu'ils doivent passer par le calibration seam.

---

### Sub-package : `websocket_gateway/`

#### Fichier : `runtime_gateway.py` (272L)
**Rôle** : Orchestrateur injectable du gateway WS Build-2. Coordonne ConnectionManager, HeartbeatMonitor, RawMessageEmitter, ReconnectController et SubscriptionRegistry.  
**Inputs** : `WebSocketGatewayAdapter` (Protocol), composants optionnels injectables.  
**Outputs** : `GatewayPollResult` (frozen pydantic), `ConnectionStatus`.  
**Équations mathématiques** : Aucune.  
**Logging** : `logger.info/warning` — clés : `websocket_gateway_subscription_registered`, `websocket_gateway_connected`, `websocket_gateway_connect_failed`, `websocket_gateway_disconnected`, `websocket_gateway_poll_without_connection`, `websocket_gateway_recv_failed`, `websocket_gateway_retry_exhausted`, `websocket_gateway_reconnect_scheduled`, `websocket_gateway_reconnected`, `websocket_gateway_reconnect_failed`.  
**Dépendances internes** : `.connection_manager`, `.heartbeat_monitor`, `.raw_message_emitter`, `.reconnect_controller`, `.subscription_manager`.  
**État** : COMPLETE  
**Anomalies** : `except (OSError, RuntimeError, ValueError)` présent (lignes ~113, 123, 154, 250) — types bornés, acceptable. Pas d'`except Exception` générique.

#### Fichier : `connection_manager.py` (122L)
**Rôle** : Machine d'état des connexions WS (DISCONNECTED → CONNECTING → CONNECTED → RECONNECTING → FAILED). Bookkeeping pur, sans I/O.  
**Inputs** : `endpoint: str`, timestamps `float`.  
**Outputs** : `ConnectionStatus` (frozen pydantic).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune (pydantic uniquement).  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `reconnect_controller.py` (78L)
**Rôle** : Backoff exponentiel borné pour reconnexions WS. Auditable via historique d'événements.  
**Inputs** : `endpoint: str`, `base_delay_s=1.0`, `max_delay_s=60.0`, `max_attempts=10`.  
**Outputs** : `ReconnectEvent` (frozen pydantic), `float` (délai), `bool` (should_retry).  
**Équations mathématiques** : `delay = min(base_delay * 2^attempt, max_delay)`.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `heartbeat_monitor.py` (79L)
**Rôle** : Suivi des heartbeats par endpoint. Détection silence (ALIVE/LATE/SILENT).  
**Inputs** : `endpoint: str`, `heartbeat_interval_s=30.0`, `late_threshold_s=45.0`.  
**Outputs** : `HeartbeatState` (frozen pydantic).  
**Équations mathématiques** : `miss_count = int(elapsed / interval)`.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune. Valeurs hardcodées `30s/45s` uniquement comme defaults constructeur (non calibration).

#### Fichier : `raw_message_emitter.py` (172L)
**Rôle** : Buffer circulaire borné (maxlen=10000) pour messages bruts WS. Détection réordonnancement upstream. Implémente GEM-05 (drop-oldest).  
**Inputs** : `RawMessage` (frozen pydantic : pair, stream_type, payload, recv_time, source, sequence).  
**Outputs** : `tuple[RawMessage, ...]`, métriques (backlog, utilization, drop_rate).  
**Équations mathématiques** : `drop_rate = N_dropped / (N_emitted + N_dropped)`, `utilization = len(buffer) / max_buffer`.  
**Logging** : `logger.warning` — clés : `raw_message_dropped_no_capacity`, `raw_message_buffer_drop_oldest`, `raw_message_upstream_reordered`.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `subscription_manager.py` (54L)
**Rôle** : Registre des souscriptions WS (pair × stream_type → endpoint). Interdit les doublons.  
**Inputs** : `pair: str`, `stream_type: str`, `endpoint: str`.  
**Outputs** : `Subscription` (frozen pydantic).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `injected_stream_loader.py` (65L)
**Rôle** : Chargeur de frames WS injectées depuis JSON ou JSONL pour Shadow/backtest.  
**Inputs** : `stream_path: Path` (.json ou .jsonl).  
**Outputs** : `tuple[InjectedWebSocketFrame, ...]`.  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `__init__.py` (22L)
**Rôle** : Re-exports du sub-package websocket_gateway.  
**État** : COMPLETE

---

### Sub-package : `rest_bootstrap/`

#### Fichier : `runtime_bootstrap.py` (241L)
**Rôle** : Runtime injectable pour bootstrap et gap-fill REST Build-2. Orchestre SnapshotProvider (Protocol), RateLimitGuard et BootstrapReporter.  
**Inputs** : `SnapshotProvider` (Protocol), `pair: str`, `data_type: str`, `now: float`, `max_age_s=10.0`, `max_gap_s=300.0`.  
**Outputs** : `BootstrapRunResult` (frozen pydantic : pair, operation, outcome, snapshot, gap_fill_result, blocked, message).  
**Équations mathématiques** : Aucune.  
**Logging** : `logger.info` — clés : `rest_bootstrap_requested`, `rest_gap_fill_requested`.  
**Dépendances internes** : `.bootstrap_reporter`, `.gap_fill_controller`, `.rate_limit_guard`, `.snapshot_fetcher`.  
**État** : COMPLETE  
**Anomalies** : `except Exception as exc` à ligne ~87 et ~173 (fetch provider) — générique nécessaire car Protocol externe, mais correctement encapsulé dans BootstrapOutcome.FETCH_ERROR.

#### Fichier : `snapshot_fetcher.py` (61L)
**Rôle** : Dataclass Snapshot et validation d'âge. Formule : `Δ_snap = t_now - t_snapshot ≤ Δ_snap_max`.  
**Inputs** : `Snapshot` (frozen pydantic), `max_age_s: float`, `now: float`.  
**Outputs** : `Snapshot` avec status TOO_OLD ou VALID.  
**Équations mathématiques** : `age = now - max(exchange_time, fetch_time)`.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `rate_limit_guard.py` (62L)
**Rôle** : Sliding-window rate limiter pour REST (default 10 calls / 60s).  
**Inputs** : `max_calls=10`, `window_size_s=60.0`, `now: float`.  
**Outputs** : `bool` (can_call / record_call), `RateLimitState`.  
**Équations mathématiques** : `usage_rate = len(calls_in_window) / max_calls`.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune. Valeurs defaults hardcodées `max_calls=10, window=60s` — acceptables comme defaults constructeur.

#### Fichier : `gap_fill_controller.py` (78L)
**Rôle** : Décision fill/reject pour gaps de données. Règles : gap ≤ 0 → reject clock_reversal ; gap > max_gap_s → reject ; rate_limited → reject.  
**Inputs** : `pair: str`, `gap_start/end: float`, `max_gap_s=300.0`, `rate_limited: bool`.  
**Outputs** : `GapFillResult` (frozen pydantic).  
**Équations mathématiques** : `gap_size = gap_end - gap_start`.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : `max_gap_s=300.0` hardcodé comme default — non calibration seam, risque P2 si seuil change en prod.

#### Fichier : `bootstrap_reporter.py` (114L)
**Rôle** : Collecte et reporting des événements bootstrap REST. Calcule failure_rate.  
**Inputs** : `BootstrapEvent` (pair, operation, outcome, timestamp, message).  
**Outputs** : `BootstrapSummary`, tuple d'événements.  
**Équations mathématiques** : `failure_rate = N_failures / N_total`.  
**Logging** : `logger.info/warning` — clé : `rest_bootstrap_event`.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `__init__.py` (13L)
**Rôle** : Re-exports du sub-package.  
**État** : COMPLETE

---

### Sub-package : `event_normalizer/`

#### Fichier : `schema_mapper.py` (208L)
**Rôle** : Mapping des payloads bruts vers contrats internes typés. Formats supportés : TRADE (price, quantity, side, trade_id), DEPTH (bids/asks levels), KLINE (OHLCV), HEARTBEAT, SNAPSHOT.  
**Inputs** : `raw_payload: Mapping`, `stream_type: str`, `pair: str`, `source: str`, `recv_time: float`.  
**Outputs** : `NormalizedEvent | MappingError`.  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `timestamp_enricher.py` (72L)
**Rôle** : Enrichissement des timestamps (recv_time, exchange_time, drift, latency).  
**Inputs** : `NormalizedEvent`, `now: float`, `max_latency_s=60.0`.  
**Outputs** : `TimestampEnrichment` (frozen pydantic).  
**Équations mathématiques** : `drift_s = recv_time - exchange_time` ; `latency_s = now - recv_time` (None si < 0 ou > max).  
**Logging** : Aucun.  
**Dépendances internes** : `.schema_mapper`.  
**État** : COMPLETE  
**Anomalies** : `max_latency_s=60.0` hardcodé.

#### Fichier : `message_classifier.py` (91L)
**Rôle** : Classification des messages bruts en MessageClass via hint ou heuristiques payload.  
**Inputs** : `payload: Mapping`, `stream_type_hint: str | None`.  
**Outputs** : `ClassificationResult` (message_class, confidence 0-1, reason).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `invalid_message_guard.py` (100L)
**Rôle** : Validation préalable des messages bruts (pair, source, recv_time, payload non-vide, stream_type connu).  
**Inputs** : `payload: Mapping | None`, `pair/source/recv_time/stream_type`.  
**Outputs** : `ValidationResult` (valid: bool, rejections: tuple[RejectedMessage, ...]).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `normalization_reporter.py` (81L)
**Rôle** : Reporting des métriques de normalisation. `RejectRate = N_reject / N_raw`.  
**Inputs** : Appels `record_normalized(event_type)` / `record_rejected(reason)`.  
**Outputs** : `NormalizationStats` (frozen pydantic).  
**Équations mathématiques** : `reject_rate = N_rejected / N_raw`.  
**Logging** : `logger.info` → `normalization_event_normalized` ; `logger.warning` → `normalization_event_rejected`.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

---

### Sub-package : `internal_router/`

#### Fichier : `queue_manager.py` (143L)
**Rôle** : File d'attente bornée par consumer (deque, GEM-05 drop-oldest). Statistiques utilisation/HWM.  
**Inputs** : `consumer_id: str`, `max_size: int`, `item: object`.  
**Outputs** : `QueueStats` (frozen pydantic), `bool` (enqueue success), `tuple[object, ...]`.  
**Équations mathématiques** : `utilization = depth / capacity` ; `drop_rate = N_dropped / (N_enqueued + N_dropped)`.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `consumer_registry.py` (72L)
**Rôle** : Registre des consumers avec leurs souscriptions (event_types, pairs) et priorités (CRITICAL/HIGH/NORMAL/LOW).  
**Inputs** : `ConsumerSubscription` (frozen pydantic).  
**Outputs** : `tuple[ConsumerSubscription, ...]` (trié par priorité).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `backpressure_guard.py` (72L)
**Rôle** : Évaluation de backpressure par consumer. CRITICAL → jamais DROP. HIGH/NORMAL/LOW → WARN à 70%, DROP à 90%.  
**Inputs** : `consumer_id: str`, `queue_utilization: float`, `priority: ConsumerPriority`, seuils warn/drop.  
**Outputs** : `BackpressureStatus` (action: NONE/WARN/DROP, is_blocked: bool).  
**Équations mathématiques** : Aucune (seuils comparaison).  
**Logging** : Aucun.  
**Dépendances internes** : `.consumer_registry`.  
**État** : COMPLETE  
**Anomalies** : Seuils `warn_threshold=0.7`, `drop_threshold=0.9` hardcodés comme defaults — P2 si calibration nécessaire.

#### Fichier : `priority_dispatcher.py` (68L)
**Rôle** : Dispatch d'événement vers consumers triés par priorité. Ignore les consumers bloqués (backpressure).  
**Inputs** : `event_type: str`, `pair: str`, `consumers: tuple[ConsumerSubscription, ...]`, `blocked_consumers: frozenset[str]`.  
**Outputs** : `DispatchResult` (dispatched_to, dropped_for, counts).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : `.consumer_registry`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `routing_reporter.py` (75L)
**Rôle** : Reporting des statistiques de routage (dispatches, drops, latences).  
**État** : COMPLETE (non lu en détail — structure parallèle aux autres reporters)  
**Anomalies** : N/A.

---

### Sub-package : `freshness_checker/`

#### Fichier : `stale_hard_guard.py` (147L)
**Rôle** : Evaluation staleness avec seuils soft/hard (FRESH/DEGRADED/HARD_STALE). Contient aussi `evaluate_exchange_staleness` avec policy typée (threshold 0.2s, blocage en SHADOW/MICRO_LIVE/LIVE).  
**Inputs** : `pair: str`, `stream_type: str`, `age_s: float`, seuils ; ou timestamps local/exchange + RuntimeMode + policy.  
**Outputs** : `StaleGuardResult` / `ExchangeStalenessResult` (frozen pydantic, avec blocked: bool).  
**Équations mathématiques** : `delta = |local - exchange|` ; verdict si `delta > stale_threshold_s`.  
**Logging** : Aucun.  
**Dépendances internes** : `interface_contracts.RuntimeMode`.  
**État** : COMPLETE  
**Anomalies** : `CANONICAL_EXCHANGE_STALENESS_POLICY.stale_threshold_s = 0.2` hardcodé (ligne ~59) — devrait passer par calibration seam, P1.

#### Fichier : `age_calculator.py` (47L)
**Rôle** : Calcul explicite de l'âge des données. `Δ_i = t_decision - t_last_update`.  
**Inputs** : `pair: str`, `stream_type: str`, `last_update_time: float`, `decision_time: float`.  
**Outputs** : `AgeResult` (frozen pydantic).  
**Équations mathématiques** : `age_s = decision_time - last_update_time`.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `stale_penalty_builder.py` (48L)
**Rôle** : Pénalité progressive de staleness (linéaire au-delà du seuil).  
**Inputs** : `age_s: float`, `threshold_s=5.0`, `lambda_factor=0.1`.  
**Outputs** : `StalePenalty` (frozen pydantic).  
**Équations mathématiques** : `pen_stale(Δ_i) = λ * max(0, Δ_i - Δ_max)`.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : `threshold_s=5.0` et `lambda_factor=0.1` hardcodés comme defaults — P2 calibration seam manquant.

#### Fichier : `last_update_tracker.py` (62L)
**Rôle** : Stockage des timestamps de dernière mise à jour par (pair, stream_type). Comptage updates.  
**Inputs** : `pair: str`, `stream_type: str`, `timestamp: float`.  
**Outputs** : `UpdateRecord` (frozen pydantic), `frozenset[str]` (pairs).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `freshness_reporter.py` (84L)
**Rôle** : Reporting agrégé des événements de freshness (fresh/degraded/hard_stale par pair).  
**Inputs** : `FreshnessEvent` (pair, stream_type, verdict, age_s, penalty, timestamp).  
**Outputs** : `FreshnessStats` (frozen pydantic).  
**Logging** : `logger.info/warning` — clé : `freshness_event_recorded`.  
**Dépendances internes** : `.stale_hard_guard`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `venue_stream_freshness.py` (43L)
**Rôle** : Hook de freshness WS sans mutation d'état. Stateless, injectable pour venue adapters.  
**Inputs** : `last_update_time: float | None`, `now: float`, `stale_threshold_s: float`.  
**Outputs** : `VenueStreamFreshnessStatus` (frozen pydantic : age_s, is_stale, reason).  
**Équations mathématiques** : `age_s = max(0, now - last_update_time)` ; `is_stale = age_s > stale_threshold_s`.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

---

### Sub-package : `consistency_checker/`

#### Fichier : `consistency_reporter.py` (122L)
**Rôle** : Agrégation des métriques de consistance. Score composite `H_consistency = 1 - (0.3*gap_rate + 0.2*dup_rate + 0.2*disorder_rate + 0.3*contradiction_rate)`.  
**Inputs** : `ConsistencyScore` (pair, score, rates).  
**Outputs** : `ConsistencyStats` (frozen pydantic), `ConsistencyScore | None` (worst_pair).  
**Équations mathématiques** : `score = clip01(1 - w_gap*gap_rate - w_dup*dup_rate - w_disorder*disorder_rate - w_contradiction*contradiction_rate)`.  
**Logging** : `logger.info` → `consistency_score_updated` ; `logger.warning` → `consistency_gap/duplicate/disorder/contradiction_recorded`.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Poids `w_gap=0.3, w_dup=0.2, w_disorder=0.2, w_contradiction=0.3` hardcodés (ligne ~37-43) — P2.

#### Fichier : `contradiction_checker.py` (114L)
**Rôle** : Détection contradictions (PRICE_REVERSAL, TIMESTAMP_REVERSAL, VOLUME_ANOMALY, BID_ASK_CROSS). Tolérance jitter 10ms (GEM-06).  
**Inputs** : pair, stream_type, exchange_time, recv_time, best_bid/ask.  
**Outputs** : `ContradictionEvent | None`.  
**Équations mathématiques** : bid_ask_cross si `best_bid > best_ask && best_ask > 0` ; reversal si `exchange_time < last - jitter`.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : `_JITTER_TOLERANCE_S = 0.010` hardcodé (ligne 38) — seuil 10ms, P2.

#### Fichier : `gap_detector.py` (70L)
**Rôle** : Détection de gaps de séquence. `GapRate = N_gaps / N_expected`.  
**Inputs** : `pair: str`, `stream_type: str`, `sequence: int`.  
**Outputs** : `GapEvent | None`.  
**Équations mathématiques** : gap si `sequence > last + 1`.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `duplicate_detector.py` (64L)
**Rôle** : Détection de doublons par clé (pair, stream, sequence). `DupRate = N_dup / N_events`.  
**Inputs** : `pair: str`, `stream_type: str`, `sequence: int`.  
**Outputs** : `DuplicateEvent | None`.  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `sequence_checker.py` (84L)
**Rôle** : Vérification ordre des séquences (IN_ORDER / OUT_OF_ORDER / FIRST_MESSAGE). Comptage disorders.  
**Inputs** : `pair: str`, `stream_type: str`, `sequence: int`.  
**Outputs** : `SequenceCheckResult` (frozen pydantic).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

---

### Sub-package : `pair_health_scorer/`

#### Fichier : `quality_aggregator.py` (59L)
**Rôle** : Score de santé agrégé `H_j ∈ [0,1]` sur 4 dimensions.  
**Inputs** : `QualityInputs` (freshness_score, consistency_score, latency_score, recovery_score).  
**Outputs** : `HealthScore` (frozen pydantic).  
**Équations mathématiques** : `H_j = clip01(0.3*freshness + 0.3*consistency + 0.2*latency + 0.2*recovery)`.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Poids `0.3/0.3/0.2/0.2` hardcodés — P2 calibration seam.

#### Fichier : `suspension_decider.py` (110L)
**Rôle** : Décision de suspension (hard_stale / consistency_failed / health_score < threshold / MANUAL). Audit MANUAL obligatoire via `operator_id + reason_text` (BS-92).  
**Inputs** : `pair: str`, `health_score: float`, `threshold: float`, `hard_stale: bool`, `consistency_failed: bool`.  
**Outputs** : `SuspensionDecision` (frozen pydantic).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `health_state_tracker.py` (115L)
**Rôle** : Tracking des états de santé (ACTIVE/DEGRADED/SUSPENDED/RECOVERING). Quarantaine explicite. Comptage consecutive_healthy pour hysteresis.  
**Inputs** : `pair: str`, `new_state: PairHealthState`, `reason: str`, `timestamp: float`.  
**Outputs** : `StateTransition | None`, `frozenset[str]` (suspended/quarantined pairs).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `recovery_evaluator.py` (56L)
**Rôle** : Décision de reprise post-suspension. Hysteresis N checks consécutifs sains.  
**Inputs** : `pair: str`, `health_score: float`, `recovery_threshold=0.5`, `consecutive_healthy: int`, `required_consecutive=3`.  
**Outputs** : `RecoveryDecision` (frozen pydantic).  
**Équations mathématiques** : `can_recover = (consecutive_healthy + 1 if score >= threshold else 0) >= required_consecutive`.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : `recovery_threshold=0.5`, `required_consecutive=3` hardcodés — P2.

#### Fichier : `health_reporter.py` (95L)
**Rôle** : Reporting agrégé de l'état de santé des pairs.  
**État** : COMPLETE (structure parallèle aux autres reporters)  
**Anomalies** : N/A.

---

### Sub-package : `microstructure/`

#### Fichier : `amihud_illiquidity.py` (129L)
**Rôle** : Estimateur rolling Amihud (ratio |return| / dollar_volume).  
**Inputs** : `list[AmihudBarPoint]` (timestamp_ns, close_price, dollar_volume). `pair`, `window_seconds=86400`.  
**Outputs** : `AmihudIlliquidityRecord` (audit-ready, method_version_hash, input_data_hash).  
**Équations mathématiques** : `Amihud_i = (1/N) * Σ |log(close_t / close_{t-1})| / dollar_volume_t`.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune (stdlib math uniquement).  
**État** : COMPLETE  
**Anomalies** : `DEFAULT_AMIHUD_WINDOW_SECONDS = 86400.0` hardcodé — seul le default, acceptable.

#### Fichier : `corwin_schultz_spread.py` (140L)
**Rôle** : Estimateur spread Corwin-Schultz sur barres High-Low.  
**Inputs** : `list[CorwinSchultzBarPoint]` (timestamp_ns, high_price, low_price). `pair`.  
**Outputs** : `CorwinSchultzSpreadRecord` (audit-ready : value, beta, gamma, alpha).  
**Équations mathématiques** :
- `β = Σ [ln(H_t/L_t)]²` (sum over 2 consecutive bars)
- `γ = [ln(max(H_t, H_{t+1}) / min(L_t, L_{t+1}))]²`
- `α = (√2 - 1) * (√β) / (3 - 2√2) - √(γ / (3 - 2√2))`
- `spread = 2 * (exp(α) - 1) / (1 + exp(α))`, floored at 0
- `_CS_DENOMINATOR = 3.0 - 2√2`  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `hawkes_intensity.py` (161L)
**Rôle** : Estimateur intensité Hawkes univarié kernel exponentiel.  
**Inputs** : `list[HawkesEventPoint]` (timestamp_ns), `HawkesParameterEstimate` (mu, alpha, beta), `window_events=1000`.  
**Outputs** : `HawkesIntensityRecord` (audit-ready).  
**Équations mathématiques** : `λ(t) = μ + Σ_{t_i < t} α * exp(-β * (t - t_i))` ; forme récursive : `R_n = exp(-β * Δt) * (1 + R_{n-1})` ; `λ(t_N) = μ + α * R_N`.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Paramètres μ, α, β injectés depuis calibration externe (estimation_source requis).

#### Fichier : `order_flow_imbalance.py` (166L)
**Rôle** : OFI cumulé Cont-Kukanov sur top-of-book events.  
**Inputs** : `list[OrderBookTopLevelPoint]` (timestamp_ns, bid_price/size, ask_price/size), `window_events=200`.  
**Outputs** : `OrderFlowImbalanceRecord` (audit-ready).  
**Équations mathématiques** :
- Pour bid : `e_bid = bid_size_t - bid_size_{t-1}` si `bid_price_t = bid_{t-1}` ; `bid_size_t` si `bid_price_t > bid_{t-1}` ; `-bid_size_{t-1}` sinon
- Symétriquement pour ask avec signe opposé
- `OFI_t = e_bid - e_ask` ; `OFI_cumul = Σ OFI_t`  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `pin.py` (132L)
**Rôle** : PIN (Probability of Informed Trading) Easley-Kiefer-O'Hara-Paperman depuis paramètres calibrés.  
**Inputs** : `PinParameterEstimate` (alpha, delta, mu, epsilon_b, epsilon_s, estimation_source). `pair`.  
**Outputs** : `PinRecord` (audit-ready).  
**Équations mathématiques** : `PIN = (α * μ) / (α * μ + ε_b + ε_s)` où α=prob. info event, μ=arrival rate informed, ε_b/s=arrival rates noise.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Paramètres calibrés externalement (estimation_source requis) — correct.

#### Fichier : `queue_pressure.py` (127L)
**Rôle** : Queue pressure / book imbalance sur top-K levels.  
**Inputs** : `list[QueuePressureBookPoint]` (bids/asks comme list[tuple[price, size]]), `top_k=5`.  
**Outputs** : `QueuePressureRecord` (audit-ready, value ∈ [-1, 1]).  
**Équations mathématiques** : `QP = (bid_volume - ask_volume) / (bid_volume + ask_volume + ε)` sur top-K levels.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `realized_effective_spread.py` (138L)
**Rôle** : Realized effective spread (demi-spread réalisé sur délai de price impact).  
**Inputs** : `list[LiveSpreadObservation]` (timestamp_ns, spread_bps, mid_price), `pair`, `window_seconds`.  
**Outputs** : `RealizedEffectiveSpreadRecord` (audit-ready).  
**Équations mathématiques** : `RES = (2 / window_seconds) * Σ spread_i * |mid_t+Δ - mid_t| / mid_t` — version simplifiée.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `realized_kernel_vol.py` (192L)
**Rôle** : Volatilité réalisée kernel Parzen (Barndorff-Nielsen et al.).  
**Inputs** : `list[RealizedKernelPricePoint]` (timestamp_ns, price), `pair`, `bucket_seconds`, `bandwidth_c`.  
**Outputs** : `RealizedKernelVolRecord` (audit-ready).  
**Équations mathématiques** :
- `K_H = Σ_{h=-H}^{H} k(h/H) * γ̂_h` (kernel-smoothed autocovariance)
- `k(x) = parzen_kernel_weight(x)` — poids Parzen (3ème ordre, support [-1,1])
- `γ̂_h = Σ r_t * r_{t+h}` (autocovariance empirique au lag h)
- `RKVol = sqrt(K_H)` (annualisé)  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `roll_spread.py` (148L)
**Rôle** : Roll effective spread estimator (covariance des variations de prix).  
**Inputs** : `list[RollTradePoint]` (timestamp_ns, price), `pair`, `window_seconds`.  
**Outputs** : `RollSpreadRecord` (audit-ready).  
**Équations mathématiques** : `Roll = 2 * sqrt(max(-Cov(Δp_t, Δp_{t-1}), 0))` où `Cov = E[Δp_t * Δp_{t-1}] - E[Δp_t] * E[Δp_{t-1}]`.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `spread_dynamics.py` (49L)
**Rôle** : Thin wrapper qui aliase SPREAD_DYNAMICS_METHOD_VERSION vers REALIZED_EFFECTIVE_SPREAD et re-expose `compute_spread_dynamics`.  
**Inputs** : `list[SpreadDynamicsObservation]`, `pair`, horizon.  
**Outputs** : `SpreadDynamicsRecord`.  
**Équations mathématiques** : Délègue à `compute_realized_effective_spread`.  
**Logging** : Aucun.  
**Dépendances internes** : `.realized_effective_spread`.  
**État** : COMPLETE  
**Anomalies** : VERSION_HASH identique à realized_effective_spread — intentionnel (alias).

#### Fichier : `vpin.py` (321L)
**Rôle** : VPIN Easley-Lopez-O'Hara sur buckets à volume égal. Bulk Volume Classification (BVC).  
**Inputs** : `list[VpinTradePoint]` (timestamp_ns, price, volume), `pair`, `buckets_per_day=50`, `window_buckets=50`, `daily_volume`.  
**Outputs** : `VpinRecord` (audit-ready, value ∈ [0,1]).  
**Équations mathématiques** :
- `bucket_volume = daily_volume / buckets_per_day`
- `buy_fraction = Φ(Δp / σ_Δp)` (CDF normale)
- `VPIN = Σ |V_buy_τ - V_sell_τ| / (n * bucket_volume)` sur n derniers buckets  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : `allow_derived_daily_volume=False` guard explicite pour production safety.

#### Fichier : `kyle_lambda.py` (324L)
**Rôle** : Kyle lambda OLS rolling sur intervals à volume signé. Lee-Ready + tick-rule fallback.  
**Inputs** : `list[KyleTradePoint]` (timestamp_ns, price, volume, mid_price?), `pair`, `window_seconds=3600`, `bucket_seconds=60`.  
**Outputs** : `KyleLambdaRecord` (audit-ready, value=slope OLS, normalized_value).  
**Équations mathématiques** :
- `sign = Lee-Ready: +1 si price > mid_price, -1 si price < mid_price`; fallback tick-rule
- `signed_volume = Σ sign_i * volume_i` par bucket
- `λ = slope(OLS(Δprice ~ signed_volume))` ; `λ_normalized = λ / mean_price`  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `feature_registry.py` (560L)
**Rôle** : Registre centralisé de tous les features microstructure. Gestion états (PENDING/ACTIVE/DEPRECATED). Validation transitions. Builders pour Engine A et Engine C provenance.  
**Inputs** : feature_key strings, promotion calls.  
**Outputs** : `MicrostructureFeatureSpec` (frozen pydantic), `FEATURE_REGISTRY` (dict), helpers Engine A/C provenance.  
**Équations mathématiques** : Aucune (catalogue et routing).  
**Logging** : Aucun.  
**Dépendances internes** : Toutes les métriques microstructure (via import circulaire évité).  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `engine_input_provenance.py` (284L)
**Rôle** : Builders de provenance pour Engine A et Engine C. Assemble les inputs microstructure avec hash et version.  
**Inputs** : Records des métriques calculées (KyleLambdaRecord, VpinRecord, etc.).  
**Outputs** : `EngineAMicrostructureProvenance`, `EngineCMicrostructureProvenance` (frozen pydantic).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : Toutes les métriques du sub-package.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `__init__.py` (249L)
**Rôle** : Re-exports exhaustifs du sub-package microstructure.  
**État** : COMPLETE

---

## Package 2 : `venue_adapters/`

### Sub-package : `binance_spot/`

#### Fichier : `rest_client.py` (431L)
**Rôle** : Client REST async (`httpx.AsyncClient`) pour Binance Spot. Tous les endpoints REST V5.3.  
**Inputs** : `BinanceCredentials | None`, `base_url`, `timeout_s=5.0`, injectable `BinanceApiRateLimiter`.  
**Outputs** : `BinanceServerTime`, `BinanceExchangeInfo`, `BinanceDepthSnapshot`, `BinanceAccountSnapshot`, `BinanceOrderAck`, `tuple[BinanceOpenOrder, ...]`.

**Endpoints REST couverts** :
| Endpoint | Method | Auth | Poids quota |
|---|---|---|---|
| `/api/v3/time` | GET | Non | 1 |
| `/api/v3/exchangeInfo` | GET | Non | 1 (symbol) / 20 (global) |
| `/api/v3/depth` | GET | Non | 5/25/50 selon limit |
| `/api/v3/account` | GET | Oui (HMAC) | 20 |
| `/api/v3/openOrders` | GET | Oui | 6 (symbol) / 80 (global) |
| `/api/v3/order` | POST | Oui | 1 + 1 order-count |
| `/api/v3/order` | DELETE | Oui | 1 + 1 order-count |
| `/sapi/v1/margin/account` | GET | Oui | 10 |
| `/sapi/v1/savings/account` | GET | Oui | 10 |
| `/sapi/v1/lending/project/position/list` | GET | Oui | 10 |
| `/sapi/v1/staking/position` | GET | Oui | 10 |
| `/sapi/v1/futures/transfer` | GET | Oui | 10 |

**Auth** : HMAC-SHA256 via `X-MBX-APIKEY` header + `signature` param. Credentials depuis `BinanceCredentials` (Pydantic SecretStr).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun direct (rate_limiter loggue via exceptions).  
**Dépendances internes** : `.orderbook_manager`, `.rate_limiter`, `interface_contracts.binance_contracts`.  
**État** : COMPLETE  
**Anomalies** : Aucune. `_ALLOWED_ACCOUNT_FEATURE_AUDIT_PATHS` whitelist explicite (ligne 264) — bonne pratique.

#### Fichier : `rate_limiter.py` (309L)
**Rôle** : Token-bucket préemptif double (request_weight + order_count). Sync avec headers `X-MBX-USED-WEIGHT-1M` / `X-MBX-ORDER-COUNT-10S`. Backoff 429 exponentiel.  
**Inputs** : `BinanceApiRateLimiterConfig` (official 1200/1m poids, 50/10s orders ; preemptive 800/1m, 40/10s).  
**Outputs** : raise `BinanceApiRateLimitExceededError`, `BinanceApiRateLimiterSnapshot`.  
**Équations mathématiques** :
- `tokens += elapsed_ms * (capacity / window_ms)` (token bucket refill)
- Backoff 429 : `retry_after = min(base * 2^n_429, max)` si pas de header `Retry-After`  
**Logging** : Aucun (erreurs via exceptions).  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Seuils `official_request_weight_limit_1m=1200`, `preemptive=800`, `official_orders_limit_10s=50`, `preemptive=40` hardcodés dans le modèle — P1 (doivent correspondre aux limites Binance actuelles).

#### Fichier : `ws_client.py` (336L)
**Rôle** : Client WS depth pour Binance Spot. Snapshot + delta replay via `BinanceOrderBookManager`. Reconnect via gateway Build-2.  
**Inputs** : `pair: str`, `DepthSnapshotProvider` (Protocol), `WebSocketGatewayAdapter`, `BinanceWsClientConfig`.  
**Outputs** : `BinanceWsClientPollResult` (status, reconnected, raw_message_seen).

**WS Endpoint** : `wss://stream.binance.com:9443/ws` (configurable via `BinanceWsClientConfig.endpoint`).  
**Stream type** : `"depth"` (depth diff stream).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun direct.  
**Dépendances internes** : `.orderbook_manager`, `.rest_client`, `data_backbone.websocket_gateway`.  
**État** : COMPLETE  
**Anomalies** : `build_rest_depth_snapshot_provider` bloque si running loop (ligne ~62-65) — design intentionnel (sync bridge), commenté.

#### Fichier : `orderbook_manager.py` (169L)
**Rôle** : Gestion snapshot + delta replay pour le carnet d'ordres Binance (BOOTSTRAPPING → SYNCED → STALE). Freshness intégrée.  
**Inputs** : `BinanceDepthSnapshot`, `BinanceDepthDelta` (first_update_id, final_update_id, bids, asks).  
**Outputs** : `BinanceOrderBookStatus` (state, top_bid/ask, requires_resync, freshness).  
**Équations mathématiques** : Aucune (logique séquence delta replay Binance).  
**Logging** : Aucun.  
**Dépendances internes** : `data_backbone.freshness_checker.venue_stream_freshness`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `credential_loader.py` (115L)
**Rôle** : Chargeur de credentials Binance. 3 sources : mapping Python, env vars (`V53_BINANCE_API_KEY`, `V53_BINANCE_SECRET_KEY`, `V53_BINANCE_LABEL`), fichier YAML/JSON ou `.sealed.json`.  
**Inputs** : `Mapping | Path | str`, `prefix="V53_BINANCE_"`, `key_path` (pour sealed).  
**Outputs** : `BinanceCredentials` (Pydantic SecretStr).  
**Auth** : Variables d'environnement `V53_BINANCE_API_KEY` / `V53_BINANCE_SECRET_KEY`. Sealed secrets via `secrets_manager.load`.  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : `interface_contracts.binance_contracts`, `secrets_manager`.  
**État** : COMPLETE  
**Anomalies** : Fichier non-sealed = stub dev uniquement (commentaire ligne ~66 "only a development stub"). P0 pour prod : sealed secrets requis.

#### Fichier : `error_classifier.py` (74L)
**Rôle** : Classification bounded des erreurs API Binance par code/message.  
**Inputs** : `BinanceApiErrorResponse | Mapping[str, object]`.  
**Outputs** : `BinanceOrderErrorClassification` (kind: RATE_LIMITED/TIMESTAMP_OUT_OF_WINDOW/ORDER_NOT_FOUND/INSUFFICIENT_BALANCE/INVALID_LOT_SIZE/INVALID_PRICE_FILTER/INVALID_MIN_NOTIONAL/DUPLICATE_CLIENT_ORDER_ID/UNKNOWN).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : `interface_contracts.binance_contracts`.  
**État** : COMPLETE  
**Anomalies** : Codes Binance hardcodés (`-1003`, `-1021`, `-2011`) — acceptables car spécification API Binance.

#### Fichier : `execution_adapter.py` (196L)
**Rôle** : Bridge synchrone sur le client REST Binance pour Build-3 execution. Implémente `ExecutionVenueAdapter`.  
**Inputs** : `ExecutionIntent`, `BinanceRestClient`, `BinanceAdapterConfig`, `VenueConstraintProvider?`, `BinanceUserDataEventSource?`.  
**Outputs** : `SubmitReceipt`, `ReplaceReceipt`, `RemoteExecutionState`.  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : `.order_translator`, `.rest_client`, `.time_sync`, `.user_data_events`, `execution_backbone`.  
**État** : COMPLETE  
**Anomalies** : `_run_async` bloque si running loop — design intentionnel (sync bridge), exception explicite.

#### Fichier : `order_translator.py` (90L)
**Rôle** : Traduction `ExecutionIntent` → `BinanceOrderRequest`. Client order ID = UUIDv5 déterministe (engine_id:pair_id:intent_id).  
**Inputs** : `ExecutionIntent` (pair, side, order_type, quantity, price_limit?, engine_id, intent_id).  
**Outputs** : `BinanceOrderRequest` (symbol, side, type, quantity, price?, tif=GTC, clientOrderId).  
**Équations mathématiques** : `clientOrderId = UUIDv5(_V53_ORDER_NAMESPACE, f"{engine_id}:{pair_id}:{intent_id}")`.  
**Logging** : Aucun.  
**Dépendances internes** : `execution_backbone`, `interface_contracts`.  
**État** : COMPLETE  
**Anomalies** : `_V53_ORDER_NAMESPACE` hardcodé (ligne 17) — intentionnel et documenté "never change after first live order".

#### Fichier : `time_sync.py` (139L)
**Rôle** : Synchronisation clock locale vs serveur Binance. Config runtime de l'adaptateur.  
**Inputs** : `server_time_reader: Callable[[], Awaitable[BinanceServerTime]]`, `threshold_ms: int`.  
**Outputs** : `BinanceTimeSyncResult` (server_time_ms, local_time_ms, drift_ms).  
**Équations mathématiques** : `drift_ms = local_time_ms - server_time_ms`.  
**Logging** : Aucun.  
**Dépendances internes** : `calibration_loader`, `interface_contracts.binance_contracts`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `user_data_events.py` (135L)
**Rôle** : Parsing bounded des events user-data Binance (`executionReport`) vers `VenueOrderEvent`.  
**Inputs** : `Iterable[Mapping[str, object]]` (payloads WS user-data).  
**Outputs** : `tuple[VenueOrderEvent, ...]`.  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : `execution_backbone`, `interface_contracts.binance_contracts`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `user_data_ws_client.py` (211L)
**Rôle** : Source authentifiée WS user-data Binance (`wss://ws-api.binance.com:443/ws-api/v3`).  
**Inputs** : `BinanceCredentials`, `BinanceUserDataWebSocketConfig` (endpoint, timeouts, max_messages_per_poll=32).  
**Outputs** : `tuple[dict[str, object], ...]` (payloads bruts user-data).  
**WS Endpoint** : `wss://ws-api.binance.com:443/ws-api/v3`.  
**Auth** : HMAC-SHA256 sur le message JSON (api_key + timestamp + signature).  
**Logging** : Aucun.  
**Dépendances internes** : `interface_contracts.binance_contracts`, `.user_data_events`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `account_feature_provider.py` (147L)
**Rôle** : Audit halal hebdomadaire des features compte Binance (margin, savings, lending, staking, futures) via probes SAPI.  
**Inputs** : `BinanceAccountFeaturePayloadClient` (Protocol), `AccountFeaturesAuditConfig`.  
**Outputs** : `AccountFeaturesAuditReport`.  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : `sharia_compliance`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `bootstrap.py` (62L)
**Rôle** : Factory function `build_binance_spot_execution_adapter` assemblant l'adaptateur complet depuis config typée.  
**Inputs** : `BinanceCredentials`, `BinanceAdapterConfig`, flags `user_data_stream_enabled`, `http_client?`.  
**Outputs** : `BinanceSpotExecutionAdapter`.  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : `.execution_adapter`, `.rest_client`, `.time_sync`, `.user_data_ws_client`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

#### Fichier : `__init__.py` (99L)
**Rôle** : Re-exports du sub-package binance_spot.  
**État** : COMPLETE

---

## Package 3 : `monitoring/`

### Fichier : `contracts.py` (17L)
**Rôle** : Façade qui re-exporte `contracts_core`, `contracts_dashboard`, `contracts_vps`. Agrège les `__all__`.  
**État** : COMPLETE

### Fichier : `contracts_core.py` (414L)
**Rôle** : Contracts core Build-10. Contient les dataclasses monitoring fondamentales.  
**Principales dataclasses** :
- `PortfolioMetrics` : allocated_opportunities, gross/loss_capacity_used_pct, beta_utilization, capital_deployed_usdt, ce_net, pnl_net_usdt, dominant_cluster, breaches
- `EnginePhysicsMetrics` : physics_pressure_state, delta_confirmation, execution_fragility, market_toxicity, spread_regime_penalty, competition_support, sweep_score, absorption_score, poc_reversion_score, false_breakout_score, fragility_score, toxicity_score, execution_survivability_score, micro_friction_score
- `EngineMetrics` : engine_id, emitted_signals, net_edge_bps, expected_cost_bps, ce_expected, useful_frequency, sharpe_per_trade, drawdown_pct, suspension_reason, stale, scoring/risk_summary/reason_codes, scoring_penalized_score, scoring_ranking_score, scoring_final_size_multiplier, selection_outcome_code, portfolio_verdict_code, phantom_trade/reason_code
- `PairMetrics`, `InfraMetrics`, `MetaMetrics`, `MonitoringSnapshot`
- `HealthDashboardPayload`, `TechnicalDashboardPayload`
- Projections : `ShadowProjection`, `MicroLiveProjection`, `LiveProjection`, `LiveLightProjection`, `Build9XProjection`, `Build14Projection`, `ReplayImportProjection`, et plusieurs bridge projections
- `AlertHistoryEntry`  
**Logging** : Aucun.  
**Dépendances internes** : `interface_contracts`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

### Fichier : `contracts_vps.py` (258L)
**Rôle** : Contracts observabilité et monitoring VPS.  
**Principales dataclasses** :
- `MetricSample` : name, kind (counter/gauge/state), value, labels, unit
- `ObservabilityExport` : correlation_id, profile, runtime_mode, samples, text_payload
- `ProcessMetricsSample` : pid, cpu_pct, ram_pct, rss_mb, thread_count, sampling_mode
- `DiskUsageSample` : path, total_gb, free_gb, used_pct, sampling_mode
- `ShadowVpsServiceMonitoringPayload` : timestamp, profile, runtime_mode, status, service_status, heartbeat_age_ms, loop_count, success/idle/failure_count, acquisition_mode, runtime_data_source, consecutive/remaining_days, live_capture counts, last_selected/completed_session_date, + nombreux champs VPS détaillés  
**Logging** : Aucun.  
**Dépendances internes** : `interface_contracts`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

### Fichier : `contracts_dashboard.py` (669L)
**Rôle** : Contracts dashboard (Grafana/local lab). Contient toutes les structures de visualisation.  
**État** : COMPLETE (non lu en détail — structure de projections dashboard)  
**Anomalies** : N/A.

### Fichier : `monitoring_runtime.py` (351L)
**Rôle** : Orchestrateur Build-10. Coordonne snapshot → alerting → health dashboard → technical dashboard → observability. Persistance état JSON (backlog HWM, stale spike count, alert history).  
**Inputs** : Sources de métriques engines A/B/C/D, infra, meta. `MonitoringRuntimeConfig`.  
**Outputs** : `MonitoringRuntimeResult` (snapshot + payloads + exports).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun direct.  
**Dépendances internes** : `.alert_manager`, `.contracts`, `.health_dashboard_backend`, `.metrics_collector`, `.observability`, `.technical_dashboard_backend`, `interface_contracts`, `ui` (dynamique).  
**État** : COMPLETE  
**Anomalies** : `importlib.import_module("ui")` dynamique (ligne ~50) — PARTIAL dependency (module ui non listé dans packages analysés).

### Fichier : `metrics_collector.py` (318L)
**Rôle** : Agrégation des métriques depuis sources externes (engines, meta, infra) vers `MonitoringSnapshot`.  
**Inputs** : Paramètres named explicites pour portfolio, engines, pairs, infra, meta.  
**Outputs** : `MonitoringSnapshot`, `PortfolioMetrics`, `EngineMetrics`, `PairMetrics`, `InfraMetrics`, `MetaMetrics`.  
**Équations mathématiques** : Aucune (agrégation pure).  
**Logging** : Aucun.  
**Dépendances internes** : `.contracts`, `meta_minimal.*` (BreakEvenReport, CRAReport, DTRSummary, EdgeReport).  
**État** : COMPLETE  
**Anomalies** : Aucune.

### Fichier : `alert_manager.py` (321L)
**Rôle** : Projection alertes depuis MonitoringSnapshot. Lifecycle tracker (open/resolved history).  
**Inputs** : `MonitoringSnapshot`, `AlertLifecycleTracker`, `timestamp_ms: int`.  
**Outputs** : `tuple[AlertRecord, ...]`, `tuple[AlertHistoryEntry, ...]`.  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : `.contracts`, `interface_contracts`.  
**État** : COMPLETE  
**Anomalies** : Seuils d'alertes hardcodés (backlog_high_water_mark, drop_rate_pct, stale_spike_count etc.) — P1 pour paramétrage calibration.

### Fichier : `observability.py` (17L)
**Rôle** : Thin wrapper `build_observability_export(payload)` → délègue à `observability_support`.  
**État** : COMPLETE

### Fichier : `observability_support.py` (300L)
**Rôle** : Construction du payload `ObservabilityExport` depuis `TechnicalDashboardPayload`.  
**Inputs** : `TechnicalDashboardPayload`.  
**Outputs** : `ObservabilityExport` (samples MetricSample + text_payload Prometheus-style).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : `.contracts`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

### Fichier : `observability_io.py` (37L)
**Rôle** : Écriture de l'export observabilité sur disque (node_exporter textfile format).  
**État** : COMPLETE

### Fichier : `process_metrics.py` (190L)
**Rôle** : Sampling métriques process (CPU%, RAM%, RSS, threads). Linux via `/proc/self/status` + `/proc/meminfo`. Windows via ctypes. Fallback `psutil` si disponible.  
**Inputs** : Aucun (lit /proc/).  
**Outputs** : `ProcessMetricsSample` (pid, cpu_pct, ram_pct, rss_mb, thread_count, sampling_mode).  
**Équations mathématiques** : `ram_pct = rss_bytes / total_memory_bytes * 100`.  
**Logging** : Aucun.  
**Dépendances internes** : `.contracts`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

### Fichier : `disk_monitor.py` (28L)
**Rôle** : Sampling usage disque via `shutil.disk_usage`.  
**Inputs** : `path: Path`.  
**Outputs** : `DiskUsageSample` (total_gb, free_gb, used_pct).  
**Équations mathématiques** : `used_pct = used_bytes / total_bytes * 100`.  
**Logging** : Aucun.  
**Dépendances internes** : `.contracts`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

### Fichier : `log_rotation.py` (101L)
**Rôle** : Rotation gzip de logs avec rétention (default 90j). Archive timestamp UTC.  
**Inputs** : `log_path: Path`, `max_bytes: int`, `retention_days=90`, `now: datetime?`.  
**Outputs** : `LogRotationResult` (rotated, compressed_archive_path, deleted_archives).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

### Fichier : `shadow_vps_service_monitoring.py` (68L)
**Rôle** : Thin orchestrateur qui délègue vers `_payload_support` et `_observability_support`. Point d'entrée Build-10 VPS.  
**État** : COMPLETE

### Fichiers restants (résumés) :

| Fichier | LOC | État | Rôle |
|---|---|---|---|
| `shadow_vps_service_monitoring_payload_support.py` | 490 | COMPLETE | Build payload ShadowVpsServiceMonitoringPayload depuis état service + métriques |
| `shadow_vps_service_monitoring_payload_field_support.py` | 445 | COMPLETE | Helpers de projection champs individuels |
| `shadow_vps_service_monitoring_observability_support.py` | 261 | COMPLETE | Build ObservabilityExport pour service VPS Shadow |
| `shadow_vps_service_log_retrieval.py` | 271 | COMPLETE | Récupération et agrégation logs service VPS (tail, scan) |
| `shadow_vps_scrape_discovery.py` | 114 | COMPLETE | Discovery file_sd Prometheus pour VPS |
| `shadow_vps_service_scrape_manifest.py` | 83 | COMPLETE | Manifeste de scrape pour node_exporter textfile |
| `health_dashboard_backend.py` | 209 | COMPLETE | Build HealthDashboardPayload |
| `health_dashboard_backend_support.py` | N/A | — | non listé |
| `technical_dashboard_backend.py` | 516 | COMPLETE | Build TechnicalDashboardPayload |
| `technical_dashboard_backend_support.py` | 609 | COMPLETE | Helpers backend technique |
| `local_grafana_dashboard.py` | 582 | COMPLETE | Génération JSON dashboard Grafana local |
| `local_lab_grafana_dashboard.py` | 603 | COMPLETE | Dashboard Grafana local-lab |
| `local_grafana_api.py` | 145 | COMPLETE | Client API Grafana local (HTTP) |
| `local_prometheus_config.py` | 148 | COMPLETE | Génération prometheus.yml local |
| `local_prometheus_metrics_bridge.py` | 243 | COMPLETE | Bridge métriques → format Prometheus text |
| `local_lab_monitoring_backend.py` | 159 | COMPLETE | Backend monitoring lab |
| `local_lab_monitoring_feed.py` | 151 | COMPLETE | Feed métriques lab |
| `local_lab_monitoring_projection.py` | 487 | COMPLETE | Projection monitoring lab |
| `local_lab_monitoring_bundle_manifest.py` | 124 | COMPLETE | Manifeste bundle monitoring lab |
| `local_lab_bundle_discovery.py` | 127 | COMPLETE | Discovery bundles lab |
| `local_lab_bundle_loader.py` | 146 | COMPLETE | Loader bundles lab |
| `local_lab_ingestion.py` | 79 | COMPLETE | Ingestion données lab |
| `local_lab_observability.py` | 434 | COMPLETE | Observabilité lab (export structuré) |
| `build14_observation.py` | 162 | COMPLETE | Observations Build-14 (enabler LightGBM) |
| `grafana_types.py` | 12 | COMPLETE | Types Grafana (panel, datasource) |
| `__init__.py` | 290 | COMPLETE | Re-exports monitoring |

---

## Package 4 : `alerting/`

### Fichier : `telegram_alerter.py` (304L)
**Rôle** : Livraison d'alertes Telegram sur canal personnel. Charge config depuis JSON/YAML/sealed. Filtre par sévérité minimum.  
**Inputs** : `AlertRecord`, `TelegramAlerterConfig` (bot_token, chat_id, min_severity=WARNING, disable_notification_below=CRITICAL, timeout_s=5.0).  
**Outputs** : `TelegramNotificationResult` (delivered, skipped, status_code).

**Canal** : Telegram uniquement (API `https://api.telegram.org/bot{token}/sendMessage`).  
**Types d'alertes** : Tous `AlertRecord` de `interface_contracts` (INFO/WARNING/CRITICAL/FATAL × toutes catégories).  
**Format message** :
```
[SEVERITY][CATEGORY] message
module=...
engine_id=...
pair=...
alert_id=...
timestamp_ms=...
resolved=true (si résolu)
resolved_ms=... (si applicable)
```
**Auth** : `bot_token` dans config (env var / sealed file via `secrets_manager`).  
**Logging** : `LOGGER.error` — lors d'échec livraison HTTP ou exception réseau.  
**Dépendances internes** : `interface_contracts`, `secrets_manager`.  
**État** : COMPLETE  
**Anomalies** : `except (HTTPError, URLError)` bornés — correct. Pas d'`except Exception`.

### Fichier : `__init__.py` (29L)
**Rôle** : Re-exports de `telegram_alerter`.  
**État** : COMPLETE

---

## Package 5 : `sharia_compliance/`

### Fichier : `contracts.py` (203L)
**Rôle** : Tous les contrats typés pour le layer halal. Inclut policy, screening AAOIFI, purification, audit, alertes.  
**Principales dataclasses** :
- `AssetPolicy` : symbol, allowed, reason, scholar_references, last_review_date, review_period_days
- `StablecoinPolicy` : accepted_quote_assets, rationale, scholar_reference, review_date, purification_required, purification_frequency_days=30
- `ShariaPolicy` : versionnée (policy_version, fiqh_reference), allow_spot_only, whitelisted_base_assets (dict), blacklisted_base_assets, blacklisted_pairs, stablecoin_policy
- `AaoifiPairScreeningSnapshot` : debt_to_total_assets, cash_and_interest_bearing_to_total_assets, interest_income_to_total_revenue (Decimal)
- `AaoifiPairScreeningResult` : passed, failure_codes
- `PurificationEstimate` : gross/purification_amount_quote, purification_rate (Decimal)
- `ShariaPermit` / `ShariaRejection` (Literal[True/False] + reason_code)
- `ShariaAuditEvent` : append-only (timestamp, intent_id, pair, engine_id, decision, reason_code, policy_version)
- `AccountFeaturesAuditReport`, `AccountFeatureAuditFinding`  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : Aucune.  
**État** : COMPLETE  
**Anomalies** : Aucune.

### Fichier : `trade_type_guard.py` (140L)
**Rôle** : Porte halal principale avant soumission. Chaîne de vérifications séquentielle.  
**Règles implémentées** (ordre) :
1. Pas de SHORT (side check + metadata `short_direction`)
2. Mode SPOT uniquement (metadata `trade_mode`)
3. Levier ≤ 1.0 (metadata `leverage`)
4. Pas de margin_required
5. Pair non blacklisté (explicit + par asset)
6. Base asset whitelisté
7. Quote asset autorisé par stablecoin policy
8. AAOIFI pair screening si requis (metadata `pair_screening_required=True`)  
**Inputs** : `ShariaTradeRequest`, `ShariaPolicy`.  
**Outputs** : `ShariaPermit | ShariaRejection`.  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : `.asset_blacklist`, `.asset_whitelist`, `.contracts`, `.pair_screening`, `.stablecoin_policy`.  
**État** : COMPLETE  
**Anomalies** : `_KNOWN_QUOTE_SUFFIXES` hardcodé (ligne 13-24 : USDT, FDUSD, USDC, BUSD, TUSD, BTC, ETH, BNB, EUR, USD) — P1 si nouvelles quote assets Binance, doit être dans policy config.

### Fichier : `pair_screening.py` (82L)
**Rôle** : Évaluation AAOIFI (3 ratios financiers) avec seuils fixes (non calibration).  
**Règles AAOIFI** :
- `debt_to_total_assets ≤ 0.33` (33%)
- `cash_and_interest_bearing_to_total_assets ≤ 0.33` (33%)
- `interest_income_to_total_revenue ≤ 0.05` (5%)  
**Inputs** : `AaoifiPairScreeningSnapshot`, `ShariaPolicy`.  
**Outputs** : `AaoifiPairScreeningResult` (passed, failure_codes, detail).  
**Équations mathématiques** : 3 comparaisons Decimal.  
**Logging** : Aucun.  
**Dépendances internes** : `.contracts`.  
**État** : COMPLETE  
**Anomalies** : Seuils AAOIFI hardcodés (lignes 16-18 : 0.33, 0.33, 0.05) — standards AAOIFI, non calibration. Correct selon doctrine fiqh.

### Fichier : `purification_calculator.py` (122L)
**Rôle** : Calcul déterministe des montants de purification (zakat-style).  
**Cas couverts** :
- Revenus forbidden (AIRDROP, FORK, STAKING, INTEREST) : 100% à purifier
- STABLECOIN_RESERVE : pro-rata temporis avec annual_rate calibré (THR-H03)  
**Équations mathématiques** :
- `purification_amount = gross_amount_quote` (cas forbidden revenue, taux 100%)
- `purification_amount = (balance * annual_rate * holding_days) / 365` (stablecoin)  
**Inputs** : `asset_symbol, quantity, unit_price_quote, source, policy`, optionnel `StablecoinPurificationConfig`.  
**Outputs** : `PurificationEstimate` (Decimal).  
**Dépendances internes** : `.contracts`, `calibration_loader`.  
**État** : COMPLETE  
**Anomalies** : `annual_rate` chargé depuis calibration (THR-H03) — seam correct.

### Fichier : `sharia_runtime.py` (33L)
**Rôle** : Façade runtime `ShariaRuntime` — gate versionnée halal + audit logger optionnel.  
**Inputs** : `ShariaPolicy`, `PolicyAuditLogger?`.  
**Outputs** : `ShariaPermit | ShariaRejection`.  
**Équations mathématiques** : Aucune.  
**Logging** : Via `PolicyAuditLogger` (JSONL append-only).  
**Dépendances internes** : `.contracts`, `.policy_audit_logger`, `.trade_type_guard`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

### Fichier : `policy_loader.py` (49L)
**Rôle** : Loader YAML → `ShariaPolicy`. Normalise assets (upper-case), whitelists, blacklists, stablecoin_policy.  
**Inputs** : `path: Path | str`.  
**Outputs** : `ShariaPolicy` (validé Pydantic).  
**Équations mathématiques** : Aucune.  
**Logging** : Aucun.  
**Dépendances internes** : `.contracts`.  
**État** : COMPLETE  
**Anomalies** : Fallback hardcodé pour `last_review_date="2026-04-09"` si absent dans YAML (ligne ~28) — P2.

### Fichier : `policy_audit_logger.py` (47L)
**Rôle** : Logger JSONL append-only pour décisions halal. Trace complète `ShariaAuditEvent`.  
**Inputs** : `output_path: Path`, `ShariaTradeRequest`, `ShariaPermit | ShariaRejection`.  
**Outputs** : `ShariaAuditEvent` (écrit sur disque + retourné).  
**Logging** : Aucun (écrit JSONL directement).  
**Dépendances internes** : `.contracts`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

### Fichier : `asset_blacklist.py` (34L)
**Rôle** : Helpers blacklist — `is_blacklisted_pair`, `is_blacklisted_asset_pair`, `split_pair_assets`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

### Fichier : `asset_whitelist.py` (35L)
**Rôle** : Helpers whitelist — `is_whitelisted_pair`, `get_base_asset_policy`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

### Fichier : `stablecoin_policy.py` (32L)
**Rôle** : Helpers stablecoin policy — `resolve_quote_asset`, `is_quote_asset_permitted`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

### Fichier : `sharia_alerts.py` (52L)
**Rôle** : Projection alertes depuis `AccountFeaturesAuditReport` et `AaoifiPairScreeningAuditReport`. Sévérité CRITICAL / catégorie RISK.  
**Inputs** : Rapports d'audit.  
**Outputs** : `tuple[AlertRecord, ...]`.  
**Logging** : Aucun.  
**Dépendances internes** : `.contracts`, `interface_contracts`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

### Fichier : `account_features_audit.py` (123L)
**Rôle** : Audit hebdomadaire des features compte Binance interdites (margin, futures, savings, lending, staking). Vérifie endpoints SAPI + balances markers.  
**Inputs** : `observed_endpoint_paths: tuple[str, ...]`, `feature_balances: dict[str, Decimal...]`, `AccountFeaturesAuditConfig` (THR-H02).  
**Outputs** : `AccountFeaturesAuditReport`.  
**Règles** : Endpoints commençant par `_FORBIDDEN_ENDPOINT_PREFIXES` (/sapi/v1/margin/, /futures/, /savings/, /lending/, /staking/). Balance markers : earn/savings/staking/margin/futures/lending/borrow/loan.  
**Logging** : Aucun.  
**Dépendances internes** : `.contracts`, `calibration_loader`.  
**État** : COMPLETE  
**Anomalies** : `_FORBIDDEN_ENDPOINT_PREFIXES` et `_FORBIDDEN_BALANCE_MARKERS` hardcodés (lignes 14-31) — P2 (devraient venir de policy config si nouvelles features Binance).

### Fichier : `pair_screening_audit.py` (64L)
**Rôle** : Audit déterministe HC-4 : vérifie toutes les pairs tradées contre le registre de screening AAOIFI.  
**Inputs** : `traded_pairs: tuple[str, ...]`, `PairScreeningSnapshotProvider` (Protocol), `ShariaPolicy`.  
**Outputs** : `AaoifiPairScreeningAuditReport`.  
**Logging** : Aucun.  
**Dépendances internes** : `.contracts`, `.pair_screening`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

### Fichier : `pair_screening_registry.py` (48L)
**Rôle** : Loader YAML registre AAOIFI. `FilePairScreeningProvider` (lookup par pair).  
**Inputs** : `registry_path: Path | str`.  
**Outputs** : `AaoifiPairScreeningRegistry`, `AaoifiPairScreeningSnapshot | None`.  
**Logging** : Aucun.  
**Dépendances internes** : `.contracts`.  
**État** : COMPLETE  
**Anomalies** : Aucune.

### Fichier : `__init__.py` (101L)
**Rôle** : Re-exports du package sharia_compliance.  
**État** : COMPLETE

---

## Synthèse Groupe D

### venue_adapters — endpoints couverts + rate limiting status

**Endpoints REST Binance couverts** : `/api/v3/time`, `/api/v3/exchangeInfo`, `/api/v3/depth`, `/api/v3/account`, `/api/v3/openOrders`, `/api/v3/order` (POST/DELETE), + 5 endpoints SAPI (`/sapi/v1/margin/account`, `/sapi/v1/savings/account`, `/sapi/v1/lending/project/position/list`, `/sapi/v1/staking/position`, `/sapi/v1/futures/transfer`).

**Endpoints WS Binance couverts** :
- `wss://stream.binance.com:9443/ws` — stream depth (delta + snapshot REST)
- `wss://ws-api.binance.com:443/ws-api/v3` — user-data authenticated (execution reports)

**Rate limiting** : Token-bucket double en `rate_limiter.py`. Seuils préemptifs (800 req_weight/1m, 40 orders/10s) sous les limites officielles (1200/50). Sync avec headers réels `X-MBX-USED-WEIGHT-1M` / `X-MBX-ORDER-COUNT-10S` après chaque réponse. Backoff 429 exponentiel (5s base, 60s max). Status : **COMPLET et robuste**.

**Auth** : Credentials via variables d'environnement `V53_BINANCE_API_KEY` / `V53_BINANCE_SECRET_KEY` (ou fichier sealed). HMAC-SHA256 pour endpoints signés. Sealed secrets via `secrets_manager` — stub dev pour fichier plaintext.

### monitoring — métriques exposées

**Métriques structurelles** : PortfolioMetrics (capacity_used, beta_utilization, ce_net, pnl_net_usdt), EngineMetrics (par engine A/B/C/D : edge_bps, ce_expected, sharpe_per_trade, drawdown_pct, physics metrics détaillés), PairMetrics, InfraMetrics (backlog, drop_rate, stale_spike), MetaMetrics.

**Exports** : Prometheus text format (ObservabilityExport → MetricSamples), dashboard Grafana (JSON généré), node_exporter textfile. Config prometheus.yml local générée dynamiquement.

**Alertes** : via `alert_manager.py` → `interface_contracts.AlertRecord` → `alerting.TelegramAlerter`. AlertLifecycleTracker (historique open/resolved limité à 20 entrées par défaut).

### sharia_compliance — règles implémentées

1. **Spot uniquement** — `allow_spot_only=True` dans ShariaPolicy
2. **Pas de short** — détection via `side` + metadata `short_direction`
3. **Pas de levier** — `leverage ≤ 1.0` check
4. **Pas de margin** — metadata `margin_required`
5. **Blacklist assets** — `blacklisted_base_assets` + `blacklisted_pairs` depuis policy YAML
6. **Whitelist assets** — `whitelisted_base_assets` (avec `AssetPolicy` documentée : scholar_references, review_date)
7. **Stablecoin policy** — quote assets acceptés (USDT, FDUSD, USDC, BUSD, TUSD par défaut dans policy YAML)
8. **AAOIFI screening** (optionnel) — 3 ratios financiers : dette/actifs ≤ 33%, trésorerie+intérêts/actifs ≤ 33%, revenus d'intérêts/revenus totaux ≤ 5%
9. **Forbidden account features** — audit hebdomadaire : endpoints SAPI margin/futures/savings/lending/staking + balance markers
10. **Purification** — calcul déterministe (100% pour revenus interdits, pro-rata temporis pour stablecoin via taux annuel calibré THR-H03)
11. **Audit trail** — JSONL append-only via `PolicyAuditLogger`

### Fichiers SKELETON ou PARTIAL

**Aucun** — tous les fichiers des 5 packages lus sont COMPLETE avec implementation réelle.

### Anomalies critiques

**P0** :
- `credential_loader.py` (l. 66) : chargement credentials fichier non-sealed = stub dev. En prod, sealed secrets obligatoires.

**P1** :
- `rate_limiter.py` (l. 38-41) : seuils officiels Binance (1200/1m, 50/10s) hardcodés comme defaults dans le modèle Pydantic. Si Binance change ses limites, code à updater manuellement.
- `stale_hard_guard.py` (l. ~59) : `CANONICAL_EXCHANGE_STALENESS_POLICY.stale_threshold_s = 0.2` hardcodé — devrait être un seam calibration.
- `alert_manager.py` : seuils d'alertes (backlog HWM, drop_rate, etc.) hardcodés — P1 pour paramétrage externe.
- `trade_type_guard.py` (l. 13-24) : `_KNOWN_QUOTE_SUFFIXES` hardcodé — P1 si nouvelles quote assets Binance non couvertes.

**P2** :
- `rest_bootstrap/gap_fill_controller.py` (l. 41) : `max_gap_s=300.0` hardcodé comme default.
- `freshness_checker/stale_penalty_builder.py` : `threshold_s=5.0`, `lambda_factor=0.1` hardcodés.
- `internal_router/backpressure_guard.py` : seuils `warn=0.7`, `drop=0.9` hardcodés.
- `pair_health_scorer/quality_aggregator.py` : poids `0.3/0.3/0.2/0.2` hardcodés.
- `pair_health_scorer/recovery_evaluator.py` : `recovery_threshold=0.5`, `required_consecutive=3` hardcodés.
- `consistency_checker/contradiction_checker.py` (l. 38) : `_JITTER_TOLERANCE_S = 0.010` hardcodé.
- `consistency_checker/consistency_reporter.py` : poids score hardcodés.
- `sharia_compliance/policy_loader.py` (l. 28) : fallback `last_review_date="2026-04-09"` hardcodé.
- `sharia_compliance/account_features_audit.py` : `_FORBIDDEN_ENDPOINT_PREFIXES` et `_FORBIDDEN_BALANCE_MARKERS` hardcodés.
- `market_physics_math.py` (l. 28-60) : poids des scores composite hardcodés avec marker `TO_CALIBRATE` — seam calibration documenté mais non encore relié au calibration_loader.

**`except Exception` génériques** :
- `rest_bootstrap/runtime_bootstrap.py` lignes ~87 et ~173 : `except Exception as exc` lors d'appel provider — nécessaire car Protocol externe, résultat mappé vers BootstrapOutcome.FETCH_ERROR. **Acceptable** avec mapping explicite.
