# V5.3 — BUILD-12 SPEC
## Micro-live Light Protocol
### Protocole officiel de validation à capital réel ultra-prudent
### Douzième étape officielle du développement
### Sans code — prod-safe

---

# 0. Objet du document

Ce document couvre **Build-12** du plan officiel V5.3.

Build-12 a une mission unique :

> valider la **V5.3 Light en micro-live**, c’est-à-dire avec du capital réel mais à taille ultra-prudente, afin de confronter le système à la vérité de l’exécution, des coûts, de la latence, de la réconciliation et de la discipline opératoire.

Le micro-live n’est pas une phase de performance.  
C’est une phase de **vérité d’exécution**.

Build-12 doit répondre à une question simple :

> quand la V5.3 Light passe du shadow à l’argent réel, les hypothèses critiques restent-elles valides, ou bien les coûts, les fills, les divergences d’état et les contraintes de marché détruisent-ils l’économie du système ?

---

# 1. Mission du Micro-live Light

Le Micro-live Light existe pour tester simultanément :

- la qualité réelle de l’exécution
- le coût réel par moteur et par paire
- la stabilité de la réconciliation
- la robustesse des budgets en vrai
- la discipline de l’order_decider
- la cohérence entre shadow et réel
- la qualité de supervision opérateur
- la capacité à arrêter proprement en cas de dérive

Sans cette phase, le passage direct en Live-Light serait prématuré.

---

# 2. Ce que Build-12 n’est pas

Build-12 n’est pas :

- une phase pour “faire du PnL”
- une validation statistique définitive
- un live complet
- un test pour augmenter les tailles rapidement
- une preuve que le système est déjà mature

Build-12 est :

- un **test de vérité opérationnelle**
- un **test de vérité de coût**
- un **test de vérité de réconciliation**
- un **test de vérité de discipline**

---

# 3. Position de Build-12 dans le plan global

## Avant Build-12
Les conditions suivantes doivent être satisfaites :

- Build-1 à Build-10 validés
- Build-11 Shadow Light validé avec verdict GO
- profil Light verrouillé
- UI Light verrouillée
- exécution live réelle disponible
- DTR / CRA / break-even / edge tracker actifs
- budget micro-live défini explicitement

## Après Build-12
Si Build-12 est validé, alors seulement :
- Build-13 : Live-Light

---

# 4. Objectifs stratégiques de Build-12

Build-12 doit établir cinq vérités :

## 4.1 Vérité d’exécution
Les ordres vivent-ils réellement comme prévu :
- ACK
- fill
- partial fill
- cancel
- timeout
- reject

## 4.2 Vérité de coût
Le coût réel reste-t-il dans une zone compatible avec le shadow prudent ?

## 4.3 Vérité de réconciliation
L’état local reste-t-il aligné avec l’état exchange réel ?

## 4.4 Vérité économique minimale
Même à très petite taille, le système évite-t-il déjà les comportements économiquement absurdes :
- trades phantom
- coûts destructeurs
- sur-activité stérile

## 4.5 Vérité opératoire
L’équipe / l’opérateur peut-elle superviser et arrêter le système proprement ?

---

# 5. Préconditions obligatoires

Build-12 ne peut pas commencer si une des conditions suivantes n’est pas satisfaite :

- verdict GO Build-11 absent
- coûts shadow trop optimistes ou non crédibles
- DTR coverage insuffisante
- reconciliation non fiable
- UI Light permissive
- pair health instable
- alerting critique incomplet
- règles d’arrêt micro-live non définies

---

# 6. Périmètre du Micro-live Light

## 6.1 Profil actif
- **Light uniquement**
- 6 paires maximum
- moteurs A et B uniquement

## 6.2 Paires autorisées
Seulement les paires validées en Shadow Light, en pratique :
- BTC/USDT
- ETH/USDT
- SOL/USDT
- XRP/USDT
- LINK/USDT
- ADA/USDT ou BNB/USDT selon la validation Shadow

## 6.3 Moteurs autorisés
- A
- B

## 6.4 Composants obligatoirement actifs
- data backbone
- quality backbone
- execution backbone réel
- risk backbone
- scoring backbone
- portfolio minimal
- meta minimal
- monitoring
- UI Light verrouillée
- protocoles d’arrêt immédiat

## 6.5 Composants interdits
- moteurs C/D
- Complete profile
- overrides UI de caps
- élargissement discrétionnaire du scope
- augmentation de taille non planifiée

---

# 7. Politique de taille micro-live

## 7.1 Principe cardinal

Le micro-live doit être **ultra-prudent**.

Il doit être suffisamment petit pour :
- protéger le capital
- limiter les erreurs de jeunesse
- observer les vrais coûts
- tester la réconciliation sans pression financière excessive

Il doit être suffisamment réel pour :
- déclencher les vrais chemins exchange
- mesurer les vrais frais
- mesurer les vrais fills
- produire de vraies divergences si elles existent

## 7.2 Règle générale

Les tailles micro-live doivent être :

- très inférieures aux tailles Shadow plausibles
- très inférieures aux tailles Live-Light cibles
- compatibles avec les minimums échange
- compatibles avec des coûts encore mesurables

## 7.3 Interdictions

- aucun Tier 3
- aucun sizing agressif
- aucune montée discrétionnaire de taille en cours de route
- aucune “exception” parce qu’un signal paraît magnifique

## 7.4 Formulation conceptuelle

Si \(x_i^{live}\) désigne la taille live normale visée plus tard, alors en micro-live :

\[
x_i^{micro} \ll x_i^{live}
\]

et plus précisément :

\[
x_i^{micro} = \eta \cdot x_i^{light\_target}, \quad \eta \ll 1
\]

avec \(\eta\) fixé ex ante, documenté et non modifiable discrétionnairement en séance.

## 7.5 Taille minimale économique

Le micro-live doit éviter le paradoxe :
- taille tellement faible qu’aucun coût réel n’est observable
- ou taille tellement faible que chaque trade est automatiquement phantom

Il faut donc viser :

\[
x_i^{micro} \text{ assez petit pour protéger le capital, mais assez grand pour observer les coûts réels}
\]

---

# 8. Nature de l’exécution en Micro-live

## 8.1 Principe

Contrairement au Shadow, le Micro-live passe de vrais ordres.

On valide donc :
- type d’ordre réel
- latence ACK
- first fill latency
- partial fill rate
- coût explicite réel
- coût implicite réel
- réconciliation réelle

## 8.2 Ce qui doit être mesuré en priorité

- order send → ACK
- ACK → first fill
- full fill latency
- reject rate
- cancel rate
- partial fill rate
- ELW réel
- cost drift vs shadow
- divergence local/remote

## 8.3 Formules minimales

Latence ACK :
\[
AckLat = t^{ack} - t^{send}
\]

Latence premier fill :
\[
FirstFillLat = t^{firstfill} - t^{send}
\]

ELW réel :
\[
ELW_i = \frac{|P_i^{exec} - Mid_i|}{Mid_i}
\]

Coût réel total :
\[
c_i^{real} = f_i + c_i^{impl} + AS_i + PF_i
\]

Drift de coût vs shadow :
\[
CostDrift_i = c_i^{real} - c_i^{shadow}
\]

---

# 9. Structure temporelle du protocole

## 9.1 Durée minimale

Le micro-live doit durer assez pour observer :
- plusieurs vrais ordres
- plusieurs types d’issues (fill, partial, cancel, reject éventuel)
- plusieurs situations de coût
- au moins quelques arbitrages portefeuille A/B
- quelques épisodes de charge data / infra réalistes

## 9.2 Interdiction

Valider Build-12 après très peu de trades ou après une simple séance “sans incident” est interdit.

Le protocole doit durer assez pour vérifier :
- stabilité
- coût réel
- réconciliation
- discipline opérateur

---

# 10. Axes de validation du Micro-live

## 10.1 Axe A — Exécution réelle
On valide :
- ACK
- fills
- partial fills
- cancels
- rejects
- expirations éventuelles
- latences

## 10.2 Axe B — Coût réel
On valide :
- frais explicites réels
- ELW réel
- coût total réel
- drift réel vs shadow
- break-even réel par moteur/pair

## 10.3 Axe C — Réconciliation
On valide :
- ordres locaux vs exchange
- fills locaux vs exchange
- positions locales vs exchange
- inventaire / solde local vs exchange
- procédures de recovery

## 10.4 Axe D — Portefeuille / risque
On valide :
- respect des caps
- arbitrage A/B réel
- beta BTC maîtrisé
- clusters maîtrisés
- absence de contournement via petites tailles

## 10.5 Axe E — Observabilité / opérateur
On valide :
- alertes visibles
- UI utile
- DTR complets
- CRA fonctionnel
- break-even visible
- actions d’arrêt propres

---

# 11. Métriques obligatoires du Micro-live

## 11.1 Exécution
- nombre d’ordres envoyés
- ACK rate
- FullFillRate
- PartialFillRate
- RejectRate
- CancelRate
- AckLat
- FirstFillLat
- FullFillLat

## 11.2 Coût
- coût explicite réel
- ELW moyen / p90
- coût total réel moyen / p90
- CostDrift vs shadow
- break-even réel par moteur
- break-even réel par paire

## 11.3 Portefeuille / risque
- GrossExp réel
- LossBudget réel
- beta BTC réel
- cluster dominant
- capital libre
- positions ouvertes
- refus risque

## 11.4 Moteurs
- fréquence utile A
- fréquence utile B
- coût réel A/B
- CE réelle A/B
- drawdown micro-live A/B
- part de no-trade due au coût réel

## 11.5 Data / infra
- reconnect count
- backlog
- queue usage
- stale rate
- DTRLossRate
- log loss rate
- pair health transitions

## 11.6 Meta
- DTR coverage réel
- CRA alerts
- phantom trade count réel
- break-even drift
- edge status prudent mis à jour

---

# 12. Formules de référence Micro-live

## 12.1 Rendement net réel
\[
r_i^{real} = g_i^{real} - c_i^{real}
\]

## 12.2 Espérance observée réelle
\[
\hat{\mu}^{real} = \frac{1}{N}\sum_{i=1}^{N} r_i^{real}
\]

## 12.3 Capital efficiency réelle
\[
CE^{real} = \frac{\sum_i PnL_i^{real}}{\sum_i x_i h_i}
\]

## 12.4 Taux de partial fills
\[
PFR = \frac{N_{partial}}{N_{orders}}
\]

## 12.5 Taux de divergence réconciliation
\[
DivRate = \frac{N_{divergences}}{N_{reconciliations}}
\]

## 12.6 Taux de stérilisation réel
\[
SterilRate = \frac{\sum_i \mathbf{1}_{CE_i < CE_{min}}\mathbf{1}_{A_i=1}}{\sum_i A_i}
\]

## 12.7 Drift coût réel vs shadow
\[
CostDrift = \frac{1}{N}\sum_i (c_i^{real} - c_i^{shadow})
\]

---

# 13. Critères de validation obligatoires

## 13.1 Critères d’exécution

Le micro-live est valide en exécution si :

- les ordres sont traçables du send au terminal state
- les partial fills sont gérés
- les coûts réels sont mesurables
- les rejects / cancels sont correctement encodés
- la latence reste dans une zone compatible avec la stratégie

## 13.2 Critères de coût

Le micro-live est valide en coût si :

- le coût réel reste dans une zone cohérente avec le shadow prudent
- les p90 ne révèlent pas une destruction systémique de l’edge
- le break-even réel est lisible
- les moteurs A/B ne sont pas massivement détruits par le coût

## 13.3 Critères de réconciliation

Le micro-live est valide en réconciliation si :

- les divergences sont rares, détectées et classées
- aucune divergence critique n’est silencieuse
- le recovery peut être déclenché proprement
- l’état portefeuille local est fiable

## 13.4 Critères portefeuille

Le micro-live est valide portefeuille si :

- les caps restent respectés
- l’allocation reste cohérente
- les refus portefeuille sont explicites
- A et B restent arbitrés proprement
- aucun contournement des budgets n’apparaît

## 13.5 Critères opératoires

Le micro-live est valide opératoirement si :

- les alertes critiques sont visibles
- l’UI reste verrouillée
- l’arrêt HALTED est possible proprement
- les actions opérateur sont journalisées

---

# 14. Conditions GO vers Build-13 (Live-Light)

Le passage vers Build-13 n’est autorisé que si :

## 14.1 Exécution
- ACK / fills / cancels / rejects correctement suivis
- partial fills correctement gérés
- latences compatibles
- réconciliation fiable

## 14.2 Coût
- coût réel crédible
- drift shadow → réel acceptable
- break-even réel visible
- pas de destruction massive systémique par le coût

## 14.3 Portefeuille
- caps respectés en conditions réelles
- arbitrage A/B toujours cohérent
- beta BTC et clusters maîtrisés
- capital libre / engagé cohérents

## 14.4 Meta
- DTR complets
- CRA utile
- phantom trades visibles
- edge tracker prudent encore crédible

## 14.5 Opérations
- UI Light verrouillée
- alerting actionnable
- protocole d’arrêt éprouvé
- pas de dépendance à des bricolages manuels cachés

---

# 15. Conditions NO-GO absolues

Passage en Live-Light interdit si au moins un des points suivants est vrai :

- coûts réels très supérieurs au shadow prudent
- partial fills ou cancels mal gérés
- divergences de réconciliation critiques
- DTR incomplets en réel
- pair health instable en conditions réelles
- backlog / stale / queues non maîtrisés
- A ou B deviennent structurellement stériles en réel
- UI Light contournable
- protocole d’arrêt non fiable
- discipline de taille non respectée

---

# 16. Critères d’arrêt immédiat (Kill / Halt Conditions)

Le micro-live doit avoir des règles d’arrêt immédiat explicites.

## 16.1 Arrêt immédiat obligatoire si
- divergence critique locale / exchange
- perte de réconciliation de position
- pair health critique non gérée
- backlog ou stale sévère impactant les décisions
- DTR loss significatif
- log loss significatif sur couches critiques
- UI ou opérateur ne peut plus superviser correctement
- comportement d’exécution incohérent répété

## 16.2 Arrêt prudent recommandé si
- cost drift très défavorable
- partial fill regime nettement plus mauvais que prévu
- moteur B génère beaucoup de bruit coûteux
- moteur A ne produit rien ou trop peu pour être évalué
- trop de phantom trades en réel

---

# 17. Table des échecs typiques du Micro-live

| Échec | Symptôme | Interprétation | Action |
|---|---|---|---|
| Faux vert shadow | réel beaucoup plus cher | shadow trop optimiste | durcir exécution simulée |
| Faux vert réconciliation | positions locales fausses | tracking/recovery insuffisants | corriger Build-3 |
| Faux vert moteur B | beaucoup de petits fills coûteux | B mal calibré / trop sensible au coût | durcir B |
| Faux vert moteur A | peu de trades + coût réel plus élevé | A encore trop rare / trop tardif | réviser A |
| Faux vert opérateur | UI OK mais décisions non supervisables | dashboard incomplet | corriger Build-10 |
| Faux vert portefeuille | caps tenus mais CE faible | selector/router mal calibrés | corriger Build-8 |

---

# 18. Table des causes de rejet avant Live-Light

| Cause | Exemple | Gravité |
|---|---|---:|
| Coût réel trop mauvais | p90 très supérieur au shadow | critique |
| Réconciliation faible | divergences répétées | critique |
| DTR réels incomplets | post-mortem impossible | critique |
| Discipline taille cassée | augmentation improvisée | critique |
| Moteur B trop coûteux | fréquence brute sans CE | majeure |
| Moteur A inexploitable | trop rare en réel | majeure |
| UI / alerting insuffisants | supervision tardive | majeure |

---

# 19. Protocole d’observation recommandé

## 19.1 Étape 1 — Lancement micro-live
- profil Light
- tailles micro fixées ex ante
- A/B actifs
- caps risque complets
- UI / monitoring actifs

## 19.2 Étape 2 — Observation structurée
On collecte :
- ordres réels
- fills réels
- coûts réels
- divergences de réconciliation
- arbitrages A/B
- réactions opérateur

## 19.3 Étape 3 — Post-mortem micro-live
On produit une lecture structurée :
- shadow vs réel
- coûts
- réconciliation
- moteurs A/B
- portefeuille
- opérations
- verdict GO/NO-GO Live-Light

---

# 20. Artefacts obligatoires de fin de Build-12

À la fin du micro-live, il faut produire :

1. **rapport exécution réelle**
2. **rapport coût réel vs shadow**
3. **rapport réconciliation**
4. **rapport A vs B en réel**
5. **rapport portefeuille Light réel**
6. **rapport UI / alerting en réel**
7. **verdict GO / NO-GO Live-Light**

---

# 21. Contenu minimum du rapport GO / NO-GO

Le rapport final Build-12 doit répondre explicitement à :

- le coût réel valide-t-il le shadow prudent ?
- la réconciliation est-elle fiable ?
- les DTR réels sont-ils complets ?
- le moteur A reste-t-il utile en réel ?
- le moteur B garde-t-il une vraie fréquence utile nette ?
- le portefeuille Light reste-t-il discipliné ?
- quelles corrections sont nécessaires avant Build-13 ?

---

# 22. Tests obligatoires Build-12

## 22.1 Tests d’exécution
- ordre réel envoyé
- ACK reçu
- fill simple
- partial fill
- cancel / reject si cas rencontrés
- coût réel calculé

## 22.2 Tests de réconciliation
- ordre aligné local/remote
- fill aligné local/remote
- position alignée local/remote
- divergence classée
- recovery déclenché si nécessaire

## 22.3 Tests de supervision
- alerte critique visible
- action HALTED possible
- journalisation opérateur
- UI Light toujours verrouillée

## 22.4 Tests économiques
- break-even réel visible
- CE réelle visible
- shadow vs réel comparable
- phantom trades détectés

---

# 23. Dérives globales Build-12 à ne pas faire

- augmenter la taille trop tôt
- pardonner des divergences “parce que micro-live”
- juger la phase sur le PnL brut
- ignorer la CE et le coût réel
- passer en Live-Light parce que “ça semble marcher”
- corriger manuellement sans tracer
- laisser un opérateur sortir du profil Light

---

# 24. Verdict final Build-12

Build-12 est l’épreuve de vérité en argent réel, à petite échelle.

Si Build-12 est bien fait :
- le système rencontre enfin le marché réel avec discipline
- les coûts et la réconciliation deviennent des faits
- la transition vers Live-Light devient crédible
- les défauts restants apparaissent avant que le capital soit trop engagé

Si Build-12 est mal fait :
- le Live-Light sera lancé sur des hypothèses fausses
- les coûts réels surprendront
- les moteurs seront jugés de manière erronée
- la production Light sera vulnérable

Donc :

> Build-12 doit être traité comme un **build bloquant de vérité de marché réel**, pas comme un simple “petit live”.

---

## Fin du document
