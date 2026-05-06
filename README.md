# 365 Skills

Production-grade Claude Code skills by [Agents365-ai](https://github.com/Agents365-ai).

## Install

```bash
# Claude Code plugin marketplace
/plugin marketplace add Agents365-ai/365-skills
/plugin install drawio

# Any agent (Claude Code, Cursor, Copilot, etc.)
npx skills add Agents365-ai/365-skills -g
```

## Available plugins

| Plugin | Description |
|---|---|
| `drawio` | Draw.io diagrams — PNG/SVG/PDF export with visual review loop |
| _(more coming)_ | mermaid, excalidraw, plantuml, tldraw |

## Install a plugin

```
/plugin install drawio
```

## Development

Plugin skills are direct copies of the source repos (not submodules). To update a plugin:

```bash
cp -r ../drawio-skill/skills/drawio-skill/* plugins/drawio/skills/drawio-skill/
git add plugins/drawio && git commit -m "chore: sync drawio-skill"
```
