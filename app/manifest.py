import json,hashlib,time
from app.config import RULE_VERSION
def identify(content,options):
    material=json.dumps({"input":content,"params":options,"rule":RULE_VERSION},sort_keys=True,ensure_ascii=False,separators=(",",":"))
    return hashlib.sha256(material.encode()).hexdigest()
def create(digest,options,elapsed):
    return {"run_id":digest[:16],"sha256":digest,"rule_version":RULE_VERSION,"params":options,"elapsed_ms":round(elapsed*1000),"created_at":time.strftime("%Y-%m-%dT%H:%M:%S%z")}
