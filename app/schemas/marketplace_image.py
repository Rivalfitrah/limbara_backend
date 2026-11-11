from urllib.parse import urlparse


MAX_PRODUCT_IMAGES = 5


def validate_cloudinary_image_url(value: str) -> str:
    clean = value.strip()
    parsed = urlparse(clean)
    if parsed.scheme != "https" or parsed.netloc != "res.cloudinary.com" or not parsed.path:
        raise ValueError("Gambar harus berasal dari upload Cloudinary yang valid.")
    if len(clean) > 512:
        raise ValueError("URL gambar terlalu panjang.")
    return clean
