"""WBI signing for Bilibili endpoints that require it (e.g. space/arc search).

Algorithm reference:
1. Fetch nav endpoint to get img_url and sub_url
2. Extract filename stems (64 chars total = 32 + 32)
3. Apply MIXIN_KEY_ENC_TAB permutation, take first 32 chars -> mixin_key
4. Sort params alphabetically, strip special chars from values
5. Append wts=<unix_ts>
6. MD5(query_string + mixin_key) -> w_rid
"""

import hashlib
import time
import urllib.parse

MIXIN_KEY_ENC_TAB = [
    46,
    47,
    18,
    2,
    53,
    8,
    23,
    32,
    15,
    50,
    10,
    31,
    58,
    3,
    45,
    35,
    27,
    43,
    5,
    49,
    33,
    9,
    42,
    19,
    29,
    28,
    14,
    39,
    12,
    38,
    41,
    13,
    37,
    48,
    7,
    16,
    24,
    55,
    40,
    61,
    26,
    17,
    0,
    1,
    60,
    51,
    30,
    4,
    22,
    25,
    54,
    21,
    56,
    59,
    6,
    63,
    57,
    62,
    11,
    36,
    20,
    34,
    44,
    52,
]

_BAD_CHARS = "!'()*"


def _mixin_key(orig: str) -> str:
    return "".join(orig[i] for i in MIXIN_KEY_ENC_TAB)[:32]


def keys_from_nav(nav_data: dict) -> tuple[str, str]:
    img_url = nav_data["wbi_img"]["img_url"]
    sub_url = nav_data["wbi_img"]["sub_url"]
    img_key = img_url.rsplit("/", 1)[1].split(".")[0]
    sub_key = sub_url.rsplit("/", 1)[1].split(".")[0]
    return img_key, sub_key


def sign(params: dict, img_key: str, sub_key: str, *, now: int | None = None) -> dict:
    mixin = _mixin_key(img_key + sub_key)
    signed = dict(params)
    signed["wts"] = int(now if now is not None else time.time())
    # Strip special chars from values
    cleaned = {
        k: "".join(c for c in str(v) if c not in _BAD_CHARS) for k, v in signed.items()
    }
    query = urllib.parse.urlencode(sorted(cleaned.items()))
    # pi-lens-ignore: python-weak-hash
    signed["w_rid"] = hashlib.md5((query + mixin).encode("utf-8")).hexdigest()
    return signed


def signed_url(base_url: str, params: dict, img_key: str, sub_key: str) -> str:
    s = sign(params, img_key, sub_key)
    return f"{base_url}?{urllib.parse.urlencode(s)}"
