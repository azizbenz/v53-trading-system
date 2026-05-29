# B1 Features vs Tradability vs Expected Edge Audit

Date: `2026-05-26`  
Workflow: `strategy_ladder_workflow-37dc7b57d1ac8aaa`  
Scope: `PHASE_B1_CANDIDATE_DISCOVERY`

## Executive Verdict

| Question | Verdict | Audit proof |
| --- | --- | --- |
| Les features sont-elles calculees ? | `YES_PARTIAL_FOR_ORDERBOOK_MICROSTRUCTURE` | `candidate_events.jsonl` montre `200/200` pour les features coeur et `192/200` pour les features dependantes du book |
| Peut-on deja conclure qu'un candidat est tradable ? | `NO` | `preselection_status=ENGINE_NATIVE_PRESELECTION_NOT_PROVEN` et `candidate_truth_status=CANDIDATE_ENGINE_NATIVE_IN_PROGRESS` dans `run_manifest.progress.json` |
| Les candidats B1 sont-ils encore discovery-only ? | `YES` | `candidate_source=COMPAT_FEATURE_DISCOVERY` dans `candidate_events.jsonl` |
| A-t-on supprime les blockers proxy sur expected edge ? | `NO` | `expected_edge_truth_status=EXPECTED_EDGE_PROXY_BLOCKED` |
| A-t-on un expected edge gouverne / truth pour ce run ? | `NO` | `expected_edge_governed_count=0`, `expected_edge_proxy_count=100`, `expected_edge_label_fidelity=EXPECTED_EDGE_PROXY_DISCOVERY_ONLY` |
| Peut-on utiliser ce run pour prouver la rentabilite / execution truth ? | `NO` | `execution_label_source=REPLAY_PROXY_EXECUTION`, `fee_model_source=REPLAY_PROXY`, `spread_model_source=REPLAY_PROXY`, `slippage_model_source=REPLAY_PROXY` |

## Feature Presence Audit

Source of truth:

- `phase_b1_candidate_discovery/backtest_strategy_ladder/.../fast_candidates/candidate_events.jsonl`
- `phase_b1_candidate_discovery/backtest_strategy_ladder/.../reports/backtest_feature_engine_ml_wiring_audit.json`

| Feature | Selected in current B1 run | Present on candidate rows | Coverage | Interpretation |
| --- | --- | --- | --- | --- |
| `close_return` | yes | yes | `200/200` | Kline/trade shared feature, fully available |
| `high_low_range` | yes | yes | `200/200` | Kline shared feature, fully available |
| `volume` | yes | yes | `200/200` | Kline/trade shared feature, fully available |
| `spread_bps` | yes | yes | `200/200` | Economic discovery feature present on all rows |
| `slippage_bps` | yes | yes | `200/200` | Economic discovery feature present on all rows |
| `book_depth_levels` | yes | yes | `192/200` | Missing on `8` rows where orderbook feature readiness is not proven |
| `vpin` | yes | yes | `192/200` | Orderbook/trade microstructure feature, partial coverage |
| `cumulative_ofi` | yes | yes | `192/200` | Orderbook microstructure feature, partial coverage |
| `realized_vol_current` | yes | yes | `192/200` | Runtime microstructure/vol feature, partial coverage |

## Extra Features Already Materialized Even If Not In Active Selection

| Feature | Present on rows | Coverage | Note |
| --- | --- | --- | --- |
| `fragility` | yes | `200/200` | Discovery-grade derived feature |
| `fragility_score` | yes | `200/200` | Same rail as `fragility` |
| `sweep_score` | yes | `200/200` | Discovery-grade microstructure proxy |
| `false_breakout_context` | yes | `200/200` | Discovery-grade context feature |
| `break_even_bps` | yes | `200/200` | Economic discovery feature |
| `trade_count_hint` | yes | `200/200` | Audit helper / upstream context |
| `session_tags` | yes | `200/200` | Context tagging, not a direct tradability proof |

## Tradability Decision Matrix

| Layer | Current status | What it means |
| --- | --- | --- |
| Feature presence | `PARTIAL_READY` | Feature rows exist and are exploitable for discovery audit |
| Candidate discovery export | `READY` | `200` candidates exported, `50` per engine |
| Native engine preselection | `NOT_PROVEN_YET` | No canonical `preselection_candidates.jsonl` yet |
| B1 pass/reject decision | `NOT_PROVEN_YET` | No native pass list / rejection ledger terminalized yet |
| B2 replay truth | `NOT_STARTED_FOR_THIS_WORKFLOW` | No B2 replay evidence yet |
| Execution realism truth | `NOT_PROVEN` | Current run still cites proxy execution sources |
| Expected edge truth | `BLOCKED` | Expected edge is still proxy-blocked |
| Tradeable candidate verdict | `NO` | Feature presence alone is insufficient |

## Why Features Present Does Not Mean Tradable

| Audit point | Current proof |
| --- | --- |
| Candidate rows are still on the discovery rail | `candidate_source=COMPAT_FEATURE_DISCOVERY` |
| Native engine materialization is still running | `candidate_discovery_status=CANDIDATE_DISCOVERY_ENGINE_NATIVE_IN_PROGRESS` |
| Native preselection not finished | `preselection_status=ENGINE_NATIVE_PRESELECTION_NOT_PROVEN` |
| Candidate truth not finalized | `candidate_truth_status=CANDIDATE_ENGINE_NATIVE_IN_PROGRESS` |
| No canonical B1 preselection output yet | `preselection_candidates.jsonl` absent at audit time |
| No canonical B1 summary yet | `reports/strategy_ladder_summary.json` absent at audit time |

## Expected Edge / Proxy Status

Source of truth:

- `run_manifest.progress.json`

| Field | Current value | Audit meaning |
| --- | --- | --- |
| `expected_edge_truth_status` | `EXPECTED_EDGE_PROXY_BLOCKED` | Expected edge cannot be treated as truth |
| `expected_edge_proxy_count` | `100` | Proxy expected-edge usage still present |
| `expected_edge_governed_count` | `0` | No governed expected-edge truth rows |
| `expected_edge_model_status` | `GOVERNED_EDGE_MODEL_NOT_REQUESTED` | No governed ML edge authority requested for this run |
| `expected_edge_label_fidelity` | `EXPECTED_EDGE_PROXY_DISCOVERY_ONLY` | Labels are still proxy/discovery grade |
| `execution_label_source` | `REPLAY_PROXY_EXECUTION` | Execution truth is not yet replay-governed |
| `fee_model_source` | `REPLAY_PROXY` | Cost truth still proxy |
| `spread_model_source` | `REPLAY_PROXY` | Cost truth still proxy |
| `slippage_model_source` | `REPLAY_PROXY` | Cost truth still proxy |

## Bottom Line

| Statement | Verdict |
| --- | --- |
| `Les features sont calculees` | `YES` |
| `Les features suffisent pour dire tradable/non tradable` | `NO` |
| `On n'a plus de blocker proxy sur expected edge` | `FALSE` |
| `Le run peut deja prouver expected edge truth` | `NO` |
| `Le run peut deja prouver execution / profitability truth` | `NO` |
| `Le run est utile pour audit B1 discovery + feature coverage` | `YES` |
