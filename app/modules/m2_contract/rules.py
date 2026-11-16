import unicodedata,json
from datetime import datetime,timezone,timedelta
from decimal import Decimal,InvalidOperation
from app.config import SENTINELS
from app.errors import reject

def amount(text):
    value=unicodedata.normalize("NFKC",str(text)).strip().replace(",","")
    if value in SENTINELS:reject("MISSING","资费缺失")
    try:number=Decimal(value)
    except InvalidOperation:reject("CONTRACT","资费无效")
    if not number.is_finite() or number<0:reject("CONTRACT","资费无效")
    return number

def contract(policy):
    if not isinstance(policy.get("frequency_cap"),int) or policy["frequency_cap"]<1:reject("CONTRACT","频次上限无效")
    for channel,rule in policy["channels"].items():
        amount(rule["cpm"])
        if rule.get("currency")!="CNY":reject("CONTRACT","币种不支持")
    return policy

def normalize(row,policy):
    for key in ("event_id","at","channel","user_id","kind"):
        if row[key].strip() in SENTINELS:reject("MISSING","事件字段缺失")
    if row["channel"] not in policy["channels"]:reject("CONTRACT","渠道资费缺失")
    if row["kind"] not in {"impression","reversal"}:reject("CONTRACT","事件类型未知")
    if row["bot"] not in {"0","1"}:reject("CONTRACT","机器标记无效")
    try:
        at=datetime.fromisoformat(row["at"].replace("Z","+00:00"))
        if at.tzinfo is None:raise ValueError()
    except ValueError:reject("TIME","时间须包含偏移")
    if row["kind"]=="reversal" and row["ref"].strip() in SENTINELS:reject("REFERENCE","冲销缺少原曝光ID")
    utc=at.astimezone(timezone.utc);day=utc.astimezone(timezone(timedelta(hours=8))).date().isoformat()
    return {**row,"source":{k:v for k,v in row.items() if k!="line"},"at":utc.isoformat(),"day":day,"cpm":str(amount(policy["channels"][row["channel"]]["cpm"]))}

def deduplicate(rows):
    groups={};good=[];bad=[]
    for row in rows:groups.setdefault(row["event_id"],[]).append(row)
    for items in groups.values():
        unique={json.dumps({k:v for k,v in x.items() if k!="line"},sort_keys=True) for x in items}
        if len(unique)>1:bad.extend({"line":x["line"],"code":"CONFLICT","raw":x} for x in items)
        else:good.append(items[0]);bad.extend({"line":x["line"],"code":"DUPLICATE","raw":x} for x in items[1:])
    return good,bad
