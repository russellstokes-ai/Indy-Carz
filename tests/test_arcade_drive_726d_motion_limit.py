"""Synthetic ROM-free original master 726D–72D2 motion correction tests."""
import sys,unittest
from pathlib import Path
from random import Random
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_drive_726d_motion_limit import (
    START,STOP,STAGE_SHA,ROM_FACTOR_SHA,slot0_word,
    signed16,independent,original_z80,verify
)

def fake(factor=127,slot=42):
    master=bytearray(0x90000)
    master[0x2000+slot]=factor
    return bytes(master)

class Original726DMotionLimitTests(unittest.TestCase):
    def test_source_range_and_banked_rom_factor_gated(self):
        self.assertEqual((START,STOP),(0x726D,0x72D3))
        self.assertEqual(len(STAGE_SHA),64)
        self.assertEqual(len(ROM_FACTOR_SHA),64)
        self.assertEqual(independent(fake(127),0,42,0,0,0)["factor"],127)

    def test_original_no_motion_change_at_zero(self):
        result=independent(fake(),0,42,0,0,0)
        self.assertEqual((result["projected"],result["difference"],
                          result["change"],result["e76b"]),(0,0,0,0))
        self.assertFalse(result["first_overflow"])
        self.assertFalse(result["second_overflow"])

    def test_original_negative_clamp_unsigned_word_max(self):
        m=fake()
        found=False
        for e933 in (1,2,127,255,0x8000,0xFFFE):
            result=independent(m,99,42,0,e933,0)
            if result["negative"]:
                self.assertEqual(result["change"],max(result["half"],result["threshold"]))
                found=True
        self.assertTrue(found)

    def test_original_positive_clamp_unsigned_word_min(self):
        m=fake()
        for b in (0,1,2,5,16,127,128,255):
            result=independent(m,b,42,0,0,0)
            self.assertEqual(result["change"],min(result["half"],result["threshold"]))
            self.assertEqual(result["threshold"],(((b<<1)&255)<<3)&65535)

    def test_genuine_first_overflow_saturates_positive(self):
        rng=Random(0x726D);found=0
        master=fake(127)
        for _ in range(1000):
            result=independent(master,rng.randrange(256),42,
                               rng.randrange(65536),rng.randrange(65536),
                               rng.randrange(65536))
            if result["first_overflow"]:
                self.assertEqual(result["difference"],32767)
                self.assertFalse(result["negative"])
                found+=1
        self.assertGreater(found,0)

    def test_genuine_final_overflow_saturates_by_result_sign(self):
        rng=Random(0x7270);found=0
        master=fake(127)
        for _ in range(2000):
            result=independent(master,rng.randrange(256),42,
                               rng.randrange(65536),rng.randrange(65536),
                               rng.randrange(65536))
            if result["second_overflow"]:
                self.assertIn(result["e76b"],(0x8000,0x7FFF))
                found+=1
        self.assertGreater(found,0)

    def test_original_car_index_changes_factor_and_result(self):
        master=bytearray(fake(0,42))
        master[0x2000+43]=127
        first=independent(bytes(master),55,42,0x7500,0x0100,0x3000)
        second=independent(bytes(master),55,43,0x7500,0x0100,0x3000)
        self.assertEqual((first["factor"],second["factor"]),(0,127))
        self.assertNotEqual(first["projected"],second["projected"])

    def test_exact_two_original_xrom_slots_sign_saturations(self):
        self.assertEqual(slot0_word(0,255),0)
        self.assertEqual(slot0_word(127,127),0x7E02)
        self.assertEqual(slot0_word(128,128),0x7FFF)
        self.assertEqual(slot0_word(128,127),0x8100)

    def test_four_original_16bit_boundary_patterns(self):
        master=fake()
        for b in (0,1,127,128,255):
            for spin in (0,1,0x7FFF,0x8000,0xFFFF):
                for prior in (0,1,0x7FFF,0x8000,0xFFFF):
                    result=independent(master,b,42,spin,0x8000,prior)
                    self.assertTrue(0<=result["e76b"]<65536)
                    self.assertTrue(0<=result["change"]<65536)
                    self.assertEqual(result["next_pc"],STOP)

    def test_fail_closed_wrong_rom_size_and_invalid_inputs(self):
        for inp in ((256,42,0,0,0),(0,256,0,0,0),
                    (0,42,-1,0,0),(0,42,0,65536,0)):
            with self.assertRaises(ValueError):independent(fake(),*inp)
        with self.assertRaises(ValueError):independent(bytes(20),0,42,0,0,0)
        with self.assertRaises(ValueError):
            original_z80(bytes(20),bytes(10),0,42,0,0,0)
        with self.assertRaisesRegex(ValueError,"checksum"):
            verify(bytes(0x90000),bytes(0x40000),0)

if __name__=="__main__":unittest.main()
