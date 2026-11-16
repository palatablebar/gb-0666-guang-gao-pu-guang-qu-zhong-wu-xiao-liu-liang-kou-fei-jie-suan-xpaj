import csv,io
from app.errors import reject
COLUMNS=['event_id', 'at', 'channel', 'user_id', 'ip', 'kind', 'ref', 'bot']
def decode(raw):
    for encoding in ("utf-8-sig","gb18030"):
        try:return raw.decode(encoding),encoding
        except UnicodeDecodeError:pass
    reject("ENCODING","编码无法识别")
def read(raw):
    if len(raw)>2_000_000:reject("TOO_LARGE","文件超过2MB")
    text,encoding=decode(raw)
    if not text:reject("EMPTY_FILE","文件为空")
    reader=csv.reader(io.StringIO(text,newline=""),strict=True)
    try:header=next(reader)
    except (StopIteration,csv.Error):reject("HEADER","表头无效")
    if header!=COLUMNS:reject("HEADER","字段与契约不符")
    rows=[];bad=[];blank=0;total=0
    try:
        for values in reader:
            total+=1;line=reader.line_num
            if not values or all(not x.strip() for x in values):blank+=1;continue
            if values==header:bad.append({"line":line,"code":"REPEATED_HEADER","raw":values});continue
            if len(values)!=len(header):bad.append({"line":line,"code":"COLUMN_COUNT","raw":values});continue
            rows.append({**dict(zip(header,values)),"line":line})
    except csv.Error:reject("CSV","CSV结构损坏")
    if total==0:reject("HEADER_ONLY","只有表头")
    if blank==total:reject("BLANK_ONLY","记录全部为空")
    return {"rows":rows,"quarantine":bad,"input_count":total,"blank_count":blank,"encoding":encoding}
