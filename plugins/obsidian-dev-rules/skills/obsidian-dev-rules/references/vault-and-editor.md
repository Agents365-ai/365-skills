# Obsidian — Vault, Editor, Markdown Processing, Editor Extensions

Source: https://docs.obsidian.md/Plugins/Vault, /Plugins/Editor/{Editor,Markdown+post+processing}, editor extensions

## Vault API

A vault is "a folder, and any sub-folders within it." Access via `this.app.vault`.

### Reading

- `vault.cachedRead(file)` — for **display only** (no rewrite); reads from cache. Returns `Promise<string>`.
- `vault.read(file)` — when you'll **modify and write back**.
- Both reflect the latest content once the filesystem notifies Obsidian of a change.

### Listing / locating

- `vault.getMarkdownFiles()` — all `.md` `TFile`s.
- `vault.getFiles()` — all files.
- `vault.getFileByPath(path)` — a `TFile` or `null`.
- `vault.getFolderByPath(path)` — a `TFolder` or `null`.
- `vault.getAbstractFileByPath(path)` — a `TAbstractFile` (file or folder) or `null`.
- Always `normalizePath(userPath)` before lookups with user-supplied paths.

### Creating / modifying / deleting

- `vault.create(path, data)` — new file → `Promise<TFile>`.
- `vault.createFolder(path)`.
- `vault.modify(file, data)` — overwrite a file's contents.
- **`vault.process(file, (data) => newData)`** — atomic read-modify-write; "guarantees that the file
  doesn't change between reading and writing." **Prefer over sequential `read()`/`modify()`** to avoid
  data loss.
- `vault.append(file, data)`.
- `vault.rename(file, newPath)`, `vault.copy(file, newPath)`.
- `vault.delete(file)` — permanent; `vault.trash(file, system)` — to OS trash (`true`) or `.trash` (`false`).

### Type checks

```ts
import { TFile, TFolder } from 'obsidian';
if (fileOrFolder instanceof TFile)   { /* it's a file */ }
else if (fileOrFolder instanceof TFolder) { /* it's a folder */ }
```

### Adapter

`vault.adapter` is the low-level filesystem API — use it **only** for hidden files/folders
(e.g. inside `.obsidian`) that the Vault API doesn't see. Otherwise prefer the Vault API.

## Editor API

The `Editor` exposes the active Markdown document in edit mode. Get it via `editorCallback` in a
command, or `this.app.workspace.getActiveViewOfType(MarkdownView)?.editor`.

```ts
import { MarkdownView, moment } from 'obsidian';

// Insert today's date at the cursor
this.addCommand({
  id: 'insert-date', name: 'Insert date',
  editorCallback: (editor) => editor.replaceRange(moment().format('YYYY-MM-DD'), editor.getCursor()),
});

// Uppercase the selection
this.addCommand({
  id: 'uppercase', name: 'Uppercase selection',
  editorCallback: (editor) => editor.replaceSelection(editor.getSelection().toUpperCase()),
});
```

Common methods: `getValue()` / `setValue()`, `getSelection()` / `replaceSelection(text)`,
`getCursor()` / `setCursor(pos)`, `getLine(n)`, `lineCount()`, `getRange(from,to)`,
`replaceRange(text, from[, to])` (one position = insert), `getDoc()`. **For the active note, use the
Editor (preserves cursor/selection), not `Vault.modify`.**

## Markdown post-processing (Reading view)

Runs **after** Markdown → HTML. Register in `onload()`.

```ts
// Replace :emoji: inside the rendered output
this.registerMarkdownPostProcessor((element, context) => {
  // element: rendered DOM container; context: MarkdownPostProcessorContext
  // walk element, add/remove/replace nodes
});
```

### Code-block processor

Turn a fenced block of a custom language into rendered output:

````ts
// ```csv\n a,b\n 1,2\n ```  →  an HTML table
this.registerMarkdownCodeBlockProcessor('csv', (source, el, ctx) => {
  const rows = source.split('\n').filter(r => r.length);
  const table = el.createEl('table');
  for (const row of rows) {
    const tr = table.createEl('tr');
    for (const cell of row.split(',')) tr.createEl('td', { text: cell });
  }
});
````

Args: code-block processor gets `(source, el, ctx)`; post-processor gets `(element, context)`.
`ctx`/`context` is a `MarkdownPostProcessorContext` (sourcePath, frontmatter, `getSectionInfo(el)`,
`addChild(component)` for lifecycle-bound child components).

## Editor extensions (Live Preview / edit mode)

Obsidian's editor is **CodeMirror 6**. Extend it by registering CM6 extensions:

```ts
import { ViewPlugin } from '@codemirror/view';
// import { StateField, StateEffect } from '@codemirror/state';

this.registerEditorExtension([ /* CM6 extensions: ViewPlugin, StateField, decorations, ... */ ]);
```

Use these for decorations (widgets/marks in the live editor), state fields, and viewport-aware
rendering. Post-processors affect **Reading view**; editor extensions affect **edit/Live Preview**.
