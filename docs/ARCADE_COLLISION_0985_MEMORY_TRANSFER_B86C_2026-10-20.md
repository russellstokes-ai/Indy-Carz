# Original 0971 deeper transfer and B86C collision call selection

**Date:** 20 October 2026  
**Source:** authenticated user-owned 1991 *Indy Heat* arcade rev-1 ROM, held privately.  
**Outcome:** two bounded original CPU stages independently modelled and compared with interpreted original Z80 instructions. No original ROM, game art, sampled graphics, audio or disassembly is in the public repository.

## 1. Full 0985–0A22 memory transfer after original 0971 early-return gates

The original 158-byte fixed-master routine at **0985–0A22** (SHA-256
`d00a02f4bbf08f44769a9eebc283614f4cce2df3041cef1d5b75108d66529181`)
is now reconstructed as a **bank-controlled 24-byte memory transfer**, not an ordinary vehicle physics update.

It is reached only if the 0971 entry tests do **not** return at 0975, 097F or 0984. The initial B register contains the earlier 0971 call's input accumulator, while the original C register is inherited from the caller. This bounded verifier checks B indices **0–11** because the original fixed-master 289F table contains twelve two-byte source pointers. Unsupported selector values fail closed.

1. Store old master banking byte from E608 on the Z80 stack, clear its low nibble, write E608 and output the control byte via original port F4.
2. Use original helper **176A–1774** to select a source pointer from twelve 16-bit entries beginning at **289F**. The helper and pointer table are individually SHA-256 checked; proprietary source payloads remain in the private ROM.
3. Set active memory-bank control from **E613** and copy **twelve source bytes** using original Z80 LDI: four consecutive destination addresses, then increment destination D and subtract four from E, repeated for three rows.
4. Set control from **E615**, combined with the previous low-nibble control bits. Reverse the two D increments and four E increments, then copy another twelve source bytes at the corresponding three rows and four columns, using the newly selected bank. These are **two sets of twelve write events to the same address footprint under potentially different F4 control values**. Which physical RAM/QRAM plane(s) the controls select is not yet confirmed with live MAME.
5. Restore the low-nibble bank selection, then pop and restore the exact original E608 control value. **Five F4 port writes** occur for every complete execution.

**Important precision:** original LDI increments HL and the full 16-bit DE, and decrements the full 16-bit BC. If initial destination E is near FF, the carry into D occurs *in addition to* the routine's explicit INC D, so an ordinary hardcoded rectangular stride would be incorrect. Original B/C final values also depend on incoming C and carry from the 24 decrements. The independent model and original-opcode executor explicitly preserve these details.

### Original-ROM bounded verification (performed privately)

| Coverage | Result |
|---|---:|
| Independently generated original-code cases | **50,000** |
| Output, bank, write-event, pointer or register mismatches | **0** |
| Original source selectors covered | **12 / 12** |
| Z80 LDI bus write events checked per case | **24** |
| Original F4 writes checked per case | **5** |
| Cases with initial destination low-byte E at FC–FF | **791** |
| Cases with identical initial two control bytes | **2,208** |
| ROM-free unit regressions | **8 passed** |

The verifier captures **ordered CPU bus write events**, not a rendered framebuffer. Its source reads use the known MAME-rotated original master bank ROM views. It does *not* independently verify destination hardware memory mapping, visual meaning, sound effects or actual collision severity. Live MAME is still essential to establish these.

Public code: `tools/arcade_service_0985_bank_copy.py`; regression tests:
`tests/test_arcade_service_0985_bank_copy.py`. The original stage,
source-index helper and private pointer table have pinned checksums.

To repeat private original-code parity:

    python tools/arcade_service_0985_bank_copy.py \
      local/rom-recovery/master.mame_runtime.bin --cases 50000

To run public ROM-free synthetic checks:

    python -m unittest discover -s tests -p test_arcade_service_0985_bank_copy.py

## 2. Exact original B86C–B883 two-car B884 dispatch

Original fixed-master **B86C–B883** (24 bytes, SHA-256
`ce97b9878481042b4fad94ba2488d32b6ec8b8b2b2335649655b1e06a9cdb746`)
checks original car status **bit 1 of physical slot+0x7C**. It conditionally calls **B884** for the first car when that bit is clear, and independently calls B884 for the second car when its bit is clear. The second-car call temporarily swaps the original IX and IY pointers and restores IX afterwards.

| First car bit 1 | Second car bit 1 | Actual original B884 call order |
|---|---|---|
| Set | Set | No calls |
| Clear | Set | First car |
| Set | Clear | Second car |
| Clear | Clear | First car, then second car |

**All 65,536** possible pairs of full 8-bit status values were executed against original bounded machine-code instructions and compared with the independent call-order model; **zero mismatches**, with 16,384 scenarios in each of the four rows. **Seven** ROM-free regression tests pass.

Public verifier: `tools/arcade_collision_b86c_dispatch.py`; tests:
`tests/test_arcade_collision_b86c_dispatch.py`.

**This recovery is for the dispatcher ONLY.** The effects of the called original **B884–B8E3** routine remain unknown until its nested BC8C logic, state transfers and potential nonlocal branch are fully understood. These calls must not be approximated as damage, restitution, invulnerability or recovery actions simply because they occur in the contact path.

## Next commercial-game extraction gates

- Recover full **B884–B8E3** independently, including nested **BC8C** callbacks and exact status/RAM modifications.
- Decode remaining **B778–B86B** contact response and related B8E4 code, with original trig/X-ROM behaviour.
- Obtain debugger-enabled original MAME gameplay traces and actual E608/E613/E615 bank-to-memory mapping; capture all 14 original circuit surfaces, collision masks and lap/pit boundaries.
- Recover end-to-end original driving input, acceleration, grip, AI, turbo, fuel, repairs, upgrade economy, results and championship flow.

**Engine extraction Gate A remains OPEN.** The protected Godot camera, canonical circuit constraints and existing verified gameplay helpers were not modified. No preview/demo/APK or substitute physics was created.

## 3. Original B884–B8AB car working-state transfer and external callback gate

**New bounded original Z80 recovery:** fixed-master **B884–B8AB**, 40 actual instruction bytes, SHA-256 `f58c8693bb5d44cf4507d94b6cb73c8f116736da8f7d6a090ab8710704438dce`.

For an original car-state IX pointer 0x80 bytes into its 0x100-byte slot, the verified entry performs:

1. PUSH IX; POP HL; ADD HL,0xFF80. This selects the **start of that car's physical 256-byte record**.
2. Set DE=E72B and BC=0x0014, then original **LDIR transfers exactly twenty bytes** from the record's offsets 0–19 into the master shared working-state buffer E72B–E73E. The remaining original 96-byte scratch-state region is not modified by this first copy.
3. Write **E941 = 0xFF** and invoke the original **BC8C** callback. **BC8C is deliberately left opaque:** we do not execute, reproduce or claim its original effects.
4. After that callback returns, original code takes the high nibble of **E608**, ORs it with **0x05**, writes E608 and outputs the same byte on **port F4**.
5. Increment the byte read from **E941**. If its post-callback value was 0xFF, the increment reaches zero and the original **RET Z at B8AB** returns; otherwise the original code proceeds to **B8AC**, whose full path remains unverified.

The independent copy+gate model and bounded real-original-opcode interpreter agree on **30,000 cases, zero mismatches**, with 15,000 cases for each hypothetical callback-outcome branch. Both verified exit categories deliberately use *controlled post-callback E941/E608 inputs*; the case mix is NOT a measured gameplay frequency or a claim that BC8C behaves according to a guessed model. The remaining BC8C side effects cannot be proven by simulating its return alone.

**Seven ROM-free regression tests pass.** Public verifier:
`tools/arcade_collision_b884_callback_gate.py`;
tests: `tests/test_arcade_collision_b884_callback_gate.py`.

Original-ROM gated rerun:

    python tools/arcade_collision_b884_callback_gate.py local/rom-recovery/master.mame_runtime.bin --cases 30000

### Next: the actual BC8C callback and B8AC–B8E3

The exact B884 entry and return gate are now characterised, but **the content of BC8C and what the subsequent 0x42-byte state restoration does remain OPEN**. We must map bank-5 internal calls, E941 producer/consumer, actual memory spaces and any nonlocal diagnostic/scheduler transfers before assigning impact, damage, knockback or other gameplay effects.

There is no change to the approved original track geometry, original engine-first development gate or Godot camera baseline.
