#!/usr/bin/env python3
"""Original arcade master B4EE-B505 exact two-car fallback selection.

Model checks original status bit 0 at each car slot +7C, delegating to the
independently original-opcode-verified BABB-BB6B state restoration model.
Does not assert visible damage, spin, pit repair, or runtime event cadence.
Authentic ROM remains private.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
from random import Random
from arcade_collision_state_restore import model as restore

MASTER_SHA = '521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7'
START, STOP = 0xB4EE, 0xB506
STAGE_SHA = '519e1ee888fbe0d931a98822814cb3ead4541f51ba31e2f385595a097f58f832'


def independent(first: bytes, second: bytes) -> tuple[bytes, bytes, int]:
    """Independent control-flow reconstruction: records and number restored."""
    if len(first)!=256 or len(second)!=256:
        raise ValueError('Two original 0x100-byte car slots required')
    first_changed = not first[0x7C] & 1
    second_changed = not second[0x7C] & 1
    return (restore(first)[0] if first_changed else first,
            restore(second)[0] if second_changed else second,
            int(first_changed) + int(second_changed))


def execute_original(master: bytes, first: bytes, second: bytes) -> tuple[bytes, bytes, int]:
    """Interpret original fixed-master dispatcher; BABB separately verified."""
    if len(master)!=0x90000 or len(first)!=256 or len(second)!=256:
        raise ValueError('Original master ROM and two car records required')
    slots = [first, second]
    ix_index, iy_index = 0, 1
    z = False
    stack: list[int] = []
    calls = 0
    pc = START
    for _ in range(15):
        op = master[pc]
        if op in (0xDD, 0xFD):
            ext = master[pc+1]
            if ext == 0xCB:  # BIT 0,(IX-4) or BIT 0,(IY-4)
                if master[pc+2:pc+4] != b'\xFC\x46':
                    raise ValueError(f'Unexpected original status check {pc:04X}')
                z = not bool(slots[ix_index if op==0xDD else iy_index][0x7C] & 1)
                pc += 4
            elif ext == 0xE5:  # PUSH IX or PUSH IY
                stack.append(ix_index if op == 0xDD else iy_index)
                pc += 2
            elif ext == 0xE1:  # POP IX, swaps second-car pointer into IX
                if op != 0xDD or not stack:
                    raise ValueError('Unexpected original car-pointer stack operation')
                ix_index = stack.pop()
                pc += 2
            else:
                raise ValueError(f'Unexpected original index opcode {ext:02X} at {pc:04X}')
        elif op == 0xCC:  # CALL Z,BABB if first status bit0 clear
            if master[pc+1:pc+3] != b'\xBB\xBA':
                raise ValueError('Unexpected original fallback target')
            if z:
                slots[ix_index] = restore(slots[ix_index])[0]
                calls += 1
            pc += 3
        elif op == 0xCD:  # CALL BABB for second car via exchanged IX
            if master[pc+1:pc+3] != b'\xBB\xBA':
                raise ValueError('Unexpected original fallback target')
            slots[ix_index] = restore(slots[ix_index])[0]
            calls += 1
            pc += 3
        elif op == 0xC0:  # RET NZ skips restoring second car
            if not z:
                if stack or pc != 0xB4F9:
                    raise ValueError('Original fallback returned with unexpected stack state')
                return slots[0], slots[1], calls
            pc += 1
        elif op == 0xC9:
            if pc != STOP-1 or stack:
                raise ValueError('Unexpected original fallback return')
            return slots[0], slots[1], calls
        else:
            raise ValueError(f'Unexpected original fallback opcode {op:02X} at {pc:04X}')
        if not START <= pc < STOP:
            raise ValueError(f'Original fallback dispatched outside B4EE-B505: {pc:04X}')
    raise ValueError('Original fallback dispatch instruction budget exceeded')


def verify(master: bytes, cases: int = 50000) -> dict:
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError('Checksum-verified original 1991 arcade master required')
    if sha256(master[START:STOP]).hexdigest()!=STAGE_SHA:
        raise ValueError('Original B4EE stage checksum mismatch')
    if not 0 <= cases <= 200000:
        raise ValueError('Invalid bounded parity test count')
    rng = Random(0xB4EE)
    histogram: dict[int, int] = {0:0, 1:0, 2:0}
    for i in range(cases):
        left,right = bytearray(rng.randbytes(256)),bytearray(rng.randbytes(256))
        flags = i % 4
        left[0x7C] = (left[0x7C] & ~1) | (flags & 1)
        right[0x7C] = (right[0x7C] & ~1) | ((flags >> 1) & 1)
        expected = independent(bytes(left),bytes(right))
        actual = execute_original(master,bytes(left),bytes(right))
        if actual != expected:
            raise AssertionError(f'Original B4EE mismatch case {i}, flags {flags}')
        histogram[actual[2]] += 1
    return {
        'source':'1991 original fixed master Z80 B4EE-B505',
        'stage_sha256':STAGE_SHA,'cases':cases,'mismatches':0,
        'original_two_car_restorations_by_count':histogram,
        'first_car_condition':'restore via BABB iff first slot+7C bit0 clear',
        'second_car_condition':'restore via BABB iff second slot+7C bit0 clear',
        'dependency':'uses separately original-opcode-verified BABB-BB6B restore',
        'scope':'exact branch selection; full damage/impact/gameplay not identified',
    }


def main()->None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('master',type=Path)
    ap.add_argument('--cases',type=int,default=50000)
    args=ap.parse_args()
    print(json.dumps(verify(args.master.read_bytes(),args.cases),indent=2))

if __name__ == '__main__':
    main()
