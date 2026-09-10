# Zotero Citation Styles (CSL)

Source: <https://www.zotero.org/support/dev/citation_styles>, /citation_styles/style_editing_step-by-step, /citation_styles/citeproc-node

Zotero generates citations and bibliographies with **Citation Style Language (CSL)** styles processed
by the **citeproc-js** CSL processor. Don't hand-roll a citation formatter — author/edit a CSL style.

## Resources

- Style repository (browse/search/install): `https://www.zotero.org/styles` (`/support/styles`).
- CSL specification & docs: `https://citationstyles.org/`.
- CSL styles repo (submit here): `https://github.com/citation-style-language/styles` — follow its
  `CONTRIBUTING.md`.
- Zotero → CSL type/field mapping: `https://aurimasv.github.io/z2csl/typeMap.xml`.
- citeproc-js (the processor): upstream at `github.com/Juris-M/citeproc-js`.
- citeproc-node (server-side rendering): `/support/dev/citation_styles/citeproc-node`.

## CSL basics

A CSL style is an XML file with:

- `<info>` — metadata: title, id (a URI), links, author, category (`citation-format`, `field`), updated.
- `<citation>` — in-text / footnote citation layout, sorting, disambiguation.
- `<bibliography>` — bibliography entry layout and sorting.
- `<macro>` — reusable rendering blocks referenced by citation/bibliography.
- `<locale>` — terms and date formats (or rely on shared locale files).

**Dependent styles** are tiny files that point at an `independent-parent` style via a `link` with
`rel="independent-parent"` — use these for journals that share another style's rules.

## Editing styles

- Step-by-step guide: `/support/dev/citation_styles/style_editing_step-by-step`.
- Visual editor / live preview: the CSL Editor at `https://editor.citationstyles.org/` (Visual editor +
  Code editor with a sample bibliography preview).
- Validate against the CSL schema before submitting; match an existing similar style and diff.
- Test in Zotero by dropping the `.csl` into the styles directory (Preferences → Cite → Styles →
  add) and previewing with real items.

## Using styles via the Web API

Render bibliographies/citations server-side without a local processor:

```
GET /users/<id>/items?format=bib&style=apa
GET /users/<id>/items?include=citation,bib&style=chicago-note-bibliography&linkwrap=1
```

`style` accepts any style id from the repository (default APA if omitted). `format=bib` returns a
formatted bibliography; `include=citation` adds in-text citations to JSON.

## Submitting a style

1. Confirm no existing style fits (search the repo and the Zotero style search).
2. Base it on the closest existing independent style; keep `<info><id>` a unique URI.
3. Validate; update `<updated>` timestamp.
4. Open a PR to `citation-style-language/styles` per CONTRIBUTING (one style per PR, follow naming
   conventions). For journal variants, prefer a dependent style.
