"""ROM-free regression for original 7124 E933 projection and 714E carry."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_drive_7124_carry_projection import (
    START,STOP,STAGE_SHA,cos8,slot0,independent,
    original_opcodes,verify,
)

class OriginalHeadingCarryProjectionTests(unittest.TestCase):
    def test_exact_original_pc_stage_and_pinned_code(self):
        self.assertEqual((START,STOP),(0x7124,0x714E))
        self.assertEqual(len(STAGE_SHA),64)

    def test_zero_motion_without_carry(self):
        self.assertEqual(independent(0,0,0),{
            "e933":0,"carry":0,"cos":127,"angle":0,
            "xrom":(0x007F,0x007F),"next_pc":STOP})

    def test_original_heading_quarter_rotation(self):
        r=independent(64,0,0x1234)
        self.assertEqual((r["angle"],r["cos"],r["e933"],r["carry"]),
                         (64,0,0,0))

    def test_nonzero_outgoing_cpu_carry_matters_to_714e(self):
        r=independent(0,0,0x1234)
        self.assertEqual((r["e933"],r["carry"]),(4622,1))
        self.assertEqual(r["xrom"],(0x127F,0x1A7F))

    def test_positive_negative_motion_and_twos_complement(self):
        self.assertEqual(independent(0,0,0x7FFF)["e933"],32510)
        self.assertEqual(independent(0,0,0x8000)["e933"],33024)
        self.assertEqual(independent(0,0,0xFFFF)["e933"],65534)

    def test_original_angle_byte_wrap(self):
        r=independent(255,0xFFFF,0xFFFF)
        self.assertEqual((r["angle"],r["cos"],r["e933"]),(0,127,65534))

    def test_original_all_heading_trig_values_8bit(self):
        self.assertEqual((cos8(0),cos8(64),cos8(128),cos8(192)),
                         (127,0,128,0))
        self.assertEqual(len({cos8(x) for x in range(256)})>100,True)

    def test_original_signed_slot0_product_saturation(self):
        self.assertEqual(slot0(127,127),0x7E02)
        self.assertEqual(slot0(128,128),0x7FFF)
        self.assertEqual(slot0(128,127),0x8100)

    def test_bruteforce_reference_valid_domains(self):
        hit_carry=set()
        for heading in range(256):
            for motion in (0,1,127,255,256,0x1234,0x7FFF,0x8000,0xFFFF):
                r=independent(heading,0xCDEF,motion)
                self.assertTrue(0<=r["e933"]<=65535)
                self.assertTrue(0<=r["angle"]<=255)
                self.assertTrue(0<=r["cos"]<=255)
                self.assertTrue(all(0<=a<=65535 for a in r["xrom"]))
                hit_carry.add(r["carry"])
        self.assertEqual(hit_carry,{0,1})

    def test_original_invalid_cpu_state_or_fake_rom_rejected(self):
        for args in ((-1,0,0),(256,0,0),(0,-1,0),
                     (0,65536,0),(0,0,-1),(0,0,65536)):
            with self.assertRaises(ValueError):independent(*args)
        with self.assertRaises(ValueError):
            original_opcodes(bytes(0x90000),bytes(1),0,0,0)
        with self.assertRaisesRegex(ValueError,"Authenticated original master"):
            verify(bytes(0x90000),bytes(0x40000),0)


if __name__=="__main__":unittest.main()
