# Original Z80 2B77–2BCC banked hardware bus trace

**22 October 2026.** Recovered original master CPU instructions at
`2B77–2BCB`, opcode SHA-256
`5f4c37f23712d3c5ef974201f74a11bd66c1bf34af2fb1a2dd12c71447189171`.

The original CPU performs three ordered OUT writes to port `F4` and eight
ordered bank-tagged memory writes. It does not simply copy eight contiguous
bytes into ordinary RAM:

- `bank1 = (E608 & 0x0F) | E613`, write to `E608`, OUT F4.
- `target = ((IX+13)<<8 | (IX+12)) + 0x0108` (16-bit wrap).
- Under bank1, write E900, E902, E904, E906 to four addresses by
  incrementing **E only**. D does not increment when E wraps.
- `bank2 = (bank1 & 0x0F) | E615`, write to E608, OUT F4.
- Under bank2, write E907, E905, E903, E901 to the same four
  addresses in reverse order, decrementing **E only**.
- Restore `E608 = bank2 & 0x0F`, OUT F4, then reach original RET at `2BCC`.

**Original-code verification:** 100,000 independent Z80 opcode comparisons,
zero mismatches; 300,000 ordered F4 writes and 800,000 ordered memory bus
writes matched. This includes 897 cases where the destination low byte
wrapped. The private verifier checks actual original instructions and
compares full resulting master RAM plus the ordered bus event sequence.

The public Godot module records the bus events and final E608 control
state. It now also classifies destinations in the **MAME-verified**
A000–DFFF F4 memory view without mutating QRAM or assuming a visible
gameplay effect. See [master F4 mapping](ARCADE_MASTER_F4_BANK_MAPPING_2026-10-22.md). With caller-provided
authentic bank0 source bytes, the per-car path now connects
`2AD1 → 2AD6 → 2B77`, and stops at `2BCC` before the unverified
hardware return semantics. Without source bytes, it stops before the
first original LDI.

**Still unresolved:** The active F4 latch at every live entry point,
QRAM screen/tilemap side effects, event meaning, master/slave CPU
coordination, and complete end-to-end replay of the event path.
The physical F4 ROM and A000–DFFF QRAM/battery mapping is now grounded
in MAME's hardware implementation, but authentic runtime traces are
still required before applying gameplay-visible effects. No proprietary
ROM, tables, circuits, graphics or audio are included in public code.

Original circuit geometry and approved portrait camera remain untouched.