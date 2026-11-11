from datetime import datetime, timedelta, timezone
from typing import Any

from sqlmodel import Session, select

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.review import ProductReview
from app.models.shop import Shop
from app.models.user import User


SEED_SELLER = {
    "email": "demo-seller@limbara.test",
    "name": "Nadia Prameswari",
    "avatar_url": None,
    "is_active": True,
}

SEED_BUYERS = (
    {
        "email": "demo-buyer1@limbara.test",
        "name": "Budi Santoso",
        "avatar_url": None,
        "is_active": True,
    },
    {
        "email": "demo-buyer2@limbara.test",
        "name": "Ayu Lestari",
        "avatar_url": None,
        "is_active": True,
    },
)

SEED_SHOP = {
    "name": "Plastik Jadi Karya",
    "slug": "plastik-jadi-karya",
    "description": (
        "Studio kerajinan yang mengubah botol plastik bekas menjadi dekorasi "
        "dan karya kreatif untuk rumah."
    ),
    "waste_focus": "Botol plastik PET",
    "province": "Jawa Barat",
    "city": "Bandung",
    "district": "Coblong",
    "address": "Jl. Ir. H. Juanda No. 88, Bandung",
    "postal_code": "40132",
    "phone_number": "081234567890",
    "email": "plastikjadikarya@limbara.test",
    "courier_options": ["JNE", "JNT", "SiCepat"],
    "logo_url": "/img/botol_plastik_pot_bunga.png",
    "banner_url": "/img/botol_plastik_lampu_kamar.png",
    "is_verified": True,
}

SEED_PRODUCTS = (
    {
        "name": "Lampu Kamar Botol Plastik",
        "slug": "lampu-kamar-botol-plastik",
        "category": "Dekorasi Rumah",
        "waste_material": "Botol Plastik PET",
        "price": 129_000,
        "previous_price": 149_000,
        "stock": 8,
        "image_url": "/img/botol_plastik_lampu_kamar.png",
        "images": ["/img/botol_plastik_lampu_kamar.png"],
        "short_description": "Lampu dekoratif hangat dari botol plastik bekas pilihan.",
        "description": (
            "Lampu kamar buatan tangan dengan kap yang dirangkai dari botol PET bekas. "
            "Cocok menjadi lampu tidur atau aksen dekorasi meja. Setiap produk memiliki "
            "sedikit perbedaan bentuk karena dibuat secara manual."
        ),
        "weight_grams": 650,
        "dimensions": "22 x 22 x 35 cm",
        "production_time": "3-5 hari",
        "impact": "Memanfaatkan sekitar 18 botol plastik bekas.",
        "is_active": True,
        "sold_count": 2,
        "reviews": (
            (5, "Cahayanya hangat dan bentuknya unik. Kemasannya juga aman sampai rumah."),
            (4, "Hasil kerajinannya rapi dan cocok untuk meja kamar. Kabelnya cukup panjang."),
        ),
    },
    {
        "name": "Pot Bunga Botol Plastik",
        "slug": "pot-bunga-botol-plastik",
        "category": "Rumah dan Taman",
        "waste_material": "Botol Plastik PET",
        "price": 49_000,
        "previous_price": 59_000,
        "stock": 16,
        "image_url": "/img/botol_plastik_pot_bunga.png",
        "images": ["/img/botol_plastik_pot_bunga.png"],
        "short_description": "Pot dekoratif ringan untuk tanaman kecil dan sukulen.",
        "description": (
            "Pot bunga dekoratif dari botol plastik yang telah dicuci dan dibentuk ulang. "
            "Memiliki lubang drainase dan sesuai untuk sukulen, kaktus mini, atau tanaman meja."
        ),
        "weight_grams": 250,
        "dimensions": "16 x 16 x 18 cm",
        "production_time": "2-3 hari",
        "impact": "Memanfaatkan sekitar 6 botol plastik bekas.",
        "is_active": True,
        "sold_count": 2,
        "reviews": (
            (5, "Potnya lucu, ringan, dan lubang airnya berfungsi baik untuk sukulen saya."),
            (4, "Warna sesuai foto dan ukurannya pas untuk meja kerja. Semoga ada warna lain."),
        ),
    },
    {
        "name": "Miniatur Anjing Botol Plastik",
        "slug": "miniatur-anjing-botol-plastik",
        "category": "Kerajinan dan Koleksi",
        "waste_material": "Botol Plastik PET",
        "price": 79_000,
        "previous_price": 89_000,
        "stock": 10,
        "image_url": "/img/botol_plastik_anjing.png",
        "images": ["/img/botol_plastik_anjing.png"],
        "short_description": "Miniatur anjing ramah lingkungan untuk dekorasi rumah.",
        "description": (
            "Miniatur anjing yang dibuat dari potongan botol PET bekas dan dirakit manual. "
            "Detail ekspresinya menjadikannya dekorasi menarik sekaligus media edukasi daur ulang."
        ),
        "weight_grams": 320,
        "dimensions": "24 x 12 x 20 cm",
        "production_time": "3-4 hari",
        "impact": "Memanfaatkan sekitar 10 botol plastik bekas.",
        "is_active": True,
        "sold_count": 2,
        "reviews": (
            (5, "Detail wajah anjingnya gemas dan tidak terlihat seperti dibuat dari botol bekas."),
            (4, "Kreatif sekali dan cukup kokoh. Anak saya suka melihat proses daur ulangnya."),
        ),
    },
    {
        "name": "Miniatur Kuda Botol Plastik",
        "slug": "miniatur-kuda-botol-plastik",
        "category": "Kerajinan dan Koleksi",
        "waste_material": "Botol Plastik PET",
        "price": 99_000,
        "previous_price": 115_000,
        "stock": 7,
        "image_url": "/img/botol_plastik_kuda.png",
        "images": ["/img/botol_plastik_kuda.png"],
        "short_description": "Miniatur kuda artistik dari susunan botol plastik bekas.",
        "description": (
            "Miniatur kuda bergaya kontemporer yang dibuat dari botol plastik PET terpilah. "
            "Setiap bagian dipotong, dibentuk, dan dirangkai dengan tangan sehingga menjadi "
            "karya dekoratif yang memiliki karakter unik."
        ),
        "weight_grams": 480,
        "dimensions": "32 x 14 x 28 cm",
        "production_time": "4-6 hari",
        "impact": "Memanfaatkan sekitar 14 botol plastik bekas.",
        "is_active": True,
        "sold_count": 2,
        "reviews": (
            (5, "Bentuk kudanya artistik dan finishing-nya bersih. Bagus untuk pajangan ruang tamu."),
            (4, "Produknya sesuai foto dan terasa kokoh. Pengiriman sedikit lama karena dibuat manual."),
        ),
    },
)


def _set_values(record: Any, values: dict[str, Any]) -> None:
    for field, value in values.items():
        setattr(record, field, value)


def _upsert_user(session: Session, data: dict[str, Any]) -> User:
    user = session.exec(select(User).where(User.email == data["email"])).first()
    if user is None:
        user = User(**data)
    else:
        _set_values(user, data)
    session.add(user)
    session.flush()
    return user


def seed_marketplace(session: Session) -> dict[str, int]:
    """Create or restore deterministic marketplace demo data without committing."""
    seller = _upsert_user(session, SEED_SELLER)
    buyers = [_upsert_user(session, data) for data in SEED_BUYERS]

    shop = session.exec(select(Shop).where(Shop.slug == SEED_SHOP["slug"])).first()
    shop_values = {**SEED_SHOP, "user_id": seller.id}
    if shop is None:
        shop = Shop(**shop_values)
    else:
        _set_values(shop, shop_values)
    session.add(shop)
    session.flush()

    completed_at = datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc)
    review_count = 0

    for product_index, product_seed in enumerate(SEED_PRODUCTS, start=1):
        product_values = {key: value for key, value in product_seed.items() if key != "reviews"}
        product_values["shop_id"] = shop.id
        product = session.exec(
            select(Product).where(Product.slug == product_values["slug"])
        ).first()
        if product is None:
            product = Product(**product_values)
        else:
            _set_values(product, product_values)
        session.add(product)
        session.flush()

        for buyer_index, (buyer, review_seed) in enumerate(
            zip(buyers, product_seed["reviews"], strict=True),
            start=1,
        ):
            rating, comment = review_seed
            order_number = f"SEED-PLASTIK-{product_index:02d}-{buyer_index:02d}"
            order = session.exec(
                select(Order).where(Order.order_number == order_number)
            ).first()
            order_values = {
                "order_number": order_number,
                "buyer_id": buyer.id,
                "shop_id": shop.id,
                "status": "SELESAI",
                "total_product_amount": product.price,
                "shipping_cost": 12_000,
                "total_amount": product.price + 12_000,
                "courier": "JNT",
                "courier_service": "EZ",
                "recipient_name": buyer.name,
                "recipient_phone": f"0812000000{buyer_index}",
                "shipping_address": f"Jl. Contoh Pembeli No. {buyer_index}, Bandung",
                "shipping_province": "Jawa Barat",
                "shipping_city": "Bandung",
                "shipping_postal_code": "40123",
                "notes": "Pesanan demo untuk data ulasan marketplace.",
                "paid_at": completed_at - timedelta(days=4),
                "shipped_at": completed_at - timedelta(days=2),
                "completed_at": completed_at + timedelta(days=product_index),
            }
            if order is None:
                order = Order(**order_values)
            else:
                _set_values(order, order_values)
            session.add(order)
            session.flush()

            item = session.exec(
                select(OrderItem).where(
                    OrderItem.order_id == order.id,
                    OrderItem.product_id == product.id,
                )
            ).first()
            item_values = {
                "order_id": order.id,
                "product_id": product.id,
                "product_name": product.name,
                "product_image": product.image_url,
                "price": product.price,
                "quantity": 1,
                "subtotal": product.price,
            }
            if item is None:
                item = OrderItem(**item_values)
            else:
                _set_values(item, item_values)
            session.add(item)

            review = session.exec(
                select(ProductReview).where(
                    ProductReview.order_id == order.id,
                    ProductReview.product_id == product.id,
                )
            ).first()
            review_values = {
                "order_id": order.id,
                "product_id": product.id,
                "user_id": buyer.id,
                "user_name": buyer.name,
                "user_avatar": buyer.avatar_url,
                "rating": rating,
                "comment": comment,
                "created_at": order_values["completed_at"] + timedelta(hours=buyer_index),
            }
            if review is None:
                review = ProductReview(**review_values)
            else:
                _set_values(review, review_values)
            session.add(review)
            review_count += 1

    session.flush()
    return {
        "products": len(SEED_PRODUCTS),
        "reviews": review_count,
        "orders": len(SEED_PRODUCTS) * len(buyers),
    }
