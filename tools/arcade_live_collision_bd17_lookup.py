#!/usr/bin/env python3
"""Original 1991 arcade collision BD17 pointer and banked-ROM lookup parity.

Authentic master Z80, original signed X-ROM slot0 and REAL MAME PC data:
  BD17: constructed 16-bit HL after X-ROM word+signed addressing
  BD1A: original A loaded from CPU bank-switched ROM at HL
  BE6B: original branch when A < 0x84
  BD1D: otherwise continue original collision calculation

Exact independent arithmetic vs original MAME captured live data. This does
NOT yet prove physical terrain or collision impulses. PRIVATE owner ROM,
X-ROM, source code, memory dump, and tile art are never included in GitHub.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
from pathlib import Path

MASTER_SHA="521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
XROM_SHA="1622d5978ee86aae452ad5289a45ff17785f9a841898a3a33d10c0a35d3ca2cb"
ORIGINAL_MASTER_BANK_BASES=(
    0x02000,0x18000,0x20000,0x28000,0x30000,0x38000,
    0x40000,0x48000,0x50000,0x58000,0x60000,0x68000,
    0x70000,0x78000,0x80000,0x88000
)
CAR_IX=tuple(0xE080+0x100*i for i in range(5))
FIELDS=("frame","pc","ix","iy","hl","a","e978","e731","e73b",
        "e608","e976","e92e","mem_hl")
BRANCHES=("BE6B","BD1D")


def constructed_pointer(e731:int,e73b:int,e978:int,xrom:bytes)->dict:
    """Independent original BD00–BD16 arithmetic, not a copied ROM table.

    Original LD L,0x5A selects 8-bit operand alongside high(E73B).
    Original X-ROM slot0 returns a 16-bit word. Z80 ADD A,A wraps;
    ADD A,L sets a fresh carry; ADC A,H incorporates precisely that carry.
    """
    if (len(xrom)!=0x40000 or not 0<=e731<65536 or not 0<=e73b<65536
            or not 0<=e978<256):
        raise ValueError("Original 16-bit state, E978 byte and 256KiB private X-ROM required")
    input_address=(((e73b>>8)&255)<<8)|0x5A
    xrom_low,xrom_high=xrom[2*input_address:2*input_address+2]
    low_add=(((e731>>8)*2)&255)+xrom_low
    low=low_add&255
    carry=low_add>255
    high=(e978+xrom_high+int(carry))&255
    return {"source_xrom_address":input_address,
            "cpu_pointer":(high<<8)|low,"accumulator_before_read":high}


def read_original_bank(master:bytes,port_f4_shadow:int,address:int)->int:
    """The original MAME banked master CPU window at 2000–9FFF.

    Outside this banked-ROM window, CPU QRAM, palette and RAM mapping must
    be reproduced from the actual MAME hardware driver separately. Reject
    other memory spaces rather than reading the wrong static binary offset.
    """
    if (len(master)!=0x90000 or not 0<=port_f4_shadow<256
            or not 0x2000<=address<0xA000):
        raise ValueError("Unsupported original master ROM bank or CPU window")
    base=ORIGINAL_MASTER_BANK_BASES[port_f4_shadow&15]
    return master[base+address-0x2000]


def parse_row(row:dict[str,str])->dict:
    if not set(FIELDS).issubset(row):
        raise ValueError("Original collision data lookup CSV missing fields")
    try:
        result={"frame":int(row["frame"]),"pc":row["pc"].upper()}
        for key in FIELDS[2:]:
            result[key]=int(row[key],16)
    except (TypeError,ValueError) as exc:
        raise ValueError("Original MAME collision byte/word register malformed") from exc
    if (result["frame"]<=0 or result["pc"] not in ("BD17","BD1A",*BRANCHES)
            or result["ix"] not in CAR_IX):
        raise ValueError("Original collision stage PC, IX or frame differs")
    if any(not 0<=result[k]<256 for k in ("a","e978","e608","e976","e92e","mem_hl")):
        raise ValueError("Original BD17 byte register out of 8-bit range")
    if any(not 0<=result[k]<65536 for k in ("iy","hl","e731","e73b")):
        raise ValueError("Original BD17 16-bit word out of range")
    return result


def audit_rows(rows:list[dict[str,str]],master:bytes,xrom:bytes)->dict:
    """Check actual ORIGINAL MAME BD17→BD1A→(BE6B or BD1D) triplets."""
    if not rows or len(rows)%3:
        raise ValueError("Original live collision map trace has incomplete three-PC sequence")
    if len(master)!=0x90000 or len(xrom)!=0x40000:
        raise ValueError("Original master and X-ROM dimensions invalid")
    parsed=[parse_row(row) for row in rows]
    paths=Counter();banks=Counter();pages=Counter();cars=Counter()
    before_frame=-1
    for index in range(0,len(parsed),3):
        first,second,branch=parsed[index:index+3]
        if ([first["pc"],second["pc"]] != ["BD17","BD1A"]
                or branch["pc"] not in BRANCHES):
            raise ValueError(f"Actual original BD17/BD1A branch instruction sequence differs at {index}")
        if first["frame"]<before_frame:
            raise ValueError("Original collision trace frames are not monotonic")
        before_frame=first["frame"]
        for field in ("frame","ix","iy","hl","e978","e731","e73b",
                      "e608","e976","e92e"):
            if first[field]!=second[field] or first[field]!=branch[field]:
                raise ValueError(f"Original BD17 state changed unexpectedly within one lookup: {field}")
        expected=constructed_pointer(first["e731"],first["e73b"],
                                     first["e978"],xrom)
        ptr=expected["cpu_pointer"]
        if ptr!=first["hl"] or expected["accumulator_before_read"]!=first["a"]:
            raise ValueError(f"Original BD17 X-ROM derived pointer/accumulator mismatch at {index}")
        from_rom=read_original_bank(master,first["e608"],ptr)
        if from_rom!=second["a"] or from_rom!=first["mem_hl"] or from_rom!=branch["a"]:
            raise ValueError(f"Original bank-switched CPU ROM lookup byte mismatch at {index}")
        if branch["pc"]!=("BE6B" if from_rom<0x84 else "BD1D"):
            raise ValueError(f"Original 0x84 collision-data branch mismatch at {index}")
        paths[branch["pc"]]+=1
        banks[first["e608"]&15]+=1
        pages[ptr>>12]+=1
        cars[f'{first["ix"]:04X}']+=1
    return {
        "source":"authentic Indy Heat 1991 rev1 running in MAME 0.264, original master BD17/BD1A",
        "live_pointer_rom_byte_branch_triplets":len(rows)//3,
        "total_original_instruction_hits":len(rows),
        "observed_0x84_branch_targets":dict(sorted(paths.items())),
        "original_master_banks_observed":dict(sorted(banks.items())),
        "pointer_4KiB_pages_observed":dict(sorted(pages.items())),
        "lookups_by_original_car":dict(sorted(cars.items())),
        "mismatches":0,
        "scope":"Original X-ROM pointer maths, selected master ROM byte and threshold branch. "
                "Not a verified surface type/traction/damage/physical impulse model."
    }


def audit_file(csv_path:Path,master_path:Path,xrom_path:Path)->dict:
    master=master_path.read_bytes();xrom=xrom_path.read_bytes()
    if (sha256(master).hexdigest()!=MASTER_SHA or len(master)!=0x90000
            or sha256(xrom).hexdigest()!=XROM_SHA or len(xrom)!=0x40000):
        raise ValueError("Authentic checksum-verified original owner master and X-ROM required")
    with csv_path.open(newline="",encoding="utf-8") as stream:
        reader=csv.DictReader(stream)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise ValueError("Original private MAME debugger CSV header differs")
        report=audit_rows(list(reader),master,xrom)
    report["private_capture_sha256"]=sha256(csv_path.read_bytes()).hexdigest()
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_MAME_trace",type=Path)
    parser.add_argument("private_master",type=Path)
    parser.add_argument("private_xrom",type=Path)
    parser.add_argument("--out",type=Path,
                        default=Path("local/private-runtime/collision_bd17_live_audit.json"))
    args=parser.parse_args()
    report=audit_file(args.private_MAME_trace,args.private_master,args.private_xrom)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
