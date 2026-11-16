from fastapi import APIRouter
from app.modules.m5_quarantine.service import run
from app.errors import DomainError,http_error
router=APIRouter()
@router.get("/api/quarantine")
def evaluate(sample:str="dirty"):
    try:return run({"sample":sample})
    except DomainError as exc:raise http_error(exc)
