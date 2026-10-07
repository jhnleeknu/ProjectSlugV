"""Full RAM/13register native differential plus transactional CLI error checks."""
import json
from pathlib import Path
import struct
import subprocess
import zlib
from observe_scene_placement_execution import (BASE, STACK, RETURN, KEYS, SOURCE_SHA256, sha,
    load_verified_program, build_cases, fixture, values, Observer, assert_evidence)

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    cases,resources,manifests=build_cases(root,program);folder=root/'artifacts/scene_placement_execution';folder.mkdir(parents=True,exist_ok=True)
    exe=root/'build/execute_scene_placement';binary=sha(exe.read_bytes());inp,out,report_path=[folder/name for name in ('input.bin','cpp.bin','verification.json')];report_path.unlink(missing_ok=True)
    dependencies=[root/item['file'] for item in resources];observer=Observer(program);rows=[];previous={};negatives=[]
    def cli(entry,regs,inputs=inp,output=out,paths=dependencies):
        return subprocess.run([str(exe),str(entry)]+list(map(str,regs))+list(map(str,(inputs,output)))+list(map(str,paths)),capture_output=True,text=True)
    for index,case in enumerate(cases):
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None
        ram=fixture(case) if prior is None else bytearray(prior[0]);struct.pack_into('>H',ram,0xd418,case['phase']);regs=values(case,None if prior is None else prior[1]);expected,result,calls=observer.run(case,ram,regs)
        assert_evidence(case,ram,expected,calls)
        inp.write_bytes(ram);actual=cli(case['entry'],regs);assert not actual.returncode,(index,case,actual.stderr)
        parsed=json.loads(actual.stdout);assert parsed.pop('entry')==case['entry'];cpp=out.read_bytes()
        assert inp.read_bytes()==ram
        if parsed!=result or cpp!=expected:
            failure=dict(case_index=index,fixture=case,incoming=regs,native=result,cpp=parsed,differences=[(hex(BASE+i),a,b) for i,(a,b) in enumerate(zip(expected,cpp)) if a!=b][:30]);(folder/'failure.json').write_text(json.dumps(failure,indent=2)+'\n');raise AssertionError(failure)
        rows.append(dict(case_index=index,fixture=case,incoming=dict(zip(KEYS,regs)),result=parsed,input_ram_sha256=sha(ram),ram_sha256=sha(cpp),native_calls=calls,final_pc=RETURN,final_a7=STACK+4,mmio_writes=0))
        if 'sequence'in case:previous[case['sequence']]=(cpp,[parsed[k] for k in KEYS])
    assert len(rows)==len(cases) and all(r['case_index']==i and r['fixture']==cases[i] for i,r in enumerate(rows))
    sentinel=b'placement-output-preserved\0\xff';sample=next(c for c in cases if c['family']=='bounds-accept' and not c['bounds']);ram=fixture(sample);regs=values(sample)
    def reject(data,registers=regs,entry=0x1a470,label='invalid',paths=dependencies,output=out):
        inp.write_bytes(data);out.write_bytes(sentinel);before=output.read_bytes() if output.exists() else None
        actual=cli(entry,registers,output=output,paths=paths)
        assert actual.returncode and inp.read_bytes()==data and (before is None or output.read_bytes()==before),(label,actual.stdout,actual.stderr)
        negatives.append(dict(failure=label,input_output_preserved=True,native_executed=False))
    for size in (0,65535,65537):reject(bytes(size),label='invalid-RAM-size')
    for field in range(13):
        for bad in ('-1','4294967296','0x100000000','0x','1x',''):
            r=list(regs);r[field]=bad;reject(ram,r,label='invalid-register-parser')
    for entry in (0,0x1a442,-1,'0x',''):
        reject(ram,entry=entry,label='invalid-entry-parser')
    for length in (1,3,0x8000,0x8002,0xffff):
        data=bytearray(ram);struct.pack_into('>H',data,sample['cursor']-BASE+2,length);reject(data,label='unsupported-inline-length')
    for pointer in (1,0x100001,0x10fff2,0xffffffff):
        r=list(regs);r[8]=pointer;reject(ram,r,label='invalid-placement-pointer')
    for pointer in (1,0x100001,0x10fffa,0xffffffff):
        data=bytearray(ram);struct.pack_into('>I',data,sample['cursor']-BASE+8,pointer);reject(data,label='bad-bounds-pointer')
    for offset,pointer in ((0x4c9c,0x10ff96),(0x208,0x10fffa)):
        data=bytearray(ram);struct.pack_into('>I',data,offset,pointer);reject(data,label='late-allocation-node-successor-rollback')
    for pointer in (0,0x100001,0x10ff96,0xffffffff):
        r=list(regs);r[12]=pointer;reject(ram,r,label='bad-allocation-parent-rollback')
    data=bytearray(ram);data[0xa000:0xa01a]=data[0x6000:0x601a];struct.pack_into('>H',data,0xa002,0x7ffe);r=list(regs);r[8]=0x10a000;reject(data,r,label='late-inline-copy-after-allocation-rollback')
    alias_case=next(c for c in cases if c.get('cursor')==0x100468 and c.get('synthetic'));data=fixture(alias_case);data[0x26a]=0xa5;reject(data,values(alias_case),label='live-allocator-write-makes-inline-count-unsupported')
    fixed=next(c for c in cases if not c.get('synthetic') and c['entry']==0x1a470 and c['motion']==0);fixedram=fixture(fixed);fixedregs=values(fixed)
    reject(fixedram,fixedregs,label='missing-fixed-placement-window',paths=[])
    actualmotion=next(c for c in cases if c.get('synthetic') and c['motion']);reject(fixture(actualmotion),values(actualmotion),label='missing-fixed-motion-window',paths=[])
    address=fixed['cursor'];raw=program[address:address+32];temporary=folder/'ambiguous.ms5d';temporary.write_bytes(struct.pack('<4s7I',b'MS5D',1,1,address,address,len(raw),zlib.crc32(raw),0)+raw)
    reject(fixedram,fixedregs,label='ambiguous-fixed-placement-window',paths=dependencies+[temporary]);temporary.unlink()
    for kind in ('same','hardlink','symlink'):
        inp.write_bytes(ram);alias=inp if kind=='same' else folder/('alias-'+kind+'.bin')
        if kind!='same':
            alias.unlink(missing_ok=True)
            if kind=='hardlink':alias.hardlink_to(inp)
            else:alias.symlink_to(inp)
        reject(ram,label='input-output-'+kind+'-alias',output=alias)
        if kind!='same':alias.unlink()
    for item in resources+manifests:assert sha((root/item['file']).read_bytes())==item['sha256']
    assert sha(exe.read_bytes())==binary and sha(program)==SOURCE_SHA256
    carry_calls=sum('sequence' in c for c in cases);consumed=sum(c.get('sequence_position',0)>0 for c in cases)
    report=dict(source=source,binary_sha256=binary,cases=len(rows),completed_cases=len(rows),negative_cases=len(negatives),full_ram_13_registers_equal=True,original_rom_immutable=True,mmio_writes=0,positive_input_RAM_preserved=True,all_RTS_A7_valid=True,resources=resources,manifests=manifests,cli_carry_sequences=len(previous),cli_carry_calls=carry_calls,cli_calls_consuming_previous_outputs=consumed,results=rows,negative_results=negatives,scope='Unpatched original1a414/1a470 continuous through19802,28ae,43e08 toRTS; no callee reset/normalization. Full64KiBRAM andD0-D7/A0/A1/A2/A4/A6 equality. Every canonicalplacementroot/record, all37canonicalmotionresources available; live synthetic RAMfixtures, bounds, allocator rejection fallback and WORDalias. CLI carry uses actual priorRAM/registers with explicit hostphase updates and entryA0/A6; no natural scheduling/CCR/callback execution claim.')
    report_path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),sha256=sha(report_path.read_bytes()))))
if __name__=='__main__':main()
