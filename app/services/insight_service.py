import json
import logging
from string import Template

from dotenv import load_dotenv
from google.genai import types

from app.config.gemini_config import GEMINI_MODEL, get_gemini_client
from app.utils.waste_dictionary import WASTE_DICTIONARY

load_dotenv()

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = Template(
    """
    Kamu berperan sebagai dr ecovision, sistem AI ahli dalam memberikan edukasi sampah plastik.
    Sistem AI kami baru saja mendeteksi jenis sampah: "$item_names".

    Konteks Spesifik Benda:
    $waste_context

    ATURAN MUTLAK:
    1. FOKUS: Hanya bahas tentang "$item_names".
    2. GAYA BAHASA: Santai, edukatif, dan langsung ke intinya.
    3. Ide daur ulang harus PRAKTIS, rinci, dan bisa dilakukan di rumah tangga.
    4. STRUKTUR: Output HARUS MURNI berupa JSON valid tanpa awalan markdown.

    FORMAT JSON YANG WAJIB DIGUNAKAN:
    {
        "ringkasan_bahaya": "Satu paragraf (2-3 kalimat) dampak lingkungan spesifik dari $item_names.",
        "cara_buang": "Satu kalimat panduan praktis cara membuang sampah ini.",
        "ide_daur_ulang": [
            {
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
                    "Tali nilon 1 meter",
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
                            "Keringkan menggunakan kain atau angin-anginkan sekitar 10-15 menit."
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
                ],
                "tips": [
                    "Gunakan cutter dengan hati-hati dan jauhkan dari anak-anak.",
                    "Cat botol setelah benar-benar kering agar cat lebih awet.",
                    "Pastikan lubang drainase tidak tersumbat."
                ],
                "hasil_akhir": "Pot gantung dari botol plastik yang dapat digunakan untuk tanaman hias maupun tanaman herbal."
            }
        ],
        "fakta_menarik": "Satu fakta mengejutkan tentang $item_names.",
        "tingkat_bahaya": "rendah | sedang | tinggi",
        "dapat_didaur_ulang": true
    }
    """
)


def build_waste_context(detected_classes: list[str]) -> tuple[list[str], str]:
    item_names: list[str] = []
    context_lines: list[str] = []

    for class_name in dict.fromkeys(detected_classes):
        entry = WASTE_DICTIONARY.get(class_name)
        if entry:
            item_names.append(entry["nama"])
            context_lines.append(f"- {entry['nama']}: {entry['konteks']}")
        else:
            item_names.append(class_name)

    return item_names, "\n".join(context_lines)


def build_insight_prompt(detected_classes: list[str]) -> str:
    item_names, waste_context = build_waste_context(detected_classes)
    return PROMPT_TEMPLATE.substitute(item_names=", ".join(item_names), waste_context=waste_context)


def parse_insight_response(raw_response: str) -> dict:
    cleaned = raw_response.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    return json.loads(cleaned)


async def generate_waste_insight(detected_classes: list) -> dict:
    if not detected_classes:
        return {
            "status": "success",
            "message": "Tidak ada sampah plastik yang terdeteksi.",
            "data": None,
        }

    prompt = build_insight_prompt(detected_classes)

    try:
        response = get_gemini_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        return {
            "status": "success",
            "data": parse_insight_response(response.text),
        }
    except Exception as error:
        logger.exception("Gagal menghasilkan insight edukasi")
        return {
            "status": "error",
            "message": "Gagal menghasilkan insight edukasi.",
            "data": None,
        }