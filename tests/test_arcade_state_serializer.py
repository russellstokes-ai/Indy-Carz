"""ROM-free structural checks for arcade six-car 96-byte state serializer."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_state_serializer import (
    WORDS, SCRATCH_FIRST, SCRATCH_LAST, LOAD_BODY, SAVE_BODY,
    parse_block, validate_routine_wrappers, validate_six_car_loop,
    candidate_calls, validate_six_car_dispatch, inspect,
)


def fake_master():
    mem = bytearray(0x90000)
    mem[0x18C0] = 0xE9
    header = bytes.fromhex("f3 ed 73 2f e9 f9")
    footer = bytes.fromhex("ed 7b 2f e9 fb c9")
    for entry, end in ((0x61CE, 0x6294), (0x629A, 0x6360)):
        mem[entry:entry+6] = header
        mem[end:end+6] = footer
    for i in range(WORDS):
        ascending = SCRATCH_FIRST + i*2
        descending = SCRATCH_LAST - i*2
        mem[LOAD_BODY+4*i:LOAD_BODY+4*i+4] = bytes([
            0xE1, 0x22, ascending & 255, ascending >> 8])
        mem[SAVE_BODY+4*i:SAVE_BODY+4*i+4] = bytes([
            0x2A, descending & 255, descending >> 8, 0xE5])
    for i in range(6):
        start = 0xE000+i*0x100
        ix = start+0x80
        end = start+0x60
        pc = 0x5EA1 + i*19
        mem[pc:pc+19] = bytes([
            0x21, start & 255, start >> 8, 0xCD, 0xCE, 0x61,
            0xDD, 0x21, ix & 255, ix >> 8,
            0xCD, 0x1E, 0x60,
            0x21, end & 255, end >> 8, 0xCD, 0x9A, 0x62])
    for first, field in ((0x2D87, 0x94), (0x2E0E, 0x96)):
        for slot in range(6):
            base = 0xE000 + slot*0x100
            ix, pointer, save = base+0x80, base+field, base+0x60
            pc = first + slot*22
            mem[pc:pc+22] = bytes([
                0x21, base & 255, base >> 8,
                0xCD, 0xCE, 0x61,
                0xDD, 0x21, ix & 255, ix >> 8,
                0x2A, pointer & 255, pointer >> 8,
                0xCD, 0xC0, 0x18,
                0x21, save & 255, save >> 8,
                0xCD, 0x9A, 0x62,
            ])
    return mem


class StateSerializerTests(unittest.TestCase):
    def test_exact_48_word_transfer(self):
        mem = fake_master()
        validate_routine_wrappers(mem)
        loaded = parse_block(mem, LOAD_BODY, True)
        saved = parse_block(mem, SAVE_BODY, False)
        self.assertEqual((len(loaded), loaded[0], loaded[-1]),
                         (48, 0xE72B, 0xE789))
        self.assertEqual(list(reversed(loaded)), saved)

    def test_six_independent_256_byte_slots(self):
        records = validate_six_car_loop(fake_master())
        self.assertEqual(len(records), 6)
        self.assertEqual([c["slot_address"] for c in records],
                         ["E000", "E100", "E200", "E300", "E400", "E500"])
        self.assertEqual(records[-1]["IX_base"], "E580")
        self.assertEqual(records[0]["snapshot_end_stack_pointer"], "E060")
        self.assertTrue(all(c["snapshot_bytes"] == 96 for c in records))
        mem = fake_master()
        self.assertEqual(len(candidate_calls(mem, 0x61CE)), 6)
        self.assertEqual(len(candidate_calls(mem, 0x629A)), 6)

    def test_two_6_car_indirect_callback_passes(self):
        mem = fake_master()
        passes = validate_six_car_dispatch(mem)
        self.assertEqual(len(passes), 12)
        self.assertEqual([x["phase"] for x in passes],
                         ["first"]*6 + ["second"]*6)
        self.assertEqual(passes[0]["callback_pointer_address"], "E094")
        self.assertEqual(passes[5]["callback_pointer_address"], "E594")
        self.assertEqual(passes[6]["callback_pointer_address"], "E096")
        self.assertEqual(passes[11]["callback_pointer_address"], "E596")
        mem[0x18C0] = 0
        with self.assertRaisesRegex(ValueError, "trampoline"):
            validate_six_car_dispatch(mem)

    def test_reject_mutated_original_opcode(self):
        mem = fake_master()
        mem[0x61D4] ^= 1
        with self.assertRaisesRegex(ValueError, "discrepancy"):
            parse_block(mem, LOAD_BODY, True)

    def test_original_rom_required_for_real_report(self):
        with self.assertRaisesRegex(ValueError, "Original 1991 arcade"):
            inspect(fake_master())


if __name__ == "__main__":
    unittest.main()
