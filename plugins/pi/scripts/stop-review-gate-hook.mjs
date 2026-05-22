#!/usr/bin/env node

import fs from "node:fs";
import process from "node:process";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

import { getPiAvailability } from "./lib/pi.mjs";
import { loadPromptTemplate, interpolateTemplate } from "./lib/prompts.mjs";
import { terminateProcessTree } from "./lib/process.mjs";
import { getConfig, listJobs } from "./lib/state.mjs";
import { sortJobsNewestFirst } from "./lib/job-control.mjs";
import { SESSION_ID_ENV } from "./lib/tracked-jobs.mjs";
import { resolveWorkspaceRoot } from "./lib/workspace.mjs";

const STOP_REVIEW_TIMEOUT_MS = 15 * 60 * 1000;
const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(SCRIPT_DIR, "..");

function readHookInput() {
  const raw = fs.readFileSync(0, "utf8").trim();
  if (!raw) {
    return {};
  }
  return JSON.parse(raw);
}

function emitDecision(payload) {
  process.stdout.write(`${JSON.stringify(payload)}\n`);
}

function logNote(message) {
  if (!message) {
    return;
  }
  process.stderr.write(`${message}\n`);
}

function filterJobsForCurrentSession(jobs, input = {}) {
  const sessionId = input.session_id || process.env[SESSION_ID_ENV] || null;
  if (!sessionId) {
    return jobs;
  }
  return jobs.filter((job) => job.sessionId === sessionId);
}

function buildStopReviewPrompt(input = {}) {
  const lastAssistantMessage = String(input.last_assistant_message ?? "").trim();
  const template = loadPromptTemplate(ROOT_DIR, "stop-review-gate");
  const claudeResponseBlock = lastAssistantMessage
    ? ["Previous Claude response:", lastAssistantMessage].join("\n")
    : "";
  return interpolateTemplate(template, {
    CLAUDE_RESPONSE_BLOCK: claudeResponseBlock
  });
}

function buildSetupNote(cwd) {
  const availability = getPiAvailability(cwd);
  if (availability.available) {
    return null;
  }

  const detail = availability.detail ? ` ${availability.detail}.` : "";
  return `Pi is not set up for the review gate.${detail} Run /pi:setup.`;
}

function parseStopReviewOutput(rawOutput) {
  const text = String(rawOutput ?? "").trim();
  if (!text) {
    return {
      ok: false,
      reason:
        "The stop-time Pi review task returned no final output. Run /pi:review --wait manually or bypass the gate."
    };
  }

  const firstLine = text.split(/\r?\n/, 1)[0].trim();
  if (firstLine.startsWith("ALLOW:")) {
    return { ok: true, reason: null };
  }
  if (firstLine.startsWith("BLOCK:")) {
    const reason = firstLine.slice("BLOCK:".length).trim() || text;
    return {
      ok: false,
      reason: `Pi stop-time review found issues that still need fixes before ending the session: ${reason}`
    };
  }

  return {
    ok: false,
    reason:
      "The stop-time Pi review task returned an unexpected answer. Run /pi:review --wait manually or bypass the gate."
  };
}

// Spawn the pi-companion worker in its own process group so that, on timeout,
// terminateProcessTree can SIGTERM (and SIGKILL-escalate) the entire tree —
// including the pi grandchild that would otherwise be orphaned and keep
// burning API quota.
function runStopReview(cwd, input = {}) {
  const scriptPath = path.join(SCRIPT_DIR, "pi-companion.mjs");
  const prompt = buildStopReviewPrompt(input);
  const childEnv = {
    ...process.env,
    ...(input.session_id ? { [SESSION_ID_ENV]: input.session_id } : {})
  };

  return new Promise((resolve) => {
    let child;
    try {
      child = spawn(process.execPath, [scriptPath, "task", "--json", prompt], {
        cwd,
        env: childEnv,
        detached: process.platform !== "win32",
        windowsHide: true,
        stdio: ["ignore", "pipe", "pipe"]
      });
    } catch (error) {
      resolve({
        ok: false,
        reason: `The stop-time Pi review task could not start: ${error instanceof Error ? error.message : String(error)}`
      });
      return;
    }

    let stdout = "";
    let stderr = "";
    let timedOut = false;
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });

    const timer = setTimeout(() => {
      timedOut = true;
      if (Number.isFinite(child.pid)) {
        try {
          terminateProcessTree(child.pid);
        } catch {
          // best-effort
        }
      }
    }, STOP_REVIEW_TIMEOUT_MS);
    timer.unref?.();

    child.on("error", (error) => {
      clearTimeout(timer);
      resolve({
        ok: false,
        reason: `The stop-time Pi review task failed: ${error.message}`
      });
    });

    child.on("close", (code) => {
      clearTimeout(timer);
      if (timedOut) {
        resolve({
          ok: false,
          reason:
            "The stop-time Pi review task timed out after 15 minutes. Run /pi:review --wait manually or bypass the gate."
        });
        return;
      }

      if (code !== 0) {
        const detail = (stderr || stdout).trim();
        resolve({
          ok: false,
          reason: detail
            ? `The stop-time Pi review task failed: ${detail}`
            : "The stop-time Pi review task failed. Run /pi:review --wait manually or bypass the gate."
        });
        return;
      }

      try {
        const payload = JSON.parse(stdout);
        resolve(parseStopReviewOutput(payload?.rawOutput));
      } catch {
        resolve({
          ok: false,
          reason:
            "The stop-time Pi review task returned invalid JSON. Run /pi:review --wait manually or bypass the gate."
        });
      }
    });
  });
}

async function main() {
  const input = readHookInput();
  const cwd = input.cwd || process.env.CLAUDE_PROJECT_DIR || process.cwd();
  const workspaceRoot = resolveWorkspaceRoot(cwd);
  const config = getConfig(workspaceRoot);

  const jobs = sortJobsNewestFirst(filterJobsForCurrentSession(listJobs(workspaceRoot), input));
  const runningJob = jobs.find((job) => job.status === "queued" || job.status === "running");
  const runningTaskNote = runningJob
    ? `Pi task ${runningJob.id} is still running. Check /pi:status and use /pi:cancel ${runningJob.id} if you want to stop it before ending the session.`
    : null;

  if (!config.stopReviewGate) {
    logNote(runningTaskNote);
    return;
  }

  // If the user explicitly enabled the gate but pi is not usable, BLOCK
  // instead of silently letting the session end. A silently-broken gate is
  // worse than no gate: the user believes they have protection but do not.
  const setupNote = buildSetupNote(cwd);
  if (setupNote) {
    emitDecision({
      decision: "block",
      reason: runningTaskNote ? `${runningTaskNote} ${setupNote}` : setupNote
    });
    return;
  }

  const review = await runStopReview(cwd, input);
  if (!review.ok) {
    emitDecision({
      decision: "block",
      reason: runningTaskNote ? `${runningTaskNote} ${review.reason}` : review.reason
    });
    return;
  }

  logNote(runningTaskNote);
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exitCode = 1;
});
