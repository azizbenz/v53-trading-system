# V5.3 — CHANGELOG DOCUMENTAIRE — Audit Integration Pass
## Date : 31 mars 2026
## Scope : Intégration des audits tiers Gemini, Opus, Qwen

Note de lecture :

- ce document contient plusieurs sous-passes successives
- en cas d’écart entre deux sous-passes, **la plus récente prime**
- depuis le second pass du **1 avril 2026**, la hiérarchie finale est stabilisée autour de `V5_3_MASTER_FINAL_UNIQUE.md` comme source de vérité unique

---

# Fichiers créés

| Fichier | Rôle |
|---|---|
| `V5_3_AUDIT_INTEGRATION_DECISIONS.md` | Rapport de triage complet — classification de chaque finding |
| `V5_3_DOC_TO_CODE_ALIGNMENT_PLAN.md` | Plan de réalignement code → docs patchées, build par build |
| `V5_3_CHANGELOG_DOCUMENTAIRE_AUDIT_INTEGRATION.md` | Ce document |

---

# Fichiers modifiés

## 1. V5_3_MASTER_FINAL_UNIQUE.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| 0.3 Intégration audits tiers | **Ajoutée** | Principe officiel : audit = matière de correction, pas doctrine | Tous |
| 0.4 Distinction codé/validé/promu | **Ajoutée** | Empêcher confusion entre code existant et code validé/promu | OPUS, GEM |
| 0.5 Guardrails P0 (12 invariants) | **Ajoutée** | Injection des 12 invariants système P0 issus des audits | GEM-01 à GEM-23, QWEN-01/07 |
| 17. Build-14 conditions non-promotion | **Ajoutée** | Forcer le statut non-promu de Build-14 | OPUS |
| 18. Protocole intégration audits | **Ajoutée** | Formaliser le pipeline d'intégration des audits | Tous |

## 2. V5_3_MASTER_FINAL_CANONICAL.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| 0.3 à 0.5 | **Ajoutées** | Miroir du MASTER UNIQUE — mêmes sections | Tous |
| 26. Build-14 non-promotion | **Ajoutée** | Cohérence avec MASTER UNIQUE | OPUS |
| 27. Protocole audits | **Ajoutée** | Cohérence avec MASTER UNIQUE | Tous |

## 3. V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| Phase Audit Integration Pass | **Ajoutée** (entre Build-0 et Build-1) | Formaliser le pass documentaire comme phase du plan | Tous |
| Règle transversale codé/validé/promu | **Ajoutée** (fin de document) | Clarifier pour tous les builds | OPUS |

## 4. V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| Guardrails P0 issus des audits | **Ajoutée** | 8 catégories d'invariants obligatoires pour toute merge gate | Tous |
| Test intégration minimal obligatoire | **Ajoutée** | Pipeline data→engine→scoring→portfolio→execution | GEM, QWEN-03 |

## 5. V5_3_BUILD1_SPECS_MODULES.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| 10bis. Guardrails P0 Build-1 | **Ajoutée** | 8 guardrails : crossed book, epsilon, DAG, recovery, persistance, kill switch, smoke tests | GEM-01/02/03/04/10/19/20, QWEN-01/07 |
| Section 13 dérives | **Modifiée** | 5 items ajoutés à la liste existante | GEM-03/04/10/19 |

## 6. V5_3_BUILD2_SPECS_MODULES.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| Guardrails P0 Build-2 | **Ajoutée** | 6 guardrails : buffer, jitter, stale, latence, backlog, socket vs flux | GEM-05/06/08/18/23, QWEN-03/13 |

## 7. V5_3_BUILD3_SPECS_MODULES.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| Guardrails Build-3 | **Ajoutée** | 5 renforcements : coût réel, market impact, no-trade, latence, réconciliation | GEM-07/07b/07c/08, QWEN-03 |

## 8. V5_3_BUILD4_SPECS_MODULES.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| Guardrails Build-4 | **Ajoutée** | 4 renforcements : drawdown, beta statique, proxy vs réel, calibration future | GEM-09, QWEN-09 |

## 9. V5_3_BUILD8_SPECS_PORTFOLIO_MINIMAL.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| Guardrails Build-8 | **Ajoutée** | 5 renforcements : anti-churn, conflit redondant, coût opportunité, no-trade, time invalidation | GEM-07b/13/14 |

## 10. V5_3_BUILD9_SPECS_META_MINIMAL.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| Guardrails Build-9 | **Ajoutée** | 4 renforcements : méta utile vs vide, vrais chemins, auto-référence, persistance DTR | QWEN-01, GEM-15 |

## 11. V5_3_BUILD10_SPECS_MONITORING_UI_LIGHT.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| Guardrails Build-10 | **Ajoutée** | 4 renforcements : high-water marks, volatile/persisté, illusion verte, notification | GEM-18, QWEN-03/06 |

## 12. V5_3_BUILD11_SPEC_SHADOW_LIGHT.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| Guardrails Build-11 | **Ajoutée** | 5 préconditions : runtime réel, I/O, shadow ≠ in-memory, stale, configs YAML | QWEN-03/04, GEM-23 |

## 13. V5_3_BUILD12_SPEC_MICRO_LIVE_LIGHT.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| Guardrails Build-12 | **Ajoutée** | 6 préconditions : I/O réel, event loop, sortie positions, réconciliation, stale bloquant, config | QWEN-01/03, GEM-07c/19/23 |

## 14. V5_3_BUILD13_SPEC_LIVE_LIGHT.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| Guardrails Build-13 | **Ajoutée** | 5 préconditions : runtime complet, notification, approbation, kill switch, checklist minimale | QWEN-03/04/06/07/08, GEM-10 |

## 15. V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| Enablers absorbés audits | **Ajoutée** | 9 enablers classés avec statut forcé | GEM-11/21/22/24 |
| Statut forcé (7 règles) | **Ajoutée puis remplacée** | Grille initiale read-only / limited influence, ensuite remplacée le 31 mars par la doctrine `SHADOW_ENABLED` en Shadow | OPUS, GEM |
| Conditions promotion | **Ajoutée** | Light stable 30 jours minimum | OPUS |

## 16. V5_3_BUILD14_AI_EDGE_AND_MICROSTRUCTURE_ENRICHMENT_ADDENDUM.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| Clarification post-audit | **Ajoutée** | Enrichissements absorbés, RESEARCH_LOCAL classés, pipeline canonique | GEM-21/22/24/25 |

## 17. V5_3_UNIFIED_LOCAL_VPS_BACKTEST_ARCHITECTURE_PLAN_V2.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| Guardrails LOCAL/VPS | **Ajoutée** | 6 renforcements : feature bridge, parity, research vs shadow, fork, replay utile, market impact | GEM-15 |

## 18. V5_3_TABLE_DETAILLEE_MOTEURS.md

| Section | Action | Raison | Lien audit |
|---|---|---|---|
| Guardrails moteurs | **Ajoutée** | 4 renforcements : régime gate B, time invalidation, anti-churn, confirmation microstructure | GEM-12/13/14, GEM-11 |

---

# Fichiers NON modifiés

| Fichier | Raison |
|---|---|
| V5_3_BUILD5_SPECS_MODULES.md | Pas de finding audit ciblant Build-5 spécifiquement |
| V5_3_BUILD6_SPECS_MOTEUR_A.md | Renforcements Engine A absorbés dans TABLE_MOTEURS et BUILD-14 |
| V5_3_BUILD7_SPECS_MOTEUR_B.md | Renforcements Engine B absorbés dans TABLE_MOTEURS |
| V5_3_TABLE_DETAILLEE_INTERFACE_UTILISATEUR.md | Pas de finding audit P0 ciblant l'UI spécifiquement lors du sous-pass initial ; harmonisée ensuite par pass doctrinal et pass de stabilisation |
| V5_3_TABLE_MODULES_ANNEXE_MATH_DETAILLEE.md | Pas de correction mathématique P0 initiale ; harmonisée ensuite par pass de stabilisation |

---

---

# Pass documentaire stratégique — Nouvelle doctrine Shadow complet (31 mars 2026)

## Décision de gouvernance

Le Shadow 30 jours devient la **phase de vérité système complète** :
- Build-14 activé à 100% en Shadow (plus en lecture seule)
- Moteurs C/D activés à 100% en Shadow (plus attendus uniquement après Light)
- Tous les enrichissements pleinement utilisés et observés
- Promotion live reste strictement conditionnelle au verdict post-Shadow

## Système HARD STATE introduit

Nouveau cycle de vie documentaire officiel :
`CODED` → `DOCUMENTED` → `SHADOW_ENABLED` → `SHADOW_VALIDATED` → `MICRO_LIVE_ELIGIBLE` → `LIVE_LIGHT_ELIGIBLE` → `COMPLETE_ELIGIBLE` → `PROMOTED` | `DORMANT` | `FORBIDDEN`

## Fichiers modifiés

| Fichier | Sections modifiées |
|---|---|
| V5_3_MASTER_FINAL_UNIQUE.md | 0.4 (Hard States), 0.6 (HARD STATEMENT — Shadow vérité), 5.2 (Light profil), 7.5 (signal), 8.3 (C), 8.4 (D) |
| V5_3_MASTER_FINAL_CANONICAL.md | 0.4 (Hard States), 0.6 (HARD STATEMENT), 5.2 (Light bornes) |
| V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md | Build-11 (Shadow complet), Build-12 (prérequis verdict), Build-13 (prérequis verdict), Build-14 (gouvernance), Build-15/16 (C/D Shadow) |
| V5_3_BUILD11_SPEC_SHADOW_LIGHT.md | Mission (Shadow vérité), 4.3-4.6 (vérités ajoutées), 6.1-6.7 (périmètre complet + Hard States + verdict) |
| V5_3_BUILD12_SPEC_MICRO_LIVE_LIGHT.md | 1 (relation verdict post-Shadow) |
| V5_3_BUILD13_SPEC_LIVE_LIGHT.md | HARD STATEMENT (prérequis verdict composant par composant) |
| V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md | 0 (activé 100% Shadow), 0.2 (relation), 6.1-6.2 (mode activation), 6.5 (règles activation) |
| V5_3_BUILD15_SPECS_MOTEUR_C.md | 2 (doctrine Shadow), 3 (activation Shadow) |
| V5_3_BUILD16_SPECS_MOTEUR_D.md | 2 (doctrine Shadow), 3 (activation Shadow) |
| V5_3_BUILD17_SPEC_UI_COMPLETE_LIVE_COMPLETE.md | 2 (relation Shadow complet) |
| V5_3_TABLE_DETAILLEE_MOTEURS.md | 1.5 (Hard States moteurs), 2 (tableau maître) |
| V5_3_TABLE_DETAILLEE_INTERFACE_UTILISATEUR.md | 1.2 (affichage Hard States, verdicts, contributions) |
| V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md | 6.1-6.4 (Shadow complet, métriques, verdict) |
| V5_3_UNIFIED_LOCAL_VPS_BACKTEST_ARCHITECTURE_PLAN_V2.md | 7.1 (relation Shadow complet) |
| V5_3_DOC_TO_CODE_ALIGNMENT_PLAN.md | Nouvelle section doctrine Shadow |

## Conséquences de gouvernance

- **Plus strict** : le Shadow teste maintenant la solution complète, pas un sous-ensemble minimal
- **Plus strict** : verdict composant par composant obligatoire avant promotion
- **Plus strict** : chaque composant peut être mis en `DORMANT` malgré activation Shadow
- **Inchangé** : 30 jours minimum, interruption > 24h = reset, promotion live jamais automatique
- **Changé** : Build-14 n'est plus en lecture seule en Shadow, il est actif à 100%
- **Changé** : C/D ne sont plus attendus après Light, ils sont essayés en Shadow et promus si validés

---

# Second pass documentaire de stabilisation — 1 avril 2026

## Décision de stabilisation

Le corpus est stabilisé autour des règles suivantes :

- `V5_3_MASTER_FINAL_UNIQUE.md` = **source de vérité unique**
- `V5_3_MASTER_FINAL_CANONICAL.md` = **miroir secondaire**, non source autonome
- toute table, annexe, addendum ou document transverse actif est **subordonné** au master unique
- Build-14 = `SHADOW_ENABLED` en Shadow
- moteurs A/B/C/D = activés et utilisés en Shadow
- activation Shadow ≠ promotion live
- promotion = verdict composant par composant

## Fichiers corrigés lors du second pass

- `V5_3_MASTER_FINAL_UNIQUE.md`
- `V5_3_MASTER_FINAL_CANONICAL.md`
- `V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`
- `V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md`
- `V5_3_TABLE_DETAILLEE_MOTEURS.md`
- `V5_3_TABLE_DETAILLEE_INTERFACE_UTILISATEUR.md`
- `V5_3_TABLE_MODULES_ANNEXE_MATH_DETAILLEE.md`
- `V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md`
- `V5_3_BUILD17_SPEC_UI_COMPLETE_LIVE_COMPLETE.md`
- `V5_3_BUILD14_AI_EDGE_AND_MICROSTRUCTURE_ENRICHMENT_ADDENDUM.md`
- `V5_3_BUILD9X_SPEC_META_LEARNING_GOVERNED_LAYER_V2_FREEZE_READY.md`
- `V5_3_UNIFIED_LOCAL_VPS_BACKTEST_ARCHITECTURE_PLAN_V2.md`
- `V5_3_AUDIT_INTEGRATION_DECISIONS.md`
- `V5_3_DOC_TO_CODE_ALIGNMENT_PLAN.md`
- `V5_3_INDEX_MAITRE_FINAL_CORPUS.md`
- `V5_3_CORPUS_STABILIZATION_REPORT.md`

## Contradictions supprimées

- double master actif
- rattachements actifs à `V5_3_MASTER_FINAL_CANONICAL.md` dans les tables normatives
- reliquats Build-14 en lecture seule / influence limitée dans les specs actives
- mise en phase Build-17 incompatible avec A/B/C/D + Build-14 actifs en Shadow
- ambiguïté dans les annexes math sur le rôle Shadow des métriques enrichies

## État final du changelog

- la doctrine documentaire est stabilisée
- le code reste partiellement contradictoire avec cette doctrine
- le document `V5_3_DOC_TO_CODE_ALIGNMENT_PLAN.md` porte désormais l’état honnête docs ↔ code

## Fin du changelog
