# Original arcade race-frame signals, AI event chain and candidate-distance lookup

**Date:** 20 October 2026  
**Original reference:** user-owned authenticated 1991 arcade Indy Heat rev 1, fixed/master bank-0 and bank-3 Z80 code and private data lookup. The original executable and private derived assembly/lookup bytes are excluded from public GitHub.  
**Status:** BOUNDED original opcode parity. Whole-game engine Gate A remains **OPEN**. No new Godot gameplay, unverified physics, track geometry, commercial assets or APK added.

## Exact original three-racer frame dispatch and pending event priority (bank 3)

Original master bank 3 frame block **624C–627B** explicitly invokes the existing callback dispatcher at **18C0** for the first three racer state records, in this order:

    CALL 1078              # external update, opaque
    IX=E080: CALL 18C0     # callback through car+94 pointer, opaque
              CALL 6C8E   # external car processing, opaque
    IX=E180: CALL 18C0
              CALL 6C8E
    IX=E280: CALL 18C0
              CALL 6C8E
    CALL 1087 with HL=2    # external update, opaque

This is exact STATIC call-site order, not the complete execution of 18C0/6C8E or proof of one arcade video frame elapsed per pass. The original callback targets are runtime-dependent and require MAME traces.

The bounded master-bank3 **6C9B–6CC5** reads physical car slot **+0x77** (original IX-09), and prioritises clearing one event bit per call: **bit0, then bit2, then bit1**. If bit1 is selected, original incoming register B determines whether it returns A=0 with Z set (B nonzero), or A=FF with Z clear (B zero). No pending bit yields Z set without changing the input byte. This is the actual return status seen by the surrounding original routine, not a guessed event interpretation.

Original bank3 **6C62–6C83** checks the three first racer slots at physical byte **+0xB1 bit0** (IX+31) and global E603. When all three flags are set and E603 was zero, writes E603=1 and calls original 105F (opaque). Otherwise branches according to original flag and global state. The separate bounded **6C84–6C9A** car-service gate checks original car+0x23 and global E7DC before conditionally clearing car+0x1E bit0 and invoking original 103C (two calls then a tail JP). Original 103C itself is NOT recovered by this module.

**Original private Z80 interpreter vs independent models:** 65,536 exhaustive event-status x incoming-B pairs, 16,000 global gate pairs and 4,096 service cases, **85,632 bounded comparisons, zero mismatches**. Ten ROM-free regressions. Public replay tool: tools/arcade_race_signals.py; tests/test_arcade_race_signals.py.

## Original AI pending-event generator: master bank0 230B–2360

This code generates physical state-slot **+0x77** event bits 1 or 2 (OR, not replace), using original physical fields:
- IX+31 = physical slot+B1, bit4
- IX+32 = physical slot+B2, bit7
- IX+57 = physical slot+D7, input-like byte
- IX-45 = physical slot+3B, comparison byte
- IX+7E = physical slot+FE, bit4
- linked IY+20 from original pointer helper 1783, held as a controlled observation

The exact original threshold tiers, determined by the bounded Z80 code, are:

| Original condition | Upper threshold B | Lower threshold C |
|---|---:|---:|
| (slot+B1 bit4) or (slot+B2 bit7) set | 24 | 9 |
| Both clear and slot+D7 >= 68 | 80 | 50 |
| Both clear, slot+D7 in [60,68) | 128 | 50 |
| Both clear, slot+D7 < 60 | 128 | 72 |

- If comparison byte slot+3B is **less than B** and also **less than C**, set pending bit1.
- If it is less than B but **not** less than C, return with no new event.
- If at least B, set pending bit2 unless the original linked exclusion holds: slot+FE bit4 set, linked IY+20 = 2, and both original status flags clear. Under that exclusion, return without setting the bit.

**100,000 original Z80 executions vs independent models, zero full-record/event mismatches**. Controlled test frequencies: bit1 21,523, bit2 59,615, threshold gap 17,888, linked exclusion 974. These are synthetic input case counts, NOT live race event frequencies. Seven ROM-free tests.
Tool: tools/arcade_ai_pending_event_rules.py; test: tests/test_arcade_ai_pending_event_rules.py.

## Original linked countdown and bounded positional gate: bank0 22B8–230A

Before the threshold routine, original 22B8 reads a linked record via already-verified pointer helper 1783:
- If physical car slot+FE bit4 set, linked IY+20 is exactly 3, slot+B1 bit4 clear and slot+B2 bit7 clear: set original pending event bit1, write linked IY+0E=0 and return.
- Otherwise DEC A against original linked IY+0E. If the resulting byte has **sign bit clear** (original Z80 JP M not taken), store the decremented byte and return. Counter input 0 wraps to FF and runs the later spatial checks *without* writing the timer. Inputs 129–255 similarly take that later path, despite being nonzero; do not assume an ordinary nonnegative integer timer.
- The later gate checks two *half-open byte windows* using original RAM E642 and E95B: low bound <= slot+0B < high bound, and low bound <= slot+01 < high bound. When both pass and car slot+DC bit1 set, it sets pending bit1. Otherwise it falls through to the exact original 230B event producer above.

**100,000 original opcode executions with original 230B composition, zero model mismatches**. Nine ROM-free tests. Tool: tools/arcade_ai_linked_countdown.py.

## Original AI entry and verified bounded path: bank0 2263–22B7

The original entry:
1. Early RET NZ when slot+B3 bit1 set.
2. If global E603 is zero and car slot+91 >= low(ED59) and slot+A3=0, invokes original **31E6**. Its full entry/start state changes are not verified and the model raises UnverifiedAIExternal.
3. Derives one unsigned selector byte: (((E627 & 0x0E) >> 1) - 3) & 0xFF. When it differs from slot+7D, jumps immediately to original **021A** without the normal per-car input/event stage.
4. If slot+7D=4 and E627 bit4=0, invokes original **1190** (a banked far-call wrapper which may replace IX); fails closed because its full effects are not yet proven.
5. Otherwise computes the exact original pedal-like byte slot+D7 = (slot+F7 >> 1) & 0x7E, invokes recovered **22B8–2360**, then jumps to original **021A**.

**100,000 input cases used to challenge original opcode interpretation and independent models**: 10,000 verified early returns, 47,617 verified direct jumps to opaque 021A and 35,595 verified complete input/event stages before opaque 021A; **93,212 cases had fully verified bounded results, zero mismatches**. The other **6,788** explicitly reached unresolved original external calls: 4,389 at 31E6 and 2,399 at 1190. They are NEVER misrepresented as successful full-path comparisons. Eight ROM-free tests. Tool: tools/arcade_ai_entry_2263.py.

## Original fixed A000 metric lookup from AI tail: master 021A–028C

A further original-code stage immediately downstream reads four candidate-coordinate bytes from the car record (original IX+46/+47/+48/+49) and two baseline position bytes (IX-7F and IX-75).

It calculates two 8-bit coordinate differences with original wraparound, uses original Z80 sign-conditioned NEG, caps each apparent magnitude at **15**, combines the two capped bytes into a 4-bit x 4-bit grid index, and performs the **odd-byte lookup** at A000 + 2*index + 1 in the original **512-byte fixed-ROM table**. This happens for both candidate positions, then original Z80 **CP E; JP NC** branches to 02C3 when second lookup byte >= first, otherwise falls through to 028D. Input slot+B3 bit2 set bypasses the stage and jumps directly to opaque original 05DC.

**100,000 private original ROM table/opcode vs independent lookup comparisons, zero mismatches**, with both candidate comparison results and original B/C/D/E/HL output registers checked. Original ROM table SHA-256 is pinned; no ROM table contents are committed. Eight ROM-free tests use a synthetic alternative lookup table, not proprietary bytes. Tool: tools/arcade_ai_distance_table.py.

This original A000 table is *not proved* to be AI steering, terrain collision, path choice or damage. The numerical lookup/branch is verified, but downstream 028D, 02C3 and 05DC actual effects need controlled runtime and further extraction.

## This pass: exact verification totals and limits

| Original bounded coverage | Test inputs | Fully verified outcomes | Mismatches |
|---|---:|---:|---:|
| Bank3 racer event/global/service gates | 85,632 | 85,632 | 0 |
| Bank0 230B pending-event producer | 100,000 | 100,000 | 0 |
| Bank0 22B8 linked timer + 230B composition | 100,000 | 100,000 | 0 |
| Bank0 2263 entry + event composition | 100,000 | 93,212 | 0 |
| Fixed 021A two-candidate metric | 100,000 | 100,000 | 0 |
| **Total** | **485,632** | **478,844** | **0** |

The five verifiers exercise *bounded subroutines*, several with overlapping nested routines; the totals are NOT independent code coverage or a whole-game completion percentage. The 6,788 unverified 2263 caller cases are explicitly counted as unknown, not passed.

**Five Python regression modules, 42 ROM-free tests**; authentic opcode runs were performed only in the user's private local execution workspace. Original game binaries, images, asset data and source assembly never enter the GitHub PR.

### Remaining blockers before authentic playable Godot engine

Original master 31E6 race/start state machine, banked 1190 callable and 021A follow-ons, remaining full AI routing and actual steering, the five-car dynamics/track boundaries, sprites, fuel/pits/turbo/upgrades, race scoring/results, the original 80186 sound effects/commands, and all fourteen real runtime QRAM circuit surfaces remain unverified end-to-end.

MAME is not installed in this container and remote package download was not successful, so original *executed* full-game race/CPU/QRAM frame captures still cannot be claimed. No placeholder physics, resized tracks or premature demo/APK. Preserve the original course geometry, gameplay speed and slow bounded portrait pan.

**Original engine extraction Gate A remains OPEN.**
