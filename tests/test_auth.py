import time
import unittest
from unittest.mock import patch

from services import auth


class AuthTestCase(unittest.TestCase):
    def test_totp_validation_accepts_current_code(self) -> None:
        step: int = 123456
        code: str = auth.generate_totp(step=step)

        with patch.object(time, "time", return_value=step * 30):
            self.assertTrue(auth.validate_totp(code=code))

    def test_session_token_round_trip(self) -> None:
        with patch.object(auth, "AUTH_USERNAME", "admin"), patch.object(auth, "SESSION_TTL_SECONDS", 60):
            token: str = auth.create_session_token()

        self.assertTrue(auth.validate_session_token(token=token))
        self.assertFalse(auth.validate_session_token(token="bad-token"))

    def test_csrf_token_requires_valid_session(self) -> None:
        with patch.object(auth, "AUTH_USERNAME", "admin"), patch.object(auth, "SESSION_TTL_SECONDS", 60):
            session_token: str = auth.create_session_token()
            csrf_token: str = auth.create_csrf_token(session_token=session_token)

        self.assertTrue(auth.validate_csrf_token(session_token=session_token, csrf_token=csrf_token))
        self.assertFalse(auth.validate_csrf_token(session_token=session_token, csrf_token="bad-token"))
        self.assertFalse(auth.validate_csrf_token(session_token="bad-session", csrf_token=csrf_token))
