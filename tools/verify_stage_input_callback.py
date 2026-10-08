"""Full native callback differential, resource guards and failure-atomic CLI checks."""
import collections
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from verify_scene_motion_bounds import container
from observe_stage_input_callback import build_cases,fixture,assert_evidence,provenance,oracle_provenance,load_verified_program,sha,SOURCE_SHA256,KEYS,ENTRIES,BRANCHES,BASE,STACK,RETURN
BINARY_SHA256='7973d5cf88f0b2a5504adca95793cfe5bfc9aebd9030297a7f0ed923882b436d'


def negative_checks(root,cases):
    folder=root/'artifacts/stage_input_callback';folder.mkdir(parents=True,exist_ok=True);exe=root/'build/step_stage_input_callback';mask=root/'extracted/runtime/stage_input/default_masks.ms5d';rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temp:
        work=Path(temp);inp,out,path,other=work/'input.bin',work/'output.bin',work/'mask.ms5d',work/'other.ms5d';sentinel=b'preserved-stage-input-callback-output\0\xff';sample=next(c for c in cases if c['entry']==0x1d628);ram,regs=fixture(sample)
        def invoke(data,values,files=(mask,),entry=0x1d628,destination=out):
            inp.write_bytes(data)
            if destination!=inp and not (destination.exists() and os.path.samefile(inp,destination)):destination.write_bytes(sentinel)
            watched={p:p.read_bytes() for p in set((inp,out,destination)) if p.exists()}
            actual=subprocess.run([str(exe),str(entry)]+list(map(str,values))+[str(inp),str(destination)]+list(map(str,files)),capture_output=True,text=True)
            return actual,watched
        def reject(label,data=ram,values=regs,files=(mask,),entry=0x1d628):
            actual,watched=invoke(data,values,files,entry);assert actual.returncode and all(p.read_bytes()==before for p,before in watched.items()),(label,actual.stdout,actual.stderr);rows.append(dict(failure=label,entry=entry,input_output_preserved=True,native_bad_fixture_executed=False,error=actual.stderr.strip()))
        baseline,_=invoke(ram,regs);assert baseline.returncode==0 and json.loads(baseline.stdout)['a0']==0 and out.read_bytes()[0xd734:0xd738]==bytes(4),baseline.stderr
        for size in (0,65535,65537):reject('RAM-size',bytes(size))
        for index in range(14):
            for text in ('-1','4294967296','0x100000000','0x','1x',''):
                values=regs.copy();values[index]=text;reject('register-parser-%d'%index,values=values)
        for entry in (0,0x49d89,0x49ab4,0x49c20,0x49b0c,0x1da60,0x4d7a6,'-1','4294967296','0x','1x',''):reject('entry-parser-or-excluded',entry=entry)
        for entry in (0x49d88,0x49de6,0x49e38,0x49f2c,0x1d628):
            for pointer in (1,0x100001,0x10ffc0,0x110000,0xfffffffe,0xffffffff):
                values=regs.copy();values[8]=pointer;reject('used-object-field-alignment-or-range',values=values,entry=entry)
        # The latch byte is written before49de6 tries object+78 on this path.
        late=next(c for c in cases if c['entry']==0x49eba and c['latch']==0);data,values=fixture(late);values[8]=0x10ffc0;reject('late-object-read-after-latch-byte-write',data,values,entry=0x49eba)
        # Flag7-clear1d5e2 reads A6+3a; the flagged mapper path does not.
        parent_case=next(c for c in cases if c['entry']==0x1d5e2 and c['flag']==0);data,values=fixture(parent_case)
        for pointer in (1,0x100001,0x10ffc6,0x110000,0xfffffffe,0xffffffff):
            invalid=values.copy();invalid[13]=pointer;reject('used-A6-plus3a-read',data,invalid,entry=0x1d5e2)
        reject('late-missing-default-mask-after-callback-slot-clear',files=())
        raw=bytes.fromhex('10204080')
        for size in (1,2,3):
            path.write_bytes(container(raw[:size],cpu=0x49ab0,rom=0x49ab0));reject('late-partial-default-mask-after-setter',files=(path,))
        path.write_bytes(container(raw,cpu=0x49ab0,rom=0x49ab0));other.write_bytes(container(raw,cpu=0x49ab0,rom=0x49ab0));reject('ambiguous-complete-mask-after-setter',files=(path,other))
        other.write_bytes(container(raw[2:3],cpu=0x49ab2,rom=0x49ab2));reject('ambiguous-partial-mask-after-setter',files=(path,other))
        for packed,label in ((b'bad','truncated-header'),(container(raw)[:-1],'truncated-payload'),(container(raw,version=2),'bad-version'),(container(raw,kind=2),'wrong-kind'),(container(raw,reserved=1),'reserved'),(container(raw,cpu=0x49ab1,rom=0x49ab1),'odd-resource-start'),(container(raw,cpu=BASE,rom=BASE),'RAM-resource-address'),(container(raw,cpu=0x49ab0,rom=0x49ab2),'CPU-ROM-disagreement'),(container(raw,cpu=0xffffe,rom=0xffffe),'fixed-window-overflow'),(container(raw)+b'x','extra-payload')):
            path.write_bytes(packed);reject('loader-'+label,files=(path,))
        corrupt=bytearray(container(raw,cpu=0x49ab0,rom=0x49ab0));corrupt[-1]^=1;path.write_bytes(corrupt);reject('payload-CRC',files=(path,));reject('missing-resource-file',files=(work/'missing.ms5d',))
        for label in ('same-path','hardlink','symlink'):
            inp.write_bytes(ram);target=inp if label=='same-path' else work/label
            if label=='hardlink':os.link(inp,target)
            if label=='symlink':target.symlink_to(inp)
            actual,watched=invoke(ram,regs,destination=target);assert actual.returncode and all(p.read_bytes()==before for p,before in watched.items());rows.append(dict(failure='input-output-'+label,input_output_preserved=True,native_bad_fixture_executed=False))
        for resource,label in ((inp,'resource-input-alias'),(out,'resource-output-alias')):reject(label,files=(resource,))
        # Different path to the same resource inode is also rejected.
        path.write_bytes(mask.read_bytes());alias=work/'mask-alias.ms5d';os.link(path,alias);reject('duplicate-resource-hardlink',files=(path,alias))
    return rows


def invoke_case(exe,entry,regs,ram,inp,out,files):
    inp.write_bytes(ram);actual=subprocess.run([str(exe),str(entry)]+list(map(str,regs))+[str(inp),str(out)]+list(map(str,files)),capture_output=True,text=True);assert actual.returncode==0 and inp.read_bytes()==ram,actual.stderr;return out.read_bytes(),json.loads(actual.stdout)


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;cases=build_cases();exe=root/'build/step_stage_input_callback';assert sha(exe.read_bytes())==BINARY_SHA256;negatives=negative_checks(root,cases)
    if '--negative-only'in sys.argv:print(json.dumps(dict(negative_cases=len(negatives))));return
    inputs=provenance(root);oracle=oracle_provenance(root);folder=root/'artifacts/stage_input_callback';path=folder/'observation.json';raw=path.read_bytes();native=json.loads(raw)
    assert native['source']==source and native['inputs']==inputs and native['oracle']==oracle and native['failure'] is None and not native['program_code_modified'];assert native['cases']==native['completed_cases']==len(native['results'])==len(cases)==2943
    mask=root/'extracted/runtime/stage_input/default_masks.ms5d';inp,out=folder/'input.bin',folder/'cpp.bin';previous={};rows=[];calls=collections.Counter();branches=collections.defaultdict(collections.Counter);mapping_zero=0;absolute_memory_cases=0;restore_cases=0;omitted={};entries=set()
    for index,(case,row) in enumerate(zip(cases,native['results'])):
        assert row['case_index']==index and row['fixture']==case and row['returned'] and row['final_pc']==RETURN and row['final_a7']==STACK+4 and row['mmio_writes']==0
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None;ram,regs=fixture(case) if prior is None else (bytearray(prior[0]),prior[1].copy());assert sha(ram)==row['input_ram_sha256'] and dict(zip(KEYS,regs))==row['incoming'];expected=(folder/row['ram_file']).read_bytes();assert sha(expected)==row['ram_sha256'];assert_evidence(case,ram,expected,row['result'],row,regs)
        cpp,result=invoke_case(exe,case['entry'],regs,ram,inp,out,(mask,));assert cpp==expected and result==row['result'],(index,case,result,row['result'],[(hex(BASE+i),a,b) for i,(a,b) in enumerate(zip(expected,cpp)) if a!=b][:20])
        entries.add(case['entry']);calls.update(row['calls'])
        for branch in row['branch_successors']:branches[branch['pc']][branch['next_pc']]+=1
        if row['calls'].get('0x1d628'):mapping_zero+=1
        if case['family']=='absolute-memory-CMPA-latch-save-restore':absolute_memory_cases+=1
        if case['entry']==0x49ef0 and not ram[0xd732]&(1<<(0 if int.from_bytes(ram[0xcb8:0xcbc],'big')==regs[8] else 1)):restore_cases+=1
        if case['entry'] not in omitted and not row['calls'].get('0x49ab4'):
            other,parsed=invoke_case(exe,case['entry'],regs,ram,inp,out,());assert other==expected and parsed==row['result'];omitted[case['entry']]=index
        if 'sequence'in case:previous[case['sequence']]=(cpp,[result[key] for key in KEYS])
        rows.append(dict(case_index=index,family=case['family'],entry=case['entry'],result=result,ram_sha256=sha(cpp)))
    assert entries==set(ENTRIES) and set(branches)==set(BRANCHES) and all(len(branches[pc])==2 and all(branches[pc].values()) for pc in BRANCHES)
    assert len(previous)==4 and mapping_zero and restore_cases and absolute_memory_cases==720 and len(omitted)==16
    # A0==100cb8 with a different stored LONG takes index1; a different A0 with
    # LONG(100cb8)==A0 takes index0. These are actual branch successors.
    equality_directions=collections.Counter()
    for case,row in zip(cases,native['results']):
        if case['family']=='absolute-memory-CMPA-latch-save-restore':
            comparison=next(b for b in row['branch_successors'] if b['pc'] in (0x49ec2,0x49ef8));equal=case['absolute_memory']==case['object'];assert comparison['next_pc']==((0x49eca if equal else 0x49ec6) if comparison['pc']==0x49ec2 else (0x49f00 if equal else 0x49efc));equality_directions[(case['object']==0x100cb8,case['absolute_memory']==case['object'],comparison['next_pc'])]+=1
    assert any(not address_equal and memory_equal for address_equal,memory_equal,next_pc in equality_directions) and any(address_equal and not memory_equal for address_equal,memory_equal,next_pc in equality_directions)
    directory_case=next((i,c) for i,c in enumerate(cases) if c['entry']==0x49f66);index,case=directory_case;ram,regs=fixture(case);cpp,result=invoke_case(exe,case['entry'],regs,ram,inp,out,(mask.parent,));assert result==native['results'][index]['result'] and cpp==(folder/native['results'][index]['ram_file']).read_bytes()
    assert provenance(root)==inputs and oracle_provenance(root)==oracle and sha(exe.read_bytes())==BINARY_SHA256 and path.read_bytes()==raw and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report=dict(source=source,oracle=oracle,inputs=inputs,binary_sha256=BINARY_SHA256,native_observation_sha256=sha(raw),cases=len(rows),negative_cases=len(negatives),families=dict(collections.Counter(c['family'] for c in cases)),entry_addresses=sorted(entries),counts_by_entry=dict(sorted(collections.Counter(c['entry'] for c in cases).items())),native_call_counts=dict(calls),branch_paths=[dict(pc=pc,next_pc=n,count=count) for pc,values in sorted(branches.items()) for n,count in sorted(values.items())],both_outcomes_conditional_branches=len(branches),setter_to_mapper_zero_A0_cases=mapping_zero,absolute_memory_cases=absolute_memory_cases,absolute_compare_branches=[dict(A0_equals_player1_address=address_equal,memory_LONG_equals_A0=memory_equal,next_pc=next_pc,count=count) for (address_equal,memory_equal,next_pc),count in sorted(equality_directions.items())],D0_saved_D1_restored_cases=restore_cases,unused_mask_omission_case_indexes=list(omitted.values()),directory_resource_case_index=index,cli_carry_sequences=len(previous),cli_carry_calls=32,cli_calls_consuming_previous_outputs=28,full_RAM_14_registers_equal=True,positive_input_RAM_preserved=True,original_ROM_resources_core_binary_tools_unchanged=True,mmio_writes=0,results=rows,negative_results=negatives,scope='All eighteen assigned callback entries execute uninterrupted original calls in pinned Musashi M68000 to RTS/A7+4, with all64KiB RAM/14 exposed registers including A6 and zero MMIO. Original code/default-mask container and frozen core/tool/oracle provenance preserved. Actual successors prove both outcomes of all38 listed branches. Absolute-memory CMPA differs from immediate player-address comparison;49eba OR result is discarded,49ef0 saves D0 then restores into D1,1d628 enters49f66 with A0zero. Four actual CLI eight-call sequences carry allRAM/14registers without host rewrites. No CCR/full49b0c/dynamic dispatcher/scheduler reachability claim;1da60/4d7a6 excluded.')
    report_path=folder/'verification.json';report_path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),both_outcomes_conditional_branches=len(branches),sha256=sha(report_path.read_bytes()))))
if __name__=='__main__':main()
