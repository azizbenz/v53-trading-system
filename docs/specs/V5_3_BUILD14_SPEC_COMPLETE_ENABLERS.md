# V5.3 — BUILD-14 SPEC
## Complete Enablers Protocol
### Spécification des briques d’extension vers la V5.3 Complete
### Quatorzième étape officielle du développement
### Sans code — prod-safe

---

# 0. Objet du document

Ce document couvre **Build-14** du plan officiel V5.3.

Build-14 a une mission unique :

> préparer l’ouverture future de la V5.3 Complete en ajoutant les **briques d’enrichissement strictement utiles**, sans casser la stabilité de la Light et sans confondre sophistication de recherche et valeur de production.

Les composants couverts ici sont :

1. `microstructure_enriched_layer`
2. `regime_enriched_layer`
3. `robust_covariance_layer`
4. `risk_contribution_monitor`
5. `effective_edge_diversity_enriched`

Build-14 **n’active pas encore** :
- le moteur C en production
- le moteur D en production
- le profil Complete

Il prépare le terrain pour pouvoir, plus tard, décider rationnellement si la Complete mérite d’exister.

---

# 1. Mission du Build-14

Le Build-14 existe pour répondre à une question stratégique :

> la V5.3 Light stable peut-elle être enrichie par des briques analytiques supplémentaires qui améliorent réellement la lecture du risque, de la corrélation, de la microstructure et de la diversité d’edge, sans détériorer la stabilité opérationnelle ?

En pratique, Build-14 doit permettre de tester, en environnement contrôlé :

- si la microstructure enrichie apporte un vrai gain
- si une lecture de régime plus riche aide réellement
- si une covariance robuste améliore le pilotage portefeuille
- si les contributions marginales au risque deviennent mieux visibles
- si le portefeuille a réellement plus d’un edge effectif

---

# 2. Ce que Build-14 n’est pas

Build-14 n’est pas :

- une activation implicite de la Complete
- une autorisation à coder C et D en live
- une excuse pour introduire des modules de prestige
- une relance du scope recherche sans garde-fous
- un abandon de la discipline Light

Build-14 est :

- une **phase d’enabling**
- une **phase de preuve d’utilité**
- une **phase d’analyse enrichie**
- une **phase d’intégration prudente**

---

# 3. Position de Build-14 dans le plan global

## Avant Build-14
Les conditions suivantes doivent être satisfaites :

- Build-1 à Build-13 validés
- Live-Light techniquement stable
- coûts réels suffisamment compris
- A/B compris économiquement
- portefeuille Light crédible
- UI / monitoring / rollback maîtrisés

## Après Build-14
Si Build-14 est validé, alors seulement :
- Build-15 : Moteur C
- Build-16 : Moteur D
- Build-17 : UI Complete + Live-Complete

---

# 4. Objectifs stratégiques de Build-14

Build-14 doit établir cinq vérités :

## 4.1 Vérité microstructure
Les signaux microstructure enrichis améliorent-ils réellement la lecture du contexte ou du coût, sans trop de bruit ni surcharge ?

## 4.2 Vérité régime
Un régime plus riche améliore-t-il la segmentation utile, sans sur-fit ni inflation des veto ?

## 4.3 Vérité covariance
Une covariance plus robuste améliore-t-elle la lecture portefeuille par rapport à la version Light ?

## 4.4 Vérité contribution risque
Le système gagne-t-il à voir quelles positions consomment réellement le risque marginal ?

## 4.5 Vérité diversité d’edge
Les moteurs et paires disponibles génèrent-ils une vraie diversification d’edge, ou seulement une illusion de pluralité ?

---

# 5. Préconditions obligatoires

Build-14 ne peut pas commencer si une des conditions suivantes n’est pas satisfaite :

- Live-Light techniquement fragile
- réconciliation encore instable
- coûts réels encore mal compris
- A/B non stabilisés
- portefeuille Light encore trop stérile
- alerting / UI / DTR insuffisants
- discipline de rollback non maîtrisée

---

# 6. Périmètre du Build-14

## 6.1 Profil actif
- **Light toujours actif**
- Complete non activé

## 6.2 Mode d’introduction
Les enablers doivent être introduits :
- d’abord en lecture / analyse
- ensuite en influence limitée / shadow
- jamais comme sources immédiates de veto hard en production

## 6.3 Composants concernés
- microstructure enrichie
- régime enrichi
- covariance robuste
- contribution marginale au risque
- diversité effective d’edge

## 6.4 Composants explicitement hors périmètre
- RL live
- POMDP live
- moteur C live
- moteur D live
- optimisation lourde non démontrée
- Complete profile live

---

# 7. Principe fondamental du Build-14

Toute brique Build-14 doit d’abord prouver trois choses :

1. **utilité économique ou de pilotage**
2. **stabilité technique**
3. **non-régression Light**

Si elle échoue sur l’un des trois axes, elle ne doit pas être promue.

---

# 8. Composant 1 — MICROSTRUCTURE_ENRICHED_LAYER

## 8.1 Mission

Introduire une lecture microstructure enrichie qui améliore :
- la qualité contextuelle des signaux
- la lecture du coût probable
- la détection d’environnements toxiques

sans transformer le système en pseudo-HFT.

## 8.2 Ce que cette brique doit apporter

- confirmation ou dégradation contextuelle plus fine
- meilleure lecture des coûts implicites
- meilleure détection de flux trompeurs
- meilleure qualité sur entrées de continuation ou de reversion

## 8.3 Ce qu’elle ne doit pas faire

- piloter seule les entrées
- imposer des veto hard non validés
- consommer un budget CPU disproportionné
- multiplier les features décoratives

## 8.4 Sous-composants recommandés

### 8.4.1 ofi_dynamic_layer
Rôle :
- Order Flow Imbalance dynamique

### 8.4.2 book_imbalance_enriched
Rôle :
- imbalance multi-niveaux plus robuste

### 8.4.3 microprice_context
Rôle :
- lecture du microprice et de son écart au mid

### 8.4.4 persistence_micro_filter
Rôle :
- éviter le bruit microstructure instantané

### 8.4.5 spoofing_suspicion_filter
Rôle :
- détecter un contexte carnet trompeur

## 8.5 Variables et formules utiles

Order Flow Imbalance :
\[
OFI_t = V_t^{buy} - V_t^{sell}
\]

OFI normalisé :
\[
OFI_t^{norm} = \frac{V_t^{buy}-V_t^{sell}}{V_t^{buy}+V_t^{sell}}
\]

Imbalance carnet :
\[
BI_t = \frac{Q_t^{bid}-Q_t^{ask}}{Q_t^{bid}+Q_t^{ask}}
\]

Microprice :
\[
MP_t = \frac{P_t^{ask}Q_t^{bid}+P_t^{bid}Q_t^{ask}}{Q_t^{bid}+Q_t^{ask}}
\]

Écart microprice / mid :
\[
\Delta MP_t = \frac{MP_t - Mid_t}{Mid_t}
\]

Agrégation persistante :
\[
DOFI_t = \sum_{u=0}^{U-1}\kappa^u OFI_{t-u}
\]

## 8.6 Conditions de validation

La microstructure enrichie est utile seulement si elle :

- améliore la sélection ou le coût
- réduit certains faux signaux
- n’augmente pas excessivement la stérilisation
- n’ajoute pas une latence nuisible

## 8.7 Dérives à éviter

- 20 features microstructure sans preuve d’utilité
- dépendance CPU trop forte
- utilisation en hard block trop tôt
- croyance que le carnet dit la vérité

---

# 9. Composant 2 — REGIME_ENRICHED_LAYER

## 9.1 Mission

Introduire une segmentation de régime plus riche que la Light, si et seulement si elle améliore réellement :
- la lecture du contexte
- la compatibilité A/B
- la préparation future de C/D

## 9.2 Ce que cette brique doit apporter

- meilleure séparation trend / range / stress / transition
- meilleur contexte pour A/B
- meilleure lecture des environnements où B est toxique
- meilleure préparation à C

## 9.3 Ce qu’elle ne doit pas faire

- réintroduire une inflation de veto
- multiplier les états sans gain
- devenir un moteur caché de sur-fit

## 9.4 Sous-composants recommandés

### 9.4.1 hmm_state_layer
Rôle :
- état latent enrichi si stable

### 9.4.2 regime_transition_monitor
Rôle :
- détecter transitions et ambiguïtés

### 9.4.3 regime_confidence_enriched
Rôle :
- confiance régime plus lisible

### 9.4.4 regime_penalty_mapper
Rôle :
- transformer le régime en pénalité graduelle, pas en veto automatique

## 9.5 Variables et formules utiles

États latents :
\[
z_t \in \{1,\dots,S\}
\]

Transitions :
\[
a_{mn} = \mathbb{P}(z_{t+1}=n \mid z_t=m)
\]

Filtrage :
\[
\mathbb{P}(z_t=s \mid y_{1:t})
\]

Espérance par régime :
\[
\mu_s = \mathbb{E}[r \mid régime=s]
\]

Variance par régime :
\[
\sigma_s^2 = \mathbb{V}[r \mid régime=s]
\]

Confiance régime :
\[
Conf_{reg} = \max_s \mathbb{P}(z_t=s \mid y_{1:t})
\]

## 9.6 Conditions de validation

La couche régime enrichie est utile seulement si elle :

- améliore la qualité d’arbitrage A/B
- réduit les reversions toxiques
- améliore la lecture des coûts / contextes
- n’augmente pas excessivement le hard block rate

## 9.7 Dérives à éviter

- trop d’états
- régimes trop instables
- sur-fit à quelques épisodes
- ambiguïté de régime transformée en refus systématique

---

# 10. Composant 3 — ROBUST_COVARIANCE_LAYER

## 10.1 Mission

Fournir une lecture plus robuste de la covariance portefeuille que la version simple Light, afin d’améliorer :
- la lecture du risque portefeuille
- l’allocation future
- la préparation du profil Complete

## 10.2 Ce que cette brique doit apporter

- une covariance moins bruitée
- moins de réactions à des corrélations accidentelles de petit échantillon
- une meilleure stabilité des contributions de risque
- une meilleure préparation au multi-moteurs / multi-paires enrichi

## 10.3 Ce qu’elle ne doit pas faire

- remplacer l’intuition économique simple si les données sont insuffisantes
- créer une illusion de précision
- être utilisée comme excuse pour complexifier l’allocation sans bénéfice

## 10.4 Sous-composants recommandés

### 10.4.1 empirical_covariance_builder
Rôle :
- covariance empirique de base

### 10.4.2 shrinkage_target_builder
Rôle :
- cible de shrinkage

### 10.4.3 ledoit_wolf_estimator
Rôle :
- covariance shrinkée plus robuste

### 10.4.4 covariance_drift_monitor
Rôle :
- dérive de structure de covariance

## 10.5 Variables et formules utiles

Covariance empirique :
\[
S = \frac{1}{T-1}\sum_{t=1}^{T}(r_t-\bar{r})(r_t-\bar{r})^\top
\]

Shrinkage :
\[
\Sigma_{LW} = \delta F + (1-\delta)S
\]

Cible diagonale :
\[
F = \operatorname{diag}(S)
\]

Variance portefeuille :
\[
Var(R_p)=w^\top \Sigma_{LW} w
\]

## 10.6 Conditions de validation

La covariance robuste est utile seulement si elle :

- stabilise la lecture portefeuille
- améliore la lisibilité du risque
- n’induit pas d’allocation aberrante
- n’est pas plus trompeuse que l’estimation simple

## 10.7 Dérives à éviter

- surestimer la précision de \(\Sigma_{LW}\)
- oublier les limites petit échantillon
- croire qu’une belle matrice = meilleur portefeuille

---

# 11. Composant 4 — RISK_CONTRIBUTION_MONITOR

## 11.1 Mission

Rendre visible quelles positions, paires ou moteurs consomment réellement le risque marginal du portefeuille.

## 11.2 Ce que cette brique doit apporter

- lecture de contribution marginale au risque
- détection des positions “petites mais dangereuses”
- meilleure lisibilité de la concentration réelle
- support futur aux arbitrages Complete

## 11.3 Ce qu’elle ne doit pas faire

- déclencher seule des modifications live
- se substituer aux caps simples
- complexifier la Light si elle n’apporte rien

## 11.4 Sous-composants recommandés

### 11.4.1 portfolio_variance_monitor
Rôle :
- suivre la variance portefeuille

### 11.4.2 marginal_risk_contribution_builder
Rôle :
- calculer la contribution marginale

### 11.4.3 total_risk_contribution_builder
Rôle :
- calculer la contribution totale

### 11.4.4 concentration_alert_mapper
Rôle :
- détecter les concentrations cachées

## 11.5 Variables et formules utiles

Variance portefeuille :
\[
Var(R_p)=w^\top\Sigma w
\]

Contribution marginale :
\[
MRC_j = \frac{(\Sigma w)_j}{\sqrt{w^\top\Sigma w}}
\]

Contribution totale :
\[
RC_j = w_j \cdot MRC_j
\]

Somme :
\[
\sum_j RC_j = \sqrt{w^\top\Sigma w}
\]

## 11.6 Conditions de validation

La lecture de contribution au risque est utile seulement si elle :

- révèle des concentrations invisibles autrement
- améliore la lecture opérateur
- aide à expliquer des arbitrages ou limites futures

## 11.7 Dérives à éviter

- sur-interpréter des contributions bruitées
- remplacer des caps simples par des métriques trop complexes
- afficher sans contexte opérateur

---

# 12. Composant 5 — EFFECTIVE_EDGE_DIVERSITY_ENRICHED

## 12.1 Mission

Évaluer si le système possède réellement plusieurs edges effectifs, ou seulement plusieurs noms pour un même risque.

## 12.2 Ce que cette brique doit apporter

- lecture du nombre effectif d’edges
- détection de faux multi-edge
- mesure de la diversification réelle des moteurs/paires
- support à la décision future d’introduire C/D

## 12.3 Ce qu’elle ne doit pas faire

- devenir une métrique abstraite sans impact
- sur-interpréter de petits échantillons
- servir de justification automatique à la Complete

## 12.4 Sous-composants recommandés

### 12.4.1 engine_correlation_matrix_builder
Rôle :
- matrice de corrélation inter-moteurs

### 12.4.2 pair_engine_joint_correlation_builder
Rôle :
- lecture moteur × paire

### 12.4.3 k_eff_estimator
Rôle :
- estimation du nombre effectif d’edges

### 12.4.4 redundancy_alert_mapper
Rôle :
- alerter sur la redondance excessive

## 12.5 Variables et formules utiles

Matrice de corrélation des moteurs :
\[
\mathcal{R}_{mot} = [\rho_{a,b}^{mot}]_{a,b=1}^{K}
\]

Diversification effective spectrale :
\[
K_{eff}^{spec} = \frac{(\operatorname{tr}\mathcal{R}_{mot})^2}{\operatorname{tr}(\mathcal{R}_{mot}^2)}
\]

Cas idéal :
\[
K_{eff}^{spec} \approx K
\]

Cas redondant :
\[
K_{eff}^{spec} \approx 1
\]

## 12.6 Conditions de validation

Cette brique est utile seulement si elle :

- éclaire réellement la redondance des moteurs / paires
- permet de préparer C/D sur une base factuelle
- améliore le pilotage de diversification

## 12.7 Dérives à éviter

- prendre \(K_{eff}\) comme vérité définitive
- oublier la faiblesse de l’échantillon
- utiliser une belle métrique pour justifier un moteur inutile

---

# 13. Mode d’introduction en production Light

## 13.1 Étape 1 — Lecture seule
Les briques Build-14 doivent d’abord exister en lecture seule :
- visibles au monitoring
- visibles à l’analyse
- sans impact direct sur les décisions live

## 13.2 Étape 2 — Influence limitée
Ensuite seulement, certaines briques peuvent influencer :
- une pénalité légère
- une meilleure lecture portefeuille
- une alerte enrichie

Mais pas :
- un hard block central
- une refonte du sizing live
- un changement brutal de logique A/B

## 13.3 Étape 3 — Préparation Complete
Si leur utilité est démontrée sans régression, elles deviennent candidates à Build-15/16/17.

---

# 14. Métriques obligatoires du Build-14

## 14.1 Microstructure enrichie
- coût CPU / latence induite
- amélioration éventuelle de sélection
- faux signaux évités
- drift des features
- fréquence d’activation utile

## 14.2 Régime enrichi
- stabilité des états
- taux de changements de régime
- impact sur pénalités
- impact sur A/B
- ambiguïtés détectées

## 14.3 Covariance robuste
- stabilité de \(\Sigma\)
- cohérence de la variance portefeuille
- drift de covariance
- lisibilité pour l’opérateur

## 14.4 Contribution au risque
- top contributeurs de risque
- changements de concentration
- positions faiblement notionnelles mais fortement risquées

## 14.5 Diversité effective d’edge
- \(K_{eff}\)
- corrélations moteur/moteur
- corrélations moteur/paire
- redondances dominantes

---

# 15. Formules de référence Build-14

## 15.1 Microstructure
\[
OFI_t = V_t^{buy} - V_t^{sell}
\]
\[
BI_t = \frac{Q_t^{bid}-Q_t^{ask}}{Q_t^{bid}+Q_t^{ask}}
\]
\[
MP_t = \frac{P_t^{ask}Q_t^{bid}+P_t^{bid}Q_t^{ask}}{Q_t^{bid}+Q_t^{ask}}
\]

## 15.2 Régime
\[
\mathbb{P}(z_t=s \mid y_{1:t})
\]
\[
\mu_s = \mathbb{E}[r \mid s]
\]
\[
\sigma_s^2 = \mathbb{V}[r \mid s]
\]

## 15.3 Covariance robuste
\[
\Sigma_{LW} = \delta F + (1-\delta)S
\]
\[
Var(R_p)=w^\top \Sigma_{LW} w
\]

## 15.4 Contribution au risque
\[
MRC_j = \frac{(\Sigma w)_j}{\sqrt{w^\top\Sigma w}}
\]
\[
RC_j = w_j \cdot MRC_j
\]

## 15.5 Diversité effective
\[
K_{eff}^{spec} = \frac{(\operatorname{tr}\mathcal{R})^2}{\operatorname{tr}(\mathcal{R}^2)}
\]

---

# 16. Critères de validation obligatoires

## 16.1 Critères généraux
Chaque enabler doit prouver :

- utilité
- stabilité
- coût de complexité acceptable
- non-régression Light

## 16.2 Critères microstructure
Valider seulement si :
- utile à la sélection / coût
- pas trop bruyant
- surcharge acceptable

## 16.3 Critères régime
Valider seulement si :
- segmentation stable
- amélioration décisionnelle claire
- pas d’inflation des refus

## 16.4 Critères covariance
Valider seulement si :
- lecture portefeuille plus robuste
- pas de faux sentiment de précision

## 16.5 Critères contribution risque
Valider seulement si :
- la métrique révèle des concentrations non visibles autrement

## 16.6 Critères diversité effective
Valider seulement si :
- la lecture de redondance aide réellement à juger la suite du programme

---

# 17. Conditions GO vers Build-15 / Build-16

Le passage vers les moteurs C et D n’est envisageable que si Build-14 montre :

- microstructure enrichie utile ou au moins non nuisible
- régime enrichi utile ou au moins non nuisible
- covariance robuste lisible et stable
- meilleure lecture du risque marginal
- \(K_{eff}\) suffisamment informatif pour juger la redondance
- aucune régression majeure de la Light

---

# 18. Conditions NO-GO absolues

Passage vers Build-15/16 interdit si :

- un enabler casse la stabilité Light
- surcharge CPU/latence significative
- inflation de veto / pénalités non souhaitée
- covariance robuste trop instable
- métriques trop bruitées pour être crédibles
- \(K_{eff}\) ou risk contributions non interprétables
- l’équipe ne sait pas expliquer ce que les enablers ajoutent réellement

---

# 19. Table des échecs typiques du Build-14

| Échec | Symptôme | Interprétation | Action |
|---|---|---|---|
| Faux gain microstructure | beaucoup de features, peu de gain | sophistication décorative | réduire drastiquement |
| Faux gain régime | plus d’états, pas plus de lisibilité | sur-fit | simplifier |
| Faux gain covariance | belle matrice, décisions pires | précision illusoire | revenir simple |
| Faux gain risk contribution | beaucoup de chiffres, pas d’action | monitoring non actionnable | reformuler |
| Faux gain K_eff | métrique jolie mais échantillon faible | signal non mûr | garder en recherche |

---

# 20. Artefacts obligatoires de fin de Build-14

À la fin du Build-14, il faut produire :

1. **rapport microstructure enrichie**
2. **rapport régime enrichi**
3. **rapport covariance robuste**
4. **rapport contribution au risque**
5. **rapport diversité effective d’edge**
6. **rapport non-régression Light**
7. **verdict : préparer C / préparer D / différer Complete**

---

# 21. Contenu minimum du rapport Build-14

Le rapport final doit répondre explicitement à :

- la microstructure enrichie sert-elle réellement ?
- le régime enrichi aide-t-il ou complique-t-il ?
- la covariance robuste améliore-t-elle la lecture portefeuille ?
- les contributions de risque révèlent-elles quelque chose d’utile ?
- le système a-t-il réellement plus d’un edge effectif ?
- C et D ont-ils une base factuelle pour exister plus tard ?
- qu’est-ce qui doit être gardé, différé ou abandonné ?

---

# 22. Tests obligatoires Build-14

## 22.1 Tests de non-régression
- aucune casse Light
- aucune régression UI/monitoring
- aucune augmentation critique de backlog / latence

## 22.2 Tests microstructure
- features calculables
- coûts CPU visibles
- persistance correcte
- signaux bruités détectables

## 22.3 Tests régime
- états calculables
- transitions visibles
- pénalités enrichies traçables

## 22.4 Tests covariance
- matrice calculable
- shrinkage stable
- variance portefeuille cohérente

## 22.5 Tests contribution / K_eff
- top risk contributors visibles
- corrélations moteur/moteur calculables
- \(K_{eff}\) calculable et affichable

---

# 23. Dérives globales Build-14 à ne pas faire

- confondre build d’enabling et activation Complete
- garder des briques parce qu’elles sont élégantes
- complexifier le système avant d’avoir prouvé l’utilité
- utiliser les enablers pour relancer des veto cachés
- traiter une métrique bruitée comme une vérité dure
- oublier que la Light doit rester la base saine du programme

---

# 24. Verdict final Build-14

Build-14 est la phase où l’on décide si la V5.3 a le droit de s’enrichir sans se perdre.

Si Build-14 est bien fait :
- la Light reste stable
- les enablers utiles émergent
- la préparation de C et D repose sur des faits
- la Complete peut devenir une extension rationnelle

Si Build-14 est mal fait :
- la Light se complexifie sans gain
- la future Complete sera construite sur des illusions
- la discipline prod-safe se dégrade

Donc :

> Build-14 doit être traité comme un **build bloquant d’enrichissement sous contrôle**, pas comme une simple phase de recherche additionnelle.

---

## Fin du document
