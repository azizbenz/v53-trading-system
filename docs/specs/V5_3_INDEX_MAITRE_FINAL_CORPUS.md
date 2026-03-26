# V5.3 — INDEX MAÎTRE FINAL DU CORPUS## Répertoire canonique de navigation### Version développeur / quant / risk / opérateur### Sans code
---
# 0. Objet du document
Ce document est le **point d’entrée unique de navigation** pour l’ensemble du corpus V5.3.
Il ne remplace pas le master final, mais il dit immédiatement :
- quel fichier ouvrir
- dans quel ordre
- pour quelle tâche
- lequel fait foi
- lequel est un support secondaire

Le but est d’éviter quatre dérives classiques :
1. ouvrir le mauvais fichier
2. travailler sur un support secondaire au lieu du document canonique
3. mélanger Light et Complete
4. coder hors ordre de build

---
# 1. Hiérarchie de vérité documentaire
## Niveau 1 — Canonique absolu
Le document qui fait foi au-dessus de tous les autres est :
- `V5_3_MASTER_FINAL_UNIQUE.md`

## Niveau 2 — Canonique de progression
Le document qui fixe l’ordre réel de construction est :
- `V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`

## Niveau 3 — Canonique d’exécution IA
Le document qui fixe comment utiliser Claude Pro / ChatGPT Pro est :
- `V5_3_PROMPT_PACK_CLAUDE_CHATGPT_BUILD_BY_BUILD.md`

## Niveau 4 — Référentiels détaillés transverses
Ces documents détaillent des sous-domaines et servent de support de conception :
- table des modules
- table des moteurs
- table UI
- table merge gates

## Niveau 5 — Specs build par build
Ce sont les documents à utiliser pour développer ou auditer chaque étape concrète.

---
# 2. Ordre de lecture minimal recommandé
Pour une personne nouvelle dans le projet, l’ordre minimal est :
1. `V5_3_MASTER_FINAL_UNIQUE.md`
2. `V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`
3. `V5_3_PROMPT_PACK_CLAUDE_CHATGPT_BUILD_BY_BUILD.md`
4. le fichier spec du build concerné
5. les tables détaillées si besoin de profondeur supplémentaire

---
# 3. Ordre de lecture selon le rôle
## 3.1 Développeur backend
Lire dans cet ordre :
1. master final
2. build plan
3. spec du build courant
4. prompt pack
5. table détaillée des modules

## 3.2 Reviewer quant / risk
Lire dans cet ordre :
1. master final
2. table détaillée des moteurs
3. table des merge gates
4. spec du build ou moteur concerné
5. annexe math/module table si besoin

## 3.3 Opérateur / supervision
Lire dans cet ordre :
1. master final
2. table UI
3. merge gates
4. Build-10 à Build-13 ou Build-17 selon profil

## 3.4 Utilisation Claude Pro / ChatGPT Pro
Lire dans cet ordre :
1. prompt pack
2. master final
3. build plan
4. spec du build/module

---
# 4. Index maître de tous les fichiers
| Fichier | Statut | Quand l’ouvrir | Contenu / usage |
|---|---|---|---|| `V5_3_MASTER_FINAL_UNIQUE.md` | Source de vérité unique | À lire en premier | Architecture canonique complète, profils Light/Complete, modules, moteurs, UI, merge gates, maths utiles, interdits, workflow IA. || `V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md` | Plan d’exécution global | Juste après le master | Ordre réel de construction Build-0 à Build-17, objectifs, critères GO/NO-GO, logique de progression. || `V5_3_PROMPT_PACK_CLAUDE_CHATGPT_BUILD_BY_BUILD.md` | Manuel d’orchestration IA | Avant toute session Claude/ChatGPT | Prompts maîtres, prompts par build, workflow spec → code → audit → correction → merge gate. || `V5_3_TABLE_MODULES_ANNEXE_MATH_DETAILLEE.md` | Table détaillée des modules | Quand on conçoit une brique | Référentiel détaillé par module, sous-composants, logs, tests, dérives à éviter, activation Light/Complete. || `V5_3_TABLE_DETAILLEE_MOTEURS.md` | Table détaillée des moteurs | Quand on compare A/B/C/D | Vue consolidée des 4 moteurs, paires autorisées, logique économique, contraintes, désactivation. || `V5_3_TABLE_DETAILLEE_INTERFACE_UTILISATEUR.md` | Référentiel UI | Quand on conçoit l’interface | Écrans, composants, actions autorisées/interdites, comportement Light/Complete, tests UI. || `V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md` | Référentiel de gouvernance | Avant merge ou changement de phase | Gates de module, build, profil, Shadow, Micro-live, Live-Light, Live-Complete. || `V5_3_BUILD1_SPECS_MODULES.md` | Spec Build-1 | Début du développement | Dependency Architecture Pack : interface_contracts, manifest_registry, dag_validator, contract_test_suite, smoke_bootstrap_recovery. || `V5_3_BUILD2_SPECS_MODULES.md` | Spec Build-2 | Après Build-1 | Data Backbone Pack : websocket_gateway, rest_bootstrap, event_normalizer, internal_router, freshness_checker, consistency_checker, pair_health_scorer. || `V5_3_BUILD3_SPECS_MODULES.md` | Spec Build-3 | Après Build-2 | Execution Backbone Pack : order_decider, fill_tracker, execution_cost_meter, reconciliation_layer. || `V5_3_BUILD4_SPECS_MODULES.md` | Spec Build-4 | Après Build-3 | Risk Backbone Pack : exposure_budgeter, loss_budgeter, btc_factor_guard, correlation_cluster_guard. || `V5_3_BUILD5_SPECS_MODULES.md` | Spec Build-5 | Après Build-4 | Scoring Backbone Pack : raw_score_builder, penalty_aggregator, hard_block_gate, ranking_router. || `V5_3_BUILD6_SPECS_MOTEUR_A.md` | Spec Build-6 | Après Build-5 | Moteur A — Premium Trend / Expansion. || `V5_3_BUILD7_SPECS_MOTEUR_B.md` | Spec Build-7 | Après Build-6 | Moteur B — Mean Reversion Intraday. || `V5_3_BUILD8_SPECS_PORTFOLIO_MINIMAL.md` | Spec Build-8 | Après Build-7 | Portfolio Minimal Pack : opportunity_selector, allocation_router. || `V5_3_BUILD9_SPECS_META_MINIMAL.md` | Spec Build-9 | Après Build-8 | Meta Minimal Pack : dtr_core, cra_monitor, break_even_dashboard, edge_tracker_prudent_minimal. || `V5_3_BUILD10_SPECS_MONITORING_UI_LIGHT.md` | Spec Build-10 | Après Build-9 | Monitoring + UI Light Pack : metrics_collector, alert_manager, health_dashboard_backend, ui_light_locked. || `V5_3_BUILD11_SPEC_SHADOW_LIGHT.md` | Spec Build-11 | Quand Build-10 est prêt | Protocole Shadow Light, critères GO/NO-GO pré-micro-live. || `V5_3_BUILD12_SPEC_MICRO_LIVE_LIGHT.md` | Spec Build-12 | Après Shadow GO | Protocole Micro-live Light, tailles ultra-prudentes, coût réel, kill/halt conditions. || `V5_3_BUILD13_SPEC_LIVE_LIGHT.md` | Spec Build-13 | Après Micro-live GO | Protocole Live-Light, montée en charge prudente, DEGRADED/HALTED/rollback. || `V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md` | Spec Build-14 | Après Light stable | Complete Enablers : microstructure enrichie, régime enrichi, covariance robuste, risk contributions, K_eff. || `V5_3_BUILD15_SPECS_MOTEUR_C.md` | Spec Build-15 | Après Build-14 | Moteur C — Breakout Continuation. || `V5_3_BUILD16_SPECS_MOTEUR_D.md` | Spec Build-16 | Après Build-15 | Moteur D — Re-entry / Second Chance Logic. || `V5_3_BUILD17_SPEC_UI_COMPLETE_LIVE_COMPLETE.md` | Spec Build-17 | Fin de trajectoire | UI Complete + protocole Live-Complete 12 paires / 4 moteurs. |
---
# 5. Référentiel par phase de travail
## 5.1 Si tu veux comprendre l’architecture globale
Ouvrir :
1. `V5_3_MASTER_FINAL_UNIQUE.md`
2. `V5_3_TABLE_MODULES_ANNEXE_MATH_DETAILLEE.md`
3. `V5_3_TABLE_DETAILLEE_MOTEURS.md`

## 5.2 Si tu veux coder un module
Ouvrir :
1. `V5_3_MASTER_FINAL_UNIQUE.md`
2. `V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`
3. le fichier spec du build concerné
4. `V5_3_PROMPT_PACK_CLAUDE_CHATGPT_BUILD_BY_BUILD.md`

## 5.3 Si tu veux auditer un module
Ouvrir :
1. master final
2. spec du build concerné
3. table merge gates
4. prompt pack

## 5.4 Si tu veux travailler sur l’UI
Ouvrir :
1. master final
2. `V5_3_TABLE_DETAILLEE_INTERFACE_UTILISATEUR.md`
3. Build-10 ou Build-17 selon profil

## 5.5 Si tu veux travailler sur les moteurs
Ouvrir :
1. master final
2. table détaillée des moteurs
3. Build-6/7/15/16 selon moteur

## 5.6 Si tu veux piloter une phase Shadow / Live
Ouvrir :
1. merge gates
2. Build-11/12/13/17 selon phase
3. table UI
4. prompt pack

---
# 6. Référentiel par build
## Build-1
Fichier principal : `V5_3_BUILD1_SPECS_MODULES.md`
À croiser avec : master + build plan + prompt pack

## Build-2
Fichier principal : `V5_3_BUILD2_SPECS_MODULES.md`
À croiser avec : master + build plan + prompt pack

## Build-3
Fichier principal : `V5_3_BUILD3_SPECS_MODULES.md`
À croiser avec : master + build plan + prompt pack

## Build-4
Fichier principal : `V5_3_BUILD4_SPECS_MODULES.md`
À croiser avec : master + build plan + prompt pack

## Build-5
Fichier principal : `V5_3_BUILD5_SPECS_MODULES.md`
À croiser avec : master + build plan + prompt pack

## Build-6
Fichier principal : `V5_3_BUILD6_SPECS_MOTEUR_A.md`
À croiser avec : master + table moteurs + prompt pack

## Build-7
Fichier principal : `V5_3_BUILD7_SPECS_MOTEUR_B.md`
À croiser avec : master + table moteurs + prompt pack

## Build-8
Fichier principal : `V5_3_BUILD8_SPECS_PORTFOLIO_MINIMAL.md`
À croiser avec : master + build plan + prompt pack

## Build-9
Fichier principal : `V5_3_BUILD9_SPECS_META_MINIMAL.md`
À croiser avec : master + merge gates + prompt pack

## Build-10
Fichier principal : `V5_3_BUILD10_SPECS_MONITORING_UI_LIGHT.md`
À croiser avec : table UI + merge gates + prompt pack

## Build-11
Fichier principal : `V5_3_BUILD11_SPEC_SHADOW_LIGHT.md`
À croiser avec : merge gates + table UI + prompt pack

## Build-12
Fichier principal : `V5_3_BUILD12_SPEC_MICRO_LIVE_LIGHT.md`
À croiser avec : merge gates + prompt pack

## Build-13
Fichier principal : `V5_3_BUILD13_SPEC_LIVE_LIGHT.md`
À croiser avec : merge gates + prompt pack

## Build-14
Fichier principal : `V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md`
À croiser avec : master + prompt pack + moteurs C/D futurs

## Build-15
Fichier principal : `V5_3_BUILD15_SPECS_MOTEUR_C.md`
À croiser avec : table moteurs + Build-14 + prompt pack

## Build-16
Fichier principal : `V5_3_BUILD16_SPECS_MOTEUR_D.md`
À croiser avec : table moteurs + Build-14 + prompt pack

## Build-17
Fichier principal : `V5_3_BUILD17_SPEC_UI_COMPLETE_LIVE_COMPLETE.md`
À croiser avec : table UI + merge gates + Build-14/15/16 + prompt pack

---
# 7. Cartographie des documents par usage rapide
## Si tu veux répondre à “qu’est-ce qui fait foi ?”
Réponse : `V5_3_MASTER_FINAL_UNIQUE.md`

## Si tu veux répondre à “dans quel ordre développe-t-on ?”
Réponse : `V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`

## Si tu veux répondre à “quel prompt envoyer à Claude / ChatGPT ?”
Réponse : `V5_3_PROMPT_PACK_CLAUDE_CHATGPT_BUILD_BY_BUILD.md`

## Si tu veux répondre à “comment merger proprement ?”
Réponse : `V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md`

## Si tu veux répondre à “quel fichier ouvrir pour tel build ?”
Réponse : le fichier `V5_3_BUILDX_...md` correspondant dans la section Build-1 à Build-17 ci-dessus.

---
# 8. Règles de navigation à imposer au développeur
1. Ne jamais travailler directement depuis un document secondaire si le master traite déjà le sujet.
2. Ne jamais coder un build sans ouvrir le build plan et la spec du build.
3. Ne jamais demander du code à une IA sans lui fournir le build exact et la spec exacte.
4. Ne jamais mélanger Light et Complete sans le dire explicitement.
5. Ne jamais prendre la table UI ou la table moteurs comme source de vérité supérieure au master.
6. Ne jamais considérer le prompt pack comme remplaçant de la spec du build.

---
# 9. Arbre minimal de décision documentaire
## Cas 1 — “Je veux comprendre le projet”
Ouvrir : master final.

## Cas 2 — “Je veux savoir quoi développer ensuite”
Ouvrir : build plan.

## Cas 3 — “Je veux développer un build précis”
Ouvrir : spec du build + prompt pack.

## Cas 4 — “Je veux auditer un moteur”
Ouvrir : table moteurs + spec du moteur + master.

## Cas 5 — “Je veux vérifier si on peut passer à la phase suivante”
Ouvrir : merge gates + protocole de phase correspondant.

## Cas 6 — “Je veux travailler l’interface”
Ouvrir : table UI + Build-10 ou Build-17.

---
# 10. Ensemble documentaire minimal à transmettre à un nouveau développeur
Si tu veux donner un pack minimum à quelqu’un qui rejoint le projet, envoie seulement :
1. `V5_3_MASTER_FINAL_UNIQUE.md`
2. `V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`
3. `V5_3_PROMPT_PACK_CLAUDE_CHATGPT_BUILD_BY_BUILD.md`
4. le fichier spec du build courant

Le reste vient ensuite selon les besoins.

---
# 11. Ensemble documentaire minimal à transmettre à un reviewer quant/risk
1. master final
2. table détaillée des moteurs
3. table merge gates
4. spec du build ou moteur concerné

---
# 12. Ensemble documentaire minimal à transmettre à un opérateur
1. master final
2. table UI
3. protocole de phase courant (Shadow / Micro-live / Live-Light / Live-Complete)
4. merge gates

---
# 13. Verdict final de l’index maître
Cet index existe pour éviter la dérive documentaire.

S’il est respecté :
- le développeur ouvre le bon fichier au bon moment
- le reviewer audite sur la bonne base
- l’opérateur sait où chercher selon la phase
- Claude Pro / ChatGPT Pro restent correctement encadrés
- le master final reste réellement la source de vérité

S’il n’est pas respecté :
- les documents seront utilisés dans le désordre
- des supports secondaires deviendront des pseudo-sources de vérité
- Light et Complete se mélangeront
- les builds dériveront

Donc :

> cet index doit être utilisé comme **table de navigation canonique du corpus V5.3**.

---
## Fin du document
