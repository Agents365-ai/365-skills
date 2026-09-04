#!/usr/bin/env node

import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { parseArgs, splitRawArgumentString } from "./lib/args.mjs";
import {
  buildPersistentTaskThreadName,
  DEFAULT_CONTINUE_PROMPT,
  getPiAvailability,
  getPiModelsStatus,
  getPiSubagentsStatus,
  getSessionRuntimeStatus,
  parseStructuredOutput,
  readOutputSchema,
  runAppServerReview,
  runAppServerTurn
} from "./lib/pi.mjs";
import { readStdinIfPiped } from "./lib/fs.mjs";
import {
  addRaceWorktree,
  captureWorktreePatch,
  collectReviewContext,
  ensureGitRepository,
  getCurrentBranch,
  getHeadSha,
  getWorkingTreeState,
  isAncestor,
  removeRaceWorktree,
  resolveReviewTarget
} from "./lib/git.mjs";
import { readReviewCache, writeReviewCache } from "./lib/review-cache.mjs";
import { binaryAvailable, runCommand, terminateProcessTree } from "./lib/process.mjs";
import { loadPromptTemplate, interpolateTemplate } from "./lib/prompts.mjs";
import {
  generateJobId,
  getConfig,
  listJobs,
  resolveJobsDir,
  setConfig,
  upsertJob,
  writeJobFile
} from "./lib/state.mjs";
import {
  buildSingleJobSnapshot,
  buildStatusSnapshot,
  readStoredJob,
  resolveCancelableJob,
  resolveResultJob,
  sortJobsNewestFirst
} from "./lib/job-control.mjs";
import {
  appendLogLine,
  createJobLogFile,
  createJobProgressUpdater,
  createJobRecord,
  createProgressReporter,
  nowIso,
  runTrackedJob,
  SESSION_ID_ENV
} from "./lib/tracked-jobs.mjs";
import { resolveWorkspaceRoot } from "./lib/workspace.mjs";
import {
  normalizeReviewResultData,
  renderOutFileSummary,
  renderPanelReviewResult,
  renderRaceResult,
  renderReviewResult,
  renderShardedReviewResult,
  renderStoredJobResult,
  renderCancelReport,
  renderJobStatusReport,
  renderSetupReport,
  renderStatusReport,
  renderTaskResult,
  validateReviewResultShape
} from "./lib/render.mjs";
import { mergePanelReviews, parseModelList } from "./lib/panel.mjs";
import { buildModelChain, describeFallback, runWithModelFallback } from "./lib/fallback.mjs";
import { buildRacerLabels, buildRaceWorktreePath } from "./lib/race.mjs";
import { mergeShardReviews, splitFilesIntoShards } from "./lib/shard.mjs";

const ROOT_DIR = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const REVIEW_SCHEMA = path.join(ROOT_DIR, "schemas", "review-output.schema.json");
const DEFAULT_STATUS_WAIT_TIMEOUT_MS = 240000;
const DEFAULT_STATUS_POLL_INTERVAL_MS = 2000;
const VALID_REASONING_EFFORTS = new Set(["off", "minimal", "low", "medium", "high", "xhigh", "max"]);
const EFFORT_ALIASES = new Map([["none", "off"]]);
const STOP_REVIEW_TASK_MARKER = "Run a stop-gate review of the previous Claude turn.";

// Model selection is delegated to pi by default. The plugin only forces a
// specific model when the user pins one explicitly via --model on the slash
// command or via these env vars. With both unset, pi picks the model it is
// configured for (any provider pi supports: DeepSeek, OpenAI, Anthropic,
// Google, Ollama, LM Studio, or any OpenAI-compatible endpoint).
const ENV_REVIEW_MODEL = process.env.PI_PLUGIN_REVIEW_MODEL?.trim() || null;
const ENV_ADVERSARIAL_REVIEW_MODEL = process.env.PI_PLUGIN_ADVERSARIAL_REVIEW_MODEL?.trim() || null;
// Optional comma-separated fallback chain: when a Pi run fails, the same
// request is retried with the next model in this list.
const ENV_FALLBACK_MODELS = parseModelList(process.env.PI_PLUGIN_FALLBACK_MODELS);

function printUsage() {
  console.log(
    [
      "Usage:",
      "  node scripts/pi-companion.mjs setup [--enable-review-gate|--disable-review-gate] [--json]",
      "  node scripts/pi-companion.mjs review [--base <ref>] [--scope <auto|working-tree|branch>] [--incremental] [--model <model>|--models <m1,m2,...>] [--shards <N>] [--out-file <path>]",
      "  node scripts/pi-companion.mjs adversarial-review [--base <ref>] [--scope <auto|working-tree|branch>] [--incremental] [--model <model>|--models <m1,m2,...>] [--shards <N>] [--out-file <path>] [focus text]",
      "  node scripts/pi-companion.mjs task [--background] [--write] [--resume-last|--resume|--fresh] [--model <model>|--race <m1,m2,...>] [--effort <off|minimal|low|medium|high|xhigh|max>] [--out-file <path>] [prompt]",
      "  node scripts/pi-companion.mjs status [job-id] [--all] [--json]",
      "  node scripts/pi-companion.mjs result [job-id] [--json] [--out-file <path>]",
      "  node scripts/pi-companion.mjs cancel [job-id] [--json]"
    ].join("\n")
  );
}

function outputResult(value, asJson) {
  if (asJson) {
    console.log(JSON.stringify(value, null, 2));
  } else {
    process.stdout.write(value);
  }
}

function outputCommandResult(payload, rendered, asJson) {
  outputResult(asJson ? payload : rendered, asJson);
}

function normalizeRequestedModel(model) {
  if (model == null) {
    return null;
  }
  const normalized = String(model).trim();
  return normalized || null;
}

// --shards 1 or a non-numeric value means "no sharding" — falls back to the
// normal single review.
function normalizeShardCount(raw) {
  if (raw == null) {
    return null;
  }
  const parsed = Number.parseInt(String(raw).trim(), 10);
  if (!Number.isFinite(parsed) || parsed < 2) {
    return null;
  }
  return parsed;
}

function normalizeReasoningEffort(effort) {
  if (effort == null) {
    return null;
  }
  const normalized = String(effort).trim().toLowerCase();
  if (!normalized) {
    return null;
  }
  const resolved = EFFORT_ALIASES.get(normalized) ?? normalized;
  if (!VALID_REASONING_EFFORTS.has(resolved)) {
    throw new Error(
      `Unsupported reasoning effort "${effort}". Use one of: off, minimal, low, medium, high, xhigh, max (alias: none -> off).`
    );
  }
  return resolved;
}

function normalizeArgv(argv) {
  if (argv.length === 1) {
    const [raw] = argv;
    if (!raw || !raw.trim()) {
      return [];
    }
    return splitRawArgumentString(raw);
  }
  return argv;
}

function parseCommandInput(argv, config = {}) {
  return parseArgs(normalizeArgv(argv), {
    ...config,
    aliasMap: {
      C: "cwd",
      ...(config.aliasMap ?? {})
    }
  });
}

function resolveCommandCwd(options = {}) {
  return options.cwd ? path.resolve(process.cwd(), options.cwd) : process.cwd();
}

function resolveCommandWorkspace(options = {}) {
  return resolveWorkspaceRoot(resolveCommandCwd(options));
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function shorten(text, limit = 96) {
  const normalized = String(text ?? "").trim().replace(/\s+/g, " ");
  if (!normalized) {
    return "";
  }
  if (normalized.length <= limit) {
    return normalized;
  }
  return `${normalized.slice(0, limit - 3)}...`;
}

function firstMeaningfulLine(text, fallback) {
  const line = String(text ?? "")
    .split(/\r?\n/)
    .map((value) => value.trim())
    .find(Boolean);
  return line ?? fallback;
}

async function buildSetupReport(cwd, actionsTaken = []) {
  const workspaceRoot = resolveWorkspaceRoot(cwd);
  const nodeStatus = binaryAvailable("node", ["--version"], { cwd });
  const piStatus = getPiAvailability(cwd);
  const modelsStatus = getPiModelsStatus(process.env);
  const subagentsStatus = getPiSubagentsStatus();
  const config = getConfig(workspaceRoot);

  // Try to list available models from the pi CLI.
  let availableModels = [];
  if (piStatus.available) {
    const listResult = runCommand("pi", ["--list-models"], { cwd });
    if (listResult.status === 0 && listResult.stdout.trim()) {
      availableModels = listResult.stdout.trim().split("\n").filter(Boolean).slice(0, 10);
    }
  }

  const nextSteps = [];
  if (!piStatus.available) {
    nextSteps.push("Install Pi with `npm install -g --ignore-scripts @earendil-works/pi-coding-agent`.");
  } else if (piStatus.versionWarning) {
    nextSteps.push(piStatus.versionWarning);
  }
  if (piStatus.available && !modelsStatus.available) {
    nextSteps.push(
      "Set a provider API key (e.g. `export DEEPSEEK_API_KEY=...`), run `/login` inside pi, or write `~/.pi/agent/models.json` per pi docs."
    );
  }
  if (piStatus.available && modelsStatus.available && !config.stopReviewGate) {
    nextSteps.push("Optional: run `/pi:setup --enable-review-gate` to require a fresh review before stop.");
  }

  return {
    ready: nodeStatus.available && piStatus.available && modelsStatus.available,
    node: nodeStatus,
    pi: piStatus,
    models: modelsStatus,
    subagents: subagentsStatus,
    availableModels,
    fallbackModels: ENV_FALLBACK_MODELS,
    sessionRuntime: getSessionRuntimeStatus(process.env, workspaceRoot),
    reviewGateEnabled: Boolean(config.stopReviewGate),
    actionsTaken,
    nextSteps
  };
}

async function handleSetup(argv) {
  const { options } = parseCommandInput(argv, {
    valueOptions: ["cwd"],
    booleanOptions: ["json", "enable-review-gate", "disable-review-gate"]
  });

  if (options["enable-review-gate"] && options["disable-review-gate"]) {
    throw new Error("Choose either --enable-review-gate or --disable-review-gate.");
  }

  const cwd = resolveCommandCwd(options);
  const workspaceRoot = resolveCommandWorkspace(options);
  const actionsTaken = [];

  if (options["enable-review-gate"]) {
    setConfig(workspaceRoot, "stopReviewGate", true);
    actionsTaken.push(`Enabled the stop-time review gate for ${workspaceRoot}.`);
  } else if (options["disable-review-gate"]) {
    setConfig(workspaceRoot, "stopReviewGate", false);
    actionsTaken.push(`Disabled the stop-time review gate for ${workspaceRoot}.`);
  }

  const finalReport = await buildSetupReport(cwd, actionsTaken);
  outputResult(options.json ? finalReport : renderSetupReport(finalReport), options.json);
}

function buildReviewPrompt(templateName, context, focusText) {
  const template = loadPromptTemplate(ROOT_DIR, templateName);
  const schema = JSON.stringify(readOutputSchema(REVIEW_SCHEMA), null, 2);
  return interpolateTemplate(template, {
    REVIEW_KIND: templateName === "adversarial-review" ? "Adversarial Review" : "Review",
    TARGET_LABEL: context.target.label,
    USER_FOCUS: focusText || "No extra focus provided.",
    REVIEW_COLLECTION_GUIDANCE: context.collectionGuidance,
    REVIEW_INPUT: context.content,
    REVIEW_SCHEMA: schema
  });
}

function ensurePiAvailable(cwd) {
  const availability = getPiAvailability(cwd);
  if (!availability.available) {
    throw new Error(`${availability.detail} Then rerun \`/pi:setup\`.`);
  }
}

function validateRegularReviewRequest(_target, focusText) {
  if (focusText.trim()) {
    throw new Error(
      `\`/pi:review\` does not accept custom focus text. Retry with \`/pi:adversarial-review ${focusText.trim()}\` to ask for focused review.`
    );
  }
}

function renderStatusPayload(report, asJson) {
  return asJson ? report : renderStatusReport(report);
}

function isActiveJobStatus(status) {
  return status === "queued" || status === "running";
}

function getCurrentClaudeSessionId() {
  return process.env[SESSION_ID_ENV] ?? null;
}

function filterJobsForCurrentClaudeSession(jobs) {
  const sessionId = getCurrentClaudeSessionId();
  if (!sessionId) {
    return jobs;
  }
  return jobs.filter((job) => job.sessionId === sessionId);
}

function findLatestResumableTaskJob(jobs) {
  return (
    jobs.find(
      (job) =>
        job.jobClass === "task" &&
        job.piSessionId &&
        job.status !== "queued" &&
        job.status !== "running"
    ) ?? null
  );
}

async function waitForSingleJobSnapshot(cwd, reference, options = {}) {
  const timeoutMs = Math.max(0, Number(options.timeoutMs) || DEFAULT_STATUS_WAIT_TIMEOUT_MS);
  const pollIntervalMs = Math.max(100, Number(options.pollIntervalMs) || DEFAULT_STATUS_POLL_INTERVAL_MS);
  const deadline = Date.now() + timeoutMs;
  let snapshot = buildSingleJobSnapshot(cwd, reference);

  while (isActiveJobStatus(snapshot.job.status) && Date.now() < deadline) {
    await sleep(Math.min(pollIntervalMs, Math.max(0, deadline - Date.now())));
    snapshot = buildSingleJobSnapshot(cwd, reference);
  }

  return {
    ...snapshot,
    waitTimedOut: isActiveJobStatus(snapshot.job.status),
    timeoutMs
  };
}

function resolveLatestTrackedTaskSession(cwd, options = {}) {
  const workspaceRoot = resolveWorkspaceRoot(cwd);
  const jobs = sortJobsNewestFirst(listJobs(workspaceRoot)).filter((job) => job.id !== options.excludeJobId);
  const visibleJobs = filterJobsForCurrentClaudeSession(jobs);
  const activeTask = visibleJobs.find((job) => job.jobClass === "task" && (job.status === "queued" || job.status === "running"));
  if (activeTask) {
    throw new Error(`Task ${activeTask.id} is still running. Use /pi:status before continuing it.`);
  }

  const trackedTask = findLatestResumableTaskJob(visibleJobs);
  if (trackedTask) {
    return trackedTask.piSessionId;
  }

  return null;
}

function prepareReviewRun(request) {
  ensurePiAvailable(request.cwd);
  ensureGitRepository(request.cwd);

  const target = resolveReviewTarget(request.cwd, {
    base: request.base,
    scope: request.scope
  });
  const focusText = request.focusText?.trim() ?? "";
  const reviewName = request.reviewName ?? "Review";
  const isAdversarial = reviewName === "Adversarial Review";
  const templateName = isAdversarial ? "adversarial-review" : "review";

  const context = collectReviewContext(request.cwd, target);
  const prompt = buildReviewPrompt(templateName, context, focusText);

  return { target, reviewName, isAdversarial, context, prompt };
}

async function executeReviewRun(request) {
  return finishSingleReview(request, prepareReviewRun(request));
}

// Runs the single-review model call given an already-built prep (target,
// context, prompt). Split out from executeReviewRun so the sharded-review
// path can fall back to a plain single review without recomputing the diff
// context it already gathered when it decided there weren't enough files to
// shard.
async function finishSingleReview(request, prep) {
  const { target, reviewName, isAdversarial, context, prompt } = prep;
  // request.model: explicit --model on the slash command. Highest priority.
  // ENV_*_REVIEW_MODEL: opt-in pin via env var.
  // null: defer to pi's own configured default model.
  const envDefault = isAdversarial ? ENV_ADVERSARIAL_REVIEW_MODEL : ENV_REVIEW_MODEL;
  const model = request.model ?? envDefault ?? null;

  const { result, attempts } = await runWithModelFallback(
    buildModelChain(model, ENV_FALLBACK_MODELS),
    (attemptModel) =>
      runAppServerReview(context.repoRoot, {
        prompt,
        model: attemptModel,
        effort: request.effort,
        threadName: `Pi ${reviewName}`,
        onProgress: request.onProgress
      }),
    request.onProgress
  );
  const fallbackNote = describeFallback(attempts);

  const parsed = parseStructuredOutput(result.reviewText, {
    status: result.status,
    failureMessage: result.error?.message ?? result.stderr
  });

  const payload = {
    review: reviewName,
    target,
    piSessionId: result.piSessionId,
    piSessionFile: result.piSessionFile,
    context: {
      repoRoot: context.repoRoot,
      branch: context.branch,
      summary: context.summary
    },
    pi: {
      status: result.status,
      stderr: result.stderr,
      stdout: result.reviewText,
      reasoning: result.reasoningSummary
    },
    result: parsed.parsed,
    rawOutput: parsed.rawOutput,
    parseError: parsed.parseError,
    reasoningSummary: result.reasoningSummary,
    ...(fallbackNote ? { modelAttempts: attempts } : {})
  };

  let rendered = renderReviewResult(parsed, {
    reviewLabel: reviewName,
    targetLabel: context.target.label,
    reasoningSummary: result.reasoningSummary
  });
  if (fallbackNote) {
    rendered = `${rendered}\n${fallbackNote}\n`;
  }

  return {
    exitStatus: result.status,
    piSessionId: result.piSessionId,
    piSessionFile: result.piSessionFile,
    payload,
    rendered,
    summary:
      parsed.parsed?.summary ?? parsed.parseError ?? firstMeaningfulLine(result.reviewText, `${reviewName} finished.`),
    jobTitle: `Pi ${reviewName}`,
    jobClass: "review",
    targetLabel: context.target.label
  };
}

function prefixModelProgress(onProgress, model) {
  if (!onProgress) {
    return null;
  }
  return (eventOrMessage) => {
    const event =
      eventOrMessage && typeof eventOrMessage === "object" && !Array.isArray(eventOrMessage)
        ? eventOrMessage
        : { message: String(eventOrMessage ?? "") };
    onProgress({
      ...event,
      message: `[${model}] ${event.message ?? ""}`,
      // Per-model session ids live in the panel payload; a single job-level
      // resume pointer would be misleading.
      piSessionId: null,
      piSessionFile: null
    });
  };
}

async function runPanelMemberReview(prep, request, model) {
  try {
    const result = await runAppServerReview(prep.context.repoRoot, {
      prompt: prep.prompt,
      model,
      effort: request.effort,
      threadName: `Pi ${prep.reviewName} [${model}]`,
      onProgress: prefixModelProgress(request.onProgress, model)
    });
    const parsed = parseStructuredOutput(result.reviewText, {
      status: result.status,
      failureMessage: result.error?.message ?? result.stderr
    });

    let normalized = null;
    let failure = null;
    if (result.status !== 0) {
      failure = result.error?.message?.trim() || "Pi run failed.";
    } else if (!parsed.parsed) {
      failure = `invalid structured output: ${parsed.parseError}`;
    } else {
      const shapeError = validateReviewResultShape(parsed.parsed);
      if (shapeError) {
        failure = `unexpected review shape: ${shapeError}`;
      } else {
        normalized = normalizeReviewResultData(parsed.parsed);
      }
    }

    return { model, normalized, failure, piSessionId: result.piSessionId ?? null };
  } catch (error) {
    return {
      model,
      normalized: null,
      failure: error instanceof Error ? error.message : String(error),
      piSessionId: null
    };
  }
}

async function executePanelReviewRun(request) {
  const prep = prepareReviewRun(request);
  const { target, reviewName, context } = prep;

  const runs = await Promise.all(request.models.map((model) => runPanelMemberReview(prep, request, model)));
  const merged = mergePanelReviews(runs.map((run) => ({ model: run.model, parsed: run.normalized })));

  const members = runs.map((run) => ({
    model: run.model,
    ok: Boolean(run.normalized),
    findingCount: run.normalized ? run.normalized.findings.length : null,
    summary: run.normalized?.summary ?? null,
    failure: run.failure,
    piSessionId: run.piSessionId
  }));
  const okCount = members.filter((member) => member.ok).length;
  const consensusCount = merged.findings.filter((finding) => finding.foundBy.length >= 2).length;
  const singleCount = merged.findings.length - consensusCount;

  const payload = {
    review: `Panel ${reviewName}`,
    target,
    models: members,
    context: {
      repoRoot: context.repoRoot,
      branch: context.branch,
      summary: context.summary
    },
    result: merged
  };

  return {
    exitStatus: okCount > 0 ? 0 : 1,
    piSessionId: null,
    piSessionFile: null,
    payload,
    rendered: renderPanelReviewResult(
      { ...merged, members },
      { reviewLabel: reviewName, targetLabel: context.target.label }
    ),
    summary: `Panel ${reviewName.toLowerCase()}: ${okCount}/${members.length} models ok, ${consensusCount} consensus + ${singleCount} single-model finding${merged.findings.length === 1 ? "" : "s"}`,
    jobTitle: `Pi Panel ${reviewName}`,
    jobClass: "review",
    targetLabel: context.target.label
  };
}

async function runShardReview(request, prep, shardFiles, shardIndex, shardTotal) {
  const templateName = prep.isAdversarial ? "adversarial-review" : "review";
  const label = `shard ${shardIndex + 1}/${shardTotal}`;
  try {
    const scopedContext = collectReviewContext(request.cwd, prep.target, { files: shardFiles });
    const prompt = buildReviewPrompt(templateName, scopedContext, request.focusText?.trim() ?? "");
    const envDefault = prep.isAdversarial ? ENV_ADVERSARIAL_REVIEW_MODEL : ENV_REVIEW_MODEL;
    const model = request.model ?? envDefault ?? null;

    const { result } = await runWithModelFallback(
      buildModelChain(model, ENV_FALLBACK_MODELS),
      (attemptModel) =>
        runAppServerReview(scopedContext.repoRoot, {
          prompt,
          model: attemptModel,
          effort: request.effort,
          threadName: `Pi ${prep.reviewName} [${label}]`,
          onProgress: prefixModelProgress(request.onProgress, label)
        }),
      request.onProgress
    );
    const parsed = parseStructuredOutput(result.reviewText, {
      status: result.status,
      failureMessage: result.error?.message ?? result.stderr
    });

    let normalized = null;
    let failure = null;
    if (result.status !== 0) {
      failure = result.error?.message?.trim() || "Pi run failed.";
    } else if (!parsed.parsed) {
      failure = `invalid structured output: ${parsed.parseError}`;
    } else {
      const shapeError = validateReviewResultShape(parsed.parsed);
      if (shapeError) {
        failure = `unexpected review shape: ${shapeError}`;
      } else {
        normalized = normalizeReviewResultData(parsed.parsed);
      }
    }

    return { files: shardFiles, normalized, failure, piSessionId: result.piSessionId ?? null };
  } catch (error) {
    return {
      files: shardFiles,
      normalized: null,
      failure: error instanceof Error ? error.message : String(error),
      piSessionId: null
    };
  }
}

// Sharded review: split the changed files across N parallel review jobs,
// each scoped to its own disjoint file subset via collectReviewContext's
// `files` filter, then merge the findings. Falls back to a plain single
// review when there is only 0-1 changed file, since there is nothing to
// usefully split.
async function executeShardedReviewRun(request) {
  const prep = prepareReviewRun(request);
  const { reviewName, context } = prep;

  if (context.changedFiles.length <= 1) {
    return finishSingleReview(request, prep);
  }

  const shardFileGroups = splitFilesIntoShards(context.changedFiles, request.shards);
  const runs = await Promise.all(
    shardFileGroups.map((shardFiles, index) => runShardReview(request, prep, shardFiles, index, shardFileGroups.length))
  );
  const merged = mergeShardReviews(runs.map((run) => run.normalized));

  const shards = runs.map((run, index) => ({
    index,
    files: run.files,
    ok: Boolean(run.normalized),
    findingCount: run.normalized ? run.normalized.findings.length : null,
    failure: run.failure,
    piSessionId: run.piSessionId
  }));
  const okCount = shards.filter((shard) => shard.ok).length;

  const payload = {
    review: `Sharded ${reviewName}`,
    target: prep.target,
    shards,
    context: {
      repoRoot: context.repoRoot,
      branch: context.branch,
      summary: context.summary
    },
    result: merged
  };

  return {
    exitStatus: okCount > 0 ? 0 : 1,
    piSessionId: null,
    piSessionFile: null,
    payload,
    rendered: renderShardedReviewResult(
      { ...merged, shards },
      { reviewLabel: reviewName, targetLabel: context.target.label }
    ),
    summary: `Sharded ${reviewName.toLowerCase()} across ${shards.length} jobs: ${okCount}/${shards.length} ok, ${merged.findings.length} finding${merged.findings.length === 1 ? "" : "s"}`,
    jobTitle: `Pi Sharded ${reviewName}`,
    jobClass: "review",
    targetLabel: context.target.label
  };
}

async function runRacer(request, racer, context) {
  const onProgress = prefixModelProgress(request.onProgress, racer.model);
  let worktreePath = null;
  try {
    let runCwd = request.cwd;
    if (context.write) {
      worktreePath = buildRaceWorktreePath(os.tmpdir(), request.jobId ?? `adhoc-${process.pid}`, racer.slug);
      fs.mkdirSync(path.dirname(worktreePath), { recursive: true });
      addRaceWorktree(context.repoRoot, worktreePath);
      onProgress?.({ message: `Racer worktree ready at ${worktreePath}.`, phase: "starting" });
      runCwd = worktreePath;
    }

    const result = await runAppServerTurn(runCwd, {
      prompt: request.prompt,
      model: racer.model,
      effort: request.effort,
      sandbox: context.write ? null : "read-only",
      onProgress,
      persistThread: true,
      threadName: `Pi Race [${racer.model}]`
    });

    const patch =
      context.write && result.status === 0 && worktreePath ? captureWorktreePatch(worktreePath) : null;

    return {
      model: racer.model,
      slug: racer.slug,
      ok: result.status === 0,
      finalMessage: typeof result.finalMessage === "string" ? result.finalMessage : "",
      failure: result.status === 0 ? null : (result.error?.message ?? result.stderr ?? "Run failed."),
      piSessionId: result.piSessionId ?? null,
      patch
    };
  } catch (error) {
    return {
      model: racer.model,
      slug: racer.slug,
      ok: false,
      finalMessage: "",
      failure: error instanceof Error ? error.message : String(error),
      piSessionId: null,
      patch: null
    };
  } finally {
    if (worktreePath) {
      try {
        removeRaceWorktree(context.repoRoot, worktreePath);
      } catch {
        // best-effort cleanup; a stale worktree is prunable with `git worktree prune`
      }
    }
  }
}

async function executeRaceRun(request) {
  ensurePiAvailable(request.cwd);
  if (!request.prompt) {
    throw new Error("Provide a prompt for the race.");
  }

  const write = Boolean(request.write);
  const racers = buildRacerLabels(request.raceModels);
  const context = { write, repoRoot: null };
  let dirtyWarning = null;
  if (write) {
    context.repoRoot = ensureGitRepository(request.cwd);
    if (getWorkingTreeState(context.repoRoot).isDirty) {
      dirtyWarning = "Working tree has uncommitted changes; racers start from HEAD and cannot see them.";
      request.onProgress?.({ message: dirtyWarning, phase: "starting" });
    }
  }

  const results = await Promise.all(racers.map((racer) => runRacer(request, racer, context)));

  const workspaceRoot = resolveWorkspaceRoot(request.cwd);
  const jobsDir = resolveJobsDir(workspaceRoot);
  fs.mkdirSync(jobsDir, { recursive: true });

  const racersPayload = results.map((result) => {
    let patchFile = null;
    if (result.patch && !result.patch.isEmpty) {
      patchFile = path.join(jobsDir, `${request.jobId ?? "race"}-${result.slug}.patch`);
      fs.writeFileSync(patchFile, result.patch.patch, "utf8");
    }
    return {
      model: result.model,
      ok: result.ok,
      failure: result.failure,
      piSessionId: result.piSessionId,
      finalMessage: result.finalMessage,
      patchFile,
      patchStat: result.patch?.stat ?? null,
      patchEmpty: result.patch ? result.patch.isEmpty : null
    };
  });

  const okCount = racersPayload.filter((racer) => racer.ok).length;
  const rendered = renderRaceResult(
    { write, dirtyWarning, racers: racersPayload },
    { taskSummary: shorten(request.prompt) }
  );

  return {
    exitStatus: okCount > 0 ? 0 : 1,
    piSessionId: null,
    piSessionFile: null,
    payload: { race: true, write, dirtyWarning, racers: racersPayload },
    rendered,
    summary: `Race: ${okCount}/${racersPayload.length} models ok`,
    jobTitle: "Pi Race",
    jobClass: "task",
    write
  };
}

async function executeTaskRun(request) {
  if (Array.isArray(request.raceModels) && request.raceModels.length >= 2) {
    return executeRaceRun(request);
  }

  const workspaceRoot = resolveWorkspaceRoot(request.cwd);
  ensurePiAvailable(request.cwd);

  const taskMetadata = buildTaskRunMetadata({
    prompt: request.prompt,
    resumeLast: request.resumeLast
  });

  let resumeSessionId = null;
  if (request.resumeLast) {
    const latest = resolveLatestTrackedTaskSession(workspaceRoot, {
      excludeJobId: request.jobId
    });
    if (!latest) {
      throw new Error("No previous Pi task session was found for this repository.");
    }
    resumeSessionId = latest;
  }

  if (!request.prompt && !resumeSessionId) {
    throw new Error("Provide a prompt, a prompt file, piped stdin, or use --resume-last.");
  }

  const { result, attempts } = await runWithModelFallback(
    buildModelChain(request.model ?? null, ENV_FALLBACK_MODELS),
    (attemptModel) =>
      runAppServerTurn(workspaceRoot, {
        resumeSessionId,
        prompt: request.prompt,
        defaultPrompt: resumeSessionId ? DEFAULT_CONTINUE_PROMPT : "",
        model: attemptModel,
        effort: request.effort,
        sandbox: request.write ? null : "read-only",
        onProgress: request.onProgress,
        persistThread: true,
        threadName: resumeSessionId ? null : buildPersistentTaskThreadName(request.prompt || DEFAULT_CONTINUE_PROMPT)
      }),
    request.onProgress
  );
  const fallbackNote = describeFallback(attempts);

  const rawOutput = typeof result.finalMessage === "string" ? result.finalMessage : "";
  const failureMessage = result.error?.message ?? result.stderr ?? "";
  let rendered = renderTaskResult(
    {
      rawOutput,
      failureMessage,
      reasoningSummary: result.reasoningSummary
    },
    {
      title: taskMetadata.title,
      jobId: request.jobId ?? null,
      write: Boolean(request.write)
    }
  );
  if (fallbackNote) {
    rendered = `${rendered}\n${fallbackNote}\n`;
  }
  const payload = {
    status: result.status,
    piSessionId: result.piSessionId,
    piSessionFile: result.piSessionFile,
    rawOutput,
    touchedFiles: result.touchedFiles,
    reasoningSummary: result.reasoningSummary,
    ...(fallbackNote ? { modelAttempts: attempts } : {})
  };

  return {
    exitStatus: result.status,
    piSessionId: result.piSessionId,
    piSessionFile: result.piSessionFile,
    payload,
    rendered,
    summary: firstMeaningfulLine(rawOutput, firstMeaningfulLine(failureMessage, `${taskMetadata.title} finished.`)),
    jobTitle: taskMetadata.title,
    jobClass: "task",
    write: Boolean(request.write)
  };
}

function buildReviewJobMetadata(reviewName, target) {
  return {
    kind: reviewName === "Adversarial Review" ? "adversarial-review" : "review",
    title: reviewName === "Review" ? "Pi Review" : `Pi ${reviewName}`,
    summary: `${reviewName} ${target.label}`
  };
}

function buildTaskRunMetadata({ prompt, resumeLast = false, raceModels = null }) {
  if (Array.isArray(raceModels) && raceModels.length >= 2) {
    return {
      title: "Pi Race",
      summary: `Race (${raceModels.length} models): ${shorten(prompt || "Task")}`
    };
  }
  if (!resumeLast && String(prompt ?? "").includes(STOP_REVIEW_TASK_MARKER)) {
    return {
      title: "Pi Stop Gate Review",
      summary: "Stop-gate review of previous Claude turn"
    };
  }

  const title = resumeLast ? "Pi Resume" : "Pi Task";
  const fallbackSummary = resumeLast ? DEFAULT_CONTINUE_PROMPT : "Task";
  return {
    title,
    summary: shorten(prompt || fallbackSummary)
  };
}

function renderQueuedTaskLaunch(payload) {
  return `${payload.title} started in the background as ${payload.jobId}. Check /pi:status ${payload.jobId} for progress.\n`;
}

function getJobKindLabel(kind, jobClass) {
  if (kind === "adversarial-review") {
    return "adversarial-review";
  }
  return jobClass === "review" ? "review" : "rescue";
}

function createCompanionJob({ prefix, kind, title, workspaceRoot, jobClass, summary, write = false }) {
  return createJobRecord({
    id: generateJobId(prefix),
    kind,
    kindLabel: getJobKindLabel(kind, jobClass),
    title,
    workspaceRoot,
    jobClass,
    summary,
    write
  });
}

function createTrackedProgress(job, options = {}) {
  const logFile = options.logFile ?? createJobLogFile(job.workspaceRoot, job.id, job.title);
  return {
    logFile,
    progress: createProgressReporter({
      stderr: Boolean(options.stderr),
      logFile,
      onEvent: createJobProgressUpdater(job.workspaceRoot, job.id)
    })
  };
}

function buildTaskJob(workspaceRoot, taskMetadata, write) {
  return createCompanionJob({
    prefix: "task",
    kind: "task",
    title: taskMetadata.title,
    workspaceRoot,
    jobClass: "task",
    summary: taskMetadata.summary,
    write
  });
}

function buildTaskRequest({ cwd, model, effort, prompt, write, resumeLast, jobId, raceModels = null }) {
  return {
    cwd,
    model,
    effort,
    prompt,
    write,
    resumeLast,
    jobId,
    raceModels
  };
}

function readTaskPrompt(cwd, options, positionals) {
  if (options["prompt-file"]) {
    return fs.readFileSync(path.resolve(cwd, options["prompt-file"]), "utf8");
  }

  const positionalPrompt = positionals.join(" ");
  return positionalPrompt || readStdinIfPiped();
}

function requireTaskRequest(prompt, resumeLast) {
  if (!prompt && !resumeLast) {
    throw new Error("Provide a prompt, a prompt file, piped stdin, or use --resume-last.");
  }
}

async function runForegroundCommand(job, runner, options = {}) {
  const { logFile, progress } = createTrackedProgress(job, {
    logFile: options.logFile,
    stderr: !options.json
  });
  const execution = await runTrackedJob(job, () => runner(progress), { logFile });
  if (options.outFile && !options.json) {
    // Write the full output to a file and relay only a short summary, so a
    // large review/task does not consume the caller's context.
    fs.writeFileSync(options.outFile, execution.rendered);
    process.stdout.write(renderOutFileSummary(execution, options.outFile));
  } else {
    outputResult(options.json ? execution.payload : execution.rendered, options.json);
  }
  if (execution.exitStatus !== 0) {
    process.exitCode = execution.exitStatus;
  }
  return execution;
}

function spawnDetachedTaskWorker(cwd, jobId) {
  const scriptPath = path.join(ROOT_DIR, "scripts", "pi-companion.mjs");
  const child = spawn(process.execPath, [scriptPath, "task-worker", "--cwd", cwd, "--job-id", jobId], {
    cwd,
    env: process.env,
    detached: true,
    stdio: "ignore",
    windowsHide: true
  });
  child.unref();
  return child;
}

function enqueueBackgroundTask(cwd, job, request) {
  const { logFile } = createTrackedProgress(job);
  appendLogLine(logFile, "Queued for background execution.");

  const child = spawnDetachedTaskWorker(cwd, job.id);
  const queuedRecord = {
    ...job,
    status: "queued",
    phase: "queued",
    pid: child.pid ?? null,
    logFile,
    request
  };
  writeJobFile(job.workspaceRoot, job.id, queuedRecord);
  upsertJob(job.workspaceRoot, queuedRecord);

  return {
    payload: {
      jobId: job.id,
      status: "queued",
      title: job.title,
      summary: job.summary,
      logFile
    },
    logFile
  };
}

// After a successful review (incremental or full), record HEAD as the new
// per-branch marker so the next --incremental review starts from here.
// Detached HEAD has no branch to key the cache on, so it is skipped.
function maybeUpdateReviewCache(workspaceRoot, cwd, execution) {
  if (execution?.exitStatus !== 0) {
    return;
  }
  const branch = getCurrentBranch(cwd);
  if (branch !== "HEAD") {
    writeReviewCache(workspaceRoot, branch, getHeadSha(cwd));
  }
}

async function handleReviewCommand(argv, config) {
  const { options, positionals } = parseCommandInput(argv, {
    valueOptions: ["base", "scope", "model", "models", "shards", "effort", "cwd", "out-file"],
    booleanOptions: ["json", "incremental"],
    aliasMap: {
      m: "model"
    }
  });

  const cwd = resolveCommandCwd(options);
  const workspaceRoot = resolveCommandWorkspace(options);
  const focusText = positionals.join(" ").trim();
  const outFile = options["out-file"] ? path.resolve(cwd, options["out-file"]) : null;

  const incremental = Boolean(options.incremental);
  if (incremental && options.base) {
    throw new Error("Choose either --incremental or --base.");
  }

  let reviewBase = options.base;
  let reviewScope = options.scope;

  if (incremental) {
    const branch = getCurrentBranch(cwd);
    const headSha = getHeadSha(cwd);
    const cachedSha = readReviewCache(workspaceRoot, branch);
    if (cachedSha && cachedSha === headSha) {
      process.stdout.write(
        `No new commits to review since the last review on ${branch} (${headSha.slice(0, 9)}).\n`
      );
      return;
    }
    if (cachedSha && isAncestor(cwd, cachedSha) && cachedSha !== headSha) {
      // The incremental delta: only the commits since the cached marker.
      reviewBase = cachedSha;
      reviewScope = "branch";
    } else {
      // No cache yet, or the cached sha is no longer an ancestor of HEAD
      // (rebase, history rewrite, or a branch switch) — fall back to a full review.
      process.stderr.write(`No valid review cache for ${branch}; running a full review.\n`);
    }
  }

  const target = resolveReviewTarget(cwd, {
    base: reviewBase,
    scope: reviewScope
  });

  config.validateRequest?.(target, focusText);

  const panelModels = parseModelList(options.models);
  if (panelModels.length > 0 && options.model) {
    throw new Error("Choose either --model <one> or --models <m1,m2,...>, not both.");
  }
  const shardCount = normalizeShardCount(options.shards);
  if (shardCount && panelModels.length > 0) {
    throw new Error("Choose either --shards <N> or --models <m1,m2,...>, not both.");
  }
  // A single --models entry is just a model pin; the panel needs 2+.
  const singleModel = normalizeRequestedModel(options.model) ?? (panelModels.length === 1 ? panelModels[0] : null);
  const effort = normalizeReasoningEffort(options.effort);

  const metadata = buildReviewJobMetadata(config.reviewName, target);

  if (panelModels.length >= 2) {
    const job = createCompanionJob({
      prefix: "review",
      kind: metadata.kind,
      title: `Pi Panel ${config.reviewName}`,
      workspaceRoot,
      jobClass: "review",
      summary: `Panel (${panelModels.length} models) ${metadata.summary}`
    });
    const execution = await runForegroundCommand(
      job,
      (progress) =>
        executePanelReviewRun({
          cwd,
          base: reviewBase,
          scope: reviewScope,
          models: panelModels,
          effort,
          focusText,
          reviewName: config.reviewName,
          onProgress: progress
        }),
      { json: options.json, outFile }
    );
    maybeUpdateReviewCache(workspaceRoot, cwd, execution);
    return;
  }

  if (shardCount) {
    const job = createCompanionJob({
      prefix: "review",
      kind: metadata.kind,
      title: `Pi Sharded ${config.reviewName}`,
      workspaceRoot,
      jobClass: "review",
      summary: `Sharded (${shardCount} jobs) ${metadata.summary}`
    });
    const execution = await runForegroundCommand(
      job,
      (progress) =>
        executeShardedReviewRun({
          cwd,
          base: reviewBase,
          scope: reviewScope,
          model: singleModel,
          shards: shardCount,
          effort,
          focusText,
          reviewName: config.reviewName,
          onProgress: progress
        }),
      { json: options.json, outFile }
    );
    maybeUpdateReviewCache(workspaceRoot, cwd, execution);
    return;
  }

  const job = createCompanionJob({
    prefix: "review",
    kind: metadata.kind,
    title: metadata.title,
    workspaceRoot,
    jobClass: "review",
    summary: metadata.summary
  });
  const execution = await runForegroundCommand(
    job,
    (progress) =>
      executeReviewRun({
        cwd,
        base: reviewBase,
        scope: reviewScope,
        model: singleModel,
        effort,
        focusText,
        reviewName: config.reviewName,
        onProgress: progress
      }),
    { json: options.json, outFile }
  );
  maybeUpdateReviewCache(workspaceRoot, cwd, execution);
}

async function handleReview(argv) {
  return handleReviewCommand(argv, {
    reviewName: "Review",
    validateRequest: validateRegularReviewRequest
  });
}

async function handleTask(argv) {
  const { options, positionals } = parseCommandInput(argv, {
    valueOptions: ["model", "effort", "cwd", "prompt-file", "race", "out-file"],
    booleanOptions: ["json", "write", "resume-last", "resume", "fresh", "background"],
    aliasMap: {
      m: "model"
    }
  });

  const cwd = resolveCommandCwd(options);
  const workspaceRoot = resolveCommandWorkspace(options);
  const outFile = options["out-file"] ? path.resolve(cwd, options["out-file"]) : null;
  const raceList = parseModelList(options.race);
  if (raceList.length > 0 && options.model) {
    throw new Error("Choose either --model <one> or --race <m1,m2,...>, not both.");
  }
  // A single --race entry is just a model pin; a race needs 2+.
  const model = normalizeRequestedModel(options.model) ?? (raceList.length === 1 ? raceList[0] : null);
  const raceModels = raceList.length >= 2 ? raceList : null;
  const effort = normalizeReasoningEffort(options.effort);
  const prompt = readTaskPrompt(cwd, options, positionals);

  const resumeLast = Boolean(options["resume-last"] || options.resume);
  const fresh = Boolean(options.fresh);
  if (resumeLast && fresh) {
    throw new Error("Choose either --resume/--resume-last or --fresh.");
  }
  if (raceModels && resumeLast) {
    throw new Error("--race starts fresh racer sessions; it cannot be combined with --resume/--resume-last.");
  }
  const write = Boolean(options.write);
  const taskMetadata = buildTaskRunMetadata({
    prompt,
    resumeLast,
    raceModels
  });

  if (options.background) {
    ensurePiAvailable(cwd);
    requireTaskRequest(prompt, resumeLast);

    const job = buildTaskJob(workspaceRoot, taskMetadata, write);
    const request = buildTaskRequest({
      cwd,
      model,
      effort,
      prompt,
      write,
      resumeLast,
      jobId: job.id,
      raceModels
    });
    const { payload } = enqueueBackgroundTask(cwd, job, request);
    outputCommandResult(payload, renderQueuedTaskLaunch(payload), options.json);
    return;
  }

  const job = buildTaskJob(workspaceRoot, taskMetadata, write);
  await runForegroundCommand(
    job,
    (progress) =>
      executeTaskRun({
        cwd,
        model,
        effort,
        prompt,
        write,
        resumeLast,
        jobId: job.id,
        raceModels,
        onProgress: progress
      }),
    { json: options.json, outFile }
  );
}

async function handleTaskWorker(argv) {
  const { options } = parseCommandInput(argv, {
    valueOptions: ["cwd", "job-id"]
  });

  if (!options["job-id"]) {
    throw new Error("Missing required --job-id for task-worker.");
  }

  const workspaceRoot = resolveCommandWorkspace(options);
  const storedJob = readStoredJob(workspaceRoot, options["job-id"]);
  if (!storedJob) {
    throw new Error(`No stored job found for ${options["job-id"]}.`);
  }

  const request = storedJob.request;
  if (!request || typeof request !== "object") {
    throw new Error(`Stored job ${options["job-id"]} is missing its task request payload.`);
  }

  const { logFile, progress } = createTrackedProgress(
    {
      ...storedJob,
      workspaceRoot
    },
    {
      logFile: storedJob.logFile ?? null
    }
  );
  await runTrackedJob(
    {
      ...storedJob,
      workspaceRoot,
      logFile
    },
    () =>
      executeTaskRun({
        ...request,
        onProgress: progress
      }),
    { logFile }
  );
}

async function handleStatus(argv) {
  const { options, positionals } = parseCommandInput(argv, {
    valueOptions: ["cwd", "timeout-ms", "poll-interval-ms"],
    booleanOptions: ["json", "all", "wait"]
  });

  const cwd = resolveCommandCwd(options);
  const reference = positionals[0] ?? "";
  if (reference) {
    const snapshot = options.wait
      ? await waitForSingleJobSnapshot(cwd, reference, {
          timeoutMs: options["timeout-ms"],
          pollIntervalMs: options["poll-interval-ms"]
        })
      : buildSingleJobSnapshot(cwd, reference);
    outputCommandResult(snapshot, renderJobStatusReport(snapshot.job), options.json);
    return;
  }

  if (options.wait) {
    throw new Error("`status --wait` requires a job id.");
  }

  const report = buildStatusSnapshot(cwd, { all: options.all });
  outputResult(renderStatusPayload(report, options.json), options.json);
}

function handleResult(argv) {
  const { options, positionals } = parseCommandInput(argv, {
    valueOptions: ["cwd", "out-file"],
    booleanOptions: ["json"]
  });

  const cwd = resolveCommandCwd(options);
  const outFile = options["out-file"] ? path.resolve(cwd, options["out-file"]) : null;
  const reference = positionals[0] ?? "";
  const { workspaceRoot, job } = resolveResultJob(cwd, reference);
  const storedJob = readStoredJob(workspaceRoot, job.id);
  const payload = {
    job,
    storedJob
  };
  const rendered = renderStoredJobResult(job, storedJob);

  if (outFile && !options.json) {
    // Write the stored full result to a file and relay only a short summary,
    // so fetching a large background result does not flood the caller's context.
    fs.writeFileSync(outFile, rendered);
    process.stdout.write(renderOutFileSummary({ summary: job.summary }, outFile));
  } else {
    outputCommandResult(payload, rendered, options.json);
  }
}

function handleTaskResumeCandidate(argv) {
  const { options } = parseCommandInput(argv, {
    valueOptions: ["cwd"],
    booleanOptions: ["json"]
  });

  const workspaceRoot = resolveCommandWorkspace(options);
  const sessionId = getCurrentClaudeSessionId();
  const jobs = filterJobsForCurrentClaudeSession(sortJobsNewestFirst(listJobs(workspaceRoot)));
  const candidate = findLatestResumableTaskJob(jobs);

  const payload = {
    available: Boolean(candidate),
    sessionId,
    candidate:
      candidate == null
        ? null
        : {
            id: candidate.id,
            status: candidate.status,
            title: candidate.title ?? null,
            summary: candidate.summary ?? null,
            piSessionId: candidate.piSessionId,
            piSessionFile: candidate.piSessionFile ?? null,
            completedAt: candidate.completedAt ?? null,
            updatedAt: candidate.updatedAt ?? null
          }
  };

  const rendered = candidate
    ? `Resumable task found: ${candidate.id} (${candidate.status}).\n`
    : "No resumable task found for this session.\n";
  outputCommandResult(payload, rendered, options.json);
}

async function handleCancel(argv) {
  const { options, positionals } = parseCommandInput(argv, {
    valueOptions: ["cwd"],
    booleanOptions: ["json"]
  });

  const cwd = resolveCommandCwd(options);
  const reference = positionals[0] ?? "";
  const { workspaceRoot, job } = resolveCancelableJob(cwd, reference, { env: process.env });
  const existing = readStoredJob(workspaceRoot, job.id) ?? {};

  const terminate = terminateProcessTree(job.pid ?? Number.NaN);
  if (terminate.attempted) {
    appendLogLine(
      job.logFile,
      terminate.delivered
        ? `Sent SIGTERM to worker pid ${job.pid}.`
        : `Worker pid ${job.pid} was no longer running.`
    );
  }
  appendLogLine(job.logFile, "Cancelled by user.");

  const completedAt = nowIso();
  const nextJob = {
    ...job,
    status: "cancelled",
    phase: "cancelled",
    pid: null,
    completedAt,
    errorMessage: "Cancelled by user."
  };

  writeJobFile(workspaceRoot, job.id, {
    ...existing,
    ...nextJob,
    cancelledAt: completedAt
  });
  upsertJob(workspaceRoot, {
    id: job.id,
    status: "cancelled",
    phase: "cancelled",
    pid: null,
    errorMessage: "Cancelled by user.",
    completedAt
  });

  const payload = {
    jobId: job.id,
    status: "cancelled",
    title: job.title,
    workerSignalled: terminate.delivered
  };

  outputCommandResult(payload, renderCancelReport(nextJob), options.json);
}

async function main() {
  const [subcommand, ...argv] = process.argv.slice(2);
  if (!subcommand || subcommand === "help" || subcommand === "--help") {
    printUsage();
    return;
  }

  switch (subcommand) {
    case "setup":
      await handleSetup(argv);
      break;
    case "review":
      await handleReview(argv);
      break;
    case "adversarial-review":
      await handleReviewCommand(argv, {
        reviewName: "Adversarial Review"
      });
      break;
    case "task":
      await handleTask(argv);
      break;
    case "task-worker":
      await handleTaskWorker(argv);
      break;
    case "status":
      await handleStatus(argv);
      break;
    case "result":
      await handleResult(argv);
      break;
    case "task-resume-candidate":
      await handleTaskResumeCandidate(argv);
      break;
    case "cancel":
      await handleCancel(argv);
      break;
    default:
      throw new Error(`Unknown subcommand: ${subcommand}`);
  }
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exitCode = 1;
});
