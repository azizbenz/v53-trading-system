# Patch Plan — A2 fail-close gap (Bug confirmed)

**Date :** 2026-05-20
**Run audité :** `L:\output backtest\runs\strategy_ladder_workflow-f9bb2bdc0c8ce1fd`
**Diagnostic Codex :** VALIDÉ + complété par audit code
**Statut :** PLAN — code pas modifié, attente validation utilisateur

---

## 1. Symptôme observé

Sur le run `f9bb2bdc0c8ce1fd` :

**A2 (data_factory_manifest.json:31) :**
```json
"data_factory_status": "DATA_FACTORY_BLOCKED_BY_OHLCV_TEMPORAL_COMPLETENESS",
"blocker_codes": [
    "RAW_SOURCE_TYPE_INFERRED",
    "CURRENT_METADATA_PROXY",
    "OHLCV_1M_TEMPORAL_COMPLETENESS_BLOCKED",
    "OHLCV_10M_TEMPORAL_COMPLETENESS_BLOCKED",
    "SINGLE_PAIR_RESEARCH_ONLY",
    "BRONZE_GAPS_PRESENT",
    "BRONZE_SCHEMA_BLOCKER"
]
```

**Workflow_manifest.json :**
```json
"PHASE_A2": { "phase_status": "PHASE_A2_DATA_FACTORY_READY" }  // ← FAUX
"PHASE_B1": { "phase_status": "PHASE_B1_CANDIDATE_DISCOVERY_READY" }  // ← tourné quand même
"PHASE_B2": { "phase_status": "PHASE_B2_DETAILED_REPLAY_READY" }     // ← tourné quand même
```

**Conséquence :** B1 + B2 ont tourné sur une data factory **explicitement bloquée**. Bug doctrinal — viole fail-close V5.3.

---

## 2. Root cause — Bug au cœur du wrapper de phase

### Fichier : [`src/cockpit/action_support.py:2048-2066`](../src/cockpit/action_support.py:2048)

```python
def _phase_status_from_finished_record(record: CockpitBacktestJobRecord) -> str:
    if record.phase_id == PHASE_A2:
        if "SILVER_STORAGE_BLOAT_BLOCKER" in record.blockers:
            return PHASE_STATUS_STORAGE_BLOCKED
        if record.status.value in {"JOB_COMPLETED", "JOB_COMPLETED_WITH_BLOCKERS"}:
            return PHASE_STATUS_DATA_FACTORY_READY    # ← BUG ICI
        return PHASE_STATUS_DATA_FACTORY_BLOCKED
```

**Le bug exact :**
- Seul `SILVER_STORAGE_BLOAT_BLOCKER` est considéré comme "critique"
- TOUS les autres blockers (OHLCV temporal, BRONZE schema, etc.) sont **ignorés**
- `JOB_COMPLETED_WITH_BLOCKERS` est traité comme `JOB_COMPLETED` → **READY**
- Conséquence : A2 avec 6 blockers dont 2 critiques → marqué READY

### Bug secondaire #1 : [`src/cockpit/backtest_preflight.py:1714-1725`](../src/cockpit/backtest_preflight.py:1714)

```python
elif normalized_request.phase_id == PHASE_B1:
    inspection_status = (
        "PHASE_B1_CANDIDATE_DISCOVERY_READY"
        if launch_ready and not pair_blockers   # ← ne vérifie PAS A2 status
        else "PHASE_B1_CANDIDATE_DISCOVERY_BLOCKED"
    )
```

Le preflight B1 ne lit pas le `data_factory_manifest.json` de A2 — il vérifie seulement les pré-requis locaux du B1 lui-même.

### Bug secondaire #2 : idem pour B2 (preflight ligne 1720-1725)

---

## 3. Patch surgical en 3 layers (défense en profondeur)

### Patch A — Fix `_phase_status_from_finished_record` (action_support.py)

**Le PRINCIPAL.** Sans ce fix, les autres sont contournés.

Diff scope (~40 lignes) :

```python
# Nouvelle constante au top du fichier
_A2_CRITICAL_BLOCKERS = frozenset({
    "SILVER_STORAGE_BLOAT_BLOCKER",
    "OHLCV_1M_TEMPORAL_COMPLETENESS_BLOCKED",
    "OHLCV_5M_TEMPORAL_COMPLETENESS_BLOCKED",
    "OHLCV_10M_TEMPORAL_COMPLETENESS_BLOCKED",
    "OHLCV_15M_TEMPORAL_COMPLETENESS_BLOCKED",
    "BRONZE_SCHEMA_BLOCKER",
    "DATA_FACTORY_BLOCKED",
})

# Blockers research-acceptables (warn but ne bloquent pas)
_A2_RESEARCH_ACCEPTABLE_BLOCKERS = frozenset({
    "RAW_SOURCE_TYPE_INFERRED",
    "CURRENT_METADATA_PROXY",
    "SINGLE_PAIR_RESEARCH_ONLY",
    "BRONZE_GAPS_PRESENT",  # F2 severity classifier (Patch 2) gérera ça
})


def _is_a2_critical_blocked(blockers: tuple[str, ...]) -> bool:
    return any(b in _A2_CRITICAL_BLOCKERS for b in blockers)


def _phase_status_from_finished_record(record: CockpitBacktestJobRecord) -> str:
    if record.phase_id == PHASE_A2:
        if "SILVER_STORAGE_BLOAT_BLOCKER" in record.blockers:
            return PHASE_STATUS_STORAGE_BLOCKED
        # NEW: fail-close si blocker critique présent (PEU IMPORTE le JOB_COMPLETED_WITH_BLOCKERS)
        if _is_a2_critical_blocked(record.blockers):
            return PHASE_STATUS_DATA_FACTORY_BLOCKED
        # JOB_COMPLETED strict : pas de blocker → READY
        if record.status.value == "JOB_COMPLETED":
            return PHASE_STATUS_DATA_FACTORY_READY
        # JOB_COMPLETED_WITH_BLOCKERS : seulement READY si tous blockers research-acceptable
        if record.status.value == "JOB_COMPLETED_WITH_BLOCKERS":
            non_research = [
                b for b in record.blockers
                if b not in _A2_RESEARCH_ACCEPTABLE_BLOCKERS
            ]
            if non_research:
                return PHASE_STATUS_DATA_FACTORY_BLOCKED
            return PHASE_STATUS_DATA_FACTORY_READY
        return PHASE_STATUS_DATA_FACTORY_BLOCKED
    # ... reste inchangé
```

**Critère d'acceptation Patch A :**
- Sur le run f9bb2bdc, `phase_status` PHASE_A2 == `PHASE_A2_DATA_FACTORY_BLOCKED`
- Sur un run avec seulement `RAW_SOURCE_TYPE_INFERRED` + `CURRENT_METADATA_PROXY` : `phase_status` == `PHASE_A2_DATA_FACTORY_READY`
- Test régression : `tests/test_cockpit/test_phase_status_from_finished_record.py`

### Patch B — A2 readiness check in B1 launch path (backtest_preflight.py)

**Défense en profondeur.** Même si Patch A est buggé un jour, B1 doit refuser de tourner si A2 est BLOCKED.

Diff scope (~50 lignes) :

```python
def _read_a2_data_factory_status(workflow_run_root: Path) -> tuple[str, tuple[str, ...]]:
    """Returns (data_factory_status, blocker_codes) from A2 manifest."""
    manifest_path = workflow_run_root / "phase_a2_data_factory" / "data_factory_manifest.json"
    if not manifest_path.is_file():
        return "DATA_FACTORY_MANIFEST_NOT_FOUND", ()
    try:
        data = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        return "DATA_FACTORY_MANIFEST_UNREADABLE", ()
    status = str(data.get("data_factory_status", "UNKNOWN"))
    blockers = tuple(str(b) for b in (data.get("blocker_codes") or ()))
    return status, blockers


def _check_a2_upstream_for_b1_b2(workflow_run_root: Path) -> tuple[bool, str]:
    """Returns (can_proceed, reason_code)."""
    status, blockers = _read_a2_data_factory_status(workflow_run_root)
    if status == "DATA_FACTORY_MANIFEST_NOT_FOUND":
        return False, "A2_MANIFEST_MISSING_CANNOT_PROCEED"
    if status.startswith("DATA_FACTORY_BLOCKED_BY"):
        return False, f"A2_BLOCKED_UPSTREAM:{status}"
    if _is_a2_critical_blocked(blockers):
        return False, f"A2_CRITICAL_BLOCKER_UPSTREAM:{','.join(sorted(blockers))}"
    return True, ""


# Modifier la branche PHASE_B1 ligne 1714 :
elif normalized_request.phase_id == PHASE_B1:
    # NEW: check A2 upstream avant launch
    a2_ok, a2_reason = _check_a2_upstream_for_b1_b2(workflow_run_root)
    if not a2_ok:
        inspection_status = "PHASE_B1_CANDIDATE_DISCOVERY_BLOCKED"
        pair_blockers = (*pair_blockers, a2_reason)
    else:
        inspection_status = (
            "PHASE_B1_CANDIDATE_DISCOVERY_READY"
            if launch_ready and not pair_blockers
            else "PHASE_B1_CANDIDATE_DISCOVERY_BLOCKED"
        )
```

### Patch C — Idem pour B2 (backtest_preflight.py:1720)

Même logique que Patch B appliquée à la branche PHASE_B2.

---

## 4. Why 3 patches and not 1

**Patch A seul (action_support fix) suffit en théorie**, MAIS :
- Si quelqu'un appelle `_phase_status_from_finished_record` avec un record corrompu → workflow_manifest pourrait mentir
- Si B1 est lancé directement via CLI bypass du workflow → pas de check
- **Défense en profondeur** = check upstream à chaque entry point

**Patches B + C** garantissent que **même si workflow_manifest est buggé**, B1/B2 lisent **directement** le data_factory_manifest et refusent.

---

## 5. Effort

| Patch | Fichier | Lignes | Effort |
|---|---|---|---|
| A | `action_support.py:2048` | ~40 ajoutées | 0.3j |
| B | `backtest_preflight.py:1714` | ~50 ajoutées | 0.3j |
| C | `backtest_preflight.py:1720` | ~10 ajoutées (réutilise B) | 0.1j |
| Tests | `tests/test_cockpit/test_*.py` | ~100 lignes | 0.3j |
| **TOTAL** | | **~200 lignes** | **~1j** |

---

## 6. Doctrinal compliance

| Doctrine V5.3 | Comment ce patch la respecte |
|---|---|
| Fail-close non-bypassable | Patch A check critical blockers AVANT statut READY |
| Pas de magic numbers | Constantes `_A2_CRITICAL_BLOCKERS` + `_A2_RESEARCH_ACCEPTABLE_BLOCKERS` exhaustives + documentées |
| Audit-ready | Reason code explicite (`A2_BLOCKED_UPSTREAM:...`) dans le manifest workflow downstream |
| Surgical | Pas de refactor — juste check ajouté + taxonomie blocker → severity |
| Backward-compatible | Anciens runs (sans le check) restent lisibles ; nouveau runs respectent fail-close |

---

## 7. Distinction CRITIQUE vs RESEARCH-ACCEPTABLE

**Blockers CRITIQUES** (fail-close obligatoire) :
- `SILVER_STORAGE_BLOAT_BLOCKER` — storage broken
- `OHLCV_<tf>_TEMPORAL_COMPLETENESS_BLOCKED` — gaps OHLCV qui cassent feature timeline
- `BRONZE_SCHEMA_BLOCKER` — schéma raw mal parsé
- `DATA_FACTORY_BLOCKED` — generic critical

**Blockers RESEARCH-ACCEPTABLE** (warn mais OK pour research) :
- `RAW_SOURCE_TYPE_INFERRED` — venue inferred, pas un crash
- `CURRENT_METADATA_PROXY` — fees actuelles vs date, drift connu
- `SINGLE_PAIR_RESEARCH_ONLY` — restriction de scope
- `BRONZE_GAPS_PRESENT` — F2 severity classifier (Patch 2) gérera selon severity

**Cohérence avec recommendation Codex :**
> *« A2 avec blocage critique OHLCV temporal completeness / bronze gaps doit empêcher B1/B2 de partir en mode canonique »*

Ce patch implémente exactement ça avec la distinction critique/research.

---

## 8. Risque résiduel après patch

| Risque | Mitigation |
|---|---|
| Nouveau type de blocker ajouté plus tard et oublié dans la taxonomie | Test : un blocker `UNKNOWN_*` doit défaulter en CRITIQUE (fail-close safe) |
| BRONZE_GAPS_PRESENT sans severity → toujours research-acceptable | F2 (Patch 2) à appliquer en parallèle pour vrai check severity |
| Run avec workflow_manifest manuel hors orchestrateur | Patch B/C protège (lit manifest direct) |

---

## 9. NEXT — confirmation utilisateur

**Tu valides :**
1. Le diagnostic Codex + audit code (3 lieux du bug identifiés) ?
2. L'approche 3-patches (défense en profondeur) ?
3. La taxonomie CRITIQUE vs RESEARCH-ACCEPTABLE (4 blockers chacun) ?
4. Effort ~1j de code + tests ?

Si oui aux 4 → je code les Patches A + B + C séquentiellement et je relance le run pour valider que A2 BLOCKED bloque B1/B2.

## 10. Citations utilisateur

> *« auditer trouver les raison du pb dans le code puis intervention chirurgicale pour patch et avoir un datafactory prode safe »*

> *« le système dit correctement que la data est bloquée mais n'empêche pas encore les phases aval de tourner dessus. Si ta doctrine veut un vrai fail-close data, c'est encore un bug à fermer. »* (Codex)
