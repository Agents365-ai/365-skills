#!/usr/bin/env python3
"""Build docs/providers.html and docs/providers.md from data/providers.json."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent.parent  # ttsCN repo root
DATA_FILE = ROOT / "data" / "providers.json"
DOCS_DIR = ROOT / "docs"
HTML_OUT = DOCS_DIR / "providers.html"
MD_OUT = DOCS_DIR / "providers.md"
# GitHub Pages output at repo root docs/
PAGES_DIR = REPO_ROOT / "docs"
PAGES_HTML = PAGES_DIR / "index.html"
PAGES_MD = PAGES_DIR / "providers.md"


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════════════════
# HTML Builder
# ═══════════════════════════════════════════════════════════════════════════

def _bool_icon(val):
    return '<span class="yes">✅</span>' if val else '<span class="no">❌</span>'


def _tag_badge(tag_id, tags_meta):
    t = tags_meta.get(tag_id, {})
    label = t.get("label", tag_id)
    icon = t.get("icon", "")
    color = t.get("color", "#888")
    return f'<span class="tag" style="--tag-color:{color}">{icon} {label}</span>'


def _voice_cards(voices):
    cards = ""
    for v in voices:
        cards += f"""
        <div class="voice-card">
          <code class="voice-id">{v['id']}</code>
          <span class="voice-label">{v.get('label', '')}</span>
          <span class="voice-style">{v.get('style', '')}</span>
          <span class="voice-best">{v.get('best_for', '')}</span>
        </div>"""
    return cards


def build_html(data):
    """Generate providers.html from JSON data."""
    backends = data["backends"]
    tags_meta = data.get("tags", {})
    updated = data.get("updated", "")

    rows = ""
    detail_sections = ""
    for i, p in enumerate(backends):
        bid = p["id"]
        tags_html = " ".join(_tag_badge(t, tags_meta) for t in p.get("tags", []))
        clone_str = p["clone_detail"] if p["supports_clone"] else "—"
        ssml_icon = _bool_icon(p["supports_ssml"])
        clone_icon = _bool_icon(p["supports_clone"])
        cost_class = "free" if p.get("cost_tier") == "free" else ""

        difficulty_emoji = {"zero": "⚡", "easy": "🟢", "medium": "🟡", "hard": "🔴"}
        diff_emoji = difficulty_emoji.get(p.get("setup_difficulty", "medium"), "🟡")

        rows += f"""
        <tr class="provider-row" id="row-{bid}">
          <td class="col-name">
            <a href="#detail-{bid}" class="provider-link">
              <strong>{p['name']}</strong>
              <small>{p['provider']}</small>
            </a>
          </td>
          <td class="col-cost {cost_class}">{p['cost']}</td>
          <td class="col-voices">{p['voices_count']}</td>
          <td class="col-chars">{p['max_chars']}<small> 字/次</small></td>
          <td class="col-duration">{p['max_duration_display']}<small> /次</small></td>
          <td class="col-ssml">{ssml_icon}</td>
          <td class="col-clone">{clone_icon}</td>
          <td class="col-emoji">{p.get('supports_emotion','—')}</td>
          <td class="col-lang">{p['languages']}</td>
          <td class="col-streaming">{p['streaming']}</td>
          <td class="col-setup">{diff_emoji} {p.get('setup_label','')}</td>
        </tr>"""

        detail_sections += f"""
      <section class="detail-panel" id="detail-{bid}">
        <div class="detail-header">
          <h2>{p['name']}</h2>
          <span class="provider-name">{p['provider']}</span>
          <div class="detail-tags">{tags_html}</div>
        </div>
        <div class="detail-grid">
          <div class="detail-item"><label>费用</label><span class="cost-badge {cost_class}">{p['cost']}</span></div>
          <div class="detail-item"><label>万字成本</label><span>{p['cost_per_10k']}</span></div>
          <div class="detail-item"><label>内置音色</label><span>{p['voices_count']}</span></div>
          <div class="detail-item"><label>单次最大字数</label><span>{p['max_chars']} 字</span></div>
          <div class="detail-item"><label>单次最大时长</label><span>{p['max_duration_display']}</span></div>
          <div class="detail-item"><label>SSML</label>{ssml_icon}</div>
          <div class="detail-item"><label>声音克隆</label>{clone_icon}</div>
          <div class="detail-item"><label>情感合成</label><span>{p.get('supports_emotion','—')}</span></div>
          <div class="detail-item"><label>方言支持</label><span>{p.get('supports_dialects') or '—'}</span></div>
          <div class="detail-item"><label>语言</label><span>{p['languages']}</span></div>
          <div class="detail-item"><label>流式合成</label><span>{p['streaming']}</span></div>
          <div class="detail-item"><label>配置难度</label><span>{diff_emoji} {p.get('setup_label','')}</span></div>
          <div class="detail-item"><label>安装</label><code>{p['pip_install']}</code></div>
          <div class="detail-item"><label>API 地址</label><code>{p.get('api_url','')}</code></div>
          <div class="detail-item full-width"><label>环境变量</label><code>{' '.join(p['env_vars']) if p['env_vars'] else '无需'}</code></div>
        </div>
        {f'<div class="clone-box"><strong>🔊 声音克隆:</strong> {clone_str}</div>' if p['supports_clone'] else ''}
        {f'<div class="key-box"><strong>🔑 获取 API Key:</strong> <a href="{p["get_key_url"]}" target="_blank">{p["get_key_url"]}</a></div>' if p.get('get_key_url') else ''}
        <div class="voice-list">
          <h3>推荐音色</h3>
          {_voice_cards(p.get('voices', []))}
        </div>
      </section>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ttsCN — 中文 TTS 服务商对比</title>
<style>
:root {{
  --bg: #0f172a; --surface: #1e293b; --border: #334155;
  --text: #e2e8f0; --muted: #94a3b8; --accent: #38bdf8;
  --free: #22c55e; --paid: #f59e0b;
}}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background:var(--bg); color:var(--text); line-height:1.6; }}
a {{ color:var(--accent); text-decoration:none; }}
.container {{ max-width:1400px; margin:0 auto; padding:24px; }}

/* Header */
.header {{ text-align:center; padding:48px 0 32px; }}
.header h1 {{ font-size:2.4rem; margin-bottom:8px; }}
.header h1 span {{ color:var(--accent); }}
.header p {{ color:var(--muted); font-size:1.1rem; }}
.updated {{ color:var(--muted); font-size:0.85rem; margin-top:8px; }}

/* Filter bar */
.filter-bar {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:24px; justify-content:center; }}
.filter-btn {{ padding:6px 16px; border-radius:20px; border:1px solid var(--border); background:var(--surface); color:var(--text); cursor:pointer; font-size:0.85rem; transition:all 0.2s; }}
.filter-btn:hover,.filter-btn.active {{ border-color:var(--accent); background:rgba(56,189,248,0.1); }}

/* Table */
.table-wrap {{ overflow-x:auto; border-radius:12px; border:1px solid var(--border); background:var(--surface); margin-bottom:48px; }}
table {{ width:100%; border-collapse:collapse; font-size:0.9rem; }}
th {{ padding:14px 12px; text-align:left; font-weight:600; color:var(--muted); border-bottom:2px solid var(--border); white-space:nowrap; position:sticky; top:0; background:var(--surface); z-index:1; }}
td {{ padding:12px; border-bottom:1px solid var(--border); vertical-align:middle; }}
tr:hover {{ background:rgba(56,189,248,0.04); }}

.col-name strong {{ display:block; }}
.col-name small {{ color:var(--muted); font-size:0.78rem; }}
.col-cost {{ font-weight:700; }}
.col-cost.free {{ color:var(--free); }}
.col-chars small,.col-duration small {{ color:var(--muted); font-size:0.75rem; display:block; }}

/* Provider link */
.provider-link {{ color:var(--text); display:block; }}
.provider-link:hover strong {{ color:var(--accent); }}

/* Yes/No icons */
.yes {{ font-size:1.1rem; }}
.no {{ opacity:0.35; font-size:1.1rem; }}

/* Tags */
.tag {{ display:inline-block; padding:2px 8px; border-radius:10px; font-size:0.72rem; background:color-mix(in srgb,var(--tag-color) 18%,transparent); color:var(--tag-color); border:1px solid color-mix(in srgb,var(--tag-color) 30%,transparent); margin:2px; }}

/* Detail panels */
.detail-panel {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:32px; margin-bottom:32px; scroll-margin-top:80px; }}
.detail-panel:target {{ border-color:var(--accent); box-shadow:0 0 0 3px rgba(56,189,248,0.15); }}
.detail-header {{ margin-bottom:24px; }}
.detail-header h2 {{ font-size:1.6rem; margin-bottom:4px; }}
.detail-header .provider-name {{ color:var(--muted); }}
.detail-tags {{ margin-top:12px; }}

.detail-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:16px; margin-bottom:24px; }}
.detail-item {{ padding:12px 16px; background:rgba(15,23,42,0.5); border-radius:8px; }}
.detail-item label {{ display:block; font-size:0.75rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px; }}
.detail-item span,.detail-item code {{ font-size:0.92rem; }}
.detail-item.full-width {{ grid-column:1/-1; }}
.detail-item code,.clone-box code,.key-box code {{ background:rgba(0,0,0,0.3); padding:3px 8px; border-radius:4px; font-size:0.85rem; color:var(--accent); word-break:break-all; }}

.clone-box,.key-box {{ padding:14px 18px; border-radius:8px; margin-bottom:16px; background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.2); }}
.key-box {{ background:rgba(56,189,248,0.06); border-color:rgba(56,189,248,0.2); }}
.clone-box a,.key-box a {{ font-size:0.85rem; }}

.cost-badge {{ font-weight:700; }}
.cost-badge.free {{ color:var(--free); }}

/* Voice cards */
.voice-list {{ margin-top:24px; }}
.voice-list h3 {{ margin-bottom:12px; font-size:1.1rem; }}
.voice-card {{ display:flex; gap:12px; align-items:center; padding:10px 14px; background:rgba(0,0,0,0.2); border-radius:6px; margin-bottom:6px; flex-wrap:wrap; }}
.voice-id {{ font-weight:600; color:var(--accent); font-size:0.85rem; min-width:150px; }}
.voice-label {{ font-weight:500; font-size:0.9rem; }}
.voice-style {{ color:var(--muted); font-size:0.82rem; }}
.voice-best {{ color:var(--muted); font-size:0.8rem; margin-left:auto; font-style:italic; }}

/* Footer */
.footer {{ text-align:center; padding:32px; color:var(--muted); font-size:0.85rem; }}

/* Responsive */
@media(max-width:768px) {{
  .header h1 {{ font-size:1.6rem; }}
  .detail-grid {{ grid-template-columns:1fr; }}
  .voice-card {{ flex-direction:column; align-items:flex-start; }}
  .voice-best {{ margin-left:0; }}
}}

/* Back to top */
.back-top {{ position:fixed; bottom:24px; right:24px; width:44px; height:44px; border-radius:50%; background:var(--accent); color:var(--bg); border:none; cursor:pointer; font-size:1.2rem; display:flex; align-items:center; justify-content:center; opacity:0.7; transition:opacity 0.2s; }}
.back-top:hover {{ opacity:1; }}
</style>
</head>
<body>
<div class="container">

  <header class="header">
    <h1>🎤 ttsCN — 中文 <span>TTS</span> 服务商对比</h1>
    <p>{len(backends)} 个可用的语音合成后端 (国内 + 国际) · 点击行查看详情 · 数据更新于 {updated}</p>
    <p class="updated">💡 编辑 <code>data/providers.json</code> 即可更新此页面</p>
  </header>

  <div class="filter-bar">
    <button class="filter-btn active" data-filter="all">全部</button>
    <button class="filter-btn" data-filter="free">🆓 免费</button>
    <button class="filter-btn" data-filter="clone">🎭 声音克隆</button>
    <button class="filter-btn" data-filter="ssml">📝 SSML</button>
    <button class="filter-btn" data-filter="streaming">🌊 流式</button>
    <button class="filter-btn" data-filter="dialects">🗣️ 方言</button>
    <button class="filter-btn" data-filter="multilingual">🌍 多语言</button>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>服务商</th>
          <th>费用 (每万字)</th>
          <th>音色数</th>
          <th>最大字数</th>
          <th>最大时长</th>
          <th>SSML</th>
          <th>克隆</th>
          <th>情感</th>
          <th>语言</th>
          <th>流式</th>
          <th>配置</th>
        </tr>
      </thead>
      <tbody id="provider-tbody">
        {rows}
      </tbody>
    </table>
  </div>

  <h2 style="margin-bottom:24px;">📋 服务商详情</h2>
  {detail_sections}

  <h2 style="margin:48px 0 24px;">🔧 Developer Reference</h2>

  <div class="detail-panel" id="dev-reference">
    <h3>CLI Output Envelope</h3>
    <pre><code>// Success
{{"ok":true, "data":{{...}}, "meta":{{"version":"...","schema_version":"1.1.0","timestamp":"...","ms":123}}}}

// Error
{{"ok":false, "error":{{"code":"auth_missing_env","message":"...","retryable":false,"field":"...","backend":"..."}}, "meta":{{...}}}}</code></pre>

    <h3 style="margin-top:24px;">Exit Codes</h3>
    <table style="max-width:600px;">
      <thead><tr><th>Code</th><th>Meaning</th><th>Agent Action</th></tr></thead>
      <tbody>
        <tr><td><code>0</code></td><td>Success</td><td>Parse <code>data</code>, proceed</td></tr>
        <tr><td><code>1</code></td><td>Internal / runtime error</td><td>Report to user, do not retry</td></tr>
        <tr><td><code>2</code></td><td>Validation / input error</td><td>Fix input, retry allowed</td></tr>
        <tr><td><code>3</code></td><td>Auth / missing credentials</td><td>Ask user for API key, do not retry</td></tr>
        <tr><td><code>4</code></td><td>Backend API error</td><td>Retry with exponential backoff</td></tr>
      </tbody>
    </table>

    <h3 style="margin-top:24px;">Schema Introspection</h3>
    <pre><code>tts.py schema backends           # All {len(backends)} backends (compact by default)
tts.py schema backends --full    # All 22 fields per backend
tts.py schema backends.doubao    # Single backend full detail
tts.py schema voices             # All voice presets
tts.py schema tags               # Tag definitions
tts.py schema version            # Version + data freshness</code></pre>

    <h3 style="margin-top:24px;">JSON Output Modes</h3>
    <table style="max-width:700px;">
      <thead><tr><th>Mode</th><th>Command</th><th>Behavior</th></tr></thead>
      <tbody>
        <tr><td>Explicit JSON</td><td><code>--format json</code></td><td>JSON on stdout, diagnostics on stderr</td></tr>
        <tr><td>Auto-detect</td><td>pipe / non-TTY</td><td>Auto JSON when stdout is not a terminal</td></tr>
        <tr><td>Compact list</td><td><code>schema backends</code></td><td>11 fields (default), <code>--full</code> for 22</td></tr>
        <tr><td>Field filter</td><td><code>--fields name,cost,clone</code></td><td>Agent chooses subset, saves tokens</td></tr>
      </tbody>
    </table>

    <h3 style="margin-top:24px;">Idempotency</h3>
    <pre><code>tts.py --idempotency-key "my-job-42" --input script.txt out.wav
# Retried calls with same key → cached result (~/.ttscn_idem/)
# No double-billing. 7-day TTL.</code></pre>

    <h3 style="margin-top:24px;">Resources</h3>
    <p>
      <a href="https://github.com/Agents365-ai/ttsCN">📦 GitHub Repo</a> &nbsp;·&nbsp;
      <a href="providers.md">📄 Markdown Comparison</a> &nbsp;·&nbsp;
      <a href="https://agents365-ai.github.io/ttsCN/">🌐 GitHub Pages</a> &nbsp;·&nbsp;
      <a href="https://github.com/Agents365-ai/agent-native-design">📐 agent-native-design</a>
    </p>
  </div>

  <footer class="footer">
    <p>Generated by <strong>ttsCN</strong> · <a href="https://github.com/Agents365-ai/ttsCN">GitHub</a> · CC BY-NC 4.0</p>
  </footer>
</div>

<button class="back-top" onclick="window.scrollTo({{top:0,behavior:'smooth'}})" title="返回顶部">↑</button>

<script>
// Filter buttons
document.querySelectorAll('.filter-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const filter = btn.dataset.filter;
    document.querySelectorAll('.provider-row').forEach(row => {{
      if (filter === 'all') {{ row.style.display = ''; return; }}
      const id = row.id.replace('row-','');
      const detail = document.getElementById('detail-' + id);
      const tags = detail?.querySelectorAll('.tag') || [];
      const match = Array.from(tags).some(t => t.textContent.includes(
        filter === 'free' ? '免费' :
        filter === 'clone' ? '声音克隆' :
        filter === 'ssml' ? 'SSML' :
        filter === 'streaming' ? '流式' :
        filter === 'dialects' ? '方言' :
        filter === 'multilingual' ? '多语言' : ''
      ));
      row.style.display = match ? '' : 'none';
    }});
  }});
}});

// Row click → scroll to detail
document.querySelectorAll('.provider-link').forEach(link => {{
  link.addEventListener('click', e => {{
    const target = document.querySelector(link.getAttribute('href'));
    if (target) {{
      e.preventDefault();
      target.scrollIntoView({{behavior:'smooth',block:'start'}});
    }}
  }});
}});
</script>
</body>
</html>"""
    return html


# ═══════════════════════════════════════════════════════════════════════════
# Markdown Builder
# ═══════════════════════════════════════════════════════════════════════════

def build_md(data):
    """Generate providers.md from JSON data."""
    backends = data["backends"]
    updated = data.get("updated", "")

    lines = [
        f"# ttsCN — Chinese TTS Provider Comparison",
        f"",
        f"> Auto-generated from `data/providers.json` · Updated: {updated}",
        f"",
        f"## Quick Comparison ({len(backends)} backends)",
        f"",
    ]

    # Summary table
    header = "| Provider | Cost/10K chars | Voices | Max chars | Max duration | SSML | Clone | Emotion | Languages | Streaming | Setup |"
    sep = "|----------|---------------|--------|-----------|-------------|------|-------|---------|-----------|-----------|-------|"
    lines.append(header)
    lines.append(sep)
    for p in backends:
        ssml = "✅" if p["supports_ssml"] else "❌"
        clone = "✅" if p["supports_clone"] else "❌"
        lines.append(
            f"| **{p['name']}**<br><small>{p['provider']}</small> "
            f"| {p['cost']} "
            f"| {p['voices_count']} "
            f"| {p['max_chars']} "
            f"| {p['max_duration_display']} "
            f"| {ssml} "
            f"| {clone} "
            f"| {p.get('supports_emotion','—')} "
            f"| {p['languages']} "
            f"| {p['streaming']} "
            f"| {p.get('setup_label','')} |"
        )

    # Detail sections
    for p in backends:
        lines.append(f"")
        lines.append(f"## {p['name']}")
        lines.append(f"")
        lines.append(f"**Provider:** {p['provider']}")
        lines.append(f"")
        lines.append(f"| Property | Value |")
        lines.append(f"|----------|-------|")
        lines.append(f"| Cost | {p['cost']} ({p['cost_per_10k']}/10K chars) |")
        lines.append(f"| Built-in voices | {p['voices_count']} |")
        lines.append(f"| Max chars / chunk | {p['max_chars']} |")
        lines.append(f"| Max duration / chunk | {p['max_duration_display']} |")
        lines.append(f"| SSML | {p['supports_ssml']} |")
        lines.append(f"| Voice cloning | {p['supports_clone']} |")
        if p["supports_clone"]:
            lines.append(f"| Clone detail | {p['clone_detail']} |")
        lines.append(f"| Emotion | {p.get('supports_emotion','—')} |")
        lines.append(f"| Dialects | {p.get('supports_dialects') or '—'} |")
        lines.append(f"| Languages | {p['languages']} |")
        lines.append(f"| Streaming | {p['streaming']} |")
        lines.append(f"| Setup | {p.get('setup_label','')} |")
        lines.append(f"| Install | `{p['pip_install']}` |")
        lines.append(f"| API Key | {p.get('get_key_url') or 'N/A'} |")
        lines.append(f"| Env vars | `{' '.join(p['env_vars']) if p['env_vars'] else 'none'}` |")
        lines.append(f"")

        if p.get("voices"):
            lines.append(f"### Recommended Voices")
            lines.append(f"")
            for v in p["voices"]:
                extra = f" — {v['style']}" if v.get("style") else ""
                extra += f" → {v['best_for']}" if v.get("best_for") else ""
                lines.append(f"- `{v['id']}` {v.get('label','')}{extra}")
            lines.append(f"")

    lines.append(f"---")
    lines.append(f"*Generated by [ttsCN](https://github.com/Agents365-ai/ttsCN) from `data/providers.json`*")
    lines.append(f"")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    data = load_data()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Building docs from {len(data['backends'])} providers...")

    # Skill-internal docs
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    html = build_html(data)
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"  ✓ {HTML_OUT} ({len(html):,} bytes)")

    md = build_md(data)
    MD_OUT.write_text(md, encoding="utf-8")
    print(f"  ✓ {MD_OUT} ({len(md):,} bytes)")

    # GitHub Pages output (repo root docs/)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_HTML.write_text(html, encoding="utf-8")
    print(f"  ✓ {PAGES_HTML} ({len(html):,} bytes)  ← GitHub Pages")

    PAGES_MD.write_text(md, encoding="utf-8")
    print(f"  ✓ {PAGES_MD} ({len(md):,} bytes)")

    print("\nDone. Open docs/index.html in a browser or push to GitHub Pages.")


if __name__ == "__main__":
    main()
