import os
import re
import subprocess
from pathlib import Path

from utils.config import BACKUP_COMMAND_TIMEOUT_SECONDS
from core.logging import get_logger

logger = get_logger("backup_providers.common")

SECRET_IN_URI_PATTERN: re.Pattern[str] = re.compile(r"([a-zA-Z][a-zA-Z0-9+.-]*://[^:/@\s]+:)([^@\s]+)(@)")
MYSQL_PASSWORD_ARG_PATTERN: re.Pattern[str] = re.compile(r"(--password=)([^\s]+)")
ENV_SECRET_PATTERN: re.Pattern[str] = re.compile(
    r"\b([A-Z0-9_]*(?:PASSWORD|PASS|SECRET|TOKEN|KEY|URI)[A-Z0-9_]*=)([^\s]+)",
    re.IGNORECASE,
)
JSON_SECRET_PATTERN: re.Pattern[str] = re.compile(
    r'("?(?:password|pass|secret|token|key|uri)"?\s*[:=]\s*"?)([^",\s}]+)("?)',
    re.IGNORECASE,
)


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def run_command(command: list[str], env: dict[str, str] | None = None) -> None:
    process_env: dict[str, str] = os.environ.copy()

    if env:
        process_env.update(env)

    logger.info("Command running: executable=%s args_count=%s", command[0], len(command))
    try:
        result: subprocess.CompletedProcess[str] = subprocess.run(
            command,
            check=False,
            env=process_env,
            text=True,
            capture_output=True,
            timeout=BACKUP_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error("Command timed out: executable=%s timeout_seconds=%s", command[0], BACKUP_COMMAND_TIMEOUT_SECONDS)
        raise RuntimeError("Command timed out after {} seconds".format(BACKUP_COMMAND_TIMEOUT_SECONDS)) from exc

    if result.returncode == 0:
        logger.info("Command finished: executable=%s returncode=%s", command[0], result.returncode)
        return

    message: str = sanitize_command_output(result.stderr.strip() or result.stdout.strip() or "Command failed")
    logger.error("Command failed: executable=%s returncode=%s error=%s", command[0], result.returncode, message)
    raise RuntimeError(message)


def sanitize_command_output(message: str) -> str:
    sanitized_message: str = SECRET_IN_URI_PATTERN.sub(r"\1***\3", message)
    sanitized_message = MYSQL_PASSWORD_ARG_PATTERN.sub(r"\1***", sanitized_message)
    sanitized_message = ENV_SECRET_PATTERN.sub(r"\1***", sanitized_message)
    sanitized_message = JSON_SECRET_PATTERN.sub(r"\1***\3", sanitized_message)
    return sanitized_message


def safe_host_dir(host: str, port: str | None = None) -> str:
    if port:
        return "{}_{}".format(safe_path_component(host), safe_path_component(port))

    return safe_path_component(host)


def safe_path_component(value: str) -> str:
    cleaned_value: str = re.sub(r"[^A-Za-z0-9_.:@-]+", "_", value.strip())
    cleaned_value = cleaned_value.strip("._")
    return cleaned_value or "unnamed"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
