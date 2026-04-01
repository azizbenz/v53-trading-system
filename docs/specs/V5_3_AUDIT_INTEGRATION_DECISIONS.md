# V5.3 — AUDIT INTEGRATION DECISIONS
## Rapport de triage — Pass documentaire de correction et d'intégration
### Date : 30 mars 2026
### Statut : FREEZE DOCUMENTAIRE ACTIF

---

# 0. Cadre de ce document

Ce document classe **chaque finding issu des trois audits tiers** selon la hiérarchie canonique V5.3.

## 0.1 Sources d'audit

| ID | Source | Nature |
|---|---|---|
| GEM | Audit Gemini (29 mars 2026) | Audit code couche par couche — fondations, data, execution, engines, infra |
| OPUS | Audit Opus critique | Diagnostic "infrastructure solide, cerveau trading insuffisant" |
| QWEN | Audit détaillé angles morts code ↔ production | Persistance, connectivité, sécurité, opérations, risque modèle, performance |

## 0.2 Règle de hiérarchie

Un audit tiers n'est **jamais** une source de vérité active.
Le canon V5.3 (`V5_3_MASTER_FINAL_UNIQUE.md`) reste la seule référence.

Les audits sont de la **matière de correction**, pas de la doctrine.

## 0.2 bis Stabilisation doctrinale finale (1 avril 2026)

Après second pass documentaire :

- `V5_3_MASTER_FINAL_UNIQUE.md` est la **seule source de vérité**
- `V5_3_MASTER_FINAL_CANONICAL.md` n'est plus qu'un **miroir secondaire**
- Build-14 est `SHADOW_ENABLED` en Shadow ; sa promotion live reste conditionnelle au verdict
- les moteurs A/B/C/D sont activés et observés en Shadow ; leur promotion live reste conditionnelle au verdict
- toute table, annexe ou addendum actif est subordonné au master unique

## 0.3 Classifications

| Code | Signification |
|---|---|
| NOW_P0 | Correction immédiate dans le corpus actif |
| NOW_LIGHT | Renforcement documentaire du chemin Light |
| NEXT_BUILD14 | Enabler / SHADOW_ENABLED à 100% / promotion live conditionnelle au verdict |
| RESEARCH_LOCAL | Local replay / recherche / non live |
| REJECT | Hors cadre, redondant ou contradictoire avec le canon |

## 0.4 Distinction critique

- **codé ≠ validé ≠ promu**
- Build-14 codé ≠ Build-14 promu
- Complete enablers ≠ activation Complete
- La logique Light → Shadow → Micro-live → Live-Light → Build-14 → Complete ne doit jamais être bypass

---

# 1. Tableau de triage complet

## 1.1 Findings Gemini — Build-1 / Fondations

| finding_id | résumé angle mort | réalité estimée | impact | classification | fichier_md_cible | action documentaire | impact futur code |
|---|---|---|---|---|---|---|---|
| GEM-01 | Crossed book / carnet croisé non validé dans DepthEvent | **Réel** — SnapshotEvent valide mais DepthEvent non | Spread négatif → coûts fantômes → signaux suicidaires | **NOW_P0** | BUILD1, MASTER | Ajouter invariant crossed book dans contrats Build-1 | Ajouter validation best_ask >= best_bid dans DepthEvent |
| GEM-02 | Epsilon minimum absent sur risk/reward | **Réel** — division par risk ≈ 0 produit ratio gigantesque | Ratio R/R aberrant → filtre scoring berné | **NOW_P0** | BUILD1, MASTER | Ajouter epsilon guard dans invariants decision_contracts | Ajouter if risk < epsilon: return None |
| GEM-03 | DAG validator aveugle aux imports dynamiques (importlib) | **Réel** — import_scanner ne scanne que AST statique | Cycles invisibles, DAG "clean" faussement rassurant | **NOW_P0** | BUILD1, MASTER | Ajouter exigence de détection/signalement importlib | Flagger importlib.import_module comme dépendance wildcard |
| GEM-04 | Recovery synchrone — shutdown() puis bootstrap() immédiat | **Réel** — aucun backoff ni vérification resource release | Socket TIME_WAIT, boucle infinie de redémarrage | **NOW_P0** | BUILD1, MASTER | Ajouter backoff + resource release verification dans smoke_bootstrap_recovery | Implémenter exponential backoff + readiness check |

## 1.2 Findings Gemini — Build-2 / Data Backbone

| finding_id | résumé angle mort | réalité estimée | impact | classification | fichier_md_cible | action documentaire | impact futur code |
|---|---|---|---|---|---|---|---|
| GEM-05 | Buffer drop_newest au lieu de drop_oldest | **Réel** — list bloquante garde les vieux messages | Décisions sur données stale pendant les pics | **NOW_P0** | BUILD2, MASTER | Ajouter policy drop_oldest explicite dans buffer specs | Remplacer list par deque(maxlen=K) |
| GEM-06 | Jitter tolerance absente — TIMESTAMP_REVERSAL trop strict | **Réel** — out-of-order normal sur exchanges distribués | Fausses alertes, coupures injustifiées | **NOW_P0** | BUILD2, MASTER | Ajouter jitter tolerance band (5-10ms) dans contradiction_checker | Implémenter fenêtre de tolérance configurable |
| GEM-08 | Latence monotone — pas de plausibility check | **Réel** — time.time() peut sauter sous NTP/containers | Latences négatives → statistiques corrompues | **NOW_P0** | BUILD2, MASTER | Ajouter plausibility checks sur latence | Filtrer valeurs aberrantes, utiliser monotonic clock |
| GEM-23 | Stale guard explicite côté runtime/prod | **Partiel** — freshness_checker existe mais seuil de péremption runtime absent | Trading sur données périmées pendant lag VPS | **NOW_P0** | BUILD2, BUILD11/12/13 | Ajouter stale guard runtime avec seuil configurable | Implémenter delta check exchange_time vs local_time |

## 1.3 Findings Gemini — Build-3 / Execution Backbone

| finding_id | résumé angle mort | réalité estimée | impact | classification | fichier_md_cible | action documentaire | impact futur code |
|---|---|---|---|---|---|---|---|
| GEM-07 | Market impact ignoré dans ExecutionCostEstimator | **Réel** — slippage seul, pas de modèle d'impact | Surestimation profits sur tailles significatives | **NOW_LIGHT** | BUILD3, MASTER | Ajouter market impact prudent minimal dans cost model | Ajouter composante impact estimée |
| GEM-07b | No-trade si exécution détruit l'edge | **Réel** — pas de filtre coût vs edge net | Trades dont le coût dépasse le gain attendu | **NOW_LIGHT** | BUILD3, BUILD8 | Ajouter condition no-trade explicite | Ajouter filtre break-even dynamique |
| GEM-07c | Réconciliation à source externe | **Partiel** — reconciliation_layer existe mais sans obligation de source externe | État local ≠ état exchange en prod | **NOW_LIGHT** | BUILD3, BUILD12/13 | Clarifier obligation de réconciliation exchange comme trajectoire prod | Implémenter reconciliation exchange |

## 1.4 Findings Gemini — Build-4 / Risk Backbone

| finding_id | résumé angle mort | réalité estimée | impact | classification | fichier_md_cible | action documentaire | impact futur code |
|---|---|---|---|---|---|---|---|
| GEM-09 | Corrélation par paire sans risque factoriel | **Partiel** — correlation_cluster_guard existe mais clusters statiques | 5 actifs corrélés = 10% d'exposition sur un facteur | **NOW_LIGHT** | BUILD4, MASTER | Clarifier limites beta statique, besoin calibration dynamique future | Préparer dynamic calibration |
| GEM-10 | Kill switch en mémoire, non persisté | **Réel** — booléen volatile, reset au redémarrage | Reprise trading après crash majeur sans intervention humaine | **NOW_P0** | BUILD1, BUILD4, MASTER | Ajouter kill switch persistant comme invariant | Implémenter persistence fichier atomique |

## 1.5 Findings Gemini — Engines A/B

| finding_id | résumé angle mort | réalité estimée | impact | classification | fichier_md_cible | action documentaire | impact futur code |
|---|---|---|---|---|---|---|---|
| GEM-11 | Engine A : stop-run / liquidité fantôme sans depth confirmation | **Réel mais scope Build-14** — filtre LOB deep est un enrichissement | Breakouts sur vides de carnet | **NEXT_BUILD14** | BUILD14, ADDENDUM | Absorber comme enabler LOB deep filter | `SHADOW_ENABLED` : activé à 100% en Shadow |
| GEM-12 | Engine B : incapacité trend-shift sans filtre régime | **Partiel** — regime_engine existe canoniquement mais lien B→régime à expliciter | Mean reversion contre tendance forte | **NOW_LIGHT** | BUILD4, TABLE_MOTEURS | Clarifier que régime bloque B en trending fort | Brancher regime_classifier sur gate Engine B |
| GEM-13 | Invalidation fat tails / time-based exit absent | **Partiel** — invalidation calculée à émission, pas de time decay | Positions maintenues trop longtemps sur thèse morte | **NOW_LIGHT** | TABLE_MOTEURS, BUILD8 | Ajouter time-based invalidation comme renforcement | Ajouter timer invalidation configurable |
| GEM-14 | Conflit signaux A↔B / churn | **Réel** — pas de neutralisation explicite inter-engines | Churn : open A + close B = frais sans exposition | **NOW_LIGHT** | BUILD8, MASTER | Ajouter anti-churn A/B et neutralisation signaux contradictoires | Implémenter règle neutralisation fenêtre temporelle |

## 1.6 Findings Gemini — Infrastructure / Monitoring

| finding_id | résumé angle mort | réalité estimée | impact | classification | fichier_md_cible | action documentaire | impact futur code |
|---|---|---|---|---|---|---|---|
| GEM-16 | Imports dynamiques : runtime error en boucle | **Réel** — même finding que GEM-03, impact infra | Boucle redémarrage infinie sur module corrompu | **NOW_P0** | BUILD1 | Déjà couvert par GEM-03 + GEM-04 | Validation statique pré-import |
| GEM-17 | Recovery sans exponential backoff | **Réel** — même finding que GEM-04 | IP bannie par exchange, CPU saturé | **NOW_P0** | BUILD1 | Déjà couvert par GEM-04 | Exponential backoff |
| GEM-18 | Dashboard snapshots sans high-water marks ni drop rate | **Réel** — compteurs instantanés seulement | Illusion de santé, congestion invisible | **NOW_LIGHT** | BUILD10, MASTER | Ajouter high-water marks, drop rate, stale spikes dans dashboards | Implémenter métriques de saturation |
| GEM-19 | Persistance atomique absente | **Réel** — shutdown brutal = fichier état tronqué | Bootstrap échoue sur fichier corrompu | **NOW_P0** | BUILD1, MASTER | Ajouter persistance atomique (write-tmp-then-rename) comme invariant | Implémenter atomic write pattern |
| GEM-20 | Fuite FD dans smoke tests | **Partiel** — pas de test de fuite FD explicite | EMFILE après 48h de trading intense | **NOW_LIGHT** | BUILD1 | Ajouter smoke test fuite FD / relance dans specs | Ajouter test fermeture descripteurs |

## 1.7 Findings Gemini — Propositions de nouveaux modules

| finding_id | résumé angle mort | réalité estimée | impact | classification | fichier_md_cible | action documentaire | impact futur code |
|---|---|---|---|---|---|---|---|
| GEM-21 | LOB Deep-Filter / VWA (anti-spoofing) | **Pertinent mais Build-14** — enrichissement microstructure | Filtrage spoofing cognitif | **NEXT_BUILD14** | BUILD14, ADDENDUM | Absorber comme enabler anti-spoofing | `SHADOW_ENABLED` : activé à 100% en Shadow, promotion par verdict |
| GEM-22 | Hurst Regime Classifier | **Pertinent mais Build-14** — enrichissement régime | Classification trending/reverting/ranging plus fine | **NEXT_BUILD14** | BUILD14, ADDENDUM | Absorber comme enabler régime enrichi | `SHADOW_ENABLED` : activé à 100% en Shadow, promotion par verdict |
| GEM-24 | OBI (Order Book Imbalance) pression adverse | **Pertinent mais Build-14** — enrichissement microstructure | Détection pression adverse, ajustement sizing | **NEXT_BUILD14** | BUILD14, ADDENDUM | Absorber comme enabler OBI | `SHADOW_ENABLED` : activé à 100% en Shadow, promotion par verdict |
| GEM-25 | Predictive Shadow / What-if Engine | **Intéressant mais recherche** — inférence asymétrique | Anticipation stop-hunting | **RESEARCH_LOCAL** | LOCAL_VPS_PLAN | Classer explicitement hors chemin live initial | Expérimentation locale uniquement |

## 1.8 Findings Gemini — Simulation / Backtest

| finding_id | résumé angle mort | réalité estimée | impact | classification | fichier_md_cible | action documentaire | impact futur code |
|---|---|---|---|---|---|---|---|
| GEM-15 | Biais de survie dans replay — market impact ignoré | **Réel** — fills 100% au prix du tick, irréaliste | Backtests structurellement trop optimistes | **RESEARCH_LOCAL** | LOCAL_VPS_PLAN | Ajouter avertissement market impact dans replay | Implémenter fill model réaliste en replay |

## 1.9 Findings QWEN — Persistance & État

| finding_id | résumé angle mort | réalité estimée | impact | classification | fichier_md_cible | action documentaire | impact futur code |
|---|---|---|---|---|---|---|---|
| QWEN-01 | Stores DTR/Meta en mémoire volatile | **Réel** — list[] en mémoire, perte au redémarrage | Perte historique décisions, apprentissages, réconciliation | **NOW_P0** | BUILD1, BUILD9, MASTER | Ajouter persistance minimale de sécurité comme invariant | Implémenter flush périodique fichier |
| QWEN-02 | Gestion secrets non couverte | **Hors cadre V5.3 trading** — infra déploiement | Important mais pas dans le scope documentaire trading | **REJECT** | — | Hors scope canon trading V5.3 | Infrastructure ops séparé |

## 1.10 Findings QWEN — Connectivité & Exécution

| finding_id | résumé angle mort | réalité estimée | impact | classification | fichier_md_cible | action documentaire | impact futur code |
|---|---|---|---|---|---|---|---|
| QWEN-03 | Absence connecteurs exchange réels | **Partiel** — contrats et machines d'état existent, pas d'I/O réseau réel | Système décide mais n'envoie pas réellement | **NOW_LIGHT** | BUILD11/12/13, MASTER | Clarifier préconditions runtime réel pour shadow/micro-live/live | Implémenter adapters exchange réels |
| QWEN-04 | Tests mockés vs charge réelle | **Partiel** — inévitable à ce stade, mais gap à expliciter | Comportement différent sous charge réelle | **NOW_LIGHT** | BUILD11/12/13 | Clarifier que shadow ≠ validable sur modèles in-memory seuls | Tests de charge en trajectoire |

## 1.11 Findings QWEN — Sécurité & Opérations

| finding_id | résumé angle mort | réalité estimée | impact | classification | fichier_md_cible | action documentaire | impact futur code |
|---|---|---|---|---|---|---|---|
| QWEN-05 | UI non sécurisée (pas auth, pas HTTPS) | **Hors cadre** — dashboard local, pas exposé réseau | Risque seulement si exposé | **REJECT** | — | Hors scope canon trading V5.3 | Note infra si exposition réseau |
| QWEN-06 | Module de notification absent | **Réel** — alertes générées mais pas livrées | Alertes CRITICAL invisibles pour l'humain | **NOW_LIGHT** | BUILD10, BUILD13 | Ajouter obligation de canal de notification opérateur | Implémenter webhook/notification |
| QWEN-07 | Kill switch externe absent | **Réel** — couvert partiellement par GEM-10 | Pas de bouton rouge hors processus Python | **NOW_P0** | BUILD1, BUILD4 | Déjà couvert par GEM-10 (persistance) + ajouter kill switch externe | Kill switch fichier flag ou API admin |
| QWEN-08 | Workflow approval non codé | **Partiel** — ReviewState.PENDING existe, pas de processus | Approbation manuelle non instrumentée | **NOW_LIGHT** | BUILD13 | Clarifier processus d'approbation en trajectoire live | Interface approval minimale |

## 1.12 Findings QWEN — Risque Modèle & Performance

| finding_id | résumé angle mort | réalité estimée | impact | classification | fichier_md_cible | action documentaire | impact futur code |
|---|---|---|---|---|---|---|---|
| QWEN-09 | Corrélations statiques (clusters en dur) | **Partiel** — même diagnostic que GEM-09 | Diversification échoue exactement quand nécessaire | **NOW_LIGHT** | BUILD4 | Déjà couvert par GEM-09 | Dynamic calibration future |
| QWEN-10 | Risque liquidité — depth non utilisé pour sizing | **Réel** — DepthEvent ingéré mais pas dans sizing | Slippage massif sur ordres "autorisés" | **NOW_LIGHT** | BUILD3, BUILD8 | Ajouter consultation depth dans trajectoire sizing | Intégrer depth dans size adjustment |
| QWEN-11 | Engines C/D absents → pas de fallback | **Faux-cadre** — C/D sont planifiés, activation gouvernée | Risque si A+B inefficaces dans choppy volatile | **REJECT** | — | Canon V5.3 prévoit C/D en activation gouvernée | Suivre plan canonique |
| QWEN-12 | GIL Python / performance synchrone | **Exagéré** — le système est basse fréquence par design | Impact limité sauf pic extrême | **RESEARCH_LOCAL** | — | Pas de patch documentaire nécessaire | Load testing éventuel |
| QWEN-13 | Synchronisation horloge NTP | **Réel** — couvert partiellement par GEM-08 | Calculs latence faux si horloge dérivée | **NOW_P0** | BUILD2 | Déjà couvert par GEM-08 | Monotonic clock + NTP awareness |

---

# 2. Synthèse par classification

## 2.1 NOW_P0 — Corrections immédiates (12 findings)

| ID | Résumé court |
|---|---|
| GEM-01 | Crossed book validation |
| GEM-02 | Epsilon minimum risk/reward |
| GEM-03 | Detection imports dynamiques DAG |
| GEM-04 | Recovery backoff + resource release |
| GEM-05 | Buffer drop_oldest policy |
| GEM-06 | Jitter tolerance band |
| GEM-08 | Latence monotone / plausibility |
| GEM-10 | Kill switch persistant |
| GEM-19 | Persistance atomique minimale |
| GEM-23 | Stale guard runtime explicite |
| QWEN-01 | Persistance minimale stores critiques |
| QWEN-07 | Kill switch externe |

## 2.2 NOW_LIGHT — Renforcements Light (16 findings)

| ID | Résumé court |
|---|---|
| GEM-07 | Market impact prudent minimal |
| GEM-07b | No-trade si coût détruit edge |
| GEM-07c | Réconciliation source externe |
| GEM-09 | Limites beta statique / calibration dynamique |
| GEM-12 | Régime bloque Engine B en trending |
| GEM-13 | Time-based invalidation |
| GEM-14 | Anti-churn A/B / neutralisation |
| GEM-18 | Dashboards high-water / drop rate |
| GEM-20 | Smoke test fuite FD |
| QWEN-03 | Préconditions runtime réel shadow/micro-live |
| QWEN-04 | Shadow ≠ validable in-memory seul |
| QWEN-06 | Canal notification opérateur |
| QWEN-08 | Workflow approval trajectoire live |
| QWEN-10 | Depth dans trajectoire sizing |

## 2.3 NEXT_BUILD14 — Enablers non-promus (4 findings)

| ID | Résumé court |
|---|---|
| GEM-11 | LOB deep filter / anti-spoofing |
| GEM-21 | VWA anti-spoofing |
| GEM-22 | Hurst regime classifier enrichi |
| GEM-24 | OBI pression adverse |

## 2.4 RESEARCH_LOCAL — Recherche locale seulement (3 findings)

| ID | Résumé court |
|---|---|
| GEM-15 | Biais market impact en replay |
| GEM-25 | Predictive shadow / what-if engine |
| QWEN-12 | GIL / load testing |

## 2.5 REJECT — Hors cadre (4 findings)

| ID | Résumé court | Raison |
|---|---|---|
| QWEN-02 | Gestion secrets | Infrastructure ops, hors scope trading |
| QWEN-05 | UI sécurisée | Dashboard local, pas exposé réseau |
| QWEN-11 | Engines C/D absents | Canon V5.3 les prévoit en activation gouvernée |
| — | Propositions V5.4/V6.0 de Gemini | Hors cadre V5.3, ne pas créer d'architecture concurrente |

---

# 3. Règles de gouvernance issues de ce triage

## 3.1 Un audit tiers n'est jamais une source de vérité active

Les audits sont classés, absorbés, et patchés dans le canon.
Ils ne remplacent pas le canon.

## 3.2 Hard State documentaire — Cycle de vie officiel

| Hard State | Signification |
|---|---|
| `CODED` | Le code existe dans le dépôt |
| `DOCUMENTED` | La spécification canonique est écrite et cohérente |
| `SHADOW_ENABLED` | Activé à 100% en mode SHADOW, pleinement utilisé et observé |
| `SHADOW_VALIDATED` | Les 30 jours de Shadow sont terminés avec verdict positif |
| `PROMOTED` | Activé en production dans le profil autorisé |
| `DORMANT` | Codé et documenté mais volontairement non activé |
| `FORBIDDEN` | Interdit en V5.3 prod |

Un build `CODED` n'est PAS un build `SHADOW_VALIDATED`.
Un build `SHADOW_VALIDATED` n'est PAS un build `PROMOTED`.
`SHADOW_ENABLED` = activé à 100% en Shadow, pas en lecture seule.

## 3.3 Build-14 — Activation Shadow et promotion

Build-14 est :
- **activé à 100% en Shadow** (`SHADOW_ENABLED`) : pleinement utilisé dans les décisions Shadow, tracé, comparé, auditable
- soumis au **verdict post-Shadow** : chaque enabler reçoit `SHADOW_VALIDATED` ou `DORMANT`
- promotion live non automatique : conditionnelle au verdict
- jamais un hard blocker central en live sans verdict
- jamais une activation implicite de Complete

## 3.4 Pipeline de promotion canonique

```
[TOUT CODÉ] → Shadow 30j (A/B/C/D + Build-14 à 100%) → Verdict → Micro-live → Live-Light → Complete Shadow 30j → Complete Live
```

Activation en Shadow ≠ promotion Live. Aucun raccourci autorisé.

---

# 4. Fichiers MD impactés

| Fichier | Actions |
|---|---|
| V5_3_MASTER_FINAL_UNIQUE.md | Section audit integration + guardrails P0 |
| V5_3_MASTER_FINAL_CANONICAL.md | Idem (miroir secondaire, non source autonome) |
| V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md | Phase "Audit Integration Pass" |
| V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md | Gates P0 renforcées |
| V5_3_BUILD1_SPECS_MODULES.md | Invariants P0 renforcés |
| V5_3_BUILD2_SPECS_MODULES.md | Buffer, jitter, stale, latence |
| V5_3_BUILD3_SPECS_MODULES.md | Cost model, reconciliation, no-trade |
| V5_3_BUILD4_SPECS_MODULES.md | Beta statique, drawdown, dynamic calibration |
| V5_3_BUILD8_SPECS_PORTFOLIO_MINIMAL.md | Anti-churn, conflit opportunités, no-trade |
| V5_3_BUILD9_SPECS_META_MINIMAL.md | DTR alimenté par vrais chemins, anti auto-référence |
| V5_3_BUILD10_SPECS_MONITORING_UI_LIGHT.md | High-water marks, drop rate, stale, alerts |
| V5_3_BUILD11_SPEC_SHADOW_LIGHT.md | Préconditions runtime réel |
| V5_3_BUILD12_SPEC_MICRO_LIVE_LIGHT.md | I/O réel, event loop, reconciliation |
| V5_3_BUILD13_SPEC_LIVE_LIGHT.md | Config loading, sortie positions, notification |
| V5_3_BUILD14_SPEC_COMPLETE_ENABLERS.md | Enablers absorbés, statut forcé |
| V5_3_BUILD14_AI_EDGE_AND_MICROSTRUCTURE_ENRICHMENT_ADDENDUM.md | Enablers audits absorbés |
| V5_3_UNIFIED_LOCAL_VPS_BACKTEST_ARCHITECTURE_PLAN_V2.md | Feature bridge, parity diagnostics |
| V5_3_TABLE_DETAILLEE_MOTEURS.md | Régime gate Engine B, time invalidation |

---

# 5. HARD STATEMENT — Pipeline de promotion temporel

> **NON NÉGOCIABLE. Aucune dérogation, aucun raccourci, aucune exception.**

## 5.1 Principe

Toute la solution V5.3 (Light + Complete, Builds 1→17) est **codée intégralement**.
Le code existant ne donne **aucun droit de promotion automatique**.

## 5.2 Pipeline hard

```
[TOUT CODÉ] → Light Shadow 30j → Light Live → Complete Shadow 30j → Complete Live
```

| Étape | Durée minimum | Condition d'interruption |
|---|---|---|
| Light Shadow | 30 jours calendaires consécutifs | Interruption > 24h = compteur à zéro |
| Micro-live | 7 jours minimum | — |
| Light Live | Stable avant passage Complete | — |
| Complete Shadow | 30 jours calendaires consécutifs | Dégradation Light = désactivation + compteur à zéro |
| Complete Live | Après rapport comparatif approuvé | — |

## 5.3 Ce que le code doit implémenter

- Compteur de jours shadow persisté (fichier, pas mémoire)
- Détection d'interruption > 24h avec reset automatique
- Blocage de promotion si compteur < 30
- Rapport shadow automatique
- Rapport comparatif Light vs Complete automatique
- Non-régression Light monitored pendant shadow Complete

---

## Fin du rapport de triage
