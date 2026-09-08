# Theme & Styling Presets

Drop the directive on the first line of the `.mmd`. Use a preset instead of inventing `classDef` tweaks ad hoc during review loops.

## Light (brand-neutral)

```text
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#eef2ff','primaryBorderColor':'#4f46e5','primaryTextColor':'#1e1b4b','lineColor':'#64748b','fontFamily':'Inter, sans-serif'}}}%%
```

## Dark

```text
%%{init: {'theme':'dark', 'themeVariables': {'fontFamily':'Inter, sans-serif'}}}%%
```

Export with `--backgroundColor dark` (or `#1e293b`) so the PNG blends into dark pages.

## Print / documentation

```text
%%{init: {'theme':'neutral'}}%%
```

Also available as `mmdc --theme neutral` (no directive needed). Best contrast for printed PDFs.

## Highlighting specific nodes (flowchart)

```text
classDef hot fill:#fee2e2,stroke:#dc2626,stroke-width:2px
classDef done fill:#dcfce7,stroke:#16a34a
class C,R hot
class D,Del done
```

Use `hot` for the path under discussion, `done` for settled states. Two classDefs max — more turns into noise.

## Gotchas

- `base` is only valid **inside** a `%%{init}%%` directive — `mmdc -t base` is rejected (valid `-t` values: `default | dark | neutral | forest`).
- The directive must be the first line; a blank line before it breaks parsing in some types.
