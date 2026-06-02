import unittest
from unittest.mock import patch

from services import download_tokens


class DownloadTokensTestCase(unittest.TestCase):
    def test_download_token_round_trip(self) -> None:
        token: str = download_tokens.create_download_token(filename="BACKUP.zip")

        self.assertTrue(download_tokens.validate_download_token(token=token, filename="BACKUP.zip"))

    def test_download_token_rejects_wrong_filename(self) -> None:
        token: str = download_tokens.create_download_token(filename="BACKUP.zip")

        self.assertFalse(download_tokens.validate_download_token(token=token, filename="OTHER.zip"))

    def test_download_token_expires(self) -> None:
        with patch.object(download_tokens, "DOWNLOAD_LINK_TTL_SECONDS", -1):
            token: str = download_tokens.create_download_token(filename="BACKUP.zip")

        self.assertFalse(download_tokens.validate_download_token(token=token, filename="BACKUP.zip"))
