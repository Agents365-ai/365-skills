// Multi-model review panel: merge review results from several models into
// consensus findings. Findings from different models are considered the same
// issue when they hit the same file and overlapping line ranges (with slack,
// since models cite slightly different lines), or share a normalized title
// when line info is missing.

const SEVERITY_RANK = { critical: 0, high: 1, medium: 2, low: 3 };
const LINE_SLACK = 3;

export function severityRank(severity) {
  return SEVERITY_RANK[severity] ?? 3;
}

export function parseModelList(raw) {
  if (!raw) {
    return [];
  }
  const models = [];
  const seen = new Set();
  for (const part of String(raw).split(/[\s,]+/)) {
    const model = part.trim();
    if (model && !seen.has(model)) {
      seen.add(model);
      models.push(model);
    }
  }
  return models;
}

function normalizeTitle(title) {
  return String(title ?? "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function rangesOverlap(a, b, slack = LINE_SLACK) {
  const aStart = a.line_start - slack;
  const aEnd = (a.line_end ?? a.line_start) + slack;
  const bStart = b.line_start;
  const bEnd = b.line_end ?? b.line_start;
  return aStart <= bEnd && bStart <= aEnd;
}

export function findingsMatch(a, b) {
  if ((a.file ?? "") !== (b.file ?? "")) {
    return false;
  }
  if (a.line_start && b.line_start) {
    return rangesOverlap(a, b);
  }
  const titleA = normalizeTitle(a.title);
  return titleA !== "" && titleA === normalizeTitle(b.title);
}

function addAlternateTitle(entry, title) {
  const normalized = normalizeTitle(title);
  if (!normalized || normalized === normalizeTitle(entry.title)) {
    return;
  }
  if (!entry.alsoReportedAs.some((existing) => normalizeTitle(existing) === normalized)) {
    entry.alsoReportedAs.push(title);
  }
}

function mergeFindingInto(entry, finding, model) {
  if (!entry.foundBy.includes(model)) {
    entry.foundBy.push(model);
  }
  // Widen the matched range so later near-duplicates also merge into this entry.
  if (finding.line_start && entry.line_start) {
    entry.line_start = Math.min(entry.line_start, finding.line_start);
    entry.line_end = Math.max(entry.line_end ?? entry.line_start, finding.line_end ?? finding.line_start);
  } else if (finding.line_start && !entry.line_start) {
    entry.line_start = finding.line_start;
    entry.line_end = finding.line_end ?? finding.line_start;
  }
  if (severityRank(finding.severity) < severityRank(entry.severity)) {
    const previousTitle = entry.title;
    entry.severity = finding.severity;
    entry.title = finding.title;
    entry.body = finding.body;
    entry.recommendation = finding.recommendation;
    addAlternateTitle(entry, previousTitle);
  } else {
    addAlternateTitle(entry, finding.title);
  }
}

// runs: [{ model, parsed }] where parsed is a normalized review result
// ({ verdict, summary, findings, next_steps }) or null for a failed run.
export function mergePanelReviews(runs) {
  const succeeded = runs.filter((run) => run.parsed);
  const findings = [];
  const nextSteps = [];
  const seenSteps = new Set();

  for (const run of succeeded) {
    for (const finding of run.parsed.findings) {
      const existing = findings.find((entry) => findingsMatch(entry, finding));
      if (existing) {
        mergeFindingInto(existing, finding, run.model);
      } else {
        findings.push({ ...finding, foundBy: [run.model], alsoReportedAs: [] });
      }
    }
    for (const step of run.parsed.next_steps) {
      const key = step.toLowerCase();
      if (!seenSteps.has(key)) {
        seenSteps.add(key);
        nextSteps.push(step);
      }
    }
  }

  findings.sort((left, right) => {
    if (left.foundBy.length !== right.foundBy.length) {
      return right.foundBy.length - left.foundBy.length;
    }
    if (severityRank(left.severity) !== severityRank(right.severity)) {
      return severityRank(left.severity) - severityRank(right.severity);
    }
    return String(left.file).localeCompare(String(right.file));
  });

  return {
    verdict: succeeded.some((run) => run.parsed.verdict === "needs-attention") ? "needs-attention" : "approve",
    findings,
    next_steps: nextSteps,
    modelCount: succeeded.length
  };
}
