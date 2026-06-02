from utils.config import AUTH_PASSWORD, SESSION_SECRET, STRICT_SECURITY, TOTP_SECRET

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

    if insecure_fields:
        raise RuntimeError("Insecure default security settings: {}".format(", ".join(insecure_fields)))
