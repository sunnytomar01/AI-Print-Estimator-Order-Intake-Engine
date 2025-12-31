from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional

from app.services.llm_parser import LLMSpecParser
from app.services.pricing import PriceEngine
from app.services.validation import Validator
from app.services.workflow import WorkflowClient
from app.db.session import get_session
from app.models.order import Order

router = APIRouter()

class EstimateRequest(BaseModel):
    order_id: int
    raw_text: str
    customer_email: Optional[str] = None

@router.post("/")
async def estimate_spec(req: EstimateRequest) -> Dict[str, Any]:
    logger = __import__('logging').getLogger(__name__)
    session = get_session()
    order = session.get(Order, req.order_id)
    if order is None:
        logger.warning("Estimate requested for missing order id=%s", req.order_id)
        raise HTTPException(status_code=404, detail="Order not found")

    logger.debug("Estimate requested raw_text=%s", req.raw_text)
    parser = LLMSpecParser()
    try:
        spec = parser.parse(req.raw_text)
    except Exception as e:
        logger.exception("LLM parser error: %s", e)
        raise HTTPException(status_code=500, detail="LLM parser error")

    if not isinstance(spec, dict):
        logger.error("LLM parser returned non-dict: %s", spec)
        raise HTTPException(status_code=500, detail="LLM parser failed to return JSON")

    logger.info("Parsed spec for order_id=%s: %s", order.id, {k: spec.get(k) for k in ['product_type','quantity','size']})

    # Validation (pass raw text so validator can detect 'free' and gibberish)
    v = Validator()
    validation = v.validate(spec, req.raw_text)
    logger.info("Validation for order_id=%s => %s", order.id, validation.get("decision"))

    # Pricing
    engine = PriceEngine()
    pricing = engine.estimate(spec)
    logger.info("Pricing for order_id=%s => %s", order.id, pricing.get("final_price"))

    # Respect validation by default; allow only explicit free-text overrides (send to ...)
    override = parser.decide(spec, req.raw_text, full=False)
    if override:
        decision = override
    else:
        decision = validation.get("decision")

    # Persist all order updates in a single commit (reduces race conditions & duplicated commits)
    try:
        order.product_type = spec.get("product_type")
        order.quantity = spec.get("quantity")
        order.size = spec.get("size")
        order.paper_type = spec.get("paper_type")
        order.color = spec.get("color")
        order.finishing = ",".join(spec.get("finishing") or [])
        order.turnaround_days = spec.get("turnaround_days")
        order.rush = bool(spec.get("rush", False))
        order.final_price = pricing.get("final_price")
        order.issues = ",".join(validation.get("issues") or [])
        order.status = decision
        if req.customer_email:
            order.email = req.customer_email
        session.add(order)
        session.commit()
        session.refresh(order)
    finally:
        session.close()

    # Trigger workflow in n8n with summary payload (use LLM-decided disposition)
    wf = WorkflowClient()
    payload = {
        "order_id": order.id,
        "decision": decision,
        "price": pricing.get("final_price"),
        "issues": validation.get("issues"),
    }
    if req.customer_email:
        payload["email"] = req.customer_email

    logger.debug("Triggering workflow with payload: %s", payload)
    wf.trigger(payload)

    return {"order_id": order.id, "spec": spec, "validation": validation, "pricing": pricing}
