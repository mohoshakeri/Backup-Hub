import time
from typing import Any

import jwt

from CONSTANTS import DOWNLOAD_LINK_TTL_SECONDS
from utils.config import SESSION_SECRET

JWT_ALGORITHM: str = "HS256"
DOWNLOAD_SCOPE: str = "backup-download"


def create_download_token(filename: str) -> str:
    payload: dict[str, Any] = {
        "filename": filename,
        "exp": int(time.time()) + DOWNLOAD_LINK_TTL_SECONDS,
        "scope": DOWNLOAD_SCOPE,
    }
    return jwt.encode(payload=payload, key=SESSION_SECRET, algorithm=JWT_ALGORITHM)


def validate_download_token(token: str, filename: str) -> bool:
    try:
        payload: dict[str, Any] = jwt.decode(jwt=token, key=SESSION_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return False

    if payload.get("scope") != DOWNLOAD_SCOPE:
        return False

    return str(payload.get("filename", "")) == filename
