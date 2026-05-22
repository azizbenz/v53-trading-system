# P4 — Pattern Parent + Scan Helper for Multi-Pair Historical Paths

**Date** : 2026-05-22
**Sprint** : suite directe de P3 (UI Backtest + dropdown mode)
**Phase** : P4 / 4 — ferme le combo 1+1b+3 demandé

---

## Objective

Livrer le helper `expand_parent_path_to_pair_paths(raw_path, *, pair_universe)` qui permet à l'admin de pointer un **dossier parent** (`L:\ordre book part 1\`) au lieu d'un dossier mono-paire (`L:\ordre book part 1\BTCUSDT\`). Le helper :
- Détecte si le path est déjà un pair dir → retourne `(Path(raw_path),)` (backward-compat mono)
- Détecte si le path est un parent → scan filesystem et retourne `(Path/pair_a, Path/pair_b, ...)` filtré par `pair_universe`
- Préserve l'ordre `pair_universe` (déterministe pour l'admin UX)

**Scope strict P4** : helper standalone + tests dédiés. **Out of scope P4 (= P4b différé)** : wiring de ce helper dans `backtest_preflight.build_patch6_preflight_preview` et dans `strategy_ladder_data_factory` raw scanner. Ce wiring sera fait au moment où un admin teste effectivement le pattern parent en bout-en-bout.

---

## Pourquoi ce scope minimal

Le data_factory `raw_market_data_indexer` scanne déjà recursivement les sous-dossiers des `raw_roots`, donc pointer un parent au runner **fonctionne déjà** côté backend (le filter `request.pairs` limite ce qui est traité). Ce qui manque pour fermer la boucle UI :
1. ✅ **Helper de résolution** (P4 livré ici)
2. ⏸ **Wiring preflight UI** (P4b) — appel du helper dans `_resolve_actual_data_paths_from_form` pour valider/expand avant submit
3. ⏸ **Détection auto parent vs mono** (P4b) — pour ne pas casser le path mono actuel quand admin pointe directement un pair dir

P4 livre la pièce technique. P4b est un wire pur sans logique nouvelle.

---

## Files Changed

| Fichier | Action | Lignes |
|---|---|---|
| `src/cockpit/backtest_preflight.py` | +1 fonction `expand_parent_path_to_pair_paths` | +65 |
| `tests/cockpit/test_expand_parent_path_to_pair_paths.py` | NEW : 8 tests dédiés | +110 |

**Total** : ~175 lignes (dont 110 tests).

---

## Claims Implemented

### Claim 1 : Empty / invalid input fail-safe

- `""`, `"   "`, path inexistant → retour `()` (pas d'exception)

### Claim 2 : Mono-pair backward-compat

- Si `raw_path` matche un pair symbol (via `infer_pair_symbol_from_path`) → retourne `(Path(raw_path),)` inchangé. Comportement mono actuel préservé.

### Claim 3 : Parent + filter pair_universe

- Si `raw_path` est un parent dir + `pair_universe=("BTC","ETH")` fournis → retourne `(parent/BTC, parent/ETH)` filtré
- Paires manquantes du filesystem silently skipped (pas d'erreur)

### Claim 4 : Parent sans filter

- Si `raw_path` est un parent dir + `pair_universe=()` vide → retourne TOUTES les sous-dirs pair-like (sorted alphabétique)

### Claim 5 : ZERO hardcoded pair names

- Accepte arbitrary symbols (MMXX, FUTURE_42, etc.) via `_looks_like_pair_symbol`

### Claim 6 : Ordre déterministe

- `pair_universe=("SOL","BTC","ETH")` → résultat dans cet ordre EXACT (pas alphabétique)

---

## Tests and Proof

**Fichier** : `tests/cockpit/test_expand_parent_path_to_pair_paths.py` (8 tests)

| # | Test | Vérifie |
|---|---|---|
| 1 | `test_expand_empty_raw_path_returns_empty_tuple` | Empty/whitespace → () |
| 2 | `test_expand_nonexistent_path_returns_empty_tuple` | Path inexistant → () |
| 3 | `test_expand_pair_dir_preserves_mono_behaviour` | Pair dir actuel → (Path,) unchanged |
| 4 | `test_expand_parent_dir_with_pair_universe_filter` | Parent + filter → seulement les paires demandées |
| 5 | `test_expand_parent_dir_without_filter_returns_all_pair_subdirs` | Parent + no filter → ALL sub-pairs sorted |
| 6 | `test_expand_parent_dir_filter_ignores_missing_pairs` | Filter sur paire absente → skip silencieux |
| 7 | `test_expand_parent_dir_with_arbitrary_pair_names` | Arbitrary symbols (MMXXUSDT, FUTUREUSDC) OK |
| 8 | `test_expand_parent_dir_preserves_pair_universe_order` | Order respects pair_universe, pas alphabetical |

### Slots remplis post-exécution (2026-05-22)

- [x] **pytest_dedicated P4** : `8 passed`
- [x] **pytest_regression preflight** : `6 passed, 1 failed` — le seul FAIL (`test_command_builder_hard_guard_rejects_path_in_pairs`) est **pré-existant** (déjà identifié en P3 — TypeError sur kwargs required missing, indépendant de P4)
- [x] **guardrails P4 files** : `new_violations=0` sur 2 fichiers
- [x] **diff stat P4 only** : 2 fichiers in-scope, ~175 lignes (dont 110 tests)

---

## Deferred / Not Done

- **P4b** : wire `expand_parent_path_to_pair_paths` dans `backtest_preflight.build_patch6_preflight_preview` pour expand auto les paths parent au moment du submit
- **P4c** : adapter `strategy_ladder_data_factory.raw_market_data_indexer` pour utiliser explicitement les sub-paths résolus (au lieu du scan récursif générique)
- **P2b** différé : training C1.3.C wiring (toujours en attente)

---

## Risks

| Risque | Mitigation |
|---|---|
| Helper appelé sur path mono → retourne () au lieu de (Path,) | Test 3 (`test_expand_pair_dir_preserves_mono_behaviour`) couvre exactement ce cas, retour `(Path(raw_path),)` |
| Filesystem race condition (dir crée entre Test et iterdir) | `try/except (OSError, PermissionError)` autour de iterdir, retour `()` en cas d'erreur |
| Helper appelé hors UI casse les tests existants | Helper additif pur, aucune modification des fonctions existantes du module |

---

## Completion Status

- [x] **COMPLETE**

**Preuves consolidées** :
- 8/8 tests P4 PASS
- 0 régressions tests preflight (1 FAIL pré-existant unique, déjà identifié et non-lié)
- 0 violations guardrails P4 files

---

## Next Safe Step

- [x] **Sprint combo 1+1b+3 livré complet** :
  - Option 1 (UI multi-select Lab + Backtest) ✅ via P2 + P3
  - Option 3 (Provider edge model C1-aware) ✅ via P1
  - Option 1b (Paths historiques multi-paire) ✅ via P4 helper (P4b wiring différé jusqu'à test admin réel)
- [ ] **Reste à faire pour boucle end-to-end "live" multi-paire** :
  - **P2b** : `strategy_ladder_ml_lab_handoff.py` orchestrator → `train_multi_pair_expected_edge_artifact` (C1.3.C). C'est ce qui produit le manifest `MULTI_PAIR_C1_EXPECTED_EDGE` consommé par P1 provider.
  - **P4b** : wire `expand_parent_path_to_pair_paths` dans le preflight UI.
  - Total estimé pour fermer end-to-end : ~1.5j (P2b + P4b + integration test E2E).
