import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import create_db_and_tables
from app.routes import auth_route, chat_route, detection_route, fasilitas_route, history_route
from app.config.cloudinary_config import init_cloudinary
from app.services.fasilitas_service import fasilitas_service

init_cloudinary()


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    total_facilities = fasilitas_service.load()
    print(f"Data fasilitas BSU 2025 dimuat: {total_facilities} titik dari {fasilitas_service.excel_path}")
    yield


app = FastAPI(title="Limbara API Deteksi Gambar", lifespan=lifespan)

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
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_route.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat_route.router, prefix="/api/chat", tags=["Chat"])
app.include_router(detection_route.router, prefix="/api", tags=["Detection"])
app.include_router(history_route.router, prefix="/api/histories", tags=["Scan Histories"])
app.include_router(fasilitas_route.router, prefix="/api/fasilitas", tags=["Fasilitas Bank Sampah"])


@app.get("/")
def read_root():
    return {"message": "Server FastAPI Limbara berjalan dengan lancar!"}
