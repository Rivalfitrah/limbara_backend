import unittest

from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import AuthAccount, UserSession
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import (
    authenticate_manual_user,
    create_user_session,
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


if __name__ == "__main__":
    unittest.main()
