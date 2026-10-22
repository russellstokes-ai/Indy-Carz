"""ROM-free original Z80 7499 dual-XROM steering projection tests."""
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_drive_7499_steering_projection import (
    START,STOP,STAGE_SHA,HELPER_SHA,independent,original_opcodes,
    signed_xrom,unsigned_round8,verify
)


class OriginalSteering7499Tests(unittest.TestCase):
    def test_original_cpu_stage_and_helper_signatures(self):
        self.assertEqual((START,STOP),(0x7499,0x74D8))
        self.assertEqual(len(STAGE_SHA),64)
        self.assertEqual(len(HELPER_SHA),64)

    def test_real_original_opcode_golden_examples(self):
        cases=(
            ((64,255,28672,0),(14336,64,False,16639,14400,64)),
            ((255,255,0,0),(0,127,False,65535,127,127)),
            ((127,128,65535,0),(65532,64,False,32640,65344,32576)),
            ((0,255,65534,4096),(0,0,False,255,63232,32512)),
            ((200,255,32767,65535),(32768,99,True,51455,32867,99))
        )
        for params,golden in cases:
            actual=independent(*params)
            self.assertEqual((
                actual["de_projection"],actual["factor_b"],
                actual["overflow_saturated"],actual["slot1_address"],
                actual["first_slot0_address"],actual["second_slot0_address"]
            ),golden)
            self.assertEqual(actual["next_pc"],STOP)

    def test_original_slot1_rounding_and_signed_slot0_are_separate(self):
        self.assertEqual(unsigned_round8(255,255),254)
        self.assertEqual(unsigned_round8(128,128),64)
        self.assertEqual(signed_xrom(128,128),0x7FFF)
        self.assertEqual(signed_xrom(128,127),0x8100)

    def test_256_car_speed_inputs_and_sampled_headings(self):
        for car_byte in range(256):
            for c in (0,64,128,255):
                for angle in (0,1,0x7FFF,0x8000,0xFFFF):
                    actual=independent(c,car_byte,angle,0xF00F)
                    self.assertTrue(0<=actual["de_projection"]<65536)
                    self.assertTrue(0<=actual["factor_b"]<256)

    def test_7499_signed_helper_saturates_both_directions(self):
        values=set()
        for c in range(0,256,17):
            for car in range(0,256,19):
                for angular,heading in ((0x7FFF,0),(0,0x7FFF),
                                        (0x8000,0),(0,0x8000)):
                    actual=independent(c,car,angular,heading)
                    if actual["overflow_saturated"]:
                        self.assertIn(actual["de_projection"],(0x7FFF,0x8000))
                        values.add(actual["de_projection"])
        self.assertTrue(bool(values))

    def test_reject_invalid_original_fields_and_missing_private_binary(self):
        for case in ((-1,0,0,0),(256,0,0,0),(0,256,0,0),
                     (0,0,-1,0),(0,0,65536,0),(0,0,0,65536)):
            with self.assertRaises(ValueError):independent(*case)
        with self.assertRaises(ValueError):
            original_opcodes(bytes(2),bytes(3),0,0,0,0)
        with self.assertRaisesRegex(ValueError,"Authenticated"):
            verify(bytes(0x90000),bytes(0x40000),0)


if __name__=="__main__":unittest.main()
