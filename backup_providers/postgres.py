import os
import subprocess
from pathlib import Path

from backup_providers.base import BackupContext
from backup_providers.common import ensure_parent, safe_host_dir, split_csv
from core.logging import get_logger

logger = get_logger("postgres.backup_provider")


class PostgresBackupProvider:
    name: str = "postgres"

    def __init__(self) -> None:
        self.host: str = os.getenv("POSTGRES_HOST", "").strip()
        self.port: str = os.getenv("POSTGRES_PORT", "5432").strip()
        self.user: str = os.getenv("POSTGRES_USER", "").strip()
        self.password: str = os.getenv("POSTGRES_PASSWORD", "").strip()
        self.databases: list[str] = split_csv(os.getenv("POSTGRES_DATABASES", ""))

    def is_configured(self) -> bool:
        configured: bool = bool(self.host and self.user and self.password)
        logger.info("Postgres configuration checked: configured=%s host=%s port=%s user_set=%s", configured, self.host, self.port, bool(self.user))
        return configured

    def backup(self, context: BackupContext) -> list[Path]:
        logger.info("Postgres backup started: host=%s port=%s root=%s", self.host, self.port, context.root_dir)
        databases: list[str] = self.databases or self._list_databases()
        logger.info("Postgres database list ready: count=%s source=%s", len(databases), "env" if self.databases else "server")
        created_paths: list[Path] = []

        for database in databases:
            output_path: Path = (
                context.root_dir
                / "databases"
                / self.name
                / safe_host_dir(self.host, self.port)
                / "{}.dump".format(database)
            )
            ensure_parent(output_path)
            command: list[str] = [
                "pg_dump",
                "--host",
                self.host,
                "--port",
                self.port,
                "--username",
                self.user,
                "--format",
                "custom",
                "--file",
                str(output_path),
                database,
            ]
            logger.info("Postgres database dump started: database=%s output=%s", database, output_path)
            self._run(command=command)
            created_paths.append(output_path)
            logger.info("Postgres database dump finished: database=%s output=%s size_bytes=%s", database, output_path, output_path.stat().st_size)

        logger.info("Postgres backup finished: created_files=%s", len(created_paths))
        return created_paths

    def _list_databases(self) -> list[str]:
        logger.info("Postgres database discovery started: host=%s port=%s", self.host, self.port)
        command: list[str] = [
            "psql",
            "--host",
            self.host,
            "--port",
            self.port,
            "--username",
            self.user,
            "--dbname",
            "postgres",
            "--tuples-only",
            "--no-align",
            "--command",
            "SELECT datname FROM pg_database WHERE datistemplate = false;",
        ]
        result: subprocess.CompletedProcess[str] = self._run(command=command, capture=True)
        databases: list[str] = [item.strip() for item in result.stdout.splitlines() if item.strip()]
        logger.info("Postgres database discovery finished: count=%s", len(databases))
        return databases

    def _run(self, command: list[str], capture: bool = False) -> subprocess.CompletedProcess[str]:
        env: dict[str, str] = os.environ.copy()
        env["PGPASSWORD"] = self.password
        logger.info("Postgres command running: executable=%s capture=%s", command[0], capture)
        result: subprocess.CompletedProcess[str] = subprocess.run(
            command,
            check=False,
            env=env,
            text=True,
            capture_output=True,
        )

        if result.returncode == 0:
            logger.info("Postgres command finished: executable=%s returncode=%s", command[0], result.returncode)
            return result

        message: str = result.stderr.strip() or result.stdout.strip() or "Postgres backup failed"
        logger.error("Postgres command failed: executable=%s returncode=%s error=%s", command[0], result.returncode, message)
        raise RuntimeError(message)
