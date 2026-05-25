"""VC Data Model v2 issuance + dual-accept verification.

Phase-1 contract:
  - Newly issued credentials use v2 (`@context` v2 URL, `validFrom` / `validUntil`).
  - `verify_credential` still accepts legacy v1 credentials (`issuanceDate` /
    `expirationDate`) so credentials minted before this migration keep verifying.
"""
import datetime
import json
import os
import sys
import pytest

# Resolve `from app...` from the test file's own repo root (works on Hetzner
# server layout AND on a local checkout — conftest pins the server path which
# is irrelevant for these pure-unit tests).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.credentials import (  # noqa: E402
    VC_V2_CONTEXT,
    VC_V1_CONTEXT,
    MOLTRUST_CONTEXT,
    vc_valid_from,
    vc_valid_until,
)


# ---------------------------------------------------------------------------
# Helper functions — dual-format read
# ---------------------------------------------------------------------------

def test_valid_from_prefers_v2():
    vc = {"validFrom": "2026-05-25T10:00:00Z", "issuanceDate": "2020-01-01T00:00:00Z"}
    assert vc_valid_from(vc) == "2026-05-25T10:00:00Z"


def test_valid_from_falls_back_to_v1():
    vc = {"issuanceDate": "2026-05-25T10:00:00Z"}
    assert vc_valid_from(vc) == "2026-05-25T10:00:00Z"


def test_valid_from_missing_returns_empty():
    assert vc_valid_from({}) == ""


def test_valid_until_prefers_v2():
    vc = {"validUntil": "2027-05-25T10:00:00Z", "expirationDate": "2020-01-01T00:00:00Z"}
    assert vc_valid_until(vc) == "2027-05-25T10:00:00Z"


def test_valid_until_falls_back_to_v1():
    vc = {"expirationDate": "2027-05-25T10:00:00Z"}
    assert vc_valid_until(vc) == "2027-05-25T10:00:00Z"


def test_valid_until_missing_returns_empty():
    assert vc_valid_until({}) == ""


# ---------------------------------------------------------------------------
# Issue + verify roundtrip — needs a signing key in env
# ---------------------------------------------------------------------------

_TEST_SEED_HEX = "11" * 32


def _ensure_test_signing_key():
    """Install a deterministic test signing key.

    `app.credentials.get_signing_key` reads from KMS in production; tests run
    without that infra. We swap the function in the `app.credentials` module
    so both `issue_credential` and `verify_credential` see the same dev key.
    Patches the module-level binding rather than the underlying KMS module
    because `credentials.py` imports the KMS function by name at load time.
    """
    from nacl.signing import SigningKey
    from app import credentials as _cred
    if getattr(_cred, "_TEST_KEY_PATCHED", False):
        return
    test_sk = SigningKey(bytes.fromhex(_TEST_SEED_HEX))
    _cred.get_signing_key = lambda: test_sk
    _cred._TEST_KEY_PATCHED = True


def _test_signing_key():
    from nacl.signing import SigningKey
    return SigningKey(bytes.fromhex(_TEST_SEED_HEX))


def test_issue_credential_emits_v2_shape():
    _ensure_test_signing_key()
    from app.credentials import issue_credential
    vc = issue_credential("did:moltrust:test_v2_issue", "TestCredential", {"k": "v"})

    assert VC_V2_CONTEXT in vc["@context"], f"v2 context missing: {vc['@context']}"
    assert MOLTRUST_CONTEXT in vc["@context"]
    assert "validFrom" in vc and vc["validFrom"]
    assert "validUntil" in vc and vc["validUntil"]
    # Legacy v1 fields MUST NOT be present on freshly-issued v2 credentials
    assert "issuanceDate" not in vc
    assert "expirationDate" not in vc


def test_verify_accepts_legacy_v1_credential():
    _ensure_test_signing_key()
    from app.credentials import issue_credential, verify_credential, ISSUER_DID

    # Mint a v2 credential normally, then re-shape into a v1 envelope that we
    # re-sign — this is what a credential issued by the pre-migration code
    # looks like after it was persisted to the DB.
    vc = issue_credential("did:moltrust:test_v1_legacy", "TestCredential", {"k": "v"})
    legacy = {
        "@context": [VC_V1_CONTEXT, MOLTRUST_CONTEXT],
        "type": vc["type"],
        "issuer": vc["issuer"],
        "issuanceDate": vc["validFrom"],
        "expirationDate": vc["validUntil"],
        "credentialSubject": vc["credentialSubject"],
    }
    # Re-sign with the same key the patched issuer uses
    sk = _test_signing_key()
    payload = json.dumps(legacy, sort_keys=True).encode()
    sig = sk.sign(payload).signature.hex()
    legacy["proof"] = {
        "type": "Ed25519Signature2020",
        "created": legacy["issuanceDate"],
        "verificationMethod": f"{ISSUER_DID}#key-1",
        "proofPurpose": "assertionMethod",
        "proofValue": sig,
    }
    result = verify_credential(legacy)
    assert result["valid"] is True, f"legacy v1 credential failed verify: {result}"


def test_verify_v2_credential_roundtrip():
    _ensure_test_signing_key()
    from app.credentials import issue_credential, verify_credential
    vc = issue_credential("did:moltrust:test_v2_roundtrip", "TestCredential", {"k": "v"})
    result = verify_credential(vc)
    assert result["valid"] is True, f"v2 roundtrip failed: {result}"


def test_verify_expired_credential_v2():
    _ensure_test_signing_key()
    from app.credentials import verify_credential, ISSUER_DID

    past = (datetime.datetime.utcnow() - datetime.timedelta(days=2)).isoformat() + "Z"
    expired = {
        "@context": [VC_V2_CONTEXT, MOLTRUST_CONTEXT],
        "type": ["VerifiableCredential", "TestCredential"],
        "issuer": ISSUER_DID,
        "validFrom": past,
        "validUntil": past,  # already expired
        "credentialSubject": {"id": "did:moltrust:test_expired"},
    }
    sk = _test_signing_key()
    payload = json.dumps(expired, sort_keys=True).encode()
    sig = sk.sign(payload).signature.hex()
    expired["proof"] = {
        "type": "Ed25519Signature2020",
        "created": past,
        "verificationMethod": f"{ISSUER_DID}#key-1",
        "proofPurpose": "assertionMethod",
        "proofValue": sig,
    }
    result = verify_credential(expired)
    assert result["valid"] is False
    assert "expired" in result["error"].lower()
