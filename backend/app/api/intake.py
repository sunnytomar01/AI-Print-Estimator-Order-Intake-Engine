from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional

from app.db.session import get_session
from app.models.order import Order, OrderCreate, OrderRaw
from app.services.llm_parser import LLMSpecParser
from app.utils.pdf_reader import extract_text_from_pdf
from app.utils.image_ocr import ocr_image
from app.utils.image_quality import get_image_dpi

router = APIRouter()

@router.post("/order")
async def intake_order(
    text: Optional[str] = Form(None),
    email_body: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    email: Optional[str] = Form(None),
):
    """Accept plain text, email body, PDF, or image. Normalize, store raw input, and return order id."""
    logger = __import__('logging').getLogger(__name__)
    logger.info("Received intake request: text=%s, email_body=%s, file=%s", bool(text), bool(email_body), getattr(file, 'filename', None))

    if not any([text, email_body, file]):
        logger.warning("No input provided in intake request")
        raise HTTPException(status_code=400, detail="No input provided")

    raw_text = text or email_body or ""
    issues = []

    if file:
        try:
            content_type = file.content_type
            content = await file.read()
            logger.debug("File content type=%s size=%s", content_type, len(content))
            if content_type == "application/pdf":
                extracted = extract_text_from_pdf(content)
                logger.debug("Extracted %d chars from PDF", len(extracted))
                raw_text += "\n" + extracted
            elif content_type.startswith("image/"):
                extracted = ocr_image(content)
                raw_text += "\n" + extracted
                dpi = get_image_dpi(content)
                logger.debug("Image DPI=%s", dpi)
                if min(dpi) < 300:
                    issues.append("low_resolution")
            else:
                logger.error("Unsupported file type: %s", content_type)
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {content_type}")
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error processing uploaded file: %s", e)
            raise HTTPException(status_code=400, detail="Failed to process uploaded file")

    # persist raw_text in DB
    session = get_session()
    try:
        order = Order(raw_text=raw_text, status="received")
        if email:
            order.email = email
        session.add(order)
        session.commit()
        session.refresh(order)
        logger.info("Created order id=%s issues=%s email=%s", order.id, issues, email)
    finally:
        session.close()

    return JSONResponse({"order_id": order.id, "issues": issues, "raw_text": raw_text, "email": email}, status_code=201)
