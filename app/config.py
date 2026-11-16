from pathlib import Path
import os
TITLE='曝光结算质检室'
RULE_VERSION="2026.11.2"
SAMPLE_DIR=Path(__file__).resolve().parent.parent/"sample_data"
MODULES=[('intake', '日志采信'), ('contract', '计费契约'), ('model', '有效性判定'), ('calculate', '费用聚合'), ('quarantine', '争议隔离'), ('reconcile', '渠道对账'), ('batches', '批次复核')]
SENTINELS={"", "-", "N/A", "NULL", "未知"}
def data_dir():
    return Path(os.environ.get("DATA_DIR", "./var"))
