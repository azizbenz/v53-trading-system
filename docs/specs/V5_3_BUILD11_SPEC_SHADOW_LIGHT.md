# V5.3 — BUILD-11 SPEC
## Shadow Light Protocol
### Protocole officiel de validation pré-micro-live
### Onzième étape officielle du développement
### Première implémentation réelle, gouvernée et non-live

---

# 0. Objet du document

Ce document couvre **Build-11** du plan officiel V5.3.

Build-11 a une mission unique :

> valider la **V5.3 Light en mode Shadow intégral**, c’est-à-dire dans des conditions de flux et de logique aussi proches que possible du réel, mais sans engager de capital.

Build-11 ne crée pas un nouveau moteur ni un nouveau module central.
Il définit le **protocole de vérité pré-micro-live**.

## HARD STATEMENT — 30 jours de Shadow intégral (profil `LIGHT`) obligatoires

> **NON NÉGOCIABLE. Aucune dérogation, aucun raccourci, aucune exception.**

- La version Light doit trader en mode **SHADOW** pendant un minimum de **30 jours calendaires consécutifs**
- Données réelles obligatoires (WebSocket live ou replay de données réelles enregistrées)
- Pipeline complet : data → engine → scoring → portfolio → execution simulée
- DTR complet produit pendant les 30 jours
- Si un incident interrompt le shadow pendant plus de 24h, le compteur **reprend à zéro**
- Un rapport shadow exploitable doit être produit à l’issue (CE, coûts estimés, edge, drawdown, stale rate)
- **Aucune activation Micro-live ni Live-Light n’est autorisée avant l’expiration de cette période**
- "Le code est prêt" ou "les tests passent" ne sont PAS des arguments pour réduire cette durée

Le Shadow intégral doit répondre à une question simple :

> si l’on injecte des données réalistes, des coûts prudents, des budgets portefeuille et la logique intégrale de décision, le système reste-t-il cohérent, explicable, stable et économiquement crédible ?

## 0.1 Statut documentaire vs implémentation

Ce document définit le **protocole Build-11** et l’exigence d’une **implémentation réelle et complète** du Shadow.

Build-11 n’est considéré codé, testable et validable que si le dépôt fournit réellement :

- un `runtime_mode = SHADOW` opérable
- des données réelles ou des replays enregistrés de données réelles
- un pipeline complet `data -> engine -> scoring -> portfolio -> execution simulée`
- un DTR complet, une persistance exploitable et un rapport shadow exploitable
- une observabilité, des alerts et des états de gouvernance réellement branchés

Il ne doit jamais être lu comme :

- la preuve qu’un Shadow partiel, in-memory ou seulement gouverné suffit
- la preuve que Build-12 ou Build-13 sont ouverts
- la preuve que Build-10 est opéré en live dans le repo courant
- une autorisation à court-circuiter le chemin `LOCAL_REPLAY -> export artifact -> import VPS -> Shadow`

## 0.2 Règle d’unification local / VPS

Build-11 reste strictement dans la V5.3 unifiée :

- une seule base de code
- aucun fork local / VPS
- `runtime_mode = SHADOW`
- aucun `BACKTEST_PROFILE`
- aucun code stratégie importé et exécuté côté VPS

---

# 1. Mission du Shadow intégral — Phase de vérité système

## 1.0 Règle lexicale

- `LIGHT` et `COMPLETE` restent les deux seuls profils de rollout
- dans ce document, `Shadow intégral` désigne le Shadow du profil `LIGHT`
  où A/B et Build-14 sont activés à 100% en observation
- `Shadow intégral` n'est pas le profil `COMPLETE`

Le Shadow existe pour tester **la solution intégrale observée** simultanément :

- la qualité de la chaîne data
- la cohérence scoring / hard-soft-rank
- l’arbitrage portefeuille **A/B** (coeur runtime Light)
- les coûts attendus par moteur
- la discipline du risk backbone
- la qualité des DTR / CRA / break-even / edge tracker
- la supervision UI / monitoring
- **les enrichissements Build-14** (microstructure, régime, covariance, risk contribution, edge diversity) activés à 100%
- **les interactions inter-moteurs** A/B : conflits, duplication, concentration, complémentarité
- **la robustesse portefeuille** avec le coeur A/B et les enrichissements Build-14
- **le coût réel simulé prudent** avec activation Light + Build-14

Le Shadow n’est plus une simple validation Light minimale. Il est la **phase de vérité système** où l’on observe la solution intégrale avant de décider quoi promouvoir.

Sans ce protocole, un passage direct au micro-live serait aveugle.

---

# 2. Ce que Build-11 n’est pas

Build-11 n’est pas :

- un backtest classique
- un simple replay offline sans contrainte
- un live réel avec capital
- une validation “visuelle”
- un environnement où l’on ignore les coûts faute d’exécution réelle

Build-11 est un **mode shadow structuré**, avec :
- flux live ou quasi-live
- décisions complètes
- exécutions simulées prudentes
- budgets actifs
- logs complets
- critères de sortie falsifiables

---

# 3. Position de Build-11 dans le plan global

## Avant Build-11
Les builds précédents doivent être terminés et gelés :

- Build-1 : dependency architecture
- Build-2 : data backbone
- Build-3 : execution backbone
- Build-4 : risk backbone
- Build-5 : scoring backbone
- Build-6 : moteur A
- Build-7 : moteur B
- Build-8 : portfolio minimal
- Build-9 : meta minimal
- Build-10 : monitoring + UI Light

## Après Build-11
Si Build-11 est validé, alors seulement :
- Build-12 : micro-live Light

## 3.1 Relation avec Build-9X et LOCAL_REPLAY

- Build-9X peut alimenter Shadow via des projections gouvernées, sans devenir moteur autonome
- `LOCAL_REPLAY` peut préparer des hypothèses et artifacts, mais ne remplace jamais Build-11
- l’import d’artifact côté VPS reste en lecture seule et ne bypass jamais Shadow

---

# 4. Objectifs stratégiques de Build-11

Build-11 doit établir quatre vérités :

## 4.1 Vérité logique
Le système prend-il des décisions cohérentes et reproductibles ?

## 4.2 Vérité économique
Le système produit-il une fréquence utile plausible avec des coûts prudents ?

## 4.3 Vérité portefeuille
Le système A/B + portefeuille Light + Build-14 arbitre-t-il proprement les opportunités ?

## 4.4 Vérité opérationnelle
Le système reste-t-il observable, stable, non saturé et explicable en fonctionnement continu avec le coeur Light A/B et les enrichissements Build-14 ?

## 4.5 Vérité inter-moteurs
Les moteurs A/B apportent-ils une contribution réellement complémentaire sans duplication excessive ni inflation de coût ?

## 4.6 Vérité Build-14
Les enrichissements Build-14 améliorent-ils réellement la lecture du risque, de la corrélation, de la microstructure et de la diversité d'edge ?

---

# 5. Préconditions obligatoires

Build-11 ne peut pas commencer si une des conditions suivantes n’est pas satisfaite :

- interfaces non gelées
- DTR incomplets
- pair health non fiable
- exécution simulée non structurée
- coûts attendus non calculables
- UI Light non verrouillée
- risk backbone contournable
- moteurs A/B encore conceptuellement instables

---

# 6. Périmètre du Shadow intégral

## 6.1 Profil actif
- état canonique : `profil=LIGHT`, `runtime_mode=SHADOW`
- nom de phase lisible : `Shadow intégral`
- 6 paires maximum
- **Shadow intégral actif** : A/B + Build-14

## 6.2 Paires autorisées
- BTC/USDT
- ETH/USDT
- BNB/USDT ou ADA/USDT selon configuration Light retenue
- SOL/USDT
- XRP/USDT
- LINK/USDT

## 6.3 Moteurs activés en Shadow
- **A — activé à 100%** (`SHADOW_ENABLED`)
- **B — activé à 100%** (`SHADOW_ENABLED`)
- **C — hors scope Build-11** : réservé à Build-15
- **D — hors scope Build-11** : réservé à Build-16

Build-11 n'active pas C/D dans le runtime Shadow du rollout Light. Leur
introduction reste gouvernée par leurs builds dédiés.

## 6.4 Composants obligatoirement actifs
- data backbone
- quality backbone
- execution backbone en mode shadow
- risk backbone
- scoring backbone
- portfolio Light (arbitrage A/B, enrichi par Build-14)
- meta complet (DTR, CRA, edge tracker)
- monitoring complet
- UI Light verrouillée
- **Build-14 enablers activés à 100%** : microstructure enrichie, régime enrichi, covariance robuste, risk contribution, edge diversity

## 6.5 Composants interdits
- extension COMPLETE live sans gates passées
- overrides UI de caps
- logique RL / POMDP / experimentation libre
- **confondre activation Shadow et promotion live**

## 6.6 Hard States en entrée de Shadow

| Composant | Hard State |
|---|---|
| Moteur A | `SHADOW_ENABLED` |
| Moteur B | `SHADOW_ENABLED` |
| Moteur C | `SHADOW_ENABLED` |
| Moteur D | `SHADOW_ENABLED` |
| Build-14 microstructure | `SHADOW_ENABLED` |
| Build-14 régime | `SHADOW_ENABLED` |
| Build-14 covariance | `SHADOW_ENABLED` |
| Build-14 risk contribution | `SHADOW_ENABLED` |
| Build-14 edge diversity | `SHADOW_ENABLED` |

## 6.7 Verdict structuré à l'issue des 30 jours

À la fin du Shadow 30 jours, chaque composant reçoit un verdict individuel :

| Verdict | Signification |
|---|---|
| `SHADOW_VALIDATED` | Apporte une valeur démontrée, éligible à Micro-live |
| `DORMANT` | Ne démontre pas de valeur suffisante, désactivé pour le Micro-live |

Le verdict est composant par composant : un moteur peut être validé tandis qu'un autre est mis en dormance. La décision de promotion est basée sur les résultats observés, pas sur l'existence du code.

---

# 7. Nature de l’exécution en Shadow

## 7.1 Principe

Le Shadow ne passe pas de vrais ordres.  
Mais il ne doit pas non plus supposer une exécution parfaite.

Il doit utiliser une **exécution simulée prudente**.

## 7.2 Exécution shadow prudente

L’exécution shadow doit intégrer, au minimum :

- bid/ask ou mid+spread
- coût explicite
- slippage prudent
- latence simulée raisonnable
- partial fill risk simplifié si pertinent
- refus no-trade si coût trop élevé

## 7.3 Formules minimales

Coût total shadow :
\[
c_i^{shadow} = f_i^{sim} + s_i^{sim} + q_i^{sim}
\]

Break-even shadow :
\[
g_i^{BE,shadow} = c_i^{shadow}
\]

Valeur nette shadow :
\[
EV_i^{shadow} = x_i \cdot (\mathbb{E}[g_i] - c_i^{shadow})
\]

## 7.4 Règle critique

Le Shadow ne doit jamais utiliser :
- exécution parfaite
- spread nul
- latence nulle
- liquidité infinie

Sinon il devient un faux validateur.

---

# 8. Structure temporelle du protocole

## 8.1 Durée minimale

Le Shadow doit être observé sur une durée suffisante pour voir :

- plusieurs contextes de marché
- plusieurs séquences de décision
- au moins quelques cas de concurrence A/B
- plusieurs suspensions / reprises de paires éventuelles
- quelques scénarios de coûts défavorables

## 8.2 Principe

La durée exacte dépend du flux réel, mais le Shadow doit durer assez pour tester :
- stabilité
- explicabilité
- régularité des métriques
- non-fragilité au bruit

## 8.3 Interdiction

Valider Build-11 sur quelques heures ou un seul épisode de marché est interdit.

---

# 9. Axes de validation du Shadow

## 9.1 Axe A — Stabilité data / infra
On valide :
- reconnects
- stale rate
- pair health
- backlog
- queue usage
- DTR loss
- log loss

## 9.2 Axe B — Cohérence décisionnelle
On valide :
- DTR coverage
- hard blocks explicites
- penalties lisibles
- ranking explicable
- sélection portefeuille cohérente
- no-trade économiques clairs

## 9.3 Axe C — Viabilité économique
On valide :
- fréquence brute
- fréquence utile
- coût shadow moyen / p90
- break-even shadow
- CE attendue / observée shadow
- stérilisation

## 9.4 Axe D — Viabilité portefeuille
On valide :
- GrossExp shadow
- LossBudget shadow
- beta BTC shadow
- cluster pressure
- arbitrage A/B
- absence de redondance grossière

## 9.5 Axe E — Gouvernance opérateur
On valide :
- alertes critiques visibles
- UI Light verrouillée
- impossibilité de sortir du profil
- journalisation des actions

---

# 10. Métriques obligatoires du Shadow

## 10.1 Portefeuille
- capital simulé
- exposition brute
- budget perte
- capital libre
- beta BTC
- cluster dominant
- PnL shadow
- CE portefeuille shadow

## 10.2 Moteurs
- fréquence utile A
- fréquence utile B
- rendement net shadow A
- rendement net shadow B
- coût moyen / p90 A/B
- CE A/B
- drawdown shadow A/B
- corrélation A/B

## 10.3 Paires
- pair health
- stale rate
- coût moyen par paire
- fréquence utile par paire
- CE par paire
- suspensions / reprises

## 10.4 Data / infra
- reconnect count
- queue usage
- backlog
- disorder/gap rates
- DTR loss rate
- log loss rate
- latence événementielle

## 10.5 Meta
- DTR coverage
- hard block rate
- rejection by ranking rate
- sterilization rate
- phantom trade count
- break-even par moteur/pair
- edge status prudent

---

# 11. Formules de référence Shadow

## 11.1 Fréquence utile
\[
F_{utile} = \frac{\text{trades à expectancy utile}}{\text{temps}}
\]

## 11.2 Rendement net shadow
\[
r_i^{shadow} = g_i^{shadow} - c_i^{shadow}
\]

## 11.3 Espérance observée shadow
\[
\hat{\mu}^{shadow} = \frac{1}{N}\sum_{i=1}^{N} r_i^{shadow}
\]

## 11.4 Capital efficiency shadow
\[
CE^{shadow} = \frac{\sum_i PnL_i^{shadow}}{\sum_i x_i h_i}
\]

## 11.5 Taux de hard block
\[
HBRate = \frac{N_{HB}}{N_{candidates}}
\]

## 11.6 Taux de stérilisation
\[
SterilRate = \frac{\sum_i \mathbf{1}_{CE_i < CE_{min}}\mathbf{1}_{A_i=1}}{\sum_i A_i}
\]

## 11.7 Taux de perte DTR
\[
DTRLossRate = \frac{N_{DTR,drops}}{N_{DTR,attempted}}
\]

## 11.8 Utilisation queue
\[
\rho_q = \frac{\lambda}{\mu_s}
\]

---

# 12. Critères de validation obligatoires

## 12.1 Critères logiques

Le Shadow est valide logiquement si :

- les décisions sont reproductibles
- les DTR sont complets
- les hard blocks sont explicables
- les refus relatifs sont explicables
- les no-trades économiques sont visibles
- les phantom trades sont détectables

## 12.2 Critères économiques

Le Shadow est valide économiquement si :

- la fréquence utile Light est supérieure à V5.2 ou au moins crédiblement plus élevée
- les coûts shadow restent compatibles avec l’edge attendu
- la CE shadow n’est pas structurellement stérile
- A et B ne produisent pas massivement des trades non monétisables

## 12.3 Critères portefeuille

Le Shadow est valide portefeuille si :

- les caps sont réellement respectés
- A et B sont arbitrés avec logique
- le beta BTC reste sous contrôle
- les clusters corrélés ne sont pas surchargés
- le capital n’est pas alloué de manière absurde

## 12.4 Critères opérationnels

Le Shadow est valide opérationnellement si :

- backlog et stale restent maîtrisés
- pair health fonctionne
- la UI Light permet de superviser clairement
- l’alerting n’est ni aveugle ni hystérique

---

# 13. Conditions de sortie GO vers Build-12 (Micro-live)

Le passage vers Build-12 n’est autorisé que si :

## 13.1 Data / infra
- DTRLossRate négligeable
- log loss négligeable
- backlog sous contrôle
- reconnect storms absents ou bien gérés
- pair health stable

## 13.2 Décision
- DTR coverage suffisant
- hard blocks correctement codés
- ranking cohérent
- pas de décisions fantômes invisibles

## 13.3 Économie
- coûts shadow crédibles
- break-even visible
- fréquence utile non triviale
- CE shadow plausible
- stérilisation sous contrôle

## 13.4 Portefeuille
- budgets réellement respectés
- arbitrage A/B propre
- beta BTC maîtrisé
- pas de cluster overload récurrent

## 13.5 UI / monitoring
- dashboards complets
- alertes critiques visibles
- UI Light non contournable
- journal d’actions opérateur fonctionnel

---

# 14. Conditions NO-GO absolues

Passage en micro-live interdit si au moins un des points suivants est vrai :

- DTR incomplets
- coût shadow non crédible
- exécution shadow trop optimiste
- pair health non fiable
- backlog élevé non expliqué
- stérilisation massive
- A trop rare et B trop bruyant
- budgets portefeuille contournables
- UI Light permissive
- alerting inutilisable
- edge shadow lu sans prudence

---

# 15. Table des échecs typiques du Shadow

| Échec | Symptôme | Interprétation | Action |
|---|---|---|---|
| Faux vert logique | peu d’alertes, peu de refus | DTR / rules trop faibles | renforcer traçabilité |
| Faux vert économique | PnL shadow beau, coût irréaliste | exécution trop optimiste | durcir coût shadow |
| Faux vert portefeuille | beaucoup de trades mais CE faible | allocation mal réglée | revoir selector/router |
| Faux vert infra | système “tourne” mais backlog grimpe | saturation non visible | corriger monitoring/queues |
| Faux vert moteur B | fréquence élevée, CE faible | B fait du bruit | durcir anti-breakout / coût |
| Faux vert moteur A | très peu de trades, joli dashboard | A trop filtré | réduire veto cachés |

---

# 16. Table des causes de rejet avant micro-live

| Cause | Exemple | Gravité |
|---|---|---:|
| DTR non fiables | refus non traçables | critique |
| Coûts trop optimistes | slippage sous-estimé | critique |
| Pair health instable | suspensions incohérentes | majeure |
| Backlog / stale élevés | décisions trop vieilles | critique |
| CE shadow trop faible | activité stérile | majeure |
| Hard block inflation | trop de veto | majeure |
| Ranking non crédible | sélection arbitraire | majeure |
| UI permissive | actions interdites possibles | critique |

---

# 17. Protocole d’observation recommandé

## 17.1 Étape 1 — Mise sous observation
Le système tourne en Shadow avec :
- profil Light
- A/B actifs
- budgets complets
- UI active
- DTR / CRA / break-even / edge tracker actifs

## 17.2 Étape 2 — Observation structurée
On collecte :
- métriques continues
- incidents
- refus
- stérilisation
- arbitrages A/B
- coûts shadow

## 17.3 Étape 3 — Post-mortem Shadow
On produit une lecture structurée :
- ce qui marche
- ce qui reste fragile
- ce qui est trop optimiste
- ce qui doit être corrigé avant micro-live

---

# 18. Artefacts obligatoires de fin de Build-11

À la fin du Shadow, il faut produire :

1. **rapport stabilité data / infra**
2. **rapport décisions & DTR**
3. **rapport coûts & break-even**
4. **rapport A vs B**
5. **rapport portefeuille minimal**
6. **rapport UI / alerting**
7. **verdict GO / NO-GO micro-live**

---

# 19. Contenu minimum du rapport GO / NO-GO

Le rapport final Build-11 doit répondre explicitement à :

- la fréquence utile est-elle crédible ?
- le moteur A est-il encore trop rare ?
- le moteur B produit-il du bruit ou une vraie rotation utile ?
- les coûts shadow sont-ils prudents ?
- la CE portefeuille shadow est-elle crédible ?
- les DTR sont-ils complets ?
- l’UI Light est-elle vraiment verrouillée ?
- que faut-il corriger avant Build-12 ?

---

# 20. Tests obligatoires Build-11

## 20.1 Tests de protocole
- activation profil Light uniquement
- refus activation moteur hors gates ou hors budget
- refus activation > 6 paires
- shadow sans exécution réelle

## 20.2 Tests de cohérence
- métriques shadow publiées
- DTR coverage correcte
- break-even visible
- edge tracker prudent visible

## 20.3 Tests d’échec
- pair health dégradée
- stale spike
- coût shadow défavorable
- cluster surcharge simulée
- moteur B rejeté pour environnement hostile

## 20.4 Tests opérateur
- UI affiche alertes critiques
- action interdite refusée
- journalisation des actions opérateur
- passage HALTED possible

---

# 21. Dérives globales Build-11 à ne pas faire

- valider le Shadow sur un échantillon trop court
- se satisfaire d’un PnL shadow sans vérifier les coûts
- ignorer la CE
- lire les moteurs séparément sans regarder le portefeuille
- utiliser le Shadow comme simple démo UI
- passer en micro-live “pour voir”, sans verdict GO/NO-GO formel

---

# 22. Verdict final Build-11

Build-11 est l’épreuve de vérité pré-micro-live.

Si Build-11 est bien fait :
- la V5.3 Light devient crédible comme système réel
- les défauts restants sont visibles avant risque capital
- le micro-live peut commencer avec discipline

Si Build-11 est mal fait :
- le micro-live sera un test aveugle
- les coûts réels surprendront
- les moteurs seront mal jugés
- la production Light pourra échouer pour de mauvaises raisons

Donc :

> Build-11 doit être traité comme un **build bloquant de validation systémique**, pas comme une simple période d’observation.

---

# Guardrails issus des audits — Préconditions runtime réel Build-11

## Shadow ≠ validable sur modèles in-memory seuls (QWEN-03, QWEN-04)
- Le shadow mode doit opérer sur des données de marché réelles (WebSocket ou replay de données réelles)
- Un shadow qui tourne sur des données mockées ou générées ne constitue pas une validation
- Le shadow doit démontrer que le pipeline complet fonctionne : data → engine → scoring → portfolio → execution simulée

## Préconditions I/O et event loop (QWEN-03)
- Avant de valider Build-11, le système doit démontrer :
  - une connexion WebSocket réelle (ou un replay réaliste de données enregistrées)
  - un event loop fonctionnel qui traite les messages en flux continu
  - une persistance des décisions shadow (DTR shadow)
  - un config loading depuis fichier YAML/JSON officiel
- Si ces éléments sont absents, Build-11 reste "scaffold" et non "validé"

## Interdiction de considérer shadow validé sans runtime réel
- Un shadow qui passe ses tests unitaires mais n’a jamais tourné sur un flux réel pendant une durée significative (minimum 24h) n’est pas validé
- Le DTR shadow doit contenir des décisions sur des données réelles, pas sur des fixtures de test

## Stale guard en shadow (GEM-23)
- En shadow, les messages stale sont loggés mais ne bloquent pas
- Le logging doit capturer la fréquence et la distribution des stale events
- Ces métriques alimentent la décision de passer en Micro-live

## Clarification rôle des configs YAML
- Si des fichiers de configuration YAML existent dans le dépôt, ils doivent être chargés par un module officiel (`config_loader` ou équivalent)
- Un fichier YAML présent mais non chargé par le code est un gap documentaire
- Le shadow doit utiliser exactement les mêmes configs que les modes suivants

---

## Fin du document
