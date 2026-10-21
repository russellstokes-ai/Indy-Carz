# Original arcade BC8C collision retry and rollback — live and opcode parity

**Date:** 21 October 2026  
**Original reference:** privately held and SHA-256 authenticated user-owned 1991 Indy Heat rev-1 arcade ROM; genuine MAME 0.264 live CPU debugger trace.  
**Scope:** original collision bank setup/retry and bounded fallback, NOT complete collision response or terrain damage. No ROM, source assembly, QRAM, screenshots or original game art in public GitHub.

## Original bounded Z80 stages

**BC8C–BCAF**, fixed master, original helper called by B884:

- Read the original 16-bit word E976, then compute bank control as (E608 & 0xF0) OR low(E976); write E608 and output F4. This is bitwise OR, NOT necessarily low-nibble replacement.
- Clear bit 7 of original IX+31 (physical car slot+B1). IX points 0x80 bytes into each physical 256-byte record.
- At BC9E reset original E92E and E92C to zero. At BCA5 increment E92E modulo 256, compare with hexadecimal 12 (decimal 18), and branch into the original collision body at BCFA if the incremented value is below 18.
- An original debugger breakpoint AT BC9E observes the prior counters before the reset, so counter reset must be checked at the subsequent BCA5 hit.

**BCA5–BCF9**, original retry and fallback:

- Increment existing E92E. Values yielding 0–17 proceed to BCFA. Values yielding 18–255 enter original reset helper at C468.
- Original fixed master C468–C486 sets IX+41, IX+4C and IX+4D to zero (physical car bytes+C1/+CC/+CD), sets E76A=E768, writes 16-bit E76B=0xCC00, and writes 16-bit E765=0.
- Original BCB5–BCF6 copies exactly ELEVEN saved 16-bit geometry, position and heading words from the E747–E75C backup region to original E72B–E73E and E767 destination words, in exact original instruction order.
- Original BCF7 jumps back to BC9E, resetting the counters and starting another collision-processing attempt.
- E92E=FF wraps to zero, so this case takes the less-than-18 branch, not the fallback. A host-language unbounded counter would get this wrong.

## Private original-opcode verification

Public code tools/arcade_collision_bc8c_retry_restore.py independently models and interprets the original opcode bytes (including the complete C468 helper and all eleven original 16-bit word transfers). Checks authentic ROM and routine SHA-256 fingerprints. Unknown original instructions, unexpected RAM addresses or original external calls fail closed.

| Original bounded stage | Original-Z80 cases | Mismatches |
|---|---:|---:|
| BC8C bank, status, counter initialization | 65,536 | 0 |
| BCA5 retry and C468/11-word fallback | 30,000 | 0 |
| **Total** | **95,536** | **0** |

Within the 30,000 synthetically seeded retry-state cases, 2,123 continued directly to BCFA and 27,877 took the fallback. **These are controlled test cases, not live-game probabilities.** Thirteen public ROM-free regressions cover byte wrapping, bit clears, exact original reset fields, source/destination word copy, and unsupported inputs.

## First actual live MAME execution audit

A genuine original ROM race with MAME 0.264 produced **9,000 emulated video frames**. Exact original CPU breakpoints were checked for bank selection and status bit7 clear, both retry counters, BCA5 next-PC branching, and any C468 execution.

| Actual debugger observation | Count |
|---|---:|
| BC8C collision routine entries | **16,691** |
| BC9E counter reset site | **16,691** |
| BCA5 retry checks | **16,791** |
| BCFA processing entries | **16,791** |
| Extra retry checks after first attempt | **100** |
| BCB2 / C468 / BCF7 fallback hits | **0** |
| **Original instruction breakpoint events** | **66,964** |

All 66,964 records passed independent event-order, original bank/bit7 and counter/branch checks; **zero mismatches**. The additional 100 retries were 93 second attempts and seven third attempts. Original entries by IX: E080 3391, E180 3302, E280 3326, E380 3369, E480 3303.

**Essential limitation:** no retry reached 18 in this live sample. C468 and the eleven-word restore are original machine-code verified but have NOT been observed in a live fallback. The BCFA main collision dynamics and later callbacks remain open.

User-owned private captures remain outside GitHub. The public reproducible capture is tools/mame_capture_collision_bc8c.lua. Live audit: tools/arcade_live_collision_bc8c_audit.py. Its ROM-free corrupted-input regression suite is tests/test_arcade_live_collision_bc8c_audit.py. Private ROMs and memory dumps are never uploaded to public CI.

## Main unresolved driving/collision areas

The original BCFA–BE** calculation and its C5** subroutines, impacts on speed/handling/terrain, full acceleration and steering integration, full AI behaviour, fuel/turbo/pits/upgrades, and original runtime race-state parity remain incomplete. No guessed physics, original circuit geometry changes, track rotation, altered pace or Android APK is introduced.

**Commercial original-engine extraction Gate A remains OPEN.**
