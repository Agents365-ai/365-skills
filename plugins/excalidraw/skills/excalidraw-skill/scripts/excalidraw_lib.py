#!/usr/bin/env python3
"""Fetch and embed Excalidraw community-library items into a .excalidraw scene.

Community libraries (https://libraries.excalidraw.com, repo excalidraw/excalidraw-libraries)
are almost all built from the same vector primitives this skill already exports
(rectangle/ellipse/line/arrow/diamond/text/freedraw), so their items render correctly
through Kroki and the local brute-export CLI. This helper discovers libraries, lists
their items, and merges an item into a scene with namespaced IDs and translated
coordinates so it drops in without collisions.

Usage:
  excalidraw_lib.py search <keyword>
      List libraries whose name/description/items match <keyword>.
  excalidraw_lib.py items  <source>
      List the items in a library (index, name, element count, image flag).
  excalidraw_lib.py merge  <scene.excalidraw> <source> <item> <x> <y> [--prefix P] [--scale S]
      Add <item> (index or name substring) to the scene at (x, y), in place.

<source> is "author/name.excalidrawlib" (fetched + cached from the official repo)
or a path to a local .excalidrawlib file.
"""
import argparse, copy, json, os, sys, urllib.request

BASE = "https://raw.githubusercontent.com/excalidraw/excalidraw-libraries/main"
CACHE = "/tmp/excalidraw-libs"


def fetch(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not os.path.exists(dest):
        urllib.request.urlretrieve(url, dest)
    return dest


def load_index():
    return json.load(open(fetch(f"{BASE}/libraries.json", f"{CACHE}/libraries.json")))


def load_lib(source):
    if os.path.exists(source):
        return json.load(open(source))
    path = fetch(f"{BASE}/libraries/{source}", f"{CACHE}/{source}")
    return json.load(open(path))


def items_of(lib):
    """Return list of (name, elements) regardless of library format version."""
    raw = lib.get("libraryItems") or lib.get("library") or []
    out = []
    for i, it in enumerate(raw):
        if isinstance(it, list):
            out.append((f"item{i}", it))
        else:
            out.append((it.get("name") or f"item{i}", it.get("elements", [])))
    return out


def bbox(els):
    xs = [e.get("x", 0) for e in els]
    ys = [e.get("y", 0) for e in els]
    xe = [e.get("x", 0) + e.get("width", 0) for e in els]
    ye = [e.get("y", 0) + e.get("height", 0) for e in els]
    return min(xs), min(ys), max(xe), max(ye)


def place(els, tx, ty, prefix, scale):
    x0, y0, _, _ = bbox(els)
    idmap = {e["id"]: f"{prefix}_{e['id']}" for e in els if "id" in e}
    out = []
    for e in els:
        e = copy.deepcopy(e)
        if "id" in e:
            e["id"] = idmap[e["id"]]
        e["x"] = (e.get("x", 0) - x0) * scale + tx
        e["y"] = (e.get("y", 0) - y0) * scale + ty
        for k in ("width", "height"):
            if k in e:
                e[k] *= scale
        if "points" in e:
            e["points"] = [[px * scale, py * scale] for px, py in e["points"]]
        if "fontSize" in e:
            e["fontSize"] *= scale
        if e.get("containerId") in idmap:
            e["containerId"] = idmap[e["containerId"]]
        for be in (e.get("boundElements") or []):
            if isinstance(be, dict) and be.get("id") in idmap:
                be["id"] = idmap[be["id"]]
        for b in ("startBinding", "endBinding"):
            if e.get(b) and e[b].get("elementId") in idmap:
                e[b]["elementId"] = idmap[e[b]["elementId"]]
        out.append(e)
    return out


def resolve_item(items, sel):
    if sel.isdigit():
        return items[int(sel)]
    for name, els in items:
        if sel.lower() in name.lower():
            return name, els
    sys.exit(f"No item matching '{sel}'. Run: excalidraw_lib.py items <source>")


def cmd_search(args):
    hits = 0
    for lib in load_index():
        names = " ".join(lib.get("itemNames", []))
        hay = f"{lib['name']} {lib.get('description','')} {names}".lower()
        if args.keyword.lower() in hay:
            hits += 1
            print(f"{lib['source']}\n    {lib['name']} — {len(lib.get('itemNames', []))} items")
    if not hits:
        print(f"No libraries match '{args.keyword}'. Browse: https://libraries.excalidraw.com")


def cmd_items(args):
    for i, (name, els) in enumerate(items_of(load_lib(args.source))):
        img = "  [HAS IMAGE — won't render via export]" if any(e.get("type") == "image" for e in els) else ""
        print(f"{i:3}  {name}  ({len(els)} els){img}")


def cmd_merge(args):
    name, els = resolve_item(items_of(load_lib(args.source)), args.item)
    if any(e.get("type") == "image" for e in els):
        sys.exit(f"Item '{name}' contains an image element — skip it (won't render via Kroki/CLI).")
    scene = json.load(open(args.scene))
    prefix = args.prefix or f"lib{len(scene['elements'])}"
    scene["elements"].extend(place(els, args.x, args.y, prefix, args.scale))
    json.dump(scene, open(args.scene, "w"))
    print(f"Merged '{name}' ({len(els)} els) at ({args.x},{args.y}) into {args.scene}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("keyword"); s.set_defaults(fn=cmd_search)
    s = sub.add_parser("items"); s.add_argument("source"); s.set_defaults(fn=cmd_items)
    s = sub.add_parser("merge")
    s.add_argument("scene"); s.add_argument("source"); s.add_argument("item")
    s.add_argument("x", type=float); s.add_argument("y", type=float)
    s.add_argument("--prefix"); s.add_argument("--scale", type=float, default=1.0)
    s.set_defaults(fn=cmd_merge)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
