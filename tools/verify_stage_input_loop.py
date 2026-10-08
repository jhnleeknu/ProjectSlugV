"""FullRAM/14-register stage-input-loop CLI equivalence and rejection preservation."""
import collections
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib

from disassemble_program import load_verified_program
from observe_stage_input_loop import (BASE,STACK,RETURN,KEYS,UNKNOWN,SOURCE_SHA256,BOTH_BRANCHES,build_cases,fixture,assert_evidence,
    inventory,oracle_provenance,provenance,sha)

BINARY_SHA256='17c69e75ec803099f15a4c308776a1634780a0123bd26d5df2991c613ae0ce48'


def invoke(exe,entry,regs,inp,out,resources=()):
    return subprocess.run([str(exe),str(entry)]+list(map(str,regs))+[str(inp),str(out)]+
        list(map(str,resources)),capture_output=True,text=True)


def container(payload,cpu,**changes):
    fields=dict(version=1,kind=1,cpu=cpu,rom=cpu,size=len(payload),crc=zlib.crc32(payload),reserved=0)
    fields.update(changes)
    return struct.pack('<4s7I',b'MS5D',*(fields[k] for k in
        ('version','kind','cpu','rom','size','crc','reserved')))+payload


def negative_checks(root,program):
    exe=root/'build/step_stage_input_loop'
    mask=root/'extracted/runtime/stage_input/default_masks.ms5d'
    lookup=root/'extracted/runtime/player_record_lookup.ms5d'
    prefix=root/'extracted/runtime/game_records.ms5d'
    cases=build_cases()
    base=next(c for c in cases if c['family']=='two-null-slots-default-all-held')
    player=next(c for c in cases if c['entry']==0x4d7a6)
    rows=[]
    with tempfile.TemporaryDirectory(dir=root/'artifacts/stage_input_loop') as directory:
        work=Path(directory);inp,out,res,other=[work/n for n in ('in.bin','out.bin','one.ms5d','two.ms5d')]
        def reject(label,case=None,entry=None,values=None,ram_override=None,resources=None,input_bytes=None):
            current=base if case is None else case
            ram,regs=fixture(current)
            if ram_override is not None:ram=bytearray(ram_override)
            if values is not None:regs=values
            if input_bytes is not None:ram=input_bytes
            inp.write_bytes(ram);out.write_bytes(b'existing-output-must-survive')
            preserved=out.read_bytes()
            result=invoke(exe,current['entry'] if entry is None else entry,regs,inp,out,
                [mask,lookup] if resources is None else resources)
            assert result.returncode and not result.stdout,(label,result.stdout,result.stderr)
            assert inp.read_bytes()==ram and out.read_bytes()==preserved,label
            rows.append(dict(failure=label,input_output_preserved=True,error=result.stderr.strip(),native_executed=False))
        for entry in (0,0x49ab4,-1,'0x','4294967296',' 0x49b0c'):
            reject('invalid-entry-'+str(entry),entry=entry)
        ram,regs=fixture(base)
        for at,value in ((0,-1),(1,'0x'),(8,'4294967296'),(13,' 1'),(12,'1x')):
            bad=regs.copy();bad[at]=value;reject('invalid-register-'+str(at),values=bad)
        for size in (0,65535,65537):reject('RAM-size-'+str(size),input_bytes=bytes(size))
        for slot,label in ((UNKNOWN,'active-RAM-function-unsupported'),(0x49c38,'unlisted-original-function-unsupported'),(0xdeadbeef,'unknown-pointer-unsupported')):
            bad=dict(base,slots=[0,slot])
            reject('late-second-'+label,case=bad)
        bad=dict(base,slots=[0x1d5ac,UNKNOWN],retarget=1,d683=4)
        # First callback clears slot2, then the now-null second path needs masks.
        reject('late-after-slot-clear-missing-masks',case=bad,resources=[lookup])
        reject('late-second-null-missing-default-masks',case=dict(base,slots=[0x49e34,0]),resources=[lookup])
        reject('helper-index0-native-TRAP-unsupported',case=dict(player,indices=[0,0]))
        bad=dict(base,slots=[0,0x1da60],current=0,previous=0,player=1,retarget=1,indices=[1,0])
        reject('late-second-callback-helper-index0-TRAP',case=bad)
        reject('active-helper-missing-lookup',case=player,resources=[mask])
        bad=dict(base,slots=[0,0x1da60],current=0,previous=0,player=1,retarget=1)
        reject('late-second-callback-missing-lookup',case=bad,resources=[mask])
        bad=dict(base,slots=[0,0x1d5e2],flags=0)
        ram,regs=fixture(bad)
        for address,label in ((0x106001,'unaligned-A6-WORD'),(0xffffffff,'A6-offset-overflow'),(0x10fffe,'A6-word-outside-RAM')):
            changed=regs.copy();changed[13]=address
            reject('late-second-'+label,case=bad,values=changed)
        bad=dict(next(c for c in cases if c['entry']==0x1da60),current=0,previous=0)
        ram,regs=fixture(bad);regs[8]=0x10fffe
        reject('crossing-object-outside-RAM',case=bad,values=regs)
        reject('missing-resource-path',resources=[work/'missing.ms5d'])
        raw=bytes.fromhex('10204080')
        for packed,label in ((b'bad','header-truncated'),(container(raw,0x49ab0)[:-1],'payload-truncated'),
            (container(raw,0x49ab0)+b'x','extra-payload'),(container(raw,0x49ab0,version=2),'version'),
            (container(raw,0x49ab0,kind=2),'banked'),(container(raw,0x49ab0,reserved=1),'reserved'),
            (container(raw,0x49ab0,rom=0x49ab2),'mapping'),(container(raw,0x49ab0,crc=0),'CRC')):
            res.write_bytes(packed);reject('resource-'+label,resources=[res,lookup])
        res.write_bytes(container(raw[:3],0x49ab0))
        reject('partial-mask-late-byte',resources=[res,lookup])
        res.write_bytes(container(raw,0x49ab0));other.write_bytes(container(raw,0x49ab0))
        reject('ambiguous-complete-mask',resources=[res,other,lookup])
        other.write_bytes(container(raw[2:],0x49ab2))
        reject('ambiguous-partial-mask',resources=[res,other,lookup])
        body=program[0x4cf64:0x4df60]
        res.write_bytes(container(body[:-2],0x4cf64))
        reject('helper-not-exact4092-lookup',case=player,resources=[res,mask])
        reject('helper-full-lookup-plus-existing320-prefix-overlap',case=player,resources=[lookup,prefix,mask])
        res.write_bytes(container(body[:2],0x4cf64))
        reject('helper-full-lookup-plus-partial-overlap',case=player,resources=[lookup,res,mask])
        for label in ('same-path','hardlink','symlink'):
            ram,regs=fixture(base);inp.write_bytes(ram)
            destination=inp if label=='same-path' else work/label
            if label=='hardlink':os.link(inp,destination)
            if label=='symlink':destination.symlink_to(inp)
            result=invoke(exe,base['entry'],regs,inp,destination,[mask,lookup])
            assert result.returncode and inp.read_bytes()==ram and destination.read_bytes()==ram,label
            rows.append(dict(failure='input-output-'+label,input_output_preserved=True,native_executed=False))
        reject('resource-input-alias',resources=[inp,lookup])
        reject('resource-output-alias',resources=[out,lookup])
        out.write_bytes(container(raw,0x49ab0));alias=work/'out-resource.ms5d';os.link(out,alias)
        ram,regs=fixture(base);inp.write_bytes(ram);before=out.read_bytes()
        result=invoke(exe,base['entry'],regs,inp,out,[alias,lookup])
        assert result.returncode and inp.read_bytes()==ram and out.read_bytes()==before
        rows.append(dict(failure='resource-output-hardlink',input_output_preserved=True,native_executed=False))
    return rows


def main():
    root=Path(__file__).resolve().parents[1]
    program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    inputs,oracle=provenance(root),oracle_provenance(root.resolve())
    exe=root/'build/step_stage_input_loop';assert sha(exe.read_bytes())==BINARY_SHA256
    folder=root/'artifacts/stage_input_loop';path=folder/'observation.json'
    data=path.read_bytes();native=json.loads(data);cases=build_cases()
    assert native['source']==source and native['oracle']==oracle and native['inputs']==inputs
    assert native['cases']==native['completed_cases']==len(native['results'])==len(cases)
    assert native['failure'] is None and not native['program_code_modified'] and not native['CCR_exposed']
    negatives=negative_checks(root,program)
    resources=[root/'extracted/runtime/stage_input/default_masks.ms5d',root/'extracted/runtime/player_record_lookup.ms5d']
    rows=[];previous={};resumes=0;extra_bypasses=[];branch_counts=collections.defaultdict(collections.Counter)
    with tempfile.TemporaryDirectory(dir=folder) as directory:
        work=Path(directory);inp,out=work/'in.bin',work/'out.bin'
        for index,(case,expected) in enumerate(zip(cases,native['results'])):
            assert expected['case_index']==index and expected['fixture']==case and expected['returned']
            prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None
            ram,regs=fixture(case) if prior is None else (bytearray(prior[0]),list(prior[1]))
            resumes+=prior is not None
            assert sha(ram)==expected['input_ram_sha256'] and dict(zip(KEYS,regs))==expected['incoming']
            inp.write_bytes(ram)
            result=invoke(exe,hex(case['entry']),regs,inp,out,resources)
            assert result.returncode==0,(index,case,result.stderr)
            actual=json.loads(result.stdout);original=(folder/expected['ram_file']).read_bytes()
            assert sha(original)==expected['ram_sha256']
            assert expected['final_pc']==RETURN and expected['final_a7']==STACK+4 and expected['mmio_writes']==0
            assert_evidence(case,ram,original,regs,expected['result'],expected)
            for branch in expected['branch_successors']:
                branch_counts[branch['pc']][branch['next_pc']]+=1
            assert out.read_bytes()==original and actual==expected['result'],(index,case,actual,expected['result'])
            assert inp.read_bytes()==ram
            if 'sequence'in case:previous[case['sequence']]=(out.read_bytes(),[actual[k] for k in KEYS])
            rows.append(dict(case_index=index,entry=case['entry'],family=case['family'],full_RAM_14_registers_equal=True,ram_sha256=sha(original)))
            # These known inactive paths have no resource reads; test absence too.
            if (case['family']=='unknown-slots-inactive-marker-native-bypass' and case['slots']==[UNKNOWN,UNKNOWN]
                or case['family']=='inactive-marker-or-zero-source-bypasses-index0' and case['input_d0']==0 and case['markers']==[1,0]):
                result=invoke(exe,hex(case['entry']),regs,inp,out,[])
                assert result.returncode==0 and out.read_bytes()==original and json.loads(result.stdout)==actual
                extra_bypasses.append(dict(case_index=index,resource_files=0,full_RAM_14_registers_equal=True))
    rebuilt_branches={hex(k):{hex(a):n for a,n in sorted(v.items())} for k,v in sorted(branch_counts.items())}
    assert rebuilt_branches==native['branch_successor_counts']
    assert native['required_two_successor_branch_addresses']==list(BOTH_BRANCHES)
    assert all(len(branch_counts[pc])==2 for pc in BOTH_BRANCHES)
    audited=inventory(root)
    conditional={c['instruction']['cpu_address'] for w in audited['windows'] for c in w['direct_control_operands'] if c['instruction']['mnemonic'].split('.')[0] not in ('jsr','bsr','bra','jmp')}
    assert set(BOTH_BRANCHES)==conditional-{0x4d7ec}
    assert provenance(root)==inputs and oracle_provenance(root.resolve())==oracle
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256 and sha(path.read_bytes())==sha(data)
    report=dict(source=source,oracle=oracle,inputs=inputs,native_observation_sha256=sha(data),
        cases=len(cases),negative_cases=len(negatives),negative_results=negatives,
        counts_by_entry=native['counts_by_entry'],full_RAM_14_registers_equal=True,
        actual_output_chain_resumes=resumes,resumed_host_writes=0,CCR_exposed=False,
        resource_absence_bypasses=extra_bypasses,branch_successor_counts=rebuilt_branches,
        required_two_successor_branch_addresses=native['required_two_successor_branch_addresses'],results=rows,
        scope='Four-entry CLI compares every64KiB RAM byte and14 exposed registers with original uninterrupted pinned Musashi. '
              'All255 active lookup indices per player, BYTE-selection highbits, inactive/zero-source paths, crossing/retarget, markers and live sequential callback slots tested. '
              'First callback clears unknown second slot before native/CLI second read; active unknown/RAM callbacks and nativeTRAP are C++support rejections only, never executed natively. '
              'ActualCLI-output chains preserve fullRAM/14regs with no resumed host rewrites. Failed unsupported/missing/partial/overlap/alias/late paths preserve existing output/input files; '
              'CLI failure output has no register object, so API register transaction on rejection is not independently exposed here. No unknown closure, natural gameplay, cycle orCCR equivalence claim.')
    destination=folder/'verification.json';destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(cases),negative_cases=len(negatives),actual_output_chain_resumes=resumes,
        resource_absence_bypasses=len(extra_bypasses),full_RAM_14_registers_equal=True,sha256=sha(destination.read_bytes()))))


if __name__=='__main__':main()
