"""Password hashes and signed tokens, with the standard library only."""
import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import NamedTuple, Optional

PBKDF2_ITERATIONS = 600000
TOKEN_SECONDS = 8 * 3600


class TokenUser(NamedTuple):
    id: int
    username: str


# --- passwords -------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return (f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}$"
            f"{_pbkdf2(password, salt, PBKDF2_ITERATIONS).hex()}")


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt, digest = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        computed = _pbkdf2(password, bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(computed, bytes.fromhex(digest))
    except ValueError:
        return False


def _pbkdf2(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)


# --- tokens: base64url(payload) "." base64url(HMAC-SHA256(payload)) --------

def create_token(user: TokenUser, secret: bytes, now: Optional[float] = None) -> str:
    issued = time.time() if now is None else now
    payload = json.dumps({"sub": user.id, "name": user.username,
                          "exp": int(issued) + TOKEN_SECONDS}).encode()
    return f"{_encode(payload)}.{_encode(_sign(payload, secret))}"


def read_token(token: str, secret: bytes,
               now: Optional[float] = None) -> Optional[TokenUser]:
    """The user of a valid token, or None (wrong format, signature or expired)."""
    current = time.time() if now is None else now
    try:
        payload, signature = (_decode(part) for part in token.split("."))
        if not hmac.compare_digest(signature, _sign(payload, secret)):
            return None
        data = json.loads(payload)
        if current >= data["exp"]:
            return None
        return TokenUser(data["sub"], data["name"])
    except (ValueError, KeyError, TypeError):
        return None


def _sign(payload: bytes, secret: bytes) -> bytes:
    return hmac.new(secret, payload, hashlib.sha256).digest()


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
