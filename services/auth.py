import base64
import hashlib
import hmac
import json
import time
from typing import Any

from CONSTANTS import SESSION_SIGNER_SEPARATOR
from utils.config import AUTH_PASSWORD, AUTH_USERNAME, SESSION_SECRET, SESSION_TTL_SECONDS, TOTP_SECRET


def validate_password(username: str, password: str) -> bool:
    valid_username: bool = hmac.compare_digest(username, AUTH_USERNAME)
    valid_password: bool = hmac.compare_digest(password, AUTH_PASSWORD)
    return valid_username and valid_password


def create_session_token() -> str:
    payload: dict[str, Any] = {
        "username": AUTH_USERNAME,
        "expires_at": int(time.time()) + SESSION_TTL_SECONDS,
    }
    payload_text: str = _encode_json(payload)
    signature: str = _sign(payload_text)
    return "{}{}{}".format(payload_text, SESSION_SIGNER_SEPARATOR, signature)


def create_csrf_token(session_token: str) -> str:
    return _sign("csrf:{}".format(session_token))


def validate_csrf_token(session_token: str | None, csrf_token: str) -> bool:
    if not session_token or not csrf_token or not validate_session_token(token=session_token):
        return False

    return hmac.compare_digest(create_csrf_token(session_token=session_token), csrf_token)


def validate_session_token(token: str | None) -> bool:
    if not token or SESSION_SIGNER_SEPARATOR not in token:
        return False

    payload_text: str
    signature: str
    payload_text, signature = token.rsplit(SESSION_SIGNER_SEPARATOR, 1)

    if not hmac.compare_digest(_sign(payload_text), signature):
        return False

    try:
        payload: dict[str, Any] = json.loads(_decode(payload_text))
    except (ValueError, json.JSONDecodeError):
        return False

    expires_at: int = int(payload.get("expires_at", 0))
    username: str = str(payload.get("username", ""))
    return username == AUTH_USERNAME and expires_at > int(time.time())


def validate_totp(code: str, window: int = 1) -> bool:
    cleaned_code: str = "".join(item for item in code if item.isdigit())

    if len(cleaned_code) != 6:
        return False

    timestamp: int = int(time.time())
    step: int = timestamp // 30

    for offset in range(-window, window + 1):
        expected_code: str = generate_totp(step + offset)

        if hmac.compare_digest(cleaned_code, expected_code):
            return True

    return False


def generate_totp(step: int | None = None) -> str:
    current_step: int = step if step is not None else int(time.time()) // 30
    key: bytes = base64.b32decode(_normalize_totp_secret(TOTP_SECRET), casefold=True)
    message: bytes = current_step.to_bytes(8, "big")
    digest: bytes = hmac.new(key, message, hashlib.sha1).digest()
    offset: int = digest[-1] & 15
    code: int = int.from_bytes(digest[offset : offset + 4], "big") & 0x7FFFFFFF
    return "{:06d}".format(code % 1000000)


def _sign(payload_text: str) -> str:
    digest: bytes = hmac.new(SESSION_SECRET.encode("utf-8"), payload_text.encode("utf-8"), hashlib.sha256).digest()
    return _encode(digest)


def _encode_json(payload: dict[str, Any]) -> str:
    data: bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _encode(data)


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decode(value: str) -> str:
    padding: str = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode("{}{}".format(value, padding).encode("ascii")).decode("utf-8")


def _normalize_totp_secret(secret: str) -> str:
    cleaned_secret: str = "".join(secret.split()).upper()
    return "{}{}".format(cleaned_secret, "=" * (-len(cleaned_secret) % 8))
