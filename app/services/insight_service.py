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
            "judul_ide": "Nama hasil kerajinan",

            "deskripsi": "Penjelasan singkat mengenai fungsi hasil akhirnya.",

            "estimasi_waktu": "contoh: 30-45 menit",

            "tingkat_kesulitan": "Mudah | Sedang | Sulit",

            "alat_yang_diperlukan": [
                "Gunting",
                "Cutter",
                "Penggaris",
                "Spidol",
                "Lem tembak"
            ],

            "bahan_bahan": [
                "1 botol plastik bekas ukuran 1,5 L",
                "Tanah",
                "Bibit tanaman",
                "Tali nilon ±1 meter",
                "Cat akrilik (opsional)"
            ],

            "persiapan": [
                "Cuci botol hingga bersih menggunakan sabun.",
                "Lepaskan label botol agar permukaan lebih rapi.",
                "Keringkan botol sebelum dipotong.",
                "Siapkan seluruh alat di meja kerja."
            ],

            "tahapan_pembuatan": [
  {
    "langkah": 1,
    "judul": "Membersihkan botol",
    "tujuan": "Menghilangkan kotoran agar hasil kerajinan lebih bersih dan lem dapat menempel dengan baik.",
    "instruksi": [
      "Lepaskan tutup dan label botol secara perlahan.",
      "Cuci bagian dalam dan luar menggunakan air serta sabun.",
      "Bilas hingga tidak ada sisa sabun.",
      "Keringkan menggunakan kain atau angin-anginkan sekitar 10–15 menit."
    ],
    "tips": "Pastikan botol benar-benar kering sebelum dipotong."
  },
  {
    "langkah": 2,
    "judul": "Membuat pola potongan",
    "tujuan": "Agar bentuk pot simetris dan rapi.",
    "instruksi": [
      "Letakkan botol dalam posisi tidur di atas meja datar.",
      "Gunakan penggaris untuk mengukur area sepanjang sekitar 15 cm di bagian tengah botol.",
      "Buat garis menggunakan spidol permanen mengikuti bentuk persegi panjang atau oval sesuai desain yang diinginkan."
    ],
    "tips": "Gunakan spidol berwarna gelap agar garis mudah terlihat saat memotong."
  },
  {
    "langkah": 3,
    "judul": "Memotong botol",
    "tujuan": "Membuat lubang utama yang akan menjadi tempat tanaman.",
    "instruksi": [
      "Tusukkan ujung cutter secara perlahan pada salah satu sudut pola hingga terbentuk lubang kecil.",
      "Masukkan ujung gunting ke lubang tersebut.",
      "Potong mengikuti garis yang telah dibuat secara perlahan.",
      "Jangan memotong terlalu cepat agar hasil tetap rapi."
    ],
    "tips": "Jika pengguna masih anak-anak, lakukan langkah ini dengan bantuan orang dewasa."
  }
]

            "tips": [
                "Gunakan cutter dengan hati-hati dan jauhkan dari anak-anak.",
                "Cat botol setelah benar-benar kering agar cat lebih awet.",
                "Pastikan lubang drainase tidak tersumbat."
            ],

            "hasil_akhir": "Pot gantung dari botol plastik yang dapat digunakan untuk tanaman hias maupun tanaman herbal."
        }}
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
