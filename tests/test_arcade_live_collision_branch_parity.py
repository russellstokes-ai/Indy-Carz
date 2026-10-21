"""ROM-free tests for MAME actual collision branch/fallthrough verification."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_live_collision_branch_parity import audit_rows,original_projection,FOLLOW


def fake_master():
    b=bytearray(0x90000)
    for i in range(32): b[0xBC5C+2*i]=0
    b[0xBC5C+2*27]=0xE6 # synthetic adjacent instruction-byte case
    b[0xBC5C+2*31]=0xD3
    return bytes(b)


def valid_sequence(master,category=0,d=0,e=0,heading=0,frame=2500):
    byte=master[0xBC5C+2*category]
    mask,projected,next_pc=original_projection(byte,heading,d,e)
    start={'frame':str(frame),'stage':'START','ix':'E080','iy':'E180',
           'd':f'{d:02X}','e':f'{e:02X}','e919':f'{category|0xA0:02X}',
           'angle3d':f'{heading:02X}','a':'00','e925':'FF'}
    result=[start]
    for j,hit in enumerate(FOLLOW[next_pc]):
        child=start.copy();child['stage']=hit
        child['a']=f'{projected if j==0 else 0:02X}'
        child['e925']=f'{mask:02X}'
        result.append(child)
    return result


class LiveOriginalCollisionBranchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.master=fake_master()

    def test_all_three_complete_original_fallthrough_chains(self):
        data=(valid_sequence(self.master,0,246,0,0,2500)+
              valid_sequence(self.master,0,0,0,0,2501)+
              valid_sequence(self.master,0,10,0,0,2502))
        report=audit_rows(data,self.master)
        self.assertEqual(report['live_complete_collision_sequences'],3)
        self.assertEqual(report['actual_full_continuation_sequences'],{
            'B86C':1,'B778>B86C':1,'B728>B778>B86C':1})
        self.assertEqual(report['live_original_breakpoint_hits'],6)

    def test_original_adjacent_rom_category_24_to_31(self):
        data=[]
        for i in range(24,32):
            data+=valid_sequence(self.master,i,15,255,0,2400+i)
        r=audit_rows(data,self.master)
        self.assertEqual(r['adjacent_rom_category_events'],8)
        self.assertEqual(r['observed_original_category_indices'],list(range(24,32)))

    def test_original_category_uses_only_low_five_bits(self):
        rows=valid_sequence(self.master,27,14,32)
        self.assertEqual(rows[0]['e919'],'BB')
        self.assertEqual(audit_rows(rows,self.master)['adjacent_rom_category_events'],1)

    def test_same_original_frame_can_hold_multiple_separate_collisions(self):
        rows=valid_sequence(self.master,0,0,0,0,2500)+valid_sequence(self.master,0,20,0,0,2500)
        self.assertEqual(audit_rows(rows,self.master)['live_complete_collision_sequences'],2)

    def test_first_target_must_match_math(self):
        rows=valid_sequence(self.master,0,10,0)
        rows[1]['stage']='B86C'
        with self.assertRaisesRegex(ValueError,'branch chain mismatch'):audit_rows(rows,self.master)

    def test_fallthrough_stage_must_not_be_omitted(self):
        rows=valid_sequence(self.master,0,10,0)
        with self.assertRaisesRegex(ValueError,'branch chain mismatch'):audit_rows(rows[:-1],self.master)

    def test_original_z80_accumulator_parity_required(self):
        rows=valid_sequence(self.master,0,0,0)
        rows[1]['a']='FF'
        with self.assertRaisesRegex(ValueError,'accumulator'):audit_rows(rows,self.master)

    def test_original_e925_mask_parity_required_on_all_branches(self):
        rows=valid_sequence(self.master,31,10,20)
        rows[-1]['e925']='FF'
        with self.assertRaisesRegex(ValueError,'E925 mask'):audit_rows(rows,self.master)

    def test_context_switch_in_middle_of_one_collision_is_invalid(self):
        rows=valid_sequence(self.master,0,10,0)
        rows[2]['iy']='E280'
        with self.assertRaisesRegex(ValueError,'context'):audit_rows(rows,self.master)

    def test_frame_must_be_monotonic_across_separate_events(self):
        rows=valid_sequence(self.master,0,0,0,0,2501)+valid_sequence(self.master,0,0,0,0,2499)
        with self.assertRaisesRegex(ValueError,'order'):audit_rows(rows,self.master)

    def test_unknown_original_stage_or_sixth_slot_disallowed(self):
        rows=valid_sequence(self.master,0,0,0)
        rows[1]['stage']='B678'
        with self.assertRaises(ValueError):audit_rows(rows,self.master)
        rows=valid_sequence(self.master,0,0,0)
        rows[1]['ix']='E580'
        with self.assertRaises(ValueError):audit_rows(rows,self.master)

    def test_truncated_trace_or_bad_byte_values_rejected(self):
        with self.assertRaises(ValueError):audit_rows([],self.master)
        rows=valid_sequence(self.master,0,0,0)
        rows[0]['e919']='100'
        with self.assertRaisesRegex(ValueError,'8-bit'):audit_rows(rows,self.master)
        rows=valid_sequence(self.master,0,0,0)
        with self.assertRaises(ValueError):audit_rows(rows,bytes(5))


if __name__=='__main__':unittest.main()
