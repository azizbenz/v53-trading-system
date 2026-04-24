# V5.3 — MD maître pour Codex
## IA Lab gouverné + couche ML adéquate + auditabilité forte

**Date** : 2026-04-22  
**Auteur** : ChatGPT (arbitrage doctrinal à partir des MD fournis + brief repo-truth)  
**Statut** : STRATEGIC_DOCTRINE_ONLY  
**Portée** : cadrer le travail IA Lab sans hallucination, sans dérive doctrinale, avec formules explicites, tests obligatoires et rails d’audit.

**Repo-truth correction (2026-04-22)** : ce MD reste un cadrage doctrinal utile, mais il n’est pas une spec d’exécution ligne à ligne. Le rail IA Lab gouverné est maintenant fermé côté repo-truth ; la couche ML bornée reste une ouverture future, pas un backlog immédiat.

---

## 0. Vérité de départ — à lire avant toute ligne de code

### 0.1 Ce qu’est le IA Lab V5.3
Le IA Lab V5.3 est **d’abord** un laboratoire local gouverné de :
- replay historique
- review / diagnostic post-trade
- calibration
- production d’artefacts
- promotion-readiness
- preuve locale avant import VPS

Il n’est **pas** à traiter comme un "classical ML lab" souverain dont le cœur serait un stack sklearn/xgboost/torch pilotant directement la prod.

### 0.2 Ce que le IA Lab n’est pas
- pas un control plane live du VPS
- pas un système de recalibration automatique sur VPS
- pas un moteur qui remplace A/B/C/D
- pas une excuse pour réécrire les formules quant tant que l’objet mathématique exact n’est pas figé
- pas une seconde architecture parallèle au canon V5.3

### 0.3 Position canonique à respecter
Le bon framing est :

> **V5.3 Local IA Lab = laboratoire local gouverné de replay, review, calibration, packaging, preuve, drift et promotion-readiness, avec une couche ML locale bornée et offline.**

### 0.4 Repo-truth à ne pas trahir
1. Les seams gouvernés replay/review/export/calibration sont déjà forts.
2. Le repo n’est pas encore prouvé comme "classical ML lab" explicite.
3. Les fronts `test_export_dir_bridge` et `test_loader` ont été refermés.
4. Le résidu quant restant est doctrinal, pas un simple stub-code.
5. `live_light_runtime.py` est oversized et doit être splitté.
6. Les forecast seams Engine C/D existent déjà et ne doivent pas être remis en backlog comme manquants.
7. Pas de prétention de vérité code au-delà du repo-truth brief + des MD.

---

## 1. Rôle demandé à Codex

Tu n’es pas autorisé à improviser l’architecture.
Tu dois **converger** vers une solution audit-ready, additive et doctrinalement honnête.

### 1.1 Mission exacte
Faire progresser le IA Lab V5.3 comme :
- noyau local gouverné de replay/calibration/review/promotion
- avec une couche ML **adéquate**, c’est-à-dire :
  - locale
  - offline
  - auditable
  - artifact-driven
  - non souveraine sur les décisions live

### 1.2 Ce que tu dois produire
- du code additif ou des splits structurels minimaux
- des tests ciblés et honnêtes
- des preuves de non-régression
- des outputs auditables ensemble par humain + assistant

### 1.3 Ce que tu ne dois jamais produire
- pas de "solution magique ML" qui remplace le canon
- pas de bypass du pipeline `Replay -> Shadow -> Micro-live -> Live-Light`
- pas de modification opportuniste des formules quant bloquées
- pas de promotion live sur score/PnL seul
- pas de dépendance runtime au training

---

## 2. Invariants non négociables

### 2.1 Invariants système
- Canon V5.3 conservé
- Moteurs autorisés : **A / B / C / D uniquement**
- Aucune nouvelle architecture top-level type `src/local_ai_lab/`
- Aucune nouvelle boucle active Local <-> VPS hors artefacts et observabilité prévue
- VPS = exécution uniquement
- Local = calcul lourd / calibration / replay / ML offline

### 2.2 Invariants IA Lab
- Le IA Lab reste **descriptif, évaluatif, producteur d’artefacts**, pas exécuteur live
- Le ML local ne peut pas devenir la source de vérité unique de direction ou de sizing
- Toute sortie utile au VPS doit devenir un **artefact versionné, hashé, signé ou gouverné**

### 2.3 Invariants quant
- **NE PAS** modifier sans décision humaine préalable :
  - `src/calibration_methods/psr.py`
  - `src/calibration_methods/dsr.py`
  - `src/calibration_methods/pot_gpd.py`
  - `src/calibration_methods/energy_distance.py`
- Les 4 ancres quant résiduelles restent gelées tant que Q1–Q4 ne sont pas tranchées

### 2.4 Invariants ML
- Le training se fait hors VPS
- La prod charge des artefacts, elle n’entraîne pas
- Pas de dépendance temps réel à sklearn/xgboost/torch sur le VPS
- La couche ML ne peut pas override A/B/C/D
- La couche ML peut au mieux : moduler une confiance, enrichir un score, aider la sélection/review

---

## 3. Doctrine de la couche ML adéquate

### 3.1 Position choisie
La couche ML adéquate pour V5.3 est une **couche locale tabulaire, bornée, explicable et non souveraine**.

### 3.2 Priorité de type de modèle
Ordre recommandé pour une **ouverture future explicite** de la couche ML, pas pour le backlog immédiat :
1. **LightGBM / XGBoost / arbres boostés tabulaires**
2. régressions / classifieurs simples comme baseline
3. deep learning seulement si un besoin strict et démontré apparaît

### 3.3 Pourquoi cette couche est adéquate
Parce qu’elle est cohérente avec :
- le hardware local réel de l’utilisateur
- le style de features microstructure / replay / coûts
- le besoin d’auditabilité
- le caractère offline du lab
- la nécessité de ne pas rendre la prod dépendante d’un gros GPU

### 3.4 Ce que la couche ML peut faire
- produire `ml_confidence`
- produire un score auxiliaire
- aider le ranking
- aider la calibration et la review
- aider à détecter drift / fragilité / crowding

### 3.5 Ce que la couche ML ne peut pas faire
- choisir le `side` seule
- bypass le `hard_block`
- remplacer `SignalCandidate`
- remplacer la logique de portefeuille
- autoriser une promotion live à elle seule

### 3.6 Contrat stratégique du ML
La couche ML doit être :
- **LAB_ONLY** pour le training
- **artifact-based** pour le transport
- **bounded** dans ses effets
- **versionnée**
- **comparée** entre replay/shadow/live
- **monitorée** en drift

---

## 4. Formules et math — à respecter

## 4.1 Forecast normalizer (Carver)
But : mettre les forecasts sur une échelle commune, sans inventer une deuxième canonique.

### Forme doctrinale
- `F_raw` = forecast brut moteur
- `ForecastScalar = 10 / E[|F_raw|]`
- `F_normalised = F_raw * ForecastScalar`
- puis clip par moteur

### Cibles de clip
- Engine A : `|forecast_strength| <= 20`
- Engine B : `<= 15`
- Engine C : `<= 15`
- Engine D : **ne pas rouvrir doctrinalement le cap dans ce slice** ; conserver le repo-truth existant si déjà câblé, sinon utiliser le canon doc 20 après arbitrage humain

### Test obligatoire
- `E[|F_normalised|] ≈ 10` sur fixture contrôlée
- test de saturation du cap moteur
- test d’entrée invalide

---

## 4.2 Break-even filter
But : refuser les émissions qui n’ont pas de rentabilité nette crédible.

### Formule
- `EV_net = x * (E[gain] - E[cost])`
- émission autorisée seulement si `EV_net > floor`
- le comparateur doit rester **strictement `>`** à la frontière

### Test obligatoire
- `cost >= gain` -> no emit
- `cost < gain` avec marge -> emit
- frontière exacte -> rejet si `== floor`
- floor négatif -> rejet entrée invalide

---

## 4.3 Cost drift monitor
But : comparer coût attendu vs coût réalisé et détecter un biais structurel.

### Formule
- `bias_pct = (mean(realised_cost) - mean(expected_cost)) / mean(expected_cost)`

### Règles minimales
- seuil d’alerte par défaut : `0.20`
- hard cap doctrinal local : `0.50`
- `min_events = 10`
- `expected_cost <= 0` : invalide
- `realised_cost < 0` : invalide

### Tests obligatoires
- biais > 20% -> alerte
- données insuffisantes -> `insufficient_data`
- reset vide le buffer
- expected <= 0 rejeté
- realised < 0 rejeté

---

## 4.4 Sizing vol-target (si retouché dans un slice dédié)
**Ne pas ouvrir ce chantier si ce n’est pas explicitement dans le scope du slice.**

### Chaîne canonique
- `instrument_value_vol = price * instrument_pct_vol * point_value`
- `vol_scalar = (capital * annual_vol_target / sqrt(252)) / instrument_value_vol`
- `N_candidate = (forecast_normalised / 10) * vol_scalar`
- `N_final = clip(N_candidate * CE_filter * cluster_filter * btc_filter, min_notional, max_position_cap)`

### Tests obligatoires
- forecast nul -> taille nulle
- clip min/max respecté
- filtre CE réduit la taille
- cluster / btc filter appliqués proprement

---

## 4.5 Purged walk-forward (si training ML)
Utiliser le rail existant `build_purged_walk_forward_plan(...)`.
Aucun split train/validation naïf n’est autorisé pour conclure un signal de promotion.

### Tests obligatoires
- folds non chevauchants
- purge / embargo respectés
- validation deterministe sur fixture

---

## 4.6 Ce qu’il ne faut pas toucher maintenant
Ne pas "réparer" en douce les ancres :
- PSR 0.9505
- DSR Table 1
- POT-GPD Denmark/Coles
- Energy same-dist < 0.05

Ces sujets restent un **slice doctrinal** séparé.

---

## 5. Plan de travail recommandé pour Codex

## Phase A — discipline et structure

### A1. Ne pas rouvrir le faux backlog
- Ne pas traiter les forecast seams Engine C/D comme manquants
- Ne pas recréer un second canon de contrats
- Ne pas re-ouvrir un chantier "classical ML lab" global

### A2. Split structurel critique
- Statut repo-truth courant : fermé
- `src/protocols/live_light_runtime.py` a déjà été resplitté sous le cap guardrail
- Ne pas remettre ce point en backlog sauf régression nouvelle prouvée

### A3. Consolider le cœur IA Lab gouverné
Statut repo-truth courant : fermé pour le rail gouverné principal.

Le prochain usage correct de ce bloc est :
- conserver la stabilité de :
  - replay
  - review
  - calibration
  - export/import d’artefacts
- ne pas rouvrir artificiellement un nouveau slice de fermeture
- utiliser cette base comme prérequis si une couche ML bornée est ouverte plus tard
- break-even
- cost drift
- observabilité locale

---

## Phase B — couche ML bornée

### B1. Créer / consolider un rail ML local explicite
Seulement si cela ne casse pas le cœur gouverné.

### B2. Surface ML autorisée
Exemple de contrat recommandé :
- `MlModelArtifact`
- `feature_hash`
- `train_window`
- `oos_metric`
- `promotion_state`
- `pair_universe`
- `schema_version`

### B3. Effet runtime autorisé
Le runtime peut lire :
- `ml_confidence`
- `ml_penalty_or_bonus_bounded`
- `drift_state`

Le runtime ne peut pas lire :
- un modèle entraîné dynamiquement sur VPS
- un side direct non justifié par les moteurs

### B4. Effet maximum du ML
Le ML doit rester un **enabler** ou une couche **soft**.
Jamais une source unique d’autorisation live.

---

## Phase C — auditabilité commune humain + assistant

### C1. Chaque slice Codex doit contenir
- objectif
- fichiers touchés
- ce qui est interdit
- formules exactes
- tests ciblés
- preuves commandes
- completion status honnête
- next safe step

### C2. Chaque slice doit être auditée contre
- repo-truth brief
- invariants ci-dessus
- non-régression tests
- absence de dérive doctrinale

---

## 6. Tests obligatoires par groupe

## 6.1 Groupe IA Lab cœur
À garder verts ou refermés si rouges dans le scope :
- `tests/test_backtest_artifact_import/test_export_dir_bridge.py`
- `tests/test_calibration_loader/test_loader.py`
- suites ciblées replay/review/calibration si touchées

## 6.2 Groupe forecast / scoring
- `tests/test_interface_contracts/test_forecast_contracts.py`
- `tests/test_scoring_backbone/test_forecast_normalizer.py`
- `tests/test_scoring_backbone/test_break_even_filter.py`
- tests runtime moteur si cap / mapping touché

## 6.3 Groupe meta / drift
- `tests/test_meta_minimal/test_refusal_journal.py`
- `tests/test_meta_minimal/test_cost_drift_monitor.py`

## 6.4 Groupe non-régression structure
- split runtime : tests protocols ciblés
- DAG pass
- `new_violations=0`
- aucun nouveau fichier `src/` > cap guardrail

## 6.5 Groupe ML (si ouvert)
- artefact round-trip
- walk-forward deterministic
- pas de override direct du side
- score borné
- modèle absent -> dégradation gracieuse
- drift -> alerte ou neutralisation bornée

---

## 7. Checklist anti-hallucination pour Codex

Avant de coder, tu dois écrire dans ton brief de session :

1. **Ce que le IA Lab est** dans ce projet
2. **Ce qu’il n’est pas**
3. **Le scope exact du slice**
4. **Les fichiers interdits**
5. **Les formules exactes concernées**
6. **Les tests qui feront foi**
7. **La définition honnête de COMPLETE / PARTIAL / BLOCKED pour le slice**

Tu dois aussi explicitement dire :
- si tu fais un split mécanique
- si tu fais une convergence de tests
- si tu ajoutes un module additif
- si tu touches un contrat
- si tu n’as pas le droit de changer une formule

---

## 8. Checklist d’ouverture obligatoire pour chaque session Codex

Copier-coller puis remplir :

```md
You are working on slice: <NAME>.

Canonical identity of IA Lab:
- governed replay / review / calibration / export / promotion-readiness lab
- bounded local ML layer only
- not a classical ML-first lab

Global invariants:
- A/B/C/D only
- no new top-level architecture
- VPS never trains
- no formula edits on PSR / DSR / POT-GPD / Energy unless expressly authorized
- no new canonical contract replacing the existing one blindly

Current scope:
- <exact scope>

Forbidden defaults:
- no hallucinated backlog
- no side override by ML
- no silent threshold invention
- no fake green verdict
- no file growth beyond guardrails

Mathematical formulas in scope:
- <formula 1>
- <formula 2>

After generation, verify explicitly:
- pytest targeted
- DAG PASS
- engineering_guardrails new_violations=0
- file-size caps respected
- completion status honest
```

---

## 9. Critères d’acceptation d’un slice

Un slice ne peut être dit **COMPLETE** que si :
- le scope est entièrement fermé
- les tests ciblés sont verts
- il n’y a pas de dérive doctrinale
- le statut repo/global n’est pas sur-vendu

Un slice doit être **PARTIAL** si :
- le périmètre local est bon mais le repo global reste rouge hors-scope
- ou un résidu doctrinal externe reste ouvert

Un slice doit être **BLOCKED** si :
- la décision humaine manque sur l’objet mathématique
- ou une dépendance doctrinale amont est absente

---

## 10. Ordre recommandé d’exécution

1. **Freeze doctrinal des 4 ancres quant** (pas de code métier)
2. **Split `live_light_runtime.py`**
3. **Consolidation replay/calibration/review/export/import**
4. **Consolidation forecast / break-even / drift**
5. **Couche ML locale bornée**
6. **Seulement après : extension plus ambitieuse du training**

---

## 11. Ce qu’on devra pouvoir auditer ensemble

À la fin de chaque slice, on doit pouvoir vérifier ensemble :
- ce qui a été touché
- ce qui n’a pas été touché
- la formule exacte utilisée
- les tests verts ciblés
- les limites connues
- le vrai statut du slice
- le prochain mouvement sûr

Si un slice n’est pas audit-able ensemble, il n’est pas prod-safe.

---

## 12. Verdict doctrinal à conserver pendant tout le chantier

> **Le prod-safe pour de l’argent réel vient d’abord du rail gouverné.**  
> **Le ML n’est acceptable que comme couche locale, offline, bornée, auditée et artifact-driven.**  
> **Le IA Lab V5.3 est central, mais il n’est pas encore un classical ML lab prouvé comme cœur souverain.**
