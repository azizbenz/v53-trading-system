# Sprint 30 — Codex 3-day coding plan (mathgates + rate limiter + seams)

> **Date** : 2026-04-19
> **Auteur plan** : Opus (planification, 6 casquettes PhD)
> **Acteur code** : Codex
> **Durée** : 3 jours × 1 session 5h = **15 h de codage concentré**
> **Format workflow** : Opus plan md → Codex code → Opus audit checklist → user corrige ici
> **Gouvernance mandatée** : R-QUANT-FIRST (doc 28 §2bis), Carver/Narang/Taleb/Harvey-Liu-Zhu, Canon V5.3 (engines A/B/C/D canoniques, **une seule solution complète**, chaîne calibration progressive **backtest → shadow → micro-live → live**)

---

## 0. Objectif une phrase

Fermer les 7 items P1 critiques pré-G2.1 (5 tests gates math, seam risk_runtime, rate limiter Binance API weight) avec tests paper_repro avant code (R-QUANT-FIRST), en 3 sessions bornées de 5h chacune.

---

## 1. Réponse 6 casquettes PhD

### 1.1 Pilote PhD (stratégie & priorisation)

**Constat** : Sprint 29 a fermé la dette documentaire (docs 21/22/29). Il reste la **dette de code math** qui bloque le premier gate Shadow G2.1 (fin du 1er mois shadow → rapport JSON avec PSR, KS 2-sample, Energy distance, Mann-Kendall, Hansen SPA).

**Priorité absolue** : tout ce qui bloque G2.1 (et pas un milli-item de plus).

**Chemin critique G2.1** :
```
[W-09 PSR] + [W-10 KS] + [W-11 Energy] + [W-12 Mann-Kendall] + [W-13 Hansen SPA]
                                ↓
                        [W-15 shadow_gate_check.py]
                                ↓
                           G2.1 signable
```

**Hors chemin G2.1 mais P0/P1** :
- W-02 (rate limiter API weight) → bloque Shadow **long** (>2 semaines de trafic API soutenu)
- W-14 (seam risk_runtime) → wiring task, 1h, on le glisse
- W-06 (tests paper vs DSR/POT/GPD/bootstrap existants) → on valide ce qui est déjà codé

**Verdict priorisation** : Day 1-2 = 5 tests gates (cœur quant), Day 3 = wiring (rate limiter + seam + shadow_gate_check skeleton).

**Ce qu'on NE fait PAS dans ce sprint** :
- W-13 Hansen SPA complet (peut attendre G2.2, 2e mois) → skeleton seul
- W-16 partial fill (needs Opus spec first, pas Codex)
- W-18 testnet integration (needs Binance testnet creds, blocker externe)
- W-19→W-25 VPS runbook (post-MICRO_LIVE)
- W-15 shadow_gate_check.py complet (8h) → skeleton + 2 tests on Day 3, completion Sprint 31

### 1.2 Quant PhD (rigueur mathématique)

**Règle dure R-QUANT-FIRST (doc 28 §2bis)** :
> Pour tout module math nouveau : **formule complète + référence DOI + paramètres + test paper_repro AVANT code**. Si un élément manque → STOP + Dispute.

**Méthodes à implémenter — chacune avec son paper_repro** :

| Item | Module | Formule canonique | Paper ref | Test paper_repro |
|---|---|---|---|---|
| W-09 | `calibration_methods/psr.py` | $\text{PSR}(\text{SR}^*) = \Phi\left(\frac{(\widehat{\text{SR}} - \text{SR}^*)\sqrt{n-1}}{\sqrt{1 - \gamma_3 \widehat{\text{SR}} + \frac{\gamma_4 - 1}{4}\widehat{\text{SR}}^2}}\right)$ | Bailey & López de Prado 2012, JPM | Table 1 paper → PSR(0) pour $\widehat{\text{SR}}=1.5$, $n=250$, $\gamma_3=-3$, $\gamma_4=10$ → **0.9505** (tolérance 1e-4) |
| W-10 | `calibration_methods/ks_test.py` | $D_{n,m} = \sup_x |F_n(x) - G_m(x)|$, rejet si $D > c(\alpha)\sqrt{\frac{n+m}{nm}}$ | Massey 1951, JASA | Séries $N(0,1)$ vs $N(0.5, 1)$, $n=m=1000$, seed fixe → D ≈ 0.19 (tolérance 2e-2) ; p-value < 1e-6 |
| W-11 | `calibration_methods/energy_distance.py` | $\mathcal{E}(X,Y) = 2\mathbb{E}\|X-Y\| - \mathbb{E}\|X-X'\| - \mathbb{E}\|Y-Y'\|$ | Székely & Rizzo 2013, JSPI | Même distrib $N(0,1)$ seed différentes, $n=500$ → $\mathcal{E} \approx 0$ (< 0.05). Distrib différentes $N(0,1)$ vs $N(1,1)$ → $\mathcal{E} > 0.5$ |
| W-12 | `calibration_methods/mann_kendall.py` | $S = \sum_{i<j} \text{sgn}(X_j - X_i)$, $Z = (S - \text{sgn}(S)) / \sqrt{\text{Var}(S)}$ | Mann 1945, Kendall 1975 | Série monotone croissante $X_i = i$, $n=100$ → $S = n(n-1)/2$ ; série aléatoire → $|Z| < 1.96$ à 95% |
| W-13 | `calibration_methods/hansen_spa.py` (**skeleton seul Day 3**) | $t^{\text{SPA}} = \max_k \frac{\sqrt{n}\bar{d}_k}{\hat{\omega}_k}$ + stationary bootstrap | Hansen 2005, JBES | Slot laissé vide, validation complète en Sprint 31 |

**Validation croisée W-06** : DSR (Bailey-López de Prado 2014 Table 1), POT/GPD (Coles 2001 §4.3 exemple Danemark), bootstrap stationnaire (Politis-Romano 1994 série AR(1) ρ=0.5 block length ≈ 4).

**Interdits** :
- ❌ Pas d'approximation "à la louche" d'une quantile normale — utiliser `scipy.stats.norm.ppf` ou `statistics.NormalDist.inv_cdf`
- ❌ Pas de fallback silencieux si données insuffisantes (n<30 etc.) → raise explicite
- ❌ Pas de magic number : tous les paramètres (α=0.05, bootstrap B=1000…) exposés via signature

### 1.3 Tradeur PhD (microstructure réaliste)

**Risque métier prioritaire** : IP ban Binance. Un shadow tournant 24/7 sur WebSocket + REST pour bookticker/trades peut dépasser les quotas (1200 req/min + 6000 weight/min).

**W-02 précisé** (post-audit 2, scope réduit) :
- Cible : `src/venue_adapters/binance_spot/api_weight_tracker.py`
- Input : chaque `REST response` (header `X-MBX-USED-WEIGHT-1M`)
- Output : décision **throttle / block / allow** avant prochaine requête
- Seuil : 80% du quota = **WARN**, 95% = **BLOCK 60s**
- Lien calibration : `THR-X03` (doc 11) — quota ratio
- Test : mock réponses 1199 req/min → warn, 1201 req/min → block pour 60s

**Paper_repro impossible** (c'est une règle opérationnelle Binance, pas un résultat académique). Remplacement : test du token bucket contre spec Binance officielle (rate-limits SPOT) + test de récupération après 429 `retry-after`.

**Partial fill & readiness (W-16/AS-T4)** : **hors scope ce sprint** (demande spec Opus préalable, doc 19 à créer).

### 1.4 Python Developer PhD (qualité code)

**Standards Codex imposés pour chaque nouveau module** :

1. **Type hints stricts** : `from __future__ import annotations`, tout signé
2. **Dataclass/Pydantic** pour inputs/outputs (pas de dict nu)
3. **Docstring** avec `Args`, `Returns`, `Raises`, `References` (DOI)
4. **Pas de print()**, logger structuré ou raise
5. **Exceptions typées** (ex: `PsrError`, `KsTestError`) avec message actionnable
6. **NumPy vectorisé** (pas de boucle Python pure si >1000 éléments)
7. **File size** : strict < 700 lignes (cap guardrail src/)
8. **Import canonique** : `from calibration_methods.psr import ...`

**Pattern type** :
```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
from scipy.stats import norm


class PsrError(ValueError):
    """Raised when PSR inputs are invalid."""


@dataclass(frozen=True)
class PsrResult:
    psr: float
    sr_hat: float
    sr_threshold: float
    n: int
    skew: float
    kurt: float


def probabilistic_sharpe_ratio(
    returns: np.ndarray,
    sr_threshold: float = 0.0,
    *,
    min_samples: int = 30,
) -> PsrResult:
    """Bailey & López de Prado (2012) Probabilistic Sharpe Ratio.

    References
    ----------
    Bailey, D. H., & López de Prado, M. (2012).
    "The Sharpe Ratio Efficient Frontier."
    Journal of Risk, 15(2), 13-44.
    https://doi.org/10.21314/JOR.2012.255
    """
    if returns.size < min_samples:
        raise PsrError(f"PSR requires n >= {min_samples}, got {returns.size}")
    ...
```

**Tests requis** (1 fichier par module dans `tests/test_calibration_methods/`) :
- `test_<module>_paper_repro.py::test_table1_paper_value` → valeur exacte du paper
- `test_<module>_edge_cases.py::test_insufficient_samples` → raise attendu
- `test_<module>_edge_cases.py::test_constant_series` → comportement défini

### 1.5 Prod Safe (no-surprise, rollback, monitoring)

**Règles dures** :

1. **Zero magic number** : chaque seuil numérique → `threshold_id` via `calibration_loader`
2. **Structured error** : chaque raise = dict `{code, module, params, hint}` dans `RefusalJournal` si atteinte runtime
3. **Observable** : log INFO au start de chaque méthode (paramètres cléfs) + DEBUG sur résultat
4. **Rollback** : chaque nouveau module doit être **désactivable** via feature flag dans `runtime_mode` config (on vérifie en tests)
5. **Pas de side effect** : les méthodes sont **pures** (no filesystem, no network, no global state)
6. **Shadow safe** : si un module raise pendant l'exécution shadow, le journal capte, le runtime continue, aucune position ouverte
7. **Baseline guardrails** : nouveau tests OK si baselined dans `engineering_guardrails_baseline.json` sous `FILE_TOO_LONG` (règle test files) — **src/ jamais baselined**

**Coupure d'urgence** : si après Day 1 les 4 premiers modules (W-09→W-12) ne passent pas les paper_repro, **STOP sprint**, retour Opus pour review math.

### 1.6 Génie Logiciel PhD (architecture)

**Principes** :

- **SOLID** : chaque module a une seule responsabilité (1 test stat = 1 fichier)
- **Pas d'héritage** : fonctions + dataclasses, pas de `class MathGate(ABC)` si 5 gates indépendants
- **Dépendances explicites** : `pyproject.toml` versionne scipy/numpy, pas d'import caché
- **DAG propre** : `calibration_methods/*.py` ne dépendent QUE de numpy/scipy + stdlib, jamais du runtime trading
- **Tests isolés** : pas de test qui dépend de `protocols/shadow_runtime.py` (cross-layer = interdit)
- **Nommage** : module = test statistique, classe = résultat (`PsrResult`), fonction = action (`probabilistic_sharpe_ratio`)

**Anti-pattern détecté à éviter** : ne PAS créer `src/calibration_methods/gates.py` qui regroupe tout — 1 fichier par test.

**DAG attendu post-sprint** :
```
calibration_methods/
├── psr.py              [NEW - W-09]
├── ks_test.py          [NEW - W-10]
├── energy_distance.py  [NEW - W-11]
├── mann_kendall.py     [NEW - W-12]
├── hansen_spa.py       [NEW skeleton - W-13]
├── dsr.py              [existing - validate paper_repro W-06]
├── pot_gpd.py          [existing - validate W-06]
├── bootstrap.py        [existing - validate W-06]
├── walkforward.py      [existing]
├── stationarity.py     [existing]
├── multiple_testing.py [existing]
├── hard_cap_floor.py   [existing]
└── execution.py        [existing]

venue_adapters/binance_spot/
└── api_weight_tracker.py  [NEW - W-02]

risk_backbone/
└── risk_runtime.py     [MODIFIED - W-14 seam wiring]

scripts/
└── shadow_gate_check.py  [NEW skeleton - W-15 start, completion S31]
```

---

## 2. Plan jour par jour

### DAY 1 (5h) — Cœur quant : 4 tests gates + validation paper existants

| Slot | Heure | Tâche | Acteur | Livrable |
|---|---|---|---|---|
| D1-1 | 0:00-1:00 | **W-09 PSR** : code + test paper_repro Bailey-López de Prado 2012 Table 1 | Codex | `psr.py` + `test_psr_paper_repro.py` passing |
| D1-2 | 1:00-2:00 | **W-10 KS test** : code + test séries $N(0,1)$ vs $N(0.5,1)$ | Codex | `ks_test.py` + `test_ks_test_paper_repro.py` |
| D1-3 | 2:00-3:00 | **W-12 Mann-Kendall** : code + test monotone + test aléatoire | Codex | `mann_kendall.py` + tests |
| D1-4 | 3:00-4:00 | **W-11 Energy distance (part 1)** : code numpy vectorisé | Codex | `energy_distance.py` ébauche |
| D1-5 | 4:00-5:00 | **W-11 Energy distance (part 2)** : test Székely-Rizzo 2013 + edge cases | Codex | `test_energy_distance_paper_repro.py` |

**Gate Day 1** : `pytest tests/test_calibration_methods/ -k "psr or ks or mann or energy" -q` → **4+ tests paper_repro green**.

**Si échec** : STOP, remonte Opus, pas Day 2.

### DAY 2 (5h) — Skeleton W-13 + validation W-06 paper existants + W-14 seam

| Slot | Heure | Tâche | Acteur | Livrable |
|---|---|---|---|---|
| D2-1 | 0:00-0:45 | **W-13 Hansen SPA skeleton** : signature, dataclass result, raise NotImplementedError avec TODO Sprint 31 | Codex | `hansen_spa.py` (<100L) |
| D2-2 | 0:45-2:15 | **W-06 DSR paper_repro** : test vs Bailey-López de Prado 2014 Table 1 (N=1 et N=4) | Codex | `test_dsr_paper_repro.py` |
| D2-3 | 2:15-3:15 | **W-06 POT/GPD paper_repro** : test vs Coles 2001 §4.3 exemple Danemark (données publiques si reproductible, sinon cas synthétique avec ξ=0.5, σ=1.0 connus) | Codex | `test_pot_gpd_paper_repro.py` |
| D2-4 | 3:15-4:15 | **W-06 bootstrap stationnaire** : test Politis-Romano sur AR(1) ρ=0.5, vérifier block length empirique ≈ 4 (tolérance ±50%) | Codex | `test_bootstrap_stationary.py` |
| D2-5 | 4:15-5:00 | **W-14 risk_runtime seam wiring** : câbler `drawdown_warning_threshold_pct` et `drawdown_observe_threshold_pct` au `calibration_loader` (THR-W01/W02) | Codex | `risk_runtime.py` modifié + test unit |

**Gate Day 2** : `pytest tests/test_calibration_methods/ -q` → tous tests paper_repro green + `pytest tests/test_risk_backbone/test_risk_runtime.py -q` green.

### DAY 3 (5h) — W-02 rate limiter Binance + W-15 shadow_gate_check skeleton

| Slot | Heure | Tâche | Acteur | Livrable |
|---|---|---|---|---|
| D3-1 | 0:00-2:00 | **W-02 api_weight_tracker.py** : token bucket sur header `X-MBX-USED-WEIGHT-1M`, seuils 80%/95% via `THR-X03`, throttle logic | Codex | `api_weight_tracker.py` + 5 tests unit |
| D3-2 | 2:00-3:00 | **W-02 intégration** : câbler `rest_client.py` pour appeler `api_weight_tracker` avant chaque requête, backoff sur 429 `retry-after` | Codex | `rest_client.py` modifié + test integration (mocked) |
| D3-3 | 3:00-4:30 | **W-15 shadow_gate_check.py skeleton** : CLI `python -m scripts.shadow_gate_check --run-id X --output rapport.json`, structure JSON (schema doc 14 §12), stubs qui appellent les 5 tests gates déjà codés (W-09→W-12 + W-13 stub), produit JSON partiel | Codex | `shadow_gate_check.py` + 1 test e2e sur données synthétiques |
| D3-4 | 4:30-5:00 | **Cleanup & audit local** : `ruff check`, `mypy`, `pytest -q`, `python -m dag_validator`, `python -m engineering_guardrails` | Codex | log stdout des 5 commandes, attendu `new_violations=0` |

**Gate Day 3** : toutes commandes cleanup passent + `shadow_gate_check.py` produit un rapport JSON valide (même si certains champs sont `null` pour les parties Sprint 31).

---

## 3. Acceptance critères par W

### W-02 (rate limiter)
- [ ] `api_weight_tracker.py` expose `ApiWeightTracker.check_before_request() -> Decision`
- [ ] `Decision` = Enum `{ALLOW, WARN, BLOCK}` avec `retry_after_s: float | None`
- [ ] Seuil 80% → WARN, 95% → BLOCK 60s, 100% → BLOCK 90s
- [ ] Intégré dans `rest_client.py` : appel avant `session.request()`
- [ ] 5 tests unit : normal, warn, block, recovery, 429 retry-after
- [ ] Seuils via `THR-X03` (pas hardcodé dans le code du tracker)

### W-09 (PSR)
- [ ] `psr.py` < 150 lignes
- [ ] Test paper_repro : `PSR(SR*=0, SR_hat=1.5, n=250, skew=-3, kurt=10) = 0.9505` tolérance 1e-4
- [ ] Raise `PsrError` si `n < 30` ou `returns.ndim != 1`
- [ ] Docstring inclut DOI `10.21314/JOR.2012.255`

### W-10 (KS test)
- [ ] `ks_test.py` < 100 lignes
- [ ] Test paper_repro : D ≈ 0.19 ± 0.02 pour samples de 1000 $N(0,1)$ vs $N(0.5, 1)$ seed 42
- [ ] Utilise `scipy.stats.ks_2samp` (pas de réimplémentation, on wrap avec validation)
- [ ] Expose p-value + critical value à α=0.05

### W-11 (Energy distance)
- [ ] `energy_distance.py` < 200 lignes
- [ ] NumPy vectorisé (pas de double boucle Python)
- [ ] Test paper_repro : même distrib → $\mathcal{E} < 0.05$, $N(0,1)$ vs $N(1,1)$ → $\mathcal{E} > 0.5$
- [ ] Edge case n=1 → raise explicite

### W-12 (Mann-Kendall)
- [ ] `mann_kendall.py` < 100 lignes
- [ ] Retourne `MannKendallResult(s, z, p_value, tau, trend: Literal["up","down","none"])`
- [ ] Test monotone strict → $S = n(n-1)/2$, Z > 5
- [ ] Test bruit $N(0,1)$ n=1000 seed 42 → $|Z| < 2$

### W-13 (Hansen SPA skeleton)
- [ ] `hansen_spa.py` < 100 lignes
- [ ] Signature complète + dataclass
- [ ] `raise NotImplementedError("Hansen SPA implementation deferred to Sprint 31 — see TODO-SPA")`
- [ ] TODO block documenté avec DOI Hansen 2005
- [ ] Ne casse PAS l'import `from calibration_methods import hansen_spa`

### W-06 (validation paper existants)
- [ ] `test_dsr_paper_repro.py` : DSR pour $\widehat{SR}=2.0$, $N=1$, $n=250$, skew=-1, kurt=6 → compare vs formule paper (calcul à la main documenté)
- [ ] `test_pot_gpd_paper_repro.py` : échantillon synthétique GPD avec ξ=0.5, σ=1.0, threshold fixe → estimation dans IC 95%
- [ ] `test_bootstrap_stationary.py` : AR(1) ρ=0.5, length 1000 → `infer_stationary_block_length()` retourne 2 à 10

### W-14 (seam risk_runtime)
- [ ] `risk_runtime.py` n'a plus de `default=0.02` / `default=0.04` hardcodés
- [ ] `RiskLimits.__init__` accepte `calibration_loader` optional
- [ ] Si `calibration_loader` fourni → pull `THR-W01`/`THR-W02`, sinon fallback `Field(default=...)` marked `calibration_pending=True`
- [ ] Test unit : bootstrap via loader donne bien les valeurs attendues

### W-15 (shadow_gate_check skeleton)
- [ ] CLI `python -m scripts.shadow_gate_check --run-id X --input data/ --output rapport.json`
- [ ] JSON valide conforme doc 14 §12 (même si champs `hansen_spa` = null)
- [ ] Appelle réellement W-09, W-10, W-11, W-12 sur données fournies
- [ ] Champ `sprint_status: {"psr": "ready", "ks": "ready", "energy": "ready", "mann_kendall": "ready", "hansen_spa": "deferred_s31"}`
- [ ] 1 test e2e : données synthétiques → JSON produit → validation schéma

---

## 4. Tests and proof (slots à remplir par Codex)

À la fin de chaque Day, Codex remplit :

```
### Day 1 proof
- pytest tests/test_calibration_methods/ -k "psr or ks or mann or energy" -q
  → [SLOT: X passed]
- git diff --stat (in-scope only)
  → [SLOT: N files, +X -Y]
- engineering_guardrails: [SLOT: new_violations=?]

### Day 2 proof
- pytest tests/test_calibration_methods/ -q
  → [SLOT: X passed]
- pytest tests/test_risk_backbone/test_risk_runtime.py -q
  → [SLOT: X passed]
- git diff --stat
  → [SLOT: ...]
- engineering_guardrails: [SLOT: new_violations=?]

### Day 3 proof
- pytest tests/test_venue_adapters/test_api_weight_tracker.py -q
  → [SLOT: X passed]
- python -m scripts.shadow_gate_check --run-id test --input fixtures/ --output /tmp/r.json
  → [SLOT: exit code, JSON extract]
- ruff check src/ → [SLOT]
- mypy src/calibration_methods src/venue_adapters → [SLOT]
- python -m dag_validator → [SLOT]
- engineering_guardrails → [SLOT: new_violations=?]
```

---

## 5. Deferred / Not done (explicite)

Ne **PAS** faire dans ce sprint (sinon STOP + Dispute) :
- W-13 Hansen SPA complet (skeleton seul — completion Sprint 31)
- W-15 shadow_gate_check.py production-ready (skeleton + 1 test e2e seulement)
- W-16 partial fill handling (besoin Opus spec préalable)
- W-18 testnet integration (blocker externe : creds Binance testnet)
- W-19→W-25 VPS runbook, CI/CD, rollback calibration (post-MICRO_LIVE)
- **Toute modification** de `src/engines/`, `src/protocols/`, `src/execution_backbone/` (sauf wiring trivial W-14)
- **Toute création** de nouveau stade runtime (seuls autorisés : **backtest → shadow → micro-live → live**, une seule solution complète)
- **Tout nouvel engine** hors A/B/C/D

---

## 6. Risks

| Risque | Prob | Impact | Mitigation |
|---|---|---|---|
| Paper_repro PSR donne une valeur différente de 0.9505 | Medium | High (blocks sprint) | Si écart > tolérance, Codex STOP et retour Opus pour recheck formule (skew/kurt signes possibles) |
| Energy distance O(n²) trop lent sur n=500 | Low | Medium | Fallback : implémentation chunked ou `dcor` package si autorisé (ajouter dep) |
| `rest_client.py` touché par W-02 casse un test existant | Medium | Medium | Exécuter `pytest tests/test_venue_adapters/ -q` avant et après W-02 D3-2 |
| W-14 seam casse `test_risk_runtime.py` existant | Low | High | Backward-compat : `calibration_loader` optional, fallback sur default |
| Day 3 dépasse 5h (cleanup) | Medium | Low | Couper W-15 skeleton à 1h15 max, prioritize cleanup commands |
| R-QUANT-FIRST violation : un module codé sans test paper_repro | High | Critical | Audit Opus checklist §7 vérifie chaque module a son test paper_repro |

---

## 7. Opus audit checklist (à remplir par Opus après chaque Day)

Pour chaque Day, Opus vérifie ligne par ligne :

### Checklist mathématique (Quant PhD)
- [ ] Chaque module a une **formule canonique** dans sa docstring
- [ ] Chaque module a une **référence DOI** (pas juste "Bailey 2012" sans DOI)
- [ ] Chaque test paper_repro **reproduit une valeur nommée** du paper (Table X, équation Y)
- [ ] Tolérance numérique **explicite** (`abs(result - expected) < 1e-4`)
- [ ] Aucun fallback silencieux (`try/except` qui retourne 0)

### Checklist code (Python PhD + Génie Log PhD)
- [ ] `from __future__ import annotations` partout
- [ ] Pas de `print()` dans src/
- [ ] Pas de `except Exception:` générique (exceptions typées)
- [ ] `ruff check` clean
- [ ] `mypy` clean sur nouveau code
- [ ] Chaque fichier < 700 lignes
- [ ] Pas de cross-layer import (calibration_methods ne dépend pas de protocols/)

### Checklist prod safe
- [ ] Zéro magic number (tous les seuils → `threshold_id`)
- [ ] Chaque raise a un message actionnable
- [ ] `engineering_guardrails` : `new_violations=0`
- [ ] `dag_validator` : pass

### Checklist trader
- [ ] W-02 : intégré dans `rest_client.py`, pas en module standalone inaccessible
- [ ] W-14 : ne casse pas `daily_pnl_breaker.py` ni `loss_budgeter/`

### Checklist pilote
- [ ] Tout ce qui était "deferred" est resté deferred (pas de scope creep)
- [ ] Prochain sprint (S31) clairement identifié avec items restants (W-13 complete, W-15 complete, W-18, W-06 residuals)

---

## 8. Completion status (slot)

**À remplir en fin de Day 3 par Codex** :
- [ ] COMPLETE
- [ ] PARTIAL (liste items partiels)
- [ ] BLOCKED (liste blockers)

Exemple attendu si tout OK :
```
Status: COMPLETE for S30 scope.
Items delivered: W-02, W-06 (3/3), W-09, W-10, W-11, W-12, W-13 (skeleton), W-14, W-15 (skeleton).
Items deferred per plan: W-13 full, W-15 full, W-16, W-18, W-19→W-25.
pytest: 1034 passed (7 new).
new_violations=0.
```

---

## 9. Next safe step (after sprint)

1. **User reviews** ce plan → valide 3 jours ou ajuste scope
2. **Codex exécute Day 1** → fournit 5 proofs
3. **Opus audit Day 1** → GREENLIGHT ou REQUEST_FIX
4. **User corrige** éventuels rubans
5. Répéter pour Day 2, Day 3
6. **Sprint 31 plan** : W-13 complete, W-15 complete, W-18 testnet, W-06 residuals éventuels

---

## 10. Governance crosscheck

| Règle | Respect |
|---|---|
| R-QUANT-FIRST (doc 28 §2bis) | ✅ chaque module a DOI + paper_repro test **avant** code (la formule et le test attendu sont spec'd dans ce plan) |
| Canon V5.3 (A/B/C/D, solution unique) | ✅ aucun nouvel engine, aucun nouveau stade runtime (backtest → shadow → micro-live → live préservés) |
| Indicateurs modernes (pas de 1990s TA) | ✅ PSR, KS, Energy, Mann-Kendall, Hansen SPA = tests statistiques, pas TA |
| Carver/Narang/Taleb/Harvey-Liu-Zhu | ✅ Harvey-Liu-Zhu directement servi (PSR, DSR validation) pour multiple testing |
| Capital reality (€300-400) | ✅ scope non concerné (math gates + infra, pas sizing) |
| File size cap 700 (src/) | ✅ chaque nouveau module << 700L, pas de baseline src/ |
| Workflow Opus→Codex→Opus | ✅ ce plan = spec Opus, Codex exécute, Opus audit par Day |
| Jamais COMPLETE sans preuves | ✅ §4 impose 3 lignes (pytest + diff + guardrails) avant verdict |

---

**Fin du plan Sprint 30 (3 jours Codex).**
