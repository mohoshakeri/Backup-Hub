import os
import tempfile
import unittest
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import pyzipper

from services import backups


DATABASE_ENV_KEYS: list[str] = [
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DATABASES",
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DATABASES",
    "MONGO_URI",
    "MONGO_DATABASES",
]


class BackupsTestCase(unittest.TestCase):
    def test_create_backup_copies_directories_and_prunes_old_backups(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path: Path = Path(temp_dir)
            source_dir: Path = temp_path / "data1" / "f"
            source_dir.mkdir(parents=True)
            (source_dir / "hello.txt").write_text("hello", encoding="utf-8")
            tmp_dir: Path = temp_path / "fs" / "tmp"
            backups_dir: Path = temp_path / "fs" / "backups"
            tmp_dir.mkdir(parents=True)
            backups_dir.mkdir(parents=True)
            old_backup: Path = backups_dir / "BACKUP-2024-01-01-00:00.zip"
            old_backup.write_text("old", encoding="utf-8")

            with self._backup_patches(tmp_dir=tmp_dir, backups_dir=backups_dir, source_dir=source_dir, max_backups=1):
                archive_path: Path = backups.create_backup(now=datetime(2025, 1, 1, 12, 12, 0))

            expected_name: str = "BACKUP-2025-01-01-12:12.zip"
            expected_member: str = "BACKUP-2025-01-01-12:12/disks/{}/hello.txt".format(str(source_dir).lstrip("/"))

            self.assertEqual(archive_path.name, expected_name)
            self.assertFalse(old_backup.exists())
            self.assertEqual(list(tmp_dir.iterdir()), [])

            with pyzipper.AESZipFile(archive_path) as zip_file:
                zip_file.setpassword(b"secret-key")
                names: list[str] = zip_file.namelist()
                content: bytes = zip_file.read(expected_member)

            self.assertIn(expected_member, names)
            self.assertEqual(content, b"hello")

    def test_create_backup_writes_step_logs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path: Path = Path(temp_dir)
            source_dir: Path = temp_path / "data1" / "f"
            source_dir.mkdir(parents=True)
            (source_dir / "hello.txt").write_text("hello", encoding="utf-8")
            tmp_dir: Path = temp_path / "fs" / "tmp"
            backups_dir: Path = temp_path / "fs" / "backups"
            tmp_dir.mkdir(parents=True)
            backups_dir.mkdir(parents=True)

            with self._backup_patches(tmp_dir=tmp_dir, backups_dir=backups_dir, source_dir=source_dir, max_backups=5):
                with self.assertLogs("backups.service", level="INFO") as logs:
                    backups.create_backup(now=datetime(2025, 1, 1, 12, 12, 0))

            messages: list[str] = logs.output

            self.assertTrue(any("Backup process started" in message for message in messages))
            self.assertTrue(any("Disk backup item started" in message for message in messages))
            self.assertTrue(any("Encrypted archive finished" in message for message in messages))
            self.assertTrue(any("Backup process finished successfully" in message for message in messages))

    def test_get_backup_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            backups_dir: Path = Path(temp_dir) / "backups"
            backups_dir.mkdir()
            backup_path: Path = backups_dir / "BACKUP-2025-01-01-12:12.zip"
            backup_path.write_text("zip", encoding="utf-8")

            with patch.object(backups, "BACKUPS_DIR", backups_dir):
                self.assertEqual(backups.get_backup_or_none(filename=backup_path.name), backup_path)
                self.assertIsNone(backups.get_backup_or_none(filename="../BACKUP-2025-01-01-12:12.zip"))

    def test_get_backup_rejects_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path: Path = Path(temp_dir)
            backups_dir: Path = temp_path / "backups"
            backups_dir.mkdir()
            outside_file: Path = temp_path / "outside.zip"
            outside_file.write_text("secret", encoding="utf-8")
            symlink_path: Path = backups_dir / "BACKUP-2025-01-01-12:12.zip"

            try:
                symlink_path.symlink_to(outside_file)
            except OSError:
                self.skipTest("symlink is not supported on this filesystem")

            with patch.object(backups, "BACKUPS_DIR", backups_dir):
                self.assertIsNone(backups.get_backup_or_none(filename=symlink_path.name))

    @contextmanager
    def _backup_patches(self, tmp_dir: Path, backups_dir: Path, source_dir: Path, max_backups: int) -> Iterator[None]:
        clean_env: dict[str, str] = {key: value for key, value in os.environ.items() if key not in DATABASE_ENV_KEYS}

        with patch.dict(os.environ, clean_env, clear=True):
            with patch.multiple(
                backups,
                TMP_DIR=tmp_dir,
                BACKUPS_DIR=backups_dir,
                BACKUP_DIRECTORIES=[str(source_dir)],
                AES_ZIP_KEY="secret-key",
                MAX_BACKUPS=max_backups,
            ):
                yield
