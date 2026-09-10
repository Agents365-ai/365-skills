# Zotero Client — Internal JavaScript API & Plugin Development

Source: <https://www.zotero.org/support/dev/client_coding>, /client_coding/javascript_api, /client_coding/plugin_development

## Client coding entry points

- Source code: `/support/dev/source_code` · repo `github.com/zotero/zotero`.
- Building the desktop app: `/support/dev/client_coding/building_the_desktop_app`.
- Coding guidelines: `/support/dev/client_coding/coding_guidelines`.
- Internal JavaScript API: `/support/dev/client_coding/javascript_api`.
- Direct SQLite database access: `/support/dev/client_coding/direct_sqlite_database_access`
  (read-only, client closed; for ad hoc inspection — the JS API is preferred).
- Connector HTTP server: `/support/dev/client_coding/connector_http_server`.
- HTTP citing protocol: `/support/dev/client_coding/http_integration_protocol`.
- LibreOffice plugin wire protocol: `/support/dev/client_coding/libreoffice_plugin_wire_protocol`.
- Word processor integration APIs: separate GitHub repos (LibreOffice, Word Windows, Word Mac).

## Internal JavaScript API

Two scopes: **window scope** (UI-aware code; `ZoteroPane`, DOM access in main/secondary windows) and
**non-window scope** (DB layer, no DOM). Get the core object by importing
`chrome://zotero/content/include.js` → the `Zotero` object. `ZoteroPane` handles UI.

> Most functions that touch the database, disk, or network are **asynchronous** — use `await`. The
> Run JavaScript runner auto-wraps code containing `await` in an async function.

### Items

```javascript
// Create / modify
let item = new Zotero.Item('book');
item.setField('title', 'The Title');
item.setCreators([{ creatorType: 'author', firstName: 'Jane', lastName: 'Doe' }]);
let itemID = await item.saveTx();          // async, runs its own transaction
// Retrieve
let item2 = await Zotero.Items.getAsync(itemID);
let selected = ZoteroPane.getSelectedItems();   // window scope
// Modify existing
item2.setField('date', '2024');
await item2.saveTx();
```

`Zotero.Items.get(id)` (sync, must be loaded) / `Zotero.Items.getAsync(ids)` (async, loads).
`saveTx()` = async save in its own transaction; `save()` requires an explicit surrounding transaction.

### Batch writes — one transaction

```javascript
await Zotero.DB.executeTransaction(async function () {
  for (let it of items) {
    it.setField('extra', 'tagged');
    await it.save();          // save() inside an explicit transaction
  }
});
```

### Search

```javascript
let s = new Zotero.Search();
s.libraryID = Zotero.Libraries.userLibraryID;
s.addCondition('tag', 'is', 'tagname');
s.addCondition('creator', 'contains', 'Smith');
// s.addCondition('collectionID', 'is', collectionID);
let itemIDs = await s.search();
let results = await Zotero.Items.getAsync(itemIDs);
```

### Collections / libraries

`Zotero.Collections.get(id)` / `.getByLibrary(libraryID)`; `new Zotero.Collection()`, `setName()`,
`saveTx()`. `Zotero.Libraries.userLibraryID`, group libraries via `Zotero.Groups`.

### Notifier (events)

```javascript
let notifierID = Zotero.Notifier.registerObserver({
  notify(event, type, ids, extraData) { /* ... */ }
}, ['item', 'collection']);   // unregister with Zotero.Notifier.unregisterObserver(notifierID)
```

Events: `add`, `modify`, `delete`, `remove`, `move`. Type codes in raw data: collections `c`,
searches `s`, items `i`, tags `t`, associations `ci`, `it`.

### Common helpers

- Bibliography: `Zotero.QuickCopy.getContentFromItems(items, format)`.
- Attachments: `item.getAttachments()` → IDs; `attachment.attachmentText`; `attachment.getFilePathAsync()`.
- Files: `Zotero.File.getContentsAsync(path)`, `Zotero.File.putContentsAsync(path, data)`.

The API is "under-documented" — for advanced use, read the source under `chrome/content/zotero/xpcom/`.

## Running ad hoc JavaScript

Tools → Developer → **Run JavaScript** runs code with the `Zotero` and `ZoteroPane` objects in scope
and auto-async wrapping. Good for one-off batch edits and prototyping plugin logic.

## Plugin development (Zotero 7)

> The official docs page is a work-in-progress; the **canonical starting point is the
> [`make-it-red`](https://github.com/zotero/make-it-red) sample plugin** (step-by-step, Zotero 7 era).
> Browse existing third-party plugins at `/support/plugins`.

### Bootstrapped plugins

Zotero 7 plugins are **bootstrapped** (no restart): a `manifest.json` plus a `bootstrap.js` exposing
lifecycle functions. (Legacy overlay/`install.rdf` plugins are deprecated.)

```javascript
// bootstrap.js — called by Zotero
function install(data, reason) {}
async function startup({ id, version, rootURI }, reason) {
  // register UI, load chrome, add menu items, Zotero.PreferencePanes.register(...), etc.
}
function shutdown({ id, version, rootURI }, reason) {
  // remove everything added in startup; clean up
}
function uninstall(data, reason) {}
```

`manifest.json` carries the plugin id (`browser_specific_settings.gecko.id`), version, name, and
`applications.zotero.{strict_min_version,strict_max_version}`.

### Local dev setup

1. In the Zotero profile's `extensions/` dir, create a file **named after the plugin id** whose
   contents are the absolute path to the plugin source root (a "proxy file").
2. In the profile's `prefs.js`, remove `extensions.lastAppBuildId` and `extensions.lastAppVersion`.
3. Launch Zotero with `-purgecaches` when changing code (may be unnecessary in Zotero 7).
4. Use the Run JavaScript / Error Console + `Zotero.debug()` for debugging.

### Available APIs

Plugins can call Zotero's internal JS API (above), internal Firefox/Gecko APIs, and the word-processor
integration APIs. Full JS API reference: `/support/dev/client_coding/javascript_api`.

## Zotero 10 — plugin migration (2026-08-17)

Source: <https://www.zotero.org/support/dev/zotero_10_for_developers> · Same Firefox 140 ESR base
as Zotero 9 — no Mozilla platform changes.

### Compatibility bump

- Set `applications.zotero.strict_max_version` to `10.0.*` in `manifest.json`. If no code changes
  are needed, bumping it in the plugin's **update manifest** alone is enough — no new release.
- Beta/source builds no longer enforce `strict_max_version` (install or update); stable builds do.

### Collections pane: multi-row selection

Singular getters **throw** — the error message names the replacement:

| Removed | Replacement |
| ------ | -------- |
| `ZoteroPane.getCollectionTreeRow()` | `ZoteroPane.getCollectionTreeRows()` |
| `ZoteroPane.getSelectedLibraryID()` | `ZoteroPane.getSelectedLibraryIDs()` |
| `ZoteroPane.getSelectedCollection()` | `ZoteroPane.getSelectedCollections()` |
| `ZoteroPane.getSelectedSavedSearch()` | `ZoteroPane.getSelectedSavedSearches()` |
| `ZoteroPane.getSelectedGroup()` | filter `getCollectionTreeRows()` by `isGroup()` |
| `CollectionTree#getSelectedLibraryID()` | `CollectionTree#getSelectedLibraryIDs()` |
| `CollectionTree#getSelectedCollection()` | `CollectionTree#getSelectedCollections()` |
| `CollectionTree#getSelectedSearch()` | `CollectionTree#getSelectedSearches()` |
| `CollectionTree#getSelectedGroup()` | filter `CollectionTree#getSelectedRows()` by `isGroup()` |

Plural getters return arrays and are safe with any selection; collections and saved searches can be
selected together. `ItemTree#collectionTreeRow` is gone — use `ZoteroPane.itemsView.viewMode`
(`'default'`, `'trash'`, `'duplicates'`, `'unfiled'`, `'feed'`); actual rows via
`itemsView.collectionTreeRows`. With multiple rows selected the items list gains **library header
and spacer rows** — check `row.isObjectRow` when walking `getRow()`/`_rows` (`getSortedItems()`
already filters them). In `Zotero.MenuManager` main/library/collection and main/library/item
contexts, reading `collectionTreeRow` throws — use `collectionTreeRows`.

### Search API

- Complex logic via **condition groups**: wrap conditions in `groupStart`/`groupEnd` with a
  `joinMode`; `resultLevel` sets what the search returns (`item`, `attachment`, `note`,
  `annotation`) or, within a group, the level its conditions match at.
- `Zotero.Search#addCondition()` throws if the legacy `required` parameter is truthy — use a group.
- The `fulltextWord` condition was **removed** — use `fulltextContent` (now backed by a real FTS
  index, fast enough for general use). `childNote` is deprecated; saved searches auto-migrate to
  `note` with `resultLevel: item`.
- New conditions (annotation properties, item/tag counts) and `isEmpty`/`isNotEmpty` operators.
- Advanced Search moved into the main window — `chrome://zotero/content/advancedSearch.xhtml` is gone.

### Full-text index → SQLite FTS5

`fulltextWords` and `fulltextItemWords` were **dropped from zotero.sqlite**; content and note
indexes live in a **separate database attached as `ftindex`**. Various `Zotero.FullText` methods
were removed or replaced. External tools reading the old tables directly must migrate.

### Undo/redo

Pass an action label to make plugin changes undoable:

```javascript
await item.saveTx({
  undoAction: 'undo-action-edit-metadata',       // Fluent message ID
  undoActionArgs: { count: 1 },                  // only if the message takes variables
});
// Multiple objects in one transaction: Zotero.UndoHistory.stageAction(action, args) inside it —
// each save records its changes, stageAction() labels the commit as one undo step.
```

Plugin FTL strings can be added to Zotero's bundle with `Zotero.ftl.addResourceIds([...])` (remove
with `removeResourceIds()` on shutdown).

### Local HTTP server + local API (port 23119)

- **Host allowlist**: requests must send `Host: localhost`, `127.0.0.1`, or `[::1]` — else 400.
- **Browser-like requests dropped**: UA starting `Mozilla/` or any `Origin` header → dropped unless
  the request sends a `Zotero-Allowed-Request` header (or comes from the connector). This now
  applies to all content types — a JSON POST that worked before may now be rejected. Custom
  endpoints can opt out with `allowRequestsFromUnsafeWebContent = true`.
- **Local API (`/api/`) now supports writes.** Every response carries a `Zotero-Server-ID` header
  (stable per instance) — cache it and send it back as a request header: optional on reads,
  **required on writes**. If the ID changes, discard/reconcile cached data; object versions are
  per-instance and unrelated to web-API versions.
- Version fields in local API responses (`format=versions`, `since=`, `Last-Modified-Version`) now
  report a **local version**, not the synced version (which was 0 for unsynced objects).

### Item data validation

- `item.setType()` / `item.setField('itemTypeID')` throw when converting a regular item to/from an
  attachment, note, or annotation.
- `attachmentFilename`/`attachmentPath` setters throw if a stored-file path contains a slash —
  after the `storage:` prefix it must be a bare filename (a schema update strips legacy full paths).

### Database

- **WAL mode enabled.** External tools reading `zotero.sqlite` directly (discouraged — use the
  local API) must account for `-wal`/`-shm`: copying the main file alone yields a stale snapshot,
  and `immutable=1` reads skip the WAL.
- Accent-normalized shadow columns added (e.g. `nameNormalized` on tags) for accent-insensitive search.
- New APIs for plugin-owned databases: `Zotero.DB.loadExtension()` (bundled SQLite ext, e.g. FTS5),
  `Zotero.DB.onIdle()`, `Zotero.DB.addCorruptionHandler()`.

### Items list refactor

`ItemTree` split into `ItemTree` (virtualized table/columns), `ItemTreeRow` subclasses (row
data/rendering), and `CollectionViewItemTree` (rows for a collection-tree selection).
`ZoteroPane.itemsView` is a `CollectionViewItemTree`; common methods (`getSelectedItems()`,
`selectItems()`, `getSortedItems()`, `refresh()`) are unchanged, but some moved from `ItemTree` to
`CollectionViewItemTree` (e.g. `deleteSelection()`, `changeCollectionTreeRow()`) — check the class
you instantiate.

### Cookie management

`Zotero.CookieSandbox` is gone. Use `Zotero.HTTP.newCookieContext()` (isolated jar via a Mozilla
`userContextId`) and `dispose()` when done:

```javascript
let cookieContext = Zotero.HTTP.newCookieContext();
await Zotero.HTTP.request('GET', url, { userContextId: cookieContext.id });
let cookies = cookieContext.getCookies('example.com');
cookieContext.dispose();
```

`translate.setCookieSandbox()` still exists but now takes the context's numeric ID.
`Zotero.Utilities.Internal.getFileFromDocument()` and `saveURI()` no longer accept a `cookieSandbox`
parameter, and `Zotero.HTTP.doGet()`'s fourth argument is ignored.

### Other changes

- Plugin FTL registration reworked: one consolidated localization source with per-locale fallback
  (same language → en-US → first available) — fixes plugins shipping only a non-English locale
  showing that locale for all users, and competing registrations breaking string resolution.
- `Zotero.HTTP.download()` rewritten — streams via `fetch()`, returns a `Response`.
- Plugin `prefs.js` loads with the script cache disabled — default-pref changes apply on update,
  no restart.
- `Zotero.MenuManager` now removes a plugin's menu DOM on shutdown.
