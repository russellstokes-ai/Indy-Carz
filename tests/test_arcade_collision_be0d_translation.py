"""ROM-free regressions for original BE0D-BE67 two-axis translation."""
import sys
import unittest
from pathlib import Path
from random import Random

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_collision_be0d_translation import (
    START,STOP,RETRY_PC,X_AFFECTED,Y_AFFECTED,
    RAM_BASE,RAM_LENGTH,read16,write16,independent,original_opcodes,verify,
)


def record(x_old=1000,x_new=1000,y_old=2000,y_new=2000):
    r=bytearray([0xA5]*RAM_LENGTH)
    write16(r,0xE731,x_old)
    write16(r,0xE98D,x_new)
    write16(r,0xE73B,y_old)
    write16(r,0xE98F,y_new)
    for n,p in enumerate(X_AFFECTED+Y_AFFECTED):
        write16(r,p,(65530+n*1701)&0xFFFF)
    return bytes(r)


class OriginalBE0DTranslationTests(unittest.TestCase):
    def test_original_verified_cpu_span_and_retry_continuation(self):
        self.assertEqual((START,STOP,RETRY_PC),(0xBE0D,0xBE68,0xBCA5))
        self.assertEqual(len(X_AFFECTED),4)
        self.assertEqual(len(Y_AFFECTED),4)

    def test_no_delta_only_rewrites_same_reference_words(self):
        before=record()
        result=independent(before)
        self.assertEqual(result["ram"],before)
        self.assertFalse(result["x_branch"])
        self.assertFalse(result["y_branch"])

    def test_first_axis_only_adds_same_wrapped_delta_to_four_words(self):
        before=record(x_old=1000,x_new=1900)
        result=independent(before)
        state=result["ram"]
        self.assertEqual((result["delta_x"],result["delta_y"]),(900,0))
        for p in X_AFFECTED:
            self.assertEqual(read16(state,p),(read16(before,p)+900)&65535)
        for p in Y_AFFECTED:
            self.assertEqual(read16(state,p),read16(before,p))
        self.assertEqual(read16(state,0xE731),1900)
        self.assertEqual(read16(state,0xE73B),2000)

    def test_second_axis_only_preserves_first_geometry(self):
        before=record(y_old=5000,y_new=5001)
        result=independent(before)
        state=result["ram"]
        self.assertEqual((result["delta_x"],result["delta_y"]),(0,1))
        for p in X_AFFECTED:
            self.assertEqual(read16(state,p),read16(before,p))
        for p in Y_AFFECTED:
            self.assertEqual(read16(state,p),(read16(before,p)+1)&65535)

    def test_both_axes_with_negative_wrap(self):
        before=record(x_old=0,x_new=65535,y_old=65535,y_new=0)
        result=independent(before)
        state=result["ram"]
        self.assertEqual((result["delta_x"],result["delta_y"]),(65535,1))
        self.assertTrue(result["x_branch"] and result["y_branch"])
        for p in X_AFFECTED:
            self.assertEqual(read16(state,p),(read16(before,p)-1)&65535)
        for p in Y_AFFECTED:
            self.assertEqual(read16(state,p),(read16(before,p)+1)&65535)

    def test_original_shared_reference_words_change_but_sources_stay(self):
        before=record(x_old=0,y_old=0,x_new=50000,y_new=60000)
        result=independent(before)
        state=result["ram"]
        for p in (0xE98D,0xE98F):
            self.assertEqual(read16(state,p),read16(before,p))
        self.assertEqual(read16(state,0xE731),50000)
        self.assertEqual(read16(state,0xE73B),60000)

    def test_exact_no_unrelated_memory_changes(self):
        before=record(x_new=1490,y_new=2100)
        changed=independent(before)["ram"]
        allowed={p+i for p in (0xE731,0xE73B,*X_AFFECTED,*Y_AFFECTED)
                 for i in (0,1)}
        self.assertTrue(all(before[i]==changed[i]
                            for i in range(RAM_LENGTH) if i+RAM_BASE not in allowed))

    def test_many_independent_wrapped_translation_cases(self):
        rng=Random(0xBE0D)
        for i in range(1000):
            x=rng.randrange(65536)
            y=rng.randrange(65536)
            dx=rng.choice((0,1,65535,0x8000,rng.randrange(65536)))
            dy=rng.choice((0,1,65535,0x8000,rng.randrange(65536)))
            before=record(x,(x+dx)&65535,y,(y+dy)&65535)
            updated=independent(before)
            self.assertEqual(updated["delta_x"],dx)
            self.assertEqual(updated["delta_y"],dy)
            self.assertEqual(updated["next_pc"],RETRY_PC)

    def test_short_input_and_out_of_bounds_address_fail_closed(self):
        with self.assertRaises(ValueError):independent(bytes(255))
        with self.assertRaises(ValueError):read16(bytes(RAM_LENGTH),0xDFFF)
        with self.assertRaises(ValueError):read16(bytes(RAM_LENGTH),0xFFFF)
        with self.assertRaises(ValueError):write16(bytearray(RAM_LENGTH),0xFFFF,0)

    def test_original_opcode_verification_needs_private_rom(self):
        before=record()
        with self.assertRaises(ValueError):
            original_opcodes(bytes(3),before)
        with self.assertRaisesRegex(ValueError,"Private checksum"):
            verify(bytes(0x90000),0)


if __name__=="__main__":
    unittest.main()
