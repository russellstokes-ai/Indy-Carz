#!/usr/bin/env python3
"""Recover Indy Heat's exact car-contact coordinate translation primitives.

Master Z80 fixed ROM B985-BA1F (IX) and BA20-BABA (IY) apply a 16-bit
translation to ten 16-bit working coordinates of one selected car:
- first five pairs at record +00,+02,+04,+06,+08 receive BC
- second five at record +0A,+0C,+0E,+10,+12 receive DE
- status record+7C bit6 is set.

Both original functions also have *nonlocal scheduler calls* to $1689 when
either high translation byte is in the inclusive range 05..FA. Such cases
are explicitly marked UNRESOLVED; we do not assume the call returns normally.
No original binary/assets are included or committed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import random

MASTER_SHA = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
STAGE_HASHES = {
    "IX": ("B985", "400755ca6f3478bda5e4e765c420032c4fd59d94da55b0d5ebe52836eb008fb8"),
    "IY": ("BA20", "d6aed40a17b98f3d5d3fdd14c76f4137f13b927b3fa0d68c1e44893de8c205cf"),
}
PROLOGUE = bytes.fromhex("78 fe 05 38 05 fe fb dc 89 16 7a fe 05 38 05 fe fb dc 89 16")
BYTES_PER_RECORD = 0x100
PREFIX = {"IX": 0xDD, "IY": 0xFD}


def stage_template(prefix: int) -> bytes:
    """Generate an instruction-shaped checksum probe, not original source."""
    if prefix not in (0xDD, 0xFD):
        raise ValueError("Expected IX or IY prefix")
    seq = bytearray(PROLOGUE)
    for n in range(10):
        low = 0x80 + 2*n
        high = low + 1
        add = 0x09 if n < 5 else 0x19
        seq += bytes([prefix,0x66,high,prefix,0x6E,low,add,
                      prefix,0x74,high,prefix,0x75,low])
    seq += bytes([prefix,0xCB,0xFC,0xF6,0xC9])
    return bytes(seq)


def verify_program(master: bytes) -> list[dict]:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_SHA:
        raise ValueError("Verified private 1991 Indy Heat original master ROM required")
    verified = []
    for register, (start_hex, sha) in STAGE_HASHES.items():
        start = int(start_hex,16)
        observed = master[start:start+155]
        if observed != stage_template(PREFIX[register]):
            raise ValueError(f"Original {register} contact translation opcodes differ")
        if hashlib.sha256(observed).hexdigest() != sha:
            raise ValueError(f"Original {register} contact translation checksum differs")
        verified.append({"register": register, "start": start_hex,
                         "end_inclusive": f"{start+154:04X}", "bytes":len(observed),
                         "source_sha256": sha})
    return verified


def has_unresolved_scheduler_transfer(bc: int, de: int) -> bool:
    if not (0 <= bc <= 65535 and 0 <= de <= 65535):
        raise ValueError("Original translation operands must be 16-bit values")
    return any(5 <= (word >> 8) <= 250 for word in (bc,de))


def independent_translation(record: bytes, bc: int, de: int) -> bytes | None:
    """Bit-exact translation for paths NOT branching to external $1689."""
    if len(record) != BYTES_PER_RECORD:
        raise ValueError("Expected one complete 256-byte original car state slot")
    if has_unresolved_scheduler_transfer(bc,de):
        return None
    result = bytearray(record)
    for n in range(10):
        offset = n*2
        before = int.from_bytes(result[offset:offset+2],"little")
        delta = bc if n < 5 else de
        result[offset:offset+2] = ((before+delta)&0xffff).to_bytes(2,"little")
    result[0x7C] |= 0x40
    return bytes(result)


def original_bounded_stage(master: bytes, record: bytes, bc: int,
                           de: int, register: str) -> bytes | None:
    """Execute each instruction in authentic IX/IY 155-byte routine.

    Refuse unknown instructions. Branches to $1689 return None so this
    bounded interpreter cannot silently misrepresent the nonlocal scheduler.
    """
    if register not in PREFIX or len(record) != BYTES_PER_RECORD:
        raise ValueError("Bad indexed register or record size")
    if not (0 <= bc <= 65535 and 0 <= de <= 65535):
        raise ValueError("Original translation operands must be 16-bit")
    if len(master) != 0x90000:
        raise ValueError("Original master ROM region expected")
    start = int(STAGE_HASHES[register][0],16)
    if master[start:start+155] != stage_template(PREFIX[register]):
        raise ValueError("Original indexed Z80 routine differs")
    pc=start
    state=bytearray(record)
    b,c = bc>>8, bc&255
    d,e = de>>8, de&255
    a=h=l=0
    carry=False
    for _ in range(200):
        opcode=master[pc]
        if opcode==0x78:  # LD A,B
            a=b; pc+=1
        elif opcode==0x7A:  # LD A,D
            a=d; pc+=1
        elif opcode==0xFE:  # CP immediate
            carry=a < master[pc+1]
            pc+=2
        elif opcode==0x38:  # JR C
            jump=master[pc+1]
            if jump>=128:jump-=256
            pc=pc+2+jump if carry else pc+2
        elif opcode==0xDC:  # CALL C,1689
            if master[pc+1:pc+3]!=bytes.fromhex("8916"):
                raise ValueError("Unexpected original scheduler call")
            if carry:return None
            pc+=3
        elif opcode==PREFIX[register]:
            op2=master[pc+1]
            if op2 in (0x66,0x6E,0x74,0x75):
                address = ((master[pc+2]-0x80)&255)
                if address>0x13:raise ValueError("Unexpected car coordinate index")
                if op2==0x66:h=state[address]
                if op2==0x6E:l=state[address]
                if op2==0x74:state[address]=h
                if op2==0x75:state[address]=l
                pc+=3
            elif master[pc+1:pc+4]==bytes.fromhex("cbfcf6"):
                state[0x7C]|=0x40;pc+=4
            else:
                raise ValueError(f"Unsupported indexed original opcode at {pc:04X}")
        elif opcode in (0x09,0x19):  # ADD HL,BC or HL,DE
            value = (h<<8|l) + (bc if opcode==0x09 else de)
            h,l = (value>>8)&255,value&255
            pc+=1
        elif opcode==0xC9:  # RET
            if pc!=start+154:raise ValueError("Unexpected original return")
            return bytes(state)
        else:raise ValueError(f"Unknown original Z80 opcode {opcode:02X} at {pc:04X}")
    raise ValueError("Original translation routine exceeded bounded budget")


def verify(master: bytes, cases: int = 8000) -> dict:
    stages=verify_program(master)
    if not 0<=cases<=100000:raise ValueError("Invalid verification case count")
    rng=random.Random(0xB985BA20)
    checked=0
    safe_hi=(0,1,2,3,4,251,252,253,254,255)
    for index in range(cases):
        bc=(rng.choice(safe_hi)<<8)|rng.randrange(256)
        de=(rng.choice(safe_hi)<<8)|rng.randrange(256)
        original=rng.randbytes(256)
        expected=independent_translation(original,bc,de)
        for register in PREFIX:
            actual=original_bounded_stage(master,original,bc,de,register)
            if actual!=expected:
                raise AssertionError(f"Arcade car translation differs, {register}, case {index}")
            checked+=1
    # Cover all 256x256 combinations of the high bytes' scheduler gate.
    gate_cases=0
    for high_b in range(256):
        for high_d in range(256):
            b=high_b<<8
            d=high_d<<8
            independent=(5<=high_b<=250 or 5<=high_d<=250)
            if has_unresolved_scheduler_transfer(b,d)!=independent:
                raise AssertionError("Original byte threshold classification differs")
            gate_cases+=1
    return {
        "game":"1991 Indy Heat arcade",
        "source_routines": stages,
        "actual_state_translations_verified":checked,
        "external_scheduler_gate_classifications":gate_cases,
        "mismatches":0,
        "state_word_groups": {
            "first_five_offsets":["00","02","04","06","08"],
            "first_group_16bit_displacement":"BC",
            "second_five_offsets":["0A","0C","0E","10","12"],
            "second_group_16bit_displacement":"DE"
        },
        "car_status_bit_on_return":"record+7C, SET 6",
        "external_call":"CALL C,1689 when 5 <= B or D <= 250",
        "limitations":"Scheduler transfer at 1689 and complete contact response still unresolved; these translate saved centre and corners, not proven velocity impulses"
    }


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("master",type=Path)
    p.add_argument("--cases",type=int,default=8000)
    p.add_argument("--out",type=Path,default=Path("local/recovery/contact_geometry_translation.json"))
    a=p.parse_args()
    result=verify(a.master.read_bytes(),a.cases)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
