"""Governed trust-store and payload-hash policy for artifact signature envelopes."""

from __future__ import annotations

from datetime import date

from backtest_artifact_import.contracts import (
    ArtifactSignatureCheckResult,
    ArtifactSignatureCheckStatus,
)
from interface_contracts import (
    ArtifactPolicyErrorCode,
    ArtifactTrustKeyStatus,
    ArtifactTrustStoreEntry,
)
from local_replay_runtime.artifact_manifest import ArtifactManifest


DEFAULT_ARTIFACT_TRUST_STORE: tuple[ArtifactTrustStoreEntry, ...] = (
    ArtifactTrustStoreEntry(
        key_id="lab_ed25519_2026_q2_k1",
        public_key="lab_ed25519_public_key_q2_k1",
        status=ArtifactTrustKeyStatus.ACTIVE,
        activated_on=date(2026, 4, 5),
        operator_note="initial governed lab signing key",
    ),
    ArtifactTrustStoreEntry(
        key_id="lab_ed25519_2026_q1_k0",
        public_key="lab_ed25519_public_key_q1_k0",
        status=ArtifactTrustKeyStatus.DEPRECATED,
        activated_on=date(2026, 1, 1),
        operator_note="kept temporarily for controlled rotation",
    ),
    ArtifactTrustStoreEntry(
        key_id="lab_ed25519_2025_q4_revoked",
        public_key="lab_ed25519_public_key_q4_revoked",
        status=ArtifactTrustKeyStatus.REVOKED,
        activated_on=date(2025, 10, 1),
        revoked_on=date(2026, 4, 5),
        operator_note="revoked fixture entry",
    ),
)


def evaluate_artifact_signature_policy(
    manifest: ArtifactManifest,
    *,
    trust_store: tuple[ArtifactTrustStoreEntry, ...] | None = DEFAULT_ARTIFACT_TRUST_STORE,
    expected_payload_hash_sha256: str | None = None,
) -> ArtifactSignatureCheckResult:
    """Evaluate trust-store eligibility and optional payload-hash coherence.

    This slice does not claim Ed25519 cryptographic verification. It only governs:
    - presence of a signature envelope
    - trust-store eligibility of the declared key id
    - optional payload-hash equality when an expected hash is supplied
    """

    envelope = manifest.signature_envelope
    if envelope is None:
        return ArtifactSignatureCheckResult(
            status=ArtifactSignatureCheckStatus.NOT_PROVIDED,
            accepted=True,
        )
    if trust_store is None:
        return ArtifactSignatureCheckResult(
            status=ArtifactSignatureCheckStatus.TRUST_STORE_UNAVAILABLE,
            accepted=False,
            key_id=envelope.key_id,
            reasons=(ArtifactPolicyErrorCode.TRUST_STORE_UNAVAILABLE.value,),
        )

    trusted_entry = next((entry for entry in trust_store if entry.key_id == envelope.key_id), None)
    if trusted_entry is None:
        return ArtifactSignatureCheckResult(
            status=ArtifactSignatureCheckStatus.KEY_ID_UNKNOWN,
            accepted=False,
            key_id=envelope.key_id,
            reasons=(ArtifactPolicyErrorCode.KEY_ID_UNKNOWN.value,),
        )
    if trusted_entry.status == ArtifactTrustKeyStatus.REVOKED:
        return ArtifactSignatureCheckResult(
            status=ArtifactSignatureCheckStatus.KEY_REVOKED,
            accepted=False,
            key_id=envelope.key_id,
            trusted_key_status=trusted_entry.status.value,
            reasons=(ArtifactPolicyErrorCode.KEY_REVOKED.value,),
        )
    if (
        expected_payload_hash_sha256 is not None
        and envelope.payload_hash_sha256 != expected_payload_hash_sha256
    ):
        return ArtifactSignatureCheckResult(
            status=ArtifactSignatureCheckStatus.PAYLOAD_HASH_MISMATCH,
            accepted=False,
            key_id=envelope.key_id,
            trusted_key_status=trusted_entry.status.value,
            reasons=(ArtifactPolicyErrorCode.PAYLOAD_HASH_MISMATCH.value,),
        )
    return ArtifactSignatureCheckResult(
        status=ArtifactSignatureCheckStatus.TRUST_ELIGIBLE,
        accepted=True,
        key_id=envelope.key_id,
        trusted_key_status=trusted_entry.status.value,
    )


__all__ = [
    "DEFAULT_ARTIFACT_TRUST_STORE",
    "evaluate_artifact_signature_policy",
]
