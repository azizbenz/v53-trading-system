# Session 2026-04-26 — Observability Stack Fix : Résumé complet

**Date :** 2026-04-26  
**Statut final :** ✅ BOOTSTRAP SUCCESS — stack Shadow VPS opérationnelle  
**GAP identifié :** orchestration incomplète (IA Lab + Build-17 manquants)

---

## 1. Problème initial rapporté

Grafana démarre mais affiche **rien** sur tous les panels.  
Prometheus affiche des métriques. Binance API / `.env` bloque.

---

## 2. Architecture stack locale V5.3

| Composant | URL | Détail |
|-----------|-----|--------|
| Bridge metrics | `http://127.0.0.1:19100/metrics` | Sert le `.prom` text file |
| Prometheus | `http://127.0.0.1:9090` | Scrape le bridge |
| Grafana | `http://127.0.0.1:3000` | Datasource uid=`prometheus` |

- Dashboard uid : `v53-shadow-vps-local`, 30 panels, 56 métriques `v53_shadow_vps_*`
- Source `.prom` : `build/build11_live_websocket_campaign/service/shadow_vps_service_observability.prom`
- Grafana data dir réel : `E:\claude\grafana.db` (instance depuis `E:\claude`)
- Output dir stack : `D:\temp v5.3\local_observability_stack\`

---

## 3. Les 4 bugs — diagnostic & fixes

### Bug 1 — `.env` manquant

`E:\claude  v5.3\v53_trading_system\.env` absent.  
Script lève `ValueError` ligne 215 de `run_v53_local_solution.py` avant même de lancer la stack.

**Fix :** utiliser le flag `-PublicOnly` au lancement :
```powershell
.\scripts\Run-V53LocalSolution.ps1 -PublicOnly
```

---

### Bug 2 — `overwrite: true` manquant dans bootstrap ✅ FIXÉ

`src/monitoring/local_grafana_api.py:121` — le POST `/api/dashboards/db` n'incluait pas `"overwrite": True`.  
Sur re-import (même UID), Grafana répond 412 Precondition Failed → `HTTPError` non catchée → bootstrap crash → `local_grafana_bootstrap.summary.json` jamais écrit.

```python
# Avant (bugué)
dashboard_status_code, _ = _request_json("POST", f"{grafana_url.rstrip('/')}/api/dashboards/db", dashboard_payload, headers)

# Après (fixé)
import_payload = {**dashboard_payload, "overwrite": True, "folderId": 0}
dashboard_status_code, _ = _request_json("POST", f"{grafana_url.rstrip('/')}/api/dashboards/db", import_payload, headers)
```

---

### Bug 3 — Datasource Prometheus non provisionnée

Conséquence directe de Bug 1+2 : datasource uid=`prometheus` jamais créée.  
La variable template `DS_PROMETHEUS` des panels reste vide → "No data" sur tous les panels.

---

### Bug 4 — PermissionError [WinError 5] — ROOT CAUSE ✅ FIXÉ

Traceback révèle : `_ensure_grafana` → `_start_detached_process` → `subprocess.Popen` → `_winapi.CreateProcess` → `PermissionError`.

**Root cause :** defaults dans `Run-V53LocalSolution.ps1` pointaient sur **dossiers** au lieu de `.exe`.

```powershell
# Bugué
[string] $PrometheusExe = "C:\tools\prometheus\prometheus-3.9.1.windows-amd64"       # DOSSIER
[string] $GrafanaServerExe = "C:\tools\grafana\grafana-12.3.1\bin"                    # DOSSIER

# Fixé
[string] $PrometheusExe = "C:\tools\prometheus\prometheus-3.9.1.windows-amd64\prometheus.exe"
[string] $GrafanaServerExe = "C:\tools\grafana\grafana-12.3.1\bin\grafana-server.exe"
```

`_resolve_executable_path` ne vérifiait que `exists()`, pas `is_file()` → dossier passait → `CreateProcess(dossier)` → ACCESS DENIED.

**Fix complémentaire** dans `local_observability_stack.py` : nouvelle fonction `_coerce_to_executable_file` qui auto-trouve l'exe si on lui donne un dossier.

---

## 4. Tableau récapitulatif — 4 fixes permanents

| # | Fichier | Fix |
|---|---------|-----|
| 1 | `src/monitoring/local_grafana_api.py:121` | `{**dashboard_payload, "overwrite": True, "folderId": 0}` |
| 2 | `src/monitoring/local_observability_stack.py:177` | `CREATE_NEW_PROCESS_GROUP \| CREATE_NO_WINDOW` (remplace `DETACHED_PROCESS`) |
| 3 | `src/monitoring/local_observability_stack.py:103-115` | Nouvelle `_coerce_to_executable_file` + intégration dans `_resolve_executable_path` |
| 4 | `scripts/Run-V53LocalSolution.ps1:35,38` | Defaults exe avec `\prometheus.exe` et `\grafana-server.exe` |

---

## 5. Preuve de succès

`D:\temp v5.3\local_observability_stack\local_grafana_bootstrap.summary.json` :
```json
{
  "datasource_status_code": 200,
  "dashboard_status_code": 200,
  "datasource_uid": "prometheus",
  "dashboard_uid": "v53-shadow-vps-local"
}
```

---

## 6. GAP MAJEUR — orchestration incomplète

`Run-V53LocalSolution.ps1` ne couvre que **Shadow VPS** (1/4 de la stack complète attendue) :

```
✅ Shadow VPS service        (campagne build11)
✅ Shadow VPS dashboard      (uid: v53-shadow-vps-local, 30 panels, 56 metrics)
❌ IA Lab service            (pas dans l'orchestration)
❌ IA Lab dashboard          (local_lab_grafana_dashboard.py existe mais non bootstrapped)
❌ Build-17 supervision      (engines A/B/C/D — non lancé)
❌ Build-17 dashboard        (local_grafana_dashboard_build17.py existe mais non exposé dans monitoring/__init__.py)
```

### Modules dashboard existants

| Module | Cible | État |
|--------|-------|------|
| `src/monitoring/local_grafana_dashboard.py` | Shadow VPS | ✅ utilisé |
| `src/monitoring/local_lab_grafana_dashboard.py` | IA Lab | ❌ non bootstrapped |
| `src/monitoring/local_grafana_dashboard_build17.py` | Build-17 | ❌ non exposé dans `__init__.py` |

### Sources `.prom` disponibles

| Fichier | Statut |
|---------|--------|
| `build/build11_live_websocket_campaign/service/shadow_vps_service_observability.prom` | ✅ live |
| `build/dev_dual_role_demo/service/shadow_vps_service_observability.prom` | dev |
| `build/pytest-observability-io/local_lab_observability.prom` | ⚠️ sortie pytest uniquement |
| `build/shadow_vps_service/shadow_vps_service_observability.prom` | ✅ disponible |

---

## 7. Prochaine étape

Voir spec : `2026-04-26_orchestration_complete_lab_build17_dashboards_spec.md`

**Option B choisie** : nouveau sprint Opus → Codex pour étendre l'orchestration :
- Lab service live
- Build-17 supervision (engines A/B/C/D)
- Bootstrap des 3 dashboards
- Support authentifié Binance (`.env` configuré)
