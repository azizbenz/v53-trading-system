# Backtest + IA Lab — Mono-pair Training Doctrine

**Date :** 2026-05-21
**Statut :** ✅ DOCTRINE DOCUMENTÉE + ENFORCÉE PAR CODE (Patch MP3)
**Quote user :** *« ia lab n est pas multipaire training , il juste multitime frame , backtest aussi n a pas de multi paire training juste multi time frame training »*

---

## Résumé exécutif

L'entraînement ML expected-edge V5.3 est **MONO-PAIR par doctrine**. Multi-timeframe est supporté (1m/5m/10m/15m artifacts), multi-pair training est explicitement HORS SCOPE (Phase F13 future). Cette doctrine est maintenant :

- ✅ Documentée dans les docstrings (`StrategyLadderExpectedEdgeTrainingRequest`)
- ✅ Enforcée par validator Pydantic (`_validate_mono_pair_doctrine`)
- ✅ Message d'erreur actionable si tentative multi-pair
- ✅ 7 tests dédiés + 46/46 tests régression
- ✅ Cohérence avec data_factory qui ACCEPTE multi-pair (sourcing ≠ training)

---

## Doctrine V5.3 codifiée

| Composant | Pair scope | Source champ |
|---|---|---|
| **Data Factory** (sourcing) | **MULTI-PAIR** OK | `StrategyLadderDataFactoryRequest.pairs: tuple[str, ...]` |
| **B1 Candidate Discovery** | Multi-pair iterable | Loops per pair in `pairs` |
| **B2 Detailed Replay** | Multi-pair iterable | Loops per pair in `pairs` |
| **🔥 Expected-Edge Training** | **MONO-PAIR strict** | `StrategyLadderExpectedEdgeTrainingRequest.pair: str` |
| **IA Lab Handoff** | **MONO-PAIR strict** | `pair: str` (3 occurrences) |
| **Per-Timeframe** | **MULTI-TF** supporté | 1 artifact par tf, MÊME pair |

**Règle simple :** un artifact ML expected-edge = un (pair, timeframe) unique.

---

## Architecture

```
data_factory (multi-pair sourcing)
    ↓ pairs=("BTCUSDT", "ETHUSDT", ...) — multi-pair OK
gold/features per-pair × per-tf
    ↓
candidate_discovery (per-pair iterable)
    ↓
B2 replay (per-pair)
    ↓ label_store rows per (pair, tf, capital_bucket, candidate)
    ↓
training pipeline (MONO-PAIR)
    ↓ pair="BTCUSDT" — singular only
    ↓ timeframe="15m" — singular only
expected_edge_<pair>_<tf>.lgb artifact (1 per pair × tf)
```

**Pour entraîner 4 timeframes sur BTCUSDT :** instancier 4 `StrategyLadderExpectedEdgeTrainingRequest` (un par tf), tous avec `pair="BTCUSDT"`.

**Pour entraîner multi-pair (F13 future) :** instancier `N_pairs × N_timeframes` requests indépendants.

---

## Patch MP3 — détails techniques

### Fichier modifié
[`src/local_replay_runtime/strategy_ladder_expected_edge_training.py`](../src/local_replay_runtime/strategy_ladder_expected_edge_training.py)

### Changement #1 — Docstring classe enrichi
```python
class StrategyLadderExpectedEdgeTrainingRequest(BaseModel, frozen=True):
    """Request for a bounded Strategy Ladder expected-edge ML artifact.

    DOCTRINE V5.3 — Patch MP3 (2026-05-21) : Training is **MONO-PAIR** par doctrine.
    [...]
    Multi-timeframe par contre est SUPPORTÉ (1m/5m/10m/15m) : un artifact par
    timeframe, mais sur le MÊME pair.
    """
```

### Changement #2 — Validator explicit avec message doctrinal
```python
@field_validator("pair", mode="before")
@classmethod
def _validate_mono_pair_doctrine(cls, value: object) -> str:
    """Patch MP3 — doctrine mono-pair training strict."""
    if isinstance(value, (list, tuple, set, frozenset)):
        raise ValueError(
            f"DOCTRINE_MONO_PAIR_TRAINING — pair must be a single str (got {type(value).__name__} "
            f"with {len(value)} entries). "
            "V5.3 expected-edge training is MONO-PAIR by doctrine. For multi-pair sourcing "
            "use data_factory.pairs (multi-pair container). For multi-pair training, "
            "instantiate ONE StrategyLadderExpectedEdgeTrainingRequest PER pair (F13 future scope)."
        )
    if not isinstance(value, str):
        raise ValueError(
            f"DOCTRINE_MONO_PAIR_TRAINING — pair must be str (got {type(value).__name__})"
        )
    return value
```

### Tests dédiés (7 nouveaux, tous PASS)

| Test | Cible |
|---|---|
| `test_training_request_accepts_single_str_pair_2026_05_21` | str → accepted |
| `test_training_request_rejects_tuple_pair_with_doctrine_message_2026_05_21` | tuple → rejected + doctrine msg |
| `test_training_request_rejects_list_pair_with_doctrine_message_2026_05_21` | list → rejected |
| `test_training_request_rejects_set_pair_with_doctrine_message_2026_05_21` | set/frozenset → rejected |
| `test_training_request_rejects_non_str_with_doctrine_message_2026_05_21` | int/None/dict → rejected |
| `test_data_factory_request_accepts_multi_pair_sourcing_2026_05_21` | data_factory multi-pair OK (régression) |
| `test_training_request_doctrine_message_actionable_2026_05_21` | message actionable (data_factory.pairs + F13) |

**Régression complète sprint :** 46/46 PASS (P1+P2+P3+F16-B+F2+F2-A+MP3+5 indexer existants).

---

## Anti-pattern détecté + corrigé

**AVANT MP3 :**
```python
# Pydantic accepte silencieusement
request = StrategyLadderExpectedEdgeTrainingRequest(
    pair=("BTCUSDT", "ETHUSDT"),  # ← passé comme str via repr() → "('BTCUSDT', 'ETHUSDT')"
    ...
)
# Conséquence : training se lance avec pair="('BTCUSDT', 'ETHUSDT')" (chaîne corrompue)
# → _resolve_kline_paths cherche fichiers pour ce "pair" inexistant
# → 0 fichiers trouvés → erreur cryptique downstream
```

**APRÈS MP3 :**
```python
# Erreur claire immédiate
request = StrategyLadderExpectedEdgeTrainingRequest(
    pair=("BTCUSDT", "ETHUSDT"),  # ← REJECTED par validator
    ...
)
# ValueError: DOCTRINE_MONO_PAIR_TRAINING — pair must be a single str (got tuple with 2 entries).
# V5.3 expected-edge training is MONO-PAIR by doctrine. For multi-pair sourcing
# use data_factory.pairs (multi-pair container). For multi-pair training,
# instantiate ONE StrategyLadderExpectedEdgeTrainingRequest PER pair (F13 future scope).
```

---

## Implication pour Phase B P0-A

Phase B (training expected_edge governed) reste cohérente avec cette doctrine :

```python
# Phase B P0-A — 4 trainings mono-pair, multi-tf
TIMEFRAMES = ("1m", "5m", "10m", "15m")
for tf in TIMEFRAMES:
    request = StrategyLadderExpectedEdgeTrainingRequest(
        pair="BTCUSDT",  # ← mono-pair enforced
        timeframe=tf,    # ← multi-tf via boucle d'instances
        b2_run_root=run_root,
        feature_names=SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES,  # 12 features (F16-B)
        max_optuna_trials=50,
        ...
    )
    train_expected_edge_artifact(request)  # produit expected_edge_BTCUSDT_<tf>.lgb
```

**4 artifacts produits** (un par tf, tous BTCUSDT).

Pour multi-pair P0-A future (F13) : ajouter une boucle externe `for pair in pairs:` → `N × 4` artifacts.

---

## Cockpit IA Lab UI

Le cockpit `templates/pages/lab.html` doit afficher :
- ✅ Sélection pair = dropdown unique (pas multi-select)
- ✅ Sélection timeframe = multi-select OU séquentiel (multi-tf supporté)
- ✅ Message clair : "Training is mono-pair. Use multiple requests for multi-pair scenarios."

(UI patch hors scope MP3 — à faire séparément si besoin.)

---

## Mise à jour P0-A spec

Ajout dans `docs/2026-05-20_P0A_DECISIONS_LOCKED.md` :

```markdown
### Doctrine pair scope (MP3 — 2026-05-21)
- Training : **MONO-PAIR** (`pair: str`) — enforced par validator
- Data factory : **MULTI-PAIR** OK (sourcing scope)
- Multi-TF : **SUPPORTÉ** (1 artifact par tf)
- Phase B P0-A : 4 trainings × BTCUSDT × {1m, 5m, 10m, 15m}
- F13 future : multi-pair = N × N_tf trainings indépendants
```

---

## Quote user verrouillage

- *« ia lab n est pas multipaire training , il juste multitime frame , backtest aussi n a pas de multi paire training juste multi time frame training »*
- *« on doit d abord patche backtest et ialab ! plan svp »*
- *« go »* (plan complet 5 phases)
- *« terminer le travail »*

---

## Tasks complétées

- ✅ #24 MP1 Phase 1 Reconnaissance
- ✅ #25 MP2 Phase 2 Design
- ✅ #26 MP3 Phase 3 Code patches
- ✅ #27 MP4 Phase 4 Tests (7 nouveaux)
- ✅ #28 MP5 Phase 5 Documentation (ce doc)

---

## NEXT — Phase 6 (post-doctrine)

Maintenant que la doctrine mono-pair est enforced + documentée :

1. **Déterminer window training** selon orderbook L: disponible
2. **Lancer A2+B1+B2** sur cette window
3. **Phase B training** (4 LightGBM × BTCUSDT × {1m, 5m, 10m, 15m})
4. **Re-run B2 avec governed model** → mesurer `executed_trade_count`
5. **Verdict P0-A** : POSITIVE / NEGATIVE / INCONCLUSIVE
