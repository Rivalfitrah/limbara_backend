import unittest

from pydantic import ValidationError

from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import (
    create_session_token,
    hash_password,
    hash_session_token,
    normalize_email,
    verify_password,
)


class AuthSecurityTests(unittest.TestCase):
    def test_normalize_email_trims_and_lowercases(self):
        self.assertEqual(normalize_email("  User@Example.COM "), "user@example.com")

    def test_register_request_normalizes_email_and_name(self):
        payload = RegisterRequest(
            email="  USER@example.com ",
            name="  Budi Limbara  ",
            password="rahasia-yang-kuat",
        )

        self.assertEqual(payload.email, "user@example.com")
        self.assertEqual(payload.name, "Budi Limbara")

    def test_register_request_rejects_short_password(self):
        with self.assertRaises(ValidationError):
            RegisterRequest(email="user@example.com", name="Budi", password="pendek")

    def test_login_request_rejects_excessively_long_password(self):
        with self.assertRaises(ValidationError):
            LoginRequest(email="user@example.com", password="x" * 129)

    def test_password_hash_uses_argon2_and_verifies(self):
        encoded = hash_password("rahasia-yang-kuat")

        self.assertTrue(encoded.startswith("$argon2id$"))
        self.assertTrue(verify_password(encoded, "rahasia-yang-kuat"))
        self.assertFalse(verify_password(encoded, "password-yang-salah"))

    def test_session_token_is_random_and_only_hash_is_persistable(self):
        first = create_session_token()
        second = create_session_token()

        self.assertNotEqual(first, second)
        self.assertGreaterEqual(len(first), 32)
        self.assertNotEqual(first, hash_session_token(first))
        self.assertEqual(len(hash_session_token(first)), 64)


if __name__ == "__main__":
    unittest.main()
