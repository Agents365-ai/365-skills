# Zotero Translators

Source: <https://www.zotero.org/support/dev/translators>, /translators/coding

Translators are JavaScript files that (a) save items from websites via the Connector and (b) import/
export metadata in standard formats. Zotero auto-detects applicable translators by matching URL
patterns and running detection functions. Repo: `github.com/zotero/translators` (fork + PR;
**licensed AGPL v3**).

## Translator types

- **web** — save items from websites.
- **import** — convert a standard format (BibTeX, RIS, JSON, RDF) into Zotero items.
- **export** — output library items to a standard format.
- **search** — retrieve metadata from an identifier (DOI, ISBN, PMID).

## File structure

Three parts: **metadata block** (JSON), **JavaScript functions**, **test cases** (appended JSON).

### Metadata block

```json
{
 "translatorID": "uuid-here",
 "label": "Example Journal",
 "creator": "Your Name",
 "target": "^https?://(www\\.)?example\\.com/",
 "minVersion": "5.0",
 "maxVersion": "",
 "priority": 100,
 "inRepository": true,
 "translatorType": 4,
 "browserSupport": "gcsibv",
 "lastUpdated": "2024-01-01 00:00:00"
}
```

- `translatorType` bitfield: import=1, export=2, web=4, search=8 (combine by adding).
- `target` — URL regex (web/search) or file-extension regex (import/export). Empty web `target`
  means a "every page" translator gated entirely by `detectWeb`.
- `priority` — lower wins when multiple translators match.
- `dataMode` (import) — `"rdf/xml"` or `"xml/dom"` for structured input.
- `configOptions` — e.g. `{ "getCollections": true }` to support collection export.
- `displayOptions` — export options surfaced in the UI (e.g. `{ "exportNotes": true }`).

## Functions by type

### Web

```javascript
function detectWeb(doc, url) {
  if (url.includes('/article/')) return 'journalArticle';
  if (getSearchResults(doc, true)) return 'multiple';   // search/list page
  return false;
}

async function doWeb(doc, url) {
  if (detectWeb(doc, url) === 'multiple') {
    let items = await Zotero.selectItems(getSearchResults(doc, false));
    if (!items) return;
    for (let u of Object.keys(items)) await scrape(await requestDocument(u));
  } else {
    await scrape(doc, url);
  }
}
```

`detectWeb` returns an item type, `"multiple"`, or `false`. `doWeb` is the entry point; modern form
`async function doWeb(doc, url = doc.location.href)`. `Zotero.selectItems(obj)` shows a picker for
multiples.

### Import

```javascript
function detectImport() {
  let line, str = "";
  while ((line = Zotero.read()) !== false) { str += line; if (str.length > 50) break; }
  return /^TY  - /m.test(str);          // sniff the format
}
async function doImport() {
  let text = Zotero.read(...);          // read input
  // parse → build items
  let item = new Zotero.Item('journalArticle');
  item.title = '...';
  await item.complete();
}
```

### Export

```javascript
function doExport() {
  let item;
  while ((item = Zotero.nextItem())) {
    Zotero.write(formatItem(item));     // write output
  }
  // if configOptions.getCollections: Zotero.nextCollection()
}
```

### Search

```javascript
function detectSearch(item) { return !!(item.DOI || item.ISBN); }
async function doSearch(item) {
  // look up by identifier, augment, then:
  let newItem = new Zotero.Item('journalArticle');
  // ...fill...
  await newItem.complete();
}
```

## Creating items

```javascript
let item = new Zotero.Item('journalArticle');
item.title = "Example Title";
item.creators.push(ZU.cleanAuthor("Smith, John", "author", true)); // hasComma=true
item.attachments.push({ url, mimeType: 'application/pdf', title: 'Full Text PDF', proxy: false });
item.notes.push({ note: 'content' });
await item.complete();              // save the item
```

## Scraping helpers (in web translators)

- `text(node, selector[, index])` — trimmed text of a matched element.
- `attr(node, selector, attrName[, index])` — an attribute value.
- `innerText(node, selector[, index])` — rendered text (CSS-display aware).
- `ZU.xpath(elements, xpath[, namespaces])` / `ZU.xpathText(...)` — XPath.
- `attachments`: array with `url`/`document`, `mimeType`, `title`, `snapshot`, `proxy` (set
  `proxy:false` for already-proxied PDFs). `notes`: array of `{ note }`.

## HTTP requests (promise-based)

`request(url, opts)`, `requestText(url, opts)`, `requestJSON(url, opts)`, `requestDocument(url, opts)`.
Opts: `method`, `headers`, `body`, `responseCharset`, `responseType`.

```javascript
let bibtex = await requestText(bibtexURL, { headers: { Referer: url } });
let json   = await requestJSON(apiURL);
let doc    = await requestDocument(pageURL);
```

## Utility functions (`Zotero.Utilities` / `ZU`)

`capitalizeTitle(title[, force])` · `cleanAuthor(str, creatorType[, hasComma])` ·
`trimInternal(text)` · `removeDiacritics(str[, lowercaseOnly])` · `xpath(...)` ·
`cleanDOI`, `cleanISBN`, `strToISO` (dates) · `Zotero.debug(text)` (debug log).

## Calling other translators

```javascript
let translator = Zotero.loadTranslator("import");
translator.setTranslator("32d59d2d-b65a-4da4-b0a3-bdd3cfb979e7");   // RIS
translator.setString(text);
translator.setHandler("itemDone", (_obj, item) => { /* tweak */ item.complete(); });
await translator.translate();
```

Methods: `setSearch()`, `setString()`, `setDocument()`, `setTranslator()`, `setHandler()`,
`getTranslators()`, `getTranslatorObject()`, `translate()`. Common embedded-metadata translator id:
`951c027d-74ac-47d4-a107-9c3069ab7b48` (Embedded Metadata).

## Testing — Scaffold

Scaffold is the built-in translator IDE (Tools → Developer). Create new web translators from the
"Web Translator" template, run `detectWeb`/`doWeb` against a live page, save test cases, and run the
regression suite. Use the browser inspector to find CSS selectors / XPath. Submit finished
translators as PRs to `zotero/translators`; CI runs the test cases.
