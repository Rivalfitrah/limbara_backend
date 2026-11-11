import os
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel import select
from jose import jwt

from app.database import get_session
from app.routes import auth_route
from app.models import User


class AuthRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["COOKIE_SECURE"] = "false"
        os.environ["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-characters"
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    def setUp(self):
        SQLModel.metadata.drop_all(self.engine)
        SQLModel.metadata.create_all(self.engine)

        app = FastAPI()

        def override_session():
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_session
        app.include_router(auth_route.router, prefix="/api/auth")
        self.client = TestClient(app)

    @contextmanager
    def registered_client(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "name": "Budi Limbara",
                "password": "rahasia-yang-kuat",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        login_response = self.client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "rahasia-yang-kuat"},
        )
        self.assertEqual(login_response.status_code, 200, login_response.text)
        yield self.client

    def test_register_requires_separate_login_and_sets_no_session_cookie(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": "USER@example.com",
                "name": "Budi Limbara",
                "password": "rahasia-yang-kuat",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["message"], "Akun berhasil dibuat. Silakan masuk.")
        cookie = response.headers.get("set-cookie", "").lower()
        self.assertIn("limbara_session=", cookie)
        self.assertIn("max-age=0", cookie)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_registered_session_can_read_me_then_logout(self):
        with self.registered_client() as client:
            me_response = client.get("/api/auth/me")
            self.assertEqual(me_response.status_code, 200)
            self.assertEqual(me_response.json()["name"], "Budi Limbara")

            logout_response = client.post("/api/auth/logout")
            self.assertEqual(logout_response.status_code, 204)
            self.assertEqual(client.get("/api/auth/me").status_code, 401)

    def test_login_rejects_wrong_password_with_generic_error(self):
        with self.registered_client() as client:
            client.post("/api/auth/logout")
            response = client.post(
                "/api/auth/login",
                json={"email": "user@example.com", "password": "password-yang-salah"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Email atau password tidak valid.")

    def test_login_rate_limit_blocks_repeated_failures(self):
        register = self.client.post(
            "/api/auth/register",
            json={
                "email": "limited@example.com",
                "name": "Budi Limbara",
                "password": "rahasia-yang-kuat",
            },
        )
        self.assertEqual(register.status_code, 201)

        responses = [
            self.client.post(
                "/api/auth/login",
                json={"email": "limited@example.com", "password": "password-yang-salah"},
            )
            for _ in range(6)
        ]

        self.assertEqual(responses[-1].status_code, 429)
        self.assertIn("retry-after", responses[-1].headers)

    def test_register_rejects_untrusted_browser_origin(self):
        response = self.client.post(
            "/api/auth/register",
            headers={"Origin": "https://attacker.example"},
            json={
                "email": "user@example.com",
                "name": "Budi Limbara",
                "password": "rahasia-yang-kuat",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_legacy_jwt_cookie_no_longer_authenticates(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": "legacy@example.com",
                "name": "Legacy User",
                "password": "rahasia-yang-kuat",
            },
        )
        self.assertEqual(response.status_code, 201)
        with Session(self.engine) as session:
            user = session.exec(select(User).where(User.email == "legacy@example.com")).one()
        legacy_token = jwt.encode(
            {"sub": str(user.id)},
            os.environ["JWT_SECRET_KEY"],
            algorithm="HS256",
        )
        self.client.cookies.set("limbara_access_token", legacy_token)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_google_callback_redirects_to_login_with_auth_error_on_failure(self):
        with patch("app.routes.auth_route.fetch_google_profile") as mock_fetch:
            mock_fetch.side_effect = HTTPException(status_code=503, detail="Layanan Google tidak dapat dihubungi.")
            response = self.client.get(
                "/api/auth/google/callback?code=testcode&state=invalidstate",
                follow_redirects=False,
            )

        self.assertEqual(response.status_code, 307)
        self.assertIn("/login?auth_error=", response.headers["location"])

    def test_google_state_is_single_use(self):
        start = self.client.get(
            "/api/auth/google/login?return_to=http://localhost:3000",
            follow_redirects=False,
        )
        self.assertEqual(start.status_code, 307)
        from urllib.parse import parse_qs, urlparse

        state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
        profile = {
            "sub": "google-once",
            "email": "once@example.com",
            "email_verified": True,
            "name": "Google Once",
        }
        with patch("app.routes.auth_route.fetch_google_profile", return_value=profile):
            first = self.client.get(
                f"/api/auth/google/callback?code=testcode&state={state}",
                follow_redirects=False,
            )
            second = self.client.get(
                f"/api/auth/google/callback?code=testcode&state={state}",
                follow_redirects=False,
            )

        self.assertEqual(first.status_code, 307)
        self.assertEqual(first.headers["location"], "http://localhost:3000")
        self.assertIn("/login?auth_error=", second.headers["location"])


if __name__ == "__main__":
    unittest.main()
