"""ROM-free tests for authentic 1991 arcade BD17 lookup and MAME branch data."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_live_collision_bd17_lookup import (
    ORIGINAL_MASTER_BANK_BASES, constructed_pointer,
    read_original_bank,audit_rows,audit_file
)


def sample(byte=0x80, frame=2300):
    master=bytearray(0x90000)
    xrom=bytearray(0x40000)
    # Synthetic X-ROM output, NOT copied arcade data.
    index=(0x12<<8)|0x5A
    xrom[2*index],xrom[2*index+1]=0xA8,0x0C
    ptr=0x6D24
    master[ORIGINAL_MASTER_BANK_BASES[14]+ptr-0x2000]=byte
    row={'frame':str(frame),'pc':'BD17','ix':'E080','iy':'64E8',
         'hl':'6D24','a':'6D','e978':'60','e731':'3EFD','e73b':'12FE',
         'e608':'0E','e976':'0E','e92e':'01','mem_hl':f'{byte:02X}'}
    loaded=dict(row,pc='BD1A',a=f'{byte:02X}')
    branch=dict(row,pc='BE6B' if byte<0x84 else 'BD1D',a=f'{byte:02X}')
    return bytes(master),bytes(xrom),[row,loaded,branch]


class OriginalCollisionROMAddressTests(unittest.TestCase):
    def test_independent_16bit_pointer_computation(self):
        m,x,rows=sample()
        result=constructed_pointer(0x3EFD,0x12FE,0x60,x)
        self.assertEqual(result,{'source_xrom_address':0x125A,
                                 'cpu_pointer':0x6D24,
                                 'accumulator_before_read':0x6D})

    def test_original_both_live_threshold_branches(self):
        m,x,rows=sample(0x80)
        report=audit_rows(rows,m,x)
        self.assertEqual(report['observed_0x84_branch_targets'],{'BE6B':1})
        self.assertEqual(report['original_master_banks_observed'],{14:1})
        self.assertEqual(report['mismatches'],0)
        m,x,rows=sample(0x84)
        self.assertEqual(audit_rows(rows,m,x)['observed_0x84_branch_targets'],
                         {'BD1D':1})

    def test_original_8bit_add_carry_into_high_pointer(self):
        x=bytearray(0x40000)
        idx=(0x10<<8)|0x5A
        x[2*idx],x[2*idx+1]=0xE8,0x10
        result=constructed_pointer(0x9FFD,0x10F0,0x20,bytes(x))
        # high(E731)*2 wraps 0x9F*2 = 0x3E. + E8 => 0x126,
        # carry into the high byte makes it 0x31 (20+10+1).
        self.assertEqual(result['cpu_pointer'],0x3126)

    def test_all_original_master_banks_use_mame_rotated_mapping(self):
        for i,base in enumerate(ORIGINAL_MASTER_BANK_BASES):
            m=bytearray(0x90000)
            m[base]=i+1
            self.assertEqual(read_original_bank(bytes(m),i,0x2000),i+1)

    def test_original_cpu_window_outside_master_banked_rom_rejected(self):
        m,x,rows=sample()
        for pointer in (0,0x1FFF,0xA000,0xE000):
            with self.assertRaises(ValueError):read_original_bank(m,14,pointer)

    def test_cpu_pointer_or_z80_a_mismatch_detected(self):
        for position in (0,1):
            m,x,rows=sample()
            rows[0]['hl']='6D25' if position==0 else '6D24'
            if position: rows[0]['a']='6C'
            with self.assertRaisesRegex(ValueError,'pointer/accumulator'):
                audit_rows(rows,m,x)

    def test_wrong_original_data_byte_detected(self):
        m,x,rows=sample()
        rows[1]['a']='81'
        with self.assertRaisesRegex(ValueError,'lookup byte'):audit_rows(rows,m,x)

    def test_wrong_original_branch_detected(self):
        m,x,rows=sample()
        rows[2]['pc']='BD1D'
        with self.assertRaisesRegex(ValueError,'branch mismatch'):audit_rows(rows,m,x)

    def test_wrong_car_or_time_context_detected(self):
        m,x,rows=sample()
        rows[1]['ix']='E180'
        with self.assertRaisesRegex(ValueError,'state changed'):audit_rows(rows,m,x)
        m,x,rows=sample()
        rows[1]['frame']='2301'
        with self.assertRaisesRegex(ValueError,'state changed'):audit_rows(rows,m,x)

    def test_original_multiple_lookup_sequence_order(self):
        m,x,rows=sample(0x80,2300)
        m2,x2,rows2=sample(0x80,2301)
        result=audit_rows(rows+rows2,m,x)
        self.assertEqual(result['live_pointer_rom_byte_branch_triplets'],2)

    def test_truncation_and_unverified_source_fails_closed(self):
        m,x,rows=sample()
        with self.assertRaises(ValueError):audit_rows([],m,x)
        with self.assertRaises(ValueError):audit_rows(rows[:-1],m,x)
        with self.assertRaises(ValueError):audit_rows([{'frame':'2300'}],m,x)
        with self.assertRaises(ValueError):audit_rows(rows,m,bytes(8))
        with self.assertRaises((OSError,ValueError)):
            audit_file(Path('/missing/live.csv'),Path('/missing/master.bin'),
                       Path('/missing/xrom.bin'))

    def test_uint16_state_and_uint8_global_validation(self):
        _,x,_=sample()
        with self.assertRaises(ValueError):constructed_pointer(65536,0,0,x)
        with self.assertRaises(ValueError):constructed_pointer(0,65536,0,x)
        with self.assertRaises(ValueError):constructed_pointer(0,0,256,x)
        m,x,rows=sample()
        rows[0]['e608']='100'
        with self.assertRaisesRegex(ValueError,'8-bit'):audit_rows(rows,m,x)

if __name__=='__main__':
    unittest.main()
