"""Full RAM/12-register/carry differential against independent original execution."""
import collections
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from disassemble_program import load_verified_program
from observe_scene_motion_pair import build_cases,fixture,incoming,sha,KEYS,HIGHS,STACK,RETURN,FIXED,ENTRIES,BUG_PCS,assert_evidence,oracle_provenance
from verify_scene_motion_bounds import container
from verify_stage_catalog import SOURCE_SHA256
BINARY_SHA256='b7ecd5ffc7b33b94e537ab1f0293656150dddc65da4e2d9604c6827bb0cce7e4'

def negative_checks(root,program,cases):
    folder=root/'artifacts/scene_motion_pair';folder.mkdir(parents=True,exist_ok=True);exe=root/'build/step_scene_motion_pair';rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temp:
        work=Path(temp);inp,out,path=work/'input.bin',work/'output.bin',work/'motion.ms5d';sentinel=b'preserved-motion-pair-output\0\xff'
        sample=next(c for c in cases if c['family']=='synthetic-all36-pair-transition-bands' and c['kind']==0x14 and c['proposed_time']==25 and c['orthogonal']==0);ram=fixture(sample);regs=incoming(sample,program,ram);body=bytes.fromhex(sample['payload_hex']);path.write_bytes(container(body))
        def invoke(data,registers,resource,entry=0x19832,destination=out):
            inp.write_bytes(data)
            if destination==out:out.write_bytes(sentinel)
            args=[str(exe),str(entry)]+list(map(str,registers))+[str(inp),str(destination)]
            if resource is not None:args.append(str(resource))
            return subprocess.run(args,capture_output=True,text=True)
        def reject(data,registers,resource,label,entry=0x19832):
            result=invoke(data,registers,resource,entry);assert result.returncode and inp.read_bytes()==data and out.read_bytes()==sentinel,(label,result.stdout,result.stderr)
            rows.append(dict(failure=label,entry=entry,input_output_preserved=True,native_executed=False,error=result.stderr.strip()))
        baseline=invoke(ram,regs,path);assert baseline.returncode==0,baseline.stderr
        for size in (0,65535,65537):reject(bytes(size),regs,path,'RAM-size')
        for index in range(12):
            for text in ('-1','4294967296','0x','1x',''):
                bad=regs.copy();bad[index]=text;reject(ram,bad,path,'register-parser-%d'%index)
        for entry in (0,0x192c5,0x19833,'-1','4294967296','0x','1x',''):reject(ram,regs,path,'entry-parser-or-unsupported',entry)
        for entry in ENTRIES:
            active=regs.copy();active[9]=FIXED+10;reject(ram,active,None,'missing-active-resource',entry)
            for cursor in (0,FIXED-10,FIXED+1,FIXED+40,FIXED+44,0xffffffff,0x106000):
                badram=bytearray(ram);badregs=regs.copy()
                if entry==0x192c4:badregs[9]=cursor
                else:
                    if cursor==0:continue # Null19832 is a supported positive case.
                    struct.pack_into('>I',badram,0xd3b4,cursor)
                reject(badram,badregs,path,'invalid-authoritative-cursor',entry)
        late=struct.pack('>5H2H',10,0x14,10,0,0,20,0xffff);path.write_bytes(container(late));badcase=dict(sample,cursor=FIXED,current_time=15,proposed_time=5,payload_hex=late.hex());badram=fixture(badcase);badregs=incoming(badcase,program,badram);reject(badram,badregs,path,'late-backward-record-read-rollback')
        for raw,label in ((b'bad','truncated-header'),(container(body)[:-1],'truncated-payload'),(container(body,version=2),'bad-version'),(container(body,kind=2),'wrong-kind'),(container(body,reserved=1),'reserved'),(container(body,cpu=FIXED+1,rom=FIXED+1),'odd-resource-address'),(container(body,cpu=0x100000,rom=0x100000),'RAM-resource-address'),(container(body,cpu=FIXED,rom=FIXED+2),'CPU-ROM-address-disagreement'),(container(body)+b'x','extra-payload')):
            path.write_bytes(raw);reject(ram,regs,path,label)
        corrupt=bytearray(container(body));corrupt[-1]^=1;path.write_bytes(corrupt);reject(ram,regs,path,'payload-CRC')
        for badbody,label in ((body[:-4],'missing-terminal'),(body+b'\0\0','trailing-bytes'),(body[:2]+b'\0\1'+body[4:],'invalid-type'),(b'\0\0\xff\xff','terminal-without-record'),(body[:10]+body[10:12]+b'\xff\xff'+body[14:],'premature-terminal'),(bytes(65540),'oversized-resource')):
            path.write_bytes(container(badbody));reject(ram,regs,path,label)
        path.write_bytes(container(body));inp.write_bytes(ram)
        for label in ('same-path','hardlink','symlink'):
            target=inp if label=='same-path' else work/label
            if label=='hardlink':os.link(inp,target)
            if label=='symlink':target.symlink_to(inp)
            actual=invoke(ram,regs,path,destination=target);assert actual.returncode and inp.read_bytes()==ram
            rows.append(dict(failure='input-output-'+label,input_output_preserved=True,native_executed=False))
        inp.write_bytes(ram);actual=subprocess.run([str(exe),'0x192c4']+list(map(str,regs))+[str(inp),str(out),str(inp)],capture_output=True,text=True);assert actual.returncode and inp.read_bytes()==ram and out.read_bytes()==sentinel
        rows.append(dict(failure='resource-input-alias',input_output_preserved=True,native_executed=False))
    return rows

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;cases,resources,metadata=build_cases(root,program);exe=root/'build/step_scene_motion_pair';binary=sha(exe.read_bytes());assert binary==BINARY_SHA256;negatives=negative_checks(root,program,cases)
    if '--negative-only' in sys.argv:print(json.dumps(dict(negative_cases=len(negatives))));return
    folder=root/'artifacts/scene_motion_pair';native_path=folder/'observation.json';native_bytes=native_path.read_bytes();native=json.loads(native_bytes);unicorn_path=folder/'unicorn_observation.json';unicorn_bytes=unicorn_path.read_bytes();unicorn=json.loads(unicorn_bytes);probe_path=folder/'unicorn_flag_probe.json';probe_bytes=probe_path.read_bytes();probe=json.loads(probe_bytes)
    oracle=oracle_provenance(root);assert native['oracle']==oracle
    return_probe_path=folder/'unicorn_pair_return_probe.json';return_probe_bytes=return_probe_path.read_bytes();return_probe=json.loads(return_probe_bytes);return_probe_tool=root/'tools/probe_unicorn_pair_return.py';return_probe_tool_sha=sha(return_probe_tool.read_bytes())
    assert sha(return_probe_bytes)=='65178c381f8ebfcc116cd854930c039b18b663bbdb2c4557ef8148d6b3f5e1a7' and return_probe['cases']==36 and return_probe['branch_disagreements']==3
    assert return_probe['source']==source and return_probe['musashi_revision']==oracle['metadata']['revision'] and return_probe['musashi_library_sha256']==oracle['metadata']['library_sha256'] and return_probe['musashi_metadata_sha256']==oracle['files_sha256']['artifacts/dependencies/musashi_oracle_build/metadata.json']
    assert native['source']==unicorn['source']==source and native['resources']==resources and native['metadata']==metadata and not native['program_code_modified'] and native['failure'] is None
    assert native['cases']==native['completed_cases']==len(native['results'])==len(cases)==4232
    assert unicorn['cases']==unicorn['completed_cases']==len(unicorn['results'])==4232 and not unicorn['carry_is_authoritative']
    assert len(probe['results'])==30 and all(not r['bcs_taken'] and not r['expected_carry_after_operation'] for r in probe['results'])
    previous={};rows=[];coverage=collections.Counter();types=set();bugpcs=set();transition_carries=collections.Counter();unicorn_SR_mismatches=0;diagnostics=[];secondary_previous={};overflow=collections.Counter()
    inp,out,path=folder/'input.bin',folder/'cpp.bin',folder/'synthetic.ms5d'
    for index,(case,row,secondary) in enumerate(zip(cases,native['results'],unicorn['results'])):
        assert row['case_index']==secondary['case_index']==index and row['fixture']==secondary['fixture']==case and row['returned'] and secondary['returned'] and row['final_pc']==secondary['final_pc']==RETURN and row['final_a7']==secondary['final_a7']==STACK+4 and row['mmio_writes']==secondary['mmio_writes']==0
        original=(folder/row['ram_file']).read_bytes();other=(folder/secondary['ram_file']).read_bytes();assert sha(original)==row['ram_sha256'] and sha(other)==secondary['ram_sha256'];assert_evidence(case,original,row['result'],row)
        unicorn_SR_mismatches+=row['result']['carry']!=secondary['result']['carry']
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None;ram=fixture(case) if prior is None else bytearray(prior[0]);regs=incoming(case,program,ram,None if prior is None else prior[1]);assert sha(ram)==row['input_ram_sha256'] and dict(zip(KEYS,regs))==row['incoming']
        secondary_prior=secondary_previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None;secondary_ram=fixture(case) if secondary_prior is None else bytearray(secondary_prior[0]);secondary_regs=incoming(case,program,secondary_ram,None if secondary_prior is None else secondary_prior[1]);assert sha(secondary_ram)==secondary['input_ram_sha256'] and dict(zip(KEYS,secondary_regs))==secondary['incoming']
        same_input=bytes(ram)==bytes(secondary_ram) and regs==secondary_regs
        fullstate_equal=original==other and all(row['result'][k]==secondary['result'][k] for k in KEYS)
        assert same_input and fullstate_equal,(index,'Unicorn-Musashi fullstate disagreement')
        assert row['calls']==secondary['calls'] and row['observed_types']==secondary['observed_types'] and row['branch_successors']==secondary['branch_successors']
        if 'sequence'in case:secondary_previous[case['sequence']]=(other,[secondary['result'][k] for k in KEYS])
        resource=None
        if case['relocated']:path.write_bytes(container(bytes.fromhex(case['payload_hex'])));resource=path
        elif case.get('path_file'):resource=root/case['path_file']
        inp.write_bytes(ram);args=[str(exe),str(case['entry'])]+list(map(str,regs))+[str(inp),str(out)]
        if resource is not None:args.append(str(resource))
        actual=subprocess.run(args,capture_output=True,text=True);assert actual.returncode==0 and inp.read_bytes()==ram,(index,case,actual.stderr)
        result=json.loads(actual.stdout);assert isinstance(result['carry'],bool);cpp=out.read_bytes();assert result==row['result'] and cpp==original,(index,case,result,row['result'],[(hex(i),a,b) for i,(a,b) in enumerate(zip(cpp,original)) if a!=b][:20])
        coverage.update(row['calls']);types.update(row['observed_types']);bugpcs.update(s['pc'] for s in row['duplicate_D0_ADD_snapshots'])
        for sample in row['comparison_snapshots']:
            pc=sample['pc'];bits=32 if pc==0x19864 else 16;mask=(1<<bits)-1;sign=1<<(bits-1);lhs=sample['d7'] if bits==32 else sample['d5']&mask;rhs=sample['d6'] if bits==32 else sample['end' if pc==0x1986c else 'start'];difference=(lhs-rhs)&mask
            if ((lhs^rhs)&(lhs^difference)&sign):overflow[hex(pc)]+=1
        for transition in row['transition_returns']:transition_carries[(transition['pc'],transition['carry'])]+=1
        rows.append(dict(case_index=index,family=case['family'],entry=case['entry'],ram_sha256=sha(cpp),result=result))
        if 'sequence'in case:previous[case['sequence']]=(cpp,[result[k] for k in KEYS])
    assert all(overflow[hex(pc)]>0 for pc in (0x19864,0x1986c,0x198b0))
    assert types==set(range(0,0x90,4)) and bugpcs==set(BUG_PCS.values())
    assert coverage['0x196ac'] and coverage['0x196de'] and coverage['0x1989a'] and coverage['0x198de'] and coverage['0x1989e'] and coverage['0x198e2']
    assert all(transition_carries[(pc,c)]>0 for pc in (0x19898,0x198dc) for c in (False,True))
    assert any(r['calls'].get('0x1985e',0)>2 for r in native['results'])
    assert not diagnostics # PC/register-only Unicorn hooks agree; in-call SR reads are prohibited.
    assert return_probe_path.read_bytes()==return_probe_bytes and sha(return_probe_tool.read_bytes())==return_probe_tool_sha
    assert oracle_provenance(root)==oracle
    assert sha(exe.read_bytes())==binary and native_path.read_bytes()==native_bytes and unicorn_path.read_bytes()==unicorn_bytes and probe_path.read_bytes()==probe_bytes and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    for item in resources+[metadata]:assert sha((root/item['file']).read_bytes())==item['sha256']
    families=collections.Counter(c['family'] for c in cases);carry=families['actual-cli-carry-three-pair-calls'];report=dict(source=source,binary_sha256=binary,oracle=native['oracle'],native_observation_sha256=sha(native_bytes),unicorn_observation_sha256=sha(unicorn_bytes),unicorn_flag_probe_sha256=sha(probe_bytes),unicorn_pair_return_probe_sha256=sha(return_probe_bytes),unicorn_pair_return_probe_tool_sha256=return_probe_tool_sha,cases=len(rows),negative_cases=len(negatives),families=dict(families),canonical_resource_cases=sum(c['family'].startswith('canonical') for c in cases),relocated_synthetic_cases=sum(c['relocated'] for c in cases),null_cases=families['null-pair-clears-D6-D7'],resources=resources,metadata=metadata,resource_inputs_unchanged=True,positive_input_RAM_preserved=True,mmio_writes=0,observed_types=sorted(types),duplicate_D0_ADD_pcs=sorted(bugpcs),N_only_comparison_V1_cases=dict(overflow),native_call_counts=dict(coverage),transition_carry_counts=[dict(pc=pc,carry=c,cases=n) for (pc,c),n in sorted(transition_carries.items())],multi_step_cases=sum(r['calls'].get('0x1985e',0)>1 for r in native['results']),Unicorn_Musashi_RAM_and_12regs_equal=True,Unicorn_in_call_SR_reads=False,Unicorn_Musashi_fullstate_disagreements=len(diagnostics),Unicorn_Musashi_identical_input_fullstate_disagreements=sum(r['same_input'] for r in diagnostics),Unicorn_Musashi_fullstate_diagnostics=diagnostics,Unicorn_returned_SR_C_disagreements=unicorn_SR_mismatches,cli_carry_sequences=len(previous),cli_carry_calls=carry,cli_calls_consuming_prior_output=carry-len(previous),defensive_operation_cap_exercised=False,defensive_operation_cap_scope='Exact immutable resource<=65536bytes gives<=6553records; invariant paired times keep transition direction fixed and cursor monotonic. Terminal/first/window failure occurs before1048576 cap. Oversized-resource rejection is separately tested.',results=rows,negative_results=negatives,scope='Unpatched original192c4/19832 continuously toRTS in pinnedMusashi, full64KiBRAM/12regs/actualCCR.C/A7+4. Uninterrupted Unicorn with PC/register-only hooks agrees in fullRAM/12regs; returnedUnicorn SR.C is retained diagnostically and Musashi is the authoritative carry oracle. Separate synthetic probes show rawSRread inconsistency and in-call SR-reading hook interference; no in-call SR reads or flag correction are used in this final corpus. Canonical37/108 strict; syntheticRAM106000 native versusfixedMS5D60000 normalizesonlyoutgoingA1/RAMd3b4. All36types, original tenADD.LD0,D3 behaviors, signedWORD expandedbands, accepted/rejected forward/backward transitions andmultistep. ActualCLI outputsfeed8chains; hostwritescurrent/proposedXY between calls andresets callboundary stack/SR, no callee reset or naturalmovement claim.')
    report_path=folder/'verification.json';report_path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),sha256=sha(report_path.read_bytes()))))
if __name__=='__main__':main()
