import json
from app.config import SAMPLE_DIR
from app.modules.m1_intake.service import run as previous
from app.errors import DomainError
from .rules import contract,normalize,deduplicate

def run(options=None):
    result=previous(options);policy=contract(json.loads((SAMPLE_DIR/"rates.json").read_text()));rows=[]
    for row in result["rows"]:
        try:rows.append(normalize(row,policy))
        except DomainError as exc:result["quarantine"].append({"line":row["line"],"code":exc.code,"raw":row.get("source",row)})
    result["rows"],bad=deduplicate(rows);result["quarantine"]+=bad;result["policy"]=policy
    return result
