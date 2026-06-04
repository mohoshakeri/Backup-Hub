import shutil
from datetime import datetime
from pathlib import Path

from backup_providers import BackupContext, DatabaseBackupProvider, MongoBackupProvider, MySqlBackupProvider, PostgresBackupProvider
from CONSTANTS import BACKUP_FILE_EXTENSION, BACKUP_FILENAME_FORMAT, BACKUP_FILENAME_PREFIX
from core.logging import get_logger
from utils.config import AES_ZIP_KEY, BACKUP_DIRECTORIES, BACKUPS_DIR, MAX_BACKUPS, TMP_DIR

logger = get_logger("backups.service")


def list_backups() -> list[Path]:
    backups: list[Path] = [
        item
        for item in BACKUPS_DIR.iterdir()
        if item.is_file() and not item.is_symlink() and _is_backup_filename(filename=item.name)
    ]
    return sorted(backups, key=lambda item: item.stat().st_mtime, reverse=True)


def get_backup_or_none(filename: str) -> Path | None:
    if filename != Path(filename).name:
        return None

    if not _is_backup_filename(filename=filename):
        return None

    backup_path: Path = BACKUPS_DIR / filename
    backups_dir: Path = BACKUPS_DIR.resolve()

    try:
        resolved_backup_path: Path = backup_path.resolve(strict=True)
    except FileNotFoundError:
        return None

    if resolved_backup_path.parent != backups_dir:
        return None

    if not resolved_backup_path.is_file():
        return None

    return resolved_backup_path


def create_backup(now: datetime | None = None) -> Path:
    logger.info("Backup process started")

    if not AES_ZIP_KEY:
        logger.error("Backup process blocked because BACKUP_HUB_AES_ZIP_KEY is missing")
        raise RuntimeError("BACKUP_HUB_AES_ZIP_KEY is required")

    logger.info("Clearing temporary directory before backup: %s", TMP_DIR)
    _clear_tmp()

    logger.info("Checking backup retention in %s with max_backups=%s", BACKUPS_DIR, MAX_BACKUPS)
    _prune_old_backups()

    timestamp: datetime = now or datetime.now()
    backup_name: str = "{}-{}".format(BACKUP_FILENAME_PREFIX, timestamp.strftime(BACKUP_FILENAME_FORMAT))
    backup_root: Path = TMP_DIR / backup_name
    logger.info("Creating backup workspace: %s", backup_root)
    backup_root.mkdir(parents=True, exist_ok=True)

    try:
        context: BackupContext = BackupContext(name=backup_name, root_dir=backup_root, tmp_dir=TMP_DIR)
        logger.info("Database backup phase started for %s", backup_name)
        _backup_databases(context=context)
        logger.info("Disk backup phase started for %s", backup_name)
        _backup_directories(backup_root=backup_root)
        archive_path: Path = BACKUPS_DIR / "{}{}".format(backup_name, BACKUP_FILE_EXTENSION)
        logger.info("Encrypted archive phase started: %s", archive_path)
        _write_encrypted_zip(source_dir=backup_root, archive_path=archive_path)
        logger.info("Backup process finished successfully: %s", archive_path)
        return archive_path
    except Exception:
        logger.exception("Backup process failed for %s", backup_name)
        raise
    finally:
        logger.info("Clearing temporary directory after backup: %s", TMP_DIR)
        _clear_tmp()


def _backup_databases(context: BackupContext) -> None:
    providers: list[DatabaseBackupProvider] = [
        PostgresBackupProvider(),
        MySqlBackupProvider(),
        MongoBackupProvider(),
    ]

    for provider in providers:
        if not provider.is_configured():
            logger.info("Database backup provider skipped because env is incomplete: %s", provider.name)
            continue

        logger.info("Database backup provider started: %s", provider.name)
        created_paths: list[Path] = provider.backup(context=context)
        logger.info("Database backup provider finished: %s files=%s", provider.name, len(created_paths))


def _backup_directories(backup_root: Path) -> None:
    disks_root: Path = backup_root / "disks"

    if not BACKUP_DIRECTORIES:
        logger.info("Disk backup skipped because BACKUP_HUB_DIRECTORIES is empty")
        return

    for directory in BACKUP_DIRECTORIES:
        source_path: Path = Path(directory)
        logger.info("Disk backup item started: source=%s", source_path)

        if not source_path.exists():
            logger.error("Disk backup item missing: source=%s", source_path)
            raise RuntimeError("Backup directory does not exist: {}".format(directory))

        relative_target: Path = Path(str(source_path).lstrip("/"))
        target_path: Path = disks_root / relative_target

        if source_path.is_dir():
            shutil.copytree(source_path, target_path, dirs_exist_ok=True, symlinks=True)
            logger.info("Disk backup item finished: source=%s target=%s type=directory", source_path, target_path)
            continue

        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        logger.info("Disk backup item finished: source=%s target=%s type=file", source_path, target_path)


def _write_encrypted_zip(source_dir: Path, archive_path: Path) -> None:
    import pyzipper

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    written_files_count: int = 0

    with pyzipper.AESZipFile(
        archive_path,
        "w",
        compression=pyzipper.ZIP_DEFLATED,
        encryption=pyzipper.WZ_AES,
    ) as zip_file:
        zip_file.setpassword(AES_ZIP_KEY.encode("utf-8"))

        for item in sorted(source_dir.rglob("*")):
            if item.is_symlink() or not item.is_file():
                continue

            zip_file.write(item, item.relative_to(source_dir.parent))
            written_files_count += 1

    logger.info(
        "Encrypted archive finished: archive=%s files=%s size_bytes=%s",
        archive_path,
        written_files_count,
        archive_path.stat().st_size,
    )


def _prune_old_backups() -> None:
    backups: list[Path] = list_backups()
    max_backups: int = max(MAX_BACKUPS, 1)
    logger.info("Retention scan finished: existing_backups=%s max_backups=%s", len(backups), max_backups)

    while len(backups) >= max_backups:
        oldest_backup: Path = backups.pop()
        logger.info("Deleting old backup: %s", oldest_backup)
        oldest_backup.unlink()


def _clear_tmp() -> None:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    removed_items_count: int = 0

    for item in TMP_DIR.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
            removed_items_count += 1
            continue

        item.unlink()
        removed_items_count += 1

    logger.info("Temporary directory cleared: path=%s removed_items=%s", TMP_DIR, removed_items_count)


def _is_backup_filename(filename: str) -> bool:
    return filename.startswith(BACKUP_FILENAME_PREFIX) and filename.endswith(BACKUP_FILE_EXTENSION)
