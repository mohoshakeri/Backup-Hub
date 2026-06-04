import os
from pathlib import Path

from backup_providers.base import BackupContext
from backup_providers.common import run_command, safe_path_component, split_csv
from core.logging import get_logger

logger = get_logger("mongodb.backup_provider")


class MongoBackupProvider:
    name: str = "mongodb"

    def __init__(self) -> None:
        self.uri: str = os.getenv("MONGO_URI", "").strip()
        self.databases: list[str] = split_csv(os.getenv("MONGO_DATABASES", ""))

    def is_configured(self) -> bool:
        configured: bool = bool(self.uri and self.databases)
        logger.info("MongoDB configuration checked: configured=%s uri_set=%s databases=%s", configured, bool(self.uri), len(self.databases))
        return configured

    def backup(self, context: BackupContext) -> list[Path]:
        created_paths: list[Path] = []
        logger.info("MongoDB backup started: databases=%s root=%s", len(self.databases), context.root_dir)

        for database in self.databases:
            output_dir: Path = context.root_dir / "databases" / self.name / "mongo_uri" / safe_path_component(database)
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info("MongoDB database dump started: database=%s output=%s", database, output_dir)

            command: list[str] = [
                "mongodump",
                "--uri",
                self.uri,
                "--db",
                database,
                "--out",
                str(output_dir),
            ]
            run_command(command=command)
            created_paths.append(output_dir)
            logger.info("MongoDB database dump finished: database=%s output=%s", database, output_dir)

        logger.info("MongoDB backup finished: created_directories=%s", len(created_paths))
        return created_paths
