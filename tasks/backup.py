from pathlib import Path

from core.logging import get_logger
from services.backups import create_backup

logger = get_logger("backup.task")


def main() -> None:
    logger.info("Scheduled backup task started")
    archive_path: Path = create_backup()
    logger.info("Scheduled backup task finished: archive=%s", archive_path)
    print("Created backup: {}".format(archive_path))


if __name__ == "__main__":
    main()
