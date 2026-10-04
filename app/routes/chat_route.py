from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.chat_service import generate_chat_reply

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


@router.post("")
async def chat(request: ChatRequest):
    try:
        return {"reply": await generate_chat_reply(request.message)}
    except Exception as error:
        raise HTTPException(status_code=500, detail="Gagal memproses pesan.") from error
