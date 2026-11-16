import json
from app.config import SAMPLE_DIR
from app.modules.m5_quarantine.service import run as previous
from .rules import reconcile

def run(options=None):
    result=previous(options);result["reconciliation"]=reconcile(result,json.loads((SAMPLE_DIR/"invoices.json").read_text()))
    return result
