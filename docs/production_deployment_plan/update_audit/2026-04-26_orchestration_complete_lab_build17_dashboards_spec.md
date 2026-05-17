# Spec Codex — Bootstrap IA Lab Dashboard Grafana + fixes orchestration

**Date :** 2026-04-26  
**Priorité :** P0 — GAP observability  
**Sprint estimé :** ~3h Codex  
**Scope décidé :** 2 dashboards Grafana (Shadow VPS déjà OK, IA Lab à bootstrapper)  
**Hors scope :** Health/Technical → restent HTML operator UI Build-10

---

## Contexte

`Run-V53LocalSolution.ps1` orchestre Shadow VPS mais ignore IA Lab.  
`local_lab_grafana_dashboard.py` existe dans `src/monitoring/` mais n'est jamais appelé au démarrage.

### État actuel

```
✅ Shadow VPS dashboard     uid: v53-shadow-vps-local    30 panels    opérationnel
❌ IA Lab dashboard         uid: à vérifier              builder existant, jamais bootstrappé
```

---

## Travail demandé

### T1 — Vérifier l'API publique de `local_lab_grafana_dashboard.py`

Lire `src/monitoring/local_lab_grafana_dashboard.py` et identifier :
- La fonction publique qui retourne le payload Grafana (probablement `build_lab_dashboard_payload()` ou similaire)
- L'UID du dashboard
- La source `.prom` attendue

**Ne pas modifier ce fichier.**

---

### T2 — Ajouter `_ensure_lab_dashboard` dans `local_observability_stack.py`

Fichier : `src/monitoring/local_observability_stack.py`

Ajouter une fonction calquée sur le pattern `_ensure_shadow_vps_dashboard` :

```python
def _ensure_lab_dashboard(grafana_url: str, headers: dict) -> tuple[int, str]:
    from monitoring.local_lab_grafana_dashboard import <fonction_publique>
    payload = <fonction_publique>(<args_nécessaires>)
    import_payload = {**payload, "overwrite": True, "folderId": 0}
    status_code, _ = _request_json(
        "POST",
        f"{grafana_url.rstrip('/')}/api/dashboards/db",
        import_payload,
        headers,
    )
    return status_code, payload.get("dashboard", {}).get("uid", "unknown")
```

Appeler `_ensure_lab_dashboard` depuis `launch_local_observability_stack()` juste après le bootstrap Shadow VPS.

**Contrainte CAP 700L :** vérifier `wc -l src/monitoring/local_observability_stack.py` avant et après. Si >700L, extraire `_ensure_lab_dashboard` dans `src/monitoring/local_lab_bootstrap.py`.

---

### T3 — Étendre le résumé bootstrap JSON

Fichier : `src/monitoring/local_observability_stack.py`

Étendre `_write_bootstrap_summary()` pour inclure IA Lab :

```json
{
  "shadow_vps": {
    "datasource_status_code": 200,
    "dashboard_status_code": 200,
    "datasource_uid": "prometheus",
    "dashboard_uid": "v53-shadow-vps-local"
  },
  "lab": {
    "dashboard_status_code": 200,
    "dashboard_uid": "<uid_lab>"
  }
}
```

Fichier de sortie : même chemin `local_grafana_bootstrap.summary.json` (format étendu, rétrocompatible).

---

### T4 — `.env` absent → warning au lieu de crash

Fichier : `scripts/run_v53_local_solution.py`

Modifier le bloc `.env` (ligne ~215) :

```python
# Avant (bugué)
raise ValueError("Binance credentials not found...")

# Après
if not public_only:
    logger.warning(
        "Binance credentials not found in .env — running in public-only mode. "
        "Set BINANCE_API_KEY and BINANCE_API_SECRET in .env for authenticated mode."
    )
    public_only = True
```

Ne plus jamais lever `ValueError` pour absence de `.env`. L'user décide via `--public-only` ou en configurant le `.env`.

---

## Fichiers à modifier

| Fichier | Tâche |
|---------|-------|
| `src/monitoring/local_observability_stack.py` | T2 + T3 (+ éventuel extract si >700L) |
| `scripts/run_v53_local_solution.py` | T4 |

**Fichiers à NE PAS modifier :**
- `src/monitoring/local_lab_grafana_dashboard.py` (lire seulement)
- `src/monitoring/local_grafana_dashboard.py` (Shadow VPS, ne pas toucher)
- `scripts/Run-V53LocalSolution.ps1` (inchangé — scope suffisant)

---

## Contraintes

1. **CAP 700L** sur `local_observability_stack.py` — extraire si dépassé
2. **Pattern overwrite** : toujours `{**payload, "overwrite": True, "folderId": 0}`
3. **Rétrocompatibilité** : ancien `bootstrap.summary.json` à une seule clé ne doit pas casser les scripts qui le lisent (utiliser `.get("shadow_vps", {})` dans les consommateurs si nécessaire)
4. **0 régression tests existants**

---

## Tests à écrire

- `test_ensure_lab_dashboard_bootstrap_success` — mock Grafana POST 200, vérifier uid retourné
- `test_bootstrap_summary_extended_two_sections` — JSON contient `shadow_vps` + `lab`
- `test_env_absent_warning_not_valueerror` — `.env` absent → `logger.warning`, pas `SystemExit`/`ValueError`

---

## Critère de succès (checklist Opus)

- [ ] `python scripts/run_v53_local_solution.py --public-only` → `bootstrap.summary.json` avec sections `shadow_vps` + `lab`
- [ ] Grafana `http://127.0.0.1:3000` → **2 dashboards visibles** : Shadow VPS + IA Lab
- [ ] `.env` absent → warning dans les logs, pas crash
- [ ] `local_observability_stack.py` ≤ 700 LOC (ou découpé)
- [ ] Tous les tests existants passent (0 régressions)
- [ ] `pytest tests/test_monitoring/ -x` → vert

---

## Commit message attendu

```
feat(monitoring): bootstrap IA Lab Grafana dashboard + .env warning downgrade

- add _ensure_lab_dashboard to launch_local_observability_stack
- extend bootstrap summary to shadow_vps + lab sections
- .env absent now logs warning instead of raising ValueError
```
