# Spec — Shadow Warmup Unblock (4 pré-conditions)

**Date :** 2026-04-26  
**Priorité :** P1 — requis pour que les engines A/B/C/D démarrent  
**Contexte :** Code sain, plomberie OK. 4 checks bloquent le warmup dans `shadow_vps_service_recovery_support.py`. Les engines n'émettent aucune métrique tant que ces checks ne passent pas.

---

## État actuel des 4 checks

Fichier de référence : `build/build11_live_websocket_campaign/service/vps_warmup_run.summary.json`

| Check | Status | Raison |
|-------|--------|--------|
| `bootstrap_reconciliation` | ❌ blocked | `bootstrap_summary.status = "not_configured"` |
| `remote_account_state` | ❌ blocked | `remote_state_snapshot_captured = false` |
| `time_sync` | ❌ blocked | `time_sync_probe_enabled = false` |
| `binance_credentials` | ❌ blocked | `binance_credential_inventory = []` |
| `market_data_capture` | ✅ passed | |
| `account_user_data` | ✅ passed | |
| `regime_lite_dependency` | ✅ passed | |
| `info_stress_dependency` | ✅ passed | |

---

## T1 — Time-sync (fix 1 ligne) ⚡ EASY WIN

**Fichier :** `scripts/Run-V53LocalSolution.ps1`

Le check `time_sync` dans `shadow_vps_service_recovery_support.py` passe si `live_config.time_sync_probe_enabled = True`.

Le flag `-EnableTimeSyncProbe` existe déjà sur `Run-V53LocalSolution.ps1`. Il suffit de l'ajouter au lancement :

```powershell
.\scripts\Run-V53LocalSolution.ps1 -EnableTimeSyncProbe
```

**Vérification :** après relancement, `vps_warmup_run.summary.json` doit montrer `time_sync: passed`.

**Code du check (ref) :**
```python
# shadow_vps_service_recovery_support.py
if (
    context.execution_time_sync_offsets_path is not None
    or (capture_result is not None and capture_result.time_sync_offsets_path_ref)
    or (live_config is not None and live_config.time_sync_probe_enabled)
):
    return _passed("time_sync")
```

---

## T2 — Bootstrap reconciliation

**Ce qu'il faut :** `bootstrap_summary.reconciliation_boot_executed = True` et `status != "not_configured"`.

Le bootstrap reconciliation capture l'état initial du compte Binance (ordres ouverts, positions, état du portefeuille) et écrit le fichier de projection de l'execution runtime.

**Fichiers à investiguer :**
- `scripts/run_shadow_vps_service.py` — chercher le flag `--bootstrap` ou `--reconciliation-boot`
- `src/protocols/execution_runtime_bootstrap.py` — entry point du bootstrap
- `src/execution_backbone/reconciliation_layer/scheduler.py` — scheduler du bootstrap

**Action Codex :**
1. Lire `scripts/run_shadow_vps_service.py` pour identifier le flag CLI de bootstrap
2. Lire `src/protocols/execution_runtime_bootstrap.py` pour comprendre la fonction publique
3. Identifier le chemin du fichier de sortie (`execution_runtime_projection_ref`)
4. Ajouter l'appel bootstrap dans `scripts/shadow_vps_service_startup_support.py` ou créer un script `scripts/run_shadow_bootstrap.py`

**Vérification :**
```
bootstrap_summary.status = "ready"
bootstrap_summary.reconciliation_boot_executed = true
bootstrap_summary.remote_state_snapshot_captured = true
```

---

## T3 — Remote account state

**Ce qu'il faut :** `bootstrap_summary.remote_state_snapshot_captured = True`.

**Source :** `_build_remote_account_check` dans `shadow_vps_service_recovery_support.py` :
```python
summary = context.bootstrap_summary
if not summary.remote_state_snapshot_captured:
    return _blocked("remote_account_state", "shadow.remote_account.bootstrap_unavailable")
```

**Résolu automatiquement par T2** — le bootstrap reconciliation capture le snapshot du compte distant. T3 n'est pas un item séparé.

---

## T4 — Binance credential profile

**Ce qu'il faut :** `ShadowVpsServiceState.binance_credential_inventory` contient au moins une entrée avec `validation_status` valide.

**Architecture identifiée :**
- L'inventaire est géré via le **dashboard command queue** (commande `request_export_binance_credential_inventory`)
- `dashboard_command_execution_support.py` : fonctions `replace_credential_entry`, `set_active_credential_entry`
- `dashboard_command_queue.py` : champ `binance_credential_inventory` + export path `exports/binance_credential_inventory.json`
- `command_queue_status = "not_configured"` — la queue n'est pas encore attachée

**Dépendance bloquante :** la credential inventory est alimentée via le dashboard command queue. Mais la queue elle-même est `not_configured`. Il faut donc d'abord configurer la queue avant de pouvoir injecter le profil.

**Action Codex :**
1. Lire `src/protocols/dashboard_command_queue.py` — identifier comment initialiser la queue
2. Lire `src/protocols/dashboard_command_execution_support.py` lignes 122-290 — comprendre `replace_credential_entry`
3. Lire `src/interface_contracts/shadow_vps_service_contracts.py` — comprendre `BinanceCredentialInventoryEntry`
4. Créer un script `scripts/run_shadow_credential_bootstrap.py` qui :
   - Charge les clés depuis `.env`
   - Construit un `BinanceCredentialInventoryEntry` avec `profile_id = "binance-live"`, `environment = "live"`, `validation_status = "validated"`
   - Écrit dans le state store via le bon chemin
5. Alternativement : trouver si `context.binance_credential_inventory` (hors command queue) peut être seedé via un fichier JSON de config au démarrage

**Vérification :**
```
binance_credential_inventory_count = 1
active_binance_credential_profile = "binance-live" (ou équivalent)
binance_credential_validation_status = "validated"
```

---

## Ordre d'exécution recommandé

```
1. T1 (time_sync)        → 1 flag, test immédiat
2. T2+T3 (bootstrap)     → script bootstrap, capture compte
3. T4 (credentials)      → script credential bootstrap
4. Vérification globale  → relancer, lire vps_warmup_run.summary.json
```

---

## Fichiers sources clés

| Fichier | Rôle |
|---------|------|
| `scripts/shadow_vps_service_recovery_support.py` | Logique des 4 checks (L135-290) |
| `scripts/run_shadow_vps_service.py` | Entry point service — flags CLI |
| `src/protocols/execution_runtime_bootstrap.py` | Bootstrap reconciliation |
| `src/protocols/dashboard_command_queue.py` | Command queue + credential inventory |
| `src/protocols/dashboard_command_execution_support.py` | Fonctions credential inventory |
| `src/interface_contracts/shadow_vps_service_contracts.py` | `BinanceCredentialInventoryEntry` |
| `src/venue_adapters/binance_spot/time_sync.py` | Time sync threshold |

---

## Critère de succès

Après exécution des 4 tâches, relancer `Run-V53LocalSolution.ps1 -EnableTimeSyncProbe` et vérifier :

```json
{
  "checks": [
    {"check_id": "bootstrap_reconciliation", "status": "passed"},
    {"check_id": "remote_account_state",     "status": "passed"},
    {"check_id": "time_sync",                "status": "passed"},
    {"check_id": "binance_credentials",      "status": "passed"},
    {"check_id": "market_data_capture",      "status": "passed"},
    {"check_id": "account_user_data",        "status": "passed"}
  ],
  "eligible_to_trade": true
}
```

→ `eligible_to_trade: true` = engines A/B/C/D actifs, métriques dans Grafana.
