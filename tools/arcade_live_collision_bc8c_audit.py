#!/usr/bin/env python3
"""Audit LIVE original MAME master-Z80 BC8C collision retry/rollback states.

Reads ONLY PRIVATE user-owned live debugger CSV; reports branch counts,
original hardware bank transitions, retry values and SHA-256, not original
RAM values, ROM opcode bytes, images or graphics.

Original 1991 0xBC8C→0xBC9E→0xBCA5→0xBCFA follows a fresh entry.
0xBCFA may return to 0xBCA5 for extra attempts; when counter reaches 18
the original 0xBCB2/C468/BCF7 branch restores 11 words and retries.
This captures OBSERVED cases only. If no fallback occurs, do not claim
live parity for that branch; it has separate private original-opcode parity.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path

from arcade_collision_bc8c_retry_restore import (
    CAR_IX, MASTER_HASH, ENTRY_SHA, RETRY_SHA, HELPER_SHA,
    ENTRY_START,ENTRY_STOP,RETRY_START,HELPER_START,HELPER_STOP
)

FIELDS=("frame","pc","ix","iy","e608","e976","e92e","e92c",
        "car_b1","e768","e76a","e76b","e765")
VALID_PCS=("BC8C","BC9E","BCA5","BCFA","BCB2","C468","BCF7")


def parse(row:dict[str,str])->dict:
    if not set(FIELDS).issubset(row):
        raise ValueError("Original arcade BC8C capture is missing fields")
    result={}
    try:
        result["frame"]=int(row["frame"])
        for key in FIELDS[1:]:
            result[key]=row[key].upper() if key=="pc" else int(row[key],16)
    except (TypeError,ValueError) as exc:
        raise ValueError("Malformed original debugger control registers") from exc
    if result["pc"] not in VALID_PCS or result["ix"] not in CAR_IX or result["frame"]<=0:
        raise ValueError("Unexpected original PC, racer slot or frame")
    if any(not 0<=result[k]<256 for k in
           ("e608","e976","e92e","e92c","car_b1","e768","e76a")):
        raise ValueError("Original collision control must contain 8-bit fields")
    if any(not 0<=result[k]<65536 for k in ("iy","e76b","e765")):
        raise ValueError("Original original Z80 word outside unsigned range")
    return result


def audit_rows(source:list[dict[str,str]])->dict:
    if not source:raise ValueError("Original MAME BC8C trace is empty")
    rows=[parse(row) for row in source]
    if rows[0]["pc"]!="BC8C":
        raise ValueError("Original collision trace must start at handler entry")
    counts=Counter()
    car_counts=Counter()
    seen_retries=Counter()
    first,last=rows[0]["frame"],rows[-1]["frame"]
    previous_frame=-1
    valid_follow={
      "BC8C":("BC9E",),"BC9E":("BCA5",),
      "BCA5":("BCFA","BCB2"),"BCB2":("C468",),
      "C468":("BCF7",),"BCF7":("BC9E",),
      "BCFA":("BC8C","BCA5"),
    }
    for i,row in enumerate(rows):
        if row["frame"]<previous_frame:
            raise ValueError("Original collision frames are not monotonic")
        previous_frame=row["frame"]
        pc=row["pc"]
        counts[pc]+=1
        if pc=="BC8C":car_counts[f'{row["ix"]:04X}']+=1
        if pc=="BCA5":seen_retries[row["e92e"]]+=1
        if i+1==len(rows):continue
        next_row=rows[i+1]
        next_pc=next_row["pc"]
        if next_pc not in valid_follow[pc]:
            raise ValueError(f"Original BC8C control-flow ordering invalid at {i}")
        if next_pc!="BC8C" and (
            row["frame"]!=next_row["frame"] or row["ix"]!=next_row["ix"]
        ):
            raise ValueError("Original retry changed frame/car before stage finished")

        if pc=="BC8C":
            expected_bank=(row["e608"]&0xF0)|row["e976"]
            if next_row["e608"]!=expected_bank or next_row["car_b1"]&128:
                raise ValueError("Original BC8C F4 bank setup / RES7 state differs")

        if pc=="BC9E":
            if (next_row["e92e"],next_row["e92c"])!=(0,0):
                raise ValueError("Original BC9E did not clear both retry fields")
            if next_row["e608"]!=row["e608"]:
                raise ValueError("Original retry reset unexpectedly changed bank")

        if pc=="BCA5":
            expected=(row["e92e"]+1)&255
            target="BCFA" if expected<18 else "BCB2"
            if next_pc!=target or next_row["e92e"]!=expected:
                raise ValueError("Original 18-count retry comparison/branch differs")

        if pc=="BCFA" and next_pc=="BCA5":
            if next_row["e92e"]!=row["e92e"]:
                raise ValueError("Original repeat iteration lost its counter")

        if pc=="BCB2" and next_pc=="C468":
            if row["e92e"]!=next_row["e92e"]:
                raise ValueError("Original fallback entered with changed retry counter")

        if pc=="C468" and next_pc=="BCF7":
            if (next_row["e76a"]!=next_row["e768"] or
                next_row["e76b"]!=0xCC00 or next_row["e765"]!=0):
                raise ValueError("Original reset callback C468 state differs")
        if pc=="BCF7" and next_pc=="BC9E" and row["e92e"]!=next_row["e92e"]:
            raise ValueError("Original retry fallback unexpectedly lost counter")
    if rows[-1]["pc"] not in ("BCFA","BC9E"):
        raise ValueError("Original capture ends in an incomplete control-flow branch")
    return {
      "source":"original 1991 arcade running in MAME, master Z80 BC8C–BCF7",
      "observed_frames":[first,last],
      "total_debugger_hits":len(rows),
      "bc8c_entries":counts["BC8C"],
      "bca5_retry_checks":counts["BCA5"],
      "normal_collision_processing_entries":counts["BCFA"],
      "c468_reset_invocations":counts["C468"],
      "original_fallbacks_to_bc9e":counts["BCF7"],
      "original_counter_before_retry":dict(sorted(seen_retries.items())),
      "entries_by_car":dict(sorted(car_counts.items())),
      "mismatches":0,
      "scope":"Observed bank/bit7/counter branches only. BCFA main contact response "
              "and physical collision impulse remain unresolved. Fallback may "
              "have zero LIVE occurrences despite original-opcode validation.",
    }


def audit_file(trace:Path, original_master:Path)->dict:
    master=original_master.read_bytes()
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_HASH:
        raise ValueError("Checksum-verified original arcade master ROM required")
    for lo,hi,digest in (
        (ENTRY_START,0xBCB2,ENTRY_SHA),(RETRY_START,ENTRY_STOP,RETRY_SHA),
        (HELPER_START,HELPER_STOP,HELPER_SHA)):
        if sha256(master[lo:hi]).hexdigest()!=digest:
            raise ValueError(f"Original Z80 source changed at {lo:04X}")
    with trace.open(newline="",encoding="utf-8") as fh:
        reader=csv.DictReader(fh)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise ValueError("Original debugger capture CSV header missing fields")
        report=audit_rows(list(reader))
    report["private_trace_sha256"]=sha256(trace.read_bytes()).hexdigest()
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_capture",type=Path)
    parser.add_argument("private_master",type=Path)
    parser.add_argument("--out",type=Path,
                        default=Path("local/private-runtime/collision_bc8c_live_audit.json"))
    args=parser.parse_args()
    report=audit_file(args.private_capture,args.private_master)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
