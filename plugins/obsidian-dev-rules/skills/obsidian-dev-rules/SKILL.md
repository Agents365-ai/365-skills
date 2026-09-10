---
name: obsidian-dev-rules
description: Authoritative reference and rules for developing for Obsidian — building TypeScript plugins (Plugin lifecycle, manifest.json, commands, settings, modals, views, ribbon/status bar), the Vault and Editor APIs, the event system, Markdown post-processing & code-block processors, CodeMirror 6 editor extensions, building CSS themes (CSS variables, theme.css/manifest), and submitting plugins/themes to the community directory. Use whenever the user asks to build, debug, or review an Obsidian plugin or theme, work with the Obsidian API (Vault/Editor/Workspace/Plugin), register commands/views/events, process Markdown, or release/submit to the Obsidian community.
license: MIT
metadata: {"source":"https://docs.obsidian.md/Home","docVersion":"latest","fetched":"2026-05-24"}
---

# Obsidian Dev Rules

Obsidian is extended two ways: **plugins** (TypeScript against the Obsidian API) and **themes/snippets**
(CSS). This skill mirrors the official developer docs at https://docs.obsidian.md so you can build and
review Obsidian plugins/themes without re-fetching. The API ships as the `obsidian` npm package; the
canonical starting point is the [`obsidian-sample-plugin`](https://github.com/obsidianmd/obsidian-sample-plugin).

## When to use this skill

- Building, debugging, or reviewing an **Obsidian plugin** (lifecycle, commands, settings, UI, views).
- Reading/writing notes via the **Vault** API; manipulating the active note via the **Editor** API.
- Subscribing to **events**, registering **Markdown post-processors** / code-block processors, or
  **CodeMirror 6** editor extensions.
- Building a **theme** (CSS variables, `theme.css`, manifest) or snippets.
- **Releasing/submitting** a plugin or theme to the community directory.

## Reference index — load the file you need

| File | Covers |
|------|--------|
| `references/plugin-basics.md` | Project setup, `manifest.json`, Plugin lifecycle (`onload`/`onunload`), resource registration & cleanup, events, dev workflow / hot reload, debugging |
| `references/vault-and-editor.md` | Vault API (read/cachedRead/create/modify/process/delete, TFile/TFolder, adapter, normalizePath), Editor API, Markdown post-processing & code-block processors, CodeMirror 6 editor extensions |
| `references/ui.md` | Commands (callback variants, hotkeys), Settings (PluginSettingTab, load/saveData, Setting controls), Modals (Modal/SuggestModal/FuzzySuggestModal), Views (ItemView, registerView, workspace leaves), ribbon/status bar |
| `references/themes-and-release.md` | Themes (CSS variables, theme.css/manifest, body classes, snippets), submitting plugins & themes, developer policies & guidelines |

## Cheat sheet

```ts
import { Plugin, Notice, MarkdownView, TFile, normalizePath } from 'obsidian';

export default class MyPlugin extends Plugin {
  async onload() {
    await this.loadSettings();
    this.addRibbonIcon('dice', 'Greet', () => new Notice('Hello!'));
    this.addCommand({ id: 'do-x', name: 'Do X', callback: () => {/* ... */} });
    this.addSettingTab(new MySettingTab(this.app, this));
    // Auto-cleaned on unload — always register through these:
    this.registerEvent(this.app.vault.on('modify', (f) => {/* ... */}));
    this.registerInterval(window.setInterval(() => {/* ... */}, 1000));
    this.registerDomEvent(document, 'click', () => {/* ... */});
  }
  onunload() { /* release anything NOT registered via register*/ }
}
```

```ts
// Vault: prefer process() over read()+modify(); use cachedRead() for display only.
const file = this.app.vault.getFileByPath('Notes/x.md');
await this.app.vault.process(file, (data) => data.replace('foo', 'bar'));
// Editor of the active note (preserves cursor/selection):
const view = this.app.workspace.getActiveViewOfType(MarkdownView);
view?.editor.replaceSelection(view.editor.getSelection().toUpperCase());
```

**Plugin files**: `manifest.json` + `main.js` (+ optional `styles.css`) in `<vault>/.obsidian/plugins/<id>/`.
**Theme files**: `manifest.json` + `theme.css` in `<vault>/.obsidian/themes/<name>/`.

## Hard rules

- **Use `this.app`, never the global `app`** (global exists for debugging only and may be removed).
- **Register everything that needs teardown** via `registerEvent` / `registerInterval` /
  `registerDomEvent` / `addCommand` / `registerView` / `registerMarkdownPostProcessor` — Obsidian
  auto-cleans those on unload. Manually release anything else in `onunload()`. Leaked listeners/
  intervals degrade Obsidian after the plugin is disabled.
- **Never** use `innerHTML` / `outerHTML` / `insertAdjacentHTML` with dynamic content — build DOM with
  `createEl()` / `createDiv()` / `createSpan()`.
- **Prefer the Vault API over the Adapter API**; use `getFileByPath()` (not iterate-all); always
  `normalizePath()` user-supplied paths. Use **`process()`** (atomic) instead of sequential
  `read()`+`modify()` to avoid data loss; `cachedRead()` only when you won't write it back.
- **For the active note, edit via the Editor interface**, not `Vault.modify` — it preserves the
  cursor and selection.
- **Don't store references to view instances**; Obsidian may recreate them — fetch with
  `getLeavesOfType()` / `getActiveViewOfType()`.
- **Don't set default hotkeys** for distributed plugins (OS-dependent, conflict-prone). UI text is
  **sentence case**. Use CSS classes + Obsidian CSS variables, not hardcoded inline styles.
- **`manifest.json` required fields**: `id`, `name`, `version` (semver `x.y.z`), `minAppVersion`,
  `description`, `author`, `isDesktopOnly`. `id` must **not** contain "obsidian"; `name` is Basic-Latin,
  no emoji/punctuation except hyphens.
- **Release**: GitHub release whose **tag equals the manifest `version`**, with `main.js`,
  `manifest.json`, and optional `styles.css` attached as **individual binary assets** (not zipped).
- Use `async`/`await` (not Promise chains); `const`/`let` (not `var`).
