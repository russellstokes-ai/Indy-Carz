# Authentic arcade championship, first-round reset and transition gates

**Date:** 20 October 2026  
**Reference:** user-owned authentic 1991 Indy Heat arcade rev1, privately reconstructed and checksum-verified.  
**Status:** bounded original-Z80 race-management behaviour recovered. **Commercial engine Gate A remains OPEN.** No original program/graphics/sounds committed.

## 1. Championship start and advancement: fixed 2936-2952; master bank3 62A9-62C4

Original master fixed 2936-2952 handles entry-round selection, and original master bank3 62A9-62C4 selects the following event. Both call the actual master fixed 1747-174D indexed lookup helper and load table 1ABF-1ACD. Original RAM:
- E69A: signed mode/index selector
- E69B: championship round index (0..14)
- E699: current course index from original 15-byte ROM table.

The exact original order is: 13, 12, 1, 3, 7, 8, 4, 2, 5, 11, 0, 6, 9, 10, 1. **There are fifteen championship events but only fourteen original circuit indices.** Internal course 1 appears twice, at positions 2 and 14.

Original E69A values **0-14** (sign bit clear) select a particular event directly, regardless of prior E69B. Values 15-127 are outside the verified 15-entry table domain and fail closed in the independent model. E69A values **128-255** (sign bit set) choose automatic mode: at first championship entry round E69B becomes 0; at advancement it increments and wraps from 14 to 0. Automated advance rejects any previous E69B outside 0-14.

When first-round initialization selects round 0, the original PC proceeds to **2953**, the six-linked-slot clear. For other selected rounds it skips directly to RET at **2989**. On advancement, the checked stage ends at **62C5**, just before **CALL 2120**, which is still unverified and must not be assumed to leave race state untouched.

**Original-machine parity: 11,520 input combinations (5,760 for initialization and 5,760 for advancement), zero mismatches** against independent byte/state logic, including the original 1747 ROM lookup. Original master and table SHA256 values are pinned in tools/arcade_championship_progression.py; ROM-free tests in tests/test_arcade_championship_progression.py.

## 2. First-round six-slot linked-state reset: fixed 2953-2989

The original code starts IX=E580, B=5, DE=FF00. The original fixed **1783** helper forms pointer IY from (IX+7C,IX+7D), equivalent to *physical* state-slot offsets +FC/+FD because IX points 0x80 into each slot. It issues original CPU zero writes to linked IY offsets **1,3,2,4,5,9,3,2,12**. These are nine ordered writes with two duplicates, seven distinct offsets.

Original ADD IX,DE; DEC B; JP P loops while B is sign-clear, so it visits **six** original 256-byte slots (E580,E480,E380,E280,E180,E080). It exits after B wraps from 0 to FF. Therefore the first-round clear performs exactly **54 original CPU byte write events**, not five cars times seven offsets.

**12,000 original Z80 opcode executions vs independently generated six-linked-pointer addresses**, zero write-address, byte, order, register or exit-state mismatches. Includes pointer aliasing and full 16-bit address wrapping. The physical bus destination meaning cannot be asserted without MAME runtime. Verification tool: tools/arcade_round_zero_linked_reset.py; ROM-free regression: tests/test_arcade_round_zero_linked_reset.py.

## 3. Round-specific countdown and three-slot transition: bank3 6218-6227 and 627C-62A8

Actual original stage **6218-6227** writes a 16-bit byte counter E7D2 depending on round index E69B:

- Ordinary indices 0-13: **0x0084 = 132**
- Final index 14: **0x00C6 = 198**

These values are original internal counter units, **not established seconds/frames**.

Original gate at **627C-62A8** reads global E603 and, when E603==0, scans original IX car records E080/E180/E280. Each record passes the gate if EITHER original IX+31 bit0 (physical slot+B1) OR IX-09 bit0 (physical slot+77) is set. If all three pass the code jumps to 62A9, skipping countdown. If E603 != 0, or any checked record fails, it reads and decrements E7D2 as a **wrapping 16-bit integer**. When the result becomes zero it proceeds to round selection at 62A9; otherwise control returns to 624C. Starting at zero wraps to FFFF and does not immediately advance.

Do **not** label these tested status bits as AI readiness, fuel, damage or lap completion: their real-game meaning needs original runtime evidence.

**All 15 original counter seeds plus 60,000 independently generated original Z80 gate cases match the mathematical model with zero mismatches**, including countdown 0,1,FFFF and bit-mask boundaries. Original-code verifier: tools/arcade_race_transition_gate.py; ROM-free regression: tests/test_arcade_race_transition_gate.py.

## New cumulative original-code verification

| Bounded stage | Verified cases | Mismatches |
|---|---:|---:|
| First-round and advancement selector | 11,520 | 0 |
| Six-state first-round linked memory writes | 12,000 | 0 |
| Original per-round delay seed | 15 | 0 |
| Three-slot gate and countdown | 60,000 | 0 |
| **Total this recovery phase** | **83,535** | **0** |

Public CI runs independent ROM-free synthetic tests. Authentic original-opcode executions run only locally against privately supplied ROM. The counts do NOT imply a percentage of full-game completion or whole-game gameplay parity.

## Remaining original engine / release blockers

Original CALL 2120, race entry/results/score flow, exact lap and checkpoint scoring, AI, terrain/wall collisions, damage, steering/traction integration, fuel/turbo/repair/upgrade/pit state machines, original 80186 audio commands, frame timing, all fourteen dynamic QRAM tracks and related collision/pit masks remain to be recovered/verified. The full commercial Godot engine, replacement visual/audio assets and Android QA are not finished.

**Approved design baseline unchanged:** original circuit geometry, original arcade mechanics and pace; portrait camera uses slow smooth bounded panning, never rotated or redesigned tracks. Original ROM or proprietary art/audio/disassembly must stay PRIVATE.

**Gate A remains OPEN.**
