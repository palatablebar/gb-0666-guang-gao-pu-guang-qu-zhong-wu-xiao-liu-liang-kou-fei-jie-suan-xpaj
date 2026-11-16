from collections import Counter
from app.errors import reject

def distribution(rows):return dict(sorted(Counter(x["code"] for x in rows).items()))
def select(rows,code=None):
    if code is not None and code not in distribution(rows):reject("REASON","原因码不存在")
    return [x for x in rows if code is None or x["code"]==code]
def evidence(rows):return all(isinstance(x.get("line"),int) and x.get("code") and "raw" in x for x in rows)
