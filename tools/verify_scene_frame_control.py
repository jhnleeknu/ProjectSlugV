"""Full native differential and failure-atomic CLI checks for frame-control helpers."""
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
from observe_scene_frame_control import build_cases,fixture,incoming,assert_evidence,sha,KEYS,BASE,STACK,RETURN,ENTRIES,COND,RECT,DURATION,OBJECTS,oracle_provenance
from verify_stage_catalog import SOURCE_SHA256
BINARY_SHA256='f1aab899f94c2afcb007d00de387720910fed339b3066cecb8da80958b66e2a4'


def negative_checks(root,cases):
    folder=root/'artifacts/scene_frame_control';folder.mkdir(parents=True,exist_ok=True);exe=root/'build/step_scene_frame_control';rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temp:
        work=Path(temp);inp,out,path,other=work/'input.bin',work/'output.bin',work/'resource.ms5d',work/'other.ms5d';sentinel=b'preserved-frame-control-output\0\xff'
        sample=next(c for c in cases if c['family']=='synthetic-selector0-unsigned-phase-force' and c['phase']==1 and c['threshold']==1);ram=fixture(sample);regs=incoming(sample)
        def invoke(data,registers,files=(),entry=0x1a2b4,destination=out):
            inp.write_bytes(data)
            if destination==out:out.write_bytes(sentinel)
            return subprocess.run([str(exe),str(entry)]+list(map(str,registers))+[str(inp),str(destination)]+list(map(str,files)),capture_output=True,text=True)
        def reject(data,registers,label,files=(),entry=0x1a2b4):
            actual=invoke(data,registers,files,entry);assert actual.returncode and inp.read_bytes()==data and out.read_bytes()==sentinel,(label,actual.stdout,actual.stderr);rows.append(dict(failure=label,entry=entry,input_output_preserved=True,native_executed=False,error=actual.stderr.strip()))
        baseline=invoke(ram,regs);assert not baseline.returncode and json.loads(baseline.stdout)['carry'],baseline.stderr
        for size in (0,65535,65537):reject(bytes(size),regs,'RAM-size')
        for index in range(12):
            for text in ('-1','4294967296','0x','1x',''):
                bad=regs.copy();bad[index]=text;reject(ram,bad,'register-parser-%d'%index)
        for entry in (0,0x1a2b5,0x1a34d,0x1a29f,0x1a527,0x1a3d7,'-1','4294967296','0x','1x',''):reject(ram,regs,'entry-parser-or-unsupported',entry=entry)
        for selector in (1,2,3,12,0x8000,0xffff):
            bad=bytearray(ram);struct.pack_into('>H',bad,COND-BASE,selector);reject(bad,regs,'unknown-selector-%x'%selector)
        for pointer in (COND+1,0x10ffff,0x110000,0x60000,0xfffffffe,0xffffffff):
            bad=bytearray(ram);struct.pack_into('>I',bad,0xd422,pointer);reject(bad,regs,'invalid-condition-read')
        # Duration errors occur after condition force write and condition-pointer clear.
        for pointer in (DURATION+1,0x10fffe,0x110000,0x60000,0xfffffffe,0xffffffff):
            bad=bytearray(ram);struct.pack_into('>I',bad,0xd3b4,pointer);reject(bad,regs,'late-condition-true-duration-read');reject(bad,regs,'late-direct-duration-read',entry=0x1a29e)
        rectcase=next(c for c in cases if c['entry']==0x1a34c and c['family']=='packed-low-Y-carry-increments-X');rectram=fixture(rectcase);rectregs=incoming(rectcase)
        for pointer in (RECT+1,0x10fffe,0x110000,0x60000,0xfffffffe,0xffffffff):
            bad=rectregs.copy();bad[9]=pointer;reject(rectram,bad,'invalid-active-rectangle-read',entry=0x1a34c)
        for pointer in (OBJECTS[0]+1,0x10fffc,0x10ffbe,0x110000,0xfffffffe,0xffffffff):
            bad=rectregs.copy();bad[8]=pointer
            data=bytearray(rectram)
            if pointer==0x10fffc:struct.pack_into('>I',data,0xfffc,0x1234)
            if pointer==0x10ffbe:struct.pack_into('>I',data,0xffbe,0x1234);data[0xffd3]=0x80
            reject(data,bad,'invalid-object-field-read',entry=0x1a34c)
        body=struct.pack('>HH',0,0x1234);fixedram=bytearray(ram);struct.pack_into('>I',fixedram,0xd422,0x60000);path.write_bytes(container(body));assert invoke(fixedram,regs,[path]).returncode==0
        for raw,label in ((b'bad','truncated-header'),(container(body)[:-1],'truncated-payload'),(container(body,version=2),'bad-version'),(container(body,kind=2),'wrong-kind'),(container(body,reserved=1),'reserved'),(container(body,cpu=0x60001,rom=0x60001),'odd-resource-address'),(container(body,cpu=BASE,rom=BASE),'RAM-resource-address'),(container(body,cpu=0x60000,rom=0x60002),'CPU-ROM-disagreement'),(container(body)+b'x','extra-payload')):
            path.write_bytes(raw);reject(fixedram,regs,label,[path])
        corrupt=bytearray(container(body));corrupt[-1]^=1;path.write_bytes(corrupt);reject(fixedram,regs,'payload-CRC',[path])
        path.write_bytes(container(body));other.write_bytes(container(body));reject(fixedram,regs,'ambiguous-complete-condition-windows',[path,other])
        other.write_bytes(container(body[:2],cpu=0x60002,rom=0x60002));reject(fixedram,regs,'ambiguous-partial-condition-window',[path,other])
        path.write_bytes(container(body[:2]));reject(fixedram,regs,'partial-condition-force-word',[path])
        # Two adjacent windows cannot jointly supply one LONG rectangle read.
        bad=rectregs.copy();bad[9]=0x60000;path.write_bytes(container(b'\0\0'));other.write_bytes(container(bytes(6),cpu=0x60002,rom=0x60002));reject(rectram,bad,'split-LONG-rectangle-window',[path,other],entry=0x1a34c)
        path.write_bytes(container(bytes(6)));reject(rectram,bad,'partial-rectangle-extent',[path],entry=0x1a34c)
        late=bytearray(ram);struct.pack_into('>I',late,0xd3b4,0x60000);path.write_bytes(container(struct.pack('>5H',0,0x8001,0,0,0)));reject(late,regs,'late-raw-duration-without-terminal',[path])
        path.write_bytes(container(struct.pack('>HH',0,0x1234)));reject(ram,regs,'unused-missing-resource-loader-rejection',[work/'missing.ms5d'])
        # Pointer aliases are rejected before opening/truncating outputs.
        inp.write_bytes(ram)
        for label in ('same-path','hardlink','symlink'):
            target=inp if label=='same-path' else work/label
            if label=='hardlink':os.link(inp,target)
            if label=='symlink':target.symlink_to(inp)
            actual=invoke(ram,regs,[path],destination=target);assert actual.returncode and inp.read_bytes()==ram;rows.append(dict(failure='input-output-'+label,input_output_preserved=True,native_executed=False))
        for target,label in ((inp,'resource-input-alias'),(out,'resource-output-alias')):
            reject(ram,regs,label,[target])
        # Existing output/resource inode must not be truncated, even via an alias.
        out.write_bytes(container(body));alias=work/'output-resource.ms5d';os.link(out,alias);before=out.read_bytes();inp.write_bytes(ram);actual=subprocess.run([str(exe),'0x1a2b4']+list(map(str,regs))+[str(inp),str(out),str(alias)],capture_output=True,text=True);assert actual.returncode and out.read_bytes()==before and inp.read_bytes()==ram;rows.append(dict(failure='resource-output-hardlink',input_output_preserved=True,native_executed=False))
    return rows


class UnicornObserver:
    """PC-only hooks: no SR reads during execution, and no raw-SR carry claim."""
    def __init__(self,program):
        self.cpu=make_cpu(program);self.baseline=self.cpu.context_save();self.program=program
        def hook(cpu,address,size,user):
            if address==RETURN:cpu.emu_stop()
        def write(cpu,access,address,size,value,user):assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4
        self.cpu.hook_add(UC_HOOK_CODE,hook);self.cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    def run(self,entry,ram,values):
        cpu=self.cpu;cpu.context_restore(self.baseline);cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        for register,value in zip(REGS,values):cpu.reg_write(register,value)
        cpu.emu_start(entry,0xffffff,count=200000);assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN and cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4 and bytes(cpu.mem_read(0,BASE))==self.program[:BASE]
        return bytes(cpu.mem_read(BASE,65536)),dict(zip(KEYS,(cpu.reg_read(register)&0xffffffff for register in REGS)))


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;cases,resources,metadata=build_cases(root,program);exe=root/'build/step_scene_frame_control';binary=sha(exe.read_bytes());assert binary==BINARY_SHA256;negatives=negative_checks(root,cases)
    if '--negative-only'in sys.argv:print(json.dumps(dict(negative_cases=len(negatives))));return
    folder=root/'artifacts/scene_frame_control';native_path=folder/'observation.json';native_bytes=native_path.read_bytes();native=json.loads(native_bytes);oracle=oracle_provenance(root)
    assert native['source']==source and native['oracle']==oracle and native['resources']==resources and native['metadata']==metadata and native['failure'] is None and not native['program_code_modified']
    assert native['cases']==native['completed_cases']==len(native['results'])==len(cases)==2235
    previous={};rows=[];calls=collections.Counter();branches=collections.Counter();secondary=[];unicorn=UnicornObserver(program);inlines=set();cursor_resources=set();rect_counts=collections.Counter();shake_clamps=collections.Counter()
    inp,out=folder/'input.bin',folder/'cpp.bin'
    for index,(case,row) in enumerate(zip(cases,native['results'])):
        assert row['case_index']==index and row['fixture']==case and row['returned'] and row['final_pc']==RETURN and row['final_a7']==STACK+4 and row['mmio_writes']==0 and type(row['result']['carry']) is bool
        original=(folder/row['ram_file']).read_bytes();assert sha(original)==row['ram_sha256'];prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None;ram=fixture(case) if prior is None else bytearray(prior[0]);regs=incoming(case,None if prior is None else prior[1]);assert sha(ram)==row['input_ram_sha256'] and dict(zip(KEYS,regs))==row['incoming'];assert_evidence(case,ram,original,row['result'],row,regs)
        inp.write_bytes(ram);actual=subprocess.run([str(exe),str(case['entry'])]+list(map(str,regs))+[str(inp),str(out)]+[str(root/file) for file in case['files']],capture_output=True,text=True);assert actual.returncode==0 and inp.read_bytes()==ram,(index,case,actual.stderr);result=json.loads(actual.stdout);cpp=out.read_bytes();assert type(result['carry']) is bool and result==row['result'] and cpp==original,(index,case,result,row['result'],[(hex(i),a,b) for i,(a,b) in enumerate(zip(cpp,original)) if a!=b][:20])
        calls.update(row['calls']);branches.update((b['pc'],b['next_pc']) for b in row['branch_successors'])
        if 'canonical_inline'in case:inlines.add(case['canonical_inline'])
        if case['family']=='canonical-duration-all108-cursors':cursor_resources.add(case['motion'])
        if case['family']=='synthetic-selector8-overlap-shortcircuits':rect_counts[len(row['rectangle_calls'])]+=1
        if case['entry']==0x1a3d6:shake_clamps['positive' if row['calls'].get('0x1a3f6') else 'negative' if row['calls'].get('0x1a400') else 'unclamped']+=1
        selected=case['family'] in ('packed-low-Y-carry-increments-X','rectangle-Y-reject-preserves-unswapped-packed-registers','RAM-duration-live-d422-clear-alias','actual-cli-sixteen-shake-output-carry','condition-true-RAM-nonnull-duration') or (case['family']=='synthetic-rectangle-packed-signed-edges-camera' and case['profile']==1 and case['mode']=='active') or (case['family']=='settings-unsigned-min-max-and-D0-only-fallback' and case['profile']==1)
        if selected:
            other,other_result=unicorn.run(case['entry'],ram,regs);assert other==original and other_result=={key:result[key] for key in KEYS},(index,'secondary',other_result,result);secondary.append(dict(case_index=index,full_RAM_12regs_equal=True,no_in_call_SR_read=True))
        rows.append(dict(case_index=index,family=case['family'],entry=case['entry'],result=result,ram_sha256=sha(cpp)))
        if 'sequence'in case:previous[case['sequence']]=(cpp,[result[key] for key in KEYS])
    assert len(inlines)==9 and len(cursor_resources)==108 and all(rect_counts[n] for n in (2,3,4)) and all(shake_clamps[k] for k in ('positive','negative','unclamped'))
    for pc,a,b in ((0x1a352,0x1a35c,0x1a356),(0x1a362,0x1a3a0,0x1a366),(0x1a380,0x1a3a0,0x1a384),(0x1a386,0x1a3a0,0x1a38a),(0x1a390,0x1a3a0,0x1a394),(0x1a396,0x1a3a0,0x1a39a),(0x1a534,0x1a538,0x1a53a),(0x1a540,0x1a544,0x1a546),(0x1a55a,0x1a55e,0x1a566),(0x1a57a,0x1a57e,0x1a586),(0x1a596,0x1a59a,0x1a59e)):
        assert branches[(pc,a)] and branches[(pc,b)],(hex(pc),branches)
    # Directory loader reproduces an actual canonical selected-resource call.
    directory_case=next((i,c) for i,c in enumerate(cases) if c['family']=='canonical-nine-inline-conditions');index,case=directory_case
    with tempfile.TemporaryDirectory(dir=folder) as temp:
        directory=Path(temp);file=root/case['files'][0];(directory/file.name).write_bytes(file.read_bytes());ram=fixture(case);regs=incoming(case);inp.write_bytes(ram);actual=subprocess.run([str(exe),str(case['entry'])]+list(map(str,regs))+[str(inp),str(out),str(directory)],capture_output=True,text=True);assert actual.returncode==0 and json.loads(actual.stdout)==native['results'][index]['result'] and out.read_bytes()==(folder/native['results'][index]['ram_file']).read_bytes() and inp.read_bytes()==ram
    assert sha(exe.read_bytes())==binary and native_path.read_bytes()==native_bytes and oracle_provenance(root)==oracle and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    for item in resources:assert sha((root/item['file']).read_bytes())==item['sha256']
    assert sha((root/metadata['condition_inventory_file']).read_bytes())==metadata['condition_inventory_sha256'] and sha((root/metadata['script_manifest']['file']).read_bytes())==metadata['script_manifest']['sha256']
    families=collections.Counter(c['family'] for c in cases);carry=sum(v for k,v in families.items() if k.startswith('actual-cli-'));report=dict(source=source,oracle=oracle,binary_sha256=binary,native_observation_sha256=sha(native_bytes),cases=len(rows),negative_cases=len(negatives),families=dict(families),resources=resources,metadata=metadata,canonical_inline_count=len(inlines),canonical_motion_cursor_count=len(cursor_resources),native_call_counts=dict(calls),native_branch_paths=[dict(pc=pc,next_pc=next_pc,count=count) for (pc,next_pc),count in sorted(branches.items())],selector8_rectangle_call_counts=dict(rect_counts),shake_clamp_counts=dict(shake_clamps),positive_input_RAM_preserved=True,resource_inputs_unchanged=True,mmio_writes=0,selected_Unicorn_cases=len(secondary),selected_Unicorn_results=secondary,cli_carry_sequences=len(previous),cli_carry_calls=carry,cli_calls_consuming_prior_output=carry-len(previous),directory_loader_source_verified_case=index,results=rows,negative_results=negatives,scope='Original five helpers continuously to RTS in pinned Musashi, all 64 KiB RAM, 12 registers, actual CCR.C, A7+4, zero MMIO, native RAM-write order assertions and unchanged source ROM. All 9 canonical inline conditions and all 108 canonical motion cursors; synthetic raw condition/rectangle/duration live RAM uses identical CPU addresses in both engines, without normalization or ROM patch. Two five-helper and two sixteen-shake actual CLI chains carry entire prior RAM and 12 registers without host rewrites; only entry and call-boundary stack/SR selected. Selected Unicorn full RAM/register comparisons use PC-only hooks with no in-call SR reads; no Unicorn raw carry agreement claim. Duration raw type scanning intentionally remains untyped; API read failures and unknown selectors reject atomically. No natural-frame or cycle-equivalence claim; defensive 1048576 scan cap unexercised because the legal address window fails first.')
    report_path=folder/'verification.json';report_path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),selected_Unicorn_cases=len(secondary),sha256=sha(report_path.read_bytes()))))
if __name__=='__main__':main()
