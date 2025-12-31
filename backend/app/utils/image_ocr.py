from typing import Optional

# Minimal OCR implementation trying pytesseract, falls back to empty string

def ocr_image(content: bytes) -> str:
    try:
        from PIL import Image
        import pytesseract
        from io import BytesIO

        img = Image.open(BytesIO(content))
        text = pytesseract.image_to_string(img)
        return text or ""
    except Exception:
        return ""

