# Original arcade race-start, linked counters and bank-4 racer selection

**Recovery date:** 21 October 2026  
**Source:** user-owned authentic 1991 Indy Heat arcade rev-1 ROM, master and X-ROM SHA-256 independently authenticated. Original binaries and disassembly were read and verified **privately**. No copyrighted ROM chips, proprietary graphics, sounds, lookup tables or decoded program assets were pushed to this public repository.

**Scope:** genuine bounded original Z80 opcode parity for the three routines below, **not** a fully playable or completed original racing engine. **Commercial extraction Gate A remains OPEN.**

## 1. Fixed master 2CF9 – linked 24-bit snapshot and selected 16-bit counter

Original **31E6** starts with an actual CALL **2CF9**. The original nested path at **2CF9 → 2CD1 → 2CEB**, with original helper calls **1783** and **1775**, has now been independently reconstructed and interpreter-verified.

Exact verified behaviour:

- Read the original linked IY pointer from car **IX+7C/IX+7D** (physical state-slot +FC/+FD). Copy three master RAM bytes **E627, E628, E629** to the pointed-to linked record **IY+17, IY+18, IY+19**, in this exact little-endian order. This is a 24-bit CPU-memory snapshot; the real-world timer unit is **not** established.
- Use original car **IX−03** (physical slot +7D) as an index into a three-pointer table at fixed ROM **2D41**. The verified selectors 0,1,2 point to RAM words **ED20, ED18, ED10**, respectively. Other values are outside the documented three-entry domain and intentionally rejected.
- Read the chosen 16-bit RAM counter and execute original **INC DE**, wrapping modulo 65536. If incrementing **FFFF → 0000**, the original OR D,E / RET Z skips both stores: **the original FFFF remains FFFF**. Otherwise the updated counter is written low-byte and high-byte with original Z80 addressing.
- Preserve incoming IY with push/pop and execute the original **DI/EI** pair. This bounded stage ends with interrupts enabled, independently of the input interrupt state.

The strict original-opcode interpreter permits only genuine instructions and expected ROM/RAM addresses/calls, and reports unknown offsets rather than guessing.

**Private genuine Z80 parity:** **30,000** deterministic cases (10,000 per selector), **zero mismatches** for linked bytes, selected counter values/address, flag paths, saved IY, final interrupt state and return location. **4,280** cases exercised the FFFF skip-write; **25,720** cases incremented normally.

Public tool: tools/arcade_race_prestart_counter.py; ROM-free tests: tests/test_arcade_race_prestart_counter.py. SHA-256 signatures pinned for the original entry, body, two helpers and three-entry table.

## 2. Fixed master 31E9–3207, plus original helper 0A4F

After the original pre-start CALL **2CF9** returns, original master code:

1. Always clears global RAM bytes **E61F=0 and E69F=0**.
2. If global **E603 == 0** AND **E67B == 0**, original **RET Z at 31FA** exits. This leaves original E67C and the car+91 byte unchanged.
3. Otherwise write **E67B=1F** and **E67C=01**, then invoke original **0A4F**.
4. Original helper **0A4F** preserves AF/HL and performs original **car IX+11 (physical slot+91) = (old car+91 − low byte of ED59) & FF**. It restores A=01 on return, and execution proceeds to **3208**, beyond this bounded stage.

**Private original machine-code parity:** all **65,536** combinations of E603/E67B, with varied E67C, ED59 and car+91 bytes, plus **4,096 additional early-return edge cases**: **69,632 total, zero mismatches**. The deliberately rare E603=E67B=0 condition is explicitly stressed. The branch and byte-subtraction stages are separately SHA-256 pinned.

Public tool: tools/arcade_race_start_gate_31e6.py; regression: tests/test_arcade_race_start_gate_31e6.py.

This recovers the original linked-counter preamble and initial global/car adjustment, **not** all later startup calls at 3208 onwards.

## 3. Fixed 1190 → original master bank 4 at 20A8–213E

The previously unresolved original fixed-master **1190** target (reached along some original AI/race setup paths) contains two **far calls via fixed trampoline 14C1**. Original bytecode and bank-switching context confirm the calls, in this order:

1. **Bank 4, CPU address 20A8** — the newly recovered bounded racer-pointer selection stage.
2. **Bank 4, CPU address 2000** — separately recovered after this first-callee investigation; its bounded five-car and course-parameter behaviour is documented in **ARCADE_BANK4_RACE_INITIALIZER_2026-10-21.md**. Full downstream effects still remain open.

The first stage, **20A8–213E**, has an independently reconstructed model and strict interpreter of the authentic original bank-4 Z80 instructions:

- Early returns in priority order: **E603 != 0 → 20AC**, otherwise **E677 != 0 → 20B2**, otherwise **E67D != 0 → 20B7**.
- If E602 is nonzero, search five original linked car pointers from **E634, E632, E630, E62E, E62C** (fifth to first). Select the first whose original **IY+7E bit 6** is set; otherwise default to the first pointer. Original B receives that car's **IY+69 ordinal**. If E602 is zero, original B is the **FF sentinel**.
- Scan original pointers from **E62C** through **E634**, testing **IX+31 bit 0** and decrementing the original E63E byte where clear. The original **JP M** after DEC A selects when the **8-bit sign flag** becomes set.
- Compare original B with the selected IX car's **IX+69 ordinal** using **CP / JP M**, NOT a carry-based unsigned comparison. Depending on the original sign flag, either preserve IX and original E674 as C, or replace IX with the chosen IY pointer and set C=04.
- This first-callee selection stage stops **before original CALL 22BA at 213F**. Its full bounded numerical result has now been separately opcode-verified (docs/ARCADE_BANK4_METRIC_22BA_2026-10-21.md), and the second bank-4 2000 initializer is also verified. Full downstream in-race AI decisions remain open.

**Private genuine Z80 parity:** **50,000** cases, comparing original global exits and final IX/IY, A/B/C and pointer swap; **zero mismatches**. Branch coverage: **42,643** cases reached 213F, **2,942** returned at 20AC, **2,477** returned at 20B2, **1,938** returned at 20B7. All cases used permutations of original five ordinal bytes **0,1,2,3,4** and controlled car status bytes, not an invented 256-entry racer population.

Public tool: tools/arcade_bank4_racer_selection.py; regression: tests/test_arcade_bank4_racer_selection.py. Both the original far-call-site bytes and bank-4 stage have pinned source fingerprints.

## Verification and progress accounting

| Recovered original stage | Private original-opcode cases | Mismatches |
|---|---:|---:|
| Linked counter + 24-bit timestamp, 2CF9 | 30,000 | 0 |
| Race-start global gate + helper 0A4F | 69,632 | 0 |
| Bank-4 racer pointer selection, 20A8 | 50,000 | 0 |
| **This session** | **149,632** | **0** |

These are **bounded** verification inputs, not unique covered instructions, game runtime traces or a percent-complete measure. CI tests use ROM-free independent mathematical/boundary models. The **private authentic-ROM instruction checks** were run separately in the local analysis environment, never with ROM bytes in the public CI.

Three new public recovery/verifier modules, three ROM-free regression suites (28 tests) and this evidence report were added without touching Godot gameplay/camera, existing tests, circuit art or the approved original game constraints.

## Remaining whole-game blockers

- Original startup calls after **3208**, the downstream caller effects of the now-verified second bank-4 2000 initializer, and the post-22BA selection/control flow (despite the original 22BA numeric routine now being independently recovered).
- Original complete vehicle steering and handling, AI navigation/opponents, actual collisions/terrain, all fourteen dynamic circuit QRAM/collision masks, lap/pit gates, service/fuel/turbo/upgrades and championship presentation.
- Original Intel 80186 sound effects/commands and real multi-CPU/video timing.
- The working MAME debugger remains unavailable in this container: actual original race-phase RAM/video/CPU traces and per-circuit game-state verification cannot yet be claimed.

**Approved baseline protected:** original arcade track shapes/proportions, unchanged original racing mechanics and pace, portrait mobile camera with slow smooth bounded panning. **No guessed replacement game or Android APK. Gate A remains OPEN.**


## Follow-on original bank-4 recovery

The second fixed 1190 far call to bank4 2000–208B has now been independently recovered as a five-car status reset and fourteen-course control-parameter setup. It matched **95,536** additional actual original-Z80 instruction cases with **zero mismatches**; results and limitations are in **docs/ARCADE_BANK4_RACE_INITIALIZER_2026-10-21.md**. Critically, the original fixed 1190 order is 20A8 **before** 2000, so newly written E602 from 2000 does not retroactively affect 20A8's earlier choice in that call sequence. Full game Gate A remains OPEN.
