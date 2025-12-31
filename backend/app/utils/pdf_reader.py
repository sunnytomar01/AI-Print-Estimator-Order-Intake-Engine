from typing import Optional

# Minimal PDF text extraction helper

def extract_text_from_pdf(content: bytes) -> str:
    try:
        from io import BytesIO
        from pdfminer.high_level import extract_text
        fp = BytesIO(content)
        text = extract_text(fp)
        return text or ""
    except Exception:
        return ""
