from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict

from app.services.validation import Validator

router = APIRouter()

class ValidateRequest(BaseModel):
    spec: Dict[str, Any]

@router.post("/")
async def validate_spec(req: ValidateRequest):
    v = Validator()
    result = v.validate(req.spec)
    return result
