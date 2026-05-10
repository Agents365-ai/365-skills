"""Cross-platform file locking + atomic write for the state file.

`locked_rmw(path, mutator)` is the single entrypoint. It:
  1. Acquires an exclusive lock on a sibling `<path>.lock` file (fcntl on
     POSIX, msvcrt on Windows). The lock file is created on first call
     and NEVER deleted — deleting it races another opener's flock.
  2. Reads `path`, passes the parsed JSON to `mutator(state) -> state`.
  3. Writes the mutator's result to `<path>.tmp.<pid>` in the same
     directory and swaps it in via `os.replace`. `os.replace` is atomic
     on the same filesystem, so concurrent readers see either the old or
     the new state — never a torn write.
  4. Releases the lock.

If the mutator raises, the lock is released and no write occurs.

Readers (e.g. `research_state.py query`) do NOT need the lock — the
atomic-replace guarantee is enough for them, and locking every read would
serialize the hot path. Only writers and read-modify-write callers use
`locked_rmw`.

Known limitations (document in SKILL.md if a user hits this):
  - `fcntl.flock` on macOS NFS is unreliable. Keep state files in a
    local filesystem.
  - The lock file is intentionally never deleted. It is zero-sized and
    harmless; deleting it would introduce a race where Process A unlinks
    while Process B is about to open the same path, and B's flock would
    target an orphan inode.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable

_PLATFORM_POSIX = sys.platform != "win32"


class StateLockTimeout(Exception):
    """Raised when the state lock could not be acquired within the timeout."""

    def __init__(self, path: Path, timeout: float):
        super().__init__(
            f"Timed out after {timeout:.1f}s waiting for state lock on {path}. "
            f"Another process may be holding it; if none is, delete the lock "
            f"file manually after confirming no writer is running."
        )
        self.path = path
        self.timeout = timeout


def _acquire(lock_fd: int, timeout: float) -> None:
    """Acquire an exclusive lock on lock_fd, blocking up to `timeout` seconds."""
    deadline = time.monotonic() + timeout
    if _PLATFORM_POSIX:
        import fcntl

        while True:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except (BlockingIOError, OSError):
                if time.monotonic() >= deadline:
                    raise TimeoutError("flock: deadline exceeded")
                time.sleep(0.05)
    else:
        import msvcrt

        while True:
            try:
                msvcrt.locking(lock_fd, msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("msvcrt.locking: deadline exceeded")
                time.sleep(0.05)


def _release(lock_fd: int) -> None:
    if _PLATFORM_POSIX:
        import fcntl

        fcntl.flock(lock_fd, fcntl.LOCK_UN)
    else:
        import msvcrt

        try:
            msvcrt.locking(lock_fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass


def locked_rmw(
    path: Path,
    mutator: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    timeout: float = 30.0,
    loader: Callable[[Path], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Read-modify-write `path` under an exclusive lock.

    `mutator` receives the current state dict and must return the new
    state dict (may be the same object mutated in place).

    `loader` defaults to `json.loads(path.read_text())`. Callers that
    need richer validation (schema version, etc.) can pass a custom one.

    Returns the new state that was written, so the caller can avoid a
    second `load_state` roundtrip.
    """
    lock_path = Path(str(path) + ".lock")
    # touch the lock file exactly once — never delete
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        try:
            _acquire(lock_fd, timeout)
        except TimeoutError as exc:
            raise StateLockTimeout(path, timeout) from exc
        try:
            if loader is not None:
                state = loader(path)
            else:
                state = json.loads(path.read_text())
            new_state = mutator(state)
            # write to same-dir tmp then atomic replace
            tmp_path = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
            tmp_path.write_text(
                json.dumps(new_state, indent=2, ensure_ascii=False)
            )
            os.replace(tmp_path, path)
            return new_state
        finally:
            _release(lock_fd)
    finally:
        os.close(lock_fd)
