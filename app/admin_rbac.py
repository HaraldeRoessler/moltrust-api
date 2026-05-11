"""
MolTrust Admin RBAC — Role-Based Admin Authorization
Replaces single ADMIN_KEY with tiered permission levels.

Permission levels:
  READ    — Ghost agent detection, status checks
  WRITE   — Registration, anchoring, seed management
  DESTROY — Violation reversal, revocation, credential revoke, SPIFFE unbind

Higher permissions include lower: DESTROY > WRITE > READ.
Old ADMIN_KEY accepted at WRITE level for backwards compatibility.
"""

import os
import secrets
from enum import IntEnum
from fastapi import HTTPException, Request


class AdminPermission(IntEnum):
    READ = 1
    WRITE = 2
    DESTROY = 3


# Key hierarchy: higher keys grant all lower permissions
_KEY_LEVEL = {}


def _load_keys():
    """Load admin keys from environment. Called once at import."""
    global _KEY_LEVEL
    _KEY_LEVEL.clear()

    destroy = os.environ.get("ADMIN_KEY_DESTROY", "")
    write = os.environ.get("ADMIN_KEY_WRITE", "")
    read = os.environ.get("ADMIN_KEY_READ", "")
    legacy = os.environ.get("ADMIN_KEY", "")

    if destroy:
        _KEY_LEVEL[destroy] = AdminPermission.DESTROY
    if write:
        _KEY_LEVEL[write] = AdminPermission.WRITE
    if read:
        _KEY_LEVEL[read] = AdminPermission.READ
    if legacy and legacy not in _KEY_LEVEL:
        _KEY_LEVEL[legacy] = AdminPermission.WRITE


_load_keys()


def verify_admin(request: Request, required: AdminPermission) -> bool:
    """
    Verify admin authorization with role-based permissions.
    Higher-level keys grant access to lower-level operations.
    Uses timing-safe comparison.
    """
    provided = request.headers.get("x-admin-key", "")
    if not provided:
        raise HTTPException(401, "Admin key required")

    if not _KEY_LEVEL:
        _load_keys()

    for key, level in _KEY_LEVEL.items():
        if secrets.compare_digest(provided, key):
            if level >= required:
                return True
            raise HTTPException(
                403,
                f"Insufficient permission: {required.name} required, "
                f"{level.name} provided",
            )

    raise HTTPException(403, "Invalid admin key")


def is_admin(request: Request) -> bool:
    """Check if request has any admin key (non-raising)."""
    provided = request.headers.get("x-admin-key", "")
    if not provided:
        return False
    for key in _KEY_LEVEL:
        if secrets.compare_digest(provided, key):
            return True
    return False
