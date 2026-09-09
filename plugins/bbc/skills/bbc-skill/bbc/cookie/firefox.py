"""Firefox cookie extraction — stdlib sqlite3, no encryption.

Works on macOS, Linux, Windows. Copies DB to a temp file since Firefox may
hold a WAL lock.
"""

import glob
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path


def _profile_dirs() -> list[Path]:
    home = Path.home()
    patterns: list[str] = []
    if sys.platform == "darwin":
        patterns.append(str(home / "Library/Application Support/Firefox/Profiles/*"))
    elif sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            patterns.append(os.path.join(appdata, "Mozilla/Firefox/Profiles/*"))
    else:
        patterns.append(str(home / ".mozilla/firefox/*"))

    found = []
    for pat in patterns:
        for p in glob.glob(pat):
            path = Path(p)
            if (path / "cookies.sqlite").exists():
                found.append(path)
    return found


def extract(domain_filter: str = "bilibili.com") -> dict[str, str] | None:
    for profile in _profile_dirs():
        db = profile / "cookies.sqlite"
        try:
            with tempfile.NamedTemporaryFile(
                prefix="bbc-ff-", suffix=".sqlite", delete=False
            ) as tf:
                tmp_path = Path(tf.name)
            shutil.copy2(db, tmp_path)
            try:
                conn = sqlite3.connect(f"file:{tmp_path}?mode=ro", uri=True)
                cur = conn.execute(
                    "SELECT name, value FROM moz_cookies WHERE host LIKE ?",
                    (f"%{domain_filter}%",),
                )
                cookies = {name: value for name, value in cur.fetchall()}
                conn.close()
            finally:
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            if cookies.get("SESSDATA"):
                return cookies
        except sqlite3.DatabaseError:
            continue
    return None
