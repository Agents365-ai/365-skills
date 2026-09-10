# Obsidian Plugin UI — Commands, Settings, Modals, Views

Source: https://docs.obsidian.md/Plugins/User+interface/{Commands,Settings,Modals,Views}

## Commands

Register in `onload()` with `this.addCommand({ id, name, ... })`. `id` is unique within the plugin;
`name` shows in the Command Palette.

### Callback variants (use exactly one)

```ts
// 1. Always available
this.addCommand({ id: 'plain', name: 'Plain', callback: () => { /* run */ } });

// 2. Conditional — return true if available; when checking===false, perform the action
this.addCommand({ id: 'cond', name: 'Conditional', checkCallback: (checking) => {
  const ok = canRun();
  if (ok && !checking) doIt();
  return ok;
}});

// 3. Needs an active editor (only shown when one exists)
this.addCommand({ id: 'ed', name: 'Editor cmd', editorCallback: (editor, view) => { /* ... */ } });

// 4. Conditional + editor
this.addCommand({ id: 'edc', name: 'Editor cond', editorCheckCallback: (checking, editor, view) => {
  const ok = editor.somethingSelected();
  if (ok && !checking) act(editor);
  return ok;
}});
```

### Hotkeys

```ts
hotkeys: [{ modifiers: ['Mod', 'Shift'], key: 'a' }]
```

`'Mod'` = Cmd on macOS, Ctrl elsewhere. **Avoid shipping default hotkeys** in distributed plugins
(conflict-prone, OS-dependent); let users assign them.

## Settings

Persist with `this.loadData()` / `this.saveData()` (one JSON blob → `data.json`). Provide a settings
tab with `PluginSettingTab`.

```ts
interface MyPluginSettings { mySetting: string; }
const DEFAULT_SETTINGS: MyPluginSettings = { mySetting: 'default' };

export default class MyPlugin extends Plugin {
  settings: MyPluginSettings;
  async loadSettings() {
    // shallow-merge defaults under loaded values
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }
  async saveSettings() { await this.saveData(this.settings); }
  async onload() {
    await this.loadSettings();
    this.addSettingTab(new MySettingTab(this.app, this));
  }
}

import { App, PluginSettingTab, Setting } from 'obsidian';
class MySettingTab extends PluginSettingTab {
  plugin: MyPlugin;
  constructor(app: App, plugin: MyPlugin) { super(app, plugin); this.plugin = plugin; }
  display(): void {
    const { containerEl } = this;
    containerEl.empty();
    new Setting(containerEl)
      .setName('My setting')
      .setDesc('What it does')
      .addText(text => text
        .setPlaceholder('Enter value')
        .setValue(this.plugin.settings.mySetting)
        .onChange(async (value) => { this.plugin.settings.mySetting = value; await this.plugin.saveSettings(); }));
  }
}
```

> `Object.assign()` is a **shallow** copy — references to nested objects are shared. For nested
> settings, deep-merge/clone to avoid mutating `DEFAULT_SETTINGS`.

**Setting controls**: `addText`, `addTextArea`, `addToggle`, `addDropdown`, `addSlider`, `addSearch`,
`addButton`, `addExtraButton`, `addColorPicker`, `addProgressBar`, `addMomentFormat`.
Setting text uses **sentence case** ("Template folder location", not Title Case).

## Modals

```ts
import { App, Modal, Setting } from 'obsidian';

class InputModal extends Modal {
  result = '';
  constructor(app: App, public onSubmit: (r: string) => void) { super(app); }
  onOpen() {
    const { contentEl } = this;
    contentEl.createEl('h1', { text: 'Enter value' });
    new Setting(contentEl).setName('Name').addText(t => t.onChange(v => this.result = v));
    new Setting(contentEl).addButton(b => b.setButtonText('Submit').setCta()
      .onClick(() => { this.close(); this.onSubmit(this.result); }));
  }
  onClose() { this.contentEl.empty(); }
}
// new InputModal(this.app, (r) => new Notice(r)).open();
```

- **`SuggestModal<T>`**: implement `getSuggestions(query)`, `renderSuggestion(item, el)`,
  `onChooseSuggestion(item, evt)`.
- **`FuzzySuggestModal<T>`**: fuzzy search out of the box — implement `getItems()`, `getItemText(item)`,
  `onChooseItem(item, evt)`.

## Views (custom panes)

Extend `ItemView`; register the type in `onload()`; open it via a workspace leaf.

```ts
import { ItemView, WorkspaceLeaf } from 'obsidian';
export const VIEW_TYPE = 'my-view';

export class MyView extends ItemView {
  constructor(leaf: WorkspaceLeaf) { super(leaf); }
  getViewType() { return VIEW_TYPE; }
  getDisplayText() { return 'My view'; }
  getIcon() { return 'dice'; }
  async onOpen() { this.contentEl.createEl('h4', { text: 'Hello' }); }
  async onClose() { /* cleanup */ }
}
```

```ts
// in onload()
this.registerView(VIEW_TYPE, (leaf) => new MyView(leaf));
this.addRibbonIcon('dice', 'Open my view', () => this.activateView());

// activate without keeping a reference to the instance
async activateView() {
  const { workspace } = this.app;
  let leaf = workspace.getLeavesOfType(VIEW_TYPE)[0];
  if (!leaf) { leaf = workspace.getRightLeaf(false); await leaf.setViewState({ type: VIEW_TYPE, active: true }); }
  workspace.revealLeaf(leaf);
}
```

> **Don't store the view instance** — Obsidian may create it multiple times. Find it with
> `getLeavesOfType()` / `getActiveViewOfType()`. (Clean up in `onunload()` by detaching leaves if needed.)

## Ribbon & status bar

```ts
const ribbon = this.addRibbonIcon('dice', 'Tooltip', (evt) => new Notice('clicked'));
const status = this.addStatusBarItem();   // desktop only
status.setText('Ready');
```

Icons use Obsidian's built-in [Lucide](https://lucide.dev) set; register custom ones with `addIcon()`.
