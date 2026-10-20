#!/usr/bin/env python3
"""Verify original Indy Heat master B67E-B6EC two-car velocity projection.

The source is the *user-provided, privately retained* arcade rev-1 ROM.
This tool contains independent, integer-only reconstruction of a bounded
original collision routine and a minimal fail-closed interpreter of the real
Z80 opcodes. It does not supply a full collision/traction game engine.

Do not commit original ROM bytes, X-ROM tables, disassembly or trace records.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
from random import Random

MASTER_HASH = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_HASH = "1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
STAGE_START, STAGE_STOP = 0xB67E, 0xB6ED  # stop just before next event-classification stage
BODY_START = 0xB699
STAGE_HASH = "b1019935ece77d5bb7889204288047c1079f301e2b59fb76a782b711ca441adb"
HELPER_HASH = "d5c7aba37a28a9e98a58f316265b981f492a9ca74e4325999f4500323f0cd286"
SPEED_OFFSET = 0x41      # (IX-$3F) relative to IX == slot start +$41
HEADING_OFFSET = 0x3F    # (IX-$41) relative to IX == slot start +$3F


def signed8(byte: int) -> int:
    return byte - 256 if byte & 128 else byte


def trig8(angle: int, cosine: bool) -> int:
    if not 0 <= angle <= 255:
        raise ValueError("Heading must be one unsigned original angle byte")
    f = math.cos if cosine else math.sin
    return max(-128, min(127, round(128 * f(angle * math.tau / 256))))


def xrom_high_math(a: int, b: int) -> int:
    """High result byte of the verified original signed X-ROM slot-0 product."""
    product = max(-32768, min(32767, signed8(a & 255) * signed8(b & 255) * 2))
    return (product >> 8) & 255


def car_components(slot: bytes) -> tuple[int, int]:
    """One car -> (sin*speed projection, cos*speed projection), byte values.

    SRA A / ADC A,0 is signed ceil(speed/2), not unsigned divide.
    """
    if len(slot) != 256:
        raise ValueError("Expected one 0x100-byte original car-state record")
    angle, speed = slot[HEADING_OFFSET], signed8(slot[SPEED_OFFSET])
    halved = ((speed + 1) // 2) & 255
    return (
        xrom_high_math(halved, trig8(angle, False) & 255),
        xrom_high_math(halved, trig8(angle, True) & 255),
    )


def sat_diff_byte(second: int, first: int) -> int:
    """Original SUB and PE-signed-overflow helper at master $0B35."""
    if not 0 <= first < 256 or not 0 <= second < 256:
        raise ValueError("Signed collision projection operands must be bytes")
    return max(-128, min(127, signed8(second) - signed8(first))) & 255


def independent(first: bytes, second: bytes, e919: int) -> tuple[int, int, int, int, int, int]:
    """(E91F low, E91F high, E923 low, E923 high, D, E) at $B6ED.

    E919 bit5 swaps active IX/IY pointers before the original common body.
    The final D/E bytes represent *saturated relative projected differences*,
    not a proven velocity impulse, damage level or terrain response.
    """
    if len(first) != 256 or len(second) != 256 or not 0 <= e919 <= 255:
        raise ValueError("Two original slots and an 8-bit event status required")
    active_first, active_second = (second, first) if (e919 & 0x20) else (first, second)
    e91f_low, e91f_high = car_components(active_first)
    e923_low, e923_high = car_components(active_second)
    return (
        e91f_low, e91f_high, e923_low, e923_high,
        sat_diff_byte(e923_high, e91f_high),
        sat_diff_byte(e923_low, e91f_low),
    )


def execute_original(master: bytes, xrom: bytes, first: bytes,
                     second: bytes, e919: int) -> tuple[int, int, int, int, int, int]:
    """Run actual master Z80 opcodes B67E..B6EC with original lookup ROM.

    Interpreter intentionally recognises only instruction forms in this stage,
    stops before B6ED, checks all I/O and RAM addresses, and raises on any
    unexpected control flow instead of silently emulating an invented rule.
    """
    if len(master) != 0x90000 or len(xrom) != 0x40000:
        raise ValueError("Original master/X-ROM dimensions required")
    if len(first) != 256 or len(second) != 256 or not 0 <= e919 <= 255:
        raise ValueError("Two original 256-byte slots and 8-bit status required")

    ix, iy = first, second
    a = b = c = d = e = h = l = carry = 0
    zero = sign = overflow = False
    xrom_addr = 0
    ram = {0xE919: e919}
    pointers: list[bytes] = []
    calls: list[int] = []
    pc = STAGE_START
    for _ in range(80):
        op = master[pc]
        if op == 0x3A:  # LD A,(absolute) -- event byte or X-ROM high-output port
            addr = master[pc+1] | (master[pc+2] << 8)
            if addr == 0xE919:
                a = ram[addr]
            elif addr == 0xFFFD:
                a = xrom[2*xrom_addr+1]
            else:
                raise ValueError(f"Unexpected original Z80 byte read {addr:04X}")
            pc += 3
        elif op == 0xCB:  # BIT 5,A or SRA A, preserving original low-bit carry
            ext = master[pc+1]
            if ext == 0x6F:
                zero = not bool(a & 0x20)
            elif ext == 0x2F:
                carry = a & 1
                a = ((a >> 1) | (a & 128)) & 255
            else:
                raise ValueError(f"Unexpected Z80 CB {ext:02X} at {pc:04X}")
            pc += 2
        elif op == 0x28:  # JR Z to original unswapped body
            offset = signed8(master[pc+1])
            pc += 2 + (offset if zero else 0)
        elif op in (0xDD, 0xFD):
            ext = master[pc+1]
            if ext == 0xE5:  # PUSH IX or IY
                pointers.append(ix if op == 0xDD else iy)
                pc += 2
            elif ext == 0xE1:  # POP IX or IY
                if not pointers:
                    raise ValueError("Original indexed stack underflow")
                incoming = pointers.pop()
                if op == 0xDD: ix = incoming
                else: iy = incoming
                pc += 2
            elif ext in (0x6E, 0x7E) and master[pc+2] in (0xBF, 0xC1):
                record = ix if op == 0xDD else iy
                offset = master[pc+2] - 0x80  # IX points $80 into original slot
                value = record[offset]
                if ext == 0x6E: l = value
                else: a = value
                pc += 3
            else:
                raise ValueError(f"Unexpected indexed Z80 opcode {ext:02X} at {pc:04X}")
        elif op == 0xCD:  # CALL body only after swapping car pointers
            addr = master[pc+1] | (master[pc+2] << 8)
            if addr != BODY_START:
                raise ValueError(f"Unexpected original Z80 body target {addr:04X}")
            calls.append(pc+3)
            pc = addr
        elif op == 0x26:  # LD H,immediate -- original cos/sin table page
            h = master[pc+1]
            if h not in (0xA2, 0xA5):
                raise ValueError("Unexpected trigonometric ROM page")
            pc += 2
        elif op in (0x56, 0x46, 0x66):  # LD D/B/H,(HL)
            addr = (h << 8) | l
            if not ((0xA200 <= addr < 0xA300) or (0xA500 <= addr < 0xA600)):
                raise ValueError(f"Unexpected original lookup address {addr:04X}")
            val = master[addr]
            if op == 0x56: d = val
            elif op == 0x46: b = val
            else: h = val
            pc += 1
        elif op == 0xCE:  # ADC A,0 (SRA low-bit rounding)
            if master[pc+1] != 0:
                raise ValueError("Unexpected signed-speed rounding constant")
            a = (a + carry) & 255
            pc += 2
        elif op == 0x6F: l = a; pc += 1
        elif op == 0x22:  # LD (FFFC),HL sets full X-ROM lookup address
            if master[pc+1:pc+3] != b'\xFC\xFF':
                raise ValueError("Unexpected X-ROM address write")
            xrom_addr = (h << 8) | l
            pc += 3
        elif op == 0x32:  # LD (FFFD),A sets high lookup address only
            if master[pc+1:pc+3] != b'\xFD\xFF':
                raise ValueError("Unexpected X-ROM high-address write")
            xrom_addr = (a << 8) | (xrom_addr & 255)
            pc += 3
        elif op == 0x5F: e = a; pc += 1
        elif op == 0x57: d = a; pc += 1
        elif op == 0x4F: c = a; pc += 1
        elif op == 0x47: b = a; pc += 1
        elif op == 0x7A: a = d; pc += 1
        elif op == 0x78: a = b; pc += 1
        elif op == 0x79: a = c; pc += 1
        elif op == 0xED:
            ext = master[pc+1]
            dest = master[pc+2] | (master[pc+3] << 8)
            if ext == 0x53 and dest == 0xE91F:  # LD (E91F),DE
                ram[dest], ram[dest+1] = e, d
            elif ext == 0x43 and dest == 0xE923:  # LD (E923),BC
                ram[dest], ram[dest+1] = c, b
            else:
                raise ValueError(f"Unexpected original word store ED {ext:02X} {dest:04X}")
            pc += 4
        elif op in (0x92, 0x93):  # SUB D/E, signed overflow to helper
            second_val = signed8(a)
            first_val = signed8(d if op == 0x92 else e)
            diff = second_val - first_val
            a = diff & 255
            sign = bool(a & 128)
            overflow = not -128 <= diff <= 127
            pc += 1
        elif op == 0xEC:  # CALL PE,0B35 only if signed-overflow flag
            addr = master[pc+1] | (master[pc+2] << 8)
            if addr != 0x0B35:
                raise ValueError(f"Unexpected PE overflow target {addr:04X}")
            pc += 3
            if overflow:
                # Actual helper: JP P,0B3B / LD A,7F / RET / LD A,80 / RET
                hp = addr
                if master[hp:hp+3] != b'\xF2\x3B\x0B':
                    raise ValueError("Unexpected overflow saturation branch")
                hp = 0x0B3B if not sign else 0x0B38
                if master[hp] != 0x3E or master[hp+2] != 0xC9:
                    raise ValueError("Unexpected overflow saturation return")
                a = master[hp+1]
        elif op == 0xC9:  # RETURN after swapped IX/IY collision body
            if not calls:
                raise ValueError("Unexpected original early return")
            pc = calls.pop()
        else:
            raise ValueError(f"Unexpected original opcode {op:02X} at {pc:04X}")

        if pc == STAGE_STOP:
            if [k for k in (0xE91F,0xE920,0xE923,0xE924) if k not in ram]:
                raise ValueError("Original stage did not fill required vector RAM")
            return ram[0xE91F], ram[0xE920], ram[0xE923], ram[0xE924], d, e
        if not STAGE_START <= pc < STAGE_STOP:
            raise ValueError(f"Original projection departed bounded region at {pc:04X}")
    raise ValueError("Original projection instruction budget exceeded")


def verify(master: bytes, xrom: bytes, cases: int = 50000) -> dict:
    if len(master) != 0x90000 or sha256(master).hexdigest() != MASTER_HASH:
        raise ValueError("Checksum-verified original arcade master ROM required")
    if len(xrom) != 0x40000 or sha256(xrom).hexdigest() != XROM_HASH:
        raise ValueError("Checksum-verified original arcade X-ROM required")
    if sha256(master[STAGE_START:STAGE_STOP]).hexdigest() != STAGE_HASH:
        raise ValueError("Original B67E-B6EC opcode sequence changed")
    if sha256(master[0x0B35:0x0B3E]).hexdigest() != HELPER_HASH:
        raise ValueError("Original signed-overflow saturation helper changed")
    if cases < 0 or cases > 500000:
        raise ValueError("Bounded verification cases must be 0..500000")

    for heading in range(256):
        for cosine, page in ((True, 0xA200), (False, 0xA500)):
            if master[page+heading] != (trig8(heading, cosine) & 255):
                raise AssertionError(f"Arcade trigonometry changed at heading {heading}")
    for a in range(256):
        for b in range(256):
            addr = (a << 8) | b
            if xrom[2*addr+1] != xrom_high_math(a,b):
                raise AssertionError(f"Arcade signed multiply changed for operands {a},{b}")

    rng = Random(0xB67E)
    swaps = overflow_axes = 0
    for i in range(cases):
        l, r = bytearray(256), bytearray(256)
        l[HEADING_OFFSET], r[HEADING_OFFSET] = rng.randrange(256), rng.randrange(256)
        l[SPEED_OFFSET], r[SPEED_OFFSET] = rng.randrange(256), rng.randrange(256)
        status = (rng.randrange(256) | 0x20) if i % 2 else (rng.randrange(256) & ~0x20)
        model = independent(bytes(l), bytes(r), status)
        machine = execute_original(master, xrom, bytes(l), bytes(r), status)
        if machine != model:
            raise AssertionError(f"Arcade velocity projection mismatch {i}: model={model}, Z80={machine}")
        swaps += bool(status & 0x20)
        overflow_axes += (signed8(model[5]) != signed8(model[2])-signed8(model[0]))
        overflow_axes += (signed8(model[4]) != signed8(model[3])-signed8(model[1]))
    return {
        "source": "original 1991 arcade master Z80 B67E-B6EC, X-ROM slot 0 and helper 0B35",
        "master_stage_sha256": STAGE_HASH,
        "cases": cases,
        "mismatches": 0,
        "original_trig_lookup_bytes_checked": 512,
        "original_xrom_high_lookup_bytes_checked": 65536,
        "bit5_car_pointer_swaps": swaps,
        "saturated_relative_components": overflow_axes,
        "original_output": "two projected per-car byte pairs (E91F/E923), signed-saturated relative D/E",
        "scope": "bounded collision projection; downstream velocity/heading, contact consequence and gameplay still open",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("master", type=Path, help="private checksum-verified arcade master.mame_runtime.bin")
    ap.add_argument("xrom", type=Path, help="private checksum-verified arcade xrom.mame_runtime.bin")
    ap.add_argument("--cases", type=int, default=50000)
    ap.add_argument("--out", type=Path, default=Path("local/engine-extraction/velocity_projection_b67e.json"))
    args = ap.parse_args()
    report = verify(args.master.read_bytes(), args.xrom.read_bytes(), args.cases)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
