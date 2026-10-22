"""ROM-free regression: authentic Z80 73F6 angular steering control."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_drive_73f6_steering_control import (
    START,STOP,STAGE_SHA,HELPER_SHA,SATURATION_SHA,
    independent,original_z80,verify
)


class OriginalSteering73F6Tests(unittest.TestCase):
    def test_exact_original_stage_and_three_helper_signatures(self):
        self.assertEqual((START,STOP),(0x73F6,0x7442))
        self.assertTrue(all(len(x)==64 for x in
                            (STAGE_SHA,HELPER_SHA,SATURATION_SHA)))

    def test_original_car_sign_matches_nonnegative_angular(self):
        control=independent(0x0400,0,0,0,0)
        self.assertEqual(control["angular_sample"],8)
        self.assertTrue(control["direction_matches"])
        self.assertEqual(control["a"],72)

    def test_original_car_sign_matches_negative_angular(self):
        control=independent(0xFC00,0,0,0,0x80)
        self.assertEqual(control["angular_sample"],-8)
        self.assertTrue(control["direction_matches"])
        self.assertEqual(control["a"],72)

    def test_original_opposite_direction_diminishes_steer_angle(self):
        control=independent(0x0400,0,0,0,0x80)
        self.assertFalse(control["direction_matches"])
        self.assertEqual(control["a"],56)
        opposite=independent(0xFC00,0,0,0,0)
        self.assertEqual(opposite["a"],56)

    def test_original_positive_and_negative_saturations(self):
        large_positive=independent(0x7FFF,0,0,0,0)
        large_negative=independent(0x8000,0,0,0,0x80)
        self.assertEqual(large_positive["angular_sample"],127)
        self.assertEqual(large_negative["angular_sample"],-128)
        self.assertEqual((large_positive["a"],large_negative["a"]),(127,127))
        self.assertEqual(independent(0x7FFF,0,0,0,0x80)["a"],32)
        self.assertEqual(independent(0x8000,0,0,0,0)["a"],32)

    def test_original_first_sbc_borrow_propagates_to_second(self):
        control=independent(0,0xFFFF,0,0x007F,0)
        self.assertEqual(control["borrow_from_first_subtraction"],1)
        self.assertEqual(control["wrapped_word"],0x007F)
        self.assertEqual(control["a"],64)
        changed=independent(0,0xFFFF,0,0x0080,0)
        self.assertEqual(changed["wrapped_word"],0x0080)
        self.assertEqual(changed["a"],65)

    def test_original_exact_all_word_values_in_independent_model(self):
        for word in range(65536):
            for direction in (0,128):
                value=independent(word,0,0,0,direction)
                self.assertTrue(32<=value["a"]<=127)
                self.assertEqual(value["next_pc"],STOP)
                signed=word-65536 if word>=32768 else word
                bounded=max(-128,min(127,signed>>7))
                self.assertEqual(value["angular_sample"],bounded)

    def test_original_control_angle_stays_in_32_to_127_range(self):
        for word in (0,1,127,128,255,256,0x7FFF,0x8000,0xFF80,0xFFFF):
            for car in (0,1,0x7F,0x80,0xFF):
                result=independent(word,0,0,0,car)
                self.assertTrue(32<=result["a"]<=127)

    def test_zero_angular_sample_ignores_steering_direction(self):
        self.assertEqual(independent(0,0,0,0,0)["a"],64)
        self.assertEqual(independent(0,0,0,0,0x80)["a"],64)

    def test_private_original_rom_is_required_for_machine_parity(self):
        with self.assertRaises(ValueError):
            original_z80(bytes(0x10),0,0,0,0,0)
        with self.assertRaisesRegex(ValueError,"checksum-verified"):
            verify(bytes(0x90000),0)

    def test_invalid_z80_words_and_car_byte_fail_closed(self):
        for params in ((-1,0,0,0,0),(0,-1,0,0,0),
                       (0,0,-1,0,0),(0,0,0,65536,0),
                       (0,0,0,0,256)):
            with self.assertRaises(ValueError):independent(*params)


if __name__=="__main__":
    unittest.main()
