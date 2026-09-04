// Sharded parallel review: split changed files across N review jobs that run
// in parallel, each scoped to its own disjoint file subset, then merge the
// per-shard findings into one review result.

import { severityRank } from "./panel.mjs";

// Splits files into up to n round-robin groups. Never returns an empty
// group; if there are fewer files than shards, returns exactly files.length
// groups (one file each) instead of padding with empties.
export function splitFilesIntoShards(files, n) {
  if (files.length === 0) {
    return [];
  }
  const shardCount = Math.max(1, Math.min(n, files.length));
  const shards = Array.from({ length: shardCount }, () => []);
  files.forEach((file, index) => {
    shards[index % shardCount].push(file);
  });
  return shards;
}

// shardResults: array of parsed review results ({ verdict, summary, findings,
// next_steps }), or null for a shard whose review run failed. Shards review
// disjoint file sets, so distinct shards can never report the same finding —
// no cross-shard dedup is needed, unlike the multi-model panel.
export function mergeShardReviews(shardResults) {
  const succeeded = shardResults.filter(Boolean);

  const findings = succeeded.flatMap((result) => result.findings);
  findings.sort((left, right) => severityRank(left.severity) - severityRank(right.severity));

  const nextSteps = [];
  const seenSteps = new Set();
  for (const result of succeeded) {
    for (const step of result.next_steps) {
      const key = step.toLowerCase();
      if (!seenSteps.has(key)) {
        seenSteps.add(key);
        nextSteps.push(step);
      }
    }
  }

  return {
    verdict: succeeded.some((result) => result.verdict === "needs-attention") ? "needs-attention" : "approve",
    summary: succeeded.map((result) => result.summary).filter(Boolean).join(" "),
    findings,
    next_steps: nextSteps,
    shardCount: shardResults.length,
    failedCount: shardResults.length - succeeded.length
  };
}
