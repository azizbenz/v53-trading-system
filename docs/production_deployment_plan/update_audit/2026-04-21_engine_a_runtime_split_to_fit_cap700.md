# FU-1 — Split `engine_a_runtime.py` 711L → <700L

**Date** : 2026-04-21  
**Auteur spec** : Opus élevé  
**Exécutant** : Codex  
**Durée estimée** : ~2h  
**Déclencheur** : `engineering_guardrails` `FILE_TOO_LONG` `src/engines/engine_a/engine_a_runtime.py:1 711L>700`  

---

## §1 Objectif

Ramener `src/engines/engine_a/engine_a_runtime.py` **sous 700 lignes** par extraction chirurgicale des trois fonctions de construction du candidat de scoring vers un nouveau module `engine_a_scoring_candidate_builder.py`.

**Règle CLAUDE.md §3** : `src/` jamais baseliné pour `FILE_TOO_LONG` → split obligatoire.

---

## §2 Docs gouvernants

- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md` — pattern T9 engine_d_runtime_support (extraction vers fichier support, TYPE_CHECKING pour référence circulaire)  
- `config/engineering_guardrails_policy.json` — règle `FILE_TOO_LONG`, seuil 700  
- `CLAUDE.md §3` — interdit baselines FILE_TOO_LONG en src/

---

## §3 État actuel du code

```
src/engines/engine_a/engine_a_runtime.py   711L   ← VIOLÉ
src/engines/engine_a/engine_a_runtime_support.py  (déjà existant)
src/engines/engine_a/__init__.py
```

**Fonctions candidates à l'extraction** (lignes 648–712 du fichier actuel) :

| Nom | Lignes approx | Description |
|-----|---------------|-------------|
| `_build_scoring_candidate` | 648–668 | Construit `ScoringCandidateInput` depuis runtime_input + engine_output |
| `_build_engine_a_scoring_raw_features` | 671–690 | Extrait le dict `raw_features` depuis engine_output.block_scores |
| `_build_engine_a_scoring_weights` | 693–712 | Retourne le dict weights depuis conviction constants |

Ces trois fonctions forment un bloc cohérent (pipeline scoring candidate), ne dépendent que de types externes à `engine_a_runtime.py`, et ne souffrent d'aucune référence circulaire problématique (voir §4).

---

## §4 Analyse dépendances — zéro import circulaire bloquant

Le nouveau fichier `engine_a_scoring_candidate_builder.py` nécessite :

| Import | Source | Circulaire ? |
|--------|---------|--------------|
| `ScoringCandidateInput` | `scoring_backbone.scoring_runtime` | Non |
| `ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS`, `ENGINE_A_CONVICTION_FEATURE_WEIGHTS`, `ENGINE_A_CONVICTION_NORMALIZATION` | `.conviction_builder_a` | Non |
| `EngineARuntimeInput` | `.engine_a_runtime` | **Oui** — mais uniquement dans annotations de type |
| `EngineAOutput` | `.engine_a_runner` | Non |

`EngineARuntimeInput` apparaît **uniquement dans la signature** des fonctions (pas dans les corps : seuls des accès attributs sont faits). Avec `from __future__ import annotations` (PEP 563), toutes les annotations deviennent des chaînes évaluées paresseusement → `if TYPE_CHECKING` suffit.

**Patron exact (identique T9 engine_d_runtime_support.py lignes 43-44)** :
```python
if TYPE_CHECKING:
    from .engine_a_runtime import EngineARuntimeInput
```

---

## §5 Fichiers modifiés

### 5a — Créer `src/engines/engine_a/engine_a_scoring_candidate_builder.py`

```
"""Scoring candidate builder helpers for Engine A runtime."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scoring_backbone.scoring_runtime import ScoringCandidateInput

from .conviction_builder_a import (
    ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS,
    ENGINE_A_CONVICTION_FEATURE_WEIGHTS,
    ENGINE_A_CONVICTION_NORMALIZATION,
)
from .engine_a_runner import EngineAOutput

if TYPE_CHECKING:
    from .engine_a_runtime import EngineARuntimeInput


def _build_scoring_candidate(
    runtime_input: EngineARuntimeInput,
    engine_output: EngineAOutput,
) -> ScoringCandidateInput:
    raw_features = _build_engine_a_scoring_raw_features(engine_output)
    return ScoringCandidateInput(
        engine_id="engine_a",
        pair=engine_output.pair,
        raw_features=raw_features,
        allowed_features=frozenset(raw_features),
        weights=_build_engine_a_scoring_weights(),
        scoring_version=engine_output.scoring_version or runtime_input.engine_inputs.scoring_version,
        score_penalties=runtime_input.score_penalties,
        size_penalties=runtime_input.size_penalties,
        blocker_conditions=runtime_input.blocker_conditions,
        expected_cost=engine_output.expected_cost,
        expected_ce=engine_output.ce_expected,
        projected_size=runtime_input.projected_size,
        projected_loss=0.0 if runtime_input.projected_loss is None else runtime_input.projected_loss,
        projected_beta_impact=0.0 if runtime_input.pair_beta is None else runtime_input.pair_beta * runtime_input.projected_size,
        cluster_id=runtime_input.cluster_id,
        corr_penalty=runtime_input.corr_penalty,
        risk_penalty=runtime_input.risk_penalty,
    )


def _build_engine_a_scoring_raw_features(
    engine_output: EngineAOutput,
) -> dict[str, float]:
    neutral_midpoint = ENGINE_A_CONVICTION_NORMALIZATION["neutral_midpoint"]
    block_scores = engine_output.block_scores
    return {
        "structure": block_scores.get("structure", 0.0),
        "context": block_scores.get("context", 0.0),
        "flow": block_scores.get("flow", 0.0),
        "cost_preference": block_scores.get("cost_preference", 0.0),
        "delta_confirmation_centered": (
            block_scores.get("delta_confirmation", neutral_midpoint) - neutral_midpoint
        ),
        "competition_support_centered": (
            block_scores.get("competition_support", neutral_midpoint) - neutral_midpoint
        ),
        "fragility_score": block_scores.get("fragility_score", 0.0),
        "toxicity_score": block_scores.get("toxicity_score", 0.0),
        "micro_friction_score": block_scores.get("micro_friction_score", 0.0),
    }


def _build_engine_a_scoring_weights() -> dict[str, float]:
    return {
        **ENGINE_A_CONVICTION_FEATURE_WEIGHTS,
        "delta_confirmation_centered": ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS[
            "delta_confirmation"
        ],
        "competition_support_centered": ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS[
            "competition_support"
        ],
        "fragility_score": -ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS[
            "fragility_penalty"
        ],
        "toxicity_score": -ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS[
            "toxicity_penalty"
        ],
        "micro_friction_score": -ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS[
            "micro_friction_penalty"
        ],
    }
```

**Taille attendue : ~75L**

### 5b — Modifier `src/engines/engine_a/engine_a_runtime.py`

**1. Ajouter l'import** après la ligne important depuis `.engine_a_runtime_support` :
```python
from .engine_a_scoring_candidate_builder import (
    _build_scoring_candidate,
    _build_engine_a_scoring_raw_features,
    _build_engine_a_scoring_weights,
)
```

**2. Supprimer les trois fonctions** des lignes 648–712 (byte-for-byte, identiques à celles du nouveau fichier).

**Résultat attendu :**  
- `engine_a_runtime.py` : **~648L** (711 - 65 + 2 lignes import = ~648)  
- `engine_a_scoring_candidate_builder.py` : **~75L**

### 5c — `src/engines/engine_a/__init__.py`

Vérifier que `__init__.py` n'exporte pas explicitement `_build_scoring_candidate` etc. (fonctions privées, préfixe `_`, pas d'export attendu). Si présentes, laisser telles quelles.

---

## §6 Claims falsifiables

| ID | Claim | Preuve |
|----|-------|--------|
| C1.1 | `engine_a_runtime.py` ≤ 700L après split | `wc -l src/engines/engine_a/engine_a_runtime.py` < 700 |
| C1.2 | `engine_a_scoring_candidate_builder.py` existe et est syntaxiquement valide | `python -m py_compile src/engines/engine_a/engine_a_scoring_candidate_builder.py` rc=0 |
| C1.3 | Aucun import circulaire runtime | `python -c "from engines.engine_a.engine_a_runtime import EngineARuntime"` rc=0 (depuis $PROJ avec PYTHONPATH=src) |
| C1.4 | `engineering_guardrails` : new_violations=0 sur les 2 fichiers touchés | `python -m engineering_guardrails --paths src/engines/engine_a/engine_a_runtime.py src/engines/engine_a/engine_a_scoring_candidate_builder.py` new_violations=0 |
| C1.5 | Tests slice passent | `pytest tests/ -k "engine_a" --tb=short` 0 failures |

---

## §7 Tests et preuves (slots Codex)

```
§13 — Preuves Codex

C1.1 wc -l :
`engine_a_runtime.py` = 601 lines ; `engine_a_scoring_candidate_builder.py` = 84 lines

C1.2 py_compile :
`python -m py_compile src/engines/engine_a/engine_a_runtime.py src/engines/engine_a/engine_a_scoring_candidate_builder.py` -> rc=0

C1.3 import runtime :
`PYTHONPATH=src python -c "from engines.engine_a.engine_a_runtime import EngineARuntime; print('ok')"` -> `ok`

C1.4 guardrails new_violations :
follow-up fix applied on `src/engines/engine_a/engine_a_runtime.py:278`:
`except Exception as exc` plus explicit `error_type` logging field.

Current global `python scripts/run_engineering_guardrails.py` summary:
- `new_violations=3`
- `first_new_violation=src/engines/engine_d/engine_d_runner.py:1 FILE_TOO_LONG`

No new guardrail violation remains on `src/engines/engine_a/engine_a_runtime.py`.

C1.5 pytest engine_a :
Green subset:
- `python -m pytest -q tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_integration.py --tb=short --basetemp=.test_tmp/pytest_fu1_engine_a_b` -> `14 passed`
- `python -m pytest -q tests/test_engines/test_engine_a/test_cost_feasibility_a.py tests/test_engines/test_engine_a/test_invalidation_mapper_a.py --tb=short --basetemp=.test_tmp/pytest_fu1_engine_a_e` -> `5 passed`

Blocked subset:
- `python -m pytest -q tests/test_engines/test_engine_a/test_engine_a_runtime_downstream.py --tb=short --basetemp=.test_tmp/pytest_fu1_engine_a_d`
  -> collection error because `tests/test_engines/test_engine_a/test_engine_a_runtime.py` is truncated to a single line (`from __future__ import annotations`) and cannot provide `_base_risk_evaluation`, `_runtime`, etc.
```

---

## §8 Hors scope — interdit à Codex

- Ne pas modifier la logique des 3 fonctions (copy byte-for-byte)
- Ne pas toucher `engine_a_runtime_support.py`
- Ne pas toucher les tests existants
- Ne pas modifier `__init__.py` sauf si nécessaire pour l'import
- Ne pas splitter d'autres fonctions

---

## §9 Risques

| Risque | Probabilité | Mitigation |
|--------|-------------|------------|
| Import circulaire runtime (EngineARuntimeInput) | Faible — TYPE_CHECKING suffit | C1.3 vérifie explicitement |
| Oubli de supprimer les fonctions dans engine_a_runtime.py (doublon) | Moyen | C1.1 vérifie le nombre de lignes |
| Régression scoring tests | Faible — copy byte-for-byte | C1.5 |

---

## §10 Différés / hors périmètre

- Split des autres grandes fonctions de `engine_a_runtime.py` (`_build_accepted_runtime_result` ligne 618 = 1 ligne, `_build_circuit_breaker_blocked_result` etc.) — non requis, <700L atteint
- `engine_d_runtime_support.py` (692L) — proche cap mais non bloquant (S32)

---

## §11 Statut (slot Codex)

```
Completion status : PARTIAL
Changed :
  - created `src/engines/engine_a/engine_a_scoring_candidate_builder.py`
  - extracted `_build_scoring_candidate`, `_build_engine_a_scoring_raw_features`, `_build_engine_a_scoring_weights`
  - `src/engines/engine_a/engine_a_runtime.py` now imports the extracted helpers and is reduced to 601 lines
  - closed the pre-existing `BARE_EXCEPT` at `src/engines/engine_a/engine_a_runtime.py:278`
Remaining :
  - downstream runtime proof is blocked by truncated `tests/test_engines/test_engine_a/test_engine_a_runtime.py`
Next safe step :
  - restore `tests/test_engines/test_engine_a/test_engine_a_runtime.py` before claiming full runtime proof for Engine A
  - keep Engine A runtime changes otherwise frozen while FU-2 / DAG cleanup proceeds
```

---

## §12 Checklist audit Opus

Après exécution Codex, Opus vérifie :

- [ ] `wc -l src/engines/engine_a/engine_a_runtime.py` < 700
- [ ] `wc -l src/engines/engine_a/engine_a_scoring_candidate_builder.py` < 200
- [ ] `python -m py_compile src/engines/engine_a/engine_a_scoring_candidate_builder.py` rc=0
- [ ] `python -c "from engines.engine_a.engine_a_runtime import EngineARuntime"` rc=0 (PYTHONPATH=src)
- [ ] Les 3 fonctions sont absentes de `engine_a_runtime.py` et présentes dans `engine_a_scoring_candidate_builder.py`
- [ ] `engine_a_runtime.py` importe les 3 fonctions depuis `engine_a_scoring_candidate_builder`
- [ ] `pytest tests/ -k "engine_a" --tb=short` 0 failures
- [ ] `python -m engineering_guardrails --paths src/engines/engine_a/engine_a_runtime.py` new_violations=0

**Verdict slot :**
```
[OPUS FILL — GREENLIGHT / REQUEST_FIX]
```
