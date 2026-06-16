import os
import json
from google import genai
from google.genai import types  # Diperlukan untuk konfigurasi SDK baru
from dotenv import load_dotenv
from app.utils.waste_dictionary import WASTE_DICTIONARY

# 1. Load variabel lingkungan
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

# 2. Inisialisasi Client SDK Baru (google-genai)
if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    print("❌ Peringatan: GEMINI_API_KEY tidak ditemukan di file .env")
    client = genai.Client() 

async def generate_waste_insight(detected_classes: list) -> dict:

    if not detected_classes:
        return {
            "status": "success",
            "message": "Tidak ada sampah plastik yang terdeteksi.",
            "insights": []
        }
        
    unique_classes = list(set(detected_classes))
    item_names = []
    waste_context = ""
    
    for cls in unique_classes:
        if cls in WASTE_DICTIONARY:
            data = WASTE_DICTIONARY[cls]
            item_names.append(data['nama'])
            waste_context += f"- {data['nama']}: {data['konteks']}\n"
            
    if not item_names:
        item_names = unique_classes
        waste_context = ", ".join(unique_classes)
        
    item_names_str = ", ".join(item_names)

    # 3. PROMPT SUPER KETAT & EDUKATIF
    # 3. PROMPT SUPER KETAT & EDUKATIF
    prompt = f"""
    Kamu berperan sebagai dr ecovision, sistem AI ahli dalam memberikan edukasi sampah plastik. 
    Sistem AI kami baru saja mendeteksi jenis sampah: "{item_names_str}".

    Konteks Spesifik Benda:
    {waste_context}

    ATURAN MUTLAK:
    1. FOKUS: Hanya bahas tentang "{item_names_str}".
    2. GAYA BAHASA: Santai, edukatif, dan langsung ke intinya.
    3. Ide daur ulang harus PRAKTIS, rinci, dan bisa dilakukan di rumah tangga.
    4. STRUKTUR: Output HARUS MURNI berupa JSON valid tanpa awalan markdown ```json.

    FORMAT JSON YANG WAJIB DIGUNAKAN:
    {{
        "ringkasan_bahaya": "Satu paragraf (2-3 kalimat) dampak lingkungan spesifik dari {item_names_str}.",
        "cara_buang": "Satu kalimat panduan praktis cara membuang sampah ini.",
        "ide_daur_ulang": [
            {{
                "judul_ide": "Nama produk hasil daur ulang (misal: Pot Bunga Gantung Estetik)",
                "bahan_bahan": [
                    "Bahan 1 (misal: 1 buah botol plastik)",
                    "Bahan 2"
                ],
                "tahapan_pembuatan": [
                    "Langkah 1: Potong bagian atas...",
                    "Langkah 2: Lubangi bagian bawah..."
                ]
            }}
        ],
        "fakta_menarik": "Satu fakta mengejutkan tentang {item_names_str}.",
        "tingkat_bahaya": "rendah | sedang | tinggi",
        "dapat_didaur_ulang": true
    }}
    """

    try:
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1, 
            ),
        )
        
        ai_result = json.loads(response.text)
        
        # BUNGKUS HASILNYA AGAR SERAGAM DENGAN FORMAT ERROR
        return {
            "status": "success",
            "data": ai_result
        }
        
    except Exception as e:
        print(f"❌ Error GenAI: {e}")
        return {
            "status": "error",
            "message": "Gagal menghasilkan insight edukasi.",
            "data": None
        }