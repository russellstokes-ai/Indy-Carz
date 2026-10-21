#!/usr/bin/env python3
"""Original 1991 arcade live MAME Z80 7225-7244 motion gate parity.

Consumes PRIVATE original instruction-write trace from
mame_capture_velocity_7225.lua. Checks original E76B prewrite, original
DE input, actual HL and branch against independent integer model.
Public JSON contains only counts and checksum, never original ROM,
private RAM words, track images or unlicensed artwork.
"""
from __future__ import annotations
import argparse,csv,json
from collections import Counter
from hashlib import sha256
from pathlib import Path

from arcade_velocity_sign_gate_7225 import independent

FIELDS=("frame","pc","ix","old_motion","de_input","hl_result",
        "expected","correct","branch")
CAR_POINTERS=tuple(0xE080+i*0x100 for i in range(5))


def audit_rows(rows:list[dict[str,str]])->dict:
    if not rows:raise ValueError("Original live Z80 motion trace empty")
    branches=Counter();cars=Counter()
    first=last=previous=-1
    for i,row in enumerate(rows):
        if not set(FIELDS).issubset(row):
            raise ValueError("Original motion CPU trace CSV missing columns")
        try:
            frame=int(row["frame"])
            pc=int(row["pc"],16)
            ix=int(row["ix"],16)
            old=int(row["old_motion"],16)
            de=int(row["de_input"],16)
            hl=int(row["hl_result"],16)
            scripted=int(row["expected"],16)
            correct=int(row["correct"])
            branch=row["branch"]
        except (TypeError,ValueError) as err:
            raise ValueError(f"Malformed original motion CPU trace row {i}") from err
        if frame<previous or frame<=0:
            raise ValueError("Original motion frame order changed")
        if pc!=0x7241 or ix not in CAR_POINTERS:
            raise ValueError("Original Z80 motion PC or racing car pointer differs")
        if any(not 0<=v<65536 for v in (old,de,hl,scripted)):
            raise ValueError("Original Z80 register has invalid 16-bit value")
        reference=independent(old,de)
        if (reference["stored_e76b"]!=hl or reference["stored_e76b"]!=scripted
                or correct!=1 or reference["branch"]!=branch):
            raise ValueError(f"Original live motion arithmetic mismatch at row {i}")
        if first<0:first=frame
        last=frame;previous=frame
        branches[branch]+=1;cars[f"{ix:04X}"]+=1
    return {
        "source":"original 1991 arcade MAME master Z80 E76B write at 7241",
        "actual_motion_word_writes":len(rows),
        "first_frame":first,"last_frame":last,
        "observed_original_motion_gate_branches":dict(sorted(branches.items())),
        "original_car_ix_write_counts":dict(sorted(cars.items())),
        "original_live_arithmetic_mismatches":0,
        "scope":"Live 16-bit signed motion zero-crossing gate only; acceleration, grip and terrain remain OPEN"
    }


def audit_file(path:Path)->dict:
    with path.open(newline="",encoding="utf-8") as f:
        reader=csv.DictReader(f)
        if not set(FIELDS).issubset(reader.fieldnames or ()):
            raise ValueError("Original motion input CSV header differs")
        report=audit_rows(list(reader))
    h=sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    report["private_trace_sha256"]=h.hexdigest()
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_live_trace",type=Path)
    parser.add_argument("--out",type=Path,
                        default=Path("local/private-runtime/motion_gate_live_audit.json"))
    args=parser.parse_args()
    report=audit_file(args.private_live_trace)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
