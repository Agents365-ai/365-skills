# Pi: Providers & Custom Models
Source: https://pi.dev/docs/latest/providers, /llama-cpp, /models, /custom-provider

---

> **Auto-built from individual doc pages.**
> Sources: https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/providers.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/llama-cpp.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/models.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/custom-provider.md

## Providers

Most hosted providers support one or both of these authentication methods:

- Sign in through a browser or device flow backed by OAuth.
- Provide an API key.

Use `/login [provider]` to see the methods supported by a provider. Amazon Bedrock and Google Vertex AI can also use ambient cloud credentials.

## Authenticate interactively

Run `/login` and select a provider. Pi guides you through its OAuth or API-key flow and saves the resulting credential in [`auth.json`](configuration.md#agent-directory).

On a remote or headless machine, an OAuth callback may not reach the local process. When prompted, paste the final redirect URL or authorization code back into Pi.

Run `/logout` and select a provider to remove its stored credential. This does not unset environment variables, remove authentication from `models.json`, or revoke the credential at the provider.

`auth.json` can contain API keys and OAuth tokens. Keep it private and do not commit it.

## Use an API key from the environment

Environment variables are useful in CI and anywhere Pi should not store the key. Set the variable before starting Pi:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
pi
```

This table covers providers with a single primary API-key variable. Providers that need additional configuration or support ambient credentials are covered under [Provider Specific Config](#provider-specific-config).

| Provider | Environment variable |
|---|---|
| Anthropic | `ANTHROPIC_API_KEY` |
| Ant Ling | `ANT_LING_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| DeepSeek | `DEEPSEEK_API_KEY` |
| NVIDIA NIM | `NVIDIA_API_KEY` |
| Google Gemini | `GEMINI_API_KEY` |
| GitHub Copilot | `COPILOT_GITHUB_TOKEN` |
| Mistral | `MISTRAL_API_KEY` |
| Groq | `GROQ_API_KEY` |
| Cerebras | `CEREBRAS_API_KEY` |
| xAI | `XAI_API_KEY` |
| OpenRouter | `OPENROUTER_API_KEY` |
| Vercel AI Gateway | `AI_GATEWAY_API_KEY` |
| ZAI Coding Plan (Global) | `ZAI_API_KEY` |
| ZAI Coding Plan (China) | `ZAI_CODING_CN_API_KEY` |
| OpenCode Zen and Go | `OPENCODE_API_KEY` |
| Radius | `RADIUS_API_KEY` |
| TypeSafe ([classifier models](models.md#use-classifier-models)) | `TYPESAFE_API_KEY` |
| Hugging Face | `HF_TOKEN` |
| Fireworks | `FIREWORKS_API_KEY` |
| Together AI | `TOGETHER_API_KEY` |
| Baseten | `BASETEN_API_KEY` |
| Kimi For Coding | `KIMI_API_KEY` |
| Meta | `META_API_KEY` |
| MiniMax | `MINIMAX_API_KEY` |
| MiniMax (China) | `MINIMAX_CN_API_KEY` |
| Moonshot AI (Global and China) | `MOONSHOT_API_KEY` |
| Qwen Token Plan and Individual | `QWEN_TOKEN_PLAN_API_KEY` |
| Qwen Token Plan (China) | `QWEN_TOKEN_PLAN_CN_API_KEY` |
| Xiaomi MiMo | `XIAOMI_API_KEY` |
| Xiaomi MiMo Token Plan (China) | `XIAOMI_TOKEN_PLAN_CN_API_KEY` |
| Xiaomi MiMo Token Plan (Amsterdam) | `XIAOMI_TOKEN_PLAN_AMS_API_KEY` |
| Xiaomi MiMo Token Plan (Singapore) | `XIAOMI_TOKEN_PLAN_SGP_API_KEY` |

Anthropic also recognizes `ANTHROPIC_OAUTH_TOKEN` as an API credential and `ANTHROPIC_AUTH_TOKEN` as bearer authentication.

With no key or token set, Anthropic uses workload identity federation when `ANTHROPIC_FEDERATION_RULE_ID`, `ANTHROPIC_ORGANIZATION_ID` and `ANTHROPIC_IDENTITY_TOKEN_FILE` are set: the Anthropic SDK exchanges the identity token for a short-lived access token and refreshes it itself (re-reading the identity token file, so keep that file fresh for long sessions). `ANTHROPIC_SERVICE_ACCOUNT_ID` and `ANTHROPIC_WORKSPACE_ID` are passed through when set.

## Load an API key from a command

To use a secret manager without writing the resolved key to disk, set a provider's `key` in `auth.json` to a command prefixed with `!`:

```json
{
  "anthropic": {
    "type": "api_key",
    "key": "!security find-generic-password -ws 'anthropic'"
  }
}
```

Pi runs the command when the key is first needed and caches its standard output for the process lifetime. Empty output, a timeout, or a nonzero exit leaves the key unresolved until Pi restarts.

## Provider Specific Config

The providers below have additional setup, need additional settings, or can use credentials supplied by their platform.

A stored API-key credential can include an `env` object. Its values take priority over the process environment for that provider:

```json
{
  "cloudflare-workers-ai": {
    "type": "api_key",
    "key": "...",
    "env": {
      "CLOUDFLARE_ACCOUNT_ID": "account-id"
    }
  }
}
```

### Radius

Radius is a service crafted for Pi by the builders of Pi, Earendil Works. It provides a customizable AI gateway with organization-level controls and analytics built in, and artifacts for sharing what you create with Pi.

To get started, run `/login radius` in Pi. This adds Radius as a provider, and its models appear in `/model` like any other provider's.

Radius also has an MCP server, so Pi can manage Radius for you.

Radius is currently in early alpha and evolving quickly. See [radius.earendil.com](https://radius.earendil.com) for more.

Radius authentication uses its gateway catalog and caches refreshed model metadata for later offline startup. A custom Radius gateway configured in `models.json` uses its own catalog rather than inheriting the public `radius.pi.dev` catalog.

### Azure OpenAI

Set an API key plus either a base URL or resource name:

```bash
export AZURE_OPENAI_API_KEY=...
export AZURE_OPENAI_BASE_URL=https://your-resource.ai.azure.com
# Or:
export AZURE_OPENAI_RESOURCE_NAME=your-resource
```

Resource root URLs under `ai.azure.com`, `cognitiveservices.azure.com`, and `openai.azure.com` are normalized to the OpenAI API path.

### Amazon Bedrock

Bedrock can use a bearer token or an ambient AWS credential source:

```bash
# Named profile
export AWS_PROFILE=your-profile

# IAM keys
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
# Required for temporary credentials
export AWS_SESSION_TOKEN=...

# Bedrock bearer token
export AWS_BEARER_TOKEN_BEDROCK=...

# Region, when not supplied by the profile or AWS SDK configuration
export AWS_REGION=us-west-2
# AWS_DEFAULT_REGION is also supported
```

Pi also supports ECS task credentials and IRSA through the standard `AWS_CONTAINER_CREDENTIALS_*` and `AWS_WEB_IDENTITY_TOKEN_FILE` variables.

### Cloudflare AI Gateway

The gateway requires a token, account ID, and gateway ID:

```bash
export CLOUDFLARE_API_KEY=...
export CLOUDFLARE_ACCOUNT_ID=...
export CLOUDFLARE_GATEWAY_ID=...
```

The account and gateway IDs can come from the process environment or the credential's `env` object in `auth.json`.

`CLOUDFLARE_API_KEY` authenticates Pi to the gateway. Upstream access can use Cloudflare unified billing, credentials stored in the gateway, or an `Authorization` header configured for the provider in `models.json`.

### Cloudflare Workers AI

Workers AI requires a token and account ID:

```bash
export CLOUDFLARE_API_KEY=...
export CLOUDFLARE_ACCOUNT_ID=...
```

The account ID can also be stored in the credential's `env` object.

### Google Vertex AI

Use a Google Cloud API key:

```bash
export GOOGLE_CLOUD_API_KEY=...
```

To use Application Default Credentials, configure a project and location:

```bash
export GOOGLE_CLOUD_PROJECT=your-project
# GCLOUD_PROJECT is also supported
export GOOGLE_CLOUD_LOCATION=us-central1
```

Then authenticate:

```bash
gcloud auth application-default login
```

To use a service-account key file instead, set `GOOGLE_APPLICATION_CREDENTIALS` along with the project and location.

---

## llama.cpp Router Setup

Pi supports the [llama.cpp](https://github.com/ggml-org/llama.cpp) router server. The router discovers multiple GGUF models and loads or unloads them on demand.

Use a current llama.cpp build with router support. Follow the [build instructions](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md) or install a [prebuilt release](https://github.com/ggml-org/llama.cpp/releases) for your platform.

## Start the router

Start `llama-server` without `--model` or `-m`. Passing a model starts single-model mode instead of router mode.

```bash
llama-server \
  --models-dir ~/models \
  --no-models-autoload \
  --jinja \
  --host 127.0.0.1 \
  --port 8080 \
  -ngl 999 \
  -c 32768
```

Important options:

- `--models-dir ~/models` discovers local GGUF files.
- `--no-models-autoload` keeps loading explicit through `/llama`.
- `--jinja` enables compatible chat templates and tool calling.
- `-ngl 999` offloads as many layers as possible to the GPU.
- `-c 32768` sets the context window for each loaded model. Omit it to use the model's native context, which may require substantially more memory.

A single-file model can sit directly in the model directory. Put multimodal and multi-shard models in separate subdirectories:

```text
~/models/
├── llama-3.2-1b-Q4_K_M.gguf
├── gemma-3-4b-it-Q4_K_M/
│   ├── gemma-3-4b-it-Q4_K_M.gguf
│   └── mmproj-F16.gguf
└── large-model-Q4_K_M/
    ├── large-model-Q4_K_M-00001-of-00003.gguf
    ├── large-model-Q4_K_M-00002-of-00003.gguf
    └── large-model-Q4_K_M-00003-of-00003.gguf
```

Restart the router after manually adding files. For per-model context sizes and other options, use [llama.cpp model presets](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md#model-presets).

## Configure Pi

Start Pi and configure the provider:

```text
/login llama.cpp
```

Enter the router URL and optional API key. The default URL is `http://127.0.0.1:8080`.

If you start the router with `--no-models-autoload`, `/login llama.cpp` only stores the connection. Run `/llama` to load a model, then `/model` to select the loaded model for the current session.

Environment variables can configure the same values without `/login`:

```bash
export LLAMA_BASE_URL=http://127.0.0.1:8080
export LLAMA_API_KEY=optional-secret
pi
```

If the server uses an API key, start `llama-server` with the matching `--api-key` value. Keep `--host 127.0.0.1` for local-only access.

## Manage models

Run:

```text
/llama
```

- Select an unloaded model to load it.
- Select a loaded model to unload it.
- Select **Download model…**, search Hugging Face, then choose a repository and quantization. Exact `owner/repository[:quant]` values also work.
- Press Escape during a load or download to confirm cancellation.

Hugging Face search uses `HF_TOKEN` when set, then checks `$HF_TOKEN_PATH`, `$HF_HOME/token`, `$XDG_CACHE_HOME/huggingface/token`, and `~/.cache/huggingface/token`. Search also works without authentication, subject to lower rate limits. Pi warns before downloading gated repositories and links to their access page. The llama.cpp server performs the download, so its process must also have `HF_TOKEN` when the selected repository requires access.

If other models are loaded, Pi asks whether to unload them first or keep them loaded. Pi does not silently unload models and never deletes model files. The router may be shared with other clients, so `/llama` always displays the router's current state.

Loaded and sleeping models appear in `/model`. Sleeping models wake automatically when selected. With router autoload enabled, unloaded preset models also appear and load when selected. With `--no-models-autoload`, load a model through `/llama` before selecting it.

If the router disconnects, `/llama` shows **Retry** and **Close**. Retry reconnects and refreshes model state without replaying the interrupted operation.

## Classification

Every model listed for chat is also listed as a classifier model with the same ID and the `llama-cpp-classify` API. Classifier models answer typed `choice`, `bool`, and `score` questions about JSON state, like TypeSafe's Jev models. The model reaches them from [`codemode`](cli.md#enable-codemode) scripts, and extensions through `ctx.modelRegistry.classify()`; see [Classifier models](models.md#use-classifier-models).

The model does not generate an answer. Each question becomes one chat prompt: the state, every question of the request, the state again, and then the question with its answers under single-token labels. Labels are letters for a choice (up to 62 options), `Yes`/`No` for a bool, and digits for a score (up to 10 levels). The second copy of the state is read with the questions in view, which improved accuracy on JevBench with small models. Pi reads the probabilities of the labels as the next token and normalizes them. A choice returns every option's probability and a confidence of `(n * peak - 1) / (n - 1)`; a score returns the expected level.

- Raw label probabilities are usually overconfident. The per-request `temperature` option divides the label logits before normalizing; values above 1 soften the distribution. It changes no answer.
- Questions run one after another. Everything before the final question is the same for all questions of a request, so the server's prompt cache evaluates it once. The state appears twice, so it needs twice its size in context.
- Small models may follow instructions written inside the state. The prompt tells the model to judge the state as data, but that is not a guarantee.
- Hybrid models such as Qwen3.5 cannot rewind a partially cached prompt without context checkpoints. If each question reprocesses the whole state, start the router with `--ctx-checkpoints 32 --checkpoint-min-step 0`.

## Troubleshooting

Check that the router is reachable:

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/models
```

- **No models in `/llama`:** Check `--models-dir`, the directory layout, and restart the router.
- **Model missing from `/model` with `--no-models-autoload`:** Load it with `/llama` first.
- **Load fails or uses too much memory:** Lower `-c` or unload another model.
- **Server is not in router mode:** Start it without `--model`, `-m`, or `-hf`.

To remove the `llama.cpp` provider and `/llama`, disable `llama.cpp` under Built-in in `pi config`, or set `"extensions": ["-builtin:llama.cpp"]` in [settings](settings.md#resources).

---

## Custom Models

For a built-in provider, start with `/login`, then choose a model with `/model`. Use custom model configuration only when Pi does not already include the provider or endpoint you need.

## Choose a connection

| What you have | Recommended setup |
|---|---|
| A supported subscription | Sign in through `/login` |
| A provider API key | Store it through `/login` or set its environment variable |
| A local GGUF model | Connect Pi to the llama.cpp router |
| An OpenAI-, Anthropic-, or Google-compatible endpoint | Add it to `models.json` |
| A provider with a custom protocol or authentication flow | Build or install a provider extension |

Browse the [model catalog](https://pi.dev/models) for current providers, model IDs, capabilities, context limits, and pricing. Pi starts with its bundled catalog and can overlay newer catalog data from pi.dev. Cached catalog data remains available offline; run `pi update --models` to force a refresh.

## Authenticate

Run `/login` and select a provider. Pi stores credentials in [`auth.json`](configuration.md#agent-directory). Run `/logout` to remove stored credentials for a provider.

You can instead provide an API key through the provider's environment variable. This is useful in CI and other environments where Pi should not write credentials. [Providers](providers.md) lists the variables and provider-specific setup.

When several credential sources are configured, Pi uses a runtime `--api-key` first, then a stored `auth.json` credential, an `apiKey` from `models.json`, and finally the provider's environment variables or ambient cloud credentials. Provider extensions can define their own authentication behavior.

Keep `auth.json` and any credential commands private. Project settings and extensions can execute inside the Pi process after you trust a project. Review [Security](security.md) before loading configuration from an untrusted directory.

## Select a model

Run `/model` to search available models. The picker shows models whose providers have usable authentication. Press `Ctrl+S` on a model to save it as the default for new sessions.

Run `/thinking` to select the thinking level for the current model. Press `Ctrl+S` there to save the startup level. Pi limits the choices to levels supported by the selected model.

`Ctrl+P` cycles through available models. Use `/scoped-models` to control that cycle and save the selection, or configure model patterns through [Settings](settings.md#model-cycling).

A session records model and thinking-level changes. Resuming the session restores them without changing defaults for new sessions.

## Connect local models

Pi integrates directly with the llama.cpp router. The router discovers GGUF files and loads models on demand. Pi's `/llama` command manages the router, while `/model` selects one of its loaded models.

Follow [Local Models with llama.cpp](llama-cpp.md) for server startup, model layout, downloads, and connection troubleshooting.

For Ollama, LM Studio, vLLM, SGLang, and other compatible servers, [configure a compatible endpoint](#configure-a-compatible-endpoint) in `models.json`.

## Configure a compatible endpoint

Use [`models.json`](configuration.md#agent-directory) when an endpoint speaks an API Pi already supports. This includes most Ollama, LM Studio, vLLM, SGLang, and proxy deployments.

```json
{
  "providers": {
    "ollama": {
      "baseUrl": "http://localhost:11434/v1",
      "api": "openai-completions",
      "apiKey": "ollama",
      "models": [
        { "id": "qwen2.5-coder:7b" }
      ]
    }
  }
}
```

The dummy key makes the model available to Pi; Ollama ignores it. For an authenticated endpoint, `apiKey` and header values can use `$NAME` or `${NAME}` environment interpolation, a literal value, or a leading `!command`. Commands in `models.json` run at request time and are not cached by Pi.

Opening `/model` reloads the file. A `models` entry adds or replaces a model with the same ID on that provider. Use `modelOverrides` to change metadata for an existing built-in or extension-provided model without replacing the provider's model list. Unknown override IDs are ignored.

### Describe model input and caching

Use `inputLimits.images.resize` to control how Pi encodes new image attachments, `read` results, and tool-result images before storing them in conversation history:

```json
{
  "id": "vision-model",
  "input": ["text", "image"],
  "inputLimits": {
    "images": {
      "resize": {
        "maxWidth": 1568,
        "maxHeight": 1568,
        "maxBytes": 524288,
        "jpegQuality": 75
      }
    }
  }
}
```

`maxBytes` limits the base64-encoded payload. Omitted resize fields use conservative defaults of 2000 by 2000 pixels, 4.5 MiB encoded, and JPEG quality 80. Images are encoded once; changing models does not rewrite historical images. The catalog can also describe hard request limits with `inputLimits.maxRequestBytes`, `images.maxPerMessage`, and `images.maxPerRequest`, but Pi does not yet rewrite or reject history based on them.

<a id="prompt-cache-lifetimes"></a>

Use `promptCache` to declare the provider's best-effort cache lifetime in seconds for the `short` or `long` retention tier:

```json
{ "id": "claude-sonnet-5", "promptCache": { "short": 300, "long": 3600 } }
```

Choose the conservative end of any published range. A model without a lifetime for the active tier is not eligible for cache warming. A `modelOverrides` entry can set `inputLimits` or `promptCache` for a built-in or extension model, including a model accessed through a validated proxy. See [`cacheWarming`](settings.md#model-and-thinking).

Compatibility settings should describe verified differences in the endpoint's request or response behavior. Do not enable them based only on an endpoint advertising OpenAI or Anthropic compatibility.

## Use classifier models

Classifier models do not chat. They answer typed questions about JSON state: pick one of several choices, answer yes or no, or give a score, each with probabilities. Pi includes TypeSafe's Jev model from these providers, and Cloudflare's Clef and Clef Flash models from Workers AI:

| Provider | Model IDs | Authentication |
|---|---|---|
| `typesafe` | `jev-latest` | `TYPESAFE_API_KEY` |
| `openrouter` | `typesafe/jev-1.13`, `~typesafe/jev-latest` | `OPENROUTER_API_KEY` or `/login` |
| `cloudflare-workers-ai` | `typesafe/jev`, `@cf/cloudflare/clef`, `@cf/cloudflare/clef-flash` | `CLOUDFLARE_API_KEY` and `CLOUDFLARE_ACCOUNT_ID` |
| `vercel-ai-gateway` | `typesafe-ai/jev` | `AI_GATEWAY_API_KEY` |
| `opencode` | `jev-1.13`, `jev-1.13-free` | `OPENCODE_API_KEY` |

Chat models on a [llama.cpp router](llama-cpp.md#classification) are also listed as classifier models.

Classifier models do not appear in `/model`. The model reaches them through the [`codemode`](cli.md#enable-codemode) tool, which is off unless an MCP server turned it on. Enable it with `"defaultTools": ["+codemode"]` in [settings](settings.md#tools). Scripts then list classifier models with `models.getAvailableOfType("classifier")` and call `models.classify(model, { state, questions })`:

```js
const jev = await models.getModelOfType("classifier", "typesafe", "jev-latest");
const result = await models.classify(jev, {
  state: { message: "The change works, thanks." },
  questions: {
    approved: {
      type: "bool",
      instructions: "Does the user approve of the result?",
      criteria: { true: "Approval", false: "No approval" },
    },
  },
});
return result.answers;
```

[Codemode](codemode.md#classify) describes the question and answer types.

When the service reports token counts, as all System One services do, `result.usage` carries them with their cost. Pi adds the usage of a script's classifier calls to the `codemode` tool result, so it counts toward the session cost in the footer and `/session`. The cost uses the model's catalog price; models without one, such as TypeSafe's direct `jev-latest`, report tokens at no cost.

Extensions call classifiers through `ctx.modelRegistry.classify()`, without codemode. [Virtual models](virtual-models.md#route-requests) can use them to route requests; see the `jev-router.ts` example.

## Use image models

Image models generate images from a prompt and optional input images. Pi lists OpenRouter's image models, such as `google/gemini-2.5-flash-image` and `black-forest-labs/flux.2-pro`, under the `openrouter` provider; they use the same `OPENROUTER_API_KEY` or `/login` credential as its chat models.

Like classifier models, image models do not appear in `/model`; the model reaches them through the [`codemode`](cli.md#enable-codemode) tool. Scripts list them with `models.getAvailableOfType("image")` and call `models.generateImages(model, { input })`. The result's `output` holds base64 image blocks, which `image()` attaches to the `codemode` result so the model sees them:

```js
const painter = await models.getModelOfType("image", "openrouter", "google/gemini-2.5-flash-image");
const result = await models.generateImages(painter, {
  input: [{ type: "text", text: "A red fox in the snow, watercolor" }],
});
if (result.stopReason !== "stop") return result.errorMessage;
for (const block of result.output) if (block.type === "image") image(block);
```

`input` can also contain `{ type: "image", data, mimeType }` blocks to edit or use as references. Pi adds the usage of a script's image calls to the `codemode` tool result, like classifier calls. Generated images are not saved to disk. [Codemode](codemode.md#generate-images) describes the full API.

Extensions generate images through `ctx.modelRegistry.generateImages()`, without codemode.

## Add a custom provider

Use an extension when the provider needs custom streaming, model discovery, or authentication behavior. See [Custom Providers](custom-provider.md) for the extension workflow.

## Troubleshooting

### A model does not appear

Confirm that its provider has usable authentication. Custom models can load from `models.json` but remain unavailable in `/model` until Pi can resolve credentials. For llama.cpp, only models currently loaded by the router appear.

### Authentication works in one shell only

Check whether the key came from an environment variable rather than `auth.json`. Environment variables must be present in the process that starts Pi.

### Sign-in opens a browser on a remote machine

Complete the provider's headless authentication flow when available. Some providers let you paste the final redirect URL or authorization code back into Pi. See [Authenticate interactively](providers.md#authenticate-interactively).

### A compatible endpoint rejects requests

Check its API type and compatibility settings in `models.json`. The upstream server must support the corresponding request fields and behavior.

---

## Custom Providers

A provider extension connects Pi to a model service that needs custom authentication, model discovery, request handling, or streaming. If the service already speaks a supported API, configure it in `models.json` instead.

Provider extensions run inside Pi and can inspect credentials, prompts, tool definitions, model responses, and usage. Treat them as trusted code and avoid logging secrets or provider payloads.

## Choose the smallest integration

| Requirement | Use |
|---|---|
| Add models behind a supported API | [`models.json`](models.md#configure-a-compatible-endpoint) |
| Change an existing provider endpoint or headers | `models.json` or a small provider extension |
| Discover models dynamically | A provider with `refreshModels` |
| Add a `/login` flow | A provider with native or legacy OAuth configuration |
| Implement an unsupported wire protocol | A provider with `stream` or `streamSimple` |

A provider extension is an [extension](extensions.md), so it follows the same loading, trust, reload, and error behavior.

## Register a provider

Call `pi.registerProvider()` from the extension factory. Pi waits for asynchronous factories before startup continues, so providers registered there are available to startup model selection and `pi --list-models`.

There are two registration forms:

- Register a complete `Provider` from `@earendil-works/pi-ai` for native authentication, filtering, discovery, refresh, and streaming behavior.
- Register a provider name with `ProviderConfig` for the legacy configuration form used by existing extensions.

Prefer a complete provider for new integrations that own more than static endpoint and model metadata. Pi composes `models.json` overrides above a registered native provider.

Registering only `baseUrl` or `headers` for an existing provider preserves its built-in models. Supplying `models` in the legacy form replaces that provider's models across chat, image, and classifier operations. An omitted `type` means `"chat"`; image and classifier models require explicit discriminants and implementations keyed by their `api` values through the `images` and `classifiers` fields.

For example, a mixed-operation provider can register non-chat models and their implementations together:

```typescript
pi.registerProvider("media-tools", {
  apiKey: "$MEDIA_TOOLS_API_KEY",
  models: [
    {
      type: "image",
      id: "image-v1",
      name: "Image V1",
      api: "media-images",
      baseUrl: "https://media.example.com/v1",
      input: ["text"],
      output: ["image"],
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
    },
    {
      type: "classifier",
      id: "classifier-v1",
      name: "Classifier V1",
      api: "media-classifier",
      baseUrl: "https://media.example.com/v1",
      input: ["text"],
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
      contextWindow: 64000,
    },
  ],
  images: {
    "media-images": { generateImages: async (model, context, options) => result },
  },
  classifiers: {
    "media-classifier": { classify: async (model, context, options) => result },
  },
});
```

Model-level `baseUrl` values take precedence over the provider endpoint. If no `models` list is supplied, built-in models of every operation remain registered. Equal model IDs in different operations remain distinct, including their model-specific headers.

Calls made after initial extension loading take effect immediately. Use `pi.unregisterProvider()` to remove the dynamic provider and restore built-in behavior that it replaced.

See the checked [GitLab Duo provider](../examples/extensions/custom-provider-gitlab-duo/) for a complete registration that delegates streaming to built-in API implementations.

## Provide authentication

Static providers can resolve an API key from a literal, environment interpolation, or a command. These values use the same syntax as `models.json`:

- `$NAME` and `${NAME}` read environment variables.
- A leading `!command` uses command output.
- `$$` emits a literal `$`.
- `$!` emits a literal leading `!`.

Use native provider authentication when the integration needs stored credentials, custom resolution, provider-scoped environment, or multiple login methods.

An OAuth provider supplies a display name, login flow, token refresh, and access-token resolution. After registration it appears in `/login`, and Pi stores returned credentials in `~/.pi/agent/auth.json`.

OAuth callbacks are UI-neutral. They can open an authorization URL, show a device code, report progress, request input, or ask the user to choose a login method. Honor cancellation and the supplied abort signal during network requests.

Never write access tokens, refresh tokens, authorization headers, or complete provider responses to ordinary logs.

## Supply and refresh models

Every model needs an ID, display name, input capabilities, and cost metadata. Chat and classifier models also need a context window; chat models need an output limit and reasoning support; image models declare their output modalities. Choose the API implementation at the provider level unless one model requires an override.

Set `promptCache.short` or `promptCache.long` to the provider's best-effort cache lifetime in seconds when Pi should keep an idle prompt cache warm. Leave them unset to disable cache warming for that retention tier.

Compatibility flags describe verified differences in an otherwise supported API. Do not enable them based only on an endpoint claiming compatibility.

Confirm the request fields and response behavior against the actual server.

Use `refreshModels` when the available catalog comes from a live service. Pass `context.signal` to blocking I/O so callers can cancel refreshes.

The two registration forms have different refresh contracts:

- A complete `Provider` returns nothing. It calls `context.publish({ update })` to install provider-owned model state, after which its synchronous `getModels()` exposes the latest list.
- Legacy `ProviderConfig.refreshModels` returns mixed-operation model definitions. Pi replaces that registration’s live models with the returned list and applies any requested persistence.

Publish persisted catalog data only when it should survive across runs. A live service such as llama.cpp can update its in-memory list without persisting it; a remote catalog can retain a snapshot for offline startup.

## Reuse a supported streaming API

Use one of Pi AI’s API implementations whenever the provider protocol matches it.

Supported implementations cover Anthropic Messages, OpenAI Chat Completions and Responses, Google Generative AI and Vertex, Azure OpenAI Responses, Mistral Conversations, and Bedrock Converse.

The provider can still customize authentication, base URLs, headers, model filtering, and discovery while delegating request conversion and streaming to an existing API implementation.

This is safer than copying a stream implementation because it preserves Pi’s message conversion, tool handling, usage accounting, cancellation, and compatibility behavior.

## Implement custom streaming

Implement `streamSimple` only when no existing API implementation can represent the service. Study the implementations under [`packages/ai/src/api`](https://github.com/earendil-works/pi/tree/main/packages/ai/src/api) first.

The stream receives a normalized `TranscriptContext`. System prompts and tool declarations live in transcript system messages, so read them with `getCurrentSystemPrompt(context.messages)` and `getCurrentTools(context.messages)` rather than expecting `context.systemPrompt` or `context.tools`. A model that supports mid-conversation system messages can receive them in place; otherwise call `collapseSystemMessages(context)` to fold later system messages into the leading one.

A custom stream must:

1. Create an assistant message with provider, model, timestamp, pending stop reason, content, and zeroed usage.
2. After request setup succeeds, emit one `start` event before content events.
3. Update the message while emitting balanced text, thinking, and tool-call events.
4. Finalize usage, cost, content, and stop reason.
5. Emit exactly one terminal `done` or `error` event and close the stream.
6. Convert cancellation into an aborted result.

Request setup can fail before `start`; in that case the stream can terminate directly with `error`. Missing request authentication may also throw synchronously before a stream is returned.

Content indexes refer to blocks in the assistant message. Update each block before emitting the event whose `partial` field exposes that state. Tool-call arguments must contain valid parsed input by `toolcall_end`.

The stream must also honor request instrumentation supplied through `SimpleStreamOptions`:

- Call `options.onPayload` before sending the provider request and use any replacement payload it returns.
- Call `options.onResponse` after receiving the response but before consuming its body.
- Await `options.onProviderStreamEvent?.(providerEvent, model)` for each parsed provider event before normalizing it.
- Pass through the abort signal and provider-scoped environment.

These hooks power extension request inspection, response-header events, and provider-stream observation. Omitting them makes the provider behave differently from Pi’s built-in providers.

## Report failures and usage

Set a concrete terminal stop reason. Error and aborted messages need an `errorMessage`; successful messages need accurate input, output, cache, total-token, and cost values.

Pi can compact and retry after recognized context-overflow errors. If the service uses an unknown message, normalize only that provider’s overflow response to `context_length_exceeded` in a guarded `message_end` handler.

Do not rewrite rate limits or transient provider failures as context overflow. Those failures use Pi’s normal retry behavior instead.

## Test the integration

Test at least:

- ordinary and empty text responses
- tool calls and tool results
- image input and image tool results when supported
- usage and cost accounting
- abort behavior
- context overflow
- malformed or partial streams
- Unicode boundaries
- cross-provider session handoff
- authentication refresh and cancellation

The provider tests under [`packages/ai/test`](https://github.com/earendil-works/pi/tree/main/packages/ai/test) define the behavior expected from built-in providers. Adapt the relevant suites rather than relying only on manual prompts.

Run the extension directly while developing, then move it to a discovered extension location or distribute it through a [Pi package](packages.md). Use `/reload` after changing a discovered provider extension in an active session.
