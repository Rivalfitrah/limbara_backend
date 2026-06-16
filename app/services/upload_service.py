import cv2
import cloudinary.uploader

def upload_image_to_cloudinary(image_array) -> str:
    """
    Menerima gambar dalam bentuk Numpy Array (hasil OpenCV), 
    mengonversinya ke byte, lalu mengunggahnya ke Cloudinary.
    """
    try:
        # Konversi gambar array OpenCV (.jpg) ke buffer memori
        success, buffer = cv2.imencode('.jpg', image_array)
        if not success:
            raise Exception("Gagal mengonversi gambar ke buffer")

        # Upload langsung dari buffer byte ke Cloudinary
        upload_result = cloudinary.uploader.upload(
            buffer.tobytes(),
            folder="limbara/scan"  # Menyimpan di folder spesifik
        )
        
        # Mengembalikan URL aman (HTTPS) dari Cloudinary
        return upload_result.get("secure_url")
    
    except Exception as e:
        raise Exception(f"Gagal upload ke Cloudinary: {str(e)}")