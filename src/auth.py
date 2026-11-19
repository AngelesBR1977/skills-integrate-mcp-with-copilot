import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

PASSWORD_HASH_ITERATIONS = 600_000
SESSION_COOKIE_NAME = "teacher_session"
SESSION_LIFETIME_SECONDS = 8 * 60 * 60

_configured_session_secret = os.environ.get("SESSION_SECRET")
_session_secret = (
    _configured_session_secret.encode("utf-8")
    if _configured_session_secret
    else secrets.token_bytes(32)
)


def hash_password(password: str) -> dict[str, str]:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return {"salt": salt.hex(), "password_hash": password_hash.hex()}


def verify_password(password: str, salt_hex: str, password_hash_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    expected_hash = bytes.fromhex(password_hash_hex)
    actual_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return hmac.compare_digest(actual_hash, expected_hash)


def load_teacher_accounts(teachers_file: Path) -> list[dict[str, str]]:
    try:
        contents = teachers_file.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Teacher accounts are not configured. Run `python -m src.manage_teachers`.",
        ) from exc

    try:
        data: Any = json.loads(contents)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail="Teacher account configuration is not valid JSON.",
        ) from exc

    if not isinstance(data, dict) or not isinstance(data.get("teachers"), list):
        raise HTTPException(
            status_code=500,
            detail="Teacher account configuration must contain a teachers list.",
        )

    accounts: list[dict[str, str]] = []
    seen_usernames: set[str] = set()
    for account in data["teachers"]:
        if not isinstance(account, dict):
            raise HTTPException(status_code=500, detail="Invalid teacher account entry.")

        username = account.get("username")
        salt_hex = account.get("salt")
        password_hash_hex = account.get("password_hash")
        if not all(isinstance(value, str) and value for value in (username, salt_hex, password_hash_hex)):
            raise HTTPException(status_code=500, detail="Invalid teacher account entry.")

        normalized_username = username.casefold()
        if normalized_username in seen_usernames:
            raise HTTPException(status_code=500, detail="Duplicate teacher username configured.")
        seen_usernames.add(normalized_username)

        try:
            salt = bytes.fromhex(salt_hex)
            password_hash = bytes.fromhex(password_hash_hex)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail="Invalid teacher password hash configured.") from exc

        if len(salt) != 16 or len(password_hash) != 32:
            raise HTTPException(status_code=500, detail="Invalid teacher password hash configured.")

        accounts.append(
            {
                "username": username,
                "salt": salt_hex,
                "password_hash": password_hash_hex,
            }
        )

    return accounts


def create_session_token(username: str) -> str:
    payload = json.dumps(
        {
            "username": username,
            "expires": int(time.time()) + SESSION_LIFETIME_SECONDS,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(
        _session_secret,
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded_payload}.{signature}"


def get_session_username(request: Request) -> str | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    try:
        encoded_payload, signature = token.rsplit(".", 1)
        expected_signature = hmac.new(
            _session_secret,
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            return None

        padded_payload = encoded_payload + "=" * (-len(encoded_payload) % 4)
        payload = json.loads(
            base64.urlsafe_b64decode(padded_payload.encode("ascii")).decode("utf-8")
        )
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error):
        return None

    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("username"), str)
        or not isinstance(payload.get("expires"), int)
        or payload["expires"] <= int(time.time())
    ):
        return None

    return payload["username"]


def require_teacher(request: Request) -> str:
    username = get_session_username(request)
    if username is None:
        raise HTTPException(status_code=401, detail="Teacher login required.")
    return username
