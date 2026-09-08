#!/usr/bin/env python3
"""Encode a .mmd file into a mermaid.live editor URL (pako raw-deflate + base64url)."""

import base64
import json
import sys
import zlib


def encode_link(path):
    try:
        with open(path, encoding="utf-8") as f:
            code = f.read()
    except OSError as e:
        sys.exit(f"error: cannot read {path}: {e}")
    state = json.dumps({"code": code, "mermaid": {"theme": "default"}}).encode()
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)  # raw deflate, pako-compatible
    data = compressor.compress(state) + compressor.flush()
    b64 = base64.urlsafe_b64encode(data).decode().rstrip("=")
    # round-trip guard: fail loudly rather than hand the user a broken link
    pad = "=" * (-len(b64) % 4)
    try:
        decoded = zlib.decompress(base64.urlsafe_b64decode(b64 + pad), -15)
        if json.loads(decoded)["code"] != code:
            raise ValueError("round-trip decode mismatch")
    except (ValueError, zlib.error) as e:
        sys.exit(f"error: encoding self-check failed: {e}")
    return f"https://mermaid.live/edit#pako:{b64}"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: mermaid_live_link.py diagram.mmd")
    print(encode_link(sys.argv[1]))
