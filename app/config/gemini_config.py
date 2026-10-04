import os
from functools import lru_cache

from google import genai

GEMINI_MODEL = "gemini-3.1-flash-lite"


@lru_cache(maxsize=1)
def get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY belum dikonfigurasi.")
    return genai.Client(api_key=api_key)