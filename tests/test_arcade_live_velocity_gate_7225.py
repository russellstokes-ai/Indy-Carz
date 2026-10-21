"""ROM-free tests for live original 1991 Z80 signed motion-word write audit."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_velocity_sign_gate_7225 import independent
from arcade_live_velocity_gate_7225 import audit_rows,CAR_POINTERS


def row(old=0,delta=1,ix=0xE080,frame=2500):
    predicted=independent(old,delta)
    return {
        "frame":str(frame),"pc":"7241","ix":f"{ix:04X}",
        "old_motion":f"{old:04X}","de_input":f"{delta:04X}",
        "hl_result":f"{predicted['stored_e76b']:04X}",
        "expected":f"{predicted['stored_e76b']:04X}",
        "correct":"1","branch":predicted["branch"]
    }


class LiveOriginalVelocityGateTests(unittest.TestCase):
    def test_original_four_signed_motion_branches(self):
        inputs=((0,1),(0x1234,1),(0x8000,1),(0x8000,0xFFFF))
        result=audit_rows([row(a,b,frame=2400+i) for i,(a,b) in enumerate(inputs)])
        self.assertEqual(result["actual_motion_word_writes"],4)
        self.assertEqual(result["observed_original_motion_gate_branches"],
            {"negative_clamp":1,"negative_keep":1,"positive_clamp":1,"positive_keep":1})
        self.assertEqual(result["original_live_arithmetic_mismatches"],0)

    def test_all_five_original_racing_pointers(self):
        result=audit_rows([row(0,1,ix=ix,frame=i+1)
                           for i,ix in enumerate(CAR_POINTERS)])
        self.assertEqual(len(result["original_car_ix_write_counts"]),5)

    def test_multiple_actual_instructions_same_frame_are_permitted(self):
        actual=audit_rows([row(0,1,frame=2600),row(0,2,frame=2600)])
        self.assertEqual(actual["actual_motion_word_writes"],2)

    def test_corrupt_original_stored_motion_detected(self):
        case=row(0x8000,65535)
        case["hl_result"]="0000"
        with self.assertRaisesRegex(ValueError,"arithmetic mismatch"):audit_rows([case])

    def test_wrong_original_predicted_register_detected(self):
        case=row()
        case["expected"]="BEEF"
        with self.assertRaisesRegex(ValueError,"arithmetic mismatch"):audit_rows([case])

    def test_wrong_branch_label_detected(self):
        case=row()
        case["branch"]="negative_keep"
        with self.assertRaisesRegex(ValueError,"arithmetic mismatch"):audit_rows([case])

    def test_original_reported_mismatch_fails_closed(self):
        case=row()
        case["correct"]="0"
        with self.assertRaisesRegex(ValueError,"arithmetic mismatch"):audit_rows([case])

    def test_wrong_real_original_cpu_site_or_car(self):
        for key,value in (("pc","7225"),("ix","0000")):
            case=row()
            case[key]=value
            with self.assertRaisesRegex(ValueError,"Z80 motion PC"):audit_rows([case])

    def test_original_16bit_field_overflow_rejected(self):
        case=row()
        case["de_input"]="10000"
        with self.assertRaisesRegex(ValueError,"invalid 16-bit"):
            audit_rows([case])

    def test_original_frame_order_strict(self):
        with self.assertRaisesRegex(ValueError,"frame order"):
            audit_rows([row(frame=2501),row(frame=2500)])

    def test_original_byte_boundary_math_is_not_float(self):
        case=row(old=1,delta=65535)
        self.assertEqual(case["hl_result"],"0002")
        self.assertEqual(audit_rows([case])["original_live_arithmetic_mismatches"],0)

    def test_empty_and_missing_source_fields_rejected(self):
        with self.assertRaisesRegex(ValueError,"empty"):audit_rows([])
        with self.assertRaisesRegex(ValueError,"missing columns"):
            audit_rows([{"frame":"1"}])


if __name__=="__main__":
    unittest.main()
