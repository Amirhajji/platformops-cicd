import base64
import hashlib
import json

import pytest

from app.core import security
from app.core.security import (TokenUser, create_token, hash_password, read_token,
                               verify_password)

USER = TokenUser(7, "alice")
SECRET = b"unit-test-secret"


# --- passwords ---------------------------------------------------------------

def test_password_hash_is_salted_and_verified():
    first, second = hash_password("secret"), hash_password("secret")
    assert first != second
    assert verify_password("secret", first) and verify_password("secret", second)
    assert not verify_password("Secret", first)


def test_password_hash_format():
    algorithm, iterations, salt, digest = hash_password("secret").split("$")
    assert algorithm == "pbkdf2_sha256" and int(iterations) == 600000
    assert digest == hashlib.pbkdf2_hmac(
        "sha256", b"secret", bytes.fromhex(salt), int(iterations)).hex()


@pytest.mark.parametrize("stored", ["", "x", "md5$1$00$00", "pbkdf2_sha256$1$zz$00"])
def test_invalid_stored_hash_is_refused(stored):
    assert not verify_password("secret", stored)


# --- tokens ------------------------------------------------------------------

def test_token_round_trip():
    assert read_token(create_token(USER, SECRET), SECRET) == USER


def test_token_expires_after_8_hours():
    token = create_token(USER, SECRET, now=1000)
    assert read_token(token, SECRET, now=1000 + 8 * 3600 - 1) == USER
    assert read_token(token, SECRET, now=1000 + 8 * 3600) is None


def test_token_with_a_changed_payload_is_refused():
    signature = create_token(USER, SECRET).split(".")[1]
    payload = json.dumps({"sub": 1, "name": "admin", "exp": 10 ** 12}).encode()
    forged = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
    assert read_token(f"{forged}.{signature}", SECRET) is None


def test_token_with_another_secret_is_refused():
    assert read_token(create_token(USER, SECRET), b"other") is None


@pytest.mark.parametrize("token", ["", "a", "a.b", "a.b.c", ".", "é.é", "!!.!!", "e30.e30"])
def test_malformed_token_is_refused(token):
    assert read_token(token, SECRET) is None


@pytest.mark.parametrize("data", [b"[]", b"1", b"{}", b"not json", b'{"exp": "x"}'])
def test_signed_but_meaningless_payload_is_refused(data):
    encode = security._encode
    assert read_token(f"{encode(data)}.{encode(security._sign(data, SECRET))}", SECRET) is None
