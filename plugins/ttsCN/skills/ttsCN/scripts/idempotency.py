"""Idempotency support for ttsCN synthesis.

When an orchestrator retries a failed synthesis, the same --idempotency-key
should return the cached result instead of re-synthesizing and double-billing.

Cache lives at ~/.ttscn_idem/ — keyed by SHA-256 of the idempotency key.
Each entry stores the synthesis result JSON so retried calls are free + fast.
"""

import hashlib
import json
import os
import time
from pathlib import Path

CACHE_DIR = os.path.expanduser("~/.ttscn_idem")
CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _key_path(idempotency_key):
    """Derive a filesystem-safe cache path from the idempotency key."""
    h = hashlib.sha256(idempotency_key.encode()).hexdigest()[:32]
    return os.path.join(CACHE_DIR, h + ".json")


def lookup(idempotency_key):
    """Check whether a result already exists for this key.

    Returns (hit: bool, result: dict|None).
    Hit is false if the key is unknown, the cache file is corrupt, or TTL expired.
    """
    if not idempotency_key:
        return False, None
    path = _key_path(idempotency_key)
    if not os.path.exists(path):
        return False, None
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False, None
    age = time.time() - data.get("cached_at", 0)
    if age > CACHE_TTL_SECONDS:
        try:
            os.remove(path)
        except OSError:
            pass
        return False, None
    return True, data.get("result")


def store(idempotency_key, result):
    """Persist synthesis result under the given idempotency key."""
    if not idempotency_key:
        return
    _ensure_cache_dir()
    entry = {
        "cached_at": time.time(),
        "idempotency_key_hash": hashlib.sha256(idempotency_key.encode()).hexdigest()[:16],
        "result": result,
    }
    path = _key_path(idempotency_key)
    with open(path, "w") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)


def purge(older_than_days=None):
    """Remove expired or all cached entries. Returns count removed."""
    if older_than_days is None:
        older_than_days = 7
    cutoff = time.time() - older_than_days * 24 * 3600
    removed = 0
    if not os.path.exists(CACHE_DIR):
        return 0
    for name in os.listdir(CACHE_DIR):
        if not name.endswith(".json"):
            continue
        path = os.path.join(CACHE_DIR, name)
        try:
            mtime = os.path.getmtime(path)
            if mtime < cutoff:
                os.remove(path)
                removed += 1
        except OSError:
            pass
    return removed
