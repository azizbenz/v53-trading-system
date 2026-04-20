# 2026-04-21 — Quant Anchor Residues — Doctrinal Disambiguation (STOP slice)

**Date** : 2026-04-21  
**Auteur spec** : Opus élevé  
**Exécutant** : Codex  
**Durée estimée** : ~1h (audit + 4 questions humaines, PAS de code métier)  
**Déclencheur** : R-QUANT-FIRST — Codex tente de "forcer" la clôture des 4 résidus quant en modifiant `psr.py`, `dsr.py`, `pot_gpd.py`, `energy_distance.py`. Ceci viole la doctrine : tant que l'objet mathématique exact à reproduire n'est pas figé par une décision humaine, on ne touche pas les formules.

---

## §0 STOP ORDER — à lire avant toute autre action

Codex **DOIT s'arrêter immédiatement** de modifier :

- `src/calibration_methods/psr.py`
- `src/calibration_methods/dsr.py`
- `src/calibration_methods/pot_gpd.py`
- `src/calibration_methods/energy_distance.py`

Ainsi que leurs tests associés sous `tests/test_calibration_methods/`.

**Raison** : Les 4 résidus de la wave 1 (`2026-04-20_quant_anchor_hardening_wave1.md`) sont explicitement **Deferred / Not Done** parce que l'ancre mathématique demandée ne correspond pas à l'API publique ou au seam actuel du code. Toucher les formules sans une décision doctrinale **humaine** préalable reviendrait à trafiquer les invariants mathématiques pour satisfaire un label de test — ce qui est interdit par R-QUANT-FIRST.

---

## §1 Objectif de ce slice

Ce slice **n'est pas un slice de refactor**. Il livre :

1. Mise à jour honnête du statut des 4 résidus dans la wave 1 (BLOCKED / PARTIAL avec justification)
2. Mesure précise de l'interface réelle de chaque module (objet mathématique actuellement testé, type de preuve disponible, API publique)
3. Formulation de **4 questions doctrinales humaines** à remonter à l'utilisateur (pas pour Codex : pour Opus+user)
4. Préservation intégrale des 5 preuves fermées de la wave 1

Aucune formule n'est touchée dans ce slice.

---

## §2 Docs governants

- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md` — §3 rules on Deferred/Not Done, Completion Status honesty
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md` — structure imposée
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md` — séparation pouvoir Opus/Codex (Codex ne tranche pas la doctrine)
- `docs/production_deployment_plan/update_audit/2026-04-20_quant_anchor_hardening_wave1.md` — pack à mettre à jour en §6 ci-dessous
- R-QUANT-FIRST (doctrine implicite Sprint 30/31) : les formules fermées Bailey-Lopez de Prado, Bailey-Borwein-Lopez de Prado-Zhu, Coles, Székely-Rizzo sont intouchables tant que l'utilisateur n'a pas tranché quelle sémantique reproduire.

---

## §3 Current Code Seam — ce qui existe aujourd'hui

### PSR (`src/calibration_methods/psr.py`, 150L)

- Formule exacte Bailey-López de Prado 2012 eq. 3 : `Φ((SR_hat - SR*) * sqrt(n-1) / sqrt(1 - γ3*SR_hat + ((γ4-1)/4)*SR_hat²))`
- API publique : `compute_probabilistic_sharpe_ratio(returns, benchmark_sharpe=0.0, acceptance_floor=0.95)`
- Entrée : séquence de returns
- Sortie : `ProbabilisticSharpeRatioResult` (psr ∈ [0,1], passes_floor bool)
- **Objet mathématique testable** : pour un dataset `returns` donné, la valeur PSR produite par la formule fermée
- **Ce qui n'existe pas** : un dataset de référence dont la valeur PSR attendue soit `0.9505` selon Bailey & López de Prado 2012 (tableaux ou figures à citer précisément)

### DSR (`src/calibration_methods/dsr.py`, 141L)

- API publique : `compute_deflated_sharpe_ratio(...)` (à lire §4 pour l'interface exacte)
- **Objet mathématique testable** : sortie de l'API actuelle pour un dataset donné
- **Ce qui n'existe pas** : mapping direct entre l'exemple Table 1 de Bailey-Borwein-Lopez de Prado-Zhu 2014 et les paramètres acceptés par l'API actuelle

### POT-GPD (`src/calibration_methods/pot_gpd.py`, 192L)

- Estimateurs GPD (σ, ξ) par MLE sur excess over threshold
- **Objet mathématique testable** : estimateurs ML pour un dataset donné, VaR/ES quantiles
- **Ce qui n'existe pas** : le dataset Denmark Fire Insurance ou un dataset Coles de référence dans le repo ; copyright et licence de redistribution non résolus

### Energy distance (`src/calibration_methods/energy_distance.py`, 180L)

- Implémente une statistique Energy **scalée** (pas la statistique brute de Székely-Rizzo)
- **Objet mathématique testable** : la statistique scalée actuelle, qui a son propre comportement asymptotique
- **Ce qui n'existe pas** : alignement entre "Energy same-distribution < 0.05" (qui suppose la statistique brute sous H0 → 0) et le scaling actuel qui produit une distribution différente sous H0

---

## §4 Mesures à prendre par Codex (lecture pure, pas d'écriture)

Codex doit, **sans modifier aucun fichier .py** :

1. Lire `src/calibration_methods/dsr.py` intégralement.
2. Lire `src/calibration_methods/pot_gpd.py` intégralement.
3. Lire `src/calibration_methods/energy_distance.py` intégralement.
4. Lire les tests associés :
   - `tests/test_calibration_methods/test_psr.py` (si existant)
   - `tests/test_calibration_methods/test_dsr.py` (si existant)
   - `tests/test_calibration_methods/test_pot_gpd.py` (si existant)
   - `tests/test_calibration_methods/test_energy_distance.py`
5. Remplir la **Table d'interface** en §5 du présent document.

**Interdit** : éditer les `.py` pendant cette phase de mesure.

---

## §5 Table d'interface à remplir par Codex (slot)

### 5.1 PSR

```
Objet mathématique testé aujourd'hui :
  la formule fermée Bailey-Lopez de Prado 2012 eq. 3
  PSR(SR*) = Φ((SR_hat - SR*) * sqrt(n-1) / sqrt(1 - γ3*SR_hat + ((γ4-1)/4)*SR_hat^2))
  appliquée a une serie publique `returns`, avec SR_hat, γ3 et γ4 derives de cette serie

Interface publique exacte (signature) :
  compute_probabilistic_sharpe_ratio(
      returns: Iterable[float],
      *,
      benchmark_sharpe: float = 0.0,
      acceptance_floor: float = 0.95,
  ) -> ProbabilisticSharpeRatioResult

Type de preuve disponible aujourd'hui :
  tests de type/contrat, bornes [0,1], comportement qualitatif
  (series positives -> PSR > 0.5, series negatives -> PSR < 0.5),
  symetrie approximative autour de 0.5, guardrails d'entree invalides.
  Aucun ancrage numerique litteral 0.9505 n'est prouve in-repo.

Ancre demandée (wave 1 deferred) : PSR = 0.9505
Ce qui manque pour la fermer :
  un dataset ou un benchmark publie et cite explicitement, dont la valeur
  PSR sous cette API publique vaut 0.9505; ou bien une decision doctrinale
  disant que l'ancre peut etre fermee par equivalence via l'API `returns`
  au lieu d'une ancre fermee sur (SR_hat, n, γ3, γ4) prise directement.
```

### 5.2 DSR

```
Signature publique exacte de compute_deflated_sharpe_ratio :
  compute_deflated_sharpe_ratio(
      returns: Iterable[float],
      *,
      trial_count: int,
      acceptance_floor: float = 0.95,
  ) -> DeflatedSharpeRatioResult

Paramètres acceptés :
  returns, trial_count, acceptance_floor.
  Les quantites suivantes sont derivees en interne depuis `returns` :
  observation_count, mean_return, sample_std, sharpe_ratio, skewness,
  kurtosis, sharpe_variance, benchmark_sharpe, dsr, passes_floor.

Paramètres Table 1 Bailey-Borwein-Lopez de Prado-Zhu 2014 (strategy count, trial returns, variance of trials, etc.) :
  la reference doctrinale vise un objet type "Sharpe observe + correction
  multiple-testing" avec nombre d'essais/strategies, taille d'echantillon,
  benchmark Sharpe ajuste, variance de Sharpe et moments de la distribution.
  Le seam courant n'accepte pas cet objet verbatim; il reconstruit ces
  quantites a partir d'une serie `returns` et de `trial_count`.

Delta entre les deux (paramètres acceptés vs paramètres Table 1) :
  l'API actuelle accepte un jeu minimal (`returns`, `trial_count`) et derive
  le reste; elle n'expose pas une interface "Table 1" ou l'appelant injecte
  directement SR_hat, variance de Sharpe, skewness, kurtosis et benchmark
  Sharpe de reference. Le pont vers Table 1 n'est donc pas explicite.

Ce qui manque pour fermer l'ancre Table 1 :
  un mapping doctrinal explicite entre les parametres Table 1 et les
  quantites derivees par l'API actuelle; ou une decision humaine disant
  qu'une reproduction litterale Table 1 impose une extension d'API.
```

### 5.3 POT-GPD

```
Signature publique exacte :
  fit_pot_gpd_tail_risk(
      losses: Iterable[float],
      *,
      config: PotGpdConfig | None = None,
  ) -> PotGpdResult

Type d'ancre demandé (Coles 2001, Denmark Fire Insurance) :
  une ancre literalement rattachee a Coles 2001 / Denmark Fire Insurance,
  c'est-a-dire un dataset externe de reference ou des valeurs publiees pour
  threshold, xi, beta/sigma, VaR et eventuellement ES. Aucune valeur numerique
  canonique exploitable n'est fournie localement dans ce repo.

Statut du dataset dans le repo :
  absent. Aucun fixture Denmark/Coles redistribue n'est present dans le repo.

Alternatives envisageables (validation comportementale Coles-compatible) :
  validation comportementale sur donnees synthetiques GPD ou sur pertes
  ordonnees, avec recovery tolerable de xi/beta, VaR monotone et bootstrap
  stable. Cela reste Coles-compatible, mais ce n'est pas une ancre
  Denmark/Coles litterale.
```

### 5.4 Energy distance

```
Formule exacte implémentée (copier depuis energy_distance.py) :
  T(x, y) = (n*m / (n+m)) * E_hat(x, y)
  avec
    E_hat(x, y) = (2/(n*m)) * sum_ij |x_i - y_j|
                - (1/n^2) * sum_ij |x_i - x_j|
                - (1/m^2) * sum_ij |y_i - y_j|
  puis retour de `scale * max(e_hat, 0.0)` avec `scale = (n*m)/(n+m)`.

Statistique brute Székely-Rizzo (formule théorique) :
  E_n,m = (2/(nm)) Σ||x_i-y_j|| - (1/n²) Σ||x_i-x_i'|| - (1/m²) Σ||y_j-y_j'||

Facteur de scaling appliqué actuellement :
  scale = (n * m) / (n + m)

Comportement asymptotique sous H0 (statistique scalée actuelle) :
  sous H0, la statistique brute E_n,m tend vers 0; la statistique exposee ici
  est une version scalee et dependante de la taille d'echantillon. La magnitude
  absolue n'a donc pas la meme semantique qu'une ancre brute "proche de 0".

Pourquoi l'ancre "Energy same-dist < 0.05" est ambiguë :
  parce que le seuil < 0.05 suppose implicitement une statistique brute
  ou une calibration de sa magnitude sous H0. Le seam actuel expose une
  statistique scalee; "same-dist < 0.05" n'est donc pas un invariant
  doctrinal stable sans decider d'abord si l'ancre vise la statistique
  brute E_n,m ou la statistique scalee actuelle.
```

---

## §6 Mise à jour du pack wave 1 (écriture autorisée, UNIQUEMENT cette section)

Codex doit ouvrir `docs/production_deployment_plan/update_audit/2026-04-20_quant_anchor_hardening_wave1.md` et **appendre** en fin de fichier :

```markdown
---

## Addendum 2026-04-21 — Residue status hardening (R-QUANT-FIRST)

Following audit disambiguation pass (see `2026-04-21_quant_anchor_residues_doctrinal_disambiguation.md`), the four deferred anchors are now formally labeled:

| Anchor | Status | Reason |
|--------|--------|--------|
| PSR 0.9505 | **BLOCKED** | No reference dataset whose PSR equals 0.9505 under Bailey-López de Prado 2012 eq.3 is available in-repo; the requested numeric target is not anchored to a specific published table/figure. Awaiting human doctrinal decision: closed-form direct anchor vs equivalence-via-returns-API anchor. |
| DSR Table 1 | **BLOCKED** | `compute_deflated_sharpe_ratio(...)` public API does not accept the Table 1 parameter set of Bailey-Borwein-López de Prado-Zhu 2014 verbatim. Awaiting human doctrinal decision: literal Table 1 reproduction (requires API extension) vs demonstrated equivalence via current API. |
| POT-GPD Denmark/Coles | **PARTIAL** | The Coles 2001 reference dataset is not redistributed in-repo (licensing). A synthetic GPD simulation anchor exists in the current test harness but is not a Denmark/Coles-literal anchor. Awaiting human decision: real Denmark/Coles dataset (requires license resolution) vs Coles-compatible behavioral validation via simulation recovery. |
| Energy same-dist < 0.05 | **BLOCKED** | Current implementation uses a scaled Energy statistic; the `< 0.05` threshold assumes the unscaled Székely-Rizzo E_{n,m} statistic (which → 0 under H0). The two statistics are not equivalent. Awaiting human doctrinal decision: anchor the raw E_{n,m} statistic (requires new function or unscaled variant) vs anchor the current scaled statistic at a different threshold derived from its own null distribution. |

No formula was modified for this addendum. Wave 1 closed anchors (KS fixed-seed, Energy strong-shift under scaled statistic, Mann-Kendall S=4950, Hansen SPA two anchor cases, stationary bootstrap AR(1)) remain intact and unchanged.
```

**Interdit** : modifier toute autre ligne de la wave 1 pack.

---

## §7 Questions doctrinales humaines (slot — PAS à remplir par Codex)

Codex **remonte** ces questions à l'utilisateur via §11 "Next safe step" du présent pack. L'utilisateur (avec Opus en médiateur) tranche. Codex **n'exécute pas** tant que les réponses ne sont pas figées dans un pack suivant (`2026-04-??_quant_anchor_residues_wave2.md`).

### Q1 — PSR
> Veut-on **(A)** fermer l'ancre PSR par une formule fermée directe (identifier un dataset synthétique dont la valeur PSR est exactement calculable analytiquement et vaut `0.9505`), ou **(B)** fermer par une équivalence démontrée : ouvrir un benchmark où `(SR_hat, n, γ3, γ4)` produisent la valeur cible via l'API actuelle `compute_probabilistic_sharpe_ratio` ?

### Q2 — DSR
> Veut-on **(A)** étendre l'API actuelle pour accepter verbatim les paramètres Table 1 de Bailey-Borwein-López de Prado-Zhu 2014 (breaking change), ou **(B)** démontrer l'équivalence via l'API actuelle en fournissant un mapping explicite entre paramètres Table 1 et paramètres `compute_deflated_sharpe_ratio` ?

### Q3 — POT-GPD
> Veut-on **(A)** intégrer le dataset Denmark Fire Insurance (Coles 2001) dans le repo avec résolution préalable de la licence, ou **(B)** valider comportementalement via simulation : paramètres GPD (σ, ξ) connus → simulation → MLE recovery dans une tolérance Coles-compatible ?

### Q4 — Energy distance
> Veut-on **(A)** ancrer la statistique brute Székely-Rizzo `E_{n,m}` (nécessite une fonction ou variante unscaled dans `energy_distance.py`), ou **(B)** ancrer la statistique scalée actuelle à un seuil différent de `0.05`, dérivé de sa propre distribution sous H0 ?

---

## §8 Claims Implemented (ce slice)

- C8.1 — Les 4 résidus wave 1 sont formellement labellisés BLOCKED/PARTIAL avec justification dans l'addendum §6
- C8.2 — L'interface réelle des 4 modules est mesurée et documentée en §5
- C8.3 — Les 4 questions doctrinales humaines sont formulées en §7
- C8.4 — Aucun `.py` métier n'est modifié
- C8.5 — Les 5 preuves wave 1 fermées restent intactes (KS, Energy strong-shift, Mann-Kendall, Hansen SPA, bootstrap)

---

## §9 Tests et preuves (slots Codex)

```
C8.1 addendum wave 1 — git diff wave 1 pack :
les deux packs d'audit concernes sont actuellement `untracked` dans ce worktree,
donc `git diff` ne fournit pas une preuve utile ici. Verification de contenu:
append only en fin de
  docs/production_deployment_plan/update_audit/2026-04-20_quant_anchor_hardening_wave1.md
avec un addendum 2026-04-21 de statut:
  PSR 0.9505 -> BLOCKED
  DSR Table 1 -> BLOCKED
  POT-GPD Denmark/Coles -> PARTIAL
  Energy same-dist < 0.05 -> BLOCKED

C8.2 mesures interface — §5 rempli :
oui. §5.1 a §5.4 documentent l'objet mathematique teste, la signature
publique reelle, le type de preuve disponible et le point exact manquant
pour chaque residu.

C8.3 questions humaines — §7 non modifiées (slot par Opus/user) :
confirme. §7 laisse intactes les questions Q1 a Q4 et ne les reinterprete pas.

C8.4 aucun .py modifié — git status des 4 fichiers + tests :
honnetete requise: worktree global deja sale avant ce STOP slice.
Constat de lecture sur les fichiers proteges:
  - src/calibration_methods/dsr.py : deja modifie avant ce slice
  - src/calibration_methods/pot_gpd.py : deja modifie avant ce slice
  - tests/test_calibration_methods/test_energy_distance.py : deja modifie avant ce slice
  - aucun nouveau diff ajoute dans ce STOP slice sur les .py proteges
  - pas de diff observe au moment de la lecture sur:
      src/calibration_methods/psr.py
      src/calibration_methods/energy_distance.py
      tests/test_calibration_methods/test_psr.py
      tests/test_calibration_methods/test_dsr.py
      tests/test_calibration_methods/test_pot_gpd.py

C8.5 wave 1 closed proofs intacts :
preuve existante de la wave 1 conservee:
  python -m pytest -q tests/test_calibration_methods/test_ks_test.py tests/test_calibration_methods/test_energy_distance.py tests/test_calibration_methods/test_mann_kendall.py tests/test_calibration_methods/test_hansen_spa.py tests/test_calibration_methods/test_bootstrap.py --basetemp=.test_tmp/pytest_quant_wave1
  -> 57 passed
preuve full calibration deja etablie sur la wave 1:
  python -m pytest -q tests/test_calibration_methods --basetemp=.test_tmp/pytest_quant_full_b
  -> 98 passed
```

---

## §10 Deferred / Not Done (ce slice)

- Les 4 ancres restent non fermées — par design. C'est l'objet de ce slice de les documenter comme telles.
- La wave 2 quant (écriture de formules, datasets, variantes statistiques) est **bloquée** jusqu'aux réponses Q1–Q4.
- Repo global : le DAG baseline et engineering_guardrails baseline restent rouges hors-slice. Ce pack ne les adresse pas (FU-1 et FU-2 du 2026-04-21 s'en chargent).

---

## §11 Risks / Open Questions

- **Risque 1** : Codex tente quand même de "fermer" un des 4 résidus en modifiant une formule → régression mathématique. Mitigation : §0 STOP + §9 C8.4 `git status unchanged`.
- **Risque 2** : Confusion slice local vs repo global. Le slice calibration/anchors wave 1 est largement **vert** (98 tests passed). Le repo global reste **rouge** (guardrails new_violations=5, DAG FAIL 4 imports). Ne pas déclarer COMPLETE global sur la base d'un slice vert.
- **Open Q1–Q4** : voir §7, doivent être tranchées par l'utilisateur avant toute wave 2 quant.

---

## §12 Completion Status (slot Codex)

```
PARTIAL

Justification :
  Ce slice livre la disambiguation doctrinale (§5, §6, §7) mais ne ferme pas les 4 résidus — par design, en attente de décision humaine.

Changed :
  - Addendum appended to docs/production_deployment_plan/update_audit/2026-04-20_quant_anchor_hardening_wave1.md
  - This file (2026-04-21_quant_anchor_residues_doctrinal_disambiguation.md) populated in §5, §9, §12 and §13

Unchanged (vérifié) :
  - no new edits were added in this STOP slice to protected quant `.py` files
  - at read time, no diff was observed on:
      src/calibration_methods/psr.py
      src/calibration_methods/energy_distance.py
      tests/test_calibration_methods/test_psr.py
      tests/test_calibration_methods/test_dsr.py
      tests/test_calibration_methods/test_pot_gpd.py
  - worktree already dirty before this STOP slice on:
      src/calibration_methods/dsr.py
      src/calibration_methods/pot_gpd.py
      tests/test_calibration_methods/test_energy_distance.py

Remaining :
  - Q1–Q4 doctrinal answers from user (Opus mediator)
  - Wave 2 quant pack to be written once answers frozen
```

---

## §13 Next Safe Step (slot Codex — à remonter à Opus/user)

```
Next safe step :
  Opus relaye Q1–Q4 à l'utilisateur. Attendre 4 réponses trancheuses.
  Tant que Q1–Q4 non résolues, NE PAS ouvrir de wave 2 quant.
  En parallèle, Codex peut exécuter FU-1 (engine_a split) et FU-2 (DAG imports) —
  slices independants de cette disambiguation quant.
```

---

## §14 Checklist audit Opus

- [ ] §0 STOP order respecté (aucune modif des 4 `.py` métier ni de leurs tests) — vérifier via `git status` et `git diff src/calibration_methods/ tests/test_calibration_methods/`
- [ ] §5 rempli avec mesures précises (pas de "TODO" ou de vague)
- [ ] §6 addendum appendé à la wave 1 pack — pas de ligne wave 1 antérieure modifiée (vérifier `git diff docs/production_deployment_plan/update_audit/2026-04-20_quant_anchor_hardening_wave1.md` : **seul append** en fin)
- [ ] §9 C8.5 : les 5 tests wave 1 re-passent à l'identique (57 passed slice, 98 passed full)
- [ ] §12 Completion Status = PARTIAL (pas COMPLETE, pas BLOCKED)
- [ ] §13 Next safe step remonte Q1–Q4 à l'utilisateur

**Verdict slot :**
```
[OPUS FILL — GREENLIGHT_DOCTRINAL / REQUEST_FIX]
```

---

## §15 Scope — séparation stricte

Ce slice est **indépendant** de :

- FU-1 (`2026-04-21_engine_a_runtime_split_to_fit_cap700.md`)
- FU-2 (`2026-04-21_dag_unauthorized_imports_engine_d_execution_backbone.md`)

Codex peut les exécuter en parallèle (3 slices séparés, scopes disjoints).

Ce slice est **bloqueur** de :

- Toute future wave 2 quant (PSR/DSR/POT-GPD/Energy)
- Toute tentative de labelliser les gates G2.1/G2.2/G2.3 "production-ready" tant que PSR n'est pas ancrée

---

## §16 Rappel doctrinal final

> Une preuve verte sur un slice local ne rend pas le repo global vert.  
> Un test qui passe sur une formule trafiquée ne vaut pas un test qui passe sur une formule canonique.  
> Tant que l'objet mathématique à reproduire n'est pas figé par décision humaine, on documente l'ambiguïté — on ne la résout pas en code.

R-QUANT-FIRST est non-négociable.
