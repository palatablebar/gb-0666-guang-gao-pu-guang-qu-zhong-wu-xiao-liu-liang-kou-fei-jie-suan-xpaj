from collections import Counter

def judge(rows,cap):
    accepted=[];invalid=[];frequency=Counter()
    for row in sorted(rows,key=lambda x:(x["at"],x["event_id"])):
        if row["kind"]=="reversal":accepted.append(row);continue
        key=(row["channel"],row["day"],row["user_id"])
        if row["bot"]=="1":invalid.append({**row,"code":"BOT"});continue
        if frequency[key]>=cap:invalid.append({**row,"code":"CAP"});continue
        frequency[key]+=1;accepted.append(row)
    return accepted,invalid

def counts(invalid):
    return dict(sorted(Counter(x["code"] for x in invalid).items()))
