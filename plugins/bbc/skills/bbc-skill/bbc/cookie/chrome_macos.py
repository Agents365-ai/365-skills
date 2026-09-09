"""Chrome / Edge cookie extraction on macOS.

Uses:
- sqlite3 (stdlib) to read the Cookies DB
- `security find-generic-password` to fetch the AES password from Keychain
- hashlib.pbkdf2_hmac (stdlib) to derive the AES-128 key
- `openssl enc -aes-128-cbc` (system binary) to decrypt cookie values

Zero pip install. macOS-only.
"""

import binascii
import glob
import hashlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

SALT = b"saltysalt"
ITERATIONS = 1003
KEY_LEN = 16
IV = b" " * 16  # 16 spaces

CHROME_SERVICES = {
    "chrome": ("Chrome", "Chrome"),
    "edge": ("Microsoft Edge", "Microsoft Edge"),
    "chromium": ("Chromium", "Chromium"),
}


def _profile_paths(browser: str) -> list[Path]:
    home = Path.home()
    if browser == "chrome":
        base = home / "Library/Application Support/Google/Chrome"
    elif browser == "edge":
        base = home / "Library/Application Support/Microsoft Edge"
    elif browser == "chromium":
        base = home / "Library/Application Support/Chromium"
    else:
        return []
    if not base.exists():
        return []
    results = []
    for prof in ["Default"] + sorted(glob.glob(str(base / "Profile *"))):
        p = base / prof if isinstance(prof, str) and "/" not in prof else Path(prof)
        # Chrome >= ~96 moved Cookies under Network/
        for candidate in [p / "Network/Cookies", p / "Cookies"]:
            if candidate.exists():
                results.append(candidate)
                break
    return results


def _fetch_key(browser: str) -> bytes | None:
    if sys.platform != "darwin":
        return None
    if browser not in CHROME_SERVICES:
        return None
    svc_name, account = CHROME_SERVICES[browser]
    try:
        out = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-w",
                "-s",
                f"{svc_name} Safe Storage",
                "-a",
                account,
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode != 0:
            return None
        password = out.stdout.strip().encode()
        if not password:
            return None
        return hashlib.pbkdf2_hmac("sha1", password, SALT, ITERATIONS, KEY_LEN)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _decrypt_value(encrypted: bytes, key: bytes) -> str | None:
    if not encrypted:
        return None
    # Chrome prefixes with version tag: v10 or v11
    if encrypted[:3] in (b"v10", b"v11"):
        body = encrypted[3:]
    else:
        # Possibly legacy plaintext
        try:
            return encrypted.decode("utf-8")
        except UnicodeDecodeError:
            return None
    try:
        proc = subprocess.run(
            [
                "openssl",
                "enc",
                "-d",
                "-aes-128-cbc",
                "-K",
                binascii.hexlify(key).decode(),
                "-iv",
                binascii.hexlify(IV).decode(),
            ],
            input=body,
            capture_output=True,
            timeout=5,
        )
        if proc.returncode != 0:
            return None
        plain = proc.stdout
        # PKCS#7 padding is auto-handled by openssl; trailing spaces may still exist
        return plain.decode("utf-8", errors="ignore").rstrip("\x00 ")
    except (OSError, subprocess.TimeoutExpired):
        return None


def extract(
    browser: str = "chrome", domain_filter: str = "bilibili.com"
) -> dict[str, str] | None:
    key = _fetch_key(browser)
    if not key:
        return None

    for db_path in _profile_paths(browser):
        try:
            with tempfile.NamedTemporaryFile(
                prefix="bbc-chrome-", suffix=".db", delete=False
            ) as tf:
                tmp = Path(tf.name)
            shutil.copy2(db_path, tmp)
            try:
                conn = sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)
                cur = conn.execute(
                    "SELECT name, value, encrypted_value FROM cookies WHERE host_key LIKE ?",
                    (f"%{domain_filter}%",),
                )
                cookies: dict[str, str] = {}
                for name, value, enc in cur.fetchall():
                    if value:
                        cookies[name] = value
                    elif enc:
                        dec = _decrypt_value(bytes(enc), key)
                        if dec is not None:
                            cookies[name] = dec
                conn.close()
            finally:
                try:
                    tmp.unlink()
                except OSError:
                    pass
            if cookies.get("SESSDATA"):
                return cookies
        except sqlite3.DatabaseError:
            continue
    return None
