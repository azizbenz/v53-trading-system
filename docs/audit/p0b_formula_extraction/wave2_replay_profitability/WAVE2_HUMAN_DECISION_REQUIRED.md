# Wave 2 Human Decisions Required

## 1. CE semantic display boundary
- Current formula is clear:
  - `ce_net` is expected CE net of expected cost
- Decision still required:
  - should the cockpit label it `expected_ce_net`
  - or keep `ce_net` but attach an explicit “expected, not realized” qualifier

## 2. Exec-rate denominator naming
- Current code uses:
  - `executed_count / total_records`
- One backtest dashboard spec documents:
  - `executed_count / max(selected_count, 1)`
- Decision required:
  - keep current metric as `exec_rate_total`
  - and later add `selected_execution_rate`
  - or redefine the displayed metric and migrate consumers

## 3. Drawdown proxy promotion eligibility
- Current `drawdown_proxy` is not true max drawdown.
- Decision required:
  - whether promotion/risk review may use this proxy at all
  - or whether a true net-equity drawdown seam is required first

## 4. Sample-size threshold governance
- Current replay-related sample warnings use `30` in several cockpit surfaces.
- Decision required:
  - whether `30` remains a display-only warning
  - or whether replay economics should adopt a governed threshold catalog entry

## 5. Realized-cost interpretation on replay page
- Current `realized_cost_mean` is an all-record mean, not an executed-only mean.
- Decision required:
  - whether this is sufficient for replay display
  - or whether a separate executed-only realized-cost view is needed later

## 6. Stale replay artifact policy
- Freshness logic exists in `state_freshness.py`.
- Replay snapshot state itself does not carry a replay-economics freshness verdict.
- Decision required:
  - whether stale replay metrics must hard-block green economics in cockpit state adapters
