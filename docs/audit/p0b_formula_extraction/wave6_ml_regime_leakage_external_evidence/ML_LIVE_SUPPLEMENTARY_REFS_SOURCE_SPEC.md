# ML Live Supplementary Refs Source Spec

Date: 2026-04-30
Status: `LIVE_SUPPLEMENTARY_REFS_SOURCE_NOT_PROVEN`

## Current finding

No concrete live/shadow VPS component was proven in the inspected code as the producer of governed non-empty ML `supplementary_refs`.

Current safe doctrine:

- missing refs => ML neutral
- stale refs => ML disabled
- hash mismatch => ML disabled
- directional refs => forbidden

## Required future producer

The future producer must be the governed runtime artifact-handoff component immediately upstream of `ScoringCandidateInput.supplementary_refs`.

Required responsibilities:

- select the active ML artifact identity
- materialize or resolve the transport artifact path
- attach the transport artifact ref
- attach the summary sidecar ref
- provide freshness timestamps
- provide hash-valid refs only

## Required artifact paths

- transport artifact: `ml_model_artifact.json`
- summary sidecar: `ml_model_artifact.summary.json`

If a future runtime chooses a different storage root, the filenames must remain compatible or be aliased explicitly.

## Required validations

- summary sidecar present
- transport artifact declared in refs
- summary hash matches transport artifact hash
- summary schema version valid
- artifact schema valid
- stale horizon not breached
- source freshness within governed limit

## Runtime behavior rules

If refs are missing:

- ML status = `ML_NEUTRAL_NO_REFS`
- base scoring proceeds
- `ML_ACTIVE_GOVERNED_REFS` is forbidden

If refs are stale:

- ML status = `ML_STALE_NEUTRAL`
- base scoring proceeds
- ML active readiness blocked

If hash mismatch:

- ML status = `ML_HASH_MISMATCH_DISABLED`
- base scoring proceeds
- ML active readiness blocked

If directional refs are present:

- ML status = `ML_DIRECTIONAL_REF_FORBIDDEN`
- base scoring proceeds without ML contribution

## Promotion implication

Without a proven live supplementary-refs source:

- ML active readiness is blocked
- ML promotion remains blocked
- cockpit must not claim ML active from artifact presence alone

