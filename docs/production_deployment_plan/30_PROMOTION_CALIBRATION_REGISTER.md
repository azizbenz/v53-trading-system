# 30 - Promotion Calibration Register

> Status: living governance register for what must be calibrated, frozen, or proven before promotion through Shadow, Micro-live, and Live.
>
> Date: 2026-04-17.
>
> Hard rule: this file does not override the repo, docs `12`, `13`, `14`, or engine specs. It is an operational register that says what is still missing before a promotion decision is defensible.

---

## 0. Objective

Keep one durable place that answers a simple question:

- what must still be calibrated before an engine or shared rail is promotable in Shadow,
- what must still be proven before `G2.3 -> MICRO_LIVE`,
- what must still be re-calibrated or re-validated before Live scaling.

This file exists because the real repo now contains many engine-level hardening slices and audit packs, but the remaining promotion blockers were spread across:

- `12_LOCAL_LAB_VS_VPS_SEPARATION.md`
- `13_CALIBRATION_METHODS.md`
- `14_SHADOW_GATE_MATH.md`
- engine-specific audit packs in `docs/production_deployment_plan/update_audit/`

This register compresses those blockers into one promotion-oriented view.

---

## 1. Scope

Included:

- Engine A / B / C / D promotion blockers
- shared microstructure blockers that still matter for promotion
- shared calibration / signed-artifact blockers
- stage-specific blockers for:
  - Shadow sign-off
  - Micro-live promotion
  - Live scaling

Excluded:

- full re-explanation of calibration math from `13_...`
- full re-explanation of gate math from `14_...`
- implementation detail inventories already captured in engine audit packs

---

## 2. Reading Rules

1. Current code remains the operational source of truth.
2. `12_...` decides where calibration lives and who signs it.
3. `13_...` decides how thresholds are calibrated.
4. `14_...` decides what statistical evidence is required at promotion gates.
5. A surface can be:
   - `READY_FOR_SHADOW`
   - `NEEDS_MORE_CALIBRATION`
   - `RESEARCH_ONLY`
   - `DO_NOT_PROMOTE`
6. "Before Shadow sign-off" means before treating the rail as a governed Shadow candidate or before advancing a Shadow palier with confidence.
7. "Before Micro-live" means before `G2.3 -> MICRO_LIVE`.
8. "Before Live scaling" means before `G3 -> target live capital`.

---

## 3. Non-Calibrated Surfaces

The following are not statistical-calibration targets:

- halal prohibitions and forbidden account-feature checks
- hard caps that humans declared as absolute floors/caps
- Local IA Lab vs VPS topology
- signature requirement for calibration or promotion artifacts

These surfaces still require proof and enforcement, but not statistical threshold fitting.

---

## 4. Register Summary

| Surface | Type | Current verdict | Before Shadow sign-off | Before Micro-live | Before Live scaling | Evidence |
|---|---|---|---|---|---|---|
| Engine A | hybrid | `NEEDS_MORE_CALIBRATION` | Freeze governed A-specific cost and conviction thresholds; replace ad hoc seam injection with signed OFI/Kyle/RK upstream evidence | Pass `G2.3` evidence on real Shadow fills; prove drift and DD remain inside gate math | Recalibration cadence + Micro-live evidence before capital increase | `20`, `23`, `24`, `13`, `14`, audit pack `2026-04-17_engine_a_prompt_correction_hardening.md` |
| Engine B | hybrid | `NEEDS_MORE_CALIBRATION` | Calibrate excess/fade/conviction thresholds, especially VPIN toxic-flow fade and cost posture | Pass `G2.3` evidence on real Shadow fills; keep anti-breakout and cost rails stable under live-like noise | Recalibration cadence + Micro-live evidence before capital increase | `20`, `23`, `24`, `13`, `14`, audit packs `2026-04-17_engine_b_*` |
| Engine C | hybrid | `NEEDS_MORE_CALIBRATION` | Govern `THR-C_VPIN_MAX`; if `kyle_lambda_max` is used, source it from calibration; wire one canonical upstream assembler | Pass `G2.3` evidence on Shadow fills with final microstructure thresholds, not TBD values | Recalibration cadence + Micro-live evidence before capital increase | `21`, `23`, `24`, `29`, `13`, `14`, audit pack `2026-04-16_engine_c_continuation_microstructure_wiring.md` |
| Engine D | hybrid | `NEEDS_MORE_CALIBRATION` | Freeze anti-revenge/re-entry governance (`THR-X10`, `THR-X11`) with replay/shadow evidence; confirm option C does not leave a blind spot | Pass `G2.3` evidence on Shadow fills; maintain first-episode lineage and anti-revenge observability at promotion time | Recalibration cadence + Micro-live evidence before capital increase | `22`, `24`, `29`, `13`, `14`, `2026-04-16_docs21_22_opus_audit.md`, current `engine_d` code/tests |
| Canonical microstructure calculators | statistical | `READY_FOR_SHADOW` | No new formula calibration required at calculator level; only consumer thresholds remain to freeze | Keep the consumer-facing thresholds signed and versioned | Recalibrate thresholds by consumer, not formulas | `23`, `13`, audit packs `2026-04-16_*.md` |
| Calibration artifact / loader rail | governance_only | `READY_FOR_SHADOW` | Signed artifact required; no unsigned fallback | Same | Same | `12`, `13`, `src/calibration_loader/` |
| Shadow gate report / promotion artifact rail | governance_plus_stats | `NEEDS_MORE_CALIBRATION` | Shadow metrics may be computed, but promotion-ready signed gate artifacts still need one durable governed report path | Mandatory before `G2.3 -> MICRO_LIVE` | Mandatory before `G3` | `14`, `25`, `26`, `src/protocols/` |
| Halal / forbidden account-feature rails | deterministic | `READY_FOR_SHADOW` | No statistical calibration; only zero-violation proof | Mandatory zero-violation proof | Mandatory zero-violation proof | `12`, `13`, `14`, halal/account audit rails |
| Runtime hard caps / breakers | deterministic_plus_tightening | `READY_FOR_SHADOW` | Can only be tightened by calibration, never loosened | Same | Same | `10`, `12`, `13`, runtime risk rails |

---

## 5. Detailed Register

### 5.1 Engine A

**Current verdict**: `NEEDS_MORE_CALIBRATION`

Engine A is now materially hardened in code, but its newly explicit local semantic seams are still only halfway to governed promotion readiness.

#### Before Shadow sign-off

- Freeze `ce_min_A` and `delta_safe_A` through the signed calibration rail defined in `11_...` and `13_...`.
- Stop treating:
  - `ofi_flow_score`
  - `kyle_lambda_cost_uplift`
  - `realized_kernel_vol_scale`
  as merely injectible normalized values.
- Replace free-form injection with one governed upstream evidence path from canonical microstructure outputs into Engine A inputs.
- Keep `CostVerdict.MARGINAL` non-emittable and do not weaken the current guards.

#### Before Micro-live

- Pass the gate battery from `14_SHADOW_GATE_MATH.md` on real Shadow fills.
- Demonstrate that A's OFI/Kyle/RK seams remain additive and do not silently alter the primary A semantics.
- Confirm that cost drift between backtest, Shadow, and pre-live conditions remains inside the signed tolerance.

#### Before Live scaling

- Re-run calibration on the documented cadence.
- Re-check drawdown, CE, PSR/DSR, and drift after Micro-live evidence exists.

#### Evidence

- `docs/production_deployment_plan/update_audit/2026-04-17_engine_a_prompt_correction_hardening.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_engine_a_ofi_first_local_conviction_seam.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_engine_a_kyle_lambda_cost_seam.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_engine_a_realized_kernel_structure_seam.md`

---

### 5.2 Engine B

**Current verdict**: `NEEDS_MORE_CALIBRATION`

Engine B is auditably stronger than before, but its trading thresholds remain mostly heuristic and still need governed Shadow evidence.

#### Before Shadow sign-off

- Freeze B-specific cost thresholds:
  - `ce_min_B`
  - `delta_safe_B`
- Freeze B-specific excess / fade thresholds, especially the toxic-flow fade branch:
  - `vpin_current >= 0.35`
  - `toxic_flow_correlation > 0.7`
- Freeze conviction and anti-breakout thresholds under the same signed artifact discipline.
- Keep B as a local semantic reservoir; do not flatten its mean-reversion / fade logic into C/D-style semantics.

#### Before Micro-live

- Pass the gate battery from `14_SHADOW_GATE_MATH.md` on real Shadow fills.
- Prove that the toxic-flow fade branch improves or at least does not degrade CE net under real Shadow conditions.
- Prove that richer reason codes and runtime risk statuses stay coherent under repeated Shadow runs.

#### Before Live scaling

- Re-run the B-local calibration cadence and compare Micro-live evidence against Shadow evidence before increasing capital.

#### Evidence

- `docs/production_deployment_plan/update_audit/2026-04-17_engine_b_hardening_from_cartography_audit.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_engine_b_reaudit_residual_fixes.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_engine_b_prompt1_explicit_status_and_forecast_proofs.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_engine_b_toxic_flow_fade_local_subsignal.md`

---

### 5.3 Engine C

**Current verdict**: `NEEDS_MORE_CALIBRATION`

Engine C is already a rich and shadow-capable rail, but promotion still depends on final governed thresholds for the new microstructure gates.

#### Before Shadow sign-off

- `THR-C_VPIN_MAX` is still `TBD_shadow_calibration` in doc 21 and must be frozen before VPIN becomes a durable promotion dependency.
- If `continuation_kyle_lambda_max` is supplied, it must come from a governed calibration artifact rather than an inline one-off number.
- Wire one canonical upstream assembler into `EngineCInput` so the runtime does not accumulate duplicate calculation paths.
- Confirm `ce_min_C` and `delta_safe_C` remain governed by signed calibration, not ad hoc tuning.

#### Before Micro-live

- Pass the gate battery from `14_SHADOW_GATE_MATH.md` on real Shadow fills using the final, signed microstructure thresholds.
- Confirm that the microstructure vetoes do not create an unintended sample-size collapse that invalidates the gate math.

#### Before Live scaling

- Re-run the consumer thresholds on the documented cadence and compare Micro-live against Shadow.

#### Evidence

- `docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `docs/production_deployment_plan/update_audit/2026-04-16_engine_c_continuation_microstructure_wiring.md`
- current `src/engines/engine_c/` code and tests

---

### 5.4 Engine D

**Current verdict**: `NEEDS_MORE_CALIBRATION`

Engine D is rich and shadow-capable, but promotion remains sensitive because the user-selected option `C` explicitly refused a continuous revenge-penalty formula. That keeps the anti-revenge rail observable and governed, but still in need of replay/shadow proof.

#### Before Shadow sign-off

- Freeze operational governance around:
  - `THR-X10` anti-revenge cooldown failsafe
  - `THR-X11` max consecutive re-entries before reset
- Confirm through replay/backtest evidence that option `C` (observability, no continuous penalty) does not create a blind spot.
- Keep `first_episode_ref`, `closed_episode_journal`, and `anti_revenge_state` auditable through the current protocol rails.
- Confirm `ce_min_D` and `delta_safe_D` remain governed by signed calibration, not local heuristics.

#### Before Micro-live

- Pass the gate battery from `14_SHADOW_GATE_MATH.md` on real Shadow fills.
- Confirm that D's anti-revenge observability fields remain populated and useful at gate time, not merely logged.
- Confirm that duplication / marginal portfolio gain decisions remain explicit and stable under Shadow.

#### Before Live scaling

- Re-run calibration cadence on D-local economics and re-entry governance after Micro-live evidence exists.

#### Evidence

- `docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- `docs/production_deployment_plan/update_audit/2026-04-16_docs21_22_opus_audit.md`
- current `src/engines/engine_d/` code and tests

---

### 5.5 Canonical Microstructure Package

**Current verdict**: `READY_FOR_SHADOW`

The calculator layer itself is no longer the main blocker.

#### Before Shadow sign-off

- Do not recalibrate or mutate the canonical formulas silently.
- Freeze consumer thresholds and normalization seams, not calculator formulas.
- Keep window/hash/quality flags traceable in the current package.

#### Before Micro-live

- Confirm that every microstructure feature used by A/B/C/D comes from one canonical record path, not duplicate inline calculations.

#### Before Live scaling

- Recalibrate only the consumer thresholds and acceptance bands, not the core formulas.

#### Evidence

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/update_audit/2026-04-16_*.md`

---

### 5.6 Shared Calibration / Promotion Rail

**Current verdict**: `NEEDS_MORE_CALIBRATION`

#### Before Shadow sign-off

- Calibration artifacts must remain:
  - produced in Local IA Lab
  - human-signed
  - immutable after signature
  - verified by `calibration_loader`

#### Before Micro-live

- Promotion to Micro-live requires one governed, signed gate-evidence artifact that proves the checks in `14_...`.
- No engine should be promoted from chat history or scattered audit packs alone.

#### Before Live scaling

- The same signed-artifact discipline must apply to the Micro-live -> Live decision.

#### Evidence

- `docs/production_deployment_plan/12_LOCAL_LAB_VS_VPS_SEPARATION.md`
- `docs/production_deployment_plan/13_CALIBRATION_METHODS.md`
- `docs/production_deployment_plan/14_SHADOW_GATE_MATH.md`
- `src/calibration_loader/`
- `src/protocols/`

---

## 6. Operational Use

Use this register in the following order:

1. read the current engine or shared-rail audit pack
2. check this register for stage-specific blockers
3. verify whether the blocker is:
   - statistical calibration
   - deterministic governance proof
   - missing signed artifact
   - missing promotion evidence
4. only then decide whether the next slice is:
   - code hardening
   - calibration production in Local IA Lab
   - gate report production
   - user arbitration

---

## 7. What This Register Forbids

- Do not say "ready for promotion" only because tests are green.
- Do not say "needs calibration" without naming the stage:
  - Shadow
  - Micro-live
  - Live scaling
- Do not treat deterministic halal or hard-cap rules as statistical thresholds.
- Do not create a second promotion register elsewhere unless this one is formally replaced.

---

## 8. Next Safe Step

Keep this file updated whenever an engine or shared promotion surface changes status on:

- current verdict
- Shadow blockers
- Micro-live blockers
- Live-scaling blockers

Any future slice that claims promotion progress should update this register or explicitly justify why it does not change it.
