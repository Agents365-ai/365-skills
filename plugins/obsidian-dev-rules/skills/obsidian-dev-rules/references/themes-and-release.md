# Obsidian — Themes, Snippets, Releasing & Guidelines

Source: https://docs.obsidian.md/Themes/App+themes/Build+a+theme, /Plugins/Releasing/{Submit+your+plugin,Plugin+guidelines}

## Themes

A theme is CSS that restyles Obsidian via its CSS custom properties. Obsidian exposes **400+ CSS
variables**. Files live in `<vault>/.obsidian/themes/<name>/`.

### Files

- `manifest.json` — theme metadata (`name`, `version`, `minAppVersion`, `author`, `authorUrl`).
  **The theme folder name must match the `name` exactly.** Restart Obsidian after edits.
- `theme.css` — the stylesheet (CSS custom properties + rules).

Sample: clone the official sample theme into `.obsidian/themes/`, then Settings → Appearance →
Themes → select it.

### Selectors

- `body` — variables shared by **both** light and dark.
- `:root` — variables available to all descendants.
- `.theme-dark` / `.theme-light` — color-scheme-specific overrides (Obsidian sets one on `body`).

```css
body { --font-text-theme: Georgia, serif; }
.theme-dark  { --background-primary: #18004F; --background-secondary: #220070; }
.theme-light { --background-primary: #ECE4FF; --background-secondary: #D9C9FF; }
:root { --input-hover-border-color: red; }
```

### Discovering variables

DevTools (`Ctrl/Cmd+Shift+I`) → Sources → `app.css` (search variable names), or use the element
inspector to find which variable styles a given UI element. Full list: the docs' "CSS variables" pages.

### Snippets

CSS snippets are single `.css` files in `<vault>/.obsidian/snippets/`, toggled in Settings →
Appearance → CSS snippets — same variable/selector model, for small tweaks without a full theme.

## Submitting a plugin

**Repo root must contain**: `README.md` (purpose + usage), `LICENSE` (pick at choosealicense.com),
`manifest.json`. Confirm compliance with the Developer Policies and Submission Requirements.

**Release steps**:
1. Bump `manifest.json` `version` (semver `x.y.z`).
2. Create a **GitHub release whose tag exactly equals that version** (no `v` prefix mismatch).
3. Attach as **individual binary assets**: `main.js`, `manifest.json`, and (optional) `styles.css`
   — not a zip.
4. At `community.obsidian.md`: sign in with your Obsidian account, link GitHub to verify ownership,
   Plugins → New plugin → enter the repo URL, accept policies, submit. (Under the hood this opens a PR
   adding your entry to `community-plugins.json` in the `obsidianmd/obsidian-releases` repo.)

The system reads `manifest.json` from your default branch and downloads release assets matching that
version. An **automated review** flags required fixes — address them, publish an incremented release,
and the bot re-checks. Themes submit the same way (Themes → New theme), shipping `manifest.json` +
`theme.css`.

## Developer policies & guidelines (review checklist)

- **Use `this.app`, not the global `app`** (debug-only, may be removed).
- **Release every resource on unload.** Use `registerEvent()`, `addCommand()`, `registerInterval()`,
  `registerDomEvent()`, `registerView()` so cleanup is automatic; manually clean anything else.
- **Security**: never `innerHTML` / `outerHTML` / `insertAdjacentHTML` with dynamic input — build DOM
  with `createEl()` / `createDiv()` / `createSpan()`.
- **Files**: prefer the **Vault API** over the Adapter API; locate with `getFileByPath()` instead of
  iterating all files; `normalizePath()` user paths. Use **`Vault.process()`** for atomic edits.
- **Active note**: edit via the **Editor** interface (preserves cursor/selection), not `Vault.modify`.
- **UI**: sentence case for all text; CSS classes + Obsidian CSS variables, **no hardcoded inline
  styles**; **don't set default hotkeys**.
- **Workspace/views**: use `getActiveViewOfType()` rather than `workspace.activeLeaf`; don't store
  view references — fetch with `getLeavesOfType()` / `getActiveLeavesOfType()`.
- **Mobile**: set `isDesktopOnly` correctly; avoid Node/Electron APIs unless desktop-only; avoid
  lookbehind regex on older platforms.
- **Code quality**: `const`/`let` over `var`; `async`/`await` over Promise chains.
