import hashlib
import json
import time

from app.config import RULE_VERSION


def digest_of(payload):
    if isinstance(payload, (bytes, bytearray)):
        material = bytes(payload)
    else:
        material = json.dumps(
            payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def bill_manifest(digest, bill_id, version, elapsed, kind, parent_id=None, base_id=None):
    return {
        "bill_id": bill_id,
        "run_id": bill_id,
        "version": version,
        "kind": kind,
        "parent_id": parent_id,
        "base_id": base_id,
        "sha256": digest,
        "rule_version": RULE_VERSION,
        "elapsed_ms": round(elapsed * 1000),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
