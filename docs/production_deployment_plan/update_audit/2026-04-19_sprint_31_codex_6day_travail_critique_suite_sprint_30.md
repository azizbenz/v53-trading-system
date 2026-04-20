# Sprint 31 — Codex 6-day coding plan — TRAVAIL CRITIQUE (suite Sprint 30)

> **Date** : 2026-04-19
> **Suite de** : `2026-04-19_sprint_30_codex_3day_mathgates_ratelimiter.md`
> **Auteur plan** : Opus (planification, 6 casquettes PhD)
> **Acteur code** : Codex
> **Durée** : 6 jours × 1 session 5h = **30 h de codage concentré**
> **Format workflow** : Opus plan md → Codex code → Opus audit checklist → user corrige ici
> **Gouvernance mandatée** : R-QUANT-FIRST (doc 28 §2bis), Carver/Narang/Taleb/Harvey-Liu-Zhu, Canon V5.3 (engines A/B/C/D canoniques, **une seule solution complète**, chaîne calibration progressive **backtest → shadow → micro-live → live**), no 1990s TA

---

## 0. Objectif une phrase

Fermer **tout** le chemin critique pré-MICRO_LIVE : compléter les deferrals du S30 (Hansen SPA full, shadow_gate_check full), fermer le reste des P1/P2 (testnet, signal handlers, god files split protocols/, VPS runbook Linux, log rotation, CI, duplication governed_extensions), en 6 sessions bornées de 5h.

---

## 1. Réponse 6 casquettes PhD

### 1.1 Pilote PhD (stratégie & priorisation)

**Constat après Sprint 30** : les 5 tests gates math sont codés, le seam risk_runtime est câblé, le rate limiter Binance existe, `shadow_gate_check.py` a un skeleton. Le premier gate Shadow G2.1 est techniquement produisable avec données réelles.

**Mais** : 5 blockers restants avant d'aller en **MICRO_LIVE** (tick réel avec capital €300-400) :

1. **Hansen SPA complet** (W-13) — nécessaire pour G2.2 (2e mois shadow, déflation Sharpe multi-stratégies)
2. **shadow_gate_check.py production-ready** (W-15) — rapport JSON signable par humain
3. **Testnet integration** (W-18) — preuve que l'adapter Binance soumet des ordres réels au testnet sans crash
4. **Signal handlers SIGTERM/SIGINT** (z ai audit P1) — sans ça, un `kill` VPS laisse des positions orphelines
5. **Split god files protocols/** — `shadow_runtime.py` 1722L, `live_light_runtime.py` 1481L, `micro_live_runtime.py` 1176L : illisibles, risque de bug caché critique

**Chemin critique Sprint 31** :
```
[Day 1 W-13 Hansen SPA]
       ↓
[Day 2 W-15 shadow_gate_check full]  ← G2.1 signable (pas juste produisable)
       ↓
[Day 3 W-18 testnet + signal handlers]  ← MICRO_LIVE safety-net
       ↓
[Day 4-5 split protocols/ god files]  ← code audit-ready
       ↓
[Day 6 VPS runbook + log rotation + CI + bugs z ai résiduels]
```

**Ce qu'on ne fait PAS dans S31** :
- W-16 partial fill handling → demande spec Opus d'abord (sera doc 31, séparé)
- W-19 **spec complète** VPS : on fait le **runbook exécutable** (scripts), pas la spec architecturale étendue
- Split des god files `scripts/*` (2030L, 2029L) — hors runtime trading, baseliner
- Split de `ui/technical_dashboard_*` (>1900L) — UI non critique, baseliner + fixer juste la duplication governed_extensions
- 39 `except Exception` → audit ciblé, pas rewrite massif (reporté S32)
- 27 `type: ignore` → revue ciblée (reporté S32)

### 1.2 Quant PhD (rigueur mathématique)

**W-13 Hansen SPA full** — seule tâche math du sprint.

**Formule complète** :
$$t^{\text{SPA}} = \max_{k=1,\ldots,M} \frac{\sqrt{n}\bar{d}_k}{\hat{\omega}_k}$$

avec :
- $\bar{d}_k = \frac{1}{n}\sum_{t=1}^n d_{k,t}$ la différence moyenne de loss entre stratégie $k$ et benchmark
- $\hat{\omega}_k^2$ variance stationary bootstrap de $\sqrt{n}\bar{d}_k$ (Politis-Romano — déjà dispo dans `bootstrap.py`)
- p-value via **stationary bootstrap** $B=1000$ replications, correction des trois versions Hansen (lower, consistent, upper)

**Référence** : Hansen, P. R. (2005). "A Test for Superior Predictive Ability." *Journal of Business & Economic Statistics*, 23(4), 365-380. DOI: `10.1198/073500105000000063`.

**Test paper_repro** :
- Dataset synthétique : 5 stratégies toutes pires que benchmark (tirage $N(-0.1, 1)$, n=250) → p-value SPA > 0.5 (on ne rejette pas H0 : benchmark optimal)
- 1 stratégie meilleure (+0.3 mean) + 4 pires → p-value SPA < 0.05 (rejet H0)
- Reproduire (approximativement) Hansen 2005 Table 2 : comparaison vs White Reality Check

**Validation W-21 bonus** — DSR multi-engine N=4 :
- Bailey-López de Prado 2014, *Journal of Portfolio Management* 40(5), 94-107. DOI: `10.3905/jpm.2014.40.5.094`
- Table 1 donne des valeurs pour N=1, N=10, N=100, N=1000
- On vérifie N=4 par interpolation + formule exacte (pas par valeur directe du paper)
- Input : SR_max=2.0, T=250, skew=-1, kurt=6, variance_SR_estimée
- Output attendu : DSR entre valeurs Bailey-LdP Table 1 pour N=1 (0.9866) et N=10 (~0.945) → interpolation N=4 ≈ 0.97 ± 0.01

**Interdits** :
- ❌ Pas de `scipy.stats.*` pour SPA (pas d'implémentation standard disponible)
- ❌ Pas de p-value asymptotique normale — impérativement **stationary bootstrap** (dépendance série)

### 1.3 Tradeur PhD (microstructure réaliste)

**W-18 Testnet Binance integration** — blocker MICRO_LIVE.

**Scope** :
- `tests/test_venue_adapters/test_integration_testnet.py` (nouveau fichier, marqué `@pytest.mark.testnet` — skip sans creds env var)
- **Auth** : test que `credential_loader.py` lit les creds testnet depuis `BINANCE_TESTNET_API_KEY` / `BINANCE_TESTNET_SECRET` (env vars, pas de fichier)
- **Order submit → cancel** : soumission limit buy very low price (pas de fill), puis cancel → assertion ordre cancelé
- **Balance query** : `GET /api/v3/account` → retourne un dict avec balances
- **Server time sync** : `GET /api/v3/time` → assertion écart < 5000ms
- **Rate limit observation** : après les 3 requêtes ci-dessus, `api_weight_tracker.get_state()` rapporte un used_weight > 0

**Creds** : documentation dans `docs/production_deployment_plan/update_audit/testnet_setup.md` (à créer dans D3).
- URL testnet : `https://testnet.binance.vision`
- Clés générées manuellement par user sur https://testnet.binance.vision/ — **pas d'automation**
- Env vars **PAS committés** (règle `.env` in `.gitignore`)

**Si pas de creds testnet dispo** : le test skip (pas de fail). CI doit passer même sans creds.

**Signal handlers SIGTERM/SIGINT (z ai audit P1)** :
- Ajouter dans `src/protocols/shadow_runtime.py`, `src/protocols/live_light_runtime.py`, `src/protocols/micro_live_runtime.py`
- Pattern :
  ```python
  import signal

  def _graceful_shutdown_handler(signum, frame):
      logger.warning("signal_received", signal=signum)
      runtime.request_shutdown()  # flag → boucle exit propre
      # NE PAS sys.exit() ici — laisser la boucle finir son tour
  ```
- Au `run()` du runtime : `signal.signal(signal.SIGTERM, handler)` + `signal.signal(signal.SIGINT, handler)`
- **Test** : envoyer SIGTERM via subprocess + vérifier arrêt propre + aucune position orpheline

**Partial fill (W-16)** : **hors scope**. Notes : à lire depuis `order_translator.py` status WebSocket, mais logique métier (réouverture partielle vs annulation) demande décision humaine D-19 → sera spec séparée.

### 1.4 Python Developer PhD (qualité code)

**Split god files protocols/** — règle stricte :

1. **Ne PAS changer** la logique métier (refactor pur mécanique)
2. **Préserver** les imports publics : `from protocols.shadow_runtime import ShadowRuntime` doit continuer de marcher (via `__init__.py` ré-export ou conservation du nom dans le fichier principal)
3. **Découper par axe fonctionnel** (pas arbitraire par "ligne 500") :
   - `shadow_runtime.py` (1722L) → `shadow_runtime.py` (main loop, <700L) + `shadow_runtime_calibration.py` (pull artefacts calibration) + `shadow_runtime_metrics.py` (métriques exposées) + `shadow_runtime_refusals.py` (logique RefusalJournal)
   - `live_light_runtime.py` (1481L) → `live_light_runtime.py` (<700L) + `live_light_runtime_state_machine.py` (transitions) + `live_light_runtime_guardrails.py` (circuit breakers)
   - `micro_live_runtime.py` (1176L) → `micro_live_runtime.py` (<700L) + `micro_live_runtime_sizing.py` (tier capital €300-400) + `micro_live_runtime_observability.py`

4. **Tests runtime existants passent sans modification** (pas de changement d'API publique)

5. **Chaque nouveau sibling** a :
   - `from __future__ import annotations`
   - Docstring module expliquant le split ("Extracted from `shadow_runtime.py` in Sprint 31 — <raison>")
   - Pas de cross-import circulaire (dagvalidator doit passer)

**Anti-pattern à éviter** :
- ❌ Créer `shadow_runtime_utils.py` — nom vague, interdit
- ❌ Mettre toutes les classes privées dans un seul sibling — casse le SRP
- ❌ Toucher `execution_backbone/execution_runtime.py` (1238L) ce sprint — reporté

**Shadow_gate_check.py full (W-15)** :
- CLI : `python -m scripts.shadow_gate_check --run-id <id> --window-days 30 --input <path> --output <json>`
- Structure JSON conforme doc 14 §12 (tous les champs renseignés, pas de `null` pour champs mandatoires)
- Appelle réellement : `psr`, `ks_test`, `energy_distance`, `mann_kendall`, `hansen_spa`, `dsr` via imports canoniques
- Génère aussi :
  - Section `refusal_analysis` (compte les RefusalJournal events du run)
  - Section `capital_usage` (tier cap respecté)
  - Section `execution_stats` (fill rate, slippage moyen, spread paid)
- 3 tests e2e :
  - Données synthétiques → JSON schema valid + toutes sections renseignées
  - Cas "échec PSR" → `gate_status: "fail"` + `reasons` listé
  - Cas "succès" → `gate_status: "pass"` + tous seuils respectés

### 1.5 Prod Safe (no-surprise, rollback, monitoring)

**W-19 VPS runbook Linux — focus exécutable, pas spec architecturale** :

Livrables concrets (pas des .md descriptifs) :
1. `scripts/vps/install_python.sh` — installe Python 3.13 sur Ubuntu 24.04 (idempotent, testé en chroot ou VM snapshot)
2. `scripts/vps/deploy_shadow_service.sh` — crée le service systemd `v53-shadow.service`, enable, démarre
3. `config/systemd/v53-shadow.service` — unit file (User, WorkingDirectory, ExecStart, Restart=on-failure, StandardOutput=journal)
4. `scripts/vps/rotate_logs.sh` — cron daily, archive + compress + delete >30j (THR-I03)
5. `scripts/vps/health_check.sh` — vérifie service up, dernier log <60s, disk >10GB, retourne exit code 0/1
6. `scripts/vps/rollback_calibration.sh` — prend un version_id en arg, rsync artefact + systemctl restart
7. `docs/production_deployment_plan/19_VPS_DEPLOYMENT_RUNBOOK.md` — UPDATE (pas création) : documente chaque script en 1 paragraphe + ordre d'exécution

**W-20 log rotation** — intégré dans `scripts/vps/rotate_logs.sh` + wire Python logging handler `RotatingFileHandler` si pas déjà en place (vérifier `src/logging_config.py` ou équivalent).

**W-23 CI minimal** :
- `Makefile` à la racine du repo :
  ```make
  .PHONY: test lint typecheck guards all

  test:
  	pytest -q

  lint:
  	ruff check src/ tests/ scripts/

  typecheck:
  	mypy src/

  guards:
  	python -m engineering_guardrails

  all: lint typecheck test guards
  ```
- `.github/workflows/ci.yml` (pas de prod en prem, mais smoke test local OK) :
  - Triggers : push main + PR
  - Steps : checkout → setup Python 3.13 → pip install → `make all`
  - Note : skip job si `[skip ci]` dans le commit message

**W-24 Startup readiness sequence spec** — pas un code, mais 1 section dans `docs/production_deployment_plan/07_PHASE_PLAN_0_TO_4.md` :
- Ordre de boot : `calibration_loader` → `regime_classifier` → `engines` → `gatekeeper` → `venue_adapter` → `execution_runtime`
- Chaque stage a un health check (retourne ready/not_ready)
- Boot fails fast si un stage n'est pas ready en 30s

**W-25 Rollback calibration** — intégré dans `rollback_calibration.sh` ci-dessus + 1 section doc 12 §6.3 (nouvelle).

**Fix z ai bugs résiduels** :
- Duplication `governed_extensions` dans `src/ui/technical_dashboard_view.py` → supprimer 1 des 2 cards (garder la section "System", supprimer celle de "Extensions" qui fait doublon)
- Test : charge la vue, vérifie que `governed_extensions` apparaît **exactement 1 fois** dans le DOM

**Coupure d'urgence** : si Day 4 split `shadow_runtime.py` casse un test runtime, **STOP split**, revert, retour Opus pour re-spec.

### 1.6 Génie Logiciel PhD (architecture)

**Principes split god files** :
- Pattern **composition over inheritance** : les siblings exposent des **fonctions pures** ou **dataclass services**, le fichier principal les compose
- **Pas de cycle** : `shadow_runtime_calibration.py` importe depuis `calibration_loader/`, mais `shadow_runtime.py` importe `shadow_runtime_calibration` (one-way)
- **Naming convention** : `<parent>_<aspect>.py` (pas de `<parent>_utils.py` ni `<parent>_helpers.py`)
- **`__init__.py`** : ré-exports publics inchangés (`from .shadow_runtime import ShadowRuntime` reste valide)

**Pattern split type** (pour `shadow_runtime.py`) :

```python
# src/protocols/shadow_runtime.py (< 700L après split)
from __future__ import annotations

from protocols.shadow_runtime_calibration import pull_shadow_calibration
from protocols.shadow_runtime_metrics import ShadowMetrics
from protocols.shadow_runtime_refusals import RefusalRecorder

class ShadowRuntime:
    def __init__(self, ...):
        self._calibration = pull_shadow_calibration(...)
        self._metrics = ShadowMetrics(...)
        self._refusals = RefusalRecorder(...)
        # main loop logic only
```

**CI gates ajoutés Sprint 31** :
- `dag_validator` : détecte cycle
- `engineering_guardrails` : tous les nouveaux fichiers < 700L (src/ only), new_violations=0
- `pytest tests/test_protocols/ -q` : **tous** les 444 tests doivent passer **sans modification** (refactor mécanique pur)

**DAG attendu après S31** :
```
src/protocols/
├── shadow_runtime.py                    [split, < 700L]
├── shadow_runtime_calibration.py        [NEW]
├── shadow_runtime_metrics.py            [NEW]
├── shadow_runtime_refusals.py           [NEW]
├── live_light_runtime.py                [split, < 700L]
├── live_light_runtime_state_machine.py  [NEW]
├── live_light_runtime_guardrails.py     [NEW]
├── micro_live_runtime.py                [split, < 700L]
├── micro_live_runtime_sizing.py         [NEW]
├── micro_live_runtime_observability.py  [NEW]
└── contracts.py                          [UNCHANGED — split reporté S32]

src/ui/
└── technical_dashboard_view.py          [governed_extensions dup fix, size NOT addressed]

calibration_methods/
└── hansen_spa.py                         [COMPLETED — was skeleton S30]

scripts/
├── shadow_gate_check.py                  [COMPLETED — was skeleton S30]
└── vps/
    ├── install_python.sh                 [NEW]
    ├── deploy_shadow_service.sh          [NEW]
    ├── rotate_logs.sh                    [NEW]
    ├── health_check.sh                   [NEW]
    └── rollback_calibration.sh           [NEW]

config/systemd/
└── v53-shadow.service                    [NEW]

tests/test_venue_adapters/
└── test_integration_testnet.py           [NEW, @pytest.mark.testnet]

.github/workflows/
└── ci.yml                                [NEW]

Makefile                                   [NEW]

docs/production_deployment_plan/
├── 07_PHASE_PLAN_0_TO_4.md               [UPDATED: startup readiness §X]
├── 12_LOCAL_LAB_VS_VPS_SEPARATION.md     [UPDATED: rollback §6.3]
└── 19_VPS_DEPLOYMENT_RUNBOOK.md          [UPDATED: documente scripts vps/]
```

---

## 2. Plan jour par jour

### DAY 1 (5h) — Hansen SPA full + DSR multi-engine validation

| Slot | Heure | Tâche | Livrable |
|---|---|---|---|
| D1-1 | 0:00-1:30 | **W-13 Hansen SPA** : implémentation complète (stationary bootstrap, 3 versions lower/consistent/upper, p-value) | `hansen_spa.py` (<300L, pas skeleton) |
| D1-2 | 1:30-2:30 | **W-13 Tests paper_repro** : Hansen 2005 Table 2 approche + 5 strats pires + 1 strat meilleure | `test_hansen_spa_paper_repro.py` (3 tests) |
| D1-3 | 2:30-3:30 | **W-21 DSR N=4** : test vs Bailey-LdP 2014 Table 1 interpolation | `test_dsr_multiengine.py` (2 tests : N=1 exact + N=4 interpolation) |
| D1-4 | 3:30-4:30 | **Integration** : `shadow_gate_check.py` appelle réellement `hansen_spa` (retire le TODO) | `shadow_gate_check.py` updated |
| D1-5 | 4:30-5:00 | **Audit local** : pytest + guardrails + dag_validator | proofs 3 lignes |

**Gate Day 1** : `pytest tests/test_calibration_methods/ -q` passe + `hansen_spa.py` >50L et <300L + dag_validator pass.

### DAY 2 (5h) — shadow_gate_check.py full + JSON schema

| Slot | Heure | Tâche | Livrable |
|---|---|---|---|
| D2-1 | 0:00-1:00 | **W-15 Sections rapport** : `refusal_analysis`, `capital_usage`, `execution_stats` implémentées (lecture depuis RefusalJournal + daily_pnl_breaker state + execution logs) | `shadow_gate_check.py` étoffé |
| D2-2 | 1:00-2:00 | **W-15 JSON schema** : créer `schemas/shadow_gate_report.schema.json` (JSON Schema Draft-7) conforme doc 14 §12 | `shadow_gate_report.schema.json` + helper `validate_report()` |
| D2-3 | 2:00-3:30 | **W-15 Tests e2e** : 3 tests (synthetic pass, synthetic fail PSR, synthetic fail hansen_spa) | `test_shadow_gate_check_e2e.py` |
| D2-4 | 3:30-4:30 | **W-15 CLI polish** : args parsing robuste, exit codes (0=pass, 1=fail, 2=error), help text | CLI améliorée + doctest dans docstring |
| D2-5 | 4:30-5:00 | **Audit local** : exécuter le CLI sur fixture réelle issue du dernier shadow run (si dispo) | JSON stdout attaché dans logs |

**Gate Day 2** : `python -m scripts.shadow_gate_check --run-id test --input fixtures/ --output /tmp/r.json` → exit 0, JSON valide schema.

### DAY 3 (5h) — Testnet integration + signal handlers + duplication fix

| Slot | Heure | Tâche | Livrable |
|---|---|---|---|
| D3-1 | 0:00-2:00 | **W-18 Testnet test** : `test_integration_testnet.py` avec auth + order submit/cancel + balance + server time + weight observation | test file + docstring setup creds testnet |
| D3-2 | 2:00-2:30 | **W-18 Doc setup** : `docs/production_deployment_plan/update_audit/testnet_setup.md` (créer compte, env vars, run test) | doc |
| D3-3 | 2:30-4:00 | **Signal handlers** : ajouter `_graceful_shutdown_handler` dans les 3 runtimes (shadow, live_light, micro_live) + `request_shutdown()` flag | 3 modifs + 3 tests subprocess |
| D3-4 | 4:00-4:30 | **Fix duplication `governed_extensions`** : supprimer 1 des 2 cards dans `technical_dashboard_view.py` (garder "System", supprimer "Extensions") | diff +0 -N (N=taille de la card supprimée) |
| D3-5 | 4:30-5:00 | **Audit local** : pytest + guardrails | proofs |

**Gate Day 3** : testnet test skip OK sans creds + 3 signal handler tests pass + governed_extensions apparaît 1 fois dans DOM.

### DAY 4 (5h) — Split `shadow_runtime.py` (1722L → 3 siblings)

| Slot | Heure | Tâche | Livrable |
|---|---|---|---|
| D4-1 | 0:00-0:30 | **Analyse** : cartographier les 1722L en 4 axes (main loop, calibration pull, metrics, refusals) | commentaires inline dans fichier original |
| D4-2 | 0:30-1:30 | **Extract `shadow_runtime_calibration.py`** : fonctions `pull_shadow_calibration`, `validate_artifact_fresh`, etc. | nouveau fichier (<400L) |
| D4-3 | 1:30-2:30 | **Extract `shadow_runtime_metrics.py`** : classe `ShadowMetrics`, compteurs, exposition Prometheus | nouveau fichier (<400L) |
| D4-4 | 2:30-3:30 | **Extract `shadow_runtime_refusals.py`** : `RefusalRecorder`, traductions refusal code → journal | nouveau fichier (<300L) |
| D4-5 | 3:30-4:30 | **Résiduel `shadow_runtime.py`** : main loop uniquement, imports depuis siblings | fichier <700L |
| D4-6 | 4:30-5:00 | **Audit** : `pytest tests/test_protocols/test_shadow_runtime*.py -q` + dag_validator + guardrails new_violations=0 | proofs |

**Gate Day 4** : `pytest tests/test_protocols/ -q` → **444 tests still passing** (aucune régression) + shadow_runtime.py < 700L + 0 cycle import.

### DAY 5 (5h) — Split `live_light_runtime.py` + `micro_live_runtime.py`

| Slot | Heure | Tâche | Livrable |
|---|---|---|---|
| D5-1 | 0:00-1:00 | **Split `live_light_runtime.py` (1481L)** : extract state machine + guardrails | 2 nouveaux siblings + principal <700L |
| D5-2 | 1:00-2:00 | Tests `live_light_runtime` passent | pytest green |
| D5-3 | 2:00-3:00 | **Split `micro_live_runtime.py` (1176L)** : extract sizing + observability | 2 nouveaux siblings + principal <700L |
| D5-4 | 3:00-4:00 | Tests `micro_live_runtime` passent | pytest green |
| D5-5 | 4:00-4:30 | **Baseline `scripts/run_*_dashboard.py` et `ui/technical_dashboard_*.py`** : ajout dans `engineering_guardrails_baseline.json` (pattern `FILE_TOO_LONG`, UI non-runtime) — documentés dans un comment `# reason: UI rendering code, not trading runtime` | baseline JSON updated |
| D5-6 | 4:30-5:00 | **Audit global protocols/** : confirmer aucun fichier `src/protocols/*.py` ne dépasse 700L | guardrails report |

**Gate Day 5** : 5 nouveaux siblings, tous les tests protocols/ verts (444/444), dag_validator pass, pas de nouveau FILE_TOO_LONG dans src/.

### DAY 6 (5h) — VPS scripts Linux + Makefile CI + docs update

| Slot | Heure | Tâche | Livrable |
|---|---|---|---|
| D6-1 | 0:00-1:00 | **W-19 `install_python.sh` + `deploy_shadow_service.sh`** (idempotent, shellcheck clean) | 2 scripts + 1 unit file |
| D6-2 | 1:00-1:30 | **W-19 `health_check.sh` + `rollback_calibration.sh`** | 2 scripts |
| D6-3 | 1:30-2:00 | **W-20 `rotate_logs.sh`** + wire `RotatingFileHandler` in `logging_config.py` | script + Python patch |
| D6-4 | 2:00-2:30 | **W-23 `Makefile`** (test/lint/typecheck/guards/all) | Makefile |
| D6-5 | 2:30-3:00 | **W-23 `.github/workflows/ci.yml`** | workflow YAML |
| D6-6 | 3:00-3:30 | **W-24 Doc startup readiness** section ajoutée dans `07_PHASE_PLAN_0_TO_4.md` | doc patch |
| D6-7 | 3:30-4:00 | **W-25 Doc rollback calibration** section §6.3 dans `12_LOCAL_LAB_VS_VPS_SEPARATION.md` | doc patch |
| D6-8 | 4:00-4:30 | **Doc `19_VPS_DEPLOYMENT_RUNBOOK.md`** : documente chaque script en 1 paragraphe | doc updated |
| D6-9 | 4:30-5:00 | **Audit global sprint** : `make all` → tous verts + `git diff --stat` scope check | proofs finaux sprint |

**Gate Day 6** : `make all` exit 0 + shellcheck clean sur scripts/vps/ + 5 scripts exécutables + CI workflow présent.

---

## 3. Acceptance critères par tâche

### W-13 Hansen SPA (complet)
- [ ] `hansen_spa.py` 150-300L, NotImplementedError supprimé
- [ ] Utilise `bootstrap.py` stationary bootstrap (pas re-implémenté)
- [ ] 3 tests paper_repro : null case (p>0.5), alternative case (p<0.05), hansen table 2 approximate
- [ ] Expose 3 variantes : `spa_lower`, `spa_consistent`, `spa_upper`
- [ ] Docstring inclut DOI `10.1198/073500105000000063`
- [ ] Appelé par `shadow_gate_check.py` (remplace TODO skeleton)

### W-21 DSR multi-engine
- [ ] Test N=1 exact vs formule papers
- [ ] Test N=4 interpolation entre valeurs Bailey-LdP Table 1 N=1 et N=10
- [ ] Tolérance documentée

### W-15 shadow_gate_check.py full
- [ ] 3 sections JSON : `refusal_analysis`, `capital_usage`, `execution_stats` réellement calculées
- [ ] `schemas/shadow_gate_report.schema.json` existe et valide
- [ ] 3 tests e2e (pass / fail PSR / fail Hansen SPA)
- [ ] CLI exit codes : 0 pass, 1 fail gate, 2 error
- [ ] `--help` texte complet

### W-18 Testnet integration
- [ ] `test_integration_testnet.py` avec `@pytest.mark.testnet`
- [ ] Skip propre si env vars absentes (pas de fail)
- [ ] 5 assertions : auth OK, order submit OK, cancel OK, balance ≥0, server time delta <5s
- [ ] Doc setup creds dans `update_audit/testnet_setup.md`

### Signal handlers
- [ ] 3 runtimes patches : shadow, live_light, micro_live
- [ ] `request_shutdown()` flag stoppe la boucle proprement (pas de sys.exit immédiat)
- [ ] 3 tests subprocess : spawn runtime → send SIGTERM → attend exit 0 en <10s
- [ ] Log INFO `signal_received` avant shutdown

### Fix `governed_extensions` duplication
- [ ] `grep 'governed_extensions' src/ui/technical_dashboard_view.py` = 1 occurrence de card (plusieurs refs data OK, 1 seule card DOM)
- [ ] Test DOM (si infra dispo) : render view → count = 1

### Split protocols/
- [ ] `shadow_runtime.py` < 700L
- [ ] `live_light_runtime.py` < 700L
- [ ] `micro_live_runtime.py` < 700L
- [ ] 7 nouveaux siblings (shadow_*3, live_light_*2, micro_live_*2)
- [ ] `from protocols.shadow_runtime import ShadowRuntime` continue de marcher
- [ ] Tous tests `tests/test_protocols/` passent sans modification (444/444)
- [ ] dag_validator : 0 cycle
- [ ] Chaque nouveau sibling a docstring module expliquant l'extraction

### VPS scripts
- [ ] `shellcheck scripts/vps/*.sh` exit 0
- [ ] Tous scripts idempotents (tournent 2× sans erreur)
- [ ] `v53-shadow.service` valide (`systemd-analyze verify`, simulable)
- [ ] Doc 19 mise à jour, pas recréée

### Makefile + CI
- [ ] `make test` / `make lint` / `make typecheck` / `make guards` / `make all` tous exit 0
- [ ] `.github/workflows/ci.yml` valide syntax YAML
- [ ] CI trigger : push main + PR + skip-ci marker

---

## 4. Tests and proof (slots à remplir par Codex par Day)

```
### Day 1 proof
- pytest tests/test_calibration_methods/ -q → [SLOT: X passed]
- cat src/calibration_methods/hansen_spa.py | wc -l → [SLOT: ?L]
- git diff --stat (in-scope) → [SLOT: ...]
- engineering_guardrails new_violations → [SLOT: 0]

### Day 2 proof
- pytest tests/test_scripts/test_shadow_gate_check*.py -q → [SLOT]
- python -m scripts.shadow_gate_check --run-id smoke --input fixtures/ --output /tmp/r.json; echo $? → [SLOT: 0]
- jsonschema -i /tmp/r.json schemas/shadow_gate_report.schema.json → [SLOT: valid]
- git diff --stat → [SLOT]
- guardrails → [SLOT: 0]

### Day 3 proof
- pytest tests/test_venue_adapters/ -q → [SLOT]
- pytest tests/test_protocols/ -k "signal or shutdown" -q → [SLOT]
- grep -c 'DashboardCard.*governed_extensions' src/ui/technical_dashboard_view.py → [SLOT: 1]
- guardrails → [SLOT: 0]

### Day 4 proof
- pytest tests/test_protocols/test_shadow_runtime*.py -q → [SLOT: N passed]
- wc -l src/protocols/shadow_runtime*.py → [SLOT all <700]
- python -m dag_validator → [SLOT: pass]
- guardrails → [SLOT: 0]

### Day 5 proof
- pytest tests/test_protocols/ -q → [SLOT: 444 passed]
- wc -l src/protocols/live_light_runtime*.py src/protocols/micro_live_runtime*.py → [SLOT all <700]
- python -m dag_validator → [SLOT: pass]
- guardrails → [SLOT: 0]

### Day 6 proof
- shellcheck scripts/vps/*.sh → [SLOT: 0]
- systemd-analyze verify config/systemd/v53-shadow.service → [SLOT: 0]
- make all → [SLOT: 0]
- git diff --stat (full sprint) → [SLOT]
- guardrails → [SLOT: 0]
```

---

## 5. Deferred / Not done (explicite Sprint 31)

Ne **PAS** faire dans ce sprint (sinon STOP + Dispute) :

- **W-16 partial fill** — besoin Opus spec préalable (doc 31 à créer séparé)
- Split `execution_backbone/execution_runtime.py` (1238L) — reporté S32
- Split `monitoring/contracts.py` (1299L) + `protocols/contracts.py` (1280L) — reporté S32 (contracts = haute criticité, split demande plus de temps)
- Split `scripts/run_technical_dashboard.py` (2030L) + `scripts/run_local_lab_analysis_bundle.py` (2029L) — baselined FILE_TOO_LONG (non-runtime)
- Split `ui/technical_dashboard_*.py` (>1900L) — baselined (UI)
- 39 `except Exception` → spécialisation reportée S32
- 27 `type: ignore` → revue reportée S32
- W-18 **production** credentials Binance — testnet only
- Toute modification `src/engines/` hors bug fixes signalés
- Création nouvel engine hors A/B/C/D ou nouveau stade runtime hors backtest/shadow/micro-live/live (canon V5.3 interdit — une seule solution complète)

---

## 6. Risks

| Risque | Prob | Impact | Mitigation |
|---|---|---|---|
| Hansen SPA p-value bootstrap O(B×M×n) trop lente (n=250, M=5, B=1000) | Medium | Low | 1.25M ops numpy vectorisé → <1s. Si lent, chunked bootstrap |
| Split `shadow_runtime.py` casse un test runtime | High | High | Refactor **mécanique pur** : copier-coller logique, changer juste imports. Exécuter pytest après chaque extract. STOP si rouge |
| Testnet Binance creds absents → CI fail | Low | Low | `@pytest.mark.testnet` skip propre, CI pass sans creds |
| Signal handler avec boucle `while True` bloquée sur `socket.recv` | Medium | Medium | Timeout sur WS + check `shutdown_requested` à chaque iteration |
| VPS scripts non testables en CI (pas de VM Ubuntu) | High | Low | `shellcheck` + manual validation dans runbook, test réel lors du déploiement |
| governed_extensions fix casse dashboard render | Low | Medium | Test DOM avant/après, vérifier 1 seule card reste cohérente (section "System" est le bon keeper d'après z ai audit) |
| Day 4-5 refactor volume (1722+1481+1176=4379L déplacés) | High | Medium | Strict 1 extract = 1 commit. Si Day 4 dépasse, couper à 2 siblings shadow (calibration + metrics), refusals en Day 5 |
| Doc updates oubliés (07, 12, 19) | Medium | Low | Day 6 dédie 1h30 aux docs, ordre explicite D6-6/7/8 |

---

## 7. Opus audit checklist (par Day)

### Checklist structure (Pilote + Génie Log)
- [ ] Chaque Day a son proof block rempli (pytest + diff + guardrails)
- [ ] Aucune modification hors scope (vérifier `git diff --stat`)
- [ ] Deferred items restent deferred
- [ ] dag_validator : 0 cycle (surtout Day 4-5)

### Checklist math (Quant — Day 1 seulement)
- [ ] Hansen SPA utilise **stationary bootstrap** (pas i.i.d.)
- [ ] DOI Hansen 2005 présent
- [ ] Test paper_repro reproduit une valeur nommée (pas juste "is positive")
- [ ] p-value calculée correctement (rang de t_obs dans distribution bootstrap)

### Checklist trader (Day 3 + 6)
- [ ] Testnet test skip propre sans creds (pas de fail)
- [ ] Signal handlers sur **tous** les runtimes trading (shadow + live_light + micro_live)
- [ ] VPS scripts idempotents (rerun safe)
- [ ] Rollback script prend un version_id en arg, pas hardcodé

### Checklist code (Python PhD — tous Days)
- [ ] Chaque nouveau fichier `from __future__ import annotations`
- [ ] Pas de print() nouveau dans src/
- [ ] ruff check clean
- [ ] mypy clean
- [ ] Chaque nouveau fichier <700L (src/)

### Checklist prod safe
- [ ] Signal handlers ne font pas sys.exit() immédiat
- [ ] Rotate logs ne supprime pas les logs du jour courant
- [ ] VPS service a Restart=on-failure
- [ ] Rollback a dry-run mode

### Checklist doc
- [ ] Doc 07 updated (startup readiness)
- [ ] Doc 12 updated (§6.3 rollback)
- [ ] Doc 19 updated (pas recréé)
- [ ] Doc update_audit/testnet_setup.md créé

---

## 8. Completion status (slot fin de Day 6)

```
Status: [SLOT: COMPLETE | PARTIAL | BLOCKED]
Items delivered:
  - W-13 Hansen SPA full: [x]
  - W-21 DSR multi-engine test: [x]
  - W-15 shadow_gate_check full: [x]
  - W-18 testnet integration: [x]
  - Signal handlers (3 runtimes): [x]
  - Fix governed_extensions duplication: [x]
  - Split shadow_runtime.py: [x]
  - Split live_light_runtime.py: [x]
  - Split micro_live_runtime.py: [x]
  - VPS scripts (5): [x]
  - Makefile + CI: [x]
  - Doc updates (07, 12, 19, testnet_setup): [x]

Items deferred per plan: W-16, split execution_runtime/contracts, splits UI/scripts (baselined), 39 except Exception, 27 type:ignore

pytest: [SLOT: X passed (Y new)]
new_violations: 0
```

---

## 9. Next safe step après S31

1. Opus audit final : GREENLIGHT ou REQUEST_FIX
2. Corrections user si REQUEST_FIX
3. Décision deployment : shadow VPS peut démarrer (gate G1) → run 1 mois → G2.1
4. **Sprint 32 plan** :
   - Spec W-16 partial fill (doc 31, Opus-led)
   - Split `execution_backbone/execution_runtime.py` + contracts (monitoring + protocols)
   - Specialize 39 except Exception
   - Review 27 type:ignore
   - MICRO_LIVE préparation (capital €300-400)

---

## 10. Governance crosscheck

| Règle | Respect |
|---|---|
| R-QUANT-FIRST | ✅ seul W-13 est math, a DOI + paper_repro (3 tests) |
| Canon V5.3 (A/B/C/D, solution unique) | ✅ aucun nouvel engine, aucun nouveau stade runtime (chaîne backtest → shadow → micro-live → live préservée) |
| No 1990s TA | ✅ pas de changement indicateurs |
| Capital reality | ✅ W-18 testnet seulement, micro_live_runtime_sizing.py respecte tier |
| File size 700 src/ | ✅ Day 4-5 dédiés au split |
| File size test (règle user 2026-04-19) | ✅ tests peuvent être baselined si >700 (jamais src/) |
| Workflow Opus→Codex→Opus | ✅ plan Opus, exec Codex, audit Opus par Day |
| COMPLETE proof | ✅ §4 chaque Day exige 3 lignes |
| Sessions 5h | ✅ chaque Day borné à 5h dans §2 |
| Suite logique Sprint 30 | ✅ ouvre par closure deferrals S30 (Day 1-2) |

---

**Fin du plan Sprint 31 — 6 jours Codex travail critique (suite Sprint 30).**
