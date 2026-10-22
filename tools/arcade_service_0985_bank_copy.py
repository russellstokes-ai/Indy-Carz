#!/usr/bin/env python3
"""Original arcade master 0985-0A22: banked, two-plane 24-byte memory transfer.

Original 1991 arcade ROM is user-owned and used strictly locally; source code
here models exact bounded Z80 bus writes and bank-control sequencing, without
presuming what appears on-screen or copying the original artwork into a game.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from random import Random

MASTER_HASH = '521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7'
START, END = 0x0985, 0x0A23
HELPER, HELPER_END = 0x176A, 0x1775
STAGE_SHA = 'd00a02f4bbf08f44769a9eebc283614f4cce2df3041cef1d5b75108d66529181'
HELPER_SHA = 'd0d230e91e7be53535e0602dcf2926d5bbc03c5109fbc7a4fb31810e0a478fcd'
TABLE_SHA = '65a365a66dff533a2be9d0928f709690ee32bbd595bedb2021967e73c73133f1'
TABLE, INDEX_COUNT = 0x289F, 12
BANK_BASES = (0x02000, 0x18000, 0x20000, 0x28000, 0x30000, 0x38000,
              0x40000, 0x48000, 0x50000, 0x58000, 0x60000, 0x68000,
              0x70000, 0x78000, 0x80000, 0x88000)


def read_source(master: bytes, control: int, address: int) -> int:
    """CPU ROM-view read with the MAME-rotated original master bank window.

    This routine does not model graphics RAM or other address windows; it is
    only used for known banked ROM *source* addresses in this bounded stage.
    """
    if len(master) != 0x90000 or not 0 <= control < 256 or not 0 <= address < 0xA000:
        raise ValueError('Original master ROM, control byte and ROM-source address required')
    if address < 0x2000:
        return master[address]
    return master[BANK_BASES[control & 15] + address - 0x2000]


def _validate(master: bytes, index: int, dest: int, old_bank: int,
              plane_one: int, plane_two: int, original_c: int) -> None:
    if (len(master) != 0x90000 or not 0 <= index < INDEX_COUNT
            or not 0 <= dest <= 65535
            or any(not 0 <= x <= 255 for x in (old_bank, plane_one, plane_two, original_c))):
        raise ValueError('Original master, index 0-11, 16-bit DE and four bytes required')


def model(master: bytes, index: int, dest: int, old_bank: int,
          plane_one: int, plane_two: int, original_c: int) -> dict:
    """Independent 3 rows x 4 writes per bank, from index-selected 24 bytes.

    Captures bus write events keyed by the *entire* F4 control byte. Does NOT
    assert the target is GPU memory, or that distinct control bytes imply
    distinct physical VRAM planes. Destination bus writes are not applied to
    original ROM (the missing live RAM/QRAM mapping must be traced in MAME).
    """
    _validate(master,index,dest,old_bank,plane_one,plane_two,original_c)
    pointer_location = TABLE+index*2
    pointer = read_source(master,old_bank & 0xf0,pointer_location)
    pointer |= read_source(master,old_bank & 0xf0,pointer_location+1)<<8
    if not 0x2000 <= pointer <= 0x9fe8:
        raise ValueError('Original table selected unsupported non-ROM source range')

    first_bank = plane_one
    second_bank = (plane_two | (first_bank & 15)) & 255
    bank_sequence = [old_bank & 0xf0, first_bank, second_bank, second_bank & 15, old_bank]
    events: list[tuple[int,int,int]] = []
    d,e=dest>>8,dest&255
    c=original_c
    b=first_bank
    hl=pointer
    for pass_id, bank in enumerate((first_bank,second_bank)):
        b=plane_one if pass_id==0 else plane_two
        for row in range(3):
            for col in range(4):
                value=read_source(master,bank,hl)
                events.append((bank,(d<<8)|e,value))
                hl=(hl+1)&65535
                de=((d<<8)|e)+1
                de &= 65535
                d,e=de>>8,de&255
                c=(c-1)&255
                if c==255:b=(b-1)&255
            if row<2:
                d=(d+1)&255
                e=(e-4)&255
        if pass_id==0:
            d=(d-2)&255
            e=(e-4)&255
    return {'writes':events,'port_f4':bank_sequence, 'e608':old_bank,
            'a':old_bank,'b':b,'c':c,'d':d,'e':e,'hl':hl,'selected_source':pointer}


def opcode(master: bytes, index: int, dest: int, old_bank: int,
           plane_one: int, plane_two: int, original_c: int) -> dict:
    """Actual original instruction interpretation, bounded at 0A23/1774.

    CPU source read uses original MAME-rotated ROM banking, while destination
    writes are recorded as bus events. Unrecognised opcodes or branch escape
    fail closed; no hidden inference of graphics/damage consequences.
    """
    _validate(master,index,dest,old_bank,plane_one,plane_two,original_c)
    ram={0xE608:old_bank,0xE613:plane_one,0xE615:plane_two}
    slot=bytearray(256)
    slot[0x92:0x94]=dest.to_bytes(2,'little')
    a=b=h=l=0
    b=index
    c=original_c
    d=e=0
    carry=False
    af_stack=[]
    calls=[]
    pc=START
    events=[]
    ports=[]
    source_pointer=None
    for _ in range(180):
        op=master[pc]
        if op==0x3A:
            address=master[pc+1]|master[pc+2]<<8
            if address not in ram:raise ValueError(f'Original unexpected RAM read {address:04X}')
            a=ram[address];pc+=3
        elif op==0xF5:
            af_stack.append(a);pc+=1
        elif op==0xE6:
            a&=master[pc+1];carry=False;pc+=2
        elif op==0x32:
            address=master[pc+1]|master[pc+2]<<8
            if address!=0xE608:raise ValueError('Original unexpected RAM write')
            ram[address]=a;pc+=3
        elif op==0xD3:
            if master[pc+1]!=0xF4:raise ValueError('Unexpected original I/O port')
            ports.append(a);pc+=2
        elif op==0x78:a=b;pc+=1
        elif op==0x21:
            l,h=master[pc+1:pc+3];pc+=3
        elif op==0xCD:
            addr=master[pc+1]|master[pc+2]<<8
            if addr!=HELPER:raise ValueError(f'Unexpected original CALL {addr:04X}')
            calls.append(pc+3);pc=addr
        elif op==0x87:
            value=a*2;carry=value>255;a=value&255;pc+=1
        elif op==0x85:
            value=a+l;carry=value>255;a=value&255;pc+=1
        elif op==0x6F:l=a;pc+=1
        elif op==0x30:
            v=master[pc+1];delta=v-256 if v&0x80 else v
            pc+=2+(delta if not carry else 0)
        elif op==0x24:h=(h+1)&255;pc+=1
        elif op==0x7E:
            a=read_source(master,ram[0xE608],(h<<8)|l)
            pc+=1
        elif op==0x23:
            v=((h<<8)|l)+1;h,l=(v>>8)&255,v&255;pc+=1
        elif op==0x66:
            h=read_source(master,ram[0xE608],(h<<8)|l)
            pc+=1
        elif op==0xC9:
            if calls:
                pc=calls.pop()
                source_pointer=(h<<8)|l
            elif pc==END-1:
                if af_stack:raise ValueError('Unbalanced original AF stack')
                if len(events)!=24 or len(ports)!=5:raise ValueError('Original incomplete banked write')
                return {'writes':events,'port_f4':ports,'e608':ram[0xE608],
                        'a':a,'b':b,'c':c,'d':d,'e':e,'hl':(h<<8)|l,'selected_source':source_pointer}
            else:raise ValueError('Unexpected Z80 return')
        elif op==0x18:
            v=master[pc+1];delta=v-256 if v&128 else v
            pc+=2+delta
        elif op==0x47:b=a;pc+=1
        elif op==0xB0:a|=b;carry=False;pc+=1
        elif op==0xDD:
            ext,offset=master[pc+1:pc+3]
            if ext not in (0x56,0x5E) or offset not in (0x12,0x13):
                raise ValueError(f'Unexpected original IX instruction {ext:02X}/{offset:02X}')
            if ext==0x56:d=slot[0x80+offset]
            else:e=slot[0x80+offset]
            pc+=3
        elif op==0xED:
            if master[pc+1]!=0xA0:raise ValueError('Unexpected Z80 ED opcode')
            address=(h<<8)|l
            val=read_source(master,ram[0xE608],address)
            events.append((ram[0xE608],(d<<8)|e,val))
            new_hl=(address+1)&65535;h,l=new_hl>>8,new_hl&255
            new_de=((d<<8)|e)+1;new_de&=65535;d,e=new_de>>8,new_de&255
            new_bc=(((b<<8)|c)-1)&65535;b,c=new_bc>>8,new_bc&255
            pc+=2
        elif op==0x14:d=(d+1)&255;pc+=1
        elif op==0x15:d=(d-1)&255;pc+=1
        elif op==0x1D:e=(e-1)&255;pc+=1
        elif op==0xF1:
            if not af_stack:raise ValueError('Unbalanced original POP AF')
            a=af_stack.pop();pc+=1
        else:raise ValueError(f'Unexpected original opcode {op:02X} at {pc:04X}')
        if not (START<=pc<END or HELPER<=pc<HELPER_END):
            raise ValueError(f'Original transfer escaped fixed routine at {pc:04X}')
    raise ValueError('Original transfer instruction budget exceeded')


def verify(master: bytes, cases: int = 25000) -> dict:
    if len(master)!=0x90000 or hashlib.sha256(master).hexdigest()!=MASTER_HASH:
        raise ValueError('Checksum-verified original master ROM required')
    for begin,end,digest in ((START,END,STAGE_SHA),(HELPER,HELPER_END,HELPER_SHA),
                             (TABLE,TABLE+2*INDEX_COUNT,TABLE_SHA)):
        if hashlib.sha256(master[begin:end]).hexdigest()!=digest:
            raise ValueError(f'Original Z80 routine/table signature differs at {begin:04X}')
    if not 0<=cases<=100000:raise ValueError('Invalid bounded verification count')
    rng=Random(0x985)
    wrap=0
    alias=0
    for i in range(cases):
        index=i%12
        de=(rng.randrange(256)<<8)|rng.randrange(256)
        if de&255>=252:wrap+=1
        old=rng.randrange(256)
        first=rng.randrange(16)<<4 | (rng.randrange(16) if i%5==0 else 0)
        second=rng.randrange(16)<<4 | (rng.randrange(16) if i%7==0 else 0)
        if first==second:alias+=1
        initial_c=rng.randrange(256)
        expected=model(master,index,de,old,first,second,initial_c)
        actual=opcode(master,index,de,old,first,second,initial_c)
        if expected!=actual:
            for k in expected:
                if expected[k]!=actual[k]:
                    raise AssertionError(f'Original 0985 mismatch case {i}, key {k}: model={expected[k]!r} machine={actual[k]!r}')
    return {'source':'1991 original arcade fixed-master Z80 0985-0A22',
            'cases':cases,'mismatches':0,'source_selector_entries':12,
            'source_bytes_per_case':24,'destination_write_events_per_case':24,
            'bank_port_writes_per_case':5,'initial_dest_low_byte_wrap_cases':wrap,
            'equal_plane_control_cases':alias,
            'scope':'bank switching, destination address sequence, byte values and registers; not proven on-screen rendering or damage'}


def main()->None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('master',type=Path)
    ap.add_argument('--cases',type=int,default=25000)
    args=ap.parse_args()
    print(json.dumps(verify(args.master.read_bytes(),args.cases),indent=2))


if __name__=='__main__':main()
