# V5_3_MASTER_FINAL_CANONICAL
## Miroir documentaire secondaire — prod-safe
### Système quant crypto spot halal — V5.3
### Support développeur / quant / risk / infra aligné sur le master officiel unique
### Document miroir, non source de vérité autonome

---

# 0. Statut du document

Ce document est un **miroir documentaire secondaire** de la V5.3.

La **source de vérité unique** est `V5_3_MASTER_FINAL_UNIQUE.md`.

En cas de divergence :

- `V5_3_MASTER_FINAL_UNIQUE.md` prime immédiatement
- le présent document doit être corrigé ou relu comme simple miroir
- aucune table, annexe ou addendum ne peut se rattacher à ce document comme à une source autonome

## Règle absolue

Aucun développeur, aucune IA, aucun auditeur ne doit utiliser le présent document comme source de vérité autonome si son contenu diverge du `V5_3_MASTER_FINAL_UNIQUE.md`.

## 0.1 Statut documentaire vs réalité d’implémentation

Pour éviter toute sur-promesse :

- le **core Build-1 à Build-9** reste la base réellement exécutable / gelable
- **Build-10** dispose désormais d’une première implémentation codée côté monitoring backend et projection UI Light verrouillée
- **Build-9X** dispose désormais d’une première implémentation codée côté diagnostics, hypothèses, candidats et exports gouvernés
- **LOCAL_REPLAY** et l’import d’artifact disposent désormais de **scaffolds minimaux codés**, sans constituer encore un runtime complet opéré
- **Build-11 à Build-17** restent des étapes canoniques de validation et
  d'extension du rollout, pas des architectures concurrentes
- l'architecture complete doit etre lue comme la cible de reference deja
  documentee ; son activation reelle reste simplement gouvernee et progressive

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

## 0.3 Intégration des audits tiers — Principe officiel

Les audits tiers sont de la **matière de correction**, jamais une source de vérité active.
Chaque finding est classé (NOW_P0 / NOW_LIGHT / NEXT_BUILD14 / RESEARCH_LOCAL / REJECT) et absorbé dans le fichier MD cible.
Le rapport de triage officiel est `V5_3_AUDIT_INTEGRATION_DECISIONS.md`.

## 0.4 HARD STATE documentaire — Cycle de vie officiel

Chaque brique, build, moteur ou couche du système V5.3 est décrite par un **état officiel unique et non ambigu** :

| Hard State | Signification |
|---|---|
| `CODED` | Le code existe dans le dépôt |
| `DOCUMENTED` | La spécification canonique est écrite et cohérente |
| `SHADOW_ENABLED` | Activé à 100% en mode SHADOW, pleinement utilisé et observé |
| `SHADOW_VALIDATED` | Les 30 jours de Shadow sont terminés avec verdict positif |
| `MICRO_LIVE_ELIGIBLE` | Éligible au passage Micro-live après verdict Shadow |
| `LIVE_LIGHT_ELIGIBLE` | Éligible au passage Live-Light après Micro-live validé |
| `COMPLETE_ELIGIBLE` | Éligible au passage Live-Complete après Shadow Complete validé |
| `PROMOTED` | Activé en production dans le profil autorisé |
| `DORMANT` | Codé et documenté mais volontairement non activé |
| `FORBIDDEN` | Interdit en V5.3 prod (RL live, POMDP live, etc.) |

Règles :
- `CODED` ≠ `SHADOW_VALIDATED` ≠ `PROMOTED`
- `SHADOW_ENABLED` = activé à 100% et pleinement utilisé en Shadow, pas en lecture seule
- Build-14 `CODED` ≠ Build-14 `PROMOTED`
- Complete enablers `SHADOW_ENABLED` ≠ activation Complete live
- Activation en Shadow ≠ promotion automatique vers Live

## 0.6 HARD STATEMENT — Règle de promotion temporelle obligatoire

> **NON NÉGOCIABLE. Aucune dérogation, aucun raccourci, aucune exception.**

Toute la solution V5.3 (Light + Complete, Builds 1→17) est **codée intégralement**.
Mais le code existant ne donne **aucun droit de promotion automatique**.

### Pipeline de promotion hard

```
[TOUT CODÉ] → Light Shadow 30j → Light Live → Complete Shadow 30j → Complete Live
```

Note de lecture active :
- dans le code gouverné courant, les rails Build-11 / Build-12 / Build-13 s'ouvrent en `profil=COMPLETE`
- les libellés `Light Shadow`, `Light Live` et `Live-Light` ci-dessus doivent être lus comme des noms de phase historiques ou documentaires, pas comme la cible runtime gouvernée active

0. **Shadow = phase de vérité système complète** : pendant les 30 jours, la solution est testée dans sa forme complète utile. Build-14 activé à 100%, moteurs A/B/C/D actifs, tous les enrichissements observés. Le Shadow n'est plus une validation Light minimale.
1. **Light Shadow 30 jours** : Light trade en SHADOW sur données réelles pendant 30 jours calendaires consécutifs minimum. Build-14, C/D et enrichissements activés à 100% en Shadow. Interruption > 24h = compteur à zéro. Rapport shadow exploitable obligatoire incluant comparaison inter-moteurs et contribution Build-14.
2. **Verdict post-Shadow** : à l'issue des 30 jours, décision de promotion composant par composant. Activation Shadow ≠ promotion Live automatique. Possibilité de rollback, downgrade ou désactivation sélective.
3. **Light Live** : activation Live-Light uniquement après les 30 jours de shadow validés et verdict positif.
4. **Complete Shadow 30 jours** : Complete trade en SHADOW pendant 30 jours calendaires consécutifs minimum, en parallèle de Light live. Non-régression Light obligatoire. Dégradation = désactivation + compteur à zéro.
5. **Complete Live** : activation Live-Complete uniquement après les 30 jours de shadow Complete validés + rapport comparatif Light vs Complete approuvé.

**Aucun opérateur, aucune IA, aucun audit ne peut bypasser ces délais. L'activation complète en Shadow est un essai structuré, pas une promotion déguisée.**

## 0.5 Guardrails P0 issus des audits (invariants système)

1. **Crossed book** : DepthEvent doit valider `best_ask >= best_bid`
2. **Epsilon risk/reward** : `risk < 1e-6 → None`
3. **Imports dynamiques** : DAG validator signale `importlib.import_module` comme wildcard
4. **Recovery backoff** : exponential backoff + vérification libération ressources I/O
5. **Buffer drop_oldest** : deque(maxlen=K), jamais drop_newest
6. **Jitter tolerance** : fenêtre configurable (5-10ms) avant TIMESTAMP_REVERSAL
7. **Latence monotone** : clock monotone, filtrage valeurs aberrantes
8. **Kill switch persistant** : état circuit breaker persisté sur disque (écriture atomique)
9. **Persistance atomique** : write-tmp-then-rename pour tout état critique
10. **Stale guard runtime** : rejet si delta exchange_time vs local_time > seuil
11. **Persistance minimale stores critiques** : flush périodique DTR, états portefeuille, logs audit
12. **Kill switch externe** : mécanisme hors processus Python (fichier flag ou API admin)

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

- respect de la source de vérité unique portée par `V5_3_MASTER_FINAL_UNIQUE.md`
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

La V5.3 est documentee comme une **solution complete cible unique**.

`LIGHT` et `COMPLETE` ne decrivent pas deux architectures differentes.
Ils decrivent deux **enveloppes officielles de rollout et d'activation reelle**
d'une meme architecture complete, prod-safe et gouvernee.

Cela implique explicitement :

- l'architecture de reference couvre 12 paires cibles, 4 moteurs A/B/C/D,
  une UI capable de superviser l'etat complet, et des protocoles complets
  de risque, d'execution, de journalisation et de rollback
- le deploiement reel initial reste borne a 6 paires
- l'activation reelle des moteurs reste gouvernee par gates, budgets,
  observabilite et valeur marginale demontree
- C et D ne sont pas interdits par principe dans la doctrine cible
- aucun profil custom n'est autorise

---

# 5. Profils officiels de rollout et d’activation

## 5.1 Principe

Il n’existe pas plusieurs V5.3 documentaires.
Il existe **une seule V5.3**, avec **deux enveloppes officielles de rollout**.

La difference entre `LIGHT` et `COMPLETE` porte sur :

- la borne de paires activables en production
- l'ampleur de l'activation reelle deja autorisee
- le niveau de preuve exige pour etendre le rollout

Elle ne porte pas sur l'existence doctrinale des modules, moteurs, UI et
protocoles de la solution de reference.

## 5.2 Profil A — V5.3 Light

### Finalite
- premier rollout reel prudent et gouverne
- validation economique et operationnelle sur un univers borne
- verification que l'architecture complete reste prod-safe en conditions reelles

### Architecture disponible
- modules complets de la V5.3
- moteurs A, B, C et D presents dans la solution de reference
- UI et supervision capables d'afficher les etats disponible / arme / actif /
  borne / suspendu / non deploye
- protocoles complets de risque, execution, observabilite et rollback

### Bornes runtime initiales
- 6 paires maximum en production reelle
- activation reelle borne par paire, moteur, budget et regime
- A et B constituent le coeur attendu du rollout live initial
- **C, D et Build-14 sont activés à 100% pendant le Shadow 30 jours** : scorés, classés, arbitrés, observés et comparés à A/B
- promotion live de C/D conditionnelle au verdict post-Shadow (non automatique)
- chaque composant suit le cycle Hard State : `SHADOW_ENABLED` → verdict → `SHADOW_VALIDATED` ou `DORMANT`

### Exigences obligatoires
- data engine
- data quality
- risk backbone complet et non contournable
- execution et reconciliation completes
- portfolio complet gouverne
- T1 prudent
- T2 prudent
- T3 complet mais strictement borne par budget
- logs, DTR, alerting et rollback auditables

### Interdictions
- profil custom
- activation reelle au-dela des gates ou des budgets
- ouverture > 6 paires sans validation de rollout
- activation de C ou D sans preuve marginale, sans observabilite ou sans plan
  de desactivation
- RL directionnel live
- POMDP live
- sophistication opaque sans valeur prod-safe demontree

## 5.3 Profil B — V5.3 Complete

### Finalite
- extension gouvernee du rollout de la meme architecture complete
- passage progressif de 6 vers 8/10 puis 12 paires
- activation reelle elargie des moteurs et des capacites enrichies

### Enveloppe cible
- jusqu'a 12 paires actives
- A, B, C et D activables sous gouvernance
- orchestration portefeuille complete
- analytics enrichis
- sizing tiers complet
- correlation et contribution risque completes
- monitoring enrichi et pilotable sans opacite

### Conditions d’acces
- rollout LIGHT stable sur 6 paires
- cout reel stable
- frequence utile et edge net credibles
- capital efficiency positive ou degradation explicitement justifiee
- budget correlation maitrise
- infra stable
- pas de derive de logs ni d'etat
- preuve que l'extension ne cree pas de faux sentiment de diversification
- preuve que C et D ont une valeur marginale et restent desactivables proprement

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
- la preuve que Build-9X ou `LOCAL_REPLAY` sont déjà complets, opérés de bout en bout ou validés pour Build-11+
- la preuve que les libellés historiques `Light Shadow` / `Live-Light` décrivent encore la cible runtime gouvernée active

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
- LIGHT : base gouvernée compatible rollout initial
- COMPLETE : couche enrichie gouvernée

## 7.4 regime_engine
Rôle :
- estimation de contexte marché
- gating contextuel
- segmentation utile de l’edge

Obligatoire :
- LIGHT : version gouvernée pour rollout initial
- COMPLETE : version enrichie si stable et utile

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
- LIGHT : oui, coeur attendu du rollout initial
- COMPLETE : oui, enveloppe elargie

Niveau de priorité :
- P0

But :
- conserver la haute conviction du cœur V5.2
- sans le rendre stérile

## 9.2 Moteur B — Mean Reversion Intraday
Usage :
- LIGHT : oui, coeur attendu du rollout initial
- COMPLETE : oui, enveloppe elargie

Niveau de priorité :
- P0

But :
- augmenter fréquence utile
- utiliser des retours courts et propres

## 9.3 Moteur C — Breakout Continuation
Usage :
- LIGHT : activable seulement sous gates specifiques, budget cout et
  observabilite renforces
- COMPLETE : oui, enveloppe elargie si valeur marginale demontree

Niveau de priorité :
- P1

But :
- exploiter les expansions confirmées

## 9.4 Moteur D — Re-entry / Second Chance
Usage :
- LIGHT : activable seulement sous gates specifiques, budget correlation et
  discipline de re-entry explicites
- COMPLETE : oui, enveloppe elargie si valeur marginale demontree

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

Le systeme documente toute l'architecture mathematique.
La difference canonique porte sur l'ordre de verification et d'activation
reelle, pas sur l'existence doctrinale des composants.

## 11.1 Obligatoire avant rollout reel initial

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

## 11.2 Obligatoire avant extension gouvernée du rollout

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

## Phase Build-1 — socle commun de la solution complete
- data engine
- data quality
- execution backbone
- risk backbone
- portfolio gouverne

## Phase Build-2 — moteurs du rollout initial
- moteur A
- moteur B
- scoring hard / soft / rank
- break-even réel
- capital efficiency

## Phase Build-3 — monitoring, meta et pilotage prod-safe
- DTR
- CRA
- dashboards
- pass-rate économique
- facteurs BTC / corrélation

## Phase Build-4 — rollout réel initial borné
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

- sont **activés à 100% en Shadow** (`SHADOW_ENABLED`) : pleinement utilisés, tracés, auditables
- promotion live non automatique : soumis au verdict post-Shadow
- ne deviennent jamais des moteurs autonomes
- ne bypassent jamais A/B/C/D, le risk backbone, le portfolio ni les gates de promotion

## Phase Build-5 — extension gouvernée de la meme architecture
- montée 6 -> 8/10 -> 12 paires
- activation réelle élargie de C / D si gates passées
- covariance robuste
- HMM enrichi
- sizing tiers complet
- orchestration complète

---

# 17. Go / No-Go LIGHT — rollout reel initial

Le passage en LIVE-LIGHT n’est autorisé que si :

- coût réel estimé et stable
- fréquence utile > V5.2
- edge net > 0
- capital efficiency > V5.2
- santé infra stable
- logs / DTR fiables
- corrélation maîtrisée
- pas de stérilisation excessive
- architecture complete toujours gouvernee et observable
- aucun angle mort critique non traite n'est laisse hors surveillance

---

# 18. Go / No-Go COMPLETE — extension gouvernee du rollout

Le passage en LIVE-COMPLETE n’est autorisé que si :

- LIGHT rentable ou au moins économiquement crédible
- 6 paires déjà stables
- coût additionnel des paliers 6 -> 8/10 -> 12 sous contrôle
- budget BTC / clusters maîtrisé
- K_eff augmente réellement
- moteurs C / D apportent soit alpha, soit diversification
- aucun backlog infra critique
- aucune inflation de complexité UI ou de veto non gouvernée
- aucun contournement opérateur possible

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

# 21. Registre des risques canoniques et angles morts

Chaque angle mort ci-dessous doit etre traite explicitement par la doctrine,
les gates, les tests et la supervision runtime.

- duplication A vs C : risque de faux nouveau moteur ; impact = sur-activation
  et faux multi-edge ; garde-fou = test de non-duplication, budget cout,
  comparaison alpha marginal ; signal = correlation inter-moteurs, gain marginal
- duplication A vs D : risque de re-entry redondant ; impact = concentration
  cachee ; garde-fou = budget correlation libre, historique trade-aware,
  desactivation ; signal = concentration moteur/paire, CE marginale
- B contre vraie cassure : risque de mean reversion toxique ; impact = pertes
  contre breakout reel ; garde-fou = hard blockers regime/cout ; signal =
  taux de fade toxique, drawdown par regime
- C declenche trop tard : risque de breakout deja trop couteux ; impact =
  destruction de l'edge ; garde-fou = gate cout/slippage ; signal = cout de
  capture, faux breakout, rendement net C
- D derive en surconcentration : risque de re-entry agressif ; impact = budget
  portefeuille consomme sans diversite ; garde-fou = cap par paire/moteur,
  re-entry budget ; signal = exposition marginale, drawdown conditionnel
- illusion de diversite d'edge : risque de pluralite nominale sans vraie
  diversification ; impact = faux sentiment de securite ; garde-fou =
  K_eff, budget cluster, contribution risque ; signal = facteur BTC cache,
  correlation portefeuille
- cout implicite destructeur : risque de frequence non rentable ; impact =
  edge net negatif ; garde-fou = cout reel suivi et gates go/no-go ; signal =
  cout moyen/p90, break-even prudent, CE
- latence, backlog, stale : risque de runtime qui degrade sans alerte ; impact
  = decisions obsoletes ; garde-fou = charge streaming, stale gates,
  degradation gracieuse ; signal = lambda/mu_s, backlog, stale rate
- desalignement etat local / exchange : risque de reconciliation fausse ;
  impact = execution incoherente ; garde-fou = reconciliation stricte,
  recovery et HALTED ; signal = ecarts d'etat, erreurs de recovery
- inflation de veto ou de complexite UI : risque de systeme prod-safe en
  theorie mais inoperable ; impact = alertes noyees ou sterilisation ; garde-
  fou = UI gouvernee, review d'ergonomie critique ; signal = sterilization
  rate, alert fatigue, overrides demandes
- contournement operateur : risque de bypass manuel ; impact = rupture de
  gouvernance ; garde-fou = pas d'override non journalise ; signal = journal
  d'actions admin, refus traces
- derive documentaire : risque d'ecart entre architecture, rollout,
  manifests et runtime ; impact = incoherence de production ; garde-fou =
  source canonique unique et revue croisee ; signal = diff doctrinal,
  contradiction master/build/gates

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

### avec deux enveloppes officielles de rollout :
- LIGHT = rollout réel initial prudent et borne
- COMPLETE = extension gouvernée du meme systeme

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

---

# 26. Build-14 — Conditions d'activation et de promotion

Build-14 est **activé à 100% en Shadow** (`SHADOW_ENABLED`) : pleinement utilisé dans les décisions Shadow, tracé, comparé, auditable.
Sa promotion live reste non automatique : soumise au verdict post-Shadow.
Jamais un hard blocker central en live sans verdict. Jamais une activation implicite de Complete.
Non-régression Light obligatoire : tout enrichissement qui dégrade les métriques Light est désactivé.

Hard State : `CODED` → `SHADOW_ENABLED` → verdict → `SHADOW_VALIDATED` ou `DORMANT`

**HARD STATEMENT** : Light doit avoir tradé en shadow complet 30 jours consécutifs minimum (A/B/C/D + Build-14 à 100%) avant toute activation live.
**HARD STATEMENT** : Complete doit avoir tradé en shadow 30 jours consécutifs minimum (après Light live stable) avant toute activation live Complete.
**HARD STATEMENT** : Tout le code est implémenté, mais le code ne donne aucun droit de promotion automatique. L'activation complète en Shadow est un essai structuré, pas une promotion déguisée.

---

# 27. Protocole d'intégration des audits

1. Freeze documentaire → 2. Triage findings → 3. Patch builds P0 → 4. Réalignement docs → code → 5. Interdiction promotion implicite → 6. Requalification builds 1→14

---

## Fin du document canonique
