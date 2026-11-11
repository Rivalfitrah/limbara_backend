import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth_route, chat_route, detection_route, fasilitas_route, history_route, order_route, product_route, review_route, shipping_route, shop_route
from app.config.cloudinary_config import init_cloudinary
from app.services.fasilitas_service import fasilitas_service

init_cloudinary()


@asynccontextmanager
async def lifespan(_: FastAPI):
    total_facilities = fasilitas_service.load()
    print(f"Data fasilitas BSU 2025 dimuat: {total_facilities} titik dari {fasilitas_service.excel_path}")
    yield


app = FastAPI(title="Limbara API Deteksi Gambar", lifespan=lifespan)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/auth"):
        response.headers["Cache-Control"] = "no-store"
    if os.getenv("COOKIE_SECURE", "false").lower() == "true":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://limbara.vercel.app",
]
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url and frontend_url not in origins:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "Origin", "X-Requested-With"],
)

app.include_router(auth_route.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat_route.router, prefix="/api/chat", tags=["Chat"])
app.include_router(detection_route.router, prefix="/api", tags=["Detection"])
app.include_router(history_route.router, prefix="/api/histories", tags=["Scan Histories"])
app.include_router(fasilitas_route.router, prefix="/api/fasilitas", tags=["Fasilitas Bank Sampah"])
app.include_router(shop_route.router, prefix="/api/shops", tags=["Shops"])
app.include_router(product_route.router, prefix="/api", tags=["Products & Shop Management"])
app.include_router(shipping_route.router, prefix="/api/shipping", tags=["Shipping & RajaOngkir"])
app.include_router(order_route.router, prefix="/api/orders", tags=["Orders & Payments"])
app.include_router(review_route.router, prefix="/api", tags=["Product Reviews"])


@app.get("/")
def read_root():
    return {"message": "Server FastAPI Limbara berjalan dengan lancar!"}
