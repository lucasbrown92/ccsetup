#!/usr/bin/env python3
"""claude-retina diff — image comparison.

Primary path:  Pillow-based pixel diff → red-highlight diff image + changed regions.
Fallback path: stdlib struct.unpack PNG header for dimensions + file-size comparison.
"""

import struct
from pathlib import Path


def _read_png_dimensions(path: Path) -> tuple[int, int]:
    """Read PNG width/height from header bytes 16-24 (stdlib, no deps)."""
    with open(path, "rb") as f:
        header = f.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Not a valid PNG: {path}")
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def _require_pillow():
    try:
        from PIL import Image
        return Image
    except ImportError:
        return None


def pixel_diff(
    path_a: Path,
    path_b: Path,
    out_path: Path,
    threshold: float = 10.0,
) -> dict:
    """Compare two PNG files pixel-by-pixel.

    Returns:
      change_pct:       percentage of changed pixels
      changed_pixels:   count of changed pixels
      total_pixels:     total pixels compared
      regions:          list of {x1,y1,x2,y2} bounding boxes (up to 5, by area)
      diff_file:        path to red-highlight diff PNG (str), or None on fallback
      pillow_available: bool
    """
    Image = _require_pillow()
    if Image is None:
        return _header_only_diff(path_a, path_b)

    img_a = Image.open(path_a).convert("RGB")
    img_b = Image.open(path_b).convert("RGB")

    # Normalize dimensions
    if img_a.size != img_b.size:
        img_b = img_b.resize(img_a.size, Image.LANCZOS)

    w, h = img_a.size
    total = w * h

    pixels_a = list(img_a.getdata())
    pixels_b = list(img_b.getdata())

    changed_coords: list[tuple[int, int]] = []
    for i, (pa, pb) in enumerate(zip(pixels_a, pixels_b)):
        max_diff = max(abs(int(pa[c]) - int(pb[c])) for c in range(3))
        if max_diff > threshold:
            changed_coords.append((i % w, i // w))

    changed = len(changed_coords)
    change_pct = round(changed / total * 100, 4) if total > 0 else 0.0

    # Build diff image: gray base (35% brightness) with red changed pixels
    diff_img = img_a.copy().convert("RGBA")
    px = diff_img.load()

    # Gray out all pixels
    for y in range(h):
        for x in range(w):
            r, g, b = img_a.getpixel((x, y))
            gray = int(0.299 * r + 0.587 * g + 0.114 * b)
            g35 = int(gray * 0.35)
            px[x, y] = (g35, g35, g35, 255)

    # Paint changed pixels red (#FF3232)
    for x, y in changed_coords:
        px[x, y] = (255, 50, 50, 255)

    diff_img.save(str(out_path), "PNG")

    regions = _merge_regions(changed_coords, proximity=20, top_n=5)

    return {
        "change_pct": change_pct,
        "changed_pixels": changed,
        "total_pixels": total,
        "regions": regions,
        "diff_file": str(out_path),
        "pillow_available": True,
    }


def _merge_regions(
    coords: list[tuple[int, int]],
    proximity: int = 20,
    top_n: int = 5,
) -> list[dict]:
    """Group changed pixel coordinates into axis-aligned bounding boxes.

    Merges boxes within `proximity` pixels of each other.
    Returns top_n boxes sorted by area descending.
    """
    if not coords:
        return []

    # [x1, y1, x2, y2]
    boxes: list[list[int]] = []

    for x, y in sorted(coords):
        merged = False
        for box in boxes:
            if (
                x >= box[0] - proximity and x <= box[2] + proximity
                and y >= box[1] - proximity and y <= box[3] + proximity
            ):
                box[0] = min(box[0], x)
                box[1] = min(box[1], y)
                box[2] = max(box[2], x)
                box[3] = max(box[3], y)
                merged = True
                break
        if not merged:
            boxes.append([x, y, x, y])

    boxes.sort(key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)
    return [{"x1": b[0], "y1": b[1], "x2": b[2], "y2": b[3]} for b in boxes[:top_n]]


def _header_only_diff(path_a: Path, path_b: Path) -> dict:
    """Fallback comparison using PNG header dimensions + file size (no Pillow)."""
    try:
        wa, ha = _read_png_dimensions(path_a)
        wb, hb = _read_png_dimensions(path_b)
    except Exception as exc:
        return {
            "change_pct": -1.0,
            "changed_pixels": -1,
            "total_pixels": -1,
            "regions": [],
            "diff_file": None,
            "pillow_available": False,
            "error": str(exc),
            "note": "Install Pillow for pixel-level diff: pip install Pillow",
        }

    size_a = path_a.stat().st_size
    size_b = path_b.stat().st_size
    size_diff_pct = abs(size_a - size_b) / max(size_a, 1) * 100
    dims_match = (wa == wb and ha == hb)

    return {
        "change_pct": round(size_diff_pct, 4),
        "changed_pixels": -1,
        "total_pixels": wa * ha,
        "regions": [],
        "diff_file": None,
        "pillow_available": False,
        "note": (
            f"Header-only diff (Pillow not installed).\n"
            f"  Image A: {wa}x{ha}  ({size_a} bytes)\n"
            f"  Image B: {wb}x{hb}  ({size_b} bytes)\n"
            f"  Dimensions match: {dims_match}\n"
            f"  File-size diff:   {size_diff_pct:.2f}%\n"
            f"Install Pillow for pixel-level diff: pip install Pillow"
        ),
    }
