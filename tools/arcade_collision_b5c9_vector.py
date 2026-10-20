#!/usr/bin/env python3
"""Exact Indy Heat arcade B5C9-B63B contact-correction vector reconstruction.

The original fixed-master Z80 routine consumes the low 7 bits of contact
payload E91B, the first car's angular state (IX-0x43), and the quantised
relative heading E922. It calculates two signed 16-bit displacement words,
BC and DE, before deciding which car will receive them.

This is NOT a complete collision response, vehicle dynamics, or a Godot
implementation. Reads private user-provided original MAME ROM images; never
publish the input binaries or derived original assets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

MASTER_HASH = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_HASH = "1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
START, STOP = 0xB5C9, 0xB63C
STAGE_HASH = "a0df3e547120c5131deef88bd5df28851de30ba2815e4d73484fc6c7ae4a75d3"
MASTER_SIZE = 0x90000
XROM_SIZE = 0x40000


def signed8(value: int) -> int:
    return value - 256 if value >= 128 else value


def signed16(value: int) -> int:
    return value - 65536 if value >= 32768 else value


def asr16(value: int, bits: int) -> int:
    return (signed16(value & 65535) >> bits) & 65535


def trig8(angle: int, cosine: bool = True) -> int:
    """The arcade's original 256-step, signed 8-bit trigonometric function."""
    if not 0 <= angle <= 255:
        raise ValueError("Original angles are unsigned byte values")
    func = math.cos if cosine else math.sin
    return max(-128, min(127, round(128 * func(angle * math.tau / 256)))) & 255


def xrom_slot0_signed(a: int, b: int) -> int:
    """Independent mathematics already verified across the entire X-ROM table."""
    if not 0 <= a <= 255 or not 0 <= b <= 255:
        raise ValueError("Original operands must be bytes")
    product = signed8(a) * signed8(b) * 2
    return max(-32768, min(32767, product)) & 65535


def independent_vector(payload: int, first_car_heading: int,
                       heading_category: int) -> tuple[int, int]:
    """Original signed correction words BC,DE (16-bit two's complement).

    The four original X-ROM products are shifted right arithmetically by 1
    or 2, added with 16-bit wrap, then shifted by 4. Python truncation-to-
    zero or float vector normalisation would change negative corrections.
    """
    if not (0 <= payload < 128 and 0 <= first_car_heading < 256
            and 0 <= heading_category < 256 and heading_category % 16 == 0):
        raise ValueError("Expected seven-bit payload, heading byte, heading high nibble")
    reversed_angle = (first_car_heading + 128) & 255
    offset_angle = (first_car_heading + heading_category + 8) & 255

    def axis(cosine: bool) -> int:
        first = asr16(xrom_slot0_signed(payload, trig8(reversed_angle, cosine)), 1)
        second = asr16(xrom_slot0_signed(payload, trig8(offset_angle, cosine)), 2)
        combined = (first + second) & 65535
        return asr16(combined, 4)

    return axis(True), axis(False)


def original_b5c9_opcodes(master: bytes, xrom: bytes, payload: int,
                          heading: int, heading_category: int) -> tuple[int, int]:
    """Boundedly execute the original fixed Z80 instruction sequence.

    Source: B5C9..B63B. STOP is before IX/IY bit1 branches B63C onward.
    Emulates the original X-ROM slot-0 read/write ports and carry-only shifts.
    Any unexpected opcode or memory address fails closed.
    """
    if len(master) != MASTER_SIZE or len(xrom) != XROM_SIZE:
        raise ValueError("Original MAME master and X-ROM dimensions required")
    if not (0 <= payload < 128 and 0 <= heading < 256
            and 0 <= heading_category < 256 and heading_category % 16 == 0):
        raise ValueError("Invalid original contact-vector input range")
    pc, a = START, payload
    b = c = d = e = h = l = carry = xr = 0
    stack: list[int] = []

    for _ in range(95):
        op = master[pc]
        if op == 0x57:  # LD D,A
            d = a; pc += 1
        elif op == 0xDD:  # LD A,(IX-$43) / ADD A,(IX-$43)
            ext, disp = master[pc+1:pc+3]
            if disp != 0xBD or ext not in (0x7E, 0x86):
                raise ValueError(f"Unexpected indexed source at {pc:04X}")
            a = heading if ext == 0x7E else (a + heading) & 255
            pc += 3
        elif op == 0xC6:  # ADD A,immediate
            a = (a + master[pc+1]) & 255
            pc += 2
        elif op == 0x6F:
            l = a; pc += 1
        elif op == 0x26:
            h = master[pc+1]; pc += 2
        elif op == 0x4E:
            c = master[(h << 8) | l]; pc += 1
        elif op == 0x6E:
            l = master[(h << 8) | l]; pc += 1
        elif op == 0x62:
            h = d; pc += 1
        elif op == 0x22:  # LD ($FFFC),HL, original X-ROM slot0 address
            if master[pc+1:pc+3] != bytes.fromhex("fcff"):
                raise ValueError(f"Unexpected original ROM write address at {pc:04X}")
            xr = (h << 8) | l
            pc += 3
        elif op == 0x2A:  # LD HL,($FFFC), original signed product
            if master[pc+1:pc+3] != bytes.fromhex("fcff"):
                raise ValueError(f"Unexpected original ROM read address at {pc:04X}")
            value = xrom[2*xr] | xrom[2*xr+1] << 8
            h, l = value >> 8, value & 255
            pc += 3
        elif op == 0xCB:
            ext = master[pc+1]
            if ext == 0x2C:  # SRA H
                carry = h & 1
                h = (h >> 1) | (h & 128)
            elif ext == 0x1D:  # RR L
                previous = l
                l = (l >> 1) | (carry << 7)
                carry = previous & 1
            else:
                raise ValueError(f"Unexpected original shift opcode {ext:02X} at {pc:04X}")
            pc += 2
        elif op == 0xE5:
            stack.append((h << 8) | l); pc += 1
        elif op == 0x79:
            a = c; pc += 1
        elif op == 0x32:  # LD ($FFFC),A; ONLY low byte of X-ROM address changes
            if master[pc+1:pc+3] != bytes.fromhex("fcff"):
                raise ValueError(f"Unexpected original ROM byte-write at {pc:04X}")
            xr = (xr & 0xFF00) | a; pc += 3
        elif op == 0x3A:  # LD A,(E922)
            if master[pc+1:pc+3] != bytes.fromhex("22e9"):
                raise ValueError(f"Unexpected original input address at {pc:04X}")
            a = heading_category; pc += 3
        elif op == 0x46:
            b = master[(h << 8) | l]; pc += 1
        elif op == 0x7E:
            a = master[(h << 8) | l]; pc += 1
        elif op == 0xD1:
            if not stack: raise ValueError("Original stack underflow")
            value = stack.pop()
            d, e = value >> 8, value & 255
            pc += 1
        elif op == 0x19:  # ADD HL,DE, modulo 16-bit
            value = ((h << 8) | l) + ((d << 8) | e)
            h, l = (value >> 8) & 255, value & 255
            pc += 1
        elif op == 0x7D:
            a = l; pc += 1
        elif op == 0x1F:  # RRA with incoming carry from SRA H
            previous = a
            a = (a >> 1) | (carry << 7)
            carry = previous & 1
            pc += 1
        elif op == 0x54:
            d = h; pc += 1
        elif op == 0x5F:
            e = a; pc += 1
        elif op == 0x78:
            a = b; pc += 1
        elif op == 0xC1:
            if not stack: raise ValueError("Original stack underflow")
            value = stack.pop()
            b, c = value >> 8, value & 255
            pc += 1
        elif op == 0x09:  # ADD HL,BC
            value = ((h << 8) | l) + ((b << 8) | c)
            h, l = (value >> 8) & 255, value & 255
            pc += 1
        elif op == 0x44:
            b = h; pc += 1
        elif op == 0x4F:
            c = a; pc += 1
        else:
            raise ValueError(f"Unexpected original contact opcode {op:02X} at PC {pc:04X}")
        if pc == STOP:
            if stack:
                raise ValueError("Original vector computation did not balance its stack")
            return (b << 8) | c, (d << 8) | e
        if not START <= pc < STOP:
            raise ValueError(f"Original vector computation departed stage: {pc:04X}")
    raise ValueError("Original contact vector exceeded bounded instruction budget")


def verify(master: bytes, xrom: bytes) -> dict:
    if len(master) != MASTER_SIZE or hashlib.sha256(master).hexdigest() != MASTER_HASH:
        raise ValueError("Checksum-verified original 1991 arcade master required")
    if len(xrom) != XROM_SIZE or hashlib.sha256(xrom).hexdigest() != XROM_HASH:
        raise ValueError("Checksum-verified original 1991 arcade X-ROM required")
    if hashlib.sha256(master[START:STOP]).hexdigest() != STAGE_HASH:
        raise ValueError("Original 115-byte contact-vector instruction sequence changed")
    # Verify the actual trigonometric and signed multiply inputs, not simply
    # independently generated substitute tables.
    for angle in range(256):
        for cosine, base in ((True, 0xA200), (False, 0xA500)):
            if master[base+angle] != trig8(angle, cosine):
                raise AssertionError(f"Original trigonometric sample mismatch {angle}")
    checked = 0
    for payload in range(128):
        for heading in range(256):
            for category in range(0, 256, 16):
                expected = independent_vector(payload, heading, category)
                observed = original_b5c9_opcodes(master, xrom, payload, heading, category)
                if expected != observed:
                    raise AssertionError(
                        f"Original B5C9 mismatch payload={payload}, heading={heading}, "
                        f"category={category}: model={expected} opcode={observed}"
                    )
                checked += 1
    return {
        "source": "original Indy Heat 1991 arcade fixed master Z80 B5C9..B63B",
        "stage_sha256": STAGE_HASH,
        "exact_cases": checked,
        "sixteen_bit_outputs_compared": checked*2,
        "mismatches": 0,
        "input_payload": "E91B low seven bits (0..127), adjusted by B5AC wrapper",
        "angles": "IX-0x43; E922 high nibble + 8; first trig angle = heading+128",
        "word_BC": "arith16(((SROM(payload*cos(heading+128)>>1) + SROM(payload*cos(heading+E922+8)>>2)) mod 65536)>>4)",
        "word_DE": "identical formula with sine instead of cosine",
        "scope": "Exact two correction words only; which-car corrections, impulse/damage and live gameplay parity remain OPEN",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("master", type=Path, help="Private master.mame_runtime.bin")
    ap.add_argument("xrom", type=Path, help="Private xrom.mame_runtime.bin")
    ap.add_argument("--out", type=Path,
                    default=Path("local/engine-extraction/contact_vector_b5c9.json"))
    args = ap.parse_args()
    result = verify(args.master.read_bytes(), args.xrom.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
