> STATUT : ARCHIVE DE TRAVAIL CONCATÉNÉE, NON CANONIQUE.
> Les sources canoniques séparées priment :
> - V5_3_UNIFIED_LOCAL_VPS_BACKTEST_ARCHITECTURE_PLAN_V2.md
> - V5_3_BUILD14_AI_EDGE_AND_MICROSTRUCTURE_ENRICHMENT_ADDENDUM.md
> - V5_3_STRATEGY_ONBOARDING_PROTOCOL.md

# V5.3 — UNIFIED LOCAL/VPS BACKTEST ARCHITECTURE PLAN — V2
## Plan unifié d’architecture locale/VPS pour backtest, replay, import et gouvernance
### Document d’implémentation dérivé du master canonique V5.3
### Sans code — prod-safe

---

# 0. Statut du document

- Statut : PLAN D’ARCHITECTURE V2
- Portée : définir comment la V5.3 doit fonctionner sur PC local et sur VPS sans divergence de logique
- Nature : plan d’implémentation dérivé des documents canoniques V5.3
- Objectif : unifier
  - le runtime local de replay/backtest
  - le runtime VPS Shadow/Micro-live/Live
  - le module d’import d’artifacts
  - la gouvernance manifest/DAG/contracts
- Hors périmètre :
  - création d’une seconde V5.3
  - création d’un nouveau profil métier
  - exécution de code stratégie arbitraire sur la VPS
  - bypass des builds officiels de validation

## 0.1 Règle de hiérarchie documentaire

Ce document **ne remplace pas** le master canonique V5.3.

Il doit être compris comme :
- un plan d’implémentation
- un addendum d’architecture
- une clarification locale/VPS/backtest

En cas de conflit :
1. le master canonique prime
2. le build plan officiel prime
3. les specs de build officielles priment
4. ce document sert à organiser l’implémentation sans contredire le canon

---

# 1. Problème à résoudre

Le projet a besoin de backtests réellement représentatifs, mais il ne peut pas accepter :

- une logique locale différente de la logique VPS
- un HMM local différent
- des kills locaux différents
- des features ou équations locales qui n’existent pas dans le runtime V5.3
- des coûts de backtest décoratifs différents du shadow prudent
- un chemin permissif où un résultat local devient quasi-live sans protocole officiel

Le risque central est simple :

> si le backtest local n’est pas la même V5.3 que la VPS, alors il produit une validation économiquement et opérationnellement trompeuse.

---

# 2. Décision d’architecture centrale

## 2.1 Décision retenue

Le backtest local doit être :

> **la même V5.3 que la VPS, exécutée en mode `LOCAL_REPLAY`**

et non :
- un ancien moteur V1 séparé
- un script de recherche ressemblant à V5.3
- un shadow bricolé
- une seconde architecture parallèle

## 2.2 Conséquence

Le projet doit conserver :

- **une seule base de code V5.3**
- **une seule vérité documentaire canonique**
- **deux profils métier officiels uniquement**
  - `LIGHT`
  - `COMPLETE`

et ajouter à côté des **modes runtime** :

- `LOCAL_REPLAY`
- `SHADOW`
- `MICRO_LIVE`
- `LIVE`

## 2.3 Interdiction critique

Ne pas créer :
- `BACKTEST_PROFILE`
- `LOCAL_PROFILE`
- `PC_PROFILE`
- `RESEARCH_PROFILE`

Local/VPS n’est pas un profil.
C’est un **mode runtime / target d’exécution**, pas un troisième axe métier concurrent au master.

---

# 3. Principe d’identité logique

À données équivalentes, paramètres équivalents et conditions de replay équivalentes :

> la V5.3 locale et la V5.3 VPS doivent produire les mêmes décisions logiques.

Cela inclut :
- mêmes features
- mêmes équations
- même HMM / logique régime
- mêmes hard blockers
- mêmes pénalités
- même scoring
- même risk backbone
- même logique portefeuille
- même discipline de coût prudent
- même décision trade / no-trade

Les différences acceptables portent seulement sur :
- la source des données
- l’horloge
- l’adapter d’exécution
- la densité d’observabilité
- le réel vs simulé pour l’exécution

---

# 4. Vue cible d’architecture

```text
                     ┌──────────────────────────────────┐
                     │        V5.3 SHARED CORE          │
                     │----------------------------------│
                     │ interface_contracts              │
                     │ manifest_registry                │
                     │ dag_validator                    │
                     │ data backbone                    │
                     │ data quality backbone            │
                     │ microstructure / regime          │
                     │ signal engines                   │
                     │ scoring backbone                 │
                     │ risk backbone                    │
                     │ portfolio engine                 │
                     │ meta logic                       │
                     │ monitoring contracts             │
                     └────────────────┬─────────────────┘
                                      │
                 ┌────────────────────┴────────────────────┐
                 │                                         │
   ┌──────────────────────────────┐        ┌──────────────────────────────┐
   │       VPS RUNTIME            │        │     LOCAL REPLAY RUNTIME     │
   │------------------------------│        │------------------------------│
   │ runtime_mode=SHADOW          │        │ runtime_mode=LOCAL_REPLAY    │
   │ runtime_mode=MICRO_LIVE      │        │ replay_clock                 │
   │ runtime_mode=LIVE            │        │ historical_data_gateway      │
   │ websocket_gateway            │        │ replay_event_router          │
   │ rest_bootstrap               │        │ shadow_execution_simulator   │
   │ live/shadow execution        │        │ artifact_exporter            │
   │ ops persistence              │        │ local persistence            │
   └──────────────────────────────┘        └──────────────────────────────┘

                                      │
                                      ▼
                 ┌────────────────────────────────────────────┐
                 │     BACKTEST ARTIFACT IMPORT (VPS)         │
                 │--------------------------------------------│
                 │ validation                                 │
                 │ register / lifecycle                       │
                 │ UI / Meta / Monitoring projections         │
                 │ no execution, no auto-promotion            │
                 └────────────────────────────────────────────┘
```

---

# 5. Shared core obligatoire

Les briques suivantes doivent être partagées sans fork logique entre local et VPS :

- `interface_contracts`
- `manifest_registry`
- `dag_validator`
- `websocket/data contracts`
- `event_normalizer`
- `freshness_checker`
- `consistency_checker`
- `pair_health_scorer`
- `microstructure_engine`
- `regime_engine`
- `raw_score_builder`
- `penalty_aggregator`
- `hard_block_gate`
- `ranking_router`
- `exposure_budgeter`
- `loss_budgeter`
- `btc_factor_guard`
- `correlation_cluster_guard`
- `order_decider`
- `fill_tracker` (parties compatibles runtime)
- `execution_cost_meter`
- `reconciliation_layer` (parties compatibles)
- `opportunity_selector`
- `allocation_router`
- `dtr_core`
- `cra_monitor`
- `break_even_dashboard`
- `edge_tracker_prudent_minimal`
- modules moteurs A/B, puis plus tard C/D selon le profil

## 5.1 Invariant

Aucun de ces modules ne doit exister en double version :
- une version “PC”
- une version “VPS”
- une version “backtest”
- une version “live”

Le code métier doit rester unique.

---

# 6. Ce qui peut différer entre PC et VPS

## 6.1 Sources de données

### VPS
- `websocket_gateway`
- `rest_bootstrap`

### Local replay
- `historical_data_gateway`
- `historical_snapshot_loader`
- `replay_event_router`

## 6.2 Horloge

### VPS
- temps réel ou quasi-live

### Local replay
- `replay_clock`
- accélération temporelle
- chunking
- relance contrôlée

## 6.3 Exécution

### VPS Shadow
- exécution simulée prudente sur flux live/quasi-live

### VPS Micro-live / Live
- exécution réelle exchange

### Local replay
- `shadow_execution_simulator`
- même philosophie prudente que Shadow
- pas d’exécution parfaite

## 6.4 Observabilité

### VPS
- monitoring actif
- alertes
- UI opérateur
- supervision continue

### Local replay
- monitoring allégé ou batchable
- export de rapports
- UI live facultative
- diagnostics de parité

---

# 7. Relation entre Local Replay et Shadow

## 7.1 Principe

Le local replay doit réutiliser la **même logique** que le Shadow Light.

Cela signifie :
- mêmes no-trade
- mêmes hard blockers
- mêmes pénalités
- mêmes seuils de coût prudent
- mêmes décisions moteur A/B
- même arbitrage portefeuille
- même logique de stérilisation
- même break-even prudent

## 7.2 Ce que le local replay n’est pas

Le local replay n’est pas :
- le protocole Shadow opérationnel brut utilisé tel quel sur des années d’historique
- un simple backtest candle-only
- un simulateur PnL détaché du scoring/risk/portfolio

## 7.3 Formulation correcte

Le local replay doit être :

> un **runner historique accéléré shadow-compatible**
> utilisant le même shared core que le Shadow,
> mais avec des adapters historiques et une horloge accélérée.

---

# 8. Interdiction explicite de bypass Build-11 / Build-12 / Build-13

## 8.1 Règle critique

Le `LOCAL_REPLAY` ne remplace pas :
- Build-11 `SHADOW`
- Build-12 `MICRO_LIVE`
- Build-13 `LIVE_LIGHT`

## 8.2 Conséquence

Un excellent résultat de replay local ne donne jamais directement :
- l’autorisation Shadow
- l’autorisation Micro-live
- l’autorisation Live-Light

## 8.3 Pipeline officiel conservé

L’ordre officiel reste :

1. shared core + builds canoniques
2. Shadow Light
3. Micro-live Light
4. Live-Light
5. Complete enablers
6. moteurs C/D
7. Live-Complete

## 8.4 Mission du replay local

Le replay local sert à :
- diagnostiquer
- accélérer les itérations
- comparer des versions
- mesurer la parité logique
- produire des artifacts
- préparer les revues

Il ne sert pas à sauter les gates de vérité opérationnelle réelle.

---

# 9. Stratégies, features, équations, HMM

## 9.1 Source de vérité unique

Les stratégies ne doivent pas vivre en parallèle dans :
- un plugin local libre
- un notebook isolé
- un script de backtest spécial
- un export de résultats sans contrat
- un HMM local expérimental non intégré

## 9.2 Tous les éléments suivants doivent être versionnés

- `strategy_version`
- `feature_set_version`
- `formula_set_version`
- `scoring_version`
- `regime_version`
- `risk_policy_version`
- `cost_model_version`

## 9.3 Invariant anti-fork

Une feature, une formule ou un paramètre HMM utilisé en replay local ne peut pas exister uniquement localement.

Tout élément décisif doit être :
- déclaré
- versionné
- testé
- intégré au shared core
- compatible avec le runtime VPS

## 9.4 Règle de promotion

Nouvelle formule / feature :
1. définition versionnée
2. intégration dans le shared core
3. tests
4. audit logique
5. validation replay
6. candidature Shadow éventuelle
7. protocole officiel ensuite seulement

---

# 10. Runtime modes officiels

## 10.1 Modes autorisés
- `LOCAL_REPLAY`
- `SHADOW`
- `MICRO_LIVE`
- `LIVE`

## 10.2 Exemple de combinaison correcte
- `profile_scope=LIGHT`, `runtime_mode=LOCAL_REPLAY`
- `profile_scope=LIGHT`, `runtime_mode=SHADOW`
- `profile_scope=LIGHT`, `runtime_mode=MICRO_LIVE`
- `profile_scope=LIGHT`, `runtime_mode=LIVE`
- `profile_scope=COMPLETE`, `runtime_mode=LOCAL_REPLAY` (plus tard, si validé)

## 10.3 Combinaisons interdites
- `profile_scope=BACKTEST`
- `profile_scope=LOCAL`
- `runtime_mode=COMPLETE`
- `runtime_mode=PROFILE_LIGHT`

---

# 11. Performance du local replay

## 11.1 Objectif

Le local replay doit permettre des backtests historiques massifs.

Mais la performance ne doit jamais être obtenue en simplifiant la logique métier.

## 11.2 Les gains autorisés viennent de :
- l’adapter historique
- l’horloge accélérée
- le pré-calcul/caching
- le chunking temporel
- la parallélisation prudente
- l’allègement des logs et de l’observabilité non critique

## 11.3 Les gains interdits viennent de :
- kills désactivés
- HMM simplifié
- scoring modifié
- risk contourné
- portefeuille contourné
- coût prudent supprimé
- ordre des décisions changé

## 11.4 Deux modes de performance recommandés

### `shadow_fidelity_mode`
- fidélité maximale
- diagnostic riche
- vitesse secondaire

### `research_fast_mode`
- accélération des runs massifs
- réduction d’I/O et de logs
- mêmes décisions métier
- artifact exportable et traçable

## 11.5 Règle absolue

`research_fast_mode` peut alléger :
- fréquence de logs
- snapshots intermédiaires
- UI live
- monitoring non critique

`research_fast_mode` ne peut pas changer :
- les décisions
- les refus
- les coûts prudents logiques
- l’ordre de sélection
- l’identité des signaux retenus

---

# 12. Package local replay recommandé

```text
src/local_replay_runtime/
├── __init__.py
├── contracts.py
├── enums.py
├── errors.py
├── replay_clock.py
├── historical_data_gateway.py
├── historical_snapshot_loader.py
├── replay_event_router.py
├── replay_session_config.py
├── replay_run_manifest.py
├── replay_state_store.py
├── shadow_execution_simulator.py
├── replay_metrics_collector.py
├── replay_dtr_exporter.py
├── artifact_exporter.py
├── performance_mode_guard.py
├── run_consistency_guard.py
└── replay_orchestrator.py
```

## 12.1 Principe de design
Ces composants doivent être :
- fins
- explicites
- déterministes
- centrés runtime
- sans duplication de logique métier

---

# 13. `shadow_execution_simulator`

## 13.1 Mission

Le local replay doit utiliser un simulateur d’exécution prudent, aligné avec le Shadow.

## 13.2 Il doit intégrer au minimum
- spread plausible
- slippage prudent
- pénalité de latence simulée
- non-remplissage possible
- partial fills plausibles si supportés
- refus de trades économiquement absurdes
- calcul cohérent du coût attendu

## 13.3 Interdictions
Interdiction de supposer :
- exécution parfaite
- coût nul
- latence nulle
- carnet infini
- fill systématique

---

# 14. Artifact export local → import VPS

## 14.1 Rôle du local replay

Le local replay produit un artifact standardisé.

## 14.2 Rôle du module d’import

Le module `backtest_artifact_import` côté VPS :
- valide l’artifact
- le parse
- le mappe au canon V5.3
- l’enregistre dans un registre
- produit des projections UI / Meta / Monitoring
- ne calcule pas le backtest
- n’exécute pas la stratégie
- n’active pas Shadow
- ne remplace pas les protocoles officiels

## 14.3 Position correcte du module import

Le module d’import est une brique de :
- gouvernance
- observabilité
- intégration
- consultation

Il n’est pas :
- un moteur
- un protocole Shadow
- une passerelle de promotion automatique

---

# 15. Contrat minimal d’un run local

Chaque run local doit porter au minimum :

- `run_id`
- `strategy_id`
- `strategy_version`
- `profile_scope`
- `runtime_mode = LOCAL_REPLAY`
- `engine_scope`
- `tested_pairs`
- `dataset_manifest_id`
- `timeframe_scope`
- `feature_set_version`
- `formula_set_version`
- `scoring_version`
- `regime_version`
- `risk_policy_version`
- `cost_model_version`
- `performance_mode`
- `artifact_schema_version`
- `artifact_hash`

Et produire au minimum :
- résumé de métriques
- agrégats par paire
- agrégats par moteur
- historique de décisions suffisant
- DTR / raisons structurées
- logs de refus pertinents
- informations de coût
- informations de drawdown
- contribution portefeuille

---

# 16. Diagnostics de parité obligatoires

Le système doit rendre possible au minimum :

- comparaison `LOCAL_REPLAY` vs `SHADOW`
- distribution des hits de gates
- comparaison des no-trade
- comparaison du ranking
- comparaison des coûts prudents
- comparaison des décisions finales
- rapport de divergence par paire / moteur / régime

## 16.1 Mission

Ces diagnostics servent à mesurer :
- la fidélité du replay
- les écarts résiduels
- les zones où le système dérive
- les hypothèses trop optimistes

## 16.2 Interdiction

Un écart de parité ne doit jamais être traité comme “normal par défaut”.
Il doit être visible, codé et explicable.

---

# 17. Manifest / DAG / contracts

## 17.1 Modules à officialiser

Le manifest doit pouvoir enregistrer au minimum :

- `local_replay_runtime`
- `shadow_execution_simulator`
- `artifact_exporter`
- `backtest_artifact_import`

## 17.2 Dépendances autorisées
- `interface_contracts`
- `manifest_registry`
- `dag_validator`
- modules canoniques du shared core
- utilitaires déterministes de config / persistence / logs

## 17.3 Dépendances interdites
- code stratégie externe libre
- notebooks comme source de vérité
- plugin non versionné
- second moteur A/B local distinct
- code arbitraire exécuté côté VPS

## 17.4 Règle DAG

Le `dag_validator` doit refuser :
- toute duplication de logique métier dans `local_replay_runtime`
- toute dépendance cachée du module d’import vers les moteurs runtime
- toute tentative de second core décisionnel
- tout chemin de promotion implicite vers Shadow / Live

---

# 18. Si le repo actuel n’a codé que Build-1 à Build-6

## 18.1 Situation

Dans ce cas :
- Build-7 n’est pas encore opérationnel
- Build-8 n’est pas encore opérationnel
- Build-9 n’est pas encore opérationnel
- Build-10 n’est pas encore opérationnel
- Build-11 n’est pas encore opérationnel

## 18.2 Conséquence

Il faut tout de même figer l’architecture maintenant, mais phaser l’implémentation.

## 18.3 Phase A — maintenant
- ajouter ce plan d’architecture
- ajouter les entrées manifest
- ajouter les contrats runtime
- créer les stubs des adapters locaux
- figer les invariants anti-fork
- préparer le module d’import de manière isolée

## 18.4 Phase B — quand les builds existent réellement
- brancher B quand Build-7 existe
- brancher portfolio quand Build-8 existe
- brancher Meta quand Build-9 existe
- brancher Monitoring/UI quand Build-10 existe
- aligner le replay avec Shadow quand Build-11 existe

## 18.5 Interdiction

Ne pas simuler faussement Build-8/9/10/11 si le repo ne les a pas encore codés.

---

# 19. Tests obligatoires

## 19.1 Tests d’identité logique
- même input historique -> mêmes décisions répétées
- même config -> mêmes hard blockers
- même config -> mêmes pénalités
- même config -> même ranking
- même config -> mêmes tailles finales si déterminisme attendu

## 19.2 Tests anti-fork
- divergence feature/version rejetée
- divergence HMM/version rejetée
- formule non enregistrée rejetée
- mode rapide qui change les décisions rejeté

## 19.3 Tests runtime local
- bootstrap OK
- bootstrap FAIL si config critique absente
- recovery OK
- chunk replay OK
- export artifact OK
- hash stable
- artifact importable côté VPS

## 19.4 Tests module import
- bundle complet accepté
- bundle incomplet rejeté
- collision explicite détectée
- idempotence vérifiée
- projections minimales produites
- aucune promotion implicite

## 19.5 Tests de performance
- run court en mode fidélité OK
- run massif en mode rapide OK
- fidélité vs rapide -> mêmes décisions métier
- mémoire acceptable
- I/O contrôlés

---

# 20. Merge gates spécifiques à cette architecture

Refuser le merge si :
- un nouveau profil a été créé au lieu d’un `runtime_mode`
- la logique métier est dupliquée côté replay
- le replay change les décisions du shared core
- le mode rapide change le résultat logique
- le module import exécute ou recalcule la stratégie
- l’export artifact n’est pas versionné
- le manifest n’est pas mis à jour
- le DAG ne protège pas contre les forks
- une promotion implicite vers Build-11/12/13 est introduite

---

# 21. Instructions directes à Claude

Tu dois mettre à niveau l’architecture V5.3 pour permettre :
- un `LOCAL_REPLAY` fidèle
- un `SHADOW` / `MICRO_LIVE` / `LIVE` côté VPS
- un `backtest_artifact_import` gouverné
- une parité logique maximale entre PC et VPS

Tu dois respecter les règles suivantes :

1. conserver une seule base de code V5.3
2. ne créer aucun nouveau profil métier
3. utiliser `runtime_mode`, pas `profile`, pour Local/VPS
4. réutiliser le même shared core pour local et VPS
5. ne jamais dupliquer la logique des moteurs, du scoring, du HMM, du risk ou du portefeuille
6. créer des adapters locaux :
   - `historical_data_gateway`
   - `replay_clock`
   - `replay_event_router`
   - `shadow_execution_simulator`
   - `artifact_exporter`
7. prévoir deux modes :
   - `shadow_fidelity_mode`
   - `research_fast_mode`
8. garantir que les deux modes produisent les mêmes décisions métier
9. garder `backtest_artifact_import` comme module d’intégration / registre / projections seulement
10. ne jamais transformer le replay local en raccourci vers Shadow/Micro-live/Live-Light
11. mettre à jour manifest / DAG / contracts / tests
12. ne pas utiliser ce document comme nouveau master concurrent ; il est subordonné au canon V5.3
13. ne pas introduire de bypass des étapes officielles Build-11, Build-12, Build-13

---

# 22. Verdict final

Le bon modèle est :

> **une seule V5.3**
>
> **deux profils métier officiels seulement**
>
> **des runtime_modes distincts pour local et VPS**
>
> **un shared core identique**
>
> **un local replay shadow-compatible**
>
> **un module d’import séparé pour la gouvernance des artifacts**
>
> **aucun bypass des protocoles officiels de validation**

Autrement dit :

- PC = exécution locale de la vraie V5.3 en replay
- VPS = exécution Shadow / Micro-live / Live de la vraie V5.3
- import artifact = passerelle de revue et d’observabilité
- master canonique = source de vérité unique
- ce document = plan d’implémentation dérivé

> oui à la vitesse locale,  
> oui à la parité logique,  
> non à la seconde V5.3 cachée.




# V5.3 — BUILD-14 AI EDGE & MICROSTRUCTURE COMBATIVITY ADDENDUM
## Addendum spécialisé pour rendre V5.3 plus combative face aux flux manipulés, crowdés ou dominés par comportements machine
### Document dérivé du Build-14 canonique — sans remplacement du spec officiel
### Sans code — prod-safe

---

# 0. Statut du document

- Statut : ADDENDUM BUILD-14 / V1
- Portée : compléter le Build-14 canonique avec des briques ciblées pour :
  - détecter les environnements microstructure trompeurs
  - mieux estimer la toxicité locale du marché
  - détecter le crowding comportemental
  - mesurer la durée de vie réelle de l’edge
  - améliorer le timing d’entrée/sortie d’un edge déjà validé
- Nature : addendum spécialisé de microstructure enrichie, régime enrichi et diversité effective d’edge
- Objectif : rendre V5.3 plus combative **sans** transformer la Light en pseudo-HFT ni introduire de logique opaque

## 0.1 Règle de hiérarchie documentaire

Ce document **ne remplace pas** :
- le master canonique V5.3
- le build plan officiel
- le `V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md`

Il doit être compris comme :
- un addendum ciblé
- une extension spécialisée du Build-14
- un guide d’implémentation pour des briques anti-flux trompeur / anti-crowding / timing enrichi

En cas de conflit :
1. le master canonique prime
2. le build plan officiel prime
3. le spec Build-14 officiel prime
4. ce document enrichit Build-14 sans le redéfinir

---

# 1. Principe central

Le but n’est pas de rendre V5.3 “plus IA” au sens marketing.

Le but est de rendre V5.3 plus **combative** en améliorant sa capacité à :

- détecter quand le carnet ment
- détecter quand le coût a déjà tué l’edge
- détecter quand plusieurs signaux sont en réalité le même edge crowdé
- détecter quand un comportement machine domine localement le flow
- améliorer le timing d’entrée/sortie d’un edge déjà validé
- éviter les faux signaux microstructure et les faux multi-edge

---

# 2. Règles non négociables

## 2.1 Cet addendum reste dans l’esprit Build-14

Toutes les briques proposées ici doivent respecter le mode d’introduction Build-14 :

### Étape 1
- lecture seule
- monitoring / analyse
- sans impact direct live

### Étape 2
- influence limitée
- pénalité légère
- meilleure lecture portefeuille
- alerte enrichie

### Étape 3
- seulement si utilité démontrée
- préparation éventuelle de Build-15 / 16 / 17

## 2.2 Interdictions absolues

Ces briques ne doivent jamais :
- devenir des moteurs autonomes
- créer un moteur E/F/G
- remplacer A/B/C/D
- remplacer le portfolio engine
- remplacer le risk backbone
- piloter seules l’entrée d’un trade
- imposer immédiatement un veto hard central
- introduire RL live
- introduire POMDP live
- introduire un “agent IA libre” de carnet

## 2.3 Principe d’influence

Une brique Build-14 enrichie doit influencer au début seulement :

- un score contextuel enrichi
- un score de toxicité
- une pénalité légère
- une alerte
- une lecture portefeuille plus fine
- une aide au timing d’exécution

Elle ne doit pas :
- casser la logique Light
- réécrire A/B
- recoder le sizing live
- ouvrir Complete implicitement

---

# 3. Gabarit mathématique obligatoire pour chaque brique

Chaque module de cet addendum doit être spécifié avec les 8 blocs suivants :

1. **Mission**
2. **Inputs**
3. **Formule / score**
4. **Seuils**
5. **Output contract**
6. **Politique d’influence**
7. **Métriques de validation**
8. **Dérives à éviter**

Aucun module ne doit “deviner”.
Tout module doit **calculer explicitement**.

---

# 4. Variables de référence

## 4.1 Variables canoniques héritées du Build-14

Order Flow Imbalance :
\[
OFI_t = V_t^{buy} - V_t^{sell}
\]

Book imbalance :
\[
BI_t = \frac{Q_t^{bid}-Q_t^{ask}}{Q_t^{bid}+Q_t^{ask}}
\]

Microprice :
\[
MP_t = \frac{P_t^{ask}Q_t^{bid}+P_t^{bid}Q_t^{ask}}{Q_t^{bid}+Q_t^{ask}}
\]

Diversité effective spectrale :
\[
K_{eff}^{spec} = \frac{(\operatorname{tr}\mathcal{R})^2}{\operatorname{tr}(\mathcal{R}^2)}
\]

## 4.2 Variables enrichies proposées

### Annulation relative
\[
CancelRate_t = \frac{N_t^{cancel}}{N_t^{add}+N_t^{cancel}+\varepsilon}
\]

### Persistance d’un mur de liquidité
\[
WallPersist_t = \frac{1}{w}\sum_{u=t-w+1}^{t}\mathbf{1}\{Q_u^{wall} \ge \theta_{wall}\}
\]

### Vitesse de disparition d’un mur
\[
WallDrop_t = \frac{Q_{t-1}^{wall} - Q_t^{wall}}{\max(Q_{t-1}^{wall},\varepsilon)}
\]

### Confirmation par volume exécuté
\[
ExecConfirm_t = \frac{V_t^{exec,aligned}}{V_t^{exec,total}+\varepsilon}
\]

### Évaporation de liquidité
\[
LiqEvap_t = \frac{\Delta Q_t^{-}}{Q_{t-1}+\varepsilon}
\]

### Pression microprice
\[
MicroDrift_t = \frac{MP_t - Mid_t}{Spread_t+\varepsilon}
\]

### Fraîcheur d’un signal
\[
Fresh_t = \exp(-\lambda \Delta t_{signal})
\]

### Fragilité d’exécution
\[
FragExec_t = \alpha_1 \cdot SpreadStress_t + \alpha_2 \cdot SlipRisk_t + \alpha_3 \cdot LatencyRisk_t + \alpha_4 \cdot LiqEvap_t
\]

### Demi-vie de l’edge
\[
HalfLife_{edge} = \inf\{\tau > 0 \mid Edge(\tau) \le 0.5 \cdot Edge(0)\}
\]

---

# 5. Module 1 — SPOOFING_SUSPICION_FILTER

## 5.1 Mission

Détecter les contextes où le carnet semble afficher de la liquidité trompeuse non confirmée par l’exécution réelle.

## 5.2 Inputs

- `CancelRate_t`
- `WallPersist_t`
- `WallDrop_t`
- `ExecConfirm_t`
- `BI_t`
- `ΔBI_t`
- `MicroDrift_t`

## 5.3 Score proposé

\[
S_{spoof,t} =
0.30 \cdot CancelRate_t
+ 0.25 \cdot WallDrop_t
+ 0.20 \cdot |\Delta BI_t|
+ 0.15 \cdot (1-ExecConfirm_t)
+ 0.10 \cdot |MicroDrift_t|
\]

Score normalisé dans \([0,1]\).

## 5.4 Seuils

- `CLEAR` si \(S_{spoof,t} < 0.35\)
- `WARNING` si \(0.35 \le S_{spoof,t} < 0.65\)
- `HIGH_SUSPICION` si \(S_{spoof,t} \ge 0.65\)

## 5.5 Output contract

- `spoof_score`
- `spoof_verdict`
- `top_components`
- `supporting_metrics`
- `reason_codes`

## 5.6 Politique d’influence

### Étape 1
- lecture seule
- logs / monitoring

### Étape 2
- pénalité légère sur contexte ou coût probable
- alerte enrichie

### Étape 3
- éventuellement dégradation plus forte si validé
- jamais hard veto central initial

## 5.7 Métriques de validation

- faux signaux évités
- amélioration de sélection
- drift du score
- fréquence utile
- coût CPU

## 5.8 Dérives à éviter

- confondre carnet vide et spoofing
- sur-réagir aux petits échantillons
- faire du spoof score une vérité absolue

---

# 6. Module 2 — LIQUIDITY_WALL_PERSISTENCE_MONITOR

## 6.1 Mission

Distinguer :
- mur réel/persistant
- mur décoratif
- mur possiblement spoofé

## 6.2 Inputs

- `Q_t^{wall}`
- `WallPersist_t`
- `WallDrop_t`
- `ExecConfirm_t`
- `OFI_t`
- `MicroDrift_t`

## 6.3 Scores proposés

### Solidité du mur
\[
S_{wall\_solid,t} =
0.40 \cdot WallPersist_t
+ 0.30 \cdot ExecConfirm_t
+ 0.20 \cdot \max(0, OFI_t^{aligned})
+ 0.10 \cdot \max(0, MicroDrift_t^{aligned})
\]

### Mur trompeur
\[
S_{wall\_fake,t} =
0.45 \cdot WallDrop_t
+ 0.30 \cdot (1-ExecConfirm_t)
+ 0.15 \cdot CancelRate_t
+ 0.10 \cdot |\Delta BI_t|
\]

## 6.4 Seuils

- `REAL_WALL`
- `UNCERTAIN_WALL`
- `FAKE_WALL_SUSPECTED`

## 6.5 Output contract

- `wall_solid_score`
- `wall_fake_score`
- `wall_verdict`
- `side`
- `reason_codes`

## 6.6 Politique d’influence

- meilleure lecture contexte continuation/réversion
- pénalité légère si mur fake suspected
- pas de trade créé automatiquement

## 6.7 Validation

- amélioration de qualité d’entrée
- réduction des faux supports/résistances
- cohérence avec exécutions réelles

## 6.8 Dérives

- traiter toute grosse taille comme mur réel
- ignorer l’absence de confirmation par prints

---

# 7. Module 3 — LIQUIDITY_EVAPORATION_DETECTOR

## 7.1 Mission

Détecter les contextes où la liquidité visible s’évapore avant ou pendant l’exécution.

## 7.2 Inputs

- `LiqEvap_t`
- `CancelRate_t`
- spread
- slippage attendu
- `ExecConfirm_t`

## 7.3 Score proposé

\[
S_{evap,t} =
0.35 \cdot LiqEvap_t
+ 0.25 \cdot CancelRate_t
+ 0.20 \cdot SpreadStress_t
+ 0.20 \cdot SlipRisk_t
\]

## 7.4 Seuils

- `STABLE`
- `FRAGILE`
- `EVAPORATING`

## 7.5 Politique d’influence

- dégradation de la qualité d’entrée
- hausse du coût prudent attendu
- aide au sniper d’entrée/sortie

## 7.6 Validation

- amélioration CE
- réduction des entrées dans des trous de liquidité
- baisse des phantom trades

---

# 8. Module 4 — MARKET_TOXICITY_LAYER

## 8.1 Mission

Fournir une lecture synthétique de la toxicité locale du marché.

## 8.2 Inputs

- `S_spoof`
- `S_evap`
- `FragExec_t`
- `|MicroDrift_t|`
- `OFI_t` instable
- spread stress

## 8.3 Score proposé

\[
S_{tox,t} =
0.25 \cdot S_{spoof,t}
+ 0.20 \cdot S_{evap,t}
+ 0.20 \cdot FragExec_t
+ 0.15 \cdot SpreadStress_t
+ 0.10 \cdot OFIInstab_t
+ 0.10 \cdot |MicroDrift_t|
\]

## 8.4 Seuils

- `LOW_TOXICITY`
- `MEDIUM_TOXICITY`
- `HIGH_TOXICITY`

## 8.5 Politique d’influence

- lecture seule puis pénalité légère
- dégradation du score de timing d’entrée
- dégradation de la confiance
- aide au ranking portefeuille

## 8.6 Validation

- faux signaux évités
- coût attendu mieux aligné avec coût observé
- amélioration CE conditionnelle

---

# 9. Module 5 — MACHINE_DOMINATED_REGIME_DETECTOR

## 9.1 Mission

Détecter des régimes de flow dominés par comportements machine ou très réactionnels.

## 9.2 États recommandés

- `NORMAL_FLOW`
- `DIRECTIONAL_FLOW`
- `CANCEL_HEAVY_FLOW`
- `CROWDED_REACTIONAL_FLOW`
- `LIQUIDITY_EVACUATION_FLOW`
- `PSEUDO_BREAKOUT_FLOW`

## 9.3 Inputs

- `CancelRate_t`
- `OFI_t`
- `BI_t`
- `MicroDrift_t`
- spread stress
- rythme des changements de carnet
- persistance du flow

## 9.4 Score d’état conceptuel

\[
\mathbb{P}(z_t=s \mid y_{1:t})
\]

avec des features enrichies incluant microstructure, cancellations et crowding local.

## 9.5 Politique d’influence

- lecture seule initialement
- pénalité légère si état fortement hostile à A/B
- préparation pour Build-15/16 seulement après preuve

## 9.6 Validation

- stabilité des états
- ambiguïtés détectées
- amélioration segmentation utile
- non-régression A/B

---

# 10. Module 6 — EDGE_HALF_LIFE_MONITOR

## 10.1 Mission

Mesurer la durée de vie économique d’un edge après apparition du signal.

## 10.2 Inputs

- timestamp signal
- timestamp entrée
- coût attendu à différents horizons
- CE attendue conditionnelle
- MFE/MAE conditionnelles
- distance à invalidation

## 10.3 Mesures proposées

### Demi-vie de l’edge
\[
HalfLife_{edge} = \inf\{\tau > 0 \mid Edge(\tau) \le 0.5 \cdot Edge(0)\}
\]

### Dégradation relative
\[
Decay_t = 1 - \frac{Edge(t)}{Edge(0)+\varepsilon}
\]

## 10.4 Sorties

- `half_life_estimate`
- `decay_score`
- `entry_urgency`
- `exit_urgency`

## 10.5 Politique d’influence

- aide au timing d’entrée
- aide au governor de sortie
- alerte sur edge crowdé ou vite consommé

## 10.6 Validation

- meilleure qualité d’entrée
- réduction des entrées tardives
- meilleure CE conditionnelle

---

# 11. Module 7 — CROWDING_SIGNATURE_MONITOR

## 11.1 Mission

Détecter quand plusieurs signaux différents sont en réalité la même exposition comportementale crowdée.

## 11.2 Inputs

- corrélations moteur/moteur
- corrélations moteur/paire
- simultanéité des activations
- facteur BTC caché
- similarité des patterns de carnet
- `K_eff^{spec}`

## 11.3 Score proposé

\[
S_{crowd} =
0.30 \cdot PairSynchrony
+ 0.25 \cdot EngineCorr
+ 0.20 \cdot HiddenBTCFactor
+ 0.15 \cdot PatternSimilarity
+ 0.10 \cdot \left(1-\frac{K_{eff}^{spec}}{K}\right)
\]

## 11.4 Seuils

- `DIVERSE`
- `PARTLY_CROWDED`
- `HIGHLY_CROWDED`

## 11.5 Politique d’influence

- lecture portefeuille enrichie
- alerte redondance
- pénalité légère de diversification
- jamais justification automatique d’un veto central

## 11.6 Validation

- meilleure lecture de faux multi-edge
- amélioration arbitrage portefeuille
- cohérence avec `K_eff`

---

# 12. Module 8 — EXECUTION_FRAGILITY_SCORE

## 12.1 Mission

Mesurer la fragilité économique d’un trade à l’exécution.

## 12.2 Inputs

- spread stress
- slippage risk
- latency risk
- `S_evap`
- phantom trade risk

## 12.3 Score proposé

\[
S_{frag,t} =
0.25 \cdot SpreadStress_t
+ 0.25 \cdot SlipRisk_t
+ 0.20 \cdot LatencyRisk_t
+ 0.20 \cdot S_{evap,t}
+ 0.10 \cdot PhantomRisk_t
\]

## 12.4 Seuils

- `ROBUST_EXECUTION`
- `FRAGILE_EXECUTION`
- `VERY_FRAGILE_EXECUTION`

## 12.5 Politique d’influence

- pénalité légère sur timing
- meilleure lecture CE
- alerte portefeuille/exécution

## 12.6 Validation

- réduction des trades stériles
- meilleure cohérence coût attendu / coût observé
- baisse des phantom trades

---

# 13. Module 9 — CONDITIONAL_CE_SURFACE

## 13.1 Mission

Construire une lecture conditionnelle de la capital efficiency attendue selon le contexte.

## 13.2 Variables conditionnantes

- moteur
- paire
- régime
- état toxicité
- état crowding
- fenêtre horaire
- facteur BTC
- niveau de coût

## 13.3 Surface conceptuelle

\[
CE_{cond} = \mathbb{E}\left[\frac{PnL}{x \cdot h} \middle| moteur, paire, régime, toxicité, crowding, temps\right]
\]

## 13.4 Politique d’influence

- lecture enrichie portefeuille
- support au ranking
- meilleure comparaison opportunités

## 13.5 Validation

- amélioration arbitrage entre opportunités
- meilleure stabilité CE live/shadow
- lisibilité opérateur

---

# 14. Module 10 — MICRO_EDGE_ENTRY_TIMING_LAYER

## 14.1 Mission

Améliorer **le timing d’entrée** d’un trade déjà validé par A/B/C/D, sans créer de trade de manière autonome.

## 14.2 Inputs

- `CE_cond`
- `expected_cost_now`
- `expected_cost_baseline`
- `S_tox`
- `S_frag`
- `Fresh_t`
- `wall_verdict`
- `spoof_verdict`
- `support_micro`
- `HalfLife_edge`

## 14.3 Score d’entrée proposé

\[
S_{entry} =
0.25 \cdot \Delta CE^{+}
+ 0.20 \cdot \Delta Cost^{-}
+ 0.20 \cdot SupportMicro
+ 0.15 \cdot (1-S_{tox})
+ 0.10 \cdot Fresh_t
+ 0.10 \cdot (1-S_{frag})
\]

où :
- \(\Delta CE^{+}\) = gain relatif de CE attendu
- \(\Delta Cost^{-}\) = amélioration relative du coût attendu

## 14.4 Seuils

- `ENTER_NOW` si \(S_{entry} \ge 0.65\)
- `WAIT` si \(0.35 \le S_{entry} < 0.65\)
- `ABORT` si \(S_{entry} < 0.35\)

## 14.5 Politique d’influence

- lecture seule initialement
- ensuite raffinement de timing
- jamais création autonome de trade
- jamais bypass du moteur ou du portfolio

## 14.6 Validation

- amélioration coût moyen d’entrée
- amélioration CE
- moins d’entrées toxiques
- pas de baisse de fréquence utile excessive

## 14.7 Dérives à éviter

- transformer ce module en mini-moteur autonome
- chercher un timing parfait au prix de signaux perdus
- introduire de l’optimal stopping opaque en Light

---

# 15. Module 11 — MICRO_EDGE_EXIT_GOVERNOR

## 15.1 Mission

Améliorer **le timing de sortie** d’un trade déjà vivant.

## 15.2 Inputs

- `edge_decay`
- `S_tox`
- `S_frag`
- `breakout_hostility`
- coût de maintien
- proximité invalidation
- MFE/MAE conditionnelles

## 15.3 Score de sortie proposé

\[
S_{exit} =
0.30 \cdot EdgeDecay
+ 0.20 \cdot S_{tox}
+ 0.15 \cdot S_{frag}
+ 0.15 \cdot BreakoutHostility
+ 0.10 \cdot CostToStay
+ 0.10 \cdot InvalidationProximity
\]

## 15.4 Seuils

- `HOLD`
- `TRIM`
- `EXIT`

## 15.5 Politique d’influence

- lecture/analyse initiale
- ensuite aide à sortie / trim / protection
- jamais remplacement complet de la logique d’invalidation des moteurs

## 15.6 Validation

- amélioration CE réalisée
- réduction des sorties tardives
- drawdown local mieux contrôlé

---

# 16. Module 12 — ADVERSARIAL_BREAKOUT_FALSE_POSITIVE_MODEL

## 16.1 Mission

Détecter les cassures visibles mais économiquement déjà compromises ou manipulées.

## 16.2 Inputs

- distance à la cassure
- volume de confirmation
- persistance
- réintégration rapide du range
- `S_tox`
- `S_spoof`
- `S_frag`

## 16.3 Score proposé

\[
S_{fake\_brk} =
0.25 \cdot ReentryRisk
+ 0.20 \cdot (1-Persistence)
+ 0.20 \cdot (1-VolumeConfirm)
+ 0.15 \cdot S_{tox}
+ 0.10 \cdot S_{spoof}
+ 0.10 \cdot DistanceOverextension
\]

## 16.4 Politique d’influence

- lecture préparatoire Build-15
- légère pénalité sur continuation si validé
- jamais moteur C implicite

---

# 17. Module 13 — CAPITAL_COMPETITION_MONITOR

## 17.1 Mission

Mesurer quelles opportunités consomment du capital alors qu’elles dominent mal économiquement les alternatives.

## 17.2 Inputs

- ranking final
- coût d’opportunité
- `CE_cond`
- diversité d’edge
- consommation de caps portefeuille
- crowding signature

## 17.3 Mesure proposée

\[
OppCost_i = \max_{j \in \mathcal{A}_t}\left(CE_{cond,j} - CE_{cond,i}\right)^{+}
\]

\[
S_{capital\_competition,i} =
0.50 \cdot OppCost_i
+ 0.30 \cdot CrowdPenalty_i
+ 0.20 \cdot CapConsumption_i
\]

## 17.4 Politique d’influence

- lecture portefeuille enrichie
- alerte d’arbitrage sous-optimal
- support aux choix Build-8/9

---

# 18. Synthèse des influences autorisées

## 18.1 Lecture seule
Tous les modules commencent en lecture seule.

## 18.2 Influence limitée autorisée
Après validation, influence limitée possible via :
- pénalité légère
- alerte enrichie
- lecture portefeuille enrichie
- timing d’entrée/sortie amélioré

## 18.3 Influences interdites au début
- hard block central
- sizing live réécrit
- reclassification brutale des moteurs
- activation implicite Build-15/16
- passage automatique à Complete

---

# 19. Métriques globales obligatoires de validation

Chaque module proposé ici doit être évalué au minimum sur :

- coût CPU / latence induite
- amélioration éventuelle de sélection
- faux signaux évités
- drift des features
- fréquence d’activation utile
- amélioration CE
- amélioration de coût prudent
- amélioration de lecture portefeuille
- non-régression Light
- lisibilité opérateur

---

# 20. Merge gates spécifiques à cet addendum

Refuser l’implémentation si :
- le module ne possède pas de formule explicite
- le module “devine” au lieu de calculer
- le module crée des trades seul
- le module devient un hard block central immédiat
- le module dégrade A/B sans gain économique clair
- le coût CPU devient disproportionné
- le module sert seulement à faire “plus IA”

---

# 21. Instructions directes à Claude

Tu dois implémenter ces briques comme **enablers Build-14** et respecter strictement les règles suivantes :

1. ne remplace pas le Build-14 canonique
2. implémente ces briques comme addendum spécialisé
3. chaque brique doit avoir :
   - mission
   - inputs
   - formule/score
   - seuils
   - output contract
   - politique d’influence
   - métriques de validation
4. aucune brique ne doit devenir un moteur autonome
5. aucune brique ne doit créer un moteur E/F/G
6. aucune brique ne doit introduire RL/POMDP live
7. toutes les briques commencent en lecture seule
8. influence limitée seulement après preuve d’utilité
9. le `micro_edge_entry_timing_layer` et le `micro_edge_exit_governor` ne doivent jamais bypass moteurs/risk/portfolio
10. la validation doit mesurer :
   - faux signaux évités
   - amélioration CE
   - qualité de lecture coût
   - stabilité
   - coût CPU
   - non-régression Light

---

# 22. Verdict final

Le bon modèle pour rendre V5.3 plus combative est :

> **plus lucide sur la toxicité**
>
> **plus lucide sur le crowding**
>
> **plus lucide sur la durée de vie de l’edge**
>
> **plus lucide sur la qualité d’exécution**
>
> **sans devenir un bot opaque ou un pseudo-HFT**

Autrement dit :

- moins naïve sur le carnet
- moins naïve sur les faux breakouts
- moins naïve sur la fausse diversité d’edge
- meilleure sur le timing d’entrée/sortie
- toujours disciplinée par le canon V5.3

> oui à la combativité,
> non au gadget “IA”.



# V5.3 — STRATEGY ONBOARDING PROTOCOL
## Protocole canonique d’ajout, d’évaluation et de promotion d’une nouvelle stratégie dans V5.3
### Document d’implémentation dérivé du master canonique V5.3
### Sans code — prod-safe

---

# 0. Statut du document

- Statut : PROTOCOL V1
- Portée : définir **le chemin officiel** par lequel une nouvelle stratégie peut entrer dans la V5.3
- Nature : protocole de classification, intégration, replay, export d’artifact, import VPS et promotion éventuelle
- Objectif :
  - empêcher l’ajout anarchique de stratégies
  - empêcher les plugins de recherche non gouvernés
  - empêcher les divergences PC / VPS
  - empêcher la confusion entre backtest local, Shadow, Micro-live et Live
  - préserver l’unicité du canon V5.3

## 0.1 Règle de hiérarchie documentaire

Ce document **ne remplace pas** le master canonique V5.3.

Il doit être compris comme :
- un protocole d’onboarding
- un addendum d’architecture/process
- un guide de gouvernance pour l’ajout de stratégie

En cas de conflit :
1. le master canonique prime
2. le build plan officiel prime
3. les specs de build officielles priment
4. ce document organise l’onboarding sans contredire le canon

---

# 1. Principe central

Dans V5.3, on **n’ajoute pas directement une nouvelle stratégie en production**.

Une stratégie nouvelle doit suivre un pipeline officiel :

```text
idée stratégique
-> classification
-> versioning
-> intégration shared core
-> LOCAL_REPLAY
-> export artifact
-> import VPS
-> revue de valeur marginale
-> candidature contrôlée
-> Shadow / Micro-live / Live uniquement selon le plan officiel
```

---

# 2. Contraintes canoniques à respecter

## 2.1 V5.3 reste un système à 4 moteurs cibles

La V5.3 canonique est définie autour de 4 moteurs cibles :

- Moteur A — Premium Trend / Expansion
- Moteur B — Mean Reversion Intraday
- Moteur C — Breakout Continuation
- Moteur D — Re-entry / Second Chance Logic

Le protocole d’onboarding doit donc respecter cette cible architecturale.

## 2.2 Deux profils métier officiels seulement

La V5.3 n’a que deux profils officiels :

- `LIGHT`
- `COMPLETE`

Interdiction de créer :
- `BACKTEST_PROFILE`
- `RESEARCH_PROFILE`
- `LOCAL_PROFILE`
- `EXPERIMENTAL_PROFILE`

## 2.3 Modes runtime autorisés

Les contextes d’exécution autorisés sont :

- `LOCAL_REPLAY`
- `SHADOW`
- `MICRO_LIVE`
- `LIVE`

Une nouvelle stratégie ne contourne jamais cette hiérarchie.

## 2.4 Interdictions absolues

Interdiction de :
- charger un plugin stratégie arbitraire côté VPS
- exécuter du code stratégie importé via artifact
- créer un moteur E/F/G sans décision de scope explicite
- laisser des features/formules/HMM vivre seulement sur PC
- promouvoir une stratégie à partir d’un bon backtest seul

---

# 3. Question obligatoire avant tout onboarding

Avant d’ajouter une stratégie, il faut répondre à la question :

> **Qu’est-ce que cette stratégie est réellement dans le cadre canonique V5.3 ?**

La stratégie candidate doit être classée dans **une seule** des catégories ci-dessous.

---

# 4. Taxonomie officielle des nouvelles stratégies

## 4.1 Catégorie A — `A_variant`

La stratégie candidate est une nouvelle version du moteur A, par exemple :
- nouvelle feature de trend / structure
- nouvelle formule de conviction
- nouveau mapping invalidation premium
- amélioration coût / CE / EV
- nouveau régime applicable à A

Dans ce cas :
- on ne crée pas un nouveau moteur
- on versionne A
- la stratégie reste une variante de A

## 4.2 Catégorie B — `B_variant`

La stratégie candidate est une nouvelle version du moteur B, par exemple :
- nouveau z-score plus robuste
- meilleure estimation de moyenne locale
- meilleur filtre anti-breakout
- meilleure prudence coût
- meilleure invalidation mean-reversion

Dans ce cas :
- on ne crée pas un nouveau moteur
- on versionne B
- la stratégie reste une variante de B

## 4.3 Catégorie C — `Build14_enabler`

La stratégie candidate n’est pas un moteur autonome, mais une brique d’enrichissement, par exemple :
- microstructure enrichie
- régime enrichi
- covariance robuste
- contributions marginales au risque
- mesure enrichie de diversité effective d’edge

Dans ce cas :
- on ne crée pas un moteur live
- on l’intègre comme enabler Build-14
- on prouve d’abord son utilité

## 4.4 Catégorie D — `C_candidate`

La stratégie candidate est une logique de continuation post-breakout distincte de A.

Conditions minimales :
- non-duplication avec A
- utilité économique propre
- fréquence utile additionnelle
- coût supportable
- contribution portefeuille distincte

Dans ce cas :
- elle entre comme candidat moteur C
- elle ne devient pas automatiquement production
- elle doit suivre la trajectoire Build-15

## 4.5 Catégorie E — `D_candidate`

La stratégie candidate est une logique de réentrée / seconde chance disciplinée.

Conditions minimales :
- valeur marginale positive
- non-confusion avec A
- non-dérive vers revenge trading
- concentration portefeuille supportable

Dans ce cas :
- elle entre comme candidat moteur D
- elle ne devient pas automatiquement production
- elle doit suivre la trajectoire Build-16

## 4.6 Catégorie F — `out_of_scope_for_V5_3`

La stratégie candidate n’entre pas proprement dans A / B / Build-14 / C / D.

Dans ce cas :
- elle n’est pas ajoutée à V5.3 comme moteur canonique
- elle peut rester en recherche locale
- ou être reclassée dans un scope futur (ex. V5.4)
- ou être rejetée

---

# 5. Décision de classification

## 5.1 Règle absolue

Aucune ligne de code d’intégration ne doit être produite tant que la classification n’est pas faite.

## 5.2 Sortie attendue de cette étape

Chaque idée stratégique doit produire une fiche de classification minimale :

- `proposal_id`
- `proposal_name`
- `classification`
- `expected_engine_scope`
- `why_not_A`
- `why_not_B`
- `why_not_Build14_enabler`
- `why_not_duplicate`
- `economic_hypothesis`
- `portfolio_hypothesis`
- `promotion_target`

---

# 6. Contrat de versioning obligatoire

Toute stratégie candidate doit être décrite par des versions explicites.

## 6.1 Champs minimums

- `strategy_id`
- `strategy_version`
- `feature_set_version`
- `formula_set_version`
- `scoring_version`
- `regime_version`
- `risk_policy_version`
- `cost_model_version`

## 6.2 Interdiction

Interdiction d’avoir :
- une feature uniquement locale
- une formule non versionnée
- un HMM local non déclaré
- un seuil critique uniquement dans un notebook
- une stratégie “connue par le code mais pas par les manifests”

---

# 7. Source de vérité unique

## 7.1 Règle

Une stratégie candidate doit être intégrée au **shared core** V5.3.

Elle ne doit pas vivre comme :
- plugin libre externe
- script spécial PC
- notebook exécutoire isolé
- code importé dynamiquement sur VPS

## 7.2 Conséquence

Le PC local et la VPS doivent utiliser :
- la même logique métier
- les mêmes features
- les mêmes équations
- le même HMM / regime logic
- les mêmes kills / hard blockers
- les mêmes règles de coût prudent
- les mêmes contrats d’output

---

# 8. Étape 1 — Intégration shared core

## 8.1 Mission

La stratégie candidate doit être intégrée au shared core selon sa classification.

## 8.2 Cas par cas

### Si `A_variant`
- intégrer dans modules moteur A
- mettre à jour versioning
- ajouter tests ciblés
- vérifier non-régression sur A existant

### Si `B_variant`
- intégrer dans modules moteur B
- mettre à jour versioning
- ajouter tests ciblés
- vérifier non-régression sur B existant

### Si `Build14_enabler`
- intégrer dans le périmètre Build-14
- prouver que l’enabler aide réellement
- ne pas l’activer comme moteur

### Si `C_candidate`
- intégrer sous un package dédié moteur C
- préparer un output canonique moteur C
- respecter les exigences Build-15

### Si `D_candidate`
- intégrer sous un package dédié moteur D
- préparer un output canonique moteur D
- respecter les exigences Build-16

---

# 9. Étape 2 — Tests locaux obligatoires

Avant tout replay massif, la stratégie candidate doit passer :

- tests unitaires
- tests de contrats
- tests d’identité logique
- tests anti-fork
- tests de non-régression
- tests de logs structurés
- tests d’outputs auditables

## 9.1 Interdiction

Une stratégie ne doit jamais être évaluée sérieusement si :
- son output n’est pas audit-ready
- sa décision n’est pas reproductible
- son scoring n’est pas lisible
- ses raisons de no-trade ne sont pas traçables

---

# 10. Étape 3 — Validation en `LOCAL_REPLAY`

## 10.1 Règle

Toute nouvelle stratégie doit d’abord être évaluée en :

- `runtime_mode = LOCAL_REPLAY`

et jamais directement en :
- `SHADOW`
- `MICRO_LIVE`
- `LIVE`

## 10.2 Pourquoi

Le `LOCAL_REPLAY` existe pour :
- tester avec la vraie logique V5.3
- éviter une divergence PC / VPS
- accélérer les itérations
- produire des artifacts standardisés
- mesurer la valeur réelle avant toute candidature

## 10.3 Ce que le replay doit réutiliser

Le replay doit utiliser le même shared core :
- scoring
- risk
- portfolio
- coût prudent
- hard/soft/rank
- moteurs / enablers selon classification

---

# 11. Étape 4 — Artifact export

## 11.1 Mission

À la fin d’un run `LOCAL_REPLAY`, le système doit produire un artifact standardisé.

## 11.2 Champs minimums d’un run

- `run_id`
- `strategy_id`
- `strategy_version`
- `profile_scope`
- `runtime_mode = LOCAL_REPLAY`
- `engine_scope`
- `tested_pairs`
- `dataset_manifest_id`
- `timeframe_scope`
- `feature_set_version`
- `formula_set_version`
- `scoring_version`
- `regime_version`
- `risk_policy_version`
- `cost_model_version`
- `performance_mode`
- `artifact_schema_version`
- `artifact_hash`

## 11.3 Outputs minimums

- résumé de métriques
- agrégats par paire
- agrégats par moteur
- historique suffisant des décisions
- DTR / raisons structurées
- coûts
- drawdown
- contribution portefeuille

---

# 12. Étape 5 — Import VPS

## 12.1 Mission

L’artifact produit localement peut être importé sur la VPS via `backtest_artifact_import`.

## 12.2 Rôle du module d’import

Le module d’import :
- valide
- parse
- mappe au canon V5.3
- enregistre dans le registre
- produit des projections UI / Meta / Monitoring

## 12.3 Ce que le module d’import ne fait pas

Il ne doit jamais :
- exécuter la stratégie
- recalculer le backtest
- activer Shadow
- promouvoir automatiquement la stratégie

---

# 13. Étape 6 — Revue de valeur marginale

## 13.1 Question centrale

La stratégie candidate apporte-t-elle quelque chose de **réellement distinct** ?

## 13.2 Les quatre tests obligatoires

### a) Test d’edge propre
La stratégie a-t-elle un edge net défendable ?

### b) Test de coût
Le coût réel/prudent détruit-il l’edge ?

### c) Test portefeuille
La stratégie améliore-t-elle le portefeuille, et pas seulement son propre backtest ?

### d) Test de non-duplication
La stratégie n’est-elle pas juste un doublon plus compliqué d’un moteur existant ?

---

# 14. Critères par classe de stratégie

## 14.1 Pour `A_variant`
Go si :
- améliore A sans l’opacifier
- coût maîtrisé
- edge net au moins stable
- CE au moins stable
- lisibilité conservée

No-go si :
- version plus opaque
- gain marginal non démontré
- coût supérieur sans compensation
- dérive vers sur-filtrage ou sur-fitting

## 14.2 Pour `B_variant`
Go si :
- améliore B sans casser sa rotation utile
- coût strictement maîtrisé
- meilleure robustesse face aux faux breakouts
- CE défendable

No-go si :
- plus de trades mais moins de qualité
- coût détruit l’edge
- breakout risk sous-estimé

## 14.3 Pour `Build14_enabler`
Go si :
- enrichit réellement l’analyse
- ne dégrade pas la stabilité Light
- n’ajoute pas de complexité décorative

No-go si :
- sophistication sans gain
- surcharge infra
- baisse de lisibilité

## 14.4 Pour `C_candidate`
Go si :
- continuation distincte de A démontrée
- alpha additionnel ou diversification démontrée
- coût supportable
- faux breakout tolérable

No-go si :
- doublon nerveux de A
- poursuite non distincte
- coût trop élevé
- fréquence brute sans valeur économique

## 14.5 Pour `D_candidate`
Go si :
- valeur marginale positive démontrée
- réengagement discipliné
- concentration supportable
- coût marginal acceptable

No-go si :
- revenge trading automatisé
- surconcentration
- pas de valeur additionnelle
- simple répétition d’A

---

# 15. États officiels du cycle de vie stratégie

## 15.1 États recommandés

- `PROPOSED`
- `CLASSIFIED`
- `CORE_INTEGRATED`
- `LOCAL_REPLAY_READY`
- `LOCAL_REPLAY_VALIDATED`
- `ARTIFACT_EXPORTED`
- `IMPORTED`
- `BACKTEST_VALIDATED`
- `SHADOW_CANDIDATE`
- `SHADOW_VALIDATED`
- `MICRO_LIVE_CANDIDATE`
- `MICRO_LIVE_VALIDATED`
- `LIVE_ELIGIBLE`
- `REJECTED`
- `ARCHIVED`

## 15.2 Interdiction

Interdiction des transitions implicites du type :

- `LOCAL_REPLAY_VALIDATED -> LIVE_ELIGIBLE`
- `BACKTEST_VALIDATED -> SHADOW_ACTIVE`
- `IMPORTED -> PRODUCTION_READY`

---

# 16. Relation avec les builds officiels

## 16.1 Pour A/B

A et B peuvent être enrichis, mais doivent rester compatibles avec la trajectoire Light.

## 16.2 Pour les enablers

Les briques analytiques additionnelles relèvent de Build-14.

## 16.3 Pour C

Le chemin officiel est :
- Build-14 validé
- Build-15 seulement ensuite
- preuve de non-duplication avec A

## 16.4 Pour D

Le chemin officiel est :
- Build-15 validé
- Build-16 seulement ensuite
- preuve de valeur marginale positive

## 16.5 Pour la Complete

Même une stratégie convaincante ne donne pas automatiquement le droit d’ouvrir Complete.
La Complete reste conditionnée par :
- Light validée
- coûts réels compris
- C/D validés
- gains système réels
- gouvernance UI/rollback maîtrisée

---

# 17. Interdictions critiques de gouvernance

Interdiction de :
- créer un moteur E “temporaire”
- promouvoir une stratégie pour des raisons esthétiques/psychologiques
- conclure sur la base d’un seul backtest
- confondre document de recherche et spec d’implémentation
- confondre plus de trades et meilleur edge
- laisser la VPS devenir un laboratoire de recherche libre

---

# 18. Check-list d’onboarding minimal

Une stratégie candidate ne peut pas être considérée sérieusement tant que les cases suivantes ne sont pas cochées :

- classification faite
- hypothèse économique explicite
- hypothèse portefeuille explicite
- versioning complet
- shared core intégré
- tests unitaires OK
- tests de contrat OK
- logs structurés OK
- replay local OK
- artifact export OK
- import VPS OK
- revue de non-duplication OK
- revue coût OK
- revue portefeuille OK

---

# 19. Merge gates spécifiques stratégie

Refuser le merge si :
- la classification n’existe pas
- la stratégie vit hors shared core
- la feature/formule/HMM n’est pas versionnée
- le replay local utilise une logique différente de la VPS
- l’artifact n’est pas standardisé
- le module import essaie d’exécuter la stratégie
- la promotion saute Build-11 / 12 / 13
- la stratégie duplique A/B/C/D sans preuve de différence utile

---

# 20. Instructions directes à Claude

Tu dois implémenter l’onboarding des nouvelles stratégies en respectant les règles suivantes :

1. ne jamais ajouter directement une stratégie “en live”
2. commencer par classifier la stratégie :
   - `A_variant`
   - `B_variant`
   - `Build14_enabler`
   - `C_candidate`
   - `D_candidate`
   - `out_of_scope_for_V5_3`
3. refuser tout code d’intégration avant classification
4. imposer le versioning :
   - `strategy_version`
   - `feature_set_version`
   - `formula_set_version`
   - `scoring_version`
   - `regime_version`
   - `risk_policy_version`
   - `cost_model_version`
5. intégrer toute logique décisive au shared core
6. utiliser `LOCAL_REPLAY` comme première étape d’évaluation
7. produire un artifact standardisé
8. permettre l’import VPS seulement comme registre / UI / Meta / Monitoring
9. exiger une revue de valeur marginale avant toute candidature supérieure
10. interdire toute promotion implicite vers Shadow / Micro-live / Live
11. ne jamais créer un moteur E/F/G sans décision explicite de scope
12. ne pas transformer ce protocole en second master documentaire

---

# 21. Verdict final

Le bon modèle d’ajout d’une stratégie à V5.3 est :

> **classifier**
>
> **versionner**
>
> **intégrer au shared core**
>
> **tester en LOCAL_REPLAY**
>
> **exporter un artifact**
>
> **importer sur la VPS pour gouvernance**
>
> **mesurer la valeur marginale**
>
> **promouvoir seulement selon les builds officiels**

Autrement dit :

- une idée n’est pas un moteur
- un bon backtest n’est pas une autorisation live
- un plugin local n’est pas une stratégie V5.3
- une stratégie V5.3 n’existe que si elle est gouvernée, versionnée, replayable, importable et promouvable selon le canon

> oui à l’innovation stratégique,
> non au chaos documentaire et au bypass de production.


