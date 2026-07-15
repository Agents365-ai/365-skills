# ttsCN — Chinese TTS Provider Comparison

> Auto-generated from `data/providers.json` · Updated: 2026-07-15

## Quick Comparison (11 backends)

| Provider | Cost/10K chars | Voices | Max chars | Max duration | SSML | Clone | Emotion | Languages | Streaming | Setup |
|----------|---------------|--------|-----------|-------------|------|-------|---------|-----------|-----------|-------|
| **Edge TTS**<br><small>Microsoft</small> | 免费 | 20+ | 2000 | ~10 分钟 | ✅ | ❌ | Via SSML | 100+ | WebSocket | 零配置 |
| **豆包 TTS**<br><small>ByteDance (火山引擎)</small> | ~1 元/万字 | 8 + 声音复刻 | 280 | ~1 分钟 | ❌ | ✅ | 情感预测版 (+1元/万字) | 中文、英文、中英混读 | WebSocket | 中等 |
| **CosyVoice**<br><small>Alibaba (阿里云百炼)</small> | ~2 元/万字 | 7 | 400 | ~2 分钟 | ❌ | ✅ | Via voice style | 中文 | SDK 流式 | 简单 |
| **Azure TTS**<br><small>Microsoft</small> | ~$1/百万字符 | 20+ + 自定义 | 2000 | ~10 分钟 | ✅ | ✅ | Via SSML (mstts:express-as) | 100+ | SDK 流式 | 中等 |
| **腾讯云 TTS**<br><small>Tencent</small> | 0.75 元/万字 | 380+ + 声音复刻 | 150 | ~30 秒 | ✅ | ✅ | Via SSML (精品音色) | 中文、英文、粤语 | WebSocket | 中等 |
| **百度 AI TTS**<br><small>Baidu</small> | 灵活计费 | 30+ + 声音复刻 | 500 | ~2 分钟 | ✅ | ✅ | Native 情感合成 (喜悦/悲伤/中性) | 中文、英文、日文 | WebSocket | 简单 |
| **MiniMax TTS**<br><small>MiniMax</small> | ~$1/千字符 | 300+ + 复刻 + Voice Design | 3000 | ~5 分钟 | ❌ | ✅ | Native 8种情感 (happy/sad/angry/fearful/calm/whisper...) | 40+ (中/英/日/韩/法/德/西/阿...) | REST only | 简单 |
| **讯飞 TTS**<br><small>iFlytek (科大讯飞)</small> | ~2 元/万字 | 500+ + 声音复刻 | 200 | ~1 分钟 | ✅ | ✅ | Native 超拟人情感 | 130+ (中/英/日/韩/俄/方言语种...) | WebSocket | 中等 |
| **ElevenLabs**<br><small>ElevenLabs (国际)</small> | 订阅制 $5/月起 | 20+ 预置 + 复刻 | 400 | ~2 分钟 | ❌ | ✅ | Via voice settings (stability/style) | 32 (multilingual v2) | REST / WebSocket | 简单 (需国际网络) |
| **OpenAI TTS**<br><small>OpenAI (国际)</small> | $15-30/百万字符 | 6 | 400 | ~2 分钟 | ❌ | ❌ |  | 50+ (多语言自动识别) | REST | 简单 (需国际网络) |
| **Google Cloud TTS**<br><small>Google (国际)</small> | $16/百万字符 (每月前100万字免费) | 220+ | 400 | ~2 分钟 | ❌ | ❌ |  | 40+ (含中文 cmn-CN) | REST | 简单 (需国际网络) |

## Edge TTS

**Provider:** Microsoft

| Property | Value |
|----------|-------|
| Cost | 免费 (¥0/10K chars) |
| Built-in voices | 20+ |
| Max chars / chunk | 2000 |
| Max duration / chunk | ~10 分钟 |
| SSML | True |
| Voice cloning | False |
| Emotion | Via SSML |
| Dialects | — |
| Languages | 100+ |
| Streaming | WebSocket |
| Setup | 零配置 |
| Install | `pip install edge-tts` |
| API Key | N/A |
| Env vars | `none` |

### Recommended Voices

- `zh-CN-XiaoxiaoNeural` 晓晓 — Female, 温暖标准 → 默认通用场景
- `zh-CN-YunxiNeural` 云希 — Male, 活力年轻 → 旁白、Vlog
- `zh-CN-YunjianNeural` 云健 — Male, 成熟权威 → 体育、新闻
- `zh-CN-XiaoyiNeural` 晓伊 — Female, 活泼开朗 → 短视频、抖音
- `zh-CN-YunyangNeural` 云扬 — Male, 深沉专业 → 纪录片、配音
- `zh-CN-YunfengNeural` 云峰 — Male, 浑厚深沉 → 电影预告片


## 豆包 TTS

**Provider:** ByteDance (火山引擎)

| Property | Value |
|----------|-------|
| Cost | ~1 元/万字 (~¥1/10K chars) |
| Built-in voices | 8 + 声音复刻 |
| Max chars / chunk | 280 |
| Max duration / chunk | ~1 分钟 |
| SSML | False |
| Voice cloning | True |
| Clone detail | seed-icl-2.0: 5秒音频即可复刻, 150元/音色/年 |
| Emotion | 情感预测版 (+1元/万字) |
| Dialects | — |
| Languages | 中文、英文、中英混读 |
| Streaming | WebSocket |
| Setup | 中等 |
| Install | `pip install requests` |
| API Key | https://console.volcengine.com/ark/region:ark+cn-beijing/apikey |
| Env vars | `VOLCENGINE_APPID VOLCENGINE_ACCESS_TOKEN` |

### Recommended Voices

- `BV001_streaming` 标准女声 — Female, 标准普通话 → 通用场景
- `BV002_streaming` 标准男声 — Male, 标准普通话 → 通用场景
- `BV003_streaming` 甜美女生 — Female, 甜美亲切 → 客服、导购
- `BV004_streaming` 深沉男声 — Male, 专业深沉 → 纪录片、旁白


## CosyVoice

**Provider:** Alibaba (阿里云百炼)

| Property | Value |
|----------|-------|
| Cost | ~2 元/万字 (~¥2/10K chars) |
| Built-in voices | 7 |
| Max chars / chunk | 400 |
| Max duration / chunk | ~2 分钟 |
| SSML | False |
| Voice cloning | True |
| Clone detail | 音色复刻免费(合成正常计费): 10-20s公网URL音频, 1000音色/账户, 1年不用过期; tts.py clone create --platform cosyvoice |
| Emotion | Via voice style |
| Dialects | — |
| Languages | 中文 |
| Streaming | SDK 流式 |
| Setup | 简单 |
| Install | `pip install dashscope` |
| API Key | https://bailian.console.aliyun.com/ |
| Env vars | `DASHSCOPE_API_KEY` |

### Recommended Voices

- `longxiaochun_v3` 小春 — Female, 活泼 → 短视频、社交媒体
- `longxiaoxia_v3` 小夏 — Female, 温柔 → 有声书、讲故事
- `longxiaobai_v3` 小白 — Female, 可爱 → 儿童、动画
- `longlaotie_v3` 老铁 — Male, 幽默 → 搞笑、休闲内容
- `longchen_v3` 小陈 — Male, 沉稳 → 商务、专业
- `longyuhan_v3` 雨涵 — Female, 知性 → 知识、教育
- `longyue_v3` 小悦 — Female, 甜美 → 客服、导航


## Azure TTS

**Provider:** Microsoft

| Property | Value |
|----------|-------|
| Cost | ~$1/百万字符 (≈¥0.07 (按$1/M)/10K chars) |
| Built-in voices | 20+ + 自定义 |
| Max chars / chunk | 2000 |
| Max duration / chunk | ~10 分钟 |
| SSML | True |
| Voice cloning | True |
| Clone detail | Custom Neural Voice: 需申请白名单, 300+句训练语料, 企业定制 |
| Emotion | Via SSML (mstts:express-as) |
| Dialects | — |
| Languages | 100+ |
| Streaming | SDK 流式 |
| Setup | 中等 |
| Install | `pip install azure-cognitiveservices-speech` |
| API Key | https://portal.azure.com/ |
| Env vars | `AZURE_SPEECH_KEY` |

### Recommended Voices

- `zh-CN-XiaoxiaoNeural` 晓晓 — Female, 温暖标准 → 默认通用场景
- `zh-CN-YunxiNeural` 云希 — Male, 活力年轻 → 旁白、Vlog
- `zh-CN-YunjianNeural` 云健 — Male, 成熟权威 → 体育、新闻
- `zh-CN-YunyangNeural` 云扬 — Male, 深沉专业 → 纪录片、配音
- `zh-CN-XiaochenNeural` 晓辰 — Female, 平静温柔 → 冥想、放松
- `zh-CN-XiaohanNeural` 晓涵 — Female, 柔软亲切 → 讲故事、情感


## 腾讯云 TTS

**Provider:** Tencent

| Property | Value |
|----------|-------|
| Cost | 0.75 元/万字 (¥0.75 (大厂最低)/10K chars) |
| Built-in voices | 380+ + 声音复刻 |
| Max chars / chunk | 150 |
| Max duration / chunk | ~30 秒 |
| SSML | True |
| Voice cloning | True |
| Clone detail | 一句话版(5-15s) / 基础版(10-20min), VoiceClone API |
| Emotion | Via SSML (精品音色) |
| Dialects | 粤语 |
| Languages | 中文、英文、粤语 |
| Streaming | WebSocket |
| Setup | 中等 |
| Install | `pip install tencentcloud-sdk-python-tts` |
| API Key | https://console.cloud.tencent.com/tts |
| Env vars | `TENCENT_SECRET_ID TENCENT_SECRET_KEY` |

### Recommended Voices

- `101001` 标准女声 — Female, 温暖亲切 → 通用场景
- `101002` 标准男声 — Male, 沉稳大气 → 通用场景
- `101004` 可爱童声 — Female, 可爱活泼 → 儿童、故事
- `101005` 新闻男声 — Male, 成熟稳重 → 新闻、播报


## 百度 AI TTS

**Provider:** Baidu

| Property | Value |
|----------|-------|
| Cost | 灵活计费 (按次预付费包/10K chars) |
| Built-in voices | 30+ + 声音复刻 |
| Max chars / chunk | 500 |
| Max duration / chunk | ~2 分钟 |
| SSML | True |
| Voice cloning | True |
| Clone detail | 大模型声音复刻: 任意音频→秒级复刻, 支持方言+情感迁移 |
| Emotion | Native 情感合成 (喜悦/悲伤/中性) |
| Dialects | 上海话、河南话、四川话、湖南话、贵州话 |
| Languages | 中文、英文、日文 |
| Streaming | WebSocket |
| Setup | 简单 |
| Install | `pip install baidu-aip chardet` |
| API Key | https://console.bce.baidu.com/ai/#/ai/speech/overview |
| Env vars | `BAIDU_APP_ID BAIDU_API_KEY BAIDU_SECRET_KEY` |

### Recommended Voices

- `0` 标准女声 — Female, 标准清晰 → 通用场景
- `1` 标准男声 — Male, 标准清晰 → 通用场景
- `3` 度逍遥 — Male, 情感丰富 → 故事、情感内容
- `4` 度丫丫 — Female, 情感丰富 → 故事、情感内容
- `5003` 度琪琪 — Female, 甜美亲切 → 客服、助手
- `5118` 自然男声 — Male, 温和自然 → 对话、播讲


## MiniMax TTS

**Provider:** MiniMax

| Property | Value |
|----------|-------|
| Cost | ~$1/千字符 (≈¥70 (按$0.10/K)/10K chars) |
| Built-in voices | 300+ + 复刻 + Voice Design |
| Max chars / chunk | 3000 |
| Max duration / chunk | ~5 分钟 |
| SSML | False |
| Voice cloning | True |
| Clone detail | 快速复刻: 10s-5min音频, 全球站$1.5/音色(国内站首次使用¥9.9); 新音色为临时音色, 创建后全球站7天/国内站48小时内需正式合成一次(试听不算)否则删除, 用过即永久保留; tts.py clone create --platform minimax |
| Emotion | Native 8种情感 (happy/sad/angry/fearful/calm/whisper...) |
| Dialects | — |
| Languages | 40+ (中/英/日/韩/法/德/西/阿...) |
| Streaming | REST only |
| Setup | 简单 |
| Install | `pip install requests` |
| API Key | https://platform.minimaxi.com/ |
| Env vars | `MINIMAX_API_KEY` |

### Recommended Voices

- `female-shaonv` 少女 — Female, 青春活力 → 通用、社交媒体
- `male-qn-qingse` 青涩青年 — Male, 清澈自然 → Vlog、旁白
- `female-yujie` 御姐 — Female, 成熟优雅 → 专业配音
- `presenter_male` 播音男 — Male, 专业播音 → 新闻、纪录片
- `presenter_female` 播音女 — Female, 专业播音 → 新闻、纪录片
- `female-tianmei` 甜妹 — Female, 甜美可爱 → 客服、二次元


## 讯飞 TTS

**Provider:** iFlytek (科大讯飞)

| Property | Value |
|----------|-------|
| Cost | ~2 元/万字 (~¥2/10K chars) |
| Built-in voices | 500+ + 声音复刻 |
| Max chars / chunk | 200 |
| Max duration / chunk | ~1 分钟 |
| SSML | True |
| Voice cloning | True |
| Clone detail | 一句话复刻(≈3秒): 500万+已创建声音, 130+语种, MOS>4.4 |
| Emotion | Native 超拟人情感 |
| Dialects | 多方言 (粤语/四川话/东北话...) |
| Languages | 130+ (中/英/日/韩/俄/方言语种...) |
| Streaming | WebSocket |
| Setup | 中等 |
| Install | `pip install websocket-client` |
| API Key | https://www.xfyun.cn/ |
| Env vars | `XUNFEI_APP_ID XUNFEI_API_KEY XUNFEI_API_SECRET` |

### Recommended Voices

- `xiaoyan` 小燕 — Female, 甜美标准 → 默认通用
- `xiaoyu` 小宇 — Female, 温柔自然 → 有声书、冥想
- `xiaofeng` 小峰 — Male, 成熟稳重 → 新闻、纪录片
- `xiaomei` 小梅 — Female, 活泼开朗 → 短视频、直播
- `xiaoqian` 小倩 — Female, 亲切温柔 → 客服、助手
- `xiaomeng` 小萌 — Female, 萌系可爱 → 儿童、二次元


## ElevenLabs

**Provider:** ElevenLabs (国际)

| Property | Value |
|----------|-------|
| Cost | 订阅制 $5/月起 (≈¥12 (Starter 档折算)/10K chars) |
| Built-in voices | 20+ 预置 + 复刻 |
| Max chars / chunk | 400 |
| Max duration / chunk | ~2 分钟 |
| SSML | False |
| Voice cloning | True |
| Clone detail | Instant Voice Cloning: 1分钟音频即可复刻 (付费订阅); Professional 版需 30 分钟以上语料 |
| Emotion | Via voice settings (stability/style) |
| Dialects | — |
| Languages | 32 (multilingual v2) |
| Streaming | REST / WebSocket |
| Setup | 简单 (需国际网络) |
| Install | `pip install requests` |
| API Key | https://elevenlabs.io/app/settings/api-keys |
| Env vars | `ELEVENLABS_API_KEY` |

### Recommended Voices

- `21m00Tcm4TlvDq8ikWAM` Rachel — Female, 平静美式 → 默认旁白
- `pNInz6obpgDQGcFmaJgB` Adam — Male, 深沉叙事 → 纪录片、旁白
- `ErXwobaYiN019PkySvjV` Antoni — Male, 圆润自然 → 通用场景
- `EXAVITQu4vr4xnSDxMaL` Bella — Female, 柔和亲切 → 有声书
- `AZnzlk1XvdvUeBnXmlld` Domi — Female, 自信有力 → 宣传、广告
- `TxGEqnHWrfWFTfGW9XjX` Josh — Male, 低沉磁性 → 预告片


## OpenAI TTS

**Provider:** OpenAI (国际)

| Property | Value |
|----------|-------|
| Cost | $15-30/百万字符 (≈¥1-2 (tts-1 / tts-1-hd)/10K chars) |
| Built-in voices | 6 |
| Max chars / chunk | 400 |
| Max duration / chunk | ~2 分钟 |
| SSML | False |
| Voice cloning | False |
| Emotion |  |
| Dialects | — |
| Languages | 50+ (多语言自动识别) |
| Streaming | REST |
| Setup | 简单 (需国际网络) |
| Install | `pip install requests` |
| API Key | https://platform.openai.com/api-keys |
| Env vars | `OPENAI_API_KEY` |

### Recommended Voices

- `alloy` Alloy — Neutral, 中性均衡 → 默认通用
- `echo` Echo — Male, 沉稳 → 旁白
- `fable` Fable — Male, 英伦叙事 → 讲故事
- `onyx` Onyx — Male, 低沉浑厚 → 纪录片
- `nova` Nova — Female, 活力清晰 → 短视频
- `shimmer` Shimmer — Female, 温暖柔和 → 有声书


## Google Cloud TTS

**Provider:** Google (国际)

| Property | Value |
|----------|-------|
| Cost | $16/百万字符 (每月前100万字免费) (≈¥1.2 (Neural2)/10K chars) |
| Built-in voices | 220+ |
| Max chars / chunk | 400 |
| Max duration / chunk | ~2 分钟 |
| SSML | False |
| Voice cloning | False |
| Emotion |  |
| Dialects | — |
| Languages | 40+ (含中文 cmn-CN) |
| Streaming | REST |
| Setup | 简单 (需国际网络) |
| Install | `pip install requests` |
| API Key | https://console.cloud.google.com/apis/credentials |
| Env vars | `GOOGLE_TTS_API_KEY` |

### Recommended Voices

- `en-US-Neural2-F` Neural2-F — Female, 自然美式 → 默认英文
- `en-US-Neural2-D` Neural2-D — Male, 沉稳美式 → 英文旁白
- `en-US-Neural2-J` Neural2-J — Male, 清晰美式 → 英文播报
- `cmn-CN-Wavenet-A` Wavenet-A — Female, 标准普通话 → 中文通用
- `cmn-CN-Wavenet-B` Wavenet-B — Male, 标准普通话 → 中文通用
- `cmn-CN-Wavenet-C` Wavenet-C — Male, 标准普通话 → 中文旁白

---
*Generated by [ttsCN](https://github.com/Agents365-ai/ttsCN) from `data/providers.json`*
