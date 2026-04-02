# V5.3 — PLAN DE TRAVAIL PROD-SAFE
## Audit code vs corpus canonique, mémoire de pilotage, anti-hallucination
### Date : 2026-04-02
### Statut : ACTIF

---

# 0. Objet

Ce document fixe l'ordre de travail pour reprendre V5.3 sans dérive :

- auditer le code contre le corpus canonique actif
- éviter toute réécriture documentaire instinctive
- éviter toute conclusion optimiste non prouvée
- produire une mémoire de pilotage durable pour les prochaines passes

Ce document n'est pas un nouveau canon.
Il organise la reprise de manière critique et prod-safe.

---

# 1. Hiérarchie de vérité à respecter

En cas de conflit, l'ordre retenu est :

1. `docs/specs/V5_3_MASTER_FINAL_UNIQUE.md`
2. `docs/specs/V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`
3. les specs Build-1 à Build-17
4. `docs/specs/V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md`
5. les tables détaillées et addenda actifs, seulement si subordonnés au canon
6. les handoffs / audits / worklogs, utiles pour la continuité mais non canoniques

Conséquence :

- on ne "corrige" jamais le master unique à partir d'un handoff seul
- on ne "corrige" jamais le code à partir d'une archive ou d'un vieux brouillon
- on ne déclare jamais `ALIGNED` sans preuve doc + code + tests + chemin runtime cohérent

---

# 2. Position de départ honnête

État retenu aujourd'hui :

- Build-2 : `ALIGNED`
- Build-3 : `ALIGNED`
- Build-9X : `ALIGNED`
- Build-10 : `ALIGNED`
- Build-11 : `STILL PARTIAL`
- chaîne `LOCAL_REPLAY -> export -> import VPS -> SHADOW` : `OPERATIONAL`
- service Shadow VPS autonome : présent
- mode `live_websocket` natif : codé et testé
- preuve réseau exchange live : pas encore fermée dans cet environnement

Tension importante à garder en mémoire :

- les handoffs récents recentrent l'écart principal sur le smoke `live_websocket`
- mais le corpus stabilisé reste plus exigeant : Build-11 = Shadow 30 jours comme phase de vérité complète avec A/B/C/D + Build-14 `SHADOW_ENABLED`, verdict composant par composant, puis seulement Micro-live, puis Live

Conséquence :

- il ne faut pas réduire Build-11 à un simple smoke websocket
- il ne faut pas non plus réécrire tout le canon tant que l'audit code vs docs n'est pas figé

---

# 3. Règles anti-hallucination

## 3.1 Règles de fond

- toujours partir des documents canoniques actifs
- toujours relire le code réel avant de conclure
- toujours vérifier les tests réellement exécutés
- toujours distinguer `codé`, `testé`, `validé`, `promu`
- toujours nommer les écarts avec les statuts : `ALIGNED`, `STILL PARTIAL`, `NOT READY`

## 3.2 Règles d'écriture

- aucune correction documentaire globale en une seule passe
- aucun changement de doctrine implicite
- aucune normalisation silencieuse d'une durée de gate
- aucun langage flou du type "à peu près aligné"
- aucune promotion implicite par fatigue ou par optimisme

## 3.3 Règles de preuve

Chaque assertion critique doit pouvoir pointer vers :

- une référence doc
- une référence code
- une preuve test
- et, si le sujet l'exige, une preuve runtime

Si l'un de ces quatre piliers manque :

- le verdict reste `STILL PARTIAL` ou `NOT READY`

---

# 4. Décision importante sur les durées de gates

Le corpus actif dit actuellement :

- Shadow Light : **30 jours consécutifs minimum**
- Micro-live Light : **7 jours minimum**
- Live-Light : seulement après Shadow complet validé + verdict post-Shadow + Micro-live stable

Demande candidate à traiter avec prudence :

- durcir la doctrine vers `Shadow 30j -> Micro-live 15j -> Live`

Règle retenue pour cette reprise :

- **ne pas modifier automatiquement le canon de 7 jours vers 15 jours**
- traiter ce point comme une **décision de gouvernance explicite**, pas comme une "simple correction de markdown"

Pourquoi :

- cela change les merge gates
- cela change Build-12, Build-13, les tables GO/NO-GO, le master, le plan build, possiblement les protocoles et les tests
- une telle modification doit être voulue, tracée et propagée proprement

Donc :

- le plan de travail prépare ce changement comme `change request`
- mais ne le pousse pas dans le canon sans validation explicite

---

# 5. Stratégie de travail retenue

## Phase A — Freeze de lecture

Objectif :

- figer les sources
- figer la hiérarchie
- figer les règles de verdict

Sorties attendues :

- ce plan de travail
- un tracker JSON de mémoire

## Phase B — Audit canon -> code

Objectif :

- comparer les surfaces actives du code au corpus canonique

Ordre :

1. master unique + build plan + merge gates
2. Build-11
3. Build-12
4. Build-13
5. Build-14
6. surfaces monitoring / UI / contracts liées aux Hard States
7. service VPS / `live_websocket` / chaîne `LOCAL_REPLAY`

Sortie attendue :

- matrice d'écarts claire, classée P0 / P1 / P2
- chaque écart qualifié comme :
  - `docs contradictory`
  - `code contradictory`
  - `docs ambiguous`
  - `runtime evidence missing`

## Phase C — Décision doc ou code

Pour chaque écart :

- si le canon est clair et stable : **le code s'aligne**
- si plusieurs docs actifs se contredisent encore : **les docs actives se réalignent d'abord**
- si le sujet est une décision de gouvernance nouvelle : **ouvrir une décision explicite avant patch**

## Phase D — Corrections par lots chirurgicaux

Ordre recommandé :

1. contrats / enums / statuses / gates
2. protocole Shadow et reporting
3. Micro-live / Live gates
4. monitoring / UI de lecture
5. documentation active concernée
6. preuves runtime manquantes si l'environnement le permet

## Phase E — Requalification honnête

On ne requalifie un build qu'après :

- audit doc
- lecture code
- tests verts
- et preuve runtime cohérente avec le niveau de risque du sujet

---

# 6. Lots de travail concrets

## Lot 1 — Cartographie canonique Build-11/12/13/14

But :

- extraire la doctrine opératoire exacte
- lister les contradictions internes résiduelles

Livrables :

- table doc -> obligation -> fichier impacté

## Lot 2 — Audit code `src/protocols` / `scripts`

But :

- vérifier Shadow day counter
- vérifier report builder
- vérifier promotion gates
- vérifier orchestrator/service VPS
- vérifier `live_websocket`

Livrables :

- table obligation canonique -> code présent / absent / contradictoire

## Lot 3 — Audit monitoring / UI / Hard States

But :

- vérifier si les surfaces exposent correctement `SHADOW_ENABLED`, `SHADOW_VALIDATED`, `DORMANT`, `PROMOTED`
- vérifier les reliquats `read_only` / `limited_influence`

Livrables :

- liste des champs, vues et messages à réaligner

## Lot 4 — Audit moteurs C/D et Build-14

But :

- ne pas halluciner une activation réelle si le code garde encore C/D hors runtime
- vérifier la cohérence entre doctrine Shadow complet et réalité code

Livrables :

- verdict honnête sur le gap restant

## Lot 5 — Change request éventuelle sur `Micro-live 15 jours`

But :

- traiter cette évolution comme décision de gouvernance explicite

Si validée :

- patch coordonné du master, build plan, Build-12, Build-13, merge gates, tests associés

Si non validée :

- le canon reste à 7 jours minimum

---

# 7. Ce qu'il ne faut pas faire

- réécrire tous les `.md` avant l'audit
- transformer un handoff en nouveau canon
- corriger la durée du Micro-live "par intuition"
- déclarer Build-11 `ALIGNED` parce que le service tourne
- ignorer les reliquats C/D ou Build-14 encore incohérents dans le code
- mélanger correction documentaire, patch code et changement de doctrine dans un seul commit diffus

---

# 8. Définition de terminé

Le chantier sera considéré proprement cadré quand on aura :

- un inventaire d'écarts doc vs code stable
- une décision claire sur les durées canoniques de Micro-live
- un ordre de patch par lots
- une mémoire de suivi mise à jour après chaque lot
- et aucun verdict `ALIGNED` annoncé sans preuve complète

---

# 9. Prochaine action recommandée

Avant toute réécriture du canon :

1. terminer la matrice d'audit Build-11/12/13/14
2. séparer clairement :
   - écarts code vs docs
   - écarts docs vs docs
   - changements de doctrine souhaités
3. verrouiller explicitement la politique `Micro-live 7j` ou `Micro-live 15j`
4. seulement ensuite lancer les corrections

---

# 10. Résumé opératoire

Oui, il faut bien faire un **audit code vs markdown canonique**.

Mais non, il ne faut pas "corriger tous les md" d'un coup.

La bonne méthode prod-safe est :

`audit canon -> audit code -> décision doc ou code -> corrections par lots -> tests -> preuve runtime -> requalification honnête`

Ce document doit rester la mémoire de méthode de cette reprise.

