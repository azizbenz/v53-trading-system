# V5.3 — PROD-SAFE VPS MIGRATION PLAN
## Migration de la VPS existante vers la nouvelle doctrine liquide/microstructure
### Date : 2026-04-04
### Statut : MIGRATION PLAN

---

# 0. Objet

Ce document décrit **comment transformer la VPS V5.3 existante** — déjà avancée et codée build 1 à 17 — vers la nouvelle cible post-2025, **sans casser la production ni réécrire tout le système**.

Le principe central :

> **on ne refond pas la VPS d’un bloc**
>  
> **on la migre par vagues contrôlées, avec preuve à chaque étape**

---

# 1. Décision de migration centrale

Le mauvais plan serait :

- rouvrir les 17 builds d’un coup
- injecter la logique liquidité partout
- toucher simultanément risk, scoring, moteurs, portfolio, UI, protocols

Le bon plan est :

- geler le socle
- confirmer les builds vraiment fermés
- rouvrir seulement les chantiers critiques
- utiliser Build-14 comme **couche de transition gouvernée**
- transformer A/B avant C/D
- garder `meta_learning`, `local_replay_runtime`, `protocols`, `monitoring` au centre

---

# 2. Règles non négociables

1. Pas de moteur E.
2. Pas de bypass de `risk_backbone`, `scoring_backbone` ou `protocols`.
3. Pas de promotion directe vers le live.
4. Pas de hard block microstructure brutal avant preuve.
5. Pas de refonte du sizing live avant validation.
6. Pas d’ouverture Complete pendant la migration de Light.
7. Toute intelligence nouvelle doit être replayable, shadow-trackable et monitorée.

---

# 3. Classification des builds pour la migration

## 3.1 Builds à garder gelés sauf régression prouvée
- Build-1
- Build-2
- Build-3
- Build-5
- Build-6
- Build-7
- Build-8
- Build-9
- Build-9X
- Build-10

## 3.2 Builds à rouvrir de manière contrôlée
- Build-4
- Build-11
- Build-12
- Build-13
- Build-14
- Build-15
- Build-16
- Build-17

## 3.3 Pourquoi ce découpage
- Build-4 = risk backbone à moderniser
- Build-11/12/13 = chaîne de vérité runtime
- Build-14 = couche d’enrichissement gouvernée
- Build-15/16 = moteurs C/D à ne pas polluer trop tôt
- Build-17 = surface Complete à protéger

---

# 4. Séquence prod-safe de migration

## PHASE 0 — Freeze baseline

## Objectif
Figer la vérité de départ.

## À produire
- build status matrix
- branch de référence
- baseline metrics
- baseline reason codes
- baseline monitoring snapshots
- baseline replay bundles

## Go si
- la baseline est reproductible
- les métriques de référence sont stockées
- les builds réellement fermés sont listés

## No-go si
- plusieurs sources de vérité concurrentes
- pas de baseline comparative

---

## PHASE 1 — Delta audit des builds gelés

## Objectif
Vérifier qu’aucune régression n’a rouvert silencieusement le socle.

## Action
- smoke par build
- contract checks
- tests ciblés
- diff doc vs code minimal

## Sortie
- `KEEP_FROZEN`
- ou `LOCAL_REGRESSION_TO_FIX`

## Règle
Aucun enrichissement nouveau ne doit commencer tant que le socle n’est pas stable.

---

## PHASE 2 — Instrumentation & preuve (Lot 0)

## Modules ciblés
- `meta_learning`
- `local_replay_runtime`
- `protocols`
- `monitoring`

## Objectif
Créer la chaîne de preuve avant toute mutation métier.

## Travaux
- standardiser les hypothèses d’enrichissement
- mapper hypothèse -> composant -> signal -> preuve replay -> preuve shadow
- enrichir `meta_learning` pour suivre les nouvelles raisons
- enrichir `local_replay_runtime` pour produire des bundles comparatifs
- enrichir `protocols` pour suivre les readers et les artifacts
- exposer monitoring des nouvelles raisons et de la maturité d’hypothèse

## Go si
- chaque hypothèse a un identifiant
- chaque hypothèse a un bundle replay
- chaque hypothèse a une projection monitoring
- aucune amélioration n’existe hors de cette chaîne

## No-go si
- enrichissements “ad hoc”
- nouvelles règles sans preuve replay/shadow

---

## PHASE 3 — Explicabilité cœur (Lot 1)

## Modules ciblés
- `risk_backbone`
- `scoring_backbone`
- `monitoring`
- `meta_learning`

## Objectif
Rendre le cœur capable de raconter les effets de la nouvelle logique.

## Travaux Build-4
- enrichir `RiskEvaluation`
- relier chaque refus / réduction à des reason codes stables
- exposer :
  - gross cap
  - position cap
  - loss cap
  - beta cap
  - cluster cap
  - drawdown state
- préparer l’accueil futur de :
  - micro_friction_guard
  - liquidity stop context
  - spread regime blocks

## Travaux Build-5
- enrichir `ScoringCandidateAudit`
- exposer :
  - dominant features
  - dominant penalties
  - hard blockers dominants
  - compatibilité portefeuille
  - selection outcome
- assurer la lecture des nouveaux reason codes PHYSICS_*

## Go si
- on sait pourquoi un trade a été boosté, réduit, bloqué ou rejeté
- les reason codes sont stables
- les projections monitoring/UI sont cohérentes

## No-go si
- les nouvelles règles créent de l’opacité
- les refus deviennent impossibles à expliquer

---

## PHASE 4 — Build-14 comme couche de transition

## Principe fondamental
Build-14 ne devient pas un moteur autonome.

Il reste une couche d’enrichissement introduite en 3 niveaux :

1. `READ_ONLY`
2. `SHADOW_ENABLED`
3. `LIMITED_INFLUENCE`

### Jamais directement :
- hard block central live
- refonte complète du sizing
- activation implicite de C/D
- passage Complete

---

### PHASE 4A — READ_ONLY

## Readers ciblés
- `market_toxicity`
- `execution_fragility`
- `false_breakout_model`
- `hurst_regime_classifier`
- `lob_deep_filter_vwa`
- `order_book_imbalance`
- `competition_monitor`

## Objectif
Collecter evidence, snapshots, diagnostics.

## Impact runtime
- aucun impact de décision fort
- evidence seulement
- monitoring seulement
- replay/shadow comparison seulement

## Go si
- coûts CPU / mémoire acceptables
- evidence cohérente
- pas de régression runtime

---

### PHASE 4B — SHADOW_ENABLED

## Objectif
Comparer build enrichi vs baseline en Shadow.

## Mesures obligatoires
- fréquence utile
- CE
- faux signaux évités
- gains manqués
- block rate
- drift des readers
- coût opérationnel

## Go si
- amélioration nette ou lecture utile sans nuisance
- pas de stérilisation excessive
- pas de dégradation infra

---

### PHASE 4C — LIMITED_INFLUENCE

## Objectif
Accorder une influence bornée aux readers prouvés.

## Formes autorisées
- soft boost
- soft reduce
- ranking adjustment
- reason enrichment
- no-trade borné
- size reduction bornée

## Interdictions
- bypass risk
- bypass scoring
- hard veto global brutal
- changement non monitoré

## Go si
- les reason codes sont lisibles
- l’influence améliore le net ou la survie
- le coût opérationnel reste faible

---

# 5. Reconditionnement des moteurs

## 5.1 Moteurs prioritaires : A et B

### Pourquoi
- ils portent la Light
- ils existent déjà
- ils sont les plus rentables à transformer d’abord

---

## Build-6 / Engine A

## Direction cible
A devient un moteur “trend valide uniquement si le flux et la survivabilité le confirment”.

## Garde-fous / enrichissements possibles
- delta confirmation
- execution fragility downgrade
- toxicity downgrade
- competition / crowding caution
- false breakout incompatibility

## Règle
Aucune mutation directe live sans replay/shadow bundle.

---

## Build-7 / Engine B

## Direction cible
B devient un moteur :
- sweep fade
- retour au POC / équilibre
- mean reversion disciplinée par spread regime
- anti-faux-signal via false breakout / toxicity

## Garde-fous / enrichissements possibles
- sweep validation
- delta divergence
- spread regime block
- book fragility caution
- execution survivability filter

## Règle
Aucune augmentation de fréquence brute si la CE se dégrade.

---

## 5.2 Moteurs secondaires : C et D

### Règle
Ne pas les ouvrir tant que :
- Build-14 n’a pas prouvé sa valeur
- A/B ne sont pas stabilisés
- portefeuille enrichi non prêt

---

# 6. Data / Execution feedback loop

## Modules ciblés
- `data_backbone`
- `execution_backbone`
- `meta_minimal`
- `meta_learning`

## Objectif
Reconnecter la nouvelle logique à la réalité du runtime.

## À relier explicitement
- stale / backlog / duplication
- spread widening
- slippage
- partial fills
- adverse selection
- fragilité d’exécution
- outcomes moteur par moteur

## But
Éviter qu’une “bonne règle de liquidité” soit en réalité ruinée par :
- mauvaise qualité data
- coût réel
- mauvaise exécution
- mauvaise interprétation du flux

---

# 7. Portefeuille enrichi avant Complete

## Modules ciblés
- `portfolio_minimal`
- `risk_backbone`
- `complete_enablers`

## Objectif
Empêcher que les gains locaux readers/moteurs détruisent la cohérence portefeuille.

## Enrichissements visés
- capital competition
- crowding
- risk contribution
- diversity effective
- overlap between hypotheses
- opportunity conflict resolution

---

# 8. Chaîne runtime obligatoire

Aucune règle nouvelle ne saute ces étapes :

1. replay local
2. replay comparatif bundle
3. shadow
4. limited influence
5. micro-live candidate
6. live candidate

---

# 9. Ce qu’il ne faut pas faire

## Interdits absolus
- modifier simultanément les 17 builds
- injecter le Lab dans le live directement
- traiter Build-14 comme moteur autonome
- refaire le sizing live avant preuve
- activer Complete pendant la mutation Light
- introduire de nouveaux hard blocks partout d’un coup
- réécrire A/B/C/D en parallèle

---

# 10. Ordre exact recommandé

1. Freeze baseline
2. Delta audit builds gelés
3. Audit profond Build-4 + 11/12/13
4. Lot 0 instrumentation/preuve
5. Lot 1 explicabilité risk/scoring
6. Build-14 READ_ONLY
7. Replay bundles comparatifs
8. Build-14 SHADOW_ENABLED
9. Build-14 LIMITED_INFLUENCE
10. Reconditionnement A
11. Reconditionnement B
12. Data/execution feedback loop
13. Portefeuille enrichi
14. Décision GO/NO-GO C
15. Décision GO/NO-GO D
16. Décision GO/NO-GO Complete

---

# 11. Critères GO / NO-GO par grande vague

## GO si
- baseline conservée
- amélioration démontrée
- pas de stérilisation
- CE stable ou meilleure
- coût infra acceptable
- monitoring explicable
- rollback possible

## NO-GO si
- hausse brute du no-trade sans justification
- destruction de fréquence utile
- dette opérationnelle trop forte
- explicabilité perdue
- coût CPU/logs excessif
- dérive non contrôlée

---

# 12. Conclusion

Le bon plan prod-safe pour la transformation de la VPS n’est pas une refonte totale.

C’est une **migration gouvernée en vagues**, où :

- on protège ce qui est déjà stable
- on ouvre seulement les chantiers critiques
- on utilise Build-14 comme couche de mutation
- on transforme A/B avant C/D
- on laisse `meta_learning`, `protocols`, `monitoring` et `replay` gouverner la preuve

Ce document décrit **comment migrer sans casser**.

Le document suivant décrit **comment construire le Local AI Lab sans créer une seconde V5.3**.
