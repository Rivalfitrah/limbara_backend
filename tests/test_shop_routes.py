import os
import unittest
from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.routes import auth_route, shop_route


class ShopRouteTests(unittest.TestCase):
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
        app.include_router(shop_route.router, prefix="/api/shops")
        self.client = TestClient(app)

    @contextmanager
    def authenticated_client(self, email="seller@example.com"):
        register_res = self.client.post(
            "/api/auth/register",
            json={
                "email": email,
                "name": "Pengrajin Daur Ulang",
                "password": "password-yang-sangat-kuat-123",
            },
        )
        self.assertEqual(register_res.status_code, 201)
        login_res = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": "password-yang-sangat-kuat-123"},
        )
        self.assertEqual(login_res.status_code, 200)
        yield self.client

    def test_get_my_shop_returns_none_initially(self):
        with self.authenticated_client():
            res = self.client.get("/api/shops/me")
            self.assertEqual(res.status_code, 200)
            self.assertIsNone(res.json())

    def test_create_shop_and_get_my_shop(self):
        with self.authenticated_client():
            payload = {
                "name": "Kreasi Botol Lestari",
                "description": "Pengrajin lampu hias dan pot dari limbah botol PET.",
                "waste_focus": "Plastik PET & Tutup Botol",
                "province": "Jawa Barat",
                "city": "Kota Bandung",
                "district": "Coblong",
                "address": "Jl. Dago Asri No. 12",
                "postal_code": "40135",
                "phone_number": "081234567890",
                "email": "kontak@kreasibotol.id",
                "courier_options": ["JNE", "SiCepat", "GoSend"],
                "logo_url": "https://res.cloudinary.com/demo/image/upload/shop-logo.jpg",
            }
            create_res = self.client.post("/api/shops", json=payload)
            self.assertEqual(create_res.status_code, 201)
            shop_data = create_res.json()
            self.assertEqual(shop_data["name"], "Kreasi Botol Lestari")
            self.assertEqual(shop_data["slug"], "kreasi-botol-lestari")
            self.assertEqual(shop_data["city"], "Kota Bandung")

            # Check /api/shops/me
            my_shop_res = self.client.get("/api/shops/me")
            self.assertEqual(my_shop_res.status_code, 200)
            self.assertEqual(my_shop_res.json()["slug"], "kreasi-botol-lestari")

            update_res = self.client.patch(
                "/api/shops/me",
                json={
                    "name": "Kreasi Botol Nusantara",
                    "description": "Studio karya upcycling dari Bandung.",
                    "logo_url": "https://res.cloudinary.com/demo/image/upload/shop-logo-new.jpg",
                },
            )
            self.assertEqual(update_res.status_code, 200, update_res.text)
            self.assertEqual(update_res.json()["name"], "Kreasi Botol Nusantara")
            self.assertEqual(update_res.json()["slug"], "kreasi-botol-lestari")
            self.assertTrue(update_res.json()["logo_url"].endswith("shop-logo-new.jpg"))

            invalid_update = self.client.patch("/api/shops/me", json={"name": None})
            self.assertEqual(invalid_update.status_code, 422)

            # Check public slug endpoint
            detail_res = self.client.get("/api/shops/kreasi-botol-lestari")
            self.assertEqual(detail_res.status_code, 200)
            self.assertEqual(detail_res.json()["name"], "Kreasi Botol Nusantara")

    def test_cannot_create_duplicate_shop_for_same_user(self):
        with self.authenticated_client():
            payload = {
                "name": "Toko Pertama",
                "province": "DKI Jakarta",
                "city": "Jakarta Selatan",
                "address": "Jl. Tebet Raya No. 5",
                "phone_number": "08111222333",
                "logo_url": "https://res.cloudinary.com/demo/image/upload/shop-one.jpg",
            }
            res1 = self.client.post("/api/shops", json=payload)
            self.assertEqual(res1.status_code, 201)

            # Attempt to create second shop
            res2 = self.client.post(
                "/api/shops",
                json={
                    "name": "Toko Kedua",
                    "province": "DKI Jakarta",
                    "city": "Jakarta Selatan",
                    "address": "Jl. Tebet Barat No. 8",
                    "phone_number": "08111222444",
                    "logo_url": "https://res.cloudinary.com/demo/image/upload/shop-two.jpg",
                },
            )
            self.assertEqual(res2.status_code, 409)

    def test_get_shop_by_unknown_slug_returns_404(self):
        res = self.client.get("/api/shops/toko-tidak-ada-123")
        self.assertEqual(res.status_code, 404)

    def test_create_shop_requires_cloudinary_profile_image(self):
        with self.authenticated_client():
            response = self.client.post(
                "/api/shops",
                json={
                    "name": "Toko Tanpa Foto",
                    "province": "Jawa Barat",
                    "city": "Bandung",
                    "address": "Jl. Merdeka No. 1",
                    "phone_number": "081234567890",
                },
            )
            self.assertEqual(response.status_code, 422)
