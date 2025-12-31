from typing import Optional, List
from sqlmodel import SQLModel, Field

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    raw_text: str
    product_type: Optional[str]
    quantity: Optional[int]
    size: Optional[str]
    paper_type: Optional[str]
    color: Optional[str]
    finishing: Optional[str]
    turnaround_days: Optional[int]
    rush: Optional[bool]
    status: Optional[str]
    final_price: Optional[float]
    issues: Optional[str]
    # optional customer email (may be populated by frontend or workflow)
    email: Optional[str]

class OrderCreate(SQLModel):
    raw_text: str

class OrderRaw(SQLModel):
    raw_text: str
