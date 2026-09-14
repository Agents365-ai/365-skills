# 渲染后端与已知限制

[← 返回 README](https://github.com/Agents365-ai/365-skills/blob/main/plugins/plantuml/README_CN.md)

## 渲染后端

### 方式 A — Kroki API(推荐,零安装)

```bash
# curl 已在 macOS、Linux、Windows(Git Bash / WSL)上预装
curl --version
```

仅此而已。图表通过 `https://kroki.io` 渲染。

### 方式 B — 本地 Kroki(Docker,离线使用)

```bash
docker run -d -p 8000:8000 yuzutech/kroki

# 然后将 skill 指向本地端点
curl -s -X POST http://localhost:8000/plantuml/png \
  -H "Content-Type: text/plain" \
  --data-binary "@diagram.puml" \
  -o diagram.png
```

### 方式 C — 本地 PlantUML jar(气隙环境)

```bash
# macOS
brew install graphviz openjdk
# Ubuntu/Debian
sudo apt install graphviz default-jre

# 从 https://plantuml.com/download 下载 plantuml.jar
java -jar plantuml.jar diagram.puml
# → diagram.png 会写入源文件同目录
```

| 平台 | 备注 |
| ------ | ------ |
| **macOS** | `curl` 系统自带;方式 C 用 Homebrew 安装 `graphviz` / `openjdk` |
| **Windows** | 用 Git Bash 或 WSL 以获得 `curl`;方式 C 需自行安装 Java 与 Graphviz |
| **Linux** | 大多发行版自带 `curl`;用 `apt` / `yum` / `pacman` 安装 `graphviz` 与 `default-jre` |

## 已知限制

- **公共 Kroki 限流**:`kroki.io` 是共享尽力而为服务;高负载场景请自建 Kroki 容器(方式 B)
- **默认需要联网**:方式 A 需要访问 `kroki.io`。离线 / 气隙环境请使用方式 B(本地 Docker)或方式 C(jar)
- **C4 `!include` 指令**:PlantUML 公共网站会在渲染时解析 `!include` URL,Kroki 可能不支持。请改用 Kroki 的专用 `c4plantuml` 端点(`https://kroki.io/c4plantuml/png`)
- **部分图表需要 Graphviz**:活动图、类图内部依赖 Graphviz — 方式 C 必须连同 Java 一起安装 `graphviz`
- **无视觉自检**:与 `drawio-skill` 不同,本 skill 不会回读渲染后的 PNG 自动修复布局问题
