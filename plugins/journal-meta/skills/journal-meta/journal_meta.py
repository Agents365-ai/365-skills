#!/usr/bin/env python3
"""Paper metadata lookup.

Resolve a DOI / PMID / arXiv id / OpenAlex id / title to a single record of
paper metadata (title, authors, first & corresponding author, publication date,
journal + ISO-4 abbreviation, impact factor, volume/issue/pages, DOI/PMID,
citation count, abstract).

Primary source: OpenAlex (free, no key). Crossref fallback for un-indexed DOIs.
Journal abbreviation is delegated to the `journal-abbrev` skill's jabbrv.py when
installed (falls back to AbbrevISO); impact factor is delegated to `journal-if`'s
journal_if.py (falls back to OpenAlex 2yr mean citedness).

Output is a stable JSON envelope when piped, a human view on a TTY.
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CLI_VERSION = "0.1.0"
SCHEMA_VERSION = "0.1.0"
UA = "journal-meta/%s (https://github.com/Agents365-ai/journal-meta)" % CLI_VERSION


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #
def _mailto():
    return os.environ.get("JOURNAL_META_MAILTO") or os.environ.get("OPENALEX_MAILTO")


def _get_json(url, timeout=30):
    mailto = _mailto()
    if mailto:
        sep = "&" if "?" in url else "?"
        url = "%s%smailto=%s" % (url, sep, urllib.parse.quote(mailto))
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _get_text(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace").strip()


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #
class MetaError(Exception):
    def __init__(self, code, message, retryable=False, exit_code=1):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.exit_code = exit_code


# --------------------------------------------------------------------------- #
# Identifier detection
# --------------------------------------------------------------------------- #
def detect_id(query):
    """Return (id_type, value). id_type in doi|pmid|arxiv|openalex|title."""
    s = query.strip()
    low = s.lower()
    for pre in ("https://doi.org/", "http://doi.org/", "doi.org/", "doi:"):
        if low.startswith(pre):
            return "doi", s[len(pre) :]
    if low.startswith("arxiv:"):
        return "arxiv", s[6:]
    if low.startswith("pmid:"):
        return "pmid", s[5:]
    m = re.match(
        r"^https?://(?:www\.)?ncbi\.nlm\.nih\.gov/pubmed/(\d+)", low
    ) or re.match(r"^https?://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", low)
    if m:
        return "pmid", m.group(1)
    if re.match(r"^10\.\d{4,9}/\S+$", s):
        return "doi", s
    if re.match(r"^W\d+$", s):
        return "openalex", s
    if re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", s):
        return "arxiv", s
    if re.match(r"^\d{1,9}$", s):
        return "pmid", s
    return "title", s


# --------------------------------------------------------------------------- #
# OpenAlex resolution
# --------------------------------------------------------------------------- #
def openalex_fetch(id_type, value):
    """Return an OpenAlex work dict, or raise MetaError."""
    base = "https://api.openalex.org/works"
    try:
        if id_type == "doi":
            return _get_json(
                "%s/https://doi.org/%s" % (base, urllib.parse.quote(value, safe="/"))
            )
        if id_type == "pmid":
            return _get_json("%s/pmid:%s" % (base, urllib.parse.quote(value)))
        if id_type == "openalex":
            return _get_json("%s/%s" % (base, urllib.parse.quote(value)))
        if id_type == "arxiv":
            try:
                return _get_json(
                    "%s/https://doi.org/10.48550/arXiv.%s"
                    % (base, urllib.parse.quote(value))
                )
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    raise
                id_type, value = "title", value  # fall through to search
        # title / free-text search
        res = _get_json("%s?search=%s&per_page=1" % (base, urllib.parse.quote(value)))
        results = res.get("results") or []
        if not results:
            raise MetaError("not_found", "No paper matched: %r" % value, exit_code=3)
        return results[0]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise MetaError("not_found", "No paper matched: %r" % value, exit_code=3)
        raise MetaError(
            "upstream_unavailable", "OpenAlex error: %s" % e, retryable=True
        )
    except urllib.error.URLError as e:
        raise MetaError(
            "upstream_unavailable", "OpenAlex unreachable: %s" % e, retryable=True
        )


def deinvert_abstract(idx):
    """Rebuild plain-text abstract from OpenAlex abstract_inverted_index."""
    if not idx:
        return None
    pos = {}
    for word, places in idx.items():
        for p in places:
            pos[p] = word
    return " ".join(pos[i] for i in sorted(pos)) or None


def parse_openalex(w):
    """Map an OpenAlex work dict to our flat metadata record (journal enrichment added later)."""
    auths = w.get("authorships") or []
    names = [(a.get("author") or {}).get("display_name") for a in auths]
    names = [n for n in names if n]
    first = None
    for a in auths:
        if a.get("author_position") == "first":
            first = (a.get("author") or {}).get("display_name")
            break
    if first is None and names:
        first = names[0]
    corresponding = [
        (a.get("author") or {}).get("display_name")
        for a in auths
        if a.get("is_corresponding")
    ]
    corresponding = [c for c in corresponding if c]

    src = (w.get("primary_location") or {}).get("source") or {}
    biblio = w.get("biblio") or {}
    fp, lp = biblio.get("first_page"), biblio.get("last_page")
    pages = ("%s-%s" % (fp, lp)) if fp and lp else (fp or lp)
    ids = w.get("ids") or {}
    pmid = ids.get("pmid")
    if pmid:
        pmid = pmid.rstrip("/").rsplit("/", 1)[-1]
    doi = (w.get("doi") or "").replace("https://doi.org/", "") or None

    return {
        "title": w.get("title") or w.get("display_name"),
        "authors": names,
        "author_count": len(names),
        "first_author": first,
        "corresponding_authors": corresponding,
        "publication_date": w.get("publication_date"),
        "year": w.get("publication_year"),
        "journal": src.get("display_name"),
        "journal_abbrev": None,  # filled by enrich_journal()
        "impact_factor": None,  # filled by enrich_journal()
        "impact_factor_year": None,
        "impact_factor_source": None,
        "volume": biblio.get("volume"),
        "issue": biblio.get("issue"),
        "pages": pages,
        "doi": doi,
        "pmid": pmid,
        "openalex": (ids.get("openalex") or "").rsplit("/", 1)[-1] or None,
        "issn": src.get("issn_l"),
        "type": w.get("type"),
        "is_oa": (w.get("open_access") or {}).get("is_oa"),
        "cited_by_count": w.get("cited_by_count"),
        "abstract": deinvert_abstract(w.get("abstract_inverted_index")),
        "_meta_source": "OpenAlex",
    }


# --------------------------------------------------------------------------- #
# Crossref fallback (DOI only) — used when OpenAlex has not indexed the DOI
# --------------------------------------------------------------------------- #
def crossref_fetch(doi):
    try:
        msg = _get_json(
            "https://api.crossref.org/works/%s" % urllib.parse.quote(doi, safe="/")
        )["message"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise MetaError("not_found", "No paper matched DOI: %r" % doi, exit_code=3)
        raise MetaError(
            "upstream_unavailable", "Crossref error: %s" % e, retryable=True
        )
    except urllib.error.URLError as e:
        raise MetaError(
            "upstream_unavailable", "Crossref unreachable: %s" % e, retryable=True
        )

    def _name(a):
        return " ".join(x for x in (a.get("given"), a.get("family")) if x) or a.get(
            "name"
        )

    authors = msg.get("author") or []
    names = [_name(a) for a in authors if _name(a)]
    first = next((_name(a) for a in authors if a.get("sequence") == "first"), None) or (
        names[0] if names else None
    )
    # Crossref does not reliably flag corresponding authors.
    dp = (
        (
            msg.get("published")
            or msg.get("published-print")
            or msg.get("published-online")
            or {}
        ).get("date-parts")
        or [[None]]
    )[0]
    pub_date = (
        "-".join("%02d" % p if i else str(p) for i, p in enumerate(dp) if p is not None)
        if dp and dp[0]
        else None
    )
    container = (msg.get("container-title") or [None])[0]
    short = (msg.get("short-container-title") or [None])[0]
    return {
        "title": (msg.get("title") or [None])[0],
        "authors": names,
        "author_count": len(names),
        "first_author": first,
        "corresponding_authors": [],
        "publication_date": pub_date,
        "year": dp[0] if dp else None,
        "journal": container,
        "journal_abbrev": short,  # Crossref short title; refined by enrich_journal()
        "impact_factor": None,
        "impact_factor_year": None,
        "impact_factor_source": None,
        "volume": msg.get("volume"),
        "issue": msg.get("issue"),
        "pages": msg.get("page"),
        "doi": msg.get("DOI"),
        "pmid": None,
        "openalex": None,
        "issn": (msg.get("ISSN") or [None])[0],
        "type": msg.get("type"),
        "is_oa": None,
        "cited_by_count": msg.get("is-referenced-by-count"),
        "abstract": re.sub(r"<[^>]+>", "", msg["abstract"]).strip()
        if msg.get("abstract")
        else None,
        "_meta_source": "Crossref",
    }


# --------------------------------------------------------------------------- #
# Sibling-skill delegation: journal-abbrev + journal-if
# --------------------------------------------------------------------------- #
_SIBLING_CACHE = {}


def _find_sibling(basename, env_var):
    if basename in _SIBLING_CACHE:
        return _SIBLING_CACHE[basename]
    override = os.environ.get(env_var)
    if override and os.path.isfile(override):
        _SIBLING_CACHE[basename] = override
        return override
    here = os.path.dirname(os.path.abspath(__file__))
    roots = [
        here,
        os.path.dirname(os.path.dirname(here)),  # <repo>/skills/journal-meta -> <repo>
        os.path.dirname(
            os.path.dirname(os.path.dirname(here))
        ),  # workspace root (siblings live here)
        os.path.expanduser("~/.claude/skills"),
        os.path.expanduser("~/.config/openclaw/skills"),
        os.path.expanduser("~/.openclaw/skills"),
        os.path.expanduser("~/.claude/plugins"),
    ]
    found = None
    seen = set()
    for root in roots:
        if not root or root in seen or not os.path.isdir(root):
            continue
        seen.add(root)
        for dirpath, dirnames, filenames in os.walk(root):
            depth = dirpath[len(root) :].count(os.sep)  # keep the walk shallow
            if depth > 5:
                dirnames[:] = []
                continue
            dirnames[:] = [
                d
                for d in dirnames
                if d not in (".git", "node_modules", "cache", "__pycache__", ".venv")
            ]
            if basename in filenames:
                found = os.path.join(dirpath, basename)
                break
        if found:
            break
    _SIBLING_CACHE[basename] = found
    return found


def _call_cli(path, args, timeout=40):
    try:
        p = subprocess.run(
            [sys.executable, path, *args, "--format", "json"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    out = (p.stdout or "").strip()
    if not out:
        return None
    try:
        env = json.loads(out)
    except json.JSONDecodeError:
        return None
    if env.get("ok"):
        return env.get("data")
    return None


def enrich_journal(rec, want_abbrev=True, want_if=True):
    sources = {}
    name = rec.get("journal")
    if not name:
        return sources

    # --- abbreviation ---
    if want_abbrev:
        cli = _find_sibling("jabbrv.py", "JOURNAL_ABBREV_CLI")
        data = _call_cli(cli, ["abbrev", name]) if cli else None
        if data and data.get("abbreviation"):
            rec["journal_abbrev"] = data["abbreviation"]
            sources["abbrev"] = "journal-abbrev (%s)" % data.get("source", "?")
        elif not rec.get("journal_abbrev"):
            try:
                rec["journal_abbrev"] = (
                    _get_text(
                        "https://abbreviso.toolforge.org/a/%s"
                        % urllib.parse.quote(name)
                    )
                    or None
                )
                if rec["journal_abbrev"]:
                    sources["abbrev"] = "AbbrevISO (fallback)"
            except Exception:
                pass
        elif rec.get("journal_abbrev"):
            sources["abbrev"] = "Crossref short-title"

    # --- impact factor ---
    if want_if:
        cli = _find_sibling("journal_if.py", "JOURNAL_IF_CLI")
        data = _call_cli(cli, ["lookup", name]) if cli else None
        if data and data.get("impact_factor") is not None:
            rec["impact_factor"] = data["impact_factor"]
            rec["impact_factor_year"] = data.get("year")
            rec["impact_factor_source"] = "journal-if (%s)" % data.get("source", "?")
            sources["impact_factor"] = rec["impact_factor_source"]
        else:
            issn = rec.get("issn")
            if issn:
                try:
                    s = _get_json(
                        "https://api.openalex.org/sources/issn:%s"
                        % urllib.parse.quote(issn)
                    )
                    val = (s.get("summary_stats") or {}).get("2yr_mean_citedness")
                    if val:
                        rec["impact_factor"] = round(val, 2)
                        rec["impact_factor_source"] = (
                            "OpenAlex 2yr mean citedness (approx)"
                        )
                        sources["impact_factor"] = rec["impact_factor_source"]
                except Exception:
                    pass
    return sources


# --------------------------------------------------------------------------- #
# Top-level lookup
# --------------------------------------------------------------------------- #
def lookup(query, want_abbrev=True, want_if=True):
    id_type, value = detect_id(query)
    try:
        work = openalex_fetch(id_type, value)
        rec = parse_openalex(work)
    except MetaError as e:
        # DOI not in OpenAlex -> try Crossref before giving up
        if id_type == "doi":
            if e.code == "not_found":
                rec = crossref_fetch(value)
            else:
                raise
        else:
            raise
    rec = {"query": query, "id_type": id_type, **rec}
    src = rec.pop("_meta_source", "OpenAlex")
    enrich = enrich_journal(rec, want_abbrev, want_if)
    return rec, {"metadata": src, **enrich}


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _envelope_ok(data, sources, latency_ms):
    return {
        "ok": True,
        "data": data,
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "cli_version": CLI_VERSION,
            "sources": sources,
            "latency_ms": latency_ms,
        },
    }


def _envelope_err(e, latency_ms):
    return {
        "ok": False,
        "error": {"code": e.code, "message": e.message, "retryable": e.retryable},
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "cli_version": CLI_VERSION,
            "latency_ms": latency_ms,
        },
    }


def _fmt_human(data):
    def row(label, val):
        if val in (None, "", [], {}):
            return None
        if isinstance(val, list):
            val = "; ".join(str(v) for v in val)
        return "  %-16s %s" % (label + ":", val)

    order = [
        ("Title", data.get("title")),
        ("First author", data.get("first_author")),
        ("Corresponding", data.get("corresponding_authors") or None),
        (
            "Authors",
            "%d (%s%s)"
            % (
                data.get("author_count") or 0,
                ", ".join((data.get("authors") or [])[:3]),
                ", …" if (data.get("author_count") or 0) > 3 else "",
            )
            if data.get("authors")
            else None,
        ),
        ("Published", data.get("publication_date") or data.get("year")),
        ("Journal", data.get("journal")),
        ("Abbrev", data.get("journal_abbrev")),
        (
            "Impact factor",
            (
                "%s (%s)"
                % (data["impact_factor"], data.get("impact_factor_source", ""))
                if data.get("impact_factor") is not None
                else None
            ),
        ),
        (
            "Volume/Issue",
            "/".join(x for x in (data.get("volume"), data.get("issue")) if x) or None,
        ),
        ("Pages", data.get("pages")),
        ("Type", data.get("type")),
        ("DOI", data.get("doi")),
        ("PMID", data.get("pmid")),
        ("ISSN", data.get("issn")),
        ("Cited by", data.get("cited_by_count")),
        ("Open access", data.get("is_oa")),
    ]
    lines = [r for r in (row(l, v) for l, v in order) if r]
    abs_ = data.get("abstract")
    if abs_:
        lines.append(
            "  %-16s %s"
            % ("Abstract:", (abs_[:400] + " …") if len(abs_) > 400 else abs_)
        )
    return "\n".join(lines)


def _choose_format(explicit):
    if explicit and explicit != "auto":
        return explicit
    return "human" if sys.stdout.isatty() else "json"


def emit(envelope, fmt):
    fmt = _choose_format(fmt)
    if fmt == "json":
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
        return
    if not envelope.get("ok"):
        err = envelope["error"]
        print("Error [%s]: %s" % (err["code"], err["message"]), file=sys.stderr)
        return
    data = envelope["data"]
    if isinstance(data, dict) and "results" in data:  # batch
        for i, item in enumerate(data["results"]):
            if i:
                print("-" * 60)
            if item.get("ok"):
                print(_fmt_human(item["data"]))
            else:
                print("  Error: %s" % item["error"]["message"])
    else:
        print(_fmt_human(data))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
SCHEMA = {
    "cli_version": CLI_VERSION,
    "schema_version": SCHEMA_VERSION,
    "commands": {
        "lookup": "lookup <doi|pmid|arxiv|openalex-id|title> -> one metadata record",
        "batch": "batch <file> -> one identifier/title per line",
        "schema": "print this machine-readable contract",
    },
    "flags": {
        "--format": "json|table|human|auto (default auto: json when piped, human on TTY)",
        "--json": "alias for --format json",
        "--no-abbrev": "skip journal-abbreviation enrichment",
        "--no-if": "skip impact-factor enrichment",
    },
    "env": {
        "JOURNAL_META_MAILTO / OPENALEX_MAILTO": "email for OpenAlex polite pool",
        "JOURNAL_ABBREV_CLI": "explicit path to journal-abbrev's jabbrv.py",
        "JOURNAL_IF_CLI": "explicit path to journal-if's journal_if.py",
    },
    "exit_codes": {
        "0": "success",
        "1": "runtime/upstream",
        "2": "bad input",
        "3": "not found",
    },
    "output_fields": [
        "title",
        "authors",
        "first_author",
        "corresponding_authors",
        "publication_date",
        "year",
        "journal",
        "journal_abbrev",
        "impact_factor",
        "volume",
        "issue",
        "pages",
        "doi",
        "pmid",
        "openalex",
        "issn",
        "type",
        "cited_by_count",
        "is_oa",
        "abstract",
    ],
}


def _parse_args(argv):
    fmt, flags, positional = "auto", {"abbrev": True, "if": True}, []
    it = iter(argv)
    for a in it:
        if a == "--format":
            fmt = next(it, "auto")
        elif a.startswith("--format="):
            fmt = a.split("=", 1)[1]
        elif a == "--json":
            fmt = "json"
        elif a == "--no-abbrev":
            flags["abbrev"] = False
        elif a == "--no-if":
            flags["if"] = False
        else:
            positional.append(a)
    return fmt, flags, positional


def main(argv):
    fmt, flags, pos = _parse_args(argv)
    if not pos:
        print(
            "usage: journal_meta.py <doi|pmid|arxiv|title> [--no-if] [--no-abbrev] [--format json|human]",
            file=sys.stderr,
        )
        return 2
    cmd = pos[0]
    if cmd == "schema":
        print(
            json.dumps(
                {"ok": True, "data": SCHEMA, "meta": {"cli_version": CLI_VERSION}},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    # allow bare identifier (no subcommand)
    if cmd in ("lookup", "batch"):
        rest = pos[1:]
    else:
        cmd, rest = "lookup", pos

    t0 = time.time()
    try:
        if cmd == "batch":
            if not rest or not os.path.isfile(rest[0]):
                raise MetaError(
                    "file_not_found",
                    "batch file not found: %r" % (rest[0] if rest else None),
                    exit_code=2,
                )
            with open(rest[0], encoding="utf-8") as fh:
                queries = [
                    ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")
                ]
            results, failed = [], 0
            for q in queries:
                try:
                    rec, srcs = lookup(q, flags["abbrev"], flags["if"])
                    results.append({"ok": True, "data": rec, "sources": srcs})
                except MetaError as e:
                    failed += 1
                    results.append(
                        {"ok": False, "error": {"code": e.code, "message": e.message}}
                    )
            env = _envelope_ok(
                {"results": results, "count": len(results), "failed": failed},
                {"metadata": "OpenAlex"},
                int((time.time() - t0) * 1000),
            )
            emit(env, fmt)
            return 0
        # single lookup
        query = " ".join(rest).strip()
        if not query:
            raise MetaError("validation_error", "no identifier given", exit_code=2)
        rec, srcs = lookup(query, flags["abbrev"], flags["if"])
        emit(_envelope_ok(rec, srcs, int((time.time() - t0) * 1000)), fmt)
        return 0
    except MetaError as e:
        emit(_envelope_err(e, int((time.time() - t0) * 1000)), fmt)
        return e.exit_code
    except Exception as e:  # pragma: no cover
        emit(
            _envelope_err(
                MetaError("runtime_error", str(e), retryable=True),
                int((time.time() - t0) * 1000),
            ),
            fmt,
        )
        return 1


# --------------------------------------------------------------------------- #
# Self-check (offline; runs pure functions on fixtures)
# --------------------------------------------------------------------------- #
def _selftest():
    cases = [
        ("10.1038/s41586-020-2649-2", "doi", "10.1038/s41586-020-2649-2"),
        ("https://doi.org/10.1/x", "doi", "10.1/x"),
        ("32939066", "pmid", "32939066"),
        ("pmid:123", "pmid", "123"),
        ("2101.00001", "arxiv", "2101.00001"),
        ("arxiv:2101.00001v2", "arxiv", "2101.00001v2"),
        ("W3035965352", "openalex", "W3035965352"),
        ("Attention is all you need", "title", "Attention is all you need"),
    ]
    for query, want_type, want_value in cases:
        got_type, got_value = detect_id(query)
        assert got_type == want_type, "detect_id type mismatch: %r" % query
        assert got_value == want_value, "detect_id value mismatch: %r" % query
    assert deinvert_abstract({"Hello": [1], "world": [0]}) == "world Hello"
    assert deinvert_abstract(None) is None
    work = {
        "title": "T",
        "publication_date": "2020-09-16",
        "publication_year": 2020,
        "doi": "https://doi.org/10.1/x",
        "cited_by_count": 5,
        "biblio": {
            "volume": "585",
            "issue": "7825",
            "first_page": "357",
            "last_page": "362",
        },
        "ids": {
            "openalex": "https://openalex.org/W1",
            "pmid": "https://pubmed.ncbi.nlm.nih.gov/999",
        },
        "primary_location": {
            "source": {"display_name": "Nature", "issn_l": "0028-0836"}
        },
        "authorships": [
            {
                "author": {"display_name": "A One"},
                "author_position": "first",
                "is_corresponding": False,
            },
            {
                "author": {"display_name": "B Two"},
                "author_position": "middle",
                "is_corresponding": True,
            },
        ],
    }
    r = parse_openalex(work)
    assert r["first_author"] == "A One"
    assert r["corresponding_authors"] == ["B Two"]
    assert r["pages"] == "357-362"
    assert r["pmid"] == "999" and r["openalex"] == "W1" and r["doi"] == "10.1/x"
    assert r["author_count"] == 2
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main(sys.argv[1:]))
