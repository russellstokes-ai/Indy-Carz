# Full-arcade ROM survey and complete-game recovery status — 20 October 2026

**Source:** privately retained, user-provided authentic 1991 arcade rev-1 `indyheat.zip`, original master/slave/X-ROM SHA-256 authenticated against the canonical recovery tools. This is a technical status report and PRIVATE-ARTEFACT INDEX, **not a claim that the game has been decompiled or reproduced**.

## Whole original program coverage — new static inventory

- All 27 original archive members were checked for existence, size and reconstructed-region authenticity, and the 80186 original reset entry FFFF0 -> FFD80 was independently verified.
- Entire MAME-rotated master Z80, slave Z80 and the original Intel 80186 audio-ROM images were inspected privately.
- 60 distinct Z80 CPU memory views represented: two master fixed ranges, sixteen master bank windows, one slave fixed range and **41 unique slave bank-window views**, deduplicated by actual mapped physical ROM offset.
- 61 linear assembly listings generated privately (60 Z80 memory views plus original 80186 sound). Approximately 71 MiB of machine instruction text and 4,385 candidate bank-qualified direct call targets. These are **sweep candidates**, not proven game functions: tables, sprites, data, code-banking and control flow may produce false positives.
- Original ROM chip bytes, decoded assembly, audio and original game data stay **outside public GitHub**. The user owns a 9.4 MiB private ZIP of the complete original static disassembly and cross-reference data, plus a reproducible local script.
- Six additional local regression tests pass, including all CPU/X-ROM region hash/size validations, original 80186 reset, real-world original B884 and 0A30 instruction decoding, bank-view counts, Z80 prefix/length validation and a check that the private archive has no raw ROM/graphics/audio blobs.

## Original collision continuation B8AC–B8E3 — verified in independent local original-opcode run

Directly after the already verified B884 callback gate, original fixed master **B8AC–B8E3** consists of exactly 56 machine-code bytes, SHA-256 `1011e64d6c1822f44825fb6c8d4e4ac2a269260d7b5efb0a109ffb9f64760d3c`.

- Copies exactly **0x42 (66) bytes** from master shared scratch E72B–E76C back to the car's physical state bytes +00–+41, by original Z80 LDIR.
- Original signed-wrapped 8-bit difference checks compare copied physical slot byte +01 against +1F, then copied +0B against +29.
- If either unsigned difference is **06..F9**, actual original code conditionally CALLs diagnostic/scheduler **1689**. That is a nonlocal exit — NOT a successfully completed collision or a simulated rebound.
- Otherwise BIT 7 at physical slot +B1 decides whether to set slot +7C bit1 (BIT 7 set) or return leaving the status byte unchanged.
- An independent record/byte model matched bounded interpretation of the genuine original Z80 instructions on **50,000 deterministic cases; zero output or branch mismatches**. Cases covered first-axis exceptional transfer (11,947), second-axis exceptional transfer (12,461), normal status bit set (12,813), and normal unchanged status (12,779).
- The complete original BC8C callback internals remain **unverified**, as do game-visible effects, elapsed time and other downstream systems. These are test cases for this conditional routine, not observed real-game frequency.

The private B8AC original-opcode checker is delivered with the private ROM survey update. Public code should eventually carry the ROM-free original mathematical model and case coverage, but **no private ROM-derived program bytes**.

## Entire-game commercial release remains blocked

The user-approved original circuit geometry, 14 unique tracks and 15-race original order must be preserved. Controlled MAME per-frame runtime evidence is still absent from this environment (no MAME executable or network package retrieval). That prevents validating dynamic QRAM trackmaps, actual full driving physics/terrain, lap and pit scoring, all 5 opponents, difficulty/economy, sound effects, CPU scheduling and UI progression. The 80186 and both Z80s are not compile-ready independent engine sources.

**Extraction Gate A: OPEN.** No substitute physics, gameplay demo, track rotation, invented car speed or complete APK is authorised or claimed. Approved Godot camera and existing mechanical tests remain untouched.
