# 🍃 Limbara Backend

## 🚀 Teknologi yang Digunakan

* **Framework:** FastAPI (Python 3.11)
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
npm install
```

### 3. Pengaturan Environment Variables (.env)
```bash
GEMINI_API_KEY=
CLOUDINARY_CLOUD_NAME=isi_cloud_name_anda
CLOUDINARY_API_KEY=isi_api_key_anda
CLOUDINARY_API_SECRET=isi_api_secret_anda
```

### 4. Jalankan Server Development Via Docker

```bash
sudo docker-compose up --build
```
