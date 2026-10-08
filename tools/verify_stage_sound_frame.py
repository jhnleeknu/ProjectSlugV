"""Immutable original 2efa6 and helpers vs actual CLI; original CPU persists on waits.
No in-call SR hooks or fabricated helper stubs. CCR remains outside the contract.
"""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, m68k_const as m
from disassemble_program import load_verified_program, disassemble_range
from verify_object_reset import make_cpu
from observe_scene_frame_execution import oracle_provenance
from observe_stage_region_frame import KEYS, REGS, BASE, STACK, RETURN
from pack_stage_input import SOURCE_SHA256
ENTRY, WAIT, EXTERNAL = 0x2efa6, 0x3aea, 0xd00046


def sha(data): return hashlib.sha256(data).hexdigest()
def put(ram, at, value): struct.pack_into('>H', ram, at, value & 65535)
def word(ram, at): return struct.unpack_from('>H', ram, at)[0]


def fixture(command=0x0866, head=0, tail=0, bytehead=0xffff, bytail=0, oldest=0x0455):
    ram=bytearray(hashlib.shake_256(b'stage-sound-frame').digest(65536))
    for at in (0x12,0xfd82,0xfe80,0xfd8d,0x4d7e,0xf001,0x4d7b): ram[at]=0
    struct.pack_into('>4H',ram,0x4d82,oldest,0x0566,0x0677,0x0788)
    for at,value in ((0x4d8a,head),(0x4d8c,tail),(0x4d74,bytehead),(0x4d76,bytail)):put(ram,at,value)
    ram[0xd490]=1;ram[0xd491]=0
    regs=[(0xabc00000+i*0x10203)&0xffffffff for i in range(14)]
    regs[0]=(regs[0]&0xffff0000)|command
    return ram,regs


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert sha(program)==SOURCE_SHA256
    folder=root/'artifacts/stage_sound_frame';folder.mkdir(parents=True,exist_ok=True)
    report=folder/'verification.json';report.unlink(missing_ok=True)
    names=('build/step_stage_sound_frame','engine/src/stage_sound_frame.cpp','engine/src/sound_word_execution.cpp','engine/src/sound_cancel_execution.cpp','engine/src/sound_byte_execution.cpp','engine/include/ms5/stage_sound_frame.h','engine/include/ms5/sound_word_execution.h','engine/include/ms5/sound_cancel_execution.h','engine/include/ms5/sound_byte_execution.h','engine/tools/step_stage_sound_frame.cpp','tools/verify_stage_sound_frame.py')
    inputs={name:sha((root/name).read_bytes()) for name in names};oracle=oracle_provenance()
    cpu=make_cpu(program);cpu.mem_map(0xd00000,4096)
    rows=[];pcs=[];writes=[];reads=[];state={'waits':0,'external':0}
    def code(c,address,size,user):
        pcs.append(address)
        if address==RETURN:c.emu_stop()
        elif address==WAIT:
            if int.from_bytes(c.mem_read(BASE+0x4d74,2),'big')==(c.reg_read(m.UC_M68K_REG_D1)&65535):
                state['waits']+=1
                if state['waits']==2:c.emu_stop()
            else:state['waits']=0
    def read(c,access,address,size,value,user):
        assert address==EXTERNAL and size==1
        c.mem_write(address,bytes([state['external']]));reads.append(dict(address=address,size=size,value=state['external']))
    def write(c,access,address,size,value,user):
        assert BASE<=address and address+size<=BASE+65536 or STACK-64<=address and address+size<=STACK+4,(hex(address),size,value)
        if BASE<=address<BASE+65536:writes.append(dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=value&((1<<(8*size))-1)))
    cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_READ,read,begin=EXTERNAL,end=EXTERNAL);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    inp,out=folder/'input.bin',folder/'cpp.bin'
    def args(regs,kind=0,phase=0,saved=0,external=0,waiting=None):
        return [str(root/'build/step_stage_sound_frame')]+list(map(str,regs))+[str(int(kind!=0) if waiting is None else waiting),str(kind),str(phase),str(saved),str(external),str(inp),str(out)]
    def compare(ram,regs,kind=0,phase=0,saved=0,external=0,label='',changes=None):
        if kind==0:
            cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK-64,bytes(64)+RETURN.to_bytes(4,'big'))
            for reg,value in zip(REGS,regs):cpu.reg_write(reg,value)
        else:
            assert [cpu.reg_read(r)&0xffffffff for r in REGS]==regs
            assert cpu.reg_read(m.UC_M68K_REG_PC)==WAIT
        cpu.mem_write(BASE,bytes(ram));pcs.clear();reads.clear();writes.clear();state.update(waits=0,external=external)
        cpu.emu_start(WAIT if kind else ENTRY,0xffffff,count=10000)
        pc=cpu.reg_read(m.UC_M68K_REG_PC);assert pc in (WAIT,RETURN),(label,hex(pc))
        waiting=pc==WAIT;sp=cpu.reg_read(m.UC_M68K_REG_A7)
        expected=bytes(cpu.mem_read(BASE,65536));result={k:cpu.reg_read(r)&0xffffffff for k,r in zip(KEYS,REGS)}
        outkind=0;outphase=0;pending=0
        if waiting:
            ret=int.from_bytes(cpu.mem_read(sp,4),'big')
            if ret==0x3c00:outkind,outphase=1,1
            elif ret==0x2efc8:outkind,outphase=1,2
            elif ret==0x3c70:outkind,outphase=2,1
            elif ret==0x3c76:outkind,outphase=2,2
            elif ret==0x2efda:outkind,outphase=2,3
            else:raise AssertionError(('unexpected wait stack',hex(ret)))
            stacked=(outkind==1 and outphase==1) or (outkind==2 and outphase<3)
            assert sp==(STACK-10 if stacked else STACK-4)
            if outkind==1:pending=cpu.mem_read(sp+4,1)[0] if stacked else result['d0']&255
            else:pending=int.from_bytes(cpu.mem_read(sp+4,2),'big') if stacked else result['d0']&65535
            outer=int.from_bytes(cpu.mem_read(STACK-4,4),'big')
            assert outer=={1:0x2efc8,2:0x2efda}[outkind]
        else:assert sp==STACK+4
        assert cpu.reg_read(m.UC_M68K_REG_A5)==0x108000
        result.update(waiting=waiting,kind=outkind,phase=outphase,saved=pending,external_reads=len(reads))
        replay=bytearray(ram)
        for w in writes:
            at=w['address']-BASE;replay[at:at+w['size']]=w['value'].to_bytes(w['size'],'big')
        assert bytes(replay)==expected and bytes(cpu.mem_read(0,BASE))==program[:BASE]
        if kind:
            assert not reads and not any(0x2efa6<=x<0x2efc8 or 0x2efca<=x<0x2efda for x in pcs),(label,pcs)
            assert not any(x['address']==BASE+0xd491 for x in writes)
        inp.write_bytes(ram);p=subprocess.run(args(regs,kind,phase,saved,external),capture_output=True,text=True)
        actual=json.loads(p.stdout) if p.returncode==0 else None
        assert p.returncode==0 and inp.read_bytes()==ram and out.read_bytes()==expected and actual==result,(label,p.stderr,actual,result,[(hex(i),a,b) for i,(a,b) in enumerate(zip(out.read_bytes(),expected)) if a!=b][:20])
        rows.append(dict(label=label,incoming=dict(zip(KEYS,regs),kind=kind,phase=phase,saved=saved,external=external),changes=changes or [],result=result,pcs=pcs.copy(),writes=writes.copy(),external_reads=reads.copy(),input_sha256=sha(ram),ram_sha256=sha(expected)))
        return bytearray(expected),[result[k] for k in KEYS],outkind,outphase,pending
    # Exhaust each frame BYTE input independently, including noncanonical nonzero values.
    for previous,current in sorted(set(itertools.chain(itertools.product(range(256),(0,1,0x80,0xff)),itertools.product((0,1,0x80,0xff),range(256))))):
        ram,regs=fixture();ram[0xd490]=current;ram[0xd491]=previous
        compare(ram,regs,label='all-prior-current-BYTE-values')
    for mode,fd82,fe80,fd8d,block,bit5,external in itertools.product((0,1,2),(0,1),(0,1),(0,1),(0,1),(0,32),(0,1)):
        ram,regs=fixture()
        for at,v in zip((0x12,0xfd82,0xfe80,0xfd8d,0x4d7e,0xf001),(mode,fd82,fe80,fd8d,block,bit5)):ram[at]=v
        compare(ram,regs,external=external,label='rising-all-reachable-gates')
    for current,previous,head,tail,duplicate in itertools.product((0,1),(1,0),(0,2,4,6),(0,2,4,6),(False,True)):
        ram,regs=fixture(head=head,tail=tail);ram[0xd490]=current;ram[0xd491]=previous
        if duplicate:put(ram,0x4d82+head,0x1d28)
        compare(ram,regs,label='transition-queue-duplicate-cancel-overflow')
    for oldest,bytail in itertools.product((0,0x0303,0x0355,0x5503,0x0455),(0,125,127)):
        ram,regs=fixture(head=0,tail=6,oldest=oldest,bytail=bytail)
        compare(ram,regs,label='word-overflow-zero-special3-wrap')
    for rising,index in itertools.product((False,True),(0xb27e,0xfffe,8,10,0x7ffc)):
        ram,regs=fixture(head=index,tail=6);ram[0xd490]=int(rising);ram[0xd491]=int(not rising)
        compare(ram,regs,label='signed-initial-index-alias')
    for index in (8,10,0xb27e,0xfffe,0x7ffc):
        ram,regs=fixture(head=index,tail=index)
        compare(ram,regs,label='word-append-live-head-tail-alias')
    chains=0;pending_seen=set()
    for rising,target,bytail in itertools.product((False,True),(1,2,3),(0,125,127)):
        if rising and target==3:continue
        ram,regs=fixture(head=0,tail=6,bytehead=(bytail+target)&127,bytail=bytail)
        ram[0xd490]=int(rising);ram[0xd491]=int(not rising)
        ram,regs,kind,phase,saved=compare(ram,regs,label='wait-start')
        assert kind==(1 if rising else 2) and phase==target
        pending_seen.add((kind,phase));chains+=1
        changes=[]
        for at,value in ((0x4d76,0x8000),(0x4d8a,0x8001),(0x4d8c,0xffff),(0x4d82,0xaabb)):
            put(ram,at,value);changes.append(dict(ram_offset=at,size=2,value=value))
        for at,value in ((0xd490,0 if rising else 0xff),(0xd491,0x71),(0x12,1),(0xfd82,1),(0xfd8d,0),(0x4d7e,1)):
            ram[at]=value;changes.append(dict(ram_offset=at,size=1,value=value))
        ram,regs,kind,phase,saved=compare(ram,regs,kind,phase,saved,external=255,label='wait-hold-with-mutated-frame-and-queues',changes=changes)
        assert phase==target and ram[0xd491]==0x71
        put(ram,0x4d74,0xffff)
        ram,regs,kind,phase,saved=compare(ram,regs,kind,phase,saved,external=255,label='wait-release',changes=[dict(ram_offset=0x4d74,size=2,value=0xffff)])
        assert kind==0 and phase==0 and ram[0xd491]==0x71
    for rising,bytail in itertools.product((False,True),(0,127)):
        ram,regs=fixture(head=0,tail=6,bytehead=(bytail+1)&127,bytail=bytail)
        ram[0xd490]=int(rising);ram[0xd491]=int(not rising)
        ram,regs,kind,phase,saved=compare(ram,regs,label='sequential-all-submissions-start');assert phase==1;chains+=1
        count=2 if rising else 3
        for offset in range(2,count+2):
            put(ram,0x4d74,(bytail+offset)&127)
            ram,regs,kind,phase,saved=compare(ram,regs,kind,phase,saved,label='sequential-submission-release',changes=[dict(ram_offset=0x4d74,size=2,value=(bytail+offset)&127)])
            assert phase==(offset if offset<=count else 0)
    assert pending_seen=={(1,1),(1,2),(2,1),(2,2),(2,3)}
    negatives=[]
    def reject(ram,regs,kind=0,phase=0,saved=0,external=0,waiting=None,label='',command=None):
        inp.write_bytes(ram);out.write_bytes(b'preserved\0\xff')
        p=subprocess.run(command or args(regs,kind,phase,saved,external,waiting),capture_output=True,text=True)
        assert p.returncode and not p.stdout and inp.read_bytes()==ram and out.read_bytes()==b'preserved\0\xff',(label,p.stderr)
        negatives.append(dict(label=label,input_and_output_preserved=True,native_executed=False))
    ram,regs=fixture()
    for size in (0,65535,65537):reject(bytes(size),regs,label='invalid-RAM-size')
    for index in range(14):
        for bad in ('-1','4294967296','0x','1x',''):
            r=regs.copy();r[index]=bad;reject(ram,r,label='invalid-register-parser')
    for index,values in ((15,('-1','2','')),(16,('-1','3','')),(17,('-1','4','')),(18,('-1','65536','')),(19,('-1','256',''))):
        for value in values:
            command=args(regs);command[index]=value;reject(ram,regs,label='invalid-state-parser',command=command)
    for kind,phase,saved,waiting in ((0,0,0,1),(0,1,0,0),(1,0,0,1),(1,3,0,1),(1,1,256,1),(2,0,0,1),(1,1,0,0),(2,1,0,0)):
        reject(ram,regs,kind,phase,saved,waiting=waiting,label='inconsistent-captured-state')
    for rising in (False,True):
        for at,value in ((0x4d8a,1),(0x4d8a,0x8000),(0x4d8c,1),(0x4d8c,8)):
            bad,r=fixture();bad[0xd490]=int(rising);bad[0xd491]=int(not rising);put(bad,at,value)
            reject(bad,r,label='invalid-word-index-or-nonterminating-tail')
    for kind,phase in sorted(pending_seen):
        bad,r=fixture();r[8]=0x110000;r[1]=(r[1]&0xffff0000)|1
        reject(bad,r,kind,phase,0x55,waiting=1,label='captured-byte-write-outside-RAM')
    for alias_kind in ('same','hardlink','symlink'):
        inp.write_bytes(ram);alias=inp if alias_kind=='same' else folder/('alias-'+alias_kind)
        if alias_kind!='same':
            alias.unlink(missing_ok=True)
            if alias_kind=='hardlink':alias.hardlink_to(inp)
            else:alias.symlink_to(inp)
        command=args(regs);command[-1]=str(alias);p=subprocess.run(command,capture_output=True,text=True)
        assert p.returncode and not p.stdout and inp.read_bytes()==ram
        negatives.append(dict(label='input-output-'+alias_kind+'-alias',input_and_output_preserved=True,native_executed=False))
    instructions=disassemble_range(program,ENTRY,0x2efdc-ENTRY,ENTRY)+disassemble_range(program,0x3af8,0x3c08-0x3af8,0x3af8)+disassemble_range(program,0x3c44,0x3c7c-0x3c44,0x3c44)+disassemble_range(program,0x3ac8,0x30,0x3ac8)
    conditional=[x['cpu_address'] for x in instructions if x['mnemonic'].startswith('b') and x['mnemonic'].split('.')[0] not in ('bra','bsr','btst')]
    branches=collections.defaultdict(set)
    for row in rows:
        for a,b in zip(row['pcs'],row['pcs'][1:]):
            if a in conditional:branches[a].add(b)
    frame_branches=[a for a in conditional if a>=ENTRY]
    assert all(len(branches[a])==2 for a in frame_branches),{hex(a):sorted(branches[a]) for a in frame_branches}
    assert inputs=={name:sha((root/name).read_bytes()) for name in names} and oracle_provenance()==oracle
    report.write_text(json.dumps(dict(source=source,inputs=inputs,oracle=oracle,instructions=instructions,cases=len(rows),negative_cases=negatives,chains=chains,pending_states=sorted(pending_seen),branches={hex(a):sorted(branches[a]) for a in conditional},full_frame_branch_coverage=True,results=rows,scope='Immutable original 2efa6 and full helpers vs actual CLI; full64KiBRAM,14registers,pending,conditionalexternalreads; A5,A7,and original waitstack verified. SameCPU across resumes. Synthetic host release only; no naturalIRQ/scheduler claim. CCR and audio consumption excluded. No native fixture permits ROMwrites. Helper gates unreachable from fixed command1d28 are reported without claiming full helper branch coverage.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),chains=chains,sha256=sha(report.read_bytes()))))

if __name__=='__main__':main()
