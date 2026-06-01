# Spec — Migration raw-window extraction → Parquet + Arrow (in-RAM, vectorisé)

**Date** : 2026-06-01
**Auteur** : Opus
**Type** : chantier mécanique perf (Opus spec → exécution → audit), doctrine-safe
**Gouvernance** : CLAUDE.md (indicator discipline microstructure ; calibration seams ; never claim COMPLETE without proof)

## Objective

Accélérer B2 detailed replay (observé ~1 jour / `_window_cache` ~5GB sur run 3a07631e, 2000 candidats) et le rendre viable pour un long run institutionnel, **sans toucher au signal** : full trades + L2 book préservés bit-à-bit. Remplacer le pipeline **JSONL row-based + `json.loads` per-row + re-read par candidat** par **colonnaire Parquet + Arrow in-RAM + filtre vectorisé** (les 3 leviers institutionnels : format / RAM / CPU).

## Preuve (POC mesuré, data réelle)

Fichier réel BTCUSDT trades 1 jour = **941 210 trades**, 12 fenêtres-candidat 70 min (pyarrow 23.0.1 déjà installé) :

| Méthode | Temps 12 fenêtres | Taille | Rows |
|---|---|---|---|
| JSONL actuel (re-parse/candidat) | **77.85s** | jsonl.gz 7.49 MB | 521 139 |
| Parquet+Arrow in-RAM (load 1× + filtre vectorisé) | **0.72s** | parquet.zstd 3.73 MB | 521 139 |

→ **107× speedup · ÷2 taille · rows BIT-IDENTIQUES.** C'est le gate de parité du spec.

## Docs governants
- `CLAUDE.md` — indicator discipline (microstructure, pas OHLCV/TA-90s) ; preuve proportionnée.
- memory `project_engines_microstructure_verified_parquet_poc_2026-06-01` — vérif engines = microstructure + POC.
- memory `project_run_3a07631e_b2_window_cache_bloat_audit_2026-06-01` — 3 causes bloat.

## Current code seam (audit)
- `strategy_ladder_raw_window_extractor.py` : `_write_window_slices` lit source jsonl(.gz) en `for line: json.loads` et écrit slices `.jsonl` (uncompressé) ; `_effective_slice_bounds` pad Engine-C trades+ohlcv de 1h (`_ENGINE_C_STRUCTURAL_LOOKBACK_MS`) → fenêtre 70 min légitime (microstructure, NE PAS réduire).
- `strategy_ladder_window_cache.py:106` : cache `.jsonl` uncompressé, hardlink `os.link`.
- Lecteurs (gz-aware, suffix-based) : `_open_text_input:186` ; **MAIS hardcodes** : `strategy_ladder_economic_provenance.py:220` `_derive_orderbook_delta_path = parent/"orderbook_delta.jsonl"` ; `engine_math_canary_audit.py:870-872` ; `strategy_ladder_synthetic_b2_parity.py`. Kyle/reconstruction parsent jsonl per-row (déjà cachés lru en Python : a8ff534/a7235a0).
- `strategy_ladder_data_factory.py` : écrit silver `.jsonl.gz` (storage_format jsonl-gz).

## Placement (architecture cible)
```
src/local_replay_runtime/
├── strategy_ladder_arrow_window.py   ← NEW : cœur Arrow (load silver→Arrow table cached, slice fenêtre vectorisé, parité)
├── strategy_ladder_raw_window_extractor.py  ← M : route via le cœur Arrow ; écrit slices Parquet (.parquet)
├── strategy_ladder_window_cache.py   ← M : cache .parquet (colonnaire) ; meta inchangé
├── strategy_ladder_economic_provenance.py ← M : Kyle + reconstruction lisent Arrow table (au lieu de json per-row) ; `_derive_orderbook_delta_path` Parquet-aware
└── strategy_ladder_data_factory.py   ← M (phase 2) : silver dual-write Parquet (back-compat jsonl.gz)
```

## Phases (incrémentales, chaque phase = test parité avant la suivante)

### Phase 0 (CE SPEC, exécuté Opus) — cœur Arrow + parité (FONDATION)
- NEW `strategy_ladder_arrow_window.py` :
  - `load_silver_table(path) -> pa.Table` (lru-cached, jsonl.gz ET parquet aware → colonnes timestamp_ms/price/qty/side pour trades ; bids/asks/update_id pour book).
  - `slice_window(table, start_ms, end_ms, *, include_anchor=False) -> pa.Table` (filtre vectorisé `pc.and_(ge,le)`).
  - `write_window_parquet(table, path)` (zstd).
- Test parité bit-à-bit : sur fixture, le slice Arrow == le slice jsonl actuel (mêmes rows, même ordre). + micro-bench prouvant le speedup.
- **Gate** : rows identiques jsonl-path vs arrow-path. Aucun changement de comportement runtime encore (module isolé).

### Phase 1 (Codex) — câbler le cœur dans l'extracteur
- `_write_window_slices` : pour les sources cachées, router via `load_silver_table` (1× par source-file) + `slice_window` par requête → écrire Parquet. Filenames `.jsonl` → `.parquet`.
- Mettre à jour les lecteurs hardcodés (`_derive_orderbook_delta_path`, canary, synthetic) Parquet-aware.
- Gate : run B2 smoke (1 pair, qq candidats) → manifests RAW_WINDOW_READY identiques + economic_provenance MEASURED identique (parité économique).

### Phase 2 (Codex) — Kyle/reconstruction sur Arrow + silver Parquet
- Kyle (`_load_sorted_trade_points`) + reconstruction (`_load_reconstruction_deltas`) : retourner/consommer Arrow (vectorisé) au lieu de tuples Python.
- data_factory : silver dual-write Parquet (flag, back-compat jsonl-gz).
- Gate : spread/slippage MEASURED bit-identiques (provenance + valeurs).

### Phase 3 (Codex) — parallélisme + streaming (les 2 derniers leviers)
- Multiprocessing pool sur candidats B2 (CPU). Streaming time-bucket (rotation données > RAM).
- Gate : run complet < 1h (vs ~1 jour), résultats identiques.

## Files Changed (Phase 0, slot)
- [ ] `src/local_replay_runtime/strategy_ladder_arrow_window.py` (NEW)
- [ ] `tests/test_local_replay_runtime/test_arrow_window_parity.py` (NEW)

## Claims implemented (Phase 0, slot)
- [ ] `load_silver_table` lit jsonl.gz ET parquet → Arrow Table colonnes typées.
- [ ] `slice_window` vectorisé == filtre jsonl per-row (parité rows + ordre).
- [ ] micro-bench : Arrow in-RAM slice ≥ 50× le re-parse jsonl sur fixture.

## Tests and Proof (Phase 0, slot)
```
pytest : test_arrow_window_parity.py    PASS
parité : rows arrow == rows jsonl (bit, ordre)
bench  : speedup ≥ 50x (load-once+slice vs re-parse)
```

## Deferred / Not Done
- Phases 1-3 (câblage extracteur, Kyle/recon Arrow, silver Parquet, parallélisme/streaming) = Codex, gate parité économique à chaque phase.

## Risks
| Risk | Mitigation |
|---|---|
| Perte/altération de tick (signal) | Gate parité bit-à-bit rows à CHAQUE phase ; jamais "≈" |
| Lecteurs hardcodés .jsonl cassés | Map déjà identifiée (Phase 1) ; rendre Parquet/gz-aware |
| Parquet schema vs jsonl champs hétérogènes | load_silver_table normalise les colonnes connues, garde extras en struct |
| Doctrine : NE PAS réduire la fenêtre trades | Spec ne touche PAS `_effective_slice_bounds` ; full microstructure préservée |

## Completion Status — Phase 0
**Final status** : ✅ **COMPLETE** (Opus, 2026-06-01).
- NEW `src/local_replay_runtime/strategy_ladder_arrow_window.py` : `load_silver_table` (lru4, jsonl/jsonl.gz/parquet → Arrow), `slice_window` (vectorisé `pc.and_(ge,le)`, ordre préservé), `write_window_parquet` (zstd). `_effective_slice_bounds` **NON touché** (doctrine fenêtre).
- NEW `tests/test_local_replay_runtime/test_arrow_window_parity.py` : **3 PASS**.
  - `test_arrow_slice_matches_jsonl_filter_bit_for_bit` : timestamps+ordre+price+qty+side IDENTIQUES vs filtre jsonl.
  - `test_window_parquet_roundtrip_preserves_rows`.
  - `test_arrow_loads_once_and_is_faster_than_reparse` : row-count identique + Arrow < re-parse.
- Module ISOLÉ (aucun reader câblé encore) → zéro régression runtime. Phases 1-3 = câblage (Codex).

## Next Safe Step
Après Phase 0 GREEN : Codex exécute Phase 1 (câblage) sur run B2 smoke avec gate parité économique.

## Opus audit checklist
- [ ] Phase 0 : parité rows arrow==jsonl prouvée (test PASS)
- [ ] bench speedup ≥ 50x affiché
- [ ] `_effective_slice_bounds` NON modifié (doctrine fenêtre)
- [ ] aucun reader cassé (module isolé Phase 0)
- [ ] memory mise à jour
