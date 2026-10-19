#!/usr/bin/env python3
"""Validate original Indy Heat Z80 steering lookup through the X-ROM at $341E.

One recovered numeric input->lookup stage; NOT the complete heading,
grip, speed or collision algorithm. Requires *local* reconstructed ROM data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from arcade_logic_probe import steering_table


def xrom_steering_sample(xrom: bytes, signed_response: int) -> dict:
    if len(xrom) != 0x40000:
        raise ValueError("Expected a 0x40000-byte MAME-interleaved X-ROM")
    if not -128 <= signed_response <= 127:
        raise ValueError("Input must be a signed 8-bit steering response")
    address = (((signed_response & 255) << 8) | 0x7F)
    upper = xrom[address * 2 + 1]
    doubled = (upper * 2) & 255
    return {
        "signed_steer_input": signed_response,
        "xrom_word_address": f"{address:04X}",
        "xrom_high_byte": upper,
        "doubled_signed": doubled - 256 if doubled >= 128 else doubled,
    }


def inspect(master: bytes, xrom: bytes) -> dict:
    responses = steering_table(master)
    reachable = sorted(set([-n for n in responses] + responses))
    rows = [xrom_steering_sample(xrom, n) for n in reachable]
    simple_rule_matches = all(
        row["xrom_high_byte"] == ((n - 1 if n > 0 else n) & 255)
        for n, row in zip(reachable, rows)
    )
    return {
        "location": "Master Z80 bank 0 at $341E",
        "xrom_interface": "write address to $FFFC, read upper byte at $FFFD",
        "word_address_formula": "(signed_response & 255) << 8 | 0x7F",
        "reachable_samples": len(reachable),
        "observed_simple_rule_matches": simple_rule_matches,
        "samples": rows,
        "verification_scope": "X-ROM lookup only; complete steering/yaw not yet verified",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master_runtime", type=Path)
    parser.add_argument("xrom_runtime", type=Path)
    parser.add_argument("--out", type=Path,
                        default=Path("local/recovery/steering_xrom.json"))
    args = parser.parse_args()
    result = inspect(args.master_runtime.read_bytes(), args.xrom_runtime.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Checked", result["reachable_samples"], "reachable steering inputs")
    print("Observed simple rule matched:", result["observed_simple_rule_matches"])


if __name__ == "__main__":
    main()
