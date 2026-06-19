# The two modes

After classify produces `crops/` + cached `features.npy`, the run takes one of two exits,
chosen by whether `--ref` is given.

## Mode 1 — unsupervised cluster (no `--ref`)

Embeds every crop with CCIP and groups them with average-linkage agglomerative clustering
on the pairwise distance matrix.

- Output: per group (largest first) two sibling folders — `characters/char_NN_crop/` (the
  cropped person images) and `characters/char_NN_full/` (their source full frames, deduped
  by frame; paired by frame number, e.g. crop `00029_p0.jpg` ↔ full `00029.jpg`). Plus
  `_unsorted/` (crops only) for groups smaller than `--min-samples`, `_montage.png` (first 10
  of each group — look here first to identify who is who), and `index.json`
  (`char_NN` → `[{crop, frame, time}]`).
- Flags: `--eps 0.10` (distance threshold; larger merges more) and `--min-samples 5`.
- **Why average-linkage at eps 0.10:** on this compressed 3D-render embedding, DBSCAN
  chain-merges distinct look-alikes and OPTICS under-recalls; average-linkage at 0.10 keeps
  distinct characters apart. Over-splitting one character into several `char_NN` is harmless
  (rename/merge later); merging two different characters into one group is not — so prefer
  the tighter eps.

**Tuning when grouping looks wrong (check `_montage.png` first):**

- Biggest group mixes several characters → lower `--eps`.
- One character split across many groups → raise `--eps` (but on this art style, prefer to
  leave it split rather than risk merging distinct people).
- Too few crops to form groups (everything in `_unsorted`) → lower `--scene` (e.g. `0.25`)
  to extract more frames, or lower `--min-samples`.
- Background extras leaking in → raise `--min-area`.

## Mode 2 — one-vs-rest (`--ref DIR`)

Builds CCIP prototypes from ONE character's reference folder (`DIR/*.jpg`, ideally ~200
hand-picked crops covering the character's forms/angles), computes each crop's **minimum**
distance to that prototype set, and keeps crops under `--ref-eps`. There is no margin /
competition test (only one class), which sidesteps the cross-character false-positives that
plague multi-class assignment on this embedding.

- Output: `matched/` with each kept crop copied as `0.012_<crop>.jpg` — the **distance is a
  filename prefix**, so a name-sorted browser shows the closest matches first and any
  stragglers sit at the tail for one-glance review/delete. Plus `index.json`
  (`[{dist, crop, frame, time}]`) and `matched_montage.png`.
- It also prints a **cumulative distance-band histogram** (`dist<0.04`, `<0.06`, … `<0.20`)
  so you can pick the cutoff by eye before committing.
- Flag: `--ref-eps 0.04` (max distance to a prototype).

**Threshold lore (compressed 3D-render embedding):** ~82% of all crops sit within distance
0.20 of any reference, so a loose `--ref-eps` grabs half the video. Purity lives only in the
tight bands. Verified for a 220-crop reference:

- `dist < 0.04` = pristine (zero contamination).
- `0.04–0.06` = mostly clean, slight contamination begins.
- `0.06–0.08` = other characters start to dominate.
- `≥ 0.08` = unusable.

So **`--ref-eps 0.04` for purity**, up to ~`0.06` if you need more recall. Always sanity-check
`matched_montage.png` and the high-distance tail of `matched/`. Build the reference densely
(~200 crops across all of the character's forms) — far better than a handful of seed images;
for multi-form characters, include every form in the reference folder.

### Several characters in one pass

`--ref` auto-detects its layout:

- **a folder of `*.jpg`** → ONE character → `matched/` (the single-character case above).
- **a folder of per-character SUBFOLDERS** → each subfolder is one character, matched
  independently and written to `matched/<subfolder-name>/` (each with its own
  `0.0xx_<crop>.jpg` files, `_montage.png`, and `index.json`):

  ```
  ~/refs/凡人/          # pass this as --ref
  ├── 韩立/    *.jpg     # -> matched/韩立/
  ├── 紫灵/    *.jpg     # -> matched/紫灵/
  └── 南宫婉/  *.jpg     # -> matched/南宫婉/
  ```

  Empty subfolders (no `*.jpg`) are skipped. Each character still runs as its own one-vs-rest
  (same `--ref-eps`, no cross-character competition), so the purity rules above hold per
  character — they share the crop features, so adding characters only costs one extra distance
  pass each, not a re-extract. The envelope `data` carries a `characters[]` array (one entry
  per name) instead of the flat single-character fields; `data.matched` is the total across all.
