# V5_3_MASTER_FINAL_CANONICAL
## Architecture canonique unique — prod-safe
### Système quant crypto spot halal — V5.3
### Document maître développeur / quant / risk / infra
### Référence unique du projet

---

# 0. Statut du document

Ce document est la **référence canonique unique** de la V5.3.

Il remplace l’usage simultané de plusieurs documents actifs et absorbe les travaux précédents dans une structure unique.  
Toutes les annexes, audits, notes de recherche et variantes mathématiques doivent être considérées comme :

- soit **intégrées ici**
- soit **archivées**
- soit **non binding**

## Règle absolue

Aucun développeur, aucune IA, aucun auditeur ne doit utiliser un autre document comme source de vérité active si ce document contredit ou dépasse ce master.

## 0.1 Statut documentaire vs réalité d’implémentation

Pour éviter toute sur-promesse :

- le **core Build-1 à Build-9** reste la base réellement exécutable / gelable
- **Build-10** dispose désormais d’une première implémentation codée côté monitoring backend et projection UI Light verrouillée
- **Build-9X** dispose désormais d’une première implémentation codée côté diagnostics, hypothèses, candidats et exports gouvernés
- **LOCAL_REPLAY** et l’import d’artifact disposent désormais de **scaffolds minimaux codés**, sans constituer encore un runtime complet opéré
- **Build-11 à Build-17** restent des cibles canoniques futures
- `COMPLETE` ne doit toujours pas être lu comme pleinement runtime-ready tant que Build-14 à Build-17 ne sont pas réellement validés

## 0.2 Invariants local / VPS

La V5.3 reste :

- **une seule base de code**
- **deux profils métier uniquement**
  - `LIGHT`
  - `COMPLETE`
- **quatre runtime_mode uniquement**
  - `LOCAL_REPLAY`
  - `SHADOW`
  - `MICRO_LIVE`
  - `LIVE`

Interdictions canoniques :

- `BACKTEST_PROFILE`
- `LOCAL_PROFILE`
- toute seconde V5.3 locale ou VPS
- toute promotion implicite d’une idée locale vers le live
- tout fork local / VPS

---

# 1. Mission de la V5.3

La V5.3 a pour objectif de transformer une architecture V5.2 très sophistiquée mais économiquement trop rare en un **portefeuille spot halal multi-paires, multi-moteurs, réellement monétisable**, sans trahir les contraintes de prudence, de coût réel, de simplicité d’exploitation et de robustesse opérationnelle.

## Le problème fondamental

Avec :

- capital faible
- spot uniquement
- absence de levier
- coûts réels
- fréquence initiale faible

un système peut être :

**mathématiquement élégant, mais économiquement stérile**.

La V5.3 existe pour corriger cela.

---

# 2. Contraintes non négociables

## 2.1 Contraintes de marché

- trading spot uniquement
- pas de levier
- pas de futures
- pas de perpetual
- pas de funding
- pas de dette
- pas de carry synthétique
- pas de construction à effet de levier implicite

## 2.2 Contraintes physiques

- CPU-only
- pas de GPU requis en production
- machine sobre
- faible latence utile, pas HFT
- exchange principal : Binance Spot
- capital de départ modeste
- architecture résiliente aux flux dégradés
- priorité à la stabilité d’état sur l’élégance

## 2.3 Contraintes de gouvernance

- source de vérité unique
- modules versionnés
- interfaces explicites
- contract tests obligatoires
- smoke tests de bootstrap / recovery obligatoires
- aucune mise en prod sans gates de merge

---

# 3. Philosophie générale de la V5.3

La V5.3 ne cherche pas :

- à multiplier artificiellement les trades
- à relâcher aveuglément tous les seuils
- à ajouter des couches mathématiques sans rendement économique
- à utiliser RL ou POMDP comme substitut à un edge réel

La V5.3 cherche :

- plus de **fréquence utile**
- plus de **capital efficiency**
- plus de **diversité réelle d’edge**
- moins de **veto non fatals**
- plus de **discipline de coût**
- plus de **clarté d’implémentation**
- une vraie séparation entre :
  - sécurité
  - sélection
  - taille
  - exécution
  - gouvernance

---

# 4. Architecture cible complète

## 4.1 Vue d’ensemble

La V5.3 complète est définie comme un système :

- multi-paires : **12 paires**
- multi-moteurs : **4 moteurs**
- multi-couches :
  - Data / Ingestion
  - Data Quality
  - Microstructure
  - Regime
  - Signal
  - Scoring
  - Risk
  - Execution
  - Portfolio
  - Monitoring / Meta
  - Dependency Architecture

## 4.2 Les 12 paires cibles

### Classe A — piliers
1. BTC/USDT  
2. ETH/USDT  
3. BNB/USDT  
4. SOL/USDT  

### Classe B — actives et exploitables
5. XRP/USDT  
6. ADA/USDT  
7. LINK/USDT  
8. AVAX/USDT  

### Classe C — tactiques / encadrées
9. DOGE/USDT  
10. TRX/USDT  
11. TON/USDT  
12. DOT/USDT  

## 4.3 Les 4 moteurs cibles

### Moteur A — Premium Trend / Expansion
Héritier du moteur premium V5.2.  
Objectif : setups haute conviction, structure forte, qualité maximale.

### Moteur B — Mean Reversion Intraday
Objectif : capter des excès propres de court terme avec retour vers une moyenne locale.

### Moteur C — Breakout Continuation
Objectif : capter les sorties de range et expansions confirmées.

### Moteur D — Re-entry / Second Chance Logic
Objectif : réengager proprement un edge déjà validé, sans reconstruire un moteur entièrement séparé de conviction.

## 4.4 Principe central

L’architecture complète existe comme **cible produit**, mais la production peut être activée en **profil Light** ou **profil Complete** selon l’état de validation.

---

# 5. Profils officiels d’activation

## 5.1 Principe

Il n’existe pas plusieurs V5.3 documentaires.  
Il existe **une seule V5.3**, avec **deux profils d’activation officiels**.

## 5.2 Profil A — V5.3 Light

### Univers
- 6 paires maximum

### Moteurs autorisés
- Moteur A
- Moteur B

### Couches obligatoires
- Data engine
- Data quality
- Risk
- Execution
- Portfolio minimal
- T1 minimal
- T2 prudent
- T3 complet

### Objectif
- rentabilité robuste initiale
- validation de fréquence utile
- validation coût réel
- validation capital efficiency
- validation infra

### Interdictions
- moteurs C et D en live
- 12 paires complètes en live
- RL
- POMDP
- optimal stopping complet
- sophistication non nécessaire

## 5.3 Profil B — V5.3 Complete

### Univers
- 12 paires

### Moteurs autorisés
- A, B, C, D

### Couches autorisées
- orchestration portefeuille complète
- analytics plus riches
- sizing tiers complet
- corrélation complète
- monitoring enrichi

### Conditions d’accès
- Light validé
- coût réel stable
- fréquence utile validée
- capital efficiency positive
- budget corrélation maîtrisé
- infra stable
- pas de dérive de logs ni d’état

## 5.4 Runtime modes officiels

Les profils métier ne doivent jamais être confondus avec les contextes d’exécution.

Les seuls `runtime_mode` autorisés sont :

- `LOCAL_REPLAY`
- `SHADOW`
- `MICRO_LIVE`
- `LIVE`

Le pipeline canonique de promotion reste :

`classification -> versioning -> shared core -> LOCAL_REPLAY -> export artifact -> import VPS -> candidature contrôlée -> Shadow -> Micro-live -> Live`

## 5.5 Règle critique de lecture du canon

Le canon décrit la **cible complète** de la V5.3.

Il ne doit pas être lu comme :

- la preuve que Build-10 est déjà opéré
- la preuve que Build-11/12/13 sont déjà runtime-ready
- la preuve que `COMPLETE` est déjà exécutable
- la preuve que Build-9X ou `LOCAL_REPLAY` sont déjà codés

---

# 6. Interface utilisateur : logique d’activation

## 6.1 Ce que l’interface doit permettre

L’interface doit permettre :

- afficher le **profil actif**
- afficher l’**état de déploiement**
- charger un **profil validé**
- visualiser moteurs / paires autorisés
- activer ou désactiver une paire **seulement si autorisé par le profil**
- suspendre une paire ou un moteur
- lire les dashboards de risque, coût et santé

## 6.2 Ce que l’interface ne doit pas permettre

L’interface ne doit pas permettre :

- composer librement une V5.3 “hybride”
- activer 12 paires + 4 moteurs sans validation
- contourner les budgets de corrélation
- contourner les gates de merge
- contourner les hard blockers

## 6.3 États UI officiels

- SHADOW
- MICRO-LIVE
- LIVE-LIGHT
- LIVE-COMPLETE
- DEGRADED
- HALTED

---

# 7. Modules canoniques

## 7.1 data_engine
Rôle :
- ingestion WebSocket
- normalisation
- buffers
- heartbeats
- reconnexion
- diffusion interne

Entrées :
- flux exchange

Sorties :
- événements normalisés

Obligatoire :
- oui, Light et Complete

## 7.2 data_quality_engine
Rôle :
- qualité data
- stale detection
- score santé paire
- suspension contrôlée

Obligatoire :
- oui, Light et Complete

## 7.3 microstructure_engine
Rôle :
- OFI
- book imbalance
- microprice
- features de flux

Obligatoire :
- Light : version minimale
- Complete : version enrichie

## 7.4 regime_engine
Rôle :
- estimation de contexte marché
- gating contextuel
- segmentation utile de l’edge

Obligatoire :
- Light : version simple ou stable
- Complete : version plus riche

## 7.5 signal_engine
Rôle :
- générer les signaux par moteur

## 7.6 scoring_engine
Rôle :
- score brut
- pénalités
- hard / soft / rank

## 7.7 risk_engine
Rôle :
- budgets
- sizing
- gross exposure
- correlation budget
- drawdown protection

## 7.8 execution_engine
Rôle :
- ordres
- ack
- fills
- cost logging
- re-sync

## 7.9 portfolio_engine
Rôle :
- allocation capital
- budget BTC
- clusters de corrélation
- arbitrage des opportunités simultanées

## 7.10 monitoring_engine
Rôle :
- logs
- dashboards
- alertes
- infra health
- metrics de production

## 7.11 meta_engine
Rôle :
- DTR
- CRA
- AMD
- BEE prudent
- break-even réel
- pass-rate économique
- sterilization monitoring

## 7.12 dependency_architecture
Rôle :
- interfaces
- manifest
- DAG validator
- contract tests
- build order
- merge gates

---

# 8. Réforme décisionnelle : hard / soft / rank

C’est la réforme centrale de la V5.3.

## 8.1 Hard blockers

Seulement pour les risques fatals :
- data corrompue
- data stale sévère
- liquidité absente
- spread extrême
- santé paire dégradée
- budget risque dépassé
- état infra incohérent
- divergence critique d’état exécution

## 8.2 Soft penalties

Réduisent score ou taille :
- prudence contextuelle
- signal moins propre
- microstructure dégradée mais pas invalide
- qualité moyenne mais pas fatale
- volatilité défavorable mais pas interdite

## 8.3 Ranking features

Servent à classer les opportunités :
- qualité setup
- capital efficiency attendue
- propreté du flux
- coût anticipé
- rendement ajusté temps
- priorité moteur
- priorité paire

---

# 9. Moteurs : définition canonique

## 9.1 Moteur A — Premium Trend
Usage :
- Light : oui
- Complete : oui

Niveau de priorité :
- P0

But :
- conserver la haute conviction du cœur V5.2
- sans le rendre stérile

## 9.2 Moteur B — Mean Reversion Intraday
Usage :
- Light : oui
- Complete : oui

Niveau de priorité :
- P0

But :
- augmenter fréquence utile
- utiliser des retours courts et propres

## 9.3 Moteur C — Breakout Continuation
Usage :
- Light : non
- Complete : oui

Niveau de priorité :
- P1

But :
- exploiter les expansions confirmées

## 9.4 Moteur D — Re-entry / Second Chance
Usage :
- Light : non
- Complete : oui

Niveau de priorité :
- P1

But :
- réengager proprement un edge existant
- éviter la duplication conceptuelle inutile

---

# 10. Corrélation, facteur BTC, et faux multi-edge

## 10.1 Principe

Le système ne doit jamais confondre :

- multiplicité de paires
- multiplicité de moteurs
- diversification réelle

## 10.2 Règles obligatoires

- budget BTC explicite
- budget cluster corrélé
- budget moteurs corrélés
- \(K_{eff}\) suivi au niveau portefeuille
- exposition simultanée contrôlée

## 10.3 Contraintes minimales

Le portefeuille doit avoir :
- une exposition totale bornée
- une exposition corrélée bornée
- une exposition Tier 3 bornée
- une lecture explicite du facteur BTC

---

# 11. Mathématiques : classification officielle

Le système documente toute l’architecture mathématique, mais **tout n’est pas à implémenter immédiatement**.

## 11.1 NOW — à implémenter dans Light

- rendement net par trade
- coût total réel
- break-even prudent
- espérance / variance
- erreur standard prudente
- Sharpe par trade
- capital efficiency
- facteur BTC
- variance portefeuille
- budgets corrélation
- hard / soft / rank
- stale penalty
- santé paire
- charge streaming \(\lambda / \mu_s\)
- logs minimaux mathématiquement suffisants
- critères Phase 1

## 11.2 NEXT — à implémenter dans Complete

- microstructure enrichie
- OFI dynamique
- microprice
- covariance shrinkée type Ledoit-Wolf
- HMM enrichi pour régimes
- Kelly modifié très prudent
- critères Phase 2
- orchestration corrélation plus fine
- sizing tiers complet

## 11.3 RESEARCH — documenté, non requis pour la rentabilité initiale

- optimal stopping plus formel
- version hiérarchique plus riche du cadre bayésien
- POMDP comme cadre conceptuel
- RL allocation théorique hors prod
- recherche avancée d’allocation

## 11.4 FORBIDDEN FOR V5.3 PROD

- RL directionnel en production
- PPO / DQN pour la décision de trade live
- POMDP complet live
- sophistication mathématique sans lien direct avec coût réel, fréquence utile ou capital efficiency
- toute brique qui augmente fortement la complexité sans preuve économique

---

# 12. T1 / T2 / T3 — version canonique

## 12.1 T1 — Decision Trace Engine

Composants retenus :
- DTR
- CRA
- pass-rate économique
- phantom trade monitoring
- AMD conditionnel

Exigences prod-safe :
- aucune perte silencieuse de trace
- distinction évalué / non évalué / bloqué en amont
- distinction trade actif / phantom
- métriques exploitables économiquement

## 12.2 T2 — Bayesian Edge Protocol

Retenu comme :
- outil de gouvernance prudente
- pas comme oracle absolu

Briques retenues :
- edge tracker net
- break-even réel
- lecture hiérarchique prudente
- PDP comme gate de capital

Interdictions :
- prendre le posterior comme vérité absolue
- piloter seul les changements de moteur / logique live

## 12.3 T3 — Dependency Architecture

Retenu intégralement dès Light :
- interfaces
- manifest
- DAG validator
- contract tests
- build order
- checks runtime
- smoke tests

T3 est une exigence P0, pas un luxe.

---

# 13. Streaming 12 paires : architecture canonique

## 13.1 Découpage runtime conseillé

Processus 1 — Ingestion  
Processus 2 — Normalisation / buffers  
Processus 3 — Décision  
Processus 4 — Exécution / réconciliation  
Processus 5 — Monitoring / analytics

## 13.2 Principe

Le risque principal n’est pas “36 flux WebSocket” en soi.  
Le vrai risque est :

- coût de traitement par événement
- désynchronisation d’état
- saturation de queue
- latence cachée
- perte silencieuse de messages

## 13.3 Politique

- écouter seulement les flux utiles
- buffers bornés
- heartbeats
- reconnexion
- dégradation gracieuse par paire
- suspension d’une paire sans contamination du portefeuille

---

# 14. Logs et observabilité

## 14.1 Logs obligatoires

Chaque trade doit permettre de reconstruire :

- paire
- moteur
- régime
- score
- hard blockers
- pénalités
- multiplicateur
- taille
- coûts
- rendement brut
- rendement net
- durée
- âge de la donnée
- santé paire

## 14.2 Interdictions

- aucune perte silencieuse de logs critiques
- aucun DTR “best effort” silencieux
- aucun log minimaliste qui empêche un post-mortem quant

## 14.3 Dashboards minimums

### Dashboard portefeuille
- capital
- exposition
- PnL
- drawdown
- beta BTC
- capital efficiency

### Dashboard moteurs
- fréquence utile
- rendement net
- Sharpe
- coûts
- sterilization rate

### Dashboard paires
- santé
- coût
- latence
- fréquence
- qualité

### Dashboard infra
- charge streaming
- backlog
- reconnects
- qualité data
- pertes de messages / logs

---

# 15. Gates de merge prod-safe

Aucun module n’est mergeable sans :

1. interface gelée  
2. contract tests  
3. unit tests  
4. smoke test bootstrap  
5. smoke test recovery  
6. audit logique quant  
7. audit coût / risk si module concerné  

Chaque merge doit être :
- petit
- testable
- réversible

---

# 16. Ordre de développement canonique

## Phase Build-0 — fondations
- dependency architecture
- manifest
- interfaces
- conventions logs
- conventions tests

## Phase Build-1 — cœur Light
- data engine
- data quality
- execution minimal
- risk minimal
- portfolio minimal

## Phase Build-2 — moteurs Light
- moteur A
- moteur B
- scoring hard / soft / rank
- break-even réel
- capital efficiency

## Phase Build-3 — meta & monitoring
- DTR
- CRA
- dashboards
- pass-rate économique
- facteurs BTC / corrélation

## Phase Build-4 — validation Light
- shadow
- micro-live
- live-light

## Extension documentaire post-Build-9 — Build-9X
- diagnostic post-trade gouverné
- hypothesis registry
- breakdown reports
- replay bundles
- dépendance logique : Build-9
- dépendance opératoire forte : Build-10 + `LOCAL_REPLAY`
- aucun impact live direct
- aucune auto-modification live
- aucun fork local / VPS
- aucun nouveau profil métier
- statut : **documentaire uniquement à ce stade**

## Règle Build-14 / onboarding

Les enrichissements classés `Build14_enabler` :

- entrent d’abord en lecture seule
- peuvent ensuite avoir une influence limitée
- ne deviennent jamais des moteurs autonomes
- ne bypassent jamais A/B/C/D, le risk backbone, le portfolio ni les gates de promotion

## Phase Build-5 — extension Complete
- 12 paires
- moteurs C / D
- covariance robuste
- HMM enrichi
- sizing tiers complet
- orchestration complète

---

# 17. Go / No-Go Light

Le passage en LIVE-LIGHT n’est autorisé que si :

- coût réel estimé et stable
- fréquence utile > V5.2
- edge net > 0
- capital efficiency > V5.2
- santé infra stable
- logs / DTR fiables
- corrélation maîtrisée
- pas de stérilisation excessive

---

# 18. Go / No-Go Complete

Le passage en LIVE-COMPLETE n’est autorisé que si :

- Light rentable ou au moins économiquement crédible
- 6 paires déjà stables
- moteurs A / B validés
- coût additionnel des 6 paires restantes sous contrôle
- budget BTC / clusters maîtrisé
- K_eff augmente réellement
- moteurs C / D apportent soit alpha, soit diversification
- aucun backlog infra critique

---

# 19. Ce qui est explicitement interdit dans la V5.3 prod

- coder tout le système d’un bloc
- coder 12 paires + 4 moteurs sans phase Light validée
- utiliser plusieurs masters documentaires simultanés
- laisser Claude ou ChatGPT générer des modules sans tests et interfaces
- confondre document de recherche et spec d’implémentation
- prendre les annexes mathématiques comme mandat de coder tout ce qu’elles décrivent

---

# 20. Workflow IA officiel

## 20.1 ChatGPT Pro
Usage :
- architecture
- audit quant
- cohérence math
- risk review
- critique du design

## 20.2 Claude Pro
Usage :
- génération de code modulaire
- refactorisation
- documentation technique
- longues implémentations sous contraintes

## 20.3 Pipeline officiel

1. ChatGPT : architecture / module contract  
2. Claude : code du module  
3. ChatGPT : audit logique / quant / risk  
4. Claude : correction ciblée  
5. tests  
6. merge si gates passés  

---

# 21. Registre des risques canoniques

Risques à surveiller en permanence :

- non-stationnarité
- coût réel sous-estimé
- faux multi-edge
- facteur BTC caché
- faux signal microstructure
- drawdown psychologique
- stérilisation économique
- surcharge streaming
- stale data
- dérive documentaire
- sur-complexité développeur
- faux positifs statistiques
- panne de recovery
- mauvaise qualité de logs

---

# 22. Architecture mathématique canonique : résumé

Le projet doit être jugé par sa capacité à améliorer simultanément :

- fréquence utile
- edge net
- capital efficiency
- diversité réelle d’edge

tout en maîtrisant :

- variance
- coûts
- corrélation
- exposition systémique
- budget de perte
- saturation infra

---

# 23. Décision finale de cadrage

La V5.3 est donc définie comme :

### Une architecture cible complète à 12 paires / 4 moteurs
**documentée intégralement**

### avec deux profils officiels :
- Light
- Complete

### avec une implémentation autorisée :
- progressive
- testée
- auditée
- prod-safe

---

# 24. Statut des documents précédents

Les documents précédents deviennent :

- **sources de matière intégrée**
- ou **annexes archivées**
- ou **notes de recherche**

Aucun ne doit être utilisé comme source active concurrente à ce fichier.

---

# 25. Prochaines actions

1. Geler ce document comme base canonique  
2. Produire la table des modules avec :
   - inputs
   - outputs
   - dépendances
   - tests
   - logs  
3. Produire la table des moteurs avec :
   - logique
   - métriques
   - pairs autorisées
   - profil d’activation  
4. Produire la table UI :
   - écrans
   - boutons autorisés
   - états  
5. Produire les merge gates détaillés  

---

## Fin du document canonique
