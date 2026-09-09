# Cookie extraction per platform

The skill needs a valid `SESSDATA` cookie and (ideally) `bili_jct`,
`DedeUserID`, `buvid3`. Priority at load time:

1. `--cookie-file <path>` (CLI flag)
2. `$BBC_COOKIE_FILE` env var
3. `$BBC_SESSDATA` env var (direct value)
4. `~/.config/bbc-skill/cookie.json` (cached)
5. Auto-detect from installed browsers

## Recommended: browser extension export

Fastest, works identically across OSes.

### Chrome / Edge

[**Get cookies.txt LOCALLY**](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)

- Install from Chrome Web Store
- Visit <https://www.bilibili.com> (stay logged in)
- Click extension icon → **Export** → save as `www.bilibili.com_cookies.txt`
- Pass to the CLI via `--cookie-file` or `$BBC_COOKIE_FILE`

### Firefox

[cookies.txt](https://addons.mozilla.org/firefox/addon/cookies-txt/) add-on,
same workflow.

### Safari

Safari does not have a first-party cookies.txt extension. Either:

- Use Firefox / Chrome for B站 login, export from there, or
- Use the built-in auto-detect (`--browser safari`) which parses
  `~/Library/Cookies/Cookies.binarycookies`

## Auto-detection (fallback)

Set `--browser auto` (default). The skill probes, in order:

1. Firefox — `cookies.sqlite` via stdlib `sqlite3`, unencrypted
2. Chrome (macOS) — SQLite + Keychain AES-128-CBC decryption via `security`
   and `openssl` CLI (both system-built-in)
3. Edge (macOS) — same as Chrome, different Keychain service

Windows and Linux Chrome paths are stubbed for this release — use the
extension export instead.

### Chrome / Edge on macOS — how decryption works

1. Cookie DB: `~/Library/Application Support/Google/Chrome/<profile>/Cookies`
   (or `Profile 1/Cookies`, etc.)
2. Encrypted value format: `v10` or `v11` prefix + AES-128-CBC ciphertext
3. Key derivation:
   - Fetch password via `security find-generic-password -w -s "Chrome Safe Storage" -a Chrome`
   - PBKDF2-SHA1, salt=`saltysalt`, iter=1003, dklen=16
4. Decryption: `openssl enc -d -aes-128-cbc -K <hex> -iv <hex>` with IV =
   16 spaces (`b' ' * 16`)

All tools (`security`, `openssl`) are macOS system binaries, so no
`pip install` required.

### Firefox

On all OSes Firefox stores cookies in `cookies.sqlite` with values in
plaintext. The skill copies the DB to a temp file (avoids WAL locks),
queries via stdlib `sqlite3`, and returns the row.

### Safari

Safari cookies live at `~/Library/Cookies/Cookies.binarycookies`, a custom
binary plist format. Parser not implemented in this release; recommend
exporting via extension from Chrome/Firefox instead.

## Storing cookies long-term

Two safe-ish options:

**Option A — local file, permission 600**

```bash
cp ~/Downloads/bilibili_cookies.txt ~/.config/bbc-skill/cookie.txt
chmod 600 ~/.config/bbc-skill/cookie.txt
export BBC_COOKIE_FILE=~/.config/bbc-skill/cookie.txt
```

**Option B — env var (shell profile)**

```bash
# in ~/.zshrc or ~/.bashrc
export BBC_SESSDATA="your_sessdata_value"
```

Environment variables are slightly more agent-friendly because they don't
require a filesystem round-trip, but they're visible to other processes
run from the same shell.

## Rotating / revoking

`SESSDATA` is rotated by:

- Clicking "退出登录" in any Bilibili session (invalidates all sessions)
- Waiting for natural expiry (~2 weeks of inactivity)

After rotation, re-export from the browser and update your cookie file
or env var.

## What NOT to do

- **Do not share** `SESSDATA` in bug reports, screenshots, or public
  repositories — it authorizes full account access including posting,
  deleting content, changing account settings.
- **Do not commit** the cookie file to version control.
- **Do not transmit** the cookie to third parties or external services;
  this skill only calls `api.bilibili.com` directly.
