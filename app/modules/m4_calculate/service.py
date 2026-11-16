from app.modules.m3_model.service import run as previous
from .rules import settle

def run(options=None):
    result=previous(options);result["results"],result["rows"],bad=settle(result["rows"]);result["quarantine"]+=bad
    return result
