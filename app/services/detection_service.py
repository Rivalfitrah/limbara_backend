import cv2
import numpy as np
import io
import json
from typing import List
from PIL import Image
from pydantic import BaseModel
from fastapi import UploadFile
from ultralytics import YOLO

from google import genai
from google.genai import types

from app.services.upload_service import upload_image_to_cloudinary

MODEL_PATH = "app/models/best_model.pt" 

client = genai.Client()

# Memuat model YOLOv8
try:
    model = YOLO(MODEL_PATH)
except Exception as e:
    print(f"Peringatan: Gagal memuat model. Error: {e}")
    model = None

# Skema Pydantic Gemini
class DetectionDetail(BaseModel):
    className: str
    confidence: float
    box: List[float]

class GeminiDetectionResponse(BaseModel):
    detected_class_names: List[str]
    allDetections: List[DetectionDetail]


async def process_image_and_detect(file: UploadFile):
    if model is None:
        return {"status": "error", "message": "Model YOLO belum tersedia atau path salah."}

    try:
        # 1. Membaca gambar dari input stream
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # 2. Prediksi YOLOv8
        results = model.predict(img, conf=0.50, imgsz=640) 
        result = results[0]

        detections_dict = {}  # Gunakan dict untuk deduplikasi per className
        detected_class_names = []

        for box in result.boxes:
            class_name = model.names[int(box.cls[0].item())]
            confidence = round(box.conf[0].item(), 2)
            
            # Hanya simpan deteksi dengan confidence tertinggi per className
            if class_name not in detections_dict or confidence > detections_dict[class_name]["confidence"]:
                detections_dict[class_name] = {
                    "className": class_name,
                    "confidence": confidence,
                    "box": box.xyxyn[0].tolist()
                }
            
            if class_name not in detected_class_names:
                detected_class_names.append(class_name)
        
        # Convert dict ke list untuk allDetections
        detections = list(detections_dict.values())
        # Urutkan dari confidence tertinggi ke terendah
        detections.sort(key=lambda x: x["confidence"], reverse=True)

        # 3. Fallback Gemini jika YOLO tidak mendeteksi
        if not detections:
            try:
                raw_image = Image.open(io.BytesIO(contents))
                prompt_instruction = """
                Analisis gambar ini secara akurat untuk mendeteksi berbagai jenis objek sampah atau material buangan yang ada di dalamnya.
                Fokus murni pada tugas deteksi (Object Detection). Jangan berikan insight, saran, atau narasi tambahan.
                
                Ketentuan Output:
                1. 'className': Nama objek dalam satu atau dua kata menggunakan bahasa indonesia (misal: 'botol_plastik', 'kardus', 'sisa_makanan', 'kaleng').
                2. 'confidence': Nilai keyakinan rasional antara 0.50 hingga 1.00.
                3. 'box': Estimasi koordinat ternormalisasi [ymin, xmin, ymax, xmax] dengan rentang nilai 0.0 - 1.0. Jika ragu letak presisinya, gunakan [0.0, 0.0, 1.0, 1.0].
                4. Pastikan 'detected_class_names' berisi daftar unik dari 'className' yang ditemukan.
                """

                response = client.models.generate_content(
                    model='gemini-3.1-flash-lite',
                    contents=[raw_image, prompt_instruction],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=GeminiDetectionResponse,
                        temperature=0.1,
                    ),
                )
                
                gemini_data = json.loads(response.text)
                gemini_detections = gemini_data.get("allDetections", [])
                
                if not gemini_detections:
                    return {"status": "not_found", "message": "Tidak terdeteksi sebagai sampah."}

                # Upload gambar asli ke Cloudinary (karena Gemini tidak menggambar box otomatis)
                cloudinary_url = upload_image_to_cloudinary(img)

                return {
                    "status": "success",
                    "message": "Deteksi selesai menggunakan Gemini API",
                    "image_url": cloudinary_url,
                    "totalDetected": len(gemini_detections),
                    "detected_class_names": gemini_data.get("detected_class_names", []), 
                    "allDetections": gemini_detections
                }

            except Exception as gemini_error:
                if "503" in str(gemini_error) or "overloaded" in str(gemini_error).lower():
                    return {"status": "error", "message": "Server Google overload, coba lagi."}
                return {"status": "error", "message": f"Fallback Gemini gagal: {str(gemini_error)}"}
            
        # 4. Jika YOLO Sukses: Gambar Box dan Upload
        img_with_boxes = result.plot()
        cloudinary_url = upload_image_to_cloudinary(img_with_boxes)

        return {
            "status": "success",
            "message": "Deteksi selesai menggunakan YOLOv8",
            "image_url": cloudinary_url,
            "totalDetected": len(detections),
            "detected_class_names": detected_class_names, 
            "allDetections": detections
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}