# Maintaining asta-skill

The skill is a pure instruction pack over the live Asta MCP server, so its only failure mode
is **drift**: the server changes and the skill keeps asserting yesterday's behavior. This file
holds the check that detects drift and the snapshot it is compared against.

Source of truth is the live `tools/list` (`https://asta-tools.allen.ai/mcp/v1`), never the
public docs page. The docs page lags: it documents 7 tools (omitting `get_paper_batch`, and
titles `get_paper` as `get_papers`) and states a `snippet_search` default `limit` of 250 where
the live server returns 20 (measured 2026-10-01).

## Drift check (run before every release)

```bash
export ASTA_API_KEY=xxxxxxxxxxxxxxxx
URL=https://asta-tools.allen.ai/mcp/v1
call() { curl -sS --max-time 25 -X POST "$URL" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -H "x-api-key: $ASTA_API_KEY" -d "$1" | sed -n 's/^data: //p' | tail -1; }

call '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"drift-check","version":"1"}}}' > init.json
call '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' > tools.json
call '{"jsonrpc":"2.0","id":3,"method":"prompts/list"}' > prompts.json
call '{"jsonrpc":"2.0","id":4,"method":"resources/list"}' > resources.json

python3 -c "import hashlib,json; d=json.load(open('tools.json'))['result']; print(hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest())"
```

The server is stateless (no session id, nothing carried between calls). Compare the printed
hash and the tool names, parameters and defaults against the snapshot below. `prompts` and
`resources` are advertised capabilities but have always come back empty; only their non-emptiness
would need new documentation.

If the hash changed:

1. Diff the tool set: added or removed tools, renamed parameters, changed `default`s. A
   description-only change still matters, because each tool description carries its own
   parameter documentation.
2. Re-run the behavioral checks below, since those are not visible in the schema.
3. Update `SKILL.md` (tool map, parameter exceptions, budget table, response shapes), bump the
   version, and refresh the snapshot in this file.

A short `curl` plus `diff` against a saved `tools.json` is enough for the schema half; keep the
saved file outside the repo or regenerate it, do not commit raw responses.

## Behavioral checks (re-run when the snapshot changes)

None of these are visible in `tools/list`, and each one is load-bearing for the skill's advice:

| Check | Probe | Expected (as of 2026-10-01) |
| --- | --- | --- |
| Unknown parameters are ignored, not rejected | `get_citations` with an extra `venues`, or `get_author_papers` with `fields=` instead of `paper_fields=` | Call succeeds; the filter is silently absent (title-only rows for the second case) |
| Failures hide behind HTTP 200 | Call any tool with a bad key, and call an unknown tool name | `result.isError: true` with `Error executing tool ...: HTTP status 403 Forbidden.` / `Unknown tool: get_references` |
| Venue strings | `search_papers_by_relevance` with `venues="NeurIPS"` and with a nonsense string | Abbreviations resolve; a nonsense venue returns `content: []` (empty, not an error) |
| Zero-result streams | A keyword search that matches nothing | The SSE stream can carry only `: ping` keepalives until the client times out instead of returning `[]`; requires a client timeout and one retry |
| Payload sizes | 50-row search with `abstract`; `get_paper` with `fields=...citations`; `snippet_search` with no `limit` | ~296 KB; ~200 KB; 20 rows / ~85 KB |
| Pass-through fields | `externalIds`, `citationCount`, `influentialCitationCount` in `fields` | Return correctly although undocumented |
| Author `papers` field | `search_authors_by_name` with `fields=name,papers` | Returns every paper of the author and ignores `limit` |

## Pinned snapshot

Captured 2026-10-01 from server `Asta Scientific Corpus Tools` v1.12.3, protocol `2025-03-26`.

`tools/list` canonical SHA-256:
`ac9629d3b07634e3a8d236e8defb350bd69cca52c2f2d02295efed8a6c90e02a`

```json
[
  {"name": "get_paper", "required": ["paper_id"], "params": {"paper_id": {"type": "string"}, "fields": {"type": "string", "default": "title"}}, "desc_sha256_12": "56013cd9b52e"},
  {"name": "get_paper_batch", "required": ["ids"], "params": {"ids": {"type": "array", "items": "string"}, "fields": {"type": "string", "default": "title"}}, "desc_sha256_12": "bfb11a285e75"},
  {"name": "get_citations", "required": ["paper_id"], "params": {"paper_id": {"type": "string"}, "fields": {"type": "string", "default": "title"}, "limit": {"type": "integer", "default": 100}, "publication_date_range": {"type": "string", "default": ""}}, "desc_sha256_12": "0e532cc97eb8"},
  {"name": "search_authors_by_name", "required": ["name"], "params": {"name": {"type": "string"}, "fields": {"type": "string", "default": "name"}, "limit": {"type": "integer", "default": 100}}, "desc_sha256_12": "e34446bbcedf"},
  {"name": "get_author_papers", "required": ["author_id"], "params": {"author_id": {"type": "string"}, "paper_fields": {"type": "string", "default": "title"}, "limit": {"type": "integer", "default": 1000}, "publication_date_range": {"type": "string", "default": ""}}, "desc_sha256_12": "78c5b426b19c"},
  {"name": "search_papers_by_relevance", "required": ["keyword"], "params": {"keyword": {"type": "string"}, "fields": {"type": "string", "default": "title"}, "limit": {"type": "integer", "default": 50}, "publication_date_range": {"type": "string", "default": ""}, "venues": {"type": "string", "default": ""}}, "desc_sha256_12": "0824c242abb8"},
  {"name": "search_paper_by_title", "required": ["title"], "params": {"title": {"type": "string"}, "fields": {"type": "string", "default": "title"}, "publication_date_range": {"type": "string", "default": ""}, "venues": {"type": "string", "default": ""}}, "desc_sha256_12": "48d612639aa8"},
  {"name": "snippet_search", "required": ["query"], "params": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 20}, "venues": {"type": "string", "default": ""}, "paper_ids": {"type": "string", "default": ""}, "inserted_before": {"type": "string", "default": ""}}, "desc_sha256_12": "89efc836cf5b"}
]
```

`desc_sha256_12` is the first 12 hex digits of the SHA-256 of that tool's description, so a
reworded description is attributable to one tool.

## Release checklist

1. Re-run the drift check; if the snapshot changed, complete the steps above first.
2. Bump `version` in the `SKILL.md` frontmatter (semver) and keep the asta entry in
   `.claude-plugin/marketplace.json` equal to it.
3. Refresh the `Behavior verified against:` line in `SKILL.md` when the server version changes.
4. Feature branch plus PR, then tag `vX.Y.Z` after the merge.
5. Update the repository About text or Topics only if the skill's capabilities changed.