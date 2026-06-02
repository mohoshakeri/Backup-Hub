import unittest
from unittest.mock import patch

from core import security


class SecurityTestCase(unittest.TestCase):
    def test_validate_security_settings_rejects_defaults_when_strict(self) -> None:
        with patch.object(security, "STRICT_SECURITY", True):
            with patch.object(security, "AUTH_PASSWORD", security.DEFAULT_AUTH_PASSWORD):
                with self.assertRaises(RuntimeError):
                    security.validate_security_settings()

    def test_validate_security_settings_allows_defaults_when_not_strict(self) -> None:
        with patch.object(security, "STRICT_SECURITY", False):
            security.validate_security_settings()
