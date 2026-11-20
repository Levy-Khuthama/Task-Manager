"""Password hashing using only the standard library (PBKDF2-HMAC-SHA256)."""

from __future__ import annotations

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
# Read at call time so tests can lower it to keep the suite fast.
ITERATIONS = 200_000
SALT_BYTES = 16


def hash_password(
    password: str, *, salt: bytes | None = None, iterations: int | None = None
) -> str:
    """Return ``pbkdf2_sha256$<iterations>$<salt hex>$<hash hex>``.

    A fresh random salt is used unless one is supplied (supplying one is only
    useful for tests).
    """
    iterations = iterations or ITERATIONS
    salt = salt if salt is not None else secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{ALGORITHM}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Check a password against a string produced by :func:`hash_password`.

    Malformed or unrecognised stored values simply fail verification.
    """
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$")
        if algorithm != ALGORITHM:
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(actual, expected)
