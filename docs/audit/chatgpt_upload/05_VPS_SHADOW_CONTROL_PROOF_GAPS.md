# 05 VPS SHADOW CONTROL PROOF GAPS

## Owner conflict
The discovery outputs show that control proof is spread across multiple pages instead of having one hard owner.

### Service liveness duplication
Evidence from `PAGE_DUPLICATION_AUDIT.md`:
- `operational_proof.service_liveness.*` duplicated across:
  - `overview`
  - `shadow`
  - `vps`

Problem:
- `vps` is the doctrinal owner for host/process/runtime liveness
- `shadow` should keep readiness summary, not the full liveness table
- `overview` should keep only a compact badge

### Queue consumption proof duplication
Evidence:
- `operational_proof.queue_trace.*` duplicated across:
  - `overview`
  - `shadow`
  - `vps`
  - and several fields also in `lab`

Problem:
- queue filesystem visibility and service-consumption proof are not the same thing
- duplicating both everywhere creates false control confidence

## Specific control gaps

### 1. Queue consumption proof
Current discovery says the queue trace is owner=`vps`, but it is still copied elsewhere.

Required proof split:
- `VPS`: canonical owner table
- `Shadow`: one-line summary only
- `Overview`: badge only
- `IA Lab`: no deep queue table

### 2. Heartbeat freshness
Duplicated fields:
- `heartbeat_age_seconds`
- `last_heartbeat_at`
- `main_loop_count`
- `pid`
- `pid_is_alive`

Risk:
- operator sees repeated liveness rows and mistakes duplication for independent confirmation

### 3. `archive_reader_only` vs live running
Current proof model already distinguishes:
- `shadow_service_running`
- `control_ready`
- `archive_reader_only`

Gap:
- this should be owned by `VPS`
- `Shadow` should consume the verdict, not re-own the full mechanics

### 4. Kill proof
Even without a large duplication row, kill proof is still a control gap because:
- it is operationally critical
- it appears in the global operability story
- but it does not yet have a single dominant control-proof narrative isolated from the verdict summary

### 5. Command queue status vs command consumption status
Required distinction:
- queue exists
- queue has pending/completed files
- service saw request
- service consumed request
- service completed request

These are separate proof states and should not be merged into one coarse "queue healthy" story.

## P0 remediation target
1. `VPS` owns:
   - `service_liveness.*`
   - `queue_trace.*`
   - `disk_growth.*`
   - heartbeat freshness
   - command queue proof
2. `Shadow` owns:
   - warmup / readiness / blockers
   - shadow verdict
   - pair scope
   - only compact liveness/queue summaries
3. `Overview` keeps only:
   - `Service: ONLINE/OFFLINE`
   - `Queue: CONSUMED/QUEUE_ONLY`
   - `Warmup: PASSED/BLOCKED`
