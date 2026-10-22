#!/usr/bin/env python3
"""Audit real MAME 714E/71C8 driving B/C and outgoing 7124 carry.

PRIVATE original rev1 arcade master SHA-256 authenticated. Input is a
private read-only original-Z80 debugger trace produced by
mame_capture_drive_714e_bc.lua. Original ROM/table bytes and actual
car-memory snapshots are never copied into a public GitHub report.

Only entry/exit pairs which actually return through 71C8 are checked.
A direct 714E -> 7315 original bypass needs a separate live breakpoint;
this parser never invents an exit for an unpaired entry.
"""
from __future__ import annotations
import argparse,json,re
from collections import Counter
from hashlib import sha256
from pathlib import Path
from arcade_drive_7124_carry_projection import independent as projection
from arcade_drive_714e_control_selector import independent as control

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
REQUIRED=("IX","AF","E76D","E76F","E76B","E768","E769","E933",
          "IDX0","IDX1","TABLE","E76C")
PATTERN=re.compile(r"([A-Z0-9]+)=([0-9A-F]+)")
CAR_IX=tuple(0xE080+0x100*i for i in range(5))


def _entry(line:str)->tuple[int,str,dict]:
    parts=line.strip().split(",",2)
    if len(parts)!=3 or parts[1]!="LINE":
        raise ValueError("Unexpected original MAME trace row format")
    try:frame=int(parts[0])
    except ValueError as exc:
        raise ValueError("Invalid original MAME frame") from exc
    if frame<=0:raise ValueError("Invalid original MAME frame")
    tag=parts[2].split(",",1)[0]
    if tag not in ("SE714E","SE71C8"):
        raise ValueError("Unexpected original Z80 breakpoint")
    fields=dict((k,int(v,16)) for k,v in PATTERN.findall(parts[2]))
    expected=REQUIRED if tag=="SE714E" else ("IX","AF","BC")
    if not all(name in fields for name in expected):
        raise ValueError("Original debugger record lacks required register")
    if fields["IX"] not in CAR_IX:
        raise ValueError("Unexpected original car index")
    return frame,tag,fields


def audit_rows(rows:list[str],master:bytes)->dict:
    if not rows or len(rows)%2:
        raise ValueError("Require complete original 714E/71C8 entry-exit pairs")
    if len(master)!=0x90000:
        raise ValueError("Authenticated original master ROM length required")
    hist=Counter();car_counts=Counter();first=last=None
    prior_frame=-1
    for i in range(0,len(rows),2):
        start_frame,first_tag,a=_entry(rows[i])
        exit_frame,second_tag,b=_entry(rows[i+1])
        if first_tag!="SE714E" or second_tag!="SE71C8":
            raise ValueError("Original 714E→71C8 debugger pair order incorrect")
        if exit_frame!=start_frame or a["IX"]!=b["IX"] or start_frame<prior_frame:
            raise ValueError("Original debugger frame or car pairing incorrect")
        if any(not 0<=a[k]<65536 for k in
               ("E76D","E76F","E76B","E769","E933","TABLE","AF")):
            raise ValueError("Original word register outside 16-bit range")
        if any(not 0<=a[k]<256 for k in
               ("E768","IDX0","IDX1","E76C")):
            raise ValueError("Original byte register outside 8-bit range")
        if (a["E76B"]>>8)!=a["E76C"]:
            raise ValueError("Original E76C high motion byte inconsistent")
        source=projection(a["E768"],a["E769"],a["E76B"])
        if source["e933"]!=a["E933"] or source["carry"]!=(a["AF"]&1):
            raise ValueError(f"Original 7124 projection or inherited carry mismatch pair {i//2}")
        table_pointer=a["TABLE"]
        if not 0x2000<=table_pointer<=0x9F00:
            raise ValueError("Original control-table pointer is not in verified bank0 ROM")
        table=master[table_pointer:table_pointer+256]
        if len(table)!=256:raise ValueError("Original source-control memory truncated")
        # The selection helper originally accepted 257 bytes for a
        # conservative extra boundary byte; it reads only offsets
        # 0..255. Supply one additional adjoining byte for that API.
        window=master[table_pointer:table_pointer+257]
        predicted=control(a["E76D"],a["E76F"],a["IDX0"],a["IDX1"],
                          a["E76C"],window,0,0,source["carry"])
        if predicted["next_pc"]!=0x71C8:
            raise ValueError("Original direct 7315 bypass was not paired with its own exit")
        if b["BC"]!=((predicted["b"]<<8)|predicted["c"]):
            raise ValueError(f"Original real-race control B/C differs pair {i//2}")
        hist["carry_1" if source["carry"] else "carry_0"]+=1
        hist[predicted["path"]]+=1
        hist["direction_override"]+=predicted["overridden"]
        car_counts[f"{a['IX']:04X}"]+=1
        if first is None:first=start_frame
        last=start_frame;prior_frame=start_frame
    return {
        "source":"authentic original 1991 Indy Heat rev1 MAME master Z80 714E/71C8",
        "paired_original_cpu_events":len(rows)//2,
        "first_frame":first,"last_frame":last,
        "verified_motion_carry_1":hist["carry_1"],
        "verified_motion_carry_0":hist["carry_0"],
        "original_control_paths":{k:hist[k] for k in
            ("direct_6e","direct_6f","matching_indices","rotated_blend")},
        "original_direction_override":hist["direction_override"],
        "per_car_counts":dict(sorted(car_counts.items())),
        "original_BC_output_mismatches":0,
        "original_7124_projection_carry_mismatches":0,
        "limits":"These live entries all exited at 71C8. Original bypass to 7315, physical acceleration/surface and full frame scheduling are not proven here."
    }


def audit_file(trace:Path,master_path:Path)->dict:
    master=master_path.read_bytes()
    if len(master)!=0x90000 or sha256(master).hexdigest()!=MASTER_SHA:
        raise ValueError("Authentic private original master ROM required")
    lines=trace.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0]!="frame,marker,values":
        raise ValueError("Original MAME private capture header differs")
    report=audit_rows(lines[1:],master)
    report["private_trace_sha256"]=sha256(trace.read_bytes()).hexdigest()
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_original_trace",type=Path)
    p.add_argument("private_master",type=Path)
    p.add_argument("--out",type=Path,
                   default=Path("local/private-runtime/original_714e_live_audit.json"))
    a=p.parse_args()
    report=audit_file(a.private_original_trace,a.private_master)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
