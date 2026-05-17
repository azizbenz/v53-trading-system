# Wave 6 External Audit Questions

1. Which live/shadow runtime component should become the governed producer of non-empty ML `supplementary_refs` on VPS?
2. Which process should populate live ML drift snapshots into `MlModelRiskRegistry`, and at what cadence?
3. Should a machine-verifiable anti-leakage proof artifact become mandatory before any ML promotion beyond replay/shadow analysis?
4. Is `MlDirection` acceptable as a research/debug-only hint as long as it never mutates governed runtime side, or should it be renamed to reduce operator confusion?
5. Is the permanent `ml.formalism.unresolved` blocker intentional for the current release line, or is there a planned governance wave that can replace it with explicit artifact-level promotion criteria?
6. Is the current `local_replay_runtime` placement for training-label builders sufficiently explicit, or should a stronger Local-Lab-only namespace boundary be introduced later?
7. Is regime runtime intended to remain shadow-only indefinitely, or is there a future governed promotion path for non-directional runtime use?
8. If regime runtime eventually feeds scoring or risk, which direct consumer must prove that governance boundary?
9. Are there cockpit surfaces outside the inspected state rails that still need explicit stale/missing/hash-mismatch ML/regime status hardening?

