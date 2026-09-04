// Automatic model fallback: when a Pi run fails (provider outage, auth error,
// exhausted auto-retry), retry the same request with the next model in the
// configured fallback chain instead of failing the whole job.

export function buildModelChain(primaryModel, fallbackModels = []) {
  const chain = [primaryModel ?? null];
  for (const model of fallbackModels) {
    if (model && model !== primaryModel && !chain.includes(model)) {
      chain.push(model);
    }
  }
  return chain;
}

function shortenError(message, limit = 160) {
  const normalized = String(message ?? "").trim().replace(/\s+/g, " ");
  if (normalized.length <= limit) {
    return normalized || "unknown error";
  }
  return `${normalized.slice(0, limit - 3)}...`;
}

export function modelLabel(model) {
  return model ?? "pi default model";
}

// runOnce(model) must resolve to a result object with a numeric `status`
// (0 = success) and optional `error.message`; it may also throw. With a
// single-entry chain (no fallbacks configured) behavior is identical to
// calling runOnce directly: throws propagate, the result is returned as-is.
export async function runWithModelFallback(chain, runOnce, onProgress = null) {
  const attempts = [];
  let result = null;

  for (let index = 0; index < chain.length; index += 1) {
    const model = chain[index];
    try {
      result = await runOnce(model);
    } catch (error) {
      if (index === chain.length - 1) {
        // Nothing left to fall back to — preserve the original throwing behavior.
        throw error;
      }
      result = { status: 1, error: { message: error instanceof Error ? error.message : String(error) } };
    }

    attempts.push({
      model: modelLabel(model),
      status: result.status,
      error: result.status === 0 ? null : shortenError(result.error?.message)
    });

    if (result.status === 0) {
      break;
    }

    const next = chain[index + 1];
    if (next !== undefined) {
      onProgress?.({
        message: `Model ${modelLabel(model)} failed (${shortenError(result.error?.message)}); falling back to ${next}.`,
        phase: "starting"
      });
    }
  }

  return { result, attempts };
}

export function describeFallback(attempts) {
  if (!Array.isArray(attempts) || attempts.length <= 1) {
    return null;
  }
  const finalAttempt = attempts[attempts.length - 1];
  const failed = attempts
    .slice(0, -1)
    .map((attempt) => `${attempt.model} failed (${attempt.error})`)
    .join("; ");
  if (finalAttempt.status === 0) {
    return `Model fallback: ${failed} -> succeeded with ${finalAttempt.model}.`;
  }
  return `Model fallback: ${failed} -> ${finalAttempt.model} also failed (${finalAttempt.error}).`;
}
