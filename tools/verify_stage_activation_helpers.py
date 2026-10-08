"""Actual helper CLI versus441 frozen immutable original observations.

Supplemental4e216 early-return cases are executed on the original CPU too.
No helper algorithm substitutes for observed native RAM/register/port/carry.
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
from observe_stage_activation_helpers import (BASE,STACK,STACK_START,RETURN,KEYS,RANGES,
    SOURCE_SHA256,sha,cases,fixture,Observer,oracle_provenance,load_verified_program)
NATIVE_SHA='ed26b6cc85ec93c777f211d1fa1d184eeb965659cbaec281116ed7bb4a28b0cf'


def invoke(exe,entry,registers,inp,out,ports,timeout=2):
    return subprocess.run([str(exe),str(entry)]+[str(registers[key]) for key in KEYS]+list(map(str,(inp,out,ports))),capture_output=True,text=True,timeout=timeout)


def audit(root,program,source):
    folder=root/'artifacts/stage_activation_helpers';path=folder/'observation.json';raw=path.read_bytes();native=json.loads(raw)
    assert sha(raw)==NATIVE_SHA and native['source']==source and native['oracle']==oracle_provenance()
    for name,digest in native['inputs'].items():assert sha((root/name).read_bytes())==digest,name
    static_path=folder/'source.json';static=json.loads(static_path.read_bytes());assert static['source']==source
    instructions=static['instructions'];by_pc={r['cpu_address']:r for r in instructions}
    for start,end in RANGES:
        cursor=start
        for row in instructions:
            if start<=row['cpu_address']<end:
                assert row['cpu_address']==row['rom_offset']==cursor and row['classification']=='candidate_instruction'
                assert bytes.fromhex(row['raw'])==program[cursor:cursor+row['size']];cursor+=row['size']
        assert cursor==end
    branches={r['cpu_address'] for r in instructions if r['mnemonic'].startswith('b') and not r['mnemonic'].startswith(('bset','bclr','bra'))}
    assert len(branches)==native['conditional_branch_count']==10
    assert native['cases']==native['completed_cases']==len(native['results'])==len(cases())==441
    assert native['normal_branches_both_outcomes'] and native['animation_A5_TRAP_guard_success_only']
    assert native['full_RAM_15_registers_ordered_writes_observed'] and native['carry_read_after_RTS_outside_hook']
    assert not native['original_program_modified'] and not native['in_call_SR_read'] and not native['Cpp_comparison_performed']
    coverage=collections.Counter();entries=collections.Counter();reads=0;writes=0;ports_total=0;selected=[]
    artifacts={str(path.relative_to(root)):sha(raw),str(static_path.relative_to(root)):sha(static_path.read_bytes())}
    observer=Observer(program,branches)
    for index,(case,row) in enumerate(zip(cases(),native['results'])):
        ram=fixture(case,index);assert row['case_index']==index and row['fixture']==case
        for key,digest in (('input_ram_file','input_ram_sha256'),('ram_file','ram_sha256'),('ports_file','ports_sha256'),('trace_file','trace_sha256')):
            path=folder/row[key];assert sha(path.read_bytes())==row[digest];artifacts[str(path.relative_to(root))]=row[digest]
        assert (folder/row['input_ram_file']).read_bytes()==ram
        expected=(folder/row['ram_file']).read_bytes();ports=(folder/row['ports_file']).read_bytes();trace=json.loads((folder/row['trace_file']).read_bytes())
        pcs=trace['pcs'];assert pcs[0]==case['entry'] and pcs[-1]==RETURN and len(pcs)-1==row['instructions']
        start,end=next(r for r in RANGES if r[0]==case['entry'])
        assert all(pc in by_pc and start<=pc<end for pc in pcs[:-1]) and by_pc[pcs[-2]]['mnemonic']=='rts'
        assert row['final_pc']==RETURN and row['final_a7']==STACK+4 and row['lowest_stack_write']==STACK
        assert trace['reads']==row['RAM_reads'] and trace['writes']==row['writes'] and not any(e['kind']=='stack' for e in row['writes'])
        assert len(set(pcs))==len(pcs)
        br=[dict(pc=pc,next_pc=nxt) for pc,nxt in zip(pcs,pcs[1:]) if pc in branches];assert br==row['branches']
        for b in br:coverage[(b['pc'],b['next_pc'])]+=1
        replay=bytearray(ram)
        for pc in pcs[:-1]:
            for event in trace['reads']:
                if event['pc']==pc:
                    at=event['address']-BASE;assert 0<=at and at+event['size']<=65536
                    assert event['size']==1 or event['address']%2==0
                    assert event['value']==int.from_bytes(replay[at:at+event['size']],'big')
            for event in trace['writes']:
                if event['pc']==pc:
                    assert event['size'] in (1,2,4) and 0<=event['value']<1<<(8*event['size'])
                    if event['kind']=='ram':
                        at=event['address']-BASE;assert 0<=at and at+event['size']<=65536
                        assert event['size']==1 or event['address']%2==0
                        replay[at:at+event['size']]=event['value'].to_bytes(event['size'],'big')
                    else:assert event['kind']=='ports' and case['entry']==0x49f8c
        assert bytes(replay)==expected
        assert ports==b''.join(struct.pack('>BII',e['size'],e['address'],e['value']) for e in trace['writes'] if e['kind']=='ports')
        assert len(ports)//9==row['port_count'] and len(ports)%9==0 and set(row['result'])==set(KEYS)
        assert type(row['carry']) is bool if case['entry'] in (0x4e216,0xbee) else row['carry'] is None
        output,result,actual_ports,actual_trace,info=observer.run(case,ram)
        assert output==expected and result==row['result'] and actual_ports==ports and actual_trace==trace
        assert all(row[k]==v for k,v in info.items())
        entries[hex(case['entry'])]+=1;reads+=len(trace['reads']);writes+=len(trace['writes']);ports_total+=row['port_count']
        selected.append(dict(case_index=index,fixture=case,ram=ram,expected=expected,ports=ports,result=result,carry=row['carry']))
    assert dict(entries)==native['entry_counts'] and ports_total==native['total_native_ports']==150
    assert [dict(pc=pc,next_pc=nxt,count=count) for (pc,nxt),count in sorted(coverage.items())]==native['branch_coverage']
    assert all(len({dest for branch,dest in coverage if branch==pc})==(1 if pc==0x49fb2 else 2) for pc in branches)
    return native,raw,artifacts,selected,observer,dict(entry_counts=dict(entries),RAM_reads=reads,ordered_writes=writes,
        native_replays=441,normal_branches_both_outcomes=9,TRAP_guard_success_only=True,
        bee_observed_A5_values=[0,0xffffffff])


def supplemental(observer,folder):
    rows=[];artifacts={}
    for index,first in enumerate((1,255)):
        ram=bytearray(hashlib.shake_256(b'activation-helper-skipped-second'+bytes([first])).digest(65536));ram[0xffff]=first
        incoming={key:((0xffffffff if index==0 else 0xabcd1234)+i*0x10203)&0xffffffff for i,key in enumerate(KEYS)}
        incoming['a5']=0x1175bb
        case=dict(entry=0x4e216,a5=0x1175bb,first=first,second=None,incoming=incoming,
            host_writes=[dict(address=0x10ffff,size=1,value=first)],reason='FirstBYTEvalid atRAMend; secondBYTE1100c3 outsideRAM is skipped on original earlyreturn.')
        ram=bytes(ram);output,result,ports,trace,info=observer.run(case,ram)
        assert trace['reads']==[dict(pc=0x4e216,address=0x10ffff,size=1,value=first)] and not info['carry']
        for name,data in (('input.bin',ram),('native.bin',output),('ports.bin',ports),('trace.json',(json.dumps(trace,indent=2)+'\n').encode())):
            path=folder/('supplemental-%d-'%index+name);path.write_bytes(data);artifacts[str(path)]=sha(data)
        rows.append(dict(case_index='supplemental-%d'%index,fixture=case,ram=ram,expected=output,ports=ports,result=result,carry=info['carry'],native_trace=trace,native_info=info))
    return rows,artifacts


def negatives(exe,folder,selected):
    rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp,out,ports=(work/name for name in ('input.bin','output.bin','ports.bin'))
        sample=next(row['fixture'] for row in selected if row['fixture']['entry']==0x49f8c)
        base=next(row['ram'] for row in selected if row['fixture'] is sample);registers=sample['incoming'];sentinel=b'preserved-activation-helper-output\0\xff'
        def reject(label,ram=base,entry=0x49f8c,state=registers,source=inp,outputs=None,command=None):
            destinations=(out,ports) if outputs is None else outputs
            inp.write_bytes(ram)
            for path in (out,ports)+destinations:
                if path.parent.exists() and path!=inp and not(path.exists() and os.path.samefile(path,inp)) and not(path.exists() and path.is_dir()):path.write_bytes(sentinel)
            watched={path:path.read_bytes() for path in set((inp,out,ports)+destinations) if path.exists() and path.is_file()}
            p=subprocess.run(command,capture_output=True,text=True,timeout=2) if command is not None else invoke(exe,entry,state,source,destinations[0],destinations[1],timeout=2)
            assert p.returncode and not p.stdout and all(path.read_bytes()==before for path,before in watched.items()),(label,p.stdout,p.stderr)
            rows.append(dict(label=label,input_outputs_preserved=True,native_bad_fixture_executed=False,error=p.stderr.strip()))
        for size in (0,65535,65537):reject('RAM-size-%d'%size,ram=bytes(size))
        for entry in (0,0x4e217,0xbef,0x16ed3,0x49f8d,0xffffffff):reject('unsupported-entry',entry=entry)
        for entry in ('-1','4294967296','0x100000000','0x','1x',''):reject('entry-parser',entry=entry)
        for key in KEYS:
            for value in ('-1','4294967296','0x100000000','0x','1x',''):
                reject('register-parser-'+key,state=dict(registers,**{key:value}))
        for entry,state in (
            (0x4e216,dict(registers,a5=0)),(0x4e216,dict(registers,a5=0xffffffff)),
            (0x4e216,dict(registers,a5=0x1075bb)),
            (0x16ed2,dict(registers,a5=0xff2c0)),(0x16ed2,dict(registers,a5=0x10f2c2)),
            (0x16ed2,dict(registers,a5=0x108001)),(0x16ed2,dict(registers,a5=0x10f2ba)),
            (0x16ed2,dict(registers,a5=0x108000,a6=0xfffea)),
            (0x16ed2,dict(registers,a5=0x108000,a6=0x10ffeb)),
            (0x16ed2,dict(registers,a5=0x108000,a6=0xffffffff)),
            (0x49f8c,dict(registers,a6=0xfffe7)),(0x49f8c,dict(registers,a6=0x10ffe8)),
            (0x49f8c,dict(registers,a6=0xffffffff)),
            (0x49f8c,dict(registers,a6=0x100001)),
            (0x49f8c,dict(registers,a6=0x10ffda)),(0x49f8c,dict(registers,a6=0x10ffd8)),
            (0x49f8c,dict(registers,a6=0x10ffd6)),(0x49f8c,dict(registers,a6=0x10ffd4)),
            (0x49f8c,dict(registers,a5=0x108002)),(0x49f8c,dict(registers,a5=0x108004)),
            (0x49f8c,dict(registers,a5=0x108001)),(0x49f8c,dict(registers,a5=0x107fee)),
            (0x49f8c,dict(registers,a5=0x117ff0))):
            reject('reached-span-alignment-or-TRAP-entry-%x-A5-%x-A6-%x'%(entry,state['a5'],state['a6']),entry=entry,state=state,ram=bytes(65536))
        for first in (0,5):
            payload=bytearray(65536);payload[0xffff]=first
            reject('4e216-late-second-BYTE-'+str(first),entry=0x4e216,state=dict(registers,a5=0x1175bb),ram=bytes(payload))
        reject('missing-input',source=work/'absent.bin')
        reject('input-directory',source=work)
        reject('RAM-output-directory',outputs=(work,ports));reject('port-output-directory',outputs=(out,work))
        reject('RAM-output-missing-parent',outputs=(work/'absent'/'output.bin',ports))
        reject('port-output-missing-parent',outputs=(out,work/'absent'/'ports.bin'))
        reject('input-RAM-output-alias',outputs=(inp,ports));reject('input-port-output-alias',outputs=(out,inp))
        reject('RAM-port-output-alias',outputs=(out,out))
        for kind in ('hardlink','symlink'):
            inp.write_bytes(base);alias=work/('input-'+kind)
            if kind=='hardlink':os.link(inp,alias)
            else:alias.symlink_to(inp)
            reject('input-RAM-output-'+kind,outputs=(alias,ports))
            reject('input-port-output-'+kind,outputs=(out,alias))
            out.write_bytes(sentinel);other=work/('outputs-'+kind)
            if kind=='hardlink':os.link(out,other)
            else:other.symlink_to(out)
            reject('RAM-port-output-'+kind,outputs=(out,other))
        values=[str(registers[key]) for key in KEYS]
        reject('missing-arguments',command=[str(exe)])
        reject('extra-argument',command=[str(exe),'0x49f8c']+values+list(map(str,(inp,out,ports)))+['extra'])
        fifo=work/'fifo';os.mkfifo(fifo)
        for role in ('input','RAM-output','port-output'):
            inp.write_bytes(base);out.write_bytes(sentinel);ports.write_bytes(sentinel)
            p=invoke(exe,0x49f8c,registers,fifo if role=='input' else inp,fifo if role=='RAM-output' else out,fifo if role=='port-output' else ports,timeout=2)
            assert p.returncode and not p.stdout and inp.read_bytes()==base and out.read_bytes()==sentinel and ports.read_bytes()==sentinel
            rows.append(dict(label='FIFO-'+role,rejected_without_blocking=True,input_outputs_preserved=True,native_bad_fixture_executed=False,error=p.stderr.strip()))
        probe=work/'CaseSensitivity.probe';probe.write_bytes(b'case probe');folded=work/'casesensitivity.probe'
        insensitive=folded.exists() and os.path.samefile(probe,folded)
        case_alias=dict(case_insensitive_filesystem=insensitive,applicable=insensitive)
        if insensitive:
            first,second=work/'NewScreen.bin',work/'newscreen.bin';assert not first.exists() and not second.exists();inp.write_bytes(base)
            p=invoke(exe,0x49f8c,registers,inp,first,second,timeout=2)
            assert p.returncode and not p.stdout and inp.read_bytes()==base and not first.exists() and not second.exists()
            case_alias.update(absent_output_alias_rejected=True,input_and_absent_outputs_preserved=True,error=p.stderr.strip())
            rows.append(dict(label='case-alias-new-outputs',input_outputs_preserved=True,error=p.stderr.strip()))
            first.write_bytes(b'');assert os.path.samefile(first,second)
            p=invoke(exe,0x49f8c,registers,inp,first,second,timeout=2)
            assert p.returncode and not p.stdout and inp.read_bytes()==base and first.read_bytes()==second.read_bytes()==b''
            case_alias['existing_zero_length_alias_outputs_preserved']=True
            rows.append(dict(label='case-alias-existing-zero-outputs',input_outputs_preserved=True,error=p.stderr.strip()))
        # A failed second reservation must remove only its new first placeholder.
        fresh=work/'fresh-output.bin';assert not fresh.exists();inp.write_bytes(base)
        p=invoke(exe,0x49f8c,registers,inp,fresh,fifo,timeout=2)
        assert p.returncode and not p.stdout and inp.read_bytes()==base and not fresh.exists()
        rows.append(dict(label='second-reservation-failure-cleans-only-new-first-placeholder',input_outputs_preserved=True,native_bad_fixture_executed=False,error=p.stderr.strip()))
        for label,payload,state in (
            ('bad-RAM-new-both-outputs',b'',registers),
            ('late-WORD-write-failure-new-both-outputs',base,dict(registers,a6=0x10ffd4))):
            first,second=work/'NewRAM.bin',work/'NewPorts.bin';assert not first.exists() and not second.exists()
            inp.write_bytes(payload);p=invoke(exe,0x49f8c,state,inp,first,second)
            assert p.returncode and not p.stdout and inp.read_bytes()==payload and not first.exists() and not second.exists()
            rows.append(dict(label=label,input_outputs_preserved=True,error=p.stderr.strip()))
    return rows,case_alias



def exact_result(text):
    def unique(pairs):
        result={}
        for key,value in pairs:
            assert key not in result,'duplicate JSON key';result[key]=value
        return result
    parsed=json.loads(text,object_pairs_hook=unique)
    assert type(parsed) is dict and set(parsed)==set(KEYS)|{'carry'}
    assert all(type(parsed[key]) is int and 0<=parsed[key]<=0xffffffff for key in KEYS)
    return parsed


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--audit-only',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/stage_activation_helpers_execution';folder.mkdir(parents=True,exist_ok=True)
    report=folder/'verification.json'
    if not args.audit_only:report.unlink(missing_ok=True)
    program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    native,raw,artifacts,selected,observer,coverage=audit(root,program,source)
    supplements,extra_artifacts=supplemental(observer,folder)
    artifacts.update({str(Path(name).relative_to(root)):digest for name,digest in extra_artifacts.items()})
    if args.audit_only:
        assert all(sha((root/name).read_bytes())==digest for name,digest in {**native['inputs'],**artifacts}.items())
        print(json.dumps(dict(native_sha256=sha(raw),primary_cases=len(selected),supplemental_cases=len(supplements),coverage=coverage,source_and_inputs_current=True)))
        return
    exe=root/'build/execute_stage_activation_helper'
    names=('tools/verify_stage_activation_helpers.py','build/execute_stage_activation_helper','engine/tools/execute_stage_activation_helper.cpp',
        'engine/src/stage_activation_helpers.cpp','engine/include/ms5/stage_activation_helpers.h',
        'engine/include/ms5/object_restart_execution.h','engine/include/ms5/video_port.h','Makefile',
        'docs/analysis/stage-activation-small-helpers-contract.md')
    inputs={name:sha((root/name).read_bytes()) for name in names}
    inp,out,ports=(folder/name for name in ('input.bin','cpp.bin','cpp.ports.bin'));rows=[]
    for row in selected+supplements:
        case,ram=row['fixture'],row['ram'];inp.write_bytes(ram);out.write_bytes(b'previous-RAM');ports.write_bytes(b'previous-ports')
        process=invoke(exe,case['entry'],case['incoming'],inp,out,ports);assert not process.returncode,(row['case_index'],process.stderr)
        parsed=exact_result(process.stdout)
        assert type(parsed['carry']) is bool if case['entry'] in (0x4e216,0xbee) else parsed['carry'] is None
        assert parsed==dict(row['result'],carry=row['carry']) and inp.read_bytes()==ram and out.read_bytes()==row['expected'] and ports.read_bytes()==row['ports'],row['case_index']
        recorded=dict(case_index=row['case_index'],fixture=case,result=parsed,input_ram_sha256=sha(ram),ram_sha256=sha(row['expected']),ports_sha256=sha(row['ports']),port_count=len(row['ports'])//9)
        if 'native_info' in row:recorded.update(native_info=row['native_info'],native_trace=row['native_trace'])
        rows.append(recorded)
    fresh_ram,fresh_ports=folder/'fresh-RAM.bin',folder/'fresh-ports.bin'
    fresh_ram.unlink(missing_ok=True);fresh_ports.unlink(missing_ok=True)
    row=next(row for row in selected if row['fixture']['entry']==0x49f8c);inp.write_bytes(row['ram'])
    process=invoke(exe,0x49f8c,row['fixture']['incoming'],inp,fresh_ram,fresh_ports)
    assert not process.returncode and exact_result(process.stdout)==dict(row['result'],carry=None)
    assert inp.read_bytes()==row['ram'] and fresh_ram.read_bytes()==row['expected'] and fresh_ports.read_bytes()==row['ports']
    rejected,case_alias=negatives(exe,folder,selected)
    for name,digest in {**inputs,**native['inputs'],**artifacts}.items():assert sha((root/name).read_bytes())==digest,name
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256 and oracle_provenance()==native['oracle']
    report.write_text(json.dumps(dict(source=source,oracle=native['oracle'],inputs=inputs,native_inputs=native['inputs'],
        native_artifacts=artifacts,native_observation_sha256=sha(raw),primary_cases=len(selected),supplemental_cases=len(supplements),
        cases=len(rows),coverage=coverage,branch_coverage=native['branch_coverage'],total_ordered_ports=sum(r['port_count'] for r in rows),
        negative_cases=rejected,case_alias_regression=case_alias,fresh_both_outputs_creation_native_equal=True,
        full_RAM_15_registers_ordered_ports_optional_carry_equal=True,source_and_inputs_unchanged=True,
        source_program_modified=False,in_call_SR_read=False,results=rows,
        scope='Immutable original4e216/bee/16ed2/49f8c throughRTS.441 frozen native cases fully reexecuted and replayed,150 orderedPVCwrites, full64KiBRAM15regs and returnedcarry forfirsttwo.2 supplemental original4e216 earlyreturns prove invalidsecondBYTE skipped atA5=1175bb.9 normalconditionalbranches both outcomes;49f8c A5 TRAPguard normalonly. ActualCLI carry is JSONnull fornoncarryentries; callerboolpreservation is separateAPIunit evidence. Existingbee fixtures observeA5zero/ffffffff only. Errors verifycheckedrollback/filepreservation, not nativeTRAPcompletion equivalence. No resource/physicalPVCsideeffects/otherCCR/cycles/RAMmirror/scheduler/fullstage equivalence claim.'),indent=2)+'\n')
    print(json.dumps(dict(primary_cases=len(selected),supplemental_cases=len(supplements),negative_cases=len(rejected),ports=sum(r['port_count'] for r in rows),sha256=sha(report.read_bytes()))))


if __name__=='__main__':main()
