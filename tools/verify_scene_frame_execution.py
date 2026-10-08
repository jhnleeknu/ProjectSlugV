"""Full-frame original-call/CLI full RAM, 14-register and ordered-port differential."""
import collections
import json
import os
import struct
import tempfile
from pathlib import Path
import subprocess
import sys
from verify_scene_motion_bounds import container
from observe_scene_frame_execution import build_cases,fixture,prepare,assert_evidence,sha,KEYS,BASE,STACK,RETURN,load_verified_program,SOURCE_SHA256,oracle_provenance
BINARY_SHA256='96abbe5073647073f8e6e8185c12b6a9d759798268b724755debc88962bef0bd'


def negative_checks(root,cases,rs):
    folder=root/'artifacts/scene_frame_execution';exe=root/'build/step_scene_frame';table=root/'extracted/runtime/scene_debug.ms5d';dependencies=[root/r['file'] for r in rs if r['file']!=str(table.relative_to(root))];rows=[];assert len(dependencies)==457
    with tempfile.TemporaryDirectory(dir=folder) as temp:
        work=Path(temp);inp,out,ports=work/'input.bin',work/'output.bin',work/'ports.bin';path=work/'resource.ms5d';sentinel=b'full-frame-preserved-output\0\xff';case=cases[0];ram,regs=fixture(root,case);prepare(case,ram)
        def invoke(data,values,files=dependencies,tables=table,outputs=(out,ports)):
            inp.write_bytes(data)
            for target in set(outputs):
                if target!=inp and not (target.exists() and os.path.samefile(inp,target)):target.write_bytes(sentinel)
            watched={p:p.read_bytes() for p in set((inp,out,ports)+outputs) if p.exists()}
            actual=subprocess.run([str(exe)]+list(map(str,values))+list(map(str,(inp,outputs[0],outputs[1],tables)))+list(map(str,files)),capture_output=True,text=True)
            return actual,watched
        def reject(label,data=ram,values=regs,files=dependencies,tables=table,outputs=(out,ports)):
            actual,watched=invoke(data,values,files,tables,outputs);assert actual.returncode and all(p.read_bytes()==raw for p,raw in watched.items()),(label,actual.stdout,actual.stderr);rows.append(dict(failure=label,input_outputs_preserved=True,native_bad_fixture_executed=False,error=actual.stderr.strip()))
        baseline,_=invoke(ram,regs);assert baseline.returncode==0 and json.loads(baseline.stdout)['writes']>=4,baseline.stderr
        for size in (0,65535,65537):reject('RAM-size',bytes(size))
        for index in range(14):
            for text in ('-1','4294967296','0x100000000','0x','1x',''):
                values=regs.copy();values[index]=text;reject('register-parser-%d'%index,values=values)
        for selector in (1,2,12,0x8000,0xffff):
            bad=bytearray(ram);struct.pack_into('>I',bad,0xd422,0x106000);struct.pack_into('>H',bad,0x6000,selector);reject('unknown-condition-selector-after-bank-prefix',bad)
        for pointer in (0x106001,0x10ffff,0x110000,0x60000,0xfffffffe,0xffffffff):
            bad=bytearray(ram);struct.pack_into('>I',bad,0xd422,pointer);reject('late-condition-unaligned-missing-overflow-read',bad)
        for pointer in (1,0x106000,0xfffffffe,0xffffffff):
            bad=bytearray(ram);struct.pack_into('>I',bad,0xd412,pointer);struct.pack_into('>H',bad,0xd416,0);reject('active-script-selection-after-bank-prefix',bad)
        for pointer in (1,0x106000,0xfffffffe,0xffffffff):
            bad=bytearray(ram);struct.pack_into('>I',bad,0xd3b4,pointer);reject('late-active-motion-after-settings-writes',bad)
        for node in (0x9156,0xd2d6):
            for pointer in (1,0x100001,0x10fff0,0xffffffff):
                bad=bytearray(ram);struct.pack_into('>I',bad,node+0x10,pointer);reject('late-coordinate-parent-after-camera-shake',bad)
        for pointer in (1,0x106000,0xffffffff):
            bad=bytearray(ram);struct.pack_into('>I',bad,0xd356,pointer);reject('late-path-after-coordinate-prefix',bad)
        replay=next(c for c in cases if c['family']=='controlled-canonical-setup-replay-before-motion-path-selection' and c['seed_index']==4);replayram,replayregs=fixture(root,replay);prepare(replay,replayram)
        assert invoke(replayram,replayregs)[0].returncode==0
        reject('missing-all-resources-after-bank-prefix',files=[])
        reject('missing-maps-after-real-script-command-prefix',replayram,replayregs,[p for p in dependencies if '/scene_maps/' not in str(p)])
        reject('missing-secondary-after-real-script-command-prefix',replayram,replayregs,[p for p in dependencies if '/scene_secondary/' not in str(p)])
        reject('missing-script-window-after-condition',replayram,replayregs,[p for p in dependencies if not p.name.startswith('scene_')])
        root_script=replay['host_writes'][0]['hex'];address=int(root_script,16);body=(root/'extracted/program/maincpu.decrypted.be.bin').read_bytes()[address:address+8];path.write_bytes(container(body,cpu=address,rom=address));reject('ambiguous-script-window',replayram,replayregs,dependencies+[path])
        fixed=bytearray(ram);struct.pack_into('>I',fixed,0xd422,0x60000);path.write_bytes(container(bytes(2)));reject('partial-condition-force-word',fixed,files=dependencies+[path])
        rect=bytearray(ram);struct.pack_into('>I',rect,0xd422,0x60000);rect[0xd68e]=3;struct.pack_into('>I',rect,0xcb8,0x1234);rect[0xccd]=0x80;path.write_bytes(container(struct.pack('>H',4)+bytes(6)));reject('partial-condition-rectangle-LONG',rect,files=dependencies+[path])
        # Positive live-RAM placement baseline proves this late path is actually used.
        placement=bytearray(ram);struct.pack_into('>I',placement,0xd40e,0x106200);struct.pack_into('>H',placement,0xd418,0);placement[0x6200:0x6212]=struct.pack('>4H2IH',0,0,0,0,0,0x1234,0xffff)
        positive,_=invoke(placement,regs);assert positive.returncode==0 and int.from_bytes(out.read_bytes()[0xd40e:0xd412],'big')==0x106210 and int.from_bytes(out.read_bytes()[0x4ca0:0x4ca2],'big')==int.from_bytes(placement[0x4ca0:0x4ca2],'big')-1,positive.stderr
        for offset,value,label in ((0x6202,1,'odd-inline-length'),(0x6202,0x8000,'unsupported-large-inline-length')):
            bad=bytearray(placement);struct.pack_into('>H',bad,offset,value);reject('late-placement-'+label,bad)
        bad=bytearray(placement);struct.pack_into('>I',bad,0x4c9c,1);reject('late-used-free-head-after-update',bad)
        bad=bytearray(placement);struct.pack_into('>H',bad,0xd418,1);struct.pack_into('>I',bad,0x6208,0x106001);reject('late-placement-bounds-read-after-update',bad)
        for raw,label in ((b'bad','truncated-header'),(container(body)[:-1],'truncated-payload'),(container(body,version=2),'bad-version'),(container(body,kind=3),'wrong-kind'),(container(body,reserved=1),'reserved'),(container(body)+b'x','extra-payload')):
            path.write_bytes(raw);reject('resource-loader-'+label,files=dependencies+[path])
        corrupt=bytearray(container(body));corrupt[-1]^=1;path.write_bytes(corrupt);reject('resource-payload-CRC',files=dependencies+[path])
        path.write_bytes(container(bytes(512),cpu=0x1af10,rom=0x1af10));reject('wrong-debug-table-address',tables=path)
        path.write_bytes(container(bytes(510),cpu=0x1af12,rom=0x1af12));reject('wrong-debug-table-size',tables=path)
        reject('missing-table',tables=work/'missing.ms5d')
        for outputs in ((inp,ports),(out,inp),(out,out)):reject('input-output-or-output-output-alias',outputs=outputs)
        for label in ('hardlink','symlink'):
            inp.write_bytes(ram);alias=work/label
            if label=='hardlink':os.link(inp,alias)
            else:alias.symlink_to(inp)
            reject('input-output-'+label,outputs=(alias,ports))
        for target,label in ((inp,'resource-input-alias'),(out,'resource-output-RAM-alias'),(ports,'resource-output-ports-alias')):reject(label,files=dependencies+[target])
        for target,label in ((inp,'table-input-alias'),(out,'table-output-RAM-alias'),(ports,'table-output-ports-alias')):reject(label,tables=target)
    return rows


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;cases,rs,manifests,metadata=build_cases(root,program);exe=root/'build/step_scene_frame';binary=sha(exe.read_bytes());assert binary==BINARY_SHA256;folder=root/'artifacts/scene_frame_execution';negatives=negative_checks(root,cases,rs)
    if '--negative-only' in sys.argv:print(json.dumps(dict(negative_cases=len(negatives))));return
    path=folder/'observation.json';raw=path.read_bytes();native=json.loads(raw);oracle=oracle_provenance();assert native['oracle']==oracle
    assert native['source']==source and native['resources']==rs and native['manifests']==manifests and native['metadata']==metadata and native['failure'] is None and not native['program_code_modified'] and not native['physical_bank_payload_modified'] and not native['in_call_SR_read']
    assert native['cases']==native['completed_cases']==len(native['results'])==len(cases)==594
    table=root/'extracted/runtime/scene_debug.ms5d';dependencies=[root/r['file'] for r in rs if r['file']!=str(table.relative_to(root))];inp,out,ports=[folder/n for n in ('input.bin','cpp.bin','cpp.ports.bin')];previous={};rows=[];calls=collections.Counter();branches=collections.Counter();banks=collections.Counter()
    for index,(case,row) in enumerate(zip(cases,native['results'])):
        assert row['case_index']==index and row['fixture']==case and row['returned'] and row['final_pc']==RETURN and row['final_a7']==STACK+4 and row['mmio_reads']==0
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None;ram,regs=fixture(root,case) if prior is None else (bytearray(prior[0]),prior[1].copy());prepare(case,ram);assert sha(ram)==row['input_ram_sha256'] and dict(zip(KEYS,regs))==row['incoming']
        expected=(folder/row['ram_file']).read_bytes();expected_ports=(folder/row['ports_file']).read_bytes();assert sha(expected)==row['ram_sha256'] and sha(expected_ports)==row['ports_sha256'];assert_evidence(case,ram,expected,expected_ports,row);inp.write_bytes(ram)
        actual=subprocess.run([str(exe)]+list(map(str,regs))+list(map(str,(inp,out,ports,table)))+list(map(str,dependencies)),capture_output=True,text=True);assert actual.returncode==0,(index,case,actual.stderr);parsed=json.loads(actual.stdout);cpp=out.read_bytes();cpp_ports=ports.read_bytes();assert inp.read_bytes()==ram
        if parsed!=dict(row['result'],writes=row['port_count']) or cpp!=expected or cpp_ports!=expected_ports:
            failure=dict(case_index=index,fixture=case,native=dict(row['result'],writes=row['port_count']),cpp=parsed,RAM_differences=[(hex(BASE+i),a,b) for i,(a,b) in enumerate(zip(expected,cpp)) if a!=b][:30],ports_native_sha256=sha(expected_ports),ports_cpp_sha256=sha(cpp_ports),native_ports_bytes=len(expected_ports),cpp_ports_bytes=len(cpp_ports));(folder/'failure.json').write_text(json.dumps(failure,indent=2)+'\n');raise AssertionError(failure)
        calls.update(row['calls']);branches.update((b['pc'],b['next_pc']) for b in row['branch_successors']);banks.update(row['physical_bank_reads']);rows.append(dict(case_index=index,family=case['family'],result=parsed,ram_sha256=sha(cpp),ports_sha256=sha(cpp_ports),port_count=row['port_count']))
        if 'sequence'in case:previous[case['sequence']]=(cpp,[parsed[k] for k in KEYS])
    assert len(previous)==6
    for pc,a,b in ((0x1a756,0x1a75a,0x1a75e),(0x1a77c,0x1a780,0x1a784)):assert branches[(pc,a)] and branches[(pc,b)]
    assert calls['0x19cd6'] and calls['0x19ce6'] and calls['0x185f2'] and banks['0x200000'] and banks['0x300000']
    assert calls['0x28ae']>=4 and calls['0x2912']>=2 and calls['0x43e08']>=4
    by_sequence=collections.defaultdict(list)
    for case,row in zip(cases,native['results']):
        if 'sequence' in case:by_sequence[case['sequence']].append(row)
    progress=by_sequence['canonical-script-wait16-settings'];commands={pc for row in progress for pc in row['command_addresses']};assert {0xda0a4,0xda0a8,0xda0b2,0xda0b6}<=commands and progress[0]['boundaries'][0]['phase']==0 and progress[-1]['boundaries'][-1]['phase']==32
    two=by_sequence['canonical-two-eligible-placements'];executed=[r for r in two if r['calls'].get('0x1a470')];assert len(executed)==2 and executed[1]['fixture']['sequence_position']==executed[0]['fixture']['sequence_position']+1
    first={b['pc']:b for b in executed[0]['boundaries']};second={b['pc']:b for b in executed[1]['boundaries']};assert first[0x1a78c]['phase']==832 and first[0x1a78c]['placement']==0xdcea8 and first[0x1a790]['placement']==0xdceb8 and second[0x1a78c]['placement']==0xdceb8 and second[0x1a790]['placement']==0xdcec8
    empty=by_sequence['canonical-empty-allocation-placement'];assert sum(r['calls'].get('0x2912',0) for r in empty)==2 and sum(any(w['address']==0x100ec6 for w in r['fallback_position_writes']) for r in empty)==2
    for debug in (8,16):assert any(c.get('debug',c.get('initializer',{}).get('debug'))==debug and row['calls'].get('0x1b0e0') and row['port_count']>4 for c,row in zip(cases,native['results']))
    shake_values={next(b for b in row['boundaries'] if b['pc']==0x1a788)['shake'] for c,row in zip(cases,native['results']) if c['family']=='shake-propagation-before-coordinate-update'};assert 8 in shake_values and 0xfff8 in shake_values
    carry_calls=sum(len(group) for group in by_sequence.values());assert carry_calls==360
    directory_index=next(i for i,c in enumerate(cases) if c['family']=='controlled-canonical-setup-replay-before-motion-path-selection' and c['seed_index']==4);case=cases[directory_index];row=native['results'][directory_index];ram,regs=fixture(root,case);prepare(case,ram);inp.write_bytes(ram)
    directories=[root/'extracted/runtime'/d for d in ('scene_scripts','scene_maps','scene_secondary','scene_placements')]
    assert {str(p.relative_to(root)) for d in directories for p in d.glob('*.ms5d')}=={r['file'] for r in rs if r['file']!=str(table.relative_to(root))}
    actual=subprocess.run([str(exe)]+list(map(str,regs))+list(map(str,(inp,out,ports,table)))+list(map(str,directories)),capture_output=True,text=True);assert actual.returncode==0 and inp.read_bytes()==ram and json.loads(actual.stdout)==dict(row['result'],writes=row['port_count']) and out.read_bytes()==(folder/row['ram_file']).read_bytes() and ports.read_bytes()==(folder/row['ports_file']).read_bytes(),actual.stderr
    assert oracle_provenance()==oracle and sha(exe.read_bytes())==binary and path.read_bytes()==raw and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    for item in rs+manifests:assert sha((root/item['file']).read_bytes())==item['sha256']
    for label in ('initialization_observation','initialization_verification','frame_inventory'):assert sha((root/metadata[label+'_file']).read_bytes())==metadata[label+'_sha256']
    report=dict(source=source,oracle=oracle,binary_sha256=binary,native_observation_sha256=sha(raw),cases=len(rows),directory_loader_case_index=directory_index,cli_carry_sequences=len(previous),cli_carry_calls=carry_calls,cli_calls_consuming_previous_outputs=carry_calls-len(previous),families=dict(collections.Counter(c['family'] for c in cases)),negative_cases=len(negatives),negative_results=negatives,ports=sum(r['port_count'] for r in rows),resources=rs,manifests=manifests,metadata=metadata,original_ROM_and_resources_immutable=True,positive_input_RAM_preserved=True,full_RAM_14_registers_ordered_ports_equal=True,native_call_counts=dict(calls),native_branch_paths=[dict(pc=pc,next_pc=n,count=c) for (pc,n),c in sorted(branches.items())],physical_bank_reads=dict(banks),results=rows,scope='Original uninterrupted full 1a73c call in Unicorn with no in-call SR reads; full RAM, 14 exposed registers, exact ordered 9-byte ports and native RTS/A7+4. Original fixed ROM and physical banks 2/3 immutable with exact PVC mapping. Actual native initializer output seeds; no callee substitution or in-call resets. Six actual CLI output chains cover 360 frames, with only initial force WORDd44c written and no subsequent host RAM/register rewrites. Four explicit initial setup replay cases reposition d412/d416/d422, clear d3b4 and all four path cursors before original canonical commands publish new resources. Other initial condition/enable/player-callback/shake/debug writes are listed exactly per fixture; phase/current XY are retained from the native seeds. Native shake output reaches five coordinate ADD.W operations. Canonical gates831/832 execute on separate frames despite both being eligible, and the empty-pool version proves real fallback writes. No naturally reachable post-wait motion/path replacement claim. No CCR, IRQ, scheduler, callback execution or natural-player claim.')
    report_path=folder/'verification.json';report_path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),ports=report['ports'],sha256=sha(report_path.read_bytes()))))
if __name__=='__main__':main()
