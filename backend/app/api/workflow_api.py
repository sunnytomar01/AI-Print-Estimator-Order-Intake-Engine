from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.db.session import get_session
from app.models.order import Order

router = APIRouter()

class WorkflowUpdate(BaseModel):
    order_id: int
    # n8n may send either `status` or `decision` — accept both for flexibility
    status: Optional[str] = None
    decision: Optional[str] = None
    # n8n provides `price` and `issues` fields
    price: Optional[float] = None
    issues: Optional[list] = None
    email: Optional[str] = None

@router.post("/workflow/update")
async def update_order(update: WorkflowUpdate):
    session = get_session()
    order = session.get(Order, update.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Prefer explicit `decision` if provided (keeps n8n payload semantics intact)
    if update.decision is not None:
        order.status = update.decision
    elif update.status is not None:
        order.status = update.status

    if update.price is not None:
        order.final_price = update.price
    if update.issues is not None:
        order.issues = ",".join(update.issues)
    if update.email is not None:
        # store optional email on order (model will be extended if needed)
        try:
            order.email = update.email
        except Exception:
            # If Order model doesn't have email, ignore gracefully
            pass

    session.add(order)
    session.commit()
    session.refresh(order)
    session.close()
    return {"ok": True, "order_id": order.id, "status": order.status, "final_price": order.final_price, "issues": order.issues}