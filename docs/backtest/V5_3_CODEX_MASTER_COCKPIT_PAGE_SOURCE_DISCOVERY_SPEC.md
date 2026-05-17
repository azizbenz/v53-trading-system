# V5.3 — MASTER COCKPIT PAGE SOURCE DISCOVERY SPEC
## Final Codex MD: discover what already exists before extending each cockpit page

**Scope:** Entire V5.3 cockpit/dashboard system  
**Repo root example:** `E:\claude v5.3\v53_trading_system`  
**Observed source tree:** `src/` contains major domains such as `cockpit`, `monitoring`, `local_replay_runtime`, `meta_learning`, `meta_minimal`, `data_backbone`, `engines`, `execution_backbone`, `protocols`, `interface_contracts`, `calibration_methods`, `risk_backbone`, `regime_classifier`, `venue_adapters`, `portfolio`, `portfolio_minimal`, `secrets_manager`, `sharia_compliance`, and others.

---

# 0. Executive Decision

Before adding or changing dashboard content, Codex must first discover what the repo already exposes.

The cockpit must not invent metrics, formulas, state, readiness, ML proof, queue proof, or trading conclusions.

For every page, Codex must answer:

```text
What is already available in code?
What is already available in runtime files/reports?
What is already displayed?
What exists but is not displayed?
What is scientifically required but missing?
What requires backend/domain implementation?
What must remain NOT_YET_PERSISTED?
```

This MD is a **master discovery and integration spec** for the 7 cockpit pages:

```text
Overview
Trading
Shadow
VPS
IA Lab
Backtest
Logs
Observability
```

If the actual cockpit has exactly 7 pages and no separate Overview domain, Codex must adapt the list to the current nav structure and report the exact pages found.

---

# 1. Golden Rule

```text
Discover first.
Map second.
Display third.
Never invent.
Never mutate backend.
```

A dashboard value is allowed only if it comes from one of these:

```text
1. Existing report/runtime file
2. Existing state adapter
3. Existing domain formula/function
4. Explicit display-only operational diagnostic allowed by page spec
```

If none exists:

```text
Display: MISSING / NOT_YET_PERSISTED / FORMULA_SOURCE_MISSING / UNKNOWN
```

---

# 2. Mandatory Domain Ownership

Each page owns one domain.

| Page | Owns | Does not own |
|---|---|---|
| Overview | Compact global status only | Deep diagnostics |
| Trading | Engines, pair behavior, decisions, costs, sizing, feature integrity | VPS infra, backtest formulas, IA Lab model risk |
| Shadow | Warmup, eligible_to_trade, readiness, blockers, shadow verdict, control proof | Trading decision details, VPS CPU/RAM full diagnostics |
| VPS | Host/process/heartbeat/queue/disk/network/time-sync/kill proof | Engine/pair trading analytics |
| IA Lab | ML artifacts, post-trade review, model risk, HLZ, calibration, transfer proof | Live trading decisions, VPS process internals |
| Backtest | Historical/replay job quality, formulas, artifacts, reproducibility | Live runtime state |
| Logs | Event forensics, trace IDs, parse errors, error rate, timelines | Domain-specific business interpretation |
| Observability | Prometheus/Grafana/bridge/scrape/metric coverage/dashboards | Trading or ML conclusions |

Shared metrics may appear as compact badges only:

```text
service_status
queue_status
source_freshness
run_id
last_update_age
```

Full diagnostic tables must appear only on the owner page.

---

# 3. Non-Negotiable Safety Rules

## R1 — Dashboard is read-only by default

Forbidden in page state adapters unless an existing governed form already exists and is explicitly in scope:

```text
write_text
write_bytes
atomic_write
os.kill
signal
queue writes
engine activation
runtime mutation
artifact activation
model training
threshold mutation
credential mutation
live/micro-live promotion
```

## R2 — No formula invention in display layer

Dashboard adapters may not implement missing quant formulas.

Forbidden to implement in cockpit display code:

```text
PSR
DSR
HLZ
POT-GPD
Energy distance
Sharpe / Sortino if not already present
CVaR if not already present
VPIN
PIN
OFI
Kyle lambda
Amihud
Roll spread
Corwin-Schultz
realized kernel volatility
Hawkes intensity
slippage model
fill probability
toxicity model
directional ML labels
```

If such formula exists in domain code/reports, display it with source.

If absent:

```text
FORMULA_SOURCE_MISSING
```

## R3 — No secrets

Never render:

```text
api_key
api_secret
password
token
private_key
authorization
cookie
raw credential bundle
```

Allowed:

```text
credential status
credential inventory count
active profile id
last validation time
```

## R4 — Missing source is an honest result

A missing source is not a failure of the dashboard if displayed honestly.

Correct outputs:

```text
MISSING
STALE
PARSE_ERROR
NOT_YET_PERSISTED
UNKNOWN
FORMULA_SOURCE_MISSING
```

---

# 4. Repo Source Map Codex Must Use

Codex must scan the following source folders and map them to cockpit pages.

## 4.1 `src/cockpit/`

Primary UI/state domain.

Look for:

```text
templates/pages/*.html
templates/partials/*.html
state*.py
server.py
routes*.py
view models
page-specific adapters
```

This folder tells what is already displayed or partially available.

---

## 4.2 `src/monitoring/`

Owner for observability and monitoring stack.

Look for:

```text
Prometheus exporters
Grafana builders
dashboard bootstrap
metrics bridge
prom text emitters
observability summaries
```

Relevant pages:

```text
Observability
VPS
Shadow
Overview
```

---

## 4.3 `src/local_replay_runtime/`

Owner for replay/backtest/export outputs.

Look for:

```text
replay metrics
DTR records
feature bridge
parity diagnostics
run manifests
local lab replay outputs
artifact export seams
```

Relevant pages:

```text
Backtest
Trading
IA Lab
Shadow
```

---

## 4.4 `src/backtest_artifact_import/`

Owner for import/export bridge and artifact ingestion.

Look for:

```text
export_dir bridge
artifact import contracts
manifest validation
hash validation
```

Relevant pages:

```text
Backtest
IA Lab
Shadow
```

---

## 4.5 `src/calibration_methods/` and `src/calibration_loader/`

Owner for quant formulas/calibration anchors.

Look for:

```text
PSR
DSR
POT-GPD
Energy distance
HLZ/multiple testing
thresholds
calibration reports
```

Relevant pages:

```text
Backtest
IA Lab
Trading only via displayed thresholds/values
```

Do not reimplement these in cockpit.

---

## 4.6 `src/meta_learning/` and `src/meta_minimal/`

Owner for post-trade review, learning records, hypotheses, candidates.

Look for:

```text
meta_learning_review.bundle.json writers
mistake classes
hypothesis lifecycle
candidate lifecycle
merge gates
capacity guard
model risk hooks
post-trade review writers
```

Relevant pages:

```text
IA Lab
Backtest
Logs
```

---

## 4.7 `src/data_backbone/`

Owner for data and microstructure features.

Look for:

```text
L2/L3 data
order book snapshots
trades
walls/spoofing
microstructure features
feature dictionaries
data quality checks
```

Relevant pages:

```text
Trading
Backtest
Shadow
```

---

## 4.8 `src/engines/`

Owner for engine A/B/C/D logic.

Look for:

```text
engine outputs
engine status
engine scoring
engine candidates
records
blocked reasons
side semantics
```

Relevant pages:

```text
Trading
Backtest
```

Do not modify engine semantics during dashboard work.

---

## 4.9 `src/execution_backbone/`

Owner for runtime/execution/reconciliation.

Look for:

```text
service loop
heartbeat
fills/orders
remote account state
bootstrap reconciliation
execution runtime status
kill/halt support
```

Relevant pages:

```text
VPS
Shadow
Trading badge only
```

---

## 4.10 `src/protocols/` and `src/interface_contracts/`

Owner for contracts, command queue, refusal seams, forecast contracts.

Look for:

```text
dashboard_command_queue
dashboard command execution support
forecast contracts
refusal records
queue result records
interface contracts
runtime state schemas
```

Relevant pages:

```text
Shadow
VPS
IA Lab
Logs
```

Do not mutate protocols during dashboard display work.

---

## 4.11 `src/risk_backbone/`, `src/regime_classifier/`, `src/scoring_backbone/`

Owner for risk/regime/scoring signals.

Look for:

```text
regime detector outputs
toxicity score
risk gates
score breakdown
sizing/scoring contracts
```

Relevant pages:

```text
Trading
IA Lab
Backtest
Shadow
```

Do not create directional labels in VPS regime detector.

---

## 4.12 `src/portfolio/`, `src/portfolio_minimal/`

Owner for portfolio/exposure/capital views.

Look for:

```text
positions
exposure
portfolio state
sizing caps
allocation rules
```

Relevant pages:

```text
Trading
VPS compact summary
Backtest
```

---

## 4.13 `src/venue_adapters/`

Owner for exchange connectivity.

Look for:

```text
Binance spot adapter
time sync
websocket health
rate limits
REST latency
symbol filters
fees
min notional
```

Relevant pages:

```text
VPS
Shadow
Trading
```

Do not display secrets.

---

## 4.14 `src/secrets_manager/`

Owner for secret handling.

Relevant pages:

```text
VPS credential summary only
Shadow credential readiness only
```

Never display raw secrets.

---

## 4.15 `src/sharia_compliance/`

Owner for halal constraints.

Relevant pages:

```text
Trading
IA Lab
Backtest
Shadow
```

Must ensure dashboard never promotes short/leverage states.

---

# 5. Mandatory Discovery Workflow

Codex must perform this workflow before modifying any page.

## Step A — Page inventory

Run or equivalent:

```bash
dir src\cockpit\templates\pages
dir src\cockpit\templates\partials
dir src\cockpit
```

Output:

```text
List of pages found
List of partials found
List of state adapters found
```

## Step B — Existing dashboard render inventory

For each page, extract all `vm.*` references.

Example command:

```bash
grep -R "vm\." -n src/cockpit/templates/pages src/cockpit/templates/partials
```

Output:

```text
page
template
vm path
owner page
state adapter if found
```

## Step C — Source adapter inventory

Scan:

```bash
grep -R "class .*Snapshot\|def build_\|def load_\|def read_\|BaseModel" -n src/cockpit
```

Output:

```text
adapter file
models
functions
inputs
outputs
pages using it
```

## Step D — Runtime file inventory

Search existing files:

```bash
dir /s /b build\*.json
dir /s /b build\*.jsonl
dir /s /b build\*.yml
dir /s /b build\*.yaml
dir /s /b logs\*.log
dir /s /b outputs\*.json
```

Or PowerShell:

```powershell
Get-ChildItem -Recurse build,logs,outputs -Include *.json,*.jsonl,*.yml,*.yaml,*.log -ErrorAction SilentlyContinue
```

Output:

```text
file path
mtime
size
likely owner page
schema guess
parse status
```

## Step E — Formula/code source inventory

Search formulas and key metrics:

```bash
grep -R "ce_net\|gross_return\|expected_cost\|realized_cost\|slippage\|drawdown\|sharpe\|sortino\|cvar\|psr\|dsr\|vpin\|ofi\|kyle\|amihud\|hawkes\|realized_kernel\|energy\|pot\|gpd" -n src tests
```

Output:

```text
metric/formula
code file
function/class
page that may display it
status: report/code/missing/forbidden_in_dashboard
```

---

# 6. Required Master Outputs

Codex must create/update these audit artifacts under a safe docs/audit folder, or print them if file writing is not in scope.

```text
docs/cockpit/PAGE_SOURCE_DISCOVERY_MATRIX.md
docs/cockpit/PAGE_METRIC_OWNERSHIP_MATRIX.md
docs/cockpit/PAGE_FORMULA_SOURCE_LEDGER.md
docs/cockpit/PAGE_MISSING_SOURCE_BACKLOG.md
docs/cockpit/PAGE_DUPLICATION_AUDIT.md
```

If writing docs is forbidden in current task, output the same sections in the Codex response.

---

# 7. PAGE_SOURCE_DISCOVERY_MATRIX.md

Must contain for each page:

```text
Page
Template file
Existing partials
Existing state adapters
Existing vm paths
Existing runtime files used
Missing runtime files
Source freshness available?
Parse-error handling available?
Tests found?
```

---

# 8. PAGE_METRIC_OWNERSHIP_MATRIX.md

Must contain:

```text
metric_id
display_name
owner_page
allowed_as_badge_on_pages
full_detail_page
source_type
source_file_or_code
current_display_status
missing_status
```

Example:

```text
queue_consumption_status
Queue Consumption
VPS / Shadow
Trading, IA Lab as badge
VPS full detail
dashboard_command_queue snapshot
currently displayed partial
ok
```

---

# 9. PAGE_FORMULA_SOURCE_LEDGER.md

Must contain:

```text
metric_id
formula_family
owner_page
source_status
report_source
code_source
dashboard_fallback_allowed
dashboard_currently_computes
should_be_removed_from_dashboard
missing_backlog_target
```

Allowed `source_status`:

```text
REPORT_VALUE_FOUND
CODE_FORMULA_FOUND
DISPLAY_OPERATIONAL_DIAGNOSTIC
FORMULA_SOURCE_MISSING
NOT_YET_PERSISTED
FORBIDDEN_IN_DASHBOARD
```

---

# 10. PAGE_MISSING_SOURCE_BACKLOG.md

Must contain missing items grouped by page:

```text
Page
Missing source
Why needed
Current dashboard behavior
Required backend producer
Required test
Priority P0/P1/P2
```

Priority rules:

```text
P0 = false safety risk / operator could be misled
P1 = important observability gap
P2 = nice-to-have detail
```

---

# 11. PAGE_DUPLICATION_AUDIT.md

Must identify duplicate full sections across pages.

For every duplicate:

```text
section_name
pages_where_present
owner_page
should_remain_badge_on
should_remove_or_collapse_on
reason
```

Examples:

```text
Queue Trace full detail
Owner: VPS/Shadow
Allowed badge: Trading/IA Lab
```

---

# 12. Per-Page Discovery Questions

Codex must answer these per page.

## 12.1 Trading

```text
Which engine metrics already exist?
Which pair metrics already exist?
Is engine x pair matrix available?
Is DTR decision trace available?
Is score anatomy available?
Which cost fields exist?
Which microstructure features exist?
Which formulas are report values vs code formulas?
Which missing formulas must not be implemented in cockpit?
```

## 12.2 Backtest

```text
Which runner records exist?
Which export_dir files exist?
Which formula/report values exist?
Which statistical reports exist?
Which formula sources exist in code?
Which formulas are forbidden fallback?
Which reproducibility hashes exist?
```

## 12.3 Shadow

```text
Which warmup summary exists?
Which checks exist?
Which blockers exist?
Is eligible_to_trade present?
Is service live or archive-only?
Is queue consumption proven?
Are artifact verdict bundles present?
Are comparison samples sufficient?
```

## 12.4 VPS

```text
Which host metrics exist?
Is PID tracked?
Is heartbeat fresh?
Is queue consumed by service?
Is kill proof present?
Is time sync exposed?
Is network/websocket health exposed?
Are credentials summarized without secrets?
```

## 12.5 IA Lab

```text
Which post-trade review bundle exists?
Which mistake classes exist?
Which hypotheses/candidates exist?
Which ML artifact metadata exists?
Which training/evaluation reports exist?
Which model risk registry exists?
Which HLZ/multiple-testing files exist?
Which Local→VPS hash matches exist?
```

## 12.6 Logs

```text
Which durable event logs exist?
Which event fields exist?
Are timestamps parseable?
Are run/job/command/correlation IDs present?
Are parse errors counted?
Are secrets redacted?
Are repeated errors detectable?
```

## 12.7 Observability

```text
Is Prometheus reachable?
Is Grafana reachable?
Is bridge reachable?
Is prom text present and fresh?
Which metric names are emitted?
Which expected refs are missing?
Are dashboards imported?
Are dashboard UIDs stable?
Are alert rules present?
```

## 12.8 Overview

If Overview exists:

```text
Which global summary badges are shown?
Are they duplicated from owner pages?
Are they source-mapped?
Does overview hide any critical red state?
```

---

# 13. Implementation Rule After Discovery

After discovery, Codex may extend a page only under these conditions:

```text
1. The owner page is correct.
2. The metric source exists or missing state is honest.
3. The formula source is mapped.
4. No backend protected module is modified.
5. Tests prove page survives missing sources.
6. No secret exposure.
7. No mutation from page adapters.
```

---

# 14. Global Tests to Add

Codex must add high-level cockpit integrity tests.

```text
tests/cockpit/test_page_ownership_matrix.py
tests/cockpit/test_page_source_discovery_matrix.py
tests/cockpit/test_no_formula_in_templates.py
tests/cockpit/test_no_backend_mutation_from_dashboard.py
tests/cockpit/test_no_secret_exposure_templates.py
tests/cockpit/test_all_pages_survive_missing_sources.py
tests/cockpit/test_shared_badges_not_full_duplicate_sections.py
```

## Required assertions

```text
All pages render with missing sources.
No Jinja template contains quant formulas.
No state adapter writes, kills, mutates queue, trains model, or activates artifacts.
No raw secret field is rendered.
Every displayed formula metric has ledger entry.
Every full diagnostic section has a single owner page.
```

---

# 15. Guardrails

Run:

```bash
python -m pytest tests/cockpit/ -q
python -m py_compile src/cockpit/*.py
python scripts/run_engineering_guardrails.py
```

Run mutation check:

```bash
grep -R -E "write_text|write_bytes|atomic_write|os.kill|signal\.|fit\(|partial_fit\(|train\(|requests\.post|requests\.put|requests\.delete" src/cockpit
```

Expected:

```text
0 matches in read-only state adapters
```

Run template formula check:

```bash
grep -R -E "\+|\-|\*|/|sqrt|mean|std|quantile|sharpe|sortino|cvar|psr|dsr|vpin|ofi|kyle|amihud" src/cockpit/templates
```

Expected:

```text
No financial/math formulas in templates.
Simple HTML/CSS/formatting exceptions must be manually justified.
```

Run secret exposure check:

```bash
grep -R -iE "api_secret|api_key|password|token|private_key|authorization|cookie" src/cockpit/templates
```

Expected:

```text
0 raw secret values displayed.
```

Run backend protection check:

```bash
git diff src/engines src/protocols src/interface_contracts src/calibration_methods src/meta_learning src/meta_minimal src/execution_backbone src/model_risk_registry src/venue_adapters src/secrets_manager
```

Expected:

```text
empty
```

---

# 16. Codex Required Output Format

Codex must return exactly:

```text
1. Src Tree Confirmation
2. Cockpit Page Inventory
3. Existing State Adapter Inventory
4. Runtime File Inventory
5. Per-Page Source Discovery Matrix
6. Per-Page Metric Ownership Matrix
7. Formula Source Ledger
8. Missing Source Backlog
9. Duplication Audit
10. Proposed Page-Specific Next Tasks
11. Tests Added
12. Test Results
13. Guardrail Proof
14. Remaining Gaps
15. Completion Status
```

Allowed completion statuses:

```text
DISCOVERY_COMPLETE
DISCOVERY_PARTIAL
BLOCKED_BY_REPO_ACCESS
BLOCKED_BY_PARSE_ERRORS
```

Do not return `COMPLETE` for implementation unless page modifications and tests are also done.

---

# 17. Recommended Next Work Order After Discovery

Codex must recommend next implementation order based on red-risk, but default order is:

```text
1. VPS page — false safety / process / queue / kill proof
2. Shadow page — readiness / blockers / eligible_to_trade
3. Trading page — decision quality / cost / feature integrity
4. IA Lab page — ML/post-trade/artifact proof
5. Backtest page — formula/reproducibility review
6. Logs page — forensics and redaction
7. Observability page — monitoring plumbing
8. Overview page — compact global summary only
```

If discovery shows a worse P0 elsewhere, Codex may reprioritize with evidence.

---

# 18. Final Reminder

The cockpit must become a **truth surface**.

Correct behavior:

```text
Data exists -> display with source.
Data missing -> display missing.
Formula exists -> display with formula source.
Formula missing -> do not implement in cockpit.
Page owns domain -> show full detail.
Page does not own domain -> show compact badge only.
Operator could be misled -> P0.
```

This MD is the master instruction to stop dashboard drift and make every page source-mapped, scientific, and prod-safe.
