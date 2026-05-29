# A2 cache — module livré + spec d'intégration

**Date** : 2026-05-28
**Status** : Module + tests + CLI backfill livrés. Intégration data_factory à câbler.

---

## Pourquoi

`A2_DATA_FACTORY` est le bottleneck méta du projet V5.3 :
- 54 jours BTCUSDT 15m + 22 features microstructure = **2h33min** wall + ~25 GB RAM
- Chaque itération B1/B2/B_ML force un rebuild complet d'A2 si on relance le workflow
- Le run `bc242fb957301811` a même hang **25 min** dans un cleanup post-compute → frustration max

**Sans cache, le projet n'est pas itérable.**

Le cache content-addressable supprime A2 du chemin critique pour 95% des itérations : tu paies 2h30 une fois, ensuite c'est 0 seconde.

---

## Ce qui est livré

### 1. Module `src/local_replay_runtime/a2_cache.py` (~330 lignes)

API publique :

| Fonction | Rôle |
|---|---|
| `build_a2_cache_key(...)` | Construit un `A2CacheKey` à partir des inputs typés (raw_roots, pairs, feature_names, window, etc.) |
| `compute_input_hash(key)` | SHA256 stable de la JSON canonique du key |
| `lookup_a2_cache(cache_base, hash)` | Lit l'entrée cachée si elle existe + valide |
| `populate_a2_cache(...)` | Copie atomique du silver+gold d'un run terminé vers le cache |
| `restore_a2_from_cache(...)` | Restaure silver+gold dans un nouveau run |
| `fingerprint_raw_paths(roots)` | Fingerprint cheap des fichiers raw (path+size+mtime, sorted) |
| `fingerprint_historical_metadata(root)` | Fingerprint de la cache historique métadata |

Models :

| Pydantic | Rôle |
|---|---|
| `A2CacheKey` (frozen) | Inputs déterministes qui décident l'output A2 |
| `A2CacheEntry` (frozen) | Métadonnée de cache (input_hash, source_run_id, counters_snapshot, key) |
| `RawSourceFingerprintEntry` (frozen) | (path, size_bytes, mtime_ms) par fichier raw |

### 2. Tests `tests/test_local_replay_runtime/test_a2_cache.py` (~340 lignes)

**15 PASS en 1.42s** :
- Hash determinism + variance with feature_names / use_measured_economic_provenance
- Hash ignore run_id et output paths (deux requests sans run_id matchent)
- Fingerprint stable, filtre extensions, gère missing roots
- Lookup retourne None pour hash inexistant, schema_version mismatch, input_hash mismatch
- Populate idempotent (2e appel ne destroy pas l'entry existante)
- Populate rebuilds quand metadata corrompue
- Restore raises sur silver subdir manquant
- Roundtrip complet : populate → lookup → restore avec vérification fichiers byte-equal

### 3. CLI `scripts/backfill_a2_cache.py` (~190 lignes)

Backfill manuel pour transformer le run `bc242fb957301811` (déjà sur disque) en entrée cache utilisable.

Usage :
```bash
python scripts/backfill_a2_cache.py \
    --run-dir "L:\output backtest\runs\strategy_ladder_workflow-bc242fb957301811\phase_a2_data_factory" \
    --raw-root "L:\ordrebookpart1" \
    --raw-root "L:\trades" \
    --raw-root "L:\klines" \
    --cache-base "L:\cache\a2"
```

**Exit codes** :
- 0 : succès
- 2 : progress report manquant
- 3 : silver/gold subdir manquant
- 4 : raw_root inexistant

---

## Ce qui reste à câbler (intégration data_factory)

L'intégration n'a **pas été câblée** dans `strategy_ladder_data_factory.py` cette session pour éviter de toucher au fichier mid-flight (4000+ lignes, patches Codex récents en cours). À faire en session dédiée.

### Point d'insertion 1 : entrée de `run_strategy_ladder_data_factory` (line 3891)

**Juste après** `request.gold_root.mkdir(...)` line 3899 et **avant** `source_report = resolve_strategy_ladder_raw_sources(...)` line 3903.

```python
# Patch A2-CACHE-INTEGRATION (2026-05-XX) — check the content-addressable
# cache BEFORE running A2. On a hit we restore silver+gold from cache and
# return a synthetic result with `current_stage="A2_CACHE_HIT"`. On a miss
# we run A2 normally and populate the cache at the end.
from local_replay_runtime.a2_cache import (
    A2_CACHE_HIT_STATUS,
    A2_CACHE_POPULATED_STATUS,
    build_a2_cache_key,
    compute_input_hash,
    lookup_a2_cache,
    restore_a2_from_cache,
)

CACHE_BASE = Path(os.environ.get("V53_A2_CACHE_BASE", "L:/cache/a2"))
CACHE_ENABLED = os.environ.get("V53_A2_CACHE", "1") != "0"

cache_key = build_a2_cache_key(
    raw_roots=tuple(Path(p) for p in request.raw_roots),
    historical_metadata_root=request.historical_metadata_root,
    pairs=request.pairs,
    engines=request.engines,
    timeframes=request.timeframes,
    feature_names=request.feature_names,
    start=request.start,
    end=request.end,
    data_types=request.data_types,
    compression=request.compression,
    storage_format=request.storage_format,
    max_gold_feature_rows=request.max_gold_feature_rows,
    use_measured_economic_provenance=request.use_measured_economic_provenance,
)
cache_input_hash = compute_input_hash(cache_key)
cache_hit_entry = (
    lookup_a2_cache(CACHE_BASE, cache_input_hash) if CACHE_ENABLED else None
)

if cache_hit_entry is not None:
    restore_a2_from_cache(
        entry=cache_hit_entry,
        cache_base=CACHE_BASE,
        target_silver_root=request.silver_root,
        target_gold_root=request.gold_root,
        target_progress_report_path=report_root / "a2_gold_progress_report.json",
    )
    _write_a2_progress_report(
        report_root,
        run_id=request.run_id,
        status="A2_RUNNING",
        current_stage=A2_CACHE_HIT_STATUS,
        ...,  # rest of arguments mirroring the "completed" path
        cache_input_hash=cache_input_hash,
        cache_source_run_id=cache_hit_entry.source_run_id,
    )
    return _build_result_from_cache_entry(cache_hit_entry, request)
```

### Point d'insertion 2 : sortie de `run_strategy_ladder_data_factory` (à la fin)

**Juste avant** le `return StrategyLadderDataFactoryResult(...)` final.

```python
# Populate the cache so the next run with identical inputs hits this path.
if CACHE_ENABLED and cache_hit_entry is None:
    try:
        populated_entry = populate_a2_cache(
            cache_base=CACHE_BASE,
            key=cache_key,
            source_run_id=request.run_id,
            source_silver_root=request.silver_root,
            source_gold_root=request.gold_root,
            source_progress_report_path=report_root / "a2_gold_progress_report.json",
            counters_snapshot=final_counters,
            gold_feature_row_count=gold_feature_row_count,
            silver_entry_count=silver_entry_count,
        )
        _write_a2_progress_report(
            report_root,
            ...,
            current_stage=A2_CACHE_POPULATED_STATUS,
            cache_input_hash=populated_entry.input_hash,
        )
    except Exception as exc:  # noqa: BLE001 - never block A2 on cache failures
        logger.warning("A2 cache populate failed: %s", exc)
```

### Helper à écrire : `_build_result_from_cache_entry(cache_hit_entry, request)`

Construit un `StrategyLadderDataFactoryResult` à partir d'une entrée cache restorée :
- Recopie `counters` depuis `cache_hit_entry.counters_snapshot`
- Recompute paths from `request.silver_root` et `request.gold_root` (déjà populés par restore_a2_from_cache)
- Status = `DATA_FACTORY_READY_FROM_CACHE`

### Variables d'environnement contrôlées

| Variable | Default | Effet |
|---|---|---|
| `V53_A2_CACHE` | `1` | `0` désactive complètement le cache (utile pour debug) |
| `V53_A2_CACHE_BASE` | `L:/cache/a2` | Override du chemin cache |

### Tests d'intégration à ajouter (next session)

- `test_a2_cache_hit_skips_compute` : 2 runs identiques, 2e run termine en < 2 sec
- `test_a2_cache_disabled_via_env` : `V53_A2_CACHE=0` force le recompute
- `test_a2_cache_miss_when_feature_names_change` : changer 1 feature → recompute
- `test_a2_cache_populate_failure_does_not_break_a2` : simuler erreur populate → log warning, return ok

---

## Validation immédiate possible

### A. Backfill du run `bc242fb957301811`

```bash
cd "E:/claude  v5.3/v53_trading_system"
python scripts/backfill_a2_cache.py \
    --run-dir "L:\output backtest\runs\strategy_ladder_workflow-bc242fb957301811\phase_a2_data_factory" \
    --raw-root "L:\ordrebookpart1" \
    --raw-root "L:\trades" \
    --raw-root "L:\klines" \
    --cache-base "L:\cache\a2"
```

Effet attendu :
- Création de `L:/cache/a2/{input_hash}/` (silver/, gold/, a2_cache_entry.json, a2_gold_progress_report.json)
- Le 54-day work du run `bc242fb957301811` devient réutilisable

### B. Vérification de la hit logic via Python REPL

```python
from pathlib import Path
from local_replay_runtime.a2_cache import (
    build_a2_cache_key,
    compute_input_hash,
    lookup_a2_cache,
)

key = build_a2_cache_key(
    raw_roots=(Path("L:/ordrebookpart1"), Path("L:/trades"), Path("L:/klines")),
    historical_metadata_root=None,
    pairs=("BTCUSDT",),
    engines=("engine_a", "engine_b", "engine_c", "engine_d"),
    timeframes=("15m",),
    feature_names=(
        "close_return", "high_low_range", "volume",
        # ... les 22 features du run
    ),
    start="2025-07-01",
    end="2025-08-23",
    data_types=("trades", "klines", "orderbook", "metadata"),
    compression="zstd",
    storage_format="jsonl_gz",
)
print("hash:", compute_input_hash(key))
print("entry:", lookup_a2_cache(Path("L:/cache/a2"), compute_input_hash(key)))
```

### C. Une fois l'intégration câblée

Relancer A2 avec les mêmes inputs → doit hit le cache et terminer en quelques secondes (juste copy disk-to-disk silver+gold).

---

## Pourquoi l'intégration n'a pas été faite cette session

`strategy_ladder_data_factory.py` :
- 4000+ lignes
- Codex y a appliqué des patches récents (heartbeat batch, cache eviction microstructure, evict_microstructure_file_cache)
- Risque non-quantifié de casser des invariants subtils (resume mode, dry_run mode, error paths, progress reporting cadencé)

L'approche surgical : livrer le module + tests + CLI hors du chemin critique, et faire l'intégration dans une session dédiée avec :
1. Lecture complète du flow A2 (resume, dry_run, error handling)
2. Tests d'intégration spécifiques
3. Validation sur 3 runs (cold cache, warm cache, env disabled)

---

## Roadmap après intégration

| Phase | Effort | Effet |
|---|:---:|---|
| **Phase 1** (cette session) | ✅ Livré | Module + tests + CLI backfill |
| **Phase 2** (prochaine session) | 0.5-1 jour | Wire shim dans data_factory, 4 tests intégration |
| **Phase 3** (juste après) | 1 run | Validation sur `bc242fb957301811` hit |
| **Phase 4** (long terme) | Multi-session | Étendre le cache à A1 preview + B1 candidate discovery (mêmes patterns) |

---

## Métriques attendues

- **Hit ratio** (% d'A2 servis depuis cache) : cible > 90% sur les itérations dev
- **Temps A2 mediane** : 2h30 → < 30 sec sur hit (juste copy silver+gold)
- **RAM peak** : 25 GB → < 4 GB sur hit (pas de compute)
- **Disque cache** : ~5 GB par entrée 54-jours (silver+gold) — réutilisé N fois

---

**Conclusion** : le module est solide (15 PASS), le contrat est simple, la voie est claire. **L'intégration shim est ~50 lignes** dans `data_factory.py` + 4 tests, soit 0.5-1 jour de travail bien fait — c'est ce qui transforme V5.3 de "non-itérable" à "itérable".
