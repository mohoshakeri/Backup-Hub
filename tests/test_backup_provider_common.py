import unittest

from backup_providers.common import sanitize_command_output


class BackupProviderCommonTestCase(unittest.TestCase):
    def test_sanitize_command_output_redacts_uri_password(self) -> None:
        message: str = (
            "failed to connect to mongodb://admin:plain-secret@mongo:27017: "
            "Authentication failed"
        )

        sanitized_message: str = sanitize_command_output(message=message)

        self.assertNotIn("plain-secret", sanitized_message)
        self.assertIn("mongodb://admin:***@mongo:27017", sanitized_message)

    def test_sanitize_command_output_redacts_password_arguments(self) -> None:
        message: str = "mysqldump failed with --password=plain-secret and exit code 1"

        sanitized_message: str = sanitize_command_output(message=message)

        self.assertNotIn("plain-secret", sanitized_message)
        self.assertIn("--password=***", sanitized_message)

    def test_sanitize_command_output_redacts_env_style_secrets(self) -> None:
        message: str = "PGPASSWORD=plain-secret BACKUP_HUB_AES_ZIP_KEY=zip-secret failed"

        sanitized_message: str = sanitize_command_output(message=message)

        self.assertNotIn("plain-secret", sanitized_message)
        self.assertNotIn("zip-secret", sanitized_message)
        self.assertIn("PGPASSWORD=***", sanitized_message)
        self.assertIn("BACKUP_HUB_AES_ZIP_KEY=***", sanitized_message)

    def test_sanitize_command_output_redacts_key_value_secrets(self) -> None:
        message: str = '{"password":"plain-secret","token":"token-secret","safe":"value"}'

        sanitized_message: str = sanitize_command_output(message=message)

        self.assertNotIn("plain-secret", sanitized_message)
        self.assertNotIn("token-secret", sanitized_message)
        self.assertIn('"password":"***"', sanitized_message)
        self.assertIn('"token":"***"', sanitized_message)
        self.assertIn('"safe":"value"', sanitized_message)
