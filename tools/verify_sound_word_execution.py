"""Compare the complete immutable original 3af8 with the actual full-register CLI.

Unicorn supports the conditional d00046 input; Musashi independently corroborates
fresh nonexternal samples. Pending bytes come from the original stack/D0, never
from a reimplementation of the queue algorithm. CCR is outside this contract.
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
from musashi_oracle import MusashiOracle
from observe_scene_motion_pair import oracle_provenance
from observe_stage_region_frame import KEYS, REGS, BASE, STACK, RETURN
from pack_stage_input import SOURCE_SHA256
ENTRY, WAIT, EXTERNAL = 0x3af8, 0x3aea, 0xd00046


def sha(data): return hashlib.sha256(data).hexdigest()
def put(ram, at, value): struct.pack_into('>H', ram, at, value & 65535)
def word(ram, at): return struct.unpack_from('>H', ram, at)[0]


def fixture(command=0x0866, head=0, tail=0, bytehead=0xffff, bytail=0, oldest=0x0455):
    ram=bytearray(hashlib.shake_256(b'sound-word-full-execution').digest(65536))
    for at in (0x12,0xfd82,0xfe80,0xfd8d,0x4d7e,0xf001,0x4d7b): ram[at]=0
    struct.pack_into('>4H',ram,0x4d82,oldest,0x0566,0x0677,0x0788)
    for at,value in ((0x4d8a,head),(0x4d8c,tail),(0x4d74,bytehead),(0x4d76,bytail)):put(ram,at,value)
    regs=[(0xabc00000+i*0x10203)&0xffffffff for i in range(14)]
    regs[0]=(regs[0]&0xffff0000)|command
    return ram,regs


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert sha(program)==SOURCE_SHA256
    folder=root/'artifacts/sound_word_execution';folder.mkdir(parents=True,exist_ok=True)
    report=folder/'verification.json';report.unlink(missing_ok=True)
    names=('build/execute_sound_word','engine/src/sound_word_execution.cpp','engine/src/sound_byte_execution.cpp','engine/include/ms5/sound_word_execution.h','engine/include/ms5/sound_byte_execution.h','engine/tools/execute_sound_word.cpp','tools/verify_sound_word_execution.py')
    inputs={name:sha((root/name).read_bytes()) for name in names};oracle=oracle_provenance(root)
    cpu=make_cpu(program);cpu.mem_map(0xd00000,4096)
    mu=MusashiOracle();mu.load(0,program[:BASE])
    rows=[];pcs=[];writes=[];reads=[];state={'waits':0,'external':0};corroborated=set()
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
    def args(regs,phase=0,saved=0,external=0,waiting=None):
        return [str(root/'build/execute_sound_word')]+list(map(str,regs))+[str(int(phase!=0) if waiting is None else waiting),str(phase),str(saved),str(external),str(inp),str(out)]
    def compare(ram,regs,phase=0,saved=0,external=0,label='',changes=None):
        if phase==0:
            cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK-64,bytes(64)+RETURN.to_bytes(4,'big'))
            for reg,value in zip(REGS,regs):cpu.reg_write(reg,value)
        else:
            assert [cpu.reg_read(r)&0xffffffff for r in REGS]==regs
            assert cpu.reg_read(m.UC_M68K_REG_PC)==WAIT
        cpu.mem_write(BASE,bytes(ram));pcs.clear();reads.clear();writes.clear();state.update(waits=0,external=external)
        cpu.emu_start(WAIT if phase else ENTRY,0xffffff,count=10000)
        pc=cpu.reg_read(m.UC_M68K_REG_PC);assert pc in (WAIT,RETURN),(label,hex(pc))
        waiting=pc==WAIT;sp=cpu.reg_read(m.UC_M68K_REG_A7)
        expected=bytes(cpu.mem_read(BASE,65536));result={k:cpu.reg_read(r)&0xffffffff for k,r in zip(KEYS,REGS)}
        outphase=0;low=0
        if waiting:
            ret=int.from_bytes(cpu.mem_read(sp,4),'big');outphase={0x3c00:1,RETURN:2}[ret]
            assert sp==(STACK-6 if outphase==1 else STACK)
            low=cpu.mem_read(sp+4,1)[0] if outphase==1 else result['d0']&255
        else:assert sp==STACK+4
        assert cpu.reg_read(m.UC_M68K_REG_A5)==0x108000
        result.update(waiting=waiting,phase=outphase,saved_low=low,external_reads=len(reads))
        replay=bytearray(ram)
        for w in writes:
            at=w['address']-BASE;replay[at:at+w['size']]=w['value'].to_bytes(w['size'],'big')
        assert bytes(replay)==expected and bytes(cpu.mem_read(0,BASE))==program[:BASE]
        if phase:assert not reads and all(x>=0x3ac8 and x<=0x3af6 or x in (0x3c00,0x3c02,RETURN) for x in pcs),(label,pcs)
        inp.write_bytes(ram);p=subprocess.run(args(regs,phase,saved,external),capture_output=True,text=True)
        actual=json.loads(p.stdout) if p.returncode==0 else None
        assert p.returncode==0 and inp.read_bytes()==ram and out.read_bytes()==expected and actual==result,(label,p.stderr,actual,result,[(hex(i),a,b) for i,(a,b) in enumerate(zip(out.read_bytes(),expected)) if a!=b][:20])
        # Native independent sample uses no fabricated external-memory fixture.
        cross=False
        if not phase and not reads and label not in corroborated:
            mu.reset();mu.load(BASE,ram);mu.set_reg('sr',0x2000);mu.set_reg('a5',0x108000);mu.set_reg('a7',STACK);mu.load(STACK-64,bytes(64)+RETURN.to_bytes(4,'big'))
            for k,v in zip(KEYS,regs):mu.set_reg(k,v)
            mu.set_reg('pc',ENTRY)
            for _ in range(2000):
                mp=mu.get_reg('pc')
                if mp==RETURN:break
                if mp==WAIT and mu.get_reg('d1')&65535==int.from_bytes(mu.read(BASE+0x4d74,2),'big'):
                    mu.run(2,RETURN);assert mu.get_reg('pc')==WAIT;break
                mu.run(1,RETURN)
            else:raise AssertionError('Musashi did not return/wait')
            assert mu.read(BASE,65536)==expected and {k:mu.get_reg(k) for k in KEYS}=={k:result[k] for k in KEYS}
            assert mu.get_reg('a5')==0x108000 and mu.get_reg('a7')==sp and mu.get_reg('pc')==pc
            assert mu.read(STACK-64,68)==bytes(cpu.mem_read(STACK-64,68))
            corroborated.add(label);cross=True
        rows.append(dict(label=label,incoming=dict(zip(KEYS,regs),phase=phase,saved_low=saved,external=external),changes=changes or [],result=result,pcs=pcs.copy(),writes=writes.copy(),external_reads=reads.copy(),input_sha256=sha(ram),ram_sha256=sha(expected),musashi_equal=cross))
        return bytearray(expected),[result[k] for k in KEYS],outphase,low
    commands=(0,0x1f,0x20,0xff,0x120,0x220,0x320,0x420,0xfff,0x1000,0x1020,0x1fff,0x2000,0xffff)
    for command,mode,fd82,fe80,fd8d,block,bit5,external in itertools.product(commands,(0,1),(0,1),(0,1),(0,1),(0,1),(0,32),(0,1)):
        ram,regs=fixture(command)
        for at,v in zip((0x12,0xfd82,0xfe80,0xfd8d,0x4d7e,0xf001),(mode,fd82,fe80,fd8d,block,bit5)):ram[at]=v
        compare(ram,regs,external=external,label='all-gate-branches')
    for head,tail,command,high in itertools.product((0,2,4,6),(0,2,4,6),(0x0455,0x0566,0x0677,0x0788,0x0866),(0,0xffff)):
        ram,regs=fixture(command,head,tail);regs[0]=(high<<16)|command;regs[1]=(high<<16)|0x9876
        compare(ram,regs,label='duplicate-swap-append-overflow')
    for value in range(256):
        for oldest in ((value<<8)|0x55,0x5500|value):
            ram,regs=fixture(head=0,tail=6,oldest=oldest);compare(ram,regs,label='all-overflow-high-low-bytes')
    for head,oldest,tail in itertools.product((0,2,4,6),(0,0x0303,0x0355,0x5503),(0,125,127)):
        ram,regs=fixture(head=head,tail=(head+6)&6,bytail=tail)
        put(ram,0x4d82+head,oldest);compare(ram,regs,label='zero-special3-and-byte-wrap')
    for head in (0xb27e,0xfffe,8,10,0x7ffc):
        ram,regs=fixture(head=head,tail=6)
        if head not in (8,10):put(ram,0x4d82+(head if head<32768 else head-65536),0x0866)
        compare(ram,regs,label='signed-initial-head-live-index-alias')
    for tail in (8,10,0xb27e,0xfffe,0x7ffc):
        ram,regs=fixture(head=tail,tail=tail)
        compare(ram,regs,label='signed-append-live-head-tail-alias')
    ram,regs=fixture(head=10,tail=0x0866)
    compare(ram,regs,label='duplicate-swap-overwrites-live-tail')
    for tail in (128,130,0xffff,0xb30c,0x7ffe):
        ram,regs=fixture(head=0,tail=6,bytail=tail)
        compare(ram,regs,label='signed-byte-tail-and-live-byte-index-alias')
    for command in (0,0x1f,0x2000,0xffff):
        ram,regs=fixture(command,head=0xffff,tail=0xffff,bytehead=0x8000,bytail=0x8000)
        compare(ram,regs,label='early-return-bypasses-unused-invalid-indices')
    for head in (0,2,4,6):
        ram,regs=fixture(head=head,tail=(head+6)&6,bytail=0x8000)
        put(ram,0x4d82+head,0)
        compare(ram,regs,label='zero-overflow-bypasses-unused-invalid-byte-tail')
    chains=0
    for target,tail in itertools.product((1,2),(0,125,127)):
        ram,regs=fixture(head=0,tail=6,bytehead=(tail+target)&127,bytail=tail)
        ram,regs,phase,saved=compare(ram,regs,label='wait-start');assert phase==target;chains+=1
        changes=[(0x4d76,0x8000),(0x4d8a,0x8001),(0x4d8c,0xffff),(0x4d82,0xaabb)]
        for at,v in changes:put(ram,at,v)
        ram[0x12]=1;ram[0xfd82]=1;ram[0xfd8d]=0;ram[0x4d7e]=1
        ram,regs,phase,saved=compare(ram,regs,phase,saved,external=255,label='wait-hold-no-gates-or-queue-reread',changes=changes);assert phase==target
        put(ram,0x4d74,0xffff)
        ram,regs,phase,saved=compare(ram,regs,phase,saved,external=255,label='wait-release',changes=[(0x4d74,0xffff)]);assert phase==0
    for tail in (0,127):
        ram,regs=fixture(head=0,tail=6,bytehead=(tail+1)&127,bytail=tail)
        ram,regs,phase,saved=compare(ram,regs,label='sequential-high-low-start');assert phase==1;chains+=1
        for offset,wanted in ((2,2),(4,0)):
            put(ram,0x4d74,(tail+offset)&127)
            ram,regs,phase,saved=compare(ram,regs,phase,saved,label='sequential-high-low-resume');assert phase==wanted
    negatives=[]
    def reject(ram,regs,phase=0,saved=0,external=0,waiting=None,label='',command=None):
        inp.write_bytes(ram);out.write_bytes(b'preserved\0\xff')
        p=subprocess.run(command or args(regs,phase,saved,external,waiting),capture_output=True,text=True)
        assert p.returncode and not p.stdout and inp.read_bytes()==ram and out.read_bytes()==b'preserved\0\xff',(label,p.stderr)
        negatives.append(dict(label=label,input_and_output_preserved=True,native_executed=False))
    ram,regs=fixture()
    for size in (0,65535,65537):reject(bytes(size),regs,label='invalid-RAM-size')
    for index in range(14):
        for bad in ('-1','4294967296','0x','1x',''):
            r=regs.copy();r[index]=bad;reject(ram,r,label='invalid-register-parser')
    for index,values in ((15,('-1','2','')),(16,('-1','3','')),(17,('-1','256','')),(18,('-1','256',''))):
        for value in values:
            command=args(regs);command[index]=value;reject(ram,regs,label='invalid-state-parser',command=command)
    for phase,saved,waiting in ((0,0,1),(1,0,0),(2,0,0)):
        reject(ram,regs,phase,saved,waiting=waiting,label='inconsistent-captured-state')
    for at,value in ((0x4d8a,1),(0x4d8a,0x8000),(0x4d8c,1),(0x4d8c,8)):
        bad,r=fixture();put(bad,at,value);reject(bad,r,label='invalid-word-index-or-nonterminating-tail')
    bad,r=fixture(head=0,tail=6,bytail=0x8000);reject(bad,r,label='overflow-byte-write-outside-RAM')
    for phase in (1,2):
        bad,r=fixture();r[8]=0x110000;r[1]=(r[1]&0xffff0000)|1
        reject(bad,r,phase,0x55,waiting=1,label='captured-byte-write-outside-RAM')
    for kind in ('same','hardlink','symlink'):

        inp.write_bytes(ram);alias=inp if kind=='same' else folder/('alias-'+kind)
        if kind!='same':
            alias.unlink(missing_ok=True)
            if kind=='hardlink':alias.hardlink_to(inp)
            else:alias.symlink_to(inp)
        command=args(regs);command[-1]=str(alias);p=subprocess.run(command,capture_output=True,text=True)
        assert p.returncode and not p.stdout and inp.read_bytes()==ram
        negatives.append(dict(label='input-output-'+kind+'-alias',input_and_output_preserved=True,native_executed=False))
    instructions=disassemble_range(program,ENTRY,0x3c08-ENTRY,ENTRY)+disassemble_range(program,0x3ac8,0x30,0x3ac8)
    conditional=[x['cpu_address'] for x in instructions if x['mnemonic'].startswith('b') and x['mnemonic'].split('.')[0] not in ('bra','bsr','btst')]
    branches=collections.defaultdict(set)
    for row in rows:
        for a,b in zip(row['pcs'],row['pcs'][1:]):
            if a in conditional:branches[a].add(b)
    assert all(len(branches[a])==2 for a in conditional),{hex(a):sorted(branches[a]) for a in conditional if len(branches[a])!=2}
    assert inputs=={name:sha((root/name).read_bytes()) for name in names} and oracle_provenance(root)==oracle
    report.write_text(json.dumps(dict(source=source,inputs=inputs,oracle=dict(unicorn=unicorn.__version__,musashi=oracle),instructions=instructions,cases=len(rows),negative_cases=negatives,chains=chains,branches={hex(a):sorted(v) for a,v in branches.items()},musashi_samples=len(corroborated),results=rows,scope='Immutable original full3af8 and3aea continuation vs actualCLI; full64KiBRAM,14registers,pending,conditionalexternalreads; A5,A7,andoriginalstack verified. Synthetichostrelease only; no naturalIRQ/scheduler claim. CCR/MMIO audio consumption excluded. No native fixture permits ROMwrites.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),musashi_samples=len(corroborated),sha256=sha(report.read_bytes()))))

if __name__=='__main__':main()
