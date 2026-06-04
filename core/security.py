import base64
import binascii

from utils.config import AUTH_PASSWORD, COOKIE_SECURE, CORS_ALLOWEDS, DEBUG, SESSION_SECRET, STRICT_SECURITY, TOTP_SECRET

DEFAULT_AUTH_PASSWORD: str = "1234"
DEFAULT_SESSION_SECRET: str = "pAQ!_Q4ZDy%2M4wMrQBXar_%5hFm&nUg+qT%w4-t"
DEFAULT_TOTP_SECRET: str = "JBSWY3DPEHPK3PXP"


def validate_security_settings() -> None:
    if not STRICT_SECURITY:
        return

    insecure_fields: list[str] = []

    if AUTH_PASSWORD == DEFAULT_AUTH_PASSWORD:
        insecure_fields.append("BACKUP_HUB_PASSWORD")

    if SESSION_SECRET == DEFAULT_SESSION_SECRET:
        insecure_fields.append("BACKUP_HUB_SESSION_SECRET")

    if TOTP_SECRET == DEFAULT_TOTP_SECRET:
        insecure_fields.append("BACKUP_HUB_TOTP_SECRET")

    if len(AUTH_PASSWORD) < 12:
        insecure_fields.append("BACKUP_HUB_PASSWORD length")

    if len(SESSION_SECRET) < 32:
        insecure_fields.append("BACKUP_HUB_SESSION_SECRET length")

    if not _is_valid_totp_secret(secret=TOTP_SECRET):
        insecure_fields.append("BACKUP_HUB_TOTP_SECRET format")

    if DEBUG:
        insecure_fields.append("DEBUG")

    if not COOKIE_SECURE:
        insecure_fields.append("BACKUP_HUB_COOKIE_SECURE")

    if "*" in CORS_ALLOWEDS:
        insecure_fields.append("CORS_ALLOWEDS wildcard")

    if insecure_fields:
        raise RuntimeError("Insecure security settings: {}".format(", ".join(insecure_fields)))


def _is_valid_totp_secret(secret: str) -> bool:
    cleaned_secret: str = "".join(secret.split()).upper()

    if len(cleaned_secret) < 16:
        return False

    try:
        base64.b32decode("{}{}".format(cleaned_secret, "=" * (-len(cleaned_secret) % 8)), casefold=True)
    except (binascii.Error, ValueError):
        return False

    return True
