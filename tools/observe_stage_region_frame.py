"""Five original region-frame entries: Musashi primary, banked Unicorn calls."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct
from disassemble_program import load_verified_program
from musashi_oracle import MusashiOracle
from observe_scene_motion_pair import oracle_provenance
from observe_scene_frame_execution import oracle_provenance as unicorn_provenance
from verify_object_reset import make_cpu
from inventory_stage_region_frame import inventory
from pack_stage_input import SOURCE_SHA256
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ,UC_HOOK_INTR,m68k_const as m
BASE,STACK,RETURN=0x100000,0x1feffc,0xff000
KEYS=tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(5))+('a6',)
REGS=tuple(getattr(m,'UC_M68K_REG_'+k.upper()) for k in KEYS)
ENTRIES=(0x49392,0x4d9d6,0x1c028,0xb481e,0xb4a2a)
BRANCHES=(0x49398,0x493a6,0x493b2,0x4d9dc,0x4d9e6,0x4d9f8,0x1c036,0x1c044,0xb4826,0xb4842,0xb4a38,0xb4a48,0xb4a6c,0xb4a7c,0xb4a98,0xb4aa2)
def sha(data):return hashlib.sha256(data).hexdigest()
def resources(root):
    audit=inventory(root);assert json.loads((root/'artifacts/stage_region_frame_inventory.json').read_text())==json.loads(json.dumps(audit));return audit['resource_audit']['resource_read_fixtures']
def provenance(root):
    names=('build/step_stage_region_frame','engine/src/stage_region_frame.cpp','engine/include/ms5/stage_region_frame.h','engine/tools/step_stage_region_frame.cpp','engine/src/fixed_data_resource.cpp','engine/include/ms5/fixed_data_resource.h','engine/include/ms5/scene_map_transfer.h','tools/observe_stage_region_frame.py','tools/verify_stage_region_frame.py','tools/inventory_stage_region_frame.py','artifacts/stage_region_frame_inventory.json')
    rows=[dict(file=p,sha256=sha((root/p).read_bytes())) for p in names]
    for r in resources(root):assert sha((root/r['file']).read_bytes())==r['container_sha256'];rows.append(dict(file=r['file'],sha256=r['container_sha256']))
    rows+=inventory(root)['provenance']
    return rows
def build_cases():
    cases=[]
    def add(family,entry,**kw):
        c=dict(family=family,entry=entry,profile=1,d0=0,a6=0x106f01,bank=2,carry=0,activity=3,active=[1,1],lows=[0xcb8,0xda8],source_roles=['RAM','RAM'],source_null=[False,False],coords=[[0,0],[0,0]],raw_words=[[0x7fff,0x8000,0xffff,0],[1,2,3,4]],timers=[0,0],parity=0,alias=None);c.update(kw);cases.append(c)
    for d0,mask,carry in itertools.product((0,1,2,3,0x100,0x101,0x8000,0x8001,0xabcdfffe,0xffff0001),(0,1,2,3,0xfc,0xfd,0xfe,0xff),range(2)):add('activity-bit-memory-BYTE-input-lowbit',0x49392,d0=d0,activity=mask,carry=carry,profile=carry)
    for entry,d0,active,low,a6 in itertools.product((0x4d9d6,0x1c028),(0,1,2,0x100,0x101,0xabcdef02),(0,1,0x8000),(0,1,0xcb8,0xffff),(0x106f01,0xffff1234,0x12345678)):
        add('pointer-highA6-active-null-low-and-selection-disagreement',entry,d0=d0,active=[active,active],lows=[low,low],a6=a6,carry=(low+active)&1)
    for parity,profile in itertools.product((0,1,2,0x7fff,0x8000,0xffff),range(2)):add('six-WORD-parity-clear-and-preserved-registers',0xb481e,parity=parity,profile=profile,carry=profile)
    for mask,active,null,coords in itertools.product((0,1,2,3,0xff),((0,0),(1,1),(0,1),(1,0)),((False,False),(True,False),(False,True),(True,True)),(((0,0),(0,0)),((1,0xffff),(0x8000,0x7fff)))):
        add('fullframe-mask-null-source-signextend-WORD-wrap',0xb4a2a,activity=mask,active=list(active),source_null=list(null),coords=[list(x) for x in coords],carry=mask&1,parity=mask,timers=[mask%2,0xff if mask&1 else 0])
    for timers,parity in itertools.product(itertools.product((0,1,0xff),repeat=2),(0,1)):add('fullframe-timers-0-1-ff-and-parity',0xb4a2a,timers=list(timers),parity=parity,activity=0)
    for alias in ('second-source-first-publication','second-coordinates-first-publication','both-object-same','first-source-second-sentinel','second-source-own-sentinel'):
        add('fullframe-live-'+alias,0xb4a2a,alias=alias)
    for role,bank,player in itertools.product(('fixed','bank2','bank3'),(2,3),(0,1)):
        if role.startswith('bank') and int(role[-1])!=bank:continue
        roles=['RAM','RAM'];roles[player]=role;add('fullframe-raw-source-window',0xb4a2a,source_roles=roles,bank=bank,coords=[[0xffff,1],[1,0xffff]],carry=player,parity=player)
    for step in range(6):add('actual-CLI-fullframe-output-chain',0xb4a2a,sequence='frame',sequence_position=step,timers=[0xff,1],parity=1)
    assert len(cases)==801
    return cases

def fixture(c,rs):
    ram=bytearray(hashlib.shake_256(b'stage-region-frame'+bytes([c['profile']])).digest(65536));regs=[0]*14 if not c['profile'] else [(0x89abcdef+i*0x1020304)&0xffffffff for i in range(14)];regs[0]=c['d0'];regs[13]=c['a6'];ram[0xd68e]=c['activity'];ram[0xdd58],ram[0xdd5a]=c['timers'];struct.pack_into('>H',ram,0x000e,c['parity'])
    sources=[0x106000,0x106010];lows=c['lows'].copy()
    for player in range(2):
        role=c['source_roles'][player]
        if role=='RAM':struct.pack_into('>4H',ram,sources[player]-BASE,*c['raw_words'][player])
        else:sources[player]=next(r['source_cpu_address'] for r in rs if r['role']==role)
        if c['source_null'][player]:sources[player]=0
    if c['alias']=='second-source-first-publication':sources[1]=0x10dd48
    if c['alias']=='second-coordinates-first-publication':lows[1]=0xdd06
    if c['alias']=='second-source-own-sentinel':sources[1]=0x10dd50
    if c['alias']=='both-object-same':lows[1]=lows[0]
    if c['alias']=='first-source-second-sentinel':sources[0]=0x10dd50
    for player in range(2):
        obj=0x100000+lows[player]
        # Helpers may return arbitrary opaque A0; only valid full-frame objects
        # are seeded/dereferenced by the native corpus.
        if BASE<=obj and obj+0x5a<=BASE+65536:
            struct.pack_into('>H',ram,obj-BASE+0x42,c['coords'][player][0]);struct.pack_into('>H',ram,obj-BASE+0x46,c['coords'][player][1])
        default=0xcb8+player*0xf0;struct.pack_into('>I',ram,default+0x56,sources[player]);struct.pack_into('>H',ram,default+0x42,c['coords'][player][0]);struct.pack_into('>H',ram,default+0x46,c['coords'][player][1])
        at=0xdcba+player*0x2c;struct.pack_into('>H',ram,at,c['active'][player]);struct.pack_into('>HI',ram,at+6,lows[player],sources[player])
    return ram,regs
class Observer:
    def __init__(self,program,banked=False):
        self.program=program;self.banked=banked;self.pcs=[];self.writes=[];self.movem=[];self.bank_reads=[];self.error=None;self.bank=2
        if not banked:
            self.cpu=MusashiOracle();self.cpu.load(0,program[:BASE])
            def code(pc):self.record(pc)
            def write(pc,address,size,value):self.write(pc,address,size,value)
            self.cpu.set_instruction_hook(code);self.cpu.set_write_hook(write)
        else:
            self.cpu=make_cpu(program);self.cpu.mem_map(0x200000,0x100000);self.baseline=self.cpu.context_save()
            def code(cpu,pc,size,user):
                if pc==RETURN:cpu.emu_stop();return
                self.record(pc)
            def write(cpu,access,address,size,value,user):self.write(cpu.reg_read(m.UC_M68K_REG_PC),address,size,value)
            def read(cpu,access,address,size,value,user):
                if 0x200000<=address<0x300000:self.bank_reads.append(dict(pc=cpu.reg_read(m.UC_M68K_REG_PC),address=address,size=size,bank=self.bank))
            def intr(cpu,n,user):self.error=(n,cpu.reg_read(m.UC_M68K_REG_PC));cpu.emu_stop()
            self.cpu.hook_add(UC_HOOK_CODE,code);self.cpu.hook_add(UC_HOOK_MEM_WRITE,write);self.cpu.hook_add(UC_HOOK_MEM_READ,read);self.cpu.hook_add(UC_HOOK_INTR,intr)
    def reg(self,k):return self.cpu.reg_read(getattr(m,'UC_M68K_REG_'+k.upper()))&0xffffffff if self.banked else self.cpu.get_reg(k)
    def read(self,a,n):return bytes(self.cpu.mem_read(a,n)) if self.banked else self.cpu.read(a,n)
    def record(self,pc):
        self.pcs.append(pc)
        if pc in (0xb4a50,0xb4a84):self.movem.append(dict(pc=pc,registers=[self.reg('d'+str(i)) for i in range(4)],object=self.reg('a0'),source=self.reg('a1'),coordinate_words=[int.from_bytes(self.read(self.reg('a0')+off,2),'big') for off in (0x42,0x46)]))
        op=int.from_bytes(self.read(pc,2),'big');assert op!=0x4afc and not 0x4e40<=op<=0x4e4f,(pc,op)
    def write(self,pc,address,size,value):
        assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(pc,address,size,value)
        if BASE<=address<BASE+65536:self.writes.append(dict(pc=pc,address=address,size=size,value=value&((1<<(8*size))-1)))
    def run(self,c,ram,regs):
        self.pcs.clear();self.writes.clear();self.movem.clear();self.bank_reads.clear();self.error=None;self.bank=c['bank'];cpu=self.cpu
        if self.banked:
            cpu.context_restore(self.baseline);cpu.mem_write(BASE,bytes(ram));cpu.mem_write(0x200000,self.program[self.bank*0x100000:self.bank*0x100000+0xffff0]);cpu.reg_write(m.UC_M68K_REG_SR,0x2000|c['carry']);cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
            for r,v in zip(REGS,regs):cpu.reg_write(r,v)
            cpu.emu_start(c['entry'],0xffffff,count=20000);assert not self.error and self.reg('pc')==RETURN and self.reg('a7')==STACK+4
            assert self.read(0x200000,0xffff0)==self.program[self.bank*0x100000:self.bank*0x100000+0xffff0]
        else:
            cpu.reset();cpu.load(BASE,ram);cpu.set_reg('sr',0x2000|c['carry']);cpu.set_reg('a5',0x108000);cpu.set_reg('a7',STACK);cpu.load(STACK,RETURN.to_bytes(4,'big'))
            for k,v in zip(KEYS,regs):cpu.set_reg(k,v)
            cpu.set_reg('pc',c['entry']);status=cpu.run(20000,RETURN);assert status['status']=='sentinel' and self.reg('a7')==STACK+4,status
        assert self.read(0,BASE)==self.program[:BASE];result={k:self.reg(k) for k in KEYS};result.update(bank=c['bank'],carry=bool(self.reg('sr')&1) if c['entry']==0x49392 else bool(c['carry']))
        return self.read(BASE,65536),result,dict(final_pc=RETURN,final_a7=STACK+4,pcs=self.pcs.copy(),RAM_writes=self.writes.copy(),MOVEM_W_snapshots=self.movem.copy(),banked_reads=self.bank_reads.copy(),mmio_writes=0,oracle='Unicorn2.1.4' if self.banked else 'pinnedMusashiM68000')
def branch_counts(rows):
    counts=collections.defaultdict(collections.Counter)
    for row in rows:
        pcs=row['pcs']+[RETURN]
        for p,n in zip(pcs,pcs[1:]):
            if p in BRANCHES:counts[p][n]+=1
    return {hex(p):{hex(n):v for n,v in b.items()} for p,b in counts.items()}
def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;inputs,oracle,secondary=provenance(root),oracle_provenance(root),unicorn_provenance();rs=resources(root);folder=root/'artifacts/stage_region_frame';folder.mkdir(parents=True,exist_ok=True);cases=build_cases();primary=Observer(program);banked=Observer(program,True);previous=None;rows=[]
    for i,c in enumerate(cases):
        ram,regs=fixture(c,rs) if not c.get('sequence_position',0) else (bytearray(previous[0]),list(previous[1]));observer=banked if any(r.startswith('bank') for r in c['source_roles']) else primary;out,result,info=observer.run(c,ram,regs);assert result['a6']==regs[13]
        if 'sequence'in c:previous=(out,[result[k] for k in KEYS])
        file='native_%04d.bin'%i;(folder/file).write_bytes(out);rows.append(dict(case_index=i,fixture=c,input_ram_sha256=sha(ram),incoming=dict(zip(KEYS,regs)),result=result,ram_file=file,ram_sha256=sha(out),**info))
    assert provenance(root)==inputs and oracle_provenance(root)==oracle and unicorn_provenance()==secondary and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report=dict(source=source,oracle=oracle,banked_oracle=secondary,inputs=inputs,cases=len(cases),results=rows,branch_successor_counts=branch_counts(rows),failure=None,program_code_modified=False,physical_bank_payload_modified=False,in_call_SR_read=False,scope='Five original calls uninterrupted to RTS in pinnedMusashiM68000; banked-source fullcalls separately run Unicorn2.1.4 actualimmutablebankmapping. FullRAM14regs/bank and only49392actualfinalcarry; otherentries preserve separateAPIcarry, notwholeCCR. No ROMpatch/stub/calleereset/SRhookread/MMIO. Limitedraw8bytes from existingresources are not logicalrecords/naturalusage. Six fullframeCLI output-carry fixtures have no host rewrites.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),sha256=sha(path.read_bytes()))))
if __name__=='__main__':main()
