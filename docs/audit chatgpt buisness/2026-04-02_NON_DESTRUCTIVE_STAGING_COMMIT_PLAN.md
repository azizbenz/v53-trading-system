# V5.3 — PLAN DE STAGING / COMMIT NON DESTRUCTIF
## Date : 2026-04-02
## Statut : ACTIF

---

# 0. Objet

Ce document fixe un plan de staging / commit prod-safe pour le worktree actuel.

But :

- préserver le travail utile sans perdre de fichiers non trackés
- éviter un faux commit "green" alors qu'un écart d'alignement reste ouvert
- distinguer clairement :
  - commit de préservation
  - commit merge-ready
  - nettoyage parasite

Ce document n'exécute rien.
Il décrit ce qui est sûr, ce qui est risqué, et dans quel ordre agir.

---

# 1. Faits Git figés

Constats vérifiés :

- `main`, `origin/main` et `codex/build-11-reaudit-20260402` pointent sur le même commit `e28de12`
- il n'y a pas de divergence de branches active
- le vrai risque est le **worktree sale**
- le worktree mélange :
  - modifications trackées cohérentes
  - nouveaux fichiers Shadow/VPS utiles
  - documents de continuité
  - temporaires parasites

Conséquence :

- on ne change pas de branche avant d'avoir sécurisé le contenu utile
- on ne lance aucun nettoyage massif
- on ne fait pas croire qu'un commit code est "release-ready" tant que l'écart de régression n'est pas fermé

---

# 2. Verdict de sécurité

## 2.1 Ce qui est sûr immédiatement

Un **commit docs/mémoire** est sûr immédiatement.

Il n'a pas d'impact runtime et permet de figer :

- la hiérarchie canonique
- l'état Git réel
- la méthode anti-hallucination
- le présent plan de staging

## 2.2 Ce qui est préservable immédiatement mais pas merge-ready

Le lot code Shadow/VPS peut être **préservé** par commit sur branche de travail.

Mais il ne doit pas être présenté comme lot final aligné, car :

- les tests ciblés du lot sont verts
- mais `tests/test_regression_alignment.py` reste à `50 passed, 2 failed`
- cet écart porte sur la cohérence canonique Build-11 / Build-13, pas sur un simple détail cosmétique

## 2.3 Ce qui ne doit pas être fait maintenant

- supprimer les non-trackés en masse
- déplacer le travail sur une autre branche avant sécurisation
- faire un commit "ready" vers `main`
- mélanger docs de méthode, code WIP et nettoyage parasite dans un seul commit

---

# 3. Évidence tests figée

Sous-ensembles verts vérifiés :

- `rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_day_counter.py tests/test_protocols/test_contracts.py tests/test_protocols/test_promotion_gates.py -q`
  - résultat : `66 passed`
- `rtk pytest tests/test_protocols/test_shadow_report_builder.py tests/test_protocols/test_shadow_session_registry.py tests/test_protocols/test_shadow_daily_orchestrator.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_websocket_ingest.py tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - résultat : `15 passed`

Écart bloquant restant :

- `rtk pytest tests/test_regression_alignment.py -q`
  - résultat : `50 passed, 2 failed`
  - fail 1 : `TestShadow30jGate.test_gate_passes_with_30_days`
  - fail 2 : `TestLiveLightShadowPrerequisite.test_passes_when_shadow_30j_met`

Lecture critique :

- le code a durci la logique vers `30 jours + shadow_report_ready`
- les tests de régression historiques attendent encore un comportement plus minimal
- tant que cet écart n'est pas arbitré proprement, le lot code reste **préservable** mais pas **requalifié**

---

# 4. Cartographie des groupes de fichiers

## 4.1 Groupe A — Docs / mémoire sûrs à committer

Fichiers :

- `docs/audit chatgpt buisness/2026-04-02_PROD_SAFE_CODE_VS_DOC_WORKPLAN.md`
- `docs/audit chatgpt buisness/2026-04-02_PROD_SAFE_CODE_VS_DOC_MEMORY.json`
- `docs/audit chatgpt buisness/2026-04-02_GIT_BRANCH_AND_WORKTREE_AUDIT.md`
- `docs/audit chatgpt buisness/2026-04-02_NON_DESTRUCTIVE_STAGING_COMMIT_PLAN.md`

Statut :

- committable immédiatement
- zéro impact runtime
- recommandé avant toute autre opération

## 4.2 Groupe B — Lot code Shadow/VPS cohérent mais non merge-ready

Fichiers trackés :

- `pyproject.toml`
- `scripts/run_local_replay_shadow.py`
- `src/protocols/__init__.py`
- `src/protocols/contracts.py`
- `src/protocols/shadow_day_counter.py`
- `tests/test_protocols/test_contracts.py`
- `tests/test_protocols/test_local_replay_shadow_runner.py`
- `tests/test_protocols/test_promotion_gates.py`
- `tests/test_protocols/test_shadow_day_counter.py`

Fichiers non trackés mais nécessaires au même lot :

- `scripts/run_shadow_daily_orchestrator.py`
- `scripts/run_shadow_vps_service.py`
- `src/protocols/shadow_daily_orchestrator.py`
- `src/protocols/shadow_live_websocket.py`
- `src/protocols/shadow_report_builder.py`
- `src/protocols/shadow_session_registry.py`
- `src/protocols/shadow_vps_service.py`
- `src/protocols/shadow_websocket_ingest.py`
- `tests/test_protocols/test_shadow_daily_orchestrator.py`
- `tests/test_protocols/test_shadow_daily_orchestrator_launcher.py`
- `tests/test_protocols/test_shadow_live_websocket.py`
- `tests/test_protocols/test_shadow_report_builder.py`
- `tests/test_protocols/test_shadow_session_registry.py`
- `tests/test_protocols/test_shadow_vps_service_launcher.py`
- `tests/test_protocols/test_shadow_websocket_ingest.py`

Pourquoi ce lot doit rester groupé :

- `src/protocols/__init__.py` exporte les nouveaux modules non trackés
- `scripts/run_local_replay_shadow.py` dépend de nouveaux objets maintenant fournis par `protocols`
- `pyproject.toml` ajoute `websocket-client`, requis pour la surface `live_websocket`

Statut :

- cohérent techniquement
- préservable par commit de branche
- non merge-ready tant que l'écart `regression_alignment` n'est pas traité

## 4.3 Groupe C — Docs de continuité à synchroniser avec le lot code

Fichiers :

- `docs/audit chatgpt buisness/2026-04-02_BUILD_WORKLOG_AND_STATUS.md`
- `docs/audit chatgpt buisness/2026-04-02_LOCAL_VPS_SHADOW_CHAIN_HANDOFF.md`
- `docs/audit chatgpt buisness/2026-04-02_CHATGPT_CONTINUITY_HANDOFF_5_DAYS.md`

Statut :

- utiles
- pas prioritaires avant la sécurisation du lot code
- à committer soit après le commit de préservation code, soit avec un commit docs séparé

## 4.4 Groupe D — Hors périmètre immédiat / provenance à clarifier

Fichiers :

- `CLAUDE_utf8.md`
- `docs/V5_3_STRATEGIES_TRADING_COMPLETE.md`
- `docs/audit tiers/`

Statut :

- ne pas stage par défaut
- provenance et rôle non verrouillés dans la reprise actuelle

## 4.5 Groupe E — Parasites à nettoyer plus tard

Fichiers :

- `docs/~$_3_STRATEGIES_TRADING_COMPLETE.md`
- `docs/~WRL0494.tmp`
- `docs/audit tiers/~$dit 5.3 gemini 29 mars.docx`

Statut :

- probablement supprimables plus tard
- ne pas traiter avant sécurisation des groupes A/B/C

---

# 5. Séquence recommandée

## Option recommandée — la plus prod-safe

### Étape 1

Committer **seulement** le groupe A.

Objectif :

- figer la méthode
- figer l'état Git
- préserver la mémoire d'audit

Message de commit suggéré :

- `docs(audit): freeze prod-safe audit and git recovery memory`

### Étape 2

Traiter l'écart `regression_alignment` avant tout commit code présenté comme stable.

Objectif :

- décider si le canon doit imposer explicitement `30j + shadow_report_ready`
- ou si les tests doivent rester plus permissifs

### Étape 3

Une fois l'arbitrage fait, committer le groupe B comme lot code intégral.

Message de commit suggéré :

- `feat(build11): preserve governed shadow vps and websocket runtime chain`

### Étape 4

Committer le groupe C si nécessaire en documentation d'accompagnement.

Message de commit suggéré :

- `docs(handoff): sync build11 shadow vps continuity notes`

## Option de préservation rapide

Si l'objectif immédiat est seulement de **ne pas perdre** le travail code :

- on peut faire un commit du groupe B sur la branche courante
- mais le commit doit être nommé comme **WIP de préservation**, pas comme clôture

Message de commit suggéré :

- `wip(build11): preserve shadow vps service bundle before alignment fix`

Règle :

- ce commit ne vaut pas validation canonique
- ce commit ne vaut pas readiness vers `main`

---

# 6. Commandes de staging suggérées

## 6.1 Groupe A seulement

```powershell
git add -- "docs/audit chatgpt buisness/2026-04-02_PROD_SAFE_CODE_VS_DOC_WORKPLAN.md" "docs/audit chatgpt buisness/2026-04-02_PROD_SAFE_CODE_VS_DOC_MEMORY.json" "docs/audit chatgpt buisness/2026-04-02_GIT_BRANCH_AND_WORKTREE_AUDIT.md" "docs/audit chatgpt buisness/2026-04-02_NON_DESTRUCTIVE_STAGING_COMMIT_PLAN.md"
```

## 6.2 Groupe B intégral

```powershell
git add -- pyproject.toml scripts/run_local_replay_shadow.py scripts/run_shadow_daily_orchestrator.py scripts/run_shadow_vps_service.py src/protocols/__init__.py src/protocols/contracts.py src/protocols/shadow_day_counter.py src/protocols/shadow_daily_orchestrator.py src/protocols/shadow_live_websocket.py src/protocols/shadow_report_builder.py src/protocols/shadow_session_registry.py src/protocols/shadow_vps_service.py src/protocols/shadow_websocket_ingest.py tests/test_protocols/test_contracts.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_promotion_gates.py tests/test_protocols/test_shadow_day_counter.py tests/test_protocols/test_shadow_daily_orchestrator.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_report_builder.py tests/test_protocols/test_shadow_session_registry.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_protocols/test_shadow_websocket_ingest.py
```

## 6.3 Groupe C séparé

```powershell
git add -- "docs/audit chatgpt buisness/2026-04-02_BUILD_WORKLOG_AND_STATUS.md" "docs/audit chatgpt buisness/2026-04-02_LOCAL_VPS_SHADOW_CHAIN_HANDOFF.md" "docs/audit chatgpt buisness/2026-04-02_CHATGPT_CONTINUITY_HANDOFF_5_DAYS.md"
```

---

# 7. Point critique à traiter avant merge-ready

Le point bloquant n'est pas Git.

Le point bloquant est :

- `src/protocols/shadow_runtime.py`
- `src/protocols/live_light_runtime.py`
- `tests/test_regression_alignment.py`

Écart observé :

- la gate réelle exige maintenant `30 jours + shadow_report_ready`
- au moins une partie des tests de régression attend encore `30 jours seuls`

Tant que cet écart n'est pas résolu proprement :

- pas de claim `Build-11 aligned`
- pas de commit code présenté comme final
- pas de merge vers `main`

---

# 8. Décision opérationnelle recommandée

Décision recommandée aujourd'hui :

1. committer immédiatement le groupe A
2. ne pas nettoyer les parasites avant sécurisation
3. ne committer le groupe B qu'en **WIP de préservation** ou après fix de l'écart de régression
4. traiter ensuite l'audit Build-1 -> Build-14 avec priorité sur Build-11 / Build-12 / Build-13 / Build-14

---

# 9. Résumé court

Oui, le travail utile peut être sécurisé sans risque.

Mais non, le lot code actuel ne doit pas encore être vendu comme "propre / final / aligné".

Le bon ordre est :

`commit docs mémoire -> arbitrage régression canonique -> commit code intégré -> docs de continuité -> nettoyage parasite`
