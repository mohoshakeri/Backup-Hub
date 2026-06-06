import unittest
from unittest.mock import patch

from starlette.requests import Request

from core import security
from utils import middlewares


class SecurityTestCase(unittest.TestCase):
    def test_validate_security_settings_rejects_defaults_when_strict(self) -> None:
        with patch.object(security, "STRICT_SECURITY", True):
            with patch.object(security, "AUTH_PASSWORD", security.DEFAULT_AUTH_PASSWORD):
                with self.assertRaises(RuntimeError):
                    security.validate_security_settings()

    def test_validate_security_settings_allows_defaults_when_not_strict(self) -> None:
        with patch.object(security, "STRICT_SECURITY", False):
            security.validate_security_settings()

    def test_allowed_origins_include_forwarded_host_with_port(self) -> None:
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/login",
                "scheme": "http",
                "headers": [
                    (b"host", b"localhost"),
                    (b"x-forwarded-host", b"localhost:8989"),
                    (b"x-forwarded-proto", b"http"),
                ],
            }
        )

        with patch.object(middlewares, "CORS_ALLOWEDS", []):
            allowed_origins: set[str] = middlewares._allowed_origins(request=request)

        self.assertIn("http://localhost:8989", allowed_origins)

    def test_null_origin_is_not_allowed_as_general_origin(self) -> None:
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/login",
                "scheme": "http",
                "headers": [
                    (b"host", b"127.0.0.1:8000"),
                    (b"origin", b"null"),
                    (b"sec-fetch-site", b"same-origin"),
                ],
            }
        )

        self.assertFalse(middlewares._is_allowed_origin(request=request, origin="null"))

    def test_null_origin_is_rejected_for_cross_site_posts(self) -> None:
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/login",
                "scheme": "http",
                "headers": [
                    (b"host", b"127.0.0.1:8000"),
                    (b"origin", b"null"),
                    (b"sec-fetch-site", b"cross-site"),
                ],
            }
        )

        self.assertFalse(middlewares._is_allowed_origin(request=request, origin="null"))

    def test_route_level_csrf_paths_can_handle_null_origin_themselves(self) -> None:
        for path in ["/login", "/logout", "/backups/BACKUP-2025-01-01-12:12.zip/download"]:
            request = Request(
                {
                    "type": "http",
                    "method": "POST",
                    "path": path,
                    "scheme": "http",
                    "headers": [
                        (b"host", b"127.0.0.1:8000"),
                        (b"origin", b"null"),
                        (b"sec-fetch-site", b"same-origin"),
                    ],
                }
            )

            self.assertTrue(middlewares._has_route_level_csrf(request=request))

    def test_unprotected_paths_do_not_bypass_origin_validation(self) -> None:
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/unknown",
                "scheme": "http",
                "headers": [
                    (b"host", b"127.0.0.1:8000"),
                    (b"origin", b"null"),
                    (b"sec-fetch-site", b"same-origin"),
                ],
            }
        )

        self.assertFalse(middlewares._has_route_level_csrf(request=request))
