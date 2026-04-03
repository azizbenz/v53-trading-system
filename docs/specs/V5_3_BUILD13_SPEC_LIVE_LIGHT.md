# V5.3 — BUILD-13 SPEC
## Live-Light Production Protocol
### Protocole officiel de première production réelle disciplinée
### Treizième étape officielle du développement
### Premier rollout réel borné et gouverné

---

# 0. Objet du document

Ce document couvre **Build-13** du plan officiel V5.3.

Build-13 a une mission unique :

> définir le protocole de **Live-Light**, c’est-à-dire la première production réelle de la V5.3 en profil Light, après validation du Shadow et du Micro-live.

## HARD STATEMENT — Prérequis temporels non négociables

> **NON NÉGOCIABLE. Aucune dérogation.**

- **HARD : Light a tradé en Shadow intégral 30 jours calendaires consécutifs minimum** (Build-11 validé, avec A/B/C/D et Build-14 activés à 100%)
- **HARD : Verdict post-Shadow rendu composant par composant** (chaque moteur/enabler : `SHADOW_VALIDATED` ou `DORMANT`)
- **HARD : Micro-live stable minimum 7 jours** (Build-12 validé, avec uniquement les composants `SHADOW_VALIDATED`)
- **HARD : Rapport shadow produit, exploitable et approuvé** (incluant comparaison inter-moteurs et contribution Build-14)
- Sans ces prérequis, Build-13 ne peut pas être activé, même si tout le code est prêt
- L'activation intégrale en Shadow ne signifie pas promotion live automatique de tous les composants

Le Live-Light n’est pas une architecture partielle distincte de la V5.3.
C’est le premier **rollout reel borne** de la meme architecture complete,
dans lequel le systeme doit être capable de :

- produire du trading réel de manière disciplinée
- rester gouvernable en continu
- préserver le capital
- démontrer une crédibilité économique
- accumuler des preuves de robustesse avant toute extension gouvernée du rollout

## 0.1 Statut documentaire vs implémentation

Ce document définit le protocole cible Build-13 et exige une **implémentation réelle et complète** du Live-Light.

Build-13 n’est considéré codé, testable et validable que si le dépôt fournit réellement :

- un `runtime_mode = LIVE` opérable
- un chargement de configuration effectif
- une exécution exchange réelle et bornée
- une capacité réelle de sortie de positions
- une notification opérateur fonctionnelle
- des protocoles `rollback`, `degraded` et `halted` réellement opérables
- une supervision, des budgets et des gates réellement branchés au runtime

Un gate, un planner, un execution-intent builder ou une surface bornée ne suffisent jamais à eux seuls pour déclarer Build-13 complet.

Il ne doit pas être lu comme :

- la preuve qu’un simple gate Live-Light suffit
- la preuve que tout le rollout `COMPLETE` est déjà autorisé
- une autorisation à ouvrir Build-14, Build-15, Build-16 ou Build-17 sans validation effective

## 0.2 Règle d’unification local / VPS

Build-13 reste strictement dans la V5.3 unifiée :

- une seule base de code
- aucun fork local / VPS
- `runtime_mode = LIVE`
- aucun `BACKTEST_PROFILE`
- aucune promotion implicite depuis un replay local ou un artifact importé

---

# 1. Mission du Live-Light

Le Live-Light existe pour tester simultanément, dans des conditions réelles de production :

- la stabilité continue du rollout LIGHT sur la même architecture complète
- la robustesse des composants effectivement `SHADOW_VALIDATED` et autorisés en live
- la cohérence du portefeuille minimal
- la soutenabilité des coûts réels
- la qualité de la réconciliation sur la durée
- la discipline de supervision et de rollback
- la crédibilité économique du rollout LIGHT

Le Live-Light doit répondre à une question simple :

> la V5.3 en rollout LIGHT peut-elle rester en production réelle, de façon
> stable, explicable et économiquement crédible, sans dépendre d’ajustements
> manuels improvisés ?

---

# 2. Ce que Build-13 n’est pas

Build-13 n’est pas :

- la V5.3 Complete
- une autorisation à augmenter librement les tailles
- une preuve définitive de rentabilité statistique
- une phase “on laisse tourner et on verra”
- une excuse pour relâcher les garde-fous

Build-13 est :

- une **production réelle disciplinée**
- une **phase de stabilisation**
- une **phase d’observation économique réelle**
- une **phase de gouvernance stricte**

---

# 3. Position de Build-13 dans le plan global

## Avant Build-13
Les conditions suivantes doivent être satisfaites :

- Build-1 à Build-10 validés
- Build-11 `profil=LIGHT`, `runtime_mode=SHADOW` validé
- Build-12 `profil=LIGHT`, `runtime_mode=MICRO_LIVE` validé avec verdict GO
- coûts réels compatibles avec les hypothèses prudentes
- réconciliation fiable
- UI Light verrouillée
- protocole de rollback défini

## Après Build-13
Si Build-13 est validé, alors seulement :
- consolidation / hardening Build-15 et Build-16 pour les moteurs C/D observés en Shadow mais pas encore promus
- Build-17 : UI Complete + Live-Complete

## 3.1 Relation avec Build-14, onboarding et Build-9X

- Build-14 est une phase d’enablers **activés à 100% en Shadow** (`SHADOW_ENABLED`), promotion live conditionnelle au verdict post-Shadow
- les candidats `Build14_enabler`, `C_candidate` et `D_candidate` restent gouvernés par le protocole d’onboarding
- `LOCAL_REPLAY` et l’import d’artifact peuvent préparer une candidature, mais ne remplacent jamais la chaîne `SHADOW -> MICRO_LIVE -> LIVE`
- Build-9X, s’il existe plus tard, ne peut produire que diagnostics, hypothèses et replay bundles ; jamais une mutation live directe
- aucune trajectoire locale ne bypass `SHADOW -> MICRO_LIVE -> LIVE`

---

# 4. Objectifs stratégiques de Build-13

Build-13 doit établir cinq vérités :

## 4.1 Vérité de stabilité
Le système peut-il tenir en production continue sans dérive technique majeure ?

## 4.2 Vérité économique
A et B produisent-ils une activité réelle économiquement crédible, net de coûts ?

## 4.3 Vérité portefeuille
Le portefeuille Light reste-t-il discipliné dans le temps, sans dérive de concentration ni stérilisation excessive ?

## 4.4 Vérité opératoire
L’UI, le monitoring, les alertes et les procédures HALTED/DEGRADED sont-ils réellement utilisables en production ?

## 4.5 Vérité de readiness future
Le système accumule-t-il des preuves qui permettront d’ouvrir prudemment
l’extension gouvernée du rollout ?

---

# 5. Préconditions obligatoires

Build-13 ne peut pas commencer si une des conditions suivantes n’est pas satisfaite :

- verdict GO Build-12 absent
- coût réel encore trop instable
- réconciliation encore fragile
- règles de rollback non formalisées
- pair health trop erratique
- moteur A ou B encore conceptuellement instable
- UI Light encore contournable
- DTR / CRA / break-even / edge tracker incomplets en réel

---

# 6. Périmètre du Live-Light

## 6.1 Profil actif
- état canonique : `profil=LIGHT`, `runtime_mode=LIVE`
- nom de phase lisible : `Live-Light`
- 6 paires maximum
- coeur runtime attendu : moteurs A et B, avec C/D seulement s’ils ont été `SHADOW_VALIDATED` et industrialisés

## 6.2 Paires autorisées
Uniquement les paires validées par Shadow + Micro-live, typiquement :
- BTC/USDT
- ETH/USDT
- SOL/USDT
- XRP/USDT
- LINK/USDT
- ADA/USDT ou BNB/USDT selon la configuration validée

## 6.3 Moteurs autorisés
- A
- B
- C et D peuvent être promus seulement s’ils ont été observés en Shadow,
  classés `SHADOW_VALIDATED` et passés par leurs gates spécifiques de mise en
  service

## 6.4 Composants obligatoirement actifs
- tous les backbones précédents
- portfolio minimal
- meta minimal
- monitoring complet Light
- UI Light verrouillée
- protocole rollback
- protocole degraded
- protocole halted

## 6.5 Composants interdits
- activation réelle non gouvernée de C
- activation réelle non gouvernée de D
- extension COMPLETE sans gates passées
- activation > 6 paires
- overrides opérateur sur caps de risque
- montée sauvage de taille

## 6.6 Angles morts critiques à surveiller
- dérive de corrélation malgré seulement 6 paires
- faux sentiment de diversification A/B
- coûts destructeurs masqués par fréquence brute
- latence / backlog / stale non vus assez tôt
- désalignement état local / exchange
- contournement opérateur ou journalisation incomplète

---

# 7. Politique de montée en charge

## 7.1 Principe cardinal

Le Live-Light ne démarre pas à la taille cible maximale.

Il doit suivre une **montée prudente, conditionnelle et documentée**.

## 7.2 Règle générale

La taille Live-Light doit être supérieure au micro-live, mais rester :
- compatible avec les caps Light
- compatible avec le learning progressif
- suffisamment modérée pour supporter encore une erreur de jeunesse sans dommage excessif

## 7.3 Formulation conceptuelle

Si \(x_i^{micro}\) est la taille micro-live et \(x_i^{light,target}\) la taille Light finale visée, alors en entrée de Build-13 :

\[
x_i^{micro} < x_i^{live-light,init} \le x_i^{light,target}
\]

La progression doit être **par paliers**, et jamais continue / implicite.

## 7.4 Conditions de montée de palier

Un palier supérieur n’est autorisé que si :
- coûts réels restent compatibles
- réconciliation reste propre
- pair health reste stable
- A/B restent économiquement crédibles
- stérilisation ne dérive pas
- aucun incident critique récent n’est non résolu

## 7.5 Interdictions

- aucune augmentation de taille ad hoc
- aucune augmentation parce qu’une journée est bonne
- aucune montée de taille si un sous-système critique est en surveillance

---

# 8. États opératoires officiels

Le Live-Light doit fonctionner avec les états suivants :

- **LIVE-LIGHT**
- **DEGRADED**
- **HALTED**

## 8.1 LIVE-LIGHT
État nominal de production.

## 8.2 DEGRADED
État où le système reste opérationnel mais avec restrictions, par exemple :
- suspension de certaines paires
- moteur temporairement suspendu
- réduction de certaines capacités
- vigilance accrue sur l’exécution

## 8.3 HALTED
Arrêt explicite de la production de nouveaux trades.

Règle :
- HALTED doit être possible proprement
- HALTED doit être journalisé
- HALTED ne doit pas dépendre d’un bricolage manuel non traçable

---

# 9. Axes de validation du Live-Light

## 9.1 Axe A — Stabilité continue
On valide :
- uptime logique
- pair health stable
- reconnects gérables
- backlog maîtrisé
- DTR loss négligeable
- pas de dérive silencieuse

## 9.2 Axe B — Exécution réelle durable
On valide :
- coût réel stable
- partial fills gérés
- rejects / cancels gérés
- reconciliation fiable
- absence de divergence critique prolongée

## 9.3 Axe C — Viabilité économique
On valide :
- fréquence utile réelle
- CE réelle
- break-even moteur/pair
- stérilisation
- A utile sans être trop rare
- B utile sans devenir bruyant

## 9.4 Axe D — Viabilité portefeuille
On valide :
- respect des caps
- arbitrage A/B cohérent
- beta BTC maîtrisé
- cluster pressure maîtrisée
- capital alloué de façon productive

## 9.5 Axe E — Opérations / supervision
On valide :
- alerting actionnable
- UI Light exploitable
- journalisation opérateur
- procédures DEGRADED / HALTED / rollback

---

# 10. Métriques obligatoires du Live-Light

## 10.1 Portefeuille
- capital réel
- capital engagé
- capital libre
- GrossExp
- LossBudget
- beta BTC
- cluster dominant
- PnL réel
- CE portefeuille réelle
- drawdown Light

## 10.2 Moteurs
- fréquence utile A
- fréquence utile B
- rendement net A/B
- coût moyen / p90 A/B
- CE A/B
- drawdown A/B
- hard block rate A/B
- rejection by ranking rate A/B
- sterilization rate A/B

## 10.3 Paires
- état actif/suspendu
- pair health
- stale rate
- coût moyen
- coût p90
- CE
- fréquence utile
- suspensions / reprises

## 10.4 Exécution / réconciliation
- ACK rate
- FullFillRate
- PartialFillRate
- RejectRate
- CancelRate
- ELW moyen / p90
- CostDrift vs micro-live / shadow
- DivRate reconciliation
- recovery count

## 10.5 Data / infra
- reconnect count
- queue usage
- backlog
- stale rate
- DTRLossRate
- log loss rate
- latence événementielle

## 10.6 Meta
- DTR coverage
- CRA alerts
- phantom trades
- break-even réel
- edge status prudent
- drift des statuts edge

---

# 11. Formules de référence Live-Light

## 11.1 Rendement net réel
\[
r_i^{real} = g_i^{real} - c_i^{real}
\]

## 11.2 Espérance observée réelle
\[
\hat{\mu}^{real} = \frac{1}{N}\sum_{i=1}^{N} r_i^{real}
\]

## 11.3 Capital efficiency réelle
\[
CE^{real} = \frac{\sum_i PnL_i^{real}}{\sum_i x_i h_i}
\]

## 11.4 Taux de stérilisation
\[
SterilRate = \frac{\sum_i \mathbf{1}_{CE_i < CE_{min}}\mathbf{1}_{A_i=1}}{\sum_i A_i}
\]

## 11.5 Taux de hard block
\[
HBRate = \frac{N_{HB}}{N_{candidates}}
\]

## 11.6 Taux de divergence réconciliation
\[
DivRate = \frac{N_{divergences}}{N_{reconciliations}}
\]

## 11.7 Drift coût réel
\[
CostDrift = \frac{1}{N}\sum_i (c_i^{real} - c_i^{ref})
\]

où \(c_i^{ref}\) peut être le coût shadow prudent ou le coût micro-live de référence.

---

# 12. Critères de stabilité obligatoires

## 12.1 Critères techniques

Le Live-Light est stable techniquement si :

- DTRLossRate reste négligeable
- log loss reste négligeable
- backlog et queues restent sous contrôle
- pair health ne devient pas erratique
- divergences critiques de réconciliation restent absentes ou très rares et gérées

## 12.2 Critères économiques

Le Live-Light est stable économiquement si :

- coûts réels restent dans une zone défendable
- CE réelle n’est pas structurellement négative
- A et B ont une utilité identifiable
- la fréquence utile est non triviale
- la stérilisation ne devient pas dominante

## 12.3 Critères de portefeuille

Le Live-Light est stable portefeuille si :

- caps respectés
- beta BTC maîtrisé
- clusters maîtrisés
- capital non immobilisé de manière stérile
- arbitrage A/B reste cohérent

## 12.4 Critères opératoires

Le Live-Light est stable opératoirement si :

- alertes critiques sont vues et comprises
- procédures DEGRADED / HALTED fonctionnent
- rollback est réalisable
- l’UI Light reste non contournable

---

# 13. Conditions GO vers la poursuite du Live-Light

Le Live-Light peut être poursuivi normalement si :

- coûts réels compatibles
- A utile
- B utile
- CE Light crédible
- DTR / CRA / break-even / edge tracker fiables
- pair health stable
- réconciliation fiable
- alerting opérant
- pas d’incident critique non résolu

---

# 14. Conditions de passage en DEGRADED

Passage en DEGRADED recommandé ou obligatoire si :

- une ou plusieurs paires deviennent instables
- un moteur devient temporairement trop coûteux ou trop bruité
- backlog / stale augmentent sans être encore critiques
- cost drift devient défavorable
- une composante nécessite surveillance renforcée
- la production doit être limitée sans être totalement arrêtée

Exemples d’actions DEGRADED :
- suspendre une paire
- suspendre B temporairement
- réduire les tailles au palier inférieur
- limiter l’activité à A seul si B devient trop bruité

---

# 15. Conditions de HALTED

HALTED obligatoire si au moins un des points suivants survient :

- divergence critique de réconciliation
- perte de contrôle d’état portefeuille
- pair health critique non contenue
- DTR loss significatif
- log loss critique sur couches essentielles
- UI / monitoring ne permettent plus de superviser proprement
- violation majeure des budgets risque
- comportement exécution incohérent répété
- rollback nécessaire

HALTED recommandé si :
- cost drift devient fortement destructeur
- moteur B produit une activité massivement stérile
- moteur A devient inexploitable sans explication claire
- le système entre dans une zone de doute élevé non tranchée

---

# 16. Politique de rollback

## 16.1 Mission

Le rollback existe pour revenir à un état plus sûr sans improvisation.

## 16.2 Formes possibles
- retour à palier de taille inférieur
- passage en DEGRADED
- suspension d’un moteur
- suspension d’une ou plusieurs paires
- retour à HALTED

## 16.3 Règle

Le rollback doit être :
- prédéfini
- journalisé
- déclenchable rapidement
- compréhensible ex post

## 16.4 Interdits
- rollback informel non tracé
- patch manuel non journalisé
- “on laisse tourner encore un peu pour voir”

---

# 17. Critères NO-GO vers la suite du programme

La phase Complete ne doit pas être préparée si, en Live-Light :

- coûts réels restent trop instables
- A ou B ne tiennent pas économiquement
- portefeuille Light reste trop stérile
- pair health reste trop instable
- réconciliation reste fragile
- l’UI / monitoring restent insuffisants
- le système tient seulement grâce à une intervention opérateur constante

---

# 18. Table des échecs typiques du Live-Light

| Échec | Symptôme | Interprétation | Action |
|---|---|---|---|
| Faux live stable | pas d’incident majeur mais CE faible | production techniquement stable mais économiquement faible | corriger A/B/portfolio |
| Faux moteur A | A produit presque rien | A encore trop filtré | revoir Build-6 |
| Faux moteur B | B fait du volume coûteux | B trop permissif / mal filtré | revoir Build-7 |
| Faux portefeuille | bons trades mais mauvaise allocation | selector/router mal calibrés | revoir Build-8 |
| Faux monitoring | UI “OK” mais décisions peu visibles | Build-10 incomplet | corriger supervision |
| Faux risk safety | caps tenus mais concentration cachée | cluster / beta mal interprétés | corriger Build-4 / Build-8 |

---

# 19. Artefacts obligatoires de fin de Build-13

À la fin d’une fenêtre d’observation Live-Light, il faut produire :

1. **rapport stabilité technique**
2. **rapport coûts réels**
3. **rapport réconciliation**
4. **rapport moteurs A/B**
5. **rapport portefeuille Light**
6. **rapport supervision / opérations**
7. **rapport paliers et discipline de taille**
8. **verdict : poursuivre / dégrader / halter / préparer Complete Enablers**

---

# 20. Contenu minimum du rapport Live-Light

Le rapport doit répondre explicitement à :

- le Live-Light est-il techniquement stable ?
- les coûts réels restent-ils défendables ?
- le moteur A est-il utile sans être trop rare ?
- le moteur B apporte-t-il une vraie fréquence utile nette ?
- le portefeuille Light reste-t-il discipliné ?
- la CE réelle Light est-elle crédible ?
- quels incidents ont nécessité DEGRADED ou HALTED ?
- l’extension gouvernée du rollout est-elle prématurée ou envisageable ensuite ?

---

# 21. Tests obligatoires Build-13

## 21.1 Tests de production
- palier initial respecté
- pas d’augmentation de taille non autorisée
- paliers correctement journalisés
- passage DEGRADED possible
- passage HALTED possible

## 21.2 Tests de supervision
- alertes critiques visibles
- ack opérateur journalisés
- rollback déclenchable
- UI Light toujours verrouillée

## 21.3 Tests économiques
- CE réelle calculée
- coûts réels visibles
- break-even visible
- stérilisation visible
- A/B comparables

## 21.4 Tests de portefeuille
- budgets respectés
- arbitrage A/B traçable
- beta BTC et clusters visibles
- capital libre cohérent

---

# 22. Dérives globales Build-13 à ne pas faire

- prendre une courte stabilité comme preuve définitive
- monter les tailles trop vite
- juger la phase au PnL brut
- oublier la CE, le coût réel et la stérilisation
- préparer l’extension COMPLETE par impatience
- rester en live alors qu’un HALTED est justifié
- multiplier les interventions manuelles invisibles

---

# 23. Conditions de readiness pour Complete Enablers

Build-13 ne valide pas encore l’extension COMPLETE du rollout.
Il peut seulement établir un début de readiness si :

- Light est stable techniquement
- Light est crédible économiquement
- A/B sont compris
- portefeuille Light est discipliné
- supervision opérateur est robuste
- les coûts réels sont suffisamment connus
- les incidents critiques sont rares, compris et bien gérés

Sans cela, Build-14 serait prématuré.

---

# 24. Verdict final Build-13

Build-13 est la première phase où la V5.3 Light doit prouver qu’elle sait vivre en production, et pas seulement exister techniquement.

Si Build-13 est bien fait :
- la Light devient un vrai produit de trading discipliné
- le capital est protégé
- la gouvernance réelle fonctionne
- la suite du programme peut être envisagée rationnellement

Si Build-13 est mal fait :
- la production Light masquera des faiblesses profondes
- la phase Complete sera construite sur une base fragile
- les erreurs coûteront plus cher plus tard

Donc :

> Build-13 doit être traité comme un **build bloquant de maturité de production Light**, pas comme une simple prolongation du micro-live.

---

# Guardrails issus des audits — Préconditions runtime réel Build-13

## Runtime complet obligatoire (QWEN-03, QWEN-04)
- Le Live-Light exige un runtime complet : I/O exchange, event loop continu, persistance, réconciliation, monitoring, notification
- Aucun composant ne peut être mocké ou simulé en Live-Light
- Le système doit tourner de manière autonome pendant des jours sans intervention

## Notification opérateur (QWEN-06)
- En Live-Light, les alertes CRITICAL doivent être livrées à l'opérateur humain via un canal externe
- Un webhook (Slack, Telegram, ou équivalent) doit être configuré et testé
- Une alerte non livrée est aussi grave qu'une alerte non générée

## Workflow d'approbation (QWEN-08)
- Le passage en Live-Light doit suivre un processus d'approbation explicite
- Les conditions de passage (gates) doivent être vérifiées et loggées
- L'opérateur humain doit explicitement valider le passage

## Kill switch externe opérationnel (QWEN-07, GEM-10)
- En Live-Light, le kill switch externe (fichier flag ou API admin) doit être opérationnel et testé
- Un test de kill switch doit être exécuté avant le passage en Live-Light
- Le kill switch doit fermer toutes les positions ouvertes de manière ordonnée

## Interdiction de considérer Live-Light validé sans :
- au moins 7 jours de micro-live stable
- réconciliation exchange sans divergence critique
- DTR complet avec coûts réels
- CE (Capital Efficiency) mesurée et positive ou économiquement crédible
- notification opérateur testée et fonctionnelle

---

## Fin du document
