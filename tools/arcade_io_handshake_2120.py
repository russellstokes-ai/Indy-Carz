#!/usr/bin/env python3
"""Original 1991 Indy Heat master bank-3 2120..21A2 I/O handshake.

This is the exact post-championship-selection CALL 2120:
  - master port 05/06/0C outputs and port 04 polling
  - ten attempts with 0xC350 (50,000) maximum polls per phase
  - original 2105 interrupt-state helper and restored IFF state
  - E7A4..E7AA RAM-byte initialization and retry/error marking

Real electrical peer behavior, original gameplay sound identities and
duration per poll require MAME runtime; controlled port inputs here are
test stimuli, NOT observed in-game sound/serial outcomes.
Original ROM is private; only independently modelled code is public.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
BANK3_BASE = 0x28000
START, STOP = 0x2120, 0x21A3
HELPER, HELPER_STOP = 0x2105, 0x2115
STAGE_SHA = "f024c39f98473e88dccdc9a660876d6b9afdc256cba507cbd067e56e5ec60161"
HELPER_SHA = "dde775a256640c20739a3a46a1d5aa8c2050aa629011f0589c4f558d2620d3ce"
POLL_BUDGET = 0xC350
RETRIES = 10


def validate(plan: tuple[tuple[int, int], ...], i_register: int,
             iff: bool, initial_e62b: int) -> None:
    if not isinstance(iff, bool) or not 0 <= i_register < 256 or not 0 <= initial_e62b < 256:
        raise ValueError("Z80 I register, IFF2 and status byte required")
    if not 1 <= len(plan) <= RETRIES or any(
            len(pair) != 2 or any(not 0 <= n <= POLL_BUDGET for n in pair)
            for pair in plan):
        raise ValueError("One to ten controlled handshake attempts (0..50000 polls)")


def independent(plan: tuple[tuple[int, int], ...], i_register: int,
                iff: bool, initial_e62b: int) -> dict:
    """Model original handshake as a sequence of controlled port 04 inputs.

    Each attempt specifies (#unsuccessful phase-one polls,
    #unsuccessful phase-two polls). 50000 means timeout in that phase.
    After an unsuccessful attempt another plan entry MUST exist.
    """
    validate(plan, i_register, iff, initial_e62b)
    ports = []
    reads = 0
    failure_seen = False
    outcome = None
    actual_attempts = 0
    for attempt in range(RETRIES):
        if attempt >= len(plan):
            raise ValueError("Original handshake retry requires another scripted attempt")
        phase1, phase2 = plan[attempt]
        actual_attempts += 1
        ports.extend(((6, 255), (5, 255), (12, 254), (12, 255)))
        reads += min(POLL_BUDGET, phase1+1)
        if phase1 == POLL_BUDGET:
            failure_seen = True
        else:
            ports.extend(((6, 0), (5, 0)))
            reads += min(POLL_BUDGET, phase2+1)
            if phase2 < POLL_BUDGET:
                outcome = "success"
                break
            failure_seen = True
        if attempt == RETRIES-1:
            outcome = "retry_exhausted"
    return {
        "ports": ports,
        "reads04": reads,
        "attempts": actual_attempts,
        "status_e62b": initial_e62b | 128,
        "e7aa": 255, "e7a9": int(failure_seen),
        "e7a4": 128, "e7a5": 128, "e7a6": 128,
        "e7a7": 1, "e7a8": 10,
        "returned_a": i_register if iff else 1,
        "returned_iff": iff, "outcome": outcome,
    }


def bank_view(master: bytes) -> bytes:
    if len(master) != 0x90000 or sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Checksum-verified original 1991 arcade master required")
    view = bytearray(master[:0xE000])
    view[0x2000:0xA000] = master[BANK3_BASE:BANK3_BASE+0x8000]
    return bytes(view)


def check_original(master: bytes) -> None:
    m = bank_view(master)
    for first, last, expected in (
        (START, STOP, STAGE_SHA), (HELPER, HELPER_STOP, HELPER_SHA)
    ):
        if sha256(m[first:last]).hexdigest() != expected:
            raise ValueError(f"Original handshake instruction signature differs at {first:04X}")


def original_opcode(master: bytes, plan: tuple[tuple[int, int], ...],
                    i_register: int, iff: bool, initial_e62b: int) -> dict:
    """Execute the actual original Z80 opcodes, with controlled 04 input.

    No loops are skipped: original DEC HL/IN/JP polls execute at every
    iteration, including full 50,000-poll timeout and ten-retry cases.
    Return only after the original 2120 RET PO or RET/EI route.
    """
    validate(plan, i_register, iff, initial_e62b)
    m = bank_view(master)
    ram = {
        0xE62B: initial_e62b, 0xE7AA: 0, 0xE7A9: 0, 0xE7A7: 0,
        0xE7A4: 0, 0xE7A5: 0, 0xE7A6: 0, 0xE7A8: 0,
    }
    a = b = h = l = 0
    zero = pv = False
    iff_active = iff
    stack = []
    ports = []
    pc = START
    attempts = -1
    phase1_count = phase2_count = reads = 0
    successful = False

    def result() -> dict:
        if stack:
            raise ValueError("Original handshake exited with unbalanced Z80 stack")
        return {
            "ports": ports, "reads04": reads, "attempts": attempts+1,
            "status_e62b": ram[0xE62B], "e7aa": ram[0xE7AA],
            "e7a9": ram[0xE7A9], "e7a4": ram[0xE7A4],
            "e7a5": ram[0xE7A5], "e7a6": ram[0xE7A6],
            "e7a7": ram[0xE7A7], "e7a8": ram[0xE7A8],
            "returned_a": a, "returned_iff": iff_active,
            "outcome": "success" if successful else "retry_exhausted",
        }

    while reads <= RETRIES*POLL_BUDGET*2 and len(ports) < 100:
        op = m[pc]
        if op == 0x3E:  # LD A,nn
            a = m[pc+1]
            pc += 2
        elif op == 0x32:  # LD (nn),A
            addr = m[pc+1] | (m[pc+2] << 8)
            if addr not in ram:
                raise ValueError("Original unexpected handshake memory write")
            ram[addr] = a
            pc += 3
        elif op == 0xCD:  # CALL original 2105 interrupt helper
            addr = m[pc+1] | (m[pc+2] << 8)
            if addr != HELPER:
                raise ValueError("Unexpected original I/O helper call")
            stack.append(("call", pc+3))
            pc = addr
        elif op == 0x21:  # LD HL,nn
            l, h = m[pc+1:pc+3]
            pc += 3
        elif op == 0xCB:  # SET7 or BIT7 at E62B
            ext = m[pc+1]
            addr = (h << 8) | l
            if addr != 0xE62B or ext not in (0xFE, 0x7E):
                raise ValueError("Unexpected original 2105 bit access")
            if ext == 0xFE:
                ram[addr] |= 128
            else:
                zero = not bool(ram[addr] & 128)
            pc += 2
        elif op == 0xED:  # LD A,I, P/V reflects IFF2
            if m[pc+1] != 0x57:
                raise ValueError("Unexpected original indexed interrupt opcode")
            a = i_register
            pv = iff_active
            zero = (a == 0)
            pc += 2
        elif op == 0xE8:  # RET PE
            pc += 1
            if pv:
                if not stack or stack[-1][0] != "call":
                    raise ValueError("Original helper return stack mismatch")
                pc = stack.pop()[1]
        elif op == 0x28:  # JR Z
            delta = m[pc+1]
            if delta >= 128:
                delta -= 256
            pc += 2 + (delta if zero else 0)
        elif op == 0xB7:  # OR A
            zero, pv = (a == 0), a.bit_count() % 2 == 0
            pc += 1
        elif op == 0xC9:  # RET original helper or main
            if pc == HELPER_STOP-1:
                if not stack or stack[-1][0] != "call":
                    raise ValueError("Original 2105 RET stack mismatch")
                pc = stack.pop()[1]
            elif pc == STOP-1:
                return result()
            else:
                raise ValueError("Unexpected original handshake RET")
        elif op == 0xF5:  # PUSH AF
            stack.append(("AF", a, pv))
            pc += 1
        elif op == 0xE2:  # JP PO
            addr = m[pc+1] | (m[pc+2] << 8)
            if addr != 0x212D:
                raise ValueError("Original interrupt decision target changed")
            pc = addr if not pv else pc+3
        elif op == 0xF3:  # DI
            iff_active = False
            pc += 1
        elif op == 0xAF:  # XOR A
            a, zero, pv = 0, True, True
            pc += 1
        elif op == 0xE6:  # AND imm
            a &= m[pc+1]
            zero, pv = (a == 0), a.bit_count() % 2 == 0
            pc += 2
        elif op == 0xF6:  # OR imm
            a |= m[pc+1]
            zero, pv = (a == 0), a.bit_count() % 2 == 0
            pc += 2
        elif op == 0xD3:  # OUT port,A
            port = m[pc+1]
            if port not in (5, 6, 12):
                raise ValueError("Unexpected original output port")
            ports.append((port, a))
            pc += 2
        elif op == 0x7E:  # LD A,(HL)
            addr = (h << 8) | l
            if addr not in ram:
                raise ValueError("Unexpected original indexed memory read")
            a = ram[addr]
            pc += 1
        elif op == 0x77:  # LD (HL),A
            addr = (h << 8) | l
            if addr not in ram:
                raise ValueError("Unexpected original indexed memory write")
            ram[addr] = a
            pc += 1
        elif op == 0x06:  # LD B,1E
            b = m[pc+1]
            pc += 2
        elif op == 0x10:  # DJNZ
            delta = m[pc+1]
            if delta >= 128:
                delta -= 256
            b = (b-1) & 255
            pc += 2 + (delta if b else 0)
        elif op == 0xDB:  # IN A,(04), controlled test response
            if m[pc+1] != 4:
                raise ValueError("Unexpected original response port")
            if not 0 <= attempts < len(plan):
                raise ValueError("Original loop requested unscripted attempt")
            phase1, phase2 = plan[attempts]
            if pc == 0x2162:
                a = 255 if phase1_count >= phase1 else 0
                phase1_count += 1
            elif pc == 0x2183:
                a = 0 if phase2_count >= phase2 else 1
                phase2_count += 1
            else:
                raise ValueError("Unexpected original port 04 input instruction")
            reads += 1
            pc += 2
        elif op == 0x3C:  # INC A
            a = (a+1) & 255
            zero = (a == 0)
            pc += 1
        elif op == 0xCA:  # JP Z
            addr = m[pc+1] | (m[pc+2] << 8)
            if pc == 0x2186 and zero and addr == 0x219A:
                successful = True
            pc = addr if zero else pc+3
        elif op == 0x2B:  # DEC HL
            value = (((h << 8) | l)-1) & 65535
            h, l = value >> 8, value & 255
            pc += 1
        elif op == 0x7D:  # LD A,L
            a = l
            pc += 1
        elif op == 0xB4:  # OR H
            a |= h
            zero, pv = (a == 0), a.bit_count() % 2 == 0
            pc += 1
        elif op == 0xC2:  # JP NZ
            addr = m[pc+1] | (m[pc+2] << 8)
            pc = addr if not zero else pc+3
        elif op == 0x35:  # DEC (HL)
            addr = (h << 8) | l
            if addr != 0xE7A8:
                raise ValueError("Original decrement not at retry counter")
            ram[addr] = (ram[addr]-1) & 255
            zero = ram[addr] == 0
            pc += 1
        elif op == 0xC3:  # JP nn
            pc = m[pc+1] | (m[pc+2] << 8)
        elif op == 0xF1:  # POP AF
            if not stack or stack[-1][0] != "AF":
                raise ValueError("Original AF stack mismatch")
            _, a, pv = stack.pop()
            pc += 1
        elif op == 0xE0:  # RET PO
            pc += 1
            if not pv:
                return result()
        elif op == 0xFB:  # EI
            iff_active = True
            pc += 1
        else:
            raise ValueError(f"Unrecognised original bank3 opcode {op:02X} at {pc:04X}")

        if pc == 0x2146 and (not ports or ports[-1] != (5, 255)):
            attempts += 1
            phase1_count = phase2_count = 0
        if not (START <= pc < STOP or HELPER <= pc < HELPER_STOP):
            raise ValueError("Original handshake escaped checksum-checked routine")

    raise ValueError("Original handshake bounded poll budget exceeded")


def verify(master: bytes, quick_cases: int = 6000) -> dict:
    """Actual original Z80 instruction parity with controlled input scripts."""
    check_original(master)
    from random import Random
    rng = Random(0x2120)
    checked = 0
    for i in range(quick_cases):
        status = rng.randrange(256)
        i_reg = rng.randrange(256)
        iff = bool(rng.randrange(2))
        plan = ((rng.randrange(8), rng.randrange(8)),)
        expected = independent(plan, i_reg, iff, status)
        actual = original_opcode(master, plan, i_reg, iff, status)
        if expected != actual:
            raise AssertionError(f"Original port reset mismatch quick case {i}")
        checked += 1
    edge_plans = (
        ((50000, 0), (0, 0)), ((0, 50000), (0, 0)),
        ((50000, 0),)*10, ((0, 50000),)*10,
        ((50000, 0),)*9 + ((0, 0),),
    )
    for plan in edge_plans:
        expected = independent(plan, 97, True, 77)
        actual = original_opcode(master, plan, 97, True, 77)
        if expected != actual:
            raise AssertionError(f"Original port 04 full timeout mismatch: {plan}")
        checked += 1
    return {
        "source": "Original arcade master bank3 2120-21A2, helper 2105-2114",
        "original_opcodes_executed_cases": checked, "mismatches": 0,
        "port4_max_polls_each_phase": POLL_BUDGET,
        "max_attempts": RETRIES,
        "ports_written": [5, 6, 12],
        "port_read": 4,
        "limitations": "Controlled port4 inputs are NOT real emulator electrical/device traces",
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("master", type=Path)
    ap.add_argument("--quick-cases", type=int, default=6000)
    args = ap.parse_args()
    print(json.dumps(verify(args.master.read_bytes(), args.quick_cases), indent=2))
