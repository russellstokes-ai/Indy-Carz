#!/usr/bin/env python3
"""Bounded original arcade B884-B8AB car-scratch transfer and callback gate.

The CALL BC8C is deliberately opaque: caller supplies hypothetical return RAM
E941/E608 values. Only entry memory copy, bank setup, and RET Z branching are
verified; no claim about BC8C physics or downstream B8AC response is made.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from random import Random

MASTER_HASH='521d8c16fdbc85cd6cddf9e0ce5735fdb771242c5dfed86d8cefe3855a6205e7'
START,STOP,CALLBACK=0xB884,0xB8AC,0xBC8C
STAGE_SHA='f58c8693bb5d44cf4507d94b6cb73c8f116736da8f7d6a090ab8710704438dce'


def check(slot:bytes,scratch:bytes,post_callback_e941:int,post_callback_e608:int)->None:
    if len(slot)!=256 or len(scratch)!=96 or any(not 0<=x<=255 for x in
                                                  (post_callback_e941,post_callback_e608)):
        raise ValueError('256-byte car, 96-byte scratch and callback return RAM bytes required')


def model(slot:bytes,scratch:bytes,post_callback_e941:int,post_callback_e608:int)->dict:
    check(slot,scratch,post_callback_e941,post_callback_e608)
    changed=bytearray(scratch)
    changed[:20]=slot[:20]
    bank=(post_callback_e608 & 0xF0)|5
    a=(post_callback_e941+1)&255
    return {'scratch':bytes(changed),'copy_pairs':[(i,0xE72B+i) for i in range(20)],
            'e941':post_callback_e941,'e608':bank,'out_f4':(bank,),
            'accumulator':a,'next':'return_B8AB' if a==0 else 'continue_B8AC',
            'bc8c_invocations':1}


def opcode(master:bytes,slot:bytes,scratch:bytes,
           post_callback_e941:int,post_callback_e608:int)->dict:
    check(slot,scratch,post_callback_e941,post_callback_e608)
    if len(master)!=0x90000:raise ValueError('Original master executable must be 0x90000 bytes')
    ram={0xE941:0xFF,0xE608:0}
    state=bytearray(scratch)
    ix=0xE080
    a=b=c=d=e=h=l=0
    zero=False
    stack=[]
    event=[]
    ports=[]
    callback_count=0
    pc=START
    for _ in range(38):
        op=master[pc]
        if op==0xDD and master[pc+1]==0xE5:
            stack.append(ix);pc+=2
        elif op==0xE1:
            if not stack:raise ValueError('Original pointer stack underflow')
            word=stack.pop();h,l=word>>8,word&255;pc+=1
        elif op in (0x01,0x11):
            word=master[pc+1]|master[pc+2]<<8
            if op==0x01:b,c=word>>8,word&255
            else:d,e=word>>8,word&255
            pc+=3
        elif op==0x09:
            result=(((h<<8)|l)+((b<<8)|c))&65535
            h,l=result>>8,result&255;pc+=1
        elif op==0xED:
            if master[pc+1]!=0xB0:raise ValueError('Expected original LDIR opcode')
            if (b<<8)|c != 20:raise ValueError('Expected exactly 20 original copied bytes')
            for _ in range(20):
                src=(h<<8)|l
                dst=(d<<8)|e
                if not 0xE000<=src<0xE100 or not 0xE72B<=dst<0xE72B+96:
                    raise ValueError('Original 20-byte copy escaped checked RAM buffers')
                state[dst-0xE72B]=slot[src-0xE000]
                event.append((src-0xE000,dst))
                src=(src+1)&65535;dst=(dst+1)&65535
                h,l=src>>8,src&255;d,e=dst>>8,dst&255
                bc=(((b<<8)|c)-1)&65535;b,c=bc>>8,bc&255
            pc+=2
        elif op==0x3E:
            a=master[pc+1];pc+=2
        elif op==0x32:
            address=master[pc+1]|master[pc+2]<<8
            if address not in (0xE941,0xE608):raise ValueError('Unexpected original RAM write')
            ram[address]=a;pc+=3
        elif op==0xCD:
            address=master[pc+1]|master[pc+2]<<8
            if address!=CALLBACK:raise ValueError('Unexpected original opaque callback')
            if ram[0xE941]!=0xFF:raise ValueError('Original E941 marker not initialised')
            callback_count+=1
            ram[0xE941]=post_callback_e941
            ram[0xE608]=post_callback_e608
            pc+=3
        elif op==0x3A:
            address=master[pc+1]|master[pc+2]<<8
            if address not in ram:raise ValueError('Unexpected original RAM read')
            a=ram[address];pc+=3
        elif op==0xE6:a &= master[pc+1];pc+=2
        elif op==0xF6:a |= master[pc+1];pc+=2
        elif op==0xD3:
            if master[pc+1]!=0xF4:raise ValueError('Unexpected original output port')
            ports.append(a);pc+=2
        elif op==0x3C:
            a=(a+1)&255;zero=a==0;pc+=1
        elif op==0xC8:
            if pc!=STOP-1:raise ValueError('Unexpected original RET Z site')
            pc+=1
        else:raise ValueError(f'Unexpected original B884 opcode {op:02X} at {pc:04X}')
        if pc==STOP:
            if stack or len(event)!=20 or callback_count!=1 or len(ports)!=1:
                raise ValueError('Original callback stage not completed')
            return {'scratch':bytes(state),'copy_pairs':event,
                    'e941':ram[0xE941],'e608':ram[0xE608],'out_f4':tuple(ports),
                    'accumulator':a,'next':'return_B8AB' if zero else 'continue_B8AC',
                    'bc8c_invocations':callback_count}
        if not START<=pc<STOP:raise ValueError('Original B884 left bounded stage')
    raise ValueError('Original B884 instruction budget exceeded')


def verify(master:bytes,cases:int=30000)->dict:
    if len(master)!=0x90000 or hashlib.sha256(master).hexdigest()!=MASTER_HASH:
        raise ValueError('Checksum-verified original arcade master required')
    if hashlib.sha256(master[START:STOP]).hexdigest()!=STAGE_SHA:
        raise ValueError('Original B884 opcode signature changed')
    if not 0<=cases<=100000:raise ValueError('Invalid case budget')
    rng=Random(0xB884)
    ends={'return_B8AB':0,'continue_B8AC':0}
    for i in range(cases):
        slot=rng.randbytes(256)
        scratch=rng.randbytes(96)
        e941=255 if i%2 else rng.randrange(255)
        e608=rng.randrange(256)
        expected=model(slot,scratch,e941,e608)
        observed=opcode(master,slot,scratch,e941,e608)
        if expected!=observed:
            for key in expected:
                if expected[key]!=observed[key]:
                    raise AssertionError(f'Original B884 mismatch case {i}, field {key}')
        ends[expected['next']]+=1
    return {'source':'original 1991 Indy Heat fixed-master B884-B8AB',
            'cases':cases,'mismatches':0,'original_20_byte_copy_cases':cases,
            'post_callback_return_cases':ends,
            'unverified':'BC8C effects and B8AC continuation; callback outputs are controlled inputs'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('master',type=Path)
    parser.add_argument('--cases',type=int,default=30000)
    args=parser.parse_args()
    print(json.dumps(verify(args.master.read_bytes(),args.cases),indent=2))
if __name__=='__main__':main()
