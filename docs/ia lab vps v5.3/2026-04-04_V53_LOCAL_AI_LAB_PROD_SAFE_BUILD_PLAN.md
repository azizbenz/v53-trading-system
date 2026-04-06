# V5.3 — LOCAL AI LAB PROD-SAFE BUILD PLAN
## Construction explicite et détaillée du laboratoire local IA
### Date : 2026-04-04
### Statut : LOCAL LAB BUILD PLAN

---

# 0. Objet

Ce document décrit **comment construire le Local AI Lab** de manière prod-safe.

Il répond à ces questions :

- que doit faire le Lab ?
- que ne doit-il pas faire ?
- quelles IA utiliser ?
- quelles données utiliser ?
- comment parler à la VPS ?
- comment exporter des artifacts ?
- comment éviter qu’il devienne une seconde V5.3 incontrôlée ?

---

# 1. Mission exacte du Local AI Lab

Le Local AI Lab n’est pas un runtime de trading live.

Il est une usine de :

- datasets
- replay
- backtest fidèle
- diagnostics
- calibration
- petits modèles utiles
- distillation de règles
- preuve
- packaging d’artifacts
- boucle de retour depuis la VPS

---

# 2. Ce que le Lab doit savoir faire

## 2.1 Data
- télécharger des données
- lire un dossier local
- enregistrer des datasets
- vérifier l’intégrité
- partitionner en Parquet
- versionner

## 2.2 Replay
- rejouer le shared core V5.3
- produire des bundles comparatifs
- comparer baseline vs hypothèse

## 2.3 Feature factory
- construire seulement des features autorisées
- appliquer feature lock et transform lock
- versionner les features

## 2.4 Diagnostic
- lire DTR
- lire no-trades
- lire trades phantom
- classer les patterns d’échec
- proposer des hypothèses de correction

## 2.5 Calibration
- seuils de sweep
- seuils de spread widening
- seuils de friction
- seuils de toxicité
- seuils de delta divergence
- seuils de void / absorption

## 2.6 IA utile
- entraîner de petits modèles tabulaires
- mesurer leur stabilité
- rejeter les modèles trop complexes
- distiller vers règles compactes

## 2.7 Export
- packager des artifacts
- signer les artifacts
- produire le résumé de preuve
- uploader vers la VPS

## 2.8 Retour VPS
- fetch des batches closed-loop
- joindre features, décisions, réalité
- préparer retraining et diagnostic

---

# 3. Ce que le Lab ne doit jamais faire

1. Créer sa propre logique de trading live
2. Remplacer la souveraineté de la VPS
3. Exporter du code Python
4. Exporter un modèle opaque en runtime V1/V2
5. Utiliser un LLM comme décideur critique
6. Contourner le shared core
7. Créer des features hors Physics Lock
8. Pousser directement vers Live

---

# 4. Politique IA du Lab

## 4.1 IA principales

Le cœur du Lab doit utiliser :

- XGBoost
- LightGBM
- CatBoost
- modèles tabulaires simples
- calibrateurs probabilistes
- classeurs reason-code based

## 4.2 Pourquoi ces IA

Parce qu’elles sont :
- adaptées au tabulaire
- CPU-friendly
- explicables relativement
- distillables
- compatibles avec ta machine locale

## 4.3 IA secondaires

LLM local uniquement pour :
- résumés
- mise en forme de rapports
- synthèse narrative

### Interdit
- classification critique
- taxonomie critique
- prise de décision
- génération directe de règles runtime

---

# 5. Politique de données du Lab

## 5.1 Timeframe maître
- `1m`

## 5.2 Timeframes dérivés
- `5m`
- `15m`
- `1h`

## 5.3 Profondeur historique
- archive : 2020 -> 2026
- entraînement principal : 2022 -> 2025
- holdout : 2026
- archive stress : 2020 -> 2021

## 5.4 Paires V1
- BTCUSDT
- ETHUSDT
- SOLUSDT
- BNBUSDT
- XRPUSDT
- LINKUSDT

## 5.5 Data heavy ciblée
Le Lab ne stocke pas tout le carnet complet partout.

Il stocke en haute résolution surtout autour de :
- sweeps
- spread widening
- faux breakouts
- absorptions
- trades litigieux
- événements shadow/live importants

---

# 6. Architecture interne du Lab

## Couche A — Dataset Registry
Rôle :
- enregistrer datasets
- hash
- version
- source
- période
- paires
- schéma

## Couche B — Data Acquisition
Rôle :
- downloader
- loader dossier local
- normaliser
- écrire Parquet partitionné

## Couche C — Local Replay
Rôle :
- exécuter V5.3 shared core en LOCAL_REPLAY
- produire evidence et bundles

## Couche D — Physics Feature Factory
Rôle :
- calculer les features autorisées
- appliquer lineage
- mettre en cache

## Couche E — Diagnostic Engine
Rôle :
- classer échecs
- détecter patterns
- générer hypothèses

## Couche F — Threshold Calibrator
Rôle :
- ajuster les seuils
- coarse-to-fine
- walk-forward

## Couche G — Micro-Model Lab
Rôle :
- entraîner petits modèles
- comparer
- sélectionner
- mesurer stabilité

## Couche H — Rule Distiller
Rôle :
- transformer modèle en règle compacte
- valider action_unit
- mapper les reason codes

## Couche I — Causal Validator
Rôle :
- valider ablation
- anti-cowardice
- friction regret
- burden
- segmentation régime
- capital efficiency

## Couche J — Artifact Packer
Rôle :
- sérialiser
- signer
- hasher
- exporter

## Couche K — Closed-Loop Client
Rôle :
- fetch batch VPS
- lire Parquet
- préparer diagnostics / retraining

---

# 7. Formats d’artifacts autorisés

Formats autorisés :
- `THRESHOLD_JSON`
- `LOOKUP_JSON`
- `RULE_AST_JSON`

Formats interdits :
- Python code
- ONNX runtime V1/V2
- binaire opaque
- notebook exécutable
- script injecté

---

# 8. Politique de preuve du Lab

Aucun artifact ne peut être exporté sans :

1. ablation baseline vs candidate
2. anti-cowardice pass
3. friction regret pass
4. walk-forward pass
5. regime segmentation pass
6. operational burden pass
7. capital efficiency pass si applicable

---

# 9. Relation du Lab avec la VPS

## 9.1 Le Lab doit pouvoir
- uploader un artifact
- demander son statut
- fetch des batches closed-loop
- fetch des logs ciblés
- lire la santé runtime de la VPS

## 9.2 Le Lab ne doit pas
- pousser directement en live
- ouvrir une session d’exécution décisionnelle
- streamer des commandes runtime
- contrôler les ordres

---

# 10. Relation du Lab avec plusieurs VPS

Le Lab peut parler à :
- 1 VPS
- 3 VPS
- 5 serveurs ou plus

Mais idéalement via :
- control plane central
- ou APIs gouvernées
- jamais via bricolage manuel seulement

Le Lab doit pouvoir :
- savoir quel artifact tourne où
- savoir quelle VPS dérive
- fetch des batches depuis chaque VPS
- comparer Shadow sur plusieurs VPS si nécessaire

---

# 11. Sécurité du Lab

## Obligatoire
- clé privée locale pour signature
- hash du payload
- schéma artifact strict
- aucune exportation libre de code
- journal d’export artifact

## Interdit
- clé privée sur VPS
- signature côté serveur
- artifact non signé
- artifact non tracé

---

# 12. Roadmap de construction du Lab

## Étape 1 — Doctrine & locks
- feature lock
- transform lock
- taxonomy
- complexity guard

## Étape 2 — Datasets
- registry
- downloader
- loader local
- parquet partitioning

## Étape 3 — Replay
- local replay runner
- parity bundles
- baseline comparisons

## Étape 4 — Feature factory
- features physiques
- labels
- cache

## Étape 5 — Diagnostic & calibration
- DTR reader
- reason-code clustering
- threshold calibrator

## Étape 6 — Micro-models
- XGBoost / LightGBM / CatBoost
- stability evaluator
- feature budget

## Étape 7 — Distillation
- threshold JSON
- lookup JSON
- action units
- reason code mapping

## Étape 8 — Proof
- ablation
- anti-cowardice
- friction regret
- walk-forward
- burden
- capital efficiency

## Étape 9 — Packaging & signing
- bundle builder
- signer
- export manifest

## Étape 10 — Closed-loop
- fetch client
- parquet reader
- retrain dataset builder

---

# 13. GO / NO-GO Lab

## GO si
- replay fidèle
- features lockées
- modèles petits et stables
- distillation claire
- preuves complètes
- artifacts signés
- interactions VPS bornées

## NO-GO si
- le Lab devient une seconde V5.3
- explosion de dépendances
- embeddings / vector DB dans la boucle critique
- LLM décisionnel
- modèles opaques
- règles non distillées
- artifacts sans preuve

---

# 14. Conclusion

Le Local AI Lab doit être construit comme :

- un laboratoire
- une usine à preuve
- une usine à distillation
- une usine à packaging d’artifacts
- une machine de retour closed-loop

Il ne doit jamais devenir :
- une plateforme de trading parallèle
- une plateforme ML open bar
- une deuxième V5.3 secrète

L’ordre correct est donc :

1. comprendre la cible canonique
2. migrer la VPS existante sans la casser
3. construire le Lab pour enrichir la VPS par preuve, pas par magie
