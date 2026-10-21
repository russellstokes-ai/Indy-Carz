"""ROM-free tests for original two-car dispatch, callback exits and 66-byte copy."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_live_collision_response_parity import (
    dispatch_audit,handler_audit,ldir_audit,audit_traces)


def dispatch_pair(frame=2500,second_skipped=False):
    common={'frame':str(frame),'ix':'E080','iy':'E180',
            'status_ix':'40','status_iy':'42' if second_skipped else '40',
            'e941':'00'}
    result=[dict(common,stage='DISPATCH'),dict(common,stage='SERVICE')]
    if not second_skipped:
        result.append(dict(common,stage='SERVICE',ix='E180',iy='E180',e941='FF'))
    return result


def handler_rows(frame=2500,with_full=True):
    common={'frame':str(frame),'ix':'E080','iy':'E180','e941':'00',
            'car_b1':'02','car_7c':'40','e608':'05','a':'00'}
    data=[dict(common,pc='B884'),dict(common,pc='B8AB',e941='FF')]
    if with_full:
        data += [dict(common,pc='B884',ix='E180',iy='E180',e941='FF'),
                 dict(common,pc='B8AB',ix='E180',iy='E180',e941='01'),
                 dict(common,pc='B8AC',ix='E180',iy='E180',e941='01',car_b1='82'),
                 dict(common,pc='B8E3',ix='E180',iy='E180',e941='01',car_b1='82',car_7c='42')]
    return data


def copy_rows(frame=2502,ix=0xE180):
    values=[]
    for i in range(66):
        values.append({'frame':str(frame),'pc':'B8BA','ix':f'{ix:04X}',
                       'hl':f'{0xE72B+i:04X}', 'dest':f'{ix-0x80+i:04X}',
                       'data':str((i*7+4)&255),'src_before':str((i*7+4)&255),
                       'source_val':'1'})
    return values


class OriginalCollisionResponseTests(unittest.TestCase):
    def test_complete_two_car_trace_crosschecks(self):
        result=audit_traces(dispatch_pair(),handler_rows(),copy_rows())
        self.assertEqual(result['live_dispatches'],1)
        self.assertEqual(result['live_b884_invocations'],2)
        self.assertEqual(result['original_callback_return_paths'],
                         {'complete_66byte_restore':1,'e941_ff_early_return':1})
        self.assertEqual(result['real_cpu_ldir_byte_writes'],66)
        self.assertEqual(result['mismatches'],0)

    def test_single_car_original_dispatch(self):
        data=dispatch_audit(dispatch_pair(second_skipped=True))
        self.assertEqual(data['dispatch_call_counts'],{'1_calls':1})
        self.assertEqual(data['ordered_calls'],[(2500,0xE080)])

    def test_ordered_calls_must_match_original_bit1_status(self):
        data=dispatch_pair()
        data[-1]['ix']='E080'
        with self.assertRaisesRegex(ValueError,'call order'):dispatch_audit(data)

    def test_second_car_handler_ix_iy_may_be_equal_during_swap(self):
        self.assertEqual(dispatch_audit(dispatch_pair())['b884_calls'],2)
        self.assertEqual(handler_audit(handler_rows())['handler_calls'],2)

    def test_b8ab_ff_early_return(self):
        r=handler_audit(handler_rows(with_full=False))
        self.assertEqual(r['callback_exits'],{'e941_ff_early_return':1})
        self.assertEqual(r['full_restores'],[])

    def test_non_ff_callback_requires_b8ac_continuation(self):
        data=handler_rows(with_full=False)
        data[-1]['e941']='01'
        with self.assertRaisesRegex(ValueError,'early return marker'):handler_audit(data)

    def test_b8e3_status_bit1_actual_write(self):
        data=handler_rows()
        data[-1]['car_7c']='40'
        with self.assertRaisesRegex(ValueError,'status write'):handler_audit(data)

    def test_b8e3_requires_original_car_b1_bit7(self):
        data=handler_rows()
        data[-2]['car_b1']='02'
        with self.assertRaisesRegex(ValueError,'BIT7'):handler_audit(data)

    def test_original_bank5_restored_after_callback(self):
        data=handler_rows()
        data[1]['e608']='06'
        with self.assertRaisesRegex(ValueError,'bank-5'):handler_audit(data)

    def test_original_ldir_all_66_byte_addresses(self):
        result=ldir_audit(copy_rows())
        self.assertEqual(result['original_66byte_transfers'],1)
        self.assertEqual(result['car_transfer_counts'],{'E180':1})

    def test_original_ldir_rejects_bad_source_address(self):
        data=copy_rows()
        data[10]['hl']='E700'
        with self.assertRaisesRegex(ValueError,'source/destination'):ldir_audit(data)

    def test_original_ldir_rejects_byte_mismatch(self):
        data=copy_rows()
        data[10]['data']='0'
        with self.assertRaisesRegex(ValueError,'memory copy byte'):ldir_audit(data)

    def test_original_ldir_rejects_incomplete_or_wrong_opcode(self):
        with self.assertRaisesRegex(ValueError,'divisible'):ldir_audit(copy_rows()[:-1])
        data=copy_rows();data[0]['pc']='B8BB'
        with self.assertRaisesRegex(ValueError,'instruction/car'):ldir_audit(data)

    def test_private_mame_runs_can_have_different_frame_offsets(self):
        result=audit_traces(dispatch_pair(2500),handler_rows(2500),copy_rows(2510))
        self.assertEqual(result['real_cpu_66byte_ldir_transfers'],1)
        self.assertIn('separate MAME run',result['scope'])

    def test_crosscheck_rejects_wrong_original_car_order(self):
        with self.assertRaisesRegex(ValueError,'car restoration sequence'):
            audit_traces(dispatch_pair(),handler_rows(),copy_rows(ix=0xE080))

    def test_unknown_original_diagnostic_escape_is_fail_closed(self):
        data=handler_rows(with_full=False)
        data.append(dict(data[-1],pc='1689'))
        with self.assertRaisesRegex(ValueError,'unverified path'):handler_audit(data)

if __name__=='__main__':unittest.main()
