"""Governed trust-store and payload-hash policy for artifact signature envelopes."""

from __future__ import annotations

from datetime import date
from typing import Callable

from backtest_artifact_import.contracts import (
    ArtifactSignatureCheckResult,
    ArtifactSignatureCheckStatus,
)
from backtest_artifact_import.ed25519_verifier import verify_ed25519_signature_base64
from interface_contracts import (
    ArtifactSignatureEnvelope,
    ArtifactPolicyErrorCode,
    ArtifactTrustKeyStatus,
    ArtifactTrustStoreEntry,
)
from local_replay_runtime.artifact_manifest import ArtifactManifest

ArtifactSignatureVerifier = Callable[[ArtifactSignatureEnvelope, ArtifactTrustStoreEntry], bool]

LAB_ARTIFACT_SIGNING_ACTIVE_KEY_ID = "lab_ed25519_2026_q2_k1"
LAB_ARTIFACT_SIGNING_ACTIVE_PAYLOAD_HASH_SHA256 = "hash"
LAB_ARTIFACT_SIGNING_ACTIVE_SIGNATURE_B64 = (
    "DTUMrlHO5qcQyQbhlwkzo4WemHyT3km11DmdNrrgSHzS/oWiduncTXQieU68kfos0NOMES4PbhmuhjyTokBMAg=="
)


DEFAULT_ARTIFACT_TRUST_STORE: tuple[ArtifactTrustStoreEntry, ...] = (
    ArtifactTrustStoreEntry(
        key_id=LAB_ARTIFACT_SIGNING_ACTIVE_KEY_ID,
        public_key="jIySLzUDc7s9bYHllHT51MgFtqLCKl3qYO5yFhqTMc8=",
        status=ArtifactTrustKeyStatus.ACTIVE,
        activated_on=date(2026, 4, 5),
        operator_note="initial governed lab signing key",
    ),
    ArtifactTrustStoreEntry(
        key_id="lab_ed25519_2026_q1_k0",
        public_key="rR5SQFTNof1Hi2QnHRfRGFMW8it074uDcT1g4qremLs=",
        status=ArtifactTrustKeyStatus.DEPRECATED,
        activated_on=date(2026, 1, 1),
        operator_note="kept temporarily for controlled rotation",
    ),
    ArtifactTrustStoreEntry(
        key_id="lab_ed25519_2025_q4_revoked",
        public_key="hPSprEVOj/1qq3V6UOfBL30e4JQ/fenKnIX3gKkw4kw=",
        status=ArtifactTrustKeyStatus.REVOKED,
        activated_on=date(2025, 10, 1),
        revoked_on=date(2026, 4, 5),
        operator_note="revoked fixture entry",
    ),
)


def build_lab_fixture_signature_envelope() -> ArtifactSignatureEnvelope:
    """Return the governed lab fixture envelope signed by the active Ed25519 key."""

    return ArtifactSignatureEnvelope(
        key_id=LAB_ARTIFACT_SIGNING_ACTIVE_KEY_ID,
        public_key_author_sig=LAB_ARTIFACT_SIGNING_ACTIVE_SIGNATURE_B64,
        payload_hash_sha256=LAB_ARTIFACT_SIGNING_ACTIVE_PAYLOAD_HASH_SHA256,
    )


def verify_default_artifact_signature(
    envelope: ArtifactSignatureEnvelope,
    trusted_entry: ArtifactTrustStoreEntry,
) -> bool:
    """Verify the payload-hash string against the trusted Ed25519 public key."""

    return verify_ed25519_signature_base64(
        public_key_b64=trusted_entry.public_key,
        signature_b64=envelope.public_key_author_sig,
        message=envelope.payload_hash_sha256.encode("utf-8"),
    )


def evaluate_artifact_signature_policy(
    manifest: ArtifactManifest,
    *,
    trust_store: tuple[ArtifactTrustStoreEntry, ...] | None = DEFAULT_ARTIFACT_TRUST_STORE,
    expected_payload_hash_sha256: str | None = None,
    signature_verifier: ArtifactSignatureVerifier | None = None,
) -> ArtifactSignatureCheckResult:
    """Evaluate trust-store eligibility and optional payload-hash coherence.

    This slice governs:
    - presence of a signature envelope
    - trust-store eligibility of the declared key id
    - optional payload-hash equality when an expected hash is supplied
    - cryptographic signature verification through the built-in Ed25519 path
      unless an explicit verifier override is supplied
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
    resolved_signature_verifier = signature_verifier or verify_default_artifact_signature
    try:
        verified = bool(resolved_signature_verifier(envelope, trusted_entry))
    except Exception:
        verified = False
    if not verified:
        return ArtifactSignatureCheckResult(
            status=ArtifactSignatureCheckStatus.SIGNATURE_INVALID,
            accepted=False,
            key_id=envelope.key_id,
            trusted_key_status=trusted_entry.status.value,
            reasons=(ArtifactPolicyErrorCode.SIGNATURE_INVALID.value,),
        )
    return ArtifactSignatureCheckResult(
        status=ArtifactSignatureCheckStatus.VERIFIED,
        accepted=True,
        key_id=envelope.key_id,
        trusted_key_status=trusted_entry.status.value,
    )


__all__ = [
    "ArtifactSignatureVerifier",
    "LAB_ARTIFACT_SIGNING_ACTIVE_KEY_ID",
    "LAB_ARTIFACT_SIGNING_ACTIVE_PAYLOAD_HASH_SHA256",
    "LAB_ARTIFACT_SIGNING_ACTIVE_SIGNATURE_B64",
    "DEFAULT_ARTIFACT_TRUST_STORE",
    "build_lab_fixture_signature_envelope",
    "evaluate_artifact_signature_policy",
    "verify_default_artifact_signature",
]
