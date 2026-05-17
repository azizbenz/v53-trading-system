# V5.3 — Prompt Codex : Module canonique de traitement des données raw Bybit pour IA Lab + Backtest

## Mission

Tu travailles sur le projet `v53_trading_system`.

Objectif : implémenter un module canonique de traitement des données raw Bybit qui serve de **socle unique** pour :

1. IA Lab / ML expected-edge training
2. Strategy Ladder B1/B2 backtest/replay
3. futures validations Shadow/Live

Le but n’est pas d’activer le ML ni de débloquer la promotion. Le but est de créer une chaîne data propre, traçable, anti-leakage, et réutilisable par tous les consommateurs.

---

## Contraintes globales

Ne pas :

- ne pas activer ML par défaut ;
- ne pas entraîner de modèle dans ce chantier ;
- ne pas modifier les gates de promotion ;
- ne pas supprimer `EXPECTED_EDGE_PROXY_BLOCKED` ;
- ne pas supprimer les blockers d’execution fidelity sans preuve mesurée ;
- ne pas créer de faux `selected_count` ou `executed_count` ;
- ne pas marquer `SCRATCH_ONLY` comme audité ;
- ne pas marquer `promotion/shadow/micro-live/live ready` ;
- ne pas créer un second canon concurrent ;
- ne pas faire de rewrite massif.

Le chantier doit être additif, typed, testable, et compatible avec les artifacts existants.

---

## Problème à résoudre

Aujourd’hui, IA Lab et backtest peuvent utiliser des vues différentes de la réalité marché :

- ML kline-based ;
- backtest raw-window / replay ;
- features microstructure partiellement présentes ;
- spread/slippage/adverse selection parfois proxy ;
- venue metadata parfois mal propagée ;
- raw Bybit non systématiquement transformé en dataset partagé.

Risque :

```text
train/backtest mismatch
feature drift
timestamp drift
execution drift
schema drift
hidden leakage
```

Le module doit imposer :

```text
ONE canonical market reality
MULTIPLE consumers
```

Pas :

```text
one dataset per subsystem
```

---

## Architecture cible

Pipeline cible :

```text
RAW BYBIT ZIP / CSV / JSONL
  ↓
Bronze Raw Manifest + File Index
  ↓
Canonical Normalization Layer
  ↓
Silver Synchronized Market Dataset
  ↓
Gold Feature Store
  ├── IA Lab Expected-Edge Dataset
  ├── Strategy Ladder B1/B2 Replay
  ├── Execution Realism Reports
  └── Shadow/Live parity surfaces later
```

---

# Phase 0 — Read-only scan obligatoire

Avant toute modification, inspecter et lister :

```text
src/local_replay_runtime/
src/data_backbone/
src/execution_backbone/
src/interface_contracts/
src/backtest_artifact_import/
src/calibration_methods/
src/engines/
src/cockpit/
tests/
```

Chercher explicitement :

```text
silver_index
gold_feature_store
strategy_ladder_data_factory
strategy_ladder_raw_window_extractor
strategy_ladder_detailed_replay
strategy_ladder_expected_edge_training
strategy_ladder_ml_lab_handoff
compute_economic_provenance
venue_metadata_registry
orderbook_snapshot
orderbook_delta
aggTrade
trades
klines
OFI
VPIN
queue_pressure
spread_bps
slippage
adverse_selection
```

Produire d’abord un court rapport read-only :

```text
A. modules existants réutilisables
B. modules à étendre
C. artifacts existants compatibles
D. nouveaux contracts nécessaires
E. risques DAG / import
F. plan de patch minimal
```

Ne coder qu’après ce scan.

---

# Phase 1 — Contracts typés

Créer ou étendre des contracts typés pour représenter le pipeline canonique.

## 1. Raw file manifest

Créer un contract type :

```text
RawMarketFileManifest
```

Champs attendus :

```text
schema_version
source_exchange = bybit
market_type = spot
symbol
source_type = trades | orderbook_snapshot | orderbook_delta | klines | metadata
path
format = zip | csv | jsonl | jsonl_gz | parquet
start_timestamp_ms
end_timestamp_ms
row_count
file_size_bytes
sha256
compression
created_at
source_status
```

Statuts autorisés :

```text
RAW_FILE_READY
RAW_FILE_MISSING
RAW_FILE_EMPTY
RAW_FILE_SCHEMA_UNKNOWN
RAW_FILE_TIME_RANGE_NOT_PROVEN
RAW_FILE_HASH_NOT_PROVEN
```

## 2. Bronze index manifest

Créer :

```text
BronzeMarketIndexManifest
```

Champs :

```text
schema_version
exchange
market_type
symbol
coverage_start_ms
coverage_end_ms
source_files_count
source_types_present
source_types_missing
gap_count
largest_gap_ms
duplicate_timestamp_count
out_of_order_count
index_status
source_file_refs
artifact_hash
```

Statuts :

```text
BRONZE_INDEX_READY
BRONZE_INDEX_PARTIAL
BRONZE_INDEX_BLOCKED_BY_MISSING_RAW
BRONZE_INDEX_BLOCKED_BY_SCHEMA
```

## 3. Silver synchronized manifest

Créer :

```text
SilverSynchronizedMarketManifest
```

Champs :

```text
schema_version
exchange
market_type
symbol
coverage_start_ms
coverage_end_ms
trades_status
orderbook_snapshot_status
orderbook_delta_status
ohlcv_status
depth20_status
timestamp_alignment_status
book_trade_alignment_status
stale_book_count
missing_book_count
missing_trade_count
missing_ohlcv_count
rows_written
format
compression
output_root
artifact_hash
```

Statuts :

```text
SILVER_SYNC_READY
SILVER_SYNC_PARTIAL
SILVER_SYNC_BLOCKED_BY_MISSING_TRADES
SILVER_SYNC_BLOCKED_BY_MISSING_BOOK
SILVER_SYNC_BLOCKED_BY_TIME_ALIGNMENT
SILVER_SYNC_DEBUG_ONLY
```

## 4. Gold feature manifest

Créer ou étendre :

```text
GoldMicrostructureFeatureManifest
```

Doit contenir :

```text
schema_version
exchange
market_type
symbol
timeframes
feature_row_count
feature_groups_generated
feature_groups_missing
feature_timestamp_policy
max_feature_timestamp_ms
min_feature_timestamp_ms
feature_hash
feature_status
output_path
```

Groupes minimum :

```text
returns
realized_volatility
spread
depth20
orderbook_imbalance
OFI
CVD
VPIN
queue_pressure
trade_intensity
fragility
false_breakout_context
session_tags
cost_context
break_even_context
```

Statuts :

```text
GOLD_FEATURE_STORE_READY
GOLD_FEATURE_STORE_PARTIAL
GOLD_FEATURE_STORE_BLOCKED_BY_SILVER
GOLD_FEATURE_STORE_BLOCKED_BY_MISSING_MICROSTRUCTURE
GOLD_FEATURE_STORE_DEBUG_SMALL_SAMPLE
```

---

# Phase 2 — Raw → Bronze

Implémenter un module :

```text
src/local_replay_runtime/raw_market_data_indexer.py
```

ou réutiliser un module existant si présent.

Fonctions attendues :

```python
build_raw_market_file_manifest(...)
build_bronze_market_index(...)
scan_bybit_raw_root(...)
```

Inputs typiques :

```text
L:\ordrebookpart1
L:\trades
L:\klines
```

Règles :

- ne pas charger tout en mémoire ;
- scanner par fichier / jour / symbole ;
- calculer hash ;
- extraire min/max timestamp si possible ;
- produire un index consultable par symbol/time range/source type ;
- aucun calcul de feature ici.

Sorties :

```text
raw_file_manifest.jsonl.gz
bronze_market_index.json
bronze_market_index.md
```

---

# Phase 3 — Bronze → Silver canonical synchronized

Implémenter ou étendre :

```text
src/local_replay_runtime/silver_market_synchronizer.py
```

But : créer une vue canonique partagée.

## Trades canonical schema

```text
timestamp_ms
exchange
market_type
symbol
trade_id
price
size
side_if_available
is_buyer_maker_if_available
source_path
source_row_id
```

## Orderbook canonical schema

```text
timestamp_ms
exchange
market_type
symbol
book_type = snapshot | delta
bids_px
bids_qty
asks_px
asks_qty
depth_n
source_path
source_row_id
book_sequence_id if available
```

## OHLCV canonical schema

```text
open_time_ms
close_time_ms
exchange
market_type
symbol
timeframe
open
high
low
close
volume
source_path
```

Règles :

- tri chronologique strict ;
- dedup contrôlé ;
- conversion types numériques ;
- timestamp UTC ;
- profondeur book limitée configurable : 20 par défaut ;
- stale flag book ;
- gap detection ;
- pas de feature future ;
- output compressé : `jsonl_gz` par défaut, `parquet` uniquement si déjà stable/testé.

Sorties :

```text
silver/trades/{symbol}/{date}.jsonl.gz
silver/orderbook_snapshot/{symbol}/{date}.jsonl.gz
silver/orderbook_delta/{symbol}/{date}.jsonl.gz
silver/ohlcv/{symbol}/{timeframe}/{date}.jsonl.gz
silver_synchronized_market_manifest.json
silver_quality_report.json
```

---

# Phase 4 — Silver → Gold microstructure features

Implémenter ou étendre :

```text
src/local_replay_runtime/gold_microstructure_feature_builder.py
```

Features minimum :

## Price / return

```text
close_return_1m
close_return_5m
high_low_range
realized_volatility
realized_kernel_volatility if available
```

## Book / liquidity

```text
best_bid
best_ask
mid_price
spread_bps
depth_bid_top1
depth_ask_top1
depth_bid_top5
depth_ask_top5
depth_bid_top20
depth_ask_top20
orderbook_imbalance_top5
orderbook_imbalance_top20
```

## Flow / microstructure

```text
OFI
CVD
VPIN
queue_pressure
trade_intensity
buy_sell_imbalance
aggressive_buy_volume
aggressive_sell_volume
```

## Fragility / false breakout

```text
liquidity_fragility_score
false_breakout_score
wall_pullaway_score
near_touch_cancel_ratio if available
```

## Cost / execution context

```text
fee_bps
venue_resolution_status
spread_measurement_status
slippage_proxy_or_measured_status
break_even_bps
```

Règles causales :

```text
feature_timestamp_ms <= decision_timestamp_ms
```

Chaque feature row doit porter :

```text
feature_timestamp_ms
source_window_start_ms
source_window_end_ms
feature_lag_ms
source_refs
feature_group_statuses
feature_hash
```

Sorties :

```text
gold_microstructure_features.jsonl.gz
GoldMicrostructureFeatureManifest.json
gold_feature_quality_report.json
```

---

# Phase 5 — Consumer adapters

Le même gold/silver doit servir à plusieurs consommateurs.

## 5.1 IA Lab adapter

Créer :

```text
src/local_replay_runtime/ia_lab_feature_dataset_adapter.py
```

But : produire un dataset ML **sans labels futurs dans les features**.

Sorties :

```text
expected_edge_training_feature_rows.jsonl.gz
expected_edge_feature_manifest.json
```

Ne pas entraîner.

## 5.2 Backtest adapter

Créer ou étendre :

```text
src/local_replay_runtime/backtest_replay_dataset_adapter.py
```

But : permettre à B1/B2 de consommer exactement les mêmes features et refs.

Doit fournir :

```text
candidate feature snapshot refs
raw window refs
silver index refs
gold feature refs
venue metadata refs
```

## 5.3 Runtime/shadow compatibility placeholder

Ajouter seulement le contract, pas le live runtime :

```text
runtime_feature_parity_manifest.json
```

Statut par défaut :

```text
RUNTIME_PARITY_NOT_PROVEN
```

---

# Phase 6 — Anti-leakage and quality gates

Créer :

```text
src/local_replay_runtime/data_science_quality_gates.py
```

Checks obligatoires :

```text
FEATURE_TIMESTAMP_ALIGNED
NO_FUTURE_FEATURES
LABEL_WINDOW_AFTER_DECISION
RANDOM_SPLIT_FORBIDDEN
PURGE_WINDOW_DECLARED
EMBARGO_WINDOW_DECLARED
FEATURE_HASH_STABLE
DATASET_HASH_STABLE
SOURCE_REFS_NON_EMPTY
```

Outputs :

```text
data_science_quality_report.json
anti_leakage_precheck_report.json
```

Statuts :

```text
DATA_SCIENCE_READY_FOR_RESEARCH
DATA_SCIENCE_BLOCKED_BY_LEAKAGE_RISK
DATA_SCIENCE_BLOCKED_BY_MISSING_SOURCE_REFS
DATA_SCIENCE_BLOCKED_BY_TIMESTAMP_DRIFT
DATA_SCIENCE_BLOCKED_BY_FEATURE_DRIFT
```

---

# Phase 7 — Reports / cockpit

Ajouter un rapport lisible :

```text
raw_data_processing_report.md
raw_data_processing_report.json
```

Sections :

```text
1. Raw coverage
2. Bronze index status
3. Silver synchronization status
4. Gold features generated
5. Feature groups missing
6. Timestamp / gap / stale diagnostics
7. IA Lab readiness
8. Backtest readiness
9. Replay compatibility
10. Anti-leakage precheck
11. Known blockers
```

Cockpit optionnel :

```text
Raw Data Processing / Data Science Readiness panel
```

Mais le cockpit doit seulement afficher la vérité des artifacts. Pas de logique ad hoc.

---

# Phase 8 — Integration avec Strategy Ladder

Brancher sans casser :

```text
strategy_ladder_data_factory
strategy_ladder_candidate_discovery
strategy_ladder_raw_window_extractor
strategy_ladder_detailed_replay
strategy_ladder_expected_edge_training
strategy_ladder_ml_lab_handoff
```

Règles :

- B1 peut consommer gold features ;
- B2 peut consommer silver/raw refs ;
- IA Lab peut consommer gold features + labels ;
- les paths et hashes doivent être propagés ;
- si un consumer utilise une ancienne source, il doit l’indiquer explicitement.

Ajouter champs aux manifests existants si nécessaire :

```text
canonical_data_source_status
canonical_silver_ref
canonical_gold_ref
feature_consumer_status
ia_lab_backtest_feature_parity_status
```

Statuts :

```text
FEATURE_PARITY_PROVEN
FEATURE_PARITY_NOT_PROVEN
FEATURE_PARITY_BLOCKED_BY_SCHEMA_DRIFT
FEATURE_PARITY_BLOCKED_BY_MISSING_REFS
```

---

# Phase 9 — Tests obligatoires

Ajouter tests unitaires et intégration ciblée.

## Raw/Bronze

```text
raw file manifest detects bybit/trades/orderbook/klines
bronze index detects coverage and gaps
hashes are stable
missing raw emits explicit blocker
```

## Silver

```text
trades sorted chronologically
orderbook depth20 preserved
stale book flagged
missing book/trade gaps counted
silver manifest is reproducible
```

## Gold

```text
OFI computed causally
VPIN computed causally
queue_pressure computed causally
spread_bps measured from book when available
feature_timestamp <= decision_timestamp
feature hash stable
missing feature groups explicitly reported
```

## Consumers

```text
IA Lab and Backtest read same feature_hash
B1 candidate refs include gold feature refs
B2 raw windows include silver refs
runtime parity defaults to NOT_PROVEN
```

## Anti-leakage

```text
future feature raises blocker
random split forbidden
label window after decision enforced
purge/embargo required for governed ML readiness
```

## Governance

```text
ML remains OFF by default
EXPECTED_EDGE_PROXY_BLOCKED remains active
promotion remains blocked
SCRATCH_ONLY remains SCRATCH_ONLY
DAG remains PASS
```

Commandes :

```powershell
python -m pytest -q tests/test_local_replay_runtime/test_raw_market_data_indexer.py
python -m pytest -q tests/test_local_replay_runtime/test_silver_market_synchronizer.py
python -m pytest -q tests/test_local_replay_runtime/test_gold_microstructure_feature_builder.py
python -m pytest -q tests/test_local_replay_runtime/test_data_science_quality_gates.py
python scripts/run_dag_check.py
```

---

# Phase 10 — Validation sur données réelles

Faire un mini-run contrôlé :

```text
exchange = bybit
symbol = BTCUSDT
window = 1 day
timeframes = 1m, 5m
sources = trades + orderbook + klines
```

Doit produire :

```text
raw_file_manifest.jsonl.gz
bronze_market_index.json
silver_synchronized_market_manifest.json
gold_microstructure_feature_manifest.json
data_science_quality_report.json
raw_data_processing_report.md
```

Validation attendue :

```text
SILVER_SYNC_READY or SILVER_SYNC_PARTIAL with explicit reasons
GOLD_FEATURE_STORE_READY or PARTIAL with explicit missing groups
DATA_SCIENCE_READY_FOR_RESEARCH only if no leakage/gap critical
FEATURE_PARITY_NOT_PROVEN until consumed by both IA Lab and B2
```

---

# Critères d’acceptation

Le chantier est accepté seulement si :

```text
1. raw → bronze → silver → gold fonctionne sur un mini-run réel ;
2. les artifacts sont hashés et traçables ;
3. IA Lab et Backtest peuvent référencer le même feature_hash ;
4. aucun ML n’est activé par défaut ;
5. aucun blocker de promotion n’est supprimé ;
6. les gaps sont visibles, pas masqués ;
7. DAG PASS ;
8. tests ciblés verts.
```

---

# Résultat attendu final

À la fin, fournir :

```text
- liste des fichiers modifiés/créés
- rapport read-only initial
- artifacts générés sur mini-run réel
- tests exécutés
- DAG result
- statut IA Lab readiness
- statut Backtest readiness
- blockers restants
```

Phrase de verdict attendue :

```text
Canonical raw data processing module is ready for research/backtest consumption, but it does not activate ML, does not prove profitability, and does not change promotion readiness.
```
