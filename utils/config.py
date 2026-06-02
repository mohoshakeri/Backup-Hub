import os
from pathlib import Path
from typing import Callable

from CONSTANTS import DEFAULT_BACKUP_CRON, DEFAULT_MAX_BACKUPS, DEFAULT_PORT

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv: Callable[[], bool] | None = None


if load_dotenv:
    load_dotenv()


PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
FS_ROOT: Path = PROJECT_ROOT / "fs"
TMP_DIR: Path = FS_ROOT / "tmp"
BACKUPS_DIR: Path = FS_ROOT / "backups"
DEBUG: bool = os.getenv("DEBUG", "NO").upper() == "YES"
PORT: int = int(os.getenv("PORT", str(DEFAULT_PORT)))
BASE_URL: str = os.getenv("BASE_URL", "http://localhost:{}".format(PORT)).strip()
CORS_ALLOWEDS: list[str] = [item.strip() for item in os.getenv("CORS_ALLOWEDS", "").split(",") if item.strip()]
LOGO_URL: str = os.getenv("BACKUP_HUB_LOGO_URL", "").strip()
FAVICON_URL: str = os.getenv("BACKUP_HUB_FAVICON_URL", "").strip()
BACKUP_CRON: str = os.getenv("BACKUP_HUB_CRON", DEFAULT_BACKUP_CRON).strip()
MAX_BACKUPS: int = int(os.getenv("BACKUP_HUB_MAX_BACKUPS", str(DEFAULT_MAX_BACKUPS)))
AES_ZIP_KEY: str = os.getenv("BACKUP_HUB_AES_ZIP_KEY", "").strip()
BACKUP_DIRECTORIES: list[str] = [
    item.strip()
    for item in os.getenv("BACKUP_HUB_DIRECTORIES", "").split(",")
    if item.strip()
]

if not CORS_ALLOWEDS:
    cors_defaults: set[str] = {
        BASE_URL,
        BASE_URL.replace("localhost", "127.0.0.1"),
        BASE_URL.replace("127.0.0.1", "localhost"),
    }
    CORS_ALLOWEDS = sorted(cors_defaults)

# ---------- Security Settings ----------
AUTH_USERNAME: str = os.getenv("BACKUP_HUB_USERNAME", "admin").strip()
AUTH_PASSWORD: str = os.getenv("BACKUP_HUB_PASSWORD", "1234").strip()
TOTP_SECRET: str = os.getenv("BACKUP_HUB_TOTP_SECRET", "JBSWY3DPEHPK3PXP").replace(" ", "").strip()
SESSION_SECRET: str = os.getenv("BACKUP_HUB_SESSION_SECRET", "pAQ!_Q4ZDy%2M4wMrQBXar_%5hFm&nUg+qT%w4-t").strip()
SESSION_COOKIE: str = os.getenv("BACKUP_HUB_SESSION_COOKIE", "slv_session").strip()
SESSION_TTL_SECONDS: int = int(os.getenv("BACKUP_HUB_SESSION_TTL_SECONDS", str(15 * 60)))
COOKIE_SECURE: bool = os.getenv("BACKUP_HUB_COOKIE_SECURE", "NO").upper() == "YES"

FS_ROOT.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
