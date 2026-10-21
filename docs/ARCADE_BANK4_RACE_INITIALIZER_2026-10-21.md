# Original second bank-4 far call: five-car initialization and course control

**Date:** 21 October 2026  
**Reference:** user-owned authentic original 1991 *Indy Heat* rev-1 arcade ROM, SHA-256 verified.  
**Scope:** exact, bounded original-master-Z80 code at bank-4 CPU **2000–208B**, nested original bank-4 helper **208C–20A7**, and fixed-ROM indexed helper **1744–174D**. Game-wide Gate A remains **OPEN**.

## Relation to the earlier 1190 recovery

Original fixed-master **1190** contains two bank-4 far calls through wrapper 14C1, **first 20A8 and then 2000**. The first routine was recovered earlier in docs/ARCADE_RACE_PRESTART_AND_BANK4_SELECTION_2026-10-21.md. This report covers the *second* callee.

**Important ordering:** The second call initializes E602 and the car bit-6 flags **after** the first callee at 20A8 has already read E602 and selected the car pointers. Do not mistakenly feed the just-initialized E602 back into that same earlier 20A8 execution. The updated status can affect later cycles/calls, subject to full original runtime verification.

## 1. Five car records and the first-three linked eligibility checks

The original routine clears **E61C as a 16-bit word** and global **E602=0**, then calls the original per-car helper at 208C for **three** state pointers, E080, E180, E280. The other two original pointers E380 and E480 are also visited, but only to clear bit 6 in their physical state-slot **+FE** (original IX+7E).

Original nested 208C:
- Clear original **IX+7E bit6** unconditionally.
- If **IX+31 bit0** is set, return without re-enabling bit6.
- Otherwise invoke independently verified fixed helper **1783**, which loads linked IY from the car's physical slot +FC/+FD.
- Read original linked **IY+3B**, AND with **03**. If nonzero, return.
- Otherwise set car **IX+7E bit6** and write **E602=01**.

Thus only the **first three** car slots may be re-enabled by this pass; any of them can set E602 to 1. Neither car slot four nor five is enabled here even if its previous bit 6 was set.

### Genuine original-code parity

**30,000** deterministic five-car status patterns against a separate mathematical state model, executing original 2000–2030, 208C and 1783 Z80 opcode forms: **zero mismatches** for all five resulting state bytes, E602 and E61C. In the controlled sample, E602 was set in **9,797** cases and remained clear in **20,203**. Those are synthetic test-case counts, not actual in-game participation rates.

## 2. Original control-byte selection and course-indexed lookup (2031–208B)

Original bank-4 code initializes B=C=0, reads **E676**, compares it to **FF**, and uses **JP M** to select an early branch when the **signed sign bit of the 8-bit subtraction** is set. This is NOT a generic unsigned less-than comparison: original E676 values **127–254** skip the subsequent byte adjustments in this branch.

For other values, the routine calculates B and C using **E676**, and the *low byte* of original **E641**. The exact result is stored into global RAM **E63E=B** and **E674=C**. The independently verified model preserves original DEC L, INC B/C and conditional CP/JR Z instruction semantics, including boundary values E641=1 and 2, E676=0,1,2,3,127,255.

It then calls the original fixed helper **1744** twice, using **E699 course index** to fetch one parameter from each of two original fourteen-entry tables in bank4 at **2305** and **2313**. Output bytes are stored into global RAM:
- **E623 = 0x50** for all fourteen documented original course indices.
- **E638 = 0x04** for internal course indices **1, 8, 11, 13** and **0x02** for the other ten indices.

These are authenticated original control values, **not** explanations of lap count, AI speed, fuel, difficulty or terrain until consumer uses are traced. The original proprietary ROM table bytes are not committed. Small independently reproducible numeric behaviours are represented as conditions in the public model.

### Original-code parity

**All 65,536** possible E676 and E641 low-byte combinations tested against original Z80 machine instructions, with the original course index varied across all fourteen valid values. Exact E63E/E674/E623/E638 output agreement against separate independent formula: **zero mismatches**.

Authentic original code and table range, fixed helper and bank4 208C have pinned SHA-256 signatures, including both halves of the 2000–208B routine.

## 3. Combined status and remaining recovery

| Verified bounded section | Original instruction/model cases | Mismatches |
|---|---:|---:|
| First-three linked state and all five car status bits | 30,000 | 0 |
| E676/E641 flags and course indexed controls | 65,536 | 0 |
| **Total** | **95,536** | **0** |

Public original-ROM-gated tool: **tools/arcade_bank4_race_init_2000.py**.  
ROM-free regression: **tests/test_arcade_bank4_race_init_2000.py**.

This recovery makes the two initial bank4 far-call targets from original fixed 1190 substantially understandable as bounded car-selection and state-initialization routines. **It does not recover the rest of 1190's caller response**, the remaining 213F+ selection consequences, full downstream AI driving, original terrain/collision/upgrade/fuel/pit logic, fourteen dynamic trackmaps or live MAME behaviour. The original 22BA **numerical routine is now fully recovered to its 2304 return**; see docs/ARCADE_BANK4_METRIC_22BA_2026-10-21.md.

No Godot gameplay, licensed artwork, circuit geometry, physics, camera or APK changes were made. The original-ROM data stayed in the user's private local research workspace, not the public GitHub repository.

**Gate A remains OPEN; original arcade geometry and smooth bounded portrait camera are protected.**
