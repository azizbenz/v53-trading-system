# V5.3 - ML Enabler Canon Scientifique V1

## Statut
- `WORKING_CANON`
- `PROD_SAFE_FIRST`
- `HUMAN_ARBITRATION_REQUIRED_ON_OPEN_POINTS`

## Rôle
Ce document fige le **plus petit canon scientifique et opérationnel** autorisé pour le slice ML V5.3.

Il ne retient que les points :
- mathématiquement fermés,
- compatibles avec le trading systématique V5.3,
- observables sans leakage,
- implémentables sans ambiguïté,
- auditables en prod.

Tout ce qui n'atteint pas ce niveau reste explicitement hors canon.

## Hiérarchie de vérité
Pour ce sujet, la hiérarchie à respecter est :
1. logique trading / quant / anti-leakage,
2. doctrine V5.3 réellement fermée,
3. code actuel,
4. markdowns dupliqués, historiques, ou ambigus.

Conséquence :
- si le code contredit un point canonique **fermé**, le code doit changer,
- si un markdown contredit le code mais reste ambigu ou trop large, il ne devient pas canon pour autant.

## Critères d'entrée dans le canon
Un point ne rentre dans ce canon que s'il est :
- `KNOWN`
- fermé mathématiquement,
- fondé sur des données réellement observables,
- compatible avec un runtime fail-closed,
- testable dans le repo,
- non contradictoire avec les invariants A/B/C/D et Shadow/Micro-live/Live.

## Invariants canoniques

### KNOWN - ML rôle et souveraineté
- Le ML est un **enabler additif**, jamais un moteur autonome.
- A/B/C/D restent souverains sur :
  - le `side`
  - l'émission canonique
  - les hard blocks
  - les refus
  - les caps de forecast-strength
- Le ML ne crée pas un cinquième moteur.

### KNOWN - Séparation Local / VPS
- L'entraînement est **Local-Lab only**.
- Le VPS consomme uniquement un **artefact**.
- Le VPS ne fait jamais :
  - `fit LightGBM`
  - `Optuna`
  - training online

### KNOWN - Discipline runtime
- Le runtime ML doit être **artifact-only**.
- Artefact absent / invalide / stale => dégradation à neutre.
- Le runtime ML ne doit jamais créer un faux blocage de trade.

### KNOWN - Discipline quant gelée
Les fichiers quant-anchor suivants sont hors modification dans ce slice :
- `src/calibration_methods/psr.py`
- `src/calibration_methods/dsr.py`
- `src/calibration_methods/pot_gpd.py`
- `src/calibration_methods/energy_distance.py`

## Canon du modèle

### KNOWN - Famille modèle
- La seule famille autorisée dans ce slice est **LightGBM tabulaire**.
- Aucun deep learning, RL, XGBoost, CatBoost, ou zoo multi-modèles.

### UNKNOWN - Objectif exact du modèle
Ce point n'est **pas** canonisé à ce stade.

Constat :
- les markdowns ML parlent de **classifier**
- le code actuel entraîne en **regression**

Donc :
- `classifier` n'entre pas dans le canon V1
- `regression` n'entre pas non plus dans le canon V1 comme vérité définitive
- une décision humaine explicite est requise avant tout recodage profond du trainer

## Canon du label et de la cible

### KNOWN - Principe de supervision
Le ML doit apprendre une **qualité d'issue nette conditionnelle** d'un candidat déjà émis par un moteur canonique.

Ce que cela interdit :
- prédire un trade souverain
- apprendre un side autonome
- optimiser un PnL brut sans coût

### KNOWN - Politique de cible repo-truth actuelle
Deux politiques existent et sont scientifiquement défendables :

1. cible stricte prioritaire :
- `net_return_bps_after_replay_realized_cost.v1`

2. fallback explicite :
- `net_return_bps_after_route_cost_bps.v1`

Règle canonique :
- si un `DTRRecord` aligné existe, la cible stricte est prioritaire
- sinon le fallback route-cost est autorisé, mais doit être marqué explicitement

### KNOWN - Anti-leakage
- les features utilisent uniquement des données observables à `t` ou avant
- la cible utilise uniquement de l'information postérieure à `t`
- aucun forward-fill implicite futur
- aucune interpolation future

### UNKNOWN - Formalisme cible définitif classifier vs regression
La forme finale du target d'entraînement n'est pas encore canonisée.

Ce que l'on sait :
- le problème métier est bien une qualité d'issue nette
- le repo actuel l'exprime comme une cible numérique de retour net
- le runtime actuel consomme pourtant une variable nommée `ml_confidence` avec neutralité à `0.5`

Ce qu'on ne peut pas figer sans arbitrage :
- classifier binaire
- regression continue
- ou calibration probabiliste intermédiaire

Ce qu'on peut déjà exclure comme canon prod-safe :
- une régression continue brute simplement **clippée dans `[0,1]`** puis interprétée comme une probabilité
- une sortie nommée `ml_confidence` sans définition probabiliste ou calibration explicite

Conséquence canonique :
- tant que le formalisme cible n'est pas fermé, le trainer actuel reste `REPLAY_ONLY_DOCTRINAL_PROVISIONAL`
- une promotion ML réelle ne doit pas s'appuyer sur la sémantique actuelle `regression -> clip -> confidence`

## Canon du dataset

### KNOWN - Source de données autorisée
Le dataset ML doit provenir du **replay/backtest gouverné**.

Sources autorisées :
- features reconnues au moment de la décision
- contexte route/scoring
- outcome replay
- DTR aligné si disponible

### KNOWN - Forme minimale du dataset
Le canon V1 n'est **pas** un registre ambitieux de 29 features.

Le canon V1 minimal est :
- features numériques reconnues au temps de décision
- métriques de route/scoring observables
- outcome replay / DTR aligné

### STALE_OR_REDUNDANT - `ml_dataset_builder.py`
Le chemin doctrinal `src/calibration_methods/ml_dataset_builder.py` ne doit pas piloter le code.

Seam réel actuel :
- `src/local_replay_runtime/ml_backtest_projection.py`
- `src/calibration_methods/ml_backtest_projection.py`
- `src/local_replay_runtime/local_lab_ml_artifact_training.py`

Donc :
- le concept "dataset builder" reste valide
- le chemin fichier imposé par certains markdowns ne fait pas partie du canon

## Canon des features

### KNOWN - Règle scientifique
Une feature ne devient canonique que si :
- sa formule est fermée,
- sa source est définie,
- son alignement temporel est défini,
- sa disponibilité runtime est claire si elle doit être utilisée au runtime.

### RESEARCH_ONLY - Registre 29 features
Le registre de 29 features proposé dans `SPEC_FULL_V2` ne devient pas canon V1.

Raison :
- trop large pour le niveau de preuve actuel
- pas entièrement fermé côté runtime-compatible feature schema
- pas entièrement recodé ni validé dans le repo actuel

### RESEARCH_ONLY - Features V2 de MD2
Les features suivantes restent hors canon V1 tant qu'elles ne sont pas fermées et raccordées proprement :
- `cvd_divergence_20`
- `adr_ratio`
- `hhi_trades`
- `aci_score`
- `ppe_score`
- `dei_entropy`
- `vsd_deviation`
- `funding_oi_interaction`
- `pair_liquidity_rank`

### EXCLUDED_FROM_V1
- `ADX` comme feature structurante
- toute feature sans fermeture mathématique claire
- toute feature non observable proprement à `t`

## Canon de l'artefact

### KNOWN - Artefact modèle
L'artefact ML doit être :
- typé
- hashé
- versionné
- transportable
- consommable côté runtime sans training code

### KNOWN - Champs gouvernants
Les champs suivants font partie du canon d'artefact :
- `schema_version`
- `model_family`
- `feature_hash`
- `pair_universe`
- `train_window`
- `validation_window`
- `oos_sharpe`
- `backtest_sharpe`
- `promotion_state`
- `training_seed`
- `artifact_hash`
- `created_at`
- `calibration_version`
- `dataset_hash`

### KNOWN - Transport runtime
Le transport runtime doit passer par des `supplementary_refs` gouvernés.

Le runtime ne doit pas consommer :
- un trainer
- un dataset builder
- une logique de fit

## Canon de la fusion runtime

### KNOWN - Formule exacte
La formule canonique est :

`fused_score = base_score * (1 + alpha * (ml_confidence - 0.5))`

Conséquences :
- `ml_confidence = 0.5` => neutre
- `alpha = 0` => neutre
- `ml_confidence > 0.5` => uplift
- `ml_confidence < 0.5` => penalty

### KNOWN - Bornes runtime
- `alpha <= 0.5`
- `alpha > 0.5` interdit
- `side` inchangé
- aucun override moteur
- aucune mutation de `bet_structure`
- aucun changement de famille de refus

### KNOWN - Point d'insertion canonique
Le point d'insertion runtime canonique est le **hook Build-5 de soft penalty / score modulation**.

Ce que cela exclut :
- brancher directement le ML dans la logique souveraine A/B/C/D
- court-circuiter `ScoringRuntime`

## Canon de la promotion

### KNOWN - Gate fail-closed
La promotion ML doit rester fail-closed.

Critères canoniques :
- `oos_sharpe >= 0.80 * backtest_sharpe`
- `ks_test_features_pvalue > 0.05`
- `shadow_diff_pct < 0.1`
- hash artefact valide
- métriques manquantes => blocage

### KNOWN - Conséquence opérationnelle
Tant que `shadow_diff_pct` n'est pas produit proprement, la promotion ML ne doit pas s'ouvrir.

### UNKNOWN - Producteur canonique de `shadow_diff_pct`
Le repo a la gate, mais pas encore le producteur canonique fermé de `shadow_diff_pct`.
Ce point reste hors canon d'exécution tant qu'il n'est pas spécifié et prouvé.

## SHAP

### UNKNOWN
SHAP ne fait pas partie du canon V1 d'exécution.

Ce que l'on sait :
- une référence `shap_summary_ref` existe comme champ optionnel

Ce qu'on ne sait pas encore défendre comme canon :
- SHAP obligatoire
- SHAP comme condition de promotion
- SHAP comme outil de contrôle prod systématique

Donc SHAP reste :
- `OPTIONAL_RESEARCH_AUDIT`

## Contradictions documentaires identifiées

### P0 - Type de modèle
- Docs ML : classifier
- Code actuel : regression
- Runtime actuel : consomme `ml_confidence` comme si la sortie était probabiliste/neutre à `0.5`
- Verdict : contradiction réelle, arbitrage humain requis
- Verdict critique additionnel : la chaîne actuelle `target continu -> regression -> clip [0,1] -> ml_confidence`
  n'est pas une sémantique finale de promotion prod-safe

### P0 - Dataset builder
- Docs ML : `ml_dataset_builder.py`
- Repo réel : projection scindée replay -> contrat -> rows -> trainer
- Verdict : le seam réel doit primer, l'ancien chemin fichier est stale

### P1 - Registre 29 features
- Docs larges : objectif quasi complet
- Repo réel : dataset minimal et gouverné, plus étroit
- Verdict : registre complet hors canon V1

### P1 - SHAP
- Docs larges : inclus
- Repo réel : seulement optionnel
- Verdict : hors canon d'exécution V1

## Plan de recodage sûr à partir de ce canon

### P0
Trancher explicitement :
- `classifier` ou `regression`

Sous-règle de sûreté :
- si `classifier`, fermer d'abord le label binaire, l'horizon et la marge nette
- si `regression`, renoncer au vocabulaire probabiliste runtime ou ajouter une calibration explicite

Sans cette décision, le trainer reste un état provisoire, pas un canon final.

### P1
Figer un **runtime-compatible feature schema** :
- quelles features du training doivent aussi être disponibles au scoring time
- quelles features restent training-only

### P2
Propager `supplementary_refs` ML jusqu'aux builders `ScoringCandidateInput` A/B/C/D

### P3
Construire le producteur canonique de `shadow_diff_pct`

### P4
Reclassifier les docs ML existants :
- `MASTER` = index
- `MD1` = doctrine active après nettoyage
- `MD2` = checklist active après nettoyage
- `SPEC_FULL_V2` = archive / superseded

## Règle finale
Si un point n'est pas marqué `KNOWN` ici :
- il ne doit pas piloter une modification profonde du code,
- sauf arbitrage humain explicite.
