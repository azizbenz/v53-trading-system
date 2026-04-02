# V5.3 — PLAN D'AUDIT CRITIQUE BUILD-1 À BUILD-14
## Date : 2026-04-02
## Statut : ACTIF

---

# 0. Objet

Ce document fixe le plan d'audit critique de `Build-1` à `Build-14`.

Objectif :

- produire un état des lieux fiable, build par build
- éviter toute dérive documentaire ou code "par intuition"
- séparer clairement ce qui est :
  - `ALIGNED`
  - `STILL PARTIAL`
  - `NOT READY`
  - `NOT RE-AUDITED YET`

Ce document n'est pas un canon.
Il organise l'exécution de l'audit.

---

# 1. Règles de vérité

Ordre de vérité obligatoire :

1. `docs/specs/V5_3_MASTER_FINAL_UNIQUE.md`
2. `docs/specs/V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`
3. les specs Build-1 à Build-14
4. `docs/specs/V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md`
5. tables et addenda actifs si subordonnés
6. handoffs / audits / worklogs comme contexte seulement

Règle :

- un handoff n'écrase jamais le canon
- un test vert n'écrase jamais une contradiction canonique
- un code présent n'équivaut jamais à un build validé

---

# 2. Politique anti-hallucination

Chaque verdict build doit reposer sur 4 piliers :

- référence doc
- référence code
- preuve test
- preuve runtime si le build touche l'exécution réelle ou la promotion

Si un pilier manque :

- le verdict ne peut pas dépasser `STILL PARTIAL`

Raccourcis interdits :

- "les tests passent donc c'est aligné"
- "le code existe donc le build est fait"
- "le handoff le dit donc le canon a changé"
- "le service tourne donc le protocole est satisfait"

---

# 3. Sorties attendues

Pour chaque build audité, il faudra produire :

1. obligations canoniques
2. surfaces code réellement concernées
3. tests existants et leur valeur probante
4. gaps classés `P0 / P1 / P2`
5. verdict provisoire
6. action suivante : `doc`, `code`, `test`, `runtime`, ou `governance`

Livrables finaux de la vague :

- un tableau Build-1 -> Build-14
- un registre de gaps priorisés
- un ordre de correction par lots
- une mise à jour mémoire JSON

---

# 4. Stratégie d'exécution

L'audit sera fait en 5 vagues.

## Vague A — Socle commun

Builds :

- Build-1
- Build-2
- Build-3
- Build-4
- Build-5

But :

- valider l'architecture de dépendances
- valider data / execution / risk / scoring
- vérifier que les invariants de base sont toujours cohérents avec le canon

## Vague B — Rollout Light coeur métier

Builds :

- Build-6
- Build-7
- Build-8
- Build-9
- Build-10

But :

- valider A / B / portfolio / meta / monitoring UI Light
- vérifier que le rollout Light canonique existe réellement sans contradiction majeure

## Vague C — Gates de promotion

Builds :

- Build-11
- Build-12
- Build-13

But :

- verrouiller Shadow / Micro-live / Live-Light
- vérifier les gates temporels, rapports, verdicts, onboarding et promotion

## Vague D — Enablers et extension gouvernée

Build :

- Build-14

But :

- vérifier que Build-14 reste un enabler gouverné
- vérifier son état réel en Shadow et son exposition dans contracts / monitoring / UI / Live-Light

## Vague E — Consolidation transversale

But :

- réunir les contradictions inter-builds
- trier `docs vs docs`, `docs vs code`, `tests en retard`, `runtime evidence missing`
- définir les lots de correction

---

# 5. Plan détaillé par build

## 5.1 Build-1 — Dependency Architecture

Canon à auditer :

- `docs/specs/V5_3_BUILD1_SPECS_MODULES.md`

Surfaces probables :

- `src/interface_contracts`
- graphes de dépendance
- manifests / registries / validators
- tests de contrat et bootstrap

Questions :

- les frontières de modules sont-elles toujours respectées ?
- y a-t-il des imports dynamiques ou cycles contraires au canon ?
- les contracts critiques sont-ils encore typés et stables ?

Verdict possible :

- `ALIGNED` seulement si doc + code + tests de dépendances convergent

## 5.2 Build-2 — Data Backbone

Canon :

- `docs/specs/V5_3_BUILD2_SPECS_MODULES.md`

Surfaces probables :

- data ingestion
- market events
- quality / stale / gap / timestamps
- tests data backbone

Questions :

- les invariants data critiques sont-ils codés ?
- le stale guard, disorder handling, drop policy et recovery sont-ils cohérents ?

## 5.3 Build-3 — Execution Backbone

Canon :

- `docs/specs/V5_3_BUILD3_SPECS_MODULES.md`

Surfaces probables :

- execution backbone
- reconciliation
- expected / simulated / real costs

Questions :

- ACK / fill / timeout / reconciliation sont-ils réellement couverts ?
- la frontière entre exécution simulée et réelle reste-t-elle canonique ?

## 5.4 Build-4 — Risk Backbone

Canon :

- `docs/specs/V5_3_BUILD4_SPECS_MODULES.md`

Questions :

- caps risque contournables ou non
- budget BTC
- budget cluster
- kill switch et halt

## 5.5 Build-5 — Scoring Backbone

Canon :

- `docs/specs/V5_3_BUILD5_SPECS_MODULES.md`

Questions :

- hard vs soft rules bien séparées
- ranking reproductible
- explication des refus et arbitrages

## 5.6 Build-6 — Moteur A

Canon :

- `docs/specs/V5_3_BUILD6_SPECS_MOTEUR_A.md`

Questions :

- identité du moteur A respectée
- fréquence utile plausible
- pas de régression cachée par des heuristiques externes

## 5.7 Build-7 — Moteur B

Canon :

- `docs/specs/V5_3_BUILD7_SPECS_MOTEUR_B.md`

Questions :

- B reste différencié de A
- coût et bruit correctement surveillés
- anti-breakout / filtres conformes au canon

## 5.8 Build-8 — Portfolio Minimal

Canon :

- `docs/specs/V5_3_BUILD8_SPECS_PORTFOLIO_MINIMAL.md`

Questions :

- arbitrage portefeuille réel entre moteurs
- anti-redondance
- conscience cluster / beta / budget

## 5.9 Build-9 — Meta Minimal

Canon :

- `docs/specs/V5_3_BUILD9_SPECS_META_MINIMAL.md`

Questions :

- DTR, CRA, break-even, edge tracker réellement branchés
- métriques utiles vs surfaces purement décoratives

## 5.10 Build-10 — Monitoring + UI Light

Canon :

- `docs/specs/V5_3_BUILD10_SPECS_MONITORING_UI_LIGHT.md`

Questions :

- UI verrouillée
- alerting critique visible
- surfaces Light non contournables
- vocabulaire de statut cohérent

## 5.11 Build-11 — Shadow Light

Canon :

- `docs/specs/V5_3_BUILD11_SPEC_SHADOW_LIGHT.md`

Questions :

- 30 jours consécutifs
- rapport exploitable
- verdicts composants
- A/B/C/D + Build-14 à 100% en Shadow
- cohérence runtime réelle vs doctrine

Note :

- audit déjà entamé
- rester strict sur `30 jours + rapport complet + verdicts`

## 5.12 Build-12 — Micro-live Light

Canon :

- `docs/specs/V5_3_BUILD12_SPEC_MICRO_LIVE_LIGHT.md`

Questions :

- dépendance stricte à Build-11
- 7 jours minimum
- seulement composants `SHADOW_VALIDATED`
- budgets et probes conformes

## 5.13 Build-13 — Live-Light

Canon :

- `docs/specs/V5_3_BUILD13_SPEC_LIVE_LIGHT.md`

Questions :

- Shadow complet validé
- rapport approuvé
- verdicts composants rendus
- Micro-live stable 7 jours
- onboarding / broker / exchange / observability / halt réels

## 5.14 Build-14 — Complete Enablers

Canon :

- `docs/specs/V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md`
- `docs/specs/V5_3_BUILD14_AI_EDGE_AND_MICROSTRUCTURE_ENRICHMENT_ADDENDUM.md`

Questions :

- Build-14 reste-t-il un enabler et non un moteur caché ?
- est-il réellement `SHADOW_ENABLED` en Build-11 ?
- son exposition UI / monitoring / promotion est-elle cohérente ?

---

# 6. Ordre d'exécution concret

Ordre recommandé :

1. Build-1 à Build-5
2. Build-6 à Build-10
3. Build-11
4. Build-12
5. Build-13
6. Build-14
7. consolidation transversale

Pourquoi cet ordre :

- il évite d'auditer les gates de promotion avant d'avoir revalidé le socle
- il permet de détecter tôt les faux positifs dans les couches de base
- il garde Build-11/12/13/14 comme clôture logique du parcours

---

# 7. Méthode de travail par lot

Pour chaque lot de builds :

1. lecture canonique
2. cartographie code
3. cartographie tests
4. exécution de sous-suites ciblées
5. rédaction d'un audit MD
6. mise à jour mémoire JSON
7. seulement ensuite passage au lot suivant

Règle :

- aucun verdict global "tout va bien" avant la fin d'un lot complet

---

# 8. Fichiers d'audit à produire

Fichiers recommandés :

- `docs/audit chatgpt buisness/2026-04-02_BUILD1_TO_BUILD5_AUDIT.md`
- `docs/audit chatgpt buisness/2026-04-02_BUILD6_TO_BUILD10_AUDIT.md`
- `docs/audit chatgpt buisness/2026-04-02_BUILD11_AUDIT.md`
- `docs/audit chatgpt buisness/2026-04-02_BUILD12_AUDIT.md`
- `docs/audit chatgpt buisness/2026-04-02_BUILD13_AUDIT.md`
- `docs/audit chatgpt buisness/2026-04-02_BUILD14_AUDIT.md`
- `docs/audit chatgpt buisness/2026-04-02_BUILD1_TO_BUILD14_CONSOLIDATED_GAPS.md`

---

# 9. Critères de terminé

Le plan sera considéré exécuté quand :

- chaque build `1 -> 14` a un audit explicite
- les statuts inconnus ont disparu
- chaque gap a un owner :
  - doc
  - code
  - test
  - runtime
  - governance
- un ordre de correction prod-safe est prêt

---

# 10. Décision opérationnelle

Décision de reprise :

- oui, on audite bien `Build-1 -> Build-14`
- on le fait par vagues structurées
- on documente après chaque lot
- on ne corrige pas le canon ni le code en masse avant la consolidation
