# V5.3 Artifact Expert-Bank Strategy

## 0. Status

This document is a **target architecture and governance strategy** for a more dynamic artifact runtime.

It is **not** a claim that the full operator workflow is already exposed in the current cockpit.

Current repo truth remains:

- the operator/VPS surface tracks one active ML artifact and one active Regime Detector artifact
- the deeper compiled-hook rail can represent multiple artifact ids on one hook
- that deeper rail currently expresses **composition semantics**, not **automatic performance comparison**

Relevant current files:

- `src/interface_contracts/shadow_vps_service_contracts.py`
- `src/protocols/dashboard_command_queue.py`
- `src/interface_contracts/artifact_contracts_models.py`
- `src/protocols/artifact_action_composer.py`
- `src/protocols/compiled_hook_plan_loader.py`
- `src/protocols/compiled_artifact_registry_store.py`

## 1. Problem

A single static artifact for all market conditions is too rigid.

A market-facing system sees:

- regime shifts
- changing toxicity
- changing order-book pressure
- changing volatility
- changing latency and liquidity quality

So the runtime must become **dynamic** without becoming:

- un-auditable
- combinatorially explosive
- impossible to attribute
- unsafe in production

## 2. Core Decision

The production-safe dynamic design is:

- **one canonical hook bank per engine/hook**
- **one selected champion artifact per hook at decision time**
- **zero to N shadow challengers evaluated on the same context**
- **baseline fallback when selector confidence or coverage is weak**
- **progressive promotion only through replay -> shadow -> micro-live -> live**

This means:

- not one monolithic artifact for everything
- not many live artifacts all influencing the same hook at once by default
- not an automatic self-promoting optimizer in production

## 3. Vocabulary

### 3.1 Hook

Canonical runtime decision points already present in V5.3:

- `engine_a_pre_entry_confirmation`
- `engine_b_sweep_validation`
- `engine_c_void_validation`
- `engine_d_reentry_validation`

### 3.2 Expert artifact

A bounded runtime artifact specialized for a hook and a context family.

Examples:

- `A_baseline`
- `A_breakout_low_toxicity`
- `A_defensive_high_toxicity`
- `B_fast_sweep_high_pressure`
- `D_reentry_soft_retry_mid_vol`

### 3.3 Champion

The artifact that is actually allowed to influence the runtime decision on that hook for that event.

Exactly one champion per hook/event.

### 3.4 Shadow challenger

An artifact evaluated on the same event and same feature snapshot, but whose output does **not** influence the executed path.

Its purpose is:

- counterfactual comparison
- evidence generation
- calibration and promotion analysis

### 3.5 Selector

A typed policy or artifact that chooses the champion based on context.

Its output is:

- `selected_artifact_id`
- plus confidence / coverage metadata

### 3.6 Baseline

The safest artifact for the hook.

If the selector is uncertain, out-of-coverage, stale, or unhealthy, the runtime falls back to baseline.

## 4. Exact Runtime Functioning

## 4.1 Offline side: Local IA Lab

The Lab may generate multiple candidate artifacts per hook.

Example for Engine A:

- `A1 baseline`
- `A2 low-toxicity trend`
- `A3 high-imbalance breakout`
- `A4 defensive volatile`
- `A5 liquidity-fragile veto`

The Lab may also generate:

- one selector artifact for Engine A
- or a typed compiled hook plan referencing multiple artifacts

Each candidate must remain:

- signed
- versioned
- immutable
- tied to feature/version lineage

## 4.2 Import to VPS

Artifacts move through the canonical governed rail:

- `local_replay_runtime`
- governed export bundle
- `backtest_artifact_import`
- VPS import

No direct IA-Lab code is allowed on the VPS runtime.

## 4.3 Activation stage

An artifact does not become live because it was uploaded.

It must carry a governed activation stage, for example:

- `replay_only`
- `shadow_ready`
- `limited_influence`
- `micro_live_candidate`
- `live_approved`

Shadow consumption requires `shadow_ready`.

## 4.4 Decision-time flow on the VPS

For a given hook event:

1. The runtime builds the feature snapshot for the hook.
2. The selector evaluates the context.
3. The selector chooses one champion artifact id.
4. The runtime executes the champion artifact only for the real decision path.
5. Optional shadow challengers evaluate the same snapshot in parallel.
6. The runtime stores:
   - champion decision
   - challenger counterfactual decisions
   - selector confidence / coverage
   - realized outcome later when observable
7. Promotion logic stays external and governed. The runtime does not auto-promote challengers.

## 4.5 Fallback rule

If any of these conditions happen:

- selector confidence too low
- no artifact covers the current context
- artifact is stale or invalid
- runtime budget is exhausted
- shadow subsystem is degraded

then:

- use the hook baseline
- continue logging challenger evidence if budget allows

## 5. What Is Allowed Simultaneously

## 5.1 Allowed

This is the recommended target:

- `A1` used as champion on Engine A
- `A2`, `A3`, `A4`, `A5` evaluated in shadow on the same events

Also allowed:

- `A1` as champion
- `A1'` as a challenger version with different thresholds
- compare `A1` vs `A1'` on the same context

This is the correct way to test threshold variants.

## 5.2 Not recommended as default live design

This is not the recommended primary pattern:

- `A1 + A2 + A3 + A4 + A5` all influencing the same live hook simultaneously

Why:

- attribution becomes weak
- audit becomes noisy
- failures become harder to localize
- policy interactions become nonlinear
- promotion evidence becomes ambiguous

The compiled multi-artifact composition rail may still exist for bounded cases, but it should be used as an explicit exception, not as the default dynamic strategy.

## 6. Why This Is More Dynamic Than a Single Artifact

This design is dynamic in three ways:

### 6.1 Context-dependent selection

Different contexts can choose different champions.

Examples:

- low toxicity -> `A_trend_low_toxicity`
- high toxicity -> `A_defensive_high_toxicity`
- severe imbalance -> `A_breakout_high_imbalance`

### 6.2 Continuous challenger evaluation

Even when only one champion is live, challengers continue to accumulate evidence.

This means the system keeps learning which alternative policies would have been better under current market conditions.

### 6.3 Safe replacement

When challenger evidence is strong enough, the governance layer can:

- replace the champion
- or update selector routing

without inventing an ungated self-modifying runtime.

## 7. CPU and Infra Guidance

## 7.1 Short answer

Yes, **a modest number of shadow challengers can be supported**.

No, **you should not assume that 5 challengers x 4 engines x every event is safe on one ordinary VPS**.

## 7.2 What determines cost

Infra cost depends on:

- feature-building cost
- artifact logic cost
- hook frequency
- pair count
- event rate
- persistence / logging cost
- whether challenger evaluation reuses the same feature snapshot

If artifacts are cheap threshold/rule payloads, the extra cost is often manageable.

If artifacts are heavier model inferences or repeated feature recomputations, cost rises quickly.

## 7.3 Safe infra rule

The runtime should reuse one feature snapshot and fan it out to champion + challengers.

The runtime must **not** rebuild the full feature pipeline separately for each challenger.

That is the key requirement for making challenger shadow practical.

## 7.4 Recommended budget tiers

### Tier 0 - current simple mode

- 1 champion
- 0 challengers

Use when:

- initial rollout
- unstable infra
- no CPU headroom

### Tier 1 - recommended first dynamic mode

- 1 champion
- 1 shadow challenger per hot hook

Use when:

- validating one replacement candidate
- validating one threshold variant such as `A1'`

This is the safest first step.

### Tier 2 - bounded expert-bank mode

- 1 champion
- up to 2 challengers per selected hook
- not every hook at full rate

Use when:

- selector quality is already decent
- observability and storage are under control

Good production pattern:

- Engine A and D get challengers
- Engine B and C stay champion-only

or:

- all hooks get challengers
- but only on sampled events

### Tier 3 - aggressive research mode

- 1 champion
- 4 or more challengers per hook across all pairs and all events

This is **not** a safe default VPS mode.

Use only if:

- CPU headroom is measured
- IO/logging headroom is measured
- pair scope is bounded
- challenger execution can be disabled instantly
- operator observability is strong

## 7.5 Production-safe throttles

To keep challenger shadow affordable, use one or more of:

- pair allowlist
- hook allowlist
- event sampling
- volatility-triggered challenger activation
- time-sliced challenger rotation
- hard CPU budget
- hard per-loop latency budget
- degrade-to-baseline mode when budget is exceeded

## 8. Recommended V5.3 Strategy

## 8.1 Near-term practical target

Per hook:

- 1 baseline
- 1 current champion
- 1 or 2 challengers

This gives real dynamism without losing control.

## 8.2 Selector policy

Selector inputs should come from existing governed runtime context, for example:

- regime bucket
- toxicity bucket
- order-book imbalance bucket
- volatility bucket
- spread / liquidity quality bucket

Selector outputs:

- chosen champion artifact id
- confidence score
- coverage bucket
- fallback reason if baseline is chosen

## 8.3 Promotion doctrine

Promotion should compare:

- champion realized outcomes
- challenger counterfactual signals
- replay evidence
- shadow consistency
- drift / freshness
- operator review

Promotion must remain:

- explicit
- reviewable
- reversible

No automatic self-promotion.

## 9. Answer to the Concrete Questions

### 9.1 Can V5.3 have `A1` live and `A2..A5` in shadow?

**As a target architecture: yes.**

That is the correct dynamic direction.

But it should mean:

- `A1` influences the runtime
- `A2..A5` run as shadow challengers only
- all use the same feature snapshot
- all outputs are logged with attribution
- promotion remains governed

### 9.2 Can a threshold variant `A1'` be tested in shadow at the same time?

**Yes.**

This is one of the best early uses of the pattern.

`A1'` is often better than adding a brand-new artifact family because:

- attribution is cleaner
- the delta is narrow
- shadow comparison is easier

### 9.3 Can CPU/infra hold it?

**Maybe, but only in bounded form.**

Safe answer:

- 1 champion + 1 challenger: usually realistic
- 1 champion + 2 challengers on selected hooks: often realistic if logic is lightweight
- 5 challengers per engine across all hooks/pairs/events: not safe to assume without profiling

So the production-safe plan is:

- start with 1 challenger
- measure CPU, loop latency, logging volume, and storage
- then widen gradually

## 10. Final Rule

The system should become **dynamic by selection**, not **chaotic by uncontrolled artifact multiplication**.

The right pattern is:

- expert bank
- selector
- one champion
- shadow challengers
- baseline fallback
- staged promotion

That is the most dynamic solution that remains compatible with V5.3 safety doctrine.

## 11. External Scientific and Production References

- Jacobs, Jordan, Nowlan, Hinton, *Adaptive Mixtures of Local Experts* (1991)
- Jordan and Jacobs, *Hierarchical Mixtures of Experts and the EM Algorithm* (1994)
- Li, Chu, Langford, Schapire, *A Contextual-Bandit Approach to Personalized News Article Recommendation* (WWW 2010)
- Li, Chu, Langford, Wang, *Unbiased Offline Evaluation of Contextual-bandit-based News Article Recommendation Algorithms* (WSDM 2011)
- Laroche et al., *Safe Policy Improvement with Baseline Bootstrapping* (2017/2018)
- Istio traffic mirroring guidance
- Google Cloud canary deployment guidance
