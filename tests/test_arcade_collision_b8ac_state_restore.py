"""ROM-free regression for the original B8AC post-BC8C state restoration."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_collision_b8ac_state_restore import (
    START, STOP, COPY_LEN, SCRATCH_LEN, independent, pinned_original, synthetic_cases
)

def record(status=0):
    b=bytearray(256)
    b[0xB1]=status
    b[0x7C]=0x20
    return bytes(b)

def scratch(dx=0,dy=0):
    b=bytearray(SCRATCH_LEN)
    b[0x1F]=100;b[1]=(100+dx)&255
    b[0x29]=200;b[0x0B]=(200+dy)&255
    return bytes(b)

class B8ACExactTests(unittest.TestCase):
    def test_original_size_and_copy(self):
        self.assertEqual((START,STOP,COPY_LEN),(0xB8AC,0xB8E4,0x42))
        src=scratch(1,2)
        decision,car=independent(record(),src)
        self.assertEqual(car[:66],src[:66])
        self.assertEqual(decision,"normal_return_unchanged_status")

    def test_first_difference_escape(self):
        for dx in (6,10,128,249):
            decision,_=independent(record(0x80),scratch(dx,0))
            self.assertEqual(decision,"nonlocal_1689_first_coordinate")

    def test_second_difference_escape(self):
        for dy in (6,16,240,249):
            decision,_=independent(record(),scratch(5,dy))
            self.assertEqual(decision,"nonlocal_1689_second_coordinate")

    def test_original_wraparound_boundaries_are_normal(self):
        for delta in (0,1,2,3,4,5,250,251,252,253,254,255):
            decision,_=independent(record(),scratch(delta,delta))
            self.assertEqual(decision,"normal_return_unchanged_status")

    def test_status_bit1_when_bit7_set_and_geometry_normal(self):
        decision,car=independent(record(0x80),scratch(5,251))
        self.assertEqual(decision,"status_bit1_set")
        self.assertEqual(car[0x7C],0x22)

    def test_both_escapes_precede_flag_write(self):
        first,car=independent(record(0x80),scratch(7,9))
        self.assertEqual(first,"nonlocal_1689_first_coordinate")
        self.assertEqual(car[0x7C],0x20)

    def test_source_and_original_unknown_fields_untouched(self):
        original=bytearray(record())
        original[0x81]=173
        src=scratch()
        _,changed=independent(bytes(original),src)
        self.assertEqual(changed[0x81],173)
        self.assertEqual(changed[0x42:0x7C],original[0x42:0x7C])

    def test_deterministic_model_synthetic_matrix(self):
        sample=synthetic_cases(100)
        self.assertEqual(sum(sample["counts"].values()),100)

    def test_invalid_inputs_and_forged_rom_rejected(self):
        with self.assertRaises(ValueError):independent(bytes(255),scratch())
        with self.assertRaises(ValueError):independent(record(),bytes(95))
        with self.assertRaisesRegex(ValueError,"checksum-verified"):
            pinned_original(bytes(0x90000))
        with self.assertRaises(ValueError):synthetic_cases(-1)

if __name__=="__main__":unittest.main()
