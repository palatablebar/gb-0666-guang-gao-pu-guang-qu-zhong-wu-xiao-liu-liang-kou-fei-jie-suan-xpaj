from fastapi import APIRouter
from app.modules.m1_intake.service import run
from app.errors import DomainError,http_error
router=APIRouter()
@router.get("/api/intake")
def evaluate(sample:str="dirty"):
    try:return run({"sample":sample})
    except DomainError as exc:raise http_error(exc)
