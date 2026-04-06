# V5.3 — LOCAL AI LAB FINAL IMPLEMENTATION BLUEPRINT
## Filesystem, APIs, Pydantic contracts, DB tables, build order
### Version développeur finale détaillée
### Date : 2026-04-04
### Statut : IMPLEMENTATION BLUEPRINT

---

# 0. Objet

Ce document transforme le canon final du **Local AI Lab + VPS Runtime** en plan de développement directement exploitable.

Il répond à cinq questions :

1. **où mettre les fichiers**
2. **quelles APIs exposer**
3. **quels contrats Pydantic écrire**
4. **quelles tables DB créer**
5. **dans quel ordre exact coder**

Ce document ne remplace pas le canon final.  
Il le convertit en plan d’implémentation.

---

# 1. Décisions technologiques finales

## 1.1 Langage et style

- Python 3.11+
- Pydantic v2
- FastAPI pour les APIs
- SQLAlchemy 2.x + Alembic
- PostgreSQL pour VPS / control plane
- Parquet + DuckDB pour le Lab local
- `httpx` pour clients API
- `orjson` pour sérialisation rapide
- `pyarrow` pour Parquet
- `scikit-learn`, `xgboost`, `lightgbm`, `catboost` pour le Lab
- `numpy`, `pandas`, `scipy` pour maths et validation
- `cryptography` ou `pynacl` pour Ed25519

## 1.2 Ce qu’on n’utilise pas en V1

- pas de Kubernetes
- pas de Kafka
- pas de vector DB dans la boucle critique
- pas de ONNX export en runtime
- pas de code Python injecté
- pas de Redis obligatoire
- pas de service gRPC obligatoire
- pas de mem0 comme backend de logs

## 1.3 Choix architecture V1

### Local
- stockage datasets : Parquet partitionné
- analytics rapides : DuckDB
- registry local : SQLite possible ou simple PostgreSQL local si souhaité
- batch jobs : scripts Python + CLI orchestrée

### VPS
- PostgreSQL obligatoire
- FastAPI service pour gouvernance / monitoring / batch import
- agent léger par VPS
- logs techniques en fichiers structurés + DB index minimal
- closed-loop export batch en Parquet zippé

### Control Plane
- FastAPI
- PostgreSQL
- agrégation par polling d’agents
- UI plus tard ; backend d’abord

---

# 2. Topologie code finale

## 2.1 Répertoire racine recommandé

```text
v53_trading_system/
├── docs/
│   ├── specs/
│   ├── canon/
│   ├── api/
│   ├── schemas/
│   └── runbooks/
├── src/
│   ├── interface_contracts/
│   ├── manifest_registry/
│   ├── dag_validator/
│   ├── data_backbone/
│   ├── execution_backbone/
│   ├── risk_backbone/
│   ├── scoring_backbone/
│   ├── engines/
│   │   ├── engine_a/
│   │   ├── engine_b/
│   │   ├── engine_c/
│   │   └── engine_d/
│   ├── portfolio_minimal/
│   ├── meta_learning/
│   ├── local_replay_runtime/
│   ├── backtest_artifact_import/
│   ├── monitoring/
│   ├── protocols/
│   ├── complete_enablers/
│   ├── local_ai_lab/
│   ├── vps_governance/
│   ├── vps_agent/
│   ├── control_plane/
│   ├── storage/
│   └── common/
├── tests/
├── scripts/
├── migrations/
├── configs/
├── datasets/
├── artifacts/
└── logs/
```

---

# 3. Arborescence détaillée du Local AI Lab

## 3.1 Package `src/local_ai_lab/`

```text
src/local_ai_lab/
├── __init__.py
├── enums.py
├── errors.py
├── settings.py
├── cli.py
│
├── dataset_registry/
│   ├── __init__.py
│   ├── contracts.py
│   ├── models.py
│   ├── repository.py
│   ├── registry_service.py
│   └── integrity_checker.py
│
├── data_acquisition/
│   ├── __init__.py
│   ├── contracts.py
│   ├── exchange_downloader.py
│   ├── local_folder_loader.py
│   ├── parquet_partition_writer.py
│   └── normalization_pipeline.py
│
├── feature_lock/
│   ├── __init__.py
│   ├── feature_dictionary.py
│   ├── transform_whitelist.py
│   ├── feature_lineage_validator.py
│   └── transform_lineage_validator.py
│
├── feature_factory/
│   ├── __init__.py
│   ├── contracts.py
│   ├── base_feature_builder.py
│   ├── physics_feature_builder.py
│   ├── window_aggregator.py
│   ├── label_builder.py
│   └── cached_feature_store.py
│
├── diagnostic_engine/
│   ├── __init__.py
│   ├── contracts.py
│   ├── dtr_reader.py
│   ├── outcome_classifier.py
│   ├── reason_code_clusterer.py
│   ├── failure_pattern_ranker.py
│   └── hypothesis_generator.py
│
├── threshold_calibrator/
│   ├── __init__.py
│   ├── contracts.py
│   ├── calibration_runner.py
│   ├── coarse_to_fine_search.py
│   ├── walk_forward_evaluator.py
│   └── threshold_report_builder.py
│
├── micro_model_lab/
│   ├── __init__.py
│   ├── contracts.py
│   ├── dataset_builder.py
│   ├── feature_budget_guard.py
│   ├── trainer_xgboost.py
│   ├── trainer_lightgbm.py
│   ├── trainer_catboost.py
│   ├── model_selection.py
│   ├── stability_evaluator.py
│   └── importance_reporter.py
│
├── distillation/
│   ├── __init__.py
│   ├── contracts.py
│   ├── rule_distiller.py
│   ├── threshold_json_builder.py
│   ├── lookup_json_builder.py
│   ├── action_unit_validator.py
│   ├── rule_complexity_guard.py
│   └── reason_code_mapper.py
│
├── causal_validation/
│   ├── __init__.py
│   ├── contracts.py
│   ├── ablation_runner.py
│   ├── anti_cowardice_test.py
│   ├── friction_regret_test.py
│   ├── regime_segmentation_test.py
│   ├── walk_forward_test.py
│   ├── operational_burden_test.py
│   ├── capital_efficiency_test.py
│   └── validation_verdict_builder.py
│
├── artifact_packer/
│   ├── __init__.py
│   ├── contracts.py
│   ├── artifact_bundle_builder.py
│   ├── signature_service.py
│   ├── payload_hasher.py
│   ├── bundle_exporter.py
│   └── manifest_exporter.py
│
├── closed_loop/
│   ├── __init__.py
│   ├── contracts.py
│   ├── batch_fetch_client.py
│   ├── batch_parquet_reader.py
│   ├── reality_joiner.py
│   ├── drift_feedback_builder.py
│   └── retrain_dataset_builder.py
│
└── reporting/
    ├── __init__.py
    ├── report_models.py
    ├── markdown_reporter.py
    ├── json_reporter.py
    └── human_summary_formatter.py
```

---

# 4. Arborescence détaillée VPS Governance

## 4.1 Package `src/vps_governance/`

```text
src/vps_governance/
├── __init__.py
├── settings.py
├── enums.py
├── errors.py
│
├── api/
│   ├── __init__.py
│   ├── app.py
│   ├── deps.py
│   ├── auth.py
│   ├── artifact_routes.py
│   ├── batch_routes.py
│   ├── status_routes.py
│   ├── log_routes.py
│   └── admin_routes.py
│
├── contracts/
│   ├── __init__.py
│   ├── artifact_contracts.py
│   ├── lifecycle_contracts.py
│   ├── batch_contracts.py
│   ├── telemetry_contracts.py
│   ├── hook_contracts.py
│   └── api_contracts.py
│
├── services/
│   ├── __init__.py
│   ├── artifact_schema_validator.py
│   ├── signature_verifier.py
│   ├── artifact_registry_service.py
│   ├── lifecycle_manager.py
│   ├── ttl_manager.py
│   ├── regime_distance_service.py
│   ├── circuit_breaker_service.py
│   ├── hook_injector_service.py
│   ├── artifact_status_projection.py
│   └── import_audit_logger.py
│
├── repository/
│   ├── __init__.py
│   ├── db.py
│   ├── artifact_repository.py
│   ├── lifecycle_repository.py
│   ├── regime_repository.py
│   ├── batch_repository.py
│   └── log_query_repository.py
│
└── runtime_hooks/
    ├── __init__.py
    ├── engine_a_hooks.py
    ├── engine_b_hooks.py
    ├── engine_c_hooks.py
    ├── engine_d_hooks.py
    ├── scoring_hooks.py
    ├── risk_hooks.py
    ├── portfolio_hooks.py
    └── execution_hooks.py
```

---

# 5. Arborescence détaillée agent VPS

## 5.1 Package `src/vps_agent/`

```text
src/vps_agent/
├── __init__.py
├── settings.py
├── enums.py
├── agent_main.py
├── heartbeat_publisher.py
├── host_health_collector.py
├── runtime_health_collector.py
├── artifact_status_collector.py
├── log_batch_builder.py
├── closed_loop_batch_builder.py
├── batch_export_scheduler.py
└── api_client.py
```

---

# 6. Arborescence détaillée Control Plane

## 6.1 Package `src/control_plane/`

```text
src/control_plane/
├── __init__.py
├── settings.py
├── enums.py
│
├── api/
│   ├── app.py
│   ├── vps_routes.py
│   ├── artifact_routes.py
│   ├── alert_routes.py
│   ├── health_routes.py
│   └── log_query_routes.py
│
├── services/
│   ├── vps_registry_service.py
│   ├── fleet_health_service.py
│   ├── artifact_board_service.py
│   ├── alert_aggregation_service.py
│   ├── runtime_status_service.py
│   └── log_query_federator.py
│
├── repository/
│   ├── db.py
│   ├── vps_repository.py
│   ├── fleet_snapshot_repository.py
│   ├── artifact_projection_repository.py
│   └── alert_repository.py
│
└── polling/
    ├── agent_poller.py
    ├── schedule_runner.py
    └── status_refresher.py
```

---

# 7. APIs — vue d’ensemble

## 7.1 APIs nécessaires

### Local AI Lab -> VPS Governance
- upload artifact
- query artifact status
- fetch lifecycle state
- fetch closed-loop batches
- fetch logs ciblés

### VPS Agent -> Control Plane
- heartbeat
- host health snapshot
- runtime health snapshot
- artifact state snapshot
- alert push ou poll

### Control Plane -> VPS Governance / Agent
- aggregated status queries
- log queries
- artifact fleet queries
- lifecycle fleet queries

---

# 8. Endpoints API détaillés

## 8.1 Local AI Lab -> VPS Governance

### POST `/api/v1/artifacts/upload`
Upload d’un artifact signé.

### GET `/api/v1/artifacts/{artifact_id}`
Récupérer le détail d’un artifact.

### GET `/api/v1/artifacts/{artifact_id}/lifecycle`
Récupérer l’état de cycle de vie.

### POST `/api/v1/artifacts/{artifact_id}/validate-dry-run`
Validation sans activation.

### GET `/api/v1/closed-loop/batches`
Lister les batches disponibles.

### POST `/api/v1/closed-loop/fetch`
Télécharger un batch fermé.

### POST `/api/v1/logs/query`
Requête ciblée de logs.

### GET `/api/v1/runtime/status`
État du runtime local de la VPS.

---

## 8.2 VPS Agent -> Control Plane

### POST `/api/v1/agents/heartbeat`
Heartbeat agent.

### POST `/api/v1/agents/{vps_id}/host-health`
CPU, RAM, disque, uptime.

### POST `/api/v1/agents/{vps_id}/runtime-health`
Websocket, backlog, stale, runtime mode, alertes.

### POST `/api/v1/agents/{vps_id}/artifact-status`
Projection des artifacts actifs.

### POST `/api/v1/agents/{vps_id}/alerts`
Push d’alertes critiques.

---

## 8.3 Control Plane -> vue opérateur

### GET `/api/v1/fleet/overview`
Vue flotte.

### GET `/api/v1/fleet/vps`
Liste VPS + statuts.

### GET `/api/v1/fleet/artifacts`
Vue artifacts sur flotte.

### GET `/api/v1/fleet/alerts`
Alertes agrégées.

### POST `/api/v1/fleet/logs/query`
Requête fédérée de logs sur plusieurs VPS.

---

# 9. Contrats Pydantic — Local AI Lab

## 9.1 Dataset registry

```python
class DatasetRegistrationRequest(BaseModel):
    dataset_id: str
    source_type: Literal["DOWNLOADED", "LOCAL_FOLDER", "MIXED"]
    pair_ids: list[str]
    base_timeframe: Literal["1m"]
    start_date: date
    end_date: date
    storage_path: str
    file_format: Literal["PARQUET"]
    schema_version: str
    integrity_hash_sha256: str
```

```python
class DatasetRegistrationRecord(BaseModel):
    dataset_id: str
    status: Literal["REGISTERED", "VALIDATED", "INVALID"]
    row_count: int
    pair_count: int
    created_at: datetime
```

## 9.2 Feature lineage

```python
class FeatureLineageRecord(BaseModel):
    feature_id: str
    source_module: str
    source_reader: str
    equation_id: str
    transform_chain: list[str]
    window_policy: str
    normalization_version: str
    is_allowed: bool
```

## 9.3 Micro-model training request

```python
class MicroModelTrainingRequest(BaseModel):
    experiment_id: str
    artifact_class: Literal[
        "EDGE_ADDER",
        "DAMAGE_REDUCER",
        "EXEC_SURVIVABILITY_FILTER",
        "CAPITAL_EFFICIENCY_ENHANCER",
    ]
    target_hook_id: str
    dataset_id: str
    pair_ids: list[str]
    train_start: date
    train_end: date
    validation_start: date
    validation_end: date
    allowed_feature_ids: list[str]
    max_input_features: int
    max_conditions_per_rule: int
    objective: Literal["CLASSIFICATION", "RANKING", "REGRESSION"]
    model_family: Literal["XGBOOST", "LIGHTGBM", "CATBOOST"]
```

## 9.4 Distilled rule contract

```python
class DistilledRuleCondition(BaseModel):
    condition_id: str
    feature_id: str
    operator: Literal[">", ">=", "<", "<=", "==", "IN_RANGE"]
    threshold: float | None = None
    lower_threshold: float | None = None
    upper_threshold: float | None = None
```

```python
class DistilledRuleAction(BaseModel):
    action: Literal[
        "SOFT_BOOST",
        "SOFT_REDUCE",
        "NO_TRADE",
        "SIZE_REDUCE",
        "RANK_ADJUST",
        "TIMEOUT_ADJUST",
    ]
    action_value: float
    action_unit: Literal[
        "RAW_SCORE_MULTIPLIER",
        "RAW_SCORE_ADD",
        "CONVICTION_ADD",
        "SIZE_FACTOR",
        "RANK_DELTA",
        "TIMEOUT_FACTOR",
    ]
    max_raw_score_cap: float | None = None
    min_floor: float | None = None
    reason_code: str
```

```python
class DistilledRule(BaseModel):
    rule_id: str
    logical_op: Literal["AND", "OR"]
    conditions: list[DistilledRuleCondition]
    action: DistilledRuleAction
    support_count: int
    fragility_score: float
```

## 9.5 Proof summary

```python
class ArtifactProofSummary(BaseModel):
    anti_cowardice_pass: bool
    friction_regret_pass: bool
    walk_forward_pass: bool
    regime_segmentation_pass: bool
    operational_burden_pass: bool
    capital_efficiency_pass: bool | None = None
    ablation_delta_net_pnl: float
    ablation_delta_ce: float | None = None
    friction_regret_value: float
    block_rate_delta: float
```

## 9.6 Artifact export bundle

```python
class ArtifactExportBundle(BaseModel):
    artifact_id: str
    artifact_version: str
    artifact_class: Literal[
        "EDGE_ADDER",
        "DAMAGE_REDUCER",
        "EXEC_SURVIVABILITY_FILTER",
        "CAPITAL_EFFICIENCY_ENHANCER",
    ]
    artifact_scope: str
    allowed_hook_ids: list[str]

    distilled_logic_format: Literal["THRESHOLD_JSON", "LOOKUP_JSON", "RULE_AST_JSON"]
    rules: list[DistilledRule]

    payload_hash_sha256: str
    public_key_author_sig: str

    dataset_id: str
    feature_set_version: str
    transform_set_version: str

    training_start: date
    training_end: date
    ttl_max_days: int
    rule_half_life_days: int

    regime_features_used: list[str]
    regime_feature_means: list[float]
    covariance_shrinkage_matrix_ref: str
    drift_score_threshold: float

    proof_summary: ArtifactProofSummary
```

---

# 10. Contrats Pydantic — VPS Governance

## 10.1 Upload API

```python
class ArtifactUploadRequest(BaseModel):
    bundle: ArtifactExportBundle
    uploaded_by: str
    upload_context: Literal["LOCAL_LAB", "MANUAL_ADMIN"]
```

```python
class ArtifactUploadDecision(BaseModel):
    artifact_id: str
    accepted: bool
    status: Literal[
        "REGISTERED",
        "REJECTED_SCHEMA",
        "REJECTED_SIGNATURE",
        "REJECTED_SCOPE",
        "REJECTED_PROOF",
        "DRY_RUN_OK",
    ]
    rejection_reasons: list[str] = Field(default_factory=list)
```

## 10.2 Lifecycle projection

```python
class ArtifactLifecycleProjection(BaseModel):
    artifact_id: str
    lifecycle_state: Literal[
        "REPLAY_ONLY",
        "SHADOW_READY",
        "LIMITED_INFLUENCE",
        "MICRO_LIVE_CANDIDATE",
        "LIVE_APPROVED",
        "DECAYING",
        "DORMANT",
        "EXPIRED",
    ]
    drift_score: float | None = None
    ttl_days_remaining: int | None = None
    last_runtime_seen_at: datetime | None = None
    circuit_breaker_triggered: bool = False
```

## 10.3 Closed-loop batch

```python
class ClosedLoopBatchIndexRecord(BaseModel):
    batch_id: str
    vps_id: str
    runtime_mode: Literal["SHADOW", "MICRO_LIVE", "LIVE"]
    artifact_ids: list[str]
    window_start: datetime
    window_end: datetime
    object_store_path: str
    row_count: int
    created_at: datetime
```

## 10.4 Log query

```python
class LogQueryRequest(BaseModel):
    vps_ids: list[str]
    pair_ids: list[str] | None = None
    artifact_ids: list[str] | None = None
    reason_codes: list[str] | None = None
    runtime_modes: list[str] | None = None
    start_time: datetime
    end_time: datetime
    limit: int = 1000
```

```python
class LogQueryResult(BaseModel):
    total_matches: int
    rows: list[dict]
```

---

# 11. Contrats Pydantic — VPS Agent & Control Plane

## 11.1 Heartbeat

```python
class AgentHeartbeat(BaseModel):
    vps_id: str
    agent_version: str
    sent_at: datetime
    host_name: str
    status: Literal["OK", "DEGRADED", "HALTED"]
```

## 11.2 Host health

```python
class HostHealthSnapshot(BaseModel):
    vps_id: str
    cpu_pct: float
    ram_pct: float
    disk_pct: float
    uptime_seconds: int
    load_avg_1m: float | None = None
    collected_at: datetime
```

## 11.3 Runtime health

```python
class RuntimeHealthSnapshot(BaseModel):
    vps_id: str
    runtime_mode: Literal["SHADOW", "MICRO_LIVE", "LIVE", "DEGRADED", "HALTED"]
    websocket_ok: bool
    stale_pair_count: int
    backlog_size: int
    active_pair_count: int
    alert_count_critical: int
    collected_at: datetime
```

## 11.4 Artifact runtime status

```python
class ArtifactRuntimeStatusSnapshot(BaseModel):
    vps_id: str
    artifact_id: str
    lifecycle_state: str
    hard_block_rate_1h: float | None = None
    trigger_count_1h: int | None = None
    drift_score: float | None = None
    last_seen_at: datetime
```

---

# 12. Tables DB — PostgreSQL

## 12.1 Local Lab DB (si SQLite ou Postgres local)

### `dataset_registry`
- `dataset_id` PK
- `source_type`
- `base_timeframe`
- `start_date`
- `end_date`
- `storage_path`
- `file_format`
- `schema_version`
- `integrity_hash_sha256`
- `row_count`
- `pair_count`
- `status`
- `created_at`

### `feature_lineage_registry`
- `feature_id` PK
- `source_module`
- `source_reader`
- `equation_id`
- `transform_chain_json`
- `window_policy`
- `normalization_version`
- `is_allowed`
- `created_at`

### `lab_experiments`
- `experiment_id` PK
- `artifact_class`
- `target_hook_id`
- `dataset_id`
- `model_family`
- `objective`
- `status`
- `created_at`
- `completed_at`

### `lab_validation_reports`
- `report_id` PK
- `experiment_id` FK
- `anti_cowardice_pass`
- `friction_regret_pass`
- `walk_forward_pass`
- `regime_segmentation_pass`
- `operational_burden_pass`
- `capital_efficiency_pass`
- `report_json`
- `created_at`

### `artifact_export_registry`
- `artifact_id` PK
- `artifact_version`
- `experiment_id` FK
- `bundle_path`
- `payload_hash_sha256`
- `public_key_author_sig`
- `status`
- `created_at`

---

## 12.2 VPS Governance DB

### `artifacts`
- `artifact_id` PK
- `artifact_version`
- `artifact_class`
- `artifact_scope`
- `distilled_logic_format`
- `payload_hash_sha256`
- `public_key_author_sig`
- `dataset_id`
- `feature_set_version`
- `transform_set_version`
- `training_start`
- `training_end`
- `ttl_max_days`
- `rule_half_life_days`
- `status`
- `created_at`

### `artifact_allowed_hooks`
- `id` PK
- `artifact_id` FK
- `hook_id`

### `artifact_rules`
- `id` PK
- `artifact_id` FK
- `rule_id`
- `rule_json`

### `artifact_proof_summaries`
- `id` PK
- `artifact_id` FK
- `anti_cowardice_pass`
- `friction_regret_pass`
- `walk_forward_pass`
- `regime_segmentation_pass`
- `operational_burden_pass`
- `capital_efficiency_pass`
- `ablation_delta_net_pnl`
- `friction_regret_value`
- `block_rate_delta`
- `summary_json`

### `artifact_lifecycle_events`
- `id` PK
- `artifact_id` FK
- `previous_state`
- `new_state`
- `reason`
- `drift_score`
- `ttl_days_remaining`
- `event_time`

### `closed_loop_batches`
- `batch_id` PK
- `vps_id`
- `runtime_mode`
- `window_start`
- `window_end`
- `artifact_ids_json`
- `object_store_path`
- `row_count`
- `created_at`

### `log_query_audit`
- `id` PK
- `requested_by`
- `request_json`
- `result_count`
- `created_at`

---

## 12.3 Control Plane DB

### `vps_registry`
- `vps_id` PK
- `name`
- `host`
- `environment`
- `is_enabled`
- `created_at`

### `vps_heartbeats`
- `id` PK
- `vps_id` FK
- `status`
- `agent_version`
- `sent_at`

### `vps_host_health_snapshots`
- `id` PK
- `vps_id` FK
- `cpu_pct`
- `ram_pct`
- `disk_pct`
- `uptime_seconds`
- `load_avg_1m`
- `collected_at`

### `vps_runtime_health_snapshots`
- `id` PK
- `vps_id` FK
- `runtime_mode`
- `websocket_ok`
- `stale_pair_count`
- `backlog_size`
- `active_pair_count`
- `alert_count_critical`
- `collected_at`

### `vps_artifact_status_snapshots`
- `id` PK
- `vps_id` FK
- `artifact_id`
- `lifecycle_state`
- `hard_block_rate_1h`
- `trigger_count_1h`
- `drift_score`
- `last_seen_at`

### `fleet_alerts`
- `id` PK
- `vps_id`
- `severity`
- `category`
- `message`
- `artifact_id`
- `pair_id`
- `created_at`
- `acknowledged_at`

---

# 13. Runtime hook implementation strategy

## 13.1 Principe

Le runtime ne charge jamais de code arbitraire.
Il interprète des règles typées.

## 13.2 Pattern recommandé

```python
class EngineBArtifactHookInterpreter:
    def apply_rules(
        self,
        base_score: float,
        snapshot: EngineBHookSnapshot,
        rules: list[DistilledRule],
    ) -> HookApplicationResult:
        ...
```

## 13.3 Snapshot typed par hook

Créer un snapshot typed par hook, par exemple :

```python
class EngineBHookSnapshot(BaseModel):
    pair_id: str
    sweep_score_1m: float | None = None
    delta_divergence: float | None = None
    spread_z_score: float | None = None
    distance_to_poc: float | None = None
```

Aucune règle ne doit pouvoir référencer une feature non disponible dans le snapshot de hook.

---

# 14. Choix IA par tâche

## 14.1 Diagnostic engine
- tabulaire
- clustering reason-code based
- hiérarchique / K-modes / rule statistics
- pas de LLM critique

## 14.2 Threshold calibration
- coarse-to-fine grid
- recherche bayésienne légère possible
- walk-forward obligatoire

## 14.3 Micro-model training
- XGBoost / LightGBM / CatBoost
- modèles petits
- importance feature auditable
- 5 à 20 features max

## 14.4 Distillation
- arbre faible
- if/else
- threshold packs
- lookup packs

## 14.5 LLM local
- seulement pour reporting humain
- jamais pour décision critique
- jamais pour classification critique
- jamais pour distillation critique

---

# 15. Ordre exact de codage

## Build A — Constitution & Locks
1. `feature_dictionary.py`
2. `transform_whitelist.py`
3. `feature_lineage_validator.py`
4. `rule_complexity_guard.py`
5. enums / status / taxonomy partagés

## Build B — Dataset Registry & Acquisition
1. dataset contracts
2. dataset DB model
3. integrity checker
4. folder loader
5. downloader
6. parquet writer

## Build C — Local Replay parity foundation
1. local replay adapters
2. dataset -> replay bridge
3. replay evidence exporter
4. parity tests

## Build D — Feature Factory
1. physics feature builder
2. label builder
3. cached feature store
4. transform lock enforcement

## Build E — Diagnostic & Calibration
1. DTR reader
2. reason-code clusterer
3. failure pattern ranker
4. calibrator runner
5. walk-forward evaluator

## Build F — Micro-model Lab
1. trainer contracts
2. trainer xgboost
3. trainer lightgbm
4. trainer catboost
5. model selection
6. stability evaluator

## Build G — Distillation
1. distilled rule contracts
2. threshold_json_builder
3. action_unit_validator
4. reason_code_mapper
5. rule exporter

## Build H — Proof Protocol
1. ablation runner
2. anti-cowardice
3. friction regret
4. regime segmentation
5. operational burden
6. capital efficiency
7. verdict builder

## Build I — Artifact packer & signer
1. bundle builder
2. hash service
3. Ed25519 signer
4. manifest exporter

## Build J — VPS Governance API
1. DB base
2. artifact models
3. schema validator
4. signature verifier
5. upload route
6. lifecycle route

## Build K — Lifecycle & Regime distance
1. TTL manager
2. regime distance service
3. circuit breaker
4. lifecycle state transitions

## Build L — Runtime hooks
1. hook snapshots
2. hook interpreters
3. engine B integration
4. risk integration
5. scoring integration
6. portfolio integration

## Build M — Closed-loop batch
1. agent batch builder
2. batch index route
3. batch fetch route
4. local batch fetch client
5. reality joiner

## Build N — Multi-VPS control plane
1. VPS registry
2. agent heartbeat
3. health snapshots
4. artifact board
5. alert aggregation
6. federated log query

---

# 16. Tests obligatoires par build

## Build A
- feature forbidden rejection
- transform forbidden rejection
- lineage missing rejection

## Build B
- dataset hash validation
- dataset schema validation
- folder load integrity
- downloader normalization

## Build C
- local replay parity vs shared core
- no drift in decision state

## Build D
- allowed features only
- no forbidden transformations
- cached feature reuse

## Build E
- reason-code clustering deterministic
- threshold calibration stable
- walk-forward report built

## Build F
- feature budget enforced
- feature count hard cap
- model family serialization stable

## Build G
- action_unit mandatory
- no python code export
- rules schema valid
- hook scope compatible

## Build H
- anti-cowardice fail on sterile artifact
- friction regret fail on bad blocker
- burden test fail on expensive artifact

## Build I
- valid Ed25519 signature
- invalid signature rejection
- payload hash mismatch rejection

## Build J
- upload dry-run
- invalid schema rejection
- invalid hook rejection

## Build K
- TTL expiry
- regime drift to decaying
- circuit breaker to dormant

## Build L
- typed feature access only
- no rule outside allowed snapshot
- no risk bypass possible

## Build M
- non-blocking batch export
- parquet batch parse
- batch fetch incremental

## Build N
- agent heartbeat visibility
- aggregated status
- targeted log query federated

---

# 17. Notes de design non négociables

1. Le Local AI Lab doit rester petit et discipliné.
2. Aucun modèle binaire opaque n’entre en runtime en V1/V2.
3. Tout artifact doit être distillé.
4. Tout artifact doit être signé.
5. Toute influence runtime doit être bornée par hook.
6. Toute unité d’action doit être explicite.
7. Toute distance de régime doit être régularisée.
8. Le closed-loop est batch, jamais bloquant.
9. Les logs restent des logs, pas une mémoire IA.
10. La VPS reste souveraine.

---

# 18. Conclusion

Le projet doit être développé comme un **système industriel de découverte et de gouvernance de règles physiques**, pas comme une plateforme de machine learning ouverte.

Le plan ci-dessus donne :

- les fichiers
- les APIs
- les contrats
- les tables
- l’ordre de codage

Le bon chemin n’est pas :
- code ad hoc
- scripts dispersés
- expérimentation non gouvernée

Le bon chemin est :
- locks
- replay parity
- feature factory
- diagnostics
- modèles compacts
- distillation
- preuve
- signature
- import
- runtime borné
- supervision flotte
