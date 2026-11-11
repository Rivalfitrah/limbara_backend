import os
import unittest
from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.routes import auth_route, product_route, shop_route


class ProductCrudTests(unittest.TestCase):
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
        app.include_router(product_route.router, prefix="/api")
        self.client = TestClient(app)

    @contextmanager
    def shop_owner_client(self, email="craftsman@example.com"):
        self.client.post(
            "/api/auth/register",
            json={
                "email": email,
                "name": "Budi Pengrajin",
                "password": "password-yang-sangat-kuat-123",
            },
        )
        login_res = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": "password-yang-sangat-kuat-123"},
        )
        self.assertEqual(login_res.status_code, 200)
        shop_res = self.client.post(
            "/api/shops",
            json={
                "name": "Studio Upcycling Nusantara",
                "province": "Jawa Barat",
                "city": "Kota Bandung",
                "address": "Jl. Cihampelas No. 100",
                "phone_number": "081234567890",
                "logo_url": "https://res.cloudinary.com/demo/image/upload/studio-logo.jpg",
            },
        )
        self.assertEqual(shop_res.status_code, 201)
        yield self.client

    def test_product_crud_flow(self):
        with self.shop_owner_client():
            # 1. Create product
            payload = {
                "name": "Lampu Meja PET Bintang",
                "category": "Dekorasi",
                "waste_material": "Botol Plastik PET",
                "price": 125000,
                "stock": 10,
                "image_url": "https://res.cloudinary.com/demo/image/upload/sample.jpg",
                "images": [
                    "https://res.cloudinary.com/demo/image/upload/sample.jpg",
                    "https://res.cloudinary.com/demo/image/upload/sample-2.jpg",
                ],
                "short_description": "Lampu meja hangat daur ulang botol plastik.",
                "description": "Lampu meja estetik dengan rangka kokoh.",
                "weight_grams": 450,
                "impact": "Mengalihkan 20 botol plastik dari TPA",
                "is_active": True,
            }
            create_res = self.client.post("/api/shops/me/products", json=payload)
            self.assertEqual(create_res.status_code, 201, create_res.text)
            product = create_res.json()
            product_id = product["id"]
            self.assertEqual(product["name"], "Lampu Meja PET Bintang")
            self.assertEqual(product["slug"], "lampu-meja-pet-bintang")
            self.assertEqual(product["price"], 125000)
            self.assertTrue(product["is_active"])
            self.assertEqual(len(product["images"]), 2)
            self.assertEqual(product["image_url"], product["images"][0])

            # 2. List shop products
            list_res = self.client.get("/api/shops/me/products")
            self.assertEqual(list_res.status_code, 200)
            items = list_res.json()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["id"], product_id)

            # 3. Get single product
            get_res = self.client.get(f"/api/shops/me/products/{product_id}")
            self.assertEqual(get_res.status_code, 200)
            self.assertEqual(get_res.json()["name"], "Lampu Meja PET Bintang")

            # 4. Update product
            update_res = self.client.put(
                f"/api/shops/me/products/{product_id}",
                json={"price": 140000, "stock": 15},
            )
            self.assertEqual(update_res.status_code, 200)
            updated = update_res.json()
            self.assertEqual(updated["price"], 140000)
            self.assertEqual(updated["stock"], 15)

            # 5. Toggle active status to False
            toggle_res = self.client.patch(
                f"/api/shops/me/products/{product_id}/toggle-active",
                json={"is_active": False},
            )
            self.assertEqual(toggle_res.status_code, 200)
            self.assertFalse(toggle_res.json()["is_active"])

            # 6. Dashboard summary
            dash_res = self.client.get("/api/shops/me/dashboard")
            self.assertEqual(dash_res.status_code, 200)
            summary = dash_res.json()
            self.assertEqual(summary["total_products"], 1)
            self.assertEqual(summary["active_products"], 0)
            self.assertEqual(summary["inactive_products"], 1)
            self.assertEqual(summary["total_stock"], 15)

            # 7. Active product appears in the public marketplace.
            self.client.patch(
                f"/api/shops/me/products/{product_id}/toggle-active",
                json={"is_active": True},
            )
            public_list = self.client.get("/api/products?page=1&page_size=12")
            self.assertEqual(public_list.status_code, 200, public_list.text)
            self.assertEqual(public_list.json()["total"], 1)
            self.assertEqual(public_list.json()["items"][0]["shop"]["name"], "Studio Upcycling Nusantara")

            public_detail = self.client.get(f"/api/products/{product['slug']}")
            self.assertEqual(public_detail.status_code, 200)
            self.assertEqual(public_detail.json()["id"], product_id)

            # 8. Delete product
            del_res = self.client.delete(f"/api/shops/me/products/{product_id}")
            self.assertEqual(del_res.status_code, 204)

            # Verify deleted
            get_after_del = self.client.get(f"/api/shops/me/products/{product_id}")
            self.assertEqual(get_after_del.status_code, 404)

    def test_product_rejects_more_than_five_images(self):
        with self.shop_owner_client(email="five-images@example.com"):
            images = [
                f"https://res.cloudinary.com/demo/image/upload/product-{index}.jpg"
                for index in range(6)
            ]
            response = self.client.post(
                "/api/shops/me/products",
                json={
                    "name": "Produk Terlalu Banyak Foto",
                    "category": "Dekorasi",
                    "waste_material": "Botol Plastik PET",
                    "price": 50000,
                    "stock": 1,
                    "image_url": images[0],
                    "images": images,
                },
            )
            self.assertEqual(response.status_code, 422)
