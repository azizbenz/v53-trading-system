# PAGE_SOURCE_DISCOVERY_MATRIX

## Overview
- Route: `/`
- Template: `src/cockpit/templates/index.html`
- Partials: `partials/_stat_card.html, partials/_system_flow.html, partials/_source_freshness.html, partials/_queue_trace.html, partials/_service_liveness.html, partials/_warmup_explainer.html, partials/_kill_proof.html, partials/_disk_growth.html, partials/_pair_selector.html, partials/_action_panel.html, partials/_engines_grid.html, partials/_replay_metrics.html, partials/_capacity_guard.html, partials/_lab_review.html, partials/_refusal_journal.html, partials/_model_risk.html, partials/_hlz_guard.html, partials/_calibration_thresholds.html, partials/_feature_bridge.html, partials/_sizing_chain.html`
- VM roots: `artefacts, calibration, capacity_guard, current_page, engines, feature_bridge, grafana_url, lab_review, metrics, model_risk, multiple_testing, operational_proof, operational_proof.disk_growth, operational_proof.freshness, operational_proof.kill_proof, operational_proof.queue_trace, operational_proof.service_liveness, operational_proof.system_flow, operational_proof.warmup_explainer, pairs, refusal_journal, replay, runtime, runtime.alerts, selected_pair, sizing_chain, tail_risk, welcome_message`
- VM paths discovered: `157`

## Backtest
- Route: `/backtest`
- Template: `src/cockpit/templates/pages/backtest.html`
- Partials: `none`
- VM roots: `runtime, runtime.backtest_jobs, runtime.backtest_summary, welcome_message`
- VM paths discovered: `7`

## IA Lab
- Route: `/lab`
- Template: `src/cockpit/templates/pages/lab.html`
- Partials: `partials/_run_comparison.html, partials/_lab_vps_transfer.html, partials/_lab_review.html, partials/_refusal_journal.html, partials/_model_risk.html, partials/_hlz_guard.html, partials/_calibration_thresholds.html`
- VM roots: `calibration, feature_bridge, lab_review, model_risk, multiple_testing, operational_proof, operational_proof.lab_vps_transfer, operational_proof.queue_trace, operational_proof.run_comparison, refusal_journal, runtime, runtime.artifact_family_comparisons, runtime.artifact_family_visibility, runtime.artifact_verdict_bundle, runtime.queue_snapshot, tail_risk, welcome_message`
- VM paths discovered: `89`

## Logs
- Route: `/logs`
- Template: `src/cockpit/templates/pages/logs.html`
- Partials: `none`
- VM roots: `runtime, runtime.recent_logs, welcome_message`
- VM paths discovered: `8`

## Observability
- Route: `/observability`
- Template: `src/cockpit/templates/pages/observability.html`
- Partials: `none`
- VM roots: `grafana_url, prometheus_url, runtime, runtime.observability, welcome_message`
- VM paths discovered: `19`

## Shadow
- Route: `/shadow`
- Template: `src/cockpit/templates/pages/shadow.html`
- Partials: `partials/_service_liveness.html, partials/_queue_trace.html, partials/_warmup_explainer.html, partials/_data_quality.html, partials/_pair_universe_control.html`
- VM roots: `operational_proof, operational_proof.data_quality, operational_proof.queue_trace, operational_proof.service_liveness, operational_proof.warmup_explainer, pairs, runtime, runtime.alerts, runtime.artifact_comparisons, runtime.artifact_runtime_visibility, runtime.artifact_verdict_bundle, welcome_message`
- VM paths discovered: `53`

## Trading
- Route: `/trading`
- Template: `src/cockpit/templates/pages/trading.html`
- Partials: `partials/_stat_card.html, partials/_engine_why.html, partials/_economic_sterilization.html, partials/_decision_trace.html, partials/_data_quality.html, partials/_engines_grid.html, partials/_replay_metrics.html, partials/_capacity_guard.html, partials/_feature_bridge.html, partials/_calibration_thresholds.html, partials/_sizing_chain.html`
- VM roots: `calibration, capacity_guard, engines, feature_bridge, metrics, operational_proof, operational_proof.data_quality, operational_proof.decision_trace, operational_proof.economic_sterilization, operational_proof.engine_why, operational_proof.system_flow, replay, selected_pair, sizing_chain, welcome_message`
- VM paths discovered: `66`

## VPS
- Route: `/vps`
- Template: `src/cockpit/templates/pages/vps.html`
- Partials: `partials/_disk_growth.html, partials/_service_liveness.html, partials/_queue_trace.html`
- VM roots: `operational_proof, operational_proof.disk_growth, operational_proof.queue_trace, operational_proof.service_liveness, runtime, runtime.alerts, runtime.monitoring_payload, welcome_message`
- VM paths discovered: `51`

