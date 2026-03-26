# V5.3 — LOCAL REPLAY BACKTEST RUNTIME SPEC
## Même cœur V5.3 que la VPS, exécution locale accélérée pour backtest
### Spécification d’architecture — sans code
### Compatible avec le master unique, Build-1 → Build-17, et le module `backtest_artifact_import`

---

# 0. Statut du document

- Statut : SPEC ARCHITECTURE V1
- Portée : définir comment la V5.3 doit être exécutée localement pour backtester avec la **même logique** que la VPS
- Nature : spécification de runtime local / replay historique / export d’artifacts
- Objectif : empêcher toute dérive entre :
  - la V5.3 de la VPS
  - la solution de backtest locale
  - les stratégies, features, équations, kills, HMM, scoring et risk
- Hors périmètre :
  - création d’une seconde V5.3 parallèle
  - création d’un profil "BACKTEST" autonome
  - moteur de recherche libre non gouverné dans la VPS
  - exécution de code stratégie arbitraire uploadé
  - bypass des builds officiels Shadow / Micro-live / Live-Light

---

# 1. Problème à résoudre

Le projet a un besoin fort :

- obtenir des backtests **réellement représentatifs**
- éviter que le backtest local dérive de la VPS
- garantir que les kills, HMM, scoring, risk, allocation et coûts soient identiques
- permettre un travail local rapide sur PC
- exporter ensuite des résultats vers la VPS pour revue, registre et monitoring

Le risque principal est le suivant :

> si la solution de backtest locale n’est pas la même V5.3 que la VPS, alors les résultats de backtest ne prouvent rien sur le comportement réel futur.

Conséquences d’une dérive non contrôlée :
- features différentes
- équations différentes
- HMM différent
- kills différents
- coûts différents
- décisions non reproductibles
- faux GO vers Shadow
- faux sentiment de validation

---

# 2. Décision d’architecture

## 2.1 Décision centrale

La solution de backtest locale doit être :

> **la même V5.3 que la VPS, exécutée en mode local replay**

et non :
- une solution de backtest séparée
- une V5.3 "lightement ressemblante"
- un script de replay à part
- un ancien moteur V1 reconnecté artificiellement

## 2.2 Formulation officielle

Le projet doit conserver :

- **une seule base de code V5.3**
- **deux profils métier officiels uniquement** :
  - `LIGHT`
  - `COMPLETE`

et introduire à côté un **mode runtime**, pas un nouveau profil :

- `LOCAL_REPLAY`
- `SHADOW`
- `MICRO_LIVE`
- `LIVE`

## 2.3 Conséquence

Le backtest local ne doit pas être une autre logique.

Il doit être :
- le même cœur décisionnel
- le même cœur risque
- le même cœur portefeuille
- la même logique de coût prudent
- la même logique de refus / ranking / allocation
- la même gouvernance de profil

Ce qui change seulement :
- la source des données
- l’horloge
- l’adapter d’exécution
- la densité de logs/UI
- l’export final du run

---

# 3. Règles non négociables

## 3.1 Une seule vérité de stratégie

Il ne doit exister qu’une seule vérité pour :
- features
- équations
- HMM / regime logic
- kills / hard blockers
- scoring
- risk
- allocation
- sizing
- coûts prudents

## 3.2 Interdictions absolues

Interdiction de :
- maintenir un plugin stratégie local avec logique différente
- recalculer les features avec des formules "presque identiques"
- avoir un HMM local distinct du HMM VPS
- avoir des kills locaux plus permissifs ou plus durs
- faire un coût de backtest décoratif différent du shadow prudent
- autoriser un "mode rapide" qui change les décisions
- faire du backtest sur code de recherche non versionné
- injecter du code stratégie arbitraire dans la VPS

## 3.3 Principe d’identité

À dataset équivalent, paramètres équivalents et conditions de replay équivalentes :

> la V5.3 locale et la V5.3 VPS doivent produire les mêmes décisions logiques.

Les différences acceptables portent uniquement sur :
- le contexte live vs historique
- les événements d’exécution réelle
- les coûts/fills réels du micro-live
- la vitesse d’exécution
- certaines couches d’observabilité allégées

---

# 4. Position du local replay dans la roadmap officielle

## 4.1 Le local replay n’est pas un Build-18

Le local replay ne crée pas :
- un nouveau build produit
- un nouveau moteur
- un nouveau profil
- une nouvelle architecture parallèle

Il doit être traité comme :
- une capacité runtime transverse
- une extension contrôlée de l’architecture existante
- un runner local utilisant les modules canoniques V5.3

## 4.2 Relation avec Build-11 Shadow

Le local replay doit réutiliser la même **logique** que le Shadow Light.

Mais il ne doit pas être :
- le protocole Shadow opérationnel brut
- une exécution quasi-live lente utilisée telle quelle sur des années d’historique

Conclusion :
- même cerveau que Shadow
- runner différent

## 4.3 Relation avec Build-12 Micro-live

Le local replay ne remplace pas le Micro-live.

Même un replay très fidèle ne valide pas :
- les fills réels
- la latence réelle
- les effets exchange réels
- la réconciliation réelle
- les coûts réels exacts

Le replay est un test de vérité logique et économique prudente.
Le micro-live reste le test de vérité opérationnelle réelle.

---

# 5. Architecture cible

## 5.1 Vue générale

```text
                 ┌───────────────────────────────┐
                 │        V5.3 SHARED CORE       │
                 │-------------------------------│
                 │ interface_contracts           │
                 │ manifest_registry             │
                 │ dag_validator                 │
                 │ data backbone                 │
                 │ data quality backbone         │
                 │ regime / HMM                  │
                 │ signal logic / engines        │
                 │ scoring backbone              │
                 │ risk backbone                 │
                 │ portfolio engine              │
                 │ meta logic                    │
                 │ monitoring contracts          │
                 └───────────────┬───────────────┘
                                 │
                ┌────────────────┴────────────────┐
                │                                 │
┌──────────────────────────────┐   ┌──────────────────────────────┐
│      VPS SHADOW / LIVE       │   │      LOCAL REPLAY RUNNER     │
│------------------------------│   │------------------------------│
│ websocket_gateway            │   │ historical_data_gateway      │
│ rest_bootstrap               │   │ replay_clock                 │
│ execution shadow/live        │   │ replay_event_router          │
│ live persistence             │   │ shadow_execution_simulator   │
│ ops monitoring               │   │ artifact_exporter            │
└──────────────────────────────┘   └──────────────────────────────┘
```

## 5.2 Principe

Le **shared core** contient la logique métier.

Les runners changent seulement :
- les adapters d’entrée
- l’adapter d’exécution
- les sorties de run
- certains niveaux d’observabilité

---

# 6. Modules du shared core qui doivent être identiques

Les modules suivants doivent être partagés sans fork logique :

- `interface_contracts`
- `manifest_registry`
- `dag_validator`
- `event_normalizer`
- `freshness_checker`
- `consistency_checker`
- `pair_health_scorer`
- `execution_cost_meter`
- `reconciliation_layer` (partie logique réutilisable)
- `exposure_budgeter`
- `loss_budgeter`
- `btc_factor_guard`
- `correlation_cluster_guard`
- `raw_score_builder`
- `penalty_aggregator`
- `hard_block_gate`
- `ranking_router`
- `engine_a`
- `engine_b`
- `portfolio minimal`
- `meta minimal`
- toute logique Light partagée déjà validée

Si plus tard Complete est ajouté au replay :
- mêmes règles pour C/D
- mêmes règles pour Complete enrichi
- aucune variante locale spéciale

---

# 7. Ce qui peut différer entre VPS et local

## 7.1 Adapters d’entrée

### VPS
- `websocket_gateway`
- `rest_bootstrap`

### Local replay
- `historical_data_gateway`
- `historical_snapshot_loader`
- `replay_event_router`

## 7.2 Horloge

### VPS
- temps réel ou quasi-live

### Local replay
- `replay_clock`
- accélération temporelle
- rewind / replay / chunking éventuels

## 7.3 Exécution

### VPS Shadow
- exécution simulée prudente connectée au flux live/quasi-live

### VPS Live / Micro-live
- exécution réelle exchange

### Local replay
- `shadow_execution_simulator`
- même philosophie de prudence que Shadow
- aucune hypothèse d’exécution parfaite

## 7.4 Observabilité

### VPS
- monitoring/UI opérationnels actifs
- alerting
- supervision continue

### Local replay
- observabilité minimale ou batchable
- dashboards/export en fin de run
- UI live non obligatoire

---

# 8. Le local replay doit réutiliser la logique Shadow

## 8.1 Règle

Le local replay doit être **shadow-compatible**.

Cela signifie :
- mêmes no-trade
- mêmes hard blockers
- mêmes pénalités
- mêmes seuils coût prudent
- mêmes décisions A/B
- même arbitration portefeuille
- même logique de DTR au niveau décisionnel
- même logique de trade phantom / stérilisation

## 8.2 Ce qu’il ne faut pas faire

Ne pas utiliser :
- un backtest candle-only simpliste
- un PnL simulator détaché du scoring/risk/portfolio
- un script replay qui saute la moitié des couches

## 8.3 Formulation officielle

Le local replay doit être :

> un **runner historique accéléré** qui appelle la même logique que Shadow,
> et non une réécriture simplifiée du Shadow.

---

# 9. Stratégies, features, équations, HMM

## 9.1 Source de vérité unique

Les stratégies ne doivent pas vivre dans :
- du code local libre sans contrat
- des notebooks seuls
- des docs math seules
- des exports de backtest seuls

Les éléments suivants doivent être versionnés et gouvernés :
- `strategy_version`
- `feature_set_version`
- `formula_set_version`
- `scoring_version`
- `regime_version`
- `risk_policy_version`
- `cost_model_version`

## 9.2 Invariant obligatoire

Une feature, une formule ou un paramètre HMM ne peut pas exister uniquement dans le backtest local.

Tout élément utilisé dans le replay doit être :
- déclaré
- versionné
- reproductible
- compatible avec le shared core

## 9.3 Interdiction

Interdiction d’avoir :
- un HMM research local différent du HMM runtime
- un kill local non codé dans le shared core
- une feature “temporaire” décisive uniquement dans le backtest

## 9.4 Règle de promotion

Une nouvelle formule ou nouvelle feature passe par :
1. définition versionnée
2. intégration dans le shared core
3. tests
4. audit logique
5. validation replay
6. seulement ensuite candidature Shadow

---

# 10. Profils et modes runtime

## 10.1 Profils métier officiels
- `LIGHT`
- `COMPLETE`

## 10.2 Modes runtime autorisés
- `LOCAL_REPLAY`
- `SHADOW`
- `MICRO_LIVE`
- `LIVE`

## 10.3 Interdiction
Ne pas créer :
- `BACKTEST_PROFILE`
- `PC_PROFILE`
- `RESEARCH_PROFILE`
- `LOCAL_PROFILE`

## 10.4 Configuration recommandée

Le runtime doit toujours être défini par :

- `profile_scope`
- `runtime_mode`

Exemples :
- `LIGHT + LOCAL_REPLAY`
- `LIGHT + SHADOW`
- `LIGHT + MICRO_LIVE`
- `LIGHT + LIVE`
- `COMPLETE + LOCAL_REPLAY` (plus tard, si et seulement si validé)

---

# 11. Performance : années de données en temps utile

## 11.1 Réponse d’architecture

Le local replay doit être conçu pour permettre des backtests historiques massifs.

Mais cette performance ne doit jamais être obtenue en simplifiant la logique de décision.

## 11.2 Principe

Le gain de performance doit venir de :
- l’adapter historique
- l’horloge accélérée
- le pré-calcul/caching des données dérivées
- le chunking temporel
- la parallélisation prudente
- l’allègement de l’observabilité non critique

et non de :
- kills désactivés
- HMM simplifié
- scoring approximatif
- risk contourné
- portefeuille contourné
- coût prudent supprimé

## 11.3 Modes de performance recommandés

### a) `shadow_fidelity_mode`
Objectif :
- fidélité maximale
- diagnostic profond
- observabilité riche
- vitesse secondaire

### b) `research_fast_mode`
Objectif :
- accélérer les runs massifs
- réduire les coûts d’I/O et de logs
- garder les mêmes décisions
- produire un artifact résumé + traçable

## 11.4 Règle absolue

`research_fast_mode` peut alléger :
- fréquence de logs
- snapshots intermédiaires
- UI live
- détail non critique du monitoring

`research_fast_mode` ne peut pas changer :
- features
- équations
- HMM
- kills
- scoring
- risk
- allocation
- ordre des décisions
- coût prudent
- statut trade/no-trade logique

---

# 12. Components spécifiques à créer pour le local replay

## 12.1 Package recommandé

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

## 12.2 Nature de ces composants

Ces composants doivent être :
- fins
- explicites
- déterministes
- centrés runtime
- sans logique métier dupliquée

---

# 13. `shadow_execution_simulator`

## 13.1 Mission

Le local replay doit utiliser un simulateur d’exécution prudent, aligné avec l’esprit du Shadow.

Il doit intégrer au minimum :
- spread plausible
- slippage prudent
- pénalité de latence simulée
- non-remplissage possible
- partial fills plausibles si le modèle d’exécution les supporte
- refus de trades économiquement absurdes
- calcul cohérent des coûts attendus

## 13.2 Interdictions

Interdiction de supposer :
- exécution parfaite
- fill instantané systématique
- coût nul
- carnet infini
- aucun impact de la latence

## 13.3 Règle de cohérence

Le simulateur local doit rester cohérent avec :
- les hypothèses Shadow
- les coûts prudents suivis par Meta
- les décisions ultérieures de review

---

# 14. Artifact export depuis le local replay

## 14.1 Mission

À la fin d’un run local, le système doit pouvoir produire un artifact standardisé importable dans la VPS.

## 14.2 Rôle de l’export

L’export sert à :
- archiver le run
- comparer des versions
- nourrir Meta / Monitoring / UI sur la VPS
- préparer les revues de stratégie
- candidater plus tard à un processus Shadow gouverné

## 14.3 Lien avec `backtest_artifact_import`

Le local replay produit l’artifact.
La VPS l’importe via `backtest_artifact_import`.

Le module d’import :
- ne calcule pas le backtest
- n’exécute pas la stratégie
- n’active pas Shadow
- ne remplace pas le replay local

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
- DTR/raisons structurées
- logs de refus pertinents
- informations de coût
- informations de drawdown
- contribution portefeuille

---

# 16. Build-1 / manifest / DAG

## 16.1 Manifest obligatoire

Le runtime local doit être officialisé au manifest.

Noms recommandés :
- `local_replay_runtime`
- `shadow_execution_simulator`
- `artifact_exporter`

## 16.2 Dépendances autorisées

Le runtime local peut dépendre de :
- `interface_contracts`
- `manifest_registry`
- `dag_validator`
- modules canoniques déjà présents du shared core
- utilitaires déterministes de persistence/config

## 16.3 Dépendances interdites

Interdiction de dépendre de :
- code stratégie externe libre
- notebooks
- plugin non versionné
- code Backtest V1 séparé si celui-ci diverge de V5.3
- services live non simulés comme dépendance obligatoire

## 16.4 Règle DAG

Le `dag_validator` doit refuser :
- toute logique métier dupliquée dans `local_replay_runtime`
- tout import direct interdit vers modules expérimentaux hors gouvernance
- toute création implicite d’un second moteur A/B local

---

# 17. Si le repo actuel n’a codé que Build-1 à Build-6

## 17.1 Situation

Si le repo Claude n’a réellement codé que Build-1 → Build-6 :

- Build-7 n’est pas encore opérationnel
- Build-8 n’est pas encore opérationnel
- Build-9 n’est pas encore opérationnel
- Build-10 n’est pas encore opérationnel
- Build-11 n’est pas encore opérationnel

## 17.2 Conséquence

Le spec doit tout de même être ajouté maintenant, mais l’implémentation doit être phasée.

## 17.3 Phase réaliste

### Phase A — architecture maintenant
- ajouter le spec
- ajouter le manifest
- ajouter les contrats
- créer les stubs runtime
- préparer les adapters locaux
- figer les invariants anti-fork

### Phase B — activation quand les builds existent
- brancher B si Build-7 codé
- brancher portfolio si Build-8 codé
- brancher Meta si Build-9 codé
- brancher Monitoring/UI si Build-10 codé
- aligner finement avec Shadow quand Build-11 codé

## 17.4 Interdiction

Ne pas simuler faussement Build-8/9/10/11 complets si le repo ne les a pas encore codés.

---

# 18. Tests obligatoires

## 18.1 Tests d’identité logique
- même input historique -> mêmes décisions logiques sur runs répétés
- même config -> même ordre de sélection
- même config -> mêmes hard blockers
- même config -> mêmes pénalités
- même config -> mêmes tailles finales si déterminisme attendu

## 18.2 Tests anti-fork
- toute divergence feature/version rejetée
- toute divergence HMM/version rejetée
- tout mode rapide qui change les décisions rejeté
- toute formule non enregistrée rejetée

## 18.3 Tests runtime local
- bootstrap OK
- bootstrap FAIL si config critique absente
- recovery OK
- chunk replay OK
- resume/restart propre si supporté
- export artifact OK
- hash artifact stable
- import artifact par le module consumer possible

## 18.4 Tests de performance
- run court en mode fidélité OK
- run massif en mode rapide OK
- comparaison fidélité/rapide -> mêmes décisions métier
- budget mémoire acceptable
- I/O contrôlés

---

# 19. Merge gates

Refuser le merge si :
- un nouveau profil runtime a été créé au lieu d’un mode runtime
- le local replay duplique la logique métier
- le local replay modifie les décisions par rapport au shared core
- le mode rapide change le résultat logique
- l’export artifact n’est pas versionné
- le manifest n’est pas mis à jour
- le DAG ne protège pas contre le fork
- un code stratégie libre externe devient source de vérité
- les invariants anti-fork ne sont pas testés

---

# 20. Instructions directes à Claude

Tu dois mettre à niveau l’architecture V5.3 pour permettre un **local replay backtest runtime**.

Tu dois respecter les règles suivantes :

1. conserver **une seule base de code V5.3**
2. ne créer **aucun nouveau profil**
3. introduire seulement un **runtime_mode = LOCAL_REPLAY**
4. réutiliser le même shared core que la VPS
5. ne jamais dupliquer la logique des moteurs, du scoring, du HMM, du risk ou du portefeuille
6. créer des adapters locaux :
   - historical_data_gateway
   - replay_clock
   - replay_event_router
   - shadow_execution_simulator
   - artifact_exporter
7. prévoir deux modes :
   - shadow_fidelity_mode
   - research_fast_mode
8. garantir que les deux modes produisent les **mêmes décisions métier**
9. préparer un export artifact importable dans la VPS
10. ne pas transformer ce runtime local en système de recherche libre non gouverné
11. mettre à jour manifest / DAG / contracts / tests
12. si le repo courant n’a pas encore Build-7 → Build-11, préparer l’architecture sans simuler faussement les couches absentes

Tu ne dois pas :
- créer un Build-18
- créer un profil BACKTEST
- maintenir une seconde logique de stratégie
- autoriser un HMM local distinct
- autoriser des kills locaux distincts
- simplifier les décisions pour aller plus vite
- remplacer le Micro-live comme vérité de coût réel

---

# 21. Verdict final

Le bon modèle est :

> **une seule V5.3**
>
> **même cœur logique pour VPS et PC**
>
> **runner local replay pour backtest accéléré**
>
> **artifact exporté vers la VPS**
>
> **module d’import séparé pour registre / UI / Meta / Monitoring**
>
> **aucune dérive de stratégie, de features, d’équations ou de HMM**

Autrement dit :

- PC = exécution locale de la vraie V5.3 en replay
- VPS = exécution Shadow / Micro-live / Live de la vraie V5.3
- import artifact = passerelle de revue, pas moteur de backtest

> oui à la vitesse locale,
> non à la seconde V5.3 cachée.
