# FU-2B — Close remaining A/B/C DAG runtime violations

**Date** : 2026-04-21  
**Exécutant** : Codex  
**Déclencheur** : `python scripts/run_dag_check.py` restait à `5` violations après fermeture du slice D / execution_backbone

---

## §1 Objectif

Fermer les violations DAG restantes sur :
- `engine_a -> execution_backbone`
- `engine_b -> execution_backbone`
- `engine_c -> execution_backbone`
- `engine_c -> protocols` (x2)

Sans modifier la logique métier, uniquement en remettant les seams runtime sur des contrats autorisés.

---

## §2 Décisions de design

- Engine A et Engine B n’utilisaient `execution_backbone` que pour typer `ExecutionRefusalSink`.
  Le fix retenu est un `Protocol` local `_RefusalSink` dans chaque runtime.
- Engine C utilisait :
  - `ExecutionRefusalSink` depuis `execution_backbone`
  - les types de coordination et `evaluate_engine_coordination` depuis `protocols`
- Les types de coordination ont déjà été déplacés vers `interface_contracts` dans le slice FU-2 précédent.
- Le `dag_validator` scanne l’AST statiquement.
  Donc aucun lazy import `protocols` n’est acceptable pour Engine C.
- Le fix retenu pour Engine C est donc :
  - `_RefusalSink` local
  - types importés depuis `interface_contracts`
  - `coordination_evaluator` injecté explicitement

---

## §3 Fichiers changés

- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_b/engine_b_runtime.py`
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_c/engine_c_runtime_support.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime_bs_next_regression.py`

---

## §4 Claims falsifiables

| ID | Claim | Proof |
|----|-------|-------|
| C3.1 | Engine A no longer imports `execution_backbone` from runtime | grep = 0 matches |
| C3.2 | Engine B no longer imports `execution_backbone` from runtime | grep = 0 matches |
| C3.3 | Engine C no longer imports `execution_backbone` or `protocols` from runtime surfaces | grep = 0 matches |
| C3.4 | A/B/C runtime import surface still loads | import smoke = rc 0 |
| C3.5 | Targeted A/B/C tests still pass | pytest targeted = green |
| C3.6 | Repo DAG is fully green | `python scripts/run_dag_check.py` = PASS, 0 violations |

---

## §5 Proof

### C3.1 / C3.2 / C3.3 grep

`rtk grep "from execution_backbone.execution_runtime_models import ExecutionRefusalSink|from protocols.engine_coordination_rules|evaluate_engine_coordination\\(" src/engines/engine_a src/engines/engine_b src/engines/engine_c`

Result:
- `0 matches`

### C3.4 import smoke

- `python -c "import sys; sys.path.insert(0, 'src'); from engines.engine_a.engine_a_runtime import EngineARuntime; from engines.engine_b.engine_b_runtime import EngineBRuntime; from engines.engine_c.engine_c_runtime import EngineCRuntime; from engines.engine_c.engine_c_runtime_support import *; print('abc import smoke ok')"`
  -> `abc import smoke ok`

### C3.5 targeted pytest

- `rtk pytest -q tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_integration.py tests/test_engines/test_engine_a/test_cost_feasibility_a.py tests/test_engines/test_engine_a/test_invalidation_mapper_a.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime_refusals.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_bs_next_regression.py --basetemp=.test_tmp/pytest_dag_abc`
  -> `86 passed`

### C3.6 DAG validator

- `python scripts/run_dag_check.py`
  -> `VERDICT: PASS`
  -> `Violations = 0`
  -> `Cycles = 0`

---

## §6 Guardrails

`python scripts/run_engineering_guardrails.py` remains globally red, but the red is outside this slice:
- `new_violations=3`
- `first_new_violation=src/engines/engine_d/engine_d_runner.py:1 FILE_TOO_LONG`

No new guardrail issue was introduced by this A/B/C DAG cleanup slice.

---

## §7 Status

`COMPLETE`

Reason:
- all 5 remaining DAG violations are closed
- repo DAG is now green
- targeted A/B/C runtime proof is green
- remaining guardrail debt is real but outside this DAG slice

---

## §8 Next safe step

- return to the highest-value non-DAG debt:
  - `engine_d_runner.py` `FILE_TOO_LONG`
  - truncated `tests/test_engines/test_engine_a/test_engine_a_runtime.py`
  - quant wave-2 only after human doctrinal answers `Q1–Q4`
