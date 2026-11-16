from fastapi import APIRouter
from fastapi.responses import Response

from app.errors import DomainError, http_error
from .service import run, backfill, load
from .evidence import bill_csv

router = APIRouter()


@router.get("/api/overlap")
def evaluate(sample: str = "overlap"):
    try:
        return run({"sample": sample})
    except DomainError as exc:
        raise http_error(exc)


@router.get("/api/overlap/bills/{bill_id}")
def get_bill(bill_id: str, version: int | None = None):
    try:
        return load(bill_id, version)
    except DomainError as exc:
        raise http_error(exc)


@router.post("/api/overlap/bills/{bill_id}/backfill")
def settle_backfill(bill_id: str, payload: dict):
    try:
        return backfill(bill_id, payload.get("text", ""))
    except DomainError as exc:
        raise http_error(exc)


@router.get("/api/overlap/bills/{bill_id}/evidence.csv")
def export_bill(bill_id: str, version: int | None = None):
    try:
        data = load(bill_id, version)
        filename = f"bill-{bill_id}-v{data['manifest']['version']}.csv"
        return Response(
            bill_csv(data),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except DomainError as exc:
        raise http_error(exc)
