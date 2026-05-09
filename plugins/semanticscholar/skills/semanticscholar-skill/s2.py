"""Semantic Scholar API helper for the semanticscholar-skill.

Public surface (organized by phase of the skill's 4-phase workflow):

  Plan / construct queries
    build_bool_query(phrases, required, excluded, or_terms) -> str
    deduplicate(papers) -> list

  Execute searches
    search_relevance(query, **filters)         broad, ranked by relevance
    search_bulk(query, sort=..., **filters)    boolean syntax, up to 10M
    search_snippets(query, **filters)          full-text passage match
    match_title(title)                         exact title lookup
    paper_autocomplete(query)                  query-completion suggestions

  Direct lookup
    get_paper(paper_id)                        single paper, full fields
    batch_papers(ids, fields)                  up to 500 papers in one POST
    get_citations(paper_id, max_results)       who cites this work
    get_references(paper_id, max_results)      what this work cites
    get_paper_authors(paper_id, max_results)

  Recommendations
    find_similar(paper_id, limit, pool)        single seed
    recommend(positive_ids, negative_ids, ...) multi-seed

  Authors
    search_authors(query, max_results)
    get_author(author_id)
    get_author_papers(author_id, max_results)
    batch_authors(ids, fields)

  Present / export
    format_table(papers)                       summary markdown table
    format_details(papers)                     per-paper details with TLDR
    format_citations(citations)                citation list with intent labels
    format_results(papers, query_desc)         table + details combined
    format_authors(authors)                    author table
    export_bibtex(papers) | export_markdown(...) | export_json(...)

Trust + safety contract:
  - Auth comes from the S2_API_KEY env var; never accepted via function args.
  - All endpoints are read-only.
  - Rate limiting (1.1s gap) and exponential backoff are enforced inside
    _request and shared across the process via a module-level lock.

Filter kwargs are snake_case here and translated to the S2 camelCase params
inside _add_filters (year, publication_date -> publicationDateOrYear,
fields_of_study -> fieldsOfStudy, min_citations -> minCitationCount,
pub_types -> publicationTypes, open_access -> openAccessPdf, venue).
"""

import time, os, json, requests, sys

GRAPH = "https://api.semanticscholar.org/graph/v1"
RECS = "https://api.semanticscholar.org/recommendations/v1"
DATASETS = "https://api.semanticscholar.org/datasets/v1"

_API_KEY = os.environ.get("S2_API_KEY", "").strip()
HAS_KEY = bool(_API_KEY)
HEADERS = {"x-api-key": _API_KEY} if HAS_KEY else {}

# Without a key the shared anonymous pool allows ~100 req/5 min per IP;
# use a 3s gap to stay well inside that limit.
_last_request_time = 0
_MIN_GAP = 1.1 if HAS_KEY else 3.0


def _request(method, url, params=None, json_data=None, max_retries=5):
    """Send one request with rate limiting and exponential backoff.

    Enforces a 1.1s minimum gap between requests, retries on 429/504 with
    2s -> 60s exponential backoff (max 5 retries), and re-raises on other
    4xx/5xx after surfacing the response body to stderr for debugging.
    """
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_GAP:
        time.sleep(_MIN_GAP - elapsed)

    for attempt in range(max_retries + 1):
        _last_request_time = time.time()
        try:
            if method == "GET":
                r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            else:
                r = requests.post(url, params=params, json=json_data, headers=HEADERS, timeout=30)
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt < max_retries:
                wait = min(2 ** (attempt + 1), 60)
                print(f"  [conn-error] {type(e).__name__}, retry {attempt+1}/{max_retries} in {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            raise

        if r.status_code == 403 and HAS_KEY:
            # Invalid/expired key — drop it and retry unauthenticated this attempt.
            import s2 as _self
            print("  [auth] S2_API_KEY rejected (403); switching to unauthenticated mode", file=sys.stderr)
            _self.HAS_KEY = False
            _self.HEADERS = {}
            _self._MIN_GAP = 3.0
            continue
        if r.status_code in (429, 504):
            if attempt < max_retries:
                wait = min(2 ** (attempt + 1), 60)
                print(f"  [rate-limit] {r.status_code}, retry {attempt+1}/{max_retries} in {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            r.raise_for_status()
        elif r.status_code >= 400:
            # Surface API error body before raising — S2 returns {"message": "..."} or {"error": "..."}
            print(f"  [http-{r.status_code}] {r.text[:300]}", file=sys.stderr)
            r.raise_for_status()
        return r.json()


def s2_get(url, params=None):
    """Low-level GET; use the higher-level helpers below in normal use."""
    return _request("GET", url, params=params)


def s2_post(url, params=None, json_data=None):
    """Low-level POST; use the higher-level helpers below in normal use."""
    return _request("POST", url, params=params, json_data=json_data)


# --- Pagination ---

def paginate(url, params=None, max_results=1000):
    """Offset-based pagination via the `next` cursor (search/citations/references/authors)."""
    params = dict(params or {})
    params.setdefault("limit", 100)
    params["offset"] = 0
    results = []
    while len(results) < max_results:
        r = s2_get(url, params)
        results.extend(r.get("data", []))
        if "next" not in r or len(results) >= max_results:
            break
        params["offset"] = r["next"]
    return results[:max_results]


def paginate_bulk(url, params=None, max_results=10000):
    """Token-based pagination for /paper/search/bulk (up to ~10M results)."""
    params = dict(params or {})
    token = None
    results = []
    while len(results) < max_results:
        if token:
            params["token"] = token
        r = s2_get(url, params)
        results.extend(r.get("data", []))
        token = r.get("token")
        if not token or len(results) >= max_results:
            break
    return results[:max_results]


# --- Batch ---

def batch_papers(ids, fields="title,year,citationCount"):
    """POST up to 500 paper IDs in one request. Returns a list aligned to `ids` order."""
    return s2_post(f"{GRAPH}/paper/batch", params={"fields": fields}, json_data={"ids": ids[:500]})


def batch_authors(ids, fields="name,hIndex,paperCount"):
    """POST up to 1000 author IDs in one request."""
    return s2_post(f"{GRAPH}/author/batch", params={"fields": fields}, json_data={"ids": ids[:1000]})


# --- High-level search functions ---

_DEFAULT_FIELDS = "title,year,citationCount,authors,venue,externalIds,tldr"
_BULK_FIELDS = "title,year,citationCount,authors,venue,externalIds"  # bulk search doesn't support tldr

def _add_filters(params, year=None, venue=None, fields_of_study=None,
                 min_citations=None, pub_types=None, open_access=False,
                 publication_date=None):
    """Translate snake_case skill kwargs into the S2 camelCase query params."""
    if year: params["year"] = year
    if publication_date: params["publicationDateOrYear"] = publication_date
    if venue: params["venue"] = venue
    if fields_of_study: params["fieldsOfStudy"] = fields_of_study
    if min_citations: params["minCitationCount"] = str(min_citations)
    if pub_types: params["publicationTypes"] = pub_types
    if open_access: params["openAccessPdf"] = ""
    return params


def search_relevance(query, fields=_DEFAULT_FIELDS, max_results=20, **filters):
    """Relevance-ranked paper search. Up to 1,000 results. Use for broad topic exploration."""
    params = _add_filters({"query": query, "fields": fields, "limit": min(max_results, 100)}, **filters)
    if max_results <= 100:
        r = s2_get(f"{GRAPH}/paper/search", params)
        return r.get("data", [])[:max_results]
    return paginate(f"{GRAPH}/paper/search", params, max_results)


def search_bulk(query, fields=_BULK_FIELDS, max_results=100, sort="citationCount:desc", **filters):
    """Bulk search with boolean operators and `sort`. Up to ~10M results.

    NOTE: tldr is not available on this endpoint — use search_relevance if TLDR matters.
    Build precise queries with build_bool_query() to avoid noisy matches.
    """
    params = _add_filters({"query": query, "fields": fields, "sort": sort}, **filters)
    return paginate_bulk(f"{GRAPH}/paper/search/bulk", params, max_results)


def search_snippets(query, fields="snippet.text,snippet.snippetKind,snippet.section",
                    max_results=10, paper_ids=None, authors=None, inserted_before=None, **filters):
    """Full-text passage search — finds papers containing specific sentences/methods, not just titles.

    Snippet-only filters (in addition to the shared `_add_filters` set):
      paper_ids       List of paperIds to scope the search to (sent as `paperIds`)
      authors         List of authorIds to scope the search to (sent as `authors`)
      inserted_before YYYY-MM-DD; restrict to snippets ingested before this date
    """
    params = _add_filters({"query": query, "fields": fields, "limit": min(max_results, 100)}, **filters)
    if paper_ids: params["paperIds"] = ",".join(paper_ids) if isinstance(paper_ids, list) else paper_ids
    if authors: params["authors"] = ",".join(authors) if isinstance(authors, list) else authors
    if inserted_before: params["insertedBefore"] = inserted_before
    return s2_get(f"{GRAPH}/snippet/search", params).get("data", [])[:max_results]


def paper_autocomplete(query):
    """Suggest paper completions for an in-progress query string. Returns a list of {id, title, authorsYear}.

    NOTE: this endpoint is on the public tier and rejects API-key auth with 403, so
    it's called without HEADERS. Still subject to the shared rate limiter.
    """
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_GAP:
        time.sleep(_MIN_GAP - elapsed)
    _last_request_time = time.time()
    r = requests.get(f"{GRAPH}/paper/autocomplete", params={"query": query}, timeout=30)
    r.raise_for_status()
    return r.json().get("matches", [])


def get_paper(paper_id, fields=_DEFAULT_FIELDS + ",abstract,references,openAccessPdf"):
    """Fetch one paper by ID. Accepts DOI:, ARXIV:, PMID:, PMCID:, CorpusId:, ACL:, MAG:, URL: prefixes."""
    return s2_get(f"{GRAPH}/paper/{paper_id}", {"fields": fields})


def get_citations(paper_id, fields="title,year,citationCount,authors,venue,contextsWithIntent",
                  max_results=100, publication_date=None):
    """List citations of a paper. Each item is {citingPaper, contextsWithIntent: [{context, intents}]}.

    Default fields include contextsWithIntent so format_citations() can render
    methodology/background/result intent labels per citation. Pass without it
    to reduce payload if intents aren't needed.

    `publication_date` (YYYY-MM-DD or year range) filters by the citing paper's date.
    """
    params = {"fields": fields, "limit": min(max_results, 1000)}
    if publication_date: params["publicationDateOrYear"] = publication_date
    return paginate(f"{GRAPH}/paper/{paper_id}/citations", params, max_results)


def get_references(paper_id, fields="title,year,citationCount,authors,venue", max_results=100):
    """List references of a paper. Each item is {citedPaper, contexts, intents}."""
    return paginate(f"{GRAPH}/paper/{paper_id}/references",
                    {"fields": fields, "limit": min(max_results, 1000)}, max_results)


def find_similar(paper_id, fields="title,year,citationCount,authors,venue", limit=10, pool="recent"):
    """Single-seed recommendations. `pool` is "recent" or "all-cs" (CS-only legacy pool)."""
    return s2_get(f"{RECS}/papers/forpaper/{paper_id}",
                  {"fields": fields, "limit": limit, "from": pool}).get("recommendedPapers", [])


def recommend(positive_ids, negative_ids=None, fields="title,year,citationCount,authors,venue", limit=10):
    """Multi-seed recommendations: papers similar to positives but unlike negatives."""
    body = {"positivePaperIds": positive_ids}
    if negative_ids:
        body["negativePaperIds"] = negative_ids
    return s2_post(f"{RECS}/papers/", params={"fields": fields, "limit": limit},
                   json_data=body).get("recommendedPapers", [])


# --- Author functions ---

_DEFAULT_AUTHOR_FIELDS = "name,affiliations,paperCount,citationCount,hIndex"


def search_authors(query, fields=_DEFAULT_AUTHOR_FIELDS, max_results=20):
    """Search authors by name. Up to 1,000 results. Pick by affiliation/h-index when names collide."""
    params = {"query": query, "fields": fields, "limit": min(max_results, 1000)}
    if max_results <= 1000:
        r = s2_get(f"{GRAPH}/author/search", params)
        return r.get("data", [])[:max_results]
    return paginate(f"{GRAPH}/author/search", params, max_results)


def get_author(author_id, fields=_DEFAULT_AUTHOR_FIELDS):
    """Fetch one author by ID."""
    return s2_get(f"{GRAPH}/author/{author_id}", {"fields": fields})


def get_author_papers(author_id, fields=_DEFAULT_FIELDS, max_results=100, publication_date=None):
    """List an author's papers, paginated. `publication_date` (YYYY-MM-DD or year range) filters by paper date."""
    params = {"fields": fields, "limit": min(max_results, 1000)}
    if publication_date: params["publicationDateOrYear"] = publication_date
    return paginate(f"{GRAPH}/author/{author_id}/papers", params, max_results)


def get_paper_authors(paper_id, fields=_DEFAULT_AUTHOR_FIELDS, max_results=100):
    """List the authors of a paper."""
    return paginate(f"{GRAPH}/paper/{paper_id}/authors",
                    {"fields": fields, "limit": min(max_results, 1000)}, max_results)


def match_title(title, fields=_DEFAULT_FIELDS):
    """Closest title match — single best result. Use when you have a title string and need the paper."""
    return s2_get(f"{GRAPH}/paper/search/match", {"query": title, "fields": fields})


# --- Utilities ---

def deduplicate(papers):
    """Drop duplicates by paperId, preserving first-seen order."""
    seen = set()
    out = []
    for p in papers:
        pid = p.get("paperId")
        if pid and pid not in seen:
            seen.add(pid)
            out.append(p)
    return out


def build_bool_query(phrases=None, required=None, excluded=None, or_terms=None,
                     fuzzy=None, proximity=None):
    """Compose a boolean query string for search_bulk.

    phrases    -> "exact phrase" (quoted)
    required   -> +term (must include)
    excluded   -> -term (must exclude)
    or_terms   -> (a | b | c) group
    fuzzy      -> list of (term, edit_distance): bugs~3 matches buggy/buns/busg
    proximity  -> list of (phrase, word_distance): ("blue lake", 3) matches
                  phrases with up to 3 words between "blue" and "lake"
    """
    parts = []
    for p in (phrases or []):
        parts.append(f'"{p}"')
    for r in (required or []):
        parts.append(f"+{r}")
    for e in (excluded or []):
        parts.append(f"-{e}")
    if or_terms:
        parts.append("(" + " | ".join(or_terms) + ")")
    for term, dist in (fuzzy or []):
        parts.append(f"{term}~{dist}")
    for phrase, dist in (proximity or []):
        parts.append(f'"{phrase}"~{dist}')
    return " ".join(parts)


# --- Datasets API ---

def list_releases():
    """Return a list of all available dataset release date strings (newest last)."""
    return s2_get(f"{DATASETS}/release/")


def list_datasets(release_id="latest"):
    """Return dataset metadata for a given release. Use release_id='latest' for the newest."""
    return s2_get(f"{DATASETS}/release/{release_id}")


def get_dataset_links(release_id, dataset_name):
    """Return pre-signed download URLs for a dataset file. Requires a valid API key."""
    if not HAS_KEY:
        raise RuntimeError("get_dataset_links requires S2_API_KEY — dataset downloads are not available unauthenticated")
    return s2_get(f"{DATASETS}/release/{release_id}/dataset/{dataset_name}")


def get_dataset_diffs(start_release_id, end_release_id, dataset_name):
    """Return incremental diffs (update + delete file lists) between two releases. Requires API key."""
    if not HAS_KEY:
        raise RuntimeError("get_dataset_diffs requires S2_API_KEY")
    return s2_get(f"{DATASETS}/diffs/{start_release_id}/to/{end_release_id}/{dataset_name}")


# --- Output formatting ---

def _doi(paper):
    ext = paper.get("externalIds") or {}
    return ext.get("DOI", "")


def _first_author(paper):
    authors = paper.get("authors") or []
    if not authors:
        return ""
    name = authors[0].get("name", "")
    return f"{name} et al." if len(authors) > 1 else name


def format_table(papers, max_rows=30):
    """Markdown summary table: # | Title | Year | Cites | First Author | Venue."""
    rows = ["| # | Title | Year | Cites | First Author | Venue |",
            "|---|-------|------|-------|-------------|-------|"]
    for i, p in enumerate(papers[:max_rows], 1):
        t = (p.get("title") or "")[:80]
        y = p.get("year") or ""
        c = p.get("citationCount") or 0
        a = _first_author(p)[:25]
        v = (p.get("venue") or "")[:30]
        rows.append(f"| {i} | {t} | {y} | {c} | {a} | {v} |")
    return "\n".join(rows)


def format_details(papers, max_papers=10):
    """Per-paper detailed entries (title, authors, citations, DOI, TLDR/abstract)."""
    lines = []
    for i, p in enumerate(papers[:max_papers], 1):
        title = p.get("title") or "Untitled"
        year = p.get("year") or "?"
        cites = p.get("citationCount") or 0
        doi = _doi(p)
        authors = ", ".join(a.get("name", "") for a in (p.get("authors") or [])[:5])
        if len(p.get("authors") or []) > 5:
            authors += " et al."
        tldr = (p.get("tldr") or {}).get("text", "")
        abstract = (p.get("abstract") or "")[:300]
        summary = tldr or (abstract + "..." if len(p.get("abstract") or "") > 300 else abstract)

        lines.append(f"### {i}. {title} ({year})")
        lines.append(f"**Authors:** {authors}")
        lines.append(f"**Citations:** {cites} | **DOI:** {doi}" if doi else f"**Citations:** {cites}")
        if summary:
            lines.append(f"**Summary:** {summary}")
        lines.append("")
    return "\n".join(lines)


def format_citations(citations, max_items=10):
    """Render citation envelopes with intent labels and a representative context snippet.

    Input shape (from get_citations): [{citingPaper: {...}, contextsWithIntent: [{context, intents}]}].
    Use this instead of format_details when you want WHY a paper was cited
    (methodology / background / result), not just which papers cited it.
    """
    lines = []
    for i, c in enumerate(citations[:max_items], 1):
        p = c.get("citingPaper") or {}
        title = p.get("title") or "Untitled"
        year = p.get("year") or "?"
        cites = p.get("citationCount") or 0
        authors = _first_author(p)
        cwi = c.get("contextsWithIntent") or []
        intents = sorted({i for entry in cwi for i in (entry.get("intents") or [])})
        snippet = (cwi[0].get("context") if cwi else "")[:240]

        lines.append(f"### {i}. {title} ({year})")
        lines.append(f"**Cited by:** {authors} | **Citations:** {cites}")
        if intents:
            lines.append(f"**Intents:** {', '.join(intents)}")
        if snippet:
            lines.append(f"**Context:** \"{snippet}{'...' if len(snippet) == 240 else ''}\"")
        lines.append("")
    return "\n".join(lines)


def format_results(papers, query_desc=""):
    """Combined header + summary table + top-10 details."""
    n = len(papers)
    header = f"## Search Results: {query_desc}\n\n**{n} papers found.**\n" if query_desc else f"**{n} papers found.**\n"
    table = format_table(papers)
    details = format_details(papers[:10])
    return f"{header}\n{table}\n\n---\n\n{details}"


def format_authors(authors, max_rows=20):
    """Markdown table of authors with affiliations, paper count, citations, h-index."""
    rows = ["| # | Name | Affiliations | Papers | Citations | h-index |",
            "|---|------|-------------|--------|-----------|---------|"]
    for i, a in enumerate(authors[:max_rows], 1):
        name = a.get("name", "")
        affs = ", ".join(a.get("affiliations") or [])[:40]
        pc = a.get("paperCount") or 0
        cc = a.get("citationCount") or 0
        h = a.get("hIndex") or 0
        rows.append(f"| {i} | {name} | {affs} | {pc} | {cc} | {h} |")
    return "\n".join(rows)


def export_bibtex(papers):
    """Concat the `citationStyles.bibtex` field across papers. Requires fields=...,citationStyles."""
    entries = []
    for p in papers:
        bib = (p.get("citationStyles") or {}).get("bibtex")
        if bib:
            entries.append(bib)
    return "\n\n".join(entries)


def export_markdown(papers, query_desc="", path="/tmp/s2_results.md"):
    """Write format_results() output to a file. Returns the path."""
    content = format_results(papers, query_desc)
    with open(path, "w") as f:
        f.write(content)
    print(f"Saved {len(papers)} papers to {path}")
    return path


def export_json(papers, path="/tmp/s2_results.json"):
    """Dump the raw paper list as JSON. Returns the path."""
    with open(path, "w") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(papers)} papers to {path}")
    return path
