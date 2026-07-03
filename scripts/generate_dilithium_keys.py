#!/usr/bin/env python3
"""Generate an ML-DSA-65 (Dilithium3) keypair for MolTrust.

Usage:
    pip install liboqs-python
    python scripts/generate_dilithium_keys.py [--out-dir DIR] [--kms]

Security (fixes the review's private-key stdout-leak blocker):
    The secret key is NEVER printed to stdout/stderr. It is written only to a
    chmod 600 file `dilithium_secret_key.hex` in the chosen output directory
    (default: the current directory). The public key IS printed to stdout
    (it is not secret) and also written to `dilithium_public_key.hex`.

    With --kms, the script instead prints the base64 of the raw secret-key
    bytes so it can be piped straight into `aws kms encrypt` — but it still
    does not print the hex secret key. The recommended flow is:

        python scripts/generate_dilithium_keys.py --out-dir /secure/keys
        # then encrypt /secure/keys/dilithium_secret_key.hex into KMS and
        # delete the plaintext file once the KMS blob is stored:
        aws kms encrypt --key-id $KMS_KEY_ID \
            --plaintext fileb:///secure/keys/dilithium_secret_key.hex \
            --output text --query CiphertextBlob \
            > /secure/keys/dilithium_private_key.encrypted
        shred -u /secure/keys/dilithium_secret_key.hex

Exit codes: 0 on success, 1 on a dependency/setup error.
"""
import argparse
import os
import stat
import sys

DEFAULT_OUT_DIR = "."


def _write_secret_file(path: str, secret_hex: str) -> None:
    """Write the secret key to a chmod 600 file. Fail loudly if chmod fails."""
    # O_CREAT | O_WRONLY | O_TRUNC, then explicit chmod so the file is never
    # world/group-readable even for a moment (open() respects umask, which we
    # cannot rely on).
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    try:
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        os.write(fd, secret_hex.encode("utf-8"))
        os.write(fd, b"\n")
    finally:
        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out-dir", default=DEFAULT_OUT_DIR,
        help="directory to write the key files (default: current dir)",
    )
    parser.add_argument(
        "--kms", action="store_true",
        help="emit the raw secret-key bytes (base64) to stdout for piping "
             "into `aws kms encrypt`; the hex secret key is still written to a "
             "chmod 600 file as a fallback",
    )
    args = parser.parse_args()

    try:
        import oqs
    except ImportError:
        print("Error: liboqs-python is not installed.", file=sys.stderr)
        print("Install with: pip install liboqs-python", file=sys.stderr)
        print("See: https://github.com/open-quantum-safe/liboqs-python",
              file=sys.stderr)
        return 1

    signer = oqs.Signature("ML-DSA-65")
    public_key = signer.generate_keypair()
    secret_key = signer.export_secret_key()

    secret_hex = secret_key.hex()
    public_hex = public_key.hex()

    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    # Secret key -> chmod 600 file only. NEVER stdout.
    secret_path = os.path.join(out_dir, "dilithium_secret_key.hex")
    _write_secret_file(secret_path, secret_hex)

    # Public key -> file (not secret) + stdout (not secret).
    public_path = os.path.join(out_dir, "dilithium_public_key.hex")
    with open(public_path, "w") as f:
        f.write(public_hex + "\n")

    print(f"Algorithm: ML-DSA-65 (Dilithium3)", file=sys.stderr)
    print(f"Secret key length: {len(secret_key)} bytes", file=sys.stderr)
    print(f"Public key length: {len(public_key)} bytes", file=sys.stderr)
    print(f"Secret key written to: {secret_path} (chmod 600)", file=sys.stderr)
    print(f"Public key written to: {public_path}", file=sys.stderr)
    print("", file=sys.stderr)
    print("DILITHIUM_PUBLIC_KEY_HEX=" + public_hex)
    print("", file=sys.stderr)
    if args.kms:
        import base64
        # Raw bytes for `aws kms encrypt` piping. Not the hex secret.
        print(base64.b64encode(secret_key).decode("ascii"))
    print(
        "IMPORTANT: encrypt dilithium_secret_key.hex into AWS KMS and shred "
        "the plaintext file. Never commit it to version control.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())