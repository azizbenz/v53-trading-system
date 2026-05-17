# Spec — Cockpit Phase 3 Interactive (Governed Actions Wiring)

**Date :** 2026-04-27
**Priorité :** P1 — débloque le pilotage opérationnel sans CLI
**Auteur spec :** Opus
**Implémenteur :** Codex (ou Opus direct selon vélocité)
**Auditeur :** Opus
**Phases précédentes :**
- [Phase 1 MVP 2026-04-26](2026-04-26_local_lab_cockpit_mvp.md) — landing + design ✅
- [Phase 2 Full 2026-04-27](2026-04-27_cockpit_phase2_full.md) — 10 composants quant read-only ✅

---

## 1. Objective

Phase 3 ajoute **les actions interactives** au cockpit. C'est le passage de "tableau de bord lecture" à "console de pilotage". Toutes les actions sont **gouvernées** : passage par `evaluate_locked_operator_action()` + écriture dans la `dashboard_command_queue` typée + audit trail.

**5 actions Phase 3** (ordre d'implémentation) :

1. **Kill switch < 1 s** — `POST /kill` triple canal (flag fichier + SIGTERM + enqueue async)
2. **Suspend / Resume pair** — `POST /command/suspend-pair`, `POST /command/resume-pair`
3. **Suspend / Resume engine** — `POST /command/suspend-engine`, `POST /command/resume-engine`
4. **Export credential inventory** — `POST /command/export-credential-inventory` (1-clic)
5. **Upload artefact ≤ 100 MB** — `POST /artefact/upload` (multipart, signature humaine)

**Hors scope Phase 3** (voir § 8 Deferred) :
- Promotion runtime_mode (Shadow → Micro-live → Live) — gates explicites doctrinaux
- Backtest UI (Phase 4)
- SSE log tail (Phase 3.1 — séparé pour pacing)
- HTMX partial refresh (Phase 3.1)
- Auth multi-utilisateur (Tailscale single-user OK)
- Artefacts > 100 MB (rsync out-of-band, Phase 4)

---

## 2. Docs Governants

| Document | Contrainte | Implication Phase 3 |
|---|---|---|
| `CLAUDE.md` Profile discipline | Pas de profil LIGHT en VPS | Cockpit refuse `ROLLBACK_TO_LIGHT` button (jamais exposé) |
| `CLAUDE.md` Shadow → Micro-live → Live transition gates | Jamais bypass | Aucun bouton de promotion runtime_mode |
| `CLAUDE.md` Capital reality | €300-€400 starting | Pas de form input modifiant le tier |
| `CLAUDE.md` Indicator discipline | NO 1990s TA | N/A pour cette phase (pas de panneau métrique nouveau) |
| `src/ui/operator_actions.py:evaluate_locked_operator_action` | Permission gate par profil | Toute action passe d'abord par cette fonction |
| Doctrine archi 2026-04-26 (cf. spec Phase 1 §2) | Tailscale + Hetzner + kill <1s | Triple canal kill conservé |
| `scripts/run_dashboard_governed_command.py` | Format canonique enqueue | Phase 3 réutilise EXACTEMENT le même `DashboardGovernedCommandRequest` builder |
| `interface_contracts.atomic_io.atomic_write_json` | Écriture atomique | Flag file `HALT.flag` utilise ce pattern |

---

## 3. Current Code Seam

### 3.1 Mécanique kill < 1 s

**Service Shadow** : `scripts/run_shadow_vps_service.py` instancie déjà `_ShadowVpsSignalController` qui handle `SIGINT` / `SIGTERM` et set `stop_requested = True`. La boucle `_run_shadow_vps_service_main_loop` checke ce flag à chaque cycle.

**Manque** :
1. Le service n'écrit PAS son PID dans un fichier → cockpit ne peut pas SIGTERM. Phase 3 ajoute `--pid-file` flag.
2. Le service ne watch PAS un flag fichier `HALT.flag` indépendamment du signal Unix → ajoute un check filesystem en début de chaque cycle (en plus du signal).

### 3.2 Governed command queue

`src/protocols/__init__.py` exporte :
```python
initialize_dashboard_command_queue(queue_path)
write_dashboard_command_request(queue_path, request)
process_dashboard_command_queue_once(queue_path, ...)
```

`scripts/run_dashboard_governed_command.py` montre le pattern canonique pour construire un `DashboardGovernedCommandRequest`. Codex DOIT lire ce fichier avant d'écrire `command_writer.py`.

Queue file path : à dériver depuis `service_dir`. Probablement `service_dir / "dashboard_command_queue/"` mais Codex doit vérifier le default dans `protocols`.

### 3.3 Permissions gate

`src/ui/operator_actions.py` :
- `OperatorActionType` enum (SET_HALTED, SUSPEND_PAIR, REQUEST_PAIR_RESUME, SUSPEND_ENGINE, …)
- `OperatorActionRequest` typed
- `OperatorActionOutcome` (ALLOWED / FORBIDDEN_PROFILE / FORBIDDEN_RUNTIME_MODE / …)
- `evaluate_locked_operator_action(request, …)` — appelé AVANT chaque enqueue

`_LIGHT_ALLOWED_ACTIONS` : seuls `VIEW_CRITICAL_SCREENS, SUSPEND_PAIR, REQUEST_PAIR_RESUME, SUSPEND_ENGINE, SET_HALTED` sont autorisés en LIGHT. En COMPLETE, tout est autorisé sauf transitions runtime_mode (gérées séparément).

### 3.4 Multipart upload FastAPI

Dépendance déjà installée : `python-multipart>=0.0.9`. FastAPI `File(...)` + `UploadFile` standard. Limite 100 MB enforced via Starlette `request.body()` size check ou middleware.

### 3.5 Service state for engine suspension

`build/build11_live_websocket_campaign/service/shadow_vps_service.state.json` — contient `service_status`, `loop_count`, etc. Champ `suspended_engines[]` pas encore présent dans le state observé. **Codex à confirmer** : où le service persiste-t-il les engines suspendus ? Si nulle part, c'est un trou de l'implémentation backend que Phase 3 doit signaler (sans le réparer — out of cockpit scope).

---

## 4. Placement

### 4.1 Nouveaux modules `src/cockpit/`

```
src/cockpit/
├── pid_tracker.py          # Atomic write/read/clear PID file
├── kill_channel.py         # Triple canal kill: flag + SIGTERM + async enqueue
├── command_writer.py       # Wrapper typed sur write_dashboard_command_request
├── permission_gate.py      # Wrapper sur evaluate_locked_operator_action
├── artefact_upload.py      # Multipart upload validator (size, hash, manifest)
├── routes_control.py       # POST /kill, /command/* endpoints
└── server.py               # extension: include_router(control_router)
```

### 4.2 Nouveaux templates Jinja2 (formulaires)

```
src/cockpit/templates/partials/
├── _action_panel.html              # extended: real <form> avec POST + CSRF token
├── _kill_dialog.html               # confirmation modal pour kill
├── _suspend_pair_form.html         # form select pair + textarea reason
├── _suspend_engine_form.html       # idem pour engine A/B/C/D
└── _artefact_upload_form.html      # form multipart + dropzone visuel simple
```

Pages ajoutées :
```
src/cockpit/templates/pages/
└── governance.html         # vue dédiée actions: kill + suspend + upload
```

### 4.3 Nouvelle route navigation sidebar

`partials/_sidebar.html` ajoute item "Governance" qui pointe vers `/governance` (au lieu de `?section=halt` actuel qui ne va nulle part).

### 4.4 Modification existante : service Shadow

`scripts/run_shadow_vps_service.py` :
- Nouveau flag CLI `--pid-file PATH` (optionnel, rétro-compat default `None`)
- Nouveau flag CLI `--halt-flag-file PATH` (optionnel, default `service_dir/HALT.flag`)
- Au démarrage : `pid_tracker.write_pid_atomic(path, os.getpid())` après `signal_controller` init
- Dans la boucle main : check `halt_flag_file.is_file()` au début de chaque cycle ; si présent → set `stop_requested = True` + log + supprimer le flag (one-shot)
- En finally : `pid_tracker.clear_pid(path)`

### 4.5 Configuration

`config/cockpit/cockpit.yml` (créé Phase 1) étendu avec :
```yaml
queue:
  path: ${REPO_ROOT}/build/build11_live_websocket_campaign/service/dashboard_command_queue
artefacts:
  upload_dir: ${REPO_ROOT}/build/build11_live_websocket_campaign/service/artefact_uploads
  max_size_bytes: 104857600  # 100 MB
kill:
  flag_file: ${REPO_ROOT}/build/build11_live_websocket_campaign/service/HALT.flag
operator:
  default_signed_by: aziz.benz@gmail.com
```

---

## 5. Files Changed

### 5.1 Nouveaux fichiers Python

| Fichier | Lignes estimées | Rôle |
|---|---|---|
| `src/cockpit/pid_tracker.py` | ~70 | atomic write/read/clear, `pid_is_alive` cross-platform |
| `src/cockpit/kill_channel.py` | ~110 | `request_halt(pid_file, flag_file, queue_path, reason, signed_by)` |
| `src/cockpit/command_writer.py` | ~140 | 4 wrappers : `enqueue_suspend_pair`, `enqueue_resume_pair`, `enqueue_suspend_engine`, `enqueue_resume_engine`, `enqueue_export_credential_inventory` |
| `src/cockpit/permission_gate.py` | ~60 | `gate_action(action_type, runtime_mode, …) -> OperatorActionOutcome` ; HTTP 403 sur refus |
| `src/cockpit/artefact_upload.py` | ~150 | streaming multipart save + SHA-256 hash + manifest write |
| `src/cockpit/routes_control.py` | ~250 | 7 endpoints (1 kill + 4 commands + 1 upload + 1 governance page) |
| `src/cockpit/server.py` | +30 | `app.include_router(control_router)` + nouvelle config kill_flag_file/queue_path |
| `scripts/run_cockpit.py` | +50 | flags CLI `--queue-path`, `--halt-flag-file`, `--artefact-upload-dir`, `--operator-signed-by` |
| `scripts/run_shadow_vps_service.py` | +60 | flags `--pid-file`, `--halt-flag-file` ; check flag chaque cycle ; PID write/clear |
| `src/cockpit/state.py` | +10 | `CockpitPaths` étend avec `queue_path`, `halt_flag_file`, `artefact_upload_dir`, `operator_signed_by` |

**Total nouveau code Python** : ~860 L (sans tests).

### 5.2 Templates Jinja2

| Fichier | Lignes estimées |
|---|---|
| `partials/_action_panel.html` | rewrite ~120 (forms réels au lieu de buttons disabled) |
| `partials/_kill_dialog.html` | ~50 (modal HTML + confirm) |
| `partials/_suspend_pair_form.html` | ~50 |
| `partials/_suspend_engine_form.html` | ~50 |
| `partials/_artefact_upload_form.html` | ~70 |
| `pages/governance.html` | ~80 |

### 5.3 CSS

`static/cockpit.css` +120 L : `.dialog`, `.dialog__overlay`, `.form-grid`, `.dropzone`, `.btn-confirm`, `.btn-confirm--danger`, `.toast`, `.flash-banner`.

### 5.4 Tests

| Fichier | Lignes |
|---|---|
| `tests/cockpit/test_pid_tracker.py` | ~100 |
| `tests/cockpit/test_kill_channel.py` | ~150 (mock `os.kill`, vérif flag écrit, async enqueue) |
| `tests/cockpit/test_command_writer.py` | ~140 |
| `tests/cockpit/test_permission_gate.py` | ~80 |
| `tests/cockpit/test_artefact_upload.py` | ~140 (multipart fixtures, size limit, hash) |
| `tests/cockpit/test_routes_control.py` | ~220 (TestClient sur 7 endpoints) |
| `tests/cockpit/integration/test_kill_e2e.py` | ~120 (fake service avec PID + signal handler) |

**Total tests** : ~950 L.

### 5.5 Aucune modification

`src/interface_contracts/`, `src/protocols/`, `src/ui/`, `src/engines/`, `src/meta_learning/`, `src/meta_minimal/`, `src/calibration_methods/`, `src/secrets_manager/`. Si Codex constate qu'une API publique manque → arrête et signale.

---

## 6. Claims Implemented

### C1 — PID tracker (pid_tracker.py)

```python
def write_pid_atomic(pid_file: Path, pid: int) -> None: ...
def read_pid(pid_file: Path) -> int | None: ...
def clear_pid(pid_file: Path) -> None: ...
def pid_is_alive(pid: int) -> bool: ...   # cross-platform best-effort
```

Atomique via `os.replace(tmp, dest)`. Lignes : 70.

### C2 — Service Shadow écrit son PID

`scripts/run_shadow_vps_service.py` flag `--pid-file PATH`. Si fourni :
1. Au démarrage (après `signal_controller` init) : `pid_tracker.write_pid_atomic(path, os.getpid())`
2. En `finally` (après `restore_signal_handlers()`) : `pid_tracker.clear_pid(path)`

Rétro-compat : flag absent → comportement actuel inchangé.

### C3 — Halt flag file watched par service Shadow

`scripts/run_shadow_vps_service.py` flag `--halt-flag-file PATH` (default `service_dir/HALT.flag`). Le main loop checke `halt_flag_file.is_file()` AU DÉBUT de chaque itération. Si présent :
1. Log structured `cockpit.halt_flag_observed`
2. Set `signal_controller._stop_requested = True` (via méthode publique)
3. Supprime le flag file (one-shot — sinon blocage permanent)

Permet kill < 1 s même si le PID file est désynchronisé.

### C4 — Endpoint POST /kill (kill_channel.py + routes_control.py)

```python
@router.post("/kill")
def post_kill(reason: str = Form(""), signed_by: str = Form("")) -> JSONResponse:
    outcome = permission_gate.gate_action(SET_HALTED, runtime_mode, …)
    if outcome != ALLOWED: raise HTTPException(403, str(outcome))
    result = kill_channel.request_halt(
        pid_file=app.state.paths.pid_file,
        flag_file=app.state.paths.halt_flag_file,
        queue_path=app.state.paths.queue_path,
        reason=reason or "cockpit /kill",
        signed_by=signed_by or app.state.default_signed_by,
    )
    return JSONResponse({"halt_requested": True, **result}, status_code=202)
```

`request_halt` séquence :
1. **Flag file** (atomic_write_json) avec `{requested_at, reason, signed_by}` — c'est la **trace canonique**
2. **SIGTERM** au PID s'il existe et `pid_is_alive(pid)` (sinon log warning, continue)
3. **Async enqueue** `SET_HALTED` via `BackgroundTasks` (best-effort, pas de blocking)
4. Retour avec timing `latency_ms` mesuré entre étape 1 et fin étape 3

**Garantie < 1 s** : étapes 1+2 < 50 ms, étape 3 async (n'attend pas).

### C5 — Endpoints POST /command/suspend-pair, /resume-pair

```python
@router.post("/command/suspend-pair")
def post_suspend_pair(pair: str = Form(...), reason: str = Form(""), signed_by: str = Form("")):
    if not _PAIR_RE.match(pair): raise HTTPException(400, "invalid pair")
    outcome = permission_gate.gate_action(SUSPEND_PAIR, …)
    if outcome != ALLOWED: raise HTTPException(403, …)
    command_writer.enqueue_suspend_pair(queue_path, pair=pair, reason=reason, signed_by=signed_by)
    return RedirectResponse(f"/?ok=suspend_pair_{pair}", status_code=303)
```

Symétrique pour `/command/resume-pair`. Pair regex : `^[A-Z]{2,10}USDT?$`.

### C6 — Endpoints POST /command/suspend-engine, /resume-engine

Form select avec `engine_id ∈ {engine_a, engine_b, engine_c, engine_d}`. Idem permission gate + enqueue.

### C7 — Endpoint POST /command/export-credential-inventory

1-clic, pas de form data. Enqueue `REQUEST_EXPORT_BINANCE_CREDENTIAL_INVENTORY`. Retour 303 vers `/governance?ok=export_inventory`.

### C8 — Endpoint POST /artefact/upload

```python
@router.post("/artefact/upload")
async def post_artefact_upload(
    artefact_kind: str = Form(...),
    file: UploadFile = File(...),
    signed_by: str = Form(""),
    notes: str = Form(""),
) -> JSONResponse:
    # Validate artefact_kind ∈ {ml_artifact, regime_detector, …}
    # Stream save with size guard (raise 413 si > 100 MB)
    # Compute SHA-256
    # Write manifest: artefact_uploads/<sha256>.manifest.json
    # Enqueue REQUEST_UPLOAD_ML_ARTIFACT (ou variante selon kind) avec sha256 ref
    return JSONResponse({"sha256": ..., "manifest_path": ..., "size_bytes": ...})
```

Lecture streaming chunk-by-chunk pour éviter OOM. Implémentation `artefact_upload.py`.

### C9 — Permission gate sur tous endpoints mutants

Avant chaque enqueue : `permission_gate.gate_action(action_type, runtime_mode_courant, …) -> OperatorActionOutcome`. Si `!= ALLOWED` → HTTP 403 avec body `{"forbidden_reason": str(outcome)}`.

Codex DOIT importer `evaluate_locked_operator_action` depuis `src/ui/operator_actions.py` — pas réimplémenter la logique.

### C10 — Pas de bouton interdit doctrinalement

UI ne montre JAMAIS :
- `ROLLBACK_TO_LIGHT` (LIGHT pas en VPS)
- Aucun bouton "Promote to Micro-live" / "Promote to Live" (gates explicites séparés)
- Aucun input modifiant capital tier

Audit Opus grep : `MICRO_LIVE|LIVE\b|ROLLBACK_TO_LIGHT|PROMOTE` dans `templates/` doit retourner 0 match dans des `<button>` / `<a>` mutants.

### C11 — Vue dédiée /governance

Page qui regroupe TOUTES les actions Phase 3 : kill switch, suspend pair, suspend engine, upload artefact, export inventory. Sidebar item "Governance" pointe ici. Layout 2 colonnes : actions critiques à gauche (kill, suspend), upload + export à droite.

### C12 — Default loopback bind preserved

Phase 1 garde-fou conservé : `--host 127.0.0.1` par défaut. Refus `0.0.0.0` sans `--unsafe-bind-all`.

### C13 — Audit trail dans flag file (canonique)

Le flag `HALT.flag` (kill) et chaque commande gouvernée enqueue contiennent : `requested_at_ms`, `signed_by`, `reason`, `cockpit_session_id`. La queue est la trace primaire pour les commandes ; le flag est la trace primaire pour le kill.

### C14 — Latence kill mesurée et exposée

`kill_channel.request_halt` mesure le temps entre étape 1 et fin étape 3. Retour HTTP inclut `latency_ms`. Phase 3 vise < 100 ms (bien sous le SLA 1 s).

### C15 — Action panel re-enabled avec vrais formulaires

`partials/_action_panel.html` (Phase 1 = boutons disabled) → POST `<form>` réels avec confirmation modal pour kill (HTML5 `<dialog>` ou modal CSS simple).

### C16 — Aucune modification des modules backend protégés

Audit Opus : `git diff src/interface_contracts/ src/protocols/ src/ui/ src/engines/ src/meta_learning/ src/meta_minimal/ src/calibration_methods/ src/secrets_manager/` doit être vide.

---

## 7. Tests and Proof

> **Codex doit remplir tous les slots ci-dessous.**

### 7.1 Tests unitaires

| Test | Slot |
|---|---|
| `test_pid_tracker.py::test_write_read_clear_round_trip` | ☐ |
| `test_pid_tracker.py::test_write_atomic_resists_crash_midwrite` | ☐ |
| `test_pid_tracker.py::test_pid_is_alive_returns_false_for_negative_pid` | ☐ |
| `test_kill_channel.py::test_request_halt_writes_flag_file` | ☐ |
| `test_kill_channel.py::test_request_halt_sends_sigterm` (mock os.kill) | ☐ |
| `test_kill_channel.py::test_request_halt_continues_when_pid_missing` | ☐ |
| `test_kill_channel.py::test_request_halt_enqueues_governed_command` | ☐ |
| `test_kill_channel.py::test_request_halt_latency_under_100ms` | ☐ |
| `test_command_writer.py::test_suspend_pair_writes_typed_request` | ☐ |
| `test_command_writer.py::test_suspend_engine_writes_typed_request` | ☐ |
| `test_permission_gate.py::test_gate_returns_allowed_for_complete_runtime` | ☐ |
| `test_permission_gate.py::test_gate_returns_forbidden_for_micro_live_promotion` | ☐ |
| `test_artefact_upload.py::test_streaming_save_below_limit` | ☐ |
| `test_artefact_upload.py::test_413_above_100mb` | ☐ |
| `test_artefact_upload.py::test_sha256_computed_correctly` | ☐ |
| `test_routes_control.py::test_post_kill_returns_202` | ☐ |
| `test_routes_control.py::test_post_kill_403_when_action_forbidden` | ☐ |
| `test_routes_control.py::test_post_suspend_pair_validates_form` | ☐ |
| `test_routes_control.py::test_post_artefact_upload_writes_manifest` | ☐ |
| `test_routes_control.py::test_get_governance_renders_html` | ☐ |

### 7.2 Test intégration kill end-to-end

`tests/cockpit/integration/test_kill_e2e.py` :
- Lance un faux service Python qui write son PID + handle SIGTERM
- Cockpit FastAPI TestClient lance `POST /kill`
- Assert : flag file existe, signal reçu, retour 202 en < 100 ms, latency_ms < 100

**Slot Codex** : ☐

### 7.3 Tests guardrails

| Commande | Attendu | Slot |
|---|---|---|
| `python -m dag_validator` | `new_violations=0` | ☐ |
| `python scripts/run_engineering_guardrails.py --baseline …` | `new_violations=0` | ☐ |
| `python -m pytest tests/cockpit/ -q` | tous Phase 1+2+3 pass | ☐ |
| `grep -E "MICRO_LIVE\|LIVE\\b\|ROLLBACK_TO_LIGHT\|PROMOTE" src/cockpit/templates/` | 0 match en boutons mutants | ☐ |
| `git diff src/interface_contracts/ src/protocols/ src/ui/ src/engines/ src/meta_learning/ src/meta_minimal/ src/calibration_methods/ src/secrets_manager/` | vide | ☐ |

### 7.4 Smoke kill manuel

```bash
# Service avec PID file (terminal 1)
python scripts/run_shadow_vps_service.py \
  --service-dir build/build11_live_websocket_campaign/service \
  --pid-file build/cockpit/v53_shadow.pid \
  --halt-flag-file build/build11_live_websocket_campaign/service/HALT.flag \
  --poll-interval-s 30 &

# Cockpit Phase 3 (terminal 2)
python scripts/run_cockpit.py --port 8093 \
  --pid-file build/cockpit/v53_shadow.pid \
  --halt-flag-file build/build11_live_websocket_campaign/service/HALT.flag

# Latence kill (terminal 3)
time curl -X POST http://127.0.0.1:8093/kill -d "reason=smoke" -d "signed_by=aziz.benz"
# expected: real < 1.0s, latency_ms < 100
# expected: PID a reçu SIGTERM, service en cours d'arrêt

# Verify flag file
cat build/build11_live_websocket_campaign/service/HALT.flag
# expected: {"requested_at_ms": ..., "reason": "smoke", "signed_by": "aziz.benz"}

# Verify async enqueue
ls build/build11_live_websocket_campaign/service/dashboard_command_queue/
# expected: nouveau fichier YYYYMMDDTHHMMSS_set_halted.json
```

**Slot Codex** : ☐ (coller sortie réelle, surtout `time` et `latency_ms`)

### 7.5 Smoke commande gouvernée

```bash
# Service tourne (warmup OK)
curl -X POST http://127.0.0.1:8093/command/suspend-pair \
  -d "pair=BTCUSDT" -d "reason=smoke" -d "signed_by=aziz.benz" -L

# expected: 303 redirect → 200 sur /?ok=suspend_pair_BTCUSDT
# expected: build/.../dashboard_command_queue/ contient nouveau request

# Verify request structure
cat build/.../dashboard_command_queue/<latest>.json
# expected: kind=SUSPEND_PAIR, pair=BTCUSDT, signed_by=aziz.benz, reason=smoke
```

**Slot Codex** : ☐

### 7.6 Smoke artefact upload

```bash
# Generate 50 MB fake artefact
dd if=/dev/urandom of=/tmp/fake_ml.pkl bs=1M count=50

curl -X POST http://127.0.0.1:8093/artefact/upload \
  -F "artefact_kind=ml_artifact" \
  -F "signed_by=aziz.benz" \
  -F "notes=smoke test 50MB" \
  -F "file=@/tmp/fake_ml.pkl"

# expected: JSON {"sha256": "...", "manifest_path": "...", "size_bytes": 52428800}
# expected: build/.../artefact_uploads/<sha256>.pkl + .manifest.json

# Test 413
dd if=/dev/urandom of=/tmp/big.pkl bs=1M count=120
curl -X POST http://127.0.0.1:8093/artefact/upload -F "file=@/tmp/big.pkl" ...
# expected: HTTP 413 Payload Too Large
```

**Slot Codex** : ☐

### 7.7 Preuve git

`git diff --stat` ne contient QUE `src/cockpit/`, `tests/cockpit/`, `scripts/run_cockpit.py`, `scripts/run_shadow_vps_service.py`, `config/cockpit/cockpit.yml`, `docs/...`, `static/cockpit.css`.

**Slot Codex** : ☐

---

## 8. Deferred / Not Done

| Item | Phase cible |
|---|---|
| SSE log tail (live streaming via EventSource) | Phase 3.1 |
| HTMX partial refresh (cards individuelles) | Phase 3.1 |
| Backtest UI (lancement async + render review.md) | Phase 4 |
| Artefacts > 100 MB via rsync + activation gouvernée | Phase 4 |
| Promotion runtime_mode (Shadow → Micro-live → Live) | Phase 5 (gates explicites séparés, pas dans le cockpit) |
| Multi-utilisateur / RBAC fin | Hors scope (Tailscale single-user OK) |
| MinIO/S3 stockage artefacts > 1 GB | Phase 5+ |
| Refusal Journal persistence (Phase 2.1) | Avant Phase 3 idéalement |
| Model Risk Register snapshot persistence (Phase 2.2) | Avant Phase 3 idéalement |

---

## 9. Risks

### R1 — Race condition PID file

**Scénario** : service crash juste avant `clear_pid`. PID recyclé par OS pour autre process. `POST /kill` SIGTERM un innocent.

**Mitigation** :
- Convention ops : PID file sous `/run/v53/` (tmpfs Linux, vidé au reboot)
- `pid_is_alive` checke `psutil.Process(pid).name()` matches `python` ou `v53_shadow_*` avant kill (Codex implémente)
- En cas de mismatch nom : ne PAS kill, log warning, continuer avec flag file uniquement

### R2 — Signal handling Windows

**Scénario** : tests tournent sur Windows ; `os.kill(pid, signal.SIGTERM)` n'a pas la même sémantique.

**Mitigation** :
- Tests `test_kill_channel` skipped sur Windows : `@pytest.mark.skipif(sys.platform == "win32")`
- Production VPS = Linux, donc OK
- En dev Windows : seul le **flag file** est utilisé (le service watch le flag même sans signal)

### R3 — Async enqueue échoue après kill réussi

**Scénario** : SIGTERM envoyé OK, flag écrit OK, mais `write_dashboard_command_request` échoue (queue dir corrompu).

**Mitigation** :
- Flag file = source de vérité audit (canonique)
- Async enqueue = best-effort, log warning si fail
- Cockpit retourne quand même 202 (le kill a réussi sur le canal critique)
- Doc dans le code : "flag file is canonical, queue write is best-effort secondary trail"

### R4 — Multipart upload OOM

**Scénario** : Codex charge tout le fichier en mémoire avant validation taille → OOM sur 100 MB.

**Mitigation** :
- Streaming chunk-by-chunk (8 KB chunks) avec compteur cumul
- Raise 413 dès que cumul > 100 MB (avant fin lecture)
- Test `test_413_above_100mb` valide

### R5 — Codex implémente sans permission gate

**Scénario** : un endpoint mutant skip `evaluate_locked_operator_action` → bypass governance.

**Mitigation** :
- Audit Opus § 12.1 : `grep "evaluate_locked_operator_action" src/cockpit/routes_control.py` doit retourner ≥ 5 matches (un par endpoint mutant)
- Code review : chaque endpoint mutant a un appel gate avant l'enqueue

### R6 — CSRF / form spoofing

**Scénario** : Tailscale + single-user mais quand même : un site malveillant en LAN local pourrait POST sur le cockpit via JS.

**Mitigation Phase 3** : pas de CSRF token (Tailscale single-user, surface d'attaque négligeable). Phase 5+ ajoutera un token si on ouvre à plusieurs utilisateurs.

### R7 — Latence kill > 1 s sous load

**Scénario** : flag write ou SIGTERM bloque sous IO contention.

**Mitigation** :
- Flag write atomique (1 ouverture + 1 rename, < 10 ms typique)
- SIGTERM Unix signal direct (< 5 ms)
- Async enqueue dans `BackgroundTasks` n'est PAS dans le chemin critique
- Test `test_request_halt_latency_under_100ms` valide

### R8 — Service ne watch pas le flag file (oubli implémentation)

**Scénario** : Codex oublie d'ajouter le check `halt_flag_file.is_file()` dans le main loop du service.

**Mitigation** :
- Audit Opus § 12.4 : `grep -n "halt_flag_file" scripts/run_shadow_vps_service.py` doit montrer le check au début du loop
- Test E2E `test_kill_e2e` lance un vrai service et vérifie qu'il s'arrête via flag file uniquement (sans SIGTERM, sur Windows)

---

## 10. Completion Status

```
Status: [COMPLETE | PARTIAL | BLOCKED]
Pytest: __ passed, __ failed (Phase 1 + 2 + 3)
Guardrails new_violations: __
Permission gate calls: __ (must be ≥ 5)
Forbidden buttons grep: __ (must be 0)
Backend modules diff: __ files (must be 0)
Files in diff stat: ____
Smoke kill latency: __ ms (must be < 1000)
Smoke artefact upload: [OK | FAIL]
Smoke 413 enforcement: [OK | FAIL]
Reasons (if not COMPLETE): ____
```

---

## 11. Next Safe Step

```
Suggested next pilot:
 [_] Phase 3.1 — SSE log tail + HTMX partial refresh
 [_] Phase 2.1 — refusal_journal persistence wiring
 [_] Phase 2.2 — model_risk_register snapshot persistence
 [_] Phase 4 — Backtest UI
 [_] Other: ____
```

---

## 12. Opus Audit Checklist

### 12.1 Permission gate
- [ ] `grep "evaluate_locked_operator_action\|gate_action" src/cockpit/routes_control.py` retourne ≥ 5 matches
- [ ] Chaque endpoint mutant (`/kill`, `/command/*`, `/artefact/upload`) a un appel gate avant l'enqueue
- [ ] Tests `test_routes_control` couvrent le cas 403

### 12.2 Backend modules untouched
- [ ] `git diff src/interface_contracts/ src/protocols/ src/ui/ src/engines/ src/meta_learning/ src/meta_minimal/ src/calibration_methods/ src/secrets_manager/` retourne vide

### 12.3 Forbidden buttons
- [ ] `grep -E "MICRO_LIVE\|LIVE\\b\|ROLLBACK_TO_LIGHT\|PROMOTE" src/cockpit/templates/` retourne 0 match dans `<button>` ou `<form>` mutant
- [ ] Aucun input modifiant le capital tier

### 12.4 Service Shadow modifications
- [ ] `grep -n "pid_file\|halt_flag_file" scripts/run_shadow_vps_service.py` montre les ajouts attendus
- [ ] Flag file watch en début de loop `_run_shadow_vps_service_main_loop`
- [ ] PID write/clear via try/finally garantit cleanup même sur crash

### 12.5 Kill latency
- [ ] Test `test_request_halt_latency_under_100ms` PASS
- [ ] Smoke `time curl -X POST .../kill` montre `real < 1.0s`
- [ ] Body retourne `latency_ms < 100`

### 12.6 Multipart upload safety
- [ ] Test `test_413_above_100mb` PASS
- [ ] Streaming chunk-by-chunk (pas de `await file.read()` sans limite)
- [ ] Manifest JSON contient sha256 + size + uploaded_at + signed_by

### 12.7 Tests coverage
- [ ] Pytest tests/cockpit/ ≥ 50 tests passent (Phase 1+2+3 cumulés)
- [ ] Tests Phase 1 + Phase 2 continuent de passer (régression nulle)
- [ ] Tests intégration `test_kill_e2e` PASS

### 12.8 Verdict format
```
GREENLIGHT — Phase 3 cockpit interactive complete.
Pytest: <N> passed, 0 failed
Guardrails: 0 new_violations
Permission gate calls: <N> (≥ 5)
Backend untouched: 0 diff
Kill latency proof: <X> ms (< 100)
Artefact upload smoke: OK
413 smoke: OK
Diff stat: <list>
Next: Phase 3.1 spec (SSE log tail)
```

Sinon :
```
REQUEST_FIX — <list failing audit items with file:line>
```

---

**Fin du spec — version 1.0 — 2026-04-27**
