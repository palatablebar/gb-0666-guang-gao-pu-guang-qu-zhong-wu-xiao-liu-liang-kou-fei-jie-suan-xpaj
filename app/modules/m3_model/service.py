from app.modules.m2_contract.service import run as previous
from .rules import judge,counts

def run(options=None):
    result=previous(options);result["rows"],result["invalid"]=judge(result["rows"],result["policy"]["frequency_cap"])
    result["invalid_counts"]=counts(result["invalid"])
    return result
