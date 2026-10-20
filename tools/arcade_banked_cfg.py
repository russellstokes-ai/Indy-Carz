#!/usr/bin/env python3
"""Recover a conservative Indy Heat arcade Z80 cross-bank static call graph.

Uses only verified local/private MAME-rotated CPU memory. Produces *candidate*
reachability/branch/port maps, not game source or dynamic instruction traces.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
from pathlib import Path

MASTER_HASH = "521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7"
SLAVE_HASH = "e9afaa243befc45c4d91a110ae210bd6a051e5beef61ae4d045f4d6fa6b426cd"
MASTER_BANKS = (0x02000, 0x18000, 0x20000, 0x28000, 0x30000, 0x38000,
                0x40000, 0x48000, 0x50000, 0x58000, 0x60000, 0x68000,
                0x70000, 0x78000, 0x80000, 0x88000)
FAR_WRAPPERS = {0x145F: 2, 0x1490: 3, 0x14C1: 4}


def instruction(mem: bytes, pc: int) -> tuple[int, str, int | None, int | None]:
    """Decode instruction LENGTH and control-flow class for standard Z80.

    Includes DD/FD, CB, indexed CB, ED and undocumented prefix cases.
    Cannot by itself distinguish game data from executed machine code.
    """
    start, indexed = pc, False
    for _ in range(16):
        if mem[pc] not in (0xDD, 0xFD):
            break
        indexed = True
        pc += 1
        if pc >= len(mem):
            raise IndexError("Truncated prefix")
    else:
        raise ValueError("Too many instruction prefixes")
    op = mem[pc]
    pc += 1
    x, y, z, q, p = op >> 6, (op >> 3) & 7, op & 7, (op >> 3) & 1, ((op >> 3) & 7) >> 1
    kind, target, port, immediate = "step", None, None, 0
    if op == 0xCB:
        pc += 2 if indexed else 1
    elif op == 0xED:
        ext = mem[pc]
        pc += 1
        if ext in (0x43, 0x4B, 0x53, 0x5B, 0x63, 0x6B, 0x73, 0x7B):
            pc += 2
        if ext in (0x45, 0x4D, 0x55, 0x5D, 0x65, 0x6D, 0x75, 0x7D):
            kind = "ret"
    else:
        if x == 0:
            if z == 0 and y >= 2:
                immediate = 1
                kind = "jump" if y == 3 else "condjump"
                displacement = mem[pc]
                target = (pc + 1 + (displacement - 256 if displacement >= 128 else displacement)) & 0xffff
            if z == 1 and q == 0:
                immediate = 2
            if z == 2 and p >= 2:
                immediate = 2
            if z in (4, 5, 6) and y == 6 and indexed:
                immediate += 1
            if z == 6:
                immediate += 1
        elif x == 1:
            if op == 0x76:
                kind = "stop"
            elif indexed and (y == 6 or z == 6):
                immediate += 1
        elif x == 2:
            if indexed and z == 6:
                immediate += 1
        elif x == 3:
            if z == 0:
                kind = "condret"
            if z == 1 and op in (0xC9, 0xE9):
                kind = "ret" if op == 0xC9 else "indirect"
            if z == 2:
                immediate, kind = 2, "condjump"
            if z == 3:
                if y == 0:
                    immediate, kind = 2, "jump"
                if y in (2, 3):
                    immediate, port = 1, mem[pc]
            if z == 4:
                immediate, kind = 2, "condcall"
            if z == 5 and q == 1 and p == 0:
                immediate, kind = 2, "call"
            if z == 6:
                immediate = 1
            if z == 7:
                kind, target = "call", y * 8
        if immediate == 2 and kind in ("jump", "condjump", "call", "condcall") and target is None:
            target = mem[pc] | (mem[pc + 1] << 8)
        pc += immediate
    if pc > len(mem):
        raise IndexError("Truncated instruction")
    return pc - start, kind, target, port


def bank_window(region: bytes, cpu: str, selector: int) -> bytes:
    if cpu == "master":
        offset = MASTER_BANKS[selector]
    else:
        n = selector & 15
        offset = (0x2000 if n == 0 else
                  0x10000 * n + 0x8000 * ((selector >> 4) & 1)
                  + (0x100000 * ((selector >> 5) & 1) if len(region) > 0x100000 else 0))
    if offset + 0x8000 > len(region):
        raise ValueError("Bank unavailable")
    mem = bytearray(region[:0xe000])
    mem[0x2000:0xa000] = region[offset:offset + 0x8000]
    return bytes(mem)


def graph(region: bytes, cpu: str) -> dict:
    if cpu == "master":
        windows = {i: bank_window(region, cpu, i) for i in range(16)}
        seeds = [(0, pc) for pc in (0, 0x38, 0x66, 0x83D5, 0x0C4A, 0x0D6A,
                                     0x6793, 0x7027, 0x71D9)]
    else:
        windows = {}
        for i in range(32):
            try:
                windows[i] = bank_window(region, cpu, i)
            except ValueError:
                continue
        seeds = [(0, pc) for pc in (0, 0x38, 0x66, 0xA9)]
    todo, visited = seeds[:], set()
    coverage, far_edges, direct_edges, io = collections.defaultdict(set), set(), set(), collections.defaultdict(set)
    while todo and len(visited) < 350000:
        bank, pc = todo.pop()
        if bank not in windows or not 0 <= pc < 0xa000 or (bank, pc) in visited:
            continue
        mem = windows[bank]
        try:
            length, kind, target, port = instruction(mem, pc)
        except (IndexError, ValueError):
            continue
        if not 0 < length <= 16 or pc + length > 0xa000:
            continue
        visited.add((bank, pc))
        if pc >= 0x2000:
            coverage[bank].update(range(pc, pc + length))
        if port is not None:
            io[f"{port:02X}"].add((bank, pc))
        if cpu == "master" and kind == "call" and target in FAR_WRAPPERS and pc + length + 2 <= 0xa000:
            dst = mem[pc + length] | (mem[pc + length + 1] << 8)
            if 0x2000 <= dst < 0xa000:
                destination_bank = FAR_WRAPPERS[target]
                far_edges.add((bank, pc, destination_bank, dst))
                todo.extend([(destination_bank, dst), (bank, pc + length + 2)])
                continue
        if target is not None and 0 <= target < 0xa000:
            direct_edges.add((bank, pc, bank, target, kind))
            todo.append((bank, target))
        if kind not in ("jump", "ret", "stop", "indirect") and pc + length < 0xa000:
            todo.append((bank, pc + length))
    return {
        "cpu": cpu,
        "reachable_instruction_contexts": len(visited),
        "candidate_banked_code_bytes": {str(b): len(coverage[b]) for b in sorted(windows)},
        "far_call_edges": [
            {"from_bank": a, "from_pc": f"{pc:04X}", "to_bank": b, "to_pc": f"{dst:04X}"}
            for a, pc, b, dst in sorted(far_edges)
        ],
        "direct_branches_calls": len(direct_edges),
        "io_sites": {
            port: [f"B{b:02d}:{pc:04X}" for b, pc in sorted(sites)]
            for port, sites in sorted(io.items())
        },
        "limitations": [
            "Conservative static candidate reachability, NOT executed instruction coverage",
            "Unresolved bank switches, indirect jumps and mixed ROM/data regions",
            "Fixed ROM counted separately for each reached bank context",
            "No complete game engine or physics parity inferred",
        ],
    }


def inspect(master: bytes, slave: bytes) -> dict:
    if len(master) != 0x90000 or hashlib.sha256(master).hexdigest() != MASTER_HASH:
        raise ValueError("Original arcade reconstructed master Z80 image required")
    if len(slave) != 0x160000 or hashlib.sha256(slave).hexdigest() != SLAVE_HASH:
        raise ValueError("Original arcade reconstructed slave Z80 image required")
    return {
        "game": "indyheat, original arcade 1991",
        "status": "Banked static candidate code graph, not complete source decompilation",
        "master": graph(master, "master"),
        "slave": graph(slave, "slave"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path)
    parser.add_argument("slave", type=Path)
    parser.add_argument("--out", type=Path,
                        default=Path("local/engine-extraction/banked_cfg.json"))
    args = parser.parse_args()
    result = inspect(args.master.read_bytes(), args.slave.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Master static contexts:", result["master"]["reachable_instruction_contexts"])
    print("Slave static contexts:", result["slave"]["reachable_instruction_contexts"])
    print("Master far-call edges:", len(result["master"]["far_call_edges"]))
    print("Does not demonstrate original engine or gameplay parity.")


if __name__ == "__main__":
    main()
