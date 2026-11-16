from app.config import SAMPLE_DIR
from app.errors import reject
from .rules import read
def source(options=None):
    options=options or {}
    if "text" in options:
        if not isinstance(options["text"],str):reject("CONTENT","文件内容须为文本")
        return options["text"].encode("utf-8")
    sample=options.get("sample","dirty")
    if sample not in {"dirty","clean","gb18030"}:reject("SAMPLE","样例不存在")
    return (SAMPLE_DIR/(sample+".csv")).read_bytes()
def run(options=None):return read(source(options))
