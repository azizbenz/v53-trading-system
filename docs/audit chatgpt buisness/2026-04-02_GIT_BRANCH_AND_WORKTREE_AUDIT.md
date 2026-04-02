# V5.3 — GIT BRANCH AND WORKTREE AUDIT
## Date : 2026-04-02
## Statut : PROD-SAFE SNAPSHOT

---

# 0. Executive Summary

Le problème principal n'est **pas** une divergence réelle entre `main` et la branche de travail.

Le problème réel est :

- un **nommage de branches trompeur**
- une **forêt de branches checkpoint historiques**
- un **worktree sale** contenant à la fois :
  - du vrai travail Build-11 / Shadow VPS
  - des documents utiles non suivis
  - quelques fichiers temporaires / parasites

Conclusion courte :

- `main` et `codex/build-11-reaudit-20260402` sont au **même commit**
- les branches `checkpoint-*` visibles sont des **repères historiques déjà mergés**
- le risque principal vient du **worktree**, pas du graphe Git

---

# 1. Vérité Git sur les branches

## 1.1 Branche active

- branche active : `codex/build-11-reaudit-20260402`
- HEAD : `e28de12`

## 1.2 État de `main`

- `main` : `e28de12`
- `origin/main` : `e28de12`

## 1.3 Vérification de divergence

Commande :

```powershell
git rev-list --left-right --count main...codex/build-11-reaudit-20260402
```

Résultat :

- `0 0`

Interprétation :

- aucune divergence dans un sens ni dans l'autre
- `main` et la branche courante pointent vers le même contenu commité

## 1.4 Branches non mergées dans `main`

Commande :

```powershell
git branch --no-merged main
```

Résultat :

- aucune branche locale non mergée

Interprétation :

- les branches locales visibles ne portent pas un historique secret non intégré à `main`

---

# 2. Pourquoi il y a malgré tout une impression de chaos

## 2.1 Les branches checkpoint restent visibles

Le dépôt contient beaucoup de branches du type :

- `codex/checkpoint-build-*`
- `codex/checkpoint-build-*-start-*`
- `codex/checkpoint-build-*-green-*`
- `codex/checkpoint-build-14-partial-*`

Ce ne sont pas des branches actives divergentes.
Ce sont des **jalons de travail historiques**.

## 2.2 La branche active porte un nom trompeur

`codex/build-11-reaudit-20260402` donne l'impression d'être une branche spéciale postérieure à `main`.

En réalité :

- elle pointe sur le même commit que `main`
- le vrai travail non consolidé est dans le **worktree local sale**

## 2.3 Le worktree sale masque la réalité

Quand on regarde seulement `git branch -vv`, on voit une forêt de noms.
Quand on regarde `git status`, on voit le vrai problème :

- modifications suivies non commitées
- fichiers Shadow/VPS non suivis
- docs utiles non suivis
- fichiers temporaires

---

# 3. État du worktree

## 3.1 Fichiers suivis modifiés

Modifiés et suivis :

- `docs/audit chatgpt buisness/2026-04-02_BUILD_WORKLOG_AND_STATUS.md`
- `docs/audit chatgpt buisness/2026-04-02_LOCAL_VPS_SHADOW_CHAIN_HANDOFF.md`
- `pyproject.toml`
- `scripts/run_local_replay_shadow.py`
- `src/protocols/__init__.py`
- `src/protocols/contracts.py`
- `src/protocols/shadow_day_counter.py`
- `tests/test_protocols/test_contracts.py`
- `tests/test_protocols/test_local_replay_shadow_runner.py`
- `tests/test_protocols/test_promotion_gates.py`
- `tests/test_protocols/test_shadow_day_counter.py`

Lecture :

- ce lot est cohérent
- il correspond à un **durcissement Build-11 / reporting / compteur Shadow / runner local replay**
- ce n'est pas un bruit aléatoire

## 3.2 Fichiers non suivis

Les non suivis se divisent en trois groupes.

---

# 4. Classification des fichiers non suivis

## 4.1 Groupe A — Travail utile à conserver

Ces fichiers sont explicitement cohérents avec le handoff du 2026-04-02 et avec le chantier Shadow VPS autonome :

- `docs/audit chatgpt buisness/2026-04-02_CHATGPT_CONTINUITY_HANDOFF_5_DAYS.md`
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

Justification :

- ils sont cités noir sur blanc dans le handoff de continuité
- ils correspondent exactement aux nouvelles capacités Shadow VPS / websocket / orchestration
- ils forment un lot code + scripts + tests cohérent

Verdict :

- **à préserver**
- **à intégrer proprement plus tard**
- **à ne surtout pas supprimer**

## 4.2 Groupe B — Documentation utile mais secondaire

Ces fichiers sont utiles à la continuité ou à la reprise, mais ne sont pas le canon :

- `docs/audit tiers/gemini_audit.txt`
- `docs/audit tiers/audit 5.3 gemini 29 mars.docx`
- `docs/audit tiers/audit qwwenn.docx`
- `CLAUDE_utf8.md`
- `docs/V5_3_STRATEGIES_TRADING_COMPLETE.md`
- `docs/audit chatgpt buisness/2026-04-02_PROD_SAFE_CODE_VS_DOC_WORKPLAN.md`
- `docs/audit chatgpt buisness/2026-04-02_PROD_SAFE_CODE_VS_DOC_MEMORY.json`

Lecture :

- les audits tiers sont des matériaux de contexte, pas des sources de vérité
- `CLAUDE_utf8.md` ressemble à un duplicat de confort / encodage
- `docs/V5_3_STRATEGIES_TRADING_COMPLETE.md` est un gros document stratégique lisible, mais il n'apparaît pas dans la hiérarchie canonique active déjà stabilisée
- les deux fichiers `PROD_SAFE_*` sont des mémoires de pilotage créées pendant cette reprise

Verdict :

- **à conserver pour l'instant**
- **à classer avant tout commit**
- **à ne pas traiter comme canon**

## 4.3 Groupe C — Parasites ou temporaires

Ces fichiers ressemblent à des temporaires Office / Word :

- `docs/~$_3_STRATEGIES_TRADING_COMPLETE.md`
- `docs/~WRL0494.tmp`
- `docs/audit tiers/~$dit 5.3 gemini 29 mars.docx`

Indices :

- taille minuscule pour les lock files `~$*`
- suffixe `.tmp`
- nommage typique de fichiers temporaires bureautiques

Verdict :

- **parasites**
- **ne font pas partie du travail métier**
- supprimables plus tard, mais seulement dans une passe de nettoyage volontaire

---

# 5. Ce que le handoff confirme

Le handoff [2026-04-02_CHATGPT_CONTINUITY_HANDOFF_5_DAYS.md](./2026-04-02_CHATGPT_CONTINUITY_HANDOFF_5_DAYS.md) confirme explicitement comme "vrai travail" :

- `run_shadow_vps_service.py`
- `shadow_vps_service.py`
- `shadow_daily_orchestrator.py`
- `shadow_session_registry.py`
- `shadow_report_builder.py`
- `shadow_websocket_ingest.py`
- `shadow_live_websocket.py`
- les tests associés

Donc :

- l'absence de suivi Git de ces fichiers n'est pas un signal de bruit
- c'est un **signal d'intégration incomplète du worktree**

---

# 6. Diagnostic final

## 6.1 Ce qui n'est PAS le problème

- pas de divergence `main` vs branche courante
- pas de branche locale non mergée cachée
- pas de fork Git structurel visible

## 6.2 Ce qui EST le problème

- trop de branches checkpoint encore visibles
- nom de branche active trompeur
- lot important de travail Shadow/VPS encore non tracké
- mélange de fichiers utiles et parasites dans le worktree

---

# 7. Recommandation prod-safe

## 7.1 Ne pas faire tout de suite

- ne pas changer de branche à l'aveugle
- ne pas faire de `reset --hard`
- ne pas supprimer en bloc les non suivis
- ne pas prétendre "nettoyer" avant classification

## 7.2 Faire maintenant

1. considérer `main` et la branche courante comme **équivalentes côté commit**
2. traiter le sujet comme un **problème de worktree à intégrer**, pas comme un problème de merge
3. figer les groupes :
   - `tracked_wip`
   - `untracked_useful_shadow_vps`
   - `untracked_useful_docs`
   - `untracked_parasites`
4. poursuivre l'audit / la correction sans bouger de branche tant que le lot utile n'est pas stabilisé

## 7.3 Plus tard, quand le lot sera stabilisé

Options propres :

- soit continuer sur la branche actuelle puis commit
- soit créer une nouvelle branche d'intégration claire depuis `e28de12`

Nom conseillé si on veut clarifier plus tard :

- `codex/shadow-vps-audit-integration-20260402`

Mais **pas maintenant** : aujourd'hui, le besoin prioritaire est de **ne pas perdre le vrai travail non tracké**.

---

# 8. Résumé opératoire

Verdict Git :

- `branches` : **pas cassées, mais mal lisibles**
- `main vs branche actuelle` : **même commit**
- `checkpoint-*` : **historiques déjà mergées**
- `worktree` : **sale mais majoritairement utile**

Conclusion pratique :

- le prochain risque n'est pas de "fusionner la mauvaise branche"
- le prochain risque est de **nettoyer ou déplacer le worktree sans distinguer le vrai Shadow VPS du bruit**

