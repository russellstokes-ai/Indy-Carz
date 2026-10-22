# Indy Carz — bounded hardware memory replay for original 2B77

**22 October 2026. ENGINE RECOVERY STILL OPEN.**

The original Z80 2B77–2BCB instruction sequence was previously checked on
100,000 original-execution cases. It emits three port-F4 changes and eight
ordered memory writes. This change uses those existing bus events and the
MAME documented Ataxx/Indy Heat master memory maps to apply only *known*
effects to caller-supplied hardware memory snapshots:

- ROM window 0000–9FFF ignores CPU writes.
- In A000–DFFF, F4 bits 4–5 == 0x10 select battery RAM (0x4000 bytes).
- In A000–DFFF, F4 bits 4–5 == 0x20 select QRAM, indexed with
  `((F4 & 0xC0) << 8) | (address - 0xA000)` (0x10000 bytes).
- Other A000–DFFF views ignore writes.
- Each QRAM write records one partial-screen-update request and tilemap
  dirty index `((F4 & 0x80) << 8) | (address - 0xA000)`.
- Writes outside the mapped ROM or A000–DFFF windows fail closed
  **before** modifying any caller-supplied memory planes.

These are hardware-model results, not new original-Z80 opcode comparisons or
end-to-end MAME execution parity. The code explicitly avoids simulating beam
timing, video rendering, gameplay effects or the original CALL/RET aftermath
of 2BCC. Input ROM and original graphics are not bundled.

**Tests:** six ROM-free Python tests (all five car indices, 16 combinations
of QRAM planes, F4 view selection, low-byte wrapping, ROM no-op,
invalid inputs and atomic failure). Godot headless runner includes the
same QRAM and fail-closed check. No circuit, physics, camera or art changes.

**Next:** real MAME F4+QRAM traces, original CALL 2AD1 return semantics,
full frame scheduler/collisions/AI/fuel/pits/championships/audio.

MAME reference:
- https://github.com/mamedev/mame/blob/master/src/mame/cinematronics/leland.cpp
- https://github.com/mamedev/mame/blob/master/src/mame/cinematronics/leland_m.cpp
- https://github.com/mamedev/mame/blob/master/src/mame/cinematronics/leland_v.cpp
