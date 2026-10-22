#!/usr/bin/env python3
"""Reconstruct Indy Heat rev 1 Z80 program regions for local reverse engineering.

No ROMs, disassembled proprietary code, or original assets are included.
Mapping follows the MAME Ataxx-era driver ROM_LOAD/ROM_CONTINUE/ROM_RELOAD
and rotate_memory routines. This is a local analysis utility, NOT a game port.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zlib
import zipfile
from pathlib import Path

# Original 1991 arcade set "indyheat", revision 1.
# Value: expected file size, CRC32 (hex), SHA1 (hex).
ROMS = {
    # master Z80
    "e-302-33019-01.u64": (0x20000, "2b97a347", "958a774e9ea3678c0fdd2466e578df8267b4413e"),
    "e-302-33020-01.u65": (0x20000, "71301d74", "bbabc71aa8d56f6984de573f0fb5d3fea35421a9"),
    "e-302-33017-01.u66": (0x20000, "c9612072", "d00bf703ce4ad0a344b3d8afcd1f45c3c82b54fe"),
    "e-302-33018-01.u67": (0x20000, "4c4b25e0", "f07d347cc844df2d824853af8dbfc557933e7765"),
    # slave Z80 (u152 and u153 have 0x40000 bytes each, ROM_CONTINUE)
    "e-302-33007-01.u151": (0x20000, "2622dfa4", "759e46540ad9f2ed540314b174c88f7365214051"),
    "e-302-33008-01.u152": (0x40000, "ad40e4e2", "58c3df82551199fb3f28c6459aedc2117caf520e"),
    "e-302-33009-01.u153": (0x40000, "1e3803f7", "e3862ed748cdd0dffdde8e1435c20c7388e698dd"),
    "e-302-33010-01.u154": (0x20000, "76d3c235", "48b46fe465c6db4dc46a64245a6c69b21b54ab6f"),
    "e-302-33011-01.u155": (0x20000, "d5d866b3", "2584e2299bdbc50c836ae86a1c4b7e68c65a49cd"),
    "e-302-33012-01.u156": (0x20000, "7fe71842", "4ba09ccba29f9feef89ce61155e2508e800cdee8"),
    "e-302-33013-01.u157": (0x20000, "a6462adc", "bdc744e3c836715874d40b9e32f509f288ce00fd"),
    "e-302-33014-01.u158": (0x20000, "d6ef27a3", "37fcf772ce564a9300f9dd437b9015a2d25b46b5"),
    # X-ROM: data addressed by master Z80 (often vital for tables).
    "e-302-33015-01.u68": (0x20000, "9e88efb3", "983bc22c9401b9d6c959dd211b6b7dfa1a6c14e2"),
    "e-302-33016-01.u69": (0x20000, "aa39fcb3", "0cb328d784cda3e0dff3a018f52f9b06bc5d46b8"),
}

MASTER_NAMES = (
    "e-302-33019-01.u64", "e-302-33020-01.u65",
    "e-302-33017-01.u66", "e-302-33018-01.u67",
)
SLAVE_NAMES = (
    "e-302-33007-01.u151", "e-302-33008-01.u152",
    "e-302-33009-01.u153", "e-302-33010-01.u154",
    "e-302-33011-01.u155", "e-302-33012-01.u156",
    "e-302-33013-01.u157", "e-302-33014-01.u158",
)
XROM_NAMES = ("e-302-33015-01.u68", "e-302-33016-01.u69")

def read_and_verify_roms(archive: Path) -> dict[str, bytes]:
    if not archive.is_file():
        raise ValueError(f"ROM archive not found: {archive}")
    with zipfile.ZipFile(archive) as zf:
        files = {}
        for member in zf.infolist():
            basename = Path(member.filename.replace("\\", "/")).name.lower()
            if basename in ROMS:
                if basename in files:
                    raise ValueError(f"Duplicate required ROM in archive: {basename}")
                files[basename] = member
        missing = sorted(set(ROMS).difference(files))
        if missing:
            raise ValueError("Missing rev-1 program ROMs: " + ", ".join(missing))
        result = {}
        for name, (size, crc, sha1) in ROMS.items():
            info = files[name]
            if info.file_size != size:
                raise ValueError(f"{name}: length {info.file_size}, expected {size}")
            data = zf.read(info)
            if f"{zlib.crc32(data) & 0xffffffff:08x}" != crc:
                raise ValueError(f"{name}: CRC32 mismatch (wrong revision/corrupt file)")
            if hashlib.sha1(data).hexdigest() != sha1:
                raise ValueError(f"{name}: SHA1 mismatch")
            result[name] = data
    return result

def copy_to_region(region: bytearray, offset: int, blob: bytes) -> None:
    if offset < 0 or offset + len(blob) > len(region):
        raise ValueError(f"Region overflow at 0x{offset:x} with 0x{len(blob):x} bytes")
    region[offset:offset + len(blob)] = blob

def reconstruct_regions(roms: dict[str, bytes]) -> dict[str, bytearray]:
    """Apply MAME rev-1 ROM_LOAD, ROM_RELOAD, ROM_CONTINUE, and X-ROM interleave."""
    master = bytearray(0x90000)
    first = roms[MASTER_NAMES[0]]
    copy_to_region(master, 0x00000, first)
    copy_to_region(master, 0x10000, first)  # ROM_RELOAD overwrites overlapping range
    for name, offset in zip(MASTER_NAMES[1:], (0x30000, 0x50000, 0x70000)):
        copy_to_region(master, offset, roms[name])

    slave = bytearray(0x160000)
    copy_to_region(slave, 0x00000, roms[SLAVE_NAMES[0]])
    # ROM_CONTINUE places each high 0x20000 half at 0x120000 / 0x140000.
    for name, low_offset, high_offset in (
        (SLAVE_NAMES[1], 0x20000, 0x120000),
        (SLAVE_NAMES[2], 0x40000, 0x140000),
    ):
        data = roms[name]
        copy_to_region(slave, low_offset, data[:0x20000])
        copy_to_region(slave, high_offset, data[0x20000:])
    for name, offset in zip(SLAVE_NAMES[3:], (0x60000, 0x80000, 0xa0000, 0xc0000, 0xe0000)):
        copy_to_region(slave, offset, roms[name])

    xrom = bytearray(0x40000)
    xrom[0::2] = roms[XROM_NAMES[0]]
    xrom[1::2] = roms[XROM_NAMES[1]]
    return {"master": master, "slave": slave, "xrom": xrom}

def rotate_memory(region: bytearray) -> None:
    """Replicate MAME leland_state::rotate_memory (once per Z80 region)."""
    if len(region) < 0x10000 or (len(region) - 0x10000) % 0x8000:
        raise ValueError("Invalid banked region length")
    for start in range(0x10000, len(region), 0x8000):
        block = region[start:start + 0x8000]
        region[start:start + 0x8000] = block[0x2000:] + block[:0x2000]

def bank_metadata(slave_size: int) -> dict:
    master_bases = [
        0x02000, 0x18000, 0x20000, 0x28000,
        0x30000, 0x38000, 0x40000, 0x48000,
        0x50000, 0x58000, 0x60000, 0x68000,
        0x70000, 0x78000, 0x80000, 0x88000,
    ]
    slave_bases = {}
    for control in range(64):
        bank = control & 0x0f
        base = (0x2000 if not bank else
                0x10000 * bank + 0x8000 * ((control >> 4) & 1)
                + (0x100000 * ((control >> 5) & 1) if slave_size > 0x100000 else 0))
        slave_bases[f"{control:02x}"] = (
            f"{base:06x}" if base + 0x8000 <= slave_size else "invalid->002000"
        )
    return {
        "master_cpu": "Z80 6 MHz",
        "slave_cpu": "Z80 6 MHz",
        "master_fixed": "0000-1fff = master region offset 000000",
        "master_bank_window": "2000-9fff = one 0x8000 bank",
        "master_bank_region_offsets": [f"{n:06x}" for n in master_bases],
        "master_a000_dfff": "ROM/battery/QRAM view (depends on master control)",
        "slave_fixed": "0000-1fff = slave region offset 000000",
        "slave_bank_window": "2000-9fff = one 0x8000 bank",
        "slave_bank_control_to_region_offset": slave_bases,
        "slave_reset_bank": "010000",
        "notes": "Offsets refer to MAME-rotated region images; not CPU addresses. "
                 "Dynamic RAM/VRAM/palette windows require runtime tracing.",
    }

def recover(archive: Path, output: Path) -> dict:
    roms = read_and_verify_roms(archive)
    regions = reconstruct_regions(roms)
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "set": "indyheat (1991, revision 1)",
        "status": "ROM checks passed; program regions reconstructed, NOT gameplay decompiled",
        "regions": {},
        "memory_map": bank_metadata(len(regions["slave"])),
        "reference": "MAME src/mame/cinematronics/leland.cpp and leland_m.cpp",
    }
    for name, region in regions.items():
        raw = bytes(region)
        (output / f"{name}.mame_raw.bin").write_bytes(raw)
        if name in ("master", "slave"):
            rotate_memory(region)
        data = bytes(region)
        (output / f"{name}.mame_runtime.bin").write_bytes(data)
        report["regions"][name] = {
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "rotation_applied": name != "xrom",
        }
    (output / "memory_map.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Local, user-supplied indyheat.zip (arcade rev 1)")
    parser.add_argument("--out", type=Path, default=Path("local/rom-recovery"))
    args = parser.parse_args()
    try:
        report = recover(args.archive, args.out)
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Verified and reconstructed {len(ROMS)} program/data ROMs.")
    print(f"Local output: {args.out.resolve()}")
    print("This reconstructs memory layout only; mechanical routine identification remains pending.")
    print("Commit neither the ROM archive nor generated .bin files.")
    print("Report:", args.out / "memory_map.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
