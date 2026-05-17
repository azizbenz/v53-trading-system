# Spec — Local Lab Cockpit MVP (Phase 1)

**Date :** 2026-04-26
**Priorité :** P1 — débloque pilotage opérationnel sans CLI
**Auteur spec :** Opus (architecte)
**Implémenteur :** Codex
**Auditeur :** Opus (post-implémentation)

---

## 1. Objective

Livrer un **cockpit HTTP mince** sur le VPS Hetzner permettant de piloter le trading runtime V5.3 depuis un navigateur (PC LAB local) **sans écrire de code**, en réutilisant à 80 % l'infrastructure backend déjà en place :

- **22 commandes gouvernées** existantes (`DashboardGovernedCommandKind` enum)
- **`dashboard_command_queue` typée** avec dispatcher serveur (`process_dashboard_command_queue_once`)
- **Modules UI HTML** déjà rendus (`src/ui/technical_dashboard_html.py`, `complete_dashboard_*.py`)
- **Operator actions** typées avec permissions (`src/ui/operator_actions.py`)

**Le seul vrai trou** : aucun serveur HTTP n'expose ces dashboards / commandes. Cette spec comble exactement ce trou.

**Phase 1 = MVP minimum viable** :
- Kill switch < 1 s
- 4 commandes gouvernées via boutons (HALT, SUSPEND_PAIR, EXPORT_INVENTORY, list artefacts)
- Logs tail SSE
- Liste des exports artefacts disponibles
- Authentification réseau via **Tailscale** (pas de bearer token, pas de TLS public)

**Hors scope Phase 1** (voir § Deferred) :
- Backtest UI (Phase 2)
- Artefact upload/promotion UI complet (Phase 3)
- Multi-utilisateur / RBAC fin
- MinIO/S3 pour artefacts > 100 MB

---

## 2. Docs Governants

| Document / contrainte | Source | Implication |
|---|---|---|
| Doctrine "pas de profil LIGHT en deployment" | `CLAUDE.md` | Cockpit pilote uniquement le profil COMPLETE en VPS. UI doit refuser actions hors COMPLETE. |
| `runtime_mode` discipline | `CLAUDE.md` | Cockpit affiche le `runtime_mode` courant (shadow / micro_live / live), ne le mute jamais (transitions = scope futur). |
| Shadow → Micro-live → Live transition gates | `CLAUDE.md` | Cockpit ne bypass JAMAIS ces gates. Bouton "Promote" interdit en Phase 1. |
| Capital reality (€300-400) | `CLAUDE.md` | Affichage capital tier mais pas de modifier. |
| Operator actions LIGHT vs COMPLETE | `src/ui/operator_actions.py:_LIGHT_ALLOWED_ACTIONS` | Cockpit doit utiliser `evaluate_locked_operator_action()` pour toute action utilisateur. |
| Architecture Hetzner + Tailscale | Décision archi 2026-04-26 (cf. session) | FastAPI bind sur `tailscale0` uniquement, pas `0.0.0.0`. Hetzner firewall ferme tout sauf SSH. |
| Kill switch < 1 s | Décision archi 2026-04-26 | Double canal : flag fichier + SIGTERM PID + enqueue gouverné async. |

---

## 3. Current Code Seam

### 3.1 Commandes gouvernées disponibles (22)

`src/interface_contracts/dashboard_governed_command.py` (probablement) — enum `DashboardGovernedCommandKind` :

**Trading control (5)** :
- `SET_HALTED` — kill total
- `ROLLBACK_TO_LIGHT` — rollback profile
- `SUSPEND_PAIR` / `REQUEST_PAIR_RESUME`
- `SUSPEND_ENGINE` / `REQUEST_ENGINE_RESUME`

**Artefact ML/Regime (10)** :
- 4 × `REQUEST_UPLOAD_*` (ML active, regime detector active, ML challenger, regime challenger)
- 2 × `REQUEST_CLEAR_*` (challengers)
- 6 × `REQUEST_EXPORT_*` (active ML, active regime, comparison evidence ×2, verdict bundle, audit bundle)

**Credentials (4)** :
- `REQUEST_UPLOAD_BINANCE_CREDENTIALS_BUNDLE`
- `REQUEST_ACTIVATE_BINANCE_CREDENTIALS_PROFILE`
- `REQUEST_DEACTIVATE_BINANCE_CREDENTIALS_PROFILE`
- `REQUEST_EXPORT_BINANCE_CREDENTIAL_INVENTORY`

**Phase 1 expose 4 boutons seulement** :
1. `SET_HALTED` (via canal kill direct, pas via queue)
2. `SUSPEND_PAIR` (formulaire pair → enqueue)
3. `REQUEST_PAIR_RESUME` (formulaire pair → enqueue)
4. `REQUEST_EXPORT_BINANCE_CREDENTIAL_INVENTORY` (1-clic → enqueue)

### 3.2 Protocols disponibles

`src/protocols/__init__.py` — déjà importable :
```python
from protocols import (
    initialize_dashboard_command_queue,
    write_dashboard_command_request,
    process_dashboard_command_queue_once,
)
```

CLI référence : `scripts/run_dashboard_governed_command.py` — montre exactement comment construire un `DashboardGovernedCommandRequest` valide et l'écrire dans la queue.

### 3.3 Modules UI HTML existants

`src/ui/` contient déjà :
- `technical_dashboard_html.py:render_technical_dashboard_html()` — rendu HTML des `DashboardSection` / `DashboardCard`
- `contracts.py` — `DashboardCard`, `DashboardSection`, `OperatorActionRequest`, `OperatorActionType`, `OperatorActionOutcome`
- `operator_actions.py:evaluate_locked_operator_action()` — gate de permission par profil
- `complete_dashboard_view.py`, `complete_dashboard_control_plane.py`, `complete_dashboard_artifact_sections.py` — sections déjà câblées

**Réutilisation Phase 1** : `render_technical_dashboard_html()` + construire des `DashboardSection` ad-hoc avec les status courants du service Shadow.

### 3.4 Service Shadow runtime

`scripts/run_shadow_vps_service.py` :
- Tourne en boucle (`_run_shadow_vps_service_main_loop`)
- A déjà un `_ShadowVpsSignalController` qui gère `SIGINT` / `SIGTERM`
- **N'écrit PAS son PID** dans un fichier — c'est l'ajout requis Phase 1.

Logs : Le service écrit dans `stdout` (pas de fichier dédié). À orienter vers `build/build11_live_websocket_campaign/service/shadow_service.log` pour permettre tail SSE.

### 3.5 Tailscale (hors-code, ops)

Côté VPS Hetzner :
- Install `tailscale` (apt), `tailscale up` avec auth key headless
- Hetzner firewall : ouvrir uniquement tcp/22 et tcp/41641 (Tailscale UDP NAT-T)

Côté PC LAB :
- Install Tailscale Windows
- Login Tailscale (compte unique)

Connexion automatique : depuis le PC, `http://v53-vps:8080` résout via Tailscale magic DNS.

---

## 4. Placement

### Nouveau module Python : `src/cockpit/`

```
src/cockpit/
├── __init__.py
├── server.py              # FastAPI app instance + lifespan
├── routes_control.py      # /kill, /command/* endpoints
├── routes_observability.py# /, /logs/tail, /artefacts endpoints
├── pid_tracker.py         # write/read /run/v53/v53_shadow_service.pid
├── kill_channel.py        # POST /kill = flag file + SIGTERM
├── command_writer.py      # wrapper autour de write_dashboard_command_request
├── log_tail.py            # SSE tail de shadow_service.log
├── artefact_index.py      # liste auto_exports/ + meta
└── html_renderer.py       # wrapper autour de render_technical_dashboard_html
```

### Nouveau script CLI : `scripts/run_cockpit.py`

Lance le serveur cockpit avec config CLI :
- `--host` (défaut : `0.0.0.0` en dev local, doit être surchargé en `tailscale0` en prod via `--host 100.x.y.z`)
- `--port` (défaut : `8080`)
- `--service-dir` (défaut : `build/build11_live_websocket_campaign/service`)
- `--pid-file` (défaut : `/run/v53/v53_shadow_service.pid` Linux, fallback `build/cockpit/v53_shadow_service.pid` Windows)
- `--log-file` (défaut : `build/build11_live_websocket_campaign/service/shadow_service.log`)
- `--auto-exports-root` (défaut : `build/build11_live_websocket_campaign/auto_exports`)

### Modification existante : `scripts/run_shadow_vps_service.py`

Ajout : écriture du PID au démarrage, suppression à l'arrêt.

```python
pid_tracker.write_pid_atomic(pid_file_path, os.getpid())
try:
    ...
finally:
    pid_tracker.clear_pid(pid_file_path)
```

Nouveau flag CLI `--pid-file` (optionnel, désactivé par défaut pour rétrocompat).

### Templates HTML : **Jinja2 dès Phase 1** (révision 2026-04-26)

Décision révisée : Jinja2 introduit dès Phase 1 pour éviter une réécriture complète en Phase 2. Le coût est marginal (1 dépendance, 1 setup `Jinja2Templates(directory=...)`).

```
src/cockpit/templates/
├── base.html              # Layout : sidebar + topbar + content slot
├── index.html             # Landing : welcome banner + stat cards + pair selector + actions
├── partials/
│   ├── _sidebar.html      # Navigation gauche (Dashboard, Trading, Backtest, Artefacts, Logs)
│   ├── _topbar.html       # Search + notifications + user menu
│   ├── _stat_card.html    # Card métrique réutilisable (price/change/sparkline)
│   ├── _pair_selector.html# Dropdown / pills BTCUSDT, ETHUSDT, ...
│   ├── _action_panel.html # Boutons gouvernés (HALT, suspend, export)
│   └── _logs_pane.html    # SSE log tail viewer
└── components/
    ├── candle_placeholder.html  # Iframe vers Grafana panel ou img placeholder
    └── markets_table.html       # Tableau des paires (price, %7d, %24h, vol, mcap)
```

`render_technical_dashboard_html()` (existant `src/ui/`) reste dispo pour pages techniques avancées Phase 2+. Pour la landing Phase 1, on utilise Jinja2 directement (plus flexible pour le design demandé).

### Fichiers de config

- `config/cockpit/cockpit.yml` — host/port/paths overridable

---

## 5. Files Changed

### Nouveaux fichiers

| Fichier | Lignes estimées | Rôle |
|---|---|---|
| `src/cockpit/__init__.py` | ~5 | Package marker |
| `src/cockpit/server.py` | ~80 | FastAPI app + lifespan + middleware |
| `src/cockpit/routes_control.py` | ~120 | 4 endpoints commandes (kill, suspend pair, resume pair, export inventory) |
| `src/cockpit/routes_observability.py` | ~100 | 3 endpoints observabilité (/, /logs/tail SSE, /artefacts) |
| `src/cockpit/pid_tracker.py` | ~60 | Atomic write/read/clear PID file |
| `src/cockpit/kill_channel.py` | ~80 | Flag file + SIGTERM PID + enqueue async |
| `src/cockpit/command_writer.py` | ~70 | Wrapper typed sur `write_dashboard_command_request` |
| `src/cockpit/log_tail.py` | ~60 | SSE generator pour tail file |
| `src/cockpit/artefact_index.py` | ~70 | Scan `auto_exports/`, retourne liste typée |
| `src/cockpit/html_renderer.py` | ~120 | Compose `DashboardSection` + Tailwind layout |
| `scripts/run_cockpit.py` | ~80 | CLI launcher |
| `config/cockpit/cockpit.yml` | ~20 | Default config |
| `tests/cockpit/__init__.py` | ~1 | Test package |
| `tests/cockpit/test_pid_tracker.py` | ~80 | PID atomic write/read/clear |
| `tests/cockpit/test_kill_channel.py` | ~120 | Flag file + SIGTERM mocked |
| `tests/cockpit/test_command_writer.py` | ~80 | Wrapper enqueue |
| `tests/cockpit/test_artefact_index.py` | ~80 | Scan + tri par date |
| `tests/cockpit/test_routes_control.py` | ~120 | TestClient FastAPI sur 4 endpoints |
| `tests/cockpit/test_routes_observability.py` | ~100 | TestClient SSE + /artefacts |
| `tests/cockpit/test_html_renderer.py` | ~60 | Snapshot HTML structure |

**Total nouveau code** : ~1500 lignes (src + tests).

### Modifications existantes

| Fichier | Changement | Impact |
|---|---|---|
| `scripts/run_shadow_vps_service.py` | + flag `--pid-file`, write PID atomic au démarrage, clear au teardown via `try/finally` | Rétrocompat OK (flag optionnel) |
| `scripts/Run-V53LocalSolution.ps1` | + param `-LaunchCockpit` (switch) + `-CockpitPort` | Rétrocompat OK |
| `scripts/Start-BinanceShadowLiveCampaign.ps1` | Pas de changement nécessaire — le service existant accepte déjà `--pid-file` après ajout T1 | — |
| `pyproject.toml` ou `requirements.txt` | Ajouter `fastapi>=0.110`, `uvicorn[standard]>=0.27`, `jinja2>=3.1`, `python-multipart>=0.0.9` (pour future Phase 3 upload) | Nouvelles deps |

### Aucune modification dans `src/interface_contracts/`, `src/protocols/`, `src/ui/`

C'est délibéré. Le cockpit **consomme** ces APIs publiques sans les muter. Si Codex constate qu'une API n'est pas exposable telle quelle, il **arrête et signale** plutôt que de modifier le contrat.

---

## 6. Claims Implemented

### C1 — Endpoint `GET /` retourne dashboard HTML

**Inspiration design** : layout type "Crypto Admin" (dark theme deep navy `#0e1726`, accent jaune-orange `#fbbf24` pour la marque "Benz Family", sidebar fixe gauche, topbar avec search + notifications, content principal en grille).

**Structure visuelle (rendu Jinja2 `index.html`)** :

```
┌────────────────────────────────────────────────────────────────────┐
│ [Crypto-style topbar: search · notif · profile · settings]         │
├──────────┬─────────────────────────────────────────────────────────┤
│          │  ┌──────────────────────────────────────────────────┐   │
│ SIDEBAR  │  │  WELCOME BENZ FAMILY · AI BOT TRADING            │   │
│          │  │  Runtime: shadow · Service: ●running · PID 1234  │   │
│ Dashboard│  └──────────────────────────────────────────────────┘   │
│ Trading  │                                                          │
│ Backtest │  ┌────────┐ ┌────────┐ ┌────────┐    ┌──────────────┐  │
│ Artefact │  │BTCUSDT │ │ETHUSDT │ │BNBUSDT │    │  AMOUNT       │  │
│ Logs     │  │$67,200 │ │$3,450  │ │$640    │    │  $XXX,XXX     │  │
│ Settings │  │+1.2% ↗ │ │+0.5% ↗ │ │-0.3% ↘ │    │  Deposit Wdrw │  │
│          │  └────────┘ └────────┘ └────────┘    └──────────────┘  │
│          │                                                          │
│          │  ┌────── PAIR SELECTOR ──────┐  ┌──── EXCHANGE ────┐    │
│          │  │ ●BTCUSDT  ○ETHUSDT  +Add │  │ Send: [ETH ▾]    │    │
│          │  └───────────────────────────┘  │     ↕            │    │
│          │                                  │ Get:  [BTC ▾]    │    │
│          │  ┌──── TRADING MARKET CHART ────┐│                  │    │
│          │  │ [iframe Grafana panel]        │└──────────────────┘    │
│          │  │ ou candle preview placeholder │                        │
│          │  └───────────────────────────────┘ ┌──── ACTIONS ────┐   │
│          │                                     │ 🛑 KILL ALL     │   │
│          │  ┌──── MARKETS TABLE ─────────────┐ │ ⏸  SUSPEND PAIR │   │
│          │  │ Pair   Price  %7d  %24h  Vol    │ │ ▶  RESUME PAIR  │   │
│          │  │ BTC    67200  10.25 4.52 35.1B  │ │ 📦 EXPORT INV   │   │
│          │  │ ETH    3450    8.50 2.57 25.4B  │ └─────────────────┘   │
│          │  └────────────────────────────────┘                       │
│          │                                                            │
│          │  ┌──── LIVE LOGS (SSE) ──────────────────────────────┐    │
│          │  │ 14:02:15 cycle=42 captured BTCUSDT=67200          │    │
│          │  │ 14:02:45 cycle=43 ...                             │    │
│          │  └────────────────────────────────────────────────────┘    │
└──────────┴─────────────────────────────────────────────────────────┘
```

**Contenu data-driven** :
- **Welcome banner** : `"Welcome Benz Family · AI Bot Trading"` (en-tête fixe, demande utilisateur 2026-04-26)
- **Status row** : runtime_mode, service status (running via PID file présent), PID, dernière capture timestamp
- **3 stat cards** : top 3 paires de la `live_websocket_config.json` (par défaut BTC/ETH/BNB), avec dernier prix lu depuis `live_websocket_snapshot_batch.json`, variation 24h calculée si dispo
- **Pair selector** : pills cliquables qui filtrent les graphiques + définissent la pair pour les actions SUSPEND/RESUME (state via querystring `?pair=BTCUSDT`)
- **Exchange widget** : décoratif Phase 1 (placeholder, lecture seule). Phase 3 connectera aux ordres simulés.
- **Trading chart** : iframe vers panneau Grafana spécifique (`http://v53-vps:3000/d-solo/v53-shadow-vps-local/...?panelId=N`) — réutilise Grafana qui tourne déjà
- **Markets table** : lecture du `live_websocket_snapshot_batch.json`, format identique à l'image de référence
- **Action panel droite** : 4 boutons (kill rouge, suspend orange, resume vert, export gris) → POST sur les endpoints C2-C5
- **Live logs** : SSE depuis `/logs/tail` rendu en console terminal-style

**Refresh strategy** :
- Cards et table : refresh auto toutes les 10 s via HTMX (`hx-get="/partials/stats" hx-trigger="every 10s"`)
- Logs : streaming SSE permanent (pas de refresh)
- Pas de full page reload — UX fluide

**Réutilisation** :
- `_runtime_mode_from_warmup_summary()` lit `vps_warmup_run.summary.json`
- `artefact_index.list_pairs_from_config()` lit `live_websocket_config.json`
- `markets_data.read_snapshot_batch()` lit `live_websocket_snapshot_batch.json`

### C2 — Endpoint `POST /kill` arrête le service en < 1 s

Séquence :
1. Lire PID depuis `pid_file_path` (404 si absent → service pas tracké)
2. Écrire flag `Path(service_dir) / "HALT.flag"` (atomic write JSON `{"requested_at": ts, "reason": form.reason}`)
3. `os.kill(pid, signal.SIGTERM)` — déclenche `_ShadowVpsSignalController` côté service
4. Async background : `write_dashboard_command_request(SET_HALTED, ...)` pour audit gouverné
5. Retour HTTP 202 immédiat avec body `{"halt_requested": true, "pid": pid, "flag_path": "..."}`

**Garantie < 1 s** : étapes 1-3 < 50 ms, étape 4 async fire-and-forget.

### C3 — Endpoint `POST /command/suspend-pair` enqueue commande gouvernée

- Form data : `pair` (e.g. `BTCUSDT`), `reason` (texte libre)
- Validation : `pair` doit matcher regex `^[A-Z]{2,10}USDT?$`
- Construit `DashboardGovernedCommandRequest(kind=SUSPEND_PAIR, pair=pair, ...)` selon le pattern de `scripts/run_dashboard_governed_command.py`
- Appelle `write_dashboard_command_request(queue_path, request)`
- Retour : HTTP 202 + redirect 303 vers `/` avec query `?ok=suspend_pair_BTCUSDT`

### C4 — Endpoint `POST /command/resume-pair` enqueue `REQUEST_PAIR_RESUME`

Symétrique de C3.

### C5 — Endpoint `POST /command/export-credential-inventory` enqueue export

1-clic, pas de paramètres. Enqueue `REQUEST_EXPORT_BINANCE_CREDENTIAL_INVENTORY`.

### C6 — Endpoint `GET /logs/tail` stream SSE

- Tail des 200 dernières lignes du log au connect
- Puis `yield` chaque nouvelle ligne dès qu'elle arrive (poll `os.stat` sur file size, lecture incrémentale)
- Format SSE : `data: <line>\n\n`
- Heartbeat toutes les 15 s (`event: ping\ndata: {}\n\n`)
- Limite : ferme la connexion après 1 h (anti-leak Phase 1)

### C7 — Endpoint `GET /artefacts` liste exports disponibles

- Scan récursif `auto_exports/YYYY-MM-DD/`
- Retourne JSON : `[{"date": "2026-04-26", "files": [{"name": "...", "size_bytes": ..., "mtime_iso": "..."}]}, ...]`
- Tri par date desc, puis par mtime desc

### C8 — PID tracker côté service

- `pid_tracker.write_pid_atomic(path, pid)` :
  - mkdir parent si absent
  - écrit `str(pid).encode()` dans `path.tmp` puis `os.replace(path.tmp, path)`
- `pid_tracker.read_pid(path) -> int | None` : retourne `None` si absent ou contenu invalide
- `pid_tracker.clear_pid(path)` : `path.unlink(missing_ok=True)`

### C9 — Service Shadow écrit son PID au démarrage

Modif `run_shadow_vps_service.py` :
- Nouveau flag `--pid-file PATH` (défaut : `None` = pas d'écriture, rétrocompat)
- Si flag fourni : `pid_tracker.write_pid_atomic(path, os.getpid())` après init signal controller
- `try / finally` garantit `clear_pid()` même sur crash

### C10 — Permissions via `evaluate_locked_operator_action()`

Avant chaque enqueue, le cockpit construit un `OperatorActionRequest` typé et appelle `evaluate_locked_operator_action()`. Si `outcome != ALLOWED`, retourne HTTP 403 avec `outcome.reason` dans le body.

Garantit que LIGHT (jamais en VPS de toute façon) ne peut pas faire `ROLLBACK_TO_LIGHT` etc.

### C11 — Binding réseau sécurisé par défaut

`scripts/run_cockpit.py` :
- Par défaut `--host 127.0.0.1` (loopback)
- En prod VPS : passer `--host <tailscale-ip>` explicitement
- **Refus de bind sur `0.0.0.0`** sauf flag explicite `--unsafe-bind-all` (avec warning loggué)

### C12 — Configuration Tailscale documentée

Nouveau fichier `docs/production_deployment_plan/operations/tailscale_setup.md` (court, ~80 lignes) :
- Install Tailscale Hetzner (apt commands)
- Auth key headless
- Hetzner firewall rules (UFW snippets)
- Verification : `tailscale status`, `curl http://v53-vps:8080`

---

## 7. Tests and Proof

> **Codex doit remplir tous les slots ci-dessous. Aucun claim de COMPLETE sans ces preuves.**

### 7.1 Tests unitaires (à créer)

| Test | Cible | Slot Codex |
|---|---|---|
| `test_pid_tracker.py::test_write_read_clear_round_trip` | `pid_tracker.py` | ☐ |
| `test_pid_tracker.py::test_atomic_write_resists_crash_midwrite` | `pid_tracker.py` | ☐ |
| `test_pid_tracker.py::test_read_returns_none_if_corrupted` | `pid_tracker.py` | ☐ |
| `test_kill_channel.py::test_kill_writes_flag_file` | `kill_channel.py` | ☐ |
| `test_kill_channel.py::test_kill_sends_sigterm_to_pid` (mock `os.kill`) | `kill_channel.py` | ☐ |
| `test_kill_channel.py::test_kill_404_if_pid_file_missing` | `kill_channel.py` | ☐ |
| `test_kill_channel.py::test_kill_enqueues_governed_command_async` | `kill_channel.py` | ☐ |
| `test_command_writer.py::test_suspend_pair_writes_typed_request` | `command_writer.py` | ☐ |
| `test_command_writer.py::test_invalid_pair_raises` | `command_writer.py` | ☐ |
| `test_artefact_index.py::test_scan_returns_sorted_by_date_desc` | `artefact_index.py` | ☐ |
| `test_artefact_index.py::test_scan_handles_empty_dir` | `artefact_index.py` | ☐ |
| `test_routes_control.py::test_post_kill_returns_202` (TestClient) | `routes_control.py` | ☐ |
| `test_routes_control.py::test_post_suspend_pair_validates_form` | `routes_control.py` | ☐ |
| `test_routes_control.py::test_post_command_403_if_action_forbidden` | `routes_control.py` | ☐ |
| `test_routes_observability.py::test_get_root_returns_html` | `routes_observability.py` | ☐ |
| `test_routes_observability.py::test_get_artefacts_returns_json` | `routes_observability.py` | ☐ |
| `test_routes_observability.py::test_get_logs_tail_sse_format` | `routes_observability.py` | ☐ |
| `test_html_renderer.py::test_dashboard_html_contains_required_sections` | `html_renderer.py` | ☐ |

### 7.2 Tests d'intégration (à créer)

`tests/cockpit/integration/test_kill_e2e.py` :
- Lance un faux service avec PID file + signal handler
- Appelle `POST /kill` via TestClient
- Vérifie : flag file existe, signal reçu, retour 202 en < 100 ms

**Slot Codex** : ☐

### 7.3 Tests guardrails

| Commande | Attendu | Slot Codex |
|---|---|---|
| `python -m dag_validator` | `new_violations=0` | ☐ |
| `python scripts/run_engineering_guardrails.py --baseline config/engineering_guardrails_baseline.json` | `new_violations=0` | ☐ |
| `python -m pytest tests/cockpit/ -q` | All pass | ☐ |

### 7.4 Smoke run manuel à documenter

Codex doit lancer le smoke et coller la sortie ici :

```bash
# 1. Service Shadow avec PID tracker
python scripts/run_shadow_vps_service.py \
  --service-dir build/build11_live_websocket_campaign/service \
  --pid-file build/cockpit/v53_shadow_service.pid \
  --poll-interval-s 30 &

# 2. Cockpit
python scripts/run_cockpit.py \
  --host 127.0.0.1 \
  --port 8080 \
  --pid-file build/cockpit/v53_shadow_service.pid

# 3. Test kill latency (depuis autre terminal)
time curl -X POST http://127.0.0.1:8080/kill -d "reason=test"
```

**Slot Codex** : ☐ (coller sortie réelle, en particulier `time` < 1.0s)

### 7.5 Preuve git

| Commande | Slot Codex |
|---|---|
| `git diff --stat` (uniquement `src/cockpit/`, `tests/cockpit/`, `scripts/run_cockpit.py`, `scripts/run_shadow_vps_service.py`, `config/cockpit/`, `docs/...tailscale_setup.md`) | ☐ |

---

## 8. Deferred / Not Done

| Item | Raison report | Phase cible |
|---|---|---|
| Backtest UI (formulaire date range, lancement async, render `meta_learning_review.md`) | Plus complexe, mérite spec dédié | Phase 2 |
| Artefact upload (POST `/artefact` multipart < 100 MB) | Manipule artefacts ML production, scope sensible | Phase 3 |
| Artefact promote / shadow challenger lifecycle UI | Idem | Phase 3 |
| Authentification fine (multi-utilisateur, RBAC) | Tailscale suffit pour single-user | Hors scope |
| TLS public + Caddy + Let's Encrypt | Évité par Tailscale | Hors scope |
| MinIO/S3 pour artefacts > 100 MB | Pas besoin tant que < 100 MB | Phase 3+ |
| Promotion runtime_mode (Shadow → Micro-live) | Doctrinalement interdit sans gates explicites | Phase 4 |
| Notifications Telegram/email sur événements critiques | Le service a déjà infra Telegram (cf. `telegram_post_func`), juste à hook | Phase 2 |
| Re-render Grafana dashboards depuis le cockpit | Grafana garde son rôle d'observatoire séparé | Hors scope |

---

## 9. Risks

### R1 — Race condition PID file vs SIGTERM

**Scénario** : service crash juste avant `clear_pid()`. PID file pointe vers un PID recyclé par OS pour un autre process. `POST /kill` envoie SIGTERM à un innocent.

**Mitigation** :
- Pas de mitigation parfaite côté code. **Convention ops** : le PID file est sous `/run/` (tmpfs Linux, vidé au reboot).
- Optionnel Phase 1 : checker `psutil.Process(pid).name()` matches `"python"` avant kill. **Codex à décider** : faire ou différer.

### R2 — Signal handling Windows ≠ Linux

**Scénario** : dev local sur Windows, `os.kill(pid, signal.SIGTERM)` n'a pas la même sémantique. Le service Windows n'a pas le même handler.

**Mitigation** :
- Phase 1 : cibler Linux uniquement pour `/kill`. Sur Windows, retourner HTTP 501 Not Implemented avec message clair.
- Tests : skip `test_kill_*` sur Windows (`@pytest.mark.skipif(sys.platform == "win32")`)

### R3 — SSE memory leak si client jamais déconnecté

**Mitigation** :
- Limite de 1 h par connexion (fermeture explicite côté serveur)
- Heartbeat toutes les 15 s pour détecter clients déconnectés silencieusement

### R4 — Binding `0.0.0.0` accidentel en prod

**Scénario** : Codex met `0.0.0.0` par défaut sans réfléchir. VPS Hetzner expose 8080 au monde.

**Mitigation** :
- Default `127.0.0.1` (loopback only) — explicit `--host` requis pour bind ailleurs
- Refus du bind `0.0.0.0` sauf flag explicite `--unsafe-bind-all` avec warning loggué + log line `WARNING: cockpit bound on 0.0.0.0 — ensure firewall blocks public access`

### R5 — Audit trail incohérent entre kill direct et command queue

**Scénario** : `POST /kill` exécute SIGTERM avant que l'enqueue async ait terminé. Si l'enqueue échoue, on a un kill sans trace gouvernée.

**Mitigation** :
- L'enqueue est best-effort (logged warning si fail), le **flag file** sert de trail primaire.
- Le flag file contient timestamp + reason + actor — c'est la source de vérité du kill, pas la queue.
- Doc dans le code : "flag file is canonical, queue write is best-effort secondary trail"

### R6 — Codex implémente sans relire `evaluate_locked_operator_action()`

**Scénario** : bypass des permissions, n'importe qui peut tout faire.

**Mitigation** :
- Audit Opus checklist § 12 vérifie explicitement chaque endpoint appelle bien `evaluate_locked_operator_action()` avant l'action.

### R7 — Dépendance FastAPI / uvicorn nouvelle dans le repo

**Scénario** : casse `pyproject.toml`, conflit version avec autre dep.

**Mitigation** :
- Codex doit lancer `pip install -e .` dans un venv frais et confirmer pas de conflit
- Slot proof § 7.5 doit inclure `pip list | grep -E "fastapi|uvicorn|starlette"` après install

---

## 10. Completion Status

> **Slot Codex à remplir après implémentation** :

```
Status: [COMPLETE | PARTIAL | BLOCKED]
Pytest: __ passed, __ failed
Guardrails new_violations: __
Files in diff stat: ____
Smoke run kill latency: __ ms
Reasons (if not COMPLETE): ____
```

---

## 11. Next Safe Step

> **Slot Codex à remplir** :

```
Suggested next pilot:
 [_] Write Phase 2 spec (backtest UI)
 [_] Document Tailscale operations (separate doc)
 [_] Add Phase 1 Telegram alerts hook
 [_] Other: ____
```

---

## 12. Opus Audit Checklist

Après livraison Codex, Opus vérifie :

### 12.1 Architecture / contrats
- [ ] **Aucune modification** dans `src/interface_contracts/`, `src/protocols/`, `src/ui/` (audit `git diff src/interface_contracts/ src/protocols/ src/ui/` doit être vide)
- [ ] Tous les endpoints `/command/*` appellent `evaluate_locked_operator_action()` AVANT l'enqueue (grep `evaluate_locked_operator_action` dans `src/cockpit/routes_control.py` doit retourner ≥ 4 matches)
- [ ] `POST /kill` n'écrit PAS dans `command_queue` de manière bloquante (background task via `asyncio.create_task` ou `BackgroundTasks` FastAPI)
- [ ] Flag file `HALT.flag` écrit avec `atomic_write_json` (pattern V5.3)

### 12.2 Sécurité
- [ ] Default `--host 127.0.0.1` confirmé dans `scripts/run_cockpit.py`
- [ ] `--unsafe-bind-all` flag présent et loggué warning
- [ ] Aucun secret en clair dans le code (grep `BINANCE_API_KEY|API_SECRET|password\s*=\s*['"]\w` dans `src/cockpit/` et `scripts/run_cockpit.py` doit être vide)
- [ ] Doc Tailscale crée et liste les ports à fermer

### 12.3 Tests
- [ ] `pytest tests/cockpit/ -q` passe à 100%
- [ ] Couverture : chaque fichier `src/cockpit/*.py` a son `tests/cockpit/test_*.py` correspondant
- [ ] Tests intégration `test_kill_e2e.py` mesure latence < 100 ms (devrait être bien sous 1 s)
- [ ] `test_kill_channel.py` skip sur Windows avec marker explicite

### 12.4 Smoke proof
- [ ] Sortie `time curl -X POST .../kill` collée dans § 7.4 montre `real < 1.0s`
- [ ] `git diff --stat` collé dans § 7.5 ne contient QUE les fichiers listés § 5

### 12.5 Doctrine / canon
- [ ] Aucun bouton "promote runtime_mode" dans l'UI (vérifié visuellement et par grep `MICRO_LIVE|LIVE` dans HTML rendered)
- [ ] Aucun bypass de transition gates Shadow → Micro-live → Live
- [ ] Capital tier affiché en lecture seule, pas de form `<input>` modifiant le tier

### 12.6 Verdict format
Si tous les items ci-dessus passent :
```
GREENLIGHT — Phase 1 cockpit MVP complete.
Pytest: <N> passed, 0 failed
Guardrails: 0 new_violations
Diff stat: <list>
Kill latency proof: <X> ms
Next: Phase 2 spec (backtest UI)
```

Sinon :
```
REQUEST_FIX — <enumerate failing audit items with file:line refs>
```

---

## 13. Annexe — Exemple endpoint complet (référence Codex)

Pour éviter ambiguïté, voici le squelette attendu pour `POST /command/suspend-pair` :

```python
# src/cockpit/routes_control.py

from fastapi import APIRouter, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import re

from interface_contracts import (
    DashboardGovernedCommandKind,
    RuntimeMode,
)
from ui.contracts import (
    OperatorActionRequest,
    OperatorActionType,
    OperatorActionOutcome,
)
from ui.operator_actions import evaluate_locked_operator_action

from cockpit.command_writer import enqueue_governed_command
from cockpit.html_renderer import _runtime_mode_from_warmup_summary

router = APIRouter()

_PAIR_RE = re.compile(r"^[A-Z]{2,10}USDT?$")


@router.post("/command/suspend-pair", status_code=status.HTTP_303_SEE_OTHER)
def post_suspend_pair(
    pair: str = Form(...),
    reason: str = Form(""),
) -> RedirectResponse:
    if not _PAIR_RE.match(pair):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid pair format: {pair!r} (expected e.g. BTCUSDT)",
        )

    runtime_mode = _runtime_mode_from_warmup_summary()  # reads vps_warmup_run.summary.json
    request = OperatorActionRequest(
        action=OperatorActionType.SUSPEND_PAIR,
        runtime_mode=runtime_mode,
        # ... other required fields per OperatorActionRequest contract
    )
    outcome = evaluate_locked_operator_action(request, ...)
    if outcome != OperatorActionOutcome.ALLOWED:
        raise HTTPException(status_code=403, detail=str(outcome))

    enqueue_governed_command(
        kind=DashboardGovernedCommandKind.SUSPEND_PAIR,
        payload={"pair": pair, "reason": reason},
    )
    return RedirectResponse(url=f"/?ok=suspend_pair_{pair}", status_code=303)
```

Codex doit adapter aux signatures exactes de `OperatorActionRequest` (champs requis lus depuis `src/ui/contracts.py`).

---

**Fin du spec — version 1.0 — 2026-04-26**
