import unittest
from io import BytesIO

from fastapi import HTTPException
from PIL import Image

from app.services.marketplace_image_service import validate_marketplace_image


def image_bytes(image_format: str) -> bytes:
    output = BytesIO()
    Image.new("RGB", (8, 8), color="green").save(output, format=image_format)
    return output.getvalue()


class MarketplaceImageValidationTests(unittest.TestCase):
    def test_accepts_supported_image_bytes(self):
        validate_marketplace_image(image_bytes("JPEG"), "image/jpeg")
        validate_marketplace_image(image_bytes("PNG"), "image/png")
        validate_marketplace_image(image_bytes("WEBP"), "image/webp")

    def test_rejects_spoofed_image_content(self):
        with self.assertRaises(HTTPException) as context:
            validate_marketplace_image(b"this is not an image", "image/png")
        self.assertEqual(context.exception.status_code, 400)

    def test_rejects_mime_that_does_not_match_bytes(self):
        with self.assertRaises(HTTPException) as context:
            validate_marketplace_image(image_bytes("PNG"), "image/jpeg")
        self.assertEqual(context.exception.status_code, 400)

    def test_rejects_unsupported_mime(self):
        with self.assertRaises(HTTPException) as context:
            validate_marketplace_image(image_bytes("PNG"), "image/gif")
        self.assertEqual(context.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
