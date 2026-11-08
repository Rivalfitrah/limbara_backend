import os
import unittest
from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.routes import auth_route


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
        yield self.client

    def test_register_sets_http_only_session_cookie_and_returns_user(self):
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": "USER@example.com",
                "name": "Budi Limbara",
                "password": "rahasia-yang-kuat",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["email"], "user@example.com")
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("limbara_session=", cookie)
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=lax", cookie)

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


if __name__ == "__main__":
    unittest.main()
