import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import AuthAccount, UserSession
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import (
    authenticate_manual_user,
    create_user_session,
    fetch_google_profile,
    get_user_from_session_token,
    register_manual_user,
    revoke_session_token,
    upsert_google_user,
)


class AuthServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    def setUp(self):
        SQLModel.metadata.drop_all(self.engine)
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self):
        self.session.close()

    def test_register_manual_user_stores_argon2_hash_not_plaintext(self):
        user = register_manual_user(
            self.session,
            RegisterRequest(email="USER@example.com", name="Budi", password="rahasia-yang-kuat"),
        )

        account = self.session.exec(select(AuthAccount).where(AuthAccount.user_id == user.id)).one()
        self.assertEqual(user.email, "user@example.com")
        self.assertEqual(account.provider, "LOCAL")
        self.assertNotEqual(account.password_hash, "rahasia-yang-kuat")
        self.assertTrue(account.password_hash.startswith("$argon2id$"))
        self.assertIsNone(user.last_login_at)

    def test_register_manual_user_rejects_duplicate_email(self):
        payload = RegisterRequest(email="user@example.com", name="Budi", password="rahasia-yang-kuat")
        register_manual_user(self.session, payload)

        with self.assertRaises(HTTPException) as context:
            register_manual_user(self.session, payload)

        self.assertEqual(context.exception.status_code, 409)

    def test_authenticate_manual_user_accepts_only_correct_password(self):
        register_manual_user(
            self.session,
            RegisterRequest(email="user@example.com", name="Budi", password="rahasia-yang-kuat"),
        )

        user = authenticate_manual_user(
            self.session,
            LoginRequest(email="user@example.com", password="rahasia-yang-kuat"),
        )
        self.assertEqual(user.email, "user@example.com")

        with self.assertRaises(HTTPException) as context:
            authenticate_manual_user(
                self.session,
                LoginRequest(email="user@example.com", password="password-yang-salah"),
            )
        self.assertEqual(context.exception.status_code, 401)

    def test_session_token_resolves_user_and_can_be_revoked(self):
        user = register_manual_user(
            self.session,
            RegisterRequest(email="user@example.com", name="Budi", password="rahasia-yang-kuat"),
        )

        token = create_user_session(self.session, user, user_agent="Unit Test")
        stored_session = self.session.exec(select(UserSession)).one()

        self.assertNotEqual(stored_session.token_hash, token)
        self.assertEqual(get_user_from_session_token(self.session, token).id, user.id)

        revoke_session_token(self.session, token)
        self.assertIsNone(get_user_from_session_token(self.session, token))

    def test_session_expires_after_two_hours_idle(self):
        user = register_manual_user(
            self.session,
            RegisterRequest(email="idle@example.com", name="Budi", password="rahasia-yang-kuat"),
        )
        token = create_user_session(self.session, user)
        stored_session = self.session.exec(select(UserSession)).one()
        stored_session.last_seen_at = stored_session.last_seen_at - __import__("datetime").timedelta(hours=2, seconds=1)
        self.session.add(stored_session)
        self.session.commit()
        self.assertIsNone(get_user_from_session_token(self.session, token))

    def test_fourth_session_revokes_oldest_active_session(self):
        user = register_manual_user(
            self.session,
            RegisterRequest(email="devices@example.com", name="Budi", password="rahasia-yang-kuat"),
        )
        tokens = [create_user_session(self.session, user) for _ in range(4)]
        sessions = self.session.exec(select(UserSession).order_by(UserSession.created_at)).all()
        self.assertEqual(sum(item.revoked_at is None for item in sessions), 3)
        self.assertIsNone(get_user_from_session_token(self.session, tokens[0]))
        self.assertIsNotNone(get_user_from_session_token(self.session, tokens[-1]))

    def test_google_user_creates_google_identity(self):
        user = upsert_google_user(
            self.session,
            {
                "sub": "google-subject",
                "email": "GOOGLE@example.com",
                "email_verified": True,
                "name": "Google User",
                "picture": "https://example.com/avatar.png",
            },
        )

        account = self.session.exec(select(AuthAccount).where(AuthAccount.user_id == user.id)).one()
        self.assertEqual(user.email, "google@example.com")
        self.assertIsNotNone(user.email_verified_at)
        self.assertEqual(account.provider, "GOOGLE")
        self.assertEqual(account.provider_subject, "google-subject")

    def test_google_user_does_not_silently_link_matching_local_email(self):
        register_manual_user(
            self.session,
            RegisterRequest(email="user@example.com", name="Budi", password="rahasia-yang-kuat"),
        )

        with self.assertRaises(HTTPException) as context:
            upsert_google_user(
                self.session,
                {
                    "sub": "google-subject",
                    "email": "user@example.com",
                    "email_verified": True,
                },
            )

        self.assertEqual(context.exception.status_code, 409)

    def test_fetch_google_profile_verifies_id_token_and_nonce(self):
        os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
        os.environ["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["GOOGLE_REDIRECT_URI"] = "http://localhost:8005/api/auth/google/callback"

        mock_response = MagicMock()
        mock_response.is_error = False
        mock_response.json.return_value = {
            "access_token": "mock-access-token",
            "id_token": "signed-google-token",
        }

        verified_claims = {
            "sub": "1234567890",
            "email": "tester@gmail.com",
            "email_verified": True,
            "name": "Tester Limbara",
            "picture": "https://example.com/avatar.jpg",
            "nonce": "expected-nonce",
        }
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, patch(
            "app.services.auth_service.google_id_token.verify_oauth2_token",
            return_value=verified_claims,
        ) as mock_verify:
            mock_post.return_value = mock_response
            profile = asyncio.run(fetch_google_profile("test-auth-code", "expected-nonce"))

        mock_verify.assert_called_once()
        self.assertEqual(profile["sub"], "1234567890")
        self.assertEqual(profile["email"], "tester@gmail.com")
        self.assertEqual(profile["name"], "Tester Limbara")
        self.assertEqual(profile["picture"], "https://example.com/avatar.jpg")

    def test_fetch_google_profile_raises_503_on_network_failure(self):
        os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
        os.environ["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["GOOGLE_REDIRECT_URI"] = "http://localhost:8005/api/auth/google/callback"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused / DNS failure")
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with self.assertRaises(HTTPException) as ctx:
                    asyncio.run(fetch_google_profile("test-auth-code", "expected-nonce"))

        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("Gagal terhubung ke server autentikasi Google", ctx.exception.detail)

    def test_fetch_google_profile_rejects_nonce_mismatch(self):
        os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
        os.environ["GOOGLE_CLIENT_SECRET"] = "test-client-secret"
        os.environ["GOOGLE_REDIRECT_URI"] = "http://localhost:8005/api/auth/google/callback"
        mock_response = MagicMock()
        mock_response.is_error = False
        mock_response.json.return_value = {"id_token": "signed-google-token"}
        claims = {
            "sub": "1234567890",
            "email": "tester@gmail.com",
            "email_verified": True,
            "nonce": "different-nonce",
        }
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response), patch(
            "app.services.auth_service.google_id_token.verify_oauth2_token",
            return_value=claims,
        ):
            with self.assertRaises(HTTPException) as context:
                asyncio.run(fetch_google_profile("test-auth-code", "expected-nonce"))

        self.assertEqual(context.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
