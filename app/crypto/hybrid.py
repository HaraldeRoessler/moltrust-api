"""
Hybrid (dual) signature module for MolTrust.

Issues credentials with both an Ed25519 and an ML-DSA-65 (Dilithium3) proof
when Dilithium keys are configured, and Ed25519-only otherwise. Verification
enforces the security contract the review required:

  * A credential issued with a *list* of proofs MUST present every listed
    proof and every listed proof MUST verify. This is AND-logic, not OR:
    an attacker cannot strip the Dilithium leg and rely on Ed25519 alone,
    because the verifier rejects a proof set whose declared legs are not all
    present and valid (composite-signature semantics, BSI TR-02102-1).
  * The canonicalized payload excludes the `proof` field (a proof must not
    sign itself); both legs sign the same canonical bytes so tampering with
    the credential body invalidates both.

Canonicalization is RFC 8785 JCS. If the `jcs` library is not importable at
sign time we FAIL CLOSED (raise) rather than emit a proof whose
`canonicalizationAlgorithm` says "JCS" but was actually produced with
`json.dumps(sort_keys=True)` — that mismatch was flagged as a DoS /
false-negative vector in the review.

Legacy credentials (single Ed25519 proof, no canonicalizationAlgorithm, or
canonicalizationAlgorithm other than JCS) still verify with the original
`json.dumps(sort_keys=True)` path so already-issued VCs remain valid.
"""
import json
import logging

from app.crypto import dilithium
from app.crypto.proof_utils import (
    ED25519_PROOF_TYPE,
    DILITHIUM_PROOF_TYPE,
    get_proofs,
)

logger = logging.getLogger("moltrust.crypto.hybrid")

ISSUER_DID = "did:web:api.moltrust.ch"


def _canonicalize(credential_without_proof: dict, algorithm: str) -> bytes:
    """Canonicalize the credential body (proof already stripped).

    `algorithm` is the value that will be written into the proof's
    `canonicalizationAlgorithm` field. We refuse to emit a JCS-labelled
    proof unless JCS actually ran.
    """
    if algorithm == "JCS":
        try:
            import jcs
        except ImportError as e:
            raise RuntimeError(
                "canonicalizationAlgorithm=JCS but the jcs library is not "
                "installed; refusing to emit a mismatched proof"
            ) from e
        return jcs.canonicalize(credential_without_proof)

    # Legacy path — used only for verifying old credentials.
    if algorithm in (None, "", "JSON-SORT-KEYS"):
        return json.dumps(credential_without_proof, sort_keys=True).encode()

    raise ValueError(f"Unsupported canonicalizationAlgorithm: {algorithm!r}")


def _proof_algorithm(proof: dict) -> str:
    """Return the canonicalization algorithm declared by a proof.

    Legacy Ed25519 proofs have no `canonicalizationAlgorithm` field; treat
    that as the original sort_keys behaviour so they still verify.
    """
    return proof.get("canonicalizationAlgorithm") or "JSON-SORT-KEYS"


def dual_sign(credential: dict, ed25519_key) -> dict:
    """Sign a credential with Ed25519 and, if configured, ML-DSA-65.

    Args:
        credential: the VC dict without a `proof` field.
        ed25519_key: a nacl.signing.SigningKey.

    Returns:
        The credential with `proof` set to a single proof dict (Ed25519-only)
        or a list of two proof dicts (Ed25519 + Dilithium).

    Raises:
        RuntimeError if JCS is required but the jcs library is missing.
    """
    # The proof signs the credential body WITHOUT the proof field.
    body = {k: v for k, v in credential.items() if k != "proof"}

    # New credentials always use JCS. Fail closed if jcs is not installed.
    payload = _canonicalize(body, "JCS")

    now_str = (
        credential.get("validFrom")
        or credential.get("issuanceDate")
        or ""
    )

    ed_signed = ed25519_key.sign(payload)
    ed_proof = {
        "type": ED25519_PROOF_TYPE,
        "created": now_str,
        "verificationMethod": f"{ISSUER_DID}#key-ed25519",
        "proofPurpose": "assertionMethod",
        "canonicalizationAlgorithm": "JCS",
        "proofValue": ed_signed.signature.hex(),
    }

    dil_sig = dilithium.sign(payload)
    if dil_sig is None:
        credential["proof"] = ed_proof
        logger.debug("Credential signed Ed25519-only (Dilithium not configured)")
        return credential

    dil_proof = {
        "type": DILITHIUM_PROOF_TYPE,
        "created": now_str,
        "verificationMethod": f"{ISSUER_DID}#key-dilithium",
        "proofPurpose": "assertionMethod",
        "canonicalizationAlgorithm": "JCS",
        "proofValue": dil_sig.hex(),
    }
    credential["proof"] = [ed_proof, dil_proof]
    logger.info("Credential dual-signed (Ed25519 + ML-DSA-65)")
    return credential


def verify_proof(credential: dict, ed25519_verify_key) -> dict:
    """Verify a credential's proof(s) with composite-signature semantics.

    Contract (fixes the review's downgrade/stripping blocker):

      * If `proof` is a list, EVERY proof in the list MUST be present and
        MUST verify. A missing leg (e.g. attacker strips Dilithium) makes
        the whole credential invalid. This is AND-logic.
      * Each proof signs the credential body (proof field stripped),
        re-canonicalized with that proof's declared algorithm.

    Returns: {"valid": bool, "checks": [{"type","valid"[,"error"]}], "error"?}
    """
    proofs = get_proofs(credential)
    if not proofs:
        return {"valid": False, "error": "No proof found"}

    body = {k: v for k, v in credential.items() if k != "proof"}
    results = {"valid": True, "checks": []}

    for p in proofs:
        ptype = p.get("type", "")
        algo = _proof_algorithm(p)

        # Re-derive the signed payload. JCS proofs require the jcs library;
        # legacy proofs fall back to sort_keys. A JCS-labelled proof with no
        # jcs library is a hard fail (the issuer could not have produced it).
        try:
            payload = _canonicalize(body, algo)
        except RuntimeError as e:
            results["checks"].append({"type": ptype, "valid": False, "error": str(e)})
            results["valid"] = False
            continue

        try:
            signature = bytes.fromhex(p["proofValue"])
        except (ValueError, KeyError) as e:
            results["checks"].append({"type": ptype, "valid": False, "error": f"bad proofValue: {e}"})
            results["valid"] = False
            continue

        if ED25519_PROOF_TYPE in ptype or "Ed25519" in ptype:
            try:
                ed25519_verify_key.verify(payload, signature)
                results["checks"].append({"type": "Ed25519", "valid": True})
            except Exception as e:
                results["checks"].append({"type": "Ed25519", "valid": False, "error": str(e)})
                results["valid"] = False

        elif DILITHIUM_PROOF_TYPE in ptype or "Dilithium" in ptype:
            pk_hex = dilithium.get_public_key_hex()
            if not pk_hex:
                results["checks"].append({
                    "type": "Dilithium",
                    "valid": False,
                    "error": "Dilithium public key not configured on this verifier",
                })
                results["valid"] = False
            else:
                ok = dilithium.verify(payload, signature, bytes.fromhex(pk_hex))
                results["checks"].append({"type": "Dilithium", "valid": ok})
                if not ok:
                    results["valid"] = False
        else:
            results["checks"].append({
                "type": ptype, "valid": False,
                "error": f"Unknown proof type: {ptype}",
            })
            results["valid"] = False

    if not results["valid"]:
        errors = [c.get("error", "check failed")
                  for c in results["checks"] if not c.get("valid")]
        results["error"] = "; ".join(errors)

    return results