"""ROM-free regressions for the controlled MAME BC8C threshold-18 fallback."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_controlled_collision_fallback_audit import (
    FIELDS, EXPECTED, ORIGINAL_IX, RETRY_THRESHOLD, BACKUP_WORDS, audit_rows
)


def rows():
    return [{"frame":"2400","kind":kind,"pc":f"{pc:04X}",
             "ix":f"{ORIGINAL_IX:04X}","addr":f"{address:04X}",
             "correct":"1","counter":str(RETRY_THRESHOLD)}
            for kind,pc,address in EXPECTED]


class OriginalControlledFallbackTests(unittest.TestCase):
    def test_complete_real_cpu_write_order(self):
        result=audit_rows(rows())
        self.assertEqual(result["original_cpu_write_events"],30)
        self.assertEqual(result["original_restored_16bit_words"],11)
        self.assertEqual(result["original_restored_bytes"],22)
        self.assertEqual(result["original_source_byte_mismatches"],0)
        self.assertIn("NOT natural",result["source_kind"])

    def test_three_original_car_bytes_cleared(self):
        self.assertEqual([e[2] for e in EXPECTED if e[0]=="car_reset"],
                         [0xE0C1,0xE0CD,0xE0CC])

    def test_original_global_reset_bytes(self):
        self.assertEqual([(e[1],e[2]) for e in EXPECTED if e[0]=="global_reset"],
                         [(0xC46F,0xE76A),(0xC475,0xE76B),
                          (0xC475,0xE76C),(0xC47B,0xE765),(0xC47B,0xE766)])

    def test_exact_ordered_eleven_backup_pairs(self):
        expected=[(pc,base+i) for pc,base in BACKUP_WORDS for i in (0,1)]
        self.assertEqual([(pc,addr) for kind,pc,addr in EXPECTED if kind=="restore"],
                         expected)

    def test_single_missing_or_extra_write_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"exactly 30"):
            audit_rows(rows()[:-1])
        with self.assertRaisesRegex(ValueError,"exactly 30"):
            audit_rows(rows()+rows()[:1])

    def test_incorrect_original_source_byte_match_is_rejected(self):
        rs=rows()
        rs[12]["correct"]="0"
        with self.assertRaisesRegex(ValueError,"source/reset mismatch"):
            audit_rows(rs)

    def test_original_threshold_must_be_decimal_18_not_hex_17(self):
        for wrong in (0,17,23,24,255):
            rs=rows()
            rs[5]["counter"]=str(wrong)
            with self.assertRaisesRegex(ValueError,"counter not 18"):
                audit_rows(rs)

    def test_duplicate_or_reordered_source_destinations_rejected(self):
        rs=rows()
        rs[10],rs[11]=rs[11],rs[10]
        with self.assertRaisesRegex(ValueError,"PC or destination"):
            audit_rows(rs)

    def test_original_first_car_pointer_and_frame_are_fixed(self):
        rs=rows()
        rs[3]["ix"]="E180"
        with self.assertRaisesRegex(ValueError,"frame/car"):
            audit_rows(rs)
        rs=rows()
        rs[3]["frame"]="2401"
        with self.assertRaisesRegex(ValueError,"frame/car"):
            audit_rows(rs)

    def test_wrong_original_reset_instruction_rejected(self):
        rs=rows()
        rs[1]["pc"]="C468"
        with self.assertRaisesRegex(ValueError,"PC or destination"):
            audit_rows(rs)

    def test_untrusted_trace_fields_are_rejected(self):
        rs=rows()
        del rs[0]["pc"]
        with self.assertRaisesRegex(ValueError,"missing columns"):
            audit_rows(rs)
        rs=rows()
        rs[0]["addr"]="garbled"
        with self.assertRaisesRegex(ValueError,"Invalid controlled"):
            audit_rows(rs)


if __name__=="__main__":
    unittest.main()
