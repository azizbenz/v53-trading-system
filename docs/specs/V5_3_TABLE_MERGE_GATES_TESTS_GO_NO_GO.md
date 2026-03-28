# V5.3 — TABLE DES MERGE GATES / TESTS / CRITÈRES GO-NO-GO
## Spécification prod-safe de livraison et de déploiement
### Complément canonique au `V5_3_MASTER_FINAL_CANONICAL.md`
### Sans code

---

# 0. Objet du document

Ce document définit les règles obligatoires de :

- merge de module
- validation de build
- passage shadow → micro-live → live
- activation Light / Complete
- critères go / no-go

L’objectif est simple :

> empêcher qu’une brique “intelligente” entre en prod alors qu’elle n’est ni testée, ni observable, ni économiquement justifiée.

---

# 1. Hiérarchie des gates

## 1.1 Niveaux
1. **Gate de module**
2. **Gate de build**
3. **Gate de profil**
4. **Gate de déploiement**
5. **Gate économique**
6. **Gate d’extension Complete**

## 1.2 Principe
Un niveau ne compense jamais un autre.  
Exemple :
- un module mathématiquement élégant mais sans recovery test = refus
- un build complet avec bon PnL shadow mais sans logs suffisants = refus
- un profil Complete sans Light validé = refus

## 1.3 Invariants local / VPS et runtime_mode

La V5.3 reste :

- une seule base de code
- deux profils métier uniquement : `LIGHT`, `COMPLETE`
- quatre `runtime_mode` uniquement : `LOCAL_REPLAY`, `SHADOW`, `MICRO_LIVE`, `LIVE`

Refus immédiat si l’on introduit :

- `BACKTEST_PROFILE`
- `LOCAL_PROFILE`
- une seconde V5.3 locale ou VPS
- une promotion implicite local -> live
- l’exécution sur VPS d’un code stratégie importé par artifact

---

# 2. GATE DE MODULE

## 2.1 Conditions minimales de merge d’un module

Un module n’est mergeable que si :

1. interface définie  
2. responsabilité claire  
3. dépendances autorisées uniquement  
4. tests de contrat écrits  
5. tests unitaires présents  
6. smoke test bootstrap  
7. smoke test recovery si module stateful  
8. logs obligatoires définis  
9. audit logique quant si module métier  
10. documentation module minimale rédigée  
11. `correlation_id` / `event_id` / `source_version` si le module produit diagnostics, artifacts, états de promotion ou événements opératoires  

## 2.2 Table standard de merge

| Critère | Obligatoire ? | Refus si absent ? |
|---|---:|---:|
| Interface explicite | oui | oui |
| Inputs / outputs documentés | oui | oui |
| Dépendances validées | oui | oui |
| Contract tests | oui | oui |
| Unit tests | oui | oui |
| Smoke bootstrap | oui | oui |
| Smoke recovery si stateful | oui | oui |
| Logs critiques | oui | oui |
| Audit quant / risk si pertinent | oui | oui |
| Documentation module | oui | oui |
| IDs structurés si module stateful / artifact / promotion | oui | oui |

## 2.3 Dérives à éviter
- “on merge puis on écrira les tests”
- module sans ownership
- module sans logs
- module généré par IA sans revue croisée

---

# 3. TESTS OBLIGATOIRES PAR TYPE DE MODULE

## 3.1 data_engine
Tests minimums :
- reconnexion WS
- disorder d’événements
- duplication
- perte temporaire de flux
- backlog croissant
- recovery

Refus si :
- ordre des événements non fiable
- backlog non mesuré
- aucune logique de dégradation

## 3.2 data_quality_engine
Tests minimums :
- stale data
- incohérence multi-flux
- suspension paire
- reprise paire

Refus si :
- pas de raison explicite de suspension
- contamination des autres paires

## 3.3 signal_engine
Tests minimums :
- génération signal correcte
- non génération hors conditions
- cohérence par régime
- duplication A/B/C/D détectable

Refus si :
- moteur non différencié
- signal sans coût attendu

## 3.4 scoring_engine
Tests minimums :
- hard blockers
- soft penalties
- ranking
- refus des profils interdits

Refus si :
- soft = hard déguisé
- impossible de reproduire une décision

## 3.5 risk_engine
Tests minimums :
- cap exposition
- cap perte
- budget BTC
- budget cluster
- refus Tier 3 excessif

Refus si :
- cap contournable
- budget non journalisé

## 3.6 execution_engine
Tests minimums :
- ordre ACK
- partial fill
- order timeout
- reconciliation
- coût réel loggé

Refus si :
- état local divergent du compte
- coût non mesuré

## 3.7 portfolio_engine
Tests minimums :
- arbitrage opportunités simultanées
- budget corrélation
- refus sur-exposition
- sélection priorisée

Refus si :
- le moteur choisit par score brut seul
- aucune conscience portefeuille

## 3.8 monitoring_engine
Tests minimums :
- collecte métriques
- alertes
- backlog visible
- DTR loss visible

Refus si :
- dashboards sans métriques critiques

## 3.9 meta_engine
Tests minimums :
- DTR complet
- phantom trade detection
- break-even réel
- edge tracker minimal

Refus si :
- perte silencieuse de DTR
- confusion trade actif / phantom

## 3.10 dependency_architecture
Tests minimums :
- import graph
- contract checks
- build order
- bootstrap clean

Refus si :
- cycle
- interface brisée
- manifest incohérent

---

# 4. GATE DE BUILD

## 4.1 Un build Light est recevable seulement si
- tous les modules P0 Light sont présents
- les interfaces sont cohérentes
- les smoke tests passent
- les logs critiques remontent
- la UI minimale fonctionne
- aucun module FORBIDDEN n’est activé

## 4.2 Un build Complete est recevable seulement si
- build Light déjà stable
- modules P1 Complete ajoutés sans casser P0
- moteurs C/D présents mais encore validables
- budgets corrélation enrichis
- saturation infra toujours sous contrôle

## 4.3 Refus automatique du build si
- backlog critique
- DTR incomplets
- configuration non versionnée
- UI contournable
- logs critiques absents

---

# 5. GATE DE PROFIL

## 5.1 Profil Light — conditions
- maximum 6 paires actives
- moteurs A/B seulement
- budgets risque activés
- coût réel mesuré
- CE affichée
- UI verrouillée Light
- tous les modules P0 présents

## 5.2 Profil Complete — conditions
- Light déjà validé
- maximum 12 paires
- moteurs A/B/C/D
- corrélation enrichie
- CE et K_eff suivis
- moteurs C/D mesurés avant activation pleine

## 5.3 Refus automatique
- profil hybride
- activation manuelle de C/D en Light
- 12 paires en Light
- configuration non signée / non journalisée

---

# 5 bis. GATE LOCAL_REPLAY / ARTIFACT / ONBOARDING

## 5 bis.1 Objet
Encadrer le chemin documentaire et futur d’introduction d’une nouvelle hypothèse ou stratégie :

`classification -> versioning -> shared core -> LOCAL_REPLAY -> export artifact -> import VPS -> candidature contrôlée`

## 5 bis.2 Conditions minimales
- classification explicite : `A_variant`, `B_variant`, `Build14_enabler`, `C_candidate`, `D_candidate`, `out_of_scope_for_V5_3`
- versioning explicite
- intégration shared core, jamais plugin libre
- export artifact signé / versionné / horodaté
- import VPS en lecture seule
- aucun code stratégie exécutable importé
- `correlation_id`, `artifact_id`, `proposal_id`, `source_version` visibles

## 5 bis.3 Refus automatique
- artifact non versionné
- import qui modifie le live ou le profil actif
- fork local / VPS
- création d’un `BACKTEST_PROFILE`
- contournement de Shadow / Micro-live / Live

## 5 bis.4 Statut Build-9X
- Build-9X peut produire diagnostics, hypothèses, checklists, improvement candidates et replay bundles
- Build-9X n’est pas promouvable tant qu’il n’est pas codé, testé et validé par les gates normales
- aucune auto-modification live n’est autorisée
- aucune auto-promotion n’est autorisée

---

# 6. GATE SHADOW

## 6.1 Objectif
Valider la logique sans risque capital.

## 6.2 Métriques minimales
- fréquence brute
- fréquence utile
- coût attendu
- coût simulé
- DTR complets
- pass-rate économique
- santé infra
- backlog
- pair health

## 6.3 Conditions de sortie de Shadow
- pas de panne d’état majeure
- décisions reproductibles
- coûts plausibles
- corrélation portefeuille lisible
- aucun module critique instable

## 6.4 Refus si
- DTR incomplets
- signaux non explicables
- coûts simulés incohérents
- infra déjà proche de saturation

---

# 7. GATE MICRO-LIVE

## 7.1 Objectif
Valider :
- exécution réelle
- coûts réels
- qualité d’ACK / fills
- reconciliation
- stabilité sous vraie latence

## 7.2 Taille micro-live
- notional réduit
- budget perte très faible
- aucune exposition agressive
- pas de Tier 3

## 7.3 Métriques minimales
- coût réel vs attendu
- fill latency
- partial fill rate
- stale decision rate
- pair health live
- CE live
- divergence shadow/live

## 7.4 Refus de progression si
- coût réel > coût prudent prévu
- reconciliation instable
- stérilisation trop élevée
- gross breaches
- backlog critique

---

# 8. GATE LIVE-LIGHT

## 8.1 Objectif
Autoriser la production initiale.

## 8.2 Conditions go
- fréquence utile Light > V5.2
- edge net Light > 0 ou au moins économiquement crédible
- CE Light > V5.2
- coûts réels stables
- DTR et logs fiables
- saturation infra absente
- budgets risque respectés
- beta BTC contrôlé
- drawdown supportable
- sterilization rate acceptable

## 8.3 Conditions no-go
- coût non maîtrisé
- trop de phantom trades
- moteur B détruit la CE
- A trop rare
- corrélation cluster non contrôlée
- infra instable

---

# 9. GATE LIVE-COMPLETE

## 9.1 Objectif
Passer à 12 paires / 4 moteurs seulement si la complexité supplémentaire apporte un gain réel.

## 9.2 Conditions go
- Live-Light stable sur durée suffisante
- 6 paires déjà propres
- moteurs A/B validés
- C apporte alpha ou fréquence utile
- D apporte valeur marginale
- coût des paires additionnelles soutenable
- budget BTC et clusters sous contrôle
- K_eff augmente
- CE portefeuille augmente ou au minimum ne se dégrade pas excessivement
- infra toujours stable

## 9.3 Conditions no-go
- C duplique A
- D n’ajoute rien
- les 6 paires additionnelles augmentent le bruit plus que l’edge
- K_eff reste quasi constant
- backlog / logs / DTR se dégradent
- le profil Complete n’améliore que la fréquence brute

---

# 9 bis. GATE BUILD-14 ENRICHI

## 9 bis.1 Règle d’introduction
Toute brique `Build14_enabler` doit suivre trois étapes :

1. lecture seule
2. influence limitée
3. candidature éventuelle vers Build-15/16/17

## 9 bis.2 Refus automatique
- moteur autonome déguisé
- bypass de A/B/C/D
- bypass du risk backbone ou du portfolio
- hard block live immédiat
- influence significative sans validation replay puis shadow

## 9 bis.3 Budgets minimaux attendus
- budget CPU documenté
- budget RAM documenté
- budget I/O documenté
- impact latence documenté
- logs structurés et projections UI prévues

---

# 10. GATE ÉCONOMIQUE

## 10.1 Règle fondamentale
La progression n’est jamais décidée sur :
- win rate seul
- PnL brut seul
- fréquence brute seule
- quantité de modules développés

## 10.2 Variables de décision
- edge net
- coût réel
- CE
- fréquence utile
- budget risque
- beta BTC
- drawdown
- K_eff
- sterilization rate

## 10.3 Formules de référence
\[
CE = \frac{PnL}{capital \times temps}
\]
\[
SterilRate = \frac{\sum_i \mathbf{1}_{CE_i < CE_{min}} \mathbf{1}_{A_i=1}}{\sum_i A_i}
\]
\[
\Beta_{port} = \sum_j w_j \beta_j
\]

## 10.4 Refus si
- fréquence augmente mais CE baisse trop
- CE augmente mais risque systémique explose
- edge net dépend uniquement d’une paire
- le coût détruit l’alpha

---

# 11. GATE INFRASTRUCTURE

## 11.1 Variables minimales
- \(\lambda\) total
- \(\mu_s\)
- \(\rho_q\)
- \(W_q\)
- reconnect count
- stale rate
- log loss rate
- DTR loss rate

## 11.2 Formules de référence
\[
\rho_q = \frac{\lambda}{\mu_s}
\]
\[
W_q = \frac{\lambda}{\mu_s(\mu_s-\lambda)}
\]

## 11.3 Refus si
- \(\rho_q\) trop élevé durablement
- \(W_q\) dérive
- DTR loss non nul de manière significative
- état pair health trop volatil
- stale rate non négligeable

---

# 12. GATE UI / OPÉRATIONS

## 12.1 Conditions go
- UI affiche toutes les métriques critiques
- aucune action interdite n’est possible
- journalisation des actions opérateur complète
- états Light/Complete respectés

## 12.2 Refus si
- l’UI permet un override critique
- moteur C/D activable en Light
- 12 paires activables en Light
- hard blocker bypassable

---

# 13. TABLE DES GO / NO-GO PAR PROFIL

| Critère | Shadow | Micro-live | Live-Light | Live-Complete |
|---|---:|---:|---:|---:|
| DTR fiables | obligatoire | obligatoire | obligatoire | obligatoire |
| Coûts réels | simulés cohérents | obligatoires | obligatoires | obligatoires |
| CE | estimée | mesurée | positive/crédible | meilleure ou stable |
| Budgets risque | simulés | actifs | actifs | actifs enrichis |
| Beta BTC | suivi | suivi | contrôlé | contrôlé |
| K_eff | optionnel | utile | utile | obligatoire |
| Backlog/queues | stable | stable | stable | stable renforcé |
| UI verrouillée | oui | oui | oui | oui |
| Moteurs C/D | non | non | non | oui si validés |

---

# 14. TABLE DES PRIORITÉS DE TEST

| Élément | Priorité | Pourquoi |
|---|---:|---|
| Reconciliation exécution | P0 | sans cela, portefeuille faux |
| DTR complets | P0 | sinon analytics inutiles |
| Budget risque | P0 | sinon drawdown non borné |
| Coût réel | P0 | sinon faux edge |
| Pair health | P0 | sinon contamination système |
| Backlog / queues | P0 | sinon stale decisions |
| CE | P0 | sinon activité stérile |
| K_eff | P1 | utile pour Complete |
| Ledoit-Wolf | P2 | amélioration, pas blocage |
| HMM enrichi | P2 | amélioration, pas blocage |

---

# 15. WORKFLOW IA OBLIGATOIRE

## 15.1 Pour chaque module
1. spec module
2. tests attendus
3. génération code
4. audit croisé
5. corrections
6. merge si gates passés

## 15.2 Refus si
- code généré sans tests
- code merge sans audit
- plusieurs modules critiques mergés en même temps
- build cassé toléré “temporairement”

---

# 16. DÉRIVES GLOBALES À NE PAS FAIRE

- passer en live parce que “ça a l’air bon”
- accepter une UI permissive
- accepter un backlog latent
- regarder seulement le PnL
- promouvoir Complete pour “faire avancer le projet”
- considérer qu’un moteur codé = un moteur validé

---

# 17. CONCLUSION

Un système V5.3 prod-safe ne devient pas sûr parce qu’il a beaucoup de modules ou beaucoup d’équations.

Il devient sûr parce qu’il a :

- des modules mergeables
- des builds contrôlés
- des profils verrouillés
- des métriques économiques réelles
- une infrastructure observable
- des règles go/no-go falsifiables

Ce document doit être utilisé comme **checklist de vérité avant tout merge et avant tout changement de profil**.

---

## Fin du document
