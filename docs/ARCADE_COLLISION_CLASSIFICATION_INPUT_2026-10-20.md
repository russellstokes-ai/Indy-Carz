# Original arcade collision classification and conditional input update

**Recovered:** 20 October 2026  
**Source:** user's privately supplied, checksum-verified original 1991 Indy Heat arcade rev-1 master Z80 and X-ROM  
**State:** two bounded original stages verified; full engine Gate A remains OPEN. No playable build, substitute physics or proprietary assets committed.

## 1. Original contact-projection classification: fixed master B6ED–B727

- **59 actual original instruction bytes** at B6ED–B727; SHA-256 26c2518291bc6c7c30213890de48ef122aac164c519e5f90aa9a1fabad0ef215.
- Original E919 low five bits index a **24-record, two-byte-per-entry** contact-category table at fixed master BC5C, through original indexed lookup helper 1747–174D. Cases with low-five-bit index 24–31 are not verified valid categories and are explicitly rejected in the bounded model. Original table bytes are PRIVATE, never checked into GitHub.
- The first selected table byte has its 0x33 bits stored in original RAM E925. Its 0xC0 bits are added modulo 256 to original IY-0x43, i.e. physical state-slot +0x3D, to determine a trigonometric orientation.
- Original cosine/sine pages A200/A500 and original signed 8×8 doubled X-ROM multiplication then project the existing D/E bytes to high signed product bytes.
- Original SCF; ADC A,H adds one extra unit to the two signed high bytes; original helper 0B3E saturates overflow at [-128,127].
- **Exact independent bounded maths:** angle = ((table_byte & 0xC0) + slot_plus_3D) & 255; value = signed_clamp8(signed8(high_signed_xrom(D, cos8(angle))) + signed8(high_signed_xrom(E, sin8(angle))) + 1); E925 = table_byte & 0x33.
- **Three original continuation branches:** negative result → B86C; result 0..3 → B778; result >=4 → B728. No claim that those are actual game-visible damage or car impulse levels until full consumers and real runtime are traced.

### Original-code parity executed privately

| Check | Verified result |
|---|---|
| Original bounded Z80 opcode execution vs independent integer model | **100,000 comparisons** |
| Original projection/output/branch mismatches | **0** |
| Branch B728 | **48,520** |
| Branch B778 | **1,802** |
| Branch B86C | **49,678** |
| Original trigonometry bytes independently checked | **512/512** |
| Original signed X-ROM high-result bytes checked | **65,536/65,536** |
| ROM-free local tests | **8 passed** |

The exact master stage, original private 24-record table, indexed lookup helper and signed-overflow helper have pinned SHA-256 signatures. Unsupported opcodes, addresses, call stacks and category values are rejected rather than silently approximated.

Public source: tools/arcade_collision_projection_classification.py; ROM-free tests: tests/test_arcade_collision_projection_classification.py.

## 2. Original conditional collision-triggered car byte: fixed master 0A30–0A41

The contact path at B728 invokes a small fixed-master helper, 0A30–0A41. The original code is exactly **18 bytes**, SHA-256 d470099ad81e5a07fbfc417160f06ee821dc1d6cc4601a44482e747c853c0494.

**Important original RAM alignment:** the original IX pointer is **0x80 bytes into** each 0x100-byte physical state slot. Index and physical offsets therefore differ:

| Original IX-relative field | Physical slot byte | Purpose in this bounded routine |
|---|---|---|
| IX+0x31 | slot+0xB1 | Read status bit 0 |
| IX+0x77 | slot+0xF7 | Read source byte |
| IX+0x57 | slot+0xD7 | Write result when enabled |

Exact original behaviour:

    if slot[0xB1] & 1:
        slot[0xD7] = (slot[0xF7] >> 1) & 0x7E
    # Otherwise leave slot untouched.
    # The Z80 accumulator A is restored via PUSH AF/POP AF.

All **65,536** status-byte × source-byte combinations were checked against original Z80 opcode execution and an independent byte model, **zero mismatches**, using varied other car-state bytes. **Six** local ROM-free regressions also passed.

The stronger original B728 event branch writes 0xFF to source field IX+0x77 before calling 0A30, implying an exact result of 0x7E at IX+0x57 when status IX+0x31 bit 0 is set. Further consequences from original calls to 0971, the rest of the collision controller and visible gameplay have NOT yet been verified.

Public source: tools/arcade_collision_contact_input_gate.py; tests: tests/test_arcade_collision_contact_input_gate.py.

## Re-run against user-owned original ROM (private workspace only)

First reconstruct the private original memory images using tools/arcade_rom_recovery.py. Then execute:

    python tools/arcade_collision_projection_classification.py local/rom-recovery/master.mame_runtime.bin local/rom-recovery/xrom.mame_runtime.bin --cases 100000

    python tools/arcade_collision_contact_input_gate.py local/rom-recovery/master.mame_runtime.bin

ROM-free regressions:

    python -m unittest discover -s tests -p test_arcade_collision_projection_classification.py
    python -m unittest discover -s tests -p test_arcade_collision_contact_input_gate.py

## Outstanding engine-wide gate

Complete original 0971 effects after its verified early exits, and follow the original B728–B777 collision branch into B778–B86B and negative B86C; obtain controlled MAME in-game frame/CPU/RAM traces; recover road and pit masks, actual dynamics, full AI, fuel, turbo, repairs, upgrades and the championship systems.

**Preserve the canonical Godot baseline.** The present ArcadeCarRecord uses some original IX-relative offsets; physical slot mapping requires a complete audit before refactoring this code. Do not introduce speculative physics, reshape or rotate the circuits, or release original ROM/assets in public.

**Original engine Gate A remains OPEN.** No new playable Godot code, concept build or APK was produced.


## 3. Original two-car collision response branch: B728–B777 (bounded original 0971 early-return domains)

Recovered the original **80-byte** fixed-master stage B728–B777, opcode SHA-256:
2f1cafa7bdd97f1c002be910f91fe13276b5b7336bbb641595591b0c45f2b7ff.

This bounded verification now covers all THREE original early-return branches of helper 0971 (at 0975, 097F and 0984). When original 0971 passes all three and reaches the longer continuation at 0985, both machine and independent models deliberately raise **FullHandlerUnverified** instead of guessing effects. Some early-return branches write car slot+0xCE before returning; this additional original state modification is now modelled.

For each car with its original status **BIT 1 at physical slot+0xDC set**:
- Write **0x30** at its physical slot+0xDC.
- Write **0xFF** at its slot+0xE3 and slot+0xF7.
- Set bit 3 and clear bit 4 at its slot+0xB3.
- Invoke the **verified original 0A30** helper.
- Save A, invoke original **0971** with A=0 and restore A.

**Critical original pointer detail:** The second-car (IY) event branch performs original CALL 0A30 **before** exchanging IX/IY for its CALL 0971. Consequently **both 0A30 calls operate on the original first car (IX)**. When only IY's event is active, the original first car's +0xD7 output may change using its existing +0xF7 byte, but the second car's +0xD7 remains untouched by this particular routine. This is proven by the original machine-code call/pointer ordering, not an assumed design improvement.

### Privately executed Z80 parity

- **100,000** independently generated two-car states versus bounded original B728–B777 opcode execution, composing independently verified original 0A30 and three original 0971 early-return paths.
- **Zero** full two-car record or resulting-A mismatches.
- Exactly **25,000** scenarios for each of the original four cases: no car events, first-car event only, second-car event only, both events.
- **Ten** ROM-free local regression tests, including the first-car IX pointer behaviour and the additional two original 0971 early-return cases.

Source: tools/arcade_collision_contact_two_car_fastpath.py.
Tests: tests/test_arcade_collision_contact_two_car_fastpath.py.

**Next real extraction gate:** Recover the longer original 0971 path from 0985, then the B778 and B86C continuations and correlate these status and input fields with real arcade execution traces. The original 24-contact-category lookup remains private. Godot gameplay, track geometry and mobile camera remain untouched; overall engine Gate A stays OPEN.


## 4. Original 0971 entry and three early-return gates: fixed master 0971–0984

The original 20-byte fixed master Z80 stage 0971–0984 has SHA-256:
9cf5938e82faad23619e335977fcc5c4c553dc6b3a280399d0abe3e3ed4c9233.

Here IX points 0x80 bytes into the physical 256-byte state slot:

- If original **IX+0x31 bit0 is SET** (physical slot+0xB1), the routine immediately **RET NZ at 0975**, without changing the car record. Original A is unchanged.
- If that bit is CLEAR, it writes original A to **IX+0x4E** (physical slot+0xCE), stores A in B, then reads **IX-0x03** (physical slot+0x7D).
- If that byte is **unsigned 3 or greater**, it returns at **097F** with A holding the original slot+0x7D byte and B holding the call's entry accumulator.
- Otherwise it reads **IX+0x23** (physical slot+0xA3). When nonzero, the routine returns at **0984**, with that byte in A and the original A in B.
- Only if all three early exits fail does original execution reach **0985**, which has a much longer and still unverified memory-transfer/game-state path. Reject, do not invent the rest.

### Exhaustive private original-code parity

- **131,072** input cases: two original bit0 statuses × all 256 values of the first comparator × all 256 values of the second.
- **131,069** cases returned from original 0971–0984 through one of the three proven exits; exactly **three** input combinations reached 0985. All **131,072** returned or escalated exactly as in original opcode execution, zero mismatches.
- Per-exit original combinations: **65,536** at 0975; **64,768** at 097F; **765** at 0984; **3** intentionally unresolved at 0985.
- **Seven** ROM-free unit tests check write priorities, branch boundaries, original A/B semantics and safe rejection of the deeper path.

**Important:** Input-domain case frequencies are NOT proof of real-game runtime frequency. The unrecovered 0985 continuation may be frequently or deliberately entered during actual races.

Public verifier: tools/arcade_collision_service_0971_entry.py; ROM-free tests: tests/test_arcade_collision_service_0971_entry.py.

The B728 original paired-event verifier was extended and **rerun on 100,000 private original-code cases with zero mismatches**, exercising all three verified 0971 returns. The original first-car IX helper-call ordering remains unchanged. No speculation, gameplay or original graphical assets were added.
