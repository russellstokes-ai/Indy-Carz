"""ROM-free regressions for authentic arcade master 2CF9 counter snapshot."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_race_prestart_counter import (
    COUNT_ADDRESSES, TABLE, SIGNATURES, independent, actual_opcodes, verify,
)


class OriginalPrestartCounterTests(unittest.TestCase):
    def test_original_entry_and_table_address(self):
        self.assertEqual(TABLE,0x2D41)
        self.assertEqual(COUNT_ADDRESSES,(0xED20,0xED18,0xED10))
        self.assertEqual(SIGNATURES[0][:2],(0x2CF9,0x2CFE))

    def test_all_three_original_counter_selectors(self):
        for selector,address in enumerate(COUNT_ADDRESSES):
            actual=independent(selector,0x123456,42)
            self.assertEqual(actual["counter_address"],address)
            self.assertEqual(actual["counter"],43)
            self.assertEqual(actual["linked"],[0x56,0x34,0x12])

    def test_counter_ffff_is_not_overwritten_with_zero(self):
        for index in range(3):
            result=independent(index,0,0xFFFF)
            self.assertEqual(result["counter"],0xFFFF)
            self.assertFalse(result["counter_write"])
            self.assertEqual(result["original_return_pc"],0x2CF4)

    def test_counter_fffe_reaches_ffff(self):
        result=independent(0,0xABCDEF,0xFFFE)
        self.assertEqual(result["counter"],0xFFFF)
        self.assertTrue(result["counter_write"])
        self.assertEqual(result["original_return_pc"],0x2CF8)

    def test_16bit_carry_is_preserved(self):
        self.assertEqual(independent(1,0,0x00FF)["counter"],0x0100)
        self.assertEqual(independent(1,0,0x7FFF)["counter"],0x8000)

    def test_original_snapshot_is_little_endian(self):
        self.assertEqual(independent(2,0xFFFFFF,0)["linked"],[255,255,255])
        self.assertEqual(independent(0,0x800100,0)["linked"],[0,1,128])

    def test_unconditional_original_ei_and_saved_iy(self):
        result=independent(2,0,0,previous_iy=0x5ABC)
        self.assertTrue(result["interrupts_enabled"])
        self.assertEqual(result["final_iy"],0x5ABC)

    def test_invalid_selector_timestamp_count_or_pointer(self):
        for args in ((-1,0,0,0xE900,0),(3,0,0,0xE900,0),
                     (0,1<<24,0,0xE900,0),(0,0,65536,0xE900,0),
                     (0,0,0,0x1234,0),(0,0,0,0xE900,65536)):
            with self.assertRaises(ValueError):independent(*args)

    def test_untrusted_master_rejected(self):
        with self.assertRaises(ValueError):
            actual_opcodes(bytes(0x90000),0,0,0)
        with self.assertRaisesRegex(ValueError,"Authenticated original"):
            verify(bytes(0x90000),0)


if __name__=="__main__":
    unittest.main()
