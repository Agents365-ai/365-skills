# Pi: Platform Setup
Source: https://pi.dev/docs/latest/windows, /termux, /tmux, /terminal-setup, /shell-aliases

---

> **Auto-built from individual doc pages.**
> Sources: https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/windows.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/termux.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/tmux.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/terminal-setup.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/shell-aliases.md

## Windows

Run Pi either as a native Windows process or inside Windows Subsystem for Linux (WSL). Native Windows uses Git Bash by default for Bash commands and can optionally expose PowerShell to the model. Pi inside WSL uses the Linux environment and its Bash installation.

Follow the main [Quickstart](quickstart.md) to install and authenticate Pi. Use this page to choose and configure its command environment.

## Choose native Windows or WSL

| Environment | Command environment | Use it when |
|---|---|---|
| Native Windows with Git Bash | Git Bash for the built-in `bash` tool and `!` commands | Your files and development tools primarily live on Windows |
| Native Windows with the `powershell` tool | PowerShell for model tool calls; Bash remains available for `!` commands | The task depends on PowerShell modules or Windows-native commands |
| WSL | Linux Bash and tools inside the selected WSL distribution | Your files and toolchain already live in Linux or WSL |

## Use Git Bash on native Windows

For most native Windows users, installing [Git for Windows](https://git-scm.com/download/win) is sufficient.

Pi resolves Bash in this order:

1. `shellPath` from `~/.pi/agent/settings.json`
2. Git Bash under `Program Files` or `Program Files (x86)`
3. `bash.exe` on `PATH`, including Cygwin, MSYS2, or legacy WSL Bash

Start Pi and enter this command to verify the shell:

```text
!printf 'Bash is working\n'
```

If Pi cannot find Bash, it reports the locations it checked. Install Git for Windows, put another Bash executable on `PATH`, or configure `shellPath`.

## Let the model use PowerShell

The optional `powershell` tool runs commands through `pwsh.exe` when available, then falls back to Windows PowerShell. It starts PowerShell with `-NoProfile -NonInteractive -ExecutionPolicy Bypass`. Administrator-enforced execution policies can still take precedence.

To replace the model-facing `bash` tool with `powershell`, add this to `~/.pi/agent/settings.json`:

```json
{
  "defaultTools": ["read", "powershell", "edit", "write"]
}
```

`["-bash", "+powershell"]` does the same while keeping any other default tools you configured.

Restart Pi, then ask it to run a harmless PowerShell command. The `!` and `!!` editor commands continue to use Bash. The `powershell` tool is available only when Pi runs as a native Windows process.

See [Settings](settings.md#tools) for other tool combinations.

## Use a custom Bash executable

Set `shellPath` when Bash is installed somewhere Pi does not discover automatically:

```json
{
  "shellPath": "C:\\cygwin64\\bin\\bash.exe"
}
```

JSON uses backslashes for escape sequences. When you write a Windows path with backslashes, write each backslash twice, as shown above.

See [Configure shell commands](shell-aliases.md) for command prefixes, aliases, and the complete shell-resolution behavior.

## Configure Windows Terminal

Windows Terminal reserves or rewrites some modified keys. See [Windows Terminal](terminal-setup.md#windows-terminal) to configure `Shift+Enter` and `Alt+Enter`, and [Keybindings](keybindings.md) for Pi's Windows and WSL shortcut defaults.

---

## Termux on Android

Pi runs on Android through [Termux](https://termux.dev/), a terminal emulator and Linux environment. Text input, file tools, and shell commands are supported. Pi can copy and paste text through the Android clipboard with Termux:API. Clipboard image paste is not supported.

## Before you begin

Install Termux from [GitHub or F-Droid](https://github.com/termux/termux-app#installation). Do not use the deprecated Google Play build.

[Termux:API](https://github.com/termux/termux-api#installation) is optional. Install it only when you want Pi to copy or paste Android clipboard text, or when shell commands need Android device APIs.

## Install Pi

1. Update Termux packages:

   ```bash
   pkg update && pkg upgrade
   ```

2. Install Node.js and Git:

   ```bash
   pkg install nodejs git
   ```

3. Install Pi:

   ```bash
   npm install -g --ignore-scripts @earendil-works/pi-coding-agent
   ```

4. Verify the installation:

   ```bash
   pi --version
   ```

5. Open the folder you want to work in and start Pi:

   ```bash
   cd /path/to/working-folder
   pi
   ```

Continue with the main [Quickstart](quickstart.md#3-choose-a-model) to connect a model and run your first task.

## Access Android shared storage

Termux cannot access shared Android storage until you grant permission. Run this once:

```bash
termux-setup-storage
```

After approval, Android shared storage is available under `/storage/emulated/0` and through the links Termux creates under `~/storage/`.

Only grant this permission when Pi should be able to access those files. Commands and tools running in Termux use the same storage permissions as the Termux process.

## Use clipboard commands

Pi uses `termux-clipboard-set` to copy text and `termux-clipboard-get` for its clipboard-paste shortcut. Shell commands can use both commands directly. Install the Termux:API app and its command-line package:

```bash
pkg install termux-api
```

Verify the integration:

```bash
printf 'Pi clipboard test' | termux-clipboard-set
termux-clipboard-get
```

The second command should print `Pi clipboard test`.

The Termux clipboard API supports text only. Pi's clipboard-paste shortcut inserts that text into the editor but cannot attach clipboard images.

## Add Termux-specific instructions

Pi detects that it is running in Termux, but it cannot infer how you want it to interact with Android. Add only the environment details relevant to your work to `~/.pi/agent/AGENTS.md`:

````markdown
# Termux environment

- Pi runs in Termux on Android.
- Shared Android storage is under `/storage/emulated/0`.
- Open URLs with `termux-open-url "https://example.com"`.
- Open files with `termux-open <path>`.
- Do not access shared storage unless the task requires it.
````

Run `/reload` after changing the file during an active session.

## Troubleshooting

### Clipboard integration fails

Confirm that you installed both components:

1. The Termux:API Android app from the same source as Termux
2. The `termux-api` command-line package

Then run the clipboard verification commands above outside Pi. If they fail there, fix the Termux:API installation before retrying Pi's copy command.

### Shared storage reports permission denied

Run `termux-setup-storage`, approve the Android permission request, and retry the path under `~/storage/` or `/storage/emulated/0`.

### Pi is not found after installation

Open a new Termux shell and run:

```bash
npm prefix -g
command -v pi
```

Confirm that the global npm binary directory is on `PATH`, then reinstall Pi if the package is missing.

---

## tmux

Pi works inside tmux, but tmux can report `Shift+Enter`, `Ctrl+Enter`, and plain `Enter` as the same key. Enable extended keys so Pi can distinguish them.

## Check your tmux version

```bash
tmux -V
```

For tmux 3.5 or newer, use the recommended CSI-u configuration below. For tmux 3.2 through 3.4, use the older-version configuration.

## Enable extended keys in tmux 3.5 or newer

Add these lines to `~/.tmux.conf`:

```tmux
set -g extended-keys on
set -g extended-keys-format csi-u
```

Pi requests extended-key reporting when the terminal does not provide the Kitty keyboard protocol directly. CSI-u is the most reliable format for forwarding modified keys through tmux.

## Restart tmux

The configuration applies to the tmux server. To guarantee that it is active, close your tmux sessions and start a new server.

If you choose to stop the server from the command line, save your work first. This command terminates every session managed by that server:

```bash
tmux kill-server
tmux
```

## Verify modified keys

Start Pi inside the new tmux session and check that:

1. `Shift+Enter` inserts a new line in the editor.
2. `Enter` submits the prompt.
3. `Alt+Enter` queues a follow-up on macOS and Linux. Windows and WSL use `Ctrl+Q` by default.

If these keys still behave like plain `Enter`, verify that the terminal outside tmux can report modified keys. See [Configure your terminal](terminal-setup.md).

## Use tmux 3.2 through 3.4

These versions support extended keys but not `extended-keys-format csi-u`. Add only:

```tmux
set -g extended-keys on
```

Pi supports the xterm `modifyOtherKeys` format used by these versions. Restart tmux and repeat the verification steps.

For older versions, upgrade tmux or use Pi outside tmux rather than relying on modified Enter shortcuts.

---

## Terminal Setup

Most modern terminals work with Pi without additional setup. Use this page when modified keys, scrolling, links, images, colors, or input-method editor (IME) positioning do not behave as expected.

Pi uses extended-key protocols so terminals can distinguish combinations such as `Shift+Enter` and `Alt+Enter` from plain `Enter`. Terminal proxies, multiplexers, and built-in IDE terminals can change or discard that information.

## Troubleshooting

| Symptom | Start here |
|---|---|
| `Shift+Enter` submits instead of inserting a line | Your terminal's section below; for tmux, see [Run Pi in tmux](tmux.md) |
| `Alt+Enter` does not queue a follow-up | [WezTerm](#wezterm), [Alacritty](#alacritty), or [Windows Terminal](#windows-terminal) |
| Fullscreen scrolling is unusually slow | [iTerm2](#iterm2) |
| Links work but show no hover preview | [Ghostty](#ghostty) |
| Inline images or colors are not detected | [Override detected capabilities](#override-detected-capabilities) |
| An IME candidate window appears in the wrong place | [WezTerm](#wezterm) or [IntelliJ IDEA](#intellij-idea-integrated-terminal) |
| Modified keys fail only inside tmux | [Run Pi in tmux](tmux.md) |

Use `/hotkeys` to inspect Pi's active shortcuts. See [Keybindings](keybindings.md) to change them.

## Kitty

Kitty supports the required keyboard protocol without additional configuration.

## iTerm2

Regular terminal mode works without additional configuration.

### Fix slow fullscreen scrolling

In fullscreen mode, Pi owns the viewport, so iTerm2 sends mouse-wheel reports instead of scrolling native terminal history. Fast trackpad gestures can then move only about one line at a time.

To change this behavior:

1. Open **iTerm2 > Settings > Advanced**.
2. Search for **Trackpad scrolls fast?**.
3. Set it to **No**.

This is an iTerm2-wide setting and can also change native trackpad scrolling. The underlying behavior is tracked in [iTerm2 issue 9619](https://gitlab.com/gnachman/iterm2/-/work_items/9619).

## Apple Terminal

Pi enables enhanced key reporting when available. If Terminal.app still sends plain Return for `Shift+Enter`, Pi uses a local macOS modifier fallback and treats it as `Shift+Enter`.

The fallback works only when Pi runs on the same Mac as Terminal.app. It cannot inspect the local modifier state when Pi runs on another machine over SSH.

## Ghostty

Add this mapping to Ghostty's configuration if `Alt+Backspace` does not work:

```text
keybind = alt+backspace=text:\x1b\x7f
```

The configuration file is `~/Library/Application Support/com.mitchellh.ghostty/config` on macOS and `~/.config/ghostty/config` on Linux.

Older Claude Code configurations may contain:

```text
keybind = shift+enter=text:\n
```

This sends a raw linefeed, which Pi cannot distinguish from `Ctrl+J`. Remove the mapping if an older Claude Code installation is the only reason you added it. Pi already binds `Ctrl+J` as a newline alternative, so the mapping may appear to work while still preventing Pi and tmux from receiving a real `Shift+Enter` event.

### Open links in fullscreen mode

Links remain clickable in fullscreen mode, but Ghostty does not show its normal hover underline or URL preview while Pi captures mouse input. Hold `Shift+Command` on macOS or `Shift+Ctrl` on Linux to use Ghostty's native link handling.

## WezTerm

WezTerm normally reports `Shift+Enter` through xterm extended keys. To enable the Kitty keyboard protocol explicitly, create `~/.wezterm.lua`:

```lua
local wezterm = require 'wezterm'
local config = wezterm.config_builder()
config.enable_kitty_keyboard = true
return config
```

### Forward Alt+Enter on macOS

WezTerm binds `Option+Enter` to fullscreen by default on macOS. To use it for Pi's follow-up queue, add this entry to your `config.keys` table:

```lua
{
  key = 'Enter',
  mods = 'ALT',
  action = wezterm.action.SendString('\x1b[13;3u'),
}
```

A complete minimal configuration is:

```lua
local wezterm = require 'wezterm'
local config = wezterm.config_builder()
config.keys = {
  {
    key = 'Enter',
    mods = 'ALT',
    action = wezterm.action.SendString('\x1b[13;3u'),
  },
}
return config
```

### Position an IME candidate window in WSL

If CJK IME candidates do not follow Pi's text cursor in WSL, show the hardware cursor:

```bash
export PI_HARDWARE_CURSOR=1
pi
```

You can instead set `showHardwareCursor` to `true` in Pi settings.

## Alacritty

Alacritty normally reports `Shift+Enter`. On macOS, `Option+Enter` can arrive as plain `Enter`. Add this to `~/.config/alacritty/alacritty.toml` to forward it to Pi:

```toml
[[keyboard.bindings]]
key = "Enter"
mods = "Alt"
chars = "\u001b[13;3u"
```

Restart Alacritty after changing the file.

## VS Code integrated terminal

VS Code 1.109.5 and newer enable the Kitty keyboard protocol in the integrated terminal by default.

For an older version, add a `Shift+Enter` terminal binding to `keybindings.json`:

```json
{
  "key": "shift+enter",
  "command": "workbench.action.terminal.sendSequence",
  "args": { "text": "\u001b[13;2u" },
  "when": "terminalFocus"
}
```

The user `keybindings.json` file is normally located at:

- macOS: `~/Library/Application Support/Code/User/keybindings.json`
- Linux: `~/.config/Code/User/keybindings.json`
- Windows: `%APPDATA%\\Code\\User\\keybindings.json`

## Zed integrated terminal

Add these bindings to Zed's `keymap.json`:

```json
{
  "context": "Terminal",
  "bindings": {
    "shift-enter": ["terminal::SendText", "\u001b[13;2u"],
    "ctrl--": ["terminal::SendText", "\u001b[45;5u"],
    "ctrl-alt-]": ["terminal::SendText", "\u001b[93;7u"]
  }
}
```

## Windows Terminal

Windows Terminal uses Pi's Windows and WSL shortcut defaults. See [Keybindings](keybindings.md) for the complete list.

### Forward Shift+Enter

Open Windows Terminal's `settings.json` with `Ctrl+Shift+,` or **Settings > Open JSON file**. Add this object to its `actions` array:

```json
{
  "command": { "action": "sendInput", "input": "\u001b[13;2u" },
  "keys": "shift+enter"
}
```

Fully close and reopen Windows Terminal, then verify that `Shift+Enter` inserts a new line in Pi.

### Use Alt+Enter for follow-ups

Windows Terminal binds `Alt+Enter` to fullscreen by default. Pi therefore uses `Ctrl+Q` for follow-ups on Windows and WSL.

To use `Alt+Enter` instead, configure Windows Terminal to forward the key and bind `app.message.followUp` to `alt+enter` in Pi's `keybindings.json`. See [Keybindings](keybindings.md#assign-keybindings).

## xfce4-terminal and Terminator

These terminals cannot reliably distinguish modified Enter keys from plain `Enter`. Custom bindings such as `Ctrl+Enter` or `Shift+Enter` therefore may not work.

Use a terminal with modern extended-key support when you need those shortcuts, such as Kitty, Ghostty, WezTerm, iTerm2, Windows Terminal, or a compatible Alacritty build.

## IntelliJ IDEA integrated terminal

IntelliJ IDEA's built-in terminal cannot reliably distinguish `Shift+Enter` from plain `Enter`. Use `Ctrl+J` for a newline or run Pi in a terminal with modern extended-key support.

If an IME candidate window does not follow the text cursor, show the hardware cursor:

```bash
export PI_HARDWARE_CURSOR=1
pi
```

## Override detected capabilities

Pi automatically detects OSC 8 hyperlinks, inline image protocols, and truecolor support. A terminal proxy or multiplexer can make that detection inaccurate.

| Capability | Environment variable | Setting |
|---|---|---|
| Hyperlinks | `PI_HYPERLINKS=1\|0\|auto` | `terminal.hyperlinks: true\|false\|"auto"` |
| Inline images | `PI_IMAGE_PROTOCOL=kitty\|iterm2\|none\|auto` | `terminal.images: "kitty"\|"iterm2"\|false\|"auto"` |
| Truecolor | `PI_TRUE_COLOR=1\|0\|auto` | `terminal.trueColor: true\|false\|"auto"` |

Settings take precedence over environment variables. An unset value or `auto` preserves automatic detection.

Only force a capability supported by the complete terminal path. Unsupported escape sequences can corrupt rendering. See [Environment Variables](environment-variables.md#pi-process-configuration) and [Settings](settings.md) for the canonical value definitions.

---

## Shell Aliases

Pi starts a separate non-interactive shell process for each Bash command. Non-interactive Bash does not expand aliases by default and usually does not load the same startup files as an interactive terminal.

Use `shellPath` to choose the Bash executable and `shellCommandPrefix` to run setup before each command.

## Understand which shell Pi uses

| Command source | Shell |
|---|---|
| Model calls the built-in `bash` tool | Pi's resolved Bash executable |
| You enter `!command` or `!!command` | The same resolved Bash executable |
| Model calls the optional `powershell` tool | PowerShell 7 (`pwsh.exe`) or Windows PowerShell |
| An extension provides or replaces a shell tool | The operations implemented by that extension |

Pi normally invokes Bash with `bash -c`. On Unix systems, it uses `/bin/bash`, then `bash` on `PATH`, and finally `sh` when Bash is unavailable. Native Windows first checks the configured path, then Git Bash, then `bash.exe` on `PATH`.

## Choose a Bash executable

Set `shellPath` in `~/.pi/agent/settings.json` when Pi should use a specific executable:

```json
{
  "shellPath": "~/.local/bin/bash"
}
```

On Windows, use forward slashes or escape backslashes:

```json
{
  "shellPath": "C:\\cygwin64\\bin\\bash.exe"
}
```

Run `/reload` after changing the setting. See [Run Pi on Windows](windows.md) for the native Windows defaults.

## Run setup before every Bash command

Set `shellCommandPrefix` to prepend shell setup to both the built-in `bash` tool and user-entered `!` or `!!` commands:

```json
{
  "shellCommandPrefix": "export CI=1"
}
```

Pi joins the prefix and requested command with a newline. The prefix runs again for every command, so keep it fast and free of interactive prompts.

## Enable Bash aliases

Store aliases needed by Pi in a Bash-compatible file instead of parsing an entire interactive shell configuration.

Create `~/.bash_aliases`:

```bash
alias ll='ls -la'
alias gs='git status --short'
```

Then configure Pi to enable alias expansion and load the file:

```json
{
  "shellCommandPrefix": "shopt -s expand_aliases\nsource ~/.bash_aliases"
}
```

Run `/reload`, then verify the alias through Pi:

```text
!ll
```

The command should produce the same listing as `ls -la`.

Aliases must use Bash-compatible syntax. Do not source an arbitrary `.zshrc` into Bash because zsh options, functions, and plugins may not parse or behave correctly there.

## Troubleshooting

### The prefix works for `!` but not for an extension tool

`shellCommandPrefix` configures Pi's built-in Bash execution. An extension that replaces the `bash` tool or provides its own shell operations controls its own setup. Check that extension's documentation.

### `shopt` is not found

Pi has fallen back to `sh` or `shellPath` points to a non-Bash shell. Install Bash or set `shellPath` to a Bash executable before using Bash-specific setup such as `shopt`.

### A setup command waits for input

Remove interactive commands from `shellCommandPrefix`. The prefix runs in a non-interactive process before every Bash command.

For the complete setting definitions, see [Shell settings](settings.md#shell).
