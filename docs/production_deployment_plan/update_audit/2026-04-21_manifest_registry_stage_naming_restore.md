# Spec Opus→Codex — Manifest Registry : restauration canonique des noms de stage Build-12/13/17

**Date** : 2026-04-21
**Auteur Opus** : arbitrage doctrinal session 2026-04-21
**Verdict** : `TESTS_CANONICAL_RESTORE_REGISTRY` (arbitrage B — `project_v53_arbitration_2026_04_21_engine_b_smoke_and_manifest_naming.md`)
**Target Codex** : exécution mécanique, 1 slice, <15 min

---

## Objective

Restaurer la nomenclature canonique V5.3 des stages Build-12, Build-13, Build-17 dans `src/manifest_registry/build_order_registry.py`. Le registry a unilatéralement renommé les 3 stages hors d'un corpus doctrinal de 13+ sources primaires (docs 20, 21, 22, whitebook, master, spec Build-17 dédié, gates table, prompt pack, playbook, cartographie 2026-04-19, coding slices 09, ET les noms de fichiers code `live_light_runtime.py` / `LiveLightInput` / `LiveLightRunSummary`).

Corriger simultanément le drift **local du test** sur Build-12 : `"Micro-live Light"` n'a aucun ancrage doctrinal ; la doctrine dit toujours juste `"Micro-live"` sans suffixe.

**Distinction doctrinale fondamentale** (à retenir pour éviter confusion future) :
- La règle "no LIGHT profile" (CLAUDE.md 2026-04-14 + memory 2026-04-19) porte sur les **profils de déploiement** (artefacts LIGHT-profile / COMPLETE-profile)
- Les noms de stage `Live-Light` / `Live-Complete` sont des **paliers de rampe capital** (T3+ / T4+) de la phase live — **catégorie orthogonale** aux profils
- Renommer les stages n'est **pas** requis par la règle anti-profil

---

## Docs Governants

Preuve doctrinale par citation directe (13+ sources primaires) :

| Rang | Référence | Ligne | Citation |
|---|---|---|---|
| 1 | `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md` | L11 | *"pipeline `Replay → Shadow → Micro-live → Live-Light`"* |
| 2 | `docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md` | L240-242 | *"Shadow → Micro-live → Live-Light (T3+)"* |
| 3 | `docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md` | L364 | *"Shadow → Micro-live → Live-Light (T4+)"* |
| 4 | `docs/production_deployment_plan/09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md` | L2156 | *"Micro-live and Live-Light now carry the runtime projection seam"* |
| 5 | `docs/production_deployment_plan/09_...md` | L2161 | *"`src/protocols/live_light_runtime.py` now propagates..."* |
| 6 | `docs/production_deployment_plan/09_...md` | L2443 | *"through `Shadow → Micro-live → Live-Light`"* |
| 7 | `docs/production_deployment_plan/update_audit/2026-04-19_carto_B_protocols.md` | L113 | *"`LiveLightInput`, `LiveLightDecision`, `LiveLightRunSummary`"* |
| 8 | `docs/production_deployment_plan/update_audit/2026-04-19_carto_B_protocols.md` | L324 | *"Gate Build-13 Live-Light"* |
| 9 | `docs/specs/V5_3_BUILD17_SPEC_UI_COMPLETE_LIVE_COMPLETE.md` | L2 | *"UI Complete + Live-Complete Protocol"* |
| 10 | `docs/specs/V5_3_MASTER_FINAL_UNIQUE.md` | L1492 | *"Build-17 — UI Complete + Live-Complete"* |
| 11 | `docs/specs/V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md` | L639 | *"Shadow \| Micro-live \| Live-Light \| Live-Complete"* |
| 12 | `docs/V5_3_STRATEGY_BUILD_INTEGRATION_PLAYBOOK.md` | L881 | *"Build-17 — UI Complete + Live-Complete"* |
| 13 | `docs/specs/V5_3_PROMPT_PACK_CLAUDE_CHATGPT_BUILD_BY_BUILD.md` | L1220 | *"Build-17 — UI Complete + Live-Complete"* |
| 14 | `docs/whitebook/V5_3_WHITE_BOOK_PART_1_DOCTRINE_ARCHITECTURE_AND_BUILD_STATE.md` | L394 | *"validation Live-Complete"* |
| 15 | `src/protocols/live_light_runtime.py` | fichier entier | implémentation runtime Build-13 existante |

**Terme `"Micro-live Light"`** : absent de TOUT le corpus doctrinal (confirmé par grep). Drift local du test uniquement.

---

## Current Code Seam

### Registry actuel : `src/manifest_registry/build_order_registry.py` L114-150

```python
BuildStage(
    stage=12,
    name="Micro-live Runtime",                                 # ← drift
    description="Validation Micro-live gouvernee sur le rail runtime actif complet, avec capital reel ultra-prudent; Build-13 Live reste ensuite gouverne et distinct",
    modules=("protocols",),
),
BuildStage(
    stage=13,
    name="Live Runtime",                                       # ← drift
    description="Premiere execution reelle minimale et gouvernee sur le rail runtime actif complet, sans ouvrir l'extension gouvernee",
    modules=("protocols",),
),
...
BuildStage(
    stage=17,
    name="Operator UI + Live Extension",                       # ← drift
    description="Extension finale: UI operateur et protocole live gouverne etendu",
    modules=("ui", "protocols"),
),
```

### Test actuel : `tests/test_manifest_registry/test_build_order.py`

```python
# L51-55
def test_build12_exists(self):
    """Build-12 Micro-live Light must exist per V5.3 plan."""         # ← drift local
    stage12 = get_build_stage(12)
    assert stage12 is not None
    assert stage12.name == "Micro-live Light"                         # ← drift local

# L69-73 — CORRECT
def test_build13_exists(self):
    """Build-13 Live-Light must exist per V5.3 plan."""
    stage13 = get_build_stage(13)
    assert stage13 is not None
    assert stage13.name == "Live-Light"

# L80-84 — CORRECT
def test_build17_exists(self):
    """Build-17 UI Complete + Live-Complete must exist per V5.3 plan."""
    stage17 = get_build_stage(17)
    assert stage17 is not None
    assert stage17.name == "UI Complete + Live-Complete"
```

---

## Placement

Deux fichiers strictement, aucun autre :
1. `src/manifest_registry/build_order_registry.py` — 3 lignes `name=...`
2. `tests/test_manifest_registry/test_build_order.py` — 2 lignes (assert + docstring) sur Build-12 uniquement

Aucune mutation de :
- `description` (elles restent doctrinalement neutres)
- `modules` (les modules et dépendances sont corrects)
- Autre fichier dans `src/`
- Autre fichier dans `tests/`
- `docs/` (corpus déjà canonique)

---

## Files Changed

| Fichier | Type | Lignes modifiées |
|---|---|---|
| `src/manifest_registry/build_order_registry.py` | modif | L116, L122, L146 (3 × `name=...`) |
| `tests/test_manifest_registry/test_build_order.py` | modif | L52 (docstring), L55 (assert) |

Diff attendu : `2 files changed, 5 insertions(+), 5 deletions(-)`.

---

## Claims Implemented

### C-1. Registry Build-12 : `"Micro-live Runtime"` → `"Micro-live"`

`src/manifest_registry/build_order_registry.py` L116 :
```python
# AVANT
name="Micro-live Runtime",
# APRÈS
name="Micro-live",
```

Justification : le corpus doctrinal (docs 20/21/22, doc 09, cartographie B_protocols, gates table) nomme le stage uniquement `"Micro-live"` sans suffixe. Aucune source doctrinale n'écrit ni "Micro-live Light" ni "Micro-live Runtime".

### C-2. Registry Build-13 : `"Live Runtime"` → `"Live-Light"`

`src/manifest_registry/build_order_registry.py` L122 :
```python
# AVANT
name="Live Runtime",
# APRÈS
name="Live-Light",
```

Justification : doctrine massive (doc 20 L11, doc 21 L240, doc 22 L364, doc 09 L2156/2161/2443, cartographie 2026-04-19 L113/324, gates table L639, whitebook, master, code `live_light_runtime.py`, types `LiveLightInput`/`LiveLightDecision`/`LiveLightRunSummary`). "Live Runtime" est une invention registry-only.

### C-3. Registry Build-17 : `"Operator UI + Live Extension"` → `"UI Complete + Live-Complete"`

`src/manifest_registry/build_order_registry.py` L146 :
```python
# AVANT
name="Operator UI + Live Extension",
# APRÈS
name="UI Complete + Live-Complete",
```

Justification : le **spec Build-17 dédié** (`docs/specs/V5_3_BUILD17_SPEC_UI_COMPLETE_LIVE_COMPLETE.md`) porte ce titre littéralement, ainsi que master final unique L1492, whitebook Part 1 L394, playbook L881, prompt pack L1220, gates table L639. "Live Extension" n'est dans aucun doc.

### C-4. Test Build-12 : corriger drift local `"Micro-live Light"` → `"Micro-live"`

`tests/test_manifest_registry/test_build_order.py` L52 + L55 :
```python
# AVANT
def test_build12_exists(self):
    """Build-12 Micro-live Light must exist per V5.3 plan."""
    stage12 = get_build_stage(12)
    assert stage12 is not None
    assert stage12.name == "Micro-live Light"
# APRÈS
def test_build12_exists(self):
    """Build-12 Micro-live must exist per V5.3 plan."""
    stage12 = get_build_stage(12)
    assert stage12 is not None
    assert stage12.name == "Micro-live"
```

Justification : "Micro-live Light" n'est pas doctrinal. Le test avait un drift local indépendant de la mutation registry.

### C-5. PAS DE TOUCHE aux `description`, `modules`, `stage`

Les trois champs `description` restent identiques (contenu informationnel correct). Les `modules` sont corrects (`("protocols",)` pour B12/B13, `("ui", "protocols")` pour B17). Les numéros de stage sont corrects.

---

## Tests and Proof (slots)

### T-1. Tests manifest registry ciblés

```bash
rtk python -m pytest tests/test_manifest_registry/test_build_order.py -xvs
```

Attendu : `ALL passed`. En particulier :
- `TestBuildOrderCoherent::test_build12_exists` ✅
- `TestBuildOrderCoherent::test_build13_exists` ✅
- `TestBuildOrderCoherent::test_build17_exists` ✅
- `test_all_stage_modules_exist_in_inventory`, `test_all_inventory_modules_have_stage`, `test_build_11_12_13_sequential` ✅

**Slot résultat Codex** : `___`

### T-2. Tests manifest registry complet (non-régression voisinage)

```bash
rtk python -m pytest tests/test_manifest_registry/ -xvs
```

Attendu : `ALL passed`. Vérifie que les helpers `get_build_stage`, `get_next_stage`, `get_prerequisite_modules`, `validate_build_order_coherent`, `validate_modules_have_stages` continuent de fonctionner (aucune logique touchée, uniquement des strings `name`).

**Slot résultat Codex** : `___`

### T-3. Grep anti-régression : absence totale des anciens noms registry

```bash
rtk grep -rn 'name="Micro-live Runtime"' src/ tests/
rtk grep -rn 'name="Live Runtime"' src/ tests/
rtk grep -rn 'name="Operator UI \+ Live Extension"' src/ tests/
rtk grep -rn '"Micro-live Light"' tests/
```

Attendu : 4 × `no matches found`. Aucun résidu.

**Slot résultat Codex** : `___`

### T-4. Grep preuve présence des noms canoniques

```bash
rtk grep -n 'name="Micro-live"' src/manifest_registry/build_order_registry.py
rtk grep -n 'name="Live-Light"' src/manifest_registry/build_order_registry.py
rtk grep -n 'name="UI Complete \+ Live-Complete"' src/manifest_registry/build_order_registry.py
```

Attendu : 3 × 1 match chacun, sur L116, L122, L146 respectivement.

**Slot résultat Codex** : `___`

### T-5. Engineering guardrails

```bash
rtk python -m engineering_guardrails --format=stat
```

Attendu : `new_violations=0`.

**Slot résultat Codex** : `___`

### T-6. DAG validator

```bash
rtk python -m dag_validator
```

Attendu : `PASS` (aucune mutation d'import).

**Slot résultat Codex** : `___`

### T-7. Git diff stat

```bash
rtk git diff --stat
```

Attendu :
```
 src/manifest_registry/build_order_registry.py    | 6 +++---
 tests/test_manifest_registry/test_build_order.py | 4 ++--
 2 files changed, 5 insertions(+), 5 deletions(-)
```
(Approximatif — peut varier de ±1 selon rendu). Ce qui compte : `2 files changed`, aucun autre.

**Slot résultat Codex** : `___`

---

## Deferred / Not Done

- **Note doctrinale de clarification stage≠profile** : rédaction d'une note courte `docs/production_deployment_plan/update_audit/2026-04-21_stage_naming_vs_profile_naming.md` actant la distinction paliers-live vs profils-de-déploiement — **à rédiger séparément par Opus** après ce pilot, pour éviter futures confusions.
- **Description harmonization** : les `description` actuelles en Build-12/13/17 contiennent "runtime actif complet" / "extension gouverne etendu" qui pourraient être alignées sur le vocabulaire whitebook plus tard. Hors scope ici.
- **Arbitrage A (smoke Engine B flow_coherence)** : spec séparée `2026-04-21_smoke_engine_b_flow_coherence_alignment.md`.
- **Splits pending** (P2 S32) : hors scope.
- **Test `_base_risk_evaluation` cassé** (P1 S32) : hors scope.

---

## Risks

1. **Risque très faible** : 3 strings + 1 docstring, aucune logique touchée, aucun import affecté.
2. **Risque de tests voisins** : tester `tests/test_manifest_registry/` complet couvre tout le module (T-2). Aucun test ne dépend des anciens noms — vérifié par grep T-3.
3. **Risque documentaire** : aucun — la doctrine dit déjà ces noms, le registry les rejoint.
4. **Risque UI / reporting** : si un dashboard affiche `stage.name` directement, il affichera désormais les noms canoniques. C'est le comportement attendu, pas une régression.
5. **Risque baseline guardrails** : aucune violation nouvelle (pas d'augmentation de LOC, uniquement mutation de strings).

---

## Completion Status (slot)

**Codex remplit** : `COMPLETE` / `PARTIAL` / `BLOCKED` avec justification.

**Slot** : `___`

---

## Next Safe Step (slot)

**Codex propose** : prochain pas sûr (ex: "ouvrir spec note doctrinale stage-vs-profile").

**Slot** : `___`

---

## Opus audit checklist

Après exécution Codex, Opus vérifie :

1. [ ] `git diff --stat` = exactement 2 fichiers touchés (`src/manifest_registry/build_order_registry.py`, `tests/test_manifest_registry/test_build_order.py`), ~5 insertions / ~5 deletions
2. [ ] `git diff src/manifest_registry/build_order_registry.py` montre uniquement 3 × `name=...` modifiés sur L116/L122/L146 (rien d'autre — pas de description, pas de modules, pas de stage)
3. [ ] `git diff tests/test_manifest_registry/test_build_order.py` montre uniquement 2 × modifications sur le docstring L52 et l'assert L55 de `test_build12_exists` (rien d'autre)
4. [ ] Aucune modification de `docs/`
5. [ ] Aucune modification de `src/protocols/`, `src/engines/`, `src/manifest_registry/module_inventory.py`, `src/manifest_registry/dependency_registry.py`
6. [ ] T-1 : tests `test_build_order.py` passent
7. [ ] T-2 : `tests/test_manifest_registry/` entier passe
8. [ ] T-3 : 4 grep négatifs (aucun résidu des anciens noms)
9. [ ] T-4 : 3 grep positifs (1 match chacun sur les nouveaux noms canoniques)
10. [ ] T-5 : `new_violations=0`
11. [ ] T-6 : DAG PASS

Verdict Opus attendu : `GREENLIGHT` si 11/11 ; `REQUEST_FIX` sinon avec feedback ligne-à-ligne.
