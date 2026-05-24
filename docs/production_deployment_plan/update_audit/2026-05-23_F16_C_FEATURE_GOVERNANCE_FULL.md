# F16-C — Feature Governance Full (extension pool + UI picker + promotion gate)

**Date** : 2026-05-23
**Sprint** : suite directe de F16-B (livré 2026-05-21, ENRICHED 12 features)
**Phase** : F16-C / 3 piliers (P1 validator + label_store v3, P2 promotion registry + ablation, P3 UI Lab feature picker)
**Branche cible** : `codex/full-solution-runtime-2026-05-17`

---

## Objective

Refermer **3 gaps actifs** identifiés dans [project_training_backtest_feature_parity_gap_2026-05-23](../../../memory/project_training_backtest_feature_parity_gap_2026-05-23.md) :

1. **Pool de features étendu** : ajouter au moins 10 features numériques + 1 catégoriel (`anti_revenge_state` one-hot) au validator `SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES`. Fermer l'incohérence `latency_penalty_bps` (présent dans `_EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS` mais absent du validator).
2. **Promotion gouvernée post-backtest** : chaque feature reçoit un verdict `PROMOTED / NEUTRAL / DEMOTED / INSUFFICIENT_EVIDENCE` basé sur SHAP rank + ablation P&L (leave-one-out backtest, ΔPSR/ΔSharpe/ΔBreak-even). Verdict persisté dans `feature_promotion_registry.json` par pair/timeframe, Talab quadruple filter + Bailey-LdP MinBTL appliqués.
3. **UI Lab feature picker** : page `/lab` expose un multi-select checkbox alimenté dynamiquement par `SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES`, avec badge verdict (PROMOTED/NEUTRAL/DEMOTED/N-A) à droite de chaque checkbox. Pré-cochage basé sur dernier verdict du registry. Choix persisté dans `LabMlHandoffFormState.selected_features`.

**Scope strict F16-C** : les 3 piliers ci-dessus. **Out of scope F16-C** :
- Auto-application du verdict (Pilier 2 expose les verdicts ; le user reste maître via UI Pilier 3)
- Re-training automatique post-démotion (différé en F16-D si besoin)
- Multi-pair feature governance (chaque pair garde son registry séparé ; F13 multi-pair native est orthogonal)

**Décisions architecturales validées user (2026-05-23)** :
- Promotion logic : **SHAP + Ablation P&L** (verdict P&L-grounded conforme Talab)
- UI design : **Multi-select avec verdict badge** (pré-cochage selon dernier verdict)
- Categorical encoding : **One-hot encoding** (`anti_revenge_state__*` colonnes booléennes)
- Schema migration : **Backward-compat nullable** (v3 ajoute champs `float | None = None`, anciens v2 chargent avec None)

---

## Docs Governants

- [project_f16_b_implemented_2026-05-21.md](../../../memory/project_f16_b_implemented_2026-05-21.md) — livraison F16-B ENRICHED (label store v2, 12 features supportés)
- [project_training_backtest_feature_parity_gap_2026-05-23.md](../../../memory/project_training_backtest_feature_parity_gap_2026-05-23.md) — gap actif identifié 2026-05-23 (CLI default 3, 11+ features engines non trainables)
- [reference_v53_statistical_anchors.md](../../../memory/reference_v53_statistical_anchors.md) — PSR/DSR Bailey-LdP, KS, Energy, Hansen-SPA, seuils doctrinaux (G2.1=0.60, G2.2=0.85, G2.3=0.95, DSR=0.95)
- [reference_industry_sample_size_anchors_verified.md](../../../memory/reference_industry_sample_size_anchors_verified.md) — MinBTL Bailey-Borwein-LdP-Zhu 2014, Hou-Xue-Zhang non-réplication
- CLAUDE.md § "Governance frameworks (mandatory reference)" — Talab quadruple filter, Carver volume targeting, model_risk_registry
- CLAUDE.md § "Indicator discipline" — features autorisés (microstructure modern only, no 1990s TA)

---

## Current Code Seam

### Pilier 1 — Validator / label_store / capture bridge

| Couche | Fichier | Lignes actuelles |
|---|---|---|
| Validator `SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES` | [strategy_ladder_expected_edge_training.py:41-60](../../../src/local_replay_runtime/strategy_ladder_expected_edge_training.py#L41) | 12 features (3 LEGACY + 9 ENRICHED) |
| Validator `_require_supported_legacy_features` | [strategy_ladder_expected_edge_training.py:408-415](../../../src/local_replay_runtime/strategy_ladder_expected_edge_training.py#L408) | Lock kline-only à 3 LEGACY (intentionnel) |
| Schema `StrategyLadderB2LabelStoreRow` v2 | [strategy_ladder_b2_label_store_builder.py:342-399](../../../src/local_replay_runtime/strategy_ladder_b2_label_store_builder.py#L342) | 29 communs + 3 ENRICHED (vpin/cumulative_ofi/queue_pressure) |
| Augmented feature keys label_store | [strategy_ladder_b2_label_store_builder.py:89-102](../../../src/local_replay_runtime/strategy_ladder_b2_label_store_builder.py#L89) | 8 keys (incohérence : `latency_penalty_bps` présent, absent validator) |
| Capture bridge microstructure | [strategy_ladder_runner.py:1837-1870](../../../src/local_replay_runtime/strategy_ladder_runner.py#L1837) | `_extract_bridge_microstructure_scalars` capture 3 scalars (vpin/ofi/queue) |
| Sélection engine payload | [strategy_ladder_runner.py:1759-1808](../../../src/local_replay_runtime/strategy_ladder_runner.py#L1759) | `_selected_engine_payload_fields` expose ~20 fields, dont les non-trainables actuels |
| Build-14 reader extraction | [strategy_ladder_runner.py:1726-1743](../../../src/local_replay_runtime/strategy_ladder_runner.py#L1726) | `_build14_reader_observed_value` extrait 3 readers (micro_edge_*, fragility) |

### Pilier 2 — Promotion registry + ablation

| Couche | Fichier | État actuel |
|---|---|---|
| Training report SHAP | [strategy_ladder_expected_edge_training.py:165-204](../../../src/local_replay_runtime/strategy_ladder_expected_edge_training.py#L165) | `shap_summary_ref: str \| None` champ existe, mais pas exploité downstream |
| Backtest verdict produit | (à inventorier en exécution) | aucun module ne produit `feature_promotion_verdict` actuellement |
| Registry | (n'existe pas) | nouveau module |

### Pilier 3 — UI Lab feature picker

| Couche | Fichier | Lignes actuelles |
|---|---|---|
| Form state pydantic | [form_state_support.py:72-103](../../../src/cockpit/form_state_support.py#L72) | `LabMlHandoffFormState.feature_names: str = "close_return,high_low_range,volume"` (CSV string) |
| Template Lab | [src/cockpit/templates/pages/lab.html](../../../src/cockpit/templates/pages/lab.html) | `<input name="feature_names" value="...">` text input plat |
| Discovery pair (modèle réutilisable) | [strategy_ladder_ml_handoff_support.py:476-545](../../../src/cockpit/strategy_ladder_ml_handoff_support.py#L476) | `discover_lab_pair_capabilities` — pattern à dupliquer pour features |
| VM render | [state.py:840-860](../../../src/cockpit/state.py#L840) | Render Lab VM ; ajouter `lab_feature_governance` analogue à `lab_discovered_pair_capabilities` |

---

## Placement

### Pilier 1

| Élément | Module | Type |
|---|---|---|
| `SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES` étendu (+11 numériques) | `strategy_ladder_expected_edge_training.py` | refonte constante |
| `ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES` nouveau (3 colonnes) | `strategy_ladder_expected_edge_training.py` | nouvelle constante |
| `_validate_feature_names` accepte one-hot suffixes | `strategy_ladder_expected_edge_training.py` | enrichissement validator |
| Schema row v3 `StrategyLadderB2LabelStoreRow` | `strategy_ladder_b2_label_store_builder.py` | bump `schema_version`, +13 champs nullables |
| `_EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS` aligné sur validator | `strategy_ladder_b2_label_store_builder.py` | fix incohérence latency_penalty_bps |
| `_extract_bridge_microstructure_scalars` étendu | `strategy_ladder_runner.py` | +`kyle_lambda`, +`realized_vol_*` |
| Helper `_extract_engine_d_governance_scalars` | `strategy_ladder_runner.py` (nouveau) | extrait `history_score`, `marginal_value_score`, `reentry_lateness`, `concentration_headroom` depuis payload engine D |
| Helper `_extract_build14_observed_values` | `strategy_ladder_runner.py` (nouveau) | extrait `micro_edge_exit_governor`, `micro_edge_entry_timing` depuis Build14ShadowReport |
| Helper `_extract_anti_revenge_one_hot` | `strategy_ladder_runner.py` (nouveau) | encode `anti_revenge_state` en 3 booléens |
| Helper `_extract_latency_penalty_bps` | `strategy_ladder_runner.py` (nouveau) | depuis native_output ou compatibility payload |

### Pilier 2

| Élément | Module | Type |
|---|---|---|
| `expected_edge_feature_promotion_registry.py` | `src/local_replay_runtime/` | NOUVEAU |
| `ExpectedEdgeFeatureVerdict` (PROMOTED/NEUTRAL/DEMOTED/INSUFFICIENT_EVIDENCE) | nouveau module | StrEnum |
| `FeaturePromotionEntry` pydantic | nouveau module | row registry |
| `FeaturePromotionRegistry` pydantic | nouveau module | dict[(pair,tf), tuple[FeaturePromotionEntry,...]] |
| `load_feature_promotion_registry(path)` | nouveau module | reader fail-closed |
| `save_feature_promotion_registry(path, registry)` | nouveau module | atomic_write_json |
| `expected_edge_feature_ablation_orchestrator.py` | `src/local_replay_runtime/` | NOUVEAU |
| `FeatureAblationRequest` pydantic | nouveau module | feature, baseline_artifact, backtest_inputs, min_btl |
| `FeatureAblationReport` pydantic | nouveau module | delta_psr, delta_sharpe, delta_break_even, talab_quadruple_pass, verdict |
| `run_feature_ablation(request)` | nouveau module | re-train sans feature + re-backtest + diff |
| `compute_feature_promotion_verdict(shap_rank, ablation_report, talab_filters)` | nouveau module | logic centrale |
| `apply_feature_promotion_to_registry(report, registry_path, pair, timeframe)` | nouveau module | wiring registry |

### Pilier 3

| Élément | Module | Type |
|---|---|---|
| `LabMlHandoffFormState.selected_features: tuple[str, ...]` | `form_state_support.py` | nouveau champ pydantic (additif, backward-compat) |
| `LabMlHandoffFormState.discovered_feature_governance: tuple[FeaturePromotionEntry, ...]` | `form_state_support.py` | nouveau champ pydantic (audit-trail) |
| `discover_lab_feature_governance(form_state)` | `strategy_ladder_ml_handoff_support.py` | NOUVEAU helper (lit registry, retourne entries par pair/tf) |
| Template Lab `<select>` → checkbox list + badges | `lab.html` | refonte form input |
| VM `lab_feature_governance` | `state.py` | render-time hook |
| Endpoint `_build_lab_handoff_form_state` accepte `selected_features: list[str]` | `server.py` | enrichissement signature |
| Endpoint propage `selected_features` au `StrategyLadderMlLabHandoffRequest` | `server.py` | propagation |
| CSS badges verdict | `cockpit.css` | styles `.feat-badge--promoted/neutral/demoted/na` |

---

## Files Changed

| Fichier | Action | Lignes estimées | Pilier |
|---|---|---|---|
| `src/local_replay_runtime/strategy_ladder_expected_edge_training.py` | +constantes étendues, +validator one-hot | +60 | P1 |
| `src/local_replay_runtime/strategy_ladder_b2_label_store_builder.py` | bump v3, +13 champs nullables, fix augmented_keys | +50 | P1 |
| `src/local_replay_runtime/strategy_ladder_runner.py` | +4 helpers extraction, wire dans compatibility_payload | +180 | P1 |
| `src/local_replay_runtime/expected_edge_feature_promotion_registry.py` | NEW | +220 | P2 |
| `src/local_replay_runtime/expected_edge_feature_ablation_orchestrator.py` | NEW | +280 | P2 |
| `src/cockpit/form_state_support.py` | +2 champs pydantic | +15 | P3 |
| `src/cockpit/strategy_ladder_ml_handoff_support.py` | +helper `discover_lab_feature_governance` | +60 | P3 |
| `src/cockpit/state.py` | +VM `lab_feature_governance` | +20 | P3 |
| `src/cockpit/server.py` | endpoint signature + propagation handoff | +40 | P3 |
| `src/cockpit/templates/pages/lab.html` | refonte feature_names input | +85 | P3 |
| `src/cockpit/static/cockpit.css` | styles feat-badges | +50 | P3 |
| `scripts/run_strategy_ladder_ml_lab_handoff.py` | NE PAS toucher le default (backward-compat CLI) ; ajouter doc string mentionnant SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES | +10 | meta |
| `tests/test_local_replay_runtime/test_expected_edge_training_extended_features.py` | NEW : 12 tests | +250 | P1 |
| `tests/test_local_replay_runtime/test_label_store_row_v3_migration.py` | NEW : 8 tests | +160 | P1 |
| `tests/test_local_replay_runtime/test_bridge_capture_extended.py` | NEW : 10 tests | +220 | P1 |
| `tests/test_local_replay_runtime/test_feature_promotion_registry.py` | NEW : 10 tests | +180 | P2 |
| `tests/test_local_replay_runtime/test_feature_ablation_orchestrator.py` | NEW : 8 tests (avec backtest stub minimal) | +280 | P2 |
| `tests/cockpit/test_lab_feature_picker.py` | NEW : 8 tests | +200 | P3 |

**Total estimé** : ~2360 lignes (dont 1290 tests).

---

## Claims Implemented

### Pilier 1 — Validator + label_store v3 + capture bridge

#### Claim P1-1 : `SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES` étendu

`strategy_ladder_expected_edge_training.py` :
```python
# Existant (F16-B)
DEFAULT_EXPECTED_EDGE_FEATURE_NAMES = ("close_return", "high_low_range", "volume")
REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES = (
    "spread_bps", "slippage_bps", "book_depth_levels", "break_even_bps",
    "fragility_score", "false_breakout_context",
    "vpin", "cumulative_ofi", "queue_pressure",
)

# AJOUTÉ F16-C
EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES = (
    "kyle_lambda",
    "realized_vol_current",
    "realized_vol_at_break",
    "latency_penalty_bps",  # ferme l'incohérence avec _EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS
)
BUILD14_OBSERVED_EXPECTED_EDGE_FEATURE_NAMES = (
    "micro_edge_exit_governor_observed",
    "micro_edge_entry_timing_observed",
)
ENGINE_D_GOVERNANCE_EXPECTED_EDGE_FEATURE_NAMES = (
    "history_score",
    "marginal_value_score",
    "reentry_lateness",
    "concentration_headroom",
)
ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES = (
    "anti_revenge_state__active",
    "anti_revenge_state__cooling",
    "anti_revenge_state__idle",
)

SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES = (
    *DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
    *REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
    *EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
    *BUILD14_OBSERVED_EXPECTED_EDGE_FEATURE_NAMES,
    *ENGINE_D_GOVERNANCE_EXPECTED_EDGE_FEATURE_NAMES,
    *ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES,
)
# Total : 3 + 9 + 4 + 2 + 4 + 3 = 25 features autorisées
```

#### Claim P1-2 : `_validate_feature_names` accepte one-hot suffixes

- Ne rejette pas `anti_revenge_state__active` etc. tant qu'ils sont dans `ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES`
- Validation existante préservée : déduplication, strip, non-vide
- Backward-compat strict : default reste `DEFAULT_EXPECTED_EDGE_FEATURE_NAMES` (3 LEGACY)

#### Claim P1-3 : Schema row v3 backward-compat nullable

`strategy_ladder_b2_label_store_builder.py:342` :
```python
class StrategyLadderB2LabelStoreRow(BaseModel, frozen=True):
    """Canonical supervised label row derived from one B2 replay candidate."""

    # Patch F16-C (2026-05-23) — schema_version bumped v2 → v3 pour ajout des
    # 13 nouveaux champs feature governance (4 microstructure étendue + 2 Build-14
    # observed + 4 engine D governance + 3 anti_revenge_state one-hot).
    # Backward-compat : tous nullables, anciens label stores v2 chargent avec None.
    schema_version: str = Field(default="strategy_ladder.b2_label_store_row.v3", min_length=1)
    # ... 29 champs v2 existants inchangés ...
    # ... 3 champs F16-B (vpin/cumulative_ofi/queue_pressure) inchangés ...

    # F16-C extension microstructure (2026-05-23)
    kyle_lambda: float | None = None
    realized_vol_current: float | None = None
    realized_vol_at_break: float | None = None
    latency_penalty_bps: float | None = None

    # F16-C Build-14 observed values
    micro_edge_exit_governor_observed: float | None = None
    micro_edge_entry_timing_observed: float | None = None

    # F16-C engine D governance scalars
    history_score: float | None = None
    marginal_value_score: float | None = None
    reentry_lateness: float | None = None
    concentration_headroom: float | None = None

    # F16-C anti_revenge_state one-hot (categorical → 3 booleans)
    anti_revenge_state__active: bool | None = None
    anti_revenge_state__cooling: bool | None = None
    anti_revenge_state__idle: bool | None = None
```

#### Claim P1-4 : `_EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS` aligné

Ajouter au tuple `_EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS` :
```python
_EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS = (
    "spread_bps", "slippage_bps", "latency_penalty_bps", "book_depth_levels",
    "break_even_bps",
    "vpin", "cumulative_ofi", "queue_pressure",
    # F16-C ajouts (2026-05-23)
    "kyle_lambda", "realized_vol_current", "realized_vol_at_break",
    "micro_edge_exit_governor_observed", "micro_edge_entry_timing_observed",
    "history_score", "marginal_value_score", "reentry_lateness", "concentration_headroom",
    "anti_revenge_state__active", "anti_revenge_state__cooling", "anti_revenge_state__idle",
)
```

#### Claim P1-5 : Capture bridge étendue

`strategy_ladder_runner.py:1837` — `_extract_bridge_microstructure_scalars` étendu :
```python
def _extract_bridge_microstructure_scalars(
    bridge_or_result: object | None,
) -> dict[str, float | None]:
    scalars: dict[str, float | None] = {
        "vpin": None, "cumulative_ofi": None, "queue_pressure": None,
        # F16-C ajouts
        "kyle_lambda": None,
        "realized_vol_current": None,
        "realized_vol_at_break": None,
    }
    if bridge_or_result is None:
        return scalars
    # Existant : vpin, cumulative_ofi, queue_pressure
    # ...
    # F16-C : kyle_lambda (depuis bridge.kyle_lambda_record si présent)
    kyle_record = getattr(bridge_or_result, "kyle_lambda_record", None)
    if kyle_record is not None:
        try:
            scalars["kyle_lambda"] = float(kyle_record.value)
        except (AttributeError, TypeError, ValueError):
            pass
    # Idem pour realized_vol_current_record et realized_vol_at_break_record
    return scalars
```

#### Claim P1-6 : Helpers extraction nouveaux

Trois nouveaux helpers dans `strategy_ladder_runner.py` :

**a) `_extract_engine_d_governance_scalars(payload, native_output) -> dict`**
Extrait depuis `engine_input_payload` (qui contient déjà ces fields via `_selected_engine_payload_fields:1773-1777`) :
- `history_score`, `marginal_value_score`, `reentry_lateness`, `concentration_headroom`

**b) `_extract_build14_observed_values(build14_application) -> dict`**
Extrait via `_build14_reader_observed_value` :
- `micro_edge_exit_governor_observed`
- `micro_edge_entry_timing_observed`
(le 3e reader `execution_fragility_score` est déjà mappé en `fragility_score` ENRICHED F16-B)

**c) `_extract_anti_revenge_one_hot(payload) -> dict`**
Lit `engine_input_payload["anti_revenge_state"]` (déjà capturé par `_selected_engine_payload_fields:1773`) :
- Mapping `"active" → {active:True, cooling:False, idle:False}`
- Mapping `"cooling" → {active:False, cooling:True, idle:False}`
- Mapping `"idle" → {active:False, cooling:False, idle:True}`
- Mapping default/None → tous None (fail-closed nullable)

**d) `_extract_latency_penalty_bps(native_output, compatibility_payload) -> float | None`**
Lit `latency_penalty_bps` depuis native_output puis compatibility_payload (déjà dans augmented_keys F16-B, juste exposer).

#### Claim P1-7 : Wire dans compatibility_payload

`strategy_ladder_runner.py:~2155-2160` (zone Patch F16-B existante) :
- Appeler les 4 nouveaux helpers
- Merger tous les scalars dans `compatibility_payload`
- Préserver l'ordre existant (microstructure bridge en premier, puis governance D, puis Build-14, puis anti_revenge one-hot)
- Aucune feature ajoutée silencieusement : si extracteur retourne `None`, le champ reste absent du payload

### Pilier 2 — Promotion registry + ablation

#### Claim P2-1 : `ExpectedEdgeFeatureVerdict` StrEnum

```python
from enum import StrEnum

class ExpectedEdgeFeatureVerdict(StrEnum):
    PROMOTED = "PROMOTED"
    NEUTRAL = "NEUTRAL"
    DEMOTED = "DEMOTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
```

#### Claim P2-2 : `FeaturePromotionEntry` pydantic

```python
class FeaturePromotionEntry(BaseModel, frozen=True):
    schema_version: str = Field(default="expected_edge.feature_promotion_entry.v1", min_length=1)
    feature_name: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    timeframe: str = Field(..., min_length=1)
    verdict: ExpectedEdgeFeatureVerdict
    shap_rank: int | None = Field(default=None, ge=1)  # rank 1-based dans le SHAP summary
    shap_mean_abs: float | None = Field(default=None, ge=0.0)
    ablation_delta_psr: float | None = None  # PSR_with - PSR_without (positif = feature aide)
    ablation_delta_sharpe: float | None = None
    ablation_delta_break_even_bps: float | None = None  # négatif = feature réduit le break-even = aide
    ablation_min_btl_satisfied: bool | None = None  # MinBTL Bailey-Borwein-LdP-Zhu 2014
    talab_quadruple_pass: bool | None = None
    last_evaluated_at_ms: int = Field(..., ge=0)
    evidence_artifact_ref: str = ""  # path vers le rapport ablation détaillé
    detail: str = ""
```

#### Claim P2-3 : `FeaturePromotionRegistry` pydantic

```python
class FeaturePromotionRegistry(BaseModel, frozen=True):
    schema_version: str = Field(default="expected_edge.feature_promotion_registry.v1", min_length=1)
    generated_at_ms: int = Field(..., ge=0)
    entries: tuple[FeaturePromotionEntry, ...] = ()

    def lookup(self, pair: str, timeframe: str, feature_name: str) -> FeaturePromotionEntry | None:
        for entry in self.entries:
            if entry.pair == pair and entry.timeframe == timeframe and entry.feature_name == feature_name:
                return entry
        return None

    def entries_for_pair_tf(self, pair: str, timeframe: str) -> tuple[FeaturePromotionEntry, ...]:
        return tuple(e for e in self.entries if e.pair == pair and e.timeframe == timeframe)
```

#### Claim P2-4 : Reader/writer fail-closed

```python
def load_feature_promotion_registry(path: Path) -> FeaturePromotionRegistry:
    """Fail-closed reader : return empty registry if path missing/invalid."""
    if not path.is_file():
        return FeaturePromotionRegistry(generated_at_ms=_now_ms(), entries=())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return FeaturePromotionRegistry.model_validate(payload)
    except (OSError, ValueError):
        # Fail-closed : log structured + retourner empty registry
        return FeaturePromotionRegistry(generated_at_ms=_now_ms(), entries=())

def save_feature_promotion_registry(path: Path, registry: FeaturePromotionRegistry) -> None:
    """Atomic JSON write with sorted keys for deterministic hashing."""
    atomic_write_json(path, registry.model_dump(mode="json"), indent=2)
```

#### Claim P2-5 : `FeatureAblationRequest` + `FeatureAblationReport`

```python
class FeatureAblationRequest(BaseModel, frozen=True):
    feature_name: str = Field(..., min_length=1)
    baseline_artifact_path: Path  # artifact entraîné AVEC la feature
    label_store_dataset_path: Path  # dataset à utiliser pour re-training sans feature
    backtest_inputs_path: Path  # même fenêtre OOS que baseline
    pair: str = Field(..., min_length=1)
    timeframe: str = Field(..., min_length=1)
    min_btl: int = Field(default=252, ge=10)  # Bailey-Borwein-LdP-Zhu 2014 default 1 an
    talab_quadruple_required: bool = True

class FeatureAblationReport(BaseModel, frozen=True):
    schema_version: str = Field(default="expected_edge.feature_ablation_report.v1", min_length=1)
    feature_name: str
    pair: str
    timeframe: str
    baseline_psr: float | None = None
    ablated_psr: float | None = None
    delta_psr: float | None = None  # baseline - ablated
    baseline_sharpe: float | None = None
    ablated_sharpe: float | None = None
    delta_sharpe: float | None = None
    baseline_break_even_bps: float | None = None
    ablated_break_even_bps: float | None = None
    delta_break_even_bps: float | None = None
    min_btl_satisfied: bool
    talab_quadruple_pass: bool
    verdict: ExpectedEdgeFeatureVerdict
    evidence_artifact_ref: str = ""
    blockers: tuple[str, ...] = ()
```

#### Claim P2-6 : `run_feature_ablation` orchestrator

```python
def run_feature_ablation(request: FeatureAblationRequest) -> FeatureAblationReport:
    """Leave-one-out ablation : re-train sans la feature, re-backtest, diff vs baseline.

    Steps :
    1. Load baseline artifact (lecture seule, fait foi pour `feature_names` set complet)
    2. Build feature_names = baseline.feature_names \ {request.feature_name}
    3. Re-train (avec même seed, même hparams, même validation cut) → ablated artifact
    4. Re-backtest sur backtest_inputs_path (même fenêtre OOS) → ablated metrics
    5. Compute delta_psr, delta_sharpe, delta_break_even_bps
    6. Apply MinBTL check (sample size >= request.min_btl)
    7. Apply Talab quadruple filter (stability, non-regression, scale-invariance, anti-fragility)
    8. Compute verdict via compute_feature_promotion_verdict()
    9. Emit FeatureAblationReport + persister evidence artifact
    """
    # Implémentation détaillée TBD par Codex selon les modules training/backtest existants
```

#### Claim P2-7 : `compute_feature_promotion_verdict` logic centrale

```python
def compute_feature_promotion_verdict(
    *,
    shap_rank: int | None,
    shap_mean_abs: float | None,
    delta_psr: float | None,
    delta_sharpe: float | None,
    delta_break_even_bps: float | None,
    min_btl_satisfied: bool,
    talab_quadruple_pass: bool,
    thresholds: FeaturePromotionThresholds,
) -> ExpectedEdgeFeatureVerdict:
    """Verdict logic — NO MAGIC NUMBERS, tous seuils dans thresholds (calibration seam).

    Logic :
    - INSUFFICIENT_EVIDENCE si min_btl non satisfait OU données manquantes (delta_psr is None)
    - DEMOTED si delta_psr < -thresholds.psr_demote_threshold OR delta_sharpe < -thresholds.sharpe_demote_threshold
      OR (talab_quadruple_required AND not talab_quadruple_pass)
    - PROMOTED si delta_psr > thresholds.psr_promote_threshold AND delta_sharpe > thresholds.sharpe_promote_threshold
      AND shap_rank <= thresholds.shap_top_n AND talab_quadruple_pass
    - NEUTRAL sinon
    """
```

Avec `FeaturePromotionThresholds` pydantic :
```python
class FeaturePromotionThresholds(BaseModel, frozen=True):
    schema_version: str = Field(default="expected_edge.feature_promotion_thresholds.v1", min_length=1)
    # Defaults TO_CALIBRATE — passés en paramètres explicites par caller, JAMAIS hardcoded
    psr_promote_threshold: float = Field(..., ge=0.0)
    psr_demote_threshold: float = Field(..., ge=0.0)
    sharpe_promote_threshold: float = Field(..., ge=0.0)
    sharpe_demote_threshold: float = Field(..., ge=0.0)
    break_even_promote_bps: float = Field(..., ge=0.0)
    break_even_demote_bps: float = Field(..., ge=0.0)
    shap_top_n: int = Field(..., ge=1)
    calibration_status: str = Field(default="TO_CALIBRATE", min_length=1)
```

### Pilier 3 — UI Lab feature picker

#### Claim P3-1 : `LabMlHandoffFormState` backward-compat

```python
class LabMlHandoffFormState(BaseModel, frozen=True):
    # ... champs existants ...
    feature_names: str = "close_return,high_low_range,volume"  # backward-compat CLI/persistence
    # F16-C ajouts (2026-05-23)
    selected_features: tuple[str, ...] = ()  # priorité sur feature_names si non-vide
    discovered_feature_governance: tuple[FeaturePromotionEntry, ...] = ()  # audit-trail render-time
```

Rule : si `selected_features` non-vide → utiliser ; sinon parser `feature_names` CSV (backward-compat).

#### Claim P3-2 : `discover_lab_feature_governance` helper

```python
def discover_lab_feature_governance(
    form_state: LabMlHandoffFormState,
    *,
    registry_path: Path | None = None,
) -> tuple[FeaturePromotionEntry, ...]:
    """Lit feature_promotion_registry.json pour (pair, timeframe) du form_state.

    Si registry absent ou pas d'entries pour ce pair/tf → retourne tuple vide.
    Le caller (state.py) handle le fallback (toutes features affichées avec badge N-A).
    """
    if registry_path is None:
        # Default path : <jobs_root>/feature_promotion_registry.json
        return ()
    registry = load_feature_promotion_registry(registry_path)
    pair = (form_state.selected_pairs[0] if form_state.selected_pairs else form_state.pair) or "BTCUSDT"
    return registry.entries_for_pair_tf(pair, form_state.timeframe)
```

#### Claim P3-3 : VM `lab_feature_governance`

`src/cockpit/state.py:~848` (zone existante avec `lab_discovered_pair_capabilities`) :
```python
from cockpit.strategy_ladder_ml_handoff_support import (
    discover_lab_pair_capabilities,
    discover_lab_feature_governance,  # NEW
)

lab_discovered_pair_capabilities = discover_lab_pair_capabilities(lab_ml_handoff_form)
# F16-C — Pilier 3
lab_feature_governance = discover_lab_feature_governance(
    lab_ml_handoff_form,
    registry_path=jobs_root / "feature_promotion_registry.json" if jobs_root else None,
)
```

#### Claim P3-4 : Template Lab refonte

Remplacer `<input type="text" name="feature_names">` par :
```html
<div class="feature-picker">
  {% for feature_name in supported_feature_names %}
    {% set entry = lab_feature_governance | selectattr('feature_name', 'equalto', feature_name) | first %}
    {% set verdict = entry.verdict if entry else 'N-A' %}
    <label class="feature-picker__item">
      <input type="checkbox" name="selected_features" value="{{ feature_name }}"
        {% if feature_name in handoff_form.selected_features or (not handoff_form.selected_features and feature_name in handoff_form.feature_names.split(',')) %}checked{% endif %} />
      <span class="feature-picker__label">{{ feature_name }}</span>
      <span class="feat-badge feat-badge--{{ verdict | lower }}" title="{% if entry %}ΔPSR={{ entry.ablation_delta_psr }}, SHAP rank={{ entry.shap_rank }}, talab_pass={{ entry.talab_quadruple_pass }}{% else %}Pas d'évaluation pour ce pair/tf{% endif %}">{{ verdict }}</span>
    </label>
  {% endfor %}
</div>
<!-- Fallback : préserver le CSV pour CLI compat -->
<input type="hidden" name="feature_names" value="{{ handoff_form.feature_names }}" />
```

Avec `supported_feature_names` passé depuis state.py = `SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES`.

#### Claim P3-5 : Endpoint `_build_lab_handoff_form_state` accepte `selected_features`

`server.py` :
```python
async def _build_lab_handoff_form_state(
    request: Request,
    # ... params existants ...
    selected_features: list[str] | None = None,
) -> LabMlHandoffFormState:
    # ...
    return LabMlHandoffFormState(
        # ...
        selected_features=tuple(dict.fromkeys(selected_features or [])),
        # ...
    )
```

#### Claim P3-6 : Propagation vers `StrategyLadderMlLabHandoffRequest`

```python
# server.py — quand on submit le form Lab
effective_feature_names = (
    lab_form.selected_features
    if lab_form.selected_features
    else tuple(part.strip() for part in lab_form.feature_names.split(",") if part.strip())
)
handoff_request = StrategyLadderMlLabHandoffRequest(
    # ...
    feature_names=effective_feature_names,
    # ...
)
```

#### Claim P3-7 : Doctrine fail-closed UI

- Si user décoche TOUTES les features → server retourne 400 + message « ≥1 feature requise ; default reset au minimal 3 »
- Si user coche une feature avec verdict `DEMOTED` → warning UI inline (pas de blocage) : « Cette feature a été démontrée comme nuisible au backtest précédent ; cocher manuellement override le verdict gouverné »
- Pas de validation pydantic stricte sur `selected_features` (zero hardcode), juste check via `_validate_feature_names` du request (qui rejette unsupported names)

---

## Tests and Proof

### Pilier 1

**Fichier `tests/test_local_replay_runtime/test_expected_edge_training_extended_features.py`** :

| # | Test | Vérifie |
|---|---|---|
| 1 | `test_supported_features_count_25` | `len(SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES) == 25` (3+9+4+2+4+3) |
| 2 | `test_validator_accepts_kyle_lambda` | feature_names tuple avec `kyle_lambda` passe |
| 3 | `test_validator_accepts_anti_revenge_one_hot_triplet` | les 3 booléens passent |
| 4 | `test_validator_rejects_partial_anti_revenge_one_hot` | un seul sur 3 → erreur (les 3 doivent venir ensemble) |
| 5 | `test_validator_rejects_unknown_feature` | `"rsi_14"` rejeté |
| 6 | `test_validator_default_backward_compat` | sans feature_names → 3 LEGACY |
| 7 | `test_validator_dedup_preserves_order` | `("vpin","vpin","kyle_lambda")` → `("vpin","kyle_lambda")` |
| 8 | `test_legacy_kline_only_lock_unchanged` | `_require_supported_legacy_features` lock à 3 préservé |
| 9 | `test_latency_penalty_bps_now_validatable` | ferme l'incohérence pré-F16-C |
| 10 | `test_build14_observed_features_present_in_set` | les 2 Build-14 sont là |
| 11 | `test_engine_d_governance_features_present` | les 4 sont là |
| 12 | `test_extended_microstructure_features_present` | les 4 sont là |

**Fichier `tests/test_local_replay_runtime/test_label_store_row_v3_migration.py`** :

| # | Test | Vérifie |
|---|---|---|
| 1 | `test_schema_version_v3_default` | nouveau row a `schema_version == "...v3"` |
| 2 | `test_old_v2_payload_loads_with_none_defaults` | payload v2 → row v3 valide, nouveaux champs None |
| 3 | `test_temporal_invariant_unchanged` | validator `feature_timestamp_ms <= decision_timestamp_ms` préservé |
| 4 | `test_anti_revenge_one_hot_nullable_triplet` | les 3 bool acceptent None |
| 5 | `test_anti_revenge_one_hot_full_active` | `{active:True, cooling:False, idle:False}` valide |
| 6 | `test_kyle_lambda_finite_only` | NaN/Inf rejetés via validator |
| 7 | `test_augmented_keys_aligned_with_validator` | `_EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS` ⊆ `SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES` |
| 8 | `test_serialized_json_deterministic` | dump → load → dump produit même hash |

**Fichier `tests/test_local_replay_runtime/test_bridge_capture_extended.py`** :

| # | Test | Vérifie |
|---|---|---|
| 1 | `test_extract_bridge_extended_kyle_lambda` | mock bridge avec `kyle_lambda_record.value=0.0023` → scalars["kyle_lambda"]==0.0023 |
| 2 | `test_extract_bridge_realized_vol_current` | idem realized_vol_current |
| 3 | `test_extract_bridge_realized_vol_at_break` | idem realized_vol_at_break |
| 4 | `test_extract_bridge_missing_records_return_none` | bridge sans attributes → all None |
| 5 | `test_extract_engine_d_governance_scalars` | mock payload avec 4 fields → dict retourne les 4 |
| 6 | `test_extract_build14_observed_values` | mock Build14Application avec 2 readers → 2 valeurs |
| 7 | `test_extract_anti_revenge_one_hot_active` | `"active"` → `{active:True, cooling:False, idle:False}` |
| 8 | `test_extract_anti_revenge_one_hot_cooling` | `"cooling"` |
| 9 | `test_extract_anti_revenge_one_hot_idle` | `"idle"` |
| 10 | `test_extract_anti_revenge_one_hot_unknown_returns_all_none` | `"foobar"` → 3× None (fail-closed nullable) |

### Pilier 2

**Fichier `tests/test_local_replay_runtime/test_feature_promotion_registry.py`** :

| # | Test | Vérifie |
|---|---|---|
| 1 | `test_empty_registry_default` | `FeaturePromotionRegistry()` valide avec entries=() |
| 2 | `test_registry_lookup_by_pair_tf_feature` | lookup retourne bonne entry ou None |
| 3 | `test_registry_entries_for_pair_tf_filter` | filtre correct |
| 4 | `test_load_missing_file_returns_empty_registry` | fail-closed read |
| 5 | `test_load_invalid_json_returns_empty_registry` | fail-closed read |
| 6 | `test_save_load_roundtrip_deterministic` | save + load = même registry |
| 7 | `test_verdict_enum_4_values` | PROMOTED, NEUTRAL, DEMOTED, INSUFFICIENT_EVIDENCE |
| 8 | `test_entry_schema_v1` | schema_version constant |
| 9 | `test_registry_schema_v1` | schema_version constant |
| 10 | `test_atomic_write_no_partial_file` | crash mid-write ne corrompt pas |

**Fichier `tests/test_local_replay_runtime/test_feature_ablation_orchestrator.py`** :

| # | Test | Vérifie |
|---|---|---|
| 1 | `test_ablation_promotes_when_positive_psr_delta` | mock baseline PSR=0.92, ablated=0.85 → delta=+0.07 → PROMOTED (avec talab pass) |
| 2 | `test_ablation_demotes_when_negative_psr_delta` | baseline=0.85, ablated=0.92 → DEMOTED |
| 3 | `test_ablation_insufficient_evidence_when_min_btl_unmet` | trades < min_btl → INSUFFICIENT_EVIDENCE |
| 4 | `test_ablation_neutral_when_within_thresholds` | delta dans bande neutre |
| 5 | `test_ablation_demoted_when_talab_quadruple_fails` | même si PSR positif, talab fail → DEMOTED |
| 6 | `test_compute_verdict_no_magic_numbers` | thresholds explicites required, default TO_CALIBRATE non-utilisable directement |
| 7 | `test_report_evidence_artifact_persisted` | rapport JSON écrit sur disque |
| 8 | `test_apply_to_registry_replaces_existing_entry` | promotion remplace l'entry existante (pair,tf,feature) |

### Pilier 3

**Fichier `tests/cockpit/test_lab_feature_picker.py`** :

| # | Test | Vérifie |
|---|---|---|
| 1 | `test_lab_form_state_selected_features_backward_compat` | `LabMlHandoffFormState(feature_names="a,b,c")` → `selected_features=()` |
| 2 | `test_lab_form_state_selected_features_priority` | `selected_features=("a","b")` ignore `feature_names` |
| 3 | `test_discover_lab_feature_governance_missing_registry_returns_empty` | path missing → tuple() |
| 4 | `test_discover_lab_feature_governance_filters_by_pair_tf` | seules les entries du bon pair/tf retournées |
| 5 | `test_sync_handoff_uses_selected_features_when_present` | request handoff a bon feature_names |
| 6 | `test_template_renders_supported_feature_count_25` | smoke render-time |
| 7 | `test_template_feature_badge_class_matches_verdict` | `PROMOTED → feat-badge--promoted` etc. |
| 8 | `test_endpoint_rejects_empty_selected_features` | server retourne 400 si tous décochés |

### Commandes audit (Opus pré-GREENLIGHT)

```powershell
# Pilier 1
rtk pytest tests/test_local_replay_runtime/test_expected_edge_training_extended_features.py -v
rtk pytest tests/test_local_replay_runtime/test_label_store_row_v3_migration.py -v
rtk pytest tests/test_local_replay_runtime/test_bridge_capture_extended.py -v

# Pilier 2
rtk pytest tests/test_local_replay_runtime/test_feature_promotion_registry.py -v
rtk pytest tests/test_local_replay_runtime/test_feature_ablation_orchestrator.py -v

# Pilier 3
rtk pytest tests/cockpit/test_lab_feature_picker.py -v

# Régression
rtk pytest tests/test_local_replay_runtime/ -v  # full local_replay_runtime
rtk pytest tests/cockpit/ -v  # full cockpit
rtk python -m dag_validator  # structural

# Guardrails
rtk python scripts/check_engineering_guardrails.py --files \
  src/local_replay_runtime/strategy_ladder_expected_edge_training.py \
  src/local_replay_runtime/strategy_ladder_b2_label_store_builder.py \
  src/local_replay_runtime/strategy_ladder_runner.py \
  src/local_replay_runtime/expected_edge_feature_promotion_registry.py \
  src/local_replay_runtime/expected_edge_feature_ablation_orchestrator.py \
  src/cockpit/form_state_support.py \
  src/cockpit/strategy_ladder_ml_handoff_support.py \
  src/cockpit/state.py \
  src/cockpit/server.py \
  src/cockpit/templates/pages/lab.html \
  src/cockpit/static/cockpit.css
```

**Slots remplis post-exécution (à compléter par Codex)** :

- [ ] **pytest_pilier_1** : XX passed — `tests/test_local_replay_runtime/test_expected_edge_training_extended_features.py + test_label_store_row_v3_migration.py + test_bridge_capture_extended.py`
- [ ] **pytest_pilier_2** : XX passed — `tests/test_local_replay_runtime/test_feature_promotion_registry.py + test_feature_ablation_orchestrator.py`
- [ ] **pytest_pilier_3** : XX passed — `tests/cockpit/test_lab_feature_picker.py`
- [ ] **pytest_regression_local_replay** : XX passed (baseline X)
- [ ] **pytest_regression_cockpit** : XX passed (baseline X)
- [ ] **dag_validator** : PASS / FAIL + détails
- [ ] **guardrails new_violations** : 0 / N + détails
- [ ] **diff stat F16-C only** : (liste fichiers + lignes)

---

## Deferred / Not Done

- **Auto-application du verdict** : F16-C expose les verdicts dans l'UI mais ne re-trigger PAS automatiquement un re-train post-DEMOTION. User décide via UI. (Si automatisation souhaitée → F16-D.)
- **Multi-pair feature governance native** : chaque pair a son registry séparé, pas de pondération cross-pair (compatible doctrine MONO-PAIR training [[doctrine-c1-multi-pair-training-2026-05-21]]).
- **Auto-calibration des thresholds** : `FeaturePromotionThresholds` est passé explicitement, default `TO_CALIBRATE` (cohérent avec engine A/B `structure_unfavorable`/`no_excess` thresholds [[p0b-engines-a-b-root-cause]]). Calibration formelle = chantier séparé.
- **Permutation importance complement** : SHAP-only + ablation P&L. Permutation importance pourrait enrichir mais ajoute coût + risque corrélations colinéaires (reporté F16-D si besoin).
- **Backtest stub minimal pour test_feature_ablation_orchestrator** : ablation orchestrator dépend du module backtest existant ; tests peuvent stubber le re-backtest ou exécuter un mini-backtest sur dataset synthétique (TBD Codex selon faisabilité).
- **CLI `--feature-names` default INCHANGÉ** : backward-compat strict pour scripts/CI existants. User ajoute features via UI Lab (Pilier 3) ou flag CLI explicite. Ne PAS changer le default tant que F16-C n'est pas validé en run audité.

---

## Risks

| Risque | Mitigation |
|---|---|
| Re-training ablation explose en coût (N+1 trainings par run) | Ablation lazy : ne re-train QUE les features cochées par user au backtest précédent ; orchestrator skip features `NEUTRAL`/`INSUFFICIENT_EVIDENCE` connues |
| Schema v3 casse anciens stores v2 | Backward-compat nullable strict, tests dédiés `test_old_v2_payload_loads_with_none_defaults` |
| One-hot anti_revenge_state pollue feature_names si état futur ajouté | Validator rejette partial one-hot (test #4 P1) ; nouvel état = bump constante explicite |
| UI surcharge avec 25 checkboxes | Template groupe visuel : section LEGACY / ENRICHED / EXTENDED / BUILD14 / D_GOVERNANCE / ANTI_REVENGE (CSS class par groupe) |
| Verdict `DEMOTED` user override silencieux | Warning UI inline + log structured `EXPECTED_EDGE_FEATURE_USER_OVERRIDE_DEMOTED` pour audit |
| `kyle_lambda_record` n'existe pas dans le bridge actuel | Vérifier en Phase 0 reconnaissance ; si absent, ajouter calcul dans `engine_native_adapter.py` ou downgrade ce feature à NEUTRAL avec evidence_class `BRIDGE_FEATURE_NOT_PROVEN_F16C` |
| `realized_vol_*` déjà calculés mais pas exposés en bridge_record | Idem : Phase 0 reconnaissance avant promesse |
| Codex sur-engineer les thresholds defaults | Spec explicite `TO_CALIBRATE` + tests #6 P2 enforce thresholds explicites requis |
| MinBTL=252 trop strict pour pair/tf à bas trade volume | `min_btl` paramétrable dans request, default doctrinal 252 (Bailey-Borwein-LdP-Zhu 2014) |
| Tests cockpit nouveaux cassent baseline existant | Tests F16-C séparés (nouveau fichier), pas d'édition tests existants |

---

## Completion Status (slot — à remplir post-exécution)

- [ ] **COMPLETE / PARTIAL / BLOCKED**

**Preuves attendues** :
- 56+ tests F16-C dédiés PASS (12+8+10+10+8+8)
- Régression local_replay_runtime + cockpit baseline ≥ pré-F16-C
- 0 violations guardrails sur 11 fichiers F16-C
- DAG validator PASS
- Diff stat ne touche QUE les fichiers listés dans "Files Changed"

---

## Next Safe Step (slot — à remplir post-GREENLIGHT)

- [ ] **Phase 0 reconnaissance Codex** (avant claims P1-5/P1-6) :
  - Vérifier existence `bridge.kyle_lambda_record`, `bridge.realized_vol_current_record`, `bridge.realized_vol_at_break_record` dans `engine_native_adapter.py:586-630`
  - Si absent : décider (a) downgrade le feature en INSUFFICIENT_EVIDENCE, (b) ajouter calcul dans `engine_native_adapter.py` (scope expansion), (c) reporter à F16-C2
- [ ] **Calibration thresholds F16-C** : produire spec calibration thresholds promotion (psr_promote, psr_demote, sharpe_*, break_even_*, shap_top_n) sur dataset historique
- [ ] **Run P0-A Phase 1 avec feature_names étendu** : test end-to-end avec UI Lab Pilier 3, valider verdict registry après backtest aval
- [ ] **F16-D (optionnel)** : auto-application verdict + permutation importance complement

---

## Opus audit checklist

Quand Codex remonte status, Opus doit vérifier :

1. **Tests dédiés** : 56+ tests F16-C PASS (count exact dans slots)
2. **Régression** : `pytest tests/test_local_replay_runtime/ tests/cockpit/` baseline ≥ pré-F16-C (zéro nouveau FAIL non pré-existant)
3. **DAG** : `python -m dag_validator` PASS
4. **Guardrails** : `new_violations=0` sur les 11 fichiers F16-C
5. **Diff stat** : `git diff --stat` ne touche QUE les fichiers listés "Files Changed" (pas de creep)
6. **Doctrine V5.3** :
   - Aucun magic number dans `compute_feature_promotion_verdict` (thresholds passés explicitement)
   - Schema v3 backward-compat avec v2 (test dédié PASS)
   - Anti_revenge_state one-hot triplet rejette partial (test dédié PASS)
   - `_EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS` ⊆ `SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES` (test dédié PASS)
   - CLI default `--feature-names` INCHANGÉ (grep dans diff)
7. **Audit-ready** :
   - `FeaturePromotionEntry.evidence_artifact_ref` populé pour chaque verdict
   - `FeatureAblationReport` persisté sur disque
   - Verdict `DEMOTED` user override log structured `EXPECTED_EDGE_FEATURE_USER_OVERRIDE_DEMOTED`
8. **UI smoke** : page `/lab` render-time avec multi-select visible + badges, pas de 500
9. **Three lines mandatory verdict** : pytest pass count concret + guardrails new_violations=0 + git diff --stat in-scope only AVANT verdict line

**Verdict ligne finale** : `GREENLIGHT` ou `REQUEST_FIX` + line-level feedback.
