# V5.3 - ENGINE C / ENGINE D BUILD-11 SHADOW INTEGRATION AUDIT
## Date: 2026-04-03
## Branch: codex/full-shadow-abcd-migration-20260403
## Status: LOCAL_GREEN_LOT_FROZEN

---

# 0. Purpose

This audit freezes the corrective lot that followed the focused `engine_c` / `engine_d`
review on the Full Shadow migration branch.

The goal of this lot was not to declare Build-15 or Build-16 operationally closed.
It was to fix four concrete local problems:

- `engine_c` missing several spec-visible structural breakout artifacts
- `engine_d` missing the auditable link to the origin context / prior trade
- non-duplication with `engine_a` not materialized as measurable engine artifacts
- Build-11 local Shadow still synthesizing `engine_c` / `engine_d` component verdicts
  instead of executing their runtime path and persisting proof

---

# 1. Fixes applied

## 1.1 Engine C contract enrichment

`engine_c` now exposes additional audit-ready fields in runner output and logs:

- resolved range bounds
- range width
- breakout type
- continuation context
- distance to breakout
- duplication indicator and overlap with `engine_a`
- marginal portfolio gain
- covered-share indicator vs `engine_a`
- `K_eff` contribution proxy

The runtime signal reason now also carries the breakout type instead of a generic
`breakout` tag only.

## 1.2 Engine D contract enrichment

`engine_d` now exposes the origin linkage required by the Build-16 spec:

- `origin_context_id`
- `origin_trade_id`
- `link_type`
- `structure_reformed_detected`

It also now materializes measurable non-duplication / marginality artifacts:

- duplication indicator and overlap with `engine_a`
- marginal portfolio gain
- covered-share indicator vs `engine_a`
- explicit marginal concentration field

The runtime signal reason now carries the origin link path.

## 1.3 Build-11 local Shadow runner integration

`scripts/run_local_replay_shadow.py` no longer treats `engine_c` and `engine_d`
as pure synthetic component verdicts.

The runner now:

- executes a governed demo runtime evaluation for `engine_c`
- executes a governed demo runtime evaluation for `engine_d`
- writes a dedicated sidecar:
  - `local_replay_shadow.engine_shadow_evidence.json`
- derives the `engine_c` / `engine_d` component assessment summaries from those
  runtime results
- uses the same runtime evidence to populate the candidate payload engine metrics

This keeps the lot local/demo-scoped, but removes the previous false impression
that `C/D` had been proven without being executed.

---

# 2. Validation

## 2.1 Engine and local Shadow surface

```powershell
rtk pytest tests/test_engines/test_engine_c tests/test_engines/test_engine_d tests/test_protocols/test_local_replay_shadow_runner.py -q
```

Result:

- `31 passed`

## 2.2 Broader Build-11 focused surface

```powershell
rtk pytest tests/test_engines/test_engine_c tests/test_engines/test_engine_d tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_runtime.py tests/test_protocols/test_shadow_day_counter.py tests/test_regression_alignment.py -q
```

Result:

- `116 passed`

## 2.3 Canonical runtime surface export

```powershell
rtk pytest tests/test_manifest_registry/test_runtime_surface.py -q
```

Result:

- `21 passed`

---

# 3. Honest reading

What this lot proves:

- `engine_c` and `engine_d` are richer and more audit-ready locally
- the missing origin-link story for `engine_d` is now encoded in code and tests
- measurable non-duplication artifacts now exist on both engines
- the Build-11 local Shadow runner now executes `C/D` runtime logic before
  asserting their component evidence

What this lot does not prove:

- final operational closure of Build-15
- final operational closure of Build-16
- a real target-environment 30-day Full Shadow proof for `A/B/C/D`
- downstream Build-12 / Build-13 readiness

---

# 4. Conclusion

Verdict for this lot:

- `engine_c`: locally strengthened and better aligned with Build-15 intent
- `engine_d`: locally strengthened and materially closer to Build-16 intent
- `Build-11 local runner`: more honest, because `C/D` evidence is now execution-backed

But the branch still must keep the following honest reading:

- Build-11 remains gated by real Shadow-day accumulation and target-environment proof
- Build-15 and Build-16 still need dedicated hardening / closure beyond this local lot

---

# 5. Next safe move

The next safe move after this lot is:

- keep using the improved local chain for regression protection
- continue the honest Build-11 runtime-proof frontier on target environment
- only then revisit late-build closure claims for `C` and `D`
