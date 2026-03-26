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
