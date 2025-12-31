from fastapi import FastAPI
from sqlmodel import SQLModel
from fastapi.middleware.cors import CORSMiddleware

from app.api import intake, estimate, validate, dashboard, workflow_api
from app.db.session import get_engine

app = FastAPI(title="AI Print Estimator")

# CORS for frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(intake.router, prefix="/intake", tags=["intake"])
app.include_router(estimate.router, prefix="/estimate", tags=["estimate"])
app.include_router(validate.router, prefix="/validate", tags=["validate"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(workflow_api.router, prefix="", tags=["workflow"])

@app.on_event("startup")
def on_startup():
    engine = get_engine()
    SQLModel.metadata.create_all(engine)

    # Ensure existing Postgres DB has the `email` column (added in models). This is a small
    # non-destructive migration that adds the column if it's missing so running containers
    # don't crash on writes from the frontend/workflow.
    try:
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text('ALTER TABLE "order" ADD COLUMN IF NOT EXISTS email VARCHAR(256);'))
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to run simple migration for 'email' column: %s", e)

@app.get("/")
async def root():
    return {"status": "ok", "service": "ai-print-estimator"}

# --- CSR / MIS Minimal API (single-file, production-style, in-memory storage) ---
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID
import threading

# Thread-safe in-memory stores (simple, suitable for local dev or testing)
_store_lock = threading.Lock()
_csr_tasks: dict[str, dict] = {}
_orders: dict[int, dict] = {}
_retry_queue: list[dict] = []

# Pydantic models expected by n8n
class CSRTaskCreate(BaseModel):
    order_id: int
    status: str
    issues: str
    price: Optional[float] = None
    created_at: datetime

class CSRTaskResponse(BaseModel):
    task_id: UUID
    status: str

class OrderUpdate(BaseModel):
    status: str
    updated_at: datetime
    price: Optional[float] = None
    issues: Optional[str] = None
    csr_action: Optional[str] = None

class RetryQueueItem(BaseModel):
    order_id: str
    failed_at: datetime
    error: str
    retry_count: int = Field(..., ge=0)

from app.db.session import get_session
from app.models.order import Order


@app.put("/orders/{order_id}")
def update_order(order_id: int, upd: OrderUpdate):
    """Update an order's status (as called by n8n nodes). This will try to update the persisted DB Order if present, otherwise fall back to the in-memory store for tests/local dev."""
    record = {"order_id": order_id, "status": upd.status, "updated_at": upd.updated_at.isoformat()}

    # First try to update the DB-backed Order if it exists
    session = None
    try:
        session = get_session()
        db_order = session.get(Order, order_id)
        if db_order is not None:
            db_order.status = upd.status
            if upd.price is not None:
                db_order.final_price = upd.price
            if upd.issues is not None:
                db_order.issues = upd.issues
            session.add(db_order)
            session.commit()
            session.refresh(db_order)
            logger.info("DB Order updated order_id=%s status=%s", order_id, upd.status)
            return {
                "order_id": db_order.id,
                "status": db_order.status,
                "final_price": db_order.final_price,
                "issues": db_order.issues,
            }
    except Exception as e:
        logger.exception("Failed to update DB order: %s", e)
    finally:
        if session:
            session.close()

    # Fallback to in-memory store (keeps existing tests and simple local behaviour)
    with _store_lock:
        _orders[order_id] = record
    logger.info("Order updated in-memory order_id=%s status=%s", order_id, upd.status)
    return record


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    # prefer DB-backed order, otherwise return in-memory if present
    session = None
    try:
        session = get_session()
        db_order = session.get(Order, order_id)
        if db_order is not None:
            return {
                "order_id": db_order.id,
                "status": db_order.status,
                "final_price": db_order.final_price,
                "issues": db_order.issues,
                "product_type": db_order.product_type,
                "quantity": db_order.quantity,
            }
    finally:
        if session:
            session.close()

    with _store_lock:
        rec = _orders.get(order_id)
    if not rec:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="order not found")
    return rec

class MISResponse(BaseModel):
    message: str

import logging
logger = logging.getLogger("csr_mis")

@app.post("/csr/tasks", response_model=CSRTaskResponse, status_code=201)
def create_csr_task(task: CSRTaskCreate):
    """Create a CSR review task. Returns a UUID task_id and status."""
    # basic validation
    if task.status != "needs_review":
        logger.warning("CSR task status is not 'needs_review': %s", task.status)

    task_id = uuid4()
    record = {
        "task_id": str(task_id),
        "order_id": task.order_id,
        "status": task.status,
        "issues": task.issues,
        "price": task.price,
        "created_at": task.created_at.isoformat(),
    }
    with _store_lock:
        _csr_tasks[str(task_id)] = record
    logger.info("Created CSR task task_id=%s order_id=%s", task_id, task.order_id)
    return {"task_id": task_id, "status": "created"}

@app.get("/csr/tasks/{task_id}")
def get_csr_task(task_id: str):
    with _store_lock:
        rec = _csr_tasks.get(task_id)
    if not rec:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="task not found")
    return rec



@app.post("/retry-queue", status_code=201)
def log_retry_item(item: RetryQueueItem):
    rec = {
        "order_id": item.order_id,
        "failed_at": item.failed_at.isoformat(),
        "error": item.error,
        "retry_count": item.retry_count,
    }
    with _store_lock:
        _retry_queue.append(rec)
    logger.warning("Logged MIS retry item for order_id=%s retry_count=%s", item.order_id, item.retry_count)
    return {"status": "logged"}

@app.get("/retry-queue")
def list_retry_queue():
    with _store_lock:
        return list(_retry_queue)

@app.post("/mis/orders", response_model=MISResponse)
def mis_orders(payload: dict):
    """Dummy MIS endpoint that always returns 200 OK with a JSON message."""
    logger.info("MIS received order payload (len=%s)" , len(payload) if payload else 0)
    return {"message": "Order received by MIS"}

# End CSR/MIS API
