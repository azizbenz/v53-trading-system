# 29 — Sprint final Codex : fermer les 3% restants avant lundi

**Date** : 2026-04-16
**Auteur** : Opus
**Destinataire** : Codex
**Deadline** : dimanche 2026-04-20 23h59 UTC
**Gouvernance** : doc 28 (arbitration) + doc 25 (audit protocol) + doc 26 (template)
**Règle prioritaire** : **R-QUANT-FIRST** (doc 28 §2bis) — formule complète avant code

---

## 0. État actuel — ce qui est FAIT vs ce qui RESTE

### FAIT (97%)

| ID | Livrable | Statut | Preuve |
|---|---|---|---|
| P0-1 | `revenge_risk_penalty` → user option C (observability, pas de continuous penalty) | ✅ COMPLETE | Engine D anti-revenge fields in validation rail |
| P0-2 | `ClosedEpisodeJournal` + `EpisodeRef` contracts | ✅ COMPLETE | `src/protocols/closed_episode_journal.py`, 26 tests passed |
| P0-3 | Helpers REQUIRED/OPTIONAL tranchés | ✅ COMPLETE | docs 21/22 §2 mis à jour |
| P0-4 | `k_HLZ` explicite + `multiple_testing_guard.py` | ✅ COMPLETE | module blob `b2aafc74…`, 8 tests passed |
| Doc 21 | Engine C spec — doctrinal deepening | ✅ SPEC | Cohérent avec doc 20 §11, doc 24 |
| Doc 22 | Engine D spec — doctrinal deepening | ✅ SPEC | Strategy β, R-D rules, sizing R-D-4 |
| Doc 23 | Microstructure Feature Dictionary | ✅ SPEC | Features + prohibitions + HLZ |
| Doc 27 | Opus→Codex audit brief | ✅ rev-3 | 4 disputes résolues, journal clean |
| Doc 28 | Arbitration protocol | ✅ RULE | 4 rangs, R-QUANT-FIRST, registre |

### RESTE (3%) — 9 tâches ordonnées

| # | Tâche | Priorité | Effort estimé | Dépendances |
|---|---|---|---|---|
| T1 | P0-5a : Annexe A formules quant — doc 21 | **P0 BLOQUANT** | 45 min | Aucune |
| T2 | P0-5b : Annexe A formules quant — doc 22 | **P0 BLOQUANT** | 15 min | T1 (copie + adaptations D-spécifiques) |
| T3 | P0-5c : 4 tests `paper_repro` | **P0 BLOQUANT** | 60 min | T1, T2 |
| T4 | P1-7 : Table "D-sur-A vs D-sur-C" | P1 | 20 min | T2 |
| T5 | P1-8 : Colonne `calibration_module` dans tables §5/§6 | P1 | 10 min | T1, T2 |
| T6 | P1-9 : Version-pin doc 23 | P1 | 5 min | Aucune |
| T7 | P1-10 : Source VPIN threshold crypto | P1 | 15 min | Aucune |
| T8 | §5 : 4 corrections docs 19/20 | P1 | 30 min | Aucune |
| T9 | Verification pass final + guardrails | **GATE** | 20 min | Tout |

**Total estimé** : ~3h30 de travail concentré.

---

## 1. T1 — P0-5a : Annexe A formules quant — doc 21

### Quoi faire

Ajouter à `21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md` une section **§Annexe A — Formules microstructure : spécification complète** contenant les 4 formules ci-dessous. Chaque formule est `CONSTRAINT_DOCTRINAL` (rang 1).

### Formule 1 : Realized Kernel Volatility

```
σ_RK = Σ_{h=-H}^{H} k(h/H) · γ(h)

Définitions :
  γ(h) = Σ_j r_j · r_{j+h}              # autocovariance réalisée d'ordre h
  r_j  = log(P_j) - log(P_{j-1})         # log-return sur bucket
  k(x) = Parzen kernel :
         k(x) = 1 - 6x² + 6|x|³         si |x| ≤ 0.5
         k(x) = 2(1 - |x|)³             si 0.5 < |x| ≤ 1
         k(x) = 0                         sinon
  H    = ⌈c · n^(3/5)⌉                   # bandwidth optimale
  c    = THR-C_RK_BANDWIDTH_C            # default 0.4, cap 1.0
  n    = nombre de buckets dans la fenêtre d'estimation
  bucket_size = THR-C_RK_BUCKET_SIZE     # default 5 min, cap 15 min

Source : Barndorff-Nielsen, Hansen, Lunde, Shephard (2008)
         "Designing Realized Kernels to Measure the Ex-Post Variation
          of Equity Prices in the Presence of Noise"
         Econometrica, Vol. 76, No. 6, eq.(3.1)–(3.7)
         DOI: 10.3982/ECTA6495
```

**Comment vérifier** :
1. Ouvrir le paper (DOI ci-dessus), aller à eq.(3.1) et (3.7)
2. Confirmer que le kernel Parzen correspond exactement à eq.(3.5) du paper
3. Confirmer que la règle de bandwidth `H = c · n^(3/5)` correspond à Theorem 2 du paper
4. Si Codex ne peut pas accéder au paper → ouvrir Dispute `D-2026-04-17-001`, ne pas inventer

### Formule 2 : Order Flow Imbalance (OFI)

```
OFI_t = Σ_{i=t-N+1}^{t} Δe_i

où l'event contribution à chaque update i du LOB est :
  Δe_i = ΔQ^b_i · 𝟙(P^b_i ≥ P^b_{i-1}) − ΔQ^a_i · 𝟙(P^a_i ≤ P^a_{i-1})

Définitions :
  P^b_i  = meilleur bid prix à l'event i
  P^a_i  = meilleur ask prix à l'event i
  ΔQ^b_i = Q^b_i − Q^b_{i-1}  (changement de quantité au meilleur bid)
  ΔQ^a_i = Q^a_i − Q^a_{i-1}  (changement de quantité au meilleur ask)
  𝟙()    = indicatrice
  N      = THR-C_OFI_WINDOW    # default 500 events, cap 2000

Interprétation :
  OFI > 0  → pression acheteuse nette (bid queue croît / ask queue décroît)
  OFI < 0  → pression vendeuse nette
  OFI ≈ 0  → équilibre

Source : Cont, Kukanov, Stoikov (2014)
         "The Price Impact of Order Book Events"
         Journal of Financial Econometrics, Vol. 12, No. 1, eq.(1)–(3)
         DOI: 10.1016/j.finmar.2013.06.001
```

**Comment vérifier** :
1. Paper eq.(1) : vérifier que `Δe_i` correspond exactement (attention au signe des termes ask)
2. Paper §3 Proposition 1 : confirmer que OFI prédit la direction du price change
3. Si ambiguïté sur les indicatrices (certaines versions simplifient) → utiliser la version complète eq.(3)

### Formule 3 : Kyle Lambda (λ)

```
Modèle de régression :
  ΔP_t = λ · SignedVolume_t + ε_t

Définitions :
  ΔP_t          = P_t − P_{t-1}  (changement de prix mid)
  SignedVolume_t = Σ_k volume_k · sign(direction_k)
                   sur tous les trades du bucket t
  direction_k   = +1 (buy) ou −1 (sell), classifié par :
                   - Lee-Ready rule (comparaison au mid) si L2 disponible
                   - Tick rule (comparaison au trade précédent) sinon
  λ              = coefficient OLS (price impact par unité de volume signé)
  fenêtre        = THR-C_KYLE_WINDOW  # default 1h rolling, cap 4h
  bucket         = 1 min (agrégation des trades avant régression)

Propriétés attendues :
  λ > 0 toujours (prix monte quand buy pressure, baisse quand sell pressure)
  λ élevé → marché illiquide (fort impact par unité de volume)
  λ faible → marché liquide

Source : Kyle (1985)
         "Continuous Auctions and Insider Trading"
         Econometrica, Vol. 53, No. 6, eq.(1)
         DOI: 10.2307/1913210
```

**Comment vérifier** :
1. Kyle 1985 est un modèle théorique ; l'estimation OLS est standard (Hasbrouck 1991 pour la version empirique)
2. Vérifier que `λ > 0` sur toute donnée réelle (sinon bug d'implémentation ou de classification trade direction)
3. Si classification Lee-Ready non disponible sur Binance (pas de quote data synchrone) → utiliser tick rule et documenter

### Formule 4 : VPIN

```
VPIN = (1/n) · Σ_{τ=1}^{n} |V^S_τ − V^B_τ| / V_bucket

Définitions :
  V_bucket = DailyVolume / THR-C_VPIN_BUCKETS  # default 50 buckets/jour, cap 100
  τ        = index du volume bucket (chaque bucket contient exactement V_bucket de volume total)
  V^B_τ    = volume classifié "buy" dans le bucket τ
  V^S_τ    = volume classifié "sell" dans le bucket τ
  n        = THR-C_VPIN_N_BUCKETS_WINDOW  # default 50 buckets, rolling

Classification Bulk Volume (BVC) — méthode Easley-López :
  Pour chaque trade de volume v au prix P :
    V^B = v · Φ((P − P̄) / σ_ΔP)
    V^S = v · (1 − Φ((P − P̄) / σ_ΔP))
  où :
    Φ()    = CDF normale standard
    P̄      = prix moyen du bucket courant
    σ_ΔP   = écart-type des changements de prix dans le bucket

Domaine :
  VPIN ∈ [0, 1]
  VPIN → 0 : flux équilibré (non toxique)
  VPIN → 1 : flux 100% unilatéral (toxique)
  Seuil toxic : THR-C_VPIN_MAX  # default 0.35, cap 0.5, TBD_shadow_calibration pour crypto

Source : Easley, López de Prado, O'Hara (2012)
         "Flow Toxicity and Liquidity in a High-Frequency World"
         Review of Financial Studies, Vol. 25, No. 5, eq.(2)–(4)
         DOI: 10.1093/rfs/hhs053
```

**Comment vérifier** :
1. Paper eq.(2) : bucket par volume, pas par temps — c'est la distinction clé
2. Paper eq.(3) : BVC classification — vérifier que Φ est bien la CDF normale
3. Boundary test : si tous les trades sont du même côté → VPIN = 1.0 exactement
4. Le default `THR-C_VPIN_MAX = 0.35` est plus conservateur que 0.5 ; ce choix vient de Abad-Yagüe 2012 sur equities, **pas** d'une étude crypto → marquer `TBD_shadow_calibration`

### Nouveaux thresholds à ajouter dans doc 21 §5

| ID | Meaning | Default | Hard cap | Module | Calibration seam |
|---|---|---|---|---|---|
| THR-C_RK_BANDWIDTH_C | Realized kernel bandwidth constant c | 0.4 | 1.0 | `structure_detector_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_RK_BUCKET_SIZE | Realized kernel bucket duration | 5 min | 15 min | `structure_detector_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_OFI_WINDOW | OFI cumulation window (L2 events) | 500 | 2000 | `continuation_validator_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_KYLE_WINDOW | Kyle λ OLS regression window | 1h | 4h | `continuation_validator_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_VPIN_BUCKETS | VPIN volume-bucket count per day | 50 | 100 | `continuation_validator_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_VPIN_N_BUCKETS_WINDOW | VPIN rolling window (# buckets) | 50 | 200 | `continuation_validator_c` | `risk_runtime_drawdown_calibration.py` |

### Acceptance criteria T1

- [ ] §Annexe A existe dans doc 21
- [ ] 4 formules complètes avec toutes les variables définies
- [ ] 4 DOI + eq. numbers cités
- [ ] 6 nouveaux THR-C_* dans table §5 avec default + cap + calibration_module
- [ ] Aucune variable laissée indéfinie (grep "calibrated" sans valeur → 0 match)
- [ ] Chaque formule a un bloc "Comment vérifier"

---

## 2. T2 — P0-5b : Annexe A formules quant — doc 22

### Quoi faire

Ajouter à `22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md` une section **§Annexe A — Formules microstructure : précisions D-spécifiques** :

```markdown
## Annexe A — Formules microstructure : précisions D-spécifiques

Engine D utilise les mêmes formules microstructure que C (voir doc 21 Annexe A
pour les équations complètes). Les différences D-spécifiques sont :

### Realized kernel volatility
**Recalculé** sur la fenêtre courante (post first_episode_ref.closed_at).
Raison : le contexte de vol a changé entre l'épisode original et le re-entry.
Ne PAS hériter σ_RK du first_episode_ref.

### OFI
**Recalculé** sur la fenêtre [first_episode_ref.closed_at, now].
Vérifie la persistance du flow dans la direction du re-entry APRÈS
la fermeture de l'épisode original.
THR-D_OFI_WINDOW = THR-C_OFI_WINDOW (default 500, même seam).

### Kyle λ
**Recalculé** sur la fenêtre courante.
Si λ_current > 2 × λ_at_first_episode → marché devenu plus illiquide
→ facteur de pénalisation sur le score de conviction.

### VPIN
**Recalculé** sur la fenêtre courante.
Si VPIN_current > THR-C_VPIN_MAX → skip (même règle que C).
```

### Acceptance criteria T2

- [ ] §Annexe A existe dans doc 22
- [ ] Chaque formule dit explicitement "recalculé" (pas "hérité") avec justification
- [ ] Pas de duplication des équations complètes (renvoi à doc 21 Annexe A)
- [ ] La pénalisation Kyle λ pour D est documentée (2× threshold)

---

## 3. T3 — P0-5c : 4 tests paper_repro

### Quoi faire

Créer 4 fichiers de test (ou un seul regroupé `tests/test_microstructure/test_paper_repro.py`) :

### Test 1 : `test_realized_kernel_parzen`

```python
"""Reproduce Barndorff-Nielsen 2008 Parzen kernel shape properties.
Source: DOI 10.3982/ECTA6495, eq.(3.5)
"""
def test_parzen_kernel_at_zero_is_one():
    """k(0) = 1 (centre du kernel)"""
    assert parzen_kernel(0.0) == 1.0

def test_parzen_kernel_at_boundary_is_zero():
    """k(±1) = 0 (bords du kernel)"""
    assert parzen_kernel(1.0) == 0.0
    assert parzen_kernel(-1.0) == 0.0

def test_parzen_kernel_symmetry():
    """k(x) = k(-x) pour tout x"""
    for x in [0.1, 0.25, 0.5, 0.75, 0.99]:
        assert parzen_kernel(x) == parzen_kernel(-x)

def test_parzen_kernel_nonnegative():
    """k(x) ≥ 0 pour tout x ∈ [-1, 1]"""
    for x in [i/100 for i in range(-100, 101)]:
        assert parzen_kernel(x) >= 0.0

def test_bandwidth_scaling():
    """H = ⌈c · n^(3/5)⌉ avec c=0.4, n=1000 → H = ⌈0.4 × 63.1⌉ = 26"""
    import math
    c, n = 0.4, 1000
    H = math.ceil(c * n ** 0.6)
    assert H == 26  # valeur de référence hardcodée
```

### Test 2 : `test_ofi_direction`

```python
"""Reproduce Cont-Kukanov 2014 §3 Proposition 1: OFI predicts price direction.
Source: DOI 10.1016/j.finmar.2013.06.001
"""
def test_ofi_positive_when_bid_grows_ask_shrinks():
    """Bid queue +100, ask queue -50 → OFI > 0"""
    events = [
        LOBEvent(bid_price=100.0, bid_qty=1000, ask_price=100.1, ask_qty=500),   # t=0
        LOBEvent(bid_price=100.0, bid_qty=1100, ask_price=100.1, ask_qty=450),   # t=1, bid+100 ask-50
    ]
    assert compute_ofi(events) > 0

def test_ofi_negative_when_ask_grows_bid_shrinks():
    """Bid queue -80, ask queue +120 → OFI < 0"""
    events = [
        LOBEvent(bid_price=100.0, bid_qty=1000, ask_price=100.1, ask_qty=500),
        LOBEvent(bid_price=100.0, bid_qty=920,  ask_price=100.1, ask_qty=620),
    ]
    assert compute_ofi(events) < 0

def test_ofi_zero_when_symmetric():
    """Bid +50, ask -50 puis bid -50, ask +50 → OFI ≈ 0"""
    events = [
        LOBEvent(bid_price=100.0, bid_qty=1000, ask_price=100.1, ask_qty=500),
        LOBEvent(bid_price=100.0, bid_qty=1050, ask_price=100.1, ask_qty=450),
        LOBEvent(bid_price=100.0, bid_qty=1000, ask_price=100.1, ask_qty=500),
    ]
    assert abs(compute_ofi(events)) < 1e-10
```

### Test 3 : `test_kyle_lambda_positive`

```python
"""Reproduce Kyle 1985 basic prediction: λ > 0.
Source: DOI 10.2307/1913210, eq.(1)
"""
def test_lambda_positive_with_informed_trader(seed=42):
    """Synthetic market: informed buyer drives price up → λ > 0"""
    import numpy as np
    rng = np.random.default_rng(seed)
    n = 500
    # informed: always buys → SignedVolume > 0 → price drifts up
    signed_volume = rng.exponential(100, n)
    noise = rng.normal(0, 0.5, n)
    true_lambda = 0.001
    delta_p = true_lambda * signed_volume + noise
    # OLS
    lambda_hat = np.cov(delta_p, signed_volume)[0,1] / np.var(signed_volume)
    assert lambda_hat > 0, f"λ should be positive, got {lambda_hat}"
    assert abs(lambda_hat - true_lambda) < 0.0005, f"λ should be ≈ {true_lambda}"
```

### Test 4 : `test_vpin_boundary`

```python
"""Reproduce Easley-López-O'Hara 2012 boundary case: 100% informed → VPIN=1.
Source: DOI 10.1093/rfs/hhs053
"""
def test_vpin_one_when_all_same_side():
    """All trades classified as buys → V^S=0 in every bucket → VPIN=1.0"""
    trades = [Trade(price=100.0 + i*0.01, volume=10, direction="buy") for i in range(1000)]
    daily_volume = sum(t.volume for t in trades)
    vpin = compute_vpin(trades, n_buckets_per_day=50, window=50, daily_volume=daily_volume)
    assert abs(vpin - 1.0) < 1e-6

def test_vpin_zero_when_perfectly_balanced():
    """Alternating buy/sell of equal volume → VPIN ≈ 0"""
    trades = []
    for i in range(1000):
        direction = "buy" if i % 2 == 0 else "sell"
        trades.append(Trade(price=100.0, volume=10, direction=direction))
    daily_volume = sum(t.volume for t in trades)
    vpin = compute_vpin(trades, n_buckets_per_day=50, window=50, daily_volume=daily_volume)
    assert vpin < 0.05  # not exactly 0 due to BVC approximation but close
```

### Acceptance criteria T3

- [ ] 4 fichiers de test (ou 1 regroupé) créés
- [ ] Chaque test cite DOI + eq/fig en docstring
- [ ] Chaque test utilise seed fixe pour reproductibilité
- [ ] `rtk pytest -q tests/test_microstructure/test_paper_repro.py` → all passed
- [ ] Aucun test n'importe un module microstructure qui n'existe pas encore — les tests vérifient les PROPRIÉTÉS MATHÉMATIQUES, pas l'intégration. Si le module n'existe pas encore, le test est écrit avec des fonctions helper locales (et un TODO pour wirer au module réel plus tard)

---

## 4. T4 — P1-7 : Table "D-sur-A vs D-sur-C"

### Quoi faire

Ajouter à doc 22 §3 Stage 8 (avant le bloc `SignalCandidate`) :

```markdown
### Comportement de D selon l'engine d'origine du first_episode_ref

| Dimension | D-sur-A (first_episode vient de A) | D-sur-C (first_episode vient de C) |
|---|---|---|
| bet_structure hérité | DIRECTIONAL_LONG ou DIRECTIONAL_SHORT | BREAKOUT (continuation variant) |
| forecast_strength clip | [0, 10] (identique) | [0, 10] (identique) |
| conviction profile | Structure reformation dans direction trend A | Structure reformation post-breakout continuation |
| invalidation | first_episode_ref.invalidation tightened 0.5× | first_episode_ref.invalidation tightened 0.5× |
| sizing | 0.5 × N_first_episode (R-D-4) | 0.5 × N_first_episode (R-D-4) |
| risque spécifique | Réversion contre le trend si momentum épuisé | Faux breakout continuation (fade setup) |
| OFI requis | Dans la direction du trend A original | Dans la direction de la continuation C originale |
```

### Acceptance criteria T4

- [ ] Table ajoutée à doc 22 §3
- [ ] Les deux cas (D-sur-A, D-sur-C) couverts
- [ ] Pas de nouvelle formule introduite (les formules sont celles de l'Annexe A)

---

## 5. T5 — P1-8 : Colonne calibration_module dans tables thresholds

### Quoi faire

Dans doc 21 §5 et doc 22 §6, ajouter une colonne `Calibration seam` à chaque table de thresholds pointant vers le module de calibration :

- Les THR-X* (X08, X09, X10, X11) → `engine_coordination_rules.py` via `risk_runtime_drawdown_calibration.py`
- Les THR-C_* (lookback, OFI, queue, VPIN, invalidation) → `risk_runtime_drawdown_calibration.py`
- Les THR-D_* (lookback, min_gap, marginal_ev) → `risk_runtime_drawdown_calibration.py`
- THR-W01, THR-T01, THR-D01 → renvoi doc 19 §threshold table

### Acceptance criteria T5

- [ ] Chaque threshold pointe vers un module de calibration existant ou à créer
- [ ] Aucun "calibrated" orphelin (sans module pointé)

---

## 6. T6 — P1-9 : Version-pin doc 23

### Quoi faire

Dans le header de doc 21 et doc 22, remplacer :
```
companion: docs 19, 20, 22, 23
```
par :
```
companion: docs 19, 20, 22, 23 (pinned: doc_23@<git_hash_of_23_MICROSTRUCTURE_FEATURE_DICTIONARY.md>)
```

Obtenir le hash via :
```bash
rtk git log --format="%H" -1 -- docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md
```

### Acceptance criteria T6

- [ ] Hash réel (pas placeholder) dans headers docs 21 et 22

---

## 7. T7 — P1-10 : Source VPIN threshold crypto

### Quoi faire

Doc 21 §5 dit `THR-C_VPIN_MAX ≤ 0.5` sans source crypto.

Action :
1. Chercher (timebox 15 min) une étude VPIN sur crypto. Candidats :
   - Abad-Yagüe et al. (2018) "Does VPIN predict cryptocurrency crashes?"
   - Wei-Wang (2020) "Liquidity and Market Efficiency in Cryptocurrencies"
   - Ardia-Bluteau-Rüede (2019) "Regime changes in Bitcoin GARCH volatility dynamics" (mentionne VPIN comme feature)
2. Si trouvé → citer DOI + valeur seuil observée dans la table §5
3. Si non trouvé → marquer explicitement dans la table :
   ```
   THR-C_VPIN_MAX | Max VPIN before toxic skip | 0.35 | 0.5 | continuation_validator_c |
   Note: default 0.35 from Abad-Yagüe 2012 (equities); crypto-specific calibration TBD_shadow_calibration
   ```

### Acceptance criteria T7

- [ ] Soit DOI crypto citée, soit mention explicite "TBD_shadow_calibration" + source equities transitoire

---

## 8. T8 — §5 : 4 corrections docs 19 et 20

### Quoi faire

4 corrections chirurgicales. Pour chaque correction, je donne le grep pour trouver l'occurrence et le remplacement exact.

### Correction 1 : `src/meta_engine/` → paths corrects

```bash
rtk grep -n "meta_engine" docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md
rtk grep -n "meta_engine" docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md
```

Remplacer selon contexte :
- `src/meta_engine/<runtime>` → `src/meta_minimal/<runtime>`
- `src/meta_engine/<governance>` → `src/meta_learning/<governance>`
- `src/meta_engine/<coordination>` → `src/protocols/<coordination>`
- `tests/test_meta_engine/` → `tests/test_protocols/` ou `tests/test_meta_minimal/` selon le module testé

### Correction 2 : `side="flat"` résiduel

```bash
rtk grep -n 'side.*flat\|flat.*side\|"flat"' docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md
```

Si trouvé → remplacer par le pattern standard :
> "append `ConditioningRecord(family=HARD_BLOCK)` + `RefusalRecord(category=HARD_BLOCK)`, emit no canonical `SignalCandidate`"

### Correction 3 : "drop-in replacement"

```bash
rtk grep -n "drop-in\|drop.in" docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md
```

Remplacer par :
> "backward-compatible extension: optional fields added first, then per-engine migration on a staged schedule"

### Correction 4 : "A/B only coded"

```bash
rtk grep -n "A/B only\|A.B only\|seulement A.B\|only A and B" docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md
```

Remplacer par :
> "A/B/C/D codés ; C et D requièrent doctrinal deepening (voir docs 21, 22)"

### Acceptance criteria T8

- [ ] `grep "meta_engine" docs/production_deployment_plan/19_*.md docs/production_deployment_plan/20_*.md` → 0 occurrences
- [ ] `grep '"flat"' docs/production_deployment_plan/20_*.md` → 0 occurrences
- [ ] `grep "drop-in" docs/production_deployment_plan/20_*.md` → 0 occurrences
- [ ] `grep "only.*coded\|A/B only" docs/production_deployment_plan/19_*.md` → 0 occurrences

---

## 9. T9 — Verification pass final

### Quoi faire (dans cet ordre exact)

```bash
# 1. Guardrails — zéro nouvelle violation
python scripts/run_engineering_guardrails.py
# Vérifier: new_violations=0

# 2. Tests paper_repro
rtk pytest -q tests/test_microstructure/test_paper_repro.py
# Vérifier: all passed

# 3. Tests existants engine C/D — pas de régression
rtk pytest -q tests/test_engines/test_engine_c/ tests/test_engines/test_engine_d/
# Vérifier: no failures

# 4. Tests protocoles — pas de régression
rtk pytest -q tests/test_protocols/
# Vérifier: no failures

# 5. Tests calibration — pas de régression
rtk pytest -q tests/test_calibration_methods/
# Vérifier: no failures

# 6. Cohérence inter-docs — vérification manuelle
rtk grep -n "meta_engine" docs/production_deployment_plan/*.md
# Vérifier: 0 résultats (ou seulement dans contexte historique "was meta_engine, now...")

rtk grep -n '"flat"' docs/production_deployment_plan/*.md
# Vérifier: 0 résultats dans un contexte d'émission SignalCandidate

# 7. Checklist R-QUANT-FIRST pour chaque formule en Annexe A
# Pour chaque formule, vérifier:
#   [ ] Équation complète
#   [ ] DOI + eq. number
#   [ ] Paramètres avec THR-* default + cap
#   [ ] Test paper_repro référencé
```

### Acceptance criteria T9

- [ ] `new_violations=0`
- [ ] Tous les tests passent (paper_repro + engine C/D + protocols + calibration)
- [ ] 0 `meta_engine` résiduel dans les docs
- [ ] 0 `side="flat"` résiduel dans contexte d'émission
- [ ] Checklist R-QUANT-FIRST verte pour les 4 formules

---

## 10. Rapport de complétion Codex

Après T9, Codex produit un **bloc de complétion** dans le format suivant :

```
SPRINT FINAL COMPLETION REPORT
===============================
Date: YYYY-MM-DD
Branch: <branch name>

T1 P0-5a (Annexe A doc 21):
  status: COMPLETE | PARTIAL | BLOCKED
  files: <list>
  formulas: 4/4 with DOI
  thresholds_added: <count>

T2 P0-5b (Annexe A doc 22):
  status: COMPLETE | PARTIAL | BLOCKED
  files: <list>

T3 P0-5c (paper_repro tests):
  status: COMPLETE | PARTIAL | BLOCKED
  tests_passed: <n>/<total>

T4 P1-7 (D-sur-A vs D-sur-C):
  status: COMPLETE | PARTIAL | BLOCKED

T5 P1-8 (calibration_module column):
  status: COMPLETE | PARTIAL | BLOCKED

T6 P1-9 (version-pin doc 23):
  hash: <actual git hash>

T7 P1-10 (VPIN crypto source):
  status: COMPLETE (DOI found) | COMPLETE (TBD_shadow marked)

T8 §5 (corrections docs 19/20):
  meta_engine_remaining: 0
  flat_remaining: 0
  drop_in_remaining: 0
  ab_only_remaining: 0

T9 Verification:
  guardrails: new_violations=<n>
  paper_repro_tests: <passed>/<total>
  engine_cd_tests: <passed>/<total>
  protocol_tests: <passed>/<total>
  calibration_tests: <passed>/<total>

OVERALL: COMPLETE | PARTIAL | BLOCKED
BLOCKED_BY: <if partial/blocked, what's missing>
DISPUTES_OPENED: <list or "none">
```

Ce rapport est ajouté à `docs/production_deployment_plan/update_audit/2026-04-16_docs21_22_opus_audit.md` section "Tests and Proof".

---

## 11. Après le sprint — handback Opus

Quand Codex envoie le rapport de complétion :
1. Opus exécute le re-audit final sous protocole 25
2. Cible verdict : ≥ 9.0/10 (le seuil monte de 8.5 à 9.0 parce que P0-5 comble le trou quant)
3. Si ≥ 9.0 → docs 21/22 passent de `SPEC` à `APPROVED SPEC` → merge autorisé
4. Si < 9.0 → Opus liste les écarts restants dans un nouveau doc 27 §addendum

---

## 12. Timeline recommandée

| Jour | Tâches | Heures estimées |
|---|---|---|
| Jeudi 17 avril | T1 + T2 (formules) | 1h |
| Vendredi 18 avril | T3 (tests paper_repro) + T4 (D-sur-A/C) | 1h30 |
| Samedi 19 avril | T5 + T6 + T7 + T8 (corrections P1) | 1h |
| Dimanche 20 avril matin | T9 (verification pass) + rapport de complétion | 30 min |
| Dimanche 20 avril après-midi | Handback Opus → re-audit | Opus side |

---

**Fin du brief. Codex : commencer par T1 (formules Annexe A doc 21). Ne pas coder de feature microstructure avant que T1 et T2 soient COMPLETE.**
