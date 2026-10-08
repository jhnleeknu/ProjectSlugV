"""Full actualCLI16ea4 comparisons and continuous previous-output resumes.

Native report/source/input/output hashes and original phase traces are audited.
The C++ chain always feeds its own previous RAM/15regs/waiting forward, applying
only the recorded external RAM writes. Expected native state is never injected.
"""
import argparse
import collections
import json
import os
from pathlib import Path
import subprocess
import tempfile
from observe_object_sprite_wrapper import (BASE,STACK,RETURN,WAIT_PC,KEYS,ENTRY,RANGES,
    SOURCE_SHA256,sha,cases,fixture,expected_prefix,Observer,oracle_provenance,
    load_verified_program,assert_native_writes,branch_counts)
NATIVE_SHA='49b4e745f9243d6c6b044e81327c7cbaa5122c2d051d8bdfe9734793ea95c525'


def invoke(exe,regs,waiting,inp,out):
    flag=int(waiting) if type(waiting) is bool else waiting
    return subprocess.run([str(exe)]+[str(regs[k]) for k in KEYS]+[str(flag),str(inp),str(out)],capture_output=True,text=True,timeout=2)


def apply_writes(ram,writes):
    result=bytearray(ram)
    for item in writes:
        at=item['address']-BASE;raw=bytes.fromhex(item['raw_hex'])
        assert 0<=at and at+len(raw)<=65536;result[at:at+len(raw)]=raw
    return bytes(result)


def audit(root,program,source):
    folder=root/'artifacts/object_sprite_wrapper';path=folder/'observation.json';raw=path.read_bytes();native=json.loads(raw)
    assert sha(raw)==NATIVE_SHA and native['source']==source and sha(program)==SOURCE_SHA256
    assert native['oracle']==oracle_provenance(root) and not native['program_code_modified'] and native['failure'] is None
    for item in native['inputs']:assert sha((root/item['file']).read_bytes())==item['sha256'],item
    static_path=folder/'source.json';static=json.loads(static_path.read_bytes())
    assert static['source']==source and static['ranges']==[list(r) for r in RANGES]
    by_pc={r['cpu_address']:r for r in static['instructions']}
    for start,end in RANGES:
        cursor=start
        for row in static['instructions']:
            if start<=row['cpu_address']<end:
                assert row['classification']=='candidate_instruction' and row['rom_offset']==row['cpu_address']==cursor
                assert bytes.fromhex(row['raw'])==program[cursor:cursor+row['size']];cursor+=row['size']
        assert cursor==end
    assert len(native['results'])==native['cases']==len(cases())==96
    artifacts={str(path.relative_to(root)):sha(raw),str(static_path.relative_to(root)):sha(static_path.read_bytes())}
    counts=collections.Counter();phases=0;pending=0;writes=0;observer=Observer(program)
    for index,(case,row) in enumerate(zip(cases(),native['results'])):
        assert row['case_index']==index and row['fixture']==case
        ram,regs=fixture(case,index);before=ram;incoming=regs
        assert len(row['phases'])==(3 if case['pending'] else 1)
        observer.prepare(ram,regs);captured=None
        for i,phase in enumerate(row['phases']):
            assert phase['phase']==('begin','hold','ready')[i]
            before=apply_writes(before,phase['external_RAM_writes'])
            assert sha(before)==phase['input_ram_sha256'] and phase['incoming']==incoming
            path=folder/phase['ram_file'];output=path.read_bytes();assert sha(output)==phase['ram_sha256'];artifacts[str(path.relative_to(root))]=phase['ram_sha256']
            pcs=phase['pcs'];assert all(pc in by_pc for pc in pcs) and len(pcs)==phase['native']['instructions']
            assert phase['native']['fault_address']==0 and phase['native']['cpu_writes']==len(phase['ordered_writes'])
            assert phase['RAM_writes']==[e for e in phase['ordered_writes'] if e['kind']=='ram']
            replay=bytearray(before)
            for event in phase['ordered_writes']:
                assert event['pc'] in pcs and event['size'] in (2,4) and 0<=event['value']<1<<(8*event['size'])
                if event['kind']=='ram':
                    at=event['address']-BASE;assert 0<=at and at+event['size']<=65536
                    replay[at:at+event['size']]=event['value'].to_bytes(event['size'],'big')
                else:assert event==dict(pc=0xcd5c,address=STACK-4,size=4,value=0xcd5e,kind='stack')
            assert bytes(replay)==output and phase['mmio_writes']==0
            assert set(phase['result'])==set(KEYS) and phase['waiting']==(phase['status']==3)
            assert_native_writes(phase['status'],phase['RAM_writes'],case['deferred'])
            if i==0:
                assert not phase['external_RAM_writes'] and pcs[0]==ENTRY
                assert phase['boundary_snapshots']==[dict(pc=0xcd58,registers=expected_prefix(ram,regs),a7=STACK)]
                assert len([e for e in phase['ordered_writes'] if e['kind']=='stack'])==1
                captured=phase['result']
            else:
                assert not phase['boundary_snapshots'] and not any(ENTRY<=pc<0x16ed2 or pc in (0xcd58,0xcd5c,0xcd82,0xcd98) for pc in pcs)
            if i==1:
                assert phase['native']['status']=='budget_exhausted' and pcs==[0xcda4,0xcda8] and phase['native']['pc']==WAIT_PC
                assert phase['result']==captured and output==before and not phase['ordered_writes'] and len(phase['external_RAM_writes'])==8
            else:
                assert phase['native']['status']=='sentinel' and phase['native']['pc']==(WAIT_PC if case['pending'] and i==0 else RETURN)
            assert phase['final_a7']==(STACK if phase['waiting'] else STACK+4)
            # Independent same-nativeCPU replay, without reset/register/SR writes
            # after prepare; observer.mutate contains only listed host RAM writes.
            observer.mutate(phase['external_RAM_writes'])
            result,actual,actual_regs,actual_pcs,events,snapshots=observer.run(WAIT_PC if case['pending'] and i==0 else RETURN,2 if i==1 else 2000)
            assert result==phase['native'] and actual==output and actual_regs==phase['result'] and actual_pcs==pcs
            assert events==phase['ordered_writes'] and snapshots==phase['boundary_snapshots']
            counts[str(phase['status'])]+=1;phases+=1;writes+=len(phase['RAM_writes']);before=output;incoming=phase['result']
        pending+=case['pending']
    assert phases==native['phases']==112 and pending==native['pending_chains']==8
    assert dict(sorted(counts.items()))==native['counts_by_status'] and branch_counts(native['results'])==native['branch_successor_counts']
    return native,raw,artifacts,dict(cases=96,phases=112,pending_chains=8,native_RAM_writes=writes,
        statuses=dict(sorted(counts.items())),six_callee_conditional_branches_both_outcomes=True,actual_native_replays=112)


def negatives(exe,folder,native):
    rows=[];case=cases()[0];base,regs=fixture(case,0)
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp,out=work/'input.bin',work/'output.bin';sentinel=b'preserved-object-sprite-output'
        def reject(label,state=regs,waiting=False,payload=base,source=None,destination=None,command=None):
            inp.write_bytes(payload);out.write_bytes(sentinel)
            src=inp if source is None else source;dest=out if destination is None else destination
            watched={p:p.read_bytes() for p in (inp,out,src,dest) if p.exists() and p.is_file()}
            process=subprocess.run(command,capture_output=True,text=True,timeout=2) if command else invoke(exe,state,waiting,src,dest)
            assert process.returncode and not process.stdout,(label,process.stdout,process.stderr)
            assert all(p.read_bytes()==data for p,data in watched.items()),label
            rows.append(dict(label=label,input_outputs_preserved=True,native_bad_fixture_executed=False,error=process.stderr.strip()))
        for size in (0,65535,65537):reject('RAM-size-'+str(size),payload=bytes(size))
        for key in KEYS:
            for bad in ('-1','4294967296','0x100000000','0x','1x',''):
                reject('register-parser-'+key+'-'+repr(bad),state=dict(regs,**{key:bad}))
        for bad in ('-1','2','4294967296','0x','1x',''):
            reject('waiting-parser-'+repr(bad),waiting=bad)
        for a6 in (0,0xffffffff,0x10ffad,0xfffac,0xfffad,0x100001,0xfffbe):
            reject('fresh-object-reached-read-span-A6-'+hex(a6),state=dict(regs,a6=a6))
        for callback in (0,0x106000,0xffffffff):
            payload=bytearray(base);payload[0x9152:0x9156]=callback.to_bytes(4,'big')
            reject('callback-failure-after-prefix-'+hex(callback),payload=bytes(payload))
        clipped=bytearray(base);clipped[0x9152:0x9156]=(0x106000).to_bytes(4,'big')
        reject('unsupported-callback-before-clip',state=dict(regs,d0=0),payload=bytes(clipped))
        for key,at,values in (('normal-index',0x8d38,(1,0x74cc)),('deferred-index',0x914e,(1,0x70b2))):
            for value in values:
                payload=bytearray(base);payload[at:at+2]=value.to_bytes(2,'big')
                if key=='deferred-index':payload[case['a6']-BASE+0x12:case['a6']-BASE+0x16]=(regs['d1']|64).to_bytes(4,'big')
                reject('late-'+key+'-'+hex(value),payload=bytes(payload))
        for offset in (1,0x8000,0x80ca):
            payload=bytearray(base);payload[0x8b36:0x8b38]=offset.to_bytes(2,'big')
            reject('late-record-write-'+hex(offset),payload=bytes(payload))
        pending=next(row for row in native['results'] if row['fixture']['pending'])['phases'][0]
        pending_regs=pending['result'];pending_ram=(folder.parent/'object_sprite_wrapper'/pending['ram_file']).read_bytes()
        for a5 in (0,0x108001,0x108002,0xffffffff):
            reject('captured-wait-invalid-A5-'+hex(a5),state=dict(pending_regs,a5=a5),waiting=True,payload=pending_ram)
        # Synthetic public ready snapshots test checked source/destination errors;
        # they are deliberately not represented as original captured histories.
        ready=bytearray(pending_ram);ready[0x8d34:0x8d36]=(pending_regs['d4']&65535).to_bytes(2,'big')
        for d6,a1,label in ((1,0x108b34,'odd-index'),(0,0x110000,'outside-source'),(0,0xffffffff,'overflow-source')):
            reject('synthetic-resume-'+label,state=dict(pending_regs,d6=d6,a1=a1),waiting=True,payload=bytes(ready))
        reject('missing-arguments',command=[str(exe)])
        reject('extra-argument',command=[str(exe)]+[str(regs[k]) for k in KEYS]+['0',str(inp),str(out),'extra'])
        reject('missing-input',source=work/'absent-input');reject('input-directory',source=work)
        reject('output-directory',destination=work);reject('missing-output-parent',destination=work/'absent'/'output.bin')
        reject('input-output-identical',destination=inp)
        for kind in ('hardlink','symlink'):
            alias=work/kind
            if kind=='hardlink':os.link(inp,alias)
            else:alias.symlink_to(inp)
            reject('input-output-'+kind,destination=alias)
        fifo=work/'fifo';os.mkfifo(fifo)
        reject('FIFO-input',source=fifo);reject('FIFO-output',destination=fifo)
        fresh=work/'fresh-output'
        reject('invalid-RAM-does-not-leave-new-output',payload=b'',destination=fresh);assert not fresh.exists()
        reject('invalid-register-does-not-leave-new-output',state=dict(regs,d0='-1'),destination=fresh);assert not fresh.exists()
        bad_callback=bytearray(base);bad_callback[0x9152:0x9156]=bytes(4)
        reject('late-callback-failure-does-not-leave-new-output',payload=bytes(bad_callback),destination=fresh);assert not fresh.exists()
        probe=work/'CaseProbe';probe.write_bytes(b'probe');folded=work/'caseprobe'
        insensitive=folded.exists() and os.path.samefile(probe,folded)
        case_alias=dict(case_insensitive_filesystem=insensitive,applicable=insensitive)
        if insensitive:
            alias=work/'INPUT.BIN';assert os.path.samefile(inp,alias)
            reject('case-insensitive-input-output-alias',destination=alias);case_alias['input_preserved']=True
    return rows,case_alias


def exact_result(text):
    def unique(pairs):
        result={}
        for key,value in pairs:
            assert key not in result,'duplicate JSON key';result[key]=value
        return result
    parsed=json.loads(text,object_pairs_hook=unique)
    assert type(parsed) is dict and set(parsed)==set(KEYS)|{'waiting','status'}
    assert all(type(parsed[k]) is int and 0<=parsed[k]<=0xffffffff for k in KEYS)
    assert type(parsed['waiting']) is bool and type(parsed['status']) is int and parsed['status'] in (0,1,2,3)
    assert parsed['waiting']==(parsed['status']==3)
    return parsed



def public_snapshot_supplements(root,folder,program,native,exe,primary_rows):
    # Explicit public snapshot register mutations, separate from the unmodified
    # primary chains. Both original CPU and actual C++ start from their own
    # already-compared captured begin states. No native expected regs injected.
    index=next(r['case_index'] for r in native['results'] if r['fixture']['pending'])
    case=cases()[index];ram,regs=fixture(case,index);phases=native['results'][index]['phases']
    cpp_begin=next(r for r in primary_rows if r['case_index']==index and r['phase']=='begin')
    results=[];artifacts={};inp,out=folder/'supplement-input.bin',folder/'supplement-cpp.bin'
    for a6 in (0,0xffffffff):
        observer=Observer(program);observer.prepare(ram,regs);native_begin=observer.run(WAIT_PC)
        assert native_begin[2]=={key:cpp_begin['result'][key] for key in KEYS}
        cpp_ram=(root/cpp_begin['cpp_ram_file']).read_bytes();cpp_state=cpp_begin['result'].copy()
        observer.cpu.set_reg('a6',a6);cpp_state['a6']=a6
        for position,phase in enumerate(phases[1:]):
            observer.mutate(phase['external_RAM_writes']);cpp_ram=apply_writes(cpp_ram,phase['external_RAM_writes'])
            native_result,native_ram,native_regs,pcs,events,snapshots=observer.run(RETURN,2 if position==0 else 2000)
            assert not snapshots and not any(ENTRY<=pc<0x16ed2 or pc in (0xcd58,0xcd5c,0xcd82,0xcd98) for pc in pcs)
            inp.write_bytes(cpp_ram);out.write_bytes(b'previous-supplement-output')
            process=invoke(exe,{key:cpp_state[key] for key in KEYS},cpp_state['waiting'],inp,out)
            assert not process.returncode,process.stderr
            parsed=exact_result(process.stdout);actual=out.read_bytes()
            assert actual==native_ram and inp.read_bytes()==cpp_ram and parsed==dict(native_regs,waiting=position==0,status=3 if position==0 else 0)
            files={}
            for label,data in (('input',cpp_ram),('native',native_ram),('cpp',actual)):
                path=folder/('public-A6-%08x-%s-%s.bin'%(a6,phase['phase'],label));path.write_bytes(data)
                name=str(path.relative_to(root));artifacts[name]=sha(data);files[label]=dict(file=name,sha256=sha(data))
            results.append(dict(A6=a6,phase=phase['phase'],case_index=index,files=files,result=parsed,
                host_register_writes_before_hold=[dict(register='a6',value=a6)] if position==0 else [],
                external_RAM_writes=phase['external_RAM_writes'],native=native_result,pcs=pcs,ordered_writes=events,
                scope='Explicit publiccaptured-snapshot A6 mutation outsidehooks; separatefromprimaryunchanged96/112history.'))
            cpp_ram=actual;cpp_state=parsed
    assert len(results)==4
    return results,artifacts

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--audit-only',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/object_sprite_wrapper_execution';folder.mkdir(parents=True,exist_ok=True)
    report=folder/'verification.json'
    if not args.audit_only:report.unlink(missing_ok=True)
    program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    native,raw,artifacts,coverage=audit(root,program,source)
    if args.audit_only:
        assert all(sha((root/name).read_bytes())==digest for name,digest in artifacts.items())
        print(json.dumps(dict(native_sha256=sha(raw),coverage=coverage,source_and_inputs_current=True)));return
    exe=root/'build/execute_object_sprite_wrapper'
    names=('tools/verify_object_sprite_wrapper.py','build/execute_object_sprite_wrapper','engine/tools/execute_object_sprite_wrapper.cpp',
        'engine/src/object_sprite_wrapper.cpp','engine/include/ms5/object_sprite_wrapper.h','engine/src/sprite_submit_execution.cpp',
        'engine/include/ms5/sprite_submit_execution.h','engine/include/ms5/sprite_producer.h','engine/include/ms5/scene_map_transfer.h',
        'engine/include/ms5/fixed_data_resource.h','engine/include/ms5/video_port.h','Makefile',
        'docs/analysis/stage-object-output-wrappers-contract.md')
    inputs={name:sha((root/name).read_bytes()) for name in names}
    inp,out=folder/'input.bin',folder/'cpp.bin';rows=[];resumes=0
    for index,(case,row) in enumerate(zip(cases(),native['results'])):
        ram,regs=fixture(case,index);waiting=False;prior=None
        for phase in row['phases']:
            if prior is not None:
                # Carry actual C++ outputs forward; expected native state is only
                # compared below and never assigned into the next call.
                ram=apply_writes(prior[0],phase['external_RAM_writes'])
                regs={key:prior[1][key] for key in KEYS};waiting=prior[1]['waiting'];resumes+=1
            else:assert not phase['external_RAM_writes']
            assert sha(ram)==phase['input_ram_sha256'] and regs==phase['incoming']
            inp.write_bytes(ram);out.write_bytes(b'previous-output')
            process=invoke(exe,regs,waiting,inp,out);assert not process.returncode,(index,phase['phase'],process.stderr)
            parsed=exact_result(process.stdout);actual=out.read_bytes()
            expected_ram=(root/'artifacts/object_sprite_wrapper'/phase['ram_file']).read_bytes()
            assert inp.read_bytes()==ram and actual==expected_ram and parsed==dict(phase['result'],waiting=phase['waiting'],status=phase['status']),(index,phase['phase'])
            path=folder/('cpp_%04d_%s.bin'%(index,phase['phase']));path.write_bytes(actual);artifacts[str(path.relative_to(root))]=sha(actual)
            rows.append(dict(case_index=index,phase=phase['phase'],input_ram_sha256=sha(ram),result=parsed,
                cpp_ram_file=str(path.relative_to(root)),cpp_ram_sha256=sha(actual),previous_actual_CPP_output_carried=prior is not None,
                external_RAM_writes=phase['external_RAM_writes']))
            prior=(actual,parsed)
    assert len(rows)==112 and resumes==16
    supplements,extra_artifacts=public_snapshot_supplements(root,folder,program,native,exe,rows)
    artifacts.update(extra_artifacts)
    fresh=folder/'fresh-output.bin';fresh.unlink(missing_ok=True);ram,regs=fixture(cases()[0],0);inp.write_bytes(ram)
    process=invoke(exe,regs,False,inp,fresh);phase=native['results'][0]['phases'][0]
    assert not process.returncode and exact_result(process.stdout)==dict(phase['result'],waiting=phase['waiting'],status=phase['status'])
    assert inp.read_bytes()==ram and sha(fresh.read_bytes())==phase['ram_sha256']
    rejected,case_alias=negatives(exe,folder,native)
    native_inputs={r['file']:r['sha256'] for r in native['inputs']}
    for name,digest in {**inputs,**native_inputs,**artifacts}.items():assert sha((root/name).read_bytes())==digest,name
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256 and oracle_provenance(root)==native['oracle']
    report.write_text(json.dumps(dict(source=source,oracle=native['oracle'],inputs=inputs,native_inputs=native_inputs,
        native_and_CPP_artifacts=artifacts,native_observation_sha256=sha(raw),cases=96,phases=len(rows),
        previous_actual_CPP_output_resumes=resumes,public_snapshot_supplemental_phases=len(supplements),public_snapshot_supplements=supplements,
        coverage=coverage,branch_successor_counts=native['branch_successor_counts'],
        negative_cases=rejected,case_alias_regression=case_alias,fresh_output_creation_native_equal=True,
        full_RAM_15_registers_status_waiting_equal=True,positive_input_RAM_preserved=True,source_and_inputs_unchanged=True,
        source_program_modified=False,in_call_SR_read=False,results=rows,
        scope='Immutable original16ea4 tailJMPcd58/defaultcd50,96 cases112 phases including8sameCPUchains. Entire original phase trace/RAM writes reexecuted and audited; source.json explicitlyhashed. ActualCLI consumes previous actualC++RAM/15regs/waiting plus onlylistedhostRAMwrites on16resumes. Poisonobject/callback/prepared/producer doesnotreplayprefix. Errorfixtures checktransactionalfilepreservation; syntheticinvalidresumes are not nativehistories. CapturedA5canonical;4 separatepublicsnapshot native/C++hold-ready comparisons mutateA6to0/ffffffff outsidehooks, provingunusedA6onresume. No resource/ports, arbitrarycallback, otherCCR/cycles/physicalRAMmirror/naturalIRQ/scheduler/fullstage equivalence claim.'),indent=2)+'\n')
    print(json.dumps(dict(cases=96,phases=len(rows),resumes=resumes,supplemental_phases=len(supplements),negative_cases=len(rejected),sha256=sha(report.read_bytes()))))


if __name__=='__main__':main()
