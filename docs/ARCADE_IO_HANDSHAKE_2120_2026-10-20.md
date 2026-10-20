# Original arcade I/O handshake at 2120 — whole-game sound/interface investigation

**Recovery:** 20 October 2026  
**Original reference:** authentic 1991 Indy Heat arcade master Z80 bank3 (user-owned original ROM).  
**Status:** exact bounded I/O-control protocol code, under controlled input-port responses, **VERIFIED**. Hardware partner, original sound meanings, CPU scheduling and gameplay timing are **NOT YET VERIFIED** by live MAME.

## Why this matters to the whole game

The 15-round championship selection at original bank3 62A9-62C4 invokes **CALL 2120** immediately after selecting the original circuit. Its target is NOT another round-index calculator. It performs an interrupt-aware, multi-port initialization/handshake with retry logic and original control/status RAM.

The recovered bounded original bank3 routine spans **2120–21A2**, and invokes the original **2105–2114** interrupt-status helper. Both are SHA-256 pinned in tools/arcade_io_handshake_2120.py. Port 05/06 also appear in a separately recovered audio-command path, but this alone does NOT establish the exact device peer or identities of original sound cues.

## Original Z80 stage behaviour

1. Set **E7AA = FE**, invoke helper 2105: set bit7 in **E62B**, read Z80 I register through LD A,I (the original P/V flag reflects IFF2). Depending on original interrupt state, either DI is issued or not. The original AF state is saved.
2. Initialize original RAM: E7A9=00; E7A7=01; E7A4/E7A5/E7A6=80; E7A8=0A.
3. Every handshake attempt: output **FF on port06**, then **FF on port05**; pulse E7AA/port0C from **FE** to **FF**, separated by a short original DJNZ delay. There are up to **ten attempts**.
4. Phase 1: poll **IN A,(04)** with an original 16-bit counter initialized to **C350 hexadecimal = 50,000 decimal**. The original byte FF means success: INC A wraps to 00, so JP Z enters phase 2. If 50,000 reads elapse without FF, set **E7A9=01**, decrement E7A8 and retry (or exit if retries exhausted).
5. Phase 2: after first-phase success, output **00 on port06 and port05**, then poll port04 for byte **00**, again for up to 50,000 reads. A nonzero input eventually times out and triggers the same retry/error sequence.
6. At a success or final exhausted exit, E7A8 is restored to **0A**. A previous timeout can leave E7A9=01 even after later success; E7A9 alone is therefore NOT a reliable success indicator. The interrupt state is restored through the original saved AF plus RET PO / EI+RET branches.

The 50,000 value is a CPU polling iteration limit, **not 50,000 video frames or real-world milliseconds**. Runtime responsiveness is unknown without MAME CPU timing and original hardware service execution.

## Verification completed against original source

The private interpreter executes each genuine original Z80 instruction, including actual repeated port-input/DEC HL/JP loops: it does NOT fast-forward the 50,000-iteration polling sequence.

- **6,000** varied quick-success cases with random original I registers, original IFF status, original E62B and bounded input-read sequences.
- **Five** long-path cases covering first-phase timeout followed by success, second-phase timeout followed by success, ten first-phase timeouts, ten second-phase timeouts, and success only on the tenth attempt.
- Total **6,005 genuine original-opcode scenarios, zero mismatches** comparing all port output values/order, number of reads, retry count, original E62B/E7A4..E7AA state, original A and restored IFF.

This is **controlled Z80 code-path parity**, not live emulator hardware response, sound fidelity, device electrical output verification or game-cadence validation.

Public tool: tools/arcade_io_handshake_2120.py; ROM-free regressions: tests/test_arcade_io_handshake_2120.py. Original ROM inputs remain private, never committed or attached to the public GitHub PR.

## Open questions after this substantial bounded recovery

- Which actual original hardware endpoint(s) respond to port04/05/06/0C during round transitions, and how does this differ between the original MAME master, slave and 80186 sound devices?
- How frequently is this handshake invoked during actual race/race restart and what happens when it times out?
- Which sound-command bytes correspond to specific original car/AI/turbo/pit/collision events? Reconstruct separately from original 80186 command processing; use rights-cleared new sound effects.
- Full track QRAM capture, end-to-end car dynamics, AI decisions, pits/fuel/turbo/upgrades, lap/result/score and championship control still require live original runtime observation.

**Commercial original-engine Gate A remains OPEN.** No playable Godot port or substitute arcade physics is claimed. Original track layouts, new-brand asset requirements and approved portrait camera remain unchanged.
