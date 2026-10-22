#!/usr/bin/env python3
"""Audit live MAME Indy Heat championship RAM and four-bank QRAM snapshots.

Reads PRIVATE user-supplied original arcade runtime captures made with
tools/mame_capture_live_arcade.lua. Public JSON report contains only frame
boundaries, callback addresses, SHA-256 fingerprints and tile counts,
never proprietary graphic/pixel/tile data or ROM code.

A 15-round sequence is genuine MAME execution evidence, NOT evidence of
completed driving physics, track-wall collision masks or full game parity.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from hashlib import sha256
import json
from pathlib import Path
import re
import struct

MAGIC = b"ICR1"
BASE, RAM_SIZE, STRIDE = 0xE000, 0xA00, 0xA04
ROUND_ORDER = (13,12,1,3,7,8,4,2,5,11,0,6,9,10,1)
SCREEN = (320,240)
QRAM_BYTES = 0x10000
QRAM_NAME = re.compile(r"qram_\d+_f(\d+)_c(\d+)_r(\d+)\.bin$")
CAR_BASES = (0xE080,0xE180,0xE280,0xE380,0xE480,0xE580)

def scan_ram(path: Path) -> dict:
    """Stream authentic original MAME RAM records, including sparse captures."""
    if not path.is_file():
        raise ValueError("Original private master RAM capture not found")
    transitions = []
    callback_counts = Counter()
    sample_count = 0
    previous_frame = -1
    previous_state = None
    interval_hist = Counter()
    digest = sha256()
    with path.open("rb") as fh:
        header = fh.read(12)
        if len(header) != 12 or header[:4] != MAGIC:
            raise ValueError("Invalid original capture magic/header")
        if struct.unpack("<II",header[4:]) != (BASE,RAM_SIZE):
            raise ValueError("Unrecognised original arcade master RAM range")
        digest.update(header)
        while True:
            record = fh.read(STRIDE)
            if not record: break
            if len(record) != STRIDE:
                raise ValueError("Truncated original RAM record")
            digest.update(record)
            frame = struct.unpack_from("<I", record)[0]
            if frame <= previous_frame:
                raise ValueError("Original frame numbers not strictly increasing")
            if previous_frame >= 0:
                interval_hist[frame-previous_frame] += 1
            previous_frame = frame
            ram = record[4:]
            course, round_index = ram[0x699],ram[0x69B]
            callbacks = tuple(ram[base-BASE+0x14] |
                              (ram[base-BASE+0x15]<<8) for base in CAR_BASES[:3])
            state = (round_index, course)
            if state != previous_state:
                transitions.append({
                    "frame":frame,"round":round_index,"course":course,
                    "e603":ram[0x603],
                    "callbacks":[f"{v:04X}" for v in callbacks],
                })
                previous_state = state
            callback_counts[f"{callbacks[0]:04X}/{callbacks[1]:04X}/{callbacks[2]:04X}"] += 1
            sample_count += 1
    if not sample_count:
        raise ValueError("Original master RAM capture contains zero frames")
    return {
        "frame_samples":sample_count,
        "last_frame":previous_frame,
        "sample_stride_histogram":dict(sorted(interval_hist.items())),
        "sha256":digest.hexdigest(),
        "transitions":transitions,
        "most_common_three_racer_callbacks":callback_counts.most_common(12),
    }


def original_first_championship(transitions: list[dict]) -> tuple[list[dict], int|None]:
    """Ignore original pre-coin E699=00, return the first *real* race cycle.

    Only start when the original software selects round0/course13.
    The second time round0/course13 appears marks the first complete
    15-event cycle ending. Return None if the second cycle is not observed.
    """
    first = None
    for index,t in enumerate(transitions):
        if (t["round"],t["course"]) == (0,ROUND_ORDER[0]):
            first=index
            break
    if first is None: return [],None
    end=None
    for index in range(first+1,len(transitions)):
        if (transitions[index]["round"],transitions[index]["course"]) == (0,ROUND_ORDER[0]):
            end=transitions[index]["frame"]
            break
    sequence=transitions[first: (index if end is not None else len(transitions))]
    return sequence,end


def tile_statistics(qram: bytes) -> dict:
    """Original MAME ataxx_scan / get_tile_info layout, not image contents."""
    if len(qram) != QRAM_BYTES:
        raise ValueError("Original four bank QRAM must be 65,536 bytes")
    codes=set()
    for y in range(128):
        row=((y & 0x3F)<<8)|((y & 0x40)<<9)
        for x in range(256):
            p=row+x
            code=qram[p]|((qram[0x4000|p]&0x7F)<<8)
            if code>=16384:
                raise ValueError("Original 14-bit tile code outside 16,384 graphics tiles")
            codes.add(code)
    return {"unique_tile_codes":len(codes),"maximum_tile_code":max(codes),
            "tile_grid":[256,128],"full_qram_bytes":len(qram)}


def inspect_qram(directory: Path, index_path: Path,
                 sequence: list[dict],cycle_end: int|None) -> dict:
    """Choose original live-race 2EAF callbacks per round when available."""
    if not index_path.is_file():raise ValueError("Original capture index CSV missing")
    with index_path.open(newline="",encoding="utf-8") as fh:
        reader=csv.DictReader(fh)
        required={"frame","course","round","callback0","callback1","callback2","qram_file"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Original capture index columns incomplete")
        rows=list(reader)
    last=-1
    candidates=defaultdict(list)
    for row in rows:
        try:
            frame,course,rnd=int(row["frame"]),int(row["course"]),int(row["round"])
        except (TypeError,ValueError) as exc:
            raise ValueError("Invalid original capture index frame/course/round") from exc
        if frame<=last:raise ValueError("Original capture index frames must strictly increase")
        last=frame
        name=row["qram_file"]
        if not name:continue
        if name!=Path(name).name or not QRAM_NAME.fullmatch(name):
            raise ValueError("Invalid/path-traversal original QRAM file name")
        match=QRAM_NAME.fullmatch(name)
        if (int(match[1]),int(match[2]),int(match[3]))!=(frame,course,rnd):
            raise ValueError("QRAM filename does not match observed original course/round")
        if cycle_end is not None and frame>=cycle_end:continue
        candidates[(rnd,course)].append((frame,row))
    results=[]
    for event in sequence:
        rnd,course=event["round"],event["course"]
        if rnd<0 or rnd>=len(ROUND_ORDER) or course!=ROUND_ORDER[rnd]:
            raise ValueError("Original course/index order differs from authenticated ROM")
        all_candidates=[(f,r) for f,r in candidates[(rnd,course)] if f>=event["frame"]]
        if not all_candidates:
            results.append({"round":rnd,"course":course,"capture_available":False})
            continue
        active=[(f,r) for f,r in all_candidates
                if all(r[f"callback{i}"].upper()=="2EAF" for i in range(3))]
        frame,row=(active or all_candidates)[len(active or all_candidates)//2]
        path=directory/row["qram_file"]
        if not path.is_file():raise ValueError(f"Missing original QRAM file {path.name}")
        data=path.read_bytes()
        statistics=tile_statistics(data)
        results.append({
            "round":rnd,"course":course,"frame":frame,
            "capture_available":True,
            "all_three_active_callback":bool(active),
            "qram_sha256":sha256(data).hexdigest(),
            "capture_filename":path.name,
            **statistics,
        })
    return {
        "original_qram_snapshots_for_first_championship":sum(x["capture_available"] for x in results),
        "all_fourteen_course_indices_seen":len({x["course"] for x in results if x["capture_available"]})==14,
        "samples":results,
    }


def analyse(directory: Path) -> dict:
    master=scan_ram(directory/"master_ram_frames.bin")
    sequence,end=original_first_championship(master["transitions"])
    expected=list(ROUND_ORDER)
    observed=[x["course"] for x in sequence]
    verified=(len(observed)==15 and observed==expected and end is not None)
    qram=inspect_qram(directory,directory/"capture_index.csv",sequence,end)
    return {
        "source":"live original 1991 arcade Indy Heat rev1 running in MAME",
        "complete_first_fifteen_race_sequence":verified,
        "original_expected_course_order":expected,
        "observed_course_order":observed,
        "observed_start_frames":[x["frame"] for x in sequence],
        "first_cycle_ended_at_frame":end,
        "master_ram":{k:v for k,v in master.items() if k!="transitions"},
        "all_observed_transitions":master["transitions"],
        "qram":qram,
        "limitations":[
            "QRAM data are original game-derived bytes and stay PRIVATE",
            "Original screenshot and pixel data are not emitted in this report",
            "A tile memory snapshot does not prove original terrain collision masks",
            "Original AI handling, circuit boundaries, pit regions and emulator/game timing need further trace parity",
        ],
    }


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_dir",type=Path)
    parser.add_argument("--out",type=Path,default=Path("local/engine-extraction/runtime/live_audit.json"))
    args=parser.parse_args()
    report=analyse(args.capture_dir)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("Original arcade RAM frames:",report["master_ram"]["frame_samples"])
    print("Whole championship live-verified:",report["complete_first_fifteen_race_sequence"])
    print("Unique original circuits with QRAM snapshots:",len({
        r["course"] for r in report["qram"]["samples"] if r["capture_available"]}))
    print("Public report hashes/metadata only. Raw QRAM, original art and RAM stay private.")

if __name__=="__main__":
    main()
