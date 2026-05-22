import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";

import { readJsonFile } from "./fs.mjs";
import { PiRpcClient } from "./pi-rpc.mjs";
import { binaryAvailable } from "./process.mjs";

const TASK_THREAD_PREFIX = "Pi Companion Task";
const DEFAULT_CONTINUE_PROMPT =
  "Continue from the current session state. Pick the next highest-value step and follow through until the task is resolved.";

const REVIEW_TOOLS = ["read", "grep", "find", "ls"];

const VALID_THINKING_LEVELS = new Set(["off", "minimal", "low", "medium", "high", "xhigh"]);

function cleanPiStderr(stderr) {
  return stderr
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter(Boolean)
    .join("\n");
}

function shorten(text, limit = 72) {
  const normalized = String(text ?? "").trim().replace(/\s+/g, " ");
  if (!normalized) {
    return "";
  }
  if (normalized.length <= limit) {
    return normalized;
  }
  return `${normalized.slice(0, limit - 3)}...`;
}

function looksLikeVerificationCommand(command) {
  return /\b(test|tests|lint|build|typecheck|type-check|check|verify|validate|pytest|jest|vitest|cargo test|npm test|pnpm test|yarn test|go test|mvn test|gradle test|tsc|eslint|ruff)\b/i.test(
    command
  );
}

function buildTaskThreadName(prompt) {
  const excerpt = shorten(prompt, 56);
  return excerpt ? `${TASK_THREAD_PREFIX}: ${excerpt}` : TASK_THREAD_PREFIX;
}

function normalizeReasoningText(text) {
  return String(text ?? "").replace(/\s+/g, " ").trim();
}

function mergeReasoningSections(existingSections, nextSections) {
  const merged = [];
  for (const section of [...existingSections, ...nextSections]) {
    const normalized = normalizeReasoningText(section);
    if (!normalized || merged.includes(normalized)) {
      continue;
    }
    merged.push(normalized);
  }
  return merged;
}

function emitProgress(onProgress, message, phase = null, extra = {}) {
  if (!onProgress || !message) {
    return;
  }
  if (!phase && Object.keys(extra).length === 0) {
    onProgress(message);
    return;
  }
  onProgress({ message, phase, ...extra });
}

function emitLogEvent(onProgress, options = {}) {
  if (!onProgress) {
    return;
  }
  onProgress({
    message: options.message ?? "",
    phase: options.phase ?? null,
    stderrMessage: options.stderrMessage ?? null,
    logTitle: options.logTitle ?? null,
    logBody: options.logBody ?? null
  });
}

function extractAssistantText(message) {
  if (!message || !Array.isArray(message.content)) {
    return "";
  }
  return message.content
    .filter((block) => block?.type === "text" && typeof block.text === "string")
    .map((block) => block.text)
    .join("");
}

function extractAssistantThinking(message) {
  if (!message || !Array.isArray(message.content)) {
    return [];
  }
  return message.content
    .filter((block) => block?.type === "thinking" && typeof block.thinking === "string")
    .map((block) => normalizeReasoningText(block.thinking))
    .filter(Boolean);
}

function describeToolStart(toolName, args) {
  if (toolName === "bash") {
    const command = String(args?.command ?? "");
    return {
      message: `Running command: ${shorten(command, 96)}`,
      phase: looksLikeVerificationCommand(command) ? "verifying" : "running"
    };
  }
  if (toolName === "edit" || toolName === "write") {
    const filePath = String(args?.path ?? args?.file_path ?? args?.target ?? "");
    return {
      message: filePath ? `Applying file change: ${filePath}` : "Applying file change.",
      phase: "editing"
    };
  }
  if (toolName === "read") {
    const filePath = String(args?.path ?? args?.file_path ?? "");
    return {
      message: filePath ? `Reading file: ${filePath}` : "Reading file.",
      phase: "investigating"
    };
  }
  if (toolName === "grep" || toolName === "find" || toolName === "ls") {
    return {
      message: `Running tool: ${toolName}.`,
      phase: "investigating"
    };
  }
  return {
    message: `Calling tool: ${toolName}.`,
    phase: "investigating"
  };
}

function describeToolEnd(toolName, args, result, isError) {
  if (toolName === "bash") {
    const command = String(args?.command ?? "");
    const exitCode = result?.details?.exitCode;
    const exitText = typeof exitCode === "number" ? `exit ${exitCode}` : isError ? "error" : "ok";
    return {
      message: `Command completed: ${shorten(command, 96)} (${exitText})`,
      phase: looksLikeVerificationCommand(command) ? "verifying" : "running"
    };
  }
  if (toolName === "edit" || toolName === "write") {
    const filePath = String(args?.path ?? args?.file_path ?? args?.target ?? "");
    return {
      message: isError
        ? `File change failed${filePath ? `: ${filePath}` : ""}.`
        : `File changes ${filePath ? `applied: ${filePath}` : "applied"}.`,
      phase: "editing"
    };
  }
  return {
    message: `Tool ${toolName} ${isError ? "failed" : "completed"}.`,
    phase: "investigating"
  };
}

function recordToolForResult(state, toolName, args, result, isError) {
  if (toolName === "edit" || toolName === "write") {
    const filePath = args?.path ?? args?.file_path ?? args?.target ?? null;
    if (filePath) {
      state.fileChanges.push({
        type: "fileChange",
        status: isError ? "failed" : "completed",
        changes: [{ path: String(filePath), status: isError ? "failed" : "applied" }]
      });
    }
    return;
  }
  if (toolName === "bash") {
    state.commandExecutions.push({
      type: "commandExecution",
      command: String(args?.command ?? ""),
      status: isError ? "failed" : "completed",
      exitCode: result?.details?.exitCode ?? null
    });
  }
}

function collectTouchedFiles(fileChanges) {
  const paths = new Set();
  for (const fileChange of fileChanges) {
    for (const change of fileChange.changes ?? []) {
      if (change.path) {
        paths.add(change.path);
      }
    }
  }
  return [...paths];
}

function createTurnCaptureState(options = {}) {
  return {
    sessionId: null,
    sessionFile: null,
    turnId: null,
    finalTurn: null,
    lastAgentMessage: "",
    reviewText: "",
    reasoningSummary: [],
    error: null,
    fileChanges: [],
    commandExecutions: [],
    completed: false,
    onProgress: options.onProgress ?? null
  };
}

function handlePiEvent(state, event) {
  switch (event.type) {
    case "agent_start":
      emitProgress(state.onProgress, "Pi agent started.", "starting");
      return;
    case "turn_start":
      emitProgress(state.onProgress, "Turn started.", "starting");
      return;
    case "tool_execution_start": {
      const description = describeToolStart(event.toolName, event.args);
      emitProgress(state.onProgress, description.message, description.phase);
      return;
    }
    case "tool_execution_end": {
      const description = describeToolEnd(event.toolName, event.args, event.result, Boolean(event.isError));
      emitProgress(state.onProgress, description.message, description.phase);
      recordToolForResult(state, event.toolName, event.args, event.result, Boolean(event.isError));
      return;
    }
    case "message_end": {
      const text = extractAssistantText(event.message);
      const thinking = extractAssistantThinking(event.message);
      if (text) {
        state.lastAgentMessage = text;
        emitLogEvent(state.onProgress, {
          message: `Assistant message captured: ${shorten(text, 96)}`,
          phase: "finalizing",
          logTitle: "Assistant message",
          logBody: text
        });
      }
      if (thinking.length > 0) {
        state.reasoningSummary = mergeReasoningSections(state.reasoningSummary, thinking);
        emitLogEvent(state.onProgress, {
          message: `Reasoning summary captured: ${shorten(thinking[0], 96)}`,
          logTitle: "Reasoning summary",
          logBody: thinking.map((section) => `- ${section}`).join("\n")
        });
      }
      return;
    }
    case "auto_retry_start":
      emitProgress(
        state.onProgress,
        `Pi auto-retrying after transient error (attempt ${event.attempt}/${event.maxAttempts}).`,
        null
      );
      return;
    case "auto_retry_end":
      if (event.success === false) {
        state.error = { message: event.finalError ?? "auto-retry exhausted" };
        emitProgress(state.onProgress, `Pi error: ${state.error.message}`, "failed");
      }
      return;
    case "compaction_start":
      emitProgress(state.onProgress, `Compaction (${event.reason}) started.`, null);
      return;
    case "compaction_end":
      if (event.aborted) {
        emitProgress(state.onProgress, "Compaction aborted.", null);
      } else if (event.errorMessage) {
        emitProgress(state.onProgress, `Compaction failed: ${event.errorMessage}`, null);
      } else {
        emitProgress(state.onProgress, "Compaction completed.", null);
      }
      return;
    case "agent_end":
      // Final message is captured by message_end; nothing additional to do.
      // Caller resolves the completion promise separately.
      return;
    default:
      return;
  }
}

function declineExtensionUi(client, request) {
  if (request.method === "select" || request.method === "input" || request.method === "editor") {
    client.respondToUi(request.id, { cancelled: true });
    return;
  }
  if (request.method === "confirm") {
    client.respondToUi(request.id, { confirmed: false });
    return;
  }
  // Fire-and-forget methods need no response.
}

function buildSpawnArgs(options = {}) {
  const args = [];

  if (options.resumeSession) {
    args.push("--session", options.resumeSession);
  } else if (options.noSession) {
    args.push("--no-session");
  }

  if (options.sandbox === "read-only") {
    args.push("--tools", REVIEW_TOOLS.join(","));
  }

  if (options.disableExtensions) {
    args.push("--no-extensions");
  }
  if (options.disablePromptTemplates) {
    args.push("--no-prompt-templates");
  }

  if (options.model) {
    args.push("--model", String(options.model));
  }
  if (options.provider) {
    args.push("--provider", String(options.provider));
  }

  if (Array.isArray(options.extraArgs)) {
    args.push(...options.extraArgs);
  }

  return args;
}

async function withPiRpc(cwd, options, fn) {
  const client = new PiRpcClient(cwd, {
    spawnArgs: buildSpawnArgs(options),
    env: options.env ?? process.env
  });
  client.setUiHandler((request) => declineExtensionUi(client, request));
  try {
    await client.start();
    return await fn(client);
  } finally {
    await client.close().catch(() => {});
  }
}

async function runPiAgentRun(client, prompt, options = {}) {
  const state = createTurnCaptureState({ onProgress: options.onProgress });

  // Capture session metadata once available.
  try {
    const initialState = await client.getState();
    if (initialState?.sessionId) {
      state.sessionId = initialState.sessionId;
      emitProgress(options.onProgress, `Session ready (${state.sessionId}).`, "starting", {
        piSessionId: state.sessionId,
        piSessionFile: initialState.sessionFile ?? null
      });
      state.sessionFile = initialState.sessionFile ?? null;
    }
  } catch {
    // pi older than expected — proceed without session metadata.
  }

  if (options.sessionName) {
    try {
      await client.setSessionName(options.sessionName);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      // best-effort: pi versions without set_session_name should not block the run.
      // Log only when the failure shape is not the expected "method not found",
      // since that case is part of the soft contract.
      if (!/method|command|unknown/i.test(msg)) {
        process.stderr.write(`[pi] note: set_session_name failed: ${msg}\n`);
      }
    }
  }

  if (options.effort && VALID_THINKING_LEVELS.has(options.effort)) {
    try {
      await client.setThinkingLevel(options.effort);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      process.stderr.write(
        `[pi] note: thinking level "${options.effort}" requested but pi rejected it (${msg}). The configured model may not support thinking.\n`
      );
    }
  }

  let agentEndResolve;
  let agentEndReject;
  const agentEndPromise = new Promise((resolve, reject) => {
    agentEndResolve = resolve;
    agentEndReject = reject;
  });

  const detachHandler = () => client.setEventHandler(null);

  client.setEventHandler((event) => {
    try {
      handlePiEvent(state, event);
    } catch (err) {
      detachHandler();
      agentEndReject(err);
      return;
    }
    if (event.type === "agent_end") {
      state.completed = true;
      agentEndResolve(event);
    }
  });

  try {
    await client.sendPrompt(prompt);
  } catch (error) {
    // Detach the handler so any late stdout events cannot trigger a dangling
    // rejection on agentEndPromise (which nobody is awaiting after this early
    // return). Node ≥15 terminates the process on unhandled rejection.
    detachHandler();
    agentEndResolve();
    state.error = { message: error instanceof Error ? error.message : String(error) };
    state.completed = false;
    state.finalTurn = { id: state.turnId ?? "rejected", status: "failed" };
    return state;
  }

  // Race against the client's exit promise so that a crashing pi process which
  // never emits agent_end does not deadlock the run. If the pi process exits
  // first, treat that as a failure and surface the captured exit error.
  await Promise.race([agentEndPromise, client.exitPromise]);
  detachHandler();

  if (!state.completed) {
    const exitErrorMessage =
      client.exitError instanceof Error ? client.exitError.message : "pi exited before agent_end";
    state.error = state.error ?? { message: exitErrorMessage };
    state.finalTurn = { id: state.turnId ?? "interrupted", status: "failed" };
    return state;
  }

  // After agent_end, fetch the canonical last assistant text and current
  // session info. Skip if pi already tore down its stdin pipe; otherwise the
  // silent catch would shadow the streamed message_end capture with an empty
  // value if the RPC happens to succeed against a half-closed pipe.
  const stdinAlive = Boolean(client.proc?.stdin && !client.proc.stdin.destroyed && !client.closed);
  if (stdinAlive) {
    try {
      const final = await client.getLastAssistantText();
      if (final && typeof final.text === "string" && final.text) {
        state.lastAgentMessage = final.text;
      }
    } catch {
      // pi may already be tearing down; rely on streamed message_end
    }

    try {
      const finalState = await client.getState();
      if (finalState?.sessionId && !state.sessionId) {
        state.sessionId = finalState.sessionId;
      }
      if (finalState?.sessionFile && !state.sessionFile) {
        state.sessionFile = finalState.sessionFile;
      }
    } catch {
      // tolerate teardown races
    }
  }

  state.finalTurn = {
    id: state.turnId ?? "single-turn",
    status: state.error ? "failed" : "completed"
  };
  return state;
}

function buildResultStatus(turnState) {
  return turnState.finalTurn?.status === "completed" ? 0 : 1;
}

export function getPiAvailability(cwd) {
  const versionStatus = binaryAvailable("pi", ["--version"], { cwd });
  if (!versionStatus.available) {
    return {
      available: false,
      detail: `pi CLI is not installed. Install with \`npm install -g --ignore-scripts @earendil-works/pi-coding-agent\`. (${versionStatus.detail})`
    };
  }

  return {
    available: true,
    detail: versionStatus.detail
  };
}

export function getPiModelsStatus(env = process.env) {
  const envHints = [];
  if (env.DEEPSEEK_API_KEY) {
    envHints.push("DEEPSEEK_API_KEY");
  }
  if (env.OPENAI_API_KEY) {
    envHints.push("OPENAI_API_KEY");
  }
  if (env.ANTHROPIC_API_KEY) {
    envHints.push("ANTHROPIC_API_KEY");
  }
  if (env.GOOGLE_API_KEY) {
    envHints.push("GOOGLE_API_KEY");
  }

  const piDir = env.PI_CODING_AGENT_DIR || path.join(os.homedir(), ".pi", "agent");
  const modelsPath = path.join(piDir, "models.json");
  let modelsFileExists = false;
  let providerCount = 0;
  try {
    if (fs.existsSync(modelsPath)) {
      modelsFileExists = true;
      const parsed = JSON.parse(fs.readFileSync(modelsPath, "utf8"));
      if (parsed && typeof parsed.providers === "object") {
        providerCount = Object.keys(parsed.providers).length;
      }
    }
  } catch {
    // ignore parse errors; treated as no providers configured
  }

  if (envHints.length === 0 && providerCount === 0) {
    return {
      available: false,
      detail: `No provider API key in env and no providers configured at ${modelsPath}`,
      modelsPath,
      modelsFileExists,
      providerCount,
      envHints
    };
  }

  const detailParts = [];
  if (providerCount > 0) {
    detailParts.push(`${providerCount} provider${providerCount === 1 ? "" : "s"} in ${modelsPath}`);
  }
  if (envHints.length > 0) {
    detailParts.push(`env keys: ${envHints.join(", ")}`);
  }

  return {
    available: true,
    detail: detailParts.join("; "),
    modelsPath,
    modelsFileExists,
    providerCount,
    envHints
  };
}

export function getSessionRuntimeStatus(_env = process.env, _cwd = process.cwd()) {
  return {
    mode: "direct",
    label: "direct startup",
    detail:
      "Each Pi command spawns a dedicated pi --mode rpc subprocess. There is no shared runtime to attach to."
  };
}

export async function interruptAppServerTurn(_cwd, _options = {}) {
  return {
    attempted: false,
    interrupted: false,
    transport: null,
    detail: "Pi has no shared runtime; cancellation is delivered by terminating the worker process."
  };
}

export async function runAppServerReview(cwd, options = {}) {
  const availability = getPiAvailability(cwd);
  if (!availability.available) {
    throw new Error(availability.detail);
  }

  return withPiRpc(
    cwd,
    {
      env: options.env,
      noSession: true,
      sandbox: "read-only",
      disableExtensions: true,
      disablePromptTemplates: true,
      model: options.model
    },
    async (client) => {
      emitProgress(options.onProgress, "Starting Pi review session.", "starting");
      const state = await runPiAgentRun(client, options.prompt, {
        onProgress: options.onProgress,
        effort: options.effort,
        sessionName: options.threadName
      });

      return {
        status: buildResultStatus(state),
        piSessionId: state.sessionId,
        piSessionFile: state.sessionFile,
        turnId: state.turnId,
        reviewText: state.lastAgentMessage,
        reasoningSummary: state.reasoningSummary,
        turn: state.finalTurn,
        error: state.error,
        stderr: cleanPiStderr(client.stderr)
      };
    }
  );
}

export async function runAppServerTurn(cwd, options = {}) {
  const availability = getPiAvailability(cwd);
  if (!availability.available) {
    throw new Error(availability.detail);
  }

  const prompt = options.prompt?.trim() || options.defaultPrompt || "";
  if (!prompt) {
    throw new Error("A prompt is required for this Pi run.");
  }

  return withPiRpc(
    cwd,
    {
      env: options.env,
      resumeSession: options.resumeSessionId ?? null,
      noSession: false,
      sandbox: options.sandbox ?? null,
      model: options.model
    },
    async (client) => {
      emitProgress(
        options.onProgress,
        options.resumeSessionId ? `Resuming session ${options.resumeSessionId}.` : "Starting Pi task session.",
        "starting"
      );

      const state = await runPiAgentRun(client, prompt, {
        onProgress: options.onProgress,
        effort: options.effort,
        sessionName: options.persistThread ? options.threadName : options.threadName ?? null
      });

      return {
        status: buildResultStatus(state),
        piSessionId: state.sessionId,
        piSessionFile: state.sessionFile,
        turnId: state.turnId,
        finalMessage: state.lastAgentMessage,
        reasoningSummary: state.reasoningSummary,
        turn: state.finalTurn,
        error: state.error,
        stderr: cleanPiStderr(client.stderr),
        fileChanges: state.fileChanges,
        touchedFiles: collectTouchedFiles(state.fileChanges),
        commandExecutions: state.commandExecutions
      };
    }
  );
}

export function buildPersistentTaskThreadName(prompt) {
  return buildTaskThreadName(prompt);
}

export function parseStructuredOutput(rawOutput, fallback = {}) {
  if (!rawOutput) {
    return {
      parsed: null,
      parseError: fallback.failureMessage ?? "Pi did not return a final structured message.",
      rawOutput: rawOutput ?? "",
      ...fallback
    };
  }

  const trimmed = rawOutput.trim();
  const fenced = trimmed.match(/```json\s*([\s\S]*?)```/i) ?? trimmed.match(/```\s*([\s\S]*?)```/);
  const candidate = fenced ? fenced[1].trim() : trimmed;

  try {
    return {
      parsed: JSON.parse(candidate),
      parseError: null,
      rawOutput,
      ...fallback
    };
  } catch (error) {
    return {
      parsed: null,
      parseError: error.message,
      rawOutput,
      ...fallback
    };
  }
}

export function readOutputSchema(schemaPath) {
  return readJsonFile(schemaPath);
}

export { DEFAULT_CONTINUE_PROMPT, TASK_THREAD_PREFIX };
