from io import BytesIO

import cloudinary.uploader
from fastapi import HTTPException, status
from PIL import Image, UnidentifiedImageError


MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}


def validate_marketplace_image(file_bytes: bytes, content_type: str | None) -> None:
    expected_format = ALLOWED_IMAGE_FORMATS.get(content_type or "")
    if expected_format is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format gambar harus JPG, PNG, atau WEBP.",
        )

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Berkas gambar tidak boleh kosong.",
        )

    if len(file_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ukuran gambar maksimal 5 MB.",
        )

    try:
        with Image.open(BytesIO(file_bytes)) as image:
            detected_format = image.format
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Isi berkas bukan gambar yang valid.",
        ) from None

    if detected_format != expected_format:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format isi gambar tidak sesuai dengan tipe berkas.",
        )


def upload_marketplace_image(
    file_bytes: bytes,
    content_type: str | None,
    folder: str,
) -> str:
    validate_marketplace_image(file_bytes, content_type)

    try:
        result = cloudinary.uploader.upload(
            file_bytes,
            folder=folder,
            resource_type="image",
        )
        secure_url = result.get("secure_url")
        if not secure_url:
            raise RuntimeError("Cloudinary did not return a secure URL")
        return secure_url
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gagal mengunggah gambar. Silakan coba lagi.",
        ) from None
