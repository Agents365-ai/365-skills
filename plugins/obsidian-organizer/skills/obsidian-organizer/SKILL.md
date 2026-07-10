---
name: obsidian-organizer
description: >-
  File new notes into the right folder and audit/reorganize folder structure in
  the user's Obsidian vault, using the `obsidian` CLI and a single source-of-truth
  map note (`00_Index/Folder_Map.md`) that lives inside the vault. Use this
  whenever a note needs to be placed, filed, sorted, or moved into the vault;
  whenever the user asks where a note "belongs" or "should go"; and whenever they
  want to clean up, reorganize, deduplicate, audit, or restructure vault folders
  (e.g. orphaned notes, dead-end notes, near-duplicate titles, overlapping
  folders). Trigger even when the user just says "add this to my vault", "put
  this somewhere sensible", or "tidy up the cellchat notes" without naming a
  folder. Requires the Obsidian desktop app to be running.
---

# Obsidian Organizer

Keep a large Obsidian vault tidy over time by (1) filing new notes into the
best-fit folder and (2) auditing/reorganizing existing structure. Both modes lean
on one shared idea: a plain-markdown map of "what goes where" that lives **inside
the vault** so it never drifts out of sync with reality.

This skill drives the `obsidian` CLI (from the separate `obsidian-cli` skill),
which talks to the **live, running Obsidian desktop app**. The app must be open.
If a command fails with a connection/vault error, tell the user to open Obsidian
rather than guessing.

## Why the map lives in the vault (read this first)

Deciding a folder for every new note by re-listing ~650 folders is expensive and
guesses drift. Copying the folder taxonomy into Claude's private memory creates a
worse problem: a stale copy that silently disagrees with the real vault.

The fix is one file, `00_Index/Folder_Map.md`, checked into the vault itself. It
is the single source of truth for filing decisions. Read it with one cheap call
before you file or reorganize — do **not** re-run a full `obsidian folders`
traversal unless the map is missing or the user asks you to rebuild it.

```bash
obsidian read path="00_Index/Folder_Map.md"
```

It is deliberately plain markdown (headers + bullets, no required frontmatter) so
both you and the human can append to it by hand as new categories emerge. When you
create a new folder/category, add a line to this file so the next filing decision
remembers it.

If the map does not exist (deleted, or a fresh vault), rebuild it **from the live
vault**, not from a copy stashed in this skill — a bundled copy would drift from
reality, which is the whole failure this file exists to prevent. List the real
structure with `obsidian vault="MyVault" folders` (and `folders folder=...`
for depth), draft a plain-markdown map grouped by top-level PARA folder with a
short "what goes here" note per folder plus a filing rule-of-thumb, confirm the
groupings with the user, then create it:
`obsidian vault="MyVault" create path="00_Index/Folder_Map.md" content="..."`.

## Vault targeting

`MyVault` above is a placeholder — substitute the user's actual vault name
everywhere. If the user has more than one vault, target the intended one
explicitly on every command so a stray "most recently focused vault" default
cannot misfile a note:

```bash
obsidian vault="MyVault" read path="00_Index/Folder_Map.md"
```

`vault=` must be the **first** parameter. This is the only vault-specific value
in the skill — everything else comes from the vault's own `Folder_Map.md`.

## The one hard safety rule: never touch vault files with raw shell

When you relocate or rename a file, **always** use the CLI's own `move` / `rename`
commands. These go through Obsidian's API, so Obsidian's built-in "automatically
update internal links" behavior rewrites every wikilink and backlink across the
vault to follow the moved file. A raw `mv`, `rm`, `rmdir`, or `find -delete` on a
path inside the vault skips that repair and silently leaves broken links pointing
at the old location.

So, for anything under the vault directory:

- Move/rename → `obsidian move ...` or `obsidian rename ...`
- Delete → `obsidian delete ...` (sends to trash unless `permanent`)
- **Never** use Bash `mv` / `rm` / `rmdir` / `find -delete` on vault-internal paths.

Reading a file's bytes with a non-mutating tool is fine; mutating vault files is
CLI-only.

---

## Mode 1 — File a note

Goal: given a note (an existing path, or a title + content you're about to
write), put it in the single best-fit folder.

1. **Read the map** once: `obsidian vault="MyVault" read path="00_Index/Folder_Map.md"`.
2. **Match** the note's topic to a destination using the map's filing rules. Favor
   an existing specific subfolder over a general one (e.g. a Seurat how-to goes to
   `03_Research_Knowledge/Bioinformatics/seurat/`, not a generic bucket).
3. **Act on the best fit:**
   - *A clearly matching folder exists* → file it there.
     - New note: `obsidian vault="MyVault" create path="03_Research_Knowledge/Bioinformatics/seurat/My Note.md" content="..." silent`
     - Existing note to relocate: `obsidian vault="MyVault" move path="00_Inbox/My Note.md" to="03_Research_Knowledge/Bioinformatics/seurat"` (`to` may be a folder or a full path).
   - *A rough-but-imperfect fit exists* (e.g. a tool with no dedicated subfolder) →
     use the map's catch-all convention (e.g. `Bioinformatics/misc/`) and tell the
     user where it went.
   - *No category fits well* → **stop and ask** the user before inventing a folder.
     Propose a name and location; don't silently create new taxonomy.
4. **Remember new categories.** When the user approves a new folder, append a line
   describing it under the right section of `00_Index/Folder_Map.md`
   (`obsidian append path="00_Index/Folder_Map.md" content="..."`) so future
   filing decisions know about it.
5. Briefly report the final path.

Notes on the CLI: `create` makes intermediate folders as needed; add `silent` so
it doesn't steal focus by opening the note. `move`'s `to` accepts a destination
folder or a full path; use `rename name="New Title"` to change a title in place.

---

## Mode 2 — Audit / reorganize

Goal: given a scope (a folder path, "recent inbox notes", or an explicit request
like "clean up the cellchat notes"), find problems, **propose a plan, get explicit
confirmation, then execute.** Never move, merge, or delete in bulk silently.

### Step 1 — Gather signals for the scope

Read the map first for context, then use the structural commands. Scope every list
to the folder in question where the command supports it.

- `obsidian vault="MyVault" files folder="<scope>"` — inventory + spot
  near-duplicate titles (e.g. "CellChat analysis" vs "CellChat Analysis v2").
- `obsidian vault="MyVault" orphans` — notes with no incoming links (nothing
  links to them; candidates for filing/merging/archiving).
- `obsidian vault="MyVault" deadends` — notes with no outgoing links
  (often stubs or captures that were never developed).
- `obsidian vault="MyVault" search:context query="<topic>" path="<scope>"` —
  compare content of suspected near-duplicates before proposing a merge.
- `obsidian vault="MyVault" backlinks path="<file>"` — before merging or
  deleting a note, see what links to it so you don't strand references.

There is no dedicated "duplicates" command; detect duplicates by comparing the
titles from `files` and confirming with `search:context` / `read`.

### Step 2 — Propose a plan (and wait)

Present a concrete, itemized plan and stop for confirmation. Group by action:

```
Proposed reorganization for Bioinformatics/cellchat/ (7 notes):

MERGE
- "CellChat analysis.md" + "CellChat analysis (1).md" → keep "CellChat analysis.md",
  fold unique content from the duplicate in, then delete the duplicate.

MOVE
- "Spatial CellChat.md" → Single_Cell/Spatial_Omics/ (topic is spatial, not the tool)

RENAME
- "untitled cellchat.md" → "CellChat LR database notes.md"

No change: 3 notes look fine.

Proceed? I won't move/merge/delete anything until you confirm.
```

Keep the plan honest about uncertainty — flag guesses so the user can veto them.

### Step 3 — Execute only after "yes"

On confirmation, run the moves/renames/deletes **through the CLI** in the order
that keeps links intact (usually: merge content first, then delete the emptied
duplicate; move before rename if both apply). Use `move`, `rename`, `delete`,
`append`/`read` for merges — never raw shell. Report what changed, and append any
new folders/categories you created to `00_Index/Folder_Map.md`.

### Known standing reorg candidates

If the vault's `Folder_Map.md` calls out known problem areas (legacy folders
that overlap a newer one, a subfolder with accumulated near-duplicate titles,
etc.), surface them when they're in scope — but still propose-and-confirm
before touching anything.

---

## Command quick reference

| Need | Command |
| --- | --- |
| Read the map | `obsidian vault="MyVault" read path="00_Index/Folder_Map.md"` |
| Create/file a new note | `obsidian vault="MyVault" create path="Folder/Note.md" content="..." silent` |
| Move/relocate a note | `obsidian vault="MyVault" move path="Old/Note.md" to="New/Folder"` |
| Rename in place | `obsidian vault="MyVault" rename path="Folder/Note.md" name="New Title"` |
| Delete (to trash) | `obsidian vault="MyVault" delete path="Folder/Note.md"` |
| List files in a folder | `obsidian vault="MyVault" files folder="<scope>"` |
| Orphans / dead-ends | `obsidian vault="MyVault" orphans` · `... deadends` |
| Search with context | `obsidian vault="MyVault" search:context query="..." path="<scope>"` |
| Backlinks to a note | `obsidian vault="MyVault" backlinks path="Folder/Note.md"` |
| Append to the map | `obsidian vault="MyVault" append path="00_Index/Folder_Map.md" content="- ..."` |

Run `obsidian help <command>` to confirm exact params — the CLI is the ground truth.
