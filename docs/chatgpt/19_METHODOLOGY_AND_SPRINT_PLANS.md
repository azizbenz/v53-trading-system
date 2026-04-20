# 19_METHODOLOGY_AND_SPRINT_PLANS

## Included Source Docs
- docs/production_deployment_plan/update_audit/2026-04-17_codex_methodology_semantic_gap_guard.md
- docs/production_deployment_plan/update_audit/2026-04-19_sprint_30_codex_3day_mathgates_ratelimiter.md
- docs/production_deployment_plan/update_audit/2026-04-19_sprint_31_codex_6day_travail_critique_suite_sprint_30.md

---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_codex_methodology_semantic_gap_guard.md

## Objective

Hard-code a work-method correction in `CODEX_PROMPT.md` so Codex no longer:

- flattens Engine A/B into shared seams derived from Engine C/D
- starts ideating before a direct double-check of current code, active docs, and real module placement

## Docs Governants

- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md`

## Current Code Seam

`CODEX_PROMPT.md` already contained a session lesson noting the error, but it was still advisory. The failure mode was methodological:

- compare weaker engines to richer engines
- infer a shared seam too early
- risk copying trading semantics across engines with different intents
- start ideating from intuition before verifying the current repo and the governing docs

## Placement

- Root prompt: `CODEX_PROMPT.md`
- Audit pack: `docs/production_deployment_plan/update_audit/2026-04-17_codex_methodology_semantic_gap_guard.md`

## Files Changed

- `CODEX_PROMPT.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_codex_methodology_semantic_gap_guard.md`

## Claims Implemented

1. The faulty methodology is now explicitly banned, not merely noted.
2. A repository-wide double-check method is now mandatory before any design direction:
   - `CODE CHECK`
   - `DOC CHECK`
   - `PLACEMENT CHECK`
3. A replacement classification method is now mandatory before enriching Engine A/B:
   - `ENGINE_LOCAL_SEMANTICS`
   - `TRANSVERSAL_SHARED_SEAM`
   - `OBSERVABILITY_ONLY`
   - `GOVERNANCE_ONLY`
   - `USER_DECISION_REQUIRED`
4. C/D are restricted to engineering-quality reference use, not semantic-template use.
5. A/B semantic patches now require an explicit pre-patch checklist.

## Tests and Proof

- Root prompt inspected before patch.
- Existing Engine B folder scanned before considering further code work.
- No new `.py` created in this slice.

## Deferred / Not Done

- No engine code changed in this slice.
- The next engine-level slice still requires a classified semantic gap before implementation.

## Risks / Open Questions

- This patch hardens method, not runtime behavior by itself.
- The next A/B semantic slice must still prove whether the missing richness is local or transversal.

## Completion Status

`COMPLETE`

## Next Safe Step

Run the next Engine A/B slice using the new classification method and stop for user arbitration if the gap is semantically ambiguous.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-19_sprint_30_codex_3day_mathgates_ratelimiter.md

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


---

## Source: docs/production_deployment_plan/update_audit/2026-04-19_sprint_31_codex_6day_travail_critique_suite_sprint_30.md

# Sprint 31 — Codex 6-day coding plan — TRAVAIL CRITIQUE (suite Sprint 30)

> **Date** : 2026-04-19
> **Suite de** : `2026-04-19_sprint_30_codex_3day_mathgates_ratelimiter.md`
> **Auteur plan** : Opus (planification, 6 casquettes PhD)
> **Acteur code** : Codex
> **Durée** : 6 jours × 1 session 5h = **30 h de codage concentré**
> **Format workflow** : Opus plan md → Codex code → Opus audit checklist → user corrige ici
> **Gouvernance mandatée** : R-QUANT-FIRST (doc 28 §2bis), Carver/Narang/Taleb/Harvey-Liu-Zhu, Canon V5.3 (engines A/B/C/D canoniques, **une seule solution complète**, chaîne calibration progressive **backtest → shadow → micro-live → live**), no 1990s TA

---

## 0. Objectif une phrase

Fermer **tout** le chemin critique pré-MICRO_LIVE : compléter les deferrals du S30 (Hansen SPA full, shadow_gate_check full), fermer le reste des P1/P2 (testnet, signal handlers, god files split protocols/, VPS runbook Linux, log rotation, CI, duplication governed_extensions), en 6 sessions bornées de 5h.

---

## 1. Réponse 6 casquettes PhD

### 1.1 Pilote PhD (stratégie & priorisation)

**Constat après Sprint 30** : les 5 tests gates math sont codés, le seam risk_runtime est câblé, le rate limiter Binance existe, `shadow_gate_check.py` a un skeleton. Le premier gate Shadow G2.1 est techniquement produisable avec données réelles.

**Mais** : 5 blockers restants avant d'aller en **MICRO_LIVE** (tick réel avec capital €300-400) :

1. **Hansen SPA complet** (W-13) — nécessaire pour G2.2 (2e mois shadow, déflation Sharpe multi-stratégies)
2. **shadow_gate_check.py production-ready** (W-15) — rapport JSON signable par humain
3. **Testnet integration** (W-18) — preuve que l'adapter Binance soumet des ordres réels au testnet sans crash
4. **Signal handlers SIGTERM/SIGINT** (z ai audit P1) — sans ça, un `kill` VPS laisse des positions orphelines
5. **Split god files protocols/** — `shadow_runtime.py` 1722L, `live_light_runtime.py` 1481L, `micro_live_runtime.py` 1176L : illisibles, risque de bug caché critique

**Chemin critique Sprint 31** :
```
[Day 1 W-13 Hansen SPA]
       ↓
[Day 2 W-15 shadow_gate_check full]  ← G2.1 signable (pas juste produisable)
       ↓
[Day 3 W-18 testnet + signal handlers]  ← MICRO_LIVE safety-net
       ↓
[Day 4-5 split protocols/ god files]  ← code audit-ready
       ↓
[Day 6 VPS runbook + log rotation + CI + bugs z ai résiduels]
```

**Ce qu'on ne fait PAS dans S31** :
- W-16 partial fill handling → demande spec Opus d'abord (sera doc 31, séparé)
- W-19 **spec complète** VPS : on fait le **runbook exécutable** (scripts), pas la spec architecturale étendue
- Split des god files `scripts/*` (2030L, 2029L) — hors runtime trading, baseliner
- Split de `ui/technical_dashboard_*` (>1900L) — UI non critique, baseliner + fixer juste la duplication governed_extensions
- 39 `except Exception` → audit ciblé, pas rewrite massif (reporté S32)
- 27 `type: ignore` → revue ciblée (reporté S32)

### 1.2 Quant PhD (rigueur mathématique)

**W-13 Hansen SPA full** — seule tâche math du sprint.

**Formule complète** :
$$t^{\text{SPA}} = \max_{k=1,\ldots,M} \frac{\sqrt{n}\bar{d}_k}{\hat{\omega}_k}$$

avec :
- $\bar{d}_k = \frac{1}{n}\sum_{t=1}^n d_{k,t}$ la différence moyenne de loss entre stratégie $k$ et benchmark
- $\hat{\omega}_k^2$ variance stationary bootstrap de $\sqrt{n}\bar{d}_k$ (Politis-Romano — déjà dispo dans `bootstrap.py`)
- p-value via **stationary bootstrap** $B=1000$ replications, correction des trois versions Hansen (lower, consistent, upper)

**Référence** : Hansen, P. R. (2005). "A Test for Superior Predictive Ability." *Journal of Business & Economic Statistics*, 23(4), 365-380. DOI: `10.1198/073500105000000063`.

**Test paper_repro** :
- Dataset synthétique : 5 stratégies toutes pires que benchmark (tirage $N(-0.1, 1)$, n=250) → p-value SPA > 0.5 (on ne rejette pas H0 : benchmark optimal)
- 1 stratégie meilleure (+0.3 mean) + 4 pires → p-value SPA < 0.05 (rejet H0)
- Reproduire (approximativement) Hansen 2005 Table 2 : comparaison vs White Reality Check

**Validation W-21 bonus** — DSR multi-engine N=4 :
- Bailey-López de Prado 2014, *Journal of Portfolio Management* 40(5), 94-107. DOI: `10.3905/jpm.2014.40.5.094`
- Table 1 donne des valeurs pour N=1, N=10, N=100, N=1000
- On vérifie N=4 par interpolation + formule exacte (pas par valeur directe du paper)
- Input : SR_max=2.0, T=250, skew=-1, kurt=6, variance_SR_estimée
- Output attendu : DSR entre valeurs Bailey-LdP Table 1 pour N=1 (0.9866) et N=10 (~0.945) → interpolation N=4 ≈ 0.97 ± 0.01

**Interdits** :
- ❌ Pas de `scipy.stats.*` pour SPA (pas d'implémentation standard disponible)
- ❌ Pas de p-value asymptotique normale — impérativement **stationary bootstrap** (dépendance série)

### 1.3 Tradeur PhD (microstructure réaliste)

**W-18 Testnet Binance integration** — blocker MICRO_LIVE.

**Scope** :
- `tests/test_venue_adapters/test_integration_testnet.py` (nouveau fichier, marqué `@pytest.mark.testnet` — skip sans creds env var)
- **Auth** : test que `credential_loader.py` lit les creds testnet depuis `BINANCE_TESTNET_API_KEY` / `BINANCE_TESTNET_SECRET` (env vars, pas de fichier)
- **Order submit → cancel** : soumission limit buy very low price (pas de fill), puis cancel → assertion ordre cancelé
- **Balance query** : `GET /api/v3/account` → retourne un dict avec balances
- **Server time sync** : `GET /api/v3/time` → assertion écart < 5000ms
- **Rate limit observation** : après les 3 requêtes ci-dessus, `api_weight_tracker.get_state()` rapporte un used_weight > 0

**Creds** : documentation dans `docs/production_deployment_plan/update_audit/testnet_setup.md` (à créer dans D3).
- URL testnet : `https://testnet.binance.vision`
- Clés générées manuellement par user sur https://testnet.binance.vision/ — **pas d'automation**
- Env vars **PAS committés** (règle `.env` in `.gitignore`)

**Si pas de creds testnet dispo** : le test skip (pas de fail). CI doit passer même sans creds.

**Signal handlers SIGTERM/SIGINT (z ai audit P1)** :
- Ajouter dans `src/protocols/shadow_runtime.py`, `src/protocols/live_light_runtime.py`, `src/protocols/micro_live_runtime.py`
- Pattern :
  ```python
  import signal

  def _graceful_shutdown_handler(signum, frame):
      logger.warning("signal_received", signal=signum)
      runtime.request_shutdown()  # flag → boucle exit propre
      # NE PAS sys.exit() ici — laisser la boucle finir son tour
  ```
- Au `run()` du runtime : `signal.signal(signal.SIGTERM, handler)` + `signal.signal(signal.SIGINT, handler)`
- **Test** : envoyer SIGTERM via subprocess + vérifier arrêt propre + aucune position orpheline

**Partial fill (W-16)** : **hors scope**. Notes : à lire depuis `order_translator.py` status WebSocket, mais logique métier (réouverture partielle vs annulation) demande décision humaine D-19 → sera spec séparée.

### 1.4 Python Developer PhD (qualité code)

**Split god files protocols/** — règle stricte :

1. **Ne PAS changer** la logique métier (refactor pur mécanique)
2. **Préserver** les imports publics : `from protocols.shadow_runtime import ShadowRuntime` doit continuer de marcher (via `__init__.py` ré-export ou conservation du nom dans le fichier principal)
3. **Découper par axe fonctionnel** (pas arbitraire par "ligne 500") :
   - `shadow_runtime.py` (1722L) → `shadow_runtime.py` (main loop, <700L) + `shadow_runtime_calibration.py` (pull artefacts calibration) + `shadow_runtime_metrics.py` (métriques exposées) + `shadow_runtime_refusals.py` (logique RefusalJournal)
   - `live_light_runtime.py` (1481L) → `live_light_runtime.py` (<700L) + `live_light_runtime_state_machine.py` (transitions) + `live_light_runtime_guardrails.py` (circuit breakers)
   - `micro_live_runtime.py` (1176L) → `micro_live_runtime.py` (<700L) + `micro_live_runtime_sizing.py` (tier capital €300-400) + `micro_live_runtime_observability.py`

4. **Tests runtime existants passent sans modification** (pas de changement d'API publique)

5. **Chaque nouveau sibling** a :
   - `from __future__ import annotations`
   - Docstring module expliquant le split ("Extracted from `shadow_runtime.py` in Sprint 31 — <raison>")
   - Pas de cross-import circulaire (dagvalidator doit passer)

**Anti-pattern à éviter** :
- ❌ Créer `shadow_runtime_utils.py` — nom vague, interdit
- ❌ Mettre toutes les classes privées dans un seul sibling — casse le SRP
- ❌ Toucher `execution_backbone/execution_runtime.py` (1238L) ce sprint — reporté

**Shadow_gate_check.py full (W-15)** :
- CLI : `python -m scripts.shadow_gate_check --run-id <id> --window-days 30 --input <path> --output <json>`
- Structure JSON conforme doc 14 §12 (tous les champs renseignés, pas de `null` pour champs mandatoires)
- Appelle réellement : `psr`, `ks_test`, `energy_distance`, `mann_kendall`, `hansen_spa`, `dsr` via imports canoniques
- Génère aussi :
  - Section `refusal_analysis` (compte les RefusalJournal events du run)
  - Section `capital_usage` (tier cap respecté)
  - Section `execution_stats` (fill rate, slippage moyen, spread paid)
- 3 tests e2e :
  - Données synthétiques → JSON schema valid + toutes sections renseignées
  - Cas "échec PSR" → `gate_status: "fail"` + `reasons` listé
  - Cas "succès" → `gate_status: "pass"` + tous seuils respectés

### 1.5 Prod Safe (no-surprise, rollback, monitoring)

**W-19 VPS runbook Linux — focus exécutable, pas spec architecturale** :

Livrables concrets (pas des .md descriptifs) :
1. `scripts/vps/install_python.sh` — installe Python 3.13 sur Ubuntu 24.04 (idempotent, testé en chroot ou VM snapshot)
2. `scripts/vps/deploy_shadow_service.sh` — crée le service systemd `v53-shadow.service`, enable, démarre
3. `config/systemd/v53-shadow.service` — unit file (User, WorkingDirectory, ExecStart, Restart=on-failure, StandardOutput=journal)
4. `scripts/vps/rotate_logs.sh` — cron daily, archive + compress + delete >30j (THR-I03)
5. `scripts/vps/health_check.sh` — vérifie service up, dernier log <60s, disk >10GB, retourne exit code 0/1
6. `scripts/vps/rollback_calibration.sh` — prend un version_id en arg, rsync artefact + systemctl restart
7. `docs/production_deployment_plan/19_VPS_DEPLOYMENT_RUNBOOK.md` — UPDATE (pas création) : documente chaque script en 1 paragraphe + ordre d'exécution

**W-20 log rotation** — intégré dans `scripts/vps/rotate_logs.sh` + wire Python logging handler `RotatingFileHandler` si pas déjà en place (vérifier `src/logging_config.py` ou équivalent).

**W-23 CI minimal** :
- `Makefile` à la racine du repo :
  ```make
  .PHONY: test lint typecheck guards all

  test:
  	pytest -q

  lint:
  	ruff check src/ tests/ scripts/

  typecheck:
  	mypy src/

  guards:
  	python -m engineering_guardrails

  all: lint typecheck test guards
  ```
- `.github/workflows/ci.yml` (pas de prod en prem, mais smoke test local OK) :
  - Triggers : push main + PR
  - Steps : checkout → setup Python 3.13 → pip install → `make all`
  - Note : skip job si `[skip ci]` dans le commit message

**W-24 Startup readiness sequence spec** — pas un code, mais 1 section dans `docs/production_deployment_plan/07_PHASE_PLAN_0_TO_4.md` :
- Ordre de boot : `calibration_loader` → `regime_classifier` → `engines` → `gatekeeper` → `venue_adapter` → `execution_runtime`
- Chaque stage a un health check (retourne ready/not_ready)
- Boot fails fast si un stage n'est pas ready en 30s

**W-25 Rollback calibration** — intégré dans `rollback_calibration.sh` ci-dessus + 1 section doc 12 §6.3 (nouvelle).

**Fix z ai bugs résiduels** :
- Duplication `governed_extensions` dans `src/ui/technical_dashboard_view.py` → supprimer 1 des 2 cards (garder la section "System", supprimer celle de "Extensions" qui fait doublon)
- Test : charge la vue, vérifie que `governed_extensions` apparaît **exactement 1 fois** dans le DOM

**Coupure d'urgence** : si Day 4 split `shadow_runtime.py` casse un test runtime, **STOP split**, revert, retour Opus pour re-spec.

### 1.6 Génie Logiciel PhD (architecture)

**Principes split god files** :
- Pattern **composition over inheritance** : les siblings exposent des **fonctions pures** ou **dataclass services**, le fichier principal les compose
- **Pas de cycle** : `shadow_runtime_calibration.py` importe depuis `calibration_loader/`, mais `shadow_runtime.py` importe `shadow_runtime_calibration` (one-way)
- **Naming convention** : `<parent>_<aspect>.py` (pas de `<parent>_utils.py` ni `<parent>_helpers.py`)
- **`__init__.py`** : ré-exports publics inchangés (`from .shadow_runtime import ShadowRuntime` reste valide)

**Pattern split type** (pour `shadow_runtime.py`) :

```python
# src/protocols/shadow_runtime.py (< 700L après split)
from __future__ import annotations

from protocols.shadow_runtime_calibration import pull_shadow_calibration
from protocols.shadow_runtime_metrics import ShadowMetrics
from protocols.shadow_runtime_refusals import RefusalRecorder

class ShadowRuntime:
    def __init__(self, ...):
        self._calibration = pull_shadow_calibration(...)
        self._metrics = ShadowMetrics(...)
        self._refusals = RefusalRecorder(...)
        # main loop logic only
```

**CI gates ajoutés Sprint 31** :
- `dag_validator` : détecte cycle
- `engineering_guardrails` : tous les nouveaux fichiers < 700L (src/ only), new_violations=0
- `pytest tests/test_protocols/ -q` : **tous** les 444 tests doivent passer **sans modification** (refactor mécanique pur)

**DAG attendu après S31** :
```
src/protocols/
├── shadow_runtime.py                    [split, < 700L]
├── shadow_runtime_calibration.py        [NEW]
├── shadow_runtime_metrics.py            [NEW]
├── shadow_runtime_refusals.py           [NEW]
├── live_light_runtime.py                [split, < 700L]
├── live_light_runtime_state_machine.py  [NEW]
├── live_light_runtime_guardrails.py     [NEW]
├── micro_live_runtime.py                [split, < 700L]
├── micro_live_runtime_sizing.py         [NEW]
├── micro_live_runtime_observability.py  [NEW]
└── contracts.py                          [UNCHANGED — split reporté S32]

src/ui/
└── technical_dashboard_view.py          [governed_extensions dup fix, size NOT addressed]

calibration_methods/
└── hansen_spa.py                         [COMPLETED — was skeleton S30]

scripts/
├── shadow_gate_check.py                  [COMPLETED — was skeleton S30]
└── vps/
    ├── install_python.sh                 [NEW]
    ├── deploy_shadow_service.sh          [NEW]
    ├── rotate_logs.sh                    [NEW]
    ├── health_check.sh                   [NEW]
    └── rollback_calibration.sh           [NEW]

config/systemd/
└── v53-shadow.service                    [NEW]

tests/test_venue_adapters/
└── test_integration_testnet.py           [NEW, @pytest.mark.testnet]

.github/workflows/
└── ci.yml                                [NEW]

Makefile                                   [NEW]

docs/production_deployment_plan/
├── 07_PHASE_PLAN_0_TO_4.md               [UPDATED: startup readiness §X]
├── 12_LOCAL_LAB_VS_VPS_SEPARATION.md     [UPDATED: rollback §6.3]
└── 19_VPS_DEPLOYMENT_RUNBOOK.md          [UPDATED: documente scripts vps/]
```

---

## 2. Plan jour par jour

### DAY 1 (5h) — Hansen SPA full + DSR multi-engine validation

| Slot | Heure | Tâche | Livrable |
|---|---|---|---|
| D1-1 | 0:00-1:30 | **W-13 Hansen SPA** : implémentation complète (stationary bootstrap, 3 versions lower/consistent/upper, p-value) | `hansen_spa.py` (<300L, pas skeleton) |
| D1-2 | 1:30-2:30 | **W-13 Tests paper_repro** : Hansen 2005 Table 2 approche + 5 strats pires + 1 strat meilleure | `test_hansen_spa_paper_repro.py` (3 tests) |
| D1-3 | 2:30-3:30 | **W-21 DSR N=4** : test vs Bailey-LdP 2014 Table 1 interpolation | `test_dsr_multiengine.py` (2 tests : N=1 exact + N=4 interpolation) |
| D1-4 | 3:30-4:30 | **Integration** : `shadow_gate_check.py` appelle réellement `hansen_spa` (retire le TODO) | `shadow_gate_check.py` updated |
| D1-5 | 4:30-5:00 | **Audit local** : pytest + guardrails + dag_validator | proofs 3 lignes |

**Gate Day 1** : `pytest tests/test_calibration_methods/ -q` passe + `hansen_spa.py` >50L et <300L + dag_validator pass.

### DAY 2 (5h) — shadow_gate_check.py full + JSON schema

| Slot | Heure | Tâche | Livrable |
|---|---|---|---|
| D2-1 | 0:00-1:00 | **W-15 Sections rapport** : `refusal_analysis`, `capital_usage`, `execution_stats` implémentées (lecture depuis RefusalJournal + daily_pnl_breaker state + execution logs) | `shadow_gate_check.py` étoffé |
| D2-2 | 1:00-2:00 | **W-15 JSON schema** : créer `schemas/shadow_gate_report.schema.json` (JSON Schema Draft-7) conforme doc 14 §12 | `shadow_gate_report.schema.json` + helper `validate_report()` |
| D2-3 | 2:00-3:30 | **W-15 Tests e2e** : 3 tests (synthetic pass, synthetic fail PSR, synthetic fail hansen_spa) | `test_shadow_gate_check_e2e.py` |
| D2-4 | 3:30-4:30 | **W-15 CLI polish** : args parsing robuste, exit codes (0=pass, 1=fail, 2=error), help text | CLI améliorée + doctest dans docstring |
| D2-5 | 4:30-5:00 | **Audit local** : exécuter le CLI sur fixture réelle issue du dernier shadow run (si dispo) | JSON stdout attaché dans logs |

**Gate Day 2** : `python -m scripts.shadow_gate_check --run-id test --input fixtures/ --output /tmp/r.json` → exit 0, JSON valide schema.

### DAY 3 (5h) — Testnet integration + signal handlers + duplication fix

| Slot | Heure | Tâche | Livrable |
|---|---|---|---|
| D3-1 | 0:00-2:00 | **W-18 Testnet test** : `test_integration_testnet.py` avec auth + order submit/cancel + balance + server time + weight observation | test file + docstring setup creds testnet |
| D3-2 | 2:00-2:30 | **W-18 Doc setup** : `docs/production_deployment_plan/update_audit/testnet_setup.md` (créer compte, env vars, run test) | doc |
| D3-3 | 2:30-4:00 | **Signal handlers** : ajouter `_graceful_shutdown_handler` dans les 3 runtimes (shadow, live_light, micro_live) + `request_shutdown()` flag | 3 modifs + 3 tests subprocess |
| D3-4 | 4:00-4:30 | **Fix duplication `governed_extensions`** : supprimer 1 des 2 cards dans `technical_dashboard_view.py` (garder "System", supprimer "Extensions") | diff +0 -N (N=taille de la card supprimée) |
| D3-5 | 4:30-5:00 | **Audit local** : pytest + guardrails | proofs |

**Gate Day 3** : testnet test skip OK sans creds + 3 signal handler tests pass + governed_extensions apparaît 1 fois dans DOM.

### DAY 4 (5h) — Split `shadow_runtime.py` (1722L → 3 siblings)

| Slot | Heure | Tâche | Livrable |
|---|---|---|---|
| D4-1 | 0:00-0:30 | **Analyse** : cartographier les 1722L en 4 axes (main loop, calibration pull, metrics, refusals) | commentaires inline dans fichier original |
| D4-2 | 0:30-1:30 | **Extract `shadow_runtime_calibration.py`** : fonctions `pull_shadow_calibration`, `validate_artifact_fresh`, etc. | nouveau fichier (<400L) |
| D4-3 | 1:30-2:30 | **Extract `shadow_runtime_metrics.py`** : classe `ShadowMetrics`, compteurs, exposition Prometheus | nouveau fichier (<400L) |
| D4-4 | 2:30-3:30 | **Extract `shadow_runtime_refusals.py`** : `RefusalRecorder`, traductions refusal code → journal | nouveau fichier (<300L) |
| D4-5 | 3:30-4:30 | **Résiduel `shadow_runtime.py`** : main loop uniquement, imports depuis siblings | fichier <700L |
| D4-6 | 4:30-5:00 | **Audit** : `pytest tests/test_protocols/test_shadow_runtime*.py -q` + dag_validator + guardrails new_violations=0 | proofs |

**Gate Day 4** : `pytest tests/test_protocols/ -q` → **444 tests still passing** (aucune régression) + shadow_runtime.py < 700L + 0 cycle import.

### DAY 5 (5h) — Split `live_light_runtime.py` + `micro_live_runtime.py`

| Slot | Heure | Tâche | Livrable |
|---|---|---|---|
| D5-1 | 0:00-1:00 | **Split `live_light_runtime.py` (1481L)** : extract state machine + guardrails | 2 nouveaux siblings + principal <700L |
| D5-2 | 1:00-2:00 | Tests `live_light_runtime` passent | pytest green |
| D5-3 | 2:00-3:00 | **Split `micro_live_runtime.py` (1176L)** : extract sizing + observability | 2 nouveaux siblings + principal <700L |
| D5-4 | 3:00-4:00 | Tests `micro_live_runtime` passent | pytest green |
| D5-5 | 4:00-4:30 | **Baseline `scripts/run_*_dashboard.py` et `ui/technical_dashboard_*.py`** : ajout dans `engineering_guardrails_baseline.json` (pattern `FILE_TOO_LONG`, UI non-runtime) — documentés dans un comment `# reason: UI rendering code, not trading runtime` | baseline JSON updated |
| D5-6 | 4:30-5:00 | **Audit global protocols/** : confirmer aucun fichier `src/protocols/*.py` ne dépasse 700L | guardrails report |

**Gate Day 5** : 5 nouveaux siblings, tous les tests protocols/ verts (444/444), dag_validator pass, pas de nouveau FILE_TOO_LONG dans src/.

### DAY 6 (5h) — VPS scripts Linux + Makefile CI + docs update

| Slot | Heure | Tâche | Livrable |
|---|---|---|---|
| D6-1 | 0:00-1:00 | **W-19 `install_python.sh` + `deploy_shadow_service.sh`** (idempotent, shellcheck clean) | 2 scripts + 1 unit file |
| D6-2 | 1:00-1:30 | **W-19 `health_check.sh` + `rollback_calibration.sh`** | 2 scripts |
| D6-3 | 1:30-2:00 | **W-20 `rotate_logs.sh`** + wire `RotatingFileHandler` in `logging_config.py` | script + Python patch |
| D6-4 | 2:00-2:30 | **W-23 `Makefile`** (test/lint/typecheck/guards/all) | Makefile |
| D6-5 | 2:30-3:00 | **W-23 `.github/workflows/ci.yml`** | workflow YAML |
| D6-6 | 3:00-3:30 | **W-24 Doc startup readiness** section ajoutée dans `07_PHASE_PLAN_0_TO_4.md` | doc patch |
| D6-7 | 3:30-4:00 | **W-25 Doc rollback calibration** section §6.3 dans `12_LOCAL_LAB_VS_VPS_SEPARATION.md` | doc patch |
| D6-8 | 4:00-4:30 | **Doc `19_VPS_DEPLOYMENT_RUNBOOK.md`** : documente chaque script en 1 paragraphe | doc updated |
| D6-9 | 4:30-5:00 | **Audit global sprint** : `make all` → tous verts + `git diff --stat` scope check | proofs finaux sprint |

**Gate Day 6** : `make all` exit 0 + shellcheck clean sur scripts/vps/ + 5 scripts exécutables + CI workflow présent.

---

## 3. Acceptance critères par tâche

### W-13 Hansen SPA (complet)
- [ ] `hansen_spa.py` 150-300L, NotImplementedError supprimé
- [ ] Utilise `bootstrap.py` stationary bootstrap (pas re-implémenté)
- [ ] 3 tests paper_repro : null case (p>0.5), alternative case (p<0.05), hansen table 2 approximate
- [ ] Expose 3 variantes : `spa_lower`, `spa_consistent`, `spa_upper`
- [ ] Docstring inclut DOI `10.1198/073500105000000063`
- [ ] Appelé par `shadow_gate_check.py` (remplace TODO skeleton)

### W-21 DSR multi-engine
- [ ] Test N=1 exact vs formule papers
- [ ] Test N=4 interpolation entre valeurs Bailey-LdP Table 1 N=1 et N=10
- [ ] Tolérance documentée

### W-15 shadow_gate_check.py full
- [ ] 3 sections JSON : `refusal_analysis`, `capital_usage`, `execution_stats` réellement calculées
- [ ] `schemas/shadow_gate_report.schema.json` existe et valide
- [ ] 3 tests e2e (pass / fail PSR / fail Hansen SPA)
- [ ] CLI exit codes : 0 pass, 1 fail gate, 2 error
- [ ] `--help` texte complet

### W-18 Testnet integration
- [ ] `test_integration_testnet.py` avec `@pytest.mark.testnet`
- [ ] Skip propre si env vars absentes (pas de fail)
- [ ] 5 assertions : auth OK, order submit OK, cancel OK, balance ≥0, server time delta <5s
- [ ] Doc setup creds dans `update_audit/testnet_setup.md`

### Signal handlers
- [ ] 3 runtimes patches : shadow, live_light, micro_live
- [ ] `request_shutdown()` flag stoppe la boucle proprement (pas de sys.exit immédiat)
- [ ] 3 tests subprocess : spawn runtime → send SIGTERM → attend exit 0 en <10s
- [ ] Log INFO `signal_received` avant shutdown

### Fix `governed_extensions` duplication
- [ ] `grep 'governed_extensions' src/ui/technical_dashboard_view.py` = 1 occurrence de card (plusieurs refs data OK, 1 seule card DOM)
- [ ] Test DOM (si infra dispo) : render view → count = 1

### Split protocols/
- [ ] `shadow_runtime.py` < 700L
- [ ] `live_light_runtime.py` < 700L
- [ ] `micro_live_runtime.py` < 700L
- [ ] 7 nouveaux siblings (shadow_*3, live_light_*2, micro_live_*2)
- [ ] `from protocols.shadow_runtime import ShadowRuntime` continue de marcher
- [ ] Tous tests `tests/test_protocols/` passent sans modification (444/444)
- [ ] dag_validator : 0 cycle
- [ ] Chaque nouveau sibling a docstring module expliquant l'extraction

### VPS scripts
- [ ] `shellcheck scripts/vps/*.sh` exit 0
- [ ] Tous scripts idempotents (tournent 2× sans erreur)
- [ ] `v53-shadow.service` valide (`systemd-analyze verify`, simulable)
- [ ] Doc 19 mise à jour, pas recréée

### Makefile + CI
- [ ] `make test` / `make lint` / `make typecheck` / `make guards` / `make all` tous exit 0
- [ ] `.github/workflows/ci.yml` valide syntax YAML
- [ ] CI trigger : push main + PR + skip-ci marker

---

## 4. Tests and proof (slots à remplir par Codex par Day)

```
### Day 1 proof
- pytest tests/test_calibration_methods/ -q → [SLOT: X passed]
- cat src/calibration_methods/hansen_spa.py | wc -l → [SLOT: ?L]
- git diff --stat (in-scope) → [SLOT: ...]
- engineering_guardrails new_violations → [SLOT: 0]

### Day 2 proof
- pytest tests/test_scripts/test_shadow_gate_check*.py -q → [SLOT]
- python -m scripts.shadow_gate_check --run-id smoke --input fixtures/ --output /tmp/r.json; echo $? → [SLOT: 0]
- jsonschema -i /tmp/r.json schemas/shadow_gate_report.schema.json → [SLOT: valid]
- git diff --stat → [SLOT]
- guardrails → [SLOT: 0]

### Day 3 proof
- pytest tests/test_venue_adapters/ -q → [SLOT]
- pytest tests/test_protocols/ -k "signal or shutdown" -q → [SLOT]
- grep -c 'DashboardCard.*governed_extensions' src/ui/technical_dashboard_view.py → [SLOT: 1]
- guardrails → [SLOT: 0]

### Day 4 proof
- pytest tests/test_protocols/test_shadow_runtime*.py -q → [SLOT: N passed]
- wc -l src/protocols/shadow_runtime*.py → [SLOT all <700]
- python -m dag_validator → [SLOT: pass]
- guardrails → [SLOT: 0]

### Day 5 proof
- pytest tests/test_protocols/ -q → [SLOT: 444 passed]
- wc -l src/protocols/live_light_runtime*.py src/protocols/micro_live_runtime*.py → [SLOT all <700]
- python -m dag_validator → [SLOT: pass]
- guardrails → [SLOT: 0]

### Day 6 proof
- shellcheck scripts/vps/*.sh → [SLOT: 0]
- systemd-analyze verify config/systemd/v53-shadow.service → [SLOT: 0]
- make all → [SLOT: 0]
- git diff --stat (full sprint) → [SLOT]
- guardrails → [SLOT: 0]
```

---

## 5. Deferred / Not done (explicite Sprint 31)

Ne **PAS** faire dans ce sprint (sinon STOP + Dispute) :

- **W-16 partial fill** — besoin Opus spec préalable (doc 31 à créer séparé)
- Split `execution_backbone/execution_runtime.py` (1238L) — reporté S32
- Split `monitoring/contracts.py` (1299L) + `protocols/contracts.py` (1280L) — reporté S32 (contracts = haute criticité, split demande plus de temps)
- Split `scripts/run_technical_dashboard.py` (2030L) + `scripts/run_local_lab_analysis_bundle.py` (2029L) — baselined FILE_TOO_LONG (non-runtime)
- Split `ui/technical_dashboard_*.py` (>1900L) — baselined (UI)
- 39 `except Exception` → spécialisation reportée S32
- 27 `type: ignore` → revue reportée S32
- W-18 **production** credentials Binance — testnet only
- Toute modification `src/engines/` hors bug fixes signalés
- Création nouvel engine hors A/B/C/D ou nouveau stade runtime hors backtest/shadow/micro-live/live (canon V5.3 interdit — une seule solution complète)

---

## 6. Risks

| Risque | Prob | Impact | Mitigation |
|---|---|---|---|
| Hansen SPA p-value bootstrap O(B×M×n) trop lente (n=250, M=5, B=1000) | Medium | Low | 1.25M ops numpy vectorisé → <1s. Si lent, chunked bootstrap |
| Split `shadow_runtime.py` casse un test runtime | High | High | Refactor **mécanique pur** : copier-coller logique, changer juste imports. Exécuter pytest après chaque extract. STOP si rouge |
| Testnet Binance creds absents → CI fail | Low | Low | `@pytest.mark.testnet` skip propre, CI pass sans creds |
| Signal handler avec boucle `while True` bloquée sur `socket.recv` | Medium | Medium | Timeout sur WS + check `shutdown_requested` à chaque iteration |
| VPS scripts non testables en CI (pas de VM Ubuntu) | High | Low | `shellcheck` + manual validation dans runbook, test réel lors du déploiement |
| governed_extensions fix casse dashboard render | Low | Medium | Test DOM avant/après, vérifier 1 seule card reste cohérente (section "System" est le bon keeper d'après z ai audit) |
| Day 4-5 refactor volume (1722+1481+1176=4379L déplacés) | High | Medium | Strict 1 extract = 1 commit. Si Day 4 dépasse, couper à 2 siblings shadow (calibration + metrics), refusals en Day 5 |
| Doc updates oubliés (07, 12, 19) | Medium | Low | Day 6 dédie 1h30 aux docs, ordre explicite D6-6/7/8 |

---

## 7. Opus audit checklist (par Day)

### Checklist structure (Pilote + Génie Log)
- [ ] Chaque Day a son proof block rempli (pytest + diff + guardrails)
- [ ] Aucune modification hors scope (vérifier `git diff --stat`)
- [ ] Deferred items restent deferred
- [ ] dag_validator : 0 cycle (surtout Day 4-5)

### Checklist math (Quant — Day 1 seulement)
- [ ] Hansen SPA utilise **stationary bootstrap** (pas i.i.d.)
- [ ] DOI Hansen 2005 présent
- [ ] Test paper_repro reproduit une valeur nommée (pas juste "is positive")
- [ ] p-value calculée correctement (rang de t_obs dans distribution bootstrap)

### Checklist trader (Day 3 + 6)
- [ ] Testnet test skip propre sans creds (pas de fail)
- [ ] Signal handlers sur **tous** les runtimes trading (shadow + live_light + micro_live)
- [ ] VPS scripts idempotents (rerun safe)
- [ ] Rollback script prend un version_id en arg, pas hardcodé

### Checklist code (Python PhD — tous Days)
- [ ] Chaque nouveau fichier `from __future__ import annotations`
- [ ] Pas de print() nouveau dans src/
- [ ] ruff check clean
- [ ] mypy clean
- [ ] Chaque nouveau fichier <700L (src/)

### Checklist prod safe
- [ ] Signal handlers ne font pas sys.exit() immédiat
- [ ] Rotate logs ne supprime pas les logs du jour courant
- [ ] VPS service a Restart=on-failure
- [ ] Rollback a dry-run mode

### Checklist doc
- [ ] Doc 07 updated (startup readiness)
- [ ] Doc 12 updated (§6.3 rollback)
- [ ] Doc 19 updated (pas recréé)
- [ ] Doc update_audit/testnet_setup.md créé

---

## 8. Completion status (slot fin de Day 6)

```
Status: [SLOT: COMPLETE | PARTIAL | BLOCKED]
Items delivered:
  - W-13 Hansen SPA full: [x]
  - W-21 DSR multi-engine test: [x]
  - W-15 shadow_gate_check full: [x]
  - W-18 testnet integration: [x]
  - Signal handlers (3 runtimes): [x]
  - Fix governed_extensions duplication: [x]
  - Split shadow_runtime.py: [x]
  - Split live_light_runtime.py: [x]
  - Split micro_live_runtime.py: [x]
  - VPS scripts (5): [x]
  - Makefile + CI: [x]
  - Doc updates (07, 12, 19, testnet_setup): [x]

Items deferred per plan: W-16, split execution_runtime/contracts, splits UI/scripts (baselined), 39 except Exception, 27 type:ignore

pytest: [SLOT: X passed (Y new)]
new_violations: 0
```

---

## 9. Next safe step après S31

1. Opus audit final : GREENLIGHT ou REQUEST_FIX
2. Corrections user si REQUEST_FIX
3. Décision deployment : shadow VPS peut démarrer (gate G1) → run 1 mois → G2.1
4. **Sprint 32 plan** :
   - Spec W-16 partial fill (doc 31, Opus-led)
   - Split `execution_backbone/execution_runtime.py` + contracts (monitoring + protocols)
   - Specialize 39 except Exception
   - Review 27 type:ignore
   - MICRO_LIVE préparation (capital €300-400)

---

## 10. Governance crosscheck

| Règle | Respect |
|---|---|
| R-QUANT-FIRST | ✅ seul W-13 est math, a DOI + paper_repro (3 tests) |
| Canon V5.3 (A/B/C/D, solution unique) | ✅ aucun nouvel engine, aucun nouveau stade runtime (chaîne backtest → shadow → micro-live → live préservée) |
| No 1990s TA | ✅ pas de changement indicateurs |
| Capital reality | ✅ W-18 testnet seulement, micro_live_runtime_sizing.py respecte tier |
| File size 700 src/ | ✅ Day 4-5 dédiés au split |
| File size test (règle user 2026-04-19) | ✅ tests peuvent être baselined si >700 (jamais src/) |
| Workflow Opus→Codex→Opus | ✅ plan Opus, exec Codex, audit Opus par Day |
| COMPLETE proof | ✅ §4 chaque Day exige 3 lignes |
| Sessions 5h | ✅ chaque Day borné à 5h dans §2 |
| Suite logique Sprint 30 | ✅ ouvre par closure deferrals S30 (Day 1-2) |

---

**Fin du plan Sprint 31 — 6 jours Codex travail critique (suite Sprint 30).**


