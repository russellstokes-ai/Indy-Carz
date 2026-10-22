"""ROM-free address, source bank, register and fail-closed tests for 0985 transfer."""
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from arcade_service_0985_bank_copy import (START, END, HELPER, TABLE, BANK_BASES,
                                           INDEX_COUNT, read_source, model, opcode, verify)


def synthetic():
    m=bytearray(0x90000)
    for i in range(INDEX_COUNT):
        ptr=0x3000+24*i
        m[TABLE+2*i:TABLE+2*i+2]=ptr.to_bytes(2,'little')
        for bank in (0,1,2,3,5):
            start=BANK_BASES[bank]+ptr-0x2000
            m[start:start+24]=bytes((n+i+bank*40)&255 for n in range(24))
    return bytes(m)


class BankCopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.master=synthetic()

    def test_bounds_and_explicit_source_count(self):
        self.assertEqual((START,END,HELPER,TABLE,INDEX_COUNT),
                         (0x0985,0x0A23,0x176A,0x289F,12))

    def test_3_by_4_row_addresses_in_each_bank(self):
        r=model(self.master,0,0x4234,0xA7,0x10,0x20,100)
        target=[((0x42+y)<<8)|(0x34+x) for y in range(3) for x in range(4)]
        self.assertEqual([w[1] for w in r['writes'][:12]],target)
        self.assertEqual([w[1] for w in r['writes'][12:]],target)
        self.assertEqual([w[0] for w in r['writes']],[0x10]*12+[0x20]*12)
        self.assertEqual(r['port_f4'],[0xA0,0x10,0x20,0,0xA7])
        self.assertEqual(r['selected_source'],0x3000)
        self.assertEqual(r['hl'],0x3018)
        self.assertEqual((r['d'],r['e']), (0x44,0x38))

    def test_banked_source_memory_changes_actual_values(self):
        r=model(self.master,0,0x5000,0x00,0x11,0x23,0)
        self.assertEqual(r['port_f4'],[0,0x11,0x23,3,0])
        self.assertEqual(r['writes'][0],(0x11,0x5000,40))
        self.assertEqual(r['writes'][12],(0x23,0x5000,132))
        self.assertEqual(read_source(self.master,0x35,0x3000),200)

    def test_original_borrow_across_two_ldi_groups(self):
        for original_c,b_after in ((0,0x20),(20,0x1f),(24,0x20),(255,0x20)):
            r=model(self.master,2,0xA012,0,0x10,0x20,original_c)
            self.assertEqual(r['c'],(original_c-24)&255)
            self.assertEqual(r['b'],b_after)

    def test_address_wrap_is_preserved_not_faked_as_rectangular(self):
        a=model(self.master,0,0x40FE,0x77,0x10,0x20,10)
        self.assertEqual([x[1] for x in a['writes'][:4]],
                         [0x40FE,0x40FF,0x4100,0x4101])
        self.assertEqual(a['writes'][4][1],0x42FE)
        self.assertEqual(len(a['writes']),24)

    def test_all_twelve_original_source_selectors(self):
        for i in range(12):
            r=model(self.master,i,0x7000,0x7F,0x10,0x20,60)
            self.assertEqual(r['selected_source'],0x3000+24*i)
            self.assertEqual(len(r['writes']),24)

    def test_invalid_inputs_do_not_silently_guess(self):
        args=[self.master,0,0,0,0,0,0]
        for pos,bad in [(1,12),(1,-1),(2,65536),(3,256),(4,-1),(5,256),(6,256)]:
            values=args.copy()
            values[pos]=bad
            with self.assertRaises(ValueError):model(*values)
        with self.assertRaises(ValueError):
            model(bytes(0x100),0,0,0,0,0,0)

    def test_corrupt_executable_fails_closed(self):
        with self.assertRaises(ValueError):
            opcode(bytes(0x90000),0,0x5010,0,0,0,0)
        with self.assertRaises(ValueError):
            verify(bytes(0x90000),0)


if __name__=='__main__':unittest.main()
