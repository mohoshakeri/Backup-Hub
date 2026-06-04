import os
import subprocess
from pathlib import Path

from backup_providers.base import BackupContext
from backup_providers.common import ensure_parent, safe_host_dir, safe_path_component, sanitize_command_output, split_csv
from core.logging import get_logger
from utils.config import BACKUP_COMMAND_TIMEOUT_SECONDS

logger = get_logger("mysql.backup_provider")


class MySqlBackupProvider:
    name: str = "mysql"

    def __init__(self) -> None:
        self.host: str = os.getenv("MYSQL_HOST", "").strip()
        self.port: str = os.getenv("MYSQL_PORT", "3306").strip()
        self.user: str = os.getenv("MYSQL_USER", "").strip()
        self.password: str = os.getenv("MYSQL_PASSWORD", "").strip()
        self.databases: list[str] = split_csv(os.getenv("MYSQL_DATABASES", ""))

    def is_configured(self) -> bool:
        configured: bool = bool(self.host and self.user and self.password)
        logger.info("MySQL configuration checked: configured=%s host=%s port=%s user_set=%s", configured, self.host, self.port, bool(self.user))
        return configured

    def backup(self, context: BackupContext) -> list[Path]:
        logger.info("MySQL backup started: host=%s port=%s root=%s", self.host, self.port, context.root_dir)
        databases: list[str] = self.databases or self._list_databases()
        logger.info("MySQL database list ready: count=%s source=%s", len(databases), "env" if self.databases else "server")
        created_paths: list[Path] = []

        for database in databases:
            output_path: Path = (
                context.root_dir
                / "databases"
                / self.name
                / safe_host_dir(self.host, self.port)
                / "{}.sql".format(safe_path_component(database))
            )
            ensure_parent(output_path)
            command: list[str] = [
                "mysqldump",
                "--host={}".format(self.host),
                "--port={}".format(self.port),
                "--user={}".format(self.user),
                "--single-transaction",
                "--routines",
                "--triggers",
                "--events",
                database,
            ]
            logger.info("MySQL database dump started: database=%s output=%s", database, output_path)
            self._run_to_file(command=command, output_path=output_path)
            created_paths.append(output_path)
            logger.info("MySQL database dump finished: database=%s output=%s size_bytes=%s", database, output_path, output_path.stat().st_size)

        logger.info("MySQL backup finished: created_files=%s", len(created_paths))
        return created_paths

    def _list_databases(self) -> list[str]:
        logger.info("MySQL database discovery started: host=%s port=%s", self.host, self.port)
        command: list[str] = [
            "mysql",
            "--host={}".format(self.host),
            "--port={}".format(self.port),
            "--user={}".format(self.user),
            "--batch",
            "--skip-column-names",
            "--execute",
            "SHOW DATABASES;",
        ]
        env: dict[str, str] = os.environ.copy()
        env["MYSQL_PWD"] = self.password

        try:
            result: subprocess.CompletedProcess[str] = subprocess.run(
                command,
                check=False,
                env=env,
                text=True,
                capture_output=True,
                timeout=BACKUP_COMMAND_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            logger.error("MySQL database discovery timed out: timeout_seconds=%s", BACKUP_COMMAND_TIMEOUT_SECONDS)
            raise RuntimeError("MySQL database list timed out after {} seconds".format(BACKUP_COMMAND_TIMEOUT_SECONDS)) from exc

        if result.returncode != 0:
            message: str = sanitize_command_output(result.stderr.strip() or result.stdout.strip() or "MySQL database list failed")
            logger.error("MySQL database discovery failed: returncode=%s error=%s", result.returncode, message)
            raise RuntimeError(message)

        ignored: set[str] = {"information_schema", "mysql", "performance_schema", "sys"}
        databases: list[str] = [item.strip() for item in result.stdout.splitlines() if item.strip() and item.strip() not in ignored]
        logger.info("MySQL database discovery finished: count=%s ignored_system_databases=%s", len(databases), len(ignored))
        return databases

    def _run_to_file(self, command: list[str], output_path: Path) -> None:
        logger.info("MySQL command running: executable=%s output=%s", command[0], output_path)
        env: dict[str, str] = os.environ.copy()
        env["MYSQL_PWD"] = self.password

        with output_path.open("w", encoding="utf-8") as output_file:
            try:
                result: subprocess.CompletedProcess[str] = subprocess.run(
                    command,
                    check=False,
                    env=env,
                    text=True,
                    stdout=output_file,
                    stderr=subprocess.PIPE,
                    timeout=BACKUP_COMMAND_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired as exc:
                logger.error("MySQL command timed out: executable=%s timeout_seconds=%s", command[0], BACKUP_COMMAND_TIMEOUT_SECONDS)
                raise RuntimeError("MySQL command timed out after {} seconds".format(BACKUP_COMMAND_TIMEOUT_SECONDS)) from exc

        if result.returncode == 0:
            logger.info("MySQL command finished: executable=%s returncode=%s", command[0], result.returncode)
            return

        message: str = sanitize_command_output(result.stderr.strip() if result.stderr else "MySQL backup failed")
        logger.error("MySQL command failed: executable=%s returncode=%s error=%s", command[0], result.returncode, message)
        raise RuntimeError(message)
