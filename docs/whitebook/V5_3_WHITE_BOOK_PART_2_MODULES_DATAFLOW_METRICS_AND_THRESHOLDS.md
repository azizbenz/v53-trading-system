# V5.3 WHITE BOOK - PARTIE 2
## Modules, flux de données, métriques, seuils, forces, faiblesses et angles morts

---

# 0. Comment lire cette partie

Cette partie couvre tous les modules canoniques de la branche.

Pour chaque module, l’objectif est de répondre à :

- ce qu’il fait
- ce qu’il consomme
- ce qu’il produit
- quelles métriques et quelles équations comptent
- quels seuils sont explicites
- pourquoi le module existe
- ce qu’il fait bien
- où il peut échouer

Règle importante :

- quand un seuil est dur et explicite dans le code ou la spec, il est écrit comme seuil
- quand un seuil est configurable selon la stratégie ou l’environnement, il est décrit comme tel

---

# 1. Build-1 - fondation architecture et contrats

| Module | Rôle | Inputs -> Outputs | Métriques / équations coeur | Seuils / gates | Pourquoi il existe | Forces | Faiblesses / angles morts | État branche |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `interface_contracts` | langage commun du système | valeurs métier typées -> contrats partagés | cohérence des types, stabilité des enums, vocabulaire paire/profil/runtime | empêche la dérive de profils au-delà de `LIGHT` et `COMPLETE` | éviter la fragmentation sémantique | langage canonique fort | peut retarder si docs et code divergent sans refreeze | `ALIGNED` |
| `manifest_registry` | inventaire unique des modules et profils | métadonnées modules -> table canonique | mapping build-stage, profile scope, ownership | aucun module caché ne devrait exister hors manifest | garder le système lisible et auditable | très fort anti-sprawl | peut devenir obsolète si des contributeurs le contournent | `ALIGNED` |
| `dag_validator` | hygiène des dépendances | graphe d’import -> rapport de validation | nombre de cycles, imports non autorisés | pas de cycles, pas de dépendances cross-layer interdites | empêcher la dette structurelle | détecte tôt la dérive architecturale | ne juge pas la logique métier | `ALIGNED` |
| `contract_test_suite` | vérification contractuelle | modèles typés et interfaces -> pass/fail | couverture schéma, couverture cas négatifs | obligatoire au merge | empêcher la casse silencieuse des schémas | très fort levier sur le shared core | ne prouve pas l’économie runtime | `ALIGNED` |
| `smoke_bootstrap_recovery` | preuve de démarrage et recovery | scénarios start/restart -> smoke evidence | succès bootstrap, succès recovery | le bootstrap doit rester green | garantir démarrage et reprise | critique opérationnellement | ne remplace pas la preuve longue durée | `ALIGNED` |

---

# 2. Build-2 - data backbone

## 2.1 Rôle canonique

Le data backbone est la première couche de vérité réelle.

Il doit répondre à :

- le flux exchange est-il connecté
- le flux d’événements est-il cohérent
- la donnée est-elle assez fraîche
- une paire peut-elle se dégrader sans contaminer les autres

## 2.2 Équations et métriques clés

Les docs et le code rendent explicites plusieurs métriques Build-2 :

- intensité totale entrante :
  - `lambda_tot = sum_j sum_f lambda_j,f`
- utilisation du service :
  - `rho = lambda / mu`
- évolution de file :
  - `B(t+1) = B(t) + A(t) - S(t)`
- latence événement :
  - `Lat_u = t_recv,u - t_exch,u`
- drift :
  - `Drift_u = t_local - t_reference`
- âge de la donnée au moment de la décision :
  - `Delta_i = t_decision - t_last_update`

## 2.3 Seuils explicites déjà visibles

- tolérance jitter réseau : `5-10ms` avant escalade contradiction timestamp
- stale guard exchange par défaut : `0.2s` (`200ms`)
- stale soft threshold général dans le code : `5s`
- stale hard threshold général dans le code : `30s`
- maximum de latence accepté dans le code : `60s` avant rejet comme valeur aberrante
- politique buffer : `drop_oldest`, jamais `drop_newest`

## 2.4 Ligne module

| Module | Rôle | Inputs -> Outputs | Métriques / seuils | Pourquoi il existe | Forces | Faiblesses / angles morts | État branche |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `data_backbone` | ingestion exchange et intégrité data | websocket / bootstrap REST -> événements typés normalisés et faits de santé paire | backlog, stale rate, latence, drift, gap rate, utilisation queues | aucune décision de trading n’est fiable sans intégrité data | dégradation par paire et logique de fraîcheur explicite très solides | fortement dépendant de la connectivité exchange et de la qualité des timestamps | `ALIGNED` |

Sous-composants à retenir :

- `websocket_gateway`
- `rest_bootstrap`
- `event_normalizer`
- `internal_router`
- `freshness_checker`
- `consistency_checker`
- `pair_health_scorer`

Point fort :

- Build-2 n’est pas seulement une couche “collecte data” ; c’est déjà une surface de risque.

Angle mort :

- si le volume de messages augmente fortement avec plus de paires et plus de streams, le backlog peut devenir l’ennemi caché avant même que la qualité d’alpha ne soit en cause

---

# 3. Build-3 - execution backbone

| Module | Rôle | Inputs -> Outputs | Métriques coeur | Seuils / gates | Pourquoi il existe | Forces | Faiblesses / angles morts | État branche |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `execution_backbone` | traduire une intention approuvée en vérité d’ordre réelle | candidat approuvé portefeuille -> ACK, fills, réconciliation, faits de coût | first-fill latency, full-fill latency, coût réalisé, slippage, partial-fill ratio, divergence de réconciliation | la divergence compte / état local est un mode d’échec dur | ancrer le système dans l’exécution réelle | la réconciliation explicite est un gros point fort fintech | l’edge exchange réel peut se dégrader avant que les modèles coût/latence ne le reflètent | `ALIGNED` |

Pourquoi c’est important :

- beaucoup de stacks quant optimisent l’edge pré-trade et négligent la vérité post-trade
- V5.3 essaie de recoller ces deux mondes

Négatif probable :

- une stack spot-only peut quand même sous-estimer la friction d’exécution sur les paires moins liquides hors BTC/ETH

---

# 4. Build-4 - risk backbone

## 4.1 Équations principales

Les docs rendent explicites les équations suivantes :

- budget perte agrégé :
  - `LossBudget = sum_i L_i`
- cap budget :
  - `LossBudget <= LB_max`
- budget projeté :
  - `LossBudget + L_new <= LB_max`
- utilisation budget :
  - `LossUtil = LossBudget / LB_max`
- exposition cluster :
  - `ClusterExp_c = sum_{i in cluster c} x_i`
- cap cluster :
  - `ClusterExp_c <= X_cluster,c^max`
- logique facteur BTC :
  - `Beta_port = sum_j w_j beta_j`

## 4.2 Ligne module

| Module | Rôle | Inputs -> Outputs | Métriques / seuils | Pourquoi il existe | Forces | Faiblesses / angles morts | État branche |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `risk_backbone` | empêcher la concentration cachée et l’hémorragie de capital | candidats + état paire + état portefeuille -> approvals/refus durs et faits de budget | budget perte, beta BTC, pression cluster, drawdown, caps par paire, éligibilité tier | aucun candidat live ne doit bypasser la logique budget | architecture anti-concentration robuste | les proxys statiques peuvent sous-réagir en changement de régime | `STILL_PARTIAL` opérationnellement à cause du gap de preuve sandbox, pas à cause d’un défaut logique prouvé |

Sous-composants mis en avant :

- `exposure_budgeter`
- `loss_budgeter`
- `btc_factor_guard`
- `correlation_cluster_guard`

Lecture pratique importante :

- ce n’est pas un modèle de risque dynamique complet
- c’est un moteur de budget gouverné
- c’est à la fois une force et une limite

Angle mort :

- beta statique et clusters statiques peuvent réagir trop lentement lors d’explosions de corrélation en crise

---

# 5. Build-5 - scoring backbone

| Module | Rôle | Inputs -> Outputs | Métriques / équations | Seuils / gates | Pourquoi il existe | Forces | Faiblesses / angles morts | État branche |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `scoring_backbone` | séparer hard blockers, soft penalties et ranking | candidats moteurs bruts + faits risque/data -> candidats classables et explicables | hard-block count, budget soft penalties, rang de score, contribution CE | aucune règle soft ne doit se comporter comme un hard kill déguisé | éviter la soupe heuristique tout-ou-rien | excellent pour l’explicabilité et le replay | peut quand même sur-stériliser si trop de soft penalties s’accumulent | `ALIGNED` |

Pourquoi il existe :

- un bon système a besoin à la fois de refus et de priorisation
- V5.3 traite ces deux opérations séparément

Angle mort :

- trop de pénalités soft peuvent imiter un hard refusal tout en gardant une apparence “mathématique”

---

# 6. Build-6 et Build-7 - noyau moteurs

| Module | Rôle | Inputs -> Outputs | Métriques | Seuils / gates | Pourquoi il existe | Forces | Faiblesses / angles morts | État branche |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `engine_a` | premium trend / expansion | structure, régime, coût, liquidité -> candidat haute conviction | CE attendue, faisabilité coût, score contexte, éligibilité tier | gate coût la plus exigeante des moteurs | garder les setups premium vivants | identité économique claire | peut devenir trop rare, trop pur et économiquement stérile | `ALIGNED` |
| `engine_b` | mean reversion intraday | faits de dislocation locale -> candidat plus fréquent | CE attendue, proba de reversion, compatibilité contexte/risque | ne doit pas trader contre une vraie cassure structurelle | ajoute de la fréquence utile | meilleure cadence de trade | vulnérable aux continuations de tendance | `ALIGNED` |

Les détails moteurs approfondis sont en partie 3.

---

# 7. Build-8 portfolio et Build-9 meta

| Module | Rôle | Inputs -> Outputs | Métriques coeur | Seuils / gates | Pourquoi il existe | Forces | Faiblesses / angles morts | État branche |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `portfolio` | arbitrer les opportunités simultanées | candidats classables + budgets -> allocation sélectionnée | ranking CE, budget perte restant, saturation cluster, concentration paire | doit refuser une sélection purement score brut | transformer un set de stratégies en portefeuille | empêche les empilements mono-factoriels | dépend fortement de la comparabilité des signaux amont | `ALIGNED` |
| `meta` | vérité post-trade et substrat de learning | faits de trade exécuté ou shadowé -> DTR, CRA, break-even, statut d’edge | break-even drift, CRA sterilization rate, phantom trade detection, degraded edge count | la perte de DTR est opérationnellement critique | crée de la responsabilité causale | excellent substrat d’audit | peut devenir descriptif sans levier correctif si Build-9X est faible | `ALIGNED` |

Pourquoi `meta` est central :

- sans DTR et sans vérité break-even, le système peut facilement confondre bruit et alpha

---

# 8. Build-9X - learning gouverné

## 8.1 Rôle

Build-9X est l’extension de learning gouverné.

Ce n’est pas un optimiseur live.  
C’est une couche de diagnostic et de préparation au replay.

## 8.2 Merge gates explicites désormais présents

- `NO_LIVE_MUTATION_PATH`
- `END_TO_END_ID_CORRELATION`
- `STRUCTURED_LEARNING_LOGS_PRESENT`
- `LEARNING_BACKPRESSURE_HANDLED`
- `RESOURCE_BUDGETS_RESPECTED`
- `STATISTICAL_GOVERNANCE_PRESENT`

## 8.3 Seuils de capacité codés

Le capacity guard expose deux seuils explicites :

- seuil d’alerte backlog : `1000`
- seuil de protection backlog : `5000`

Au-dessus du seuil de protection :

- le capture mode se dégrade vers la capture minimale
- la review et la promotion sont bloquées pour cause de données incomplètes

## 8.4 Ligne module

| Module | Rôle | Inputs -> Outputs | Métriques / seuils | Pourquoi il existe | Forces | Faiblesses / angles morts | État branche |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `meta_learning` | learning post-trade gouverné | diagnostics, hypothèses, replay bundles, review exports | queue depth, queue age, worker CPU, worker RSS, write latency, export failures, log loss, merge-gate pass/fail | alerte à `1000`, protection à `5000`, interdiction de live mutation path | garde le learning discipliné et auditable | la gouvernance explicite est un très gros point fort | la qualité review/orchestration peut encore être en retard sur l’ambition de recherche | `ALIGNED` |

Angle mort :

- les systèmes de learning échouent souvent en prétendant que les “propositions” sont sans danger ; V5.3 est meilleure que la moyenne ici, mais seulement si les merge gates restent réellement enforce de bout en bout

---

# 9. Build-10 - monitoring et UI

| Module | Rôle | Inputs -> Outputs | Métriques | Seuils / gates | Pourquoi il existe | Forces | Faiblesses / angles morts | État branche |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `monitoring` | visibilité opérationnelle | snapshots runtime + artefacts -> alertes, projections, export observability | backlog, stale rate, drawdown, kill-switch status, edge degradation, halt readiness | pas de dashboard sans métriques critiques | rend le système inspectable | forte discipline d’alerte | des métriques placeholder peuvent créer un faux confort si elles ne sont pas honnêtement branchées | `ALIGNED`, mais certaines cartes demandent encore une vraie hydration live |
| `ui` | control plane opérateur | payloads monitoring + actions opérateur -> dashboards locaux et actions de safing | visibilité d’état, downgrade path, statut account/user-data, live market lab | l’UI ne doit jamais bypasser profils ou gates | permet une supervision humaine explicite | les outils HTML locaux sont pratiques et auditables | des surfaces hybrides demo/live peuvent embrouiller si elles ne sont pas bien étiquetées | `ALIGNED` |

Note pratique :

- les travaux récents ont amélioré le branchement live marché et le user-data account
- mais certaines cartes de supervision restent encore projection-driven plutôt que reliées à une vraie télémétrie process

---

# 10. Replay, import, protocoles et contrôle runtime

| Module | Rôle | Inputs -> Outputs | Métriques / seuils | Pourquoi il existe | Forces | Faiblesses / angles morts | État branche |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `local_replay_runtime` | replay gouverné de la même V5.3 | artefacts versionnés -> replay evidence | replay CE, replay metrics, drawdown proxy, parity diagnostics | aucun fork de profil autorisé | rend le learning testable sur le même coeur | fort principe anti-fork | il reste plus facile de surcroire au replay qu’à la preuve live | `ACTIVE` mais ne remplace pas la fermeture runtime |
| `backtest_artifact_import` | gouvernance d’import entre local et VPS | artefacts replay -> requête import / validation | artifact versioning, source_version, bypass attempts | le bypass des runtime gates est interdit | protège l’intégrité topologique | anti-sprawl et anti-plugin chaos | la gouvernance d’import ne prouve pas à elle seule la qualité stratégie | `ACTIVE` |
| `protocols` | orchestration des builds runtime | entrées runtime -> résumés, gates et rapports Shadow/Micro-live/Live | compteur 30 jours, halt readiness, report readiness, gates de phase | Build-11 a besoin de `30/30`, Build-13 a besoin de Build-12 stable | transforme la doctrine en états opérables | crucial pour un rollout honnête | peut paraître complet avant que la preuve temps réel existe | `ACTIVE`, mais la fermeture aval reste mixte |

---

# 11. Build-14 - complete enablers

## 11.1 Logique générale

Build-14 n’est pas une nouvelle famille de moteurs.  
C’est une couche d’enrichissement.

Ses contraintes contractuelles dures sont :

- ne peut pas override les moteurs
- ne peut pas bypass le risque
- ne peut pas bypass le portefeuille
- ne peut pas trader de façon autonome

## 11.2 Inputs d’observation déjà modélisés

`Build14ObservationInput` contient :

- DTR coverage
- CRA sterilization rate
- CRA alert count
- break-even drift alert
- degraded edge count
- queue backlog
- stale pair count
- DTR loss count
- log loss count
- net CE
- breakout failure rate
- volume support ratio
- VWA absorption ratio
- ghost liquidity ratio
- adverse OBI pressure
- Hurst exponent
- competition density

## 11.3 Ligne module

| Module | Rôle | Inputs -> Outputs | Métriques / seuils | Pourquoi il existe | Forces | Faiblesses / angles morts | État branche |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `complete_enablers` | readers bornés post-core | faits existants du système -> snapshots Build-14 et influence report | reader scores, severity bands, confidence penalties, recommended budget factors | jamais autonome, jamais en bypass | apporte du contexte plus riche sans remplacer les moteurs core | compromis élégant entre enrichissement utile et gouvernance | zone facile de dérive vers l’inflation de features si la discipline baisse | `ALIGNED` |

Les formules reader-level sont détaillées en partie 3.

---

# 12. Build-15 et Build-16 - moteurs d’extension

| Module | Rôle | Inputs -> Outputs | Métriques / seuils | Pourquoi il existe | Forces | Faiblesses / angles morts | État branche |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `engine_c` | breakout continuation | contexte breakout + continuation -> candidat C gouverné | `CE_C`, Sharpe par trade, drawdown C, contradiction microstructure, breaches loss/beta/cluster | stale hard, loss-budget breach, beta breach, cluster breach | ajoute de l’expansion et de la diversification au-delà de A/B | utile si son edge est vraiment distinct de A | peut dupliquer A avec plus de bruit | `STILL_PARTIAL` |
| `engine_d` | re-entry / second chance | post-break / pullback / continuation partielle -> candidat D gouverné | `CE_D`, contribution marginale, coût de concentration, drawdown D | stale hard, loss-budget breach, beta breach, cluster breach | monétise des opportunités de seconde entrée | peut apporter une diversification non triviale | peut devenir une duplication déguisée de A ou surconcentrer les thèmes | `STILL_PARTIAL` |

Les équations et angles morts profonds sont en partie 3.

---

# 13. Build-17 - surface live Complete

| Module | Rôle | Inputs -> Outputs | Métriques / seuils | Pourquoi il existe | Forces | Faiblesses / angles morts | État branche |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Build-17 runtime/UI scope` | surface supervisée du rollout Complete | runtime complete + A/B/C/D + contributions Build-14 -> supervision opérateur complete | portfolio CE, beta, cluster, drawdown par moteur, backlog, stale, contribution Build-14 | exige 1-13 plus 15 et 16 validés honnêtement | nécessaire pour une vraie supervision Complete | crée un control plane final cohérent | encore incomplet sur cette branche | `PARTIAL_SURFACE_ONLY` |

---

# 14. Conclusion de la partie 2

Le paysage modulaire de V5.3 est inhabituellement mature pour une architecture de trading retail à petit/moyen capital.

Ses meilleures qualités au niveau modules sont :

- contrats explicites
- étapes de rollout explicites
- logique explicite de santé infra et de qualité data
- gouvernance explicite du learning

Ses principaux dangers au niveau modules sont :

- complexité opérationnelle
- télémétrie placeholder qui peut se faire passer pour de la vérité runtime
- inflation fonctionnelle de Build-14
- retard de fermeture sur Build-11 / 15 / 16 / 17

Le point positif est que ces dangers sont visibles, pas cachés.

