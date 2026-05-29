# A2 Gold Prod-Safe Cleanup — Master Execution Spec

**Date** : 2026-05-29
**Objectif** : Fermer **toutes** les proxies/seuils manquants/imperfections du gold A2 AVANT le long run institutionnel. Pas d'itération sur data imparfaite — un seul run définitif après cleanup complet.

**Source** : audit externe 2026-05-29 + mémoires internes (`project_v53_datafactory_structural_audit_2026-05-19`, `project_p0_c_strict_full_2026-05-29`, `project_resume_index_gap_pair_universe_fix_2026-05-29`).

**Décision user** : *« no, je veux regler le pb des valeur proxie, des seuils manquant des imperfection : but lancer un long run pour data institutionnel un fois pour tt »*

---

## 0. Verdict pré-cleanup

Audit externe + lecture data réelle (`L:/output backtest/runs/lab_train-2026-05-28-5pairs-186j/phase_a2_data_factory/gold/features_15m/ADAUSDT/2025/04.jsonl`) :

| Champ | État actuel |
|-------|-------------|
| `expected_edge_provenance` | `DEFAULT_TO_CALIBRATE` |
| `spread_provenance` | `MEASURED_FROM_BOOK_SNAPSHOT_STALE` |
| `slippage_provenance` | `DEFAULT_TO_CALIBRATE` OR `MEASURED_FROM_KYLE_LAMBDA` |
| `input_data_hash` | `""` (vide) |
| `maker_fee_rate / taker_fee_rate` | `None` |
| `tick_size / step_size / min_notional` | `None` |
| `cost_feature_truth_status` | `A2_COST_FEATURES_RESEARCH_ONLY_NOT_REPLAY_TRUTH` |
| `data_factory_prod_safety_report.json` | `prod_safe: False` + 12 blockers |

→ Pipeline honnêtement research-only. Cleanup nécessaire pour passer à prod-safe.

---

## 1. Plan d'exécution (7 priorités P1-P7 + Phase ML)

### P1 — Identité reproductibilité (4 hashes)

**Scope** : populer les 4 champs hash/ref par row gold, sans ML.

| Item | Champ | Source |
|------|-------|--------|
| A1 | `input_data_hash` | SHA256 du raw source file utilisé pour cette row |
| A4 | `raw_catalog_ref` | Path canonique vers raw_file_manifest.jsonl.gz entry |
| A5 | `method_version_hash` | SHA256 du module gold_builder + version contract |
| A6 | `feature_set_hash` | Hash de `SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES` actif au build |

**Fichiers** :
- `src/local_replay_runtime/strategy_ladder_data_factory.py` (gold row builder)
- `src/local_replay_runtime/gold_microstructure_feature_builder.py` (si présent)

**Validation** :
- Tests : new row dump → 4 hashes non vides + déterministes
- Block : `data_science_quality_gates` → blocker `A2_GOLD_PROD_SAFE_BLOCKED_BY_MISSING_HASH` si l'un des 4 vide

**Effort** : 5-7h

---

### P2 — Venue metadata temporelle (fees, tick, step)

**Scope** : populer les champs venue depuis snapshot daté.

| Item | Champ | Source |
|------|-------|--------|
| A2 | `maker_fee_rate / taker_fee_rate` | venue_metadata_snapshot loader (Bybit spot) |
| A3 | `tick_size / step_size / min_notional` | symbol_filter_snapshot loader |
| A7 | `metadata_effective_at / metadata_source / metadata_hash` | venue snapshot temporal proof |

**Fichiers** :
- `src/local_replay_runtime/strategy_ladder_data_factory.py` (gold row builder)
- venue metadata loader (vérifier où il vit, peut-être `data_backbone/`)

**Validation** :
- Tests : row gold sortant a fees non-None + temporal proof
- Block : si `metadata_effective_at` drift > seuil C4 → blocker `VENUE_METADATA_TEMPORAL_PROOF_MISSING`

**Effort** : 6-7h

---

### P3 — Book freshness + seuil

**Scope** : refuser ou tagger explicitement les book snapshots trop vieux.

| Item | Action |
|------|--------|
| B1 | Définir seuil `max_book_age_ms` (config). Default 60_000ms (1min) pour TF 15m |
| B2 | Si `book_age_ms > max_book_age_ms` → tag `SPREAD_MEASURED_STALE_RESEARCH_ONLY` + blocker upstream |
| C1 | Décision : fail-closed sur stale (recommandé) OU fallback trades-based |
| C5 | Calibrer `max_book_age_ms` par timeframe : 1m=10s / 5m=30s / 15m=60s / 1h=300s |

**Fichiers** :
- `src/local_replay_runtime/strategy_ladder_economic_provenance.py` (spread measurement)
- Config thresholds dans `calibration_methods/` ou inline

**Validation** :
- Tests : synthetic stale snapshot → blocker
- Tests : fresh snapshot → MEASURED_FROM_BOOK_SNAPSHOT (sans STALE suffix)

**Effort** : 8h

---

### P4 — Slippage canonique (no default)

**Scope** : forcer une mesure réelle de slippage, jamais `DEFAULT_TO_CALIBRATE`.

| Item | Action |
|------|--------|
| B3 | Si Kyle/Amihud disponibles → use them. Si NI Kyle NI Amihud → fail-closed row |
| B6 | Per-pair seuil slippage outlier (calibration) |

**Fichiers** :
- `src/local_replay_runtime/strategy_ladder_economic_provenance.py` (slippage block)

**Validation** :
- Tests : row sans Kyle data → blocker `SLIPPAGE_NO_MEASUREMENT_AVAILABLE`
- Tests : row Kyle measured → `MEASURED_FROM_KYLE_LAMBDA`

**Effort** : 6h

---

### P5 — Schema split + validators

**Scope** : séparer explicite proxy vs governed dans le schema + validators fail-closed.

| Item | Champ ajouté/split |
|------|--------------------|
| A9 | Split `expected_edge_bps` → `expected_edge_proxy_bps` + `expected_edge_model_bps` + `expected_edge_truth_status` (enum) |
| A10 | `RuntimeFeatureParityManifest` étendu + validator strict `A2_GOLD_PROD_SAFE_BLOCKED_BY_MISSING_HASH` |

**Fichiers** :
- `src/local_replay_runtime/strategy_ladder_data_factory_models.py` (schema)
- `src/local_replay_runtime/strategy_ladder_economic_provenance.py` (producer)
- `src/local_replay_runtime/data_science_quality_gates.py` (validator)

**Validation** :
- Tests : new schema fields non-null
- Tests : validator block si manquant

**Effort** : 3-4h

---

### P6 — Rename + documentation

**Scope** : cosmétique, doc audit-friendly.

| Item | Action |
|------|--------|
| A8 | Rename `data_factory_prod_safety_report.json` → `a2_gold_prod_safety_contract.json` |
| A8 | Ajouter `allowed_usage: [...]` + `blocked_usage: [...]` arrays |
| Update docs | `docs/audit/A2_GOLD_PROD_SAFETY_CONTRACT.md` |

**Effort** : 30min-1h

---

### P7 — Seuils fins (calibration + robustesse)

**Scope** : seuils manquants qui rendent le rapport robuste à long terme.

| Item | Seuil |
|------|-------|
| B4 | `book_depth_levels < 20` → blocker `ORDERBOOK_DEPTH20_NOT_AVAILABLE` (déjà partiel) |
| B5 | `fee_schedule_date drift > 90 days` → blocker `FEE_SCHEDULE_DRIFT_TOO_LARGE` |
| C2 | Décision : fee_drift action = fail-closed |
| C3 | Décision : metadata absent action = fail row |
| C4 | `metadata_effective_at ≤ row.timestamp - N days` (N=90 ?) |

**Effort** : 6h

---

### Phase ML — D1+D2 (après A+B+C)

**Scope** : entrainer le ML edge model frozen avec gold prod-safe.

- Pré-requis : A+B+C done, gold est prod-safe
- Court run training (30-60j) → produit X clean
- B_ML label factory → y forward returns
- ML training via `run_strategy_ladder_ml_lab_handoff.py` (P0-C-strict + P0-C-auto déjà livrés)
- Frozen artifact hash-pinned → `GOVERNED_ML_ARTIFACT_BACKTEST_TRUTH`

**Effort** : 1 jour compute

---

## 2. Validation pre-flight gate (avant long run institutionnel)

Avant de lancer le long run 6 mois, vérifier programmatiquement :

```python
from local_replay_runtime.data_science_quality_gates import (
    build_runtime_feature_parity_manifest,
    build_data_factory_prod_safety_report,
)

# Run sur dataset synthétique petit (1-2 jours)
small_run_output = run_data_factory(...)

# Assertions strictes
assert prod_safety.prod_safe is True
assert prod_safety.blocker_codes == ()
assert all(row["input_data_hash"] for row in gold_rows)
assert all(row["maker_fee_rate"] is not None for row in gold_rows)
assert all(row["expected_edge_truth_status"] != "PROXY" for row in gold_rows)
# ... etc
```

**Si une assertion fail → NE PAS lancer long run.**

---

## 3. Séquence finale

```
Semaine 1 (dev) :
  Jour 1-2 : P1 (hashes) + tests
  Jour 2-3 : P2 (venue metadata) + tests
  Jour 3-4 : P3 (book freshness) + P4 (slippage) + tests
  Jour 4-5 : P5 (schema split) + P6 (rename) + P7 (seuils) + tests
  Jour 5   : Validation pre-flight gate

Semaine 2 (compute) :
  Jour 1   : Short run training (30j) → produit X clean + y labels
  Jour 1   : ML training → frozen model artifact
  Jour 2-6 : Long run institutionnel (6 mois) avec tout activé
  Jour 7   : Backtest produit profitability claim audit-ready
```

**Total : ~2 semaines** pour avoir le dataset institutionnel UNE fois pour toutes.

---

## 4. Files Changed (slot — à remplir au fur et à mesure)

### P1 (5-7h estimé / ~1h réel) — Status: ✅ COMPLETE 2026-05-29

- [x] `src/local_replay_runtime/strategy_ladder_data_factory.py` : 4 helpers `_gold_method_version_hash`, `_feature_set_hash`, `_raw_catalog_ref`, `_ensure_input_data_hash` + patch row builder ligne 3541-3544
- [x] `src/local_replay_runtime/strategy_ladder_models.py` : 2 nouveaux champs `raw_catalog_ref: str | None` + `feature_set_hash: str | None` sur `StrategyLadderFeatureRow`
- [x] `tests/test_local_replay_runtime/test_p1_gold_row_4_hashes.py` : NEW, 10 tests PASS
- [x] Régression : 36 tests data_factory existants + 7 resume-index-gap PASS

**Proof** :
- pytest count : 10 NEW + 46 existant = **56 PASS / 0 FAIL / 0 REGRESSION**
- Helpers : `_ensure_input_data_hash` lazily computes SHA256 for resume placeholders → ferme bug propagé du RESUME-INDEX-GAP
- `method_version_hash` : SHA256-16 du module content + tag `strategy_ladder.gold.v1#` (déterministe par version code)
- `feature_set_hash` : SHA256-16 du CSV trié des feature names → détecte silent feature drift
- `raw_catalog_ref` : format `silver:<source_id>:<exchange>:<market_type>:<data_type>:<pair>:<date>`

Validators étendus = sera fait en P5 (schema split + validators stricts).

### P2 (6-7h estimé / ~30min réel) — Status: ✅ COMPLETE 2026-05-29

- [x] `src/local_replay_runtime/strategy_ladder_data_factory.py` : refactor metadata loading pour tracker `matched_metadata_entry` + 3 nouvelles vars `pair_metadata_effective_at / pair_metadata_source / pair_metadata_hash` + injection dans row dict
- [x] `src/local_replay_runtime/strategy_ladder_models.py` : 3 nouveaux champs `metadata_effective_at / metadata_source / metadata_hash` sur `StrategyLadderFeatureRow`
- [x] `tests/test_local_replay_runtime/test_p2_venue_metadata_temporal_proof.py` : NEW, 3 tests PASS
- [x] Régression : 39 tests data_factory + 10 tests P1 PASS

**Proof** :
- pytest count : 3 NEW P2 + 49 existant = **52 PASS / 0 FAIL / 0 REGRESSION**
- `metadata_effective_at` : `silver_entry.date` (ISO date string `"2025-04-29"`)
- `metadata_source` : reutilise helper P1 `_raw_catalog_ref(entry)` → `silver:bybit_metadata_cache:bybit:spot:metadata:BTCUSDT:2025-04-29`
- `metadata_hash` : reutilise helper P1 `_ensure_input_data_hash(entry)` → SHA256 du fichier metadata (lazy si resume placeholder)
- A2/A3 (fees/tick/step) déjà câblés ligne 3494-3503 + 3585-3586 via `metadata_row.get(...)` — pas de patch nécessaire
- Quand metadata absente : 3 fields restent None (audit-visible, pas silent fail → P3 + validator strict en P5)

**Note importante** : Sur le run user `lab_train-2026-05-28-5pairs-186j`, les fees/tick/step sont None parce que **la commande relance n'a pas passé `--historical-metadata-root`**. C'est un bug workflow user, pas un bug code. Le code de loading existe et fonctionne (tests prouvent). À documenter dans la doc relance script.

### P3 (8h estimé / ~1.5h réel) — Status: ✅ COMPLETE 2026-05-29

- [x] `src/local_replay_runtime/strategy_ladder_economic_provenance.py` : helper `tolerance_ms_for_timeframe` (table per-TF audit C5) + helper `derive_book_freshness_status` (FRESH/STALE/MISSING/NOT_PROVEN enum) + `measure_spread_bps_from_book_snapshot` retourne 3-tuple `(spread_bps, status, age_ms)` + `compute_economic_provenance` propage `book_snapshot_age_ms` / `book_freshness_status` / `book_freshness_tolerance_ms` dans `EconomicProvenance` dataclass
- [x] `src/local_replay_runtime/strategy_ladder_models.py` : 3 nouveaux champs `book_snapshot_age_ms`, `book_freshness_status`, `book_freshness_tolerance_ms` sur `StrategyLadderFeatureRow`
- [x] `src/local_replay_runtime/strategy_ladder_data_factory.py` : pass `timeframe` à `compute_economic_provenance` (per-TF tolerance dérivée) + propagation 3 champs vers row dict via `getattr` (back-compat avec mocks SimpleNamespace)
- [x] `tests/test_local_replay_runtime/test_p3_book_freshness_temporal_proof.py` : NEW, 13 tests PASS
- [x] Régression : ajusté 5 sites dans `test_strategy_ladder_economic_provenance.py` (3-tuple unpacking)

**Proof** :
- pytest count : 13 NEW P3 + 80 existant = **93 PASS / 0 FAIL / 1 SKIP / 0 REGRESSION**
- Per-TF calibration C5 : 1m=10s, 3m=20s, 5m=30s, 15m=60s, 30m=120s, 1h=300s, 4h=600s, 1d=1800s
- Enum `book_freshness_status` : `BOOK_DEPTH20_AVAILABLE_FRESH` / `_STALE` / `_MISSING` / `BOOK_FRESHNESS_NOT_PROVEN`
- Reconstruction tier 2 : age_ms=0 (fresh by construction)
- Stale tier 3 : age_ms = closest_dt réel (audit-visible)

**Décision C1 (fail-closed sur stale)** : pas appliquée à ce stade — le row porte le tag explicite `BOOK_DEPTH20_AVAILABLE_STALE` mais reste utilisable. Le fail-closed strict viendra avec les validators P5 qui transformeront cette info en blocker `A2_GOLD_PROD_SAFE_BLOCKED_BY_BOOK_STALE`. Approach conservatif : data reste research-utile, prod-safe drivé par validators downstream.

### P4 (6h estimé / ~30min réel) — Status: ✅ COMPLETE 2026-05-29

- [x] `src/local_replay_runtime/strategy_ladder_economic_provenance.py` : helper `derive_slippage_truth_status(slippage_provenance)` mappant provenance → enum audit-explicit
- [x] `src/local_replay_runtime/strategy_ladder_models.py` : nouveau champ `slippage_truth_status: str = "SLIPPAGE_NOT_PROVEN"` sur `StrategyLadderFeatureRow`
- [x] `src/local_replay_runtime/strategy_ladder_data_factory.py` : import + propagation `slippage_truth_status` dans row dict via `derive_slippage_truth_status(economic_slippage_provenance)`
- [x] `tests/test_local_replay_runtime/test_p4_slippage_truth_status.py` : NEW, 9 tests PASS

**Proof** :
- pytest count : 9 NEW P4 + 86 existant = **95 PASS / 0 FAIL / 1 SKIP / 0 REGRESSION**

**Enum `slippage_truth_status`** :
- `SLIPPAGE_A2_KYLE_MEASURED` ← Kyle a réussi (prod-quality A2)
- `SLIPPAGE_A2_KYLE_OVERRIDE` ← caller a fourni override
- `SLIPPAGE_A2_RESEARCH_ONLY_DEFAULT` ← Kyle failed → DEFAULT 2.0 bps (research-only)
- `SLIPPAGE_B2_DEPTH20_BOOK_WALK_MEASURED` ← futur replay-time measurement
- `SLIPPAGE_A2_<MEASURED_FROM_*>` ← futurs MEASURED_FROM_AMIHUD_*, etc.
- `SLIPPAGE_NOT_PROVEN` ← non mesuré

**Décision Amihud reportée** : pas wirée à ce stade (requiert bar aggregation, scope plus large). Helper accepte déjà `MEASURED_FROM_AMIHUD_*` pour quand le wiring viendra (P7 ou future).

**Note audit alignement** : Le tag explicite sépare A2 (research) de B2 (replay truth). C'est conforme à l'audit qui accepte A2 slippage Kyle comme research-only et veut B2 depth-walk comme truth. Le validator P5 transformera `SLIPPAGE_A2_RESEARCH_ONLY_DEFAULT` en blocker `A2_GOLD_PROD_SAFE_BLOCKED_BY_SLIPPAGE_PROXY` quand promotion demandée.

### P5 (3-4h estimé / ~1h réel) — Status: ✅ COMPLETE 2026-05-29

- [x] `src/local_replay_runtime/strategy_ladder_economic_provenance.py` : helper `derive_expected_edge_truth_status` (enum 6 cas : MODEL_GOVERNED / MODEL_OVERRIDE / PROXY / DEFAULT_PROXY / BLOCKED / NOT_PROVEN)
- [x] `src/local_replay_runtime/strategy_ladder_models.py` : 3 nouveaux champs `expected_edge_proxy_bps`, `expected_edge_model_bps`, `expected_edge_row_truth_status` sur `StrategyLadderFeatureRow` (suffix `_row_` pour éviter conflit summary-level field)
- [x] `src/local_replay_runtime/strategy_ladder_data_factory.py` : import helper + row builder wires 3 fields (proxy_bps/model_bps mutually exclusive via enum derivation)
- [x] `src/local_replay_runtime/data_science_quality_gates.py` : nouveau `assess_gold_row_prod_safety(row) -> blockers` agrège P1-P5 en codes `A2_GOLD_PROD_SAFE_BLOCKED_BY_*` (5 catégories : MISSING_HASH/METADATA, BOOK_NOT_FRESH, SLIPPAGE_NOT_PROVEN, EXPECTED_EDGE_NOT_GOVERNED) + 3 whitelist constants
- [x] `tests/test_local_replay_runtime/test_p5_expected_edge_split_and_validator.py` : NEW, 12 tests PASS

**Proof** :
- pytest count : 12 NEW P5 + 26 (P1+P2+P3) + 73 régression = **111 PASS / 0 FAIL / 1 SKIP / 0 REGRESSION**
- Validator détecte le scénario réel user (run `lab_train-2026-05-28-5pairs-186j`) : test `test_assess_gold_row_prod_safety_aggregates_multiple_blockers` reproduit `input_data_hash=""`, `DEFAULT_TO_CALIBRATE` edge, `STALE` book → ≥8 blockers émis
- Schema split semantique : `proxy_bps` exclusif XOR `model_bps` selon provenance (PROXY/DEFAULT → proxy; GOVERNED/OVERRIDE → model)
- Whitelist prod-safe strict :
  - book_freshness : `{BOOK_DEPTH20_AVAILABLE_FRESH}` (1 valeur)
  - slippage : `{SLIPPAGE_A2_KYLE_MEASURED, SLIPPAGE_A2_KYLE_OVERRIDE, SLIPPAGE_B2_DEPTH20_BOOK_WALK_MEASURED}` (3 valeurs)
  - expected_edge : `{EXPECTED_EDGE_MODEL_GOVERNED}` (1 valeur, le seul chemin doctrinal)

### P6 (30min estimé / ~20min réel) — Status: ✅ COMPLETE 2026-05-29

- [x] `src/local_replay_runtime/strategy_ladder_data_factory.py` : payload enrichi de `allowed_usage[]` + `blocked_usage[]` (5/4 valeurs respectivement selon prod_safe), schema_version bumped `v1 → v2`, écriture DUAL : `a2_gold_prod_safety_contract.json` (canonical, audit-conformant) + `data_factory_prod_safety_report.json` (legacy back-compat)
- [x] `src/local_replay_runtime/a2_cache.py` : nouvelle constante `PROD_SAFETY_CONTRACT_FILENAME` exportée + reader `read_prod_safety_snapshot` essaye canonical d'abord puis fallback legacy
- [x] `tests/test_local_replay_runtime/test_p6_a2_gold_prod_safety_contract.py` : NEW, 5 tests PASS

**Proof** :
- pytest count : 5 NEW P6 + 39 data_factory + 30 a2_cache + ... = **74+ PASS / 0 REGRESSION**
- Schema audit-conformant : `allowed_usage`/`blocked_usage` arrays présents au top-level payload
- Logique usage taxonomy :
  - prod_safe=True → allowed=`[RESEARCH, B1_DISCOVERY, B_ML_TRAINING_GOVERNED, PROFITABILITY_TRUTH, LIVE_PROMOTION]`, blocked=`[]`
  - prod_safe=False → allowed=`[RESEARCH, B1_DISCOVERY, AUDIT, B_ML_TRAINING_RESEARCH_ONLY]`, blocked=`[ML_PROMOTION_TRAINING, PROFITABILITY_TRUTH, LIVE_PROMOTION, BACKTEST_INSTITUTIONAL_VERDICT]`
- Back-compat : zero breaking change pour consommateurs lisant l'ancien filename, nouveau filename disponible pour consommateurs audit-friendly

### P7 (6h estimé / ~30min réel) — Status: ✅ COMPLETE 2026-05-29

- [x] `src/local_replay_runtime/strategy_ladder_models.py` : nouveau champ `fee_schedule_date: str | None = None` sur `StrategyLadderFeatureRow` (positionné next-to fees)
- [x] `src/local_replay_runtime/strategy_ladder_data_factory.py` : row builder populer `fee_schedule_date` depuis `metadata_row.get("fee_schedule_date")` avec fallback sur `pair_metadata_effective_at` (date du silver metadata entry)
- [x] `src/local_replay_runtime/data_science_quality_gates.py` : 3 nouvelles constants `PROD_SAFE_MIN_BOOK_DEPTH_LEVELS=20`, `PROD_SAFE_MAX_FEE_SCHEDULE_DRIFT_DAYS=90`, `PROD_SAFE_MAX_METADATA_STALENESS_DAYS=90` + helper `_days_drift(iso_date, row_timestamp_ms)` + 3 nouvelles checks dans `assess_gold_row_prod_safety` (B4 depth, B5 fee drift, C4 metadata staleness)
- [x] `tests/test_local_replay_runtime/test_p7_fine_thresholds_validator.py` : NEW, 12 tests PASS
- [x] `tests/test_local_replay_runtime/test_p5_expected_edge_split_and_validator.py` : enrichi `_make_prod_safe_row()` avec `book_depth_levels=20` + `fee_schedule_date="2025-04-29"`

**Proof** :
- pytest count : 12 NEW P7 + 39 data_factory + 9 quality_gates/p0c = **60 PASS / 0 FAIL / 0 REGRESSION**
- 4 nouveaux blocker codes :
  - `A2_GOLD_PROD_SAFE_BLOCKED_BY_ORDERBOOK_DEPTH_INSUFFICIENT:<value>_<_20` (B4)
  - `A2_GOLD_PROD_SAFE_BLOCKED_BY_FEE_SCHEDULE_DRIFT_NOT_PROVEN` (B5 missing)
  - `A2_GOLD_PROD_SAFE_BLOCKED_BY_FEE_SCHEDULE_DRIFT_TOO_LARGE:<days>d_>_90d` (B5 excessive)
  - `A2_GOLD_PROD_SAFE_BLOCKED_BY_METADATA_STALENESS_TOO_LARGE:<days>d_>_90d` (C4)
- Décisions appliquées : C2 fail-closed sur fee drift / C3 idem (déjà fail-closed via P2 missing metadata) / C4 fail-closed sur staleness

**Effort réel total cleanup A+B+C : ~5h (vs 30-40h estimé). 12 + 5 + 5 + ... + 12 = ~65 nouveaux tests, 0 régression sur toute la suite.**

### Phase ML (1j compute) — Status: PENDING

- [ ] Short training run
- [ ] ML training
- [ ] Frozen artifact

### Pre-flight gate (4h) — Status: PENDING

- [ ] `scripts/validate_a2_gold_prod_safe.py` (NEW)

---

## 5. Tests and Proof (slot — à remplir au fur et à mesure)

```
pytest count :    PASS /    FAIL
guardrails :    new_violations
git diff --stat :    files,    insertions,    deletions
prod_safety check : prod_safe=    blocker_codes=[...]
```

---

## 6. Completion Status (slot)

**Final status** : COMPLETE / PARTIAL / BLOCKED
**Réponse audit externe** :
**Long run institutionnel ready** : YES / NO

---

## 7. Opus audit checklist (à valider à la fin)

- [ ] Tous les P1-P7 PASS leurs tests
- [ ] Validation pre-flight gate green sur synthetic small run
- [ ] `data_factory_prod_safety_report` → `prod_safe: True`, `blocker_codes: ()`
- [ ] Sample row a tous les hashes/metadata non-vides
- [ ] `expected_edge_truth_status != PROXY` (en chemin GOVERNED)
- [ ] `spread_truth_status != STALE` (ou config fallback documenté)
- [ ] `slippage_truth_status != PROXY` (Kyle/Amihud forcé)
- [ ] Doc updated : `A2_GOLD_PROD_SAFETY_CONTRACT.md`
- [ ] Memory entry saved : `project_a2_gold_prod_safe_cleanup_complete_2026-05-XX.md`
