#!/usr/bin/env python3
"""extract_pdf.py — extract text from a PDF.

Two engines:
  - pypdf (default, zero extra deps) — fast, stdlib-only, plain text.
    Multi-column layouts may interleave; tables/figures dropped; scanned
    PDFs return junk.
  - docling (optional, `pip install docling`) — layout-aware, markdown
    output, preserves headings/tables/figure captions/formulas. Slower
    (loads ML models on first use) but handles the cases pypdf can't.

Engine selection (--engine):
  - auto (default): try pypdf; if the result looks scanned/sparse
    (char_count/page < 200), re-run with docling when it's installed.
    Otherwise return the pypdf result.
  - pypdf: force pypdf.
  - docling: force docling. Errors with `missing_dependency` if not installed.

OCR for the docling engine (--ocr-backend / --ocr-lang):
  Docling has OCR ON by default (do_ocr=True). Override the backend
  with --ocr-backend {auto,rapidocr,ocrmac,easyocr,tesseract,none}
  (default `auto` lets docling pick). Pass --ocr-lang to specify the
  language; lang vocab differs per backend — see --help for details.
  Use `--ocr-backend none` to skip OCR entirely on a known-clean PDF
  and save the ~10s model-load cost.

Usage:
  python scripts/extract_pdf.py --input paper.pdf --output paper.md
  python scripts/extract_pdf.py --doi 10.1038/x --engine docling --output paper.md
  python scripts/extract_pdf.py --input scan.pdf --engine docling --ocr-lang en
  python scripts/extract_pdf.py --input clean.pdf --engine docling --ocr-backend none

DOI resolution (--doi):
  1. paper-fetch skill if installed (5-source OA chain)
  2. Unpaywall direct fallback
  Discovery: PAPER_FETCH_SCRIPT env var → ~/.claude/skills/paper-fetch/scripts/fetch.py

Output format is reported in `meta.format` ("text" for pypdf, "markdown" for
docling). With docling, --pages is ignored (whole-document conversion).
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from typing import Any

from _common import (
    EXIT_RUNTIME, EXIT_UPSTREAM, EXIT_VALIDATION,
    command_signature, err, maybe_emit_schema, ok, read_cache,
    set_command_meta, write_cache,
)
from _pdf_fetch import FetchError, fetch_pdf, find_paper_fetch_script

try:
    from pypdf import PdfReader
except ImportError:
    err("missing_dependency",
        "pypdf not installed. Run: pip install pypdf",
        retryable=False, exit_code=EXIT_RUNTIME,
        dependency="pypdf")


# ---------- FetchError → err() exit-code mapping ----------
#
# Single-paper extract is fail-fast: any FetchError translates to one
# err() call with the matching exit code. The mapping preserves the
# pre-refactor envelope-shape contract — exit codes shipped with
# specific error codes do not change.
_FETCH_EXIT = {
    "paper_fetch_failed": EXIT_UPSTREAM,
    "paper_fetch_bad_response": EXIT_RUNTIME,
    "paper_fetch_error": EXIT_UPSTREAM,
    "paper_fetch_no_pdf": EXIT_RUNTIME,
    "unpaywall_request_failed": EXIT_UPSTREAM,
    "no_open_access_pdf": EXIT_VALIDATION,
    "pdf_download_failed": EXIT_UPSTREAM,
}

# Heuristic threshold (chars/page). Below this, pypdf almost certainly
# missed the layout (scanned/image-only PDF, or pathological encoding) —
# trigger the docling fallback in --engine auto.
_THIN_TEXT_PER_PAGE = 200


# ---------- extraction ----------

def parse_pages(spec: str | None, total: int) -> list[int]:
    if not spec:
        return list(range(total))
    pages: set[int] = set()
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            pages.update(range(int(a) - 1, int(b)))
        else:
            pages.add(int(part) - 1)
    return sorted(p for p in pages if 0 <= p < total)


def extract_pypdf(pdf_path: Path, pages: list[int]) -> tuple[str, dict]:
    reader = PdfReader(str(pdf_path))
    parts = []
    warnings = []
    for i in pages:
        try:
            t = reader.pages[i].extract_text() or ""
        except Exception as e:
            warnings.append(f"page {i+1}: {e}")
            t = ""
        parts.append(t)
    text = "\n\n".join(parts)
    char_count = len(text.strip())
    is_scanned = char_count < _THIN_TEXT_PER_PAGE * len(pages)
    meta = {
        "engine": "pypdf",
        "format": "text",
        "pages_extracted": len(pages),
        "total_pages": len(reader.pages),
        "char_count": char_count,
        "looks_scanned": is_scanned,
        "warnings": warnings,
    }
    return text, meta


def _build_ocr_options(backend: str, lang: str | None):
    """Map --ocr-backend / --ocr-lang to a docling `ocr_options` instance.

    Returns the options object, or None when `backend=="none"` (caller
    sets `do_ocr=False` instead). Each backend uses its own language
    code vocabulary — RapidOCR: 'chinese'/'english'/'japan'; EasyOCR:
    'ch_sim'/'en'; OcrMac: BCP-47 like 'en-US'/'zh-CN'; Tesseract:
    'eng'/'chi_sim'. The CLI passes the user's string through verbatim
    (split on ',') rather than trying to normalize across backends.
    """
    if backend == "none":
        return None

    # Lazy import — only fail if the user actually requested docling.
    from docling.datamodel.pipeline_options import (
        EasyOcrOptions, OcrAutoOptions, OcrMacOptions, RapidOcrOptions,
        TesseractOcrOptions,
    )
    cls = {
        "auto": OcrAutoOptions,
        "rapidocr": RapidOcrOptions,
        "ocrmac": OcrMacOptions,
        "easyocr": EasyOcrOptions,
        "tesseract": TesseractOcrOptions,
    }[backend]

    kwargs: dict = {}
    if lang:
        kwargs["lang"] = [s.strip() for s in lang.split(",") if s.strip()]
    return cls(**kwargs)


def extract_docling(pdf_path: Path, *,
                    ocr_backend: str = "auto",
                    ocr_lang: str | None = None) -> tuple[str, dict]:
    """Convert a PDF to markdown via docling.

    Lazy import so the optional dep is only required when docling is
    actually selected. Returns the markdown text and a meta dict with
    `engine="docling"`, `format="markdown"`, and the OCR config that
    was actually used.

    OCR is on by default (docling's `do_ocr=True`). Pass
    `ocr_backend="none"` to skip OCR for a known-clean PDF.
    """
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import (
            DocumentConverter, PdfFormatOption,
        )
    except ImportError:
        err("missing_dependency",
            "docling not installed. Run: pip install docling (or use --engine pypdf).",
            retryable=False, exit_code=EXIT_RUNTIME,
            dependency="docling")

    pipeline_options = PdfPipelineOptions()
    if ocr_backend == "none":
        pipeline_options.do_ocr = False
    else:
        try:
            pipeline_options.ocr_options = _build_ocr_options(
                ocr_backend, ocr_lang,
            )
        except KeyError:
            err("invalid_ocr_backend",
                f"Unknown --ocr-backend: {ocr_backend!r}",
                retryable=False, exit_code=EXIT_VALIDATION,
                backend=ocr_backend)

    converter = DocumentConverter(format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
    })
    try:
        result = converter.convert(str(pdf_path))
    except Exception as e:
        err("docling_failure",
            f"docling failed to convert {pdf_path}: {type(e).__name__}: {e}",
            retryable=False, exit_code=EXIT_RUNTIME,
            path=str(pdf_path))

    markdown = result.document.export_to_markdown()
    # Read page count defensively — docling exposes it as a method on some
    # versions, an int attr on others, and via the `pages` collection on
    # older releases. Any failure here is non-fatal — page count is just
    # metadata, not contract.
    total_pages = 0
    num_pages = getattr(result.document, "num_pages", None)
    if callable(num_pages):
        try:
            total_pages = int(num_pages() or 0)
        except Exception:
            total_pages = 0
    elif isinstance(num_pages, int):
        total_pages = num_pages
    if not total_pages:
        try:
            total_pages = len(getattr(result.document, "pages", []) or [])
        except TypeError:
            total_pages = 0
    char_count = len(markdown.strip())
    meta = {
        "engine": "docling",
        "format": "markdown",
        "total_pages": total_pages,
        "char_count": char_count,
        "looks_scanned": False,
        "warnings": [],
        "ocr_backend": ocr_backend,
        "ocr_lang": ocr_lang,
        "do_ocr": pipeline_options.do_ocr,
    }
    return markdown, meta


def _do_extract(pdf_path: Path, engine: str, page_spec: str | None,
                *, ocr_backend: str = "auto",
                ocr_lang: str | None = None) -> tuple[str, dict]:
    """Engine selector. Returns `(text, meta)`."""
    if engine == "docling":
        if page_spec:
            # docling converts whole documents; surface this clearly
            # rather than silently ignoring --pages.
            return _with_warning(
                extract_docling(pdf_path, ocr_backend=ocr_backend,
                                ocr_lang=ocr_lang),
                "docling ignores --pages; converted whole document.",
            )
        return extract_docling(pdf_path, ocr_backend=ocr_backend,
                               ocr_lang=ocr_lang)

    # pypdf path (also the auto-mode starting point).
    reader = PdfReader(str(pdf_path))
    page_indices = parse_pages(page_spec, len(reader.pages))
    text, meta = extract_pypdf(pdf_path, page_indices)

    if engine == "pypdf":
        return text, meta

    # engine == "auto": upgrade to docling if pypdf result looks empty
    # AND docling is importable; otherwise return the pypdf result with
    # a `fallback_skipped` note so the agent knows why.
    if not meta["looks_scanned"]:
        return text, meta

    try:
        import docling  # noqa: F401
    except ImportError:
        meta["engine_fallback_reason"] = (
            "looks_scanned but docling not installed; install with "
            "`pip install docling` to auto-upgrade scanned/sparse PDFs."
        )
        return text, meta

    # Re-extract with docling. Preserve the pypdf attempt's diagnostic
    # data in the meta so the agent can see why we upgraded.
    doc_text, doc_meta = extract_docling(pdf_path, ocr_backend=ocr_backend,
                                          ocr_lang=ocr_lang)
    doc_meta["engine_fallback_reason"] = (
        f"pypdf produced {meta['char_count']} chars across "
        f"{meta['pages_extracted']} pages (looks_scanned); "
        "auto-upgraded to docling."
    )
    return doc_text, doc_meta


def _with_warning(result: tuple[str, dict], message: str) -> tuple[str, dict]:
    text, meta = result
    meta.setdefault("warnings", []).append(message)
    return text, meta


def _write_output(text: str, output: str | None, meta: dict) -> None:
    """Write extracted text to `output` (if set) and update meta in-place."""
    if output:
        out = Path(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        meta["output"] = str(out)
    else:
        meta["text_preview"] = text[:500]


def main() -> None:
    p = argparse.ArgumentParser(description="Extract text from PDF.")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="Local PDF path")
    src.add_argument("--url", help="URL to download then extract")
    src.add_argument("--doi", help="DOI to resolve via paper-fetch or Unpaywall")
    p.add_argument("--output", help="Write extracted text to this path "
                                    "(suggested: .md for docling, .txt for pypdf)")
    p.add_argument("--pages", help="Page range, e.g. 1-5,8,10-12 "
                                   "(pypdf only; docling converts whole doc)")
    p.add_argument("--engine", choices=("auto", "pypdf", "docling"),
                   default="auto",
                   help="Extraction engine. 'auto' tries pypdf then "
                        "upgrades to docling for scanned/sparse output "
                        "when docling is installed.")
    p.add_argument("--ocr-backend",
                   choices=("auto", "rapidocr", "ocrmac", "easyocr",
                            "tesseract", "none"),
                   default="auto",
                   help="OCR backend for the docling engine. 'auto' lets "
                        "docling pick whichever is installed (RapidOCR is "
                        "the typical default). 'none' disables OCR for "
                        "known-clean PDFs to skip the ~10s model-load cost. "
                        "Only consulted when the docling engine actually "
                        "runs (force via --engine docling, or let --engine "
                        "auto upgrade on a scanned PDF).")
    p.add_argument("--ocr-lang",
                   help="Comma-separated language hint passed verbatim to "
                        "the OCR backend. Vocab differs per backend: "
                        "RapidOCR uses 'chinese'/'english'/'japan'; EasyOCR "
                        "'ch_sim'/'en'; OcrMac 'en-US'/'zh-CN'; Tesseract "
                        "'eng'/'chi_sim'. Example: --ocr-lang en for an "
                        "English-only scan (avoids the Chinese-comma "
                        "artifact RapidOCR's default model produces).")
    p.add_argument("--idempotency-key",
                   help="Cache the extracted text under this key so retries "
                        "replay the same response (and rewrite --output) "
                        "without re-running the engine.")
    p.add_argument("--schema", action="store_true",
                   help="Print this command's parameter schema as JSON and exit")
    set_command_meta(p, since="0.14.0", tier="read")
    maybe_emit_schema(p, "extract_pdf")
    args = p.parse_args()

    # Idempotency: check cache before any download or extraction. Cache
    # entry holds {response, _text, signature} so a hit can replay the
    # output-file side effect.
    sig = command_signature(args)
    if args.idempotency_key:
        cached = read_cache(args.idempotency_key)
        if cached is not None:
            if cached.get("signature") and cached["signature"] != sig:
                err("idempotency_key_mismatch",
                    f"Idempotency key '{args.idempotency_key}' was previously "
                    "used with different arguments. Use a new key or flush "
                    "the cache entry.",
                    retryable=False, exit_code=EXIT_VALIDATION,
                    key=args.idempotency_key,
                    cached_signature=cached["signature"],
                    current_signature=sig)
            response = dict(cached["response"])
            text = response.pop("_text", "")
            # Always rewrite --output on cache hit — even when the
            # extraction produced an empty document. The agent asked
            # for a file at this path; an absent file would silently
            # break the consumer.
            if args.output:
                out = Path(args.output)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(text)
                response["output"] = str(out)
            ok(response, meta={
                "cache_hit": True,
                "idempotency_key": args.idempotency_key,
                "cached_at": cached.get("cached_at"),
            })
            return

    fetch_meta: dict[str, Any] | None = None

    if args.doi:
        fetch_script = find_paper_fetch_script()
        if fetch_script:
            print(f"[info] Using paper-fetch: {fetch_script}", file=sys.stderr)
        else:
            print("[info] paper-fetch not found, falling back to Unpaywall",
                  file=sys.stderr)
        try:
            pdf_path, fetch_meta = fetch_pdf(
                args.doi, fetch_script=fetch_script,
            )
        except FetchError as e:
            err(e.code, e.message,
                retryable=e.retryable,
                exit_code=_FETCH_EXIT.get(e.code, EXIT_UPSTREAM),
                **e.ctx)
    elif args.url:
        import httpx
        try:
            r = httpx.get(args.url, follow_redirects=True, timeout=60.0,
                          headers={"User-Agent": "scholar-deep-research/0.1"})
            r.raise_for_status()
        except httpx.HTTPError as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            err("download_failed",
                f"Failed to download {args.url}: {type(e).__name__}: {e}",
                retryable=True, exit_code=EXIT_UPSTREAM,
                url=args.url, status=status)
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(r.content)
        tmp.close()
        pdf_path = Path(tmp.name)
    else:
        pdf_path = Path(args.input)
        if not pdf_path.exists():
            err("file_not_found",
                f"PDF not found: {pdf_path}",
                retryable=False, exit_code=EXIT_VALIDATION,
                path=str(pdf_path))

    try:
        text, meta = _do_extract(pdf_path, args.engine, args.pages,
                                  ocr_backend=args.ocr_backend,
                                  ocr_lang=args.ocr_lang)
    except SystemExit:
        # err() inside the engine helpers already emitted the envelope.
        raise
    except Exception as e:
        err("extract_failure",
            f"{args.engine} engine failed on {pdf_path}: {type(e).__name__}: {e}",
            retryable=False, exit_code=EXIT_RUNTIME,
            path=str(pdf_path), engine=args.engine)

    if fetch_meta:
        meta["fetch_meta"] = fetch_meta

    _write_output(text, args.output, meta)

    if args.idempotency_key:
        # Store text alongside meta so a retry can replay the file write.
        write_cache(
            args.idempotency_key,
            {**meta, "_text": text},
            signature=sig,
        )
        ok(meta, meta={
            "cache_hit": False,
            "idempotency_key": args.idempotency_key,
        })
    else:
        ok(meta)


if __name__ == "__main__":
    main()
