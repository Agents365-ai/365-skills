# Zotero Plugin Gallery

Snapshot of the [Zotero Chinese community plugin store](https://zotero-chinese.com/plugins/) registry — [`zotero-chinese/zotero-plugins`](https://github.com/zotero-chinese/zotero-plugins), `src/plugins.ts`. Fetched 2026-07-19; refresh by re-parsing the registry.

## Use when developing a new plugin

1. Find the tag closest to the feature you want to build (tables below).
2. Shortlist repos — prefer recently-updated, Zotero 7+ compatible ones.
3. Read the repo source for the integration-point pattern: bootstrap `startup`/`shutdown`, `Zotero.ItemPaneManager.registerSection`, items-list column registration, `Zotero.Notifier` observers, preference panes.
   Real plugin code is the best documentation for integration points the official docs cover thinly.
4. Check the deprecated list at the bottom so you never recommend or fork a dead plugin.

## Plugins by tag (137 active)

### productivity (14) — workflow efficiency (bulk ops, automation, shortcuts)

| Repo | Zotero | Tags |
| ------ | -------- | ------ |
| [`alansirius/Zotero-Exitem`](https://github.com/alansirius/Zotero-Exitem) | 8/7 | productivity, ai, notes |
| [`Bowen-0x00/zotero-action-cmd`](https://github.com/Bowen-0x00/zotero-action-cmd) | 7 | productivity |
| [`Chikit-L/zotero-fulltext-translate`](https://github.com/Chikit-L/zotero-fulltext-translate) | 8/7 | productivity |
| [`Dominic-DallOsto/zotero-reading-list`](https://github.com/Dominic-DallOsto/zotero-reading-list) | 8/7/6 | productivity |
| [`guaguastandup/zotero-pdf2zh`](https://github.com/guaguastandup/zotero-pdf2zh) | 8/7 | productivity |
| [`immersive-translate/zotero-immersivetranslate`](https://github.com/immersive-translate/zotero-immersivetranslate) | 7 | productivity |
| [`janbaykara/zotero-syllabus`](https://github.com/janbaykara/zotero-syllabus) | 7 | productivity, visualization |
| [`OneOneLiu/zotero-annotation-summary`](https://github.com/OneOneLiu/zotero-annotation-summary) | 8/7 | productivity |
| [`retorquere/zotero-folder-import`](https://github.com/retorquere/zotero-folder-import) | 7 | productivity |
| [`Royshare/zotero-spotlight`](https://github.com/Royshare/zotero-spotlight) | 8 | productivity |
| [`samreading/zotero-mindmap`](https://github.com/samreading/zotero-mindmap) | 8/7/9 | productivity |
| [`WildDataX/suppr-zotero-plugin`](https://github.com/WildDataX/suppr-zotero-plugin) | 8/7 | productivity |
| [`windingwind/zotero-actions-tags`](https://github.com/windingwind/zotero-actions-tags) | 8/7/6 | productivity |
| [`wshanks/Zutilo`](https://github.com/wshanks/Zutilo) | 7/6 | productivity |

### ai (29) — LLM / AI integration (chat, translation, embeddings)

| Repo | Zotero | Tags |
| ------ | -------- | ------ |
| [`edwintuan/pdf-ai-bookmarks`](https://github.com/edwintuan/pdf-ai-bookmarks) | 8 | ai |
| [`ET06731/zotero-paper2slides`](https://github.com/ET06731/zotero-paper2slides) | 7 | ai, productivity, notes |
| [`introfini/ZotSeek`](https://github.com/introfini/ZotSeek) | 8 | ai |
| [`j-cyoung/PaperViewZoteroPlugin`](https://github.com/j-cyoung/PaperViewZoteroPlugin) | 8 | ai, productivity |
| [`jetxa/zotero-ai-assistant`](https://github.com/jetxa/zotero-ai-assistant) | 8 | ai |
| [`jlegewie/beaver-zotero`](https://github.com/jlegewie/beaver-zotero) | 8/7 | ai |
| [`justinfjx/zotero-ai-collection`](https://github.com/justinfjx/zotero-ai-collection) | 7/8 | ai, productivity |
| [`kazgu/zotero-chatgpt`](https://github.com/kazgu/zotero-chatgpt) | 7 | ai, productivity |
| [`l0o0/Garden-for-Zotero`](https://github.com/l0o0/Garden-for-Zotero) | 8/7 | ai, productivity |
| [`l0o0/MagicZotero`](https://github.com/l0o0/MagicZotero) | 8/7 | ai, productivity, integration |
| [`leike0813/Zotero-Skills`](https://github.com/leike0813/Zotero-Skills) | 7 | ai, integration |
| [`lifan0127/ai-research-assistant`](https://github.com/lifan0127/ai-research-assistant) | 7/6 | ai, productivity |
| [`lisontowind/zotero-copilot`](https://github.com/lisontowind/zotero-copilot) | 8/9 | ai, productivity |
| [`lisontowind/zotero-mineru`](https://github.com/lisontowind/zotero-mineru) | 8/9 | ai, attachment, productivity |
| [`menyoung/zoTLDR`](https://github.com/menyoung/zoTLDR) | 8 | ai |
| [`MuiseDestiny/zotero-gpt`](https://github.com/MuiseDestiny/zotero-gpt) | 8/7/6 | ai, interface, productivity |
| [`papersgpt/papersgpt-for-zotero`](https://github.com/papersgpt/papersgpt-for-zotero) | 7 | ai, productivity |
| [`replynow20/gemini-zotero`](https://github.com/replynow20/gemini-zotero) | 8/7 | ai, productivity |
| [`sheny-bio/marginalia`](https://github.com/sheny-bio/marginalia) | 8/7 | ai, productivity |
| [`steven-jianhao-li/zotero-AI-Butler`](https://github.com/steven-jianhao-li/zotero-AI-Butler) | 8/7 | ai, notes, productivity |
| [`swcxito/zotero-ai-bar`](https://github.com/swcxito/zotero-ai-bar) | 8/7 | ai, productivity |
| [`syt2/paper-chat-for-zotero`](https://github.com/syt2/paper-chat-for-zotero) | 7/8 | ai |
| [`vastronghq/MarginMind`](https://github.com/vastronghq/MarginMind) | 8 | ai |
| [`Visterainer/zoteroAI`](https://github.com/Visterainer/zoteroAI) | 8/7 | ai, productivity |
| [`wdcpclover/ai4paper`](https://github.com/wdcpclover/ai4paper) | 7/8/9 | ai, productivity, reader, notes, metadata, interface, visualization |
| [`WilliamsLiang/zotero-skr`](https://github.com/WilliamsLiang/zotero-skr) | 7 | ai, productivity |
| [`windfollowingheart/zotero-paper-agent`](https://github.com/windfollowingheart/zotero-paper-agent) | 7 | ai, productivity |
| [`YanSH258/zotero-dailypaper`](https://github.com/YanSH258/zotero-dailypaper) | 7 | ai |
| [`yilewang/llm-for-zotero`](https://github.com/yilewang/llm-for-zotero) | 8/7 | ai, notes, productivity |

### metadata (22) — metadata lookup, cleanup, identifiers

| Repo | Zotero | Tags |
| ------ | -------- | ------ |
| [`AllanChain/zotero-arxiv-workflow`](https://github.com/AllanChain/zotero-arxiv-workflow) | 8/7 | metadata |
| [`bwiernik/zotero-shortdoi`](https://github.com/bwiernik/zotero-shortdoi) | 7/6 | metadata |
| [`Creling/Zotero-Metadata-Scraper`](https://github.com/Creling/Zotero-Metadata-Scraper) | 7 | metadata |
| [`daeh/zotero-citation-tally`](https://github.com/daeh/zotero-citation-tally) | 7 | metadata |
| [`diegodlh/zotero-cita`](https://github.com/diegodlh/zotero-cita) | 8/7 | metadata |
| [`federicotorrielli/zotero-metadata-hunter`](https://github.com/federicotorrielli/zotero-metadata-hunter) | 8 | metadata |
| [`fkguo/zotero-inspire`](https://github.com/fkguo/zotero-inspire) | 8/7 | metadata |
| [`FrLars21/ZoteroCitationCountsManager`](https://github.com/FrLars21/ZoteroCitationCountsManager) | 7 | metadata |
| [`GroundbreakerLhy/CCF-Rank`](https://github.com/GroundbreakerLhy/CCF-Rank) | 8/7 | metadata |
| [`Jarvis-Towne/paper-feed-zotero`](https://github.com/Jarvis-Towne/paper-feed-zotero) | 8 | metadata |
| [`jmiba/Zotero-add-items-from-text`](https://github.com/jmiba/Zotero-add-items-from-text) | 8 | metadata |
| [`justinribeiro/zotero-google-scholar-citation-count`](https://github.com/justinribeiro/zotero-google-scholar-citation-count) | 7 | metadata |
| [`kevin65536/zotero-openreview-plugin`](https://github.com/kevin65536/zotero-openreview-plugin) | 8/7 | metadata |
| [`MuiseDestiny/zotero-reference`](https://github.com/MuiseDestiny/zotero-reference) | 8/7 | metadata, reader |
| [`northword/zotero-format-metadata`](https://github.com/northword/zotero-format-metadata) | 7/6 | metadata |
| [`panhaoyu/zotero-categorial-tags`](https://github.com/panhaoyu/zotero-categorial-tags) | 8/7 | metadata, productivity, interface |
| [`redleafnew/zotero-updateifsE`](https://github.com/redleafnew/zotero-updateifsE) | 8/7/6 | metadata |
| [`retorquere/zotero-pmcid-fetcher`](https://github.com/retorquere/zotero-pmcid-fetcher) | 7 | metadata |
| [`RoadToDream/ZotMeta`](https://github.com/RoadToDream/ZotMeta) | 7 | metadata |
| [`syt2/Zotero-TLDR`](https://github.com/syt2/Zotero-TLDR) | 8/7 | metadata |
| [`theRatramnus/RIOPACAddChapter`](https://github.com/theRatramnus/RIOPACAddChapter) | 7 | metadata |
| [`TimeTrapzz/zotero-ccf-info`](https://github.com/TimeTrapzz/zotero-ccf-info) | 8/7 | metadata |

### integration (16) — bridges to external tools (Obsidian, editors, etc.)

| Repo | Zotero | Tags |
| ------ | -------- | ------ |
| [`018/zotero-excalidraw`](https://github.com/018/zotero-excalidraw) | 7 | integration |
| [`1ywan/zotero-odh`](https://github.com/1ywan/zotero-odh) | 7 | integration |
| [`bulletproof-system/zotero-maimemo-sync`](https://github.com/bulletproof-system/zotero-maimemo-sync) | 7 | integration |
| [`cookjohn/zotero-mcp`](https://github.com/cookjohn/zotero-mcp) | 8/7 | integration, ai |
| [`daeh/zotero-markdb-connect`](https://github.com/daeh/zotero-markdb-connect) | 8/7/6 | integration |
| [`dvanoni/notero`](https://github.com/dvanoni/notero) | 8/7/6 | integration |
| [`egh/zotxt`](https://github.com/egh/zotxt) | 7/6 | integration |
| [`etShaw-zh/zotracer`](https://github.com/etShaw-zh/zotracer) | 7 | integration, visualization, productivity |
| [`inciteful-xyz/inciteful-zotero-plugin`](https://github.com/inciteful-xyz/inciteful-zotero-plugin) | 8/7/6 | integration |
| [`jyjulianwong/PolarRec-Zotero-Plugin`](https://github.com/jyjulianwong/PolarRec-Zotero-Plugin) | 7 | integration |
| [`occasional16/researchopia`](https://github.com/occasional16/researchopia) | 9/8/7 | integration |
| [`PubPeerFoundation/pubpeer_zotero_plugin`](https://github.com/PubPeerFoundation/pubpeer_zotero_plugin) | 8/7 | integration |
| [`retorquere/zotero-better-bibtex`](https://github.com/retorquere/zotero-better-bibtex) | 8/7 | integration |
| [`ScienceLiveHub/science-live-platform`](https://github.com/ScienceLiveHub/science-live-platform) | 7/8 | integration, metadata |
| [`scitedotai/scite-zotero-plugin`](https://github.com/scitedotai/scite-zotero-plugin) | 7/6 | integration |
| [`yueneiqi/zotero2eagle`](https://github.com/yueneiqi/zotero2eagle) | 8/7 | integration |

### interface (10) — UI customization, themes, layout

| Repo | Zotero | Tags |
| ------ | -------- | ------ |
| [`aidecameron/zotero-annotation-color-customizer`](https://github.com/aidecameron/zotero-annotation-color-customizer) | 7 | interface |
| [`alima-webdev/zotero-review-assistant`](https://github.com/alima-webdev/zotero-review-assistant) | 7 | interface, visualization |
| [`B3000Kcn/daily-folder-for-zotero`](https://github.com/B3000Kcn/daily-folder-for-zotero) | 8/7 | interface |
| [`B3000Kcn/minimize-zotero-to-tray`](https://github.com/B3000Kcn/minimize-zotero-to-tray) | 8/7 | interface |
| [`Dominic-DallOsto/zotero-annotations-count`](https://github.com/Dominic-DallOsto/zotero-annotations-count) | 8/7 | interface, visualization |
| [`Dominic-DallOsto/zotero-pin-items`](https://github.com/Dominic-DallOsto/zotero-pin-items) | 8/7 | interface |
| [`github-young/zotero-better-authors`](https://github.com/github-young/zotero-better-authors) | 8/7 | interface |
| [`Qiujv/zotero-hashtags-column`](https://github.com/Qiujv/zotero-hashtags-column) | 8/7 | interface |
| [`qiwei-ma/zotero-pdf-setHorizontal`](https://github.com/qiwei-ma/zotero-pdf-setHorizontal) | 8/7 | interface |
| [`Rphone/zotero-tab-enhance`](https://github.com/Rphone/zotero-tab-enhance) | 7 | interface, productivity |

### reader (11) — PDF/EPUB reader enhancements

| Repo | Zotero | Tags |
| ------ | -------- | ------ |
| [`dawaltconley/zotero-center-pdf`](https://github.com/dawaltconley/zotero-center-pdf) | 8 | reader |
| [`forrtproject/fred_zotero`](https://github.com/forrtproject/fred_zotero) | 8 | reader |
| [`ImperialSquid/zotero-zotts`](https://github.com/ImperialSquid/zotero-zotts) | 7 | reader |
| [`Infinity4B/zotero-hjfy-split-reader`](https://github.com/Infinity4B/zotero-hjfy-split-reader) | 8 | reader, productivity |
| [`jagaldol/zotero-cite-preview-resizer`](https://github.com/jagaldol/zotero-cite-preview-resizer) | 8 | reader |
| [`mobench/zotero-annotation-links`](https://github.com/mobench/zotero-annotation-links) | 8 | reader |
| [`MuiseDestiny/zotero-figure`](https://github.com/MuiseDestiny/zotero-figure) | 8/7/6 | reader, productivity |
| [`q77190858/zotero-pdf-background`](https://github.com/q77190858/zotero-pdf-background) | 7/6 | reader |
| [`quertt/zotero-keyword-highlighter`](https://github.com/quertt/zotero-keyword-highlighter) | 8 | reader |
| [`taotaozsky2025-beep/zotero-var-highlighter`](https://github.com/taotaozsky2025-beep/zotero-var-highlighter) | 8/7 | reader, productivity |
| [`windingwind/bionic-for-zotero`](https://github.com/windingwind/bionic-for-zotero) | 8/7 | reader |

### attachment (11) — file attachment handling, rename, move

| Repo | Zotero | Tags |
| ------ | -------- | ------ |
| [`ANGJustinl/zotero-plugin-hjfy`](https://github.com/ANGJustinl/zotero-plugin-hjfy) | 8 | attachment, productivity |
| [`franzbischoff/zotero-pdf-metadata`](https://github.com/franzbischoff/zotero-pdf-metadata) | 7/8/7 | attachment |
| [`MuiseDestiny/zotero-attanger`](https://github.com/MuiseDestiny/zotero-attanger) | 8/7 | attachment |
| [`nutstore/zotero-plugin-nutstore-sso`](https://github.com/nutstore/zotero-plugin-nutstore-sso) | 9/8/7 | attachment, integration |
| [`redleafnew/delitemwithatt`](https://github.com/redleafnew/delitemwithatt) | 8/7/6 | attachment |
| [`retorquere/zotero-open-pdf`](https://github.com/retorquere/zotero-open-pdf) | 8/7 | attachment |
| [`SciImage/zotero-attachment-scanner`](https://github.com/SciImage/zotero-attachment-scanner) | 8/7 | attachment |
| [`syt2/zotero-scipdf`](https://github.com/syt2/zotero-scipdf) | 8/7 | attachment |
| [`Theigrams/zotero-pdf-custom-rename`](https://github.com/Theigrams/zotero-pdf-custom-rename) | 7 | attachment |
| [`theRatramnus/Zotero-download-DigiVatLib-pdf`](https://github.com/theRatramnus/Zotero-download-DigiVatLib-pdf) | 7 | attachment |
| [`wileyyugioh/zotmoov`](https://github.com/wileyyugioh/zotmoov) | 8/7 | attachment |

### visualization (2) — graphs, timelines, charts

| Repo | Zotero | Tags |
|------|--------|------|
| [`etShaw-zh/zotero-career-tracker`](https://github.com/etShaw-zh/zotero-career-tracker) | 8 | visualization |
| [`StevenGLee/zotero-author-browser`](https://github.com/StevenGLee/zotero-author-browser) | 7 | visualization |

### favorite (10) — collections, tagging, organization

| Repo | Zotero | Tags |
| ------ | -------- | ------ |
| [`ChenglongMa/zoplicate`](https://github.com/ChenglongMa/zoplicate) | 8/7/6 | favorite, metadata |
| [`l0o0/jasminum`](https://github.com/l0o0/jasminum) | 8/7/6 | favorite, metadata |
| [`MuiseDestiny/eaiser-citation`](https://github.com/MuiseDestiny/eaiser-citation) | 8/7/6 | favorite, writing |
| [`MuiseDestiny/ZoteroStyle`](https://github.com/MuiseDestiny/ZoteroStyle) | 8/7/6 | favorite, interface, visualization |
| [`MuiseDestiny/ZoteroStyle`](https://github.com/MuiseDestiny/ZoteroStyle) | 7/6 | favorite, interface, visualization |
| [`northword/zotero-format-metadata`](https://github.com/northword/zotero-format-metadata) | 9/8/7/6 | favorite, metadata |
| [`syt2/zotero-addons`](https://github.com/syt2/zotero-addons) | 8/7/6 | favorite, others |
| [`volatile-static/Chartero`](https://github.com/volatile-static/Chartero) | 8/7/6 | favorite, visualization, interface |
| [`windingwind/zotero-better-notes`](https://github.com/windingwind/zotero-better-notes) | 8/7/6 | favorite, notes |
| [`windingwind/zotero-pdf-translate`](https://github.com/windingwind/zotero-pdf-translate) | 8/7/6 | favorite, productivity |

### notes (2) — note-taking enhancements

| Repo | Zotero | Tags |
|------|--------|------|
| [`018/zotcard`](https://github.com/018/zotcard) | 7/6 | notes |
| [`BlueBlueKitty/zotero-ainote`](https://github.com/BlueBlueKitty/zotero-ainote) | 8/7 | notes, ai, productivity |

### developer (4) — developer tooling (debug, scaffold)

| Repo | Zotero | Tags |
| ------ | -------- | ------ |
| [`GOKORURI007/zotero-api-plus`](https://github.com/GOKORURI007/zotero-api-plus) | 8 | developer |
| [`introfini/mcp-server-zotero-dev`](https://github.com/introfini/mcp-server-zotero-dev) | 8 | developer |
| [`retorquere/zotero-better-bibtex`](https://github.com/retorquere/zotero-better-bibtex) | 7 | developer |
| [`windingwind/know-ur-zotero`](https://github.com/windingwind/know-ur-zotero) | 8/7 | developer |

### others (6) — miscellaneous

| Repo | Zotero | Tags |
| ------ | -------- | ------ |
| [`BryceWG/zotero-ai-tags`](https://github.com/BryceWG/zotero-ai-tags) | 8/7 | others |
| [`david3684/zotero-tab-limiter`](https://github.com/david3684/zotero-tab-limiter) | 7 | others |
| [`l0o0/tara`](https://github.com/l0o0/tara) | 8/7 | others |
| [`UB-Mannheim/zotero-ocr`](https://github.com/UB-Mannheim/zotero-ocr) | 8/7 | others |
| [`yhmtsai/KeepZotero`](https://github.com/yhmtsai/KeepZotero) | 7/6 | others |
| [`zzlb0224/zotero-annotation-manage`](https://github.com/zzlb0224/zotero-annotation-manage) | 8/7 | others |

## Deprecated / dead (23)

Do not recommend or base new work on these (superseded, unmaintained, or removed):

- `AgiNetz/semantic-zotero`
- `AlbertShenC/Zotero-Literature-Manager`
- `argenos/zotero-mdnotes`
- `eschnett/zotero-citationcounts`
- `ethanwillis/zotero-scihub`
- `frangoud/ZoteroDuplicatesMerger`
- `inciteful-xyz/inciteful-zotero-plugin`
- `iShareStuff/Backup-Plugin-for-Zotero`
- `iShareStuff/ZoteroFields-Plugin-for-Zotero`
- `iShareStuff/ZoteroTheme`
- `jlegewie/zotfile`
- `ManuelaRunge/Zotitle`
- `mpatelh/zbatch`
- `paulusm/zotero-trilium`
- `redleafnew/zotero-updateifs`
- `retorquere/zotero-storage-scanner`
- `SiriusXT/Zotero-Scholar-Rank`
- `tefkah/zotero-night`
- `wbthomason/zotodo`
- `whacked/zotero-special-tags-column`
- `windingwind/zotero-pdf-preview`
- `wshanks/lyz`
- `Zar-rok/Zotero-Add-Collection-Tag`
