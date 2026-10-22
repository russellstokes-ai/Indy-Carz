# Indy Heat master F4 bank mapping — 22 October 2026

MAME hardware reference: mamedev/mame src/mame/cinematronics/leland.cpp,
leland_m.cpp and leland_v.cpp. This is a ROM-free hardware mapping recovery,
not proof of full-game parity.

The master Z80 CPU 2000–9FFF window is banked. Port F4 low four bits select
one of 16 ROM banks. MAME-rotated master-region offsets are bank0 0x02000,
then banks1–15 0x18000 through 0x88000 in 0x8000 increments.

All 512 event-table bytes at CPU 3F00–40FF are banked, correcting earlier
notes that only 4000+ might be banked. The exact mapped region offset is
bank_base[F4 & 15] + CPU_address - 0x2000.

For CPU A000–DFFF, F4 bits 4–5 select: 0x10 battery RAM, 0x20 QRAM,
otherwise fixed read-only ROM. QRAM index is ((F4 & 0xC0) << 8)
plus CPU_address - 0xA000. MAME also performs screen partial updates
and marks tilemap entries dirty on QRAM writes.

New public modules resolve banked ROM reads and classify hardware writes
using caller-supplied MAME-rotated images and the actually observed F4
latch. They never assume E608 is synchronized with the physical latch,
embed original ROM data, or apply unverified game/video side effects.

Independent synthetic tests cover all 256 F4 values, all 16 ROM banks,
all four event staging groups, bank rotation, and four QRAM planes.

Remaining: observe the live F4 latch across original event calls in MAME,
validate full QRAM effects and frame scheduling, then integrate the
remaining collision, AI, pits, damage, race and audio systems.

MAME source:
https://github.com/mamedev/mame/blob/master/src/mame/cinematronics/leland_m.cpp
https://github.com/mamedev/mame/blob/master/src/mame/cinematronics/leland.cpp
https://github.com/mamedev/mame/blob/master/src/mame/cinematronics/leland_v.cpp
