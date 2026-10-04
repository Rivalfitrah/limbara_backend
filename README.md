# Limbara Backend

## 🚀 Teknologi yang Digunakan

* **Framework:** FastAPI (Python 3.11)
* **Database:** PostgreSQL
* **Authentication:** Google OAuth 2.0 dan JWT
* **AI/ML Models:** YOLOv8 (Object Detection) & Gemini API (Generative AI)
* **Containerization:** Docker & Docker Compose
* **Cloud Storage:** Cloudinary SDK

---

## 🛠️ Tahapan Instalasi & Menjalankan Aplikasi

Ikuti langkah-langkah berikut untuk menjalankan aplikasi Limbara backend di komputermu (Local Development):

### 1. Kloning Repositori
Buka terminal dan jalankan perintah ini untuk mengunduh kode dari GitHub:
```bash
git clone https://github.com/Rivalfitrah/limbara_backend.git
```

```bash
cd limbara_Backend
```

### 2. Instalasi Dependensi
```bash
cp .env.example .env
```

### 3. Pengaturan Environment Variables (.env)
```bash
GEMINI_API_KEY=
CLOUDINARY_CLOUD_NAME=isi_cloud_name_anda
CLOUDINARY_API_KEY=isi_api_key_anda
CLOUDINARY_API_SECRET=isi_api_secret_anda
DATABASE_URL=postgresql+psycopg://limbara:limbara@postgres:5432/limbara
POSTGRES_DB=limbara
POSTGRES_USER=limbara
POSTGRES_PASSWORD=ganti_dengan_password_yang_aman
JWT_SECRET_KEY=ganti_dengan_kunci_acak_minimal_32_karakter
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
FRONTEND_URL=http://localhost:3000
COOKIE_SECURE=false
FASILITAS_EXCEL_PATH=/app/Data/Data_Fasilitas_BSU_KLHK_2025.xlsx
```

### 4. Data Fasilitas Bank Sampah

Backend memuat `Data/Data_Fasilitas_BSU_KLHK_2025.xlsx` (sumber: KLHK 2025) sekali saat start
lalu menyimpannya di memory. Hanya baris berstatus `A` dengan koordinat `lat`/`lng` yang dipakai
(9.899 titik unik). Lokasi file dapat diubah lewat `FASILITAS_EXCEL_PATH`.

| Method | Endpoint                        | Keterangan                            |
|--------|---------------------------------|---------------------------------------|
| GET    | `/api/fasilitas/nearby`         | `lat`, `lng`, `radius_km`, `limit`    |

### 4. Jalankan Server Development Via Docker

```bash
sudo docker-compose up --build
```

Daftarkan nilai `GOOGLE_REDIRECT_URI` yang sama pada kredensial OAuth Google. Untuk deployment HTTPS, gunakan URL publik backend, atur `FRONTEND_URL` ke domain frontend, dan set `COOKIE_SECURE=true`.
