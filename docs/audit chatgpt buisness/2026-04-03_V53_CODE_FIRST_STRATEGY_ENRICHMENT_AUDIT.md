# 2026-04-03 - V5.3 code-first strategy enrichment audit

## Objet

Ce document prolonge l'audit code-first des modules.

But:
- partir des composants **reellement presents dans le code**
- dire **comment les utiliser pour creer des strategies**
- dire **comment les enrichir sans sauter d'etapes**
- dire **ou sont les vraies capacites**, les limites, les angles morts et les priorites

Ce document est donc:
- un audit d'usage strategique
- un registre d'enrichissement
- une grille anti-oubli

Source primaire:
- le code de `src/`
- le registre [V53_CODE_FIRST_MODULE_COMPONENT_AUDIT.md](E:/claude%20%20v5.3/v53_trading_system/docs/audit%20chatgpt%20buisness/2026-04-03_V53_CODE_FIRST_MODULE_COMPONENT_AUDIT.md)

## Regles de travail pour enrichir V5.3

1. ne pas commencer par les moteurs seuls
2. ne pas enrichir un moteur si la preuve replay/shadow n'est pas branchee
3. ne pas ajouter de logique qui contourne `risk_backbone`, `scoring_backbone` ou `protocols`
4. ne pas traiter Build-14 comme un moteur autonome
5. ne pas utiliser Build-9X pour muter le live
6. ne pas oublier que la valeur strategique reelle de V5.3 vient de la chaine complete:
   - data
   - risk
   - scoring
   - engine
   - portfolio
   - meta
   - replay
   - shadow
   - monitoring

## Vue d'ensemble: ou se trouvent les vraies capacites strategiques

| Famille code-backed | Valeur strategique actuelle | Interet pour creer de nouvelles strategies | Priorite d'enrichissement |
| --- | --- | --- | --- |
| `data_backbone` | lecture marche, qualite, sante paire | tres forte | haute |
| `execution_backbone` | economie d'execution reelle | tres forte | haute |
| `risk_backbone` | survivabilite, caps, drawdown | tres forte | haute |
| `scoring_backbone` | selection economique et rank | tres forte | haute |
| `engine_a/b/c/d` | alpha explicite | forte | haute |
| `portfolio_minimal` | coherence inter-signaux | forte | moyenne-haute |
| `meta_minimal` | observabilite economique | forte | moyenne |
| `meta_learning` | diagnostic, hypotheses, revue | tres forte | tres haute |
| `local_replay_runtime` | preuve rapide et reproductible | tres forte | tres haute |
| `protocols` | passage replay -> shadow -> live | critique | tres haute |
| `complete_enablers` | contexte enrichi gouverne | forte | haute |
| `monitoring/ui` | lisibilite et gouvernance | forte | moyenne-haute |

## Audit composant par composant oriente strategie

### 1. `data_backbone`

#### Role strategique reel
- fournir des evenements de marche exploitables
- penaliser ou suspendre les paires dont la qualite est douteuse
- reduire les faux signaux dus a une mauvaise fraicheur ou a des gaps

#### Ce que cette famille permet deja
- strategies basees sur flux live ou replay propre
- differenciation par paire saine vs paire degradee
- adaptation du comportement en fonction du stale/backlog

#### Ce qu'il faut enrichir en priorite
- enrichir les signaux microstructure exploites par les moteurs
- mieux exposer les facts de:
  - fraicheur
  - gaps
  - duplications
  - saturation file d'attente
- brancher plus explicitement ces facts dans le scoring et le risk

#### Ce qu'il ne faut pas faire
- enrichir un moteur sans preuve que les inputs data sont propres
- confondre richesse de flux et qualite de flux

#### Impact strategie
- permet de creer des strategies conditionnelles:
  - trend seulement sur paires propres
  - reversion seulement si coherence + fraicheur
  - breakout seulement si le bruit data est faible

### 2. `execution_backbone`

#### Role strategique reel
- convertir une idee rentable en execution realiste
- mesurer le cout reel et la friction
- proteger contre les strategies qui "marchent" seulement sans execution

#### Ce que cette famille permet deja
- evaluer les strategies en tenant compte des:
  - fees
  - latence
  - partial fills
  - divergence ordre/fill
  - adverse selection

#### Ce qu'il faut enrichir en priorite
- relier plus finement les hypotheses de moteur aux outcomes d'execution
- exploiter le retour execution pour penaliser:
  - les setups trop chers
  - les signaux trop fragiles
  - les paires liquides en apparence mais mauvaises en execution

#### Ce qu'il ne faut pas faire
- declarer un edge valide sans passage execution
- laisser l'execution etre seulement un module de reporting

#### Impact strategie
- permet de filtrer les strategies "beaux backtests / mauvaise execution"
- indispensable pour breakout, re-entry et event-driven

### 3. `risk_backbone`

#### Role strategique reel
- borne de survie du systeme
- arbitre entre opportunite locale et risque global

#### Capacites code-backed utiles
- `gross_cap`
- `position_cap`
- `loss_cap`
- `beta_cap`
- `cluster_cap`
- drawdown guard avec seuils:
  - `drawdown_warning_threshold_pct = 0.02`
  - `drawdown_observe_threshold_pct = 0.04`

#### Ce que cette famille permet deja
- strategies multi-paires sans explosion d'exposition
- penalisation des themes trop correles
- reduction ou refus en regime de drawdown

#### Ce qu'il faut enrichir en priorite
- audit plus fin des raisons de refus pour mieux retro-informer les moteurs
- brancher davantage les facts risk dans `meta_learning`
- ajouter une lecture plus explicite des concentrations de themes/cluster

#### Angle mort actuel
- la surface de log est moins riche que Build-9X/11/14
- le risk raisonne fort, mais raconte moins explicitement pourquoi au niveau lineage

### 4. `scoring_backbone`

#### Role strategique reel
- transformer des opportunites heterogenes en classement economiquement comparable

#### Capacites code-backed utiles
- feature selection
- raw score
- penalties score
- penalties size
- hard blockers
- ranking
- compatibilite portefeuille

#### Seuils visibles dans le code
- `max_score_penalty = 3.0`
- `min_size_multiplier = 0.05`
- `anomaly_low = -10.0`
- `anomaly_high = 10.0`

#### Ce que cette famille permet deja
- melanger des moteurs differents sans perdre la gouvernance
- classer par rentabilite ajustee du cout et du risque
- eliminer les candidats incompatibles avant portefeuille

#### Ce qu'il faut enrichir en priorite
- rendre les features et les penalties encore plus explicites strategy-by-strategy
- utiliser plus agressivement Build-14 comme contexte de penalisation gouvernee
- reconnecter les raisons de blocage aux hypotheses Build-9X

### 5. `engine_a`

#### Role strategique reel
- noyau trend / premium / expansion

#### Ce qu'il permet deja
- strategies de poursuite structurelle
- signaux porteurs sur actifs leaders et regimes expansion

#### Enrichissements utiles
- lier plus fortement la decision A aux readers Build-14:
  - `false_breakout_model`
  - `competition_monitor`
  - `market_toxicity`
- ajouter une decomposition plus explicite des echecs par contexte

#### Angle mort
- risque de sur-detecter des tendances bruitees si le filtre microstructure n'est pas assez fort

### 6. `engine_b`

#### Role strategique reel
- mean reversion intraday

#### Ce qu'il permet deja
- strategies de retour vers moyenne locale
- exploitation des exces et excusions temporaires

#### Enrichissements utiles
- conditionner plus finement par:
  - `hurst_regime_classifier`
  - `order_book_imbalance`
  - `execution_fragility`
- mieux distinguer:
  - reversion saine
  - faux signal face a un vrai breakout

#### Angle mort
- risque de combattre un trend structurel si les filtres regime ne sont pas assez stricts

### 7. `engine_c`

#### Role strategique reel
- breakout continuation

#### Ce qu'il permet deja
- strategies de sortie de range et poursuite d'impulsion

#### Enrichissements utiles
- le coupler nativement avec:
  - `lob_deep_filter_vwa`
  - `false_breakout_model`
  - `competition_monitor`
- enrichir la lecture du contexte de cassure et de post-cassure

#### Angle mort
- c'est le moteur le plus sensible aux faux breakouts et au cout d'execution

### 8. `engine_d`

#### Role strategique reel
- re-entry / second chance

#### Ce qu'il permet deja
- strategies de reprise apres signal initial manque ou invalide partiellement
- re-engagement controle au lieu de sur-trader l'entree initiale

#### Points forts reels
- liens de contexte source code-backed:
  - `origin_context_id`
  - `origin_trade_id`
  - `link_type`

#### Enrichissements utiles
- utiliser `meta_learning` pour analyser quand la seconde chance est legitime
- relier D aux contextes:
  - rejection initiale trop stricte
  - execution ratee
  - regime en amelioration

#### Angle mort
- sans diagnostic fort, D peut devenir un moteur de “revenge trade”

### 9. `portfolio_minimal`

#### Role strategique reel
- eviter que des bons signaux individuels forment un mauvais portefeuille global

#### Ce qu'il permet deja
- selection
- allocation
- coherence budgetaire Light

#### Enrichissements utiles
- exposer plus clairement:
  - contribution au risque
  - diversification effective
  - overlap des moteurs
- brancher plus explicitement les readers Build-14 dans l'allocation

#### Angle mort
- la logique portefeuille existe, mais une partie des sous-fonctions canoniques reste absorbee plutot qu'isolee

### 10. `meta_minimal`

#### Role strategique reel
- rendre la strategie observable economiquement

#### Ce qu'il permet deja
- DTR
- CRA
- break-even drift
- edge tracking

#### Enrichissements utiles
- relier plus explicitement les findings meta aux hypotheses Build-9X
- produire des diagnostics plus segmentes:
  - par paire
  - par moteur
  - par regime
  - par cout d'execution

#### Angle mort
- forte valeur de supervision, mais moins de gouvernance explicite que Build-9X

### 11. `meta_learning`

#### Role strategique reel
- transformer les erreurs et quasi-reussites en hypotheses gouvernees

#### Ce qu'il permet deja
- diagnostic post-trade
- mistake classification
- near-miss analysis
- hypotheses
- candidats
- replay bundles
- review queue
- merge gates explicites

#### Seuils et garde-fous visibles
- backlog alert: `1000`
- backlog protection: `5000`
- passage possible en `capture_minimale`
- blocage review/promotion si donnees incompletes

#### Ce qu'il faut enrichir en priorite
- faire de chaque enrichissement de strategie un objet Build-9X complet
- ne plus ajouter de logique “ad hoc” hors de cette chaine
- augmenter la granularite des diagnostics de casse:
  - faux breakout
  - regime mismatch
  - cout > edge
  - stale data
  - cluster overcrowding

#### C'est la meilleure base pour:
- creer des variantes gouvernees de A/B/C/D
- enrichir des penalties
- enrichir des contexts Build-14
- decider quoi envoyer en replay puis en shadow

### 12. `local_replay_runtime`

#### Role strategique reel
- laboratoire de preuve avant Shadow

#### Ce qu'il permet deja
- export replay gouverne
- evidence bundle
- replay metrics
- replay DTR
- performance guard
- consistency guard

#### Ce qu'il faut enrichir en priorite
- multiplier les protocoles de comparaison par:
  - moteur
  - regime
  - reader Build-14
  - contexte execution
- fabriquer des bundles standards par type d'hypothese

#### Angle mort
- si on n'utilise pas vraiment cette couche, on force trop de travail plus tard dans Shadow

### 13. `protocols`

#### Role strategique reel
- machine de preuve V5.3

#### Ce qu'il permet deja
- Shadow complet
- comptage de jours
- orchestrator daily
- service VPS
- websocket live capture
- micro-live gate
- live-light gate
- safing manuel gouverne

#### Ce qu'il faut enrichir en priorite
- toujours brancher tout enrichissement strategique a cette couche
- suivre reader par reader et moteur par moteur dans les rapports Shadow
- ne pas promouvoir une logique si elle n'a pas de preuve protocolaire

#### C'est la couche qui decide si une idee devient:
- replay-only
- shadow-ready
- micro-live-ready
- live-light-ready

### 14. `complete_enablers`

#### Role strategique reel
- enrichir la decision sans casser le canon des moteurs

#### Readers code-backed
- `market_toxicity`
- `execution_fragility`
- `false_breakout_model`
- `hurst_regime_classifier`
- `lob_deep_filter_vwa`
- `order_book_imbalance`
- `competition_monitor`

#### Regles de gouvernance visibles
- en Shadow:
  - `SHADOW_ENABLED`
  - influence active pour comparaison
- apres Shadow:
  - `READ_ONLY` ou `LIMITED_INFLUENCE`
- severites et budgets visibles:
  - critique -> penalty `0.25`, budget `0.0`
  - eleve -> penalty `0.10` ou `0.15`, budget `0.85` ou `0.75`

#### Ce que cette famille permet deja
- filtrer ou penaliser des signaux selon le contexte enrichi
- rendre A/B/C/D beaucoup plus intelligents sans multiplier les moteurs

#### Meilleur usage strategique
- ne pas creer un moteur “E”
- faire de Build-14 la couche de contexte et de protection transverse

### 15. `monitoring` + `ui`

#### Role strategique reel
- rendre la strategie lisible
- rendre les degradations visibles
- rendre la preuve partageable et exploitable

#### Ce qu'ils permettent deja
- projections Build-9, 9X, 11, 12, 13, 14
- dashboard technique
- actions operateur
- market lab
- account/user-data projection

#### Enrichissements utiles
- exposer plus directement:
  - raisons de veto
  - raisons de penalisation
  - diagnostics Build-9X par famille
  - facts portefeuille/cluster/regime

#### Angle mort
- si le dashboard ne remonte pas les vraies raisons, l'equipe enrichit a l'aveugle

## Ordre recommande pour enrichir V5.3 sans oublier de composant

1. partir d'un probleme strategique explicite
   - ex: faux breakout
   - ex: mean reversion qui combat un trend
   - ex: execution trop chere
2. cartographier le probleme dans la chaine complete
   - data
   - moteur
   - scoring
   - risk
   - portfolio
   - execution
   - meta
3. decider si la reponse doit vivre dans:
   - un moteur
   - Build-14
   - un penalty scoring
   - un veto risk
   - un diagnostic Build-9X
4. creer l'hypothese dans `meta_learning`
5. la prouver en `local_replay_runtime`
6. la brancher dans `protocols`
7. l'observer en Shadow
8. seulement apres, discuter d'influence live

## Matrice anti-oubli pour creation de strategie

Pour chaque nouvelle idee, verifier:

| Question | Famille concernee |
| --- | --- |
| Les donnees d'entree sont-elles propres? | `data_backbone` |
| Le cout d'execution tue-t-il l'edge? | `execution_backbone` |
| Le risque global l'autorise-t-il? | `risk_backbone` |
| La comparaison economique avec les autres candidats est-elle correcte? | `scoring_backbone` |
| Le moteur est-il le bon endroit pour cette logique? | `engine_*` |
| Le portefeuille garde-t-il du sens? | `portfolio_minimal` |
| Le systeme saura-t-il expliquer l'echec? | `meta_minimal` |
| L'amelioration est-elle gouvernee? | `meta_learning` |
| Peut-on la prouver en replay? | `local_replay_runtime` |
| Peut-on la suivre en Shadow? | `protocols` |
| Est-ce un contexte enrichi plutot qu'un nouveau moteur? | `complete_enablers` |
| Les raisons sont-elles visibles en supervision? | `monitoring/ui` |

## Conclusion operable

Si l'objectif est de creer des strategies en utilisant **toute** la capacite de V5.3, alors il ne faut pas penser:
- “quel moteur ajouter ?”

Il faut penser:
- “dans quelle couche du systeme cette intelligence doit vivre ?”

Le constat code-first est net:
- les moteurs ne sont qu'une partie de la valeur
- la vraie puissance de V5.3 vient de la combinaison:
  - alpha explicite
  - selection economique
  - risque
  - preuve replay/shadow
  - contexte enrichi Build-14
  - diagnostic et gouvernance Build-9X

La meilleure suite n'est donc pas d'ajouter des strategies au hasard.
La meilleure suite est un travail composant par composant, en priorisant:

1. `meta_learning`
2. `local_replay_runtime`
3. `protocols`
4. `complete_enablers`
5. `risk_backbone`
6. `scoring_backbone`
7. `engine_a/b/c/d`
8. `portfolio_minimal`
9. `monitoring/ui`

Ce document sert de base pour cette phase.
