# P3 — UI Backtest Multi-Select + Expected-Edge Artifact Mode

**Date** : 2026-05-22
**Sprint** : suite directe de P2 (UI Lab multi-select livré)
**Phase** : P3 / 4 (P4 bloquée par P3)

---

## Objective

1. Remplacer le champ CSV `<input name="pairs">` du formulaire Backtest par un **multi-select checkbox** alimenté par `pair_capability_discovery` (réutilise la primitive P2).
2. Ajouter un **dropdown explicite `expected_edge_artifact_mode = MONO_PAIR_LEGACY | MULTI_PAIR_C1`** dans le bloc ML, propagé jusqu'au CLI `--expected-edge-artifact-mode` (consommé par P1 provider).

**Scope** : surface UI + propagation end-to-end (UI → form state → endpoint → command builder → CLI → request pydantic → provider P1). Pas de wire training C1.3.C (toujours P2b différé).

---

## Docs Governants

- `2026-05-22_P1_edge_model_provider_c1_aware.md` — provider C1-aware ; expose `--expected-edge-artifact-mode`
- `2026-05-22_P2_ui_lab_multipair_select.md` — composant checkbox + helpers discovery factorisés
- `docs/2026-05-21_C1_MULTI_PAIR_TRAINING_DOCTRINE.md` — doctrine multi-paire

---

## Files Changed

| Fichier | Action | Lignes |
|---|---|---|
| `src/cockpit/form_state_support.py` | +3 (`expected_edge_artifact_mode` champ) | +3 |
| `src/cockpit/strategy_ladder_ml_handoff_support.py` | refactor : primitive `_discover_pair_capabilities_from_paths` + wrapper `discover_backtest_pair_capabilities` | +30 |
| `src/cockpit/state.py` | +5 (VM `backtest_discovered_pair_capabilities` + wire au render) | +5 |
| `src/cockpit/server.py` | endpoint backtest_run + sync + form_state | +25 |
| `src/cockpit/action_support.py` | builder propage `--expected-edge-artifact-mode` | +15 |
| `scripts/run_backtest_strategy_ladder.py` | CLI accepte `--expected-edge-artifact-mode` + passe au request | +10 |
| `src/cockpit/templates/pages/backtest.html` | checkbox list + dropdown mode (bloc Stage 3) | +35 |
| `tests/cockpit/test_backtest_multipair_form_state.py` | NEW : 7 tests dédiés | +135 |

**Total** : ~258 lignes (dont 135 tests).

---

## Claims Implemented

### Claim 1 : Form state backward-compat

- `BacktestFormState.expected_edge_artifact_mode: str = "MONO_PAIR_LEGACY"` (default safe)
- `model_copy(update={...})` préserve le mode

### Claim 2 : Discovery filesystem-driven (réutilise P2)

- `discover_backtest_pair_capabilities(backtest_form)` → tuple[PairCapability, ...]
- Source paths : `BacktestFormState.{klines_path, trades_path, orderbook_path}`
- Retourne `()` si pas de `klines_path` → template fallback CSV input

### Claim 3 : Endpoint multi-select prend priorité sur CSV

- Endpoint POST `/backtest/run` accepte `selected_pairs: list[str] = Form([])` ET `pairs: str = Form("")` (CSV)
- Si `selected_pairs` non-vide → utilisé comme source (strip/dedup/order preserved)
- Sinon → fallback CSV `pairs.split(",")`

### Claim 4 : Dropdown mode propagé au CLI

- Endpoint accepte `expected_edge_artifact_mode: str = Form("MONO_PAIR_LEGACY")`
- Stocké dans `BacktestFormState.expected_edge_artifact_mode`
- Passé à `launch_backtest_job(expected_edge_artifact_mode=...)`
- Builder `_build_backtest_command` émet `--expected-edge-artifact-mode {mode}` quand `ml_mode_status == "ML_MODE_OVERLAY_FROZEN"` (bloc déjà conditionnel sur ce mode)
- CLI `run_backtest_strategy_ladder.py` parse `--expected-edge-artifact-mode` (choices `MONO_PAIR_LEGACY | MULTI_PAIR_C1`) et le passe à `StrategyLadderRequest(expected_edge_artifact_mode=...)` — déjà validé par P1

### Claim 5 : Template conditionnel (multi vs CSV)

- Si `vm.backtest_discovered_pair_capabilities` non-vide → checkbox list avec badges (FULL / LEGACY / INSUFFICIENT / no-OB)
- Sinon → input text CSV (comportement actuel préservé)
- Champ caché `<input name="pairs">` reste actif en mode multi pour préserver la valeur précédente

---

## Tests and Proof

**Fichier** : `tests/cockpit/test_backtest_multipair_form_state.py` (7 tests)

| # | Test | Vérifie |
|---|---|---|
| 1 | `test_backtest_form_state_expected_edge_artifact_mode_default` | Default = MONO_PAIR_LEGACY |
| 2 | `test_backtest_form_state_expected_edge_artifact_mode_multi` | Mode MULTI_PAIR_C1 accepté |
| 3 | `test_backtest_form_state_mode_persists_through_model_copy` | `model_copy` préserve le mode |
| 4 | `test_discover_backtest_pair_capabilities_empty_form_returns_empty` | Pas de klines_path → () |
| 5 | `test_discover_backtest_pair_capabilities_scans_paths` | Filesystem scan → 2 capabilities (BTCUSDT/ETHUSDT) avec orderbook/trades flags |
| 6 | `test_build_backtest_command_emits_expected_edge_artifact_mode_default` | CLI emit `--expected-edge-artifact-mode MONO_PAIR_LEGACY` |
| 7 | `test_build_backtest_command_propagates_multi_pair_c1_mode` | CLI emit `--expected-edge-artifact-mode MULTI_PAIR_C1` + `--pairs BTCUSDT,ETHUSDT,SOLUSDT` |

### Slots remplis post-exécution (2026-05-22)

- [x] **pytest_dedicated P3** : `7 passed`
- [x] **pytest_dedicated P2+P3 combined** : `15 passed`
- [x] **pytest_regression backtest routes** : `39 passed, 1 failed` — le seul FAIL (`test_command_builder_hard_guard_rejects_path_in_pairs`) était **déjà parmi les 4 FAIL pré-existants notés en P2** (TypeError sur kwargs required manquants dans le test fixture, indépendant de P3 — message d'erreur cite `frozen_ml_ar...` pas `expected_edge_artifact_mode`).
- [x] **guardrails P3 files** : `new_violations=0` sur 8 fichiers
- [x] **diff stat P3 only** : 8 fichiers in-scope, ~258 lignes (dont 135 tests)

---

## Deferred / Not Done

- **P2b** : wire `strategy_ladder_ml_lab_handoff.py` orchestrator au `train_multi_pair_expected_edge_artifact` (C1.3.C) — à faire quand un admin teste effectivement MULTI_PAIR_C1 en backtest (cas concret).
- **Préflight validator backtest** : si admin coche MULTI_PAIR_C1 + 1 seule paire sélectionnée → warning UI (mono-paire dans manifest C1 inutile). Reporté.
- **Auto-suggestion mode** (bundle JSON inspection au render-time) — supprimé du scope car contraire à la décision admin "champ explicite".

---

## Risks

| Risque | Mitigation |
|---|---|
| Régression endpoint backtest_run | `selected_pairs: Form([])` default vide + `expected_edge_artifact_mode: Form("MONO_PAIR_LEGACY")` default safe → backward-compat 100% |
| CLI script `run_backtest_strategy_ladder.py` rejette ancien mode | argparse `choices=("MONO_PAIR_LEGACY", "MULTI_PAIR_C1")` avec default → ancien comportement préservé |
| Builder cockpit casse autres job_kinds | `--expected-edge-artifact-mode` ajouté SEULEMENT dans le bloc `STRATEGY_LADDER_RUNNER + ML_MODE_OVERLAY_FROZEN` (chemin conditionnel existant) |
| Template casse mono-paire actuel | `{% if vm.backtest_discovered_pair_capabilities %}...{% else %}<input CSV>{% endif %}` — fallback explicite |

---

## Completion Status

- [x] **COMPLETE**

**Preuves consolidées** :
- 7/7 tests P3 PASS
- 15/15 P2+P3 combinés PASS
- 39/40 régression backtest routes PASS (1 FAIL pré-existant non-P3, vérifié par contenu du message d'erreur)
- 0 violations guardrails P3 files

---

## Next Safe Step

- [x] **Débloquer P4** : paths historiques multi-paire (pattern parent + scan auto sous-dossiers paires).
  - Surface P4 : `src/cockpit/backtest_preflight.py` (inférer paires depuis paths) + `src/local_replay_runtime/strategy_ladder_data_factory.py` (scan paths multi-paire pour data factory) + tests.
  - P4 est l'étape qui permet à l'admin de pointer `L:\ordre book part 1\` (parent) au lieu de `L:\ordre book part 1\BTCUSDT` (mono-paire actuel).
