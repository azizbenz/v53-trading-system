# V5.3 - AUDIT BUILD-6 TO BUILD-10
## Date: 2026-04-02
## Status: ACTIVE

---

# 0. Object

This document records the critical audit of the Light functional core:

- Build-6
- Build-7
- Build-8
- Build-9
- Build-10

Method:

- read the active canonical Build-6 to Build-10 specs
- map the real code surfaces
- execute the most probative test suites
- classify materially observed drifts

---

# 1. Executive summary

Current lot verdict:

- Build-6: `ALIGNED`
- Build-7: `ALIGNED`
- Build-8: `ALIGNED`
- Build-9: `ALIGNED`
- Build-10: `ALIGNED`

Short reading:

- engines A and B remain present and tested
- the minimal portfolio layer remains present and tested
- the minimal meta layer remains present and tested
- monitoring and the locked Light UI remain green after the latest operator
  safing work

Important:

- the previous Build-1 DAG drift was corrected on the current branch
- it also does not close the later Build-14 and promotion-gate questions
- it says only that the canonical Light core for Builds 6 to 10 remains
  functionally clean in its own evidence frame

---

# 2. Executed evidence

## 2.1 Canonical reading

Documents reread:

- `docs/specs/V5_3_BUILD6_SPECS_MOTEUR_A.md`
- `docs/specs/V5_3_BUILD7_SPECS_MOTEUR_B.md`
- `docs/specs/V5_3_BUILD8_SPECS_PORTFOLIO_MINIMAL.md`
- `docs/specs/V5_3_BUILD9_SPECS_META_MINIMAL.md`
- `docs/specs/V5_3_BUILD10_SPECS_MONITORING_UI_LIGHT.md`

## 2.2 Code mapping

Confirmed surfaces:

- `src/engines/engine_a`
- `src/engines/engine_b`
- `src/portfolio_minimal`
- `src/meta_minimal`
- `src/monitoring`
- `src/ui`

## 2.3 Tests executed

- `rtk pytest tests/test_engines -q`
  - result: `125 passed`
- `rtk pytest tests/test_portfolio_minimal -q`
  - result: `82 passed`
- `rtk pytest tests/test_meta_minimal tests/test_monitoring tests/test_ui -q`
  - result: `219 passed`
- `rtk pytest tests/test_monitoring tests/test_ui -q`
  - result: `141 passed`

---

# 3. Findings

## No new P0/P1 functional finding confirmed inside this lot

This wave does not expose a new blocking contradiction on:

- engine A
- engine B
- portfolio minimal
- meta minimal
- monitoring and locked Light UI

The Light functional core remains coherent with:

- the packages present on disk
- the expected surface APIs
- the targeted test evidence

## Cross-build caveat outside the lot

This lot still does not close later rollout drifts on:

- later Build-14 vocabulary and exposure questions

---

# 4. Verdict by build

## 4.1 Build-6 - Engine A

Verdict:

- `ALIGNED`

Why:

- the canonical engine A surface exists
- the engine suite remains green
- no new drift was observed in this wave

## 4.2 Build-7 - Engine B

Verdict:

- `ALIGNED`

Why:

- the canonical engine B surface exists
- the engine suite remains green
- no new drift was observed in this wave

## 4.3 Build-8 - Portfolio Minimal

Verdict:

- `ALIGNED`

Why:

- `src/portfolio_minimal` remains present and distinct
- the targeted suite remains green
- no new drift was observed in this wave

## 4.4 Build-9 - Meta Minimal

Verdict:

- `ALIGNED`

Why:

- `src/meta_minimal` remains present and distinct
- the targeted suite remains green
- no new drift was observed in this wave

## 4.5 Build-10 - Monitoring and UI Light

Verdict:

- `ALIGNED`

Why:

- `src/monitoring` and `src/ui` remain functionally green
- the refreshed focused suite is green: `141 passed`
- the broader refreshed suite with `meta_minimal` included is also green:
  `219 passed`

Important nuance:

- the latest safing and launcher work did not break the Build-10 functional
  surface
- the earlier Build-1 architectural caveat tied to `monitoring_runtime` was
  resolved in the dedicated Build-1 correction wave

---

# 5. Cross-build reading

The current Build-6 to Build-10 picture confirms something important:

- the Light functional core is more stable than the repository-wide
  rollout-closure problem

In practice:

- the useful business layers are still holding
- the main visible debt is now later in the rollout chain, not local to
  engines A/B, portfolio, meta, or the functional monitoring/UI surface

---

# 6. Recommended actions

## Action 1

Keep Build-6 to Build-10 as the current green functional baseline while the
rest of the audit continues.

## Action 2

Keep Build-10 as a green baseline while Build-11 closure and Build-14
normalization continue downstream.

## Action 3

Continue now with Build-11 to Build-14, with specific attention on:

- Shadow temporal gates
- report completeness
- component verdicts
- Micro-live and Live-Light promotion semantics
- Build-14 exposure semantics

---

# 7. Lot decision

Decision after refresh:

- Build-6: aligned
- Build-7: aligned
- Build-8: aligned
- Build-9: aligned
- Build-10: aligned
