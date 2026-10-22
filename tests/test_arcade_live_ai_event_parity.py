"""ROM-free regression of original live MAME AI event opcode write trace."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_live_ai_event_parity import original_thresholds,audit_rows


def row(*,pc='2336',ix='E080',old=0,compare=0,response=0,b1=0,b2=0,
        fe=0,linked=1,x=10,y=20,dc=0,bx=0x1405,by=0x1E0F,frame=2500):
    event=2 if pc=='2336' else 4
    return {'frame':str(frame),'pc':pc,'ix':ix,
            'addr':f'{int(ix,16)-9:04X}',
            'old':str(old),'new':str(old|event),
            'cmp':str(compare),'pedal_response':str(response),
            'b1':str(b1),'b2':str(b2),'fe':str(fe),
            'linked20':str(linked),'x':str(x),'y':str(y),
            'dc':str(dc),'bound_x':str(bx),'bound_y':str(by),
            'course':'13','round':'0'}


class OriginalLiveAIEventTests(unittest.TestCase):
    def test_original_four_threshold_tiers(self):
        self.assertEqual(original_thresholds(16,0,0),(24,9,True))
        self.assertEqual(original_thresholds(0,128,0),(24,9,True))
        self.assertEqual(original_thresholds(0,0,0),(128,72,False))
        self.assertEqual(original_thresholds(0,0,60),(128,50,False))
        self.assertEqual(original_thresholds(0,0,68),(80,50,False))

    def test_original_both_event_sites_in_one_capture(self):
        r=audit_rows([row(pc='2336',old=4),row(pc='235C',old=2,compare=129,frame=2501)])
        self.assertEqual(r['events_checked'],2)
        self.assertEqual((r['verified_event_bit1'],r['verified_event_bit2']),(1,1))
        self.assertEqual(r['mismatches'],0)

    def test_original_bit1_event_threshold(self):
        r=audit_rows([row(response=0,compare=71,dc=0)])
        self.assertEqual(r['bit1_threshold_condition_observed'],1)
        self.assertEqual(r['bit1_spatial_condition_observed'],0)

    def test_original_spatial_condition_only(self):
        r=audit_rows([row(response=126,compare=90,dc=2)])
        self.assertEqual(r['bit1_spatial_condition_observed'],1)
        self.assertEqual(r['bit1_threshold_condition_observed'],0)

    def test_original_forced_event_condition_only(self):
        r=audit_rows([row(response=126,compare=90,fe=16,linked=3,dc=0)])
        self.assertEqual(r['bit1_forced_condition_observed'],1)
        self.assertEqual(r['bit1_threshold_condition_observed'],0)

    def test_original_bit2_threshold_and_other_flags_preserved(self):
        r=audit_rows([row(pc='235C',old=0x81,compare=130,response=126)])
        self.assertEqual(r['verified_event_bit2'],1)

    def test_original_bit2_exclusion_rejects_invalid_path(self):
        with self.assertRaisesRegex(ValueError,'threshold/gate'):
            audit_rows([row(pc='235C',compare=130,response=126,fe=16,linked=2)])
        with self.assertRaisesRegex(ValueError,'threshold/gate'):
            audit_rows([row(pc='235C',compare=1,response=126,fe=0)])

    def test_no_original_bit1_source_is_error(self):
        with self.assertRaisesRegex(ValueError,'no proven source'):
            audit_rows([row(compare=130,response=126,dc=0,fe=0)])

    def test_source_status_byte_mismatch_fails_closed(self):
        x=row();x['new']='0'
        with self.assertRaisesRegex(ValueError,'byte mismatch'):audit_rows([x])

    def test_wrong_original_opcode_or_physical_slot_fails_closed(self):
        for updates in ({'ix':'0000'},{'pc':'2200'},{'addr':'E0F7'}):
            x=row();x.update(updates)
            with self.assertRaisesRegex(ValueError,'opcode'):audit_rows([x])

    def test_original_frame_order_and_field_domains(self):
        with self.assertRaisesRegex(ValueError,'out of frame order'):
            audit_rows([row(frame=2501),row(frame=2500)])
        x=row();x['cmp']='256'
        with self.assertRaisesRegex(ValueError,'non-byte'):audit_rows([x])
        x=row();x['bound_x']='65536'
        with self.assertRaisesRegex(ValueError,'bounds'):audit_rows([x])

    def test_empty_or_incomplete_original_trace_rejected(self):
        with self.assertRaises(ValueError):audit_rows([])
        with self.assertRaisesRegex(ValueError,'columns incomplete'):
            audit_rows([{'frame':'1'}])


if __name__=='__main__':
    unittest.main()
