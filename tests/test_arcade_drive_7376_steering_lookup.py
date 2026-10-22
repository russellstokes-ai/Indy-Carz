"""ROM-free regressions for original 7376-73CC steering byte selector.

All data bytes are SYNTHETIC, not original game ROM or track data.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_drive_7376_steering_lookup import (
    START,STOP,STAGE_SHA,independent,original_z80,verify
)

SYNTH=bytes((i*57+113)&255 for i in range(256))


class OriginalSteeringLookup7376Tests(unittest.TestCase):
    def test_original_cpu_bounds_and_sha(self):
        self.assertEqual((START,STOP),(0x7376,0x73CD))
        self.assertEqual(len(STAGE_SHA),64)

    def test_original_carry_affects_e773_equality_with_0x100(self):
        blended=independent(0x7376,0x100,130,2,SYNTH)
        halved=independent(0x7376,0x101,130,2,SYNTH)
        self.assertEqual(blended["branch"],"blended_indices")
        self.assertEqual(halved["branch"],"halved_car70")
        self.assertEqual(blended["b"],SYNTH[4])
        self.assertEqual(halved["b"],SYNTH[4]>>1)

    def test_first_entry_late_timer_uses_original_car70(self):
        a=independent(0x7376,65535,7,21,SYNTH)
        self.assertEqual(a["branch"],"halved_car70")
        self.assertEqual((a["b"],a["c"]),(SYNTH[14]>>1,SYNTH[15]>>1))
        self.assertEqual(a["next_pc"],STOP)

    def test_direct_7381_entry_uses_car71_and_halves_each_byte(self):
        result=independent(0x7381,0,7,21,SYNTH)
        self.assertEqual(result["branch"],"halved_car71")
        self.assertEqual((result["b"],result["c"]),
                         (SYNTH[42]>>1,SYNTH[43]>>1))

    def test_same_index_full_uses_original_unhalved_bytes(self):
        result=independent(0x7394,0,27,27,SYNTH)
        self.assertEqual(result["branch"],"same_index_full")
        self.assertEqual((result["b"],result["c"]),(SYNTH[54],SYNTH[55]))

    def test_original_interpolation_rra_uses_carry_from_byte_add(self):
        table=bytearray(256)
        table[2:4]=bytes((255,254))
        table[4:6]=bytes((255,255))
        result=independent(0x7394,0,1,2,bytes(table))
        self.assertEqual(result["branch"],"blended_indices")
        self.assertEqual((result["b"],result["c"]),(255,254))

    def test_eight_bit_doubling_drops_index_high_bit(self):
        for i in range(128):
            low=independent(0x7381,0,0,i,SYNTH)
            high=independent(0x7381,0,0,i+128,SYNTH)
            self.assertEqual((low["b"],low["c"]),(high["b"],high["c"]))
        for i in (0,1,100,127):
            same=independent(0x7394,0,i,i+128,SYNTH)
            self.assertEqual(same["branch"],"blended_indices")
            self.assertEqual((same["b"],same["c"]),(SYNTH[2*i],SYNTH[2*i+1]))

    def test_full_256_pair_table_is_used_without_proprietary_rom(self):
        for i in range(256):
            row=independent(0x7381,0,0,i,SYNTH)
            pos=(2*i)&255
            self.assertEqual((row["b"],row["c"]),
                             (SYNTH[pos]>>1,SYNTH[pos+1]>>1))

    def test_original_three_entry_paths_all_stop_at_73cd(self):
        for entry in (0x7376,0x7381,0x7394):
            for e773 in (0,0x100,0x101,0xFFFF):
                result=independent(entry,e773,0,255,SYNTH)
                self.assertEqual(result["next_pc"],STOP)

    def test_bad_original_table_or_index_and_untrusted_master(self):
        for args in ((0x7375,0,0,0,SYNTH),(0x7376,-1,0,0,SYNTH),
                     (0x7376,0,-1,0,SYNTH),(0x7376,0,0,256,SYNTH),
                     (0x7381,0,0,0,bytes(255))):
            with self.assertRaises(ValueError):independent(*args)
        with self.assertRaises(ValueError):
            original_z80(bytes(0x90000),0x7381,0,0,0,bytes(5))
        with self.assertRaisesRegex(ValueError,"Checksum-verified"):
            verify(bytes(0x90000),0)


if __name__=="__main__":
    unittest.main()
