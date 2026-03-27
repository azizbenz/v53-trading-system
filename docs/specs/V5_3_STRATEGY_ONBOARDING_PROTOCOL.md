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
