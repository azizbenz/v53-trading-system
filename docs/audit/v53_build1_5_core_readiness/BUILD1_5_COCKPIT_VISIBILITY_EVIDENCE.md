# Build-1 to Build-5 Cockpit Visibility Evidence

Date: `2026-05-01`

## Scope

Primary cockpit rails inspected:

- `src/cockpit/state_data_quality.py`
- `src/cockpit/state_replay_metrics.py`
- `src/cockpit/state_system_flow.py`
- `src/cockpit/state_engine_why.py`
- `src/cockpit/state_feature_bridge.py`
- `src/cockpit/templates/*`

Representative tests:

- `tests/cockpit/test_state_data_quality.py`
- `tests/cockpit/test_state_replay_metrics.py`
- `tests/cockpit/test_state_system_flow.py`
- `tests/cockpit/test_state_feature_bridge.py`
- `tests/cockpit/test_state_engine_why.py`

## Build-by-Build Visibility

| Build | Surface audited | Classification | Notes |
|---|---|---|---|
| Build-1 | DAG / smoke / engineering guardrails / build-stage coherence | `NOT_VISIBLE` | No explicit cockpit page or state was found that projects the current Build-1 red state. |
| Build-2 | Data quality / freshness / pair health | `VISIBLE` | `state_data_quality.py` and related tests project live data quality and pair-level health. |
| Build-3 | Execution backbone build health | `CODED_NOT_DISPLAYED` | Execution runtime semantics exist and are tested, but no explicit build-level execution status page was proven in the cockpit. |
| Build-4 | Risk readiness / cost completeness / small-capital and drawdown caveats | `VISIBLE` | `state_replay_metrics.py` and `state_system_flow.py` surface major non-green readiness semantics. |
| Build-5 | Scoring readiness / expected-CE caveat / ML neutralization states | `VISIBLE` | scoring-related caveats and readiness semantics are projected on cockpit/system-flow surfaces. |

## False-Green Risk Review

### Build-1

Classification: `FALSE_GREEN_RISK`

Reason:

- downstream cockpit pages can look operational while the foundational Build-1 smoke state is red
- the failure is real and tested, but not operator-visible at the same abstraction level

### Build-2

Classification: `LOW`

Reason:

- data quality is explicitly surfaced

### Build-3

Classification: `PARTIAL`

Reason:

- execution safety semantics are present in runtime and tests
- a single build-level execution-health status was not proven in cockpit

### Build-4 / Build-5

Classification: `MANAGED`

Reason:

- replay/system-flow/economic-sterilization surfaces explicitly prevent key economics false-green states

## Required Visibility Gaps

- explicit Build-1 DAG / smoke / guardrail projection
- explicit core-build health banner or state
- optional build-level execution readiness surface, separate from later replay/economics views

## Verdict

Cockpit visibility verdict: `PARTIAL`

Reason:

- Build-2, Build-4, and Build-5 have meaningful operator-facing surfaces
- Build-1 core red-state visibility is missing
- Build-3 build-level status is weaker than its runtime/test coverage
