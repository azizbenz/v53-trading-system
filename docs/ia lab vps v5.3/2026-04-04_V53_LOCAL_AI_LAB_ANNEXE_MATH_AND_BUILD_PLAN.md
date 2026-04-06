# V5.3 — LOCAL AI LAB
## Annexe mathématique + plan de développement build par build
### Date : 2026-04-04
### Statut : BUILD PLAN EXÉCUTABLE POUR CODEX

---

# 0. Objet

Ce document a deux objectifs :

1. définir l’**annexe mathématique** du Local AI Lab
2. définir un **ordre build par build**, détaillé et exécutable, pour que Codex puisse coder le Lab de façon prod-safe

Ce document n’est pas une note stratégique.  
C’est une **spécification de construction**.

---

# 1. Mission du Local AI Lab

Le Local AI Lab doit :

- télécharger ou charger des données locales
- rejouer fidèlement la logique V5.3
- calculer des features lockées
- diagnostiquer les échecs
- calibrer les seuils
- entraîner de petits modèles utiles
- distiller des règles
- prouver leur utilité
- signer des artifacts
- récupérer les batches closed-loop de la VPS

Le Lab ne doit jamais :

- devenir une seconde V5.3 live
- exporter du code exécutable
- exporter une boîte noire runtime en V1/V2
- utiliser un LLM comme décideur logique

---

# 2. Annexe mathématique du Lab

## 2.1 Physics Feature Dictionary — familles autorisées

Les features d’entraînement autorisées doivent provenir exclusivement des familles suivantes :

- delta proxy
- cumulative delta
- OFI / OBI
- microprice deviation
- spread regime
- slippage / friction proxy
- volume profile
- POC / HVN / LVN / VAH / VAL
- sweep score
- absorption score
- false breakout score
- toxicity score
- resiliency score
- refill speed
- execution survivability score
- regime features enrichies
- portfolio crowding / overlap

---

## 2.2 Delta proxy

\[
\Delta V_t^{proxy} = \frac{C_t - O_t}{\max(H_t - L_t,\epsilon)} \cdot V_t
\]

## 2.3 Cumulative delta

\[
CD_t = \sum_{u=t-k+1}^{t}\Delta V_u^{proxy}
\]

## 2.4 Spread regime

\[
SpreadRel_t = \frac{Ask_t - Bid_t}{Mid_t}
\]

\[
SpreadZ_t = \frac{SpreadRel_t - \mu_{Spread,W}}{\sigma_{Spread,W} + \epsilon}
\]

## 2.5 Participation

\[
Participation_t = \frac{OrderSize_t}{\overline{Vol}_{1m,t} + \epsilon}
\]

## 2.6 Slippage proxy

\[
SlipProxy_t = a_1 SpreadRel_t + a_2 \sigma_{1m,t} + a_3 Participation_t
\]

## 2.7 Sweep score

\[
SweepScore_t = w_1 \cdot WickRatio_t + w_2 \cdot VolBurst_t + w_3 \cdot Reject_t
\]

## 2.8 Absorption score

\[
AbsorptionScore_t = \frac{|OFI_t^{norm}|}{|\Delta P_t| + \epsilon}
\]

## 2.9 Void score

\[
VoidScore_t = 1 - \frac{\sum_{p \in \mathcal{R}} Vol(p;W)}{|\mathcal{R}| \cdot \overline{Vol}_W + \epsilon}
\]

## 2.10 Toxicity score

\[
Toxicity_t = d_1 |OFI_t^{norm}| + d_2 SpreadZ_t + d_3 VolJump_t + d_4 Fragility_t
\]

## 2.11 Execution survivability

\[
ESS_t = c_1(1-SpreadZ_t^{+}) + c_2 Resiliency_t + c_3 RefillSpeed_t - c_4 Toxicity_t - c_5 Fragility_t
\]

---

# 3. Règles mathématiques de construction du Lab

## 3.1 Feature budget

Un modèle candidat ne peut pas utiliser plus de :
- minimum 5 features
- maximum 20 features

Mais le budget réel doit aussi respecter :
- `max_conditions_per_rule`
- `min_rule_support_count`
- `min_regime_coverage_count`
- `max_fragility_score`

## 3.2 Rule support

Une règle distillée doit avoir un support suffisant dans :
- train
- validation
- walk-forward

## 3.3 Drift régime

Pour un artifact, le Lab doit stocker :

- `regime_feature_means`
- `covariance_shrinkage_matrix_ref`
- `drift_score_threshold`

Distance live vs entraînement :

\[
D_M(x_t) = \sqrt{(x_t - \mu_{train})^T \Sigma_{shrunk}^{-1}(x_t - \mu_{train})}
\]

avec :

\[
\Sigma_{shrunk} = (1-\alpha)\Sigma + \alpha \cdot \operatorname{diag}(\Sigma)
\]

## 3.4 Anti-cowardice condition

Une amélioration n’est pas valide si elle vient uniquement d’une chute non justifiée de fréquence utile.

## 3.5 Friction regret

\[
FrictionRegret = -\sum P_{blocked}^{positive}
\]

## 3.6 Capital efficiency

\[
CE_i = \frac{\mathbb{E}[PnL_i^{net}]}{x_i \cdot h_i + \epsilon}
\]

## 3.7 Classe D — variance / Sharpe

\[
Sharpe = \frac{\mu_r}{\sigma_r + \epsilon}
\]

ou

\[
VarReduction = \sigma^2_{base} - \sigma^2_{artifact}
\]

---

# 4. Choix d’IA du Lab

## 4.1 IA principales

- XGBoost
- LightGBM
- CatBoost
- modèles tabulaires simples
- calibrateurs

## 4.2 IA interdites comme cœur

- gros deep learning opaque
- export ONNX runtime V1/V2
- LLM critique
- vector DB critique

## 4.3 LLM local

Autorisé seulement pour :
- résumé humain
- formatage de rapport
- synthèse narrative

Jamais pour :
- classification critique
- décision
- distillation
- validation

---

# 5. Politique de données du Lab

## 5.1 Timeframe maître
- `1m`

## 5.2 Timeframes dérivés
- `5m`
- `15m`
- `1h`

## 5.3 Données historiques
- archive 2020 -> 2026
- train principal 2022 -> 2025
- holdout 2026
- archive stress 2020 -> 2021

## 5.4 Paires V1
- BTCUSDT
- ETHUSDT
- SOLUSDT
- BNBUSDT
- XRPUSDT
- LINKUSDT

---

# 6. Build order du Lab — vue d’ensemble

```text
Build-L0  Doctrine locks
Build-L1  Dataset registry
Build-L2  Data acquisition
Build-L3  Local replay bridge
Build-L4  Physics feature factory
Build-L5  Diagnostic engine
Build-L6  Threshold calibrator
Build-L7  Micro-model lab
Build-L8  Rule distillation
Build-L9  Proof protocol
Build-L10 Artifact packer & signer
Build-L11 Closed-loop client
Build-L12 Control-plane aware lab integration
```

---

# 7. BUILD-L0 — Doctrine Locks

## Modules
- feature dictionary
- transform whitelist
- feature lineage validator
- transform lineage validator
- complexity guard
- artifact taxonomy enums

## Objectif
Empêcher le Lab de dériver avant même d’entraîner le premier modèle.

## Fichiers à créer
- `src/local_ai_lab/feature_lock/feature_dictionary.py`
- `src/local_ai_lab/feature_lock/transform_whitelist.py`
- `src/local_ai_lab/feature_lock/feature_lineage_validator.py`
- `src/local_ai_lab/feature_lock/transform_lineage_validator.py`
- `src/local_ai_lab/micro_model_lab/feature_budget_guard.py`
- `src/local_ai_lab/enums.py`

## Tests obligatoires
- feature interdite rejetée
- transformation interdite rejetée
- feature sans lineage rejetée
- max feature budget enforced

## Go si
- aucune feature hors lock
- aucune transformation hors lock
- taxonomie A/B/C/D stable

---

# 8. BUILD-L1 — Dataset Registry

## Modules
- dataset contracts
- registry service
- integrity checker

## Objectif
Donner au Lab une mémoire structurée de ses datasets.

## Fichiers à créer
- `src/local_ai_lab/dataset_registry/contracts.py`
- `src/local_ai_lab/dataset_registry/models.py`
- `src/local_ai_lab/dataset_registry/repository.py`
- `src/local_ai_lab/dataset_registry/registry_service.py`
- `src/local_ai_lab/dataset_registry/integrity_checker.py`

## Contrats minimaux
- `DatasetRegistrationRequest`
- `DatasetRegistrationRecord`

## Tests obligatoires
- hash dataset valide
- hash invalide rejeté
- schéma dataset invalide rejeté

## Go si
- dataset_id unique
- schéma versionné
- intégrité vérifiable

---

# 9. BUILD-L2 — Data Acquisition

## Modules
- downloader
- local folder loader
- parquet writer
- normalization pipeline

## Objectif
Télécharger ou lire des données, puis les normaliser vers un format canonique.

## Fichiers à créer
- `src/local_ai_lab/data_acquisition/exchange_downloader.py`
- `src/local_ai_lab/data_acquisition/local_folder_loader.py`
- `src/local_ai_lab/data_acquisition/parquet_partition_writer.py`
- `src/local_ai_lab/data_acquisition/normalization_pipeline.py`

## Politique de partitionnement recommandée
- pair / year / month

## Tests obligatoires
- téléchargement -> Parquet correct
- dossier local -> Parquet correct
- base timeframe = 1m validé
- paires invalides rejetées

## Go si
- datasets normalisés
- partitionnement stable
- métadonnées complètes

---

# 10. BUILD-L3 — Local Replay Bridge

## Modules
- replay bridge
- evidence exporter
- parity runner

## Objectif
Faire tourner le shared core V5.3 en local sans fork logique.

## Fichiers à créer
- `src/local_ai_lab/replay_bridge.py`
- `src/local_ai_lab/replay_evidence_exporter.py`
- `src/local_ai_lab/parity_runner.py`

## Tests obligatoires
- parité d’état de décision
- parité reason codes
- parité baseline replay

## Go si
- même logique métier que V5.3
- même no-trade
- mêmes états critiques

---

# 11. BUILD-L4 — Physics Feature Factory

## Modules
- feature builder
- window aggregator
- label builder
- cache

## Objectif
Construire toutes les features physiques autorisées et les rendre réutilisables.

## Fichiers à créer
- `src/local_ai_lab/feature_factory/contracts.py`
- `src/local_ai_lab/feature_factory/base_feature_builder.py`
- `src/local_ai_lab/feature_factory/physics_feature_builder.py`
- `src/local_ai_lab/feature_factory/window_aggregator.py`
- `src/local_ai_lab/feature_factory/label_builder.py`
- `src/local_ai_lab/feature_factory/cached_feature_store.py`

## Labels utiles
- trade profitable net / non
- sweep fade success / fail
- breakout continuation success / fail
- execution survivability success / fail

## Tests obligatoires
- delta proxy correct
- cumulative delta correct
- spread z-score correct
- sweep score correct
- void score correct
- forbidden transform rejection

## Go si
- features versionnées
- lineage intact
- cache réutilisable

---

# 12. BUILD-L5 — Diagnostic Engine

## Modules
- DTR reader
- outcome classifier
- reason-code clusterer
- failure pattern ranker
- hypothesis generator

## Objectif
Transformer l’historique de décisions en cartes d’échecs exploitables.

## Fichiers à créer
- `src/local_ai_lab/diagnostic_engine/dtr_reader.py`
- `src/local_ai_lab/diagnostic_engine/outcome_classifier.py`
- `src/local_ai_lab/diagnostic_engine/reason_code_clusterer.py`
- `src/local_ai_lab/diagnostic_engine/failure_pattern_ranker.py`
- `src/local_ai_lab/diagnostic_engine/hypothesis_generator.py`

## Règle critique
Clustering déterministe basé sur :
- reason codes
- états
- outcomes
- contexte

Pas d’embeddings critiques.

## Tests obligatoires
- clustering stable sur même input
- motifs d’échec reproductibles
- hypothèse textuelle liée à evidence réelle

## Go si
- les classes d’échecs sont lisibles
- les hypothèses ne sont pas générées à vide

---

# 13. BUILD-L6 — Threshold Calibrator

## Modules
- calibration runner
- coarse-to-fine search
- walk-forward evaluator
- threshold report builder

## Objectif
Calibrer les seuils sans grille brute géante.

## Fichiers à créer
- `src/local_ai_lab/threshold_calibrator/calibration_runner.py`
- `src/local_ai_lab/threshold_calibrator/coarse_to_fine_search.py`
- `src/local_ai_lab/threshold_calibrator/walk_forward_evaluator.py`
- `src/local_ai_lab/threshold_calibrator/threshold_report_builder.py`

## Seuils visés
- sweep score
- spread widening
- toxicity
- friction
- delta divergence
- void score
- absorption score

## Tests obligatoires
- calibration reproductible
- walk-forward stable
- meilleur seuil différent de baseline si gain réel

## Go si
- seuils stables
- gains non purement in-sample

---

# 14. BUILD-L7 — Micro-Model Lab

## Modules
- dataset builder
- trainers
- model selection
- stability evaluator
- importance reporter

## Objectif
Entraîner des modèles utiles et petits.

## Fichiers à créer
- `src/local_ai_lab/micro_model_lab/dataset_builder.py`
- `src/local_ai_lab/micro_model_lab/trainer_xgboost.py`
- `src/local_ai_lab/micro_model_lab/trainer_lightgbm.py`
- `src/local_ai_lab/micro_model_lab/trainer_catboost.py`
- `src/local_ai_lab/micro_model_lab/model_selection.py`
- `src/local_ai_lab/micro_model_lab/stability_evaluator.py`
- `src/local_ai_lab/micro_model_lab/importance_reporter.py`

## Contraintes
- 5 à 20 features max
- modèles petits
- importance explicable
- pas de boîte noire runtime

## Tests obligatoires
- feature budget enforced
- sélection modèle stable
- importance feature disponible
- modèle rejeté si trop fragile

## Go si
- le modèle est utile
- le modèle est compressible
- le modèle est stable hors échantillon

---

# 15. BUILD-L8 — Rule Distillation

## Modules
- rule distiller
- threshold JSON builder
- lookup JSON builder
- action unit validator
- reason code mapper
- complexity guard

## Objectif
Transformer le modèle en règle compacte et sûre.

## Fichiers à créer
- `src/local_ai_lab/distillation/rule_distiller.py`
- `src/local_ai_lab/distillation/threshold_json_builder.py`
- `src/local_ai_lab/distillation/lookup_json_builder.py`
- `src/local_ai_lab/distillation/action_unit_validator.py`
- `src/local_ai_lab/distillation/reason_code_mapper.py`
- `src/local_ai_lab/distillation/rule_complexity_guard.py`

## Règle absolue
- pas de Python exporté
- pas d’ONNX
- pas de logique libre

## Tests obligatoires
- `action_unit` obligatoire
- `reason_code` obligatoire
- règle hors scope rejetée
- code Python rejeté
- schema JSON valide

## Go si
- règle compacte
- hook target clair
- influence bornée

---

# 16. BUILD-L9 — Proof Protocol

## Modules
- ablation runner
- anti-cowardice test
- friction regret test
- walk-forward test
- regime segmentation test
- operational burden test
- capital efficiency test
- verdict builder

## Objectif
Refuser tout artifact non prouvé.

## Fichiers à créer
- `src/local_ai_lab/causal_validation/ablation_runner.py`
- `src/local_ai_lab/causal_validation/anti_cowardice_test.py`
- `src/local_ai_lab/causal_validation/friction_regret_test.py`
- `src/local_ai_lab/causal_validation/walk_forward_test.py`
- `src/local_ai_lab/causal_validation/regime_segmentation_test.py`
- `src/local_ai_lab/causal_validation/operational_burden_test.py`
- `src/local_ai_lab/causal_validation/capital_efficiency_test.py`
- `src/local_ai_lab/causal_validation/validation_verdict_builder.py`

## Tests obligatoires
- artifact stérile rejeté
- artifact coûteux rejeté
- artifact utile accepté
- classe D validée sur variance/Sharpe/CE

## Go si
- verdict global stable
- toutes les preuves présentes
- pas de gain illusoire

---

# 17. BUILD-L10 — Artifact Packer & Signer

## Modules
- bundle builder
- payload hasher
- signature service
- bundle exporter
- manifest exporter

## Objectif
Créer un artifact sûr, signé, vérifiable.

## Fichiers à créer
- `src/local_ai_lab/artifact_packer/artifact_bundle_builder.py`
- `src/local_ai_lab/artifact_packer/payload_hasher.py`
- `src/local_ai_lab/artifact_packer/signature_service.py`
- `src/local_ai_lab/artifact_packer/bundle_exporter.py`
- `src/local_ai_lab/artifact_packer/manifest_exporter.py`

## Sécurité
- Ed25519
- clé privée locale uniquement
- hash du payload
- export manifest

## Tests obligatoires
- signature valide
- signature invalide rejetée
- hash mismatch détecté

## Go si
- artifact portable
- signature vérifiable
- schéma complet

---

# 18. BUILD-L11 — Closed-Loop Client

## Modules
- batch fetch client
- parquet reader
- reality joiner
- drift feedback builder
- retrain dataset builder

## Objectif
Faire revenir la réalité VPS dans le Lab sans coupling dangereux.

## Fichiers à créer
- `src/local_ai_lab/closed_loop/batch_fetch_client.py`
- `src/local_ai_lab/closed_loop/batch_parquet_reader.py`
- `src/local_ai_lab/closed_loop/reality_joiner.py`
- `src/local_ai_lab/closed_loop/drift_feedback_builder.py`
- `src/local_ai_lab/closed_loop/retrain_dataset_builder.py`

## Règle
- batch only
- jamais streaming critique
- jamais bloquant

## Tests obligatoires
- batch fetch incrémental
- lecture Parquet correcte
- join décision / réalité correcte

## Go si
- retrain dataset propre
- feedback drift disponible

---

# 19. BUILD-L12 — Control-plane aware integration

## Modules
- status client
- artifact status fetch
- multi-VPS awareness
- reporting centralisé

## Objectif
Permettre au Lab de travailler proprement avec plusieurs VPS.

## Fichiers à créer
- `src/local_ai_lab/control_plane_client.py`
- `src/local_ai_lab/artifact_status_fetcher.py`
- `src/local_ai_lab/multi_vps_context.py`
- `src/local_ai_lab/fleet_comparison_reporter.py`

## Ce que le Lab doit pouvoir faire
- savoir où tourne un artifact
- savoir quelle VPS est en dérive
- comparer plusieurs Shadow
- fetch logs ciblés

## Tests obligatoires
- vue multi-VPS stable
- artifact fleet query correcte
- comparaison inter-VPS correcte

## Go si
- le Lab reste centralisé
- aucune logique live ne lui est transférée

---

# 20. Ordre d’exécution Codex recommandé

Codex doit exécuter dans cet ordre exact :

1. Build-L0
2. Build-L1
3. Build-L2
4. Build-L3
5. Build-L4
6. Build-L5
7. Build-L6
8. Build-L7
9. Build-L8
10. Build-L9
11. Build-L10
12. Build-L11
13. Build-L12

## Règle critique
- aucun build ne commence si les tests du précédent ne sont pas verts
- aucun artifact runtime schema n’est codé avant Build-L8
- aucun upload réel vers VPS avant Build-L10
- aucun closed-loop avant Build-L11

---

# 21. Invariants finaux du Lab

1. Une seule logique métier V5.3.
2. Aucune feature hors Physics Lock.
3. Aucune transformation hors whitelist.
4. Aucun LLM dans la boucle critique.
5. Aucun code exporté.
6. Aucun modèle opaque runtime V1/V2.
7. Aucun artifact sans preuve.
8. Aucun artifact sans signature.
9. Aucun closed-loop bloquant.
10. Le Lab n’est jamais souverain sur le live.

---

# 22. Conclusion

Le Local AI Lab doit être construit comme une **chaîne industrielle de découverte, preuve et distillation**, pas comme un terrain libre de machine learning.

Le bon ordre build par build est celui ci-dessus.

Codex doit comprendre que :

- le Lab ne sert pas à inventer une seconde V5.3
- le Lab sert à fabriquer des règles physiques prouvées
- la VPS reste souveraine
- la preuve passe avant l’intelligence
