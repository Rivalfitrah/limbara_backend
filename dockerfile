# 1. Gunakan OS Linux + Python 3.11 yang super ringan
FROM python:3.11-slim

# 2. Set folder kerja di dalam server
WORKDIR /app

# 3. Install komponen sistem yang diperlukan untuk OpenCV dan Healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    libxext6 \
    libsm6 \
    libxrender1 \
    curl \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# 4. Copy requirements dan install dependencies sekaligus (OpenCV Headless diatur di sini)
COPY requirements.txt .
RUN pip install --no-cache-dir --compile -r requirements.txt

# 5. Copy seluruh kode aplikasi
COPY . .

# 6. Buat folder untuk uploads jika belum ada
RUN mkdir -p /app/static/uploads

# 7. Gunakan non-root user untuk security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 8. Jalankan FastAPI dengan workers minimal untuk memory efficiency
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]