// Model racing: run the same rescue task with several models in parallel and
// let the caller pick the winner. Write races isolate each racer in its own
// git worktree (created from HEAD) and capture the result as a patch.

import path from "node:path";

export function sanitizeModelForPath(model) {
  const sanitized = String(model ?? "")
    .replace(/[^a-zA-Z0-9._-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return sanitized || "model";
}

// Models like "provider/model" and "provider-model" can sanitize to the same
// slug; uniquify with an index suffix so worktree paths and patch files never
// collide. Checked against already-produced slugs (not just base counts), so
// a later racer's own natural slug can't collide with an earlier uniquified
// one (e.g. "x/y", "x-y", "x:y" all sanitize toward "x-y").
export function buildRacerLabels(models) {
  const used = new Set();
  return models.map((model) => {
    const base = sanitizeModelForPath(model);
    let slug = base;
    let suffix = 1;
    while (used.has(slug)) {
      suffix += 1;
      slug = `${base}-${suffix}`;
    }
    used.add(slug);
    return { model, slug };
  });
}

export function buildRaceWorktreePath(baseDir, jobId, slug) {
  return path.join(baseDir, `pi-race-${jobId}`, slug);
}
