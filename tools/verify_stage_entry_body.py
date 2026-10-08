"""Actual CLI differential against immutable whole47a94 native observations."""
import gzip
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
from observe_stage_entry_body import (BASE,STACK,RETURN,KEYS,ARGS,STATE_KEYS,PREFIX,
    SOURCE_SHA256,sha,put,initial,load_verified_program,resources,build_cases,
    prepare_case,provenance,oracle_provenance)


def invoke(exe,state,external,inp,out,ports,table,windows,timeout=20):
    values=[state[k] for k in KEYS+ARGS]+[external,state['a5'],state['body_phase']]
    return subprocess.run([str(exe)]+list(map(str,values))+list(map(str,(inp,out,ports,table)))+list(map(str,windows)),capture_output=True,text=True,timeout=timeout)


def main():
    root=Path(__file__).resolve().parents[1]
    verifier_at_entry=sha(Path(__file__).read_bytes())
    folder=root/'artifacts/stage_entry_body';exe=root/'build/step_stage_entry_body'
    report=folder/'verification.json';report.unlink(missing_ok=True)
    names=['tools/verify_stage_entry_body.py','build/step_stage_entry_body','engine/tools/step_stage_entry_body.cpp','Makefile']
    names += [str(p.relative_to(root)) for directory in ('engine/src','engine/include/ms5') for p in (root/directory).glob('*') if p.suffix in ('.cpp','.h')]
    inputs={n:sha((root/n).read_bytes()) for n in names}
    assert inputs['tools/verify_stage_entry_body.py']==verifier_at_entry
    program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    rs,metadata,groups=resources(root,program);cases=build_cases(program,groups)
    observation=folder/'observation.json';raw=observation.read_bytes();native=json.loads(raw)
    assert native['source']==source and native['failure'] is None and native['inputs']==provenance(root) and native['oracle']==oracle_provenance()
    assert native['resources']==rs and native['metadata']==metadata and native['cases']==native['completed_cases']==len(cases)==len(native['results'])
    assert not native['program_code_modified'] and not native['physical_bank_payload_modified'] and not native['in_call_SR_read']
    table=root/'extracted/runtime/scene_debug.ms5d';mask=root/'extracted/runtime/stage_input/default_masks.ms5d'
    windows=[root/r['file'] for r in rs if root/r['file']!=table]
    inp,out,ports=(folder/n for n in ('input.bin','cpp.bin','cpp.ports.bin'))
    rows=[];pending=set();event_branches=set();lookup_seen=set();first_frame_boundaries=0
    for index,(case,row) in enumerate(zip(cases,native['results'])):
        assert row['case_index']==index and row['fixture']==case
        ram,state,fixture_metadata=prepare_case(root,program,case)
        assert row['fixture_metadata']==fixture_metadata
        for phase in row['phases']:
            for write in phase['host_writes']:
                data=bytes.fromhex(write['hex']);at=write['address']-BASE
                assert ram[at:at+len(data)].hex()==write['previous']
                ram[at:at+len(data)]=data
            assert phase['incoming']==state and phase['input_ram_sha256']==sha(ram)
            expected=(folder/phase['ram_file']).read_bytes();expected_ports=(folder/phase['ports_file']).read_bytes()
            packed=(folder/phase['trace_file']).read_bytes();assert sha(packed)==phase['trace_sha256']
            trace=json.loads(gzip.decompress(packed));assert trace['schema_version']==phase['trace_schema_version']==1
            assert phase['trace_format']=='gzip JSON pcs/RAM_writes/physical_bank_reads'
            assert len(trace['pcs'])==phase['instructions'] and len(trace['RAM_writes'])==phase['RAM_write_count'] and len(trace['physical_bank_reads'])==phase['physical_bank_read_count']
            assert sha(expected)==phase['ram_sha256'] and sha(expected_ports)==phase['ports_sha256'] and len(expected_ports)==9*phase['port_count']
            replay=bytearray(ram)
            for w in trace['RAM_writes']:replay[w['address']-BASE:w['address']-BASE+w['size']]=w['value'].to_bytes(w['size'],'big')
            assert bytes(replay)==expected
            if state['body_phase']==0:
                assert [p['pc'] for p in phase['prefix']]==list(PREFIX)
                event=next(p for p in phase['prefix'] if p['pc']==0xe905c)
                callback=next(p for p in phase['prefix'] if p['pc']==0x47ae6)
                events=[struct.unpack_from('>BII',expected_ports,offset*9) for offset in range(event['port_count'],callback['port_count'])]
                assert events[0]==(1,0x300001,event['registers']['d0']&255)
                nonnull=event['registers']['a0']!=0
                assert events[1:]==([(2,0x2ffff2,0x1000),(2,0x2ffff0,0)] if nonnull else [])
                event_branches.add(nonnull);lookup_seen.add(case['lookup']);first_frame_boundaries+=1
                call_pcs=[p['pc'] for p in phase['boundaries']]
                expected_callees=[0x47642,0x1a73c,0x49b0c,0x4aa88,0xb4a2a,0x6f1c2,0x4701e,0xe8a48,0x2efa6]
                assert call_pcs==expected_callees
            else:
                assert not phase['prefix'] and not any(pc in trace['pcs'] for pc in PREFIX)
                assert not phase['external_reads']
            inp.write_bytes(ram);out.write_bytes(b'old-output');ports.write_bytes(b'old-ports')
            # Sound resume proves unrelated initializer table/windows are unused.
            chosen_table=table if state['body_phase']==0 else mask
            chosen_windows=windows if state['body_phase']==0 else []
            p=invoke(exe,state,phase['external'],inp,out,ports,chosen_table,chosen_windows)
            assert p.returncode==0,(index,case,phase['name'],p.stderr)
            parsed=json.loads(p.stdout)
            assert inp.read_bytes()==ram and out.read_bytes()==expected and ports.read_bytes()==expected_ports and parsed==phase['result'],(index,case,phase['name'],parsed,phase['result'],[(hex(BASE+i),a,b) for i,(a,b) in enumerate(zip(out.read_bytes(),expected)) if a!=b][:20])
            assert phase['final_a5']==parsed['a5']==0x108000
            if parsed['body_phase']==1:pending.add((parsed['sound_kind'],parsed['sound_phase']))
            else:assert parsed['body_phase']==2 and phase['final_pc']==RETURN and phase['final_a7']==STACK+4
            ram=bytearray(out.read_bytes());state={k:parsed[k] for k in STATE_KEYS}
            rows.append(dict(case_index=index,name=phase['name'],result=parsed,input_ram_sha256=phase['input_ram_sha256'],ram_sha256=sha(ram),ports_sha256=sha(expected_ports),port_count=phase['port_count'],native_trace_sha256=phase['trace_sha256'],initializer_resources_omitted_on_resume=chosen_windows==[]))
    assert pending=={(1,1),(1,2),(2,1),(2,2),(2,3)} and event_branches=={False,True} and lookup_seen==set(range(8))
    negatives=[]
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);ni,no,np=(work/n for n in ('input.bin','output.bin','ports.bin'))
        base,base_state,_=prepare_case(root,program,cases[0]);sentinel=b'preserved-entry-body-output\0\xff'
        def reject(label,ram=base,state=base_state,external=0,selected=windows,selected_table=table,outputs=None):
            destinations=(no,np) if outputs is None else outputs
            ni.write_bytes(ram)
            for path in destinations:
                if path not in selected and path!=selected_table and path!=ni and not(path.exists() and os.path.samefile(path,ni)):path.write_bytes(sentinel)
            watched={path:path.read_bytes() for path in set((ni,no,np,selected_table)+destinations+tuple(selected)) if path.exists() and path.is_file()}
            p=invoke(exe,state,external,ni,destinations[0],destinations[1],selected_table,selected)
            assert p.returncode and not p.stdout and all(path.read_bytes()==before for path,before in watched.items()),(label,p.stdout,p.stderr)
            negatives.append(dict(label=label,input_outputs_resources_preserved=True,native_bad_fixture_executed=False,error=p.stderr.strip()))
        for size in (0,65535,65537):reject('RAM-size-%d'%size,ram=bytes(size))
        for key in STATE_KEYS:
            for invalid in ('-1','4294967296','0x','1x',''):
                reject('numeric-parser-'+key,state=dict(base_state,**{key:invalid}))
        for external in ('-1','256','1x',''):reject('external-parser',external=external)
        for values in (dict(a5=0),dict(a5=0x108001),dict(body_phase=3),dict(body_phase=2),dict(body_phase=1),dict(body_phase=0,stage=3,sound_kind=1,sound_phase=1),dict(body_phase=1,stage=0),dict(body_phase=0,saved_a0=1),dict(a6=0x100001),dict(a6=0x110000),dict(a6=0xffffffff)):
            reject('invalid-body-state',state=dict(base_state,**values))
        reject('missing-record-group-windows',selected=[p for p in windows if '/stages/' not in str(p)])
        reject('missing-lookup-after-initializer-ports',selected=[p for p in windows if p.name!='lookup_0030ec.ms5d'])
        reject('missing-event-windows-after-initializer-ports',selected=[p for p in windows if '/stage_events/' not in str(p)])
        reject('missing-all-fresh-windows',selected=[])
        bad=bytearray(base);put(bad,0xc04,2,1);reject('late-event-restart-type-after-scene-and-lookup',ram=bad)
        bad=bytearray(base);put(bad,0xdc88,4,0x110000);reject('late-frame-buffer-after-all-initializers',ram=bad)
        waited=next(r for r in native['results'] if r['fixture']['family']=='wholebody-sound-wait' and r['fixture']['rising'] and r['fixture']['target']==1)['phases'][0]
        bad=bytearray((folder/waited['ram_file']).read_bytes());put(bad,0x4d74,2,0xffff)
        captured={k:waited['result'][k] for k in STATE_KEYS};captured['a0']=0x110000
        reject('late-sound-resume-write-range',ram=bad,state=captured,selected=[],selected_table=mask)
        reject('input-output-alias',outputs=(ni,np));reject('input-ports-alias',outputs=(no,ni));reject('output-output-alias',outputs=(no,no))
        reject('resource-output-collision',outputs=(windows[0],np));reject('table-output-collision',outputs=(table,np))
        for kind in ('hardlink','symlink'):
            ni.write_bytes(base);alias=work/kind
            if kind=='hardlink':os.link(ni,alias)
            else:alias.symlink_to(ni)
            reject('input-output-'+kind,outputs=(alias,np))
        fifo=work/'fifo';os.mkfifo(fifo)
        for role in ('input','RAM-output','port-output','table','window'):
            ni.write_bytes(base);no.write_bytes(sentinel);np.write_bytes(sentinel)
            input_path=fifo if role=='input' else ni
            ram_path=fifo if role=='RAM-output' else no
            port_path=fifo if role=='port-output' else np
            table_path=fifo if role=='table' else table
            resource_paths=windows+[fifo] if role=='window' else windows
            p=invoke(exe,base_state,0,input_path,ram_path,port_path,table_path,resource_paths,timeout=2)
            assert p.returncode and not p.stdout and ni.read_bytes()==base and no.read_bytes()==sentinel and np.read_bytes()==sentinel
            negatives.append(dict(label='FIFO-'+role,rejected_without_blocking=True,input_outputs_preserved=True,native_bad_fixture_executed=False,error=p.stderr.strip()))
        probe=work/'CaseSensitivity.probe';probe.write_bytes(b'case probe');folded=work/'casesensitivity.probe'
        insensitive=folded.exists() and os.path.samefile(probe,folded)
        case_alias=dict(case_insensitive_filesystem=insensitive,applicable=insensitive)
        if insensitive:
            first,second=work/'NewBody.bin',work/'newbody.bin';assert not first.exists() and not second.exists();ni.write_bytes(base)
            p=invoke(exe,base_state,0,ni,first,second,table,windows)
            assert p.returncode and not p.stdout and ni.read_bytes()==base and not first.exists() and not second.exists()
            case_alias.update(rejected=True,input_and_absent_outputs_preserved=True,error=p.stderr.strip())
    assert inputs=={n:sha((root/n).read_bytes()) for n in names}
    assert observation.read_bytes()==raw and native['inputs']==provenance(root) and native['oracle']==oracle_provenance()
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256
    for item in rs+metadata:assert sha((root/item['file']).read_bytes())==item['sha256']
    result=dict(source=source,inputs=inputs,oracle=native['oracle'],native_observation_sha256=sha(raw),cases=len(cases),phases=len(rows),canonical_unique_records=59,resource_count=len(rs),pending_sound_states=sorted(pending),lookup_indices=sorted(lookup_seen),event_null_and_nonnull_observed=sorted(event_branches),first_frame_boundaries=first_frame_boundaries,live_record_reread_fixture=True,negative_cases=negatives,case_alias_regression=case_alias,full_RAM_15_registers_bank_pending_ordered_ports_external_reads_equal=True,actual_CLI_outputs_carried_across_waits=True,source_resources_binary_oracle_unchanged=True,results=rows,scope=native['scope'])
    report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(cases),phases=len(rows),negative_cases=len(negatives),ports=sum(r['port_count'] for r in rows),sha256=sha(report.read_bytes()))))


if __name__=='__main__':main()
