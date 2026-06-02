import os
import subprocess
from pathlib import Path

from core.logging import get_logger

logger = get_logger("backup_providers.common")


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def run_command(command: list[str], env: dict[str, str] | None = None) -> None:
    process_env: dict[str, str] = os.environ.copy()

    if env:
        process_env.update(env)

    logger.info("Command running: executable=%s args_count=%s", command[0], len(command))
    result: subprocess.CompletedProcess[str] = subprocess.run(
        command,
        check=False,
        env=process_env,
        text=True,
        capture_output=True,
    )

    if result.returncode == 0:
        logger.info("Command finished: executable=%s returncode=%s", command[0], result.returncode)
        return

    message: str = result.stderr.strip() or result.stdout.strip() or "Command failed"
    logger.error("Command failed: executable=%s returncode=%s error=%s", command[0], result.returncode, message)
    raise RuntimeError(message)


def safe_host_dir(host: str, port: str | None = None) -> str:
    if port:
        return "{}_{}".format(host.replace("/", "_"), port)

    return host.replace("/", "_")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
