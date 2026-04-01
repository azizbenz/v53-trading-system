# Annexe de preuves - Audit independant V5.3
## Date: 31 mars 2026

Cette annexe conserve les ancrages principaux utilises pour le rapport principal.

## 1. Sources de verite et hierarchie

- `docs/specs/V5_3_INDEX_MAITRE_FINAL_CORPUS.md:21-30`
  - place `V5_3_MASTER_FINAL_UNIQUE.md` au-dessus de tous les autres.
- `docs/specs/V5_3_MASTER_FINAL_UNIQUE.md:10`
  - declare la "source de verite unique".
- `docs/specs/V5_3_MASTER_FINAL_CANONICAL.md:11-16`
  - se declare encore "reference canonique unique".
- `docs/specs/V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md:3`
- `docs/specs/V5_3_TABLE_DETAILLEE_MOTEURS.md:3`
- `docs/specs/V5_3_TABLE_DETAILLEE_INTERFACE_UTILISATEUR.md:3`
- `docs/specs/V5_3_TABLE_MODULES_ANNEXE_MATH_DETAILLEE.md:3`
  - restent branches sur `MASTER_FINAL_CANONICAL`.

## 2. Nouvelle doctrine Shadow complete

- `docs/specs/V5_3_MASTER_FINAL_UNIQUE.md:68-91`
  - Hard States documentaires.
- `docs/specs/V5_3_MASTER_FINAL_UNIQUE.md:109-145`
  - Shadow comme phase de verite systeme complete.
- `docs/specs/V5_3_BUILD11_SPEC_SHADOW_LIGHT.md:60-76`
  - mission du Shadow complet.
- `docs/specs/V5_3_BUILD11_SPEC_SHADOW_LIGHT.md:184-202`
  - A/B/C/D et Build-14 actifs a 100% en Shadow.
- `docs/specs/V5_3_BUILD12_SPEC_MICRO_LIVE_LIGHT.md:69-74`
  - activation Shadow != activation Micro-live.
- `docs/specs/V5_3_BUILD13_SPEC_LIVE_LIGHT.md:21-27`
  - prerequis Shadow complet et verdict par composant.
- `docs/specs/V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md:27-31`
- `docs/specs/V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md:191-222`
- `docs/specs/V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md:663-673`
  - Build-14 actif en Shadow, promotion live conditionnelle.
- `docs/specs/V5_3_BUILD15_SPECS_MOTEUR_C.md:62-68`
- `docs/specs/V5_3_BUILD16_SPECS_MOTEUR_D.md:63-70`
  - C/D `SHADOW_ENABLED`.
- `docs/specs/V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md:329-356`
- `docs/specs/V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md:407-526`
  - gates Shadow et Build-14.
- `docs/specs/V5_3_TABLE_DETAILLEE_MOTEURS.md:70-103`
  - Hard States moteurs.
- `docs/specs/V5_3_TABLE_DETAILLEE_INTERFACE_UTILISATEUR.md:60-64`
  - UI censee afficher Hard States, moteurs A/B/C/D, Build-14 et verdicts.
- `docs/specs/V5_3_UNIFIED_LOCAL_VPS_BACKTEST_ARCHITECTURE_PLAN_V2.md:170-177`
  - local replay ne remplace pas le Shadow.

## 3. Reliquats de l'ancienne doctrine

- `docs/specs/V5_3_BUILD14_AI_EDGE_AND_MICROSTRUCTURE_ENRICHMENT_ADDENDUM.md:26-29`
  - Build-14 avec "influence limitee gouvernee".
- `docs/specs/V5_3_BUILD14_AI_EDGE_AND_MICROSTRUCTURE_ENRICHMENT_ADDENDUM.md:51-61`
- `docs/specs/V5_3_BUILD14_AI_EDGE_AND_MICROSTRUCTURE_ENRICHMENT_ADDENDUM.md:167-173`
  - meme document bascule ensuite vers `SHADOW_ENABLED`.
- `docs/specs/V5_3_BUILD9X_SPEC_META_LEARNING_GOVERNED_LAYER_V2_FREEZE_READY.md:77-80`
  - Build-14 encore resume comme "influence limitee".
- `docs/specs/V5_3_BUILD17_SPEC_UI_COMPLETE_LIVE_COMPLETE.md:605-608`
  - rollout en paliers incompatible avec la doctrine Shadow complete.
- `docs/specs/V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md:961-986`
  - `flag / diagnostic / soft veto / influence limitee` encore presents.
- `docs/specs/V5_3_ARCHIVE_COMBINED_WORKING_COPY_BUILD14_ONBOARDING_LOCAL_VPS.md:1-5`
  - archive non canonique.
- `docs/specs/V5_3_ARCHIVE_COMBINED_WORKING_COPY_BUILD14_ONBOARDING_LOCAL_VPS.md:889-899`
- `docs/specs/V5_3_ARCHIVE_COMBINED_WORKING_COPY_BUILD14_ONBOARDING_LOCAL_VPS.md:1674-1741`
  - ancienne doctrine archivee.

## 4. Changelog et docs -> code

- `docs/specs/V5_3_CHANGELOG_DOCUMENTAIRE_AUDIT_INTEGRATION.md:117`
  - conserve la grille "read-only, limited influence...".
- `docs/specs/V5_3_CHANGELOG_DOCUMENTAIRE_AUDIT_INTEGRATION.md:147`
  - dit que l'UI n'a pas ete modifiee.
- `docs/specs/V5_3_CHANGELOG_DOCUMENTAIRE_AUDIT_INTEGRATION.md:154-196`
  - annonce la nouvelle doctrine et liste l'UI parmi les fichiers modifies (`:184`).
- `docs/specs/V5_3_DOC_TO_CODE_ALIGNMENT_PLAN.md:20-24`
  - annonce Shadow comme verite systeme complete.
- `docs/specs/V5_3_DOC_TO_CODE_ALIGNMENT_PLAN.md:186-187`
  - dit Build-14 `SHADOW_ENABLED`.
- `docs/specs/V5_3_DOC_TO_CODE_ALIGNMENT_PLAN.md:203`
  - dit "All verified DORMANT / NOT PROMOTED".
- `docs/specs/V5_3_DOC_TO_CODE_ALIGNMENT_PLAN.md:245-251`
  - reconnait que Hard States, Build-14 actif en Shadow et C/D en Shadow ne sont pas codes.

## 5. Etat reel du code

### Build-14

- `src/complete_enablers/enums.py:8-21`
  - seulement `READ_ONLY` et `LIMITED_INFLUENCE`.
- `src/complete_enablers/contracts.py:16-42`
  - docstring "Read-only first, limited influence later, never autonomous."
- `src/complete_enablers/contracts.py:23-24`
  - mode par defaut `READ_ONLY`.
- `src/complete_enablers/contracts.py:38-41`
  - validation explicite read-only / limited influence.
- `src/complete_enablers/limited_influence.py:31-119`
  - logique de modulation bornee, pas activation pleine en Shadow.
- `src/complete_enablers/market_toxicity_snapshot.py:1-49`
  - "Read-only market toxicity reader", log key `build14.read_only.market_toxicity`.
- `src/complete_enablers/execution_fragility_score.py:1-48`
  - "Read-only execution fragility reader", log key `build14.read_only.execution_fragility`.
- `src/smoke_bootstrap_recovery/shadow_readiness.py:22`
- `src/smoke_bootstrap_recovery/shadow_readiness.py:70-91`
  - readiness basee sur `build14_read_only_fenced`.
- `src/monitoring/contracts.py:264-280`
  - `Build14Projection` = "limited-influence summary", defaults `read_only / observe`.
- `src/monitoring/technical_dashboard_backend.py:134-155`
  - projection par defaut Build-14 en `read_only`.
- `src/monitoring/technical_dashboard_backend.py:253-256`
  - texte "Build-14 limited influence remain governed".
- `src/ui/technical_dashboard_view.py:480-535`
  - section "Build-14 Limited Influence".
- `tests/test_complete_enablers/test_contracts.py:39-46`
- `tests/test_complete_enablers/test_contracts.py:71-92`
- `tests/test_complete_enablers/test_contracts.py:118-182`
  - tests structures autour de `read_only` et `limited_influence`.
- `tests/test_ui/test_technical_dashboard.py:224`
- `tests/test_ui/test_technical_dashboard.py:239`
- `tests/test_ui/test_technical_dashboard.py:243`
- `tests/test_ui/test_technical_dashboard.py:456-511`
  - tests UI centres sur "Build-14 Limited Influence".

### C et D

- `src/manifest_registry/module_inventory.py:254-285`
  - `complete_enablers`, `engine_c`, `engine_d` en `PLANNED`.
- `src/manifest_registry/profile_registry.py:4-12`
- `src/manifest_registry/profile_registry.py:51-69`
  - C/D absents des profils tant que non `ACTIVE`.
- `src/engines/engine_c/__init__.py:1`
- `src/engines/engine_d/__init__.py:1`
  - `ImportError`, moteurs non implementes.
- `tests/test_manifest_registry/test_runtime_surface.py:14-25`
  - imports canoniques ne couvrent pas C/D.

### Hard States et promotions

- `src/interface_contracts/domain_types.py:53-58`
  - `RuntimeMode` present.
- `src/interface_contracts/domain_types.py:73-81`
  - `PromotionState` present, mais pas les Hard States documentaires.
- `src/protocols/shadow_day_counter.py:1-196`
  - compteurs 30 jours Light/Complete.
- `src/protocols/promotion_gates.py:1-70`
  - gates temporels centraux.
- `src/backtest_artifact_import/validators.py:28-35`
- `src/backtest_artifact_import/validators.py:104-125`
  - pas de bypass, mais Build-14 reste `REPLAY_ONLY` et C/D restent "later builds".
- `src/protocols/live_light_runtime.py:216-271`
- `src/protocols/live_light_runtime.py:368-540`
- `src/protocols/live_light_runtime.py:622-628`
  - gating Live-Light encore construit autour du modele Build-14 `read_only / limited_influence`.
