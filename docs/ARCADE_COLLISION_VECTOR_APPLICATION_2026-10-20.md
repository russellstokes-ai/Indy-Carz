# Indy Carz — recovered original contact correction vectors and application

**Original source:** checksum-verified 1991 arcade Indy Heat, master Z80 ROM and X-ROM.  
**Recovery date:** 20 October 2026.  
**Status:** Two bounded routines recovered; complete collision physics and commercial release Gate A remain OPEN.

## Original correction-vector generator: B5C9–B63B

The original fixed-master routine occupies 115 bytes; SHA-256
a0df3e547120c5131deef88bd5df28851de30ba2815e4d73484fc6c7ae4a75d3.

Inputs:
- Seven-bit contact payload from E91B after the side selection at B5AC; actual physical force units remain unverified
- First car heading from IX-0x43, an 8-bit angle
- Original relative orientation category E922, limited to the sixteen high-nibble values 0,16,...,240
- Original signed 8-bit sine/cosine tables A500/A200 and signed saturated multiplication X-ROM slot 0

The original routine computes BC (first axis) and DE (second axis):

    phi = (heading + 128) & 255
    psi = (heading + E922 + 8) & 255
    mul(a,b) = clamp(signed8(a)*signed8(b)*2, -32768, 32767) & 65535
    ASR16(v,n) = (signed16(v) >> n) & 65535
    BC = ASR16((ASR16(mul(payload,cos8(phi)),1) +
                ASR16(mul(payload,cos8(psi)),2)) & 65535,4)
    DE = ASR16((ASR16(mul(payload,sin8(phi)),1) +
                ASR16(mul(payload,sin8(psi)),2)) & 65535,4)

Arithmetic shifts are signed, additions wrap to 16 bits, and the original
Z80 writes only the low byte to the X-ROM address port FFFC when changing
the trigonometric sample, retaining the multiply operand in its upper byte.

**Full original-domain parity:** all 128 payload values × 256 heading values
× 16 quantised relative heading values = 524,288 inputs. Independent formula
and bounded original Z80 opcode interpretation matched on 1,048,576 output
words, with ZERO mismatches. The source and ROM images remain private.
Public reproducer: tools/arcade_collision_b5c9_vector.py.
ROM-free tests: tests/test_arcade_collision_b5c9_vector.py.

## Original correction application: B63C–B67D

The next 66-byte original routine has SHA-256
26ded78ff150d95cb1669636a0a00b230400264a21007953288ff9bddb186c13.

It checks bit 1 of both indexed car state records at offset +0x7C.
This is an original eligibility branch; the status-bit's full semantics
have NOT yet been verified.

| First car status bit 1 | Second car status bit 1 | Original action |
|---|---|---|
| Set | Set | Jump to original B4EE; independently tests slot+7C bit0 for each car, restoring those with bit0 clear through verified BABB |
| Set | Clear | Double 16-bit BC/DE and translate second-car geometry via BA20 |
| Clear | Set | Double 16-bit BC/DE and translate first-car geometry via B985 |
| Clear | Clear | Translate first car via B985, then translate second with original borrow-dependent reversed BC/DE |

For the both-car branch, the original instructions preserve Z80 carry from
the first translator's last 16-bit coordinate addition. The reversal is:

    carry_from_first = int(old_first_slot_word(+0x12) + DE > 65535)
    reversed_BC = (-BC - carry_from_first) & 65535
    next_borrow = int(BC + carry_from_first > 0)
    reversed_DE = (-DE - next_borrow) & 65535

This is NOT ordinary symmetric negation: the outgoing carry from the first
car affects the second car's BC correction, and the next subtraction borrow
can affect the DE correction.

40,000 controlled original-code instruction-path comparisons matched the
independent assignment model, which composes the **separately verified**
B985/BA20 original geometry translation models. Zero mismatches. All
high-byte threshold transfers to original scheduler at CPU 1689 are surfaced
as unresolved, never silently treated as normal returns.

Public source: tools/arcade_collision_b63c_assignment.py.
ROM-free tests: tests/test_arcade_collision_b63c_assignment.py.

## Scope and next real blocker

**Recovered:** bounded contact-vector equations; car-selection branch
conditions; integer doubling/borrowing; geometry translation when its
original routine returns normally.

**Still open:** further impact, heading and velocity state processing from
B6ED onward (B67E–B6EC projection now verified), exceptional 1689 scheduling branch,
all damage/sound/event consequences, track/terrain collision, complete
original player/AI/fuel/pit mechanics, and game-runtime parity.

**Next target:** master fixed-ROM B67E–B8E4. Trace its per-car velocity/heading
updates and event flags with proper original bank and X-ROM contexts.

No Godot gameplay development, concept build or alternative racing physics
is authorised while complete original-engine Gate A remains open. Do not
commit original ROM, disassembly, source sprites or audio to public GitHub.


### B4EE alternative path subsequently recovered

Fixed-master B4EE–B505 is now fully verified as a conditional per-car BABB restoration dispatcher: slot+7C bit0 clear triggers restoration; bit0 set skips it. 50,000 original-opcode vs independent cases, zero mismatches, including all four status combinations. See docs/ARCADE_COLLISION_RESPONSE_2026-10-20.md. The 111-byte B67E–B6EC dual-car velocity projection was also recovered with 50,000 original-code parity cases; see docs/ARCADE_COLLISION_VELOCITY_PROJECTION_2026-10-20.md. Full contact effects and original-engine Gate A remain open.
