#!/usr/bin/env python3
"""Prepare privately held Indy Heat rev 1 ROM data for Z80 analysis.

Reconstructs MAME master/slave/xrom byte arrangements, performs Leland bank
rotation and writes private images. Does NOT download ROMs or decompile.
No third-party Python modules required.

Usage:
  python tools/prepare_indyheat_rom.py --rom-set /path/to/indyheat.zip \
      --out reference_private/prepared
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

# SHA-1 values and ROM layout from MAME's leland.cpp, ROM_START(indyheat).
# (filename, expected SHA1, ordered operations: (region, destination, length,
# source file offset, stride)). Reload repeats from offset 0; continue
# reads additional bytes from the same file.
ROMS = [
    ("e-302-33019-01.u64", "958a774e9ea3678c0fdd2466e578df8267b4413e", [
        ("master", 0x00000, 0x20000, 0, 1),
        ("master", 0x10000, 0x20000, 0, 1)]),
    ("e-302-33020-01.u65", "bbabc71aa8d56f6984de573f0fb5d3fea35421a9", [
        ("master", 0x30000, 0x20000, 0, 1)]),
    ("e-302-33017-01.u66", "d00bf703ce4ad0a344b3d8afcd1f45c3c82b54fe", [
        ("master", 0x50000, 0x20000, 0, 1)]),
    ("e-302-33018-01.u67", "f07d347cc844df2d824853af8dbfc557933e7765", [
        ("master", 0x70000, 0x20000, 0, 1)]),
    ("e-302-33007-01.u151", "759e46540ad9f2ed540314b174c88f7365214051", [
        ("slave", 0x00000, 0x20000, 0, 1)]),
    ("e-302-33008-01.u152", "58c3df82551199fb3f28c6459aedc2117caf520e", [
        ("slave", 0x20000, 0x20000, 0, 1),
        ("slave", 0x120000, 0x20000, 0x20000, 1)]),
    ("e-302-33009-01.u153", "e3862ed748cdd0dffdde8e1435c20c7388e698dd", [
        ("slave", 0x40000, 0x20000, 0, 1),
        ("slave", 0x140000, 0x20000, 0x20000, 1)]),
    ("e-302-33010-01.u154", "48b46fe465c6db4dc46a64245a6c69b21b54ab6f", [
        ("slave", 0x60000, 0x20000, 0, 1)]),
    ("e-302-33011-01.u155", "2584e2299bdbc50c836ae86a1c4b7e68c65a49cd", [
        ("slave", 0x80000, 0x20000, 0, 1)]),
    ("e-302-33012-01.u156", "4ba09ccba29f9feef89ce61155e2508e800cdee8", [
        ("slave", 0xa0000, 0x20000, 0, 1)]),
    ("e-302-33013-01.u157", "bdc744e3c836715874d40b9e32f509f288ce00fd", [
        ("slave", 0xc0000, 0x20000, 0, 1)]),
    ("e-302-33014-01.u158", "37fcf772ce564a9300f9dd437b9015a2d25b46b5", [
        ("slave", 0xe0000, 0x20000, 0, 1)]),
    ("e-302-33015-01.u68", "983bc22c9401b9d6c959dd211b6b7dfa1a6c14e2", [
        ("xrom", 0x00000, 0x20000, 0, 2)]),
    ("e-302-33016-01.u69", "0cb328d784cda3e0dff3a018f52f9b06bc5d46b8", [
        ("xrom", 0x00001, 0x20000, 0, 2)]),
]
REGION_SIZES = {"master": 0x90000, "slave": 0x160000, "xrom": 0x40000}

def rotate_memory(region: bytearray) -> None:
    """Match leland_m.cpp rotate_memory exactly, from offset 0x10000."""
    start = 0x10000
    assert (len(region) - start) % 0x8000 == 0
    for p in range(start, len(region), 0x8000):
        bank = bytes(region[p:p + 0x8000])
        region[p:p + 0x8000] = bank[0x2000:] + bank[:0x2000]

def load_chips(source: Path) -> dict[str, bytes]:
    chips = {}
    if source.is_file() and zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as zf:
            for name, sha, _ in ROMS:
                chips[name] = zf.read(name)  # named entries only; never unzip
    elif source.is_dir():
        for name, sha, _ in ROMS:
            chips[name] = (source / name).read_bytes()
    else:
        raise ValueError("ROM set must be a directory or ZIP file")
    for name, expected, operations in ROMS:
        data = chips[name]
        digest = hashlib.sha1(data).hexdigest()
        if digest != expected:
            raise ValueError(
                f"ROM SHA1 mismatch: {name}: expected {expected}, got {digest}"
            )
        minimum_size = max(offset + length for _, _, length, offset, _ in operations)
        if len(data) < minimum_size:
            raise ValueError(f"ROM too short: {name}: need {minimum_size:#x} bytes")
    return chips

def rebuild_regions(chips: dict[str, bytes]) -> dict[str, bytearray]:
    regions = {name: bytearray(size) for name, size in REGION_SIZES.items()}
    for filename, _, operations in ROMS:
        data = chips[filename]
        for region_name, destination, length, offset, stride in operations:
            end = destination + (length - 1) * stride + 1
            region = regions[region_name]
            if end > len(region):
                raise ValueError(f"ROM write outside {region_name}: {filename}")
            region[destination:end:stride] = data[offset:offset + length]
    rotate_memory(regions["master"])
    rotate_memory(regions["slave"])
    return regions

def export(regions: dict[str, bytearray], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    metadata = {}
    for name, data in regions.items():
        path = out / (name + "_mame_mapped.bin")
        path.write_bytes(data)
        metadata[name] = {
            "filename": path.name,
            "length": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "rotation_applied": name in ("master", "slave"),
        }
        if name in ("master", "slave"):
            bankdir = out / f"{name}_banks"
            bankdir.mkdir(exist_ok=True)
            # Fixed boot code, plus bank slices meant to be mapped at
            # CPU address 0x2000..0x9fff while inspecting with a disassembler.
            (bankdir / "fixed_0000_1fff.bin").write_bytes(data[:0x2000])
            for i, offset in enumerate(range(0x10000, len(data), 0x8000)):
                (bankdir / f"bank_{i:02d}_region_{offset:05x}.bin").write_bytes(
                    data[offset:offset + 0x8000]
                )
    (out / "derived_manifest.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rom-set", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    if not any(x == "reference_private" for x in a.out.parts):
        raise SystemExit(
            "Refusing to generate proprietary-derived binaries outside "
            "a reference_private/ directory"
        )
    regions = rebuild_regions(load_chips(a.rom_set))
    export(regions, a.out)
    print(f"Prepared mapped ROM images and disassembly banks in {a.out}")
    print("Keep these private. No decompilation/port is implied by this step.")

if __name__ == "__main__":
    main()
