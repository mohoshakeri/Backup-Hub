import tempfile
import unittest
from pathlib import Path

from endpoints.web import _backup_view, _nginx_download_response


class FrontendTestCase(unittest.TestCase):
    def test_frontend_assets_are_separated(self) -> None:
        required_files: list[Path] = [
            Path("templates/base.html"),
            Path("templates/login.html"),
            Path("templates/dashboard.html"),
            Path("static/css/app.css"),
            Path("static/js/app.js"),
        ]

        for path in required_files:
            self.assertTrue(path.is_file())

    def test_backup_view_model_contains_download_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path: Path = Path(temp_dir) / "BACKUP-2025-01-01-12:12.zip"
            backup_path.write_bytes(b"backup")

            backup: dict[str, str] = _backup_view(backup=backup_path)

        self.assertEqual(backup["name"], "BACKUP-2025-01-01-12:12.zip")
        self.assertEqual(backup["size"], "6.00 B")
        self.assertEqual(backup["download_url"], "/backups/BACKUP-2025-01-01-12:12.zip/download")

    def test_nginx_download_response_uses_x_accel_redirect(self) -> None:
        backup_path: Path = Path("BACKUP-2025-01-01-12:12.zip")

        response = _nginx_download_response(backup_path=backup_path)

        self.assertEqual(response.headers["x-accel-redirect"], "/_protected_backups/BACKUP-2025-01-01-12%3A12.zip")
        self.assertEqual(response.headers["content-type"], "application/octet-stream")
