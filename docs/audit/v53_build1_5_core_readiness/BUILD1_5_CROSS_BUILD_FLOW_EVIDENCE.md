# Build-1 to Build-5 Cross-Build Flow Evidence

Date: `2026-05-01`

## Declared Build Dependency Flow

Source of truth:

- `src/manifest_registry/module_inventory.py`
- `src/manifest_registry/build_order_registry.py`
- `src/manifest_registry/dependency_registry.py`

Declared canonical build flow:

```text
contracts
-> data
-> execution
-> risk
-> scoring
```

This is source-proven by:

- Build-1 modules in `BUILD_STAGES`
- Build-2 modules in `BUILD_STAGES`
- Build-3 modules in `BUILD_STAGES`
- Build-4 modules in `BUILD_STAGES`
- Build-5 modules in `BUILD_STAGES`
- `execution_backbone` allowed to depend on `data_backbone`
- `risk_backbone` allowed to depend on `execution_backbone`
- `scoring_backbone` allowed to depend on `risk_backbone` and `execution_backbone`

## Practical Trading Flow

Observed practical runtime flow is:

```text
data_backbone
-> engine inputs
-> scoring / risk
-> portfolio / meta later
-> execution
```

Important distinction:

- this practical trading flow is not identical to the build-order dependency flow
- build order expresses legal module dependencies
- practical runtime flow expresses how runtime data and candidate state move laterally across the system

## Coherence Checks

### Legal import direction

Status: `PARTIAL`

Reason:

- the declared dependency graph is coherent for the core builds
- one unauthorized observed import still exists: `cockpit -> data_backbone`

### Circular dependency

Status: `PROVEN_CLEAN`

Reason:

- DAG validation reported `0` cycles

### Shared contracts without duplication

Status: `PROVEN`

Reason:

- one canonical `interface_contracts` rail is reused across builds

### Reason codes survive across builds

Status: `PROVEN`

Source-level evidence:

- data backbone uses explicit health/freshness/consistency status rails rather than silent pass-through
- execution backbone carries `reason_codes` and `NO_TRADE`/blocked dispositions
- risk backbone carries `carriage_reason_codes`, `input_reason_codes`, and explainability `reason_codes`
- scoring backbone carries `carriage_reason_codes`, artifact hook reason codes, and cost-readiness reason codes

### Hidden side mutation

Status: `NOT_PROVEN`

Reason:

- no hidden side mutation path was found in the audited Build-1..5 core rails
- side creation remains an engine/decision concern, not a Build-1..5 core behavior

### Hidden live enablement

Status: `NOT_PROVEN`

Reason:

- Build-3 and later rails include explicit governed-mode fail-close checks rather than silent live enablement

### Cockpit displays only what is proven

Status: `PARTIAL`

Reason:

- many runtime readiness states are projected explicitly
- Build-1 DAG/smoke/guardrail red state is not projected clearly on cockpit surfaces

## Cross-Build Failure Surface

The single largest coherence break across Build-1..5 is not a cycle. It is a registry mismatch:

- `cockpit` is inventory-registered
- `cockpit` is dependency-registered
- `cockpit` is not build-stage-registered
- `cockpit` imports `data_backbone` without that edge being allowed by the dependency registry

## Verdict

Cross-build flow verdict: `PARTIAL`

Reason:

- core build dependency direction is mostly coherent
- real source modules exist and later builds validate cleanly
- Build-1 governance coherence is still broken by the `cockpit` stage/dependency mismatch
