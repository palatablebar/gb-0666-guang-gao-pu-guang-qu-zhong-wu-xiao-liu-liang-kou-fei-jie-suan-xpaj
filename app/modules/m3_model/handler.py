from fastapi import APIRouter
from app.modules.m3_model.service import run
from app.errors import DomainError,http_error
router=APIRouter()
@router.get("/api/model")
def evaluate(sample:str="dirty"):
    try:return run({"sample":sample})
    except DomainError as exc:raise http_error(exc)
