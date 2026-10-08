"""Independent full-RAM/12-register native differential and CLI transaction checks."""
import collections
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import zlib
from disassemble_program import load_verified_program
from observe_scene_motion_bounds import build_cases,fixture,values,sha,KEYS,HIGHS,STACK,RETURN,FIXED,ENTRIES,assert_evidence
from verify_stage_catalog import SOURCE_SHA256

BINARY_SHA256='26a6a36905958222df410a61b662d9a224fa134755390bc1a9f54dfdafbbcd3d'
def container(body,cpu=FIXED,rom=FIXED,version=1,kind=1,reserved=0):
    return struct.pack('<4s7I',b'MS5D',version,kind,cpu,rom,len(body),zlib.crc32(body),reserved)+body

def negative_checks(root,program,cases):
    folder=root/'artifacts/scene_motion_bounds';folder.mkdir(parents=True,exist_ok=True);exe=root/'build/step_scene_motion_bounds';rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temp:
        work=Path(temp);inp,out,resource=work/'input.bin',work/'output.bin',work/'motion.ms5d';sentinel=b'preserved-motion-bounds-output\0\xff'
        sample=next(c for c in cases if c['relocated'] and c['entry']==0x19d08 and c['kind']==0x14 and c['extent']==1 and c['fraction']==0)
        ram=fixture(sample);regs=values(sample,program,ram);body=bytes.fromhex(sample['payload_hex']);resource.write_bytes(container(body))
        def invoke(data,registers,path,entry=0x19d08,destination=out):
            inp.write_bytes(data)
            if destination==out:out.write_bytes(sentinel)
            args=[str(exe),str(entry)]+list(map(str,registers))+[str(inp),str(destination)]
            if path is not None:args.append(str(path))
            result=subprocess.run(args,capture_output=True,text=True)
            return result
        def reject(data,registers,path,label,entry=0x19d08):
            actual=invoke(data,registers,path,entry)
            assert actual.returncode and inp.read_bytes()==data and out.read_bytes()==sentinel,(label,actual.stdout,actual.stderr)
            rows.append(dict(failure=label,entry=entry,input_output_preserved=True,error=actual.stderr.strip(),native_executed=False))
        baseline=invoke(ram,regs,resource);assert baseline.returncode==0,baseline.stderr
        for size in (0,65535,65537):reject(bytes(size),regs,resource,'RAM-size')
        for index in range(12):
            for text in ('-1','4294967296','0x','1x',''):
                invalid=list(regs);invalid[index]=text;reject(ram,invalid,resource,'register-parser-%d'%index)
        for entry in (0,0x198ef,0x19d99,'-1','4294967296','0x','1x',''):reject(ram,regs,resource,'entry-parser-or-unsupported',entry)
        for entry in ENTRIES:
            reject(ram,regs,None,'missing-active-resource',entry)
            for cursor in (FIXED-10,FIXED+1,FIXED+30,FIXED+34,0xffffffff,0x106000):
                bad=bytearray(ram);struct.pack_into('>I',bad,0xd3b4,cursor);reject(bad,regs,resource,'invalid-cursor',entry)
        # Failure after19d08 has reset all four bounds and evaluated coordinate/time.
        late=struct.pack('>5H2H',10,0x14,1,0,0,20,0xffff);resource.write_bytes(container(late));bad=bytearray(ram);struct.pack_into('>I',bad,0xd3b4,FIXED);struct.pack_into('>II',bad,0xd3bc,0,0)
        reject(bad,regs,resource,'late-backward-read-after-bounds-reset')
        for malformed,label in ((b'bad','truncated-header'),(container(body)[:-1],'truncated-payload'),(container(body,version=2),'bad-version'),(container(body,kind=2),'wrong-kind'),(container(body,reserved=1),'reserved'),(container(body,cpu=FIXED+1,rom=FIXED+1),'odd-resource-address'),(container(body,cpu=0x100000,rom=0x100000),'RAM-resource-address'),(container(body)+b'x','extra-payload')):
            resource.write_bytes(malformed);reject(ram,regs,resource,label)
        corrupt=bytearray(container(body));corrupt[-1]^=1;resource.write_bytes(corrupt);reject(ram,regs,resource,'payload-CRC')
        # Runtime validation uses complete10-byte records plus exact4-byte terminal.
        for badbody,label in ((body[:-4],'missing-terminal'),(body+b'\0\0','trailing-bytes'),(body[:2]+b'\0\1'+body[4:],'invalid-type'),(b'\0\0\xff\xff','terminal-without-record'),(body[:10]+body[10:12]+b'\xff\xff'+body[14:],'premature-terminal')):
            resource.write_bytes(container(badbody));reject(ram,regs,resource,label)
        resource.write_bytes(container(body));inp.write_bytes(ram)
        for name in ('same-path','hardlink','symlink'):
            target=inp if name=='same-path' else work/name
            if name=='hardlink':os.link(inp,target)
            if name=='symlink':target.symlink_to(inp)
            actual=invoke(ram,regs,resource,destination=target);assert actual.returncode and inp.read_bytes()==ram
            rows.append(dict(failure='input-output-'+name,input_output_preserved=True,native_executed=False))
        # Optional resource omitted with null input; compare independently against native report later.
    return rows

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;cases,resources,metadata=build_cases(root,program);exe=root/'build/step_scene_motion_bounds';binary=sha(exe.read_bytes());assert binary==BINARY_SHA256
    negatives=negative_checks(root,program,cases)
    if '--negative-only' in sys.argv:print(json.dumps(dict(negative_cases=len(negatives))));return
    folder=root/'artifacts/scene_motion_bounds';observation_path=folder/'observation.json';observation_bytes=observation_path.read_bytes();native=json.loads(observation_bytes)
    assert native['source']==source and native['resources']==resources and native['metadata']==metadata and not native['program_code_modified'] and native['failure'] is None
    assert native['cases']==native['completed_cases']==len(native['results'])==len(cases)==3606
    previous={};rows=[];coverage=collections.Counter();types={hex(entry):set() for entry in ENTRIES}
    inp,out,resource=folder/'input.bin',folder/'cpp.bin',folder/'synthetic.ms5d'
    for index,(case,row) in enumerate(zip(cases,native['results'])):
        assert row['case_index']==index and row['fixture']==case and row['returned'] and row['final_pc']==RETURN and row['final_a7']==STACK+4 and row['mmio_writes']==0
        original=(folder/row['ram_file']).read_bytes();assert sha(original)==row['ram_sha256'];assert_evidence(case,original,row['result'],row)
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None;ram=fixture(case) if prior is None else bytearray(prior[0]);struct.pack_into('>H',ram,0xd418,case['phase']);regs=values(case,program,ram,None if prior is None else prior[1]);assert sha(ram)==row['input_ram_sha256'] and dict(zip(KEYS,regs))==row['incoming']
        path=None
        if case['relocated']:resource.write_bytes(container(bytes.fromhex(case['payload_hex'])));path=resource
        elif case.get('path_file'):path=root/case['path_file']
        inp.write_bytes(ram);args=[str(exe),str(case['entry'])]+list(map(str,regs))+[str(inp),str(out)]
        if path is not None:args.append(str(path))
        actual=subprocess.run(args,capture_output=True,text=True);assert actual.returncode==0 and inp.read_bytes()==ram,(index,case,actual.stderr)
        result=json.loads(actual.stdout);cpp=out.read_bytes();assert result==row['result'] and cpp==original,(index,case,result,row['result'],[(hex(i),a,b) for i,(a,b) in enumerate(zip(cpp,original)) if a!=b][:20])
        for pc,count in row['calls'].items():coverage[pc]+=count
        types[hex(case['entry'])].update(row['observed_types'])
        rows.append(dict(case_index=index,family=case['family'],entry=case['entry'],ram_sha256=sha(cpp),result=result))
        if 'sequence' in case:previous[case['sequence']]=(cpp,[result[k] for k in KEYS])
    assert all(v==set(range(0,0x90,4)) for v in types.values());assert coverage['0x196ac'] and coverage['0x196de'] and coverage['0x19d72'] and coverage['0x19d8e']
    for branch,store in (('0x19dc0','0x19dc4'),('0x19dcc','0x19dd0'),('0x19dd8','0x19ddc'),('0x19de4','0x19de8')):assert coverage[branch]>coverage[store]>0
    assert sha(exe.read_bytes())==binary and observation_path.read_bytes()==observation_bytes and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    for item in resources+[metadata]:assert sha((root/item['file']).read_bytes())==item['sha256']
    families=collections.Counter(c['family'] for c in cases);carry=families['actual-cli-carry-four-helper-chain'];report=dict(source=source,binary_sha256=binary,native_observation_sha256=sha(observation_bytes),cases=len(rows),canonical_resource_cases=families['canonical37-all-four-entries-time-boundaries'],null_cases=families['null-base-signed-WORD-boundaries']+families['19d08-only-last-ADD-overflow-saturation'],relocated_synthetic_cases=sum(c['relocated'] for c in cases),families=dict(families),negative_cases=len(negatives),resources=resources,metadata=metadata,resource_inputs_unchanged=True,positive_input_RAM_preserved=True,mmio_writes=0,observed_types={k:sorted(v) for k,v in types.items()},native_call_counts=dict(coverage),overflow_branch_evidence_cases=families['N-only-LONG-vs-signed-WORD-overflow'],last_ADD_overflow_cases=families['19d08-only-last-ADD-overflow-saturation'],distinct_envelope_target_cases=sum(r['fixture']['entry']==0x19d08 and len(set(r['envelope_times']))==2 for r in native['results']),stack_restore_evidence_cases=families['19d08-distinct-unsigned-clamps-and-stack-restore'],cli_carry_sequences=len(previous),cli_carry_calls=carry,cli_calls_consuming_prior_output=carry-len(previous),results=rows,negative_results=negatives,scope='Originalunpatched198ee/19978/19d98/19d08 uninterruptedtoRTS all64KiBRAM/12regs withA7+4 andzeroMMIO. Canonical37 strictCPUaddresses; syntheticRAM106000 native versusMS5D60000 C++ normalizesonlyoutgoingA1 andRAMd3b4. All36types,fiveWORDextents,negativefractions/overflow,forward/backwardselection,N-onlyLONGclamps versus signedWORDbounds,onlyfinalADDsaturation. ActualCLI RAM/all12regs carry4chains, hostupdatesD7 andphase eachcall andcameraXY before19d08; no naturalframe/CCR claim. Nativefixture/hash/fullcountguards preventtruncation.')
    path=folder/'verification.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),sha256=sha(path.read_bytes()))))
if __name__=='__main__':main()
