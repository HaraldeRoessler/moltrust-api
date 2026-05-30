"""RFC 8785 (JCS) canonical JSON + Ed25519 signing for registry receipts."""
import base64
import jcs

from app.registry_keys import REGISTRY_KID, get_private_key


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def canonicalize(payload: dict) -> bytes:
    """RFC 8785 JSON Canonicalization Scheme — returns UTF-8 bytes."""
    return jcs.canonicalize(payload)


def sign_payload(payload: dict) -> str:
    """Sign payload with registry private key. Returns base64url-encoded signature."""
    sig = get_private_key().sign(canonicalize(payload))
    return _b64url_encode(sig)


def build_registry_jws(payload: dict, kid: str = REGISTRY_KID) -> str:
    """Compact JWS (RFC 7515) over JCS-canonicalised payload, EdDSA/Ed25519.

    Returns three-part dot-separated token verifiable by any stock JOSE library
    against the public JWK published in /.well-known/jwks.json.
    """
    header = {"alg": "EdDSA", "typ": "JWT", "kid": kid}
    header_b64 = _b64url_encode(canonicalize(header))
    payload_b64 = _b64url_encode(canonicalize(payload))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = get_private_key().sign(signing_input)
    return f"{header_b64}.{payload_b64}.{_b64url_encode(sig)}"


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


def sign_agent_card(card: dict, kid: str = REGISTRY_KID) -> dict:
    """Return `card` augmented with an A2A v1.0.1 `signatures[]` entry.

    Per the A2A spec, AgentCardSignature is `{protected, signature}` —
    NOT a compact JWS string. `protected` is the base64url JCS-canonical
    JWS header; `signature` is the base64url raw Ed25519 signature over
    `signing_input = f"{protected_b64}.{payload_b64}"` (RFC 7515 §5.1).

    The payload is the AgentCard with any existing `signatures` field
    stripped — otherwise the signature would cover itself recursively.
    """
    card_to_sign = {k: v for k, v in card.items() if k != "signatures"}
    payload_b64 = _b64url_encode(canonicalize(card_to_sign))

    header = {"alg": "EdDSA", "kid": kid, "typ": "a2a-card+jws"}
    protected_b64 = _b64url_encode(canonicalize(header))

    signing_input = f"{protected_b64}.{payload_b64}".encode("ascii")
    sig = get_private_key().sign(signing_input)
    signature_b64 = _b64url_encode(sig)

    return {
        **card_to_sign,
        "signatures": [
            {"protected": protected_b64, "signature": signature_b64},
        ],
    }
