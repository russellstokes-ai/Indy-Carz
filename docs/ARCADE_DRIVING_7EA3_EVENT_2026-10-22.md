# Original Indy Heat event dispatch: 7EA3–7F32

**Recovery checkpoint: 22 October 2026.** This is a bounded original-Z80 engine
recovery, not a claim that the full arcade engine, race loop or mobile game is
finished.

## Authenticated original instruction boundaries

- Main master bank 0: \`7EA3–7F32\` (event dispatch, reuse, allocation, record setup).
- Allocator: \`8659–8693\`, 16 slots of 16 bytes at master RAM \`E800–E8FF\`.
- Course lookup: fixed \`1767–1774\` selects a 20-byte course block from the
  14-entry pointer table at \`8282\`; fixed \`174E–1766\` selects a four-byte
  per-car event tuple. Five cars, four bytes each, in original E,D,L,H order.
- Normal return from the caller's \`7E5E\` is \`7091\`, then the existing
  \`7092\` car-ID gate and possible \`2AD1\` call.
- \`8022\` invokes the much larger \`0971\` collision service. Its effects are
  **not** modelled by this stage and execution stops there.
- Missing authentic course data stops at the original \`1767\` call, retaining
  the exact already-executed event-record prewrites.

The stage sets \`IX+31\` bit 6 and \`IX+7E\` bit 3. A qualifying event may
reuse an earlier slot, reject allocation, allocate the first free slot, or
replace the earliest strictly lower-priority slot. Successful allocation
initializes the original event record, including its priority, car ID, course
coordinates, flags and countdown. Reuse updates only the original four fields.

**Decoder caution:** The actual \`DD 75 64\` opcode stores register **L** at
\`(IX+64)\`, not IXL. Similarly \`DD 6E 64\` loads **L** from \`(IX+64)\`.
Some linear disassembly labels are misleading here. The recovered implementation
uses the actual instruction semantics.

## Independent verification

A private, SHA-256 authenticated master image was reconstructed from the owner's
earlier private disassembly archive. An independent integer/state model was
compared with a bounded interpreter executing the original Z80 instruction bytes,
including \`8659\`, \`1767\` and \`174E\`. The interpreter does **not** execute
the unresolved \`8022\` call.

- **100,000 original-opcode comparisons: zero mismatches**, including external
  stop, event reuse, allocator rejection, free allocation, replacement and
  missing-course-data stop.
- All **14 original course pointers and 70 original per-car event tuples**
  were also checked against the original opcode path, without publishing their
  proprietary values.
- Public Python tests cover exact record writes, allocator priority ties,
  reuse, collision stop, missing lookup and fail-closed invalid inputs.
- Godot headless tests cover the new stage across all five physical car slots.
  The original 7017 driving pipeline now resumes only on an authentic
  \`7091\` return. It stops on unresolved \`8022\`, \`1767\`, \`7F1A\` or
  \`2AD6\` paths.
- No original ROM, source listings, artwork, music or course-table contents
  are committed to GitHub. The Godot API requires caller-provided table bytes.

## Still open — required before 100% engine acceptance

1. Original \`8022 → 0971\` collision-service effects, nested contact dispatch
   and complete car/terrain collision resolution.
2. Original \`2AD6\` banked event path and \`7F33+\` event execution/lifecycle.
3. Real original frame scheduler, six-slot callback timing, AI and opponents.
4. Fuel, turbo, damage, repairs, pits, upgrades, race rules, championships,
   economy, audio and all other master/slave/audio CPU interactions.
5. Whole-race original-running MAME state comparisons and repeatable
   deterministic gameplay parity, beyond isolated instruction windows.

Original circuit geometry and the approved portrait camera were not changed.
