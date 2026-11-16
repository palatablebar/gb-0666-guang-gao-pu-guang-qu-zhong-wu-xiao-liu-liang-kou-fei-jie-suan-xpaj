from decimal import Decimal,ROUND_HALF_UP

def settle(rows):
    originals={x["event_id"]:x for x in rows if x["kind"]=="impression"};reversed_ids=set();groups={};bad=[];good=[]
    def group(row):
        key=(row["channel"],row["day"])
        return groups.setdefault(key,{"channel":row["channel"],"day":row["day"],"impressions":0,"reversed":0,"gross_raw":Decimal(0),"credit_raw":Decimal(0),"lines":[]})
    for row in sorted(originals.values(),key=lambda x:x["event_id"]):
        target=group(row);target["impressions"]+=1;target["gross_raw"]+=Decimal(row["cpm"])/1000;target["lines"].append(row["line"]);good.append(row)
    for row in sorted((x for x in rows if x["kind"]=="reversal"),key=lambda x:(x["at"],x["event_id"])):
        original=originals.get(row["ref"]);code=None
        if original is None:code="REFERENCE"
        elif original["channel"]!=row["channel"]:code="CHANNEL"
        elif row["at"]<original["at"]:code="REVERSE_TIME"
        elif row["ref"] in reversed_ids:code="OVER_REVERSE"
        if code:bad.append({"line":row["line"],"code":code,"raw":row.get("source",row)});continue
        reversed_ids.add(row["ref"]);target=group(original);target["reversed"]+=1;target["credit_raw"]+=Decimal(original["cpm"])/1000;target["lines"].append(row["line"]);good.append(row)
    results=[]
    for key,item in sorted(groups.items()):
        gross=item["gross_raw"].quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
        net=(item["gross_raw"]-item["credit_raw"]).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
        results.append({**item,"gross_raw":str(item["gross_raw"]),"credit_raw":str(item["credit_raw"]),"gross":str(gross),"credit":str(gross-net),"net":str(net),"status":"已扣减" if item["reversed"] else "通过"})
    return results,good,bad
