# V5.3 — BUILD-17 SPEC
## UI Complete + Live-Complete Protocol
### Spécification de l’interface Complete et du protocole d’activation 12 paires / 4 moteurs
### Dix-septième étape officielle du développement
### Sans code — prod-safe

---

# 0. Objet du document

Ce document couvre **Build-17** du plan officiel V5.3.

Build-17 a une mission unique :

> définir la **UI Complete** et le protocole officiel de **Live-Complete**,
> c’est-à-dire l’extension gouvernée du rollout de la même architecture complète
> vers sa cible 12 paires / 4 moteurs, sans casser la stabilité, la discipline
> et la lisibilité acquises en LIGHT.

Build-17 n’est pas une simple “version plus grande” de la Light.  
C’est une phase qui doit démontrer que l’architecture complète :

- apporte une valeur réelle
- reste gouvernable
- reste compréhensible
- ne dégrade pas excessivement la CE
- n’introduit pas une complexité incontrôlable

---

# 1. Mission de Build-17

Build-17 existe pour répondre à une question centrale :

> la V5.3 peut-elle etendre de manière gouvernée son rollout de **LIGHT discipliné**
> vers **COMPLETE élargi** sans transformer une base saine en système opaque,
> trop corrélé, trop coûteux ou trop lourd à opérer ?

Il faut donc formaliser simultanément :

- une **UI Complete** capable de montrer 12 paires, 4 moteurs et les nouvelles couches enrichies
- un protocole **Live-Complete** avec conditions d’activation strictes
- des règles de montée en charge, de dégradation et de rollback
- des critères de réussite qui ne confondent pas fréquence brute et amélioration réelle

---

# 2. Ce que Build-17 n’est pas

Build-17 n’est pas :

- une permission d’activer tout d’un coup
- une preuve automatique que la Complete est meilleure
- une excuse pour relâcher la discipline de la Light
- un cockpit permissif pour expérimenter en live
- une validation implicite de C et D sans preuve marginale

Build-17 est :

- une **phase de formalisation finale**
- une **phase d’extension sous contrôle**
- une **phase de gouvernance renforcée**
- une **phase de preuve d’utilité systémique**

## Relation avec le Shadow complet

La UI Complete doit être préparée pour :

- **visualiser les résultats du Shadow complet** (30 jours avec A/B/C/D + Build-14 à 100%)
- **montrer les verdicts individuels** sur chaque moteur (A/B/C/D) et chaque enabler Build-14
- **afficher la contribution des enablers Build-14** : microstructure, régime, covariance, risk contribution, edge diversity
- **afficher les Hard States** de chaque composant (`SHADOW_ENABLED`, `SHADOW_VALIDATED`, `DORMANT`, `PROMOTED`)
- **soutenir la décision de promotion / non-promotion** avec données comparatives
- **montrer les risques** de duplication, churn, coût, concentration entre moteurs

---

# 3. Position de Build-17 dans le plan global

## Avant Build-17
Les conditions suivantes doivent être satisfaites :

- Build-1 à Build-13 validés
- Build-14 validé ou au moins suffisamment analysé
- Build-15 (Moteur C) validé
- Build-16 (Moteur D) validé
- Light techniquement stable
- Light économiquement crédible
- coûts réels suffisamment compris
- UI Light / monitoring / rollback maîtrisés

## Après Build-17
Si Build-17 est validé, alors :
- la V5.3 COMPLETE peut entrer dans une trajectoire de production contrôlée
- la gouvernance complète du système est formalisée
- le projet atteint son périmètre cible

---

# 4. Objectifs stratégiques de Build-17

Build-17 doit établir six vérités :

## 4.1 Vérité de gouvernance
L’architecture Complete peut-elle être pilotée sans perdre la maîtrise opératoire ?

## 4.2 Vérité de lisibilité
L’UI Complete montre-t-elle la complexité utile sans noyer l’opérateur ?

## 4.3 Vérité économique
La Complete améliore-t-elle réellement fréquence utile, diversité d’edge, CE ou robustesse — et pas seulement le nombre de trades ?

## 4.4 Vérité portefeuille
Le portefeuille 12 paires / 4 moteurs reste-t-il discipliné face à la corrélation, au facteur BTC et à la concentration cachée ?

## 4.5 Vérité moteur
C et D apportent-ils une vraie valeur marginale au-delà de A et B ?

## 4.6 Vérité opérationnelle
Le système sait-il encore se dégrader, se stopper et revenir en arrière proprement ?

---

# 5. Préconditions obligatoires

Build-17 ne peut pas commencer si une des conditions suivantes n’est pas satisfaite :

- Live-Light encore fragile
- C non justifié économiquement
- D non justifié marginalement
- Complete Enablers non compris
- \(K_{eff}\) non interprétable
- risk contribution encore trop floue
- UI Light déjà insuffisante
- règles DEGRADED / HALTED / rollback non éprouvées

---

# 6. Périmètre du Build-17

## 6.1 Profil cible
- **Complete**
- 12 paires maximum
- moteurs A, B, C, D

## 6.2 Composants inclus
- UI Complete
- dashboards enrichis
- protocoles Live-Complete
- règles de montée en charge
- règles de dégradation
- règles de rollback
- règles de readiness continue

## 6.3 Composants explicitement hors périmètre
- RL live
- POMDP live
- overrides non journalisés
- auto-activation d’éléments non validés
- optimisation continue non gouvernée

---

# 7. Différence fondamentale Light vs Complete

## 7.1 Light
- 6 paires
- architecture complète visible et supervisable
- coeur runtime attendu : A/B
- C/D armables ou activables seulement sous gates spécifiques et bornes strictes
- priorité à la stabilité et à la lisibilité gouvernée
- objectif : produire un rollout rentable crédible

## 7.2 Complete
- 12 paires
- 4 moteurs activables sous gouvernance
- analytics enrichis
- plus de variété de contextes
- plus de corrélation potentielle
- plus de besoins d’arbitrage
- plus de risques d’illusion de diversification

## 7.3 Règle critique

La Complete doit être jugée sur :
- son **gain marginal**
- sa **stabilité marginale**
- son **coût marginal**
- sa **diversité effective marginale**

et non sur son apparente sophistication.

---

# 8. UI COMPLETE — Mission

La UI Complete doit permettre de superviser un système plus riche sans le rendre moins gouvernable.

Elle doit :

- montrer l’état global du système
- rendre visible la pluralité de moteurs et de paires
- exposer les budgets critiques
- exposer la corrélation, le facteur BTC, les contributions au risque
- rendre visibles les nouvelles briques enrichies
- permettre uniquement les actions compatibles avec la Complete validée

Elle ne doit jamais :

- devenir un cockpit de bricolage
- masquer les risques de corrélation
- autoriser des activations non validées
- noyer les alertes critiques dans trop d’informations

---

# 9. Architecture de la UI Complete

## 9.1 Écrans canoniques

1. **Overview portefeuille Complete**
2. **Profils & état de déploiement**
3. **Paires (12 paires)**
4. **Moteurs (A/B/C/D)**
5. **Risque & exposition enrichis**
6. **Coûts & exécution enrichis**
7. **Qualité data & infra**
8. **Meta / DTR / CRA / edge**
9. **Covariance & risk contributions**
10. **Diversité effective d’edge**
11. **Logs & événements**
12. **Administration contrôlée Complete**

## 9.2 Principe de hiérarchie

Même en Complete, l’opérateur doit pouvoir répondre en quelques secondes à :
- le système est-il sain ?
- le capital est-il en danger ?
- quel moteur ou quelle paire dérive ?
- le portefeuille est-il trop corrélé ?
- les nouveaux moteurs C/D apportent-ils vraiment quelque chose ?
- faut-il passer en DEGRADED ou HALTED ?

---

# 10. Écran 1 — OVERVIEW PORTEFEUILLE COMPLETE

## 10.1 Mission
Donner une vue instantanée du système complet.

## 10.2 Blocs obligatoires
- profil actif : Complete
- état de déploiement
- nombre de paires actives
- moteurs actifs
- capital total
- capital engagé
- capital libre
- PnL réel
- CE portefeuille
- drawdown
- beta BTC
- cluster dominant
- \(K_{eff}\)
- alertes critiques

## 10.3 Formules utiles
\[
GrossExp = \sum_i x_i
\]
\[
LossBudget = \sum_i L_i
\]
\[
CE_{port} = \frac{\sum_i PnL_i}{\sum_i x_i h_i}
\]
\[
\Beta_{port} = \sum_j w_j \beta_j
\]
\[
K_{eff}^{spec} = \frac{(\operatorname{tr}\mathcal{R})^2}{\operatorname{tr}(\mathcal{R}^2)}
\]

---

# 11. Écran 2 — PROFILS & ÉTAT DE DÉPLOIEMENT

## 11.1 États officiels
- LIVE-LIGHT
- LIVE-COMPLETE
- DEGRADED
- HALTED

## 11.2 Actions autorisées
- charger Complete si et seulement si les gates sont passés
- repasser vers Light si rollback requis
- passer en HALTED
- constater un DEGRADED automatique ou opérateur

## 11.3 Actions interdites
- profil custom
- activation partielle non validée de Complete
- passer Complete sans C/D validés si la config l’exige
- contourner les gates de profil

---

# 12. Écran 3 — PAIRES (12 paires)

## 12.1 Mission
Superviser 12 paires sans perdre la lisibilité opérationnelle.

## 12.2 Colonnes minimales
- paire
- classe A/B/C
- état actif/suspendu
- pair health
- coût moyen
- coût p90
- CE
- fréquence utile
- moteur(s) actifs
- cluster
- beta paire
- raison de suspension

## 12.3 Actions autorisées
- suspendre paire
- demander reprise
- filtrer par cluster / moteur / état

## 12.4 Interdits
- activer une paire non validée
- dépasser le périmètre Complete validé
- réactiver une paire critique sans justification

---

# 13. Écran 4 — MOTEURS (A/B/C/D)

## 13.1 Mission
Comparer A/B/C/D non par prestige, mais par valeur réelle.

## 13.2 Colonnes minimales
- moteur
- actif/suspendu
- fréquence utile
- rendement net
- coût moyen
- coût p90
- CE
- Sharpe par trade
- drawdown
- cluster d’exposition dominant
- paires actives
- raison de suspension

## 13.3 Métriques critiques
- non-duplication A/C
- valeur marginale D
- stérilisation C/D
- contribution \(K_{eff}\)
- coût marginal C/D

## 13.4 Interdits
- activer un moteur non validé
- modifier caps moteur par UI
- masquer les coûts ou la stérilisation

---

# 14. Écran 5 — RISQUE & EXPOSITION ENRICHIS

## 14.1 Mission
Rendre visible le vrai risque portefeuille Complete.

## 14.2 Blocs obligatoires
- GrossExp
- LossBudget
- beta BTC
- cluster pressure
- variance portefeuille
- top risk contributors
- RC par moteur
- RC par paire
- breaches
- positions Tier 3 si autorisées

## 14.3 Formules utiles
\[
Var(R_p)=w^\top \Sigma w
\]
\[
MRC_j = \frac{(\Sigma w)_j}{\sqrt{w^\top\Sigma w}}
\]
\[
RC_j = w_j \cdot MRC_j
\]

## 14.4 Interdits
- pilotage au notional seul
- cacher les positions “petites mais dangereuses”
- masquer les clusters dominants

---

# 15. Écran 6 — COÛTS & EXÉCUTION ENRICHIS

## 15.1 Mission
Voir si la Complete paie trop cher son expansion.

## 15.2 Blocs obligatoires
- coût par moteur
- coût par paire
- coût C vs A
- coût D vs alternative “ne rien faire”
- ELW moyen / p90
- partial fill rate
- reconciliation alerts
- cost drift vs Light baseline

## 15.3 Formules utiles
\[
ELW_i = \frac{|P_i^{exec} - Mid_i|}{Mid_i}
\]
\[
c_i = f_i + c_i^{impl} + AS_i + PF_i
\]
\[
CostDrift = \frac{1}{N}\sum_i (c_i^{real} - c_i^{ref})
\]

---

# 16. Écran 7 — QUALITÉ DATA & INFRA

## 16.1 Mission
S’assurer que la Complete ne sature pas l’architecture.

## 16.2 Blocs obligatoires
- reconnects
- queue usage
- backlog
- stale rate
- pair health transitions
- DTR loss
- log loss
- CPU/RAM/I/O
- latence end-to-end

## 16.3 Formules utiles
\[
\rho_q = \frac{\lambda}{\mu_s}
\]
\[
W_q = \frac{\lambda}{\mu_s(\mu_s-\lambda)}
\]

## 16.4 Interdits
- cacher une surcharge pour “protéger le dashboard”
- regarder CPU seul sans queues
- ignorer DTR loss

---

# 17. Écran 8 — META / DTR / CRA / EDGE

## 17.1 Mission
Superviser la causalité et la qualité économique en Complete.

## 17.2 Blocs obligatoires
- DTR coverage
- hard block rate
- ranking rejection rate
- CRA alerts
- phantom trades
- break-even par moteur/pair
- edge status prudent
- drift edge par moteur

## 17.3 Formules utiles
\[
SterilRate = \frac{\sum_i \mathbf{1}_{CE_i < CE_{min}}\mathbf{1}_{A_i=1}}{\sum_i A_i}
\]
\[
\hat{\mu} = \frac{1}{N}\sum_i r_i
\]
\[
SE(\hat{\mu}) = \frac{\hat{\sigma}}{\sqrt{N}}
\]

---

# 18. Écran 9 — COVARIANCE & RISK CONTRIBUTIONS

## 18.1 Mission
Rendre visible la structure portefeuille enrichie.

## 18.2 Blocs obligatoires
- matrice de covariance / corrélation
- top corrélations
- top risk contributors
- risque marginal par paire
- risque marginal par moteur
- drift covariance

## 18.3 Formules utiles
\[
\Sigma_{LW} = \delta F + (1-\delta)S
\]
\[
MRC_j = \frac{(\Sigma w)_j}{\sqrt{w^\top\Sigma w}}
\]
\[
RC_j = w_j \cdot MRC_j
\]

---

# 19. Écran 10 — DIVERSITÉ EFFECTIVE D’EDGE

## 19.1 Mission
Montrer si la Complete ajoute de vrais edges ou seulement des redondances.

## 19.2 Blocs obligatoires
- corrélations A/B/C/D
- corrélations moteur × paire
- \(K_{eff}\)
- redondance dominante
- contribution marginale de C
- contribution marginale de D

## 19.3 Formules utiles
\[
K_{eff}^{spec} = \frac{(\operatorname{tr}\mathcal{R})^2}{\operatorname{tr}(\mathcal{R}^2)}
\]

---

# 20. Écran 11 — LOGS & ÉVÉNEMENTS

## 20.1 Mission
Centraliser les événements critiques de la Complete.

## 20.2 Catégories
- infra
- data
- risk
- execution
- portefeuille
- moteur
- paire
- opérateur
- alertes

## 20.3 Interdits
- logs introuvables
- absence de lien entre événements
- pas de corrélation par trade/run/session

---

# 21. Écran 12 — ADMINISTRATION CONTRÔLÉE COMPLETE

## 21.1 Actions possibles
- suspendre / reprendre paire
- suspendre / reprendre moteur
- passer DEGRADED
- passer HALTED
- rollback vers Light si prévu
- consulter gates Complete

## 21.2 Actions interdites
- profil custom
- activation d’un moteur non validé
- modification caps de risque
- injection config non versionnée
- bypass hard blockers

## 21.3 Journalisation obligatoire
- utilisateur
- timestamp
- ancienne valeur
- nouvelle valeur
- raison
- référence de changement

---

# 22. Politique de montée en charge Complete

## 22.1 Principe cardinal

La Complete ne démarre pas avec 12 paires et 4 moteurs à intensité maximale.

Elle doit suivre une montée prudente par :
- paliers de paires
- paliers de tailles
- paliers de capital
- paliers de charge opératoire

## 22.2 Règle générale
La montée en charge Live-Complete se fait **après Shadow Complete validé**, par étapes documentées, par exemple :

1. 6 paires / UI Complete active / seuls les composants déjà `SHADOW_VALIDATED` sont autorisés en live
2. 8–9 paires / mêmes composants validés / budgets et monitoring renforcés
3. 10–12 paires / extension prudente des paires / aucune promotion implicite de composant supplémentaire
4. 12 paires / Live-Complete contrôlé / seuls les composants explicitement `PROMOTED` restent actifs en live

L’ordre exact dépend des validations précédentes.

Les paliers de Build-17 portent sur le rollout live des composants déjà jugés après Shadow ; ils ne recréent pas une activation Shadow partielle de A/B/C/D ou de Build-14.

## 22.3 Interdictions
- activer 12 paires + 4 moteurs d’un seul coup
- augmenter les tailles pendant l’activation initiale
- mélanger activation de paires et hausse de taille sans séquencement

---

# 23. Protocole Live-Complete

## 23.1 Mission
Valider la production complète sur :
- diversité réelle
- stabilité technique
- coûts réels
- gouvernance opérateur
- apport marginal de C/D

## 23.2 Conditions de départ
- Light stable
- C validé
- D validé
- enablers compris
- UI Complete prête
- rollback vers Light possible

## 23.3 Questions de vérité
- la Complete améliore-t-elle le portefeuille ?
- les coûts marginaux sont-ils soutenables ?
- la corrélation cachée est-elle sous contrôle ?
- l’opérateur reste-t-il capable de comprendre le système ?

---

# 24. Métriques obligatoires du Live-Complete

## 24.1 Portefeuille
- capital total
- capital engagé
- capital libre
- GrossExp
- LossBudget
- beta BTC
- cluster dominant
- variance portefeuille
- CE portefeuille
- drawdown Complete

## 24.2 Moteurs
- fréquence utile A/B/C/D
- rendement net A/B/C/D
- coût moyen / p90 A/B/C/D
- CE A/B/C/D
- drawdown A/B/C/D
- stérilisation A/B/C/D
- non-duplication A/C
- valeur marginale D

## 24.3 Paires
- état
- pair health
- coût moyen / p90
- CE
- fréquence utile
- cluster
- moteur(s) actifs
- suspensions/reprises

## 24.4 Exécution / réconciliation
- ACK rate
- FullFillRate
- PartialFillRate
- RejectRate
- CancelRate
- ELW moyen / p90
- DivRate
- recovery count
- cost drift vs Light

## 24.5 Data / infra
- reconnects
- queue usage
- backlog
- stale rate
- DTRLossRate
- log loss rate
- CPU/RAM/I/O
- latence end-to-end

## 24.6 Meta / diversification
- DTR coverage
- CRA alerts
- break-even par moteur/pair
- edge status
- \(K_{eff}\)
- top risk contributors
- drift covariance

---

# 25. Formules de référence Live-Complete

## 25.1 Rendement net réel
\[
r_i^{real} = g_i^{real} - c_i^{real}
\]

## 25.2 Capital efficiency réelle
\[
CE^{real} = \frac{\sum_i PnL_i^{real}}{\sum_i x_i h_i}
\]

## 25.3 Variance portefeuille
\[
Var(R_p)=w^\top \Sigma w
\]

## 25.4 Contribution marginale au risque
\[
MRC_j = \frac{(\Sigma w)_j}{\sqrt{w^\top\Sigma w}}
\]

## 25.5 Diversité effective
\[
K_{eff}^{spec} = \frac{(\operatorname{tr}\mathcal{R})^2}{\operatorname{tr}(\mathcal{R}^2)}
\]

## 25.6 Gain marginal de la Complete
\[
\Delta CE_{port}^{Complete} = CE_{port}^{A,B,C,D} - CE_{port}^{A,B}
\]

## 25.7 Drift coût vs Light
\[
CostDrift^{Complete/Light} = \frac{1}{N}\sum_i (c_i^{Complete} - c_i^{LightRef})
\]

---

# 26. Critères de validation obligatoires

## 26.1 Critères techniques
La Complete est techniquement valide si :
- backlog maîtrisé
- queues maîtrisées
- DTR loss négligeable
- pair health stable
- réconciliation fiable
- UI Complete fluide et lisible

## 26.2 Critères économiques
La Complete est économiquement valide si :
- CE portefeuille ne se dégrade pas excessivement
- C apporte un gain réel ou une fréquence utile nette
- D apporte une vraie valeur marginale
- les coûts additionnels restent défendables
- la stérilisation n’explose pas

## 26.3 Critères portefeuille
La Complete est portefeuille-valide si :
- beta BTC maîtrisé
- clusters maîtrisés
- contributions de risque lisibles
- diversification effective non illusoire
- capital alloué de façon productive

## 26.4 Critères opératoires
La Complete est opératoirement valide si :
- l’opérateur peut comprendre les dashboards
- alerting actionnable
- procédures DEGRADED / HALTED / rollback fonctionnent
- aucune dépendance à un expert unique non remplaçable

---

# 27. Conditions GO pour maintenir Live-Complete

Le Live-Complete peut être poursuivi si :
- la stabilité technique tient
- la CE portefeuille reste crédible
- C prouve une vraie utilité
- D prouve une vraie utilité marginale
- \(K_{eff}\) et la contribution au risque apportent une lecture utile
- l’opérateur garde la maîtrise
- les coûts marginaux restent défendables

---

# 28. Conditions de passage en DEGRADED (Complete)

Passage en DEGRADED recommandé ou obligatoire si :
- un moteur C ou D devient trop coûteux
- une famille de paires devient instable
- le portefeuille devient trop corrélé
- un enabler enrichi devient trop bruité ou trompeur
- la charge infra augmente sans être encore critique

Exemples d’actions DEGRADED :
- suspendre C
- suspendre D
- revenir à 8–9 paires
- réduire les tailles
- revenir à A+B seulement
- désactiver un enabler enrichi en influence active

---

# 29. Conditions de HALTED (Complete)

HALTED obligatoire si :
- divergence critique de réconciliation
- perte de contrôle d’état portefeuille
- DTR loss significatif
- surcharge infra critique
- budgets risque réellement menacés
- UI/monitoring ne permettent plus une supervision sûre
- rollback vers Light nécessaire

HALTED recommandé si :
- coûts marginaux Complete deviennent clairement destructeurs
- C ou D dégradent fortement la CE
- la Complete ajoute surtout du bruit et de la corrélation

---

# 30. Politique de rollback Complete → Light

## 30.1 Mission
Permettre un retour vers un état plus simple et plus sûr.

## 30.2 Formes de rollback
- Complete → A+B seulement
- 12 paires → 6 paires
- UI Complete → UI Light
- désactivation des enablers influents
- retour à Live-Light ou HALTED

## 30.3 Règle
Le rollback doit être :
- prévu
- rapide
- journalisé
- non honteux
- déclenché sur critères, pas sur ego

---

# 31. Conditions de réussite globale de la Complete

La Complete n’est considérée réussie que si elle apporte **au moins un** des bénéfices suivants, sans trop dégrader le reste :

- meilleure fréquence utile
- meilleure CE portefeuille
- meilleure diversification effective
- meilleure robustesse portefeuille
- meilleure exploitation de contextes jusqu’ici non couverts

Et surtout si elle n’introduit pas :
- une surcharge opératoire excessive
- une opacité excessive
- une corrélation cachée plus forte
- une inflation de coûts destructrice

---

# 32. Conditions d’échec de la Complete

La Complete doit être considérée comme non validée si :
- elle n’améliore que la fréquence brute
- elle baisse trop la CE portefeuille
- C duplique A
- D ajoute surtout de la concentration
- \(K_{eff}\) n’augmente pas réellement
- les coûts marginaux explosent
- l’opérateur perd la lisibilité du système
- la Light apparaissait en réalité plus robuste et plus rentable

---

# 33. Table des échecs typiques du Build-17

| Échec | Symptôme | Interprétation | Action |
|---|---|---|---|
| Faux gain Complete | plus de trades, CE en baisse | fréquence brute sans valeur | rollback vers Light |
| Faux moteur C | C ressemble à A | redondance stratégique | suspendre C |
| Faux moteur D | D augmente la concentration | valeur marginale négative | suspendre D |
| Faux gain UI | plus d’écrans, moins de lisibilité | complexité non gouvernée | simplifier UI |
| Faux gain diversification | 12 paires mais beta BTC inchangée | diversification illusoire | revoir clusters / sélection |
| Faux gain analytics | beaucoup de métriques, peu d’action | surcharge cognitive | réduire dashboards |

---

# 34. Artefacts obligatoires de fin de Build-17

À la fin d’une fenêtre d’observation Complete, il faut produire :

1. **rapport UI Complete**
2. **rapport stabilité technique Complete**
3. **rapport coûts marginaux Complete**
4. **rapport moteurs C/D**
5. **rapport portefeuille 12 paires / 4 moteurs**
6. **rapport corrélation / covariance / risk contributions**
7. **rapport diversité effective d’edge**
8. **rapport rollback / degraded / halted**
9. **verdict final : maintenir Complete / limiter Complete / revenir Light**

---

# 35. Contenu minimum du rapport Build-17

Le rapport final doit répondre explicitement à :

- la UI Complete reste-t-elle gouvernable ?
- la Complete améliore-t-elle réellement le portefeuille ?
- C a-t-il une valeur propre ?
- D a-t-il une valeur marginale propre ?
- les coûts additionnels sont-ils soutenables ?
- la corrélation cachée reste-t-elle maîtrisée ?
- la Light était-elle en fait préférable ?
- faut-il maintenir, limiter ou annuler la Complete ?

---

# 36. Tests obligatoires Build-17

## 36.1 Tests UI Complete
- écrans construits
- alertes critiques visibles
- actions autorisées / interdites respectées
- UI non contournable
- rollback vers Light visible

## 36.2 Tests Complete profile
- 12 paires max respectées
- A/B/C/D respectés
- impossible d’activer au-delà du profil
- passage DEGRADED/HALTED possible

## 36.3 Tests économiques
- CE portefeuille Complete visible
- coûts marginaux visibles
- break-even moteur/pair visible
- contribution marginale C/D visible

## 36.4 Tests portefeuille
- beta BTC visible
- cluster pressure visible
- risk contributions visibles
- \(K_{eff}\) visible
- arbitrages enrichis traçables

## 36.5 Tests rollback
- Complete → Light possible
- suspension C possible
- suspension D possible
- réduction 12 → 6 paires possible
- journalisation complète

---

# 37. Dérives globales Build-17 à ne pas faire

- activer tout trop tôt
- juger la Complete au seul nombre de trades
- préférer la sophistication à la CE
- masquer la redondance de C/D
- laisser l’UI devenir un cockpit d’expérimentation libre
- refuser un rollback par orgueil
- oublier que la meilleure version finale peut rester proche de la Light enrichie

---

# 38. Verdict final Build-17

Build-17 est la dernière épreuve de maturité de la V5.3.

Si Build-17 est bien fait :
- la Complete devient une extension rationnelle et gouvernable
- les 12 paires / 4 moteurs restent lisibles
- la diversification réelle peut augmenter
- l’opérateur garde la maîtrise
- la V5.3 atteint son périmètre cible sans trahir sa discipline prod-safe

Si Build-17 est mal fait :
- la Complete deviendra un système opaque, trop coûteux, trop corrélé ou trop lourd
- la Light apparaîtra rétrospectivement comme la vraie bonne version
- le projet gagnera en complexité et perdra en vérité

Donc :

> Build-17 doit être traité comme un **build bloquant de gouvernance finale de la Complete**, pas comme une simple couche d’interface supplémentaire.

---

## Fin du document
