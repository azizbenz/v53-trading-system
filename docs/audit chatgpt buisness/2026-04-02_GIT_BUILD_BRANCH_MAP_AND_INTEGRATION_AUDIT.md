# V5.3 — GIT BUILD BRANCH MAP AND INTEGRATION AUDIT
## Date : 2026-04-02
## Statut : ACTIF

---

# 0. Objet

Ce document fixe l'état réel des branches locales `checkpoint-build-*` afin de
répondre à une question simple :

- le travail par build existe-t-il vraiment dans Git ?
- est-il encore porté par des branches vivantes distinctes ?
- ou est-il déjà intégré dans `main` / la branche courante ?

---

# 1. Conclusion courte

Conclusion nette :

- oui, il existe bien un historique local `par build`
- non, ces branches ne portent plus de divergence active
- toutes les branches `checkpoint-build-*` relevées sont déjà **ancêtres de
  `main`** et aussi de la branche courante `codex/build-11-reaudit-20260402`
- le vrai travail non sécurisé aujourd'hui n'est pas dans ces anciennes
  branches, mais dans le **worktree sale actuel**

Autrement dit :

- les branches `checkpoint-*` sont devenues des **marqueurs historiques**
- le WIP le plus récent Shadow/VPS vit surtout dans les fichiers modifiés /
  non suivis du workspace actuel

---

# 2. Référentiel vérifié

Branche courante :

- `codex/build-11-reaudit-20260402`

Branches de référence :

- `main`
- `origin/main`

Constat d'intégration :

- chaque tip `checkpoint-build-*` inspecté est `inMain=yes`
- chaque tip `checkpoint-build-*` inspecté est `inHead=yes`

Donc :

- aucune de ces branches ne contient aujourd'hui un commit unique absent de
  `main`

---

# 3. Carte par build

## 3.0 Build-1

Constat :

- aucune branche locale dédiée `checkpoint-build-1*` n'a été trouvée
- aucun tag Build-1 dédié n'a été trouvé non plus
- le point d'ancrage Git le plus ancien visible pour Build-1 est surtout :
  - `8e01173` -> `V5.3 Trading System — initial commit (Build-1 through Build-4)`

Lecture :

- Build-1 n'a pas été checkpointé localement comme les builds suivants
- sa réalité Git est portée :
  - par le commit initial
  - par les commits intégrés ultérieurs
  - par les audits et tests récents autour de `manifest_registry`,
    `dag_validator` et `smoke_bootstrap_recovery`

Conclusion :

- pour Build-1, il faut raisonner en `état architectural courant du dépôt`,
  pas en `branche build historique dédiée`

## 3.1 Build-2

Branches trouvées :

- `codex/checkpoint-build-2-start-20260401-020628` -> `5ad16ad`
  - sujet : `docs(specs): align build14 limited influence truth`
  - intégré dans `main` : `yes`
  - intégré dans `HEAD` : `yes`
- `codex/checkpoint-build-2-green-20260401-022543` -> `77eec4c`
  - sujet : `build-8: enforce anti-churn and allocation viability`
  - intégré dans `main` : `yes`
  - intégré dans `HEAD` : `yes`

Lecture :

- le nom `build-2-green` est trompeur, car son tip pointe sur un commit Build-8
- cette branche n'est plus un instantané propre du seul Build-2

## 3.2 Build-3

Branches trouvées :

- `codex/checkpoint-build-3-start-20260401-023151` -> `8f44267`
  - sujet : `build-2: align data backbone runtime and guards`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-3-green-20260401-024201` -> `ea2a1f9`
  - sujet : `build-3: harden execution backbone invariants`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-3-restart-green-20260401-093206` -> `1bf6e0f`
  - sujet : `build-3: add real execution runtime path`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-3-restart-start-20260401-090410` -> `e28de12`
  - sujet : `feat: publish audited builds and local-vps-shadow chain`
  - `main=yes`, `HEAD=yes`

Lecture :

- il y a bien eu au moins deux passes Build-3
- tout est maintenant absorbé dans `main`

## 3.3 Build-4

Branches trouvées :

- `codex/checkpoint-build-4-start-20260401-024327` -> `ea2a1f9`
  - sujet : `build-3: harden execution backbone invariants`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-4-green-20260401-024853` -> `3887ec1`
  - sujet : `build-4: add minimal drawdown risk guard`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-4-restart-start-20260401-093313` -> `1bf6e0f`
  - sujet : `build-3: add real execution runtime path`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-4-restart-green-20260401-094107` -> `d9e00c0`
  - sujet : `build-4: add real risk runtime path`
  - `main=yes`, `HEAD=yes`

## 3.4 Build-5

Branches trouvées :

- `codex/checkpoint-build-5-start-20260401-025023` -> `3887ec1`
  - sujet : `build-4: add minimal drawdown risk guard`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-5-green-20260401-031200` -> `17aee89`
  - sujet : `build-5: enforce penalty registry in scoring pipeline`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-5-restart-start-20260401-094107` -> `d9e00c0`
  - sujet : `build-4: add real risk runtime path`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-5-restart-green-20260401-094733` -> `e8ac30b`
  - sujet : `build-5: add real scoring runtime path`
  - `main=yes`, `HEAD=yes`

## 3.5 Build-6

Branches trouvées :

- `codex/checkpoint-build-6-start-20260401-031858` -> `17aee89`
  - sujet : `build-5: enforce penalty registry in scoring pipeline`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-6-green-20260401-032130` -> `273e9cc`
  - sujet : `build-6: wire engine a runtime path into scoring gates`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-6-start-20260401-101451` -> `e8ac30b`
  - sujet : `build-5: add real scoring runtime path`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-6-green-20260401-102528` -> `4014d94`
  - sujet : `build-6: add real engine-a runtime path`
  - `main=yes`, `HEAD=yes`

## 3.6 Build-7

Branches trouvées :

- `codex/checkpoint-build-7-start-20260401-032612` -> `273e9cc`
  - sujet : `build-6: wire engine a runtime path into scoring gates`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-7-green-20260401-033020` -> `95aa37c`
  - sujet : `build-7: wire engine b context and breakout guards`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-7-start-20260401-103200` -> `4014d94`
  - sujet : `build-6: add real engine-a runtime path`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-7-green-20260401-103710` -> `3195192`
  - sujet : `build-7: add real engine-b runtime path`
  - `main=yes`, `HEAD=yes`

## 3.7 Build-8

Branches trouvées :

- `codex/checkpoint-build-8-start-20260401-033500` -> `95aa37c`
  - sujet : `build-7: wire engine b context and breakout guards`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-8-green-20260401-034116` -> `77eec4c`
  - sujet : `build-8: enforce anti-churn and allocation viability`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-8-start-20260401-103946` -> `3195192`
  - sujet : `build-7: add real engine-b runtime path`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-8-green-20260401-105622` -> `d5e12e1`
  - sujet : `build-8: harden portfolio runtime guards`
  - `main=yes`, `HEAD=yes`

## 3.8 Build-9

Branches trouvées :

- `codex/checkpoint-build-9-start-20260401-034620` -> `77eec4c`
  - sujet : `build-8: enforce anti-churn and allocation viability`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-9-green-20260401-034621` -> `77eec4c`
  - sujet : `build-8: enforce anti-churn and allocation viability`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-9-start-20260401-110200` -> `d5e12e1`
  - sujet : `build-8: harden portfolio runtime guards`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-9-green-20260401-111445` -> `c22c9ce`
  - sujet : `build-9: add real meta runtime path`
  - `main=yes`, `HEAD=yes`

Lecture :

- le checkpoint utile le plus propre pour Build-9 est surtout
  `codex/checkpoint-build-9-green-20260401-111445`

## 3.9 Build-10

Branches trouvées :

- `codex/checkpoint-build-10-start-20260401-035022` -> `77eec4c`
  - sujet : `build-8: enforce anti-churn and allocation viability`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-10-green-20260401-035023` -> `9278294`
  - sujet : `docs: require real complete runtime for builds 11-14`
  - `main=yes`, `HEAD=yes`

Lecture :

- ce checkpoint est plus documentaire que purement Build-10 code

## 3.10 Build-11

Branches trouvées :

- `codex/checkpoint-build-11-start-20260401-031049` -> `77eec4c`
  - sujet : `build-8: enforce anti-churn and allocation viability`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-11-green-20260401-031049` -> `e50767f`
  - sujet : `build-11: harden full-system shadow gate`
  - `main=yes`, `HEAD=yes`

Lecture :

- le travail Build-11 committé existe bien et est intégré
- le WIP Build-11 plus récent n'est pas dans cette branche checkpoint ; il vit
  surtout dans le worktree actuel

## 3.11 Build-12

Branches trouvées :

- `codex/checkpoint-build-12-start-20260401-032625` -> `e50767f`
  - sujet : `build-11: harden full-system shadow gate`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-12-green-20260401-032625` -> `275f729`
  - sujet : `build-12: filter micro-live activation by shadow verdicts`
  - `main=yes`, `HEAD=yes`

## 3.12 Build-13

Branches trouvées :

- `codex/checkpoint-build-13-start-20260401-033302` -> `275f729`
  - sujet : `build-12: filter micro-live activation by shadow verdicts`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-13-green-20260401-034620` -> `7eba60c`
  - sujet : `build-13: enforce live-light temporal gates`
  - `main=yes`, `HEAD=yes`

## 3.13 Build-14

Branches trouvées :

- `codex/checkpoint-build-14-start-20260401-034658` -> `7eba60c`
  - sujet : `build-13: enforce live-light temporal gates`
  - `main=yes`, `HEAD=yes`
- `codex/checkpoint-build-14-partial-20260401-035903` -> `1316d56`
  - sujet : `build-14: align shadow activation contracts and monitoring`
  - `main=yes`, `HEAD=yes`

Lecture :

- Build-14 n'a pas de checkpoint `green`
- le meilleur marqueur historique trouvé est `partial`
- là aussi, le travail plus récent Build-14 / Shadow VPS est surtout hors de
  ces checkpoints, dans le workspace actuel

---

# 4. Ce que cela veut dire réellement

## 4.1 Ce qui est sécurisé dans Git

Le travail committé par build existe bien.

Il est visible à travers les sujets de commit suivants :

- Build-3 : `build-3: add real execution runtime path`
- Build-4 : `build-4: add real risk runtime path`
- Build-5 : `build-5: add real scoring runtime path`
- Build-6 : `build-6: add real engine-a runtime path`
- Build-7 : `build-7: add real engine-b runtime path`
- Build-8 : `build-8: harden portfolio runtime guards`
- Build-9 : `build-9: add real meta runtime path`
- Build-11 : `build-11: harden full-system shadow gate`
- Build-12 : `build-12: filter micro-live activation by shadow verdicts`
- Build-13 : `build-13: enforce live-light temporal gates`
- Build-14 : `build-14: align shadow activation contracts and monitoring`

## 4.2 Ce qui n'est pas sécurisé par ces branches

Le travail le plus récent autour de :

- Shadow VPS service
- native live websocket
- ré-audit Build-11
- correction régression Build-11 / Build-13
- nouveaux MD d'audit

ne repose pas sur les anciennes branches `checkpoint-*`.

Il vit surtout dans :

- la branche courante `codex/build-11-reaudit-20260402`
- les commits locaux récents `1863d81` et `46329d2`
- le worktree sale actuel

## 4.3 Problème principal

Le vrai problème Git n'est pas la perte des branches build.

Le vrai problème est :

- des branches historiques encore visibles
- des noms parfois trompeurs
- un WIP récent important non encore consolidé proprement

---

# 5. Anomalies de nommage

Plusieurs branches `start` ou même `green` pointent vers des commits d'un autre
build.

Exemples :

- `build-2-green` pointe sur un commit `build-8`
- `build-10-start` pointe sur un commit `build-8`
- `build-11-start` pointe sur un commit `build-8`
- `build-14-start` pointe sur un commit `build-13`

Conclusion :

- ces branches ne doivent pas être relues comme une vérité “1 build = 1 branche
  propre”
- elles servent davantage de checkpoints opérationnels historiques

---

# 6. Verdict final

Verdict :

- oui, le travail par build a bien existé et il est encore visible localement
- oui, il a déjà été intégré dans `main`
- non, les branches `checkpoint-*` ne portent plus une divergence active
- oui, le risque actuel est ailleurs : dans le WIP plus récent non encore
  sécurisé proprement

---

# 7. Action recommandée

Ne pas utiliser les anciennes branches `checkpoint-*` comme base de reprise.

Base de reprise recommandée :

- branche actuelle `codex/build-11-reaudit-20260402`
- plus l'inventaire explicite du worktree actuel

Action Git prod-safe suivante :

1. figer un commit ou bundle de préservation du WIP Shadow/VPS actuel
2. seulement ensuite décider ce qui doit être poussé, nettoyé ou restructuré
