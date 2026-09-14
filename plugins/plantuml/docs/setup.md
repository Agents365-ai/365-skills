# Setup & Limitations

[← Back to README](https://github.com/Agents365-ai/365-skills/blob/main/plugins/plantuml/README.md)

## Rendering backends

### Option A — Kroki API (recommended, zero install)

```bash
# curl is pre-installed on macOS, Linux, and Windows (Git Bash / WSL)
curl --version
```

That's it. Diagrams render via `https://kroki.io`.

### Option B — Local Kroki via Docker (offline use)

```bash
docker run -d -p 8000:8000 yuzutech/kroki

# Then point the skill at the local endpoint
curl -s -X POST http://localhost:8000/plantuml/png \
  -H "Content-Type: text/plain" \
  --data-binary "@diagram.puml" \
  -o diagram.png
```

### Option C — Local PlantUML jar (air-gapped)

```bash
# macOS
brew install graphviz openjdk
# Ubuntu/Debian
sudo apt install graphviz default-jre

# Download plantuml.jar from https://plantuml.com/download
java -jar plantuml.jar diagram.puml
# → diagram.png is written next to the source
```

| Platform | Notes |
| ---------- | ------- |
| **macOS** | `curl` ships with the OS; Homebrew handles `graphviz` / `openjdk` for Option C |
| **Windows** | Use Git Bash or WSL so `curl` is available; install Java + Graphviz for Option C |
| **Linux** | `curl` ships with most distros; `apt`/`yum`/`pacman` install `graphviz` + `default-jre` |

## Known Limitations

- **Public Kroki rate limits**: The hosted `kroki.io` endpoint is shared and best-effort; for heavy workloads run your own Kroki container (Option B)
- **Network required by default**: Option A needs egress to `kroki.io`. Use Option B (local Docker) or Option C (jar) for offline / air-gapped environments
- **C4 `!include` directives**: The public PlantUML web server resolves `!include` URLs at render time; Kroki may not. Use Kroki's dedicated `c4plantuml` endpoint instead (`https://kroki.io/c4plantuml/png`)
- **Graphviz needed for some diagram types**: Activity and class diagrams use Graphviz internally — Option C requires `graphviz` to be installed alongside Java
- **No vision-based self-check**: Unlike `drawio-skill`, this skill does not read back the rendered PNG to auto-fix layout issues
