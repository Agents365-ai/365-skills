function severityRank(severity) {
  switch (severity) {
    case "critical":
      return 0;
    case "high":
      return 1;
    case "medium":
      return 2;
    default:
      return 3;
  }
}

function formatLineRange(finding) {
  if (!finding.line_start) {
    return "";
  }
  if (!finding.line_end || finding.line_end === finding.line_start) {
    return `:${finding.line_start}`;
  }
  return `:${finding.line_start}-${finding.line_end}`;
}

function pushFinding(lines, finding) {
  const lineSuffix = formatLineRange(finding);
  lines.push(`- [${finding.severity}] ${finding.title} (${finding.file}${lineSuffix})`);
  lines.push(`  ${finding.body}`);
  if (finding.recommendation) {
    lines.push(`  Recommendation: ${finding.recommendation}`);
  }
}

export function validateReviewResultShape(data) {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    return "Expected a top-level JSON object.";
  }
  if (typeof data.verdict !== "string" || !data.verdict.trim()) {
    return "Missing string `verdict`.";
  }
  if (typeof data.summary !== "string" || !data.summary.trim()) {
    return "Missing string `summary`.";
  }
  if (!Array.isArray(data.findings)) {
    return "Missing array `findings`.";
  }
  if (!Array.isArray(data.next_steps)) {
    return "Missing array `next_steps`.";
  }
  return null;
}

function normalizeReviewFinding(finding, index) {
  const source = finding && typeof finding === "object" && !Array.isArray(finding) ? finding : {};
  const lineStart = Number.isInteger(source.line_start) && source.line_start > 0 ? source.line_start : null;
  const lineEnd =
    Number.isInteger(source.line_end) && source.line_end > 0 && (!lineStart || source.line_end >= lineStart)
      ? source.line_end
      : lineStart;

  return {
    severity: typeof source.severity === "string" && source.severity.trim() ? source.severity.trim() : "low",
    title: typeof source.title === "string" && source.title.trim() ? source.title.trim() : `Finding ${index + 1}`,
    body: typeof source.body === "string" && source.body.trim() ? source.body.trim() : "No details provided.",
    file: typeof source.file === "string" && source.file.trim() ? source.file.trim() : "unknown",
    line_start: lineStart,
    line_end: lineEnd,
    recommendation: typeof source.recommendation === "string" ? source.recommendation.trim() : ""
  };
}

export function normalizeReviewResultData(data) {
  return {
    verdict: data.verdict.trim(),
    summary: data.summary.trim(),
    findings: data.findings.map((finding, index) => normalizeReviewFinding(finding, index)),
    next_steps: data.next_steps
      .filter((step) => typeof step === "string" && step.trim())
      .map((step) => step.trim())
  };
}

function isStructuredReviewStoredResult(storedJob) {
  const result = storedJob?.result;
  if (!result || typeof result !== "object" || Array.isArray(result)) {
    return false;
  }
  return (
    Object.prototype.hasOwnProperty.call(result, "result") ||
    Object.prototype.hasOwnProperty.call(result, "parseError")
  );
}

function formatJobLine(job) {
  const parts = [job.id, `${job.status || "unknown"}`];
  if (job.kindLabel) {
    parts.push(job.kindLabel);
  }
  if (job.title) {
    parts.push(job.title);
  }
  return parts.join(" | ");
}

function escapeMarkdownCell(value) {
  return String(value ?? "")
    .replace(/\|/g, "\\|")
    .replace(/\r?\n/g, " ")
    .trim();
}

function formatPiResumeCommand(job) {
  if (!job?.piSessionId) {
    return null;
  }
  return `pi --session ${job.piSessionId}`;
}

function appendActiveJobsTable(lines, jobs) {
  lines.push("Active jobs:");
  lines.push("| Job | Kind | Status | Phase | Elapsed | Pi Session ID | Summary | Actions |");
  lines.push("| --- | --- | --- | --- | --- | --- | --- | --- |");
  for (const job of jobs) {
    const actions = [`/pi:status ${job.id}`];
    if (job.status === "queued" || job.status === "running") {
      actions.push(`/pi:cancel ${job.id}`);
    }
    lines.push(
      `| ${escapeMarkdownCell(job.id)} | ${escapeMarkdownCell(job.kindLabel)} | ${escapeMarkdownCell(job.status)} | ${escapeMarkdownCell(job.phase ?? "")} | ${escapeMarkdownCell(job.elapsed ?? "")} | ${escapeMarkdownCell(job.piSessionId ?? "")} | ${escapeMarkdownCell(job.summary ?? "")} | ${actions.map((action) => `\`${action}\``).join("<br>")} |`
    );
  }
}

function pushJobDetails(lines, job, options = {}) {
  lines.push(`- ${formatJobLine(job)}`);
  if (job.summary) {
    lines.push(`  Summary: ${job.summary}`);
  }
  if (job.phase) {
    lines.push(`  Phase: ${job.phase}`);
  }
  if (options.showElapsed && job.elapsed) {
    lines.push(`  Elapsed: ${job.elapsed}`);
  }
  if (options.showDuration && job.duration) {
    lines.push(`  Duration: ${job.duration}`);
  }
  if (job.piSessionId) {
    lines.push(`  Pi session ID: ${job.piSessionId}`);
  }
  const resumeCommand = formatPiResumeCommand(job);
  if (resumeCommand) {
    lines.push(`  Resume in Pi: ${resumeCommand}`);
  }
  if (job.logFile && options.showLog) {
    lines.push(`  Log: ${job.logFile}`);
  }
  if ((job.status === "queued" || job.status === "running") && options.showCancelHint) {
    lines.push(`  Cancel: /pi:cancel ${job.id}`);
  }
  if (job.status !== "queued" && job.status !== "running" && options.showResultHint) {
    lines.push(`  Result: /pi:result ${job.id}`);
  }
  if (job.status !== "queued" && job.status !== "running" && job.jobClass === "task" && job.write && options.showReviewHint) {
    lines.push("  Review changes: /pi:review --wait");
    lines.push("  Stricter review: /pi:adversarial-review --wait");
  }
  if (job.progressPreview?.length) {
    lines.push("  Progress:");
    for (const line of job.progressPreview) {
      lines.push(`    ${line}`);
    }
  }
}

function appendReasoningSection(lines, reasoningSummary) {
  if (!Array.isArray(reasoningSummary) || reasoningSummary.length === 0) {
    return;
  }

  lines.push("", "Reasoning:");
  for (const section of reasoningSummary) {
    lines.push(`- ${section}`);
  }
}

export function renderSetupReport(report) {
  const lines = [
    "# Pi Setup",
    "",
    `Status: ${report.ready ? "ready" : "needs attention"}`,
    "",
    "Checks:",
    `- node: ${report.node.detail}`,
    `- pi: ${report.pi.detail}`
  ];

  if (report.pi.version) {
    const ok = report.pi.versionWarning ? "!" : "ok";
    lines.push(`  version: ${report.pi.version} (>= 0.75.0 ${ok})`);
  }

  lines.push(`- models: ${report.models.detail}`);

  if (report.availableModels.length > 0) {
    lines.push(`- available models: ${report.availableModels.join(", ")}`);
  }

  const fallbackModels = report.fallbackModels ?? [];
  lines.push(
    fallbackModels.length > 0
      ? `- fallback models: ${fallbackModels.join(", ")}`
      : "- fallback models: none (set PI_PLUGIN_FALLBACK_MODELS=model1,model2 to auto-retry failed runs on another model)"
  );

  if (report.subagents) {
    if (report.subagents.installed) {
      const names = report.subagents.agentNames.length > 0
        ? report.subagents.agentNames.join(", ")
        : "scout, researcher, planner, worker, reviewer, context-builder, oracle, delegate";
      lines.push(`- pi-subagents: installed (${report.subagents.agentCount} agents: ${names})`);
    } else {
      lines.push("- pi-subagents: not installed (run `pi install npm:pi-subagents` to enable parallel subagents)");
    }
  }

  lines.push(
    `- session runtime: ${report.sessionRuntime.label}`,
    `- review gate: ${report.reviewGateEnabled ? "enabled" : "disabled"}`,
    ""
  );

  if (report.actionsTaken.length > 0) {
    lines.push("Actions taken:");
    for (const action of report.actionsTaken) {
      lines.push(`- ${action}`);
    }
    lines.push("");
  }

  if (report.nextSteps.length > 0) {
    lines.push("Next steps:");
    for (const step of report.nextSteps) {
      lines.push(`- ${step}`);
    }
  }

  return `${lines.join("\n").trimEnd()}\n`;
}

// Compact severity breakdown, e.g. "5 findings: 1 critical, 2 high, 2 low".
function summarizeSeverityCounts(findings) {
  if (findings.length === 0) {
    return "No material findings.";
  }
  const counts = new Map();
  for (const finding of findings) {
    const severity = finding.severity || "low";
    counts.set(severity, (counts.get(severity) ?? 0) + 1);
  }
  const parts = [...counts.entries()]
    .sort((left, right) => severityRank(left[0]) - severityRank(right[0]))
    .map(([severity, count]) => `${count} ${severity}`);
  return `${findings.length} finding${findings.length === 1 ? "" : "s"}: ${parts.join(", ")}`;
}

// --out-file mode: the full rendered output is written to a file; only this
// short summary is relayed to the caller, so a large review does not flood the
// caller's context. Reviews get verdict + severity counts + one line per
// finding; free-form runs (task/race) fall back to their one-line summary.
export function renderOutFileSummary(execution, outFile) {
  const lines = [];
  const result = execution.payload?.result;
  const findings = Array.isArray(result?.findings) ? result.findings : null;
  if (result && typeof result.verdict === "string" && result.verdict.trim()) {
    lines.push(`Verdict: ${result.verdict}`);
  }
  if (findings) {
    lines.push(summarizeSeverityCounts(findings));
    const sorted = [...findings].sort((left, right) => severityRank(left.severity) - severityRank(right.severity));
    for (const finding of sorted) {
      lines.push(`- [${finding.severity}] ${finding.title} (${finding.file}${formatLineRange(finding)})`);
    }
  } else if (execution.summary) {
    lines.push(execution.summary);
  }
  lines.push("", `Full output written to ${outFile}`);
  return `${lines.join("\n")}\n`;
}

export function renderReviewResult(parsedResult, meta) {
  if (!parsedResult.parsed) {
    const lines = [
      `# Pi ${meta.reviewLabel}`,
      "",
      "Pi did not return valid structured JSON.",
      "",
      `- Parse error: ${parsedResult.parseError}`
    ];

    if (parsedResult.rawOutput) {
      lines.push("", "Raw final message:", "", "```text", parsedResult.rawOutput, "```");
    }

    appendReasoningSection(lines, meta.reasoningSummary ?? parsedResult.reasoningSummary);

    return `${lines.join("\n").trimEnd()}\n`;
  }

  const validationError = validateReviewResultShape(parsedResult.parsed);
  if (validationError) {
    const lines = [
      `# Pi ${meta.reviewLabel}`,
      "",
      `Target: ${meta.targetLabel}`,
      "Pi returned JSON with an unexpected review shape.",
      "",
      `- Validation error: ${validationError}`
    ];

    if (parsedResult.rawOutput) {
      lines.push("", "Raw final message:", "", "```text", parsedResult.rawOutput, "```");
    }

    appendReasoningSection(lines, meta.reasoningSummary ?? parsedResult.reasoningSummary);

    return `${lines.join("\n").trimEnd()}\n`;
  }

  const data = normalizeReviewResultData(parsedResult.parsed);
  const findings = [...data.findings].sort((left, right) => severityRank(left.severity) - severityRank(right.severity));
  const lines = [
    `# Pi ${meta.reviewLabel}`,
    "",
    `Target: ${meta.targetLabel}`,
    `Verdict: ${data.verdict}`,
    "",
    data.summary,
    ""
  ];

  if (findings.length === 0) {
    lines.push("No material findings.");
  } else {
    lines.push("Findings:");
    for (const finding of findings) {
      pushFinding(lines, finding);
    }
  }

  if (data.next_steps.length > 0) {
    lines.push("", "Next steps:");
    for (const step of data.next_steps) {
      lines.push(`- ${step}`);
    }
  }

  appendReasoningSection(lines, meta.reasoningSummary);

  return `${lines.join("\n").trimEnd()}\n`;
}

function pushPanelFinding(lines, finding) {
  const lineSuffix = formatLineRange(finding);
  lines.push(`- [${finding.severity}] ${finding.title} (${finding.file}${lineSuffix}) — found by: ${finding.foundBy.join(", ")}`);
  lines.push(`  ${finding.body}`);
  if (finding.alsoReportedAs.length > 0) {
    lines.push(`  Also reported as: ${finding.alsoReportedAs.map((title) => `"${title}"`).join(", ")}`);
  }
  if (finding.recommendation) {
    lines.push(`  Recommendation: ${finding.recommendation}`);
  }
}

// panel: merged review data plus per-model member outcomes:
// { verdict, findings, next_steps, members: [{ model, ok, findingCount, summary, failure }] }
export function renderPanelReviewResult(panel, meta) {
  const okCount = panel.members.filter((member) => member.ok).length;
  const lines = [
    `# Pi Panel ${meta.reviewLabel}`,
    "",
    `Target: ${meta.targetLabel}`,
    `Models: ${okCount}/${panel.members.length} succeeded`
  ];

  for (const member of panel.members) {
    if (member.ok) {
      lines.push(`- ${member.model}: ok (${member.findingCount} finding${member.findingCount === 1 ? "" : "s"})`);
      if (member.summary) {
        lines.push(`  ${member.summary}`);
      }
    } else {
      lines.push(`- ${member.model}: failed — ${member.failure}`);
    }
  }
  lines.push("");

  if (okCount === 0) {
    lines.push("All panel models failed; no review result was produced.");
    return `${lines.join("\n").trimEnd()}\n`;
  }

  lines.push(`Verdict: ${panel.verdict}`, "");

  const consensus = panel.findings.filter((finding) => finding.foundBy.length >= 2);
  const singleSource = panel.findings.filter((finding) => finding.foundBy.length === 1);

  if (panel.findings.length === 0) {
    lines.push("No material findings from any model.");
  }
  if (consensus.length > 0) {
    lines.push("Consensus findings (2+ models):");
    for (const finding of consensus) {
      pushPanelFinding(lines, finding);
    }
    lines.push("");
  }
  if (singleSource.length > 0) {
    lines.push("Single-model findings:");
    for (const finding of singleSource) {
      pushPanelFinding(lines, finding);
    }
    lines.push("");
  }

  if (panel.next_steps.length > 0) {
    if (lines[lines.length - 1] !== "") {
      lines.push("");
    }
    lines.push("Next steps:");
    for (const step of panel.next_steps) {
      lines.push(`- ${step}`);
    }
  }

  return `${lines.join("\n").trimEnd()}\n`;
}

// sharded: merged review data plus per-shard outcomes:
// { verdict, summary, findings, next_steps, shards: [{ index, files, ok, findingCount, failure }] }
export function renderShardedReviewResult(sharded, meta) {
  const okCount = sharded.shards.filter((shard) => shard.ok).length;
  const lines = [
    `# Pi Sharded ${meta.reviewLabel}`,
    "",
    `Target: ${meta.targetLabel}`,
    `Sharded across ${sharded.shards.length} review jobs: ${okCount}/${sharded.shards.length} succeeded`
  ];

  for (const shard of sharded.shards) {
    const fileList = shard.files.join(", ");
    if (shard.ok) {
      lines.push(`- shard ${shard.index + 1} (${fileList}): ok (${shard.findingCount} finding${shard.findingCount === 1 ? "" : "s"})`);
    } else {
      lines.push(`- shard ${shard.index + 1} (${fileList}): failed — ${shard.failure}`);
    }
  }
  lines.push("");

  if (okCount === 0) {
    lines.push("All review shards failed; no review result was produced.");
    return `${lines.join("\n").trimEnd()}\n`;
  }

  lines.push(`Verdict: ${sharded.verdict}`, "");
  if (sharded.summary) {
    lines.push(sharded.summary, "");
  }

  if (sharded.findings.length === 0) {
    lines.push("No material findings.");
  } else {
    lines.push("Findings:");
    for (const finding of sharded.findings) {
      pushFinding(lines, finding);
    }
  }

  if (sharded.next_steps.length > 0) {
    lines.push("", "Next steps:");
    for (const step of sharded.next_steps) {
      lines.push(`- ${step}`);
    }
  }

  return `${lines.join("\n").trimEnd()}\n`;
}

// race: { write, dirtyWarning, racers: [{ model, ok, finalMessage, failure,
//   patchFile, patchStat, patchEmpty, piSessionId }] }
export function renderRaceResult(race, meta) {
  const okCount = race.racers.filter((racer) => racer.ok).length;
  const lines = [
    `# Pi Race (${race.racers.length} models)`,
    "",
    `Task: ${meta.taskSummary}`,
    race.write
      ? "Mode: write — each racer ran in an isolated git worktree created from HEAD"
      : "Mode: read-only — racers analyzed the same working tree"
  ];
  if (race.dirtyWarning) {
    lines.push(`Warning: ${race.dirtyWarning}`);
  }
  lines.push("");

  for (const racer of race.racers) {
    lines.push(`## ${racer.model} — ${racer.ok ? "ok" : "failed"}`);
    if (!racer.ok) {
      lines.push("", racer.failure || "Run failed.", "");
      continue;
    }
    if (racer.finalMessage?.trim()) {
      lines.push("", racer.finalMessage.trim(), "");
    }
    if (race.write) {
      if (racer.patchEmpty || !racer.patchFile) {
        lines.push("Patch: no file changes.", "");
      } else {
        lines.push("Patch:", "```text", racer.patchStat, "```", `Apply with: git apply ${racer.patchFile}`, "");
      }
    }
    if (racer.piSessionId) {
      lines.push(`Resume in Pi: pi --session ${racer.piSessionId}`, "");
    }
  }

  if (okCount === 0) {
    lines.push("All racers failed.");
  } else if (race.write) {
    lines.push("Pick a winner: review each patch, then apply exactly one with `git apply <patch>`.");
  } else {
    lines.push("Pick a winner: compare the answers above; agreement across models is a strong signal.");
  }

  return `${lines.join("\n").trimEnd()}\n`;
}

export function renderTaskResult(parsedResult, _meta) {
  const rawOutput = typeof parsedResult?.rawOutput === "string" ? parsedResult.rawOutput : "";
  if (rawOutput) {
    return rawOutput.endsWith("\n") ? rawOutput : `${rawOutput}\n`;
  }

  const message = String(parsedResult?.failureMessage ?? "").trim() || "Pi did not return a final message.";
  return `${message}\n`;
}

export function renderStatusReport(report) {
  const lines = [
    "# Pi Status",
    "",
    `Session runtime: ${report.sessionRuntime.label}`,
    `Review gate: ${report.config.stopReviewGate ? "enabled" : "disabled"}`,
    ""
  ];

  if (report.running.length > 0) {
    appendActiveJobsTable(lines, report.running);
    lines.push("");
    lines.push("Live details:");
    for (const job of report.running) {
      pushJobDetails(lines, job, {
        showElapsed: true,
        showLog: true
      });
    }
    lines.push("");
  }

  if (report.latestFinished) {
    lines.push("Latest finished:");
    pushJobDetails(lines, report.latestFinished, {
      showDuration: true,
      showLog: report.latestFinished.status === "failed"
    });
    lines.push("");
  }

  if (report.recent.length > 0) {
    lines.push("Recent jobs:");
    for (const job of report.recent) {
      pushJobDetails(lines, job, {
        showDuration: true,
        showLog: job.status === "failed"
      });
    }
    lines.push("");
  } else if (report.running.length === 0 && !report.latestFinished) {
    lines.push("No jobs recorded yet.", "");
  }

  if (report.needsReview) {
    lines.push("The stop-time review gate is enabled.");
    lines.push("Ending the session will trigger a fresh Pi adversarial review and block if it finds issues.");
  }

  return `${lines.join("\n").trimEnd()}\n`;
}

export function renderJobStatusReport(job) {
  const lines = ["# Pi Job Status", ""];
  pushJobDetails(lines, job, {
    showElapsed: job.status === "queued" || job.status === "running",
    showDuration: job.status !== "queued" && job.status !== "running",
    showLog: true,
    showCancelHint: true,
    showResultHint: true,
    showReviewHint: true
  });
  return `${lines.join("\n").trimEnd()}\n`;
}

export function renderStoredJobResult(job, storedJob) {
  const piSessionId = storedJob?.piSessionId ?? job.piSessionId ?? null;
  const resumeCommand = piSessionId ? `pi --session ${piSessionId}` : null;
  if (isStructuredReviewStoredResult(storedJob) && storedJob?.rendered) {
    const output = storedJob.rendered.endsWith("\n") ? storedJob.rendered : `${storedJob.rendered}\n`;
    if (!piSessionId) {
      return output;
    }
    return `${output}\nPi session ID: ${piSessionId}\nResume in Pi: ${resumeCommand}\n`;
  }

  const rawOutput =
    (typeof storedJob?.result?.rawOutput === "string" && storedJob.result.rawOutput) ||
    (typeof storedJob?.result?.pi?.stdout === "string" && storedJob.result.pi.stdout) ||
    "";
  if (rawOutput) {
    const output = rawOutput.endsWith("\n") ? rawOutput : `${rawOutput}\n`;
    if (!piSessionId) {
      return output;
    }
    return `${output}\nPi session ID: ${piSessionId}\nResume in Pi: ${resumeCommand}\n`;
  }

  if (storedJob?.rendered) {
    const output = storedJob.rendered.endsWith("\n") ? storedJob.rendered : `${storedJob.rendered}\n`;
    if (!piSessionId) {
      return output;
    }
    return `${output}\nPi session ID: ${piSessionId}\nResume in Pi: ${resumeCommand}\n`;
  }

  const lines = [
    `# ${job.title ?? "Pi Result"}`,
    "",
    `Job: ${job.id}`,
    `Status: ${job.status}`
  ];

  if (piSessionId) {
    lines.push(`Pi session ID: ${piSessionId}`);
    lines.push(`Resume in Pi: ${resumeCommand}`);
  }

  if (job.summary) {
    lines.push(`Summary: ${job.summary}`);
  }

  if (job.errorMessage) {
    lines.push("", job.errorMessage);
  } else if (storedJob?.errorMessage) {
    lines.push("", storedJob.errorMessage);
  } else {
    lines.push("", "No captured result payload was stored for this job.");
  }

  return `${lines.join("\n").trimEnd()}\n`;
}

export function renderCancelReport(job) {
  const lines = [
    "# Pi Cancel",
    "",
    `Cancelled ${job.id}.`,
    ""
  ];

  if (job.title) {
    lines.push(`- Title: ${job.title}`);
  }
  if (job.summary) {
    lines.push(`- Summary: ${job.summary}`);
  }
  lines.push("- Check `/pi:status` for the updated queue.");

  return `${lines.join("\n").trimEnd()}\n`;
}
