# Original arcade collision movement projection — master B67E–B6EC

**Date:** 20 October 2026  
**Evidence:** checksum-verified original *Indy Heat* (1991 arcade rev 1) master Z80 and X-ROM. Original binaries and decoded game assets remain private.  
**Recovery status:** one bounded original routine **VERIFIED**; whole-engine Gate A **OPEN**.

## Exact bounded original behaviour

The original fixed-master routine occupies **111 bytes**, CPU addresses **B67E–B6EC**. SHA-256: b1019935ece77d5bb7889204288047c1079f301e2b59fb76a782b711ca441adb. Its body begins at **B699**. When master RAM **E919 bit 5** is set, the original instructions exchange active IX/IY car pointers before calling the common body, then restore them after the complete call. For this bounded stage, either ordering is reproduced exactly.

For each active 256-byte slot (original IX/IY pointers 0x80 bytes into its record):

- **Slot +0x3F:** heading, unsigned 256-step index into the original A200 cosine and A500 sine tables.
- **Slot +0x41:** signed input byte used by this stage. Its wider gameplay meaning and update timing are **not established**.
- Original SRA A; ADC A,0 converts that signed byte to ceil(signed8(value)/2), which is not unsigned division and is not arithmetic right shift alone.
- Original X-ROM slot-0 signed 8×8 multiply, doubled and positively saturated, supplies the high result byte for each trigonometric component. The code writes the full lookup address at FFFC, then changes only its high address byte through FFFD for the second lookup.

The routine stores the first car's projected **sine, cosine bytes** at E91F,E920; the second pair at E923,E924.

Finally, original SUB with conditional overflow helper **0B35** calculates:

    D = sat_signed8(E924 - E920)  # second cosine minus first cosine
    E = sat_signed8(E923 - E91F)  # second sine minus first sine

All six output bytes (E91F, E920, E923, E924, D, E) are verified independently. The helper uses original Z80 overflow condition PE and returns +127 or -128 as appropriate. Its instruction sequence is SHA-256 pinned.

## Original-code parity evidence

- **50,000** deterministic, varied two-car original instruction executions against a separate integer/formula implementation: **zero six-byte output mismatches**.
- **25,000** cases on each original E919 bit-5 car-order path.
- **512/512** original sine and cosine bytes checked against independent 256-step mathematical reconstruction.
- **65,536/65,536** original X-ROM slot-0 high-result lookup bytes checked against independent signed-multiply mathematics.
- **Six ROM-free unit tests** cover signed negative rounding, heading axes, pointer swapping, independent subtraction saturation boundaries, and invalid-input rejection.

Original X-ROM and master SHA-256 values are pinned in tools/arcade_collision_velocity_projection.py. The verifier executes only approved instruction forms and fails closed on unexpected opcode, I/O, address or checksum. Original input ROMs are passed **locally**, never stored in public CI.

To rerun privately after tools/arcade_rom_recovery.py reconstructs arcade regions:

    python tools/arcade_collision_velocity_projection.py \
      local/rom-recovery/master.mame_runtime.bin \
      local/rom-recovery/xrom.mame_runtime.bin --cases 50000

ROM-free checks:

    python -m unittest discover -s tests -p 'test_arcade_collision_velocity_projection.py'

## Explicit limitations

The routine calculates projected signed bytes and relative components; it does **not** prove the meaning of collision impulse, damage, car fuel, terrain drag, speed integration or full race dynamics. The saturation helper is independently boundary-tested but was not dynamically exercised through an overflowing projection in the 50,000 varied car records.

**Next extraction:** continue from **B6ED** through the remainder of the original contact response, including event classification, subsequent IX/IY state modifications, original B4EE alternative branch and diagnostic scheduler 1689. Controlled live MAME car-state traces and remaining game subsystems are still needed. No new playable Godot physics, track or APK is authorised or claimed. Track geometry and approved portrait camera presentation remain unchanged.
