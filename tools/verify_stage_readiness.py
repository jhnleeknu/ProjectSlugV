"""Audit immutable4847c native evidence and compare actual readiness CLI.

Carry comes from the native post-RTS SR sample. This verifier does not compute
readiness from a duplicate algorithm. All original214 cases are replayed on
actual native CPU, including their complete isolated-stack trace.
"""
import argparse
import collections
import json
import os
from pathlib import Path
import subprocess
import tempfile
from observe_stage_readiness import (BASE,STACK,STACK_START,RETURN,KEYS,ENTRY,RANGES,
    CALLEES,PROFILES,sha,build_cases,fixture,Observer,oracle_provenance,musashi_provenance,
    SOURCE_SHA256,load_verified_program)

NATIVE_SHA='45ad59018ae534c4059d6348dc835e09d37d9d08dbc3554e2562c7cfe90a4844'


def invoke(exe,regs,inp,out):
    return subprocess.run([str(exe)]+[str(regs[k]) for k in KEYS]+list(map(str,(inp,out))),
        capture_output=True,text=True,timeout=2)


def audit(root,program,source):
    folder=root/'artifacts/stage_readiness';path=folder/'observation.json';raw=path.read_bytes();native=json.loads(raw)
    assert sha(raw)==NATIVE_SHA and native['source']==source
    assert native['oracle']==oracle_provenance() and native['cross_oracle']==musashi_provenance(root)
    assert native['entry_pc']==ENTRY and native['cases']==native['completed_cases']==214
    assert native['profiles']==list(PROFILES) and native['total_native_ports']==0
    assert native['full_RAM_15_registers_returned_carry_observed'] and native['carry_read_after_RTS_outside_hook']
    assert not native['in_call_SR_read'] and not native['original_program_modified'] and not native['Cpp_comparison_performed']
    for name,digest in native['inputs'].items():assert sha((root/name).read_bytes())==digest,name
    static_path=folder/'source.json';static=json.loads(static_path.read_bytes());assert static['source']==source
    instructions=static['instructions'];by_pc={r['cpu_address']:r for r in instructions}
    for row in instructions:
        at=row['rom_offset'];assert at==row['cpu_address'] and bytes.fromhex(row['raw'])==program[at:at+row['size']]
        assert row['classification']=='candidate_instruction' and any(start<=at<end for start,end in RANGES)
    for start,end in RANGES:
        cursor=start
        for row in instructions:
            if start<=row['cpu_address']<end:
                assert row['cpu_address']==cursor;cursor+=row['size']
        assert cursor==end
    branch_pcs={r['cpu_address'] for r in instructions if r['mnemonic'].startswith('b') and r['mnemonic'] not in ('btst.b','bra.w')}
    assert len(branch_pcs)==native['conditional_branch_count']==19 and native['every_conditional_branch_both_outcomes']
    artifacts={str(path.relative_to(root)):sha(raw),str(static_path.relative_to(root)):sha(static_path.read_bytes())}
    coverage=collections.Counter();calls=collections.Counter();carry_counts=collections.Counter();read_count=0;stack_count=0
    observer=Observer(program,branch_pcs);cases=build_cases();assert len(cases)==len(native['results'])==214
    selected=[]
    for index,(case,row) in enumerate(zip(cases,native['results'])):
        ram=fixture(case,index);assert row['case_index']==index and row['fixture']==case
        for file_key,hash_key in (('input_ram_file','input_ram_sha256'),('ram_file','ram_sha256'),('trace_file','trace_sha256')):
            p=folder/row[file_key];assert sha(p.read_bytes())==row[hash_key];artifacts[str(p.relative_to(root))]=row[hash_key]
        assert (folder/row['input_ram_file']).read_bytes()==ram==(folder/row['ram_file']).read_bytes()
        trace=json.loads((folder/row['trace_file']).read_bytes());pcs=trace['pcs']
        assert pcs[0]==ENTRY and pcs[-1]==RETURN and all(pc in by_pc for pc in pcs[:-1])
        assert by_pc[pcs[-2]]['mnemonic']=='rts' and row['instructions']==len(pcs)-1
        assert row['final_pc']==RETURN and row['final_a7']==STACK+4 and row['port_count']==0
        assert type(row['carry']) is bool and row['carry']==bool(row['returned_sr']&1)
        assert set(row['result'])==set(KEYS) and all(type(v) is int and 0<=v<=0xffffffff for v in row['result'].values())
        assert trace['reads']==row['RAM_reads'] and trace['writes']==row['stack_writes']
        branches=[dict(pc=pc,next_pc=nxt) for pc,nxt in zip(pcs,pcs[1:]) if pc in branch_pcs]
        assert branches==row['branches']
        for branch in branches:coverage[(branch['pc'],branch['next_pc'])]+=1
        for event in trace['reads']:
            pc,address,size,value=(event[k] for k in ('pc','address','size','value'))
            assert pc in pcs and size in (1,2,4) and BASE<=address and address+size<=BASE+65536
            assert size==1 or address%2==0
            assert value==int.from_bytes(ram[address-BASE:address-BASE+size],'big')
        # Independently reconstruct native JSR/RTS stack order and return targets.
        sp=STACK;stack={STACK:RETURN};writes=[];boundaries=[]
        boundary_index=0
        for pc,nxt in zip(pcs,pcs[1:]):
            if pc in CALLEES:
                boundary=row['boundaries'][boundary_index];boundary_index+=1
                assert boundary['pc']==pc and boundary['a7']==sp and set(boundary['registers'])==set(KEYS)
                boundaries.append(pc)
            ins=by_pc[pc]
            if ins['mnemonic']=='jsr':
                sp-=4;value=pc+ins['size'];stack[sp]=value
                writes.append(dict(pc=pc,address=sp,size=4,value=value))
                assert int.from_bytes(program[pc+2:pc+6],'big')==nxt
            elif ins['mnemonic']=='rts':
                assert stack[sp]==nxt;sp+=4
        assert writes==trace['writes'] and sp==STACK+4 and boundary_index==len(row['boundaries'])
        assert row['lowest_stack_write']==min([r['address'] for r in writes]+[STACK])>=STACK_START
        assert dict(collections.Counter(hex(pc) for pc in boundaries))==row['calls']
        assert row['boundaries'][0]['registers']==case['incoming']
        for key in KEYS:
            if key not in ('d0','d1','a0','a4'):assert row['result'][key]==case['incoming'][key]
        # Replay real original execution, including actual returned carry, to reject
        # stale traces or fabricated metadata without any readiness formula.
        output,result,replayed_trace,info=observer.run(case,ram)
        assert output==ram and result==row['result'] and replayed_trace==trace
        assert all(row[key]==value for key,value in info.items())
        calls.update(row['calls']);carry_counts[str(row['carry'])]+=1;read_count+=len(trace['reads']);stack_count+=len(writes)
        selected.append((case,ram,case['incoming'],row['result'],row['carry']))
    assert [dict(pc=pc,next_pc=nxt,count=count) for (pc,nxt),count in sorted(coverage.items())]==native['branch_coverage']
    assert all(len({nxt for pc2,nxt in coverage if pc2==pc})==2 for pc in branch_pcs)
    cross=native['musashi_crosschecks'];assert len(cross)==10 and len({r['case_index'] for r in cross})==10
    for row in cross:
        actual=native['results'][row['case_index']]
        assert row['full_RAM_15regs_carry_equal'] and row['carry']==actual['carry']
        assert row['status']==dict(status='sentinel',instructions=actual['instructions'],pc=RETURN,cpu_writes=len(actual['stack_writes']),fault_address=0)
    return native,raw,artifacts,selected,dict(carry_counts=dict(carry_counts),native_RAM_operand_reads=read_count,
        native_stack_writes=stack_count,calls=dict(calls),actual_native_replays=214)


def negatives(exe,folder,row,ram):
    rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp,out=work/'input.bin',work/'output.bin';sentinel=b'preserved-readiness-output';regs=row['incoming']
        def reject(label,state=regs,payload=ram,source=None,destination=None,command=None):
            inp.write_bytes(payload);out.write_bytes(sentinel)
            src=inp if source is None else source;dest=out if destination is None else destination
            watched={p:p.read_bytes() for p in (inp,out,src,dest) if p.exists() and p.is_file()}
            p=subprocess.run(command,capture_output=True,text=True,timeout=2) if command else invoke(exe,state,src,dest)
            assert p.returncode and not p.stdout,(label,p.stdout,p.stderr)
            assert all(p.read_bytes()==data for p,data in watched.items()),label
            rows.append(dict(label=label,input_outputs_preserved=True,error=p.stderr.strip()))
        for size in (0,65535,65537):reject('RAM-size-'+str(size),payload=bytes(size))
        for key in KEYS:
            for bad in ('-1','4294967296','0x100000000','0x','1x',''):
                reject('register-parser-'+key,state=dict(regs,**{key:bad}))
        reject('missing-arguments',command=[str(exe)])
        reject('extra-argument',command=[str(exe)]+[str(regs[k]) for k in KEYS]+[str(inp),str(out),'extra'])
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
        bounds=(
            ('first-marker-below-RAM',0x107346,()),
            ('first-marker-above-RAM',0x117346,()),
            ('first-LONG-misaligned',0x108001,()),
            ('A5-zero',0,()),('A5-max-no-wrap',0xffffffff,()),
            ('first-a8-late',0x117344,()),
            ('second-marker-late',0x117258,((0x117258-0x7348,4,0x270e),)),
            ('second-a8-late',0x117254,((0x117254-0x7348,4,0x270e),)),
            ('first-record-WORD-late',0x10a2ea,()),
            ('second-record-WORD-late',0x10a2e4,((0x10a2e4-0x7348,4,0x270e),)),
            ('flag5684-late',0x10a97c,((0x10a97c-0x7348,4,0x270e),(0x10a97c-0x7258,4,0x270e))),
            ('first-mask-BYTE-late',0x107348,((0x100000,4,0x270e),(0x107348-0x7258,4,0x270e))))
        for label,a5,patches in bounds:
            payload=bytearray(65536)
            for address,size,value in patches:
                assert BASE<=address and address+size<=BASE+65536
                payload[address-BASE:address-BASE+size]=value.to_bytes(size,'big')
            reject(label,state=dict(regs,a5=a5),payload=bytes(payload))
        fresh=work/'fresh-output'
        reject('invalid-RAM-does-not-leave-new-output',payload=b'',destination=fresh);assert not fresh.exists()
        reject('invalid-register-does-not-leave-new-output',state=dict(regs,d0='-1'),destination=fresh);assert not fresh.exists()
        reject('late-failure-does-not-leave-new-output',state=dict(regs,a5=0x10a2ea),payload=bytes(65536),destination=fresh);assert not fresh.exists()
        probe=work/'CaseProbe';probe.write_bytes(b'probe');folded=work/'caseprobe'
        insensitive=folded.exists() and os.path.samefile(probe,folded)
        case_alias=dict(case_insensitive_filesystem=insensitive,applicable=insensitive)
        if insensitive:
            alias=work/'INPUT.BIN';assert os.path.samefile(inp,alias)
            reject('case-insensitive-input-output-alias',destination=alias);case_alias['input_preserved']=True
    return rows,case_alias



def main():
    parser=argparse.ArgumentParser();parser.add_argument('--audit-only',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/stage_readiness_execution';folder.mkdir(parents=True,exist_ok=True)
    report=folder/'verification.json'
    if not args.audit_only:report.unlink(missing_ok=True)
    program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    native,raw,artifacts,selected,coverage=audit(root,program,source)
    if args.audit_only:
        assert all(sha((root/name).read_bytes())==digest for name,digest in {**native['inputs'],**artifacts}.items())
        print(json.dumps(dict(native_sha256=sha(raw),cases=len(selected),coverage=coverage,source_and_inputs_current=True)))
        return
    exe=root/'build/execute_stage_readiness'
    names=('tools/verify_stage_readiness.py','build/execute_stage_readiness','engine/tools/execute_stage_readiness.cpp',
        'engine/src/stage_readiness.cpp','engine/include/ms5/stage_readiness.h',
        'engine/include/ms5/object_restart_execution.h','engine/include/ms5/video_port.h','Makefile',
        'docs/analysis/stage-readiness-contract.md')
    inputs={name:sha((root/name).read_bytes()) for name in names}
    inp,out=folder/'input.bin',folder/'cpp.bin';rows=[]
    for index,(case,ram,regs,result,carry) in enumerate(selected):
        inp.write_bytes(ram);out.write_bytes(b'previous-output')
        process=invoke(exe,regs,inp,out);assert not process.returncode,(index,process.stderr)
        parsed=json.loads(process.stdout)
        assert set(parsed)==set(KEYS)|{'carry'} and type(parsed['carry']) is bool
        assert all(type(parsed[k]) is int and 0<=parsed[k]<=0xffffffff for k in KEYS)
        assert parsed==dict(result,carry=carry) and inp.read_bytes()==out.read_bytes()==ram,index
        rows.append(dict(case_index=index,result=parsed,ram_sha256=sha(ram)))
    fresh=folder/'fresh-output.bin';fresh.unlink(missing_ok=True)
    case,ram,regs,result,carry=selected[-1];inp.write_bytes(ram)
    process=invoke(exe,regs,inp,fresh)
    assert not process.returncode and json.loads(process.stdout)==dict(result,carry=carry) and inp.read_bytes()==fresh.read_bytes()==ram
    rejected,case_alias=negatives(exe,folder,dict(incoming=regs),ram)
    for name,digest in {**inputs,**native['inputs'],**artifacts}.items():assert sha((root/name).read_bytes())==digest,name
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256 and oracle_provenance()==native['oracle'] and musashi_provenance(root)==native['cross_oracle']
    report.write_text(json.dumps(dict(source=source,oracle=native['oracle'],cross_oracle=native['cross_oracle'],
        inputs=inputs,native_inputs=native['inputs'],native_artifacts=artifacts,native_observation_sha256=sha(raw),
        cases=len(rows),coverage=coverage,conditional_branch_count=19,branch_coverage=native['branch_coverage'],
        every_conditional_branch_both_outcomes=True,negative_cases=rejected,case_alias_regression=case_alias,
        fresh_output_creation_native_equal=True,full_RAM_15_registers_carry_equal=True,
        source_and_inputs_unchanged=True,source_program_modified=False,in_call_SR_read=False,
        results=rows,scope='Immutable original4847c through RTS with actual1bdde/289e/4dee2/4e166. All214 native fullRAM/15regs/returnedcarry observations replayed on original CPU and compared with actualCLI;19 conditional branches both outcomes. Complete native RAM reads and JSR/RTS stack order audited. No duplicate readiness algorithm as oracle. Native10 selectedMusashi crosschecks retained. Failure fixtures check actual reachedRAM/alignment and late errors; oddA5 fails firstLONG so an independently reached late oddWORD is impossible on this entry. No resources/ports, otherCCRbits/cycles, physicalhardware/RAMmirror, scheduler or fullstage equivalence claim.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negative_cases=len(rejected),sha256=sha(report.read_bytes()))))


if __name__=='__main__':main()
