---
name: zotero-dev-rules
description: Authoritative reference and rules for developing with Zotero — the Web API v3 (read/write requests, file upload, syncing, streaming, OAuth, item types & fields), the desktop client's internal JavaScript API, building Zotero plugins (7–10, incl. Zotero 10 migration notes), writing translators (web/import/export/search), and creating/editing CSL citation styles. Use whenever the user asks to query or write to a Zotero library via the API, build or debug a Zotero plugin, write a Zotero translator, work with citeproc-js / CSL styles, sync Zotero data programmatically, or script the Zotero client.
version: 0.4.1
license: CC BY-NC 4.0
homepage: https://github.com/Agents365-ai/365-skills
metadata: {"source":"https://www.zotero.org/support/dev","docVersion":"web_api_v3","fetched":"2026-08-19"}
---

# Zotero Dev Rules

Zotero is an open-source reference manager. Developers extend it three ways: the **Web API**
(`https://api.zotero.org`) for online libraries, **plugins / the internal JavaScript API** for the
desktop client, and **translators** (JS scrapers/converters). Citations come from **CSL** styles via
**citeproc-js**. This skill mirrors <https://www.zotero.org/support/dev> so you can answer Zotero dev
questions and build integrations without re-fetching.

## When to use this skill

- Reading from / writing to a Zotero library over the **Web API** (items, collections, tags, searches).
- File attachment upload, full-library or partial **syncing**, **streaming** (WebSocket) updates, **OAuth**.
- Building or debugging a **Zotero plugin** (7–10 bootstrapped era; Zotero 10 migration notes included); scripting the client via its **JavaScript API** / Run JavaScript.
- Finding an **existing open-source plugin** with similar functionality (to study its code) before building a new one.
- Writing or fixing a **translator** (web/import/export/search) and testing it in **Scaffold**.
- Creating or editing **CSL citation styles**; working with citeproc-js / citeproc-node.

## Reference index — load the file you need

| File | Covers |
| ------ | -------- |
| `references/web-api.md` | Base URL, auth/API keys, versioning, read requests, write requests, batch, file upload, item types/fields, syncing algorithm, streaming API, OAuth |
| `references/client-and-plugins.md` | Internal JavaScript API (Zotero.Items/Item/Search/DB/Notifier), Run JavaScript, plugin development (Zotero 7 bootstrap/manifest), Zotero 10 migration notes, client coding entry points |
| `references/translators.md` | Translator metadata block, detectWeb/doWeb/doImport/doExport/doSearch, scraping helpers (text/attr/ZU), HTTP requests, calling other translators, Scaffold/testing |
| `references/citation-styles.md` | CSL, citeproc-js / citeproc-node, style repository, style editing, type mapping |
| `references/plugin-gallery.md` | Snapshot of the zotero-chinese plugin-store registry (137 plugins by tag + deprecated list) — find similar open-source plugins and study their code before building |

## Cheat sheet — Web API

```bash
# Read (public library needs no key). HTTPS only. Always pin the version.
curl -H "Zotero-API-Version: 3" -H "Zotero-API-Key: <KEY>" \
  "https://api.zotero.org/users/<userID>/items?format=json&limit=25"

# Library prefix: /users/<userID> or /groups/<groupID>
# Common params: format=json|atom|bib|keys|versions, include=bib,citation, q=, itemType=, tag=,
#                sort=, direction=, limit=1..100 (def 25), start=, since=<version>
# Response headers: Last-Modified-Version, Total-Results, Link (rel=next/last), Backoff
# Rate limits: honor Backoff; on 429 wait per Retry-After.

# Write (key with write access). Up to 50 objects/request. Must carry a version.
curl -X POST -H "Zotero-API-Key: <KEY>" -H "Content-Type: application/json" \
  -H "If-Unmodified-Since-Version: <libVersion>" \
  -d '[{"itemType":"book","title":"..."}]' \
  "https://api.zotero.org/users/<userID>/items"
# PUT replaces (omitted fields cleared); PATCH merges (only changed fields). 412 = version mismatch.
```

```javascript
// Client internal JS API (Run JavaScript / plugin). Most DB/disk/network calls are async.
let item = new Zotero.Item('journalArticle');
item.setField('title', 'Example');
item.setCreators([{ creatorType: 'author', firstName: 'Jane', lastName: 'Doe' }]);
await item.saveTx();                               // async, own transaction
let items = ZoteroPane.getSelectedItems();         // window scope
```

**Key endpoints**: `/itemTypes` `/itemFields` `/itemTypeFields?itemType=` `/itemTypeCreatorTypes?itemType=`
`/creatorFields` `/items/new?itemType=` · full schema: `https://api.zotero.org/schema`.

## Hard rules

- **Always pin the API version** with `Zotero-API-Version: 3` (production) — never rely on the default.
  Pass keys via the `Zotero-API-Key` header (or `Authorization: Bearer`), **not** the `key=` query param.
- **Every write must carry a version** (`If-Unmodified-Since-Version` header or per-object `version`).
  Missing → `428`; mismatch → `412 Precondition Failed` (re-fetch, merge, retry). Batch max **50** objects.
- **Respect rate limits**: obey the `Backoff` header proactively; on `429` wait `Retry-After` and slow down.
- **`mtime` is in milliseconds**, not seconds. File upload is a 3-step flow (authorize → S3 → register);
  new attachment uses `If-None-Match: *`, replacement uses `If-Match: <previous-md5>`.
- **Client JS API is async**: `await` `saveTx()` / `getAsync()` / `Zotero.DB.executeTransaction(...)`.
  Use `saveTx()` for single saves; wrap batches in one transaction. Get the `Zotero` object via
  `chrome://zotero/content/include.js`.
- **Translators**: metadata block + functions + test cases; `detectWeb` returns a type / `"multiple"` /
  `false`; finish items with `item.complete()`. Use promise helpers (`requestText/JSON/Document`).
  Licensed AGPL v3; submit via PR to `zotero/translators`. Test in **Scaffold**.
- **Syncing is version-based**: treat the library version as an opaque monotonic integer; use
  `?format=versions` + `?since=` to diff, store pristine JSON snapshots for 3-way merge, restart the
  pass if `Last-Modified-Version` changes mid-sync. New local objects start at version `0`.
- **Citation styles use CSL + citeproc-js**; submit styles to the `citation-style-language/styles` repo
  per its CONTRIBUTING guidelines — don't hand-roll a citation formatter.
