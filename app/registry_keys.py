"""Registry signing key management — Ed25519, JWK serialization.

kid: moltrust-registry-2026-v1 (annual rotation, next Jan 2027).
Private key loaded from MOLTRUST_REGISTRY_PRIVATE_KEY env var (hex).
"""
import os
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

REGISTRY_KID = "moltrust-registry-2026-v1"


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def get_private_key() -> Ed25519PrivateKey:
    hex_key = os.environ.get("MOLTRUST_REGISTRY_PRIVATE_KEY")
    if not hex_key:
        raise RuntimeError("MOLTRUST_REGISTRY_PRIVATE_KEY not set")
    raw = bytes.fromhex(hex_key.strip())
    if len(raw) != 32:
        raise RuntimeError(f"Expected 32-byte Ed25519 key, got {len(raw)} bytes")
    return Ed25519PrivateKey.from_private_bytes(raw)


def get_public_key_bytes() -> bytes:
    return get_private_key().public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def get_public_jwk() -> dict:
    return {
        "kid": REGISTRY_KID,
        "kty": "OKP",
        "crv": "Ed25519",
        "x": _b64url_encode(get_public_key_bytes()),
        "use": "sig",
        "alg": "EdDSA",
    }
