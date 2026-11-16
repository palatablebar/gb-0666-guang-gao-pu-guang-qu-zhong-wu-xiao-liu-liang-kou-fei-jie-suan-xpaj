import sqlite3,json
from contextlib import contextmanager
from app.config import data_dir
from app.errors import reject
@contextmanager
def connect():
    d=data_dir();d.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(d/"records.sqlite",timeout=20)
    c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY,digest TEXT UNIQUE,body TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1,decision TEXT NOT NULL DEFAULT '待复核')")
    c.execute("CREATE TABLE IF NOT EXISTS bill_versions (bill_id TEXT NOT NULL,base_id TEXT,parent_id TEXT,version INTEGER NOT NULL,digest TEXT NOT NULL UNIQUE,source_digest TEXT NOT NULL,source_text TEXT NOT NULL,kind TEXT NOT NULL,body TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(bill_id,version))")
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()
def save(result):
    m=result["manifest"]
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO runs(id,digest,body) VALUES(?,?,?)",(m["run_id"],m["sha256"],json.dumps(result,ensure_ascii=False)))
    return fetch(m["run_id"])
def fetch(run_id):
    with connect() as c:row=c.execute("SELECT * FROM runs WHERE id=?",(run_id,)).fetchone()
    if row is None:reject("NOT_FOUND","运行不存在")
    data=json.loads(row["body"]);data["revision"]=row["revision"];data["decision"]=row["decision"]
    return data
def history():
    with connect() as c:return [dict(x) for x in c.execute("SELECT id,revision,decision FROM runs ORDER BY rowid DESC LIMIT 100")]
def review(run_id,revision,decision):
    if not isinstance(revision,int) or isinstance(revision,bool) or revision<1:reject("VERSION","修订号须为正整数")
    if decision not in ("通过","退回"):reject("DECISION","复核状态无效")
    with connect() as c:
        changed=c.execute("UPDATE runs SET revision=revision+1,decision=? WHERE id=? AND revision=?",(decision,run_id,revision)).rowcount
        if not changed:reject("STALE_VERSION","数据已更新，请重新载入")
    return fetch(run_id)

def save_bill_version(bill_id,parent_id,digest,source_digest,source_text,kind,body,base_id=None):
    """幂等归档账单版本：同一输入摘要只产生一条版本，重试不新增曝光或抵扣。"""
    with connect() as c:
        existing=c.execute("SELECT * FROM bill_versions WHERE digest=?",(digest,)).fetchone()
        if existing is not None:
            return dict(existing),False
        parent=c.execute("SELECT * FROM bill_versions WHERE bill_id=? ORDER BY version DESC LIMIT 1",(bill_id,)).fetchone() if parent_id else None
        if parent_id and parent is None:reject("BACKFILL_BASE","原账单不存在，补数失败，旧版账单保留")
        if parent is not None and (parent["bill_id"]!=parent_id or parent["bill_id"]!=bill_id):reject("BILL_VERSION","账单链路冲突")
        version=1 if parent is None else parent["version"]+1
        c.execute(
            "INSERT INTO bill_versions(bill_id,base_id,parent_id,version,digest,source_digest,source_text,kind,body,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (bill_id,bill_id if base_id is None else base_id,parent_id,version,digest,source_digest,source_text,kind,
             json.dumps(body,ensure_ascii=False),body["manifest"]["created_at"]),
        )
        row=c.execute("SELECT * FROM bill_versions WHERE bill_id=? AND version=?",(bill_id,version)).fetchone()
        return dict(row),True

def fetch_bill(bill_id,version=None):
    with connect() as c:
        if version is None:
            row=c.execute("SELECT * FROM bill_versions WHERE bill_id=? ORDER BY version DESC LIMIT 1",(bill_id,)).fetchone()
        else:
            row=c.execute("SELECT * FROM bill_versions WHERE bill_id=? AND version=?",(bill_id,version)).fetchone()
    if row is None:reject("NOT_FOUND","账单不存在")
    return dict(row)

def bill_history(bill_id=None,limit=100):
    with connect() as c:
        if bill_id:
            rows=c.execute("SELECT bill_id,base_id,parent_id,version,kind,source_digest,created_at FROM bill_versions WHERE bill_id=? ORDER BY version",(bill_id,)).fetchall()
        else:
            rows=c.execute("SELECT bill_id,base_id,parent_id,version,kind,source_digest,created_at FROM bill_versions ORDER BY rowid DESC LIMIT ?",(limit,)).fetchall()
    return [dict(x) for x in rows]
