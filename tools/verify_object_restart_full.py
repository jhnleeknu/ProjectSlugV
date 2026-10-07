"""Unpatched2a28 observations vs full15register CLI and transactional errors."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
from observe_object_restart_full import (SOURCE_SHA256, KEYS, sha, load_verified_program,
    build_cases, fixture, values, assert_evidence)

def invoke(exe,registers,inp,out,ports):
    return subprocess.run([str(exe)]+list(map(str,registers))+list(map(str,(inp,out,ports))),capture_output=True,text=True)

def negatives(program,cases,exe,folder):
    inp,out,ports=[folder/name for name in ('negative.input.bin','negative.ram.bin','negative.ports.bin')];results=[];sentinel=b'full-object-restart-output-preserved\0\xff'
    sample=next(c for c in cases if c['count']==1 and c['reference']==1 and c['profile']==1);ram=fixture(program,sample);regs=values(sample)
    def reject(data=ram,registers=regs,label='invalid',outputs=(out,ports)):
        inp.write_bytes(data);out.write_bytes(sentinel);ports.write_bytes(sentinel);watched={p:p.read_bytes() for p in (inp,out,ports)+tuple(outputs)}
        result=invoke(exe,registers,inp,outputs[0],outputs[1])
        assert result.returncode and all(p.read_bytes()==before for p,before in watched.items()),(label,result.stdout,result.stderr)
        results.append(dict(failure=label,input_outputs_preserved=True,native_bad_fixture_executed=False,error=result.stderr.strip()))
    for size in (0,65535,65537):reject(bytes(size),label='invalid-RAM-size')
    for register in range(15):
        for text in ('-1','4294967296','0x100000000','0x','1x',''):
            r=list(regs);r[register]=text;reject(registers=r,label='invalid-register-parser')
    for address in (0,1,0x100001,0x10ff3e,0xffffffff):
        r=list(regs);r[8]=address;reject(registers=r,label='invalid-object-address-or-span')
    for type in (1,0x7fff,0x8000,0xffff):
        data=bytearray(ram);struct.pack_into('>H',data,sample['object']-0x100000+0x10,type);reject(data,label='input-nonzero-object-type-original-TRAP')
    for coordinate in (8,9,0x7f):
        data=bytearray(ram);data[sample['object']-0x100000+0x6c]=coordinate;reject(data,label='late-coordinate-index-after-palette-release')
    for field in (0x4d92,0x4d94,0x5d92):
        for link in (1,0x8000,0xb26a,0xffff):
            data=bytearray(ram);struct.pack_into('>H',data,field,link);reject(data,label='late-signed-palette-link-alignment-or-RAM-span')
    attached=next(c for c in cases if c['coord']==0 and c['parent']==0x100200 and c['profile']==1);coordram=fixture(program,attached);coordregs=values(attached)
    for parent in (1,0x100001,0x10ffdc,0xffffffff):
        data=bytearray(coordram);struct.pack_into('>I',data,0xd4f6,parent);reject(data,coordregs,label='late-coordinate-parent-after-palette-and-node-writes')
    edge=next(c for c in cases if c['object']==0x10ff3c);data=fixture(program,edge);data[0xff59]=255;reject(data,values(edge),label='raw-count255-object-near-RAM-end-late-slot-read')
    alias=next(c for c in cases if c.get('alias_type') and not c['next_type']);aliasram=fixture(program,alias);aliasregs=values(alias)
    for field in (0x6004,0x6008):
        for pointer in (1,0x100001,0x10fffa,0xffffffff):
            data=bytearray(aliasram);struct.pack_into('>I',data,field,pointer);reject(data,aliasregs,label='late-linked-fallback-pointer-after-alias-type-change')
    data=bytearray(aliasram);struct.pack_into('>I',data,0x6004,0x106000);struct.pack_into('>I',data,0x4c9c,0x106000);reject(data,aliasregs,label='linked-self-cycle-65536-loop-budget-rollback')
    assert 'budget' in results[-1]['error']
    for output_pair in ((inp,ports),(out,inp),(out,out)):
        reject(label='input-output-or-output-output-same-path-alias',outputs=output_pair)
    for kind in ('hardlink','symlink'):
        inp.write_bytes(ram);aliasfile=folder/('negative.alias-'+kind);aliasfile.unlink(missing_ok=True)
        if kind=='hardlink':aliasfile.hardlink_to(inp)
        else:aliasfile.symlink_to(inp)
        reject(label='input-output-'+kind+'-alias',outputs=(aliasfile,ports));aliasfile.unlink()
    return results

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--negative-only',action='store_true');options=parser.parse_args()
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    folder=root/'artifacts/object_restart_full';exe=root/'build/restart_object_full';binary=sha(exe.read_bytes());cases=build_cases()
    if options.negative_only:
        rejected=negatives(program,cases,exe,folder);assert sha(exe.read_bytes())==binary;print(json.dumps(dict(negative_cases=len(rejected),binary_sha256=binary)));return
    observation=folder/'observation.json';raw=observation.read_bytes();native=json.loads(raw);assert native['source']==source and native['failure'] is None
    assert len(native['results'])==native['completed_cases']==native['cases']==len(cases)
    inp,out,ports=[folder/name for name in ('input.bin','cpp.bin','cpp.ports.bin')];rows=[];previous={}
    for index,(row,case) in enumerate(zip(native['results'],cases)):
        assert row['case_index']==index and row['fixture']==case and row['returned'] and row['final_a7']==0x1ff000
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None
        ram=fixture(program,case) if prior is None else bytearray(prior[0]);regs=values(case,None if prior is None else prior[1]);assert sha(ram)==row['input_ram_sha256'] and dict(zip(KEYS,regs))==row['incoming']
        expected=(folder/row['ram_file']).read_bytes();expected_ports=(folder/row['ports_file']).read_bytes();assert sha(expected)==row['ram_sha256'] and sha(expected_ports)==row['ports_sha256'];assert_evidence(case,ram,expected,row['result'],expected_ports,row,regs)
        inp.write_bytes(ram);actual=invoke(exe,regs,inp,out,ports);assert not actual.returncode,(index,case,actual.stderr)
        parsed=json.loads(actual.stdout);expected_result=dict(row['result'],writes=row['port_count']);cpp=out.read_bytes();cpp_ports=ports.read_bytes();assert inp.read_bytes()==ram
        if parsed!=expected_result or cpp!=expected or cpp_ports!=expected_ports:
            failure=dict(case_index=index,fixture=case,native=expected_result,cpp=parsed,ram_differences=[(hex(0x100000+i),a,b) for i,(a,b) in enumerate(zip(expected,cpp)) if a!=b][:30],native_ports_hex=expected_ports.hex(),cpp_ports_hex=cpp_ports.hex());(folder/'failure.json').write_text(json.dumps(failure,indent=2)+'\n');raise AssertionError(failure)
        if 'sequence'in case:previous[case['sequence']]=(cpp,[parsed[k] for k in KEYS])
        rows.append(dict(case_index=index,fixture=case,result=parsed,input_ram_sha256=sha(ram),ram_sha256=sha(cpp),ports_sha256=sha(cpp_ports),port_count=row['port_count'],calls=row['calls'],instructions=row['instructions']))
    assert len(previous)==4 and any(r['calls'].get('0x8e4a',0)>0 for r in rows) and any(r['calls'].get('0x43e38',0)>0 for r in rows) and any(r['calls'].get('0x29c0',0)>1 for r in rows)
    rejected=negatives(program,cases,exe,folder)
    assert sha(exe.read_bytes())==binary and observation.read_bytes()==raw and sha(program)==SOURCE_SHA256 and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report=dict(source=source,binary_sha256=binary,native_observation_sha256=sha(raw),cases=len(rows),completed_cases=len(rows),negative_cases=len(rejected),full_RAM_15_registers_ordered_ports_equal=True,ports=sum(r['port_count'] for r in rows),positive_input_RAM_preserved=True,original_ROM_immutable=True,cli_carry_sequences=len(previous),cli_carry_calls=12,cli_calls_consuming_previous_outputs=8,results=rows,negative_results=rejected,scope='Original2a28 with everycleanupcallee andlinkedfallback uninterrupted toRTS, full64KiBRAM/15registers D0-D7,A0-A6 andorderedwatchdog9byteevents. No originalROMpatch/calleecontextreset. Raw counts0..4 and5/8/32/128/255, refs0/1/2/ffff, callbackLONGs odd/RAM/ffffffff, signedlinks, coordinateparents/aliases andsyntheticpalettewrites modifyingtype exercise original read/write order. Original3ef2 initializes palette beforeentry. FouractualCLIcarry sequences retain outputRAM/registers; hostobjectA0/callbackA1 are explicit. No callbackexecution/CCR/fullstackmemory/natural scheduling claim.')
    path=folder/'verification.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),negative_cases=len(rejected),ports=report['ports'],sha256=sha(path.read_bytes()))))
if __name__=='__main__':main()
