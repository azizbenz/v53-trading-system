# V5.3 — TABLE DÉTAILLÉE DE L’INTERFACE UTILISATEUR
## Spécification UI / Console opérateur / Supervision
### Complément canonique subordonné au `V5_3_MASTER_FINAL_UNIQUE.md`
### Sans code — prod-safe

---

# 0. Objet du document

Ce document définit l’interface utilisateur officielle de la V5.3.

L’interface n’est pas un espace de bricolage libre.  
Elle est un **panneau de contrôle surveillé**, conçu pour :

- charger un profil validé
- superviser l’état du système
- suspendre proprement une paire ou un moteur
- visualiser les métriques critiques
- confirmer l’état de santé économique et opérationnel

Elle ne doit **jamais** permettre de contourner les garde-fous fondamentaux.

## 0.1 Statut documentaire vs implémentation

Cette table décrit la **cible UI canonique**.

Elle ne doit pas être lue comme la preuve que toute la surface UI est déjà codée.

Lecture honnête :

- le **core Build-1 à Build-9** est la base exécutable / gelable actuelle
- Build-10 dispose désormais d’une première implémentation backend / projection UI Light
- Build-11 à Build-17 restent des phases canoniques de validation et
  d'extension du rollout
- les vues `Build-9X`, `LOCAL_REPLAY`, `artifact import` et `strategy onboarding` décrites plus bas restent **partiellement implémentées au mieux** : quelques projections backend existent, mais la surface UI complète n’est pas finie
- ces vues futures restent liées à des `runtime_mode` gouvernés et jamais à un fork local / VPS

---

# 1. Principes non négociables

## 1.1 L’UI ne doit pas permettre
- d’activer des modules interdits par le profil
- de forcer > 6 paires en mode LIGHT
- de forcer un moteur ou une paire au-dela des gates, budgets ou borne runtime
- de contourner les hard blockers
- de bypass le risk engine
- d’éditer des paramètres critiques en live sans journalisation
- de mélanger librement Light et Complete

## 1.2 L’UI doit permettre
- la lecture claire de l’état système
- la suspension contrôlée
- la reprise contrôlée
- la consultation des métriques
- la traçabilité des changements
- l’accès rapide aux alertes et journaux critiques
- la distinction explicite entre `disponible`, `armé`, `actif`, `borné`,
  `suspendu` et `non déployé`
- **l'affichage des Hard States** de chaque composant : `SHADOW_ENABLED`, `SHADOW_VALIDATED`, `PROMOTED`, `DORMANT`
- **la visualisation des moteurs actifs en Shadow** : A/B/C/D avec statut individuel
- **la visualisation des enablers Build-14 actifs en Shadow** : microstructure, régime, covariance, risk contribution, edge diversity
- **les verdicts post-Shadow** par composant
- **la contribution de chaque moteur/enabler** : edge marginal, coût, churn, duplication, concentration, risk contribution

## 1.3 Toute action opérateur doit être
- journalisée
- horodatée
- attribuée à un acteur
- réversible si possible
- refusée si incompatible avec le profil ou l’état courant

---

# 2. Architecture générale de l’UI

## 2.1 Écrans canoniques

1. **Overview portefeuille**
2. **Profils & état de déploiement**
3. **Paires**
4. **Moteurs**
5. **Risque & exposition**
6. **Coûts & exécution**
7. **Qualité data & infra**
8. **Meta / DTR / phantom trades**
9. **Logs & événements**
10. **Administration contrôlée**

## 2.2 Règle de hiérarchie

Les écrans doivent être hiérarchisés selon la criticité :

- niveau 1 : portefeuille / état global / alertes
- niveau 2 : paires / moteurs / risque
- niveau 3 : exécution / coût / DTR
- niveau 4 : administration / historique / détails

L’opérateur doit pouvoir voir en quelques secondes :
- si le système est sain
- si le capital est en danger
- si une paire est suspendue
- si un moteur dérive
- si l’infrastructure sature

---

# 3. Écran 1 — OVERVIEW PORTEFEUILLE

## 3.1 Mission
Donner une vue synthétique immédiate de l’état du système.

## 3.2 Blocs obligatoires

### Bloc A — État global
- profil actif
- état de déploiement
- nombre de paires actives
- moteurs actifs
- dernier heartbeat système
- état infra global

### Bloc B — Capital
- capital total
- capital engagé
- capital libre
- exposition brute
- budget perte consommé
- drawdown courant

### Bloc C — Performance
- PnL jour
- PnL semaine
- PnL mois
- PnL cumulé
- CE portefeuille
- fréquence utile portefeuille

### Bloc D — Risque systémique
- beta BTC portefeuille
- cluster risk principal
- nombre de positions corrélées
- sterilization rate

## 3.3 Métriques mathématiques à afficher
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

## 3.4 Dérives à éviter
- UI belle mais sans métriques actionnables
- cacher les budgets de risque
- afficher seulement le PnL sans coût ni CE

---

# 4. Écran 2 — PROFILS & ÉTAT DE DÉPLOIEMENT

## 4.1 Mission
Permettre de voir et charger uniquement les profils validés, ainsi que l'etat
de rollout et d'activation reelle.

## 4.2 États officiels
- SHADOW
- MICRO-LIVE
- LIVE-LIGHT
- LIVE-COMPLETE
- DEGRADED
- HALTED
- disponible
- armé
- actif
- borné
- suspendu
- non déployé

## 4.3 Actions autorisées
- charger le profil Light si toutes conditions compatibles
- charger le profil Complete seulement si autorisé
- voir les composants armes mais non actifs
- passer en HALTED
- repasser en DEGRADED automatiquement en cas de breach

## 4.4 Actions interdites
- charger Complete si gates non passées
- composer un profil custom
- activer un moteur ou une paire hors gates, hors budget ou hors borne de rollout
- dépasser le nombre max de paires du profil

## 4.5 Champs obligatoires
- profil courant
- profil demandé
- raison de refus si action interdite
- dernière transition d’état
- utilisateur ayant provoqué la transition

## 4.6 Dérives à éviter
- bouton “override” sur le profil
- logique permissive “avertir mais laisser faire”

---

# 5. Écran 3 — PAIRES

## 5.1 Mission
Superviser, armer, activer et suspendre les paires dans le cadre du profil
actif et de la borne de rollout.

## 5.2 Vue tableau obligatoire
Colonnes :
- paire
- classe (A/B/C)
- état runtime
- santé \(H_j\)
- stale rate
- coût moyen
- coût p90
- CE moyenne
- fréquence utile
- moteur(s) autorisés
- moteur(s) armés
- raison de suspension si suspendue

## 5.3 Métriques mathématiques associées
\[
H_j = w_Q Q_j + w_L L_j + w_C C_j + w_R R_j
\]
\[
\mu_j^{net} = \mathbb{E}[r \mid paire=j]
\]
\[
CE_j = \frac{\sum_{i \in j} PnL_i}{\sum_{i \in j} x_i h_i}
\]

## 5.4 Actions autorisées
- suspendre paire
- demander réactivation
- afficher historique santé / coût / CE

## 5.5 Actions interdites
- réactiver une paire hard-blocked sans cause levée
- activer une paire non autorisée par le profil
- dépasser la capacité max du profil ou la borne de rollout

## 5.6 Dérives à éviter
- écran liste sans raisons explicites
- suspension manuelle non journalisée
- santé agrégée globale sans santé par paire

---

# 6. Écran 4 — MOTEURS

## 6.1 Mission
Superviser le comportement des moteurs A/B/C/D.

## 6.2 Vue tableau obligatoire
Colonnes :
- moteur
- autorisé par profil
- état runtime
- fréquence utile
- rendement net
- coût moyen
- CE
- Sharpe par trade
- drawdown
- corrélation avec portefeuille
- risque de duplication d'edge
- paires actives
- raison de suspension

## 6.3 Métriques mathématiques associées
\[
\mu_k^{net} = \mathbb{E}[r \mid moteur=k]
\]
\[
Sh_k = \frac{\mu_k}{\sigma_k}
\]
\[
CE_k = \frac{\sum_{i \in k} PnL_i}{\sum_{i \in k} x_i h_i}
\]

## 6.4 Actions autorisées
- suspendre moteur
- afficher détail par paire
- afficher coût et CE par régime

## 6.5 Actions interdites
- activer un moteur hors gates, hors budget ou sans journalisation
- réactiver un moteur sans journalisation
- changer son budget live sans passer par risk engine

## 6.6 Dérives à éviter
- suivi moteur uniquement par win rate
- aucune lecture de CE
- masquer duplication possible entre moteurs

---

# 7. Écran 5 — RISQUE & EXPOSITION

## 7.1 Mission
Rendre visibles les contraintes réelles du portefeuille.

## 7.2 Blocs obligatoires
- exposition brute
- budget perte
- beta BTC
- exposition par cluster corrélé
- nombre de positions
- positions Tier 3
- contribution marginale au risque
- breaches actives

## 7.3 Métriques mathématiques associées
\[
GrossExp = \sum_i x_i
\]
\[
LossBudget = \sum_i L_i
\]
\[
\Beta_{port} = \sum_j w_j \beta_j
\]
\[
Var(R_p)=w^\top\Sigma w
\]
\[
MRC_j = \frac{(\Sigma w)_j}{\sqrt{w^\top\Sigma w}}
\]

## 7.4 Actions autorisées
- voir les breaches
- demander réduction contrôlée
- voir quelles positions consomment le plus de risque

## 7.5 Actions interdites
- dépasser les caps via UI
- modifier les caps sans workflow admin contrôlé

## 7.6 Dérives à éviter
- se contenter du notional
- ne pas afficher les clusters corrélés
- ne pas afficher le budget BTC

---

# 8. Écran 6 — COÛTS & EXÉCUTION

## 8.1 Mission
Rendre visible l’économie réelle de l’exécution.

## 8.2 Blocs obligatoires
- coût moyen par paire
- coût p90
- frais explicites
- ELW moyen
- partial fill rate
- fill latency
- slippage vs attendu
- coût par moteur

## 8.3 Métriques mathématiques associées
\[
ELW = \frac{|P^{exec} - Mid|}{Mid}
\]
\[
c_i = f_i + c_i^{impl} + AS_i + PF_i
\]
\[
BE_{k,j} = \mathbb{E}[c \mid moteur=k, paire=j]
\]

## 8.4 Actions autorisées
- voir détail des exécutions
- filtrer par moteur / paire / période

## 8.5 Actions interdites
- masquer les coûts réels
- montrer seulement les fees
- agréger au point d’effacer les problèmes locaux

## 8.6 Dérives à éviter
- UI exécution décorative
- aucune comparaison coût attendu / coût réalisé

---

# 9. Écran 7 — QUALITÉ DATA & INFRA

## 9.1 Mission
Montrer si le système est techniquement en train de se dégrader.

## 9.2 Blocs obligatoires
- statut WS par flux
- heartbeat
- reconnect count
- queue usage
- backlog size
- stale rate
- pair health
- DTR loss rate
- log loss rate
- état CPU / RAM / I/O
- latence end-to-end

## 9.3 Métriques mathématiques associées
\[
\rho_q = \frac{\lambda}{\mu_s}
\]
\[
W_q = \frac{\lambda}{\mu_s(\mu_s-\lambda)}
\]
\[
LogLossRate = \frac{N_{drops}}{N_{events}}
\]
\[
DTRLossRate = \frac{N_{DTR,drops}}{N_{signals}}
\]

## 9.4 Actions autorisées
- passer en DEGRADED
- suspendre une paire dégradée
- voir historique infra

## 9.5 Actions interdites
- continuer en LIVE si saturation critique
- masquer le backlog

## 9.6 Dérives à éviter
- interface infra “verte” alors que les queues montent
- CPU seulement sans queue metrics

---

# 10. Écran 8 — META / DTR / PHANTOM TRADES

## 10.1 Mission
Superviser la couche d’explication économique.

## 10.2 Blocs obligatoires
- DTR récents
- pass-rate brut
- pass-rate utile
- phantom trade rate
- CRA alerts
- AMD alerts
- top blockers
- top reducers
- moteurs les plus stérilisés

## 10.3 Métriques mathématiques associées
\[
SterilRate = \frac{\sum_i \mathbf{1}_{CE_i < CE_{min}} \mathbf{1}_{A_i=1}}{\sum_i A_i}
\]
\[
F_{utile} = \frac{\text{trades à expectancy utile}}{\text{temps}}
\]

## 10.4 Actions autorisées
- drill-down sur une décision
- export audit d’un trade
- filtrer par moteur / paire / période

## 10.5 Actions interdites
- résumer les décisions sans causes
- perdre la distinction évalué / non évalué / bloqué

## 10.6 Dérives à éviter
- DTR incomplet
- analytics non reliées au coût réel

---

# 11. Écran 9 — LOGS & ÉVÉNEMENTS

## 11.1 Mission
Centraliser les événements critiques et les actions opérateur.

## 11.2 Catégories
- infra
- data
- risk
- execution
- portfolio
- moteur
- paire
- opérateur
- alertes

## 11.3 Actions obligatoires
- rechercher
- filtrer
- horodatage précis
- corrélation par run / session / trade id

## 11.4 Dérives à éviter
- logs trop verbeux mais inutiles
- logs sans relation entre eux
- aucun identifiant pour relier les événements

---

# 12. Écran 10 — ADMINISTRATION CONTRÔLÉE

## 12.1 Mission
Exposer les actions administratives strictement nécessaires.

## 12.2 Actions possibles
- suspendre / reprendre une paire
- suspendre / reprendre un moteur
- passer en HALTED
- demander changement de profil
- consulter la version active du manifest
- voir les gates de merge / de live

## 12.3 Actions interdites
- modifier les invariants de risque
- changer les caps de corrélation en live
- injecter une configuration non versionnée
- charger un profil non validé

## 12.4 Journalisation obligatoire
- utilisateur
- timestamp
- ancienne valeur
- nouvelle valeur
- raison
- ticket / référence changement

---

# 13. Comportement UI par profil

## 13.1 Light
- 6 paires max
- architecture complete visible
- A/B attendus au coeur du rollout initial
- C/D visibles avec etat `non deploye`, `arme`, `borne` ou `actif` selon gates
- pas de bouton d'override de rollout
- risque renforcé, simplicité gouvernée

## 13.2 Complete
- 12 paires max
- moteurs A/B/C/D activables sous gouvernance
- budgets corrélation enrichis
- écrans C et D déverrouillés
- analytics plus riches

---

# 14. Table des composants UI

| Composant UI | Type | Light | Complete | Criticité | Actionable ? |
|---|---|---:|---:|---:|---:|
| Overview portefeuille | écran | oui | oui | P0 | oui |
| Profils & état | écran | oui | oui | P0 | oui |
| Table paires | écran | oui | oui | P0 | oui |
| Table moteurs | écran | oui | oui | P0 | oui |
| Risque & exposition | écran | oui | oui | P0 | oui |
| Coûts & exécution | écran | oui | oui | P0 | oui |
| Data & infra | écran | oui | oui | P0 | oui |
| Meta / DTR | écran | oui | oui | P1 | oui |
| Logs & événements | écran | oui | oui | P1 | oui |
| Admin contrôlée | écran | oui | oui | P1 | oui |
| Bouton profil custom | action | non | non | FORBIDDEN | non |
| Override hard blocker | action | non | non | FORBIDDEN | non |

---

# 14 bis. Vues gouvernées — partiellement implémentées, non finalisées

## 14 bis.1 Build-9X
La surface UI/backend Build-9X doit exposer en lecture :

- diagnostics
- hypotheses
- replay eligibility
- learning events
- replay bundles

Ces vues restent :

- non promotrices par elles-mêmes
- sans mutation live
- sans override de profil
- sans réécriture d’un moteur A/B/C/D

## 14 bis.2 LOCAL_REPLAY / artifact import / onboarding
La surface UI/backend dédiée peut exposer :

- l’état d’un run `LOCAL_REPLAY`
- l’état d’export d’un artifact
- l’état d’import VPS
- la classification d’une proposition stratégie
- la traçabilité `proposal_id` / `artifact_id` / `correlation_id`

Mais elle ne doit jamais permettre :

- d’exécuter du code stratégie importé
- de créer un `BACKTEST_PROFILE`
- de contourner `SHADOW`, `MICRO_LIVE` ou `LIVE`
- de promouvoir implicitement une hypothèse locale vers le live

## 14 bis.3 Build-14 enrichi
Les briques `Build14_enabler` doivent apparaître d’abord comme :

- composants `SHADOW_ENABLED` du Shadow complet
- contributions enrichies visibles dans le scoring, le risk et le portefeuille Shadow
- verdicts post-Shadow (`SHADOW_VALIDATED` ou `DORMANT`)
- projections comparatives de coût, concentration, duplication et risk contribution

et non comme :

- moteur autonome
- source de hard block live immédiat
- voie de contournement des gates de promotion
- composant auto-promu en live sans verdict

---

# 15. Tests obligatoires de l’UI

## 15.1 Tests fonctionnels
- charger le bon profil
- refuser un mauvais profil
- suspendre une paire
- empêcher l’activation hors profil
- visualiser les métriques critiques

## 15.2 Tests de sécurité fonctionnelle
- aucun contournement des hard blockers
- aucune modification de paramètres critiques sans journal
- aucune action non autorisée par l’état courant

## 15.3 Tests de robustesse
- UI encore lisible si une paire est dégradée
- UI encore fonctionnelle si un moteur est suspendu
- UI encore cohérente si une partie des analytics secondaires est indisponible

---

# 16. Dérives globales à ne pas faire

- transformer l’UI en cockpit de bricolage
- exposer trop de boutons critiques
- masquer les coûts et la CE
- afficher du décor au lieu du risque réel
- permettre un profil hybride non validé
- autoriser des overrides non auditables

---

# 17. Verdict UI

L’UI V5.3 doit être :
- sobre
- orientée risque et coût
- pilotée par profil
- impossible à détourner contre l’architecture

Elle doit servir à **surveiller et gouverner**, pas à improviser.

---

## Fin du document
