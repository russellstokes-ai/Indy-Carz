#!/usr/bin/env python3
"""Exhaustively recover original 1991 arcade XROM arithmetic behaviour.

Reads only local/private, MAME-reconstructed XROM. No original tables or binary
data are committed. This is *table extraction*, not complete car physics.
"""
from pathlib import Path
import argparse
import hashlib
import json

EXPECTED = "1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"


def signed8(value: int) -> int:
    return value - 256 if value & 128 else value


def signed_multiply_doubled(a: int, b: int) -> int:
    return max(-32768, min(32767, signed8(a) * signed8(b) * 2)) & 0xffff


def unsigned_multiply_rounded(a: int, b: int) -> int:
    return ((a * b) + 128) >> 8


def slot0_word(data: bytes, a: int, b: int) -> int:
    pos = ((a << 8) | b) * 2
    return data[pos] | (data[pos + 1] << 8)


def slot1_low(data: bytes, a: int, b: int) -> int:
    return data[0x20000 + ((a << 8) | b) * 2]


def analyze(xrom: bytes) -> dict:
    if len(xrom) != 0x40000 or hashlib.sha256(xrom).hexdigest() != EXPECTED:
        raise ValueError("Expected original arcade MAME-interleaved XROM")
    errors_a = errors_b = saturated = 0
    for a in range(256):
        for b in range(256):
            errors_a += slot0_word(xrom, a, b) != signed_multiply_doubled(a, b)
            errors_b += slot1_low(xrom, a, b) != unsigned_multiply_rounded(a, b)
            saturated += signed8(a) * signed8(b) * 2 > 32767
    # Slot1 high byte belongs to a different, as yet unidentified function.
    high = bytes(xrom[0x20001::2])
    return {
        "source": "1991 Indy Heat arcade XROM (u68 and u69)",
        "slot0": {
            "formula": "clamp(signed8(a) * signed8(b) * 2, -32768, 32767)",
            "verified_pairs": 65536,
            "mismatches": errors_a,
            "saturation_pairs": saturated,
        },
        "slot1_low": {
            "formula": "(unsigned8(a) * unsigned8(b) + 128) >> 8",
            "verified_pairs": 65536,
            "mismatches": errors_b,
        },
        "slot1_high": {
            "status": "UNVERIFIED mathematical purpose",
            "bytes": len(high),
            "sha256": hashlib.sha256(high).hexdigest(),
        },
        "scope": "Exact two XROM numerical tables only; engine/AI/track rules not established",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xrom", type=Path, help="Private xrom.mame_runtime.bin")
    parser.add_argument("--out", type=Path,
                        default=Path("local/engine-extraction/xrom_math.json"))
    args = parser.parse_args()
    report = analyze(args.xrom.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
