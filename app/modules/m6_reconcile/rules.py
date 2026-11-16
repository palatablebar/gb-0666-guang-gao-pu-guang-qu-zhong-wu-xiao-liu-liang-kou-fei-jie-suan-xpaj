from decimal import Decimal

def reconcile(result,invoices):
    good=len(result["rows"]);invalid=len(result["invalid"]);duplicates=sum(x["code"]=="DUPLICATE" for x in result["quarantine"])
    q=len(result["quarantine"])-duplicates
    groups={};results=[]
    for row in result["results"]:groups[row["channel"]]=groups.get(row["channel"],Decimal(0))+Decimal(row["net"])
    for channel,billed in sorted(invoices.items()):
        net=groups.get(channel,Decimal(0));difference=Decimal(billed)-net
        results.append({"channel":channel,"computed":str(net),"billed":billed,"difference":str(difference),"status":"一致" if difference==0 else "有差异"})
    gross=sum((Decimal(x["gross"]) for x in result["results"]),Decimal(0));credit=sum((Decimal(x["credit"]) for x in result["results"]),Decimal(0));net=sum(groups.values(),Decimal(0))
    return {"accepted":good,"invalid":invalid,"duplicates":duplicates,"quarantined":q,"count_ok":result["input_count"]==good+invalid+duplicates+q+result["blank_count"],"gross":str(gross),"credit":str(credit),"net":str(net),"amount_ok":gross-credit==net,"channels":results}
