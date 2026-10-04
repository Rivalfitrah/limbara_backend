from google.genai import types

from app.config.gemini_config import GEMINI_MODEL, get_gemini_client

SYSTEM_PROMPT = """
Kamu adalah Limbara AI, asisten cerdas milik platform Limbara yang berfokus pada edukasi pengelolaan sampah dan limbah di Indonesia.

Jawab hanya pertanyaan yang berkaitan dengan sampah, pemilahan, daur ulang, dampak lingkungan, bank sampah, regulasi pengelolaan sampah Indonesia, kompos, biogas, limbah B3, atau gaya hidup zero waste. Jika di luar topik tersebut, tolak dengan sopan dan arahkan kembali ke topik lingkungan. Gunakan bahasa Indonesia yang santai, informatif, dan ringkas. Gunakan poin jika menjelaskan langkah atau daftar. Batasi jawaban hingga 300 kata.
""".strip()


async def generate_chat_reply(message: str) -> str:
    response = get_gemini_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=message,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.7),
    )
    return response.text or "Maaf, saya belum dapat membuat jawaban saat ini."
