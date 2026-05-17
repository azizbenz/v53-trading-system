# Spec — Cockpit Phase 2 Full (IA Lab + Engines + Quant Components)

**Date :** 2026-04-27
**Priorité :** P1 — débloque la lecture du cœur quant V5.3 depuis le browser
**Auteur spec :** Opus
**Implémenteur :** Codex
**Auditeur :** Opus
**Phase précédente :** [Phase 1 MVP 2026-04-26](2026-04-26_local_lab_cockpit_mvp.md) — livré, dashboard read-only basique up sur 8091

---

## 1. Objective

Phase 2 enrichit le cockpit (Phase 1 livré) avec **toutes les composantes quant V5.3** que l'utilisateur veut piloter sans CLI, en respectant la doctrine "**il faut pas oublier les metriques, les engines, les composantes IA Lab**" (user 2026-04-27).

Phase 2 est **strictement read-only** sur ces composants (lectures de fichiers JSON existants). Phase 3 (séparée) ajoutera les actions interactives (kill switch, suspend, upload artefact) — découpée car les boutons touchent au runtime trading et méritent une revue distincte.

**Objectif explicite** : un quant qui ouvre `http://v53-vps:8080` doit voir EN UNE SEULE PAGE (ou via 1-2 clics navigation) :
- État de chaque engine A/B/C/D (active/suspended, opportunités cycle, score range)
- Tous les composants IA Lab (review Build-9X, candidats, merge gates, lifecycle)
- Refusal Journal Taleb (top motifs, tail-risk meter)
- Model Risk Register Narang (artefacts actifs, challengers, drift)
- Capacity guard (queue, backlog)
- EDGE calibration thresholds (THR-X01/X02/E01/E02)
- Multiple Testing Guard HLZ (Sharpe deflation)
- Replay metrics quotidiens (CE net, costs, drawdown proxy, par-engine, par-pair)
- Feature bridge status (lineage lock, recognition rate)

---

## 2. Docs Governants

| Document | Contrainte | Implication Phase 2 |
|---|---|---|
| `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md` §2 | Carver — forecast standardisation, vol targeting, sizing chain | Section "Sizing Chain" affiche forecast → vol target → effective size |
| Idem §3 | Narang — enriched SignalCandidate, 4 conditioning families, model risk register | Section "Model Risk Register" lit `model_risk_registry/registry.py` snapshot |
| Idem §4 | Taleb — refusal journal, quadruple filter, tail-risk meter, anti-survivorship | Section "Refusal Journal" lit dernier dump du `refusal_journal.py` |
| `multiple_testing_guard` | Harvey-Liu-Zhu Sharpe deflation under multiple testing | Section "HLZ Guard" affiche deflation factor courant |
| `CLAUDE.md` Indicator discipline | NO 1990s TA (RSI, MACD, etc.) | Le cockpit n'affiche AUCUN indicateur classique. Uniquement : Order Flow Imbalance, VPIN, queue pressure, Kyle's lambda, Amihud, Roll/Corwin-Schultz, realized vol kernel, Hawkes intensity, PIN. |
| `CLAUDE.md` Profile discipline | Pas de profil LIGHT en VPS | Phase 2 n'expose que la vue COMPLETE. La vue LIGHT est explicitement masquée. |
| `CLAUDE.md` Capital reality | €300-€400 starting, $4000 ceiling | Capital tier display read-only, pas de form input. |
| `CLAUDE.md` Code discipline | thresholds via calibration seams | Les sections affichent les thresholds (lecture seule), ne les mutent jamais. |

---

## 3. Current Code Seam — sources de données identifiées (audit 2026-04-27)

### 3.1 Engines A/B/C/D

| Engine | Module | Runtime état attendu |
|---|---|---|
| A | `src/engines/engine_a/` | active by default ; promotion ladder via `complete_enablers/` |
| B | `src/engines/engine_b/` | dormant Phase 0 ; smoke fix flow_coherence=0.8 (cf. memory `project_v53_arbitration_2026_04_21`) |
| C | `src/engines/engine_c/` | candidate stage |
| D | `src/engines/engine_d/` | refusal-driven, fichier dédié `engine_d_runtime_support_refusal.py` |

**Source d'observation** :
- `build/build11_live_websocket_campaign/auto_exports/<date>/replay_metrics.json::engine_aggregates[]` — par engine_id : `record_count`, `selected_count`, `hard_blocked_count`, `ce_net`, `expected_cost_mean`, `realized_cost_mean`, `gross_return_mean`
- `build/build11_live_websocket_campaign/auto_exports/<date>/feature_bridge.json::engines[]` — liste des engines actifs dans le cycle
- État `suspended/active` : à dériver des artefacts du `command_queue` (cf. § 3.10) — NB Codex doit identifier le projection file. Si absent, marquer `suspension_unknown`.

### 3.2 IA Lab Build-9X review

**Source canonique** : `build/local_lab_analysis_<id>/post_trade_review/meta_learning_review.bundle.json` (31 KB structuré, format vérifié 2026-04-26).

Champs à extraire :
- `summary` (string, e.g. `"CRA sterilization elevated at 100.00%"`)
- `mistake_classes[]` (e.g. `economic_sterilization`)
- `hypotheses[]` avec `strength`, `stage` (`anecdotal`, `under_review`, `tested`, `validated`)
- `candidates[]` avec `id`, `stage`, `tests_pending`, `replay_bundles[]`
- `merge_gates[]` (6 gates : `NO_LIVE_MUTATION_PATH`, `END_TO_END_ID_CORRELATION`, `STRUCTURED_LEARNING_LOGS_PRESENT`, `LEARNING_BACKPRESSURE_HANDLED`, `RESOURCE_BUDGETS_RESPECTED`, `STATISTICAL_GOVERNANCE_PRESENT`) avec status pass/fail
- `lifecycle_transitions[]` (e.g. `diagnostic open->escalated`)
- `archive_eligibility[]` (eligible / not_eligible + reasons)
- `review_decisions[]` (state, verdict, final)
- `capacity_guard_snapshot` (queue, backlog mode, oldest_event_ms)

**Codex action** : créer `src/cockpit/state_lab_review.py` qui parse ce bundle en types Pydantic frozen.

### 3.3 Refusal Journal (Taleb)

**Source modules** :
- `src/meta_minimal/refusal_journal/refusal_journal.py` — implémentation
- `src/interface_contracts/refusal_records.py` — types

**Codex action** : identifier le **fichier de dump** émis par le service Shadow (probablement sous `service_dir/` ou `auto_exports/<date>/`) et créer `src/cockpit/state_refusal_journal.py`. Si aucun fichier n'est encore écrit, le cockpit doit afficher un message clair "Refusal journal not yet persisted to disk — Phase 2.1 wiring required" plutôt que crash.

Champs à exposer :
- Top 10 refusal motifs avec count + dernière occurrence
- Tail-risk meter value (numérique + barre visuelle 0-100%)
- Quadruple filter status : `bayes_evidence`, `out_of_sample_validation`, `tail_risk_audit`, `regime_stationarity` — chacun ✓/✗
- Anti-survivorship status (boolean)

### 3.4 Model Risk Register (Narang)

**Source module** : `src/meta_learning/model_risk_registry/registry.py`

**Codex action** : identifier le fichier de **snapshot** émis périodiquement. Le cockpit lit ce snapshot et affiche :
- `active_ml_artifact` : nom, version, hash, last_validated_at, drift_score
- `shadow_ml_challenger` : nom, version, hash, comparison_status vs active
- `active_regime_detector_artifact` : idem
- `shadow_regime_detector_challenger` : idem
- Promotion eligibility (calculée via les gates connus)

Si aucun artefact actif → message "No artefact registered yet — upload via Phase 3 cockpit or rsync + governed activate".

### 3.5 Capacity Guard

**Source module** : `src/meta_learning/capacity_guard.py`

**Source d'état runtime** : déjà inclus dans `meta_learning_review.bundle.json::capacity_guard_snapshot` (cf. § 3.2). Si on veut un signal plus frais, scanner `service_dir/shadow_vps_service_observability_export.json` (déjà connu, généré par le service Shadow).

Champs :
- `queue_depth` (int)
- `backlog_mode` (`normal` / `backpressure` / `full_capture`)
- `oldest_event_ms` (int)
- `unprocessed_count` (int)
- `blocked` (bool)
- `block_reasons[]`

### 3.6 Multiple Testing Guard (HLZ — Harvey-Liu-Zhu)

**Source modules** :
- `src/calibration_methods/multiple_testing_guard.py`
- `src/local_replay_runtime/local_lab_multiple_testing_review.py`

**Source d'état runtime** : à identifier par Codex. Le module produit probablement un fichier `multiple_testing_review.json` dans le bundle d'analyse Local IA Lab (`build/local_lab_analysis_<id>/`).

Champs à exposer :
- `tests_performed` (int)
- `sharpe_deflation_factor` (float)
- `effective_significance_level` (float)
- `passing_strategies[]` (count + names)
- `rejected_strategies[]` (count)

### 3.7 EDGE Calibration Thresholds

**Source canonique** : `config/calibration/v1/thresholds.yml` (créé 2026-04-26).

Lecture YAML simple → afficher tableau :
- `THR-X01` (clock drift max ms) — value, signed_by, signed_at
- `THR-X02` (websocket gap max s) — idem
- `THR-E01`, `THR-E02` (EDGE thresholds) — si présents (sinon "not yet calibrated, run analysis bundle with ≥ 2 trades")
- `signature.mode` (`human_attestation` / `cryptographic`)
- `signature.signed_by`
- `signature.signed_at`

### 3.8 Replay metrics

**Source** : `build/build11_live_websocket_campaign/auto_exports/<date>/replay_metrics.json`

Schéma (vérifié 2026-04-26) :
```json
{
  "total_records": 1, "total_opportunities": 1,
  "selected_count": 1, "executed_count": 1, "hard_blocked_count": 0,
  "ce_net": 0.0016, "expected_cost_mean": 0.0001,
  "realized_cost_mean": 0.0001, "gross_return_mean": 0.0021,
  "drawdown_proxy": 0.0,
  "pair_aggregates": [{"pair": "BTCUSDT", ...}],
  "engine_aggregates": [{"engine_id": "engine_a", ...}]
}
```

**Codex action** : afficher KPIs principaux en grand (CE net, gross return, drawdown proxy, exec rate = executed/total), puis 2 tableaux détaillés (par pair, par engine).

### 3.9 Feature Bridge status

**Source** : `build/build11_live_websocket_campaign/auto_exports/<date>/feature_bridge.json`

Schéma (vérifié) :
- `bridge_status` (e.g. `"ok"`)
- `feature_set_version`, `transform_set_version`
- `canonical_feature_dictionary_size`, `canonical_transform_whitelist_size`
- `record_count`, `rows_with_features`, `missing_feature_rows`
- `pairs[]`, `engines[]`
- `feature_keys[]`, `recognized_feature_keys[]`, `unrecognized_feature_keys[]`
- `lineage_lock_status` (`missing` / `present` / `valid`)
- `lineage_lock_reasons[]`
- `feature_to_engine_path` (string visualization)

**Action UI** : badge vert si lineage lock present, rouge si missing avec reasons en hover.

### 3.10 Engine suspension state

Codex action : grep le repo pour identifier où le service Shadow persiste l'état `suspended_engines[]`. Probablement `shadow_vps_service.state.json` sous `service_dir/`. Lire ce fichier, exposer la liste.

Si introuvable, créer un placeholder `suspension_unknown` plutôt que de planter.

### 3.11 Sizing chain (Carver)

Codex action : identifier où le forecast value, vol target, et effective position size sont matérialisés. Probablement dans `replay_dtr.jsonl` (déjà vu : champs `final_size`, `candidate_size`, `expected_edge_bps`, `tier`). Exposer les 4 valeurs en pipeline visuel (flèches forecast → vol target → effective size → executed size).

---

## 4. Placement

### 4.1 Nouveaux modules `src/cockpit/`

```
src/cockpit/
├── state_engines.py            # Engines A/B/C/D status + per-cycle aggregates
├── state_lab_review.py         # Build-9X meta_learning_review.bundle.json parser
├── state_refusal_journal.py    # Refusal journal dump parser
├── state_model_risk.py         # Model risk register snapshot parser
├── state_capacity_guard.py     # Capacity guard state from observability_export
├── state_multiple_testing.py   # HLZ multiple testing review parser
├── state_calibration.py        # YAML thresholds + signature metadata
├── state_replay_metrics.py     # auto_exports/<date>/replay_metrics.json
├── state_feature_bridge.py     # auto_exports/<date>/feature_bridge.json
├── state_sizing_chain.py       # Carver sizing chain from replay_dtr.jsonl
└── state.py                    # extended: composite ``DashboardViewModel`` aggregates all above
```

### 4.2 Nouveaux templates Jinja2

```
src/cockpit/templates/
├── index.html                  # extended: drops in 9 new <section> blocks (cf. § 4.3 grid)
├── partials/
│   ├── _engines_grid.html      # 4 cards A/B/C/D side-by-side
│   ├── _lab_review.html        # Build-9X mistake classes + candidates + merge gates table
│   ├── _refusal_journal.html   # Top motifs + tail-risk meter + quadruple filter
│   ├── _model_risk.html        # Active vs challenger artefacts comparison
│   ├── _capacity_guard.html    # Queue depth meter + backlog mode badge
│   ├── _hlz_guard.html         # Sharpe deflation factor card
│   ├── _calibration_thresholds.html  # Tableau thresholds + signature
│   ├── _replay_metrics.html    # KPI grand format + per-pair / per-engine tables
│   ├── _feature_bridge.html    # Status badge + lineage lock + feature recognition rate
│   └── _sizing_chain.html      # Carver pipeline visualization
└── pages/
    ├── lab.html                # Vue dédiée IA Lab (composants 4.1.2/3/4/6/9)
    └── trading.html            # Vue dédiée Trading (composants 4.1.1/5/8/10)
```

### 4.3 Nouvelle structure index.html

Layout conservé (sidebar + topbar). Le `content` change ainsi :

```
content
├── welcome-banner (existing)
├── stat-row (existing — 3 pair cards)
├── grid-2 (existing — chart + side-stack)
├── ──────── NEW Phase 2 ────────
├── _engines_grid (4 engine cards)
├── grid-2:
│   ├── _replay_metrics
│   └── _capacity_guard
├── grid-2:
│   ├── _lab_review
│   └── _refusal_journal
├── grid-2:
│   ├── _model_risk
│   └── _hlz_guard
├── grid-2:
│   ├── _calibration_thresholds
│   └── _feature_bridge
├── _sizing_chain (full-width)
├── grid-2 (existing — warmup checks + artefacts)
└── live logs placeholder (existing)
```

### 4.4 Nouvelles routes

```python
GET /              # extended landing — toutes les sections
GET /lab           # vue dédiée IA Lab
GET /trading       # vue dédiée Trading
GET /api/snapshot  # JSON dump de DashboardViewModel — utile Phase 3 HTMX refresh
```

---

## 5. Files Changed

### 5.1 Nouveaux fichiers Python

| Fichier | Lignes estimées | Rôle |
|---|---|---|
| `src/cockpit/state_engines.py` | ~140 | Parser replay_metrics + feature_bridge → `EngineRuntimeStatus` |
| `src/cockpit/state_lab_review.py` | ~180 | Parser meta_learning_review.bundle.json → `LabReviewSummary` |
| `src/cockpit/state_refusal_journal.py` | ~130 | Parser dump refusal journal → `RefusalJournalSnapshot` |
| `src/cockpit/state_model_risk.py` | ~150 | Parser registry snapshot → `ModelRiskRegisterSnapshot` |
| `src/cockpit/state_capacity_guard.py` | ~100 | Parser observability export → `CapacityGuardSnapshot` |
| `src/cockpit/state_multiple_testing.py` | ~110 | Parser HLZ review → `MultipleTestingGuardSnapshot` |
| `src/cockpit/state_calibration.py` | ~110 | Parser YAML thresholds → `CalibrationThresholdsSnapshot` |
| `src/cockpit/state_replay_metrics.py` | ~130 | Parser replay_metrics.json → `ReplayMetricsSnapshot` |
| `src/cockpit/state_feature_bridge.py` | ~110 | Parser feature_bridge.json → `FeatureBridgeSnapshot` |
| `src/cockpit/state_sizing_chain.py` | ~140 | Parser replay_dtr.jsonl → `SizingChainSnapshot` |
| `src/cockpit/state.py` | +120 | Extension `DashboardViewModel` agrège les 10 nouveaux snapshots ; nouveaux champs nullable + tests |
| `src/cockpit/server.py` | +60 | Routes `/lab`, `/trading`, `/api/snapshot` |

**Total nouveau code Python** : ~1480 lignes.

### 5.2 Nouveaux templates Jinja2

| Fichier | Lignes estimées |
|---|---|
| `templates/partials/_engines_grid.html` | ~70 |
| `templates/partials/_lab_review.html` | ~130 |
| `templates/partials/_refusal_journal.html` | ~80 |
| `templates/partials/_model_risk.html` | ~100 |
| `templates/partials/_capacity_guard.html` | ~50 |
| `templates/partials/_hlz_guard.html` | ~50 |
| `templates/partials/_calibration_thresholds.html` | ~70 |
| `templates/partials/_replay_metrics.html` | ~110 |
| `templates/partials/_feature_bridge.html` | ~60 |
| `templates/partials/_sizing_chain.html` | ~80 |
| `templates/pages/lab.html` | ~50 |
| `templates/pages/trading.html` | ~50 |
| `templates/index.html` | +70 (compose les nouveaux partials) |

### 5.3 Modifications CSS

| Fichier | Changement |
|---|---|
| `static/cockpit.css` | +220 L : classes `.engine-card`, `.merge-gate`, `.tail-risk-meter`, `.lineage-badge`, `.sizing-pipeline`, `.kpi-mega`, `.deflation-card`, `.quadruple-filter` |

### 5.4 Tests

| Fichier | Lignes estimées | Couverture |
|---|---|---|
| `tests/cockpit/test_state_engines.py` | ~140 | replay_metrics + feature_bridge fixtures |
| `tests/cockpit/test_state_lab_review.py` | ~180 | meta_learning_review.bundle.json fixture |
| `tests/cockpit/test_state_refusal_journal.py` | ~130 | dump fixture + missing-file fallback |
| `tests/cockpit/test_state_model_risk.py` | ~140 | registry snapshot fixtures |
| `tests/cockpit/test_state_capacity_guard.py` | ~100 |
| `tests/cockpit/test_state_multiple_testing.py` | ~110 |
| `tests/cockpit/test_state_calibration.py` | ~110 | YAML parsing + signature absent |
| `tests/cockpit/test_state_replay_metrics.py` | ~130 |
| `tests/cockpit/test_state_feature_bridge.py` | ~110 |
| `tests/cockpit/test_state_sizing_chain.py` | ~140 |
| `tests/cockpit/test_routes_phase2.py` | ~150 | TestClient pour `/`, `/lab`, `/trading`, `/api/snapshot` |

**Total nouveau code tests** : ~1440 lignes.

### 5.5 Aucune modification

`src/interface_contracts/`, `src/protocols/`, `src/ui/`, `src/engines/`, `src/meta_learning/`, `src/meta_minimal/`, `src/calibration_methods/` — **strictement read-only** par le cockpit. Si Codex constate qu'une API n'expose pas un champ requis, **arrête et signale** plutôt que de patcher.

---

## 6. Claims Implemented

### C1 — Engines A/B/C/D status grid
4 cards côte à côte. Chaque card affiche : engine_id, status badge (active/suspended/dormant/unknown), opportunités cycle, score range (min/max), CE net, hard_blocked count, gross_return_mean. Couleur de bordure : vert si engine actif et CE net > 0, jaune si actif mais CE négatif, gris si dormant, rouge si suspended.

### C2 — IA Lab Build-9X review section
Affiche en colonnes : (a) summary string, (b) liste mistake_classes (chips), (c) candidates table (id, stage, tests_pending, replay_bundles count), (d) 6 merge gates avec status badges. Section pliable / dépliable. Lien "Open full bundle JSON" pour ouvrir le fichier brut.

### C3 — Refusal Journal Taleb
Top 10 refusal motifs (barres horizontales triées par count desc), tail-risk meter (gauge 0-100%), quadruple filter status (4 chips ✓/✗). Si dump absent → message clair, pas de crash.

### C4 — Model Risk Register Narang
2 colonnes : Active artefacts (ML + regime detector) avec hash + last_validated_at + drift_score, Shadow challengers (ML + regime detector) avec comparison_status. Badge "promotion eligible" si tous gates passent.

### C5 — Capacity Guard
Card simple : queue_depth (gauge), backlog_mode (chip coloré), oldest_event_ms (numérique), block_reasons (liste si bloqué).

### C6 — HLZ Multiple Testing Guard
Card "Sharpe Deflation" : factor courant (grand chiffre), tests_performed, effective_significance_level. Lien vers passing/rejected strategies (Phase 2.1 si trop volumineux).

### C7 — Calibration Thresholds
Tableau avec 4 colonnes : threshold_id, value, signed_by, signed_at. En-tête de section : signature mode (`human_attestation` ou `cryptographic`). Si un threshold manque → ligne grisée "not yet calibrated".

### C8 — Replay Metrics KPIs
Grand format : 4 KPIs en ligne (CE net, Gross Return, Drawdown Proxy, Exec Rate), puis 2 tableaux : par-pair et par-engine. Les valeurs négatives en rouge, positives en vert. Drawdown affiché en bleu (informationnel, pas alarmant).

### C9 — Feature Bridge status
Card : bridge_status badge, lineage_lock status (vert/rouge/orange), feature recognition rate (`recognized_feature_keys / feature_keys`), pairs[], engines[], reasons en accordéon si lineage_lock_status != "valid".

### C10 — Carver Sizing Chain
Visualisation pipeline horizontal : Forecast (raw_score) → Vol Target (penalized_score) → Tier (final_score / tier) → Effective Size (final_size). Flèches entre les étapes, valeur affichée sur chaque nœud.

### C11 — Vue dédiée `/lab`
Route `GET /lab` rend uniquement les sections IA Lab : Build-9X review, refusal journal, model risk, HLZ guard. Layout 2 colonnes pleine page.

### C12 — Vue dédiée `/trading`
Route `GET /trading` rend uniquement : engines grid, replay metrics, capacity guard, feature bridge, sizing chain. Optimisé pour temps réel — refresh auto 10 s via meta refresh (Phase 2) ou HTMX (Phase 3).

### C13 — JSON snapshot endpoint
Route `GET /api/snapshot` retourne `DashboardViewModel.model_dump(mode="json")`. Utile pour Phase 3 (HTMX partials) et pour scripts d'audit externes.

### C14 — Robustesse aux fichiers manquants
**Aucun crash** si un fichier source est absent / corrompu. Chaque adapter retourne `None` ou un objet "empty" avec champ `source_status` ∈ {`ok`, `missing`, `parse_error`, `not_yet_persisted`}. Le template affiche un état placeholder informatif au lieu d'une stack trace.

### C15 — Pas de mutation
**Aucun endpoint Phase 2 n'écrit** dans le filesystem ou le command_queue. C'est strictement lecture. Audit Opus vérifie via `grep -E "atomic_write|.write_text|.write_bytes|os.kill|signal\." src/cockpit/state*.py` doit retourner 0 match.

### C16 — Pas d'indicateur 1990s TA
Le cockpit n'affiche AUCUN RSI / MACD / Stochastic / Bollinger / SAR / ADX / Ichimoku / candlestick pattern. Audit Opus vérifie via `grep -iE "rsi|macd|stochastic|bollinger|parabolic|ichimoku" src/cockpit/ templates/` doit retourner 0 match. (Les commentaires citant la doctrine sont OK si en majuscules `NO RSI/MACD`.)

---

## 7. Tests and Proof

> **Codex doit remplir tous les slots ci-dessous. Aucun claim de COMPLETE sans ces preuves.**

### 7.1 Tests unitaires par adapter

Chaque `state_*.py` a son `test_state_*.py` avec a minima :
- happy path : fixture JSON/YAML valide → snapshot avec tous champs renseignés
- missing file : `FileNotFoundError` → adapter retourne empty snapshot avec `source_status="missing"`
- parse error : JSON corrompu → adapter retourne empty snapshot avec `source_status="parse_error"`
- partial : champs optionnels absents → adapter retourne snapshot avec valeurs `None`

| Test fichier | Slot Codex |
|---|---|
| `test_state_engines.py` | ☐ |
| `test_state_lab_review.py` | ☐ |
| `test_state_refusal_journal.py` | ☐ |
| `test_state_model_risk.py` | ☐ |
| `test_state_capacity_guard.py` | ☐ |
| `test_state_multiple_testing.py` | ☐ |
| `test_state_calibration.py` | ☐ |
| `test_state_replay_metrics.py` | ☐ |
| `test_state_feature_bridge.py` | ☐ |
| `test_state_sizing_chain.py` | ☐ |

### 7.2 Tests d'intégration routes

`test_routes_phase2.py` :
- `GET /` → HTTP 200, contient les 9 nouveaux blocs HTML (vérifier par `assert "engines-grid" in body` etc.)
- `GET /lab` → HTTP 200, contient sections IA Lab uniquement
- `GET /trading` → HTTP 200, contient sections trading uniquement
- `GET /api/snapshot` → HTTP 200, JSON valide, contient les 10 snapshots

**Slot Codex** : ☐

### 7.3 Tests guardrails

| Commande | Attendu | Slot Codex |
|---|---|---|
| `python -m dag_validator` | `new_violations=0` | ☐ |
| `python scripts/run_engineering_guardrails.py --baseline config/engineering_guardrails_baseline.json` | `new_violations=0` | ☐ |
| `python -m pytest tests/cockpit/ -q` | ≥ 30 tests, 100% pass | ☐ |
| `grep -E "atomic_write\|\.write_text\|\.write_bytes\|os\.kill\|signal\." src/cockpit/state*.py` | 0 matches (read-only invariant) | ☐ |
| `grep -iE "rsi\|macd\|stochastic\|bollinger\|parabolic\|ichimoku" src/cockpit/ src/cockpit/templates/ \| grep -v "NO RSI\|NO MACD"` | 0 matches (no 1990s TA) | ☐ |

### 7.4 Smoke test manuel

```bash
# Service Shadow continu (terminal 1)
python scripts/run_shadow_vps_service.py --service-dir build/build11_live_websocket_campaign/service ... --poll-interval-s 30 &

# Cockpit (terminal 2)
python scripts/run_cockpit.py --port 8091

# Browser fetch
curl -s http://127.0.0.1:8091/        | grep -c 'engines-grid\|lab-review\|refusal-journal\|model-risk\|capacity-guard\|hlz-guard\|calibration-thresholds\|replay-metrics\|feature-bridge\|sizing-chain'
# expected: 10
curl -s http://127.0.0.1:8091/lab     | grep -c 'lab-review\|refusal-journal\|model-risk\|hlz-guard'
# expected: 4
curl -s http://127.0.0.1:8091/trading | grep -c 'engines-grid\|replay-metrics\|capacity-guard\|feature-bridge\|sizing-chain'
# expected: 5
curl -s http://127.0.0.1:8091/api/snapshot | jq 'keys | length'
# expected: ≥ 12
```

**Slot Codex** : ☐ (coller les sorties réelles).

### 7.5 Capture visuelle

Codex doit produire 3 captures d'écran (PNG) du cockpit sur des données réelles V5.3 :
1. `/` (vue full)
2. `/lab` (vue IA Lab)
3. `/trading` (vue Trading)

Sauvegardées sous `docs/production_deployment_plan/screenshots/cockpit_phase2_*.png`.

**Slot Codex** : ☐

### 7.6 Preuve git

| Commande | Slot Codex |
|---|---|
| `git diff --stat` (uniquement `src/cockpit/`, `tests/cockpit/`) | ☐ |

---

## 8. Deferred / Not Done

| Item | Phase cible |
|---|---|
| Boutons interactifs (kill, suspend, resume, export) | Phase 3 |
| Upload artefact (multipart < 100 MB) + activation gouvernée | Phase 3 |
| HTMX refresh partiel par section | Phase 3 |
| SSE log tail | Phase 3 |
| Backtest UI (lancement async + render review.md) | Phase 4 |
| Authentification multi-utilisateur | Hors scope (Tailscale single-user) |
| Promotion runtime_mode | Doctrinalement interdit (gates explicites) |

---

## 9. Risks

### R1 — Schémas JSON inconnus pour certaines sources

**Scénario** : Codex ne trouve pas le format exact de `model_risk_registry` snapshot ou du dump `refusal_journal`.

**Mitigation** :
- Codex DOIT lire les modules Python concernés (`src/meta_learning/model_risk_registry/registry.py`, `src/meta_minimal/refusal_journal/refusal_journal.py`) pour extraire le schéma
- Si le module ne sérialise pas vers disk : créer adapter qui retourne `source_status="not_yet_persisted"` + message UI explicite, ne PAS inventer un format
- Logger un warning structured dans tous les cas où un fichier attendu manque

### R2 — Performance (10 fichiers JSON lus à chaque GET /)

**Scénario** : 10 lectures FS par request × refresh 30 s = peut devenir lent si volumineux.

**Mitigation Phase 2** :
- Acceptable car fichiers petits (< 50 KB chacun, le bundle Build-9X = 31 KB max observé)
- Phase 3 ajoutera cache TTL court (5 s) avec `functools.lru_cache(ttl=5)` si nécessaire
- Codex peut profiler via `time curl http://...` et reporter le résultat

### R3 — Format de `meta_learning_review.bundle.json` peut varier

**Scénario** : le bundle évolue entre versions du Build-9X review.

**Mitigation** :
- Adapter défensif : tous les champs `optional`, fallback `None`
- Test fixture inclut au moins 2 versions du bundle (vide + plein)

### R4 — Codex tente de muter le state pour "réparer" un fichier manquant

**Scénario** : Codex pense bien faire en écrivant un fichier vide pour éviter l'erreur.

**Mitigation** :
- C16 audit grep DOIT retourner 0 match
- Spec explicite : « le cockpit ne CRÉE pas de fichiers, il LIT seulement »

### R5 — Conflit avec `src/cockpit/state.py` Phase 1

**Scénario** : Codex casse les fonctions Phase 1 (`build_dashboard_view_model`, `read_pair_metrics`, etc.) en refactorant.

**Mitigation** :
- Spec exige extension par composition, pas réécriture
- Tests Phase 1 (`test_state_pid_tracker.py` etc.) doivent continuer à passer

### R6 — Mauvaise interprétation des engines suspendus

**Scénario** : Codex affiche un engine comme "suspended" alors qu'il est juste dormant ou pas encore implémenté.

**Mitigation** :
- 4 états distincts : `active` / `dormant` / `suspended` / `unknown`
- `dormant` = engine défini mais pas activé en config courante (engine B Phase 0)
- `suspended` = présent dans `suspended_engines[]` du command_queue projection
- `unknown` = état non déterminable depuis les artefacts (placeholder)

### R7 — Volume de tests fait sauter `max_file_lines=700`

**Scénario** : `test_state_lab_review.py` dépasse 700 L à cause de fixtures gigantesques.

**Mitigation** :
- Doctrine V5.3 : tests autorisés à dépasser 700 L (cf. `feedback_test_files_line_count.md` mémoire)
- Si dépassement : ajout au baseline `config/engineering_guardrails_baseline.json` avec pattern `tests/cockpit/test_state_lab_review.py|FILE_TOO_LONG`
- **Jamais** sur fichiers `src/`

---

## 10. Completion Status

> **Slot Codex** :

```
Status: [COMPLETE | PARTIAL | BLOCKED]
Pytest: __ passed, __ failed
Guardrails new_violations: __
Read-only invariant grep: __ matches (must be 0)
No 1990s TA grep: __ matches (must be 0)
Files in diff stat: ____
Smoke run /lab status: ____
Smoke run /trading status: ____
Smoke run /api/snapshot keys: ____
Screenshots: [yes/no]
Reasons (if not COMPLETE): ____
```

---

## 11. Next Safe Step

> **Slot Codex** :

```
Suggested next pilot:
 [_] Phase 3 spec (kill switch + governed commands wiring)
 [_] Phase 2.1 — refusal journal dump persistence (if not yet wired)
 [_] Phase 2.2 — model risk register snapshot persistence
 [_] HTMX refresh partials
 [_] Other: ____
```

---

## 12. Opus Audit Checklist

### 12.1 Read-only invariant
- [ ] `grep -E "atomic_write\|\.write_text\|\.write_bytes\|os\.kill\|signal\." src/cockpit/state*.py` retourne 0 match
- [ ] Aucun endpoint Phase 2 n'utilise `BackgroundTasks`, `asyncio.create_task`, ou ne mute le command queue
- [ ] `git diff src/interface_contracts/ src/protocols/ src/ui/ src/engines/ src/meta_learning/ src/meta_minimal/ src/calibration_methods/` doit être vide

### 12.2 No 1990s TA
- [ ] `grep -iE "rsi\|macd\|stochastic\|bollinger\|parabolic\|ichimoku\|elliott\|candlestick.*pattern" src/cockpit/ src/cockpit/templates/` retourne 0 match (hors commentaires citant la doctrine en majuscules)
- [ ] Toutes les métriques affichées appartiennent à la liste autorisée Carver/Narang/Taleb (OFI, VPIN, queue pressure, Kyle's lambda, Amihud, Roll, Corwin-Schultz, realized vol kernels, Hawkes, PIN)

### 12.3 Robustesse
- [ ] Chaque adapter `state_*.py` test : missing file → empty snapshot avec `source_status` cohérent
- [ ] Chaque adapter `state_*.py` test : parse error → idem
- [ ] `GET /` rend 200 même si TOUS les fichiers sources sont absents (placeholder partout)

### 12.4 Couverture quant
- [ ] 4 engines (A/B/C/D) ont chacun leur card visible
- [ ] Build-9X review : summary, mistake_classes, candidates, 6 merge_gates tous affichés
- [ ] Refusal journal : top 10 motifs + tail-risk meter + quadruple filter affichés
- [ ] Model risk register : active + 2 challengers (ML + regime) affichés
- [ ] Capacity guard, HLZ guard, calibration thresholds, replay metrics, feature bridge, sizing chain — tous présents

### 12.5 Doctrine / canon
- [ ] Capital tier €300-€400 affiché en lecture seule (pas de form input)
- [ ] Aucun bouton de promotion runtime_mode
- [ ] Pas de profil LIGHT visible (vue COMPLETE uniquement)
- [ ] Vue iframe Grafana conservée (Grafana reste l'observatoire séparé)

### 12.6 Tests
- [ ] `pytest tests/cockpit/ -q` ≥ 30 tests passent
- [ ] Tests existants Phase 1 (`test_state.py`) continuent de passer
- [ ] Couverture par adapter : chaque `state_*.py` a son `test_state_*.py`

### 12.7 Smoke proof
- [ ] Sortie `curl http://127.0.0.1:8091/` collée dans § 7.4 montre les 10 sections
- [ ] 3 screenshots sauvegardés sous `docs/.../screenshots/`
- [ ] `git diff --stat` ne contient QUE les fichiers listés § 5

### 12.8 Verdict format
```
GREENLIGHT — Phase 2 cockpit full read-only quant exposure complete.
Pytest: <N> passed, 0 failed (Phase 1 + Phase 2)
Guardrails: 0 new_violations
Read-only invariant: 0 mutating call detected
No 1990s TA: 0 forbidden indicator detected
Diff stat: <list>
Sections rendered: 10/10
Screenshots: 3
Next: Phase 3 spec (kill switch + governed commands wiring)
```

Sinon :
```
REQUEST_FIX — <list failing audit items with file:line>
```

---

## 13. Annexe — schémas JSON de référence (audit 2026-04-26)

### `replay_metrics.json` (vérifié)
```json
{
  "total_records": 1, "total_opportunities": 1, "dtr_coverage": 1.0,
  "selected_count": 1, "executed_count": 1, "hard_blocked_count": 0,
  "rejected_ranking_count": 0, "phantom_count": 0,
  "ce_net": 0.0016, "expected_cost_mean": 0.0001,
  "realized_cost_mean": 0.0001, "gross_return_mean": 0.0021,
  "gross_return_total": 0.0021, "drawdown_proxy": 0.0,
  "pair_aggregates": [{"pair": "BTCUSDT", "record_count": 1, ...}],
  "engine_aggregates": [{"engine_id": "engine_a", "record_count": 1, ...}]
}
```

### `feature_bridge.json` (vérifié)
```json
{
  "bridge_status": "ok",
  "dataset_id": "live_websocket_snapshot_batch",
  "feature_set_version": "1.0.0", "transform_set_version": "1.0.0",
  "canonical_feature_dictionary_size": 10,
  "canonical_transform_whitelist_size": 13,
  "record_count": 1, "rows_with_features": 1,
  "pairs": ["BTCUSDT"], "engines": ["engine_a"],
  "feature_keys": [...], "recognized_feature_keys": [],
  "unrecognized_feature_keys": [...],
  "lineage_lock_status": "missing",
  "lineage_lock_reasons": ["feature lineage lock is required"],
  "feature_to_engine_path": "historical_prices -> computed_features -> engines -> scoring"
}
```

### `meta_learning_review.bundle.json` (structure observée — Codex doit lire le module pour le schéma exact)
- 31 KB, 14 sections principales : `summary`, `mistake_classes`, `checklist`, `hypotheses`, `candidates`, `candidate_states`, `capacity_guard`, `review_decisions`, `archive_eligibility`, `lifecycle_transitions`, `merge_gates`, `replay_bundles`, `correlation_id`, `signed_at`

### `config/calibration/v1/thresholds.yml` (vérifié)
```yaml
schema_version: calibration.v1
artifact_id: v53-binance-thresholds-v1
version: v1
thresholds:
  - threshold_id: THR-X01
    value: 1000
    description: "Max allowed clock drift between local system and Binance server (ms)"
    ...
signature:
  mode: human_attestation
  signed_by: aziz.benz@gmail.com
  signed_at: "2026-04-26T00:00:00+00:00"
```

---

**Fin du spec — version 1.0 — 2026-04-27**
