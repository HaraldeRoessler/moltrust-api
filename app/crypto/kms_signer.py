"""KMS-backed signing key decryption for MolTrust API."""
import boto3
import base64
import os
import time

_cached_key = None
_cache_expiry = 0
CACHE_TTL = 300  # 5 minutes


def get_decrypted_signing_key_hex() -> str:
    """
    Return the Ed25519 private key as a hex string (64 chars / 32 bytes).
    Decrypted via AWS KMS with 5-minute cache.
    Falls back to plaintext env var or key file during migration —
    these fallbacks are DISABLED when MOLTRUST_ENV=production so that
    an accidentally-set DID_PRIVATE_KEY_HEX env var or stray local
    keyfile cannot bypass KMS in a production deploy.
    """
    global _cached_key, _cache_expiry

    is_production = os.environ.get('MOLTRUST_ENV', '').lower() == 'production'

    # Fallback 1: plaintext env var (migration / dev only)
    encrypted = os.environ.get('DID_PRIVATE_KEY_ENCRYPTED')
    if not encrypted:
        if is_production:
            raise ValueError(
                'KMS-encrypted signing key required in production '
                '(MOLTRUST_ENV=production); plaintext fallbacks disabled. '
                'Set DID_PRIVATE_KEY_ENCRYPTED or unset MOLTRUST_ENV.'
            )
        hex_key = os.environ.get('DID_PRIVATE_KEY_HEX', '')
        if hex_key:
            return hex_key
        # Fallback 2: key file
        key_path = os.path.expanduser('~/.moltrust_did_private_key')
        if os.path.exists(key_path):
            with open(key_path) as f:
                return f.read().strip()
        raise ValueError('No signing key available (no KMS blob, no env var, no key file)')

    now = time.time()
    if _cached_key and now < _cache_expiry:
        return _cached_key

    kms = boto3.client('kms', region_name=os.environ.get('AWS_REGION', 'eu-central-1'))
    response = kms.decrypt(
        KeyId=os.environ.get('KMS_KEY_ID'),
        CiphertextBlob=base64.b64decode(encrypted)
    )

    _cached_key = response['Plaintext'].decode('utf-8').strip()
    _cache_expiry = now + CACHE_TTL
    print('[KMS] Python signing key decrypted and cached')
    return _cached_key


def clear_key_cache():
    """Clear cached key (for rotation)."""
    global _cached_key, _cache_expiry
    _cached_key = None
    _cache_expiry = 0
