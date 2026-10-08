"""Immutable original8c16/Musashi versus the actual full15-register CLI.

The oracle executes original instructions, including DIVS; no host clone of
clamping, subtraction or division supplies the expected registers or RAM.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
from disassemble_program import load_verified_program
from musashi_oracle import MusashiOracle
from observe_scene_motion_pair import oracle_provenance
from verify_stage_catalog import SOURCE_SHA256

BASE,STACK,RETURN,ENTRY=0x100000,0x1feffc,0xff000,0x8c16
KEYS=tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(7))
UNCHANGED=KEYS[4:13]+('a6',)
BRANCHES=(0x8c20,0x8c2e,0x8c38,0x8c46,0x8c50,0x8c5e,0x8c7e,0x8c9c,0x8cac)


def sha(data):return hashlib.sha256(data).hexdigest()


def build_cases():
    cases=[]
    def add(family,targets=(0,0,0),current=(0,0,0),duration=3,profile=1,a5=0xffffffff):
        cases.append(dict(family=family,targets=list(targets),current=list(current),duration=duration,profile=profile,a5=a5))
    boundaries=(-32768,-32767,-256,-33,-32,-31,-30,-1,0,1,30,31,32,33,255,32766,32767)
    for channel in range(3):
        for value in boundaries:
            for profile in range(3):
                target=[1,-1,0];target[channel]=value
                add('per-channel-signed-clamp-boundary-highwords',target,(0x1234,0x8000,0xffff),profile=profile)
    for current in (0,1,0x1fff,0x7fff,0x8000,0x8001,0xdfff,0xffff):
        for target in (-31,0,31):
            for duration in (0,1,2,3,255):
                add('signed-WORD-target-minus-current-wrap', (target,target,target),(current,current,current),duration)
    for duration in range(256):
        add('all256-duration-lowbytes-nonzero-signed-deltas',(31,-31,0),(0x8000,1,0xffff),duration,profile=1 if duration&1 else 2)
        add('all256-duration-lowbytes-all-zero-deltas',(-31,0,31),(0xe100,0,0x1f00),duration,profile=1 if duration&1 else 2)
    for target,current in (((-31,-31,-31),(0xe100,)*3),((0,0,0),(0,)*3),((31,31,31),(0x1f00,)*3)):
        for profile in range(3):
            for duration in (0,1,2,255):add('zero-delta-preserves-steps-and-register-highwords',target,current,duration,profile)
    for target,current in (((32,-32,0),(0x1f00,0xe100,0)),((32767,-32768,31),(0x1f00,0xe100,0x1f00)),((-33,33,-32767),(0xe100,0x1f00,0xe100))):
        for profile in range(3):
            for duration in (0,3,255):add('zero-delta-clamped-MOVEQ-highwords-remain-observable',target,current,duration,profile)
    # Literal target0/current pairs select signed +/-32768/32767 and mixed
    # remainders. Expected results still come only from the native DIVS.
    for current in ((0x8000,0x8001,0x7fff),(1,0xffff,2),(2,0xfffe,0x7ffe),(0,0,1)):
        for duration in (1,2,3,7,127,128,255):add('DIVS-signed-extremes-and-remainder-packing',(0,0,0),current,duration)
    for a5 in (0,1,0x108000,0x100000,0x7fffffff,0x80000000,0xffffffff):
        add('arbitrary-input-A5-overwritten-before-memory',(1,-1,31),(0xffff,1,0x8000),7,a5=a5)
    assert len(cases)==883,len(cases)
    return cases


def fixture(case):
    ram=bytearray(hashlib.shake_256(b'palette-effect-execution'+bytes([case['profile']])).digest(65536))
    for index,current in enumerate(case['current']):struct.pack_into('>H',ram,0x7dc2+index*2,current)
    # Distinct stale steps prove that the zero-delta branch leaves them alone.
    struct.pack_into('>3H',ram,0x7dce,0x1234,0xabcd,0x8001)
    profiles=(0,0xabcd0000,0xffff0000)
    high=profiles[case['profile']]
    regs=[(high+(index+1)*0x10203)&0xffffffff for index in range(15)]
    for index,value in enumerate(case['targets']):regs[index]=high|(value&65535)
    regs[3]=high|0xa500|case['duration'];regs[13]=case['a5']
    return ram,regs


class Observer:
    def __init__(self,program):
        self.cpu=MusashiOracle();self.cpu.load(0,program[:BASE]);self.program=program
        self.pcs=[];self.writes=[]
        def code(pc):
            self.pcs.append(pc)
            assert ENTRY<=pc<=0x8cc8,(hex(pc),'unexpected execution')
        def write(pc,address,size,value):
            assert (address in (0x107dc8,0x107dca,0x107dcc,0x107dce,0x107dd0,0x107dd2) and size==2) or (address==0x107dd4 and size==1),(hex(pc),hex(address),size,value)
            self.writes.append(dict(pc=pc,address=address,size=size,value=value))
        self.cpu.set_instruction_hook(code);self.cpu.set_write_hook(write)

    def run(self,ram,regs):
        cpu=self.cpu;cpu.reset();cpu.load(BASE,ram);cpu.set_reg('sr',0x2000);cpu.set_reg('a7',STACK);cpu.load(STACK,RETURN.to_bytes(4,'big'))
        for key,value in zip(KEYS,regs):cpu.set_reg(key,value)
        cpu.set_reg('pc',ENTRY);self.pcs.clear();self.writes.clear();status=cpu.run(200,RETURN)
        assert status['status']=='sentinel' and status['pc']==RETURN and cpu.get_reg('a7')==STACK+4,status
        assert cpu.read(0,BASE)==self.program[:BASE] and cpu.read(STACK,4)==RETURN.to_bytes(4,'big')
        output=cpu.read(BASE,65536);result={key:cpu.get_reg(key) for key in KEYS}
        assert result['a5']==0x108000
        for key in UNCHANGED:assert result[key]==regs[KEYS.index(key)],key
        replay=bytearray(ram)
        for write in self.writes:replay[write['address']-BASE:write['address']-BASE+write['size']]=write['value'].to_bytes(write['size'],'big')
        assert bytes(replay)==output
        if 0x8ca4 in self.pcs:
            assert output[0x7dce:0x7dd4]==ram[0x7dce:0x7dd4] and output[0x7dd4]==0
            assert result['d3']&0xffff0000==regs[3]&0xffff0000 and result['d3']&65535==0
        else:
            assert 0x8cb6 in self.pcs and result['d3']<=255 and result['d3']!=0
        return output,result,dict(final_pc=RETURN,final_a7=cpu.get_reg('a7'),status=status,pcs=self.pcs.copy(),RAM_writes=self.writes.copy())


def negatives(root,exe,folder,cases):
    rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp,out=work/'input.bin',work/'output.bin';base,registers=fixture(cases[0]);sentinel=b'palette-effect-output-preserved\0\xff'
        def command(values=registers,source=inp,destination=out):return [str(exe)]+list(map(str,values))+[str(source),str(destination)]
        def reject(label,ram=base,values=registers,destination=out,source=inp,arguments=None):
            inp.write_bytes(ram)
            if destination!=inp and not(destination.exists() and os.path.samefile(destination,inp)):out.write_bytes(sentinel)
            watched={p:p.read_bytes() for p in (inp,out,destination) if p.exists() and p.is_file()}
            p=subprocess.run(arguments or command(values,source,destination),capture_output=True,text=True,timeout=2)
            assert p.returncode and not p.stdout and all(path.read_bytes()==before for path,before in watched.items()),(label,p.stdout,p.stderr)
            rows.append(dict(label=label,input_output_preserved=True,native_bad_fixture_executed=False,error=p.stderr.strip()))
        for size in (0,65535,65537):reject('RAM-size-%d'%size,ram=bytes(size))
        for index in range(15):
            for invalid in ('-1','4294967296','0x100000000','0x','1x',''):
                values=registers.copy();values[index]=invalid;reject('register-parser-%s'%KEYS[index],values=values)
        reject('missing-input-file',source=work/'absent.bin')
        reject('input-output-same-path',destination=inp)
        for kind in ('hardlink','symlink'):
            inp.write_bytes(base);alias=work/kind
            if kind=='hardlink':os.link(inp,alias)
            else:alias.symlink_to(inp)
            reject('input-output-'+kind,destination=alias)
        reject('missing-output-parent',destination=work/'absent'/'output.bin')
        reject('output-is-directory',destination=work)
        reject('input-is-directory',source=work)
        for label,args in (('missing-arguments',[str(exe)]),('extra-argument',command()+['extra'])):reject(label,arguments=args)
        fifo=work/'fifo';os.mkfifo(fifo)
        for role in ('input','output'):
            inp.write_bytes(base);out.write_bytes(sentinel)
            p=subprocess.run(command(source=fifo if role=='input' else inp,destination=fifo if role=='output' else out),capture_output=True,text=True,timeout=2)
            assert p.returncode and not p.stdout and inp.read_bytes()==base and out.read_bytes()==sentinel
            rows.append(dict(label='FIFO-'+role,rejected_without_blocking=True,input_output_preserved=True,native_bad_fixture_executed=False,error=p.stderr.strip()))
    return rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--native-only',action='store_true');options=parser.parse_args()
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/palette_effect_execution';folder.mkdir(parents=True,exist_ok=True)
    report=folder/('native.json' if options.native_only else 'verification.json');report.unlink(missing_ok=True)
    names=['tools/verify_palette_effect_execution.py','tools/musashi_oracle.py','tools/observe_scene_motion_pair.py','tools/disassemble_program.py','artifacts/stage_post_entry_contract.json','docs/analysis/stage-post-entry-contract.md']
    if not options.native_only:names+=['build/execute_palette_effect','engine/src/palette_effect_execution.cpp','engine/include/ms5/palette_effect_execution.h','engine/tools/execute_palette_effect.cpp','engine/include/ms5/object_restart_execution.h','engine/include/ms5/video_port.h','Makefile']
    inputs={name:sha((root/name).read_bytes()) for name in names}
    program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    audit=json.loads((root/'artifacts/stage_post_entry_contract.json').read_text());assert audit['source']==source
    instructions=next(r['rows'] for r in audit['ranges'] if r['cpu']==ENTRY)
    for row in instructions:assert bytes.fromhex(row['raw'])==program[row['rom_offset']:row['rom_offset']+len(bytes.fromhex(row['raw']))]
    oracle=oracle_provenance(root);observer=Observer(program);cases=build_cases();rows=[];branches=collections.defaultdict(set);zero=0;nonzero=0;remainders=set()
    exe=root/'build/execute_palette_effect';inp,out=folder/'input.bin',folder/'cpp.bin'
    for index,case in enumerate(cases):
        ram,regs=fixture(case);expected,result,info=observer.run(ram,regs)
        for pc,next_pc in zip(info['pcs'],info['pcs'][1:]):
            if pc in BRANCHES:branches[pc].add(next_pc)
        if 0x8ca4 in info['pcs']:zero+=1
        else:
            nonzero+=1
            for key in ('d0','d1','d2'):
                remainder=result[key]>>16;remainders.add('negative' if remainder&0x8000 else 'positive' if remainder else 'zero')
        if not options.native_only:
            inp.write_bytes(ram);out.write_bytes(b'old-output');p=subprocess.run([str(exe)]+list(map(str,regs))+[str(inp),str(out)],capture_output=True,text=True,timeout=2)
            assert p.returncode==0,(index,case,p.stderr)
            parsed=json.loads(p.stdout)
            assert parsed==result and inp.read_bytes()==ram and out.read_bytes()==expected,(index,case,parsed,result,[(hex(BASE+i),a,b) for i,(a,b) in enumerate(zip(out.read_bytes(),expected)) if a!=b][:20])
        rows.append(dict(case_index=index,fixture=case,incoming=dict(zip(KEYS,regs)),input_ram_sha256=sha(ram),result=result,ram_sha256=sha(expected),**info))
    reachable=tuple(pc for pc in BRANCHES if pc!=0x8cac)
    assert all(len(branches[pc])==2 for pc in reachable),{hex(pc):sorted(branches[pc]) for pc in reachable}
    assert len(branches[0x8cac])==1 and branches[0x8cac]=={0x8cb0} # duration was normalized >=1 before this test
    assert remainders=={'negative','positive','zero'} and zero and nonzero
    rejected=[] if options.native_only else negatives(root,exe,folder,cases)
    assert inputs=={name:sha((root/name).read_bytes()) for name in names} and oracle_provenance(root)==oracle and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report.write_text(json.dumps(dict(source=source,oracle=oracle,inputs=inputs,cases=len(rows),negative_cases=rejected,branches={hex(pc):sorted(branches[pc]) for pc in BRANCHES},both_outcomes_reachable_branches=list(reachable),unreachable_normalized_zero_duration_branch=0x8cac,zero_delta_cases=zero,nonzero_delta_cases=nonzero,signed_remainder_classes=sorted(remainders),full_RAM_15_registers_equal=not options.native_only,program_code_modified=False,in_call_SR_read=False,results=rows,scope='Whole immutable original8c16 throughRTS in pinnedMusashiM68000; full64KiBRAM and15regs. OriginalCPU signedclamp/WORDwrap/EXT.L/DIVS executeswithoutalgorithmclone. A5reset108000 fromarbitraryinput, unchangedD4..7/A0..4/A6 verified. SRsetbeforeA7; hooksneverreadSR. IsolatedoracleSTACK1feffc outsidecompared64KiBRAM; A7/stack native-only, noRAMmirror/hardwarestack/CCR/cycleequivalence claim. No runtime resource or hardware MMIO dependency.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negative_cases=len(rejected),zero_delta_cases=zero,nonzero_delta_cases=nonzero,sha256=sha(report.read_bytes()))))


if __name__=='__main__':main()
