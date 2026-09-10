# Obsidian Plugin Basics — Setup, Manifest, Lifecycle, Events

Source: https://docs.obsidian.md/Plugins/Getting+started/{Build+a+plugin,Anatomy+of+a+plugin}, /Reference/Manifest, /Plugins/Events

## Prerequisites & setup

- Git, a Node.js dev environment, a code editor (VS Code recommended).
- **Use a separate vault for development**, never your main vault.
- Sample: `https://github.com/obsidianmd/obsidian-sample-plugin` (GitHub template).

```bash
cd path/to/vault
mkdir -p .obsidian/plugins
cd .obsidian/plugins
git clone https://github.com/obsidianmd/obsidian-sample-plugin.git
cd obsidian-sample-plugin
npm install
npm run dev        # watches source, rebuilds main.js on change (esbuild)
```

Enable it: Settings → Community plugins → turn on community plugins → toggle your plugin on.

### Reloading after changes

- **Source changes**: Command palette → "Reload app without saving", or toggle the plugin off/on.
- **manifest.json changes**: restart Obsidian fully.
- **Convenience**: install the community **Hot-Reload** plugin for auto-reload during dev.
- **Debug**: open DevTools — `Ctrl+Shift+I` (Win/Linux) / `Cmd+Option+I` (macOS) → Console.

## manifest.json

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `id` | Yes | string | unique; **must not contain "obsidian"** |
| `name` | Yes | string | Basic Latin only; no punctuation except hyphens; no emoji |
| `version` | Yes | string | **semver** `x.y.z` |
| `minAppVersion` | Yes | string | minimum Obsidian version |
| `description` | Yes | string | |
| `author` | Yes | string | |
| `authorUrl` | No | string | |
| `fundingUrl` | No | string \| object | single URL, or `{ "Label": "url", ... }` |
| `isDesktopOnly` | Yes | boolean | `true` if it uses Node/Electron-only APIs |

```json
{
  "id": "my-plugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "minAppVersion": "1.0.0",
  "description": "A helpful plugin for note-taking",
  "author": "Jane Doe",
  "authorUrl": "https://example.com",
  "fundingUrl": { "Buy Me a Coffee": "https://buymeacoffee.com", "GitHub Sponsor": "https://github.com/sponsors" },
  "isDesktopOnly": false
}
```

Files that ship in `<vault>/.obsidian/plugins/<id>/`: `manifest.json`, `main.js`, optional `styles.css`.

## The Plugin class & lifecycle

The base `Plugin` class "defines the lifecycle of a plugin and exposes the operations available to all plugins."

```ts
import { Plugin } from 'obsidian';

export default class ExamplePlugin extends Plugin {
  async onload() {
    // Runs when the user enables the plugin. Set up commands, UI, events, settings.
  }
  async onunload() {
    // Runs on disable. Release anything NOT auto-registered (see below).
  }
}
```

**Cleanup is mandatory**: "any resources that your plugin is using must be released here to avoid
affecting the performance of Obsidian after your plugin has been disabled."

### Auto-cleaned registration helpers

Prefer these — Obsidian detaches them automatically on unload, so you usually don't touch `onunload()`:

- `this.addCommand(...)` — command palette entries.
- `this.addRibbonIcon(icon, title, cb)` — left-ribbon button.
- `this.addStatusBarItem()` — returns an element (desktop only).
- `this.addSettingTab(tab)` — settings UI.
- `this.registerEvent(ref)` — any Obsidian `EventRef` (vault/workspace/metadataCache).
- `this.registerDomEvent(el, type, cb)` — DOM listener.
- `this.registerInterval(window.setInterval(...))` — timers.
- `this.registerView(type, factory)` — custom views.
- `this.registerMarkdownPostProcessor(...)` / `registerMarkdownCodeBlockProcessor(...)`.
- `this.registerEditorExtension([...])` — CodeMirror 6 extensions.

## Events

> "Any registered event handlers need to be detached whenever the plugin unloads." Always wrap in
> `registerEvent()` so cleanup is automatic.

```ts
this.registerEvent(this.app.vault.on('create', (file) => {
  console.log('a new file has entered the arena');
}));

// status bar updated every second; registerInterval ensures the timer is cleared on unload
this.registerInterval(window.setInterval(() => this.updateStatusBar(), 1000));
```

**Vault events**: `create`, `modify`, `delete`, `rename`.
**Workspace events**: `file-open`, `active-leaf-change`, `layout-change`, `quit`, etc.
**MetadataCache events**: `changed`, `resolved`.

Moment.js is bundled: `import { moment } from 'obsidian';`.
