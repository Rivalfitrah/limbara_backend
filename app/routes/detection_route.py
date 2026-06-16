from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List
from app.services.detection_service import process_image_and_detect
from app.services.insight_service import generate_waste_insight

router = APIRouter()

# Schema untuk menerima input daftar kelas dari Frontend
class InsightRequest(BaseModel):
    detected_classes: List[str]


# ─── RUTE 1: DETEKSI GAMBAR (YOLOv8 / FALLBACK GEMINI) ─────────────────
@router.post("/scan")
async def scan_image(file: UploadFile = File(...)):
    response_data = await process_image_and_detect(file)
    
    if response_data.get("status") == "error":
        raise HTTPException(status_code=400, detail=response_data["message"])
    return response_data


# ─── RUTE 2: EDUKASI GEMINI (INSIGHT SAMPAH) ───────────────────────────
@router.post("/insight")
async def get_waste_insight(request: InsightRequest):
    response_data = await generate_waste_insight(request.detected_classes)
    
    if response_data.get("status") == "error":
        raise HTTPException(status_code=500, detail=response_data["message"])
    return response_data