---
name: tmux-skill
description: "Use tmux from the command line to run, drive, and monitor terminal programs as a coding agent (detached sessions, send-keys input injection, capture-pane output polling, formats, completion detection, and control mode). Use when a task needs long-running or interactive processes (builds, tests, servers, REPLs, watch modes, TUI apps) kept alive across turns or inspected live; skip when plain `cmd > log 2>&1 &` is enough."
license: CC-BY-NC-4.0
author: Agents365-ai
created: 2026-07-25
updated: 2026-07-25
version: 0.1.0
metadata: {"homepage":"https://github.com/Agents365-ai/365-skills","openclaw":{"requires":{"bins":["tmux"]},"emoji":"🖥️"}}
---

# tmux for coding agents

tmux is a terminal multiplexer: it runs programs inside panes that survive
terminal closures and can be inspected, driven, and re-attached programmatically.
This skill covers **non-interactive (programmatic) tmux use**: the way a coding
agent should drive it from the shell. Grounded in the official
[tmux wiki](https://github.com/tmux/tmux/wiki).

## When to use tmux (and when not)

Use tmux when you need any of:

- a process to **outlive the agent turn / terminal** (long builds, servers, watches)
- **interactivity**: REPLs, programs that prompt, TUI apps (vim, htop, fzf)
- a real **TTY** (tools that refuse without `isatty`, or need a fixed window size)
- to **peek at live output** while it runs, or let the human `attach` and watch

Skip tmux when plain redirection is enough: `cmd > out.log 2>&1` or
`cmd &` / `nohup` is simpler and you never need to read a TUI.

## Mental model

```text
server (one per socket, auto-started, exits when last session dies)
└── sessions ($0, $1, ... unique names)
    └── windows (@0, @1, ... named, linked to 1+ sessions)
        └── panes (%0, %1, ... one terminal + one running program each)
```

- **Prefer unique IDs** (`$3` session, `@2` window, `%5` pane) over names/indexes
  in scripts: they are unambiguous and stable across renames/reorderings.
- The default socket is shared with the user's tmux. For agent-owned sessions use
  an isolated socket: `tmux -L pi-agent ...`. The same flags apply to every command.

## Core loop (the canonical pattern)

```bash
# 1. Create a detached session with a fixed size (else it defaults to 80x24,
#    which mangles wide output you later capture)
tmux -L pi-agent new-session -d -s build -x 220 -y 50

# 2. Send a command. Append an echo sentinel to detect completion reliably.
#    Grep the EXPANDED sentinel (__DONE__:<digits>): the echoed command line still
#    contains the literal "$?", so a plain grep for __DONE__ matches the echo
#    before the command even runs.
tmux -L pi-agent send-keys -t build 'make 2>&1; echo "__DONE__:$?"' Enter

# 3. Poll for the sentinel in the pane output
until tmux -L pi-agent capture-pane -p -t build | grep -q '__DONE__:[0-9]'; do sleep 1; done

# 4. Read the result (including scrollback)
tmux -L pi-agent capture-pane -p -S -2000 -t build
#    -> last line tells you the exit code after "__DONE__:"

# 5. Clean up (or leave it running for the human to attach to)
tmux -L pi-agent kill-session -t build
```

Polling with a sentinel is the most robust completion detector. `tmux wait-for`
(chan / `wait-for -S chan`) also works but races: if the signal fires before you
start waiting, you hang forever: only use it when you control both ends.

## Command cheat sheet

```bash
tmux ls                                   # list sessions (exit 1 + "no server running" = none; not an error)
tmux new-session -d -s NAME               # detached session; -x/-y set size; -c DIR sets start dir
tmux new-session -A -s NAME               # attach-or-create (human-facing convenience)
tmux send-keys -t TGT 'cmd' Enter         # type into a pane; Enter is a KEY NAME, not "\n"
tmux capture-pane -p -t TGT               # pane text to stdout (-S -3000 scrollback, -J join wrapped lines)
tmux list-panes -a -F FMT                 # enumerate panes with a format string
tmux display-message -p -t TGT '#{...}'   # expand a format for one target
tmux kill-session -t NAME                 # kill one session; kill-server kills everything
tmux split-window -h -t TGT 'cmd'         # new pane right; -v below; -d don't focus it; -b before
tmux select-pane -t %5                    # make a pane active
tmux set-option -t TGT remain-on-exit on  # keep pane (and its output) after the process exits
tmux respawn-pane -t %5                   # restart the program in a dead pane
tmux rename-window -t @2 name             # windows auto-rename by default; pin with rename or disable automatic-rename
tmux run-shell 'cmd'                      # run once in tmux's shell, no pane
tmux set-hook -t s hook 'cmds'            # run tmux commands on events (pane-died, after-send-keys, ...)
tmux wait-for CHAN / wait-for -S CHAN     # synchronization primitive (see race caveat above)
```

`-t` targets: `session:window.pane`, e.g. `build:0.1`, or a bare ID `-t %5` /
`-t @2` / `-t '$3'`. Quoted `$` so the shell doesn't expand session IDs.

## send-keys rules

```bash
tmux send-keys -t build 'echo "a b"' Enter      # args are typed into the pane; the pane's
                                                # shell does the parsing: your quoting must
                                                # survive tmux AND the target shell
tmux send-keys -t build C-c                     # send Ctrl-C to interrupt
tmux send-keys -t build Up Enter                # repeat last command (shell history)
tmux send-keys -t repl 'x = 1' Enter            # drive a REPL one statement at a time
tmux send-keys -t build -l '100%'               # -l: literal text, key names like "Enter" not interpreted
tmux send-keys -t build -H 41 42                # -H: hex-encoded keys (unicode-safe)
```

- `Enter`, `Tab`, `Space`, `BSpace`, `C-c`, `C-l`, `Up`, `Down`, `Escape`, `F1`.. are
  **key names**; unknown args are typed as literal text.
- Never send `"\n"` expecting a newline: that types the two characters `\` `n`. Send `Enter`.
- For anything with gnarly quoting (heredocs, nested quotes), **write a script file
  and send `bash /tmp/script.sh` Enter** instead of fighting quoting layers.
- `send-keys` fires and returns immediately; it does not wait for the program to act.
- Never script the `C-b` prefix: that is for humans with an attached client. Use tmux
  commands directly.

## capture-pane rules

- **Default captures only the visible screen.** Use `-S -3000` for the last N lines
  of scrollback, `-S -` for the whole history (bounded by `history-limit`, default 2000).
- `-S 0 -` captures from the top of the screen to the end of history: `-S 0 -E -`.
- `-J` joins soft-wrapped lines into logical lines: usually what you want when parsing.
- `-e` includes ANSI escape sequences (colours); omit for clean text.
- Lines may carry trailing spaces; strip with `sed -e 's/[[:space:]]*$//'` when comparing.
- `-a` captures the alternate screen (TUI apps that draw the whole screen).

## Formats (the inspection API)

`-F` on list commands and `display-message -p` give machine-readable facts:

```bash
tmux -L pi-agent list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_id} cmd=#{pane_current_command} pid=#{pane_pid} dead=#{pane_dead} path=#{pane_current_path}'
tmux -L pi-agent display-message -p -t build '#{pane_pid} #{history_size} #{cursor_y}'
```

Useful variables: `#{session_id}`/`#{session_name}`/`#{session_attached}`,
`#{window_id}`/`#{window_index}`/`#{window_name}`/`#{window_active}`,
`#{pane_id}`/`#{pane_index}`/`#{pane_active}`/`#{pane_dead}`/`#{pane_pid}`/
`#{pane_current_command}`/`#{pane_current_path}`/`#{pane_title}`/`#{pane_in_mode}`,
`#{history_size}`, `#{socket_name}`, `#{pid}` (server PID). Escape with `#{q:...}`.
Full list: `man 1 tmux`, FORMATS section.

## Completion detection, four ways

1. **Sentinel echo** (default, race-free): `send ... 'cmd; echo __DONE__:$?' Enter`, poll `capture-pane | grep`.
2. **`remain-on-exit` + `#{pane_dead}`**: set the option, run the command directly,
   then wait for `display-message -p -t %5 '#{pane_dead}'` to print `1`. The pane
   keeps its output until you `respawn-pane` or `kill-pane`.
3. **Process check**: `#{pane_pid}` is the pane's shell; if you launched `cmd`
   directly as the pane command, its exit kills the pane (combine with way 2).
4. **`wait-for`**: only when you also control ordering (see race caveat above).

## Recipes

### Long job, watched by the human too

```bash
tmux -L pi-agent new-session -d -s train -x 220 -y 50
tmux -L pi-agent send-keys -t train './train.sh' Enter
echo "watch with: tmux -L pi-agent attach -t train"   # hand this to the user
```

### Multi-pane monitor

```bash
tmux -L pi-agent new-session -d -s mon -x 220 -y 50 -c "$PWD"
tmux -L pi-agent send-keys -t mon 'tail -f app.log' Enter
tmux -L pi-agent split-window -v -t mon
tmux -L pi-agent send-keys -t mon.1 'watch -n5 df -h' Enter
# capture one specific pane: -t mon.0 / -t mon.1, or the pane ID
```

### REPL / interactive program

```bash
tmux -L pi-agent new-session -d -s repl -x 220 -y 50 'python3 -i'
sleep 1                                          # let it start before typing
tmux -L pi-agent send-keys -t repl 'print(6*7)' Enter
sleep 0.5
tmux -L pi-agent capture-pane -p -t repl         # parse "42" between prompts
tmux -L pi-agent send-keys -t repl C-d           # exit
```

### Run-and-get-output, self-contained helper

```bash
tmuxrun() {  # tmuxrun SESSION 'COMMAND' -> prints output, exit code in $?
  local s=$1; local t=$2
  tmux -L pi-agent new-session -d -s "$s" -x 220 -y 50 || return 1
  tmux -L pi-agent send-keys -t "$s" "$t; echo \"__DONE__:\$?\"" Enter
  until tmux -L pi-agent capture-pane -p -t "$s" | grep -q '__DONE__:[0-9]'; do sleep 1; done
  tmux -L pi-agent capture-pane -p -S -2000 -t "$s" | sed -e 's/[[:space:]]*$//'
  tmux -L pi-agent kill-session -t "$s"
}
```

## Pitfall checklist

- [ ] New session detached **and** sized (`-d -x ... -y ...`)? Unsized detached panes are 80x24.
- [ ] Sent a key **name** (`Enter`), not the string `\n`?
- [ ] Quoting survives both tmux and the target shell? If not: temp script file.
- [ ] Captured with `-S` when you need scrollback? Default is visible screen only.
- [ ] Completion detected via sentinel / `pane_dead`, not a fixed `sleep`?
- [ ] Sentinel grep matched the **expanded** form (`__DONE__:[0-9]`)? A bare grep for the
      sentinel name matches the shell-echoed command line before the command runs.
- [ ] Used IDs (`%0`, `@1`, `$2`) for targeting, not window names (they auto-rename)?
- [ ] On the default socket, did you check `tmux ls` first: the user may have live sessions
      you must not disturb (`kill-session`/`kill-server` on the default socket kills theirs)?
- [ ] `tmux ls` exit code 1 with "no server running" means empty, not broken.
- [ ] Left-over sessions cleaned up (`kill-session` / `kill-server`), socket file gone?
- [ ] Program exited and the pane vanished unexpectedly? Set `remain-on-exit on` before running.

## Control mode (advanced, rarely needed)

`tmux -C attach` (or `-CC` for raw applications) speaks a text protocol: commands
in, each answered between `%begin ... %end` (success) or `%begin ... %error`
(failure) guard lines; live pane output arrives as `%output %paneID text`
notifications. Useful for building a long-lived supervisor that streams pane
output; for one-shot driving the shell commands above are simpler. Flow control
(`refresh-client -f pause-after=...`, `%pause`, `%extended-output`) and format
subscriptions (`refresh-client -B`) exist for heavy streaming: see the
[Control-Mode wiki page](https://github.com/tmux/tmux/wiki/Control-Mode).

## Reference

- Wiki: <https://github.com/tmux/tmux/wiki> (Getting-Started, Formats, Control-Mode,
  Events, Clipboard, FAQ, Recipes)
- Man page: `man 1 tmux` (every command, flag, format variable)
