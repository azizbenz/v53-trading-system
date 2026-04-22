# Build 2 Repo-Truth Audit - Data Backbone - 2026-04-22

## Scope

This note audits **Build 2** only:

- `data_backbone.websocket_gateway*`
- `data_backbone.event_normalizer*`
- `data_backbone.freshness_checker*`
- `data_backbone.consistency_checker*`
- `data_backbone.internal_router*`
- `data_backbone.rest_bootstrap*`
- `data_backbone.pair_health_scorer*`
- `data_backbone.microstructure*`
- `data_backbone.market_physics_math`
- `regime_classifier.regime_lite`

It answers one question:

> Does current Build-2 code match the doctrinal expectation closely enough, or
> is there meaningful drift between the expected Data Backbone and the real
> implementation?

## Doctrine Claim

Current doctrinal baseline is the combination of:

- `src/manifest_registry/build_order_registry.py`
- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`

Repo-doctrine summary for Build 2:

- Build 2 is the governed **Data Backbone** stage.
- It must own:
  - WS ingestion
  - normalization
  - data quality / consistency
  - pair health
- It must remain typed, observable, and fail-closed where required.
- The canonical build order also places `regime_classifier` inside the same
  stage.
- Later docs 19/20 additionally describe richer microstructure and market-data
  features such as OFI, VPIN, queue pressure, realized kernel vol, spread
  dynamics, and related market-physics inputs.

## Repo-Truth Surface

### 1. Build 2 is a real multi-rail data stage, not just a websocket shim

Observed in:
- `src/data_backbone/__init__.py`

Current repo-truth Build-2 surface includes:
- `websocket_gateway`
- `rest_bootstrap`
- `event_normalizer`
- `internal_router`
- `freshness_checker`
- `consistency_checker`
- `pair_health_scorer`
- `microstructure`
- `market_physics_math`

Interpretation:
- Build 2 is not a thin transport helper
- it is already a broad governed data stage with both transport and feature seams

### 2. Ingress and timestamp handling are real and typed

Observed in:
- `src/data_backbone/websocket_gateway/runtime_gateway.py`
- `src/data_backbone/event_normalizer/timestamp_enricher.py`

Current repo-truth ingress surface includes:
- typed `AdapterMessage`
- injectable `WebSocketGatewayRuntime`
- explicit `recv_time` on emitted raw messages
- heartbeat / reconnect / backlog / utilization visibility
- typed timestamp enrichment with:
  - `recv_time`
  - `exchange_time`
  - `drift_s`
  - `latency_s`

Interpretation:
- ingress timestamps are real and auditable
- current Build 2 measures reception-side timing slices
- it does **not** by itself provide a full signal-to-order latency metric

### 3. Build 2 already owns data quality and readiness seams beyond parsing

Observed in:
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/test_freshness_checker.py`
- `tests/test_data_backbone/test_consistency_checker.py`
- `tests/test_data_backbone/test_pair_health_scorer.py`
- `tests/test_data_backbone/test_rest_bootstrap.py`

Current repo-truth also includes:
- freshness tracking and stale penalties
- consistency checking for gaps / duplicates / contradictions
- internal routing / queue / backpressure seams
- REST bootstrap and gap-fill runtime
- pair health aggregation, suspension, and recovery logic

Interpretation:
- Build 2 is already a governed operational data-quality rail
- it is not limited to message parsing or transport normalization

### 4. Later microstructure doctrine has already landed materially in code

Observed in:
- `src/data_backbone/__init__.py`
- `src/data_backbone/microstructure/`
- `tests/test_data_backbone/microstructure/test_feature_registry.py`

Current repo-truth microstructure surface includes a real feature registry and
typed implementations for canonical features such as:
- OFI
- VPIN
- Kyle lambda
- Amihud illiquidity
- Roll spread
- Corwin-Schultz spread
- realized kernel vol
- Hawkes intensity
- PIN
- queue pressure
- realized effective spread

Interpretation:
- later doc 19/20 feature doctrine is not merely planned here
- a meaningful part of it already exists as real Build-2 source surface

### 5. Market-physics and regime seams are real, but bounded

Observed in:
- `src/data_backbone/market_physics_math.py`
- `src/regime_classifier/regime_lite.py`
- `src/regime_classifier/__init__.py`

Current repo-truth also includes:
- shared market-physics math primitives
- explicit `TO_CALIBRATE` calibration markers for market physics
- typed `RegimeLite` thresholds, memory, and assessments
- bounded calibration seam for `THR-RG01..04`

Interpretation:
- Build 2 already exports operator/runtime-useful physics features
- `regime_classifier` is currently a bounded `regime_lite` seam, not a wider
  classifier family

## Verification Evidence

### Build-2 transport, normalization, quality, feature, and regime bundle

Command:

```powershell
python -m pytest tests/test_data_backbone/test_websocket_gateway.py tests/test_data_backbone/test_event_normalizer.py tests/test_data_backbone/test_freshness_checker.py tests/test_data_backbone/test_consistency_checker.py tests/test_data_backbone/test_internal_router.py tests/test_data_backbone/test_pair_health_scorer.py tests/test_data_backbone/test_rest_bootstrap.py tests/test_data_backbone/test_market_physics_math.py tests/test_data_backbone/microstructure/test_feature_registry.py tests/test_regime_classifier/test_regime_lite.py -q --tb=short
```

Result:
- `216 passed`

### Notes on local sandbox behavior

Observed once during the first run:
- three tests in `test_regime_lite.py` failed under sandbox because their
  calibration fixtures could not create `build/...` temporary directories

Rerun outside the sandbox:
- full command passed with `216 passed`

Interpretation:
- not a Build-2 doctrine/code issue
- no audited Build-2 functional failure

## Observed Divergence

### Divergence 1 - the markdown story is narrower than the current Build-2 code surface

The simplified doctrinal story often compresses Build 2 to:
- WS ingestion
- normalization
- quality
- pair health

Current repo-truth is broader:
- REST bootstrap and gap fill
- internal routing and backpressure
- freshness and consistency rails
- microstructure feature registry and implementations
- shared market-physics math
- bounded `regime_lite` classification

Interpretation:
- this is not dangerous code drift
- it is a documentation compression drift

### Divergence 2 - later docs 19/20 are mixed: several data features are real, but not every future seam is implied

Observed in current code:
- canonical microstructure features are already implemented and tested
- market-physics math is already exported and consumed downstream

Observed in current repo-truth:
- the regime surface is currently bounded to `regime_lite`
- current timestamping is ingress-local, not a full system end-to-end latency seam

Interpretation:
- later markdown is partly ahead of code and partly already landed
- current Build 2 is richer than early doctrine, but still not a universal
  end-to-end timing or full future-regime platform

### Divergence 3 - the build-order description is directionally right but operationally compressed

Observed in:
- `src/manifest_registry/build_order_registry.py`

Current build-order description:
- `Ingestion WS, normalisation, qualite data, sante paire`

Current repo-truth is broader:
- transport runtime
- REST bootstrap
- routing and backpressure
- freshness / consistency
- pair-health governance
- microstructure registry and feature implementations
- market-physics seam
- bounded regime seam

Interpretation:
- the registry description is directionally correct
- but operationally underdescribes the real Build-2 seam

## Decision

`PARTIAL`

## Why

Build 2 is clearly **implemented, typed, and green** on its audited current
surface.

What is already present:
- real websocket gateway runtime
- typed event normalization and timestamp enrichment
- freshness / consistency / router / pair-health rails
- REST bootstrap seam
- real microstructure feature registry and implementations
- shared market-physics math
- bounded typed `regime_lite` classifier

So Build 2 is not `STALE_CODE`, and not broken.

But it is not `MATCH` either, for three concrete reasons:

1. the markdown story underdescribes how broad the current Build-2 surface now is
2. later docs 19/20 are mixed, with several microstructure seams already landed while other broader future timing/regime expectations are still not current repo-truth
3. the build-order description is directionally correct but operationally too compressed for the current implementation

So the correct ruling is:
- Build 2 is operationally real and healthy
- but the doctrinal narrative is narrower in some places and broader in others than the current code-truth

## Patch Target

`docs only`
