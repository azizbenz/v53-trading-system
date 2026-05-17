# C/D Side / Halal / Spot-Only Safety Evidence

## Required Checks

| Check | Engine C | Engine D | Evidence |
|---|---|---|---|
| no shorting | `PASS` | `PASS` | runtime builders emit `Side.BUY` only |
| no leverage | `PASS` | `PASS` | no leverage or margin field found on audited runtime paths |
| no side mutation | `PASS` | `PASS` | runtime signal candidates keep `Side.BUY` |
| no fake flat | `PASS` | `PASS` | hard-block / coordination tests show refusal or hard block, not fake flat order |
| `SELL` means spot inventory reduction only if used | `PASS` | `PASS` | no SELL path audited for C/D entry runtimes |
| `NO_TRADE` not translated into venue order | `PASS` | `PASS` | coordination / ranking / portfolio / risk reject tests |
| ML/regime refs cannot create side | `PASS` | `PASS` | `supplementary_refs` additive only; no side field on ref carriage |

## Source Proof

Engine C:

```text
src/engines/engine_c/engine_c_runtime_support.py
  SignalCandidate(side=Side.BUY)
```

Engine D:

```text
src/engines/engine_d/engine_d_runtime_support.py
  SignalCandidate(side=Side.BUY)
```

## Test Proof

Engine C:
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py::test_runtime_emits_signal_and_accepts_through_risk`
- `tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py::test_runtime_coordination_block_keeps_no_fake_blocked_trade`

Engine D:
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py::test_runtime_emits_signal_and_accepts_through_risk`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py::test_runtime_never_creates_fake_flat_side_or_fake_blocked_trade`

## Conclusion

- C and D remain compatible with the spot-only / halal doctrine on the audited runtime seams.
- No audited path shows trade creation by ML/regime, side mutation, shorting, leverage, or fake flat orders.

