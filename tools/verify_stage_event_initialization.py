"""Full15register/RAM/ordered-port e905c differential plus rollback errors."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import zlib
from observe_stage_event_initialization import (SOURCE_SHA256, KEYS, sha, load_verified_program,
    build_cases, fixture, values, assert_evidence)

def resources(root,program):
    directory=root/'extracted/runtime/stage_events';path=directory/'manifest.json';manifest=json.loads(path.read_text());assert manifest['source']['sha256']==SOURCE_SHA256
    assert manifest['counts']==dict(resources=95,streams=47,indirect_pointers=47,lookups=1,catalog_records=59,stream_payload_bytes=48685,total_payload_bytes=48881,total_container_bytes=51921,overlaps=0)
    items=manifest['resources'];assert len(items)==95;result=[];ranges=[]
    for item in items:
        p=directory/item['file'];data=p.read_bytes();payload=data[32:];cpu=item['source_cpu_address'];size=item['payload_size']
        assert struct.unpack('<4s7I',data[:32])==(b'MS5D',1,1,cpu,cpu,size,zlib.crc32(payload),0)
        assert item['source_rom_offset']==cpu and item['end_cpu_address_exclusive']==item['end_rom_offset_exclusive']==cpu+size
        assert len(payload)==size and payload==program[cpu:cpu+size] and sha(data)==item['sha256'] and sha(payload)==item['payload_sha256'] and len(data)==item['size']
        if item['role']=='event_stream':assert size&1 and payload[-1]==255
        if item['role']=='event_indirect_pointer':assert size==4 and int.from_bytes(payload,'big')==item['raw_be32']
        ranges.append((cpu,cpu+size));result.append(dict(file=str(p.relative_to(root)),sha256=sha(data),cpu=cpu,rom=cpu,size=size,role=item['role']))
    ranges.sort();assert all(a[1]<=b[0] for a,b in zip(ranges,ranges[1:]))
    metadata=[]
    for p in (path,root/'artifacts/stage_event_contexts.json',root/'extracted/runtime/stages/manifest.json'):
        metadata.append(dict(file=str(p.relative_to(root)),sha256=sha(p.read_bytes())))
    assert metadata[1]['sha256']==manifest['regenerated_context_sha256'] and metadata[2]['sha256']==manifest['stage_catalog_manifest_sha256']
    return result,metadata

def invoke(exe,registers,inp,out,ports,dependencies):
    return subprocess.run([str(exe)]+list(map(str,registers))+list(map(str,(inp,out,ports)))+list(map(str,dependencies)),capture_output=True,text=True)

def negatives(root,program,cases,rs,exe,folder):
    inp,out,ports=[folder/name for name in ('negative.input.bin','negative.ram.bin','negative.ports.bin')];dependencies=[root/r['file'] for r in rs];results=[];sentinel=b'stage-event-initialization-output-preserved\0\xff'
    sample=next(c for c in cases if c['stream'] and c['target']==0xffff and c['profile']==1);ram=fixture(program,sample);regs=values(sample)
    def reject(data=ram,registers=regs,paths=dependencies,label='invalid',outputs=(out,ports)):
        inp.write_bytes(data);out.write_bytes(sentinel);ports.write_bytes(sentinel);watched={p:p.read_bytes() for p in (inp,out,ports)+tuple(outputs)}
        result=invoke(exe,registers,inp,outputs[0],outputs[1],paths)
        assert result.returncode and all(p.read_bytes()==before for p,before in watched.items()),(label,result.stdout,result.stderr)
        results.append(dict(failure=label,input_outputs_preserved=True,native_bad_fixture_executed=False,error=result.stderr.strip()))
    for size in (0,65535,65537):reject(bytes(size),label='invalid-RAM-size')
    for register in range(15):
        for text in ('-1','4294967296','0x100000000','0x','1x',''):
            r=list(regs);r[register]=text;reject(registers=r,label='invalid-register-parser')
    for a5 in (0,0x108001,0x11734a,0xffffffff):
        r=list(regs);r[13]=a5;reject(registers=r,label='A5-derived-object-alignment-or-span')
    for stream in (1,0x100001,0x10ffff,0xffffffff,0x100):
        r=list(regs);r[8]=stream;reject(registers=r,label='late-header-read-after-watchdog')
    data=bytearray(ram);struct.pack_into('>H',data,0xc04,1);reject(data,label='nonzero-restart-object-type-original-TRAP')
    reject(paths=[],label='missing-fixed-stream-window-after-watchdog')
    # All synthetic malformed readers run only on C++; original TRAP/cycle is not a positive.
    r=list(regs);r[8]=0x106000;r[0]=(r[0]&0xffff0000)|1
    for marker in (1,0x7f,0xfe):
        data=bytearray(ram);data[0x6000:0x6008]=struct.pack('>HBBHH',0,marker,0,8,6);reject(data,r,label='late-unsupported-marker-after-watchdog')
    data=bytearray(ram);data[0x6000:0x6008]=struct.pack('>HBBHH',1,0,0,0,0);reject(data,r,label='odd-header-jump-to-WORD-gate-read')
    r[0]=(r[0]&0xffff0000)|9;data=bytearray(ram);data[0x6000:0x6008]=struct.pack('>HBBHH',0,0,0,8,1);reject(data,r,label='odd-next-jump-to-WORD-gate-read')
    data=bytearray(ram);data[0x6000:0x6008]=struct.pack('>HBBHH',0,0,0,8,0x8000);reject(data,r,label='signed-next-jump-outside-provided-RAM-window')
    r[0]=(r[0]&0xffff0000)|1;data=bytearray(ram);data[0x6000:0x6008]=struct.pack('>HBBHH',0,0,0,0,0);reject(data,r,label='zero-jump-gate-cycle-budget-rollback');assert 'budget' in results[-1]['error']
    live=next(c for c in cases if c.get('ram_alias') and c['target']==1);data=fixture(program,live);r=values(live);r[8]=0x100c6a;struct.pack_into('>H',data,0xc6a,0x1234);reject(data,r,label='restart-clears-live-header-to-zero-gate-cycle-budget');assert 'budget' in results[-1]['error']
    attached=next(c for c in cases if c['count']==2 and c['coord']==0 and c['parent']==0x100200);data=fixture(program,attached);r=values(attached);struct.pack_into('>I',data,0xd4f6,0x100001);reject(data,r,label='late-coordinate-parent-after-palette-and-node-writes')
    gate=next(s['gates'][0]['cpu_address'] for s in json.loads((root/'artifacts/stage_event_contexts.json').read_text())['streams'] if s['stream_cpu_address']==sample['stream']);raw=program[gate:gate+6];ambiguous=folder/'negative.overlap.ms5d';ambiguous.write_bytes(struct.pack('<4s7I',b'MS5D',1,1,gate,gate,len(raw),zlib.crc32(raw),0)+raw)
    reject(paths=dependencies+[ambiguous],label='late-ambiguous-fixed-gate-window-after-header');ambiguous.unlink()
    malformed=folder/'negative.bad.ms5d';malformed.write_bytes(b'bad');reject(paths=dependencies+[malformed],label='malformed-resource-container');malformed.unlink()
    for pair in ((inp,ports),(out,inp),(out,out)):reject(label='input-output-or-output-output-same-path-alias',outputs=pair)
    for kind in ('hardlink','symlink'):
        inp.write_bytes(ram);alias=folder/('negative.alias-'+kind);alias.unlink(missing_ok=True)
        if kind=='hardlink':alias.hardlink_to(inp)
        else:alias.symlink_to(inp)
        reject(label='input-output-'+kind+'-alias',outputs=(alias,ports));alias.unlink()
    return results

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--negative-only',action='store_true');options=parser.parse_args()
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    folder=root/'artifacts/stage_event_initialization';exe=root/'build/initialize_stage_events';binary=sha(exe.read_bytes());cases=build_cases(root,program);rs,metadata=resources(root,program)
    if options.negative_only:
        rejected=negatives(root,program,cases,rs,exe,folder);assert sha(exe.read_bytes())==binary;print(json.dumps(dict(negative_cases=len(rejected),binary_sha256=binary)));return
    observation=folder/'observation.json';raw=observation.read_bytes();native=json.loads(raw);assert native['source']==source and native['failure'] is None and native['inventory_sha256']==metadata[1]['sha256']
    assert len(native['results'])==native['completed_cases']==native['cases']==len(cases)
    inp,out,ports=[folder/name for name in ('input.bin','cpp.bin','cpp.ports.bin')];rows=[];previous={};dependencies=[root/r['file'] for r in rs]
    for index,(row,case) in enumerate(zip(native['results'],cases)):
        assert row['case_index']==index and row['fixture']==case and row['returned'] and row['final_a7']==0x1ff000
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None;ram=fixture(program,case) if prior is None else bytearray(prior[0]);regs=values(case,None if prior is None else prior[1]);assert sha(ram)==row['input_ram_sha256'] and dict(zip(KEYS,regs))==row['incoming']
        expected=(folder/row['ram_file']).read_bytes();expected_ports=(folder/row['ports_file']).read_bytes();assert sha(expected)==row['ram_sha256'] and sha(expected_ports)==row['ports_sha256'];assert_evidence(case,ram,expected,row['result'],expected_ports,row,regs)
        inp.write_bytes(ram);actual=invoke(exe,regs,inp,out,ports,dependencies);assert not actual.returncode,(index,case,actual.stderr)
        parsed=json.loads(actual.stdout);expected_result=dict(row['result'],writes=row['port_count']);cpp=out.read_bytes();cpp_ports=ports.read_bytes();assert inp.read_bytes()==ram
        if parsed!=expected_result or cpp!=expected or cpp_ports!=expected_ports:
            failure=dict(case_index=index,fixture=case,native=expected_result,cpp=parsed,ram_differences=[(hex(0x100000+i),a,b) for i,(a,b) in enumerate(zip(expected,cpp)) if a!=b][:30],native_ports_hex=expected_ports.hex(),cpp_ports_hex=cpp_ports.hex());(folder/'failure.json').write_text(json.dumps(failure,indent=2)+'\n');raise AssertionError(failure)
        if 'sequence'in case:previous[case['sequence']]=(cpp,[parsed[k] for k in KEYS])
        rows.append(dict(case_index=index,fixture=case,result=parsed,input_ram_sha256=sha(ram),ram_sha256=sha(cpp),ports_sha256=sha(cpp_ports),port_count=row['port_count'],calls=row['calls'],visited_gate_cursors=row['visited_gate_cursors'],instructions=row['instructions']))
    assert len(previous)==2 and len(set(c['gate'] for c in cases if 'gate'in c))==612
    canonical_gates=set(json.loads((root/'artifacts/stage_event_contexts.json').read_text())['gate_cpu_addresses']);observed_gates={address for row in rows for address in row['visited_gate_cursors']}
    assert canonical_gates<=observed_gates and len(canonical_gates)==612
    assert any(r['calls'].get('0x8e4a',0)>0 for r in rows) and any(r['calls'].get('0x43e38',0)>0 for r in rows)
    rejected=negatives(root,program,cases,rs,exe,folder)
    assert sha(exe.read_bytes())==binary and observation.read_bytes()==raw and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    for item in rs+metadata:assert sha((root/item['file']).read_bytes())==item['sha256']
    report=dict(source=source,binary_sha256=binary,native_observation_sha256=sha(raw),cases=len(rows),completed_cases=len(rows),negative_cases=len(rejected),full_RAM_15_registers_ordered_ports_equal=True,ports=sum(r['port_count'] for r in rows),positive_input_RAM_preserved=True,canonical_gate_addresses_observed=612,original_ROM_and_resources_immutable=True,resources=rs,metadata=metadata,cli_carry_sequences=len(previous),cli_carry_calls=6,cli_calls_consuming_previous_outputs=4,results=rows,negative_results=rejected,scope='Originale905c andoriginal2a28/cleanup continuous toRTS. Complete64KiBRAM/15registers D0-D7,A0-A6 andorderedwatchdog/PVC9byteevents equal; no patches/intra-call reset/MMIOreads. All47rawstreamwindows/all612gate boundaries and59literalcataloginputs; target0 skip, null preservesRAM10, signednegativeRAMjumps, alternateA5object selection, live resetheader→oddFFcursor. All95MS5Dwindows sourcebyte/hash closure incl47pointercells/lookup. TwoactualCLIcarry sequences usepriorRAM/registers withhostD0.low/A0/A5 inputs. No callbackexecution/full eventgrammar/natural scheduling/CCR claim.')
    path=folder/'verification.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),negative_cases=len(rejected),ports=report['ports'],sha256=sha(path.read_bytes()))))
if __name__=='__main__':main()
