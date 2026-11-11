from sqlmodel import Session

from app.database import engine
from app.services.marketplace_seed_service import seed_marketplace


def main() -> None:
    with Session(engine) as session:
        try:
            result = seed_marketplace(session)
            session.commit()
        except Exception:
            session.rollback()
            raise

    print(
        "Seeder marketplace selesai: "
        f"{result['products']} produk, "
        f"{result['orders']} pesanan selesai, "
        f"dan {result['reviews']} review."
    )


if __name__ == "__main__":
    main()
