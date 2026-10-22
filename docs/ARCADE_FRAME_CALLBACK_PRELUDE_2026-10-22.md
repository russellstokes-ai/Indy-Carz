# Verified original 1991 Indy Heat per-car callbacks — 22 October 2026

**Engine recovery gate remains OPEN. No original ROM bytes published.**

The owner-provided `indyheat.zip` has been authenticated directly against
original ROM chip SHA-1 signatures. The reconstructed post-MAME-rotation master
Z80 region (589,824 bytes) exactly matches the previously recorded full-region
SHA-256:
`521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7`.

Three previously unimplemented original master bank0 Z80 stages were
interpreted privately from this authenticated image, with a separate independent
state model for each. Every stage stops at its first *unrecovered* external call:

1. **2EAF–2EC6 first per-car callback** — BIT1 IX+33 early return or
   exact IX+7E/IX+1E mask and IX+10/IX+56 initialization; stops at CALL 85B4.
   Original window SHA-256:
   `2b945e8c1699028d2f6088cdfde8d1b501dc1db376187f53f65f7f25c1102917`.
   **100,000 original instruction comparisons, zero mismatches.**
2. **3006–304C priority-ordered status dispatch** — nine exact original
   `BIT ...; CALL NZ` handler decisions plus IX+34 & 0x30 aggregation
   and fallthrough to original CALL 689D. Original window SHA-256:
   `3e37d1f36359bfdb082deeadb5b0ca9d0fc658138b7e62fde620161d75ee3cff`.
   **100,000 original instruction comparisons, zero mismatches.**
   Handler calls cannot be skipped when set, because an original handler can
   change the flags for subsequent instructions.
3. **30D5–30F7 callback vector prelude** — copies E96F/E971 into E77D/E77F,
   executes original EXX register semantics, OR IX+75, doubles E735
   with 16-bit carry, complements the high byte, and sets exact outgoing
   Z80 A/F/BC/DE/HL plus alternate BC/DE/HL. Requires authentic incoming
   A and HL. Stops at original JP D958. Original window SHA-256:
   `869119b2dff244b209ea2b53c38ada282989f23cccec24ca72d1d7383993b7bc`.
   **100,000 original instruction comparisons, zero mismatches.**

The bounded private interpreter and separate state models were compared in
**300,000 total original opcode cases, zero mismatches**. The new ROM-free public
regression suite exhaustively checks all 512 status combinations, four aggregate
variants, all five car slots, and exact callback vector states. Godot copies
the same bounded outputs; neither implementation embeds proprietary tables,
graphics, audio or disassembly.

**Crucial limitation:** This recovers callback *entry routing and a single
vector preparation*, not any called routine, the six-slot live scheduler,
frame timing, car/track collisions, AI, pits, turbo, fuel, races or full-game
MAME parity. No playable engine or build should be claimed from these tests.
Do not change original circuit layouts or the portrait camera while extracting
the complete master/slave/audio game engine. Never overwrite the protected
canonical driving baseline with unverified mechanics.

## Connected 1783→85B4 original linked-record continuation

The original master bank0 `85B4–85D7` calls fixed-master `1783`,
loads original IY from car IX+7C/7D, compares `(IY+1D)` to IX+04
(unsigned), and either returns or toggles IX+7E bit4, increments the
16-bit pointer stored at IY+1E/1F, and copies its pointed-to byte into
IY+1D. Exact previous writes are retained if a required read is outside
the available E000–FFFF RAM snapshot.

Original window SHA-256 hashes (no bytes published):
- `85B4–85D7`: `f92a4faf1c4d68ec956fef11b70190ebf0e7c52e0ba69c3c361060fb0fbfa7c7`
- `1783–178C`: `8870020766664bfcd4f50d3ec074b7efdfe67570af6de15f5ca389121d686418`

**100,000 further actual Z80 instruction comparisons, zero mismatches**:
25,305 unsigned early returns, 28,006 full RAM-pointer updates and
46,689 authentic stops at a CPU address requiring a different memory view.

The public connected bounded path is now original
`2EAF → CALL 85B4 → 1783 → 85B4 → 2EC7`, and checks the real
IX+31 BIT0 to select the 22B8 call or reach 2ED0. It never fakes
downstream callback behavior or master/slave frame scheduling. The
original circuit, camera, and gameplay appearance remain untouched.
