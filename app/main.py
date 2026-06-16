import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import detection_route, bank_sampah_route
from app.config.cloudinary_config import init_cloudinary

# Inisialisasi Cloudinary saat aplikasi pertama kali berjalan
init_cloudinary()

app = FastAPI(title="Limbara API Deteksi Gambar")

origins = [
    "http://localhost:3000",     
    "http://127.0.0.1:3000",
    "http://localhost:5173",     
    "http://127.0.0.1:5173",
    "https://limbara.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Menyambungkan rute ke aplikasi utama
app.include_router(detection_route.router, prefix="/api", tags=["Detection"])
app.include_router(bank_sampah_route.router, prefix="/api", tags=["Bank Sampah"])


@app.get("/")
def read_root():
    return {"message": "Server FastAPI Limbara berjalan dengan lancar!"}