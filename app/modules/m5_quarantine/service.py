from app.modules.m4_calculate.service import run as previous
from .rules import distribution,evidence

def run(options=None):
    result=previous(options);result["reason_counts"]=distribution(result["quarantine"]);result["evidence_complete"]=evidence(result["quarantine"])
    return result
