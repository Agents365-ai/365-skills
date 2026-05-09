# 365 Skills

Production-grade Claude Code skills by [Agents365-ai](https://github.com/Agents365-ai).

## Install

```bash
# Claude Code plugin marketplace
/plugin marketplace add Agents365-ai/365-skills

# Any agent (Claude Code, Cursor, Copilot, etc.)
npx skills add Agents365-ai/365-skills -g
```

## Available plugins

| Plugin | Description |
|---|---|
| `drawio` | Draw.io diagrams — PNG/SVG/PDF export with visual review loop |
| `mermaid` | Mermaid diagrams — text-based, GitHub-native, auto-layout |
| `excalidraw` | Excalidraw — hand-drawn whiteboard style |
| `plantuml` | PlantUML — UML, C4, sequence, class diagrams |
| `tldraw` | Tldraw — infinite canvas, sketch-style |
| `semanticscholar` | Semantic Scholar — academic paper search, citation graph, recommendations, BibTeX export |

## Install plugins

```
/plugin install drawio mermaid excalidraw plantuml tldraw semanticscholar
```

## Development

Plugin skills are direct copies of the source repos (not submodules). To update a plugin:

```bash
cp -r ../drawio-skill/skills/drawio-skill/* plugins/drawio/skills/drawio-skill/
git add plugins/drawio && git commit -m "chore: sync drawio-skill"
```

### Auto-sync (semanticscholar)

`semanticscholar-skill` ships a GitHub Actions workflow (`.github/workflows/sync-365-skills.yml`) that automatically pushes any change under `skills/semanticscholar-skill/**` here, and bumps the version field in `marketplace.json`. Requires the source repo to have a `SYNC_365_SKILLS_TOKEN` secret with `Contents: write` on this repo.
