from fastapi import APIRouter
from app.modules.m7_batches.service import run
from app.errors import DomainError,http_error
router=APIRouter()
@router.get("/api/batches")
def evaluate(sample:str="dirty"):
    try:return run({"sample":sample})
    except DomainError as exc:raise http_error(exc)

@router.post("/api/runs")
def create_run(options:dict):
    try:return run(options)
    except DomainError as exc:raise http_error(exc)
@router.post("/api/runs/{run_id}/review")
def approve(run_id:str,options:dict):
    from app.store import review
    try:return review(run_id,options.get("revision"),options.get("decision"))
    except DomainError as exc:raise http_error(exc)
@router.get("/api/runs/{run_id}/evidence.csv")
def evidence(run_id:str):
    from fastapi.responses import Response
    from app.store import fetch
    from .rules import csv_evidence
    try:return Response(csv_evidence(fetch(run_id)),media_type="text/csv; charset=utf-8",headers={"Content-Disposition":"attachment; filename=evidence.csv"})
    except DomainError as exc:raise http_error(exc)
