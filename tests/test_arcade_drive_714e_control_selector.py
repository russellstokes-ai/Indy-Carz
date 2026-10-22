"""ROM-free regressions for genuine original 714E–71C7 B/C selector."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_drive_714e_control_selector import (
    START,STOP,BYPASS,STAGE_SHA,independent,opcode,verify
)


def table():
    # Synthetic bytes, not original proprietary arcade control data.
    return bytes((17*i+29)&255 for i in range(257))


def call(e76d=0,e76f=0,index0=1,index1=3,e76c=0,
         b=0xAB,c=0xCD,carry=0):
    return independent(e76d,e76f,index0,index1,e76c,table(),b,c,carry)


class Original714EControlSelectorTests(unittest.TestCase):
    def test_genuine_z80_stage_and_sha(self):
        self.assertEqual((START,STOP,BYPASS),(0x714E,0x71C8,0x7315))
        self.assertEqual(len(STAGE_SHA),64)

    def test_both_high_skips_acceleration_and_preserves_bc(self):
        for idx0 in (0,127,128,255):
            result=call(e76d=0x0100,e76f=0x0100,index0=idx0,carry=0)
            self.assertEqual(result,{
                "next_pc":BYPASS,"b":0xAB,"c":0xCD,
                "path":"bypass_7315","overridden":False})

    def test_inherited_carry_changes_exact_threshold(self):
        without=call(e76d=0x0100,e76f=0x0100,carry=0)
        with_carry=call(e76d=0x0100,e76f=0x0100,carry=1)
        self.assertEqual(without["next_pc"],BYPASS)
        self.assertEqual(with_carry["path"],"rotated_blend")
        self.assertEqual(with_carry["next_pc"],STOP)

    def test_first_word_high_uses_ix_plus_6f_and_shifts_only_b(self):
        result=call(e76d=0x0110,e76f=0x00FF,index0=2,index1=19)
        source=table()
        index=(19*2)&255
        self.assertEqual(result["path"],"direct_6f")
        self.assertEqual(result["b"],source[index]>>1)
        self.assertEqual(result["c"],source[index+1])

    def test_second_word_high_uses_ix_plus_6e(self):
        result=call(e76d=0x00FF,e76f=0x0101,index0=13,index1=8)
        source=table()
        self.assertEqual(result["path"],"direct_6e")
        self.assertEqual(result["b"],source[26]>>1)
        self.assertEqual(result["c"],source[27])

    def test_matching_indices_do_not_shift_b(self):
        source=table()
        result=call(e76d=0,e76f=0,index0=19,index1=19)
        self.assertEqual(result["path"],"matching_indices")
        self.assertEqual((result["b"],result["c"]),tuple(source[38:40]))

    def test_original_rrca_blend_not_arithmetic_average(self):
        source=table()
        result=call(index0=2,index1=7)
        def rotated(x):return (x>>1)|((x&1)<<7)
        self.assertEqual(result["path"],"rotated_blend")
        self.assertEqual(result["b"],rotated((source[4]+source[14])&255))
        self.assertEqual(result["c"],rotated((source[5]+source[15])&255))

    def test_original_eight_bit_index_aliases_high_half(self):
        for selector in range(128):
            first=call(index0=selector,index1=selector)
            alias=call(index0=selector+128,index1=selector+128)
            self.assertEqual((first["b"],first["c"]),
                             (alias["b"],alias["c"]))

    def test_original_negative_motion_direction_overrides_both(self):
        for e76c in (128,129,255):
            for indices in ((0,1),(127,255),(5,5)):
                result=call(index0=indices[0],index1=indices[1],e76c=e76c)
                self.assertTrue(result["overridden"])
                self.assertEqual((result["b"],result["c"]),tuple(table()[:2]))
        # The direct 7315 bypass takes precedence over this override.
        result=call(e76d=0x100,e76f=0x100,e76c=255)
        self.assertFalse(result["overridden"])
        self.assertEqual(result["next_pc"],BYPASS)

    def test_one_byte_extra_source_required_for_end_index(self):
        # Original CPU word read can cross the 256th byte; the source
        # window must include 257 bytes to reproduce it safely.
        with self.assertRaises(ValueError):
            independent(0,0,127,128,0,bytes(256),0,0,0)

    def test_every_original_selector_has_safe_synthetic_pair(self):
        source=table()
        for selector in range(256):
            expected=(source[(selector*2)&255],
                      source[((selector*2)&255)+1])
            result=independent(0,0,selector,selector,0,source)
            self.assertEqual((result["b"],result["c"]),expected)

    def test_strict_input_ranges_and_private_opcode_integrity(self):
        source=table()
        for args in (
            (-1,0,0,0,0,source,0,0,0),
            (0,0,256,0,0,source,0,0,0),
            (0,0,0,0,256,source,0,0,0),
            (0,0,0,0,0,source,256,0,0),
            (0,0,0,0,0,source,0,0,2)
        ):
            with self.assertRaises(ValueError):independent(*args)
        with self.assertRaises(ValueError):
            opcode(bytes(8),0,0,1,2,0,source)
        with self.assertRaisesRegex(ValueError,"checksum-verified"):
            verify(bytes(0x90000),0)


if __name__=="__main__":
    unittest.main()
