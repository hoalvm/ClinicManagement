"""Retired compatibility module for password helpers.

The running API uses :mod:`backend.app.core.security` for passwords and JWTs.
No signing secret is stored in this module.
"""

from backend.app.core.security import hash_password as get_password_hash
from backend.app.core.security import verify_password

__all__ = ["get_password_hash", "verify_password"]
