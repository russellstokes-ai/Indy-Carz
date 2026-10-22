"""ROM-free structural and arithmetic regression for original contact fallback."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_collision_state_restore import START, END, model, original, verify


def synth_original_shape() -> bytes:
    """Build a synthetic bounded Z80 stage from instruction patterns."""
    stage=bytearray()
    for i in range(10):
        src_lo=0x9E+i*2
        dst_lo=0x80+i*2
        stage+=bytes([0xDD,0x66,src_lo+1,0xDD,0x6E,src_lo,
                      0xDD,0x74,dst_lo+1,0xDD,0x75,dst_lo])
    stage+=bytes([0xDD,0x66,0x9D,0xDD,0x6E,0x9C,
                  0xDD,0x74,0xBD,0xDD,0x75,0xBC])
    stage+=bytes([0xDD,0x66,0xC1,0xDD,0x6E,0xC0,
                  0x7C,0xC6,0x80,0xFE,0xA0,0x38,0x17,
                  0x54,0x5D])
    stage+=bytes([0xCB,0x2A,0xCB,0x1B])*3
    stage+=bytes([0xB7,0xED,0x52,0xDD,0x74,0xC1,0xDD,0x75,0xC0,
                  0xDD,0x7E,0xFC,0xF6,0x43,0xDD,0x77,0xFC,0xC9])
    assert len(stage)==END-START
    master=bytearray(0x90000)
    master[START:END]=stage
    return bytes(master)


class OriginalCollisionFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master=synth_original_shape()

    def test_ten_word_previous_coordinate_restore(self):
        state=bytearray(256)
        for n in range(10):
            state[0x1E+2*n:0x20+2*n]=(60000+n).to_bytes(2,"little")
            state[2*n:2*n+2]=(100+n).to_bytes(2,"little")
        state[0x1C:0x1E]=b"\x12\x34"
        state[0x3C:0x3E]=b"\xAB\xCD"
        state[0x7C]=0x80
        expected,damped=model(bytes(state))
        self.assertFalse(damped)
        self.assertEqual(expected[0:20],state[0x1E:0x32])
        self.assertEqual(expected[0x3C:0x3E],b"\x12\x34")
        self.assertEqual(expected[0x7C],0xC3)
        self.assertEqual(expected[0x1E:0x32],state[0x1E:0x32])

    def test_conditional_original_state_word_damping_boundaries(self):
        for hi,should_damp in [(0,False),(31,False),(32,True),
                               (127,True),(128,False),(255,False)]:
            state=bytearray(256)
            state[0x40:0x42]=((hi<<8)|0x7f).to_bytes(2,"little")
            observed,damped=model(bytes(state))
            self.assertEqual(damped,should_damp)
            status,from_opcodes,_=original(self.master,bytes(state))
            self.assertEqual((status,from_opcodes),(observed,damped))

    def test_many_synthetic_original_opcode_matches(self):
        for i in range(350):
            state=bytes(((j*31)+(i*7))&255 for j in range(256))
            expected=model(state)
            result=original(self.master,state)
            self.assertEqual(result[:2],expected)

    def test_original_rom_guard_and_unknown_instruction(self):
        with self.assertRaisesRegex(ValueError,"checksum-verified"):
            verify(self.master,5)
        bad=bytearray(self.master)
        bad[START]=0xFF
        with self.assertRaisesRegex(ValueError,"original opcode"):
            original(bytes(bad),bytes(256))


if __name__=="__main__":
    unittest.main()
