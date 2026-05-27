"""RFC 8785 (JCS) canonical JSON + Ed25519 signing for registry receipts."""
import base64
import jcs

from app.registry_keys import get_private_key


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def canonicalize(payload: dict) -> bytes:
    """RFC 8785 JSON Canonicalization Scheme — returns UTF-8 bytes."""
    return jcs.canonicalize(payload)


def sign_payload(payload: dict) -> str:
    """Sign payload with registry private key. Returns base64url-encoded signature."""
    sig = get_private_key().sign(canonicalize(payload))
    return _b64url_encode(sig)


def build_score_signing_payload(
    did: str,
    trust_score: float,
    computed_at: str,
    valid_until: str,
    policy_version: str,
) -> dict:
    """Deterministic minimal payload signed for trust-score responses."""
    return {
        "did": did,
        "trust_score": trust_score,
        "computed_at": computed_at,
        "valid_until": valid_until,
        "policy_version": policy_version,
    }
