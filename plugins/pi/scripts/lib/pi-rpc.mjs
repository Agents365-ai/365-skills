import { spawn } from "node:child_process";
import process from "node:process";
import { StringDecoder } from "node:string_decoder";

import { terminateProcessTree } from "./process.mjs";

const CHANNEL_DEFAULTS = {
  command: "pi",
  modeArgs: ["--mode", "rpc"],
  extraArgs: []
};

// Cap accumulated stderr to last STDERR_MAX_BYTES so a long-running task
// cannot OOM the companion via verbose pi stderr.
const STDERR_MAX_BYTES = 64 * 1024;

// SIGTERM grace before SIGKILL when closing a stuck pi process.
const KILL_GRACE_MS = 5000;
const SIGTERM_DELAY_MS = 50;

export class PiRpcClient {
  constructor(cwd, options = {}) {
    this.cwd = cwd;
    this.options = options;
    this.command = options.command ?? CHANNEL_DEFAULTS.command;
    this.spawnArgs = [
      ...CHANNEL_DEFAULTS.modeArgs,
      ...(options.spawnArgs ?? CHANNEL_DEFAULTS.extraArgs)
    ];
    this.env = options.env ?? process.env;
    this.proc = null;
    this.pending = new Map();
    this.nextId = 1;
    this.eventHandler = options.eventHandler ?? null;
    this.uiHandler = options.uiHandler ?? null;
    this.stderr = "";
    this.closed = false;
    this.exitError = null;
    this.exitResolved = false;
    this.stdoutBuffer = "";
    this.decoder = new StringDecoder("utf8");
    this.exitDetail = null;
    this._termTimer = null;
    this._killTimer = null;

    this.exitPromise = new Promise((resolve) => {
      this.resolveExit = resolve;
    });
  }

  setEventHandler(handler) {
    this.eventHandler = handler;
  }

  setUiHandler(handler) {
    this.uiHandler = handler;
  }

  async start() {
    try {
      this.proc = spawn(this.command, this.spawnArgs, {
        cwd: this.cwd,
        env: this.env,
        stdio: ["pipe", "pipe", "pipe"],
        shell: process.platform === "win32" ? (process.env.SHELL || true) : false,
        windowsHide: true
      });
    } catch (error) {
      this._handleExit(error);
      throw error;
    }

    this.proc.stderr.setEncoding("utf8");
    this.proc.stderr.on("data", (chunk) => {
      this.stderr += chunk;
      if (this.stderr.length > STDERR_MAX_BYTES * 2) {
        this.stderr = this.stderr.slice(-STDERR_MAX_BYTES);
      }
    });

    this.proc.on("error", (error) => {
      this._handleExit(error);
    });

    // Capture exit code/signal first; resolve the lifecycle promise only on
    // 'close', which fires after all stdio streams are drained. This avoids
    // dropping the final agent_end line that may still be buffered on stdout
    // when 'exit' fires.
    this.proc.on("exit", (code, signal) => {
      if (code !== 0 || signal) {
        this.exitDetail = new Error(
          `pi --mode rpc exited unexpectedly (${signal ? `signal ${signal}` : `exit ${code}`}).`
        );
      }
    });

    this.proc.on("close", () => {
      this._drainStdoutDecoder();
      this._handleExit(this.exitDetail);
    });

    this.proc.stdout.on("data", (chunk) => {
      this._handleChunk(chunk);
    });
  }

  _drainStdoutDecoder() {
    const residual = this.decoder.end();
    if (!residual) {
      return;
    }
    this.stdoutBuffer += residual;
    if (this.stdoutBuffer.length > 0) {
      // Process any complete lines, then any trailing partial line as a final record.
      while (true) {
        const newlineIndex = this.stdoutBuffer.indexOf("\n");
        if (newlineIndex === -1) {
          break;
        }
        let line = this.stdoutBuffer.slice(0, newlineIndex);
        this.stdoutBuffer = this.stdoutBuffer.slice(newlineIndex + 1);
        if (line.endsWith("\r")) {
          line = line.slice(0, -1);
        }
        this._handleLine(line);
      }
      const trailing = this.stdoutBuffer;
      this.stdoutBuffer = "";
      if (trailing.trim()) {
        this._handleLine(trailing);
      }
    }
  }

  _handleChunk(chunk) {
    const decoded = typeof chunk === "string" ? chunk : this.decoder.write(chunk);
    this.stdoutBuffer += decoded;
    while (true) {
      const newlineIndex = this.stdoutBuffer.indexOf("\n");
      if (newlineIndex === -1) {
        break;
      }
      let line = this.stdoutBuffer.slice(0, newlineIndex);
      this.stdoutBuffer = this.stdoutBuffer.slice(newlineIndex + 1);
      if (line.endsWith("\r")) {
        line = line.slice(0, -1);
      }
      this._handleLine(line);
    }
  }

  _handleLine(line) {
    if (!line.trim()) {
      return;
    }

    let message;
    try {
      message = JSON.parse(line);
    } catch (error) {
      this._handleExit(new Error(`Failed to parse pi RPC JSONL: ${error.message}: ${line.slice(0, 200)}`));
      return;
    }

    if (message.type === "response") {
      this._handleResponse(message);
      return;
    }

    if (message.type === "extension_ui_request") {
      this.uiHandler?.(message);
      return;
    }

    this.eventHandler?.(message);
  }

  _handleResponse(message) {
    const id = message.id;
    if (id === undefined || id === null) {
      return;
    }
    const pending = this.pending.get(id);
    if (!pending) {
      return;
    }
    this.pending.delete(id);

    if (message.success) {
      pending.resolve(message.data ?? null);
      return;
    }

    const errorMessage = message.error ?? `pi RPC command ${pending.command} failed.`;
    pending.reject(new Error(errorMessage));
  }

  _clearKillTimers() {
    if (this._termTimer) {
      clearTimeout(this._termTimer);
      this._termTimer = null;
    }
    if (this._killTimer) {
      clearTimeout(this._killTimer);
      this._killTimer = null;
    }
  }

  _handleExit(error) {
    if (this.exitResolved) {
      return;
    }
    this.exitResolved = true;
    this.exitError = error ?? null;
    this._clearKillTimers();

    for (const pending of this.pending.values()) {
      pending.reject(this.exitError ?? new Error("pi RPC connection closed."));
    }
    this.pending.clear();
    this.resolveExit(undefined);
  }

  _writeLine(payload) {
    if (this.closed || !this.proc?.stdin || this.proc.stdin.destroyed) {
      throw new Error("pi RPC stdin is not available.");
    }
    this.proc.stdin.write(`${JSON.stringify(payload)}\n`);
  }

  request(commandObject, options = {}) {
    if (this.closed) {
      throw new Error("pi RPC client is closed.");
    }
    const id = options.id ?? `req-${this.nextId++}`;
    const payload = { id, ...commandObject };

    return new Promise((resolve, reject) => {
      this.pending.set(id, {
        command: commandObject.type ?? "unknown",
        resolve,
        reject
      });

      try {
        this._writeLine(payload);
      } catch (error) {
        this.pending.delete(id);
        reject(error);
      }
    });
  }

  respondToUi(id, response) {
    if (this.closed || !this.proc?.stdin) {
      return;
    }
    this._writeLine({ type: "extension_ui_response", id, ...response });
  }

  async close() {
    if (this.closed) {
      await this.exitPromise;
      return;
    }
    this.closed = true;

    // start() may have failed before assigning this.proc (e.g. spawn threw
    // synchronously); short-circuit so we do not await an exitPromise that
    // nobody will resolve.
    if (!this.proc) {
      this._handleExit(null);
      return;
    }

    try {
      this.proc.stdin?.end();
    } catch {
      // ignore stdin teardown errors
    }

    const procStillAlive = () =>
      this.proc && !this.proc.killed && this.proc.exitCode === null && !this.exitResolved;

    this._termTimer = setTimeout(() => {
      this._termTimer = null;
      if (!procStillAlive()) {
        return;
      }
      try {
        terminateProcessTree(this.proc.pid);
      } catch {
        // best-effort cleanup
      }
      this._killTimer = setTimeout(() => {
        this._killTimer = null;
        if (!procStillAlive()) {
          return;
        }
        if (process.platform === "win32") {
          try {
            terminateProcessTree(this.proc.pid);
          } catch {
            // taskkill /F already attempted; nothing more to do
          }
          return;
        }
        try {
          process.kill(-this.proc.pid, "SIGKILL");
        } catch {
          try {
            this.proc.kill("SIGKILL");
          } catch {
            // process is already gone
          }
        }
      }, KILL_GRACE_MS).unref?.();
    }, SIGTERM_DELAY_MS).unref?.();

    await this.exitPromise;
  }

  // ---- High-level helpers ----

  async getState() {
    return this.request({ type: "get_state" });
  }

  async getAvailableModels() {
    return this.request({ type: "get_available_models" });
  }

  async setSessionName(name) {
    return this.request({ type: "set_session_name", name });
  }

  async setThinkingLevel(level) {
    return this.request({ type: "set_thinking_level", level });
  }

  async setModel(provider, modelId) {
    return this.request({ type: "set_model", provider, modelId });
  }

  async sendPrompt(message, options = {}) {
    return this.request({
      type: "prompt",
      message,
      ...(options.streamingBehavior ? { streamingBehavior: options.streamingBehavior } : {})
    });
  }

  async abort() {
    return this.request({ type: "abort" });
  }

  async getLastAssistantText() {
    return this.request({ type: "get_last_assistant_text" });
  }
}
