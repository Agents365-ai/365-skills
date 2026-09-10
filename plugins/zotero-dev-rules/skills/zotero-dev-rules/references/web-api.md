# Zotero Web API v3

Source: <https://www.zotero.org/support/dev/web_api/v3/{basics,write_requests,file_upload,types_and_fields,syncing,streaming_api,oauth}>

Default & recommended API version. Client libraries exist for JavaScript, Python, PHP, TypeScript, Objective-C.

## Base URL & versioning

- Base: `https://api.zotero.org` — **HTTPS required**.
- Request a version via header `Zotero-API-Version: 3` (recommended for production) or query `v=3`
  (debugging / clients that can't set headers). Response echoes `Zotero-API-Version`.
- Always pin a version in production; the default can change over time.

## Authentication

- Public libraries: no auth.
- Private: an **API key**, supplied as:
  - `Zotero-API-Key: <key>` header (recommended), or
  - `Authorization: Bearer <key>`, or
  - `key=<key>` query param (**not recommended**).

## Library prefix

Every request targets a library: `/users/<userID>` or `/groups/<groupID>`.

## Read requests

**Collections**: `/collections`, `/collections/top`, `/collections/<key>`,
`/collections/<key>/collections` (subcollections), `/collections/<key>/items`.
**Items**: `/items`, `/items/top`, `/items/trash`, `/items/<key>`, `/items/<key>/children`,
`/collections/<key>/items`, `/collections/<key>/items/top`.
**Tags**: `/tags`, `/items/<key>/tags`, `/collections/<key>/tags`, `/tags/<url-encoded-tag>`.
**Searches** (saved-search metadata): `/searches`, `/searches/<key>`.

### Parameters

| Param | Purpose |
| ------- | --------- |
| `format` | `json` (default), `atom`, `bib`, `keys`, `versions`, or an export format (e.g. `bibtex`, `ris`, `csljson`) |
| `include` | for json: add `bib`, `citation`, and/or export formats |
| `style` | CSL style for `bib`/`citation` (e.g. `style=apa`) |
| `q`, `qmode` | quick search (titles+creators; `qmode=everything` for full-text) |
| `itemType` | filter by type; supports boolean ` | | ` (OR), `-` (NOT) |
| `tag` | filter by tag; repeatable for AND, ` | | ` for OR, `-` for NOT |
| `sort`, `direction` | order (`dateModified`, `dateAdded`, `title`, `creator`, …) + `asc`/`desc` |
| `limit`, `start` | pagination; `limit` 1–100 (default 25) |
| `since` | only objects modified after a given library version |
| `itemKey`, `collectionKey`, `tag` | restrict to specific keys |

### Response headers

- `Last-Modified-Version` — current library (multi-object) or object version; use for conditional requests.
- `Total-Results` — total matching objects.
- `Link` — pagination: `rel="first|prev|next|last"`.
- `Backoff` — seconds to voluntarily wait before more requests.

### Rate limiting

Two mechanisms: a `Backoff` header (slow down proactively) and a hard `429 Too Many Requests`. On
`429`, wait the `Retry-After` seconds and reduce frequency.

## Item types & fields

- `GET /itemTypes` — all types (machine + localized names).
- `GET /itemFields` — all valid fields with localized labels.
- `GET /itemTypeFields?itemType=book` — fields for a type.
- `GET /itemTypeCreatorTypes?itemType=book` — valid creator roles for a type.
- `GET /creatorFields` — creator field names (`firstName`, `lastName`, `name`).
- `GET /items/new?itemType=book` — a template object pre-populated with the type's fields
  (use this + `/itemTypes` when writing).
- Full schema (all locales) for batch download: `https://api.zotero.org/schema`.
- These endpoints accept `If-Modified-Since` and a `locale` parameter.

## Write requests

Require an API key with write access (`Zotero-API-Key`). JSON objects carry a `data` property with
editable fields.

- **Create**: `POST <prefix>/items` (or `/collections`) with a JSON **array** of objects. All
  properties except `itemType`, `tags`, `collections`, `relations` are optional.
- **Update — PUT** `<prefix>/items/<key>`: submit complete editable JSON; **omitted fields are cleared**.
- **Update — PATCH** `<prefix>/items/<key>`: only changed fields; others untouched.
- **Delete**: single `DELETE <prefix>/items/<key>`; batch up to 50 via `DELETE <prefix>/items?itemKey=k1,k2,...`.
- Collections support `parentCollection`; same create/PUT/delete patterns.

### Versioning (mandatory)

Each write must include version info: the `If-Unmodified-Since-Version: <libVersion>` header and/or
per-object `version`. New objects use `version: 0`.

| Code | Meaning |
| ------ | --------- |
| `200 OK` / `204 No Content` | success |
| `409 Conflict` | library locked |
| `412 Precondition Failed` | version mismatch — re-fetch, merge, retry |
| `428 Precondition Required` | missing version header |

### Batch response (≤50 objects)

JSON with three keyed groups:

- `successful` — created/modified objects with assigned keys.
- `unchanged` — submitted but unmodified.
- `failed` — per-object HTTP `code` + `message`.

### Write token

For unversioned requests, `Zotero-Write-Token: <random>` prevents duplicate processing (cached 12h).

## File upload (attachments)

Three-step flow:

1. **Authorize** — `POST <prefix>/items/<itemKey>/file` with `Content-Type: application/x-www-form-urlencoded`
   and fields `md5`, `filename`, `filesize`, `mtime` (**milliseconds**). Conditional header:
   - new attachment: `If-None-Match: *`
   - replacing: `If-Match: <previous-md5>` (from the item's `md5` or the download `ETag`).
   - Response: upload params `{ url, contentType, prefix, suffix, uploadKey }`, or `{ "exists": 1 }`.
2. **Upload to S3** — concatenate `prefix` + file bytes + `suffix` and `POST` to `url`.
3. **Register** — `POST <prefix>/items/<itemKey>/file` with `upload=<uploadKey>` and the same
   conditional header. On success the attachment's `filename`, `mtime`, `md5` update automatically.

**Partial upload (binary diff)**: `PATCH <prefix>/items/<itemKey>/file?algorithm={xdelta,vcdiff,bsdiff}&upload=<uploadKey>`.
Recommended: Xdelta v3 with `-9 -S djw`.

## Syncing (version-based)

Treat the library version as an **opaque, monotonically increasing** integer (not sequential). Four
mechanisms expose versions: `Last-Modified-Version` (response), `If-Modified-Since-Version` (request →
`304` if unchanged), `If-Unmodified-Since-Version` (required on writes), and `?since=<version>`.
`?format=versions` returns `{ "<key>": <version>, ... }` for **all** matches (no limit).

**Full-library sync**:

1. Verify key — `GET /keys/current`.
2. Group metadata — `GET /users/<userID>/groups?format=versions`.
3. Sync each library:
   - **i. Download updates** — `GET <prefix>/<collections|items|searches|tags>?since=<v>&format=versions`,
     diff against local, fetch changed in batches of ≤50. Store pristine JSON snapshots per version for
     automatic three-way merge. The client auto-resolves conflicts for everything except items
     (items prompt). Flag unsavable objects for backoff-retry; don't halt.
   - **ii. Download deletions** — `GET <prefix>/deleted?since=<v>` → keys of removed collections,
     searches, items, tags.
   - **iii. Detect concurrent changes** — if any `Last-Modified-Version` changed mid-download, restart.
   - **iv. Upload modifications** — with `If-Unmodified-Since-Version: <libVersion>`; `412` ⇒ restart.
   - **v. Upload deletions** — `DELETE` from local deletion log, clear on success.
4. On success set local `synced = true` and update object versions.

**Partial sync** options: fixed collection list (one library version), per-collection versions, or
single-object versions (no library-wide version).

## Streaming API (push notifications)

WebSocket at `wss://stream.zotero.org`. Delivers **notifications, not data** — on a notification,
run a normal sync to fetch changes. Best practice: connect first, then sync.

- On connect: `{"event":"connected","retry":10000}`.
- **Subscribe**: send a `createSubscriptions` action with API keys + topics (`/users/{id}` or
  `/groups/{id}`). No topics ⇒ auto-track all accessible libraries. Public topics need no key.
- **Events**: `topicUpdated` (data changed), `topicAdded` / `topicRemoved` (access changes during auto-track).
- **Unsubscribe**: `deleteSubscriptions`.

## OAuth (OAuth 1.0a — to mint API keys)

Register an app at `https://www.zotero.org/oauth/apps` to get a Client Key + Secret. Endpoints:

- Temporary credentials: `https://www.zotero.org/oauth/request`
- Authorize (user): `https://www.zotero.org/oauth/authorize`
- Access token: `https://www.zotero.org/oauth/access`

Three-step handshake: request temp token → redirect user to authorize → exchange for a permanent API
key. Response includes the API token and the user's ID.

Permission GET params on the authorize step: `name`, `library_access` (1/0), `notes_access` (1/0),
`write_access` (1/0), `all_groups` (`none|read|write`), `identity=1` (identity only, no key created).
