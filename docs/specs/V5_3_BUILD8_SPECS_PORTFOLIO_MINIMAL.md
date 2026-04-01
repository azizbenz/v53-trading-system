# V5.3 — BUILD-8 SPECS MODULES
## Portfolio Minimal Pack
### Specs détaillées module par module
### Huitième étape officielle du développement
### Sans code — prod-safe

---

# 0. Objet du document

Ce document couvre **Build-8** du plan officiel V5.3.

Build-8 a une mission unique :

> transformer les opportunités survivantes des moteurs A et B en un **portefeuille Light cohérent**, discipliné, borné par les budgets, priorisé économiquement, et non une simple addition de trades “bons individuellement”.

Les modules couverts ici sont :

1. `opportunity_selector`
2. `allocation_router`

Build-8 ne cherche pas encore à construire la sophistication complète du portefeuille V5.3 Complete.  
Il doit construire la **forme minimale rentable et robuste** du portefeuille Light.

---

# 1. Principes Build-8

## 1.1 Objectif stratégique

Jusqu’au Build-7, on sait produire :
- de la donnée fiable
- une exécution mesurable
- un risk backbone
- un scoring backbone
- deux moteurs A et B

Mais cela ne suffit pas.

Le portefeuille peut encore échouer si :

- il prend trop de positions en même temps
- il privilégie les opportunités au score élevé mais à faible CE
- il surconsomme les budgets corrélés
- il alloue trop à une même famille de risque
- il ne sait pas arbitrer entre A et B
- il ignore le coût d’opportunité du capital

Build-8 existe pour résoudre cela.

## 1.2 Position dans l’architecture

Build-8 est :
- **obligatoire en Light**
- **obligatoire en Complete**
- **P0**
- la première vraie couche de portefeuille
- la couche qui transforme des signaux en capital alloué

## 1.3 Critère de réussite

Build-8 est réussi si :

- plusieurs opportunités simultanées peuvent être comparées proprement
- les budgets portefeuille sont respectés
- les opportunités les plus rentables économiquement sont favorisées
- la corrélation et le facteur BTC sont pris en compte
- A et B coexistent sans chaos
- le capital libre et le capital engagé restent lisibles

## 1.4 Critère d’échec

Build-8 échoue si :

- le portefeuille choisit le score brut le plus élevé sans contexte
- les opportunités sélectionnées sont trop corrélées
- l’allocation ignore le coût attendu
- A écrase toujours B ou inversement sans logique économique
- plusieurs petits trades contournent les caps de risque
- le système ne peut pas expliquer pourquoi un trade a gagné une place contre un autre

---

# 2. Vocabulaire officiel Build-8

## 2.1 Opportunité
Signal candidat déjà passé par :
- score brut
- pénalités
- hard blockers

et pouvant être classé par le portefeuille.

## 2.2 Sélection
Décision de garder ou rejeter une opportunité parmi d’autres.

## 2.3 Allocation
Décision du montant de capital à engager sur une opportunité sélectionnée.

## 2.4 Coût d’opportunité du capital
Valeur perdue lorsqu’un capital est immobilisé sur un trade moins intéressant qu’un autre.

## 2.5 Portefeuille Light
Version minimale du portefeuille V5.3 :
- 6 paires max
- moteurs A et B
- budgets risque actifs
- arbitrage simple mais rigoureux
- pas encore de sophistication complète Complete

---

# 3. Architecture Build-8

## 3.1 Chaîne de traitement

1. `opportunity_selector`
2. `allocation_router`

## 3.2 Principe de hiérarchie

- `opportunity_selector` décide **quoi mérite du capital**
- `allocation_router` décide **combien de capital attribuer**
- les deux doivent respecter :
  - risk backbone
  - scoring backbone
  - moteurs A/B
  - coût réel anticipé
  - capital efficiency attendue

---

# 4. MODULE 1 — OPPORTUNITY_SELECTOR

## 4.1 Nom canonique
`opportunity_selector`

## 4.2 Mission

Classer les opportunités simultanées A/B survivantes et sélectionner celles qui méritent réellement du capital dans le cadre du profil Light.

## 4.3 Responsabilités exactes

- recevoir le pool d’opportunités survivantes
- construire un univers classable
- comparer les opportunités selon :
  - score pénalisé
  - coût attendu
  - CE attendue
  - impact portefeuille
  - consommation de budgets
- sélectionner un sous-ensemble cohérent
- produire des refus relatifs explicites
- éviter la redondance de risque inutile

## 4.4 Ce que ce module ne doit pas faire

- recalculer les moteurs
- refaire le scoring brut
- ignorer les caps portefeuille
- allouer du capital lui-même
- masquer les refus relatifs
- prendre des décisions arbitraires non traçables

## 4.5 Sous-composants

### 4.5.1 candidate_pool_builder
Rôle :
- construire le pool des opportunités A/B recevables

### 4.5.2 eligibility_filter
Rôle :
- vérifier qu’une opportunité est encore compatible avec l’état portefeuille courant

### 4.5.3 comparative_ranker
Rôle :
- établir une priorité relative entre opportunités

### 4.5.4 correlation_conflict_checker
Rôle :
- détecter les conflits évidents d’exposition ou de redondance

### 4.5.5 selection_resolver
Rôle :
- produire la sélection finale et les rejets relatifs

## 4.6 Inputs

- opportunités A et B non hard-blocked
- score pénalisé
- coût attendu
- CE attendue
- taille candidate
- paire
- moteur
- état portefeuille
- beta BTC disponible
- cluster risk disponible
- profil actif

## 4.7 Outputs

- liste ordonnée des opportunités
- sous-ensemble sélectionné
- opportunités rejetées
- raisons des rejets relatifs
- priorités finales

## 4.8 État interne

- snapshot du pool courant
- version de ranking
- historique des sélections
- historique des rejets relatifs

## 4.9 Invariants obligatoires

- une opportunité rejetée par sélection doit rester visible
- le portefeuille ne doit pas sélectionner sur score brut seul
- le classement doit être reproductible
- la logique de sélection doit être versionnée
- la sélection doit rester compatible avec les caps risque

## 4.10 Exigences de design

- simple
- explicable
- compatible Light
- capable de s’enrichir plus tard en Complete
- stable en cas de plusieurs signaux simultanés

## 4.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `ranking_router`
- `risk_engine`
- `btc_factor_guard`
- `correlation_cluster_guard`
- `meta_engine` pour audit
- `monitoring_engine` pour métriques

## 4.12 Dépendances interdites

- exécution live directe
- recalcul moteurs
- modifications des caps
- overrides UI

## 4.13 Logs attendus

- candidate pool size
- candidate ranking built
- selected opportunities
- rejected opportunities
- rejection reason codes
- selection version
- dominant conflict source

## 4.14 Variables de décision recommandées

### 4.14.1 Score pénalisé
\[
S_i
\]

### 4.14.2 Coût attendu
\[
Cost_i^{exp}
\]

### 4.14.3 Capital efficiency attendue
\[
CE_i^{exp}
\]

### 4.14.4 Pénalité corrélation / portefeuille
\[
CorrPenalty_i
\]

### 4.14.5 Pénalité risque / budget
\[
RiskPenalty_i
\]

## 4.15 Formules mathématiques utiles

Score de ranking conceptuel :
\[
R_i = \omega_1 S_i + \omega_2 CE_i^{exp} - \omega_3 Cost_i^{exp} - \omega_4 CorrPenalty_i - \omega_5 RiskPenalty_i
\]

Pool sélectionnable :
\[
Candidates = \{i : HB_i = 0\}
\]

Sélection sous contrainte :
\[
Selected \subset Candidates
\]

avec contraintes :
\[
\sum_{i \in Selected} x_i \le X_{gross,max}
\]

\[
\sum_{i \in Selected} L_i \le LB_{max}
\]

\[
|\Beta_{port}^{proj}| \le B_{max}
\]

\[
ClusterExp_c^{proj} \le X_{cluster,c}^{max}
\]

## 4.16 Règles d’arbitrage recommandées

### Règle 1
À score proche, favoriser la meilleure CE attendue.

### Règle 2
À CE proche, favoriser le coût attendu le plus bas.

### Règle 3
Éviter deux opportunités redondantes sur le même cluster si une seule suffit.

### Règle 4
Le moteur A peut battre B en cas de forte conviction, mais pas automatiquement.

### Règle 5
Le moteur B peut battre A si :
- CE attendue meilleure
- coût plus bas
- durée plus courte
- risque portefeuille plus faible

## 4.17 Tests obligatoires

- une seule opportunité candidate
- deux opportunités A/B comparées
- score proche mais CE différente
- coût plus élevé pénalisant le meilleur score brut
- rejet pour conflit cluster
- rejet pour budget BTC
- refus relatif explicite
- même inputs → même sélection

## 4.18 Dérives possibles à ne pas faire

- sélectionner par score brut seul
- considérer A prioritaire par dogme
- considérer B prioritaire pour la fréquence
- masquer les rejets relatifs
- ne pas tenir compte du coût d’opportunité du capital
- croire qu’un plus grand nombre d’opportunités = meilleur portefeuille

## 4.19 Priorité
P0 absolue

## 4.20 Verdict
**Implémenter maintenant**

---

# 5. MODULE 2 — ALLOCATION_ROUTER

## 5.1 Nom canonique
`allocation_router`

## 5.2 Mission

Attribuer un montant de capital à chaque opportunité sélectionnée, dans le cadre du profil Light, tout en respectant les budgets et la logique économique de la V5.3.

## 5.3 Responsabilités exactes

- recevoir les opportunités sélectionnées
- calculer l’allocation réalisable
- tenir compte du moteur, du score, de la CE attendue et du risque
- appliquer les caps portefeuille
- empêcher qu’une opportunité bonne individuellement consomme trop de capital
- produire une taille finale exécutable par l’order_decider

## 5.4 Ce que ce module ne doit pas faire

- réévaluer le moteur
- ignorer les caps d’exposition et de perte
- considérer le Tier proposé comme un droit absolu
- allouer selon une formule opaque non auditée
- créer des allocations minuscules économiquement stériles sans les marquer

## 5.5 Sous-composants

### 5.5.1 base_size_builder
Rôle :
- définir la taille de base en fonction du profil et du capital

### 5.5.2 score_size_mapper
Rôle :
- transformer score / conviction en modulation de taille

### 5.5.3 portfolio_cap_applier
Rôle :
- appliquer caps globaux et résiduels

### 5.5.4 phantom_trade_guard
Rôle :
- détecter les allocations trop petites pour être économiquement utiles

### 5.5.5 allocation_reporter
Rôle :
- rapport d’allocation final

## 5.6 Inputs

- opportunités sélectionnées
- score pénalisé
- CE attendue
- coût attendu
- tier suggéré
- capital total
- capital libre
- exposition courante
- budget perte courant
- budget BTC courant
- budgets cluster
- caps du profil

## 5.7 Outputs

- taille finale par opportunité
- allocations refusées ou réduites
- raison de réduction
- indicateur phantom trade
- capital libre résiduel

## 5.8 État interne

- capital libre courant
- tailles de base actives
- historique des réductions
- historique des phantom trades évités

## 5.9 Invariants obligatoires

- aucune allocation ne peut dépasser les caps
- le capital libre ne peut pas devenir négatif
- toute réduction de taille doit être traçable
- une allocation trop petite doit être marquée comme phantom risk ou refusée
- le moteur A ne peut pas obtenir Tier 3 si le portefeuille ne le permet pas
- le moteur B ne doit presque jamais recevoir Tier 3

## 5.10 Exigences de design

- simple
- stable
- déterministe
- lisible
- priorité au capital réellement productif

## 5.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `opportunity_selector`
- `risk_engine`
- `btc_factor_guard`
- `correlation_cluster_guard`
- `meta_engine`
- `monitoring_engine`

## 5.12 Dépendances interdites

- moteurs directement
- execution live
- overrides UI
- formule de sizing non versionnée

## 5.13 Logs attendus

- allocation requested
- allocation granted
- allocation reduced
- reduction reason
- phantom trade flagged
- capital remaining
- tier downgrade

## 5.14 Variables de décision recommandées

### 5.14.1 Taille de base
\[
x_{base}
\]

### 5.14.2 Multiplicateur score / conviction
\[
m_i
\]

### 5.14.3 Taille brute candidate
\[
x_i^{raw} = x_{base} \cdot m_i
\]

### 5.14.4 Taille finale après caps
\[
x_i^{final}
\]

## 5.15 Formules mathématiques utiles

Taille candidate :
\[
x_i = x_{base} \cdot m_i \cdot \psi(S_i)
\]

Cap par position :
\[
x_i \le x_{max,pos}
\]

Cap global :
\[
\sum_i x_i \le X_{gross,max}
\]

Cap perte :
\[
\sum_i L_i \le LB_{max}
\]

Cap Tier 3 :
\[
\sum_{i \in Tier3} x_i \le X_{Tier3,max}
\]

Phantom trade condition conceptuelle :
\[
x_i \cdot \mathbb{E}[r_i] \le c_i^{op} + \epsilon
\]

Capital efficiency attendue :
\[
CE_i^{exp} = \frac{\mathbb{E}[PnL_i]}{x_i \cdot h_i}
\]

Capital libre restant :
\[
CapitalFree = P_t - \sum_i x_i
\]

## 5.16 Règles d’allocation recommandées

### Règle 1
L’allocation finale doit toujours respecter les caps avant de respecter les préférences moteur.

### Règle 2
Un trade qui devient économiquement stérile après réduction ne doit pas être maintenu “pour l’activité”.

### Règle 3
Le moteur A peut recevoir plus que B à score/CE/risque équivalents, mais pas de façon aveugle.

### Règle 4
Le moteur B peut recevoir une taille correcte s’il offre une bonne CE attendue avec coût raisonnable.

### Règle 5
Une allocation doit être refusée si sa réduction la transforme en phantom trade.

## 5.17 Tests obligatoires

- allocation simple d’une opportunité
- deux allocations simultanées sous cap
- réduction pour cap exposition
- réduction pour cap perte
- réduction pour budget cluster
- réduction pour budget BTC
- phantom trade détecté
- tier downgrade explicite
- capital libre correct

## 5.18 Dérives possibles à ne pas faire

- considérer le tier suggéré comme intangible
- allouer de minuscules positions inutiles
- réduire tout le monde un peu “pour faire rentrer”
- ne pas distinguer réduction utile et stérilisation
- favoriser toujours A ou toujours B indépendamment de la CE

## 5.19 Priorité
P0 absolue

## 5.20 Verdict
**Implémenter maintenant**

---

# 6. Interfaces entre modules Build-8

## 6.1 ranking_router → opportunity_selector
- opportunités classées
- scores pénalisés
- CE attendues
- coûts attendus
- raisons de refus relatives déjà disponibles

## 6.2 opportunity_selector → allocation_router
- sous-ensemble sélectionné
- priorité finale
- contexte portefeuille

## 6.3 allocation_router → order_decider
- taille finale
- tier final
- raison d’allocation / de réduction
- opportunités refusées pour stérilisation ou cap

## 6.4 allocation_router → meta_engine / monitoring
- capital libre
- réductions de taille
- phantom trades évités
- allocations effectives par moteur / paire

---

# 7. Ordre précis d’implémentation Build-8

## Étape 1
`opportunity_selector`

Pourquoi :
- il faut savoir quoi mérite du capital avant de distribuer ce capital

## Étape 2
`allocation_router`

Pourquoi :
- l’allocation dépend du sous-ensemble retenu et des budgets résiduels

---

# 8. Table synthétique Build-8

| Module | Ordre | Priorité | Gate critique | Sortie attendue |
|---|---:|---:|---|---|
| opportunity_selector | 1 | P0 | arbitrage cohérent | meilleures opportunités retenues |
| allocation_router | 2 | P0 | capital discipliné | tailles finales exploitables |

---

# 9. Conditions de sortie de Build-8

Build-8 est terminé si :

- plusieurs opportunités simultanées peuvent être arbitrées proprement
- l’allocation finale respecte tous les caps
- les réductions de taille sont traçables
- les phantom trades sont détectés ou refusés
- A et B peuvent coexister sans règle arbitraire cachée
- l’order_decider reçoit des tailles finales cohérentes

---

# 10. Critères de refus de sortie

Refuser Build-8 si :

- `opportunity_selector` choisit au score brut seul
- `opportunity_selector` ne sait pas expliquer un rejet relatif
- `allocation_router` crée des allocations économiquement stériles sans les marquer
- les caps portefeuille peuvent être contournés par fragmentation
- le moteur A ou B reçoit un traitement dogmatique non justifié
- le capital libre ou engagé n’est pas cohérent

---

# 11. Dérives globales Build-8 à ne pas faire

- penser qu’un bon signal individuel suffit
- croire que plus de positions = meilleur portefeuille
- réduire mécaniquement chaque position pour “faire rentrer tout le monde”
- ignorer le coût d’opportunité du capital
- laisser A écraser B ou B écraser A par tradition
- oublier qu’un portefeuille Light doit déjà être lisible comme portefeuille, pas comme liste de trades

---

# 12. Verdict final Build-8

Build-8 est la couche où la V5.3 Light devient enfin un **portefeuille**, et non plus seulement un ensemble de composants techniques et de moteurs séparés.

Si Build-8 est bien fait :
- A et B coexistent proprement
- le capital est affecté là où il a le plus de valeur
- les budgets sont réellement respectés
- la Light devient économiquement crédible

Si Build-8 est mal fait :
- les bons signaux seront mal transformés en capital
- la diversification sera mal comprise
- la CE portefeuille sera dégradée
- la production Light sera instable ou trompeuse

Donc :

> Build-8 doit être traité comme un **build bloquant de transformation signal → portefeuille**, pas comme une simple couche d’allocation.

---

# Guardrails issus des audits — Renforcements Build-8

## Anti-churn A/B (GEM-14)
- Si Engine A et Engine B émettent des signaux contradictoires sur la même paire dans une fenêtre de temps réduite, le système doit rester neutre
- Règle de neutralisation : signaux opposés A↔B dans une fenêtre configurable → aucun trade
- Le churn (open A + close B immédiat) détruit l'edge par les frais de transaction
- Le `opportunity_selector` doit implémenter cette logique de neutralisation

## Conflit d'opportunités redondantes (GEM-14)
- L'`opportunity_selector` doit rejeter de manière auditable les opportunités redondantes
- Deux signaux sur la même paire, même direction, même fenêtre = une seule opportunité retenue
- Le rejet relatif doit être loggé dans le DTR avec raison explicite

## Coût d'opportunité du capital (GEM-07b)
- L'`allocation_router` doit intégrer le coût d'opportunité du capital dans sa décision
- Allouer du capital à un trade marginal empêche de le déployer sur un trade meilleur
- Le ranking doit favoriser le CE (Capital Efficiency) et non le score brut seul

## No-trade si coût détruit edge (GEM-07b)
- Le portfolio doit appliquer le filtre no-trade en complément du Build-3
- Si le coût estimé total dépasse l'edge net attendu après allocation, le trade est rejeté
- Ce rejet est loggé comme `COST_EXCEEDS_EDGE_AFTER_ALLOCATION`

## Time-based invalidation (GEM-13)
- Les signaux retenus par le portfolio doivent avoir une durée de validité maximale
- Si un signal n'est pas exécuté dans la fenêtre de validité, il est invalidé
- Protection contre les positions maintenues sur une thèse morte

---

## Fin du document
