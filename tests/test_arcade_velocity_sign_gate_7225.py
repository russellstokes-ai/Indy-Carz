"""ROM-free original arcade Z80 7225 signed motion gate tests."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_velocity_sign_gate_7225 import (
    START,STOP,STAGE_SHA,independent,original_opcodes,verify
)


class OriginalVelocitySignGateTests(unittest.TestCase):
    def test_original_bounded_stage_and_checksum(self):
        self.assertEqual((START,STOP),(0x7225,0x7245))
        self.assertEqual(len(STAGE_SHA),64)

    def test_positive_side_keep(self):
        actual=independent(0x1234,0x0001)
        self.assertEqual((actual["stored_e76b"],actual["branch"]),
                         (0x1233,"positive_keep"))

    def test_positive_side_clamps_sign_crossing(self):
        actual=independent(0,1)
        self.assertEqual((actual["stored_e76b"],actual["branch"]),
                         (0,"positive_clamp"))
        self.assertEqual(independent(0x7FFF,0xFFFF)["branch"],"positive_clamp")

    def test_negative_side_keep(self):
        actual=independent(0x8000,0xFFFF)
        self.assertEqual((actual["stored_e76b"],actual["branch"]),
                         (0x8001,"negative_keep"))

    def test_negative_side_clamps_wraparound_crossing(self):
        actual=independent(0x8000,1)
        self.assertEqual((actual["stored_e76b"],actual["branch"]),
                         (0,"negative_clamp"))

    def test_zero_motion_with_zero_delta(self):
        actual=independent(0,0)
        self.assertEqual((actual["stored_e76b"],actual["branch"]),
                         (0,"positive_keep"))

    def test_original_z80_wrap_is_not_host_signed_math(self):
        actual=independent(1,65535)
        self.assertEqual((actual["stored_e76b"],actual["branch"]),
                         (2,"positive_keep"))

    def test_original_ex_de_hl_swaps_registers(self):
        for old,delta in ((1,1),(0xFFFF,0),(0x7FFF,0x8000),
                          (0x8000,0),(0x8000,65535)):
            actual=independent(old,delta)
            self.assertEqual(actual["hl_after"],delta)
            self.assertEqual(actual["de_after"],actual["stored_e76b"])
            self.assertEqual(actual["next_pc"],STOP)

    def test_exhaustive_original_16bit_boundaries(self):
        for old in (0,1,2,0x7FFE,0x7FFF,0x8000,0x8001,0xFFFE,0xFFFF):
            for delta in (0,1,2,0x7FFE,0x7FFF,0x8000,0x8001,0xFFFE,0xFFFF):
                actual=independent(old,delta)
                candidate=(old-delta)&65535
                expected=candidate if bool(old&32768)==bool(candidate&32768) else 0
                self.assertEqual(actual["stored_e76b"],expected)

    def test_bad_input_and_untrusted_original_fail_closed(self):
        for a,b in ((-1,0),(65536,0),(0,-1),(0,65536)):
            with self.assertRaises(ValueError):independent(a,b)
        with self.assertRaises(ValueError):original_opcodes(bytes(5),0,0)
        with self.assertRaisesRegex(ValueError,"Authenticated"):
            verify(bytes(0x90000),0)


if __name__=="__main__":unittest.main()
