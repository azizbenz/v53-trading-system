# 31_BACKTEST_STRATEGY_LADDER.md

**Statut**: SPEC / PLANNING  
**Projet**: V5.3 Trading System  
**Objet**: Backtest Strategy Ladder - pipeline hierarchique data science + microstructure + replay riche + walk-forward  
**Date**: 2026-04-30  
**Mode**: Local IA Lab uniquement, pas VPS runtime

---

## 0. Decision operationnelle

Le Backtest Strategy Ladder reste un chantier d'architecture et de planning.

Maintenant:
- ecrire le cadre documentaire
- definir les contracts d'artifacts
- ne pas coder le ladder lourd dans cette phase

Apres stabilisation des patches:
- coder par slices courtes
- tests cibles
- audit pack par slice
- pas de nouveau rail Local Lab concurrent

---

## 1. Objectif

Creer une chaine de backtest V5.3 capable de repondre a ces questions:

1. Les moteurs A/B/C/D produisent-ils un edge net exploitable?
2. L'edge survit-il aux frais, au spread, au slippage, a l'impact et aux partial fills?
3. Le systeme fonctionne-t-il sous petit capital: 400, 500, 1500, 4000?
4. Les signaux restent-ils robustes hors echantillon?
5. Le carnet depth20 permet-il reellement l'execution?
6. Les seuils dynamiques peuvent-ils etre proposes au Local IA Lab sans mutation VPS?
7. Chaque trade, non-trade et refus est-il auditable?

Le ladder n'est pas un backtest unique. C'est une chaine:

```text
Raw Bronze immutable
    -> Silver normalized parquet
        -> Gold feature/replay store
            -> Candidate discovery fast backtest
                -> Rich L2 replay around candidate windows
                    -> Slippage/fill realism
                        -> Capital ladder
                            -> Walk-forward / OOS
                                -> Signed artifact candidate
                                    -> VPS import dry-run only
```

---

## 2. Invariants non negociables

| ID | Invariant | Raison |
|---|---|---|
| INV-BTL-01 | Le pipeline vit cote Local IA Lab, pas cote VPS. | Le VPS ne calibre rien. |
| INV-BTL-02 | Le raw n'est jamais ecrase ni remplace. | Source de verite reproductible. |
| INV-BTL-03 | Le Silver/Gold peut etre compresse, mais le Raw Bronze reste immutable. | Compression sans perte de preuve. |
| INV-BTL-04 | Aucun seuil critique hardcode. | Seuils issus de calibration/artifacts signes. |
| INV-BTL-05 | Aucune nouvelle strategie A/B/C/D deguisee. | Le ladder evalue les moteurs, ne les remplace pas. |
| INV-BTL-06 | Aucun nouveau package top-level concurrent au rail canonique. | Evite le fork logique. |
| INV-BTL-07 | Pas de live mutation. | Le Lab ne modifie pas le VPS automatiquement. |
| INV-BTL-08 | Tout candidate/trade/no-trade/refusal doit avoir reason codes. | Anti-survivorship bias. |
| INV-BTL-09 | Tout artifact produit doit avoir hash + provenance + schema version. | Auditabilite. |
| INV-BTL-10 | Si le code contredit ce MD, le code gagne. | Repo truth. |
| INV-BTL-11 | Si placement ambigu, ouvrir une dispute au lieu d'inventer. | Prod-safe. |
| INV-BTL-12 | Toute formule quant nouvelle exige formule + parametres + test de reproduction ou test synthetique controle. | R-QUANT-FIRST. |

---

## 3. Non-goals

Ce chantier ne doit pas:

- creer un nouveau runtime VPS
- creer une boucle live VPS -> Lab -> VPS
- faire de l'auto-recalibration cote VPS
- changer `SignalCandidate` canonique
- modifier la logique des moteurs A/B/C/D
- ajouter un moteur E
- brancher un LLM dans la decision de trading
- produire un artifact "live approved" sans Shadow/Micro-live
- supprimer les non-trades ou refus

---

## 4. Capital-Aware Pair Universe Promotion

Doctrine canonique:

```text
Backtest propose.
Replay valide.
Shadow confirme.
VPS enforce.
```

Le VPS ne doit pas choisir librement quelles paires trader depuis une liste statique globale.
Le VPS doit consommer un artifact gouverne de profil capital produit par backtest, replay et shadow.

### 4.1 Capital buckets

Buckets canoniques:

- 400
- 500
- 1500
- 4000

Ces buckets sont des buckets de preuve et de promotion, pas des promesses de profit.

### 4.2 Objectif backtest par bucket

Pour chaque bucket capital, le ladder doit produire ou laisser explicite comme `NOT_PROVEN`:

- `allowed_pairs`
- `blocked_pairs`
- `max_active_pairs`
- `max_position_notional_per_pair`
- `average_trade_notional`
- `expected_trade_count`
- `execution_rate`
- `min_notional_block_rate`
- `cost_block_rate`
- `fill_rate`
- `partial_fill_rate`
- `expected_ce_net`
- `executed_only_net_return` quand disponible
- `true_net_equity_max_drawdown` quand disponible
- `promotion_status`
- `recommendation`

### 4.3 Promotion ladder

Statuts de promotion canoniques:

- `BACKTEST_CANDIDATE`
- `REPLAY_CONFIRMED`
- `SHADOW_CONFIRMED`
- `MICRO_LIVE_ELIGIBLE`
- `LIVE_ELIGIBLE`

### 4.4 Regle de promotion pair / bucket

Une paire n'est pas live-eligible simplement parce qu'elle existe dans la config.

Une paire est live-eligible pour un bucket capital uniquement si:

- le backtest a passe pour ce bucket
- le replay detaille a passe pour ce bucket
- le shadow a confirme la viabilite operationnelle
- l'artifact de profil capital est frais et hash-valid
- le capital utilisable courant du VPS mappe vers ce bucket ou un bucket inferieur prouve

### 4.5 Selection du bucket capital

Regle:
- si le capital libre quote tombe entre deux buckets, utiliser le bucket prouve inferieur
- ne jamais utiliser un bucket superieur au capital utilisable prouve

Exemples:
- `free_quote_balance = 470 USDT` -> bucket `400`
- `free_quote_balance = 1480 USDT` -> bucket `500` ou `1000` si defini et prouve, jamais `1500`

### 4.6 Small-capital doctrine

- le petit capital doit reduire l'univers de paires
- `400/500` ne doit pas supposer du trading 12 paires
- l'univers de paires doit etre selectionne par viabilite mesuree, pas par preference ou liste statique

### 4.7 Distinction explicite

- Backtest propose
- Replay valide
- Shadow confirme
- VPS enforce

### 4.8 Scenario matrix

Pour chaque bucket:

- `400`
- `500`
- `1500`
- `4000`

Le ladder doit executer ou specifier les scenarios suivants:

- pair universe full
- pair universe reduced
- `max_active_pairs = 1, 2, 3, 5, 8, 12` quand faisable
- cost model complete / partial
- avec fees
- avec impact
- avec min-notional constraints
- avec partial-fill model
- avec realistic venue filters

Sorties canoniques:

- `PASS`
- `REDUCE_PAIRS`
- `TOO_SMALL`
- `NEEDS_MORE_DATA`

### 4.9 Regle VPS

Un bucket ne devient jamais `MICRO_LIVE_ELIGIBLE` ou `LIVE_ELIGIBLE` sans:

- artifact backtest
- confirmation replay
- confirmation shadow
- freshness proof
- hash validity

Un bucket sans artifacts mesures reste informatif uniquement.

### 4.10 Regle additive

Cette section est additive.

Elle ne remplace pas le reste de la methode de backtest.

Le backtest ne doit pas seulement dire:

- "la strategie marche"

Il doit dire aussi:

- avec quel capital
- sur quelles paires
- avec quelle taille moyenne
- avec quel taux d'execution
- avec quels couts
- avec quel drawdown
- avec quel statut de promotion

Puis seulement:

```text
Backtest capital bucket
-> replay detaille depth20
-> artifact de paires autorisees
-> shadow confirmation
-> VPS lit l'artifact
-> VPS trade seulement les paires autorisees pour ce capital reel
```

---

## 5. Dependances connues

Chemins et rails a verifier ou consommer proprement:

```text
src/local_replay_runtime/
src/backtest_artifact_import/
src/scoring_backbone/
src/risk_backbone/
src/portfolio_minimal/
src/execution_backbone/
src/interface_contracts/
tests/test_local_replay_runtime/
tests/test_execution_backbone/
tests/test_portfolio_minimal/
tests/cockpit/
```

Le ladder depend aussi des docs/specs suivantes:

- `CAPITAL_PROFILE_ARTIFACT_CONTRACT.md`
- `VPS_CAPITAL_PROFILE_ENFORCEMENT_SPEC.md`
- `TRUE_EXECUTED_ONLY_NET_RETURN_SPEC.md`
- `TRUE_NET_EQUITY_DRAWDOWN_SPEC.md`
- `LIVE_BALANCE_SIZING_DOCTRINE.md`
- `CAPITAL_FRAGMENTATION_AND_MIN_NOTIONAL_DOCTRINE.md`
- `COST_RECOMPUTATION_AFTER_CAP_REDUCTION_SPEC.md`

---

## 6. Roles

### 6.1 Local IA Lab

Responsabilites:

- ingestion historique
- raw -> silver -> gold
- backtest rapide
- replay riche L2
- slippage/fill simulation
- capital ladder
- walk-forward/OOS
- proposition de calibration
- packaging / signature
- production d'audit packs

Ne fait pas:

- trading live
- mutation VPS
- promotion directe vers Micro-live/Live

### 6.2 VPS

Responsabilites:

- runtime Shadow/Micro-live/Live
- execution Binance Spot
- risk gates
- consommation d'artifacts signes
- enforcement du capital bucket et du pair allowlist

Ne fait pas:

- backtest lourd
- calibration
- walk-forward
- choix libre de pair universe

---

## 7. Outputs attendus

Le ladder doit produire ou consommer:

- `StrategyIdentity`
- `ForecastSignalCandidate`
- `RefusalRecord`
- `RefusalJournal`
- replay manifest
- release candidate d'artifact
- capital profile artifact par bucket
- calibration proposal
- backtest metrics report

---

## 8. Regles de mise en oeuvre future

- aucune valeur mesuree ne doit etre inventee
- `expected_ce_net` reste expected-only
- `executed_only_net_return` et `true_net_equity_max_drawdown` restent `NOT_PROVEN` tant que les rails n'existent pas
- config capital suffit pour backtest/planning
- live/shadow doivent utiliser un capital base sur account-state gouverne ou un statut explicite `CONFIG_CAPITAL_ONLY`
- une nouvelle paire ou un nouveau capital exigent donnees, calibration et artifacts, pas rewrite strategie

## 9. Workflow backtest preserve

Le reste de la facon de faire du backtest est preserve tant qu'il ne sabote pas la doctrine capital-aware ci-dessus.

Workflow preserve:

```text
Raw Bronze immutable
-> Silver normalized parquet
-> Gold feature/replay store
-> Candidate discovery fast backtest
-> Rich L2 replay around candidate windows
-> Slippage/fill realism
-> Capital ladder
-> Walk-forward / OOS
-> Signed artifact candidate
-> VPS import dry-run only
```

Ce patch ne change pas:

- la logique des moteurs
- la logique du signal
- le role du replay detaille
- le role du walk-forward
- le role du shadow comme confirmation avant enforcement VPS
