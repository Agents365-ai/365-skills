#!/usr/bin/env python3
"""Remove bilibili hard subtitles (bottom) and the corner watermark from anime
frames, then inpaint the holes with LaMa. Standalone test tool.

Subtitles are located with RapidOCR (robust to low-contrast white-on-light text
that pixel heuristics miss) and restricted to a bottom band so dialogue painted
into the scene is left alone. The semi-transparent bilibili logo is invisible to
OCR, so its fixed top-right corner box is masked directly. Holes are filled by
LaMa, which reconstructs structure (clothing lines, colour edges) instead of the
smeared band cv2.inpaint leaves behind. Frames with nothing to remove skip the
model entirely.

    python3 remove_overlay.py IMG [IMG ...] --out-dir /tmp/clean [--debug]
    python3 remove_overlay.py FRAMES_DIR --out-dir DIR        # whole folder

LaMa runs on Apple MPS / CUDA when available (~2s/frame), else CPU (~50s).
"""
import argparse
import os
from pathlib import Path

# some LaMa ops have no MPS kernel; let them fall back to CPU silently
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
import warnings
warnings.filterwarnings("ignore", message="An output with one or more elements")

import cv2
import numpy as np

_OCR = None
_LAMA = None


def _ocr():
    global _OCR
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR = RapidOCR()
    return _OCR


def _lama():
    global _LAMA
    if _LAMA is None:
        import torch
        from simple_lama_inpainting import SimpleLama
        dev = ("mps" if torch.backends.mps.is_available()
               else "cuda" if torch.cuda.is_available() else "cpu")
        _LAMA = SimpleLama(device=torch.device(dev))
        print(f"[lama] device={dev}")
    return _LAMA


def _poly_bounds(box):
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    return min(xs), min(ys), max(xs), max(ys)


def build_mask(im, sub_band, min_conf, pad, wm_h, wm_w, no_watermark):
    h, w = im.shape[:2]
    s = max(h, w) / 2000.0
    pad = max(3, int(pad * s))
    mask = np.zeros((h, w), np.uint8)

    # --- subtitles via OCR, kept only inside the bottom band ---
    y_min = int(h * (1 - sub_band))
    res, _ = _ocr()(im)
    boxes = []
    for box, _txt, conf in (res or []):
        if conf < min_conf:
            continue
        x0, y0, x1, y1 = _poly_bounds(box)
        if (y0 + y1) / 2 < y_min:            # not in the subtitle band
            continue
        if (x1 - x0) > 0.95 * w:             # full-width bar = not a subtitle
            continue
        boxes.append((x0, y0, x1, y1))
        cv2.rectangle(mask, (int(x0) - pad, int(y0) - pad),
                      (int(x1) + pad, int(y1) + pad), 255, -1)

    # --- watermark: fixed top-right corner box (OCR can't see it) ---
    if not no_watermark:
        ch, cw = int(h * wm_h), int(w * wm_w)
        mask[:ch, w - cw:] = 255
    return mask, boxes


def inpaint(im, mask):
    from PIL import Image
    rgb = Image.fromarray(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
    out = _lama()(rgb, Image.fromarray(mask))
    out = cv2.cvtColor(np.array(out), cv2.COLOR_RGB2BGR)
    # LaMa pads to a multiple of 8, so the result can be a few px larger
    return out[:im.shape[0], :im.shape[1]]


def clean(path, out_dir, debug=False, **kw):
    im = cv2.imread(str(path))
    if im is None:
        print(f"  skip (unreadable): {path}")
        return
    mask, boxes = build_mask(im, **kw)
    if mask.any():
        res = inpaint(im, mask)
    else:
        res = im                              # nothing to remove
    out = out_dir / path.name
    cv2.imwrite(str(out), res)
    print(f"  {path.name}: {len(boxes)} subtitle box(es), "
          f"masked {int(mask.sum() / 255)} px -> {out}")
    if debug:
        dbg = im.copy()
        dbg[mask > 0] = (0, 0, 255)
        cv2.imwrite(str(out_dir / f"dbg_{path.name}"), dbg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+", type=Path,
                    help="image files, or a directory of *.jpg")
    ap.add_argument("--out-dir", type=Path, default=Path("/tmp/overlay_clean"))
    ap.add_argument("--sub-band", type=float, default=0.22,
                    help="bottom fraction where subtitles are accepted")
    ap.add_argument("--min-conf", type=float, default=0.6,
                    help="min OCR confidence for a subtitle box")
    ap.add_argument("--pad", type=int, default=8,
                    help="px padding around each OCR box (scaled to image)")
    ap.add_argument("--wm-h", type=float, default=0.14,
                    help="top fraction of the watermark corner box")
    ap.add_argument("--wm-w", type=float, default=0.18,
                    help="right fraction of the watermark corner box")
    ap.add_argument("--no-watermark", action="store_true",
                    help="skip the corner box (subtitles only)")
    ap.add_argument("--debug", action="store_true",
                    help="also write dbg_* overlays of the mask")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for p in args.images:
        paths.extend(sorted(p.glob("*.jpg")) if p.is_dir() else [p])
    kw = dict(sub_band=args.sub_band, min_conf=args.min_conf, pad=args.pad,
              wm_h=args.wm_h, wm_w=args.wm_w, no_watermark=args.no_watermark)
    for p in paths:
        clean(p, args.out_dir, debug=args.debug, **kw)


if __name__ == "__main__":
    main()
