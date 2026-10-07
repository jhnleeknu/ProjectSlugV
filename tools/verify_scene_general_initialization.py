"""Stored continuous native1a5a4 vs actual CLI, full14regs/RAM/orderedports."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import zlib
from observe_scene_general_initialization import (SOURCE_SHA256, KEYS, sha, load_verified_program,
    build_cases, fixture, values, resources, assert_evidence)

def invoke(exe,regs,inp,out,ports,dependencies):
    return subprocess.run([str(exe)]+list(map(str,regs))+list(map(str,(inp,out,ports)))+list(map(str,dependencies)),capture_output=True,text=True)

def negatives(root,program,cases,rs,exe,folder):
    inp,out,ports=[folder/name for name in ('negative.input.bin','negative.ram.bin','negative.ports.bin')];dependencies=[root/r['file'] for r in rs];results=[]
    sample=next(c for c in cases if c['script']==0xd9edc and c['target']==0 and c['available']);ram=fixture(program,sample);regs=values(sample);sentinel=b'general-initializer-preserve-output\0\xff'
    def reject(data=ram,inputs=regs,paths=dependencies,label='invalid',outputs=(out,ports)):
        inp.write_bytes(data);out.write_bytes(sentinel);ports.write_bytes(sentinel);watched={p:p.read_bytes() for p in (inp,out,ports)+tuple(outputs)}
        actual=invoke(exe,inputs,inp,outputs[0],outputs[1],paths)
        assert actual.returncode and all(p.read_bytes()==before for p,before in watched.items()),(label,actual.stdout,actual.stderr)
        results.append(dict(failure=label,input_outputs_preserved=True,native_bad_fixture_executed=False,error=actual.stderr.strip()))
    for size in (0,65535,65537):reject(bytes(size),label='invalid-RAM-size')
    for register in range(14):
        for text in ('-1','4294967296','0x100000000','0x','1x',''):
            r=list(regs);r[register]=text;reject(inputs=r,label='invalid-register-parser')
    for pointer in (1,0x100001,0x10fffe,0xffffffff):
        r=list(regs);r[8]=pointer;reject(inputs=r,label='unsupported-script-pointer-after-initial-bank-ports')
    for pointer in (0,1,0x100001,0x10ff96,0xffffffff):
        r=list(regs);r[13]=pointer;reject(inputs=r,label='late-allocation-parent-after-map-port-prefix')
    for offset,pointer in ((0x4c9c,1),(0x4c9c,0x10ff96)):
        data=bytearray(ram);struct.pack_into('>I',data,offset,pointer);reject(data,label='late-used-free-head-rollback')
    reject(paths=[root/'extracted/runtime/scene_debug.ms5d'],label='missing-script-window-after-initial-bank-ports')
    reject(paths=[p for p in dependencies if '/scene_maps/' not in str(p)],label='missing-map-window-after-script-port-prefix')
    reject(paths=[p for p in dependencies if '/scene_placements/' not in str(p)],label='missing-placement-window-after-map-port-prefix')
    reject(paths=[p for p in dependencies if '/scene_secondary/' not in str(p)],label='missing-secondary-window-after-script-port-prefix')
    reject(paths=[p for p in dependencies if p.name!='scene_debug.ms5d'],label='missing-required-debug-tables')
    reject(paths=[],label='all-resources-omitted')
    malformed=folder/'negative.bad.ms5d';malformed.write_bytes(b'bad');reject(paths=dependencies+[malformed],label='malformed-resource-input');malformed.unlink()
    address=sample['script'];raw=program[address:address+8];overlap=folder/'negative.overlap.ms5d';overlap.write_bytes(struct.pack('<4s7I',b'MS5D',1,1,address,address,len(raw),zlib.crc32(raw),0)+raw)
    reject(paths=dependencies+[overlap],label='ambiguous-fixed-script-window');overlap.unlink()
    for first,second in ((inp,out),(inp,ports),(out,ports)):
        outputs=(first if second==out else out,first if second==ports else ports);reject(label='input-output-or-output-output-alias',outputs=outputs)
    for kind in ('hardlink','symlink'):
        inp.write_bytes(ram);alias=folder/('negative.alias-'+kind);alias.unlink(missing_ok=True)
        if kind=='hardlink':alias.hardlink_to(inp)
        else:alias.symlink_to(inp)
        reject(label='input-output-'+kind+'-alias',outputs=(alias,ports));alias.unlink()
    return results

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--positive-only',action='store_true');parser.add_argument('--negative-only',action='store_true');options=parser.parse_args()
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    folder=root/'artifacts/scene_general_initialization';exe=root/'build/initialize_scene';binary=sha(exe.read_bytes());rs,manifests=resources(root,program);cases=build_cases(root,program)
    if options.negative_only:
        rejected=negatives(root,program,cases,rs,exe,folder);print(json.dumps(dict(negative_cases=len(rejected),binary_sha256=binary)));return
    observation=folder/'observation.json';raw=observation.read_bytes();native=json.loads(raw);assert native['source']==source and native['failure'] is None
    assert len(native['results'])==native['completed_cases']==native['cases']==len(cases)
    dependencies=[root/r['file'] for r in rs];inp,out,ports=[folder/name for name in ('input.bin','cpp.bin','cpp.ports.bin')];rows=[];previous={}
    for index,(row,case) in enumerate(zip(native['results'],cases)):
        assert row['case_index']==index and row['fixture']==case and row['returned'] and row['final_a7']==0x1ff000
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None
        ram=fixture(program,case) if prior is None else bytearray(prior[0]);regs=values(case,None if prior is None else prior[1]);assert sha(ram)==row['input_ram_sha256'] and dict(zip(KEYS,regs))==row['incoming']
        expected=(folder/row['ram_file']).read_bytes();expected_ports=(folder/row['ports_file']).read_bytes();assert sha(expected)==row['ram_sha256'] and sha(expected_ports)==row['ports_sha256']
        assert_evidence(case,ram,expected,expected_ports,row)
        inp.write_bytes(ram);actual=invoke(exe,regs,inp,out,ports,dependencies);assert not actual.returncode,(index,case,actual.stderr)
        parsed=json.loads(actual.stdout);expected_result=dict(row['result'],writes=row['port_count']);cpp=out.read_bytes();cpp_ports=ports.read_bytes();assert inp.read_bytes()==ram
        if parsed!=expected_result or cpp!=expected or cpp_ports!=expected_ports:
            failure=dict(case_index=index,fixture=case,native=expected_result,cpp=parsed,ram_differences=[(hex(0x100000+i),a,b) for i,(a,b) in enumerate(zip(expected,cpp)) if a!=b][:30],port_bytes_expected=len(expected_ports),port_bytes_cpp=len(cpp_ports),port_sha256_native=sha(expected_ports),port_sha256_cpp=sha(cpp_ports));(folder/'failure.json').write_text(json.dumps(failure,indent=2)+'\n');raise AssertionError(failure)
        if 'sequence' in case:previous[case['sequence']]=(cpp,[parsed[k] for k in KEYS])
        rows.append(dict(case_index=index,fixture=case,result=parsed,ram_sha256=sha(cpp),ports_sha256=sha(cpp_ports),port_count=row['port_count'],calls=row['calls'],instructions=row['instructions']))
    assert any(r['calls'].get('0x1a65a',0)>1 for r in rows)
    assert any(r['calls'].get('0x1a470',0)>0 for r in rows)
    assert any(r['calls'].get('0x185f2',0)>0 and r['port_count']>4 for r in rows)
    for debug in (8,16):assert any(r['fixture']['debug']==debug and r['calls'].get('0x1b0e0',0)>0 for r in rows)
    assert any(not r['fixture']['available'] and r['calls'].get('0x2912',0)>0 for r in rows)
    assert len(previous)==4
    rejected=[] if options.positive_only else negatives(root,program,cases,rs,exe,folder)
    for item in rs+manifests:assert sha((root/item['file']).read_bytes())==item['sha256']
    assert sha(exe.read_bytes())==binary and observation.read_bytes()==raw and sha(program)==SOURCE_SHA256
    report=dict(source=source,binary_sha256=binary,native_observation_sha256=sha(raw),cases=len(rows),completed_cases=len(rows),negative_cases=len(rejected),full_RAM_14_registers_ordered_ports_equal=True,ports=sum(r['port_count'] for r in rows),positive_input_RAM_preserved=True,cli_carry_sequences=len(previous),cli_carry_calls=8,cli_calls_consuming_previous_outputs=4,original_ROM_and_resources_immutable=True,resources=rs,manifests=manifests,results=rows,negative_results=rejected,scope='Native continuous unpatched1a5a4/RTS compare complete64KiBRAM,14registers D0-D7,A0-A4,A6 and every ordered9byteport. Original2790/3ef2 seed input outsidecall; explicit debug/bounds/allocation fixtures. Physicalbank2/3 identities preserved. FouractualCLIcarry sequences retain priorRAM/registers with targetD0.low,scriptA0,parentA6 reasserted byhost. No callback/scheduler/IRQ/CCR equivalence claim.')
    report_path=folder/('verification.initial.json' if options.positive_only else 'verification.json');report_path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),negative_cases=len(rejected),ports=report['ports'],sha256=sha(report_path.read_bytes()))))
if __name__=='__main__':main()
