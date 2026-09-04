import fs from "node:fs";
import path from "node:path";

import { resolveStateDir } from "./state.mjs";

const REVIEW_CACHE_FILE_NAME = "review-cache.json";

export function reviewCacheFile(workspaceRoot) {
  return path.join(resolveStateDir(workspaceRoot), REVIEW_CACHE_FILE_NAME);
}

export function readReviewCache(workspaceRoot, branch) {
  const file = reviewCacheFile(workspaceRoot);
  if (!fs.existsSync(file)) {
    return null;
  }
  try {
    const parsed = JSON.parse(fs.readFileSync(file, "utf8"));
    return parsed?.[branch]?.sha ?? null;
  } catch {
    return null;
  }
}

export function writeReviewCache(workspaceRoot, branch, sha) {
  const file = reviewCacheFile(workspaceRoot);
  let cache = {};
  try {
    cache = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    cache = {};
  }
  cache[branch] = { sha, reviewedAt: new Date().toISOString() };
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(cache, null, 2)}\n`, "utf8");
}
