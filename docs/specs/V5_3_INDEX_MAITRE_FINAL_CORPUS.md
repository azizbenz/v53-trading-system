# V5.3 — INDEX MAÎTRE FINAL DU CORPUS
## Répertoire canonique de navigation
### Version développeur / quant / risk / opérateur
### Sans code
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

## Niveau 1 bis — Miroir secondaire
Le document suivant peut être conservé comme support de lecture, mais ne fait **pas** foi s’il diverge :
- `V5_3_MASTER_FINAL_CANONICAL.md`

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
# 1 bis. Statut final des documents

## 1 bis.1 Actifs principaux
- `V5_3_MASTER_FINAL_UNIQUE.md`
- `V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`
- les specs Build-1 à Build-17
- les tables détaillées encore actives

## 1 bis.2 Actifs secondaires subordonnés
- `V5_3_MASTER_FINAL_CANONICAL.md` : miroir secondaire, non autonome
- `V5_3_TABLE_MODULES_ANNEXE_MATH_DETAILLEE.md`
- `V5_3_TABLE_DETAILLEE_MOTEURS.md`
- `V5_3_TABLE_DETAILLEE_INTERFACE_UTILISATEUR.md`
- `V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md`
- `V5_3_BUILD14_AI_EDGE_AND_MICROSTRUCTURE_ENRICHMENT_ADDENDUM.md`
- `V5_3_STRATEGY_ONBOARDING_PROTOCOL.md`
- `V5_3_UNIFIED_LOCAL_VPS_BACKTEST_ARCHITECTURE_PLAN_V2.md`
- `V5_3_LOCAL_REPLAY_BACKTEST_RUNTIME_SPEC.md`
- `V5_3_BUILD9X_SPEC_META_LEARNING_GOVERNED_LAYER_V2_FREEZE_READY.md`

## 1 bis.3 Meta-docs actifs
- `V5_3_AUDIT_INTEGRATION_DECISIONS.md`
- `V5_3_CHANGELOG_DOCUMENTAIRE_AUDIT_INTEGRATION.md`
- `V5_3_DOC_TO_CODE_ALIGNMENT_PLAN.md`
- `V5_3_CORPUS_STABILIZATION_REPORT.md`

## 1 bis.4 Historiques
- `V5_3_BUILD9X_SPEC_META_LEARNING_GOVERNED_LAYER.md`

## 1 bis.5 Archives
- `V5_3_ARCHIVE_COMBINED_WORKING_COPY_BUILD14_ONBOARDING_LOCAL_VPS.md`

## 1 bis.6 Contaminants potentiels
- tout document secondaire utilisé contre `V5_3_MASTER_FINAL_UNIQUE.md`
- `V5_3_MASTER_FINAL_CANONICAL.md` s’il est lu comme un second master au lieu d’un miroir
- toute annexe ou addendum qui réintroduirait une doctrine Build-14 en lecture seule ou une activation tardive de C/D

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

## 4.1 Sources de vérité et pilotage
- `V5_3_MASTER_FINAL_UNIQUE.md` : master officiel unique, a lire en premier
- `V5_3_MASTER_FINAL_CANONICAL.md` : miroir secondaire, lecture de support seulement
- `V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md` : ordre reel de construction Build-1 a Build-17
- `V5_3_PROMPT_PACK_CLAUDE_CHATGPT_BUILD_BY_BUILD.md` : orchestration IA, non source autonome
- `V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md` : gouvernance de merge et de changement de phase
- `V5_3_CORPUS_STABILIZATION_REPORT.md` : matrice finale du statut de tous les fichiers Markdown

## 4.2 Tables et annexes transverses actives
- `V5_3_TABLE_MODULES_ANNEXE_MATH_DETAILLEE.md` : modules + annexe math subordonnee au master unique
- `V5_3_TABLE_DETAILLEE_MOTEURS.md` : referentiel detaille A/B/C/D
- `V5_3_TABLE_DETAILLEE_INTERFACE_UTILISATEUR.md` : referentiel UI et supervision
- `V5_3_BUILD14_AI_EDGE_AND_MICROSTRUCTURE_ENRICHMENT_ADDENDUM.md` : addendum Build-14, non autonome
- `V5_3_BUILD9X_SPEC_META_LEARNING_GOVERNED_LAYER_V2_FREEZE_READY.md` : extension meta active, gouvernee, non autonome

## 4.3 Specs Build-1 a Build-10
- `V5_3_BUILD1_SPECS_MODULES.md` : architecture de dependances
- `V5_3_BUILD2_SPECS_MODULES.md` : data backbone
- `V5_3_BUILD3_SPECS_MODULES.md` : execution backbone
- `V5_3_BUILD4_SPECS_MODULES.md` : risk backbone
- `V5_3_BUILD5_SPECS_MODULES.md` : scoring backbone
- `V5_3_BUILD6_SPECS_MOTEUR_A.md` : moteur A
- `V5_3_BUILD7_SPECS_MOTEUR_B.md` : moteur B
- `V5_3_BUILD8_SPECS_PORTFOLIO_MINIMAL.md` : portefeuille minimal
- `V5_3_BUILD9_SPECS_META_MINIMAL.md` : meta minimal
- `V5_3_BUILD10_SPECS_MONITORING_UI_LIGHT.md` : monitoring + UI operateur verrouillee (`Light UI` = libelle historique)

## 4.4 Specs Build-11 a Build-17
- `V5_3_BUILD11_SPEC_SHADOW_LIGHT.md` : protocole Shadow gouverne (`Shadow Light` = libelle historique)
- `V5_3_BUILD12_SPEC_MICRO_LIVE_LIGHT.md` : protocole Micro-live gouverne (`Micro-live Light` = libelle historique)
- `V5_3_BUILD13_SPEC_LIVE_LIGHT.md` : protocole Live gouverne (`Live-Light` = libelle historique)
- `V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md` : enablers Complete actifs en Shadow
- `V5_3_BUILD15_SPECS_MOTEUR_C.md` : moteur C
- `V5_3_BUILD16_SPECS_MOTEUR_D.md` : moteur D
- `V5_3_BUILD17_SPEC_UI_COMPLETE_LIVE_COMPLETE.md` : UI Complete + Live-Complete

## 4.5 Runtime local / VPS et onboarding
- `V5_3_UNIFIED_LOCAL_VPS_BACKTEST_ARCHITECTURE_PLAN_V2.md` : architecture active commune local / VPS
- `V5_3_LOCAL_REPLAY_BACKTEST_RUNTIME_SPEC.md` : replay et backtest local sur donnees historiques
- `V5_3_STRATEGY_ONBOARDING_PROTOCOL.md` : onboarding, classification et promotion gouvernee
- regle : `import d'artifact cote VPS en lecture seule` designe un guardrail d'import, pas une mise en archive du runtime VPS

## 4.6 Meta-docs actifs
- `V5_3_AUDIT_INTEGRATION_DECISIONS.md`
- `V5_3_CHANGELOG_DOCUMENTAIRE_AUDIT_INTEGRATION.md`
- `V5_3_DOC_TO_CODE_ALIGNMENT_PLAN.md`
- `V5_3_INDEX_MAITRE_FINAL_CORPUS.md`
- `V5_3_CORPUS_STABILIZATION_REPORT.md`

## 4.7 Historiques et archives
- `V5_3_BUILD9X_SPEC_META_LEARNING_GOVERNED_LAYER.md` : historique, non binding
- `V5_3_ARCHIVE_COMBINED_WORKING_COPY_BUILD14_ONBOARDING_LOCAL_VPS.md` : archive de travail, non canonique

Note :

- la matrice exhaustive du statut final de tous les fichiers Markdown `docs/specs` est tenue dans `V5_3_CORPUS_STABILIZATION_REPORT.md`
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
À croiser avec : master + prompt pack + tables moteurs

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
# 10. Ensemble documentaire de base à transmettre à un nouveau développeur
Si tu veux donner un pack de base à quelqu’un qui rejoint le projet, envoie seulement :
1. `V5_3_MASTER_FINAL_UNIQUE.md`
2. `V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`
3. `V5_3_PROMPT_PACK_CLAUDE_CHATGPT_BUILD_BY_BUILD.md`
4. le fichier spec du build courant

Le reste vient ensuite selon les besoins.

---
# 11. Ensemble documentaire de base à transmettre à un reviewer quant/risk
1. master final
2. table détaillée des moteurs
3. table merge gates
4. spec du build ou moteur concerné

---
# 12. Ensemble documentaire de base à transmettre à un opérateur
1. master final
2. table UI
3. protocole de phase courant (Shadow / Micro-live / Live / Live-Complete, avec libelles historiques conserves dans certains noms de fichiers)
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
