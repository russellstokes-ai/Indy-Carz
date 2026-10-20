#!/usr/bin/env python3
"""Interpret PRIVATE MAME callback and race-selector write traces.

Input comes from tools/mame_capture_callback_writes.lua. This is an offline
reporting utility; it DOES NOT execute the arcade game, prove callback entry
execution, or identify unknown gameplay semantics. No original ROM needed.
"""
from __future__ import annotations
import argparse
import collections
import csv
import io
import json
from pathlib import Path

HEADERS = ["frame", "kind", "address", "value", "master_pc"]
GLOBAL = {0xE699: "course_index", 0xE69B: "round_counter", 0xE67D: "first_phase_gate"}


def describe_address(address: int) -> tuple[int, str, int] | None:
    if not 0xE000 <= address < 0xE600:
        return None
    slot = (address - 0xE000) // 0x100
    offset = (address - 0xE000) % 0x100
    if offset in (0x94, 0x95):
        return slot, "first", offset - 0x94
    if offset in (0x96, 0x97):
        return slot, "second", offset - 0x96
    return None


def analyse(trace: str) -> dict:
    reader = csv.DictReader(io.StringIO(trace))
    if reader.fieldnames != HEADERS:
        raise ValueError("Not an original Indy Carz callback write CSV")
    current: dict[int, int] = {}
    previous_pointers: dict[tuple[int, str], int] = {}
    seen_first: dict[tuple[int, str], int] = {}
    transitions: list[dict] = []
    global_events: list[dict] = []
    raw_callbacks = 0
    frames = collections.defaultdict(list)
    previous_frame = -1
    for row in reader:
        try:
            frame = int(row["frame"])
            address = int(row["address"], 16)
            value = int(row["value"], 16)
            pc = int(row["master_pc"], 16)
            kind = row["kind"]
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("Malformed callback-write trace entry") from exc
        if frame < previous_frame or frame < 0:
            raise ValueError("Frame index went backwards")
        if not (0 <= value <= 255 and 0 <= pc <= 65535):
            raise ValueError("Invalid master Z80 byte or PC")
        if kind not in ("snapshot", "snapshot_global", "callback_write", "global_write"):
            raise ValueError("Unknown callback-write trace event type")
        previous_frame = frame
        frames[frame].append((address, value, pc, kind))
        if len(frames) > 50001:
            raise ValueError("Frame summary limit exceeded")

    for frame in sorted(frames):
        latest_pc: dict[tuple[int, str], int] = {}
        for address, value, pc, kind in frames[frame]:
            if address in GLOBAL:
                previous = current.get(address)
                if kind == "global_write" and previous != value:
                    global_events.append({
                        "frame": frame, "field": GLOBAL[address],
                        "old": previous, "new": value,
                        "pc": f"{pc:04X}" if pc != 0xFFFF else None,
                    })
                current[address] = value
                continue
            parsed = describe_address(address)
            if parsed is None or kind not in ("snapshot", "callback_write"):
                raise ValueError(f"Unexpected callback trace address {address:04X}")
            if kind == "callback_write":
                raw_callbacks += 1
            slot, phase, byte_idx = parsed
            latest_pc[(slot, phase)] = pc
            current[address] = value

        # Commit state at frame boundary to avoid phantom intermediate
        # targets while Z80 updates high and low callback bytes sequentially.
        for slot in range(6):
            base = 0xE000 + slot*0x100
            for phase, offset in (("first", 0x94), ("second", 0x96)):
                low, high = base+offset, base+offset+1
                if low not in current or high not in current:
                    continue
                value = current[low] | current[high] << 8
                key = (slot, phase)
                old = previous_pointers.get(key)
                if old is not None and old != value:
                    source = latest_pc.get(key)
                    transitions.append({
                        "frame": frame, "car_slot": slot, "phase": phase,
                        "previous_pc": f"{old:04X}", "new_pc": f"{value:04X}",
                        "last_writer_pc": f"{source:04X}" if source not in (None, 0xFFFF) else None,
                    })
                previous_pointers[key] = value

    return {
        "source": "private original arcade MAME callback write-tap CSV",
        "observed_frames": len(frames),
        "callback_byte_writes": raw_callbacks,
        "callback_pointer_transitions": transitions,
        "global_counter_changes": global_events,
        "last_observed_callback_pcs": [
            {"car_slot": slot, "phase": phase,
             "callback_pc": f"{value:04X}"}
            for (slot, phase), value in sorted(previous_pointers.items())
        ],
        "scope": "End-of-frame memory observations; transient same-frame pointers may be missed; bank context unverified",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace", type=Path)
    p.add_argument("--out", type=Path,
                   default=Path("local/engine-extraction/runtime/callback_write_summary.json"))
    a = p.parse_args()
    report = analyse(a.trace.read_text(encoding="utf-8"))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Observed callback transitions:", len(report["callback_pointer_transitions"]))
    print("Counter events:", len(report["global_counter_changes"]))
    print("MAME runtime execution/actual gameplay semantics cannot be inferred from this report alone.")


if __name__ == "__main__":
    main()
