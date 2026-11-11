import asyncio
import hashlib
import os
import unittest
import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.database import get_session
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.review import ProductReview
from app.models.shop import Shop
from app.models.user import User
from app.routes import auth_route, order_route, review_route, shipping_route
from app.services.payment_service import verify_midtrans_signature
from app.services.shipping_service import calculate_shipping_cost, get_provinces


class OrderAndShippingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["COOKIE_SECURE"] = "false"
        os.environ["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-characters"
        os.environ["MIDTRANS_SERVER_KEY"] = "SB-Mid-server-testkey123"
        os.environ["MIDTRANS_SIGNATURE_KEY"] = "SB-Mid-signature-testkey123"
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
        app.include_router(shipping_route.router, prefix="/api/shipping")
        app.include_router(order_route.router, prefix="/api/orders")
        app.include_router(review_route.router, prefix="/api")
        self.client = TestClient(app)

    def test_get_provinces_returns_provinces(self):
        with patch("app.services.shipping_service._get_api_key", return_value=""):
            provinces = asyncio.run(get_provinces())
            self.assertIsInstance(provinces, list)
            self.assertTrue(len(provinces) > 0)
            self.assertIn("province", provinces[0])

    def test_calculate_shipping_cost_jnt(self):
        with patch("app.services.shipping_service._get_api_key", return_value=""):
            results = asyncio.run(
                calculate_shipping_cost(
                    origin_city_id="151",
                    destination_city_id="444",
                    weight_grams=1000,
                    courier="jnt",
                )
            )
            self.assertEqual(results[0]["code"], "jnt")
            self.assertEqual(results[0]["name"], "J&T Express")
            services = [c["service"] for c in results[0]["costs"]]
            self.assertIn("EZ", services)

    def test_verify_midtrans_signature(self):
        order_id = "LMB-TEST-001"
        status_code = "200"
        gross_amount = "75000"
        key = "SB-Mid-signature-testkey123"
        valid_signature = hashlib.sha512(f"{order_id}{status_code}{gross_amount}{key}".encode()).hexdigest()

        self.assertTrue(
            verify_midtrans_signature(
                {
                    "order_id": order_id,
                    "status_code": status_code,
                    "gross_amount": gross_amount,
                    "signature_key": valid_signature,
                }
            )
        )

        self.assertFalse(
            verify_midtrans_signature(
                {
                    "order_id": order_id,
                    "status_code": status_code,
                    "gross_amount": gross_amount,
                    "signature_key": "invalid-signature",
                }
            )
        )

    def test_checkout_creates_order_and_reduces_stock(self):
        # 1. Register buyer
        self.client.post(
            "/api/auth/register",
            json={"email": "buyer@example.com", "name": "Budi Pembeli", "password": "rahasia-password-123"},
        )
        login_res = self.client.post(
            "/api/auth/login",
            json={"email": "buyer@example.com", "password": "rahasia-password-123"},
        )
        self.assertEqual(login_res.status_code, 200)

        # 2. Seed shop and product directly in DB
        with Session(self.engine) as session:
            user = User(email="seller@example.com", name="Seller")
            session.add(user)
            session.flush()

            shop = Shop(
                user_id=user.id,
                name="Toko Daur Ulang",
                slug="toko-daur-ulang",
                province="DKI Jakarta",
                city="Jakarta Barat",
                address="Jl. Daur Ulang No. 1",
                phone_number="08123456789",
            )
            session.add(shop)
            session.flush()

            product = Product(
                shop_id=shop.id,
                name="Tas Belanja Goni",
                slug="tas-belanja-goni",
                category="Fashion",
                waste_material="Karung Goni",
                price=50000,
                stock=10,
                image_url="https://example.com/tas.jpg",
                weight_grams=300,
            )
            session.add(product)
            session.commit()
            product_id = str(product.id)

        # 3. Mock Snap creation
        with patch("app.routes.order_route.create_snap_transaction", new_callable=AsyncMock) as mock_snap:
            mock_snap.return_value = {
                "token": "snap-token-xyz-123",
                "redirect_url": "https://app.sandbox.midtrans.com/snap/v2/vtweb/xyz-123",
            }

            response = self.client.post(
                "/api/orders/checkout",
                json={
                    "items": [{"product_id": product_id, "quantity": 2}],
                    "recipient_name": "Budi Pembeli",
                    "recipient_phone": "081234567890",
                    "shipping_address": "Jl. Mawar No. 5",
                    "shipping_province": "DKI Jakarta",
                    "shipping_city": "Jakarta Barat",
                    "shipping_postal_code": "11220",
                    "courier": "JNT",
                    "courier_service": "EZ",
                    "shipping_cost": 19000,
                    "notes": "Titipkan satpam",
                },
            )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["total_product_amount"], 100000)
        self.assertEqual(data["shipping_cost"], 19000)
        self.assertEqual(data["total_amount"], 119000)
        self.assertEqual(data["status"], "PENDING")
        self.assertEqual(data["snap_token"], "snap-token-xyz-123")
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["quantity"], 2)

        # 4. Verify stock was reduced from 10 to 8
        with Session(self.engine) as session:
            updated_product = session.get(Product, uuid.UUID(product_id))
            self.assertEqual(updated_product.stock, 8)
            self.assertEqual(updated_product.sold_count, 2)

    def test_order_full_lifecycle_and_review(self):
        buyer_client = TestClient(self.client.app)
        seller_client = TestClient(self.client.app)

        # 1. Register buyer and seller
        buyer_res = buyer_client.post(
            "/api/auth/register",
            json={"email": "buyer_cycle@example.com", "name": "Budi Pembeli", "password": "rahasia-buyer-kuat-123"},
        )
        self.assertEqual(buyer_res.status_code, 201)

        seller_res = seller_client.post(
            "/api/auth/register",
            json={"email": "seller_cycle@example.com", "name": "Siti Penjual", "password": "rahasia-seller-kuat-123"},
        )
        self.assertEqual(seller_res.status_code, 201)
        self.assertEqual(
            buyer_client.post(
                "/api/auth/login",
                json={"email": "buyer_cycle@example.com", "password": "rahasia-buyer-kuat-123"},
            ).status_code,
            200,
        )
        self.assertEqual(
            seller_client.post(
                "/api/auth/login",
                json={"email": "seller_cycle@example.com", "password": "rahasia-seller-kuat-123"},
            ).status_code,
            200,
        )
        with Session(self.engine) as session:
            seller = session.exec(select(User).where(User.email == "seller_cycle@example.com")).one()
            seller_id = seller.id

        # 2. Seed shop and product for seller
        with Session(self.engine) as session:
            shop = Shop(
                user_id=seller_id,
                name="Siti Craft Studio",
                slug="siti-craft-studio",
                province="Jawa Barat",
                city="Bandung",
                address="Jl. Dago No. 12",
                phone_number="08123456789",
            )
            session.add(shop)
            session.flush()

            prod = Product(
                shop_id=shop.id,
                name="Vas Bunga Kaca",
                slug="vas-bunga-kaca",
                category="Dekorasi",
                waste_material="Botol Kaca",
                price=75000,
                stock=5,
                image_url="https://example.com/vas.jpg",
                weight_grams=500,
            )
            session.add(prod)
            session.commit()
            product_id = str(prod.id)

        # 3. Buyer checkouts
        with patch("app.routes.order_route.create_snap_transaction", new_callable=AsyncMock) as mock_snap:
            mock_snap.return_value = {
                "token": "snap-cycle-token",
                "redirect_url": "https://app.sandbox.midtrans.com/snap/v2/vtweb/cycle",
            }
            checkout_res = buyer_client.post(
                "/api/orders/checkout",
                json={
                    "items": [{"product_id": product_id, "quantity": 1}],
                    "recipient_name": "Budi Pembeli",
                    "recipient_phone": "081234567890",
                    "shipping_address": "Jl. Merdeka No. 1",
                    "shipping_province": "Jawa Barat",
                    "shipping_city": "Bandung",
                    "courier": "JNT",
                    "courier_service": "EZ",
                    "shipping_cost": 10000,
                },
            )
        self.assertEqual(checkout_res.status_code, 201)
        order_data = checkout_res.json()
        order_id = order_data["id"]
        self.assertEqual(order_data["status"], "PENDING")

        # 4. Mark paid -> Status turns DIPROSES
        paid_res = buyer_client.post(f"/api/orders/{order_id}/mark-paid")
        self.assertEqual(paid_res.status_code, 200)
        self.assertEqual(paid_res.json()["status"], "DIPROSES")

        # 5. Seller checks orders
        seller_orders_res = seller_client.get("/api/orders/shop/me")
        self.assertEqual(seller_orders_res.status_code, 200)
        seller_orders = seller_orders_res.json()
        self.assertEqual(len(seller_orders), 1)
        self.assertEqual(seller_orders[0]["id"], order_id)

        # 6. Seller ships order with resi -> Status turns DIKIRIM
        ship_res = seller_client.post(
            f"/api/orders/shop/me/{order_id}/ship",
            json={"tracking_number": "JT123456789ID"},
        )
        self.assertEqual(ship_res.status_code, 200)
        self.assertEqual(ship_res.json()["status"], "DIKIRIM")
        self.assertEqual(ship_res.json()["tracking_number"], "JT123456789ID")

        # 7. Check review eligibility before buyer completes -> must be False
        elig_before = buyer_client.get(f"/api/products/{product_id}/review-eligibility")
        self.assertEqual(elig_before.status_code, 200)
        self.assertFalse(elig_before.json()["can_review"])

        # 8. Buyer confirms order complete -> Status turns SELESAI
        complete_res = buyer_client.post(f"/api/orders/{order_id}/complete")
        self.assertEqual(complete_res.status_code, 200)
        self.assertEqual(complete_res.json()["status"], "SELESAI")

        # 9. Check review eligibility after complete -> must be True
        elig_after = buyer_client.get(f"/api/products/{product_id}/review-eligibility")
        self.assertEqual(elig_after.status_code, 200)
        self.assertTrue(elig_after.json()["can_review"])
        self.assertEqual(elig_after.json()["order_id"], order_id)

        # 10. Buyer submits review
        review_res = buyer_client.post(
            f"/api/products/{product_id}/reviews",
            json={
                "order_id": order_id,
                "rating": 5,
                "comment": "Vas bunganya rapi banget dari botol daur ulang!",
            },
        )
        self.assertEqual(review_res.status_code, 201)
        rev_data = review_res.json()
        self.assertEqual(rev_data["rating"], 5)
        self.assertEqual(rev_data["user_name"], "Budi Pembeli")

        # 11. Duplicate review attempt is blocked
        dup_res = buyer_client.post(
            f"/api/products/{product_id}/reviews",
            json={
                "order_id": order_id,
                "rating": 4,
                "comment": "Coba ulas lagi",
            },
        )
        self.assertEqual(dup_res.status_code, 400)

        # 12. Review eligibility is now False because it has been reviewed
        elig_final = buyer_client.get(f"/api/products/{product_id}/review-eligibility")
        self.assertEqual(elig_final.status_code, 200)
        self.assertFalse(elig_final.json()["can_review"])

        # 13. Public product reviews list contains the new review
        public_reviews = self.client.get(f"/api/products/{product_id}/reviews")
        self.assertEqual(public_reviews.status_code, 200)
        self.assertEqual(len(public_reviews.json()), 1)
        self.assertEqual(public_reviews.json()[0]["comment"], "Vas bunganya rapi banget dari botol daur ulang!")


if __name__ == "__main__":
    unittest.main()
