#!/usr/bin/env python3
"""Organize frames of a Bilibili video (bangumi episode, UP upload, or a local
file) into scenery shots and per-character image groups, using anime-specific
models.

ONE pass, TWO modes:
    no  --ref : unsupervised — cluster every crop by CCIP identity into char_NN
    with --ref: one-vs-rest — pull every crop matching ONE character's reference
                folder into matched/ (filenames distance-prefixed, closest first)

Agent-native contract (see agent-native-design):
    stdout : a single JSON envelope — {"ok": true, "data": {...}, "meta": {...}}
             on success, {"ok": false, "error": {...}} on failure. Auto-detected:
             JSON when stdout is not a TTY, a human summary when it is; override
             with --format json|table.
    stderr : human-readable progress logs (liveness for long runs).
    exit   : 0 ok · 1 runtime · 2 auth · 3 validation.
    --dry-run previews the plan without downloading or running models.
    --schema prints the output-envelope schema and exits.

Pipeline (each stage skipped when its output already exists):
    download  yt-dlp pulls the video-only stream (skipped for a local file)
    extract   ffmpeg scene-change keyframes + perceptual-hash dedup
    clean     (--clean) OCR-locate subtitles + watermark, LaMa-inpaint them out
    classify  anime person detection -> scenery/ vs character crops
    cluster / match   CCIP identity embeddings -> characters/ or matched/

Cookie resolution: --cookies > $BILIBILI_COOKIES > ~/bb_up/bb_cookies/www.bilibili.com_cookies.txt
Run the CCIP step on CPU (do NOT set ONNX_MODE=CoreML — CCIP crashes there).
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HOME = Path.home()
DEFAULT_COOKIES = HOME / "bb_up" / "bb_cookies" / "www.bilibili.com_cookies.txt"
SCHEMA_VERSION = "0.3.1"
# stable exit codes (agent-native-design: documented, distinct per failure class)
EXIT_OK, EXIT_RUNTIME, EXIT_AUTH, EXIT_VALIDATION = 0, 1, 2, 3


class CliError(Exception):
    """A failure with a machine-routable code + stable exit code."""
    def __init__(self, code, message, exit_code=EXIT_RUNTIME, retryable=False):
        super().__init__(message)
        self.code, self.message = code, message
        self.exit_code, self.retryable = exit_code, retryable


def log(msg):
    # human channel — never pollutes the stdout JSON envelope
    print(msg, file=sys.stderr, flush=True)


# ----------------------------------------------------------------- input
def ep_id(url):
    m = re.search(r"(ep\d+|BV[0-9A-Za-z]+)", url)
    return m.group(1) if m else re.sub(r"\W+", "_", url)[-40:]


def full_url(arg):
    if arg.startswith("http"):
        return arg
    if arg.startswith("ep"):
        return f"https://www.bilibili.com/bangumi/play/{arg}"
    if arg.startswith("BV"):
        return f"https://www.bilibili.com/video/{arg}"
    raise CliError("validation_error",
                   f"cannot resolve input to a bilibili URL / BV / ep / local file: {arg}",
                   EXIT_VALIDATION)


def resolve_input(arg):
    """A local video file stays local (download skipped); anything else is a
    bilibili URL / BVxxxx / epNNN to fetch."""
    p = Path(arg).expanduser()
    if p.is_file():
        return "file", p
    return "url", full_url(arg)


# ---------------------------------------------------------------- download
def stage_download(url, wd, cookies, height, prefer="size"):
    # only a COMPLETE file counts as already-downloaded; an interrupted
    # yt-dlp leaves video.mp4.part, which must NOT be mistaken for the video
    # (else extract runs on a truncated file) — yt-dlp resumes .part itself
    vids = [v for v in wd.glob("video.*") if v.suffix != ".part"]
    if vids:
        return vids[0]
    if not Path(cookies).exists():
        log(f"[download] warning: cookie file not found ({cookies}); "
            f"premium / 1080p+ episodes may download as preview only")
    log(f"[download] {url} (<= {height}p, video only, prefer SDR/{prefer})")
    # prefer SDR (HDR/PQ frames come out gray/washed as JPEG). among equal-res
    # SDR streams: 'size' picks the smallest (HEVC, ~half the bytes, sharp
    # enough at 4K for crops); 'bitrate' picks the largest (AVC, marginally
    # sharper). default 'size' to match the disk-saving 4K-HEVC strategy.
    sort = "+size" if prefer == "size" else "br"
    # route yt-dlp's stdout to OUR stderr so it stays in the human channel and
    # never pollutes the stdout JSON envelope (agent-native: stdout = JSON only)
    r = subprocess.run(["yt-dlp", "--cookies", cookies, "--no-playlist",
                        "-f", "bv*/b", "-S", f"res:{height},hdr:SDR,{sort}",
                        "-o", str(wd / "video.%(ext)s"), url],
                       stdout=sys.stderr, env={**os.environ, "LC_ALL": "C"})
    if r.returncode != 0:
        raise CliError("download_error",
                       f"yt-dlp failed (exit {r.returncode}); check cookies / access",
                       EXIT_RUNTIME, retryable=True)
    vids = list(wd.glob("video.*"))
    if not vids:
        raise CliError("download_error", "yt-dlp produced no video file",
                       EXIT_RUNTIME, retryable=True)
    return vids[0]


# ----------------------------------------------------------------- extract
def dhash(path, size=8):
    img = Image.open(path).convert("L").resize((size + 1, size))
    px = list(img.getdata())
    bits = 0
    for r in range(size):
        for c in range(size):
            bits = (bits << 1) | (px[r * (size + 1) + c] > px[r * (size + 1) + c + 1])
    return bits


def _extract_ffmpeg(video, frames_dir, scene_thr, interval, skip):
    """ffmpeg scene-cut selection -> ordered [(Path, timestamp)]."""
    sel = f"gt(scene,{scene_thr})"
    if interval:
        # also keep a frame every N seconds so long takes are covered
        sel += f"+isnan(prev_selected_t)+gte(t-prev_selected_t,{interval})"
    for a, b in skip:
        # exclude OP/ED time ranges
        sel = f"({sel})*not(between(t,{a},{b}))"
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(video),
         "-vf", f"select='{sel}',showinfo",
         "-fps_mode", "vfr", "-q:v", "2", str(frames_dir / "%05d.jpg")],
        capture_output=True, text=True, env={**os.environ, "LC_ALL": "C"})
    times = re.findall(r"pts_time:([0-9.]+)", proc.stderr)
    files = sorted(frames_dir.glob("*.jpg"))
    if not files:
        raise CliError("extract_error",
                       f"ffmpeg produced no frames:\n{proc.stderr[-2000:]}",
                       EXIT_RUNTIME)
    return [(f, float(times[i]) if i < len(times) else None)
            for i, f in enumerate(files)]


def _extract_pyscenedetect(video, frames_dir, threshold, skip):
    """PySceneDetect ContentDetector -> one mid-scene frame per scene, ordered
    [(Path, timestamp)]. Heavier, but its adaptive content metric is more robust
    on fades/dissolves than the raw ffmpeg `scene` score. Lazy import; needs
    `pip install scenedetect`. Threshold is on PySceneDetect's ~0-100 scale
    (default 27), NOT ffmpeg's 0-1 --scene."""
    try:
        from scenedetect import open_video, SceneManager, ContentDetector
    except ImportError:
        raise CliError("dependency_error",
                       "--engine pyscenedetect needs `pip install scenedetect`",
                       EXIT_VALIDATION)
    import cv2
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=threshold))
    sm.detect_scenes(open_video(str(video)), show_progress=False)
    scenes = sm.get_scene_list()
    if not scenes:
        raise CliError("extract_error",
                       "PySceneDetect found no scene cuts (try a lower --pyscene-threshold)",
                       EXIT_RUNTIME)
    cap = cv2.VideoCapture(str(video))
    out = []
    for i, (start, end) in enumerate(scenes):
        mid = (start.get_seconds() + end.get_seconds()) / 2
        if any(a <= mid <= b for a, b in skip):     # exclude OP/ED ranges
            continue
        cap.set(cv2.CAP_PROP_POS_MSEC, mid * 1000)
        ok, im = cap.read()
        if not ok:
            continue
        f = frames_dir / f"{i:05d}.jpg"
        cv2.imwrite(str(f), im, [cv2.IMWRITE_JPEG_QUALITY, 95])
        out.append((f, round(mid, 3)))
    cap.release()
    if not out:
        raise CliError("extract_error", "PySceneDetect produced no frames", EXIT_RUNTIME)
    return out


def stage_extract(video, wd, scene_thr, interval, dedup, skip=(),
                  engine="ffmpeg", pyscene_thr=27.0):
    meta = wd / "frames.json"
    sig = wd / ".frames.sig"
    # extraction params (engine + thresholds + skip ranges) are the cache key,
    # so changing any of them re-extracts instead of reusing stale frames
    want = json.dumps([engine, scene_thr, pyscene_thr, interval, dedup,
                       sorted([list(r) for r in skip])], sort_keys=True)
    if meta.exists() and sig.exists() and sig.read_text() == want:
        return json.load(open(meta))
    frames_dir = wd / "frames"
    shutil.rmtree(frames_dir, ignore_errors=True)
    frames_dir.mkdir()
    if engine == "pyscenedetect":
        log(f"[extract] engine=pyscenedetect threshold={pyscene_thr}")
        cand = _extract_pyscenedetect(video, frames_dir, pyscene_thr, skip)
    else:
        log(f"[extract] engine=ffmpeg scene={scene_thr} interval={interval}s")
        cand = _extract_ffmpeg(video, frames_dir, scene_thr, interval, skip)

    # shared perceptual-hash dedup (drops near-identical consecutive frames)
    frames, last = {}, None
    for f, ts in cand:
        h = dhash(f)
        if last is not None and dedup and bin(h ^ last).count("1") <= dedup:
            f.unlink()
            continue
        last = h
        frames[f.name] = ts
    json.dump(frames, open(meta, "w"), indent=1)
    sig.write_text(want)
    # frames just changed -> any cached detection/features are stale
    (wd / "detect.json").unlink(missing_ok=True)
    (wd / "features.npy").unlink(missing_ok=True)
    log(f"[extract] kept {len(frames)}/{len(cand)} keyframes")
    return frames


# ------------------------------------------------------------------- clean
def stage_clean(wd, frames, sub_band, min_conf, no_watermark):
    """Remove burned-in subtitles + the bilibili watermark from frames/ in
    place, so every downstream crop is clean. OCR locates subtitle text; the
    semi-transparent corner logo is masked by a fixed box; holes are filled by
    LaMa. Idempotent: a signature marker over the (param, frame-set) pair skips
    frames already cleaned, and re-extraction wipes frames/ so the marker is
    naturally invalidated. Heavy deps (rapidocr + torch/LaMa) load lazily and
    are only needed when --clean is passed.
    """
    import cv2
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import remove_overlay as ro
    sig = wd / ".frames.clean.sig"
    want = json.dumps([round(sub_band, 3), round(min_conf, 3), no_watermark,
                       sorted(frames)], sort_keys=True)
    if sig.exists() and sig.read_text() == want:
        return False
    frames_dir = wd / "frames"
    log(f"[clean] removing subtitles/watermark from {len(frames)} frames")
    n_sub = 0
    for i, name in enumerate(sorted(frames), 1):
        path = frames_dir / name
        im = cv2.imread(str(path))
        if im is None:
            continue
        mask, boxes = ro.build_mask(im, sub_band=sub_band, min_conf=min_conf,
                                    pad=8, wm_h=0.14, wm_w=0.18,
                                    no_watermark=no_watermark)
        n_sub += len(boxes)
        if mask.any():
            cv2.imwrite(str(path), ro.inpaint(im, mask))
        if i % 25 == 0:
            log(f"[clean] {i}/{len(frames)} frames")
    sig.write_text(want)
    log(f"[clean] done: {n_sub} subtitle box(es) across {len(frames)} frames")
    return True


# ---------------------------------------------------------------- classify
def stage_classify(wd, frames, conf, min_area):
    det_meta = wd / "detect.json"
    if det_meta.exists():
        return json.load(open(det_meta))
    from imgutils.detect import detect_person
    scenery, crops_dir = wd / "scenery", wd / "crops"
    for d in (scenery, crops_dir):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir()
    records, n = {}, 0
    for name in sorted(frames):
        path = wd / "frames" / name
        img = Image.open(path)
        W, H = img.size
        boxes = [(b, s) for b, _, s in detect_person(path)
                 if s >= conf and (b[2] - b[0]) * (b[3] - b[1]) >= min_area * W * H]
        if not boxes:
            shutil.copy2(path, scenery / name)
            records[name] = []
        else:
            entry = []
            for i, (b, s) in enumerate(boxes):
                # pad the person box slightly so CCIP sees full silhouettes
                px, py = int((b[2] - b[0]) * 0.08), int((b[3] - b[1]) * 0.08)
                box = (max(b[0] - px, 0), max(b[1] - py, 0),
                       min(b[2] + px, W), min(b[3] + py, H))
                crop = f"{path.stem}_p{i}.jpg"
                img.crop(box).save(crops_dir / crop, quality=92)
                entry.append({"crop": crop, "box": list(map(int, box)),
                              "score": round(float(s), 3)})
            records[name] = entry
        n += 1
        if n % 25 == 0:
            log(f"[classify] {n}/{len(frames)} frames")
    json.dump(records, open(det_meta, "w"), indent=1)
    n_scenery = sum(1 for v in records.values() if not v)
    log(f"[classify] scenery {n_scenery} | frames with characters "
        f"{len(records) - n_scenery} | crops {sum(map(len, records.values()))}")
    return records


# ----------------------------------------------------------- CCIP features
def load_features(wd, crops_dir, crops):
    """Cached CCIP feature matrix for crops/, rows in sorted-crop-name order.
    Re-used across cluster/match so re-running with a different threshold is
    instant. CCIP crashes under CoreML, so this path runs on CPU."""
    import numpy as np
    fp = wd / "features.npy"
    if fp.exists():
        feats = np.load(fp)
        if len(feats) == len(crops):
            return feats
    from imgutils.metrics import ccip_batch_extract_features
    log(f"[ccip] embedding {len(crops)} crops (CPU)")
    feats = np.asarray(ccip_batch_extract_features([str(crops_dir / c) for c in crops]))
    np.save(fp, feats)
    return feats


# ------------------------------------------------------------------ montage
def montage(groups, crops_dir, out_path, thumb=160, per_row=10):
    # default PIL font can't render CJK; load a system CJK TTF so labels show
    font = None
    for fp in ("/System/Library/Fonts/PingFang.ttc",
               "/System/Library/Fonts/STHeiti Medium.ttc"):
        if Path(fp).exists():
            try:
                font = ImageFont.truetype(fp, 14)
                break
            except OSError:
                pass
    rows = []
    for label, names in groups:
        ims = [Image.open(crops_dir / n) for n in names[:per_row]]
        ims = [im.resize((int(im.width * thumb / im.height), thumb)) for im in ims]
        row = Image.new("RGB", (sum(im.width for im in ims) + 4 * len(ims), thumb + 22),
                        "white")
        x = 2
        for im in ims:
            row.paste(im, (x, 22))
            x += im.width + 4
        ImageDraw.Draw(row).text((4, 4), f"{label} ({len(names)} crops)",
                                 fill="black", font=font)
        rows.append(row)
    W = max(r.width for r in rows)
    sheet = Image.new("RGB", (W, sum(r.height for r in rows)), "white")
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    sheet.save(out_path)


# ---------------------------------------------- mode 1: unsupervised cluster
def mode_cluster(wd, frames, records, eps, min_samples):
    os.environ.pop("ONNX_MODE", None)  # CCIP crashes under CoreML — force CPU
    import numpy as np
    from imgutils.metrics import ccip_batch_differences
    from sklearn.cluster import AgglomerativeClustering
    crops_dir = wd / "crops"
    crop2frame = {e["crop"]: f for f, ents in records.items() for e in ents}
    crops = sorted(crop2frame)
    char_root = wd / "characters"
    shutil.rmtree(char_root, ignore_errors=True)
    char_root.mkdir()
    if not crops:
        log("[cluster] no character crops found")
        json.dump({}, open(wd / "index.json", "w"))
        return {"mode": "cluster", "characters": [], "unsorted": 0,
                "characters_dir": str(char_root), "montage": None,
                "index": str(wd / "index.json")}
    feats = load_features(wd, crops_dir, crops)

    # average-linkage resists the chain-merging DBSCAN suffers from on this
    # compressed 3DCG embedding; 0.10 keeps distinct characters apart (over-
    # splitting one character is harmless, merging two is not).
    if len(crops) >= 2:
        diffs = ccip_batch_differences(list(feats))
        log(f"[cluster] agglo eps={eps:.3f} over {len(crops)} crops")
        labels = AgglomerativeClustering(
            n_clusters=None, distance_threshold=eps,
            metric="precomputed", linkage="average").fit_predict(diffs)
    else:
        labels = [0]

    clusters = {}
    for i, lb in enumerate(labels):
        clusters.setdefault(int(lb), []).append(i)
    big = sorted((idx for idx in clusters.values() if len(idx) >= min_samples),
                 key=len, reverse=True)
    small = [i for idx in clusters.values() if len(idx) < min_samples for i in idx]

    index, groups = {}, []
    for ci, idx in enumerate(big, 1):
        names = [crops[i] for i in idx]
        cname = f"char_{ci:02d}"
        cdir = char_root / cname
        cdir.mkdir()
        items = []
        for n in names:
            shutil.copy2(crops_dir / n, cdir / n)
            src = crop2frame[n]
            full = cdir / f"full_{src}"
            if not full.exists():
                shutil.copy2(wd / "frames" / src, full)
            items.append({"crop": n, "frame": src, "time": frames.get(src)})
        index[cname] = items
        groups.append((cname, names))
    if small:
        udir = char_root / "_unsorted"
        udir.mkdir()
        for i in small:
            shutil.copy2(crops_dir / crops[i], udir / crops[i])
        index["_unsorted"] = [{"crop": crops[i], "frame": crop2frame[crops[i]],
                               "time": frames.get(crop2frame[crops[i]])}
                              for i in small]
    montage_path = None
    if groups:
        montage_path = char_root / "_montage.png"
        montage(groups, crops_dir, montage_path)
    json.dump(index, open(wd / "index.json", "w"), indent=1)
    log(f"[cluster] {len(groups)} characters | unsorted {len(small)} "
        f"-> {char_root} (review _montage.png)")
    return {"mode": "cluster",
            "characters": [{"name": c, "crops": len(n)} for c, n in groups],
            "unsorted": len(small), "characters_dir": str(char_root),
            "montage": str(montage_path) if montage_path else None,
            "index": str(wd / "index.json")}


# -------------------------------------------- mode 2: one-vs-rest ref match
def mode_match(wd, frames, records, ref_imgs, ref_eps):
    os.environ.pop("ONNX_MODE", None)  # CCIP crashes under CoreML — force CPU
    import numpy as np
    from imgutils.metrics import (ccip_batch_extract_features,
                                  ccip_batch_differences)
    crops_dir = wd / "crops"
    crop2frame = {e["crop"]: f for f, ents in records.items() for e in ents}
    crops = sorted(crop2frame)
    out = wd / "matched"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    bands = [0.04, 0.06, 0.08, 0.10, 0.12, 0.16, 0.20]
    if not crops:
        log("[match] no character crops found")
        json.dump([], open(out / "index.json", "w"))
        return {"mode": "match", "ref_eps": ref_eps, "prototypes": len(ref_imgs),
                "crops_total": 0, "matched": 0, "bands": {f"{b:.2f}": 0 for b in bands},
                "matched_dir": str(out), "montage": None, "index": str(out / "index.json")}
    pfeats = [np.asarray(f) for f in
              ccip_batch_extract_features([str(p) for p in ref_imgs])]
    log(f"[match] {len(pfeats)} ref prototypes")
    feats = load_features(wd, crops_dir, crops)

    # per-crop MIN distance to the prototype set (no margin test — one class)
    N = len(crops)
    mind = np.full(N, 9.0, np.float32)
    CH = 4000
    for s in range(0, N, CH):
        e = min(s + CH, N)
        cross = ccip_batch_differences(list(feats[s:e]) + pfeats)[:e - s, e - s:]
        mind[s:e] = cross.min(axis=1)

    band_counts = {f"{b:.2f}": int((mind < b).sum()) for b in bands}
    log("[match] distance bands (cumulative crops): "
        + " ".join(f"<{k}:{v}" for k, v in band_counts.items()))

    order = list(np.argsort(mind))
    sel = [i for i in order if mind[i] < ref_eps]
    index = []
    for i in sel:
        n = crops[i]
        src = crop2frame[n]
        # distance prefix => a name-sorted browser shows closest matches first
        shutil.copy2(crops_dir / n, out / f"{mind[i]:.3f}_{n}")
        index.append({"dist": round(float(mind[i]), 4), "crop": n,
                      "frame": src, "time": frames.get(src)})
    json.dump(index, open(out / "index.json", "w"), ensure_ascii=False, indent=1)
    montage_path = None
    if sel:
        samp = sel[::max(1, len(sel) // 48)][:48]
        montage_path = wd / "matched_montage.png"
        montage([("matched", [crops[i] for i in samp])], crops_dir, montage_path)
    log(f"[match] {len(sel)} crops < {ref_eps} -> {out} (distance-prefixed, closest first)")
    return {"mode": "match", "ref_eps": ref_eps, "prototypes": len(pfeats),
            "crops_total": N, "matched": len(sel), "bands": band_counts,
            "matched_dir": str(out), "montage": str(montage_path) if montage_path else None,
            "index": str(out / "index.json")}


# -------------------------------------------------------------- orchestration
def _next_hints(data):
    if data["mode"] == "cluster":
        if not data["characters"]:
            return ["no groups formed — lower --scene (more frames) or --min-samples"]
        return [f"review montage: {data['montage']}"] if data["montage"] else []
    if not data["matched"]:
        return ["0 matches — raise --ref-eps (e.g. 0.06) or check the ref folder"]
    return [f"review montage: {data['montage']}"] if data["montage"] else []


def run(args):
    """Execute the pipeline; return the envelope body (without 'ok'/'meta').
    Raises CliError for any validation/runtime failure."""
    out = Path(args.out).expanduser()
    kind, val = resolve_input(args.input)            # boundary: input resolvable
    if kind == "file":
        wd = out / (re.sub(r"\W+", "_", val.stem)[:60] or "video")
    else:
        wd = out / ep_id(val)

    ref_imgs = None
    if args.ref:                                     # boundary: ref has crops
        rd = Path(args.ref).expanduser()
        ref_imgs = sorted(rd.glob("*.jpg"))
        if not ref_imgs:
            raise CliError("validation_error",
                           f"--ref {rd}: no .jpg reference crops found",
                           EXIT_VALIDATION)
    if args.ref_eps <= 0 or args.eps <= 0:           # boundary: sane thresholds
        raise CliError("validation_error", "--eps and --ref-eps must be > 0",
                       EXIT_VALIDATION)

    if args.dry_run:
        return {"dry_run": True, "would": {
            "mode": "match" if args.ref else "cluster",
            "engine": args.engine,
            "input_kind": kind, "resolved": str(val), "work_dir": str(wd),
            "download": kind != "file",
            "cookies": str(args.cookies) if kind != "file" else None,
            "ref": str(args.ref) if args.ref else None,
            "ref_eps": args.ref_eps if args.ref else None,
            "eps": None if args.ref else args.eps,
            "min_samples": None if args.ref else args.min_samples,
            "clean": args.clean,
            "output": str(wd / ("matched" if args.ref else "characters")),
        }}

    wd.mkdir(parents=True, exist_ok=True)
    if kind == "file":
        log(f"[input] local file {val} -> {wd}")
        video = val
    else:
        video = stage_download(val, wd, args.cookies, args.height, args.prefer)

    if args.redo == "extract":
        (wd / "frames.json").unlink(missing_ok=True)
        (wd / ".frames.sig").unlink(missing_ok=True)
        (wd / ".frames.clean.sig").unlink(missing_ok=True)
    if args.redo in ("extract", "classify"):
        (wd / "detect.json").unlink(missing_ok=True)
        (wd / "features.npy").unlink(missing_ok=True)

    skip = [tuple(map(float, r.split("-", 1))) for r in args.skip.split(",") if r]
    frames = stage_extract(video, wd, args.scene, args.interval, args.dedup, skip,
                           engine=args.engine, pyscene_thr=args.pyscene_threshold)
    if args.clean:
        if stage_clean(wd, frames, args.clean_band, args.clean_conf,
                       args.clean_no_watermark):
            (wd / "detect.json").unlink(missing_ok=True)
            (wd / "features.npy").unlink(missing_ok=True)
    records = stage_classify(wd, frames, args.conf, args.min_area)

    if args.ref:
        mode_data = mode_match(wd, frames, records, ref_imgs, args.ref_eps)
    else:
        mode_data = mode_cluster(wd, frames, records, args.eps, args.min_samples)

    data = {"id": wd.name, "input": str(val), "work_dir": str(wd),
            "engine": args.engine, "frames": len(frames),
            "scenery": sum(1 for v in records.values() if not v),
            "crops": sum(len(v) for v in records.values()),
            **mode_data}
    return {"data": data, "next": _next_hints(data)}


SCHEMA = {
    "envelope": {
        "ok": "true | false | 'partial'",
        "data": "object (on success) — pipeline result, see modes below",
        "error": "{code, message, retryable} (on failure)",
        "meta": "{schema_version, tool, elapsed_ms}",
        "next": "[string] optional follow-up hints",
    },
    "data.common": {"id": "str", "input": "str", "work_dir": "str",
                    "frames": "int", "scenery": "int", "crops": "int", "mode": "cluster|match"},
    "data.cluster": {"characters": "[{name, crops}]", "unsorted": "int",
                     "characters_dir": "str", "montage": "str|null", "index": "str"},
    "data.match": {"ref_eps": "float", "prototypes": "int", "crops_total": "int",
                   "matched": "int", "bands": "{<dist>: cumulative_count}",
                   "matched_dir": "str", "montage": "str|null", "index": "str"},
    "exit_codes": {"0": "ok", "1": "runtime", "2": "auth", "3": "validation"},
}


def _render_human(env):
    """Compact human summary for a TTY reader (stderr already had progress)."""
    if not env.get("ok", True) is True and "error" in env:
        e = env["error"]
        return f"✗ {e['code']}: {e['message']}"
    if env.get("dry_run"):
        w = env["would"]
        return ("dry-run plan:\n" +
                "\n".join(f"  {k}: {v}" for k, v in w.items()))
    d = env["data"]
    head = (f"✓ {d['mode']} | id={d['id']} | frames={d['frames']} "
            f"scenery={d['scenery']} crops={d['crops']}")
    if d["mode"] == "cluster":
        chars = ", ".join(f"{c['name']}({c['crops']})" for c in d["characters"]) or "—"
        body = f"  characters: {chars} | unsorted={d['unsorted']}\n  -> {d['characters_dir']}"
    else:
        bands = " ".join(f"<{k}:{v}" for k, v in d["bands"].items())
        body = (f"  matched={d['matched']}/{d['crops_total']} (< {d['ref_eps']})\n"
                f"  bands: {bands}\n  -> {d['matched_dir']}")
    hints = "".join(f"\n  · {h}" for h in env.get("next", []))
    return f"{head}\n{body}{hints}"


def emit(env, fmt):
    if fmt == "json":
        print(json.dumps(env, ensure_ascii=False, indent=2))
    else:
        print(_render_human(env))


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?",
                    help="bilibili URL / BVxxxx / epNNN, or a local video file")
    ap.add_argument("--ref", help="folder of reference *.jpg crops of ONE character; "
                    "switches to one-vs-rest mode (pull matches into matched/)")
    ap.add_argument("--ref-eps", type=float, default=0.04,
                    help="mode-2 max distance to a reference prototype "
                         "(tight = pure; 0.04 pristine, ~0.06 recall ceiling)")
    ap.add_argument("--out", default="./bangumi_frames")
    ap.add_argument("--cookies", default=os.environ.get("BILIBILI_COOKIES",
                                                        str(DEFAULT_COOKIES)),
                    help="Netscape cookies.txt (trusted via env/file, not agent args)")
    ap.add_argument("--height", type=int, default=2160)
    ap.add_argument("--prefer", choices=["size", "bitrate"], default="size",
                    help="among equal-res SDR streams: 'size'=smallest (HEVC) / "
                         "'bitrate'=sharpest (AVC)")
    ap.add_argument("--engine", choices=["ffmpeg", "pyscenedetect"], default="ffmpeg",
                    help="keyframe selector: 'ffmpeg' scene metric (default) or "
                         "'pyscenedetect' ContentDetector (more robust on fades; "
                         "needs `pip install scenedetect`)")
    ap.add_argument("--scene", type=float, default=0.3,
                    help="ffmpeg-engine scene-cut threshold 0-1 (smaller = more frames)")
    ap.add_argument("--pyscene-threshold", type=float, default=27.0,
                    help="pyscenedetect-engine ContentDetector threshold ~0-100 "
                         "(smaller = more cuts)")
    ap.add_argument("--interval", type=float, default=0,
                    help="also keep a frame every N seconds (0 = scene cuts only)")
    ap.add_argument("--dedup", type=int, default=6,
                    help="hamming distance below which consecutive frames are dropped")
    ap.add_argument("--skip", default="",
                    help="time ranges (seconds) to exclude, e.g. 80-170,1300-1390 (OP/ED)")
    ap.add_argument("--clean", action="store_true",
                    help="remove burned-in subtitles + watermark before classifying "
                         "(needs rapidocr-onnxruntime + simple-lama-inpainting)")
    ap.add_argument("--clean-band", type=float, default=0.22)
    ap.add_argument("--clean-conf", type=float, default=0.6)
    ap.add_argument("--clean-no-watermark", action="store_true")
    ap.add_argument("--conf", type=float, default=0.45, help="min person-detection score")
    ap.add_argument("--min-area", type=float, default=0.015,
                    help="min person-box area as fraction of frame")
    ap.add_argument("--eps", type=float, default=0.10,
                    help="mode-1 cluster distance threshold (larger = merge more)")
    ap.add_argument("--min-samples", type=int, default=5,
                    help="mode-1 min crops to form a character")
    ap.add_argument("--redo", choices=["extract", "classify"],
                    help="invalidate this stage and the ones after it")
    ap.add_argument("--format", choices=["json", "table"],
                    help="output format (default: json when piped, table on a TTY)")
    ap.add_argument("--dry-run", action="store_true",
                    help="preview the plan (resolved input, work dir, output) without running")
    ap.add_argument("--schema", action="store_true",
                    help="print the output-envelope schema and exit")
    args = ap.parse_args()

    fmt = args.format or ("table" if sys.stdout.isatty() else "json")
    meta = {"schema_version": SCHEMA_VERSION, "tool": "bangumi-frames"}

    if args.schema:
        emit({"ok": True, "data": SCHEMA, "meta": meta}, fmt)
        return EXIT_OK
    if not args.input:
        emit({"ok": False, "error": {"code": "validation_error",
              "message": "missing input (URL / BV / ep / local file)", "retryable": False}}, fmt)
        return EXIT_VALIDATION

    t0 = time.time()
    try:
        body = run(args)
        meta["elapsed_ms"] = int((time.time() - t0) * 1000)
        emit({"ok": True, **body, "meta": meta}, fmt)
        return EXIT_OK
    except CliError as e:
        emit({"ok": False, "error": {"code": e.code, "message": e.message,
              "retryable": e.retryable}, "meta": meta}, fmt)
        return e.exit_code
    except KeyboardInterrupt:
        emit({"ok": False, "error": {"code": "interrupted",
              "message": "interrupted", "retryable": True}, "meta": meta}, fmt)
        return EXIT_RUNTIME
    except Exception as e:                            # last-resort structured failure
        emit({"ok": False, "error": {"code": "runtime_error",
              "message": f"{type(e).__name__}: {e}", "retryable": False}, "meta": meta}, fmt)
        return EXIT_RUNTIME


if __name__ == "__main__":
    sys.exit(main())
