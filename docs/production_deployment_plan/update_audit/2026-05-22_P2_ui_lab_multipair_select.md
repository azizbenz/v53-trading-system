# P2 — UI Lab Multi-Select Paires (checkbox + badges capability)

**Date** : 2026-05-22
**Sprint** : suite directe de P1 (provider C1-aware)
**Phase** : P2 / 4 (P3, P4 bloquées par P2)

---

## Objective

Remplacer le champ `<input name="pair">` mono-paire de la page IA Lab par un **multi-select checkbox** alimenté par `pair_capability_discovery` (C1.3.A). Si l'admin sélectionne ≥2 paires, le sync vers le backtest form passe le tuple complet ; sinon comportement mono-paire actuel.

**Scope strict P2** : surface UI + form state + propagation tuple `selected_pairs`. **Out of scope P2** : wiring backend `strategy_ladder_ml_lab_handoff.py` au orchestrator C1.3.C `train_multi_pair_expected_edge_artifact` (différé en P2b — sera traité quand l'admin choisit explicitement le mode MULTI_PAIR_C1 dans Backtest, P3).

---

## Docs Governants

- `2026-05-22_P1_edge_model_provider_c1_aware.md` — provider C1-aware livré
- `docs/2026-05-21_C1_MULTI_PAIR_TRAINING_DOCTRINE.md` — doctrine multi-paire
- CLAUDE.md — "filesystem-driven, ZERO hardcoded pair"

---

## Current Code Seam

| Couche | Fichier | État actuel |
|---|---|---|
| Form state pydantic | [form_state_support.py:69-97](../../../src/cockpit/form_state_support.py#L69) | `LabMlHandoffFormState.pair: str = "BTCUSDT"` (mono) |
| Endpoint POST form | [server.py:222-267](../../../src/cockpit/server.py#L222) | `_build_lab_handoff_form_state(pair=..., ...)` |
| Sync vers backtest | [server.py:296](../../../src/cockpit/server.py#L296) | `"pairs": ((lab_form.pair,) if lab_form.pair else ())` |
| Template input | [lab.html:148-151](../../../src/cockpit/templates/pages/lab.html#L148) | `<input type="text" name="pair" value="...BTCUSDT">` |
| Capability discovery | [pair_capability_discovery.py:46-100](../../../src/local_replay_runtime/pair_capability_discovery.py#L46) | `discover_pair_capabilities(klines_root, trades_root, orderbook_root, metadata_pairs)` |

---

## Placement

| Élément | Module | Type |
|---|---|---|
| `selected_pairs: tuple[str, ...] = ()` ajouté à `LabMlHandoffFormState` | `form_state_support.py` | nouveau champ pydantic |
| `discovered_pair_capabilities: tuple[PairCapability, ...] = ()` ajouté à `LabMlHandoffFormState` | `form_state_support.py` | nouveau champ pydantic (audit-trail) |
| Helper `discover_lab_pair_capabilities(form_state)` | nouveau dans `strategy_ladder_ml_handoff_support.py` | wrapper qui invoque `discover_pair_capabilities` avec les roots du form |
| Endpoint `_build_lab_handoff_form_state` accepte `selected_pairs: list[str]` + `discovered_pair_capabilities` | `server.py` | enrichissement signature |
| Endpoint `_sync_lab_handoff_into_backtest_form` propage `selected_pairs or (pair,)` | `server.py` | propagation |
| Template `<input name="pair">` remplacé par `{% if available_pairs %}checkbox list{% else %}fallback input{% endif %}` | `lab.html` | refonte form input |

---

## Files Changed

| Fichier | Action | Lignes estimées |
|---|---|---|
| `src/cockpit/form_state_support.py` | +2 champs pydantic | +10 |
| `src/cockpit/strategy_ladder_ml_handoff_support.py` | +1 helper `discover_lab_pair_capabilities` | +45 |
| `src/cockpit/server.py` | endpoint signature + sync update | +25 |
| `src/cockpit/templates/pages/lab.html` | bloc Stage 1 Pair → checkbox list + badges | +70 |
| `src/cockpit/static/cockpit.css` | mineurs styles checkbox list + badges | +30 |
| `tests/test_cockpit/test_lab_multipair_form_state.py` | NEW : 4 tests | +130 |

**Total** : ~310 lignes.

---

## Claims Implemented

### Claim 1 : Form state pydantic backward-compat

- Ajout `selected_pairs: tuple[str, ...] = ()` (default vide)
- Si vide → utiliser `pair` comme fallback (mono-paire backward-compat)
- Si non-vide → ignorer `pair`, utiliser `selected_pairs`

### Claim 2 : Capability discovery au render-time

- Lors du GET / re-render Lab page, si `kline_root` est non-vide dans le form_state persisté, on appelle `discover_pair_capabilities(klines_root=Path(kline_root), trades_root=...optional..., orderbook_root=...optional..., metadata_pairs=())` pour produire `discovered_pair_capabilities: tuple[PairCapability, ...]`.
- Si `kline_root` est vide → `discovered_pair_capabilities = ()` → fallback affiche l'input text mono.

### Claim 3 : Template checkbox list quand discovery non-vide

- Si `handoff_form.discovered_pair_capabilities` non-vide → render multi-select checkbox list :
  - 1 checkbox `<input type="checkbox" name="selected_pairs" value="{{ cap.pair }}">` par paire
  - Badges capability : `<span class="cap-badge cap-badge--{{ tier }}">{{ tier }}</span>` (FULL_MICROSTRUCTURE / LEGACY_OHLCV_ONLY / INSUFFICIENT)
  - Checkbox pré-cochée si paire dans `handoff_form.selected_pairs`
- Sinon → fallback `<input type="text" name="pair" ...>` (comportement actuel)

### Claim 4 : Sync vers backtest form

- Si `selected_pairs` non-vide → `backtest_form.pairs = selected_pairs`
- Sinon → `backtest_form.pairs = (lab_form.pair,) if lab_form.pair else ()` (actuel)

### Claim 5 : Doctrine fail-closed

- Si admin coche une paire avec `capability_tier == "INSUFFICIENT"` → handler doit bloquer ou warner (à minima : exposer dans la VM `blocked_selected_pairs: tuple[str, ...]`)
- Pas de validation pydantic stricte sur `selected_pairs` car les noms sont user-driven (zero hardcode)

---

## Tests and Proof

**Fichier** : `tests/test_cockpit/test_lab_multipair_form_state.py`

| # | Nom test | Vérifie |
|---|---|---|
| 1 | `test_lab_form_state_backward_compat_mono_pair` | `LabMlHandoffFormState(pair="BTCUSDT")` → `selected_pairs=()`, équivalent à l'actuel |
| 2 | `test_lab_form_state_multi_pair_preserves_order_and_dedup` | `LabMlHandoffFormState(selected_pairs=("BTC","ETH","SOL","BTC"))` → ordre conservé, dédup |
| 3 | `test_discover_lab_pair_capabilities_from_form_state` | Setup tmp_path avec sous-dossiers fake `BTCUSDT/`, `ETHUSDT/` → discovery retourne bien 2 capabilities |
| 4 | `test_sync_backtest_form_uses_selected_pairs_when_present` | Lab form avec `selected_pairs=("A","B")` → backtest form a `pairs=("A","B")` |

### Commandes

```powershell
rtk pytest tests/test_cockpit/test_lab_multipair_form_state.py -v
rtk pytest tests/test_cockpit/test_form_state_support.py -v  # régression
rtk pytest tests/test_cockpit/  # smoke cockpit
```

**Slots remplis post-exécution (2026-05-22)** :

- [x] **pytest_dedicated** : `8 passed` — `tests/cockpit/test_lab_multipair_form_state.py`
- [x] **pytest_regression_lab** : `16 passed` — `pytest -k lab` sur cockpit_server_routes
- [x] **pytest_cockpit_broader** : `128 passed, 4 failed` — les 4 FAIL ne mentionnent **aucun symbole P2** (selected_pairs / lab_pair / discovered_pair) dans les traces. Touchent `allow_broad_run`, `frozen_ml_overlay`, `path_in_pairs`, `pair_mismatch_preview` — pré-existants working tree, **non liés à P2**.
- [x] **guardrails P2 files** : `new_violations=0` sur 7 fichiers (filtrage post-scan)
- [x] **diff stat P2 only** :
  - `src/cockpit/form_state_support.py` (+3 lignes : champ `selected_pairs`)
  - `src/cockpit/strategy_ladder_ml_handoff_support.py` (+50 lignes : helper `discover_lab_pair_capabilities`)
  - `src/cockpit/state.py` (+10 lignes : champ VM + wire au render)
  - `src/cockpit/server.py` (+30 lignes : endpoint + form builder + sync update)
  - `src/cockpit/templates/pages/lab.html` (+25 lignes : checkbox list + badges)
  - `src/cockpit/static/cockpit.css` (+50 lignes : styles multi-select + cap-badge)
  - `tests/cockpit/test_lab_multipair_form_state.py` (NEW, 175 lignes)
  - **Total P2** : ~343 lignes (dont 175 tests)

---

## Deferred / Not Done

- **P2b** : wire `strategy_ladder_ml_lab_handoff.py` orchestrator au `train_multi_pair_expected_edge_artifact` (C1.3.C) quand `selected_pairs` ≥ 2. Pour P2, le sync vers backtest passe le tuple mais le **training reste mono** (le script handoff actuel entraîne 1 modèle par paire séparément si plusieurs paires). Acceptable car le mode C1 multi-paire en backtest exige explicitement `expected_edge_artifact_mode=MULTI_PAIR_C1` (P3 expose le toggle UI).
- **Capability badges interactifs** (tooltip d'explication) — différé.
- **Bouton "Rediscover"** pour rafraîchir capability scan sans submit complet — différé.
- **Validation côté serveur si admin sélectionne paire INSUFFICIENT** — différé (exposé en VM, bloqué côté backend ML).

---

## Risks

| Risque | Mitigation |
|---|---|
| Régression form mono-paire | `selected_pairs` default vide + fallback explicite côté template |
| Discovery filesystem lente au render | Lecture limitée à kline_root (1 scandir), pas d'I/O OHLCV |
| Persistence form state casse si admin downgrade Python | `selected_pairs: tuple[str, ...] = ()` default → pydantic accepte champ absent |
| Template casse si capability_tier inattendu | Switch-case avec `default` case dans Jinja |

---

## Completion Status (rempli 2026-05-22)

- [x] **COMPLETE**

**Preuves** :
- 8 tests dédiés P2 PASS (backward-compat mono, normalize multi, discovery filesystem, sync propagation)
- 16 régression Lab cockpit PASS
- 0 violations guardrails sur P2 files
- 4 FAIL cockpit_server_routes pré-existants confirmés non-liés (aucun symbole P2 dans traces)

---

## Next Safe Step (rempli 2026-05-22)

- [x] **Débloquer P3** : UI Backtest multi-select (réutilise le pattern P2) + dropdown `expected_edge_artifact_mode = MONO_PAIR_LEGACY | MULTI_PAIR_C1`.
  - Surface P3 : `src/cockpit/templates/pages/backtest.html` + `src/cockpit/form_state_support.py` (`BacktestFormState`) + `src/cockpit/server.py` endpoint backtest POST.
  - Pour la discovery, P3 peut réutiliser `discover_lab_pair_capabilities` ou créer un wrapper qui prend `BacktestFormState` (mêmes paths : `orderbook_path`, `klines_path`, `trades_path`).
- [ ] P4 reste bloqué par P3 (paths multi-paire nécessitent que l'UI propage selected_pairs).
- [ ] **P2b** différé : wire `strategy_ladder_ml_lab_handoff.py` orchestrator au `train_multi_pair_expected_edge_artifact` (C1.3.C) — à faire quand l'admin choisit MULTI_PAIR_C1 dans backtest (cas concret testable).
