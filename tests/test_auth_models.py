import unittest

from sqlmodel import SQLModel

from app.models import AuthAccount, AuthRateLimit, OAuthLoginState, User, UserSession


class AuthModelTests(unittest.TestCase):
    def test_auth_tables_are_registered(self):
        self.assertIn(AuthAccount.__tablename__, SQLModel.metadata.tables)
        self.assertIn(UserSession.__tablename__, SQLModel.metadata.tables)
        self.assertIn(AuthRateLimit.__tablename__, SQLModel.metadata.tables)
        self.assertIn(OAuthLoginState.__tablename__, SQLModel.metadata.tables)

    def test_google_id_is_nullable_during_migration(self):
        self.assertTrue(User.__table__.c.google_id.nullable)

    def test_auth_account_provider_is_unique_per_user(self):
        constraint_names = {constraint.name for constraint in AuthAccount.__table__.constraints}

        self.assertIn("uq_auth_accounts_user_provider", constraint_names)
        self.assertIn("uq_auth_accounts_provider_subject", constraint_names)

    def test_session_token_hash_is_unique(self):
        self.assertTrue(UserSession.__table__.c.token_hash.unique)


if __name__ == "__main__":
    unittest.main()
