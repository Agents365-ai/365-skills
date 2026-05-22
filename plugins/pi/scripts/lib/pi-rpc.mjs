import { spawn } from "node:child_process";
import process from "node:process";
import { StringDecoder } from "node:string_decoder";

import { terminateProcessTree } from "./process.mjs";

const CHANNEL_DEFAULTS = {
  command: "pi",
  modeArgs: ["--mode", "rpc"],
  extraArgs: []
};

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
    this.proc = spawn(this.command, this.spawnArgs, {
      cwd: this.cwd,
      env: this.env,
      stdio: ["pipe", "pipe", "pipe"],
      shell: process.platform === "win32" ? (process.env.SHELL || true) : false,
      windowsHide: true
    });

    this.proc.stderr.setEncoding("utf8");
    this.proc.stderr.on("data", (chunk) => {
      this.stderr += chunk;
    });

    this.proc.on("error", (error) => {
      this._handleExit(error);
    });

    this.proc.on("exit", (code, signal) => {
      const detail =
        code === 0
          ? null
          : new Error(`pi --mode rpc exited unexpectedly (${signal ? `signal ${signal}` : `exit ${code}`}).`);
      this._handleExit(detail);
    });

    this.proc.stdout.on("data", (chunk) => {
      this._handleChunk(chunk);
    });
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

  _handleExit(error) {
    if (this.exitResolved) {
      return;
    }
    this.exitResolved = true;
    this.exitError = error ?? null;

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

  command_send(commandObject, options = {}) {
    return this.request(commandObject, options);
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

    try {
      this.proc?.stdin?.end();
    } catch {
      // ignore stdin teardown errors
    }

    setTimeout(() => {
      if (this.proc && !this.proc.killed && this.proc.exitCode === null) {
        if (process.platform === "win32") {
          try {
            terminateProcessTree(this.proc.pid);
          } catch {
            // best-effort
          }
        } else {
          try {
            this.proc.kill("SIGTERM");
          } catch {
            // process may already be gone
          }
        }
      }
    }, 50).unref?.();

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
