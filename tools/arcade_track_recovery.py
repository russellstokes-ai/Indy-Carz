#!/usr/bin/env python3
"""Local-only Indy Heat rev1 graphics/tilemap inspector.

Implements MAME's gfx_8x8x6_planar, ataxx_scan and ataxx_get_tile_info.
No original ROM, derived atlas, QRAM dumps or tilemaps may be committed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

NAMES = [
    "e-302-33001-01.u145", "e-302-33002-01.u146",
    "e-302-33003-01.u147", "e-302-33004-01.u148",
    "e-302-33005-01.u149", "e-302-33006-01.u150",
]
SHA1 = [
    "035cc8723524e2c6aa79ffa7d7c1f6fb0a25cc51",
    "9bb521ed7202387bbf2670f9b1ae3cbe5064ae03",
    "49f5f5d6c2a82ea15905086a2f8e3ea061d37dfc",
    "a6f09b92c95321962f62a17fc0ccdbfbf78b8b88",
    "343452b883f139eb09da6b5f384aa680d3a2218c",
    "60aabedbab409acaf8ba4f2366125290825971a4",
]
PLANE_BYTES = 0x20000
TILES = 16384
COLS, ROWS = 256, 128

def read_planes(rom_zip: Path) -> list[bytes]:
    with zipfile.ZipFile(rom_zip) as zf:
        members = {Path(info.filename.replace("\\", "/")).name.lower(): info
                   for info in zf.infolist()}
        planes = []
        for name, sha in zip(NAMES, SHA1):
            if name not in members:
                raise ValueError(f"Missing 1991 arcade graphics ROM: {name}")
            payload = zf.read(members[name])
            if len(payload) != PLANE_BYTES or hashlib.sha1(payload).hexdigest() != sha:
                raise ValueError(f"{name}: wrong size/hash or arcade revision")
            planes.append(payload)
        return planes

def tile_pixels(planes: list[bytes], tile: int) -> bytes:
    """Return 64 6-bit pen values, one byte each, for a single 8x8 tile."""
    if len(planes) != 6 or any(len(p) != PLANE_BYTES for p in planes):
        raise ValueError("Expected six 0x20000 graphics planes")
    if not 0 <= tile < TILES:
        raise ValueError(f"Tile index outside 0..{TILES-1}: {tile}")
    pixels = bytearray(64)
    for y in range(8):
        row = [plane[tile * 8 + y] for plane in planes]
        for x in range(8):
            pixels[y * 8 + x] = sum(((v >> x) & 1) << (5 - bit)
                                    for bit, v in enumerate(row))
    return bytes(pixels)

def decode_qram_map(qram: bytes) -> list[list[int]]:
    """Map an MAME runtime QRAM snapshot (not in the static ROM archive).

    Matches leland_v.cpp: ataxx_scan / ataxx_get_tile_info exactly.
    Returns unmodified tile codes, including codes outside graphics range.
    """
    if len(qram) != 0x10000:
        raise ValueError("Expected a 65536-byte QRAM snapshot")
    result = []
    for y in range(ROWS):
        start = ((y & 0x3f) << 8) | ((y & 0x40) << 9)
        result.append([
            qram[start + x] | ((qram[0x4000 | (start + x)] & 0x7f) << 8)
            for x in range(COLS)
        ])
    return result

def grayscale_tile(planes: list[bytes], tile: int):
    from PIL import Image
    return Image.frombytes("L", (8, 8),
                           bytes(v * 4 for v in tile_pixels(planes, tile)))

def render_atlas(planes: list[bytes], path: Path) -> None:
    from PIL import Image
    atlas = Image.new("L", (128 * 8, 128 * 8))
    for tile in range(TILES):
        atlas.paste(grayscale_tile(planes, tile),
                    ((tile % 128) * 8, (tile // 128) * 8))
    atlas.save(path)

def render_qram(planes: list[bytes], indices: list[list[int]], path: Path) -> dict:
    from PIL import Image
    used = set(t for row in indices for t in row)
    unknown = sorted(t for t in used if not 0 <= t < TILES)
    if unknown:
        raise ValueError(f"{len(unknown)} tile codes exceed 16384 decoded tiles; "
                         "inspect graphics bank/wrapping before rendering")
    cached = {tile: grayscale_tile(planes, tile) for tile in used}
    canvas = Image.new("L", (COLS * 8, ROWS * 8))
    for y, row in enumerate(indices):
        for x, tile in enumerate(row):
            canvas.paste(cached[tile], (x * 8, y * 8))
    canvas.save(path)
    return {"unique_tile_codes": len(used), "pixels": [2048, 1024],
            "render": "background only, grayscale; no dynamic palette/foreground"}

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rom", type=Path, help="Local indyheat.zip (1991 arcade revision 1)")
    ap.add_argument("--qram", type=Path,
                    help="Optional 65536-byte runtime QRAM capture from MAME debugger")
    ap.add_argument("--atlas", action="store_true",
                    help="Export original graphics tile atlas for private analysis")
    ap.add_argument("--out", type=Path, default=Path("local/track-recovery"))
    args = ap.parse_args()
    try:
        planes = read_planes(args.rom)
        args.out.mkdir(parents=True, exist_ok=True)
        report = {"set": "indyheat",
                  "graphics": {"tile_size": [8, 8], "planes": 6, "tiles": TILES},
                  "tracks": {"status": "Not recovered; requires per-race QRAM capture"}}
        if args.atlas:
            render_atlas(planes, args.out / "inspection_atlas.png")
        if args.qram:
            track = decode_qram_map(args.qram.read_bytes())
            report["tracks"] = render_qram(
                planes, track, args.out / "race_background_preview.png")
        (args.out / "track_extraction_report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    except (OSError, ValueError, zipfile.BadZipFile, ImportError) as e:
        ap.exit(1, f"ERROR: {e}\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
