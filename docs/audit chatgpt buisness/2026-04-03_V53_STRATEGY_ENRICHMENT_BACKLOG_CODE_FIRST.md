# 2026-04-03 - V5.3 strategy enrichment backlog code-first

## Objet

Ce document transforme les audits code-first en **backlog exécutable**.

Références de départ:
- [V53_CODE_FIRST_MODULE_COMPONENT_AUDIT.md](E:/claude%20%20v5.3/v53_trading_system/docs/audit%20chatgpt%20buisness/2026-04-03_V53_CODE_FIRST_MODULE_COMPONENT_AUDIT.md)
- [V53_CODE_FIRST_STRATEGY_ENRICHMENT_AUDIT.md](E:/claude%20%20v5.3/v53_trading_system/docs/audit%20chatgpt%20buisness/2026-04-03_V53_CODE_FIRST_STRATEGY_ENRICHMENT_AUDIT.md)

But:
- rendre l’enrichissement de V5.3 **pilotable**
- éviter le travail diffus “on améliore un peu partout”
- ne sauter aucun composant réel du code
- garder la preuve replay/shadow au centre

## Principes de gouvernance

1. aucun lot ne doit contourner `risk_backbone`, `scoring_backbone` ou `protocols`
2. aucun lot ne doit créer un moteur hors `A/B/C/D`
3. Build-14 reste une couche d’enrichissement gouvernée, pas un moteur autonome
4. toute nouvelle intelligence doit être:
   - observable
   - replayable
   - shadow-trackable
5. toute logique qui influence la sélection doit être racontable dans:
   - `meta_learning`
   - `monitoring`
   - `protocols`
6. tant que `Build-11` n’a pas fini sa vraie campagne 30 jours, on évite de rouvrir inutilement `Build-12/13`

## Vue d’ensemble

| Lot | Cible principale | Familles concernées | Objectif |
| --- | --- | --- | --- |
| 0 | instrumentation et preuve | `meta_learning`, `local_replay_runtime`, `protocols`, `monitoring` | rendre chaque enrichissement traçable |
| 1 | risque et scoring explicables | `risk_backbone`, `scoring_backbone`, `meta_learning` | mieux raconter pourquoi une idée survit ou meurt |
| 2 | enrichissement A/B | `engine_a`, `engine_b`, `complete_enablers`, `meta_learning` | renforcer les moteurs Light |
| 3 | hardening C | `engine_c`, `execution_backbone`, `complete_enablers` | rendre le breakout plus robuste |
| 4 | hardening D | `engine_d`, `meta_learning`, `execution_backbone` | rendre la re-entry plus disciplinée |
| 5 | portefeuille enrichi | `portfolio_minimal`, `risk_backbone`, `complete_enablers` | mieux arbitrer les overlaps |
| 6 | Build-14 full exploitation | `complete_enablers`, `scoring_backbone`, `protocols`, `monitoring` | reader-by-reader evidence |
| 7 | data et execution feedback loop | `data_backbone`, `execution_backbone`, `meta_minimal`, `meta_learning` | reconnecter qualité et exécution aux décisions |
| 8 | supervision et opérabilité | `monitoring`, `ui`, `protocols` | rendre les raisons et états visibles |

## Lot 0 - Instrumentation et preuve avant enrichissement

### Pourquoi

Si on enrichit V5.3 sans renforcer la chaîne de preuve, on va accumuler:
- des heuristiques non auditables
- des améliorations impossibles à comparer
- du faux progrès

### Familles ciblées
- `meta_learning`
- `local_replay_runtime`
- `protocols`
- `monitoring`

### Travaux
- standardiser le format des hypothèses d’enrichissement
- imposer une table de mapping:
  - hypothèse
  - composant cible
  - famille de signal
  - preuve replay attendue
  - preuve shadow attendue
- brancher les nouvelles raisons de rejet / downgrade dans `meta_learning`
- étendre `local_replay_runtime` pour produire des bundles comparatifs par hypothèse
- s’assurer que `protocols` suit les nouvelles contributions au niveau:
  - moteur
  - reader Build-14
  - gate
- enrichir `monitoring` avec:
  - raisons de veto
  - raisons de penalisation
  - état de maturité de l’hypothèse

### Definition of done
- toute nouvelle idée d’enrichissement possède:
  - un identifiant
  - un bundle replay
  - une projection monitoring
  - une trace dans `meta_learning`
- aucune amélioration “ad hoc” ne vit hors de cette chaîne

### Preuves attendues
- tests `meta_learning`
- tests `local_replay_runtime`
- tests `protocols`
- projection visible dans le dashboard technique

## Lot 1 - Rendre risque et scoring plus explicables

### Pourquoi

Beaucoup de valeur de V5.3 est déjà dans:
- `risk_backbone`
- `scoring_backbone`

Mais ces couches sont encore moins explicites en `id/log/lineage` que Build-9X ou Build-14.

### Familles ciblées
- `risk_backbone`
- `scoring_backbone`
- `meta_learning`
- `monitoring`

### Travaux
- enrichir les raisons de `RiskEvaluation`
- relier chaque refus/reduction a des codes stables
- exposer plus finement les catégories:
  - gross cap
  - loss cap
  - beta cap
  - cluster cap
  - drawdown state
- enrichir `ScoringCandidateAudit` avec une lecture plus explicite:
  - features dominantes
  - penalties dominantes
  - hard blockers dominants
  - compatibilité portefeuille
- pousser ces raisons dans:
  - `meta_learning`
  - `monitoring`
  - exports replay

### Definition of done
- on peut expliquer, candidat par candidat:
  - pourquoi il a été accepté
  - pourquoi il a été réduit
  - pourquoi il a été rejeté
- cette explication est visible:
  - en replay
  - en monitoring
  - dans les diagnostics Build-9X

### Gain stratégique
- réduit les enrichissements “au hasard”
- permet de savoir si le vrai problème est:
  - alpha
  - coût
  - risque
  - portefeuille

## Lot 2 - Enrichissement de `engine_a` et `engine_b`

### Pourquoi

A et B restent le noyau Light. C’est le meilleur endroit pour gagner vite, à condition de ne pas casser la discipline.

### Familles ciblées
- `engine_a`
- `engine_b`
- `complete_enablers`
- `scoring_backbone`
- `meta_learning`

### Travaux `engine_a`
- mieux connecter A à:
  - `false_breakout_model`
  - `competition_monitor`
  - `market_toxicity`
- ajouter une lecture plus fine des faux trends:
  - trend trop crowdé
  - trend trop fragile
  - trend trop cher à exécuter

### Travaux `engine_b`
- conditionner B davantage par:
  - `hurst_regime_classifier`
  - `order_book_imbalance`
  - `execution_fragility`
- mieux distinguer:
  - vraie mean reversion
  - faux excès qui est en fait un début de breakout

### Definition of done
- A et B ont des variantes/hypothèses gouvernées Build-9X
- les readers Build-14 influencent clairement:
  - les diagnostics
  - les penalties
  - les reasons codes
- les améliorations passent:
  - replay
  - puis shadow

### Gain stratégique
- meilleur rendement de la couche Light
- moins de faux signaux structurels

## Lot 3 - Hardening de `engine_c`

### Pourquoi

`engine_c` est potentiellement puissant, mais c’est aussi le plus fragile face:
- aux faux breakouts
- au coût d’exécution
- au crowding

### Familles ciblées
- `engine_c`
- `execution_backbone`
- `complete_enablers`
- `meta_learning`
- `protocols`

### Travaux
- enrichir le contexte de cassure
- relier C à:
  - `lob_deep_filter_vwa`
  - `false_breakout_model`
  - `competition_monitor`
  - `execution_fragility`
- segmenter les échecs de C par catégorie:
  - breakout trop tardif
  - breakout faux
  - breakout trop coûteux
  - breakout sans suivi réel

### Definition of done
- chaque signal C a un contexte enrichi racontable
- les échecs de C sont classifiés dans `meta_learning`
- le replay prouve si l’amélioration améliore vraiment:
  - edge net
  - stabilité
  - coût

## Lot 4 - Hardening de `engine_d`

### Pourquoi

`engine_d` peut être une vraie surcouche intelligente, ou un moteur de sur-réaction. Il faut le discipliner fortement.

### Familles ciblées
- `engine_d`
- `meta_learning`
- `execution_backbone`
- `protocols`

### Travaux
- formaliser les cas d’usage légitimes de re-entry
- exploiter ses liens de contexte:
  - `origin_context_id`
  - `origin_trade_id`
  - `link_type`
- enrichir les diagnostics:
  - entrée initiale trop prudente
  - exécution ratée
  - amélioration de régime
  - faux abandon du trade initial

### Definition of done
- D n’agit jamais comme “revenge trade”
- chaque re-entry est justifiée par un contexte source explicite
- les cas de réussite/échec sont visibles en replay et en shadow

## Lot 5 - Portefeuille enrichi

### Pourquoi

Même avec de bons moteurs, un mauvais arbitrage inter-signaux peut tuer la performance.

### Familles ciblées
- `portfolio_minimal`
- `risk_backbone`
- `complete_enablers`
- `monitoring`

### Travaux
- mieux exposer:
  - overlap moteurs
  - concentration thème/cluster
  - diversité effective
  - contribution au risque
- brancher davantage les readers Build-14 dans l’allocation finale
- rendre visible la raison portefeuille d’un rejet ou d’une réduction

### Definition of done
- on peut expliquer pourquoi un bon signal individuel n’a pas été retenu
- la décision portefeuille est lisible dans monitoring et replay

## Lot 6 - Exploitation complète de Build-14

### Pourquoi

Build-14 est déjà une vraie couche code-backed riche. C’est le meilleur levier d’enrichissement transverse.

### Familles ciblées
- `complete_enablers`
- `scoring_backbone`
- `protocols`
- `monitoring`
- `engine_a/b/c/d`

### Readers concernés
- `market_toxicity`
- `execution_fragility`
- `false_breakout_model`
- `hurst_regime_classifier`
- `lob_deep_filter_vwa`
- `order_book_imbalance`
- `competition_monitor`

### Travaux
- faire un tableau reader -> usage stratégique:
  - lecture
  - pénalité
  - veto soft
  - downgrade confiance
  - budget factor
- rendre reader-level le suivi dans:
  - replay
  - shadow
  - dashboard
- comparer reader par reader:
  - utile
  - neutre
  - nocif

### Definition of done
- chaque reader a:
  - un effet mesurable
  - une justification
  - une supervision dédiée
- on sait lesquels garder en:
  - `READ_ONLY`
  - `LIMITED_INFLUENCE`
  - `DORMANT`

## Lot 7 - Boucle data/execution -> diagnostic

### Pourquoi

Beaucoup d’erreurs stratégiques ne viennent pas de l’alpha pur, mais de:
- la qualité data
- la qualité microstructure
- le coût d’exécution

### Familles ciblées
- `data_backbone`
- `execution_backbone`
- `meta_minimal`
- `meta_learning`

### Travaux
- reconnecter les facts data à la classification des échecs
- reconnecter les facts execution à la valeur réelle de l’edge
- segmenter les erreurs par:
  - stale/gaps
  - slippage
  - adverse selection
  - partial fill
  - divergence venue

### Definition of done
- les diagnostics Build-9X savent distinguer:
  - erreur d’alpha
  - erreur de donnée
  - erreur d’exécution
  - erreur de portefeuille

## Lot 8 - Supervision et opérabilité

### Pourquoi

Sans lisibilité claire, les enrichissements deviennent impossibles à piloter.

### Familles ciblées
- `monitoring`
- `ui`
- `protocols`
- `meta_learning`

### Travaux
- rendre visibles:
  - raisons de veto
  - raisons de downgrade
  - diagnostics par famille
  - état de maturité d’une hypothèse
  - effet reader Build-14
- structurer les panneaux pour les futurs audits:
  - technique
  - quant
  - trader
  - IA
  - opérateur

### Definition of done
- le dashboard raconte “pourquoi”, pas seulement “quoi”
- l’équipe peut auditer un enrichissement sans relire tout le code

## Dépendances entre lots

| Lot | Dépend de | Peut commencer quand |
| --- | --- | --- |
| 0 | aucun | tout de suite |
| 1 | 0 | après instrumentation minimale |
| 2 | 0, 1 | après explicitation risk/scoring |
| 3 | 0, 1 | après stabilité de la chaîne C |
| 4 | 0, 1 | après stabilité de la chaîne D |
| 5 | 1 | après explicitation du risque et du scoring |
| 6 | 0 | tout de suite, mais plus rentable après 1 |
| 7 | 0 | tout de suite |
| 8 | 0 | tout de suite |

## Ce qu’il ne faut pas faire

- coder des variantes moteur sans passer par `meta_learning`
- ajouter des heuristiques Build-14 sans projection replay/shadow
- enrichir `engine_c` ou `engine_d` sans feedback execution
- ouvrir `Build-12/13` comme zone d’expérimentation tant que `Build-11` reste en campagne réelle
- créer une complexité UI avant que les reasons codes soient propres

## Ordre recommandé de mise en œuvre

1. Lot 0
2. Lot 1
3. Lot 6
4. Lot 2
5. Lot 7
6. Lot 3
7. Lot 4
8. Lot 5
9. Lot 8

## Résultat attendu si ce backlog est suivi

V5.3 devient:
- plus explicable
- plus enrichissable
- moins fragile
- moins dépendante du jugement intuitif
- plus facile à auditer sous angle:
  - quant
  - trader
  - fintech
  - mathématique
  - IA

Et surtout:
- chaque nouvelle stratégie devient un objet gouverné
- chaque amélioration a une chaîne:
  - hypothèse
  - replay
  - shadow
  - supervision
  - verdict

Ce backlog est la base de cette phase.
