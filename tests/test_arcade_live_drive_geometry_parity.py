"""ROM-free tests for authentic original MAME movement/footprint write replay."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from arcade_live_drive_geometry_parity import (
    PAIRS,CAR_IX,signed8,trig8,step,center_after,corners,audit_trace_rows
)


def sample(ix=0xE080,integrated=True,frame=2500,
           angle=123,motion=63,geoangle=127,x=0x1234,y=0xA123):
    rows=[]
    endx,endy=center_after(angle,motion,x,y) if integrated else (x,y)
    original={0xE735:endx,0xE72B:endy}
    original.update(corners(geoangle,endx,endy))
    for pc,addr in PAIRS if integrated else PAIRS[2:]:
        for d in (0,1):
            is_movement=pc in (0x7555,0x756F)
            rows.append({
                'frame':str(frame),'pc':f'{pc:04X}','ix':f'{ix:04X}',
                'addr':f'{addr+d:04X}',
                'data':str((original[addr]>>(8*d))&255),
                'angle':str(angle if is_movement else geoangle),
                'motion':str(motion if is_movement else 0),
                'x':str(x if is_movement and pc==0x7555 else endx),
                'y':str(y if is_movement else endy),
                'course':'13','round':'0',
            })
    return rows


class OriginalLiveDriveParityTests(unittest.TestCase):
    def test_movement_and_geometry_end_to_end(self):
        r=audit_trace_rows(sample())
        self.assertEqual((r['verified_position_updates'],r['verified_geometry_updates'],
                          r['verified_geometry_words'],r['mismatches']),(1,1,8,0))
        self.assertEqual(r['nonzero_motion_updates'],1)

    def test_geometry_without_movement_is_valid_original_route(self):
        r=audit_trace_rows(sample(integrated=False,angle=10))
        self.assertEqual((r['verified_position_updates'],
                          r['geometry_only_original_branches']),(0,1))

    def test_mixed_five_car_original_sequence(self):
        rows=[]
        for n,ix in enumerate(CAR_IX[:5]):
            rows+=sample(ix=ix,frame=2500+n,integrated=(n&1)==0,
                         angle=n*50,motion=n*20,geoangle=255-n)
        r=audit_trace_rows(rows)
        self.assertEqual((r['verified_geometry_updates'],r['verified_position_updates']),(5,3))
        self.assertEqual(set(r['updates_by_car']),{'E080','E180','E280','E380','E480'})

    def test_negative_wrapped_motion(self):
        r=audit_trace_rows(sample(x=0,y=0,angle=225,geoangle=254,motion=255))
        self.assertEqual(r['mismatches'],0)

    def test_all_256_angle_values_synthetic(self):
        cases=[]
        for angle in range(256):
            cases+=sample(angle=angle,geoangle=angle,frame=angle+1,
                          x=(angle*197)&65535,y=(angle*301)&65535)
        r=audit_trace_rows(cases)
        self.assertEqual((r['movement_angles_seen'],r['geometry_angles_seen']),(256,256))

    def test_original_trig_and_saturation_bounds(self):
        self.assertEqual((signed8(128),signed8(255)),(-128,-1))
        self.assertEqual((trig8(0,False),trig8(64,True)),(127,127))
        self.assertEqual((trig8(128,False),trig8(192,True)),(-128,-128))
        self.assertEqual(step(127,127),(127*127*2*4+128)//256)

    def test_bad_instruction_write_order_rejected(self):
        rows=sample()
        rows[0],rows[1]=rows[1],rows[0]
        with self.assertRaisesRegex(ValueError,'order'):audit_trace_rows(rows)

    def test_bad_write_value_rejected(self):
        rows=sample()
        rows[-1]['data']=str((int(rows[-1]['data'])+1)&255)
        with self.assertRaisesRegex(ValueError,'footprint word mismatch'):
            audit_trace_rows(rows)

    def test_corrupted_coordinate_value_rejected(self):
        rows=sample()
        rows[0]['data']=str((int(rows[0]['data'])+1)&255)
        with self.assertRaisesRegex(ValueError,'position calculation mismatch'):
            audit_trace_rows(rows)

    def test_missing_original_byte_rejected(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            audit_trace_rows(sample()[:-1])

    def test_frame_pointer_change_inside_event_rejected(self):
        rows=sample()
        rows[10]['ix']='E180'
        with self.assertRaisesRegex(ValueError,'continuity'):audit_trace_rows(rows)

    def test_untrusted_pointer_and_bad_numeric_fields_rejected(self):
        rows=sample()
        rows[0]['ix']='0000'
        with self.assertRaisesRegex(ValueError,'car pointer'):audit_trace_rows(rows)
        rows=sample()
        rows[0]['angle']='256'
        with self.assertRaisesRegex(ValueError,'angle'):audit_trace_rows(rows)

    def test_empty_untrusted_trace_rejected(self):
        with self.assertRaises(ValueError):audit_trace_rows([])


if __name__=='__main__':
    unittest.main()
