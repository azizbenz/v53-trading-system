# P0-B Dashboard Formula Display Policy

- Dashboard may display report-loaded values and source labels.
- Dashboard may not recompute quant/statistical/microstructure formulas locally.
- `display_allowed=source_label_only` means the cockpit can show provenance, owner page, tests, docs, and warnings, but not claim local recomputation.
- `display_allowed=report_value_only` means the cockpit can display persisted/measured values with explicit source status.
- `PLACEHOLDER_DEFAULT` must never appear near a green verdict as a measured value.
- `NOT_YET_PERSISTED` or missing runtime evidence must remain explicit.
- Formula owner page must stay visible:
  - Trading for engines/microstructure/score-cost synthesis
  - Backtest for replay/calibration/profitability provenance
  - VPS for service/queue/kill/disk/runtime diagnostics
  - Shadow for readiness/verdict
  - IA Lab for ML/regime/artifact provenance
  - Observability for scrape/bridge/Prometheus/Grafana health