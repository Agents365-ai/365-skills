"""Parse Netscape-format cookie files (e.g. exported by browser extensions)."""

from pathlib import Path


def parse(path: Path, domain_filter: str = "bilibili.com") -> dict[str, str]:
    cookies: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain = parts[0]
        if domain_filter not in domain:
            continue
        name, value = parts[5], parts[6]
        cookies[name] = value
    return cookies
