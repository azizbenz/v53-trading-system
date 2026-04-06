# V5.3 — NEW TARGET CANONICAL VPS & LOCAL AI LAB
## Canonique cible unique — architecture post-indicateurs années 90
### Date : 2026-04-04
### Statut : CANONICAL TARGET SPEC

---

# 0. Objet

Ce document fixe la **cible canonique unique** de l’évolution V5.3.

Il répond à une seule question :

> **vers quoi la VPS V5.3 et le Local AI Lab doivent converger ?**

Ce document ne décrit pas encore :
- l’ordre exact de migration depuis l’existant
- l’ordre exact de codage du Lab

Il décrit :
- la **vision cible**
- la **doctrine**
- la **topologie finale**
- les **invariants non négociables**

---

# 1. Décision stratégique centrale

La V5.3 actuelle est déjà avancée sur le plan architecture / builds / gouvernance,  
mais sa logique quant reste encore trop marquée par une lecture :

- prix-centrique
- indicateurs classiques
- stops géométriques trop visibles
- exécution trop peu gouvernée par la physique réelle du marché

La cible post-2025 doit devenir une V5.3 centrée sur :

- **liquidité**
- **résilience de la liquidité**
- **toxicité**
- **fragmentation**
- **survivabilité d’exécution**

La question centrale n’est plus :

> “le prix a-t-il franchi une ligne ?”

La question centrale devient :

> “la topographie de liquidité, la résilience du book, la toxicité du flux et la friction d’exécution autorisent-elles réellement ce trade ?”

---

# 2. Rupture doctrinale

## 2.1 Ce qu’on déclassse

Les objets “années 90” ne doivent plus être centraux :

- RSI
- MACD
- Bollinger
- ATR comme stop principal
- moyenne mobile comme logique primaire

Ils peuvent rester :
- comme fallback
- comme normalisation
- comme outil secondaire d’explicabilité
- comme outil de scaling prudent

Ils ne doivent plus décider seuls.

## 2.2 Ce qu’on met au centre

La nouvelle V5.3 cible met au centre :

- Volume Delta / Cumulative Delta
- OFI / OBI / microprice
- Volume Profile
- POC / VAH / VAL
- HVN / LVN
- Sweep / Absorption / False Breakout
- Spread Regime
- Micro-Friction / Slippage / Execution Fragility
- Book Resiliency / Refill Speed
- Market Toxicity
- Competition / Crowding / Risk Contribution
- Regime enrichi utile à la microstructure
- Closed-loop entre décisions et réalité d’exécution

---

# 3. Règle d’architecture absolue

Il ne doit exister :

- ni une V5.3 locale différente
- ni une V5.3 VPS différente
- ni une IA locale qui décide secrètement
- ni une seconde architecture parallèle de trading

Le projet doit conserver :

- **un seul shared core V5.3**
- **un seul langage de contrats**
- **une seule logique métier**
- plusieurs modes runtime :
  - LOCAL_REPLAY
  - SHADOW
  - MICRO_LIVE
  - LIVE

---

# 4. Topologie cible finale

```text
[ DOCTRINE LOCK ]
  Physics Feature Dictionary
  Transform Whitelist
  Artifact Taxonomy
  Proof Protocol
  Hook Scope Policy
  Runtime Safety Rules

[ SHARED CORE V5.3 ]
  Data backbone
  Execution backbone
  Risk backbone
  Scoring backbone
  Engines A/B/C/D
  Portfolio
  Meta / Monitoring / Protocols
  Complete Enablers

[ LOCAL AI QUANT LAB ]
  Data acquisition
  Local replay / backtest
  Feature factory
  Diagnostic engine
  Threshold calibrator
  Micro-model trainer
  Rule distiller
  Causal validator
  Artifact packer + signer

[ VPS ARTIFACT GOVERNANCE ]
  Schema verification
  Signature verification
  TTL / decay / lifecycle
  Regime distance checker
  Circuit breaker
  Hook injector

[ VPS RUNTIME ]
  Shadow / Micro-live / Live
  Monitoring / alerting
  Runtime hooks
  Execution / reconciliation

[ MULTI-VPS CONTROL PLANE ]
  Fleet health
  Artifact board
  Runtime board
  Alert aggregation
  Log query
```

---

# 5. Rôle exact de la VPS cible

La nouvelle VPS V5.3 doit rester :

- prod-safe
- sobre
- explicable
- governable
- rollbackable

La VPS n’est pas un laboratoire.

Elle est :

- la machine de runtime
- la machine de preuve
- la machine de souveraineté
- la machine d’observabilité

## 5.1 La VPS doit savoir

- importer des artifacts validés
- refuser les artifacts invalides
- surveiller leur drift
- les passer en `DECAYING` ou `DORMANT`
- appliquer des hooks bornés
- journaliser leur impact
- protéger le runtime contre les régressions

## 5.2 La VPS ne doit jamais

- exécuter du code injecté par le Lab
- accepter un modèle opaque en runtime V1/V2
- se laisser gouverner par un LLM
- envoyer ses logs bruts en continu au Lab
- promouvoir automatiquement une règle vers le live

---

# 6. Rôle exact du Local AI Lab cible

Le Local AI Lab n’est pas un trader live.

C’est une usine de :

- recherche
- replay
- diagnostic
- calibration
- distillation
- preuve
- packaging d’artifacts

## 6.1 Il doit savoir

- télécharger des données
- lire un dossier local de données
- construire un dataset versionné
- rejouer la même logique V5.3
- tester des hypothèses
- entraîner de petits modèles utiles
- distiller des règles compactes
- signer des artifacts
- récupérer des batches closed-loop depuis la VPS

## 6.2 Il ne doit jamais

- créer une logique métier non partagée
- faire du live à la place de la VPS
- exporter du code exécutable
- devenir un monstre de ML hors contrôle
- servir de seconde source de vérité

---

# 7. Taxonomie finale des artifacts

## Classe A — EDGE_ADDER
Ajoute du vrai edge net.

## Classe B — DAMAGE_REDUCER
Retire des mauvais trades sans stériliser le système.

## Classe C — EXEC_SURVIVABILITY_FILTER
Améliore la survivabilité d’exécution.

## Classe D — CAPITAL_EFFICIENCY_ENHANCER
Améliore variance / Sharpe / CE / taille sans changer nécessairement la direction.

---

# 8. Doctrine IA cible

## 8.1 IA autorisées au centre du système local

Priorité :
- XGBoost
- LightGBM
- CatBoost
- modèles tabulaires simples
- calibrateurs
- classifieurs de risque / survie / dommage

## 8.2 IA secondaires

Tolérées uniquement pour :
- résumé humain
- rapport
- synthèse narrative

LLM locaux :
- non critiques
- jamais au centre de la décision
- jamais dans la boucle logique canonique

## 8.3 IA interdites comme runtime core

- gros deep learning opaque
- modèle binaire non interprétable importé en V1/V2
- logique exportée sous forme de code Python
- LLM comme moteur de trade

---

# 9. Doctrine de preuve

Aucun artifact n’entre dans la VPS s’il n’a pas survécu à :

- ablation / counterfactual replay
- anti-cowardice test
- friction regret test
- walk-forward stability
- regime segmentation
- operational burden test
- capital efficiency test si applicable

---

# 10. Politique de données cible

## 10.1 Timeframe maître
- **1m** comme base canonique

## 10.2 Timeframes dérivés
- 5m
- 15m
- 1h

## 10.3 Profondeur historique
- archive : 2020 -> 2026
- entraînement principal : 2022 -> 2025
- holdout récent : 2026
- archive stress : 2020 -> 2021

## 10.4 Paires V1
- BTCUSDT
- ETHUSDT
- SOLUSDT
- BNBUSDT
- XRPUSDT
- LINKUSDT

---

# 11. Multi-VPS cible

Le système cible doit fonctionner avec :

- 1 VPS
- 3 VPS
- 5 serveurs ou plus

à condition d’avoir un **control plane** qui centralise :

- état machine
- état runtime
- état artifacts
- alertes
- logs ciblés
- campagnes Shadow

---

# 12. Invariants non négociables

1. Une seule V5.3 métier.
2. Aucune injection de code.
3. Aucune boîte noire runtime en V1/V2.
4. Aucun LLM dans la boucle critique.
5. Aucune feature hors Physics Lock.
6. Aucune transformation hors Transform Lock.
7. Aucun artifact sans preuve.
8. Aucun artifact sans signature.
9. Aucun hook hors scope.
10. Aucun closed-loop bloquant.
11. Aucune promotion directe Local -> Live.
12. La VPS reste souveraine.

---

# 13. Conclusion

L’ordre conceptuel correct pour Codex / les développeurs est :

1. **comprendre la cible**
2. **migrer la VPS actuelle vers cette cible sans la casser**
3. **construire le Local AI Lab comme usine de preuve et non comme seconde V5.3**

Ce document fixe la **destination**.

Les deux documents suivants décrivent :
- la migration prod-safe de la VPS existante
- la construction prod-safe du Local AI Lab
