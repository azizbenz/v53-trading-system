# Spec Opus→Codex — Session 20h : arbitrage fixes + P1 S32 + splits + adapters A/B/C/D + W-13/14/15 stubs

**Date** : 2026-04-21
**Auteur Opus** : session critique path MICRO_LIVE post-arbitrage 2026-04-21
**Budget** : 20h Codex, 4 jours × 5h (ou 2 sessions × 10h)
**Prerequis** : commit `49669ce` mergé, MEMORY.md hook "Session 2026-04-21" à jour
**Références arbitrage** : `2026-04-21_smoke_engine_b_flow_coherence_alignment.md` + `2026-04-21_manifest_registry_stage_naming_restore.md` + `2026-04-21_stage_naming_vs_profile_naming.md`

---

## 0 · Objectif maître

Clôturer le chemin critique pré-**MICRO_LIVE** en une session unique auditée Opus :

1. Consommer les 2 arbitrages 2026-04-21 (SMOKE_OBSOLETE + REGISTRY_RESTORE)
2. Débloquer P1 S32 : `test_engine_a_runtime_downstream` + cascade 691 tests
3. Fermer l'unique oversize src/ hors UI legacy : `src/protocols/live_light_runtime.py` 718L → 2 fichiers < 700L
4. Rattraper adapters A/B inline (prompt v2 prêt), étendre à C/D
5. Écrire W-13 Live-Light **full wiring** (plus stub) — seam déjà existant, il faut fermer les gates
6. Écrire W-15 Engine C **skeleton** (doc 21) jusqu'à test canonique vert
7. Écrire W-14 seam enabler (bridge Build-14)
8. Garder DAG PASS + `new_violations=0` + guardrails verts tout du long

**Contrat** : une seule solution complète (pas de profil LIGHT), R-QUANT-FIRST respecté (aucune formule PSR/DSR/POT-GPD/Energy touchée), fichiers `src/` jamais baselinés pour `FILE_TOO_LONG`.

---

## 1 · Docs governants

| Rang | Doc | Rôle |
|---|---|---|
| 1 | `docs/production_deployment_plan/18_CODE_VS_PLAN_AUDIT_AND_WORK_PLAN.md` | work items W-01..W-25, statut |
| 2 | `docs/production_deployment_plan/19_PRODUCTION_DEPLOYMENT_PLAN.md` | phases calibration, Shadow → Micro-live → Live |
| 3 | `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md` | règles Taleb, conditioning, coordination |
| 4 | `docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md` | Engine C contract + gates |
| 5 | `docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md` | Engine D contract + gates |
| 6 | `docs/production_deployment_plan/09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md` | slicing rules pour Codex |
| 7 | `docs/specs/V5_3_BUILD17_SPEC_UI_COMPLETE_LIVE_COMPLETE.md` | titre canon Build-17 |
| 8 | `docs/specs/V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md` | table promotion |
| 9 | `docs/production_deployment_plan/update_audit/2026-04-21_ia_lab_slices_0_to_5.md` | état IA-Lab slices GREENLIGHT |
| 10 | CLAUDE.md §"Profile discipline", §"Code discipline" | anti-LIGHT-profile, cap 700L, DAG |

**Doctrine transverse** (R-QUANT-FIRST) : ne **jamais** modifier `src/calibration_methods/psr.py`, `dsr.py`, `pot_gpd.py`, `energy_distance.py` — formules gelées.

---

## 2 · Découpage des 20 heures

| Phase | Durée | Titre | Livrable | Dépendance |
|---|---|---|---|---|
| **P0** | 0.5h | Exécution arbitrage A (smoke engine B) | `scripts/run_build9_core_smoke.py` fixé | spec smoke |
| **P1** | 0.5h | Exécution arbitrage B (registry stage names) | registry + test fixés | spec registry |
| **P2** | 2h | Diagnose + fix P1 S32 `test_engine_a_runtime_downstream` | 691 tests verts | état courant repo |
| **P3** | 1.5h | Split `src/protocols/live_light_runtime.py` 718L → 2 fichiers < 700L | `live_light_runtime.py` + `live_light_runtime_support.py` | P2 (tests verts) |
| **P4** | 2h | Adapters A/B inline v2 (prompt v2 prêt) | `engine_a_adapter_inline.py` + `engine_b_adapter_inline.py` | P3 |
| **P5** | 3h | Adapters C/D inline (étend pattern v2) | `engine_c_adapter_inline.py` + `engine_d_adapter_inline.py` | P4 |
| **P6** | 4h | W-13 Live-Light protocol close gates (seam existe, fermer logic) | gates G-13.1..G-13.4 implémentées | P5 |
| **P7** | 4h | W-15 Engine C skeleton jusqu'à test canonique | `engine_c_runner.py` + test EMIT favorable | W-13 |
| **P8** | 1.5h | W-14 seam enabler (bridge Build-14 → Build-15/16) | `enabler_bridge.py` | W-15 |
| **P9** | 1h | Commit unique + audit final Opus | commit + rapport | tout |

Total : **20h**. Marge : ±5% toléré par phase, mais le total cible 20h strict.

---

## 3 · Détail par phase

### P0 — Arbitrage A : Smoke Engine B flow_coherence

**Référence** : `docs/production_deployment_plan/update_audit/2026-04-21_smoke_engine_b_flow_coherence_alignment.md`

**Action mécanique** : ajouter `flow_coherence=0.8,` dans le bloc `EngineBInput` de `_run_engine_chain` (scripts/run_build9_core_smoke.py L163-184).

**Diff attendu** : `1 file changed, 1 insertion(+)`.

**Test** : `rtk python -m pytest tests/test_execution_backbone/test_build9_core_smoke_script.py -xvs` → 5 passed.

**Slot completion** : `___`

---

### P1 — Arbitrage B : Manifest registry stage naming

**Référence** : `docs/production_deployment_plan/update_audit/2026-04-21_manifest_registry_stage_naming_restore.md`

**Actions mécaniques (5 lignes)** :
1. `src/manifest_registry/build_order_registry.py` L116 : `"Micro-live Runtime"` → `"Micro-live"`
2. idem L122 : `"Live Runtime"` → `"Live-Light"`
3. idem L146 : `"Operator UI + Live Extension"` → `"UI Complete + Live-Complete"`
4. `tests/test_manifest_registry/test_build_order.py` L52 docstring : `"Micro-live Light"` → `"Micro-live"`
5. idem L55 assert : `"Micro-live Light"` → `"Micro-live"`

**Diff attendu** : `2 files changed, 5 insertions(+), 5 deletions(-)`.

**Test** : `rtk python -m pytest tests/test_manifest_registry/ -xvs` → ALL passed.

**Slot completion** : `___`

---

### P2 — P1 S32 : `test_engine_a_runtime_downstream` + 691 tests

#### P2.1 Diagnose (30 min)

Exécuter successivement :

```bash
rtk python -m pytest tests/test_engines/test_engine_a/test_engine_a_runtime_downstream.py --collect-only 2>&1 | head -40
rtk python -m pytest tests/test_engines/test_engine_a/test_engine_a_runtime_downstream.py::test_runtime_risk_reason_codes_tolerate_blank_or_none_dominant_reason_code -xvs 2>&1 | tail -60
rtk python -m pytest tests/test_engines/test_engine_a/ -x --tb=short 2>&1 | tail -40
```

Capturer :
- Si collection error : message `ImportError` exact + symbole manquant
- Si runtime error sur `_base_risk_evaluation()` : traceback complet
- Nombre exact de tests affectés (`X errors` / `X failed`)

**Symboles critiques à valider** (tous doivent exister dans `tests/test_engines/test_engine_a/test_engine_a_runtime.py`) :
- `_base_risk_evaluation` (L126 attendu)
- `_detail_only_pre_entry_hook` (L164 attendu)
- `_FixedRiskRuntime` (L141 attendu)
- `_good_engine_inputs`, `_portfolio_state`, `_runtime`, `_runtime_input`

**Slot diagnose result** : `___` (coller 5-10 lignes clés du traceback)

#### P2.2 Fix (1h)

Selon diagnose :

**Hypothèse A** — pyc stale / cache Python :
```bash
rtk find tests/test_engines/test_engine_a -name "__pycache__" -type d -exec rm -rf {} +
rtk find src/engines/engine_a -name "__pycache__" -type d -exec rm -rf {} +
rtk python -m pytest tests/test_engines/test_engine_a -q
```

**Hypothèse B** — symbol moved post-FU-1 split :
Si un symbole a été déplacé dans `engine_a_runtime_support.py` (créé par FU-1), ajouter un ré-export dans `src/engines/engine_a/__init__.py` OU corriger l'import dans `test_engine_a_runtime.py` ligne par ligne.

**Hypothèse C** — signature change fixture `_base_risk_evaluation()` :
Vérifier que la signature `RiskEvaluation` n'a pas évolué depuis la dernière exécution verte. Si oui, mettre à jour le retour de la fixture.

**Règle absolue** : aucune modification de `src/engines/engine_a/**` pour forcer la compatibilité du test. Si un symbole a été *intentionnellement* renommé, le test suit.

#### P2.3 Non-régression (30 min)

```bash
rtk python -m pytest tests/test_engines/test_engine_a -q --tb=short
rtk python -m pytest tests/test_engines -q --tb=line
rtk python -m dag_validator
rtk python -m engineering_guardrails --format=stat
```

Attendu : `40+ passed` engine_a local, DAG PASS, `new_violations=0`.

**Slot completion** : `___`
**Slot pytest count** : `___ passed`

---

### P3 — Split `src/protocols/live_light_runtime.py` 718L → 2 fichiers < 700L

#### P3.1 Contexte

Fichier actuellement 718L (18 au-dessus du cap). Contient :
- `LiveLightInput` / `LiveLightDecision` / `LiveLightRunSummary` — contracts typés (canon Build-13)
- Runtime class `LiveLightRuntime`
- Helpers de projection / reconciliation

**Règle** : aucune rupture de l'API publique. Tout ré-export via `src/protocols/__init__.py` (pattern FU-1).

#### P3.2 Découpe proposée

Après lecture du fichier, créer :

| Fichier | Cible LOC | Contenu |
|---|---|---|
| `src/protocols/live_light_runtime.py` | ≤ 450L | `LiveLightRuntime` class + orchestration principale |
| `src/protocols/live_light_runtime_support.py` (nouveau) | ≤ 300L | helpers projection, reconciliation, reason codes |

**Contracts typés** (`LiveLightInput`, `LiveLightDecision`, `LiveLightRunSummary`) : rester dans `live_light_runtime.py` (seam stable d'import externe).

#### P3.3 Étapes

1. Lire `live_light_runtime.py` complet, identifier les fonctions privées `_*` (candidates extraction) et les classes/dataclasses publiques (restent)
2. Extraire toutes les fonctions `_*` utilitaires dans `_support.py`
3. Dans `live_light_runtime.py` : `from .live_light_runtime_support import _helper_1, _helper_2, ...`
4. Vérifier qu'aucun caller externe ne référence les `_*` (ils sont privés par convention)
5. Mettre à jour `src/protocols/__init__.py` si nécessaire (seuls les symboles publics)

#### P3.4 Tests

```bash
rtk python -m pytest tests/test_protocols -q --tb=short
rtk python -m pytest tests/test_execution_backbone -q --tb=short
rtk python -m dag_validator
rtk python -m engineering_guardrails --format=stat
rtk wc -l src/protocols/live_light_runtime.py src/protocols/live_light_runtime_support.py
```

Attendu :
- `test_protocols` : tous verts
- `test_execution_backbone` : tous verts
- DAG PASS (aucun nouvel import croisé non gouverné)
- `new_violations=0`
- Les 2 fichiers `< 700L` chacun

**Slot completion** : `___`
**Slot LOC final** : `live_light_runtime.py=___L, live_light_runtime_support.py=___L`

---

### P4 — Adapters A/B inline v2

#### P4.1 Source

Appliquer les corrections critiques de `project_v53_adapters_status_2026_04_21.md` (memory) :

| Config | Engine A | Engine B |
|---|---|---|
| `max_abs_forecast` | 20 | **15** |
| `volatility_formula` | `local_std/price` | `local_std/price` |
| `horizon_default` | MEDIUM | MEDIUM |
| `forecast_target_class` | `DIRECTION_PLUS_STRENGTH_PLUS_HORIZON` | `DIRECTION_PLUS_STRENGTH_PLUS_HORIZON` |
| `conditioning_state records` | **8 exacts** | **8 exacts** |

#### P4.2 Placement

Adapters inline = méthodes dans la classe runner (pas de fichier standalone), per arbitrage IA-Lab 2026-04-21.

- Engine A : méthode `build_forecast_signal_candidate()` dans `src/engines/engine_a/engine_a_runner.py`
- Engine B : méthode `build_forecast_signal_candidate()` dans `src/engines/engine_b/engine_b_runner.py`

#### P4.3 Contract sortie

Retourner un `ForecastSignalCandidate` (contract canon IA-Lab Slice 2, cf. `src/interface_contracts/forecast_contracts.py`) avec :
- `engine_id` (A ou B)
- `forecast_direction` ∈ {LONG, SHORT, FLAT}
- `forecast_strength` ∈ [0, max_abs_forecast]
- `forecast_horizon_class` (default MEDIUM)
- `forecast_target_class` = DIRECTION_PLUS_STRENGTH_PLUS_HORIZON
- `conditioning_state_record` (dict 8 champs exacts)
- `volatility_estimate` = `local_std / current_price`

#### P4.4 Tests

Créer :
- `tests/test_engines/test_engine_a/test_engine_a_forecast_signal_candidate.py` — 3 tests (EMIT, NO_TRADE, edge max)
- `tests/test_engines/test_engine_b/test_engine_b_forecast_signal_candidate.py` — 3 tests (EMIT, NO_TRADE, edge max)

Tests obligatoires :
1. EMIT favorable → `ForecastSignalCandidate` bien formé, `forecast_strength ≤ max_abs_forecast`
2. NO_TRADE → renvoie `None` (pas de candidate construit)
3. Edge `forecast_strength == max_abs_forecast` → clip au max sans overflow

```bash
rtk python -m pytest tests/test_engines/test_engine_a/test_engine_a_forecast_signal_candidate.py tests/test_engines/test_engine_b/test_engine_b_forecast_signal_candidate.py -xvs
```

Attendu : `6 passed`.

**Slot completion** : `___`

---

### P5 — Adapters C/D inline

Même pattern que P4, étendu à Engine C (breakout continuation) et Engine D (re-entry).

#### P5.1 Spécificités Engine C (doc 21)

- `max_abs_forecast` = 15 (cohérence avec B)
- `forecast_horizon_class` — selon `continuation_expected_duration`
- `forecast_target_class` = DIRECTION_PLUS_STRENGTH_PLUS_HORIZON
- `conditioning_state_record` — ajouter champ `breakout_confirmation_score`

#### P5.2 Spécificités Engine D (doc 22)

- `max_abs_forecast` = 12 (ré-entrée = conviction plus faible que breakout)
- `forecast_horizon_class` — SHORT par défaut (ré-entrée = opportunité courte)
- `conditioning_state_record` — ajouter champ `reentry_age_minutes`

#### P5.3 Placement

- Engine C : `src/engines/engine_c/engine_c_runner.py` — méthode `build_forecast_signal_candidate()`
- Engine D : `src/engines/engine_d/engine_d_runner.py` — méthode `build_forecast_signal_candidate()`

**Attention** : Engine C et Engine D ont déjà des runners existants. Ne PAS réécrire — ajouter uniquement la méthode.

#### P5.4 Tests

- `tests/test_engines/test_engine_c/test_engine_c_forecast_signal_candidate.py` — 3 tests
- `tests/test_engines/test_engine_d/test_engine_d_forecast_signal_candidate.py` — 3 tests

```bash
rtk python -m pytest tests/test_engines -xvs -k "forecast_signal_candidate"
```

Attendu : `12 passed` (6 P4 + 6 P5).

**Slot completion** : `___`

---

### P6 — W-13 Live-Light : fermer les gates G-13.1..G-13.4

#### P6.1 État courant

`src/protocols/live_light_runtime.py` existe (post-P3 split). Contient squelette `LiveLightRuntime` avec seam d'entrée / sortie. Les **gates de promotion** ne sont pas implémentées.

#### P6.2 Gates à implémenter (doc 21 §7 + doc 22 §7 + table V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md L639)

| Gate | Nom | Règle | Source doctrinale |
|---|---|---|---|
| G-13.1 | Kill-switch armé | `EmergencyCircuitBreaker.is_armed() == True` avant tout run | doc 20 §4 Taleb |
| G-13.2 | Replay reproducible | hash-pinned artifact disponible via `backtest_artifact_import` | doc 19 Phase 3 |
| G-13.3 | Governance signed | `GovernanceSignOff.is_signed(stage=13)` vrai | doc 19 Phase 5 |
| G-13.4 | Refusal journal présent | `RefusalJournal.is_available() == True` + rotating writer | doc 20 §4 |

#### P6.3 Structure de sortie

Chaque gate renvoie un `GateEvaluation` typé :

```python
@dataclass(frozen=True)
class GateEvaluation:
    gate_id: str           # ex "G-13.1"
    passed: bool
    reason_code: str       # canonical reason code
    details: dict[str, object]
```

`LiveLightRuntime.evaluate_promotion_gates()` renvoie `tuple[GateEvaluation, ...]` — ordre G-13.1 → G-13.4.

Règle **fail-closed** : si 1 gate failed, l'ensemble renvoie `promoted=False`, blocage immédiat (Taleb "when in doubt, don't trade").

#### P6.4 Tests

Créer `tests/test_protocols/test_live_light_runtime_gates.py` :

- `test_all_gates_pass_promotes` → 4 gates vertes → `promoted=True`
- `test_kill_switch_not_armed_blocks` → G-13.1 failed → `promoted=False`, reason `gate.kill_switch.not_armed`
- `test_replay_missing_blocks` → G-13.2 failed → `promoted=False`
- `test_governance_unsigned_blocks` → G-13.3 failed → `promoted=False`
- `test_refusal_journal_unavailable_blocks` → G-13.4 failed → `promoted=False`
- `test_multiple_gates_failed_reports_all` → vérifier que **toutes** les gates échouées sont rapportées (pas seulement la première)

```bash
rtk python -m pytest tests/test_protocols/test_live_light_runtime_gates.py -xvs
```

Attendu : `6 passed`.

#### P6.5 Intégration

`LiveLightRuntime.run()` appelle `evaluate_promotion_gates()` **avant** tout dispatch vers Engine A/B/C/D. Si `promoted=False` → retour `LiveLightDecision(action="no_trade", reason_code=<premier gate failed>)` + journal via `RefusalJournal`.

**Slot completion** : `___`

---

### P7 — W-15 Engine C skeleton

#### P7.1 Contrat (doc 21)

Engine C = breakout continuation. Entrées : `EngineCInput` (breakout score, structural break confirmation, momentum, volatility regime). Sortie : `EngineCDecision` (EMIT / NO_TRADE + reason codes).

#### P7.2 Placement

Vérifier `src/engines/engine_c/` actuel. Si déjà existe :
- Compléter les gates manquants (direction, structural_break_confirmation, continuation_score, conviction)
- Ajouter adapter inline P5 si absent

Si absent :
- Créer `src/engines/engine_c/engine_c_runner.py` (< 500L)
- Créer `src/engines/engine_c/engine_c_runner_support.py` si > 400L logique
- Créer `src/engines/engine_c/conviction_builder_c.py` (parallèle Engine B : formule conviction)
- Créer `src/engines/engine_c/__init__.py` avec exports typés

#### P7.3 Formule conviction C (doc 21 §5)

```
raw = 0.40·breakout_score + 0.25·continuation_momentum + 0.20·structure_confirmation + 0.15·cost_preference
    - 0.10·false_breakout_score
    - fragility_penalty - toxicity_penalty
Seuils : MEDIUM = 0.55, LOW = 0.30 (cohérence avec Engine B)
```

**Profile ID** : `engine_c_conviction.to_calibrate.v1` (flag "to_calibrate" obligatoire — R-QUANT-FIRST : aucune calibration hardcodée).

#### P7.4 Tests canonique

Créer `tests/test_engines/test_engine_c/test_engine_c.py` :

- `_emit_inputs()` fixture — breakout_score=0.7, continuation_momentum=0.6, structure_confirmation=0.8, cost_preference=0.7
- `test_emit_favorable` → decision == EMIT, conviction == MEDIUM, tier_suggestion == TIER_3
- `test_no_trade_low_conviction` → raw < 0.55 → NO_TRADE
- `test_false_breakout_penalty_applied` → false_breakout_score=0.5 → −0.05 pénalité visible
- `test_no_trade_hard_blocked_without_coordination` → si `coordination_input is None` → NO_TRADE reason `engine_c.coordination.missing`
- `test_engine_c_conventions_are_explicitly_governed` → vérifier `ENGINE_C_CONVICTION_PROFILE_ID` exposé

```bash
rtk python -m pytest tests/test_engines/test_engine_c -xvs
```

Attendu : `5+ passed`.

**Slot completion** : `___`

---

### P8 — W-14 seam enabler bridge

#### P8.1 Rôle

Build-14 = governed enablers (enrichissements additifs : microstructure, news, risk metrics avancés). Build-15 (Engine C) et Build-16 (Engine D) dépendent de sorties Build-14.

Le seam bridge garantit :
- Build-14 outputs **alimentent** Engine C et Engine D
- Jamais de dépendance inverse (Engine C/D ne doivent **pas** modifier Build-14)
- Désactivation graceful : si un enabler est absent, Engine C/D fonctionnent en mode dégradé (pas de crash)

#### P8.2 Placement

Créer `src/complete_enablers/enabler_bridge.py` (< 400L) :

```python
@dataclass(frozen=True)
class EnablerBundle:
    microstructure: MicrostructureEnablerOutput | None
    news: NewsEnablerOutput | None
    risk_metrics: RiskMetricsEnablerOutput | None

class EnablerBridge:
    def collect_for_engine(self, engine_id: EngineId) -> EnablerBundle: ...
    def is_degraded(self, engine_id: EngineId) -> bool: ...
```

#### P8.3 Tests

`tests/test_complete_enablers/test_enabler_bridge.py` :

- `test_collect_all_enablers_present` → bundle complet
- `test_collect_degraded_mode_partial` → 1 enabler absent → `is_degraded == True`, autres présents
- `test_collect_degraded_mode_all_absent` → toutes absent → `is_degraded == True`, bundle vide
- `test_engine_c_consumes_bundle` → Engine C accepte `EnablerBundle` en input optionnel

```bash
rtk python -m pytest tests/test_complete_enablers/test_enabler_bridge.py -xvs
```

Attendu : `4 passed`.

**Slot completion** : `___`

---

### P9 — Commit unique + audit Opus

#### P9.1 Pré-commit

```bash
rtk python -m pytest -q --tb=line
rtk python -m dag_validator
rtk python -m engineering_guardrails --format=stat
rtk git status --short
rtk git diff --stat
```

**Portes** :
- pytest : `ALL passed` (relever le nombre exact)
- DAG : `PASS`
- guardrails : `new_violations=0`
- `git status` : uniquement fichiers in-scope (pas de `build/`, pas de `.pyc`)

#### P9.2 Commit message

```
S32 session 20h : arbitrage + P1 + splits + adapters ABCD + W-13/14/15

Arbitrage 2026-04-21 :
- Smoke Engine B : flow_coherence=0.8 aligné sur fixture canon
- Registry stages : Micro-live / Live-Light / UI Complete + Live-Complete restaurés

P1 S32 : test_engine_a_runtime_downstream débloqué (N tests verts)

Splits :
- protocols/live_light_runtime.py 718L → 450L + 300L (support)

Adapters inline :
- Engine A/B/C/D build_forecast_signal_candidate (ForecastSignalCandidate v2)

W-13 Live-Light : gates G-13.1..G-13.4 fail-closed
W-15 Engine C : skeleton + conviction builder + 5 tests canon
W-14 seam : EnablerBridge degradation graceful

Doctrine : R-QUANT-FIRST respecté (0 modif calib_methods)
DAG PASS ; new_violations=0 ; X tests passed ; Y files changed

Co-Authored-By: Codex (GPT-5) <noreply@anthropic.com>
```

#### P9.3 Rapport final Codex

Remplir dans ce MD (slots ci-dessous) :
- pytest count exact
- DAG status
- guardrails stat
- `git diff --stat` condensé (top fichiers)
- completion status : COMPLETE / PARTIAL / BLOCKED

---

## 4 · Files Changed (récapitulatif attendu)

| Fichier | Phase | Type | Δ LOC estimé |
|---|---|---|---|
| `scripts/run_build9_core_smoke.py` | P0 | modif | +1 |
| `src/manifest_registry/build_order_registry.py` | P1 | modif | ±3 strings |
| `tests/test_manifest_registry/test_build_order.py` | P1 | modif | ±2 strings |
| `tests/test_engines/test_engine_a/**` | P2 | fix | dépend diagnose |
| `src/engines/engine_a/__init__.py` | P2 (si hypothèse B) | modif | ±5 |
| `src/protocols/live_light_runtime.py` | P3 | modif | -270 |
| `src/protocols/live_light_runtime_support.py` | P3 | **nouveau** | +300 |
| `src/engines/engine_a/engine_a_runner.py` | P4 | ajout méthode | +80 |
| `src/engines/engine_b/engine_b_runner.py` | P4 | ajout méthode | +80 |
| `src/engines/engine_c/engine_c_runner.py` | P5, P7 | ajout méthode + skeleton | +250 |
| `src/engines/engine_d/engine_d_runner.py` | P5 | ajout méthode | +80 |
| `tests/test_engines/test_engine_{a,b,c,d}/test_*_forecast_signal_candidate.py` | P4, P5 | **nouveau** (4) | +4×120 |
| `src/engines/engine_c/conviction_builder_c.py` | P7 | **nouveau** | +250 |
| `src/engines/engine_c/__init__.py` | P7 | **nouveau ou modif** | +20 |
| `tests/test_engines/test_engine_c/test_engine_c.py` | P7 | **nouveau** | +300 |
| `src/protocols/live_light_runtime.py` (gates) | P6 | ajout | +150 |
| `tests/test_protocols/test_live_light_runtime_gates.py` | P6 | **nouveau** | +200 |
| `src/complete_enablers/enabler_bridge.py` | P8 | **nouveau** | +300 |
| `tests/test_complete_enablers/test_enabler_bridge.py` | P8 | **nouveau** | +150 |

Total approximatif : ~2 500 LOC ajoutées, ~300 déplacées, ~10 modifiées. 8 nouveaux fichiers de code + 5 nouveaux fichiers de test.

---

## 5 · Risques et gardes

| Risque | Probabilité | Impact | Garde |
|---|---|---|---|
| Fichier `live_light_runtime.py` re-dépasse 700L après split mal calibré | moyen | bloque guardrails | vérifier `wc -l` après chaque déplacement |
| Adapter inline casse API existante Engine A/B | faible | régression | tests A/B existants doivent rester verts (cap non-régression) |
| Engine C skeleton duplique structure B | moyen | confusion doctrinale | copier pattern B textuellement, ne pas "améliorer" |
| P1 S32 cache des pyc stale non-reproductible | moyen | diagnose erronée | **toujours** supprimer `__pycache__` avant 1er test |
| Dépendance cyclique Engine C ↔ EnablerBridge | faible | DAG fail | DAG PASS après chaque phase obligatoire |
| Over-scope : ajout feature non-spec | moyen | dilution | `git diff --stat` ≤ 20 fichiers par phase |

**Règle anti-overscope** : si Codex identifie une amélioration hors-spec, la noter dans **Deferred / Not Done**, ne pas l'exécuter.

**Règle R-QUANT-FIRST** : `src/calibration_methods/*.py` jamais touchés. `conviction_builder_a/b/c/d.py` : seuils doivent avoir suffixe `.to_calibrate.v1`.

---

## 6 · Audit Opus — checklist finale (20 items)

À l'issue de la session, Opus relit et coche :

1. [ ] P0 : smoke Engine B EMIT (pytest vert)
2. [ ] P1 : registry canonique (3 noms + 1 docstring + 1 assert)
3. [ ] P2 : `test_engine_a_runtime_downstream` vert + cascade 691 tests débloqués
4. [ ] P3 : `live_light_runtime.py` + `_support.py` chacun < 700L, tests verts
5. [ ] P4 : Engine A adapter inline, 3 tests canon verts, contract conforme
6. [ ] P4 : Engine B adapter inline, 3 tests canon verts, `max_abs_forecast=15`
7. [ ] P5 : Engine C adapter inline, 3 tests canon verts
8. [ ] P5 : Engine D adapter inline, 3 tests canon verts, `max_abs_forecast=12`
9. [ ] P6 : gates G-13.1/2/3/4 présentes, fail-closed, 6 tests verts
10. [ ] P7 : Engine C skeleton, `ENGINE_C_CONVICTION_PROFILE_ID = "...to_calibrate.v1"`, 5 tests verts
11. [ ] P8 : `EnablerBridge`, mode dégradé, 4 tests verts
12. [ ] Global : `rtk python -m pytest -q` ALL PASSED (nombre X reporté)
13. [ ] DAG : PASS après chaque phase + final
14. [ ] Guardrails : `new_violations=0` final
15. [ ] Aucune modif `src/calibration_methods/*.py`
16. [ ] Aucune modif `src/engines/engine_b/conviction_builder_b.py` (formule gelée)
17. [ ] Aucun ajout profil LIGHT / COMPLETE (artefact de déploiement)
18. [ ] Aucun baseline `FILE_TOO_LONG` ajouté sur `src/`
19. [ ] `git diff --stat` ≤ 30 fichiers au total, cohérent avec §4
20. [ ] Commit message conforme §P9.2

**Verdict** :
- `GREENLIGHT` si 20/20
- `PARTIAL` si ≥ 16/20 avec rationale Deferred explicite
- `REQUEST_FIX` si < 16/20 (feedback ligne-à-ligne)

---

## 7 · Deferred / Not Done (à remplir par Codex)

Items identifiés pendant la session mais non inclus dans les 20h :

- `___`
- `___`
- `___`

(Exemples anticipés : UI legacy `technical_dashboard_*.py` 1933L/1271L — hors scope, noter pour future session ; splits mineurs pré-cap 700L ; nouveaux tests de propriété sur adapters.)

---

## 8 · Slots à remplir par Codex (résumé exécutif)

- **Phase P0** completion : `___`
- **Phase P1** completion : `___`
- **Phase P2** diagnose + fix + pytest count : `___`
- **Phase P3** split + LOC finaux : `___`
- **Phase P4** adapters A/B : `___`
- **Phase P5** adapters C/D : `___`
- **Phase P6** gates W-13 : `___`
- **Phase P7** Engine C skeleton : `___`
- **Phase P8** EnablerBridge : `___`
- **Phase P9** commit SHA + pytest total : `___`

---

## 9 · Next Safe Step (à remplir par Codex post-session)

Proposition Codex pour la prochaine session (après audit Opus GREENLIGHT) :

`___`

(Candidats anticipés : W-16 Engine D skeleton complet ; splits UI legacy ; W-18 testnet adapter ; W-23 VPS rollback playbook ; calibration empirique Engine B/C/D seuils.)

---

**Fin du spec.** Bon courage — 20h ciblées, 20 items audit, 0 formule touchée.
