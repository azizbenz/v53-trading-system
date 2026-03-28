# V5.3 — BUILD-13 SPEC
## Live-Light Production Protocol
### Protocole officiel de première production réelle disciplinée
### Treizième étape officielle du développement
### Sans code — prod-safe

---

# 0. Objet du document

Ce document couvre **Build-13** du plan officiel V5.3.

Build-13 a une mission unique :

> définir le protocole de **Live-Light**, c’est-à-dire la première production réelle de la V5.3 en profil Light, après validation du Shadow et du Micro-live.

Le Live-Light n’est pas encore la version finale de la V5.3.  
C’est la première phase où le système doit être capable de :

- produire du trading réel de manière disciplinée
- rester gouvernable en continu
- préserver le capital
- démontrer une crédibilité économique
- accumuler des preuves de robustesse avant toute extension vers Complete

## 0.1 Statut documentaire vs implémentation

Ce document définit le **protocole cible** Build-13.

Il ne doit pas être lu comme :

- la preuve que le runtime Build-13 est déjà codé
- la preuve que `COMPLETE` est déjà exécutable
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

- la stabilité continue de l’architecture Light
- la robustesse d’A et B
- la cohérence du portefeuille minimal
- la soutenabilité des coûts réels
- la qualité de la réconciliation sur la durée
- la discipline de supervision et de rollback
- la crédibilité économique de la Light

Le Live-Light doit répondre à une question simple :

> la V5.3 Light peut-elle rester en production réelle, de façon stable, explicable et économiquement crédible, sans dépendre d’ajustements manuels improvisés ?

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
- Build-11 Shadow Light validé
- Build-12 Micro-live Light validé avec verdict GO
- coûts réels compatibles avec les hypothèses prudentes
- réconciliation fiable
- UI Light verrouillée
- protocole de rollback défini

## Après Build-13
Si Build-13 est validé, alors seulement :
- Build-14 : Complete Enablers
- puis éventuellement Build-15/16/17 vers la Complete

## 3.1 Relation avec Build-14, onboarding et Build-9X

- Build-14 reste une phase d’enablers d’abord en lecture seule
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
Le système accumule-t-il des preuves qui permettront, plus tard, d’ouvrir prudemment la phase Complete ?

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
- **Light uniquement**
- 6 paires maximum
- moteurs A et B uniquement

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
- C
- D
- Complete profile
- activation > 6 paires
- overrides opérateur sur caps de risque
- montée sauvage de taille

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
- la phase Complete est-elle prématurée ou envisageable plus tard ?

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
- préparer Complete par impatience
- rester en live alors qu’un HALTED est justifié
- multiplier les interventions manuelles invisibles

---

# 23. Conditions de readiness pour Complete Enablers

Build-13 ne valide pas encore la Complete.  
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

## Fin du document
