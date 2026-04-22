# Plan Codex 5 jours — Sprint 32 post-arbitrage (25h)

**Date** : 2026-04-21
**Auteur Opus** : plan consolidé session post-arbitrage
**Budget** : 5 jours × 5h = 25h Codex
**Prerequis** : commit `49669ce` mergé, arbitrages 2026-04-21 spec'd (A smoke + B registry + note doctrinale)
**Spec technique référent** : `2026-04-21_codex_20h_session_arbitrage_p1s32_splits_adapters_w13w15.md` (détails phases P0-P9)
**Extension Day-5** : +5h → W-16 Engine D skeleton + W-06 paper-trading harness + signal handlers

---

## 0 · Objectif maître des 5 jours

Clôturer le chemin critique pré-**MICRO_LIVE** en 5 sessions auditées Opus.
À l'issue du Day 5 : adapters A/B/C/D inline + gates W-13 fermées + skeletons Engine C/D verts + EnablerBridge + paper-trading reproducible + signal handlers = **pre-flight MICRO_LIVE complet**.

**Gardes transverses** (chaque jour) :
- R-QUANT-FIRST : 0 modif `src/calibration_methods/psr|dsr|pot_gpd|energy_distance.py`
- Pas de profil LIGHT ; stages canoniques uniquement
- `src/` jamais baseliné `FILE_TOO_LONG`
- DAG PASS + `new_violations=0` gates à chaque fin de journée
- Commit intermédiaire en fin de chaque jour (squashable plus tard)

---

## 1 · Vue d'ensemble — 5 jours

| Jour | Durée | Titre | Phases | Livrable | Audit Opus |
|---|---|---|---|---|---|
| **J1** | 5h | Arbitrage + P1 S32 + split live_light | P0, P1, P2, P3 + checkpoint | 2 arbitrages consommés, 691 tests débloqués, oversize split | 11 items checklist J1 |
| **J2** | 5h | Adapters inline A/B/C/D | P4, P5 + checkpoint | 4 adapters `build_forecast_signal_candidate()` + 12 tests verts | 8 items checklist J2 |
| **J3** | 5h | W-13 gates + W-14 bridge | P6, P8 + checkpoint | 4 gates G-13.x fail-closed + EnablerBridge dégradation graceful | 10 items checklist J3 |
| **J4** | 5h | W-15 Engine C skeleton | P7 étendue + checkpoint | Engine C runner + conviction builder + 5+ tests canon | 8 items checklist J4 |
| **J5** | 5h | W-16 Engine D + W-06 paper-trading + signal handlers | P10, P11, P12 + commit final | Engine D skeleton + paper-trading harness + SIGTERM handler + audit final | 14 items checklist J5 + verdict final |

**Total** : 25h, ~10 fichiers source nouveaux, ~8 fichiers test nouveaux, ~2800 LOC ajoutées.

---

## 2 · Day 1 (5h) — Arbitrages + P1 S32 + split live_light_runtime

### 2.1 Objectif
Consommer les 2 arbitrages doctrinaux 2026-04-21, débloquer la cascade 691 tests du P1 S32, et descendre `live_light_runtime.py` sous le cap 700L.

### 2.2 Horaire

| Créneau | Phase | Action |
|---|---|---|
| 0:00–0:30 | P0 | Arbitrage A — `flow_coherence=0.8` dans `scripts/run_build9_core_smoke.py` L163-184 |
| 0:30–1:00 | P1 | Arbitrage B — 3 `name=` registry + 2 strings test |
| 1:00–3:00 | P2 | Diagnose + fix `test_engine_a_runtime_downstream` (commencer par suppression `__pycache__`) |
| 3:00–4:30 | P3 | Split `live_light_runtime.py` 718L → `live_light_runtime.py` ≤450L + `live_light_runtime_support.py` ≤300L |
| 4:30–5:00 | Checkpoint J1 | pytest + DAG + guardrails + commit J1 |

### 2.3 Détails phases
Voir spec `2026-04-21_codex_20h_session_arbitrage_p1s32_splits_adapters_w13w15.md` §3 (P0, P1, P2, P3).

### 2.4 Commit J1 (message)
```
S32 J1 : arbitrages 2026-04-21 + P1 S32 débloqué + split live_light_runtime

- Smoke Engine B : flow_coherence=0.8 aligné fixture canon (raw 0.54974→0.56474)
- Registry stages : "Micro-live" / "Live-Light" / "UI Complete + Live-Complete" restaurés
- test_engine_a_runtime_downstream : <cause diagnostic> → N tests verts
- protocols/live_light_runtime.py 718L → 450L + 300L support (cap 700L respecté)

DAG PASS ; new_violations=0 ; X passed
```

### 2.5 Checklist audit Opus J1 (11 items)
1. [ ] P0 : smoke Engine B test vert (5 passed)
2. [ ] P0 : `git diff --stat` P0 = `1 file changed, 1 insertion(+)`
3. [ ] P1 : 3 × `name=` registry modifiés (L116, L122, L146)
4. [ ] P1 : 2 × strings test `test_build12_exists` corrigées
5. [ ] P1 : `pytest tests/test_manifest_registry` ALL passed
6. [ ] P2 : `pytest tests/test_engines/test_engine_a` ALL passed (40+ tests)
7. [ ] P2 : diagnose cause précisément identifiée (pyc / symbol / signature)
8. [ ] P3 : `wc -l src/protocols/live_light_runtime.py` ≤ 700
9. [ ] P3 : `wc -l src/protocols/live_light_runtime_support.py` ≤ 700
10. [ ] DAG PASS + `new_violations=0`
11. [ ] Commit J1 formaté cf §2.4

**Verdict J1** : GREENLIGHT si 11/11 — sinon REQUEST_FIX bloquant J2.

---

## 3 · Day 2 (5h) — Adapters inline A/B/C/D

### 3.1 Objectif
Ajouter `build_forecast_signal_candidate()` en méthode **inline** (pas standalone) aux 4 runners A/B/C/D. Contract : `ForecastSignalCandidate` (IA-Lab Slice 2 canon).

### 3.2 Horaire

| Créneau | Phase | Action |
|---|---|---|
| 0:00–1:00 | P4-A | Engine A : adapter + 3 tests (`test_engine_a_forecast_signal_candidate.py`) |
| 1:00–2:00 | P4-B | Engine B : adapter + 3 tests, `max_abs_forecast=15` |
| 2:00–3:30 | P5-C | Engine C : adapter + 3 tests, `max_abs_forecast=15`, horizon selon `continuation_expected_duration` |
| 3:30–4:30 | P5-D | Engine D : adapter + 3 tests, `max_abs_forecast=12`, horizon SHORT par défaut |
| 4:30–5:00 | Checkpoint J2 | pytest + DAG + guardrails + commit J2 |

### 3.3 Config exacte par engine

| Engine | `max_abs_forecast` | `horizon_default` | `forecast_target_class` | `conditioning_state_record` |
|---|---|---|---|---|
| A | 20 | MEDIUM | DIRECTION_PLUS_STRENGTH_PLUS_HORIZON | 8 champs (cf. memory `project_v53_adapters_status_2026_04_21.md`) |
| B | **15** | MEDIUM | DIRECTION_PLUS_STRENGTH_PLUS_HORIZON | 8 champs |
| C | 15 | MEDIUM (ou selon `continuation_expected_duration`) | idem | 8 champs + `breakout_confirmation_score` |
| D | **12** | **SHORT** | idem | 8 champs + `reentry_age_minutes` |

### 3.4 Tests canon par engine (3 tests/engine)
1. `test_emit_favorable_returns_candidate` → EMIT favorable → `ForecastSignalCandidate` non None
2. `test_no_trade_returns_none` → NO_TRADE → `None`
3. `test_max_strength_clips_to_config` → signal saturé → `forecast_strength == max_abs_forecast`

### 3.5 Commit J2 (message)
```
S32 J2 : adapters inline A/B/C/D build_forecast_signal_candidate

- engine_a : max_abs=20, MEDIUM default + 3 tests canon
- engine_b : max_abs=15, MEDIUM default + 3 tests canon
- engine_c : max_abs=15, horizon selon duration + 3 tests canon
- engine_d : max_abs=12, SHORT default + 3 tests canon

Contract : ForecastSignalCandidate (IA-Lab Slice 2 canon)
DAG PASS ; new_violations=0 ; X passed (+12 nouveaux)
```

### 3.6 Checklist audit Opus J2 (8 items)
1. [ ] 4 méthodes `build_forecast_signal_candidate()` en inline (0 fichier standalone ajouté)
2. [ ] Engine B `max_abs_forecast == 15` (pas 20)
3. [ ] Engine D `max_abs_forecast == 12` + `horizon_default == SHORT`
4. [ ] 12 tests `test_*_forecast_signal_candidate.py` verts (4×3)
5. [ ] `ForecastSignalCandidate` contract respecté (pas de champ custom)
6. [ ] Engine B `volatility_estimate == local_std / current_price` cohérent
7. [ ] DAG PASS + `new_violations=0`
8. [ ] Commit J2 formaté

**Verdict J2** : GREENLIGHT si 8/8 — sinon REQUEST_FIX bloquant J3.

---

## 4 · Day 3 (5h) — W-13 gates + W-14 EnablerBridge

### 4.1 Objectif
Fermer les 4 gates de promotion Build-13 (fail-closed Taleb) et poser le pont entre Build-14 enablers et Engines C/D.

### 4.2 Horaire

| Créneau | Phase | Action |
|---|---|---|
| 0:00–1:00 | P6.1 | `GateEvaluation` dataclass + G-13.1 kill-switch armé |
| 1:00–2:00 | P6.2 | G-13.2 replay reproducible (hash-pinned artifact) |
| 2:00–2:45 | P6.3 | G-13.3 governance signed + G-13.4 refusal journal |
| 2:45–4:00 | P6.4 | 6 tests `test_live_light_runtime_gates.py` (tous verts) |
| 4:00–4:45 | P8 | `EnablerBridge` skeleton + 4 tests |
| 4:45–5:00 | Checkpoint J3 | pytest + DAG + guardrails + commit J3 |

### 4.3 Gates W-13 — règle fail-closed

```python
def evaluate_promotion_gates(self, ...) -> tuple[GateEvaluation, ...]:
    gates = (
        self._gate_kill_switch_armed(),       # G-13.1
        self._gate_replay_reproducible(),     # G-13.2
        self._gate_governance_signed(),       # G-13.3
        self._gate_refusal_journal_present(), # G-13.4
    )
    # fail-closed : SI 1 échec → promoted=False avec reason_code du 1er échec
    # MAIS toutes les gates sont évaluées (reporting complet, pas de short-circuit)
    return gates
```

### 4.4 Tests W-13 (6 tests)
- `test_all_gates_pass_promotes` → 4 verts → `promoted=True`
- `test_kill_switch_not_armed_blocks` → G-13.1 failed → `promoted=False`
- `test_replay_missing_blocks`
- `test_governance_unsigned_blocks`
- `test_refusal_journal_unavailable_blocks`
- `test_multiple_gates_failed_reports_all` → reporting complet

### 4.5 EnablerBridge (4 tests)
Voir spec 20h §P8 pour détail. Cible : `src/complete_enablers/enabler_bridge.py` ≤ 400L.

### 4.6 Commit J3 (message)
```
S32 J3 : W-13 gates fail-closed + W-14 EnablerBridge graceful degradation

- GateEvaluation dataclass + 4 gates G-13.1..4 (fail-closed Taleb)
- LiveLightRuntime.evaluate_promotion_gates() + reporting complet
- EnablerBridge : collect_for_engine + is_degraded + 4 tests
- 10 nouveaux tests verts

DAG PASS ; new_violations=0 ; X passed (+10)
```

### 4.7 Checklist audit Opus J3 (10 items)
1. [ ] `GateEvaluation` dataclass typé (4 champs + frozen)
2. [ ] 4 gates G-13.1..4 implémentées avec reason_code canonique
3. [ ] Règle fail-closed : 1 échec ⇒ `promoted=False`
4. [ ] Règle reporting complet : toutes gates évaluées même si 1 échec
5. [ ] 6 tests gates verts
6. [ ] `LiveLightRuntime.run()` appelle `evaluate_promotion_gates()` avant dispatch engines
7. [ ] `EnablerBridge` skeleton (collect_for_engine, is_degraded)
8. [ ] 4 tests EnablerBridge verts (all, partial, absent, consume)
9. [ ] DAG PASS + `new_violations=0`
10. [ ] Commit J3 formaté

**Verdict J3** : GREENLIGHT si 10/10.

---

## 5 · Day 4 (5h) — W-15 Engine C skeleton

### 5.1 Objectif
Créer Engine C (breakout continuation) selon doc 21 : runner + conviction builder + tests canoniques. Pattern textuellement dérivé d'Engine B (pas d'innovation).

### 5.2 Horaire

| Créneau | Phase | Action |
|---|---|---|
| 0:00–0:30 | P7.1 | Vérifier état `src/engines/engine_c/` existant (état courant post-IA-Lab) |
| 0:30–2:00 | P7.2 | `engine_c_runner.py` + `engine_c_runner_support.py` (si >400L logique) |
| 2:00–3:00 | P7.3 | `conviction_builder_c.py` (formule doc 21 §5) |
| 3:00–4:00 | P7.4 | `engine_c_runner_input.py` + `engine_c_runner_output.py` (contracts typés) |
| 4:00–4:45 | P7.5 | Tests canoniques `test_engine_c.py` (5+ tests : emit_favorable, no_trade_low, false_breakout, coordination_missing, conventions_governed) |
| 4:45–5:00 | Checkpoint J4 | pytest + DAG + guardrails + commit J4 |

### 5.3 Formule conviction C (doc 21 §5)

```
raw = 0.40·breakout_score + 0.25·continuation_momentum + 0.20·structure_confirmation + 0.15·cost_preference
    - 0.10·false_breakout_score
    - fragility_penalty - toxicity_penalty
Seuils : MEDIUM = 0.55, LOW = 0.30
Profile ID : "engine_c_conviction.to_calibrate.v1" (flag obligatoire)
```

### 5.4 Tests canoniques (5 tests)
1. `test_emit_favorable` → EMIT, MEDIUM, TIER_3
2. `test_no_trade_low_conviction`
3. `test_false_breakout_penalty_applied`
4. `test_no_trade_hard_blocked_without_coordination` → `engine_c.coordination.missing`
5. `test_engine_c_conventions_are_explicitly_governed` → profile_id exposé

### 5.5 Commit J4 (message)
```
S32 J4 : W-15 Engine C skeleton (breakout continuation doc 21)

- engine_c_runner + engine_c_runner_support + conviction_builder_c
- Contracts typés : EngineCInput, EngineCDecision, EngineCRunSummary
- Formule conviction 0.40/0.25/0.20/0.15 + Taleb penalties
- Profile "engine_c_conviction.to_calibrate.v1" (non-calibré flag)
- 5 tests canoniques verts

DAG PASS ; new_violations=0 ; X passed (+5)
```

### 5.6 Checklist audit Opus J4 (8 items)
1. [ ] `src/engines/engine_c/` structure cohérente (parallèle Engine B)
2. [ ] `conviction_builder_c.py` pondérations 0.40/0.25/0.20/0.15 respectées
3. [ ] `ENGINE_C_CONVICTION_PROFILE_ID = "engine_c_conviction.to_calibrate.v1"`
4. [ ] Seuils MEDIUM=0.55 / LOW=0.30 (cohérence avec Engine B)
5. [ ] 5 tests canon verts
6. [ ] Hard block coordination_missing testé
7. [ ] Aucun fichier > 700L dans `src/engines/engine_c/`
8. [ ] DAG PASS + `new_violations=0`

**Verdict J4** : GREENLIGHT si 8/8.

---

## 6 · Day 5 (5h) — W-16 Engine D + W-06 paper-trading + signal handlers + commit final

### 6.1 Objectif
Finaliser le chemin critique :
- Engine D skeleton (re-entry / second chance doc 22)
- Paper-trading replay harness (W-06 hash-pinned artifact)
- Signal handlers SIGTERM/SIGINT (Taleb graceful shutdown)
- Commit final unique + audit Opus fin-de-session

### 6.2 Horaire

| Créneau | Phase | Action |
|---|---|---|
| 0:00–2:30 | P10 | W-16 Engine D skeleton (pattern Engine C dupliqué) |
| 2:30–3:30 | P11 | W-06 paper-trading replay harness |
| 3:30–4:15 | P12 | Signal handlers SIGTERM/SIGINT + tests |
| 4:15–4:45 | P9.1 | Pré-commit : full pytest + DAG + guardrails |
| 4:45–5:00 | P9.2 | Commit final + rapport Opus |

### 6.3 P10 — Engine D skeleton (2.5h)

Pattern **strictement identique** à Engine C, adapté spec doc 22 :

| Élément | Engine D |
|---|---|
| Rôle | Re-entry / second chance (opportunités post-breakout-raté) |
| Tier minimum | T4+ |
| `max_abs_forecast` | 12 |
| Horizon default | SHORT |
| Conviction formula (doc 22 §5) | `0.35·reentry_score + 0.25·timing_window + 0.20·structure_recovery + 0.20·cost_pref - 0.10·stale_signal_score - penalties` |
| Seuils | MEDIUM=0.55, LOW=0.30 |
| Profile ID | `engine_d_conviction.to_calibrate.v1` |
| Hard block | `engine_d.coordination.missing` + `engine_d.reentry_window.expired` |

**Fichiers** :
- `src/engines/engine_d/engine_d_runner.py` (≤ 500L)
- `src/engines/engine_d/engine_d_runner_support.py` (si nécessaire)
- `src/engines/engine_d/conviction_builder_d.py`
- `src/engines/engine_d/__init__.py`
- `tests/test_engines/test_engine_d/test_engine_d.py` — 5+ tests canon

**Note** : si Engine D partiellement existant, compléter uniquement les éléments manquants.

### 6.4 P11 — Paper-trading replay harness (1h)

Référence : doc 19 Phase 3 (paper_repro) + doc 20 §4 Taleb (replay reproducible obligatoire pré-Live).

**Livrable** : `src/paper_trading/replay_harness.py`

```python
@dataclass(frozen=True)
class ReplayRun:
    artifact_hash: str              # SHA256 hash-pinned
    start_ts_ms: int
    end_ts_ms: int
    engine_ids: tuple[EngineId, ...]
    decisions: tuple[EngineDecision, ...]

class ReplayHarness:
    def load_artifact(self, hash_pinned: str) -> Artifact: ...
    def run_replay(self, artifact: Artifact, engine_id: EngineId) -> ReplayRun: ...
    def diff_against_live(self, replay: ReplayRun, live_run: LiveRun) -> ReplayDiff: ...
```

**Règle critique** : artifact **hash-pinné** (pas de mutable path). Si hash ne match pas → raise `ArtifactHashMismatch`.

**Tests** (4+ tests) :
- `test_load_artifact_hash_match_success`
- `test_load_artifact_hash_mismatch_raises`
- `test_run_replay_produces_deterministic_decisions`
- `test_diff_against_live_detects_divergence`

### 6.5 P12 — Signal handlers SIGTERM/SIGINT (45 min)

Référence : doc 20 §4 Taleb quadruple filter → "graceful shutdown on signal".

**Livrable** : `src/runtime_bootstrap/signal_handlers.py`

```python
class GracefulShutdownHandler:
    """Intercepte SIGTERM/SIGINT et arme un flag lu par les runtimes."""
    def __init__(self, kill_switch: EmergencyCircuitBreaker): ...
    def install(self) -> None:
        signal.signal(signal.SIGTERM, self._on_signal)
        signal.signal(signal.SIGINT, self._on_signal)
    def is_shutdown_requested(self) -> bool: ...
```

Intégration : `LiveLightRuntime.run()` vérifie `is_shutdown_requested()` après chaque engine dispatch, sort proprement si vrai (journal via RefusalJournal reason `shutdown.graceful`).

**Tests** (3 tests) :
- `test_sigterm_arms_shutdown_flag`
- `test_sigint_arms_shutdown_flag`
- `test_runtime_exits_gracefully_on_flag`

### 6.6 P9.1 — Pré-commit vérifications

```bash
rtk python -m pytest -q --tb=line
rtk python -m dag_validator
rtk python -m engineering_guardrails --format=stat
rtk git status --short
rtk git diff --stat
rtk find src/ -name "*.py" -exec wc -l {} + | sort -rn | head -10
```

**Portes** :
- pytest : `ALL passed` (chiffre exact reporté)
- DAG : PASS
- guardrails : `new_violations=0`
- Top LOC : aucun `src/` > 700L (hors UI legacy baseliné)
- `git status` : aucun `build/`, `.pyc`, `__pycache__/`

### 6.7 Commit final J5 (message)

```
S32 complet : arbitrages + adapters ABCD + W-13/14/15/16 + paper-trading + signal handlers

5 jours × 5h = 25h Codex — chemin critique pré-MICRO_LIVE fermé.

J1 : arbitrages doctrinaux 2026-04-21 + P1 S32 + split live_light_runtime
J2 : adapters inline build_forecast_signal_candidate A/B/C/D (12 tests)
J3 : W-13 gates G-13.1..4 fail-closed + W-14 EnablerBridge graceful
J4 : W-15 Engine C skeleton (runner + conviction + 5 tests canon)
J5 : W-16 Engine D skeleton + W-06 paper-trading + signal handlers

Totaux : +N tests verts, +M fichiers src/, 0 modif calib_methods, 0 profil LIGHT
DAG PASS ; new_violations=0 ; X passed global

Co-Authored-By: Codex (GPT-5) <noreply@anthropic.com>
```

### 6.8 Checklist audit Opus J5 (14 items)

1. [ ] Engine D : 5 fichiers `src/engines/engine_d/` présents, cohérents avec Engine C
2. [ ] Engine D : `max_abs_forecast=12`, `horizon_default=SHORT`
3. [ ] Engine D : `ENGINE_D_CONVICTION_PROFILE_ID = "engine_d_conviction.to_calibrate.v1"`
4. [ ] Engine D : 5 tests canon verts
5. [ ] Paper-trading : `ReplayHarness` hash-pinné, `ArtifactHashMismatch` raised si drift
6. [ ] Paper-trading : 4 tests verts
7. [ ] Signal handlers : SIGTERM + SIGINT interceptés, flag armé
8. [ ] Signal handlers : `LiveLightRuntime.run()` check flag après chaque engine
9. [ ] Signal handlers : 3 tests verts
10. [ ] Pytest global : ALL passed (reporter chiffre exact)
11. [ ] DAG PASS
12. [ ] `new_violations=0`
13. [ ] Aucun fichier `src/` > 700L hors baseline UI legacy
14. [ ] Commit final formaté §6.7

**Verdict J5 = Verdict final Sprint 32** :
- `GREENLIGHT-FULL` si 14/14 (+ 37/37 items cumulés J1-J4)
- `GREENLIGHT-PARTIAL` si ≥ 12/14 avec Deferred explicite
- `REQUEST_FIX` si < 12/14

---

## 7 · Récapitulatif Files Changed (5 jours)

| Fichier | Jour | Type |
|---|---|---|
| `scripts/run_build9_core_smoke.py` | J1 | modif (+1L) |
| `src/manifest_registry/build_order_registry.py` | J1 | modif (3 strings) |
| `tests/test_manifest_registry/test_build_order.py` | J1 | modif (2 strings) |
| `tests/test_engines/test_engine_a/**` | J1 | fix P1 S32 |
| `src/protocols/live_light_runtime.py` | J1, J3 | split + gates W-13 |
| `src/protocols/live_light_runtime_support.py` | J1 | **nouveau** |
| `src/engines/engine_a/engine_a_runner.py` | J2 | +méthode adapter |
| `src/engines/engine_b/engine_b_runner.py` | J2 | +méthode adapter |
| `src/engines/engine_c/engine_c_runner.py` | J2, J4 | +méthode + skeleton |
| `src/engines/engine_d/engine_d_runner.py` | J2, J5 | +méthode + skeleton |
| `src/engines/engine_c/conviction_builder_c.py` | J4 | **nouveau** |
| `src/engines/engine_d/conviction_builder_d.py` | J5 | **nouveau** |
| `src/engines/engine_c/__init__.py`, contracts | J4 | **nouveau ou modif** |
| `src/engines/engine_d/__init__.py`, contracts | J5 | **nouveau ou modif** |
| `src/complete_enablers/enabler_bridge.py` | J3 | **nouveau** |
| `src/paper_trading/replay_harness.py` | J5 | **nouveau** |
| `src/runtime_bootstrap/signal_handlers.py` | J5 | **nouveau** |
| `tests/test_engines/test_engine_{a,b,c,d}/test_*_forecast_signal_candidate.py` | J2 | **4 nouveaux** |
| `tests/test_protocols/test_live_light_runtime_gates.py` | J3 | **nouveau** |
| `tests/test_complete_enablers/test_enabler_bridge.py` | J3 | **nouveau** |
| `tests/test_engines/test_engine_c/test_engine_c.py` | J4 | **nouveau** |
| `tests/test_engines/test_engine_d/test_engine_d.py` | J5 | **nouveau ou étendu** |
| `tests/test_paper_trading/test_replay_harness.py` | J5 | **nouveau** |
| `tests/test_runtime_bootstrap/test_signal_handlers.py` | J5 | **nouveau** |

**Total estimé** : ~12 fichiers src/ nouveaux, ~10 fichiers test nouveaux, ~3000 LOC ajoutées.

---

## 8 · Deferred / Out of scope (explicite)

Items consciemment exclus des 5 jours (à planifier Sprint 33+) :

- Splits UI legacy `technical_dashboard_view.py` 1933L + `technical_dashboard_html.py` 1271L → doctrine IA-Lab les acte comme "legacy HTML dashboard, not the target operator surface" (Prometheus+Grafana local est la surface active)
- Calibration empirique des seuils `engine_{b,c,d}_conviction.to_calibrate.v1` → nécessite data historique Shadow ≥ 4 semaines (doc 21 §7)
- W-18 testnet adapter complet (skeleton connector seulement ici via paper-trading)
- W-19/20/23/24/25 VPS/CI/rollback → Sprint 33 après Micro-live validé
- Full end-to-end test Shadow → Micro-live → Live-Light → Live-Complete → Sprint 34 post-enablers Build-14

---

## 9 · Risques & escalade

| Risque | Plan de mitigation |
|---|---|
| J1 P2 ne converge pas (diagnose P1 S32 complexe) | Escalade Opus à +1h30 pour investigation plus profonde ; si blocage > 3h → REQUEST_FIX et replanifier |
| J2 adapter inline casse tests existants A/B | Vérifier non-régression à chaque engine avant de passer au suivant (pas batch) |
| J4 Engine C duplique mal pattern B | Copier **textuellement** `engine_b_runner.py` puis adapter variables — pas de reécriture |
| J5 signal handlers testés difficilement en Windows | Utiliser `signal.raise_signal()` dans tests (portable Windows+Linux) |
| Dépassement budget J5 (2.5h Engine D tight) | Si Engine D > 2.5h : reporter P11 paper-trading en Sprint 33 ; garder P12 signal handlers |

---

## 10 · Slots à remplir par Codex (rapport fin-de-session)

| Jour | Completion | Pytest count | DAG | Guardrails | Commit SHA |
|---|---|---|---|---|---|
| J1 | `___` | `___` | `___` | `___` | `___` |
| J2 | `___` | `___` | `___` | `___` | `___` |
| J3 | `___` | `___` | `___` | `___` | `___` |
| J4 | `___` | `___` | `___` | `___` | `___` |
| J5 | `___` | `___` | `___` | `___` | `___` |

**Final verdict slot** (post-audit J5) : `___`

**Next safe step slot** (Codex propose Sprint 33) : `___`

---

**Fin du plan 5 jours.** 25h de travail ciblé, 51 items d'audit cumulés, 0 formule quant touchée, chemin critique MICRO_LIVE fermé.
