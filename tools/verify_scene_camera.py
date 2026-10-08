"""Strict fullcamera/axis native differential plus transaction and overflow checks."""
import collections
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_scene_command import REGS
from verify_scene_motion_bounds import container
from observe_scene_camera import build_cases,fixture,prepare,sha,KEYS,HIGHS,STACK,RETURN,FIXED,BASE,ENTRIES,assert_evidence,oracle_provenance
from verify_stage_catalog import SOURCE_SHA256
BINARY_SHA256='8371c0c02165583693691ae20e33ef0b974b4e97ddc033957cb7243f15445944'

def negative_checks(root,program,cases):
    folder=root/'artifacts/scene_camera';folder.mkdir(parents=True,exist_ok=True);exe=root/'build/step_scene_camera';rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temp:
        work=Path(temp);inp,out,path=work/'input.bin',work/'output.bin',work/'motion.ms5d';sentinel=b'preserved-scene-camera-output\0\xff'
        sample=next(c for c in cases if c['family']=='synthetic-all36-full-camera' and c['kind']==0x14 and c['flags']==0 and c['time']==15);ram=fixture(sample,program);regs=list(HIGHS[sample['profile']]);body=bytes.fromhex(sample['payload_hex']);path.write_bytes(container(body))
        def invoke(data,registers,resource,entry=0x19b96,destination=out):
            inp.write_bytes(data)
            if destination==out:out.write_bytes(sentinel)
            args=[str(exe),str(entry)]+list(map(str,registers))+[str(inp),str(destination)]
            if resource is not None:args.append(str(resource))
            return subprocess.run(args,capture_output=True,text=True)
        def reject(data,registers,resource,label,entry=0x19b96):
            actual=invoke(data,registers,resource,entry);assert actual.returncode and inp.read_bytes()==data and out.read_bytes()==sentinel,(label,actual.stdout,actual.stderr)
            rows.append(dict(failure=label,entry=entry,input_output_preserved=True,native_executed=False,error=actual.stderr.strip()))
        baseline=invoke(ram,regs,path);assert baseline.returncode==0,baseline.stderr
        for size in (0,65535,65537):reject(bytes(size),regs,path,'RAM-size')
        for index in range(12):
            for text in ('-1','4294967296','0x','1x',''):
                bad=regs.copy();bad[index]=text;reject(ram,bad,path,'register-parser-%d'%index)
        for entry in (0,0x19a41,0x19ac9,0x19b97,'-1','4294967296','0x','1x',''):reject(ram,regs,path,'entry-parser-or-unsupported',entry)
        reject(ram,regs,None,'late-missing-active-resource-after-proposal-writes')
        forced=bytearray(ram);struct.pack_into('>H',forced,0xd3fa,0xffff);reject(forced,regs,None,'late-forced-missing-resource-after-bound-adjustment')
        for cursor in (FIXED-10,FIXED+1,FIXED+40,FIXED+44,0xffffffff,0x106000):
            bad=bytearray(ram);struct.pack_into('>I',bad,0xd3b4,cursor);reject(bad,regs,path,'late-invalid-cursor-after-proposal-writes')
        late=struct.pack('>5H2H',10,0x14,10,0,0,20,0xffff);path.write_bytes(container(late));badcase=dict(sample,cursor=FIXED,time=15,fraction=0,payload_hex=late.hex(),fixed_delta=[0xfff60000,0]);bad=fixture(badcase,program);reject(bad,regs,path,'late-backward-window-failure')
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
        for target,label in ((inp,'resource-input-alias'),(out,'resource-output-alias')):
            inp.write_bytes(ram);out.write_bytes(sentinel);actual=subprocess.run([str(exe),'0x19b96']+list(map(str,regs))+[str(inp),str(out),str(target)],capture_output=True,text=True);assert actual.returncode and inp.read_bytes()==ram and out.read_bytes()==sentinel;rows.append(dict(failure=label,input_output_preserved=True,native_executed=False))
    return rows

class UnicornAxisObserver:
    """No SR reads during execution; selected axis overflow cases have no motion data."""
    def __init__(self,program):
        self.cpu=make_cpu(program);self.baseline=self.cpu.context_save();self.program=program
        def code(cpu,address,size,user):
            if address==RETURN:cpu.emu_stop()
        def write(cpu,access,address,size,value,user):assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(address),size,value)
        self.cpu.hook_add(UC_HOOK_CODE,code);self.cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    def run(self,entry,ram,values):
        assert entry in ENTRIES[:2];cpu=self.cpu;cpu.context_restore(self.baseline);cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        for register,value in zip(REGS,values):cpu.reg_write(register,value)
        cpu.emu_start(entry,0xffffff,count=200000);assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN and cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4 and bytes(cpu.mem_read(0,BASE))==self.program[:BASE]
        return bytes(cpu.mem_read(BASE,65536)),dict(zip(KEYS,(cpu.reg_read(register)&0xffffffff for register in REGS)))

def add_overflow(add):return bool((~(add['left']^add['right'])&(add['left']^add['result']))&0x80000000)
def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;cases,resources,metadata=build_cases(root,program);exe=root/'build/step_scene_camera';binary=sha(exe.read_bytes());assert binary==BINARY_SHA256;negatives=negative_checks(root,program,cases)
    if '--negative-only'in sys.argv:print(json.dumps(dict(negative_cases=len(negatives))));return
    folder=root/'artifacts/scene_camera';native_path=folder/'observation.json';native_bytes=native_path.read_bytes();native=json.loads(native_bytes);oracle=oracle_provenance(root)
    assert native['source']==source and native['oracle']==oracle and native['resources']==resources and native['metadata']==metadata and native['failure'] is None and not native['program_code_modified']
    assert native['cases']==native['completed_cases']==len(native['results'])==len(cases)==2773
    previous={};rows=[];calls=collections.Counter();overflow=collections.Counter();overflow_signs=collections.Counter();limitpaths=collections.Counter();types=set();rejected_cursor_changed=[];secondary=[];unicorn=UnicornAxisObserver(program)
    inp,out,path=folder/'input.bin',folder/'cpp.bin',folder/'synthetic.ms5d'
    for index,(case,row) in enumerate(zip(cases,native['results'])):
        assert row['case_index']==index and row['fixture']==case and row['returned'] and row['final_pc']==RETURN and row['final_a7']==STACK+4 and row['mmio_writes']==0
        original=(folder/row['ram_file']).read_bytes();assert sha(original)==row['ram_sha256'];assert_evidence(case,original,row['result'],row)
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None;ram=fixture(case,program) if prior is None else bytearray(prior[0]);prepare(case,ram);regs=list(HIGHS[case['profile']] if prior is None else prior[1]);assert sha(ram)==row['input_ram_sha256'] and dict(zip(KEYS,regs))==row['incoming']
        resource=None
        if case['relocated']:path.write_bytes(container(bytes.fromhex(case['payload_hex'])));resource=path
        elif case.get('path_file'):resource=root/case['path_file']
        inp.write_bytes(ram);args=[str(exe),str(case['entry'])]+list(map(str,regs))+[str(inp),str(out)]
        if resource is not None:args.append(str(resource))
        actual=subprocess.run(args,capture_output=True,text=True);assert actual.returncode==0 and inp.read_bytes()==ram,(index,case,actual.stderr)
        result=json.loads(actual.stdout);cpp=out.read_bytes();assert result==row['result'] and cpp==original,(index,case,result,row['result'],[(hex(i),a,b) for i,(a,b) in enumerate(zip(cpp,original)) if a!=b][:20])
        calls.update(row['calls']);types.update(row['observed_motion_types'])
        for add in row['signed_ADD_branches']:
            if add_overflow(add):overflow[hex(add['pc'])]+=1;overflow_signs['negative' if add['result']&0x80000000 else 'nonnegative']+=1
        for branch in row['unsigned_limit_branches']:limitpaths[(branch['pc'],branch['next_pc'])]+=1
        if row['calls'].get('0x19ce6') and row['input_cursor']!=row['predecision']['cursor']:rejected_cursor_changed.append(index)
        if case['entry'] in ENTRIES[:2] and any(add_overflow(add) for add in row['signed_ADD_branches']):
            other,other_result=unicorn.run(case['entry'],ram,regs);assert other==original and other_result==row['result'];secondary.append(dict(case_index=index,entry=case['entry'],RAM_sha256=sha(other),full_RAM_12regs_equal=True,no_in_call_SR_read=True))
        rows.append(dict(case_index=index,family=case['family'],entry=case['entry'],result=result,ram_sha256=sha(cpp)))
        if 'sequence'in case:previous[case['sequence']]=(cpp,[result[key] for key in KEYS])
    assert types==set(range(0,0x90,4)) and overflow['0x19aa8'] and overflow['0x19b30'] and all(overflow_signs[k] for k in ('negative','nonnegative'))
    assert calls['0x19ce6'] and calls['0x19cd6'] and rejected_cursor_changed and calls['0x19c3e'] and calls['0x19c5a']
    assert all(limitpaths[(pc,a)] and limitpaths[(pc,b)] for pc,a,b in ((0x19c24,0x19c44,0x19c28),(0x19c32,0x19c40,0x19c36),(0x19c38,0x19c3e,0x19c3c),(0x19c4e,0x19c52,0x19c5c),(0x19c54,0x19c58,0x19c5a)))
    assert sha(exe.read_bytes())==binary and native_path.read_bytes()==native_bytes and oracle_provenance(root)==oracle and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    for item in resources+[metadata]:assert sha((root/item['file']).read_bytes())==item['sha256']
    families=collections.Counter(case['family'] for case in cases);carry=families['actual-cli-camera-carry'];report=dict(source=source,oracle=oracle,binary_sha256=binary,native_observation_sha256=sha(native_bytes),cases=len(rows),negative_cases=len(negatives),families=dict(families),canonical_resource_cases=sum(case['family'].startswith('canonical') for case in cases),relocated_synthetic_cases=sum(case['relocated'] for case in cases),null_fullcamera_cases=sum(case['entry']==0x19b96 and not case['cursor'] for case in cases),resources=resources,metadata=metadata,resource_inputs_unchanged=True,positive_input_RAM_preserved=True,mmio_writes=0,observed_motion_types=sorted(types),native_call_counts=dict(calls),signed_ADD_V1_counts=dict(overflow),signed_ADD_V1_result_signs=dict(overflow_signs),unsigned_limit_branch_paths=[dict(pc=pc,next_pc=next_pc,count=count) for (pc,next_pc),count in sorted(limitpaths.items())],rejected_with_changed_cursor_cases=rejected_cursor_changed,selected_Unicorn_axis_cases=len(secondary),selected_Unicorn_results=secondary,cli_carry_sequences=len(previous),cli_carry_calls=carry,cli_calls_consuming_prior_output=carry-len(previous),results=rows,negative_results=negatives,scope='Original unpatched19a40/19ac8/full19b96 continuously toRTS in pinnedMusashi, full64KiBRAM/12regs/A7+4/zeroMMIO, writeguard. Selectedaxis V1 cases independently agree withUnicorn PC-only hooks and no in-callSRread. Canonical37resources/all108records strict; all36types separately synthetic nativeRAM106000 versusexactMS5D60000, normalizeonlyA1/RAMd3b4. SignedADD BGE usesNxorV; Ystore-before-read; flags0..3, forcedunsignedWORD andforcedLONGwrap stillforward, unsignedlimits/fallbacks, accepted/rejected proposals withcursorretention. Eight actualCLI chains carryremainingRAM/12regs; hostrewritesbounds,centers,margins,speedlimits,oldvelocities,phaselimits,force,fixeddeltas,flags,cameraWORDs eachcall. Not naturalframe/velocitycarry/cycleequivalence.')
    report_path=folder/'verification.json';report_path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),sha256=sha(report_path.read_bytes()))))
if __name__=='__main__':main()
