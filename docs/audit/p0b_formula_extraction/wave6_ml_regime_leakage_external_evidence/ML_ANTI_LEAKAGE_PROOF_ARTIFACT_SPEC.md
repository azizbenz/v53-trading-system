# ML Anti-Leakage Proof Artifact Spec

Date: 2026-04-30
Status: spec created; implementation not yet proven.

## Purpose

ML promotion requires a machine-verifiable anti-leakage proof artifact in addition to human review.

## Required fields

```json
{
  "artifact_id": null,
  "dataset_hash": null,
  "feature_hash": null,
  "label_policy": null,
  "train_window": null,
  "validation_window": null,
  "test_window": null,
  "purge_size": null,
  "embargo_size": null,
  "label_horizon": null,
  "max_feature_timestamp": null,
  "min_label_timestamp": null,
  "random_split_forbidden": true,
  "feature_timestamp_alignment_status": null,
  "no_future_data_leak_status": null,
  "reviewer_signature": null,
  "method_version_hash": null
}
```

## Field rules

- `dataset_hash` must match the training dataset artifact
- `feature_hash` must match the artifact feature set
- `label_policy` must match the governed training-label policy
- `train_window`, `validation_window`, and `test_window` must be explicit
- `purge_size` and `embargo_size` must reflect the actual walk-forward split
- `label_horizon` must match the label-generation horizon
- `max_feature_timestamp <= min_label_timestamp` must be demonstrable or the artifact is invalid
- `random_split_forbidden` must always be `true`
- `feature_timestamp_alignment_status` must be explicit, never implied
- `no_future_data_leak_status` must be explicit, never implied

## Review rule

- human review may remain required
- machine-verifiable artifact is additionally required before ML promotion

## Failure rule

If the anti-leakage proof artifact is missing or invalid:

- ML promotion remains blocked
- replay/shadow analysis may continue
- no live-ready ML claim is allowed

