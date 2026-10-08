"""Whole original e8a48 calls and same-CPU sprite wait resumes."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct
from disassemble_program import load_verified_program
from musashi_oracle import MusashiOracle
from observe_scene_motion_pair import oracle_provenance
from inventory_stage_cue_frame import inventory
from pack_stage_cue_control import build as control_build, SOURCE_SHA256
BASE,STACK,RETURN,WAIT_PC=0x100000,0x1feffc,0xff000,0xcda4
KEYS=tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(5))+('a6',)
BRANCHES=(0xe8a4c,0xe8a66,0xe8ab2,0xe8aca,0xe8b26,0xe8b42,0xe8ad8,0xe8ae4,0xe8b00,0xe8b0e,0x28ba,0x28c2,0x28d6,0x43e52,0x43e82,0xcd66,0xcd78,0xcd94,0xcda0,0xcda8,0xcdb2)
def sha(data):return hashlib.sha256(data).hexdigest()
def resource_audit(root):
    from pack_stage_cue_frame import build
    rows=[]
    for builder,folder in ((build,'stage_cue_frame'),(control_build,'stage_cue_control')):
        files,manifest=builder(root)
        for name,data in files.items():
            path=root/'extracted/runtime'/folder/name;assert path.read_bytes()==data;rows.append(dict(file=str(path.relative_to(root)),sha256=sha(data)))
    return rows

def provenance(root):
    names=('build/step_stage_cue_frame','engine/src/stage_cue_frame.cpp','engine/include/ms5/stage_cue_frame.h','engine/tools/step_stage_cue_frame.cpp','engine/src/stage_cue_control.cpp','engine/src/object_allocation.cpp','engine/src/scene_node.cpp','engine/src/sprite_submit_execution.cpp','engine/src/fixed_data_resource.cpp','tools/observe_stage_cue_frame.py','tools/verify_stage_cue_frame.py','tools/pack_stage_cue_frame.py','tools/pack_stage_cue_control.py','tools/inventory_stage_cue_frame.py')
    return [dict(file=n,sha256=sha((root/n).read_bytes())) for n in names]+resource_audit(root)
def build_cases(root):
    audited=inventory(root);p=root/'artifacts/stage_cue_frame_inventory.json';assert json.loads(p.read_text())==json.loads(json.dumps(audited));catalog=audited['catalog_cue_pointer_inventory'];roots=catalog['roots'];assert len(roots)==42
    cases=[]
    def add(family,**kw):
        c=dict(family=family,profile=1,tag=0x1c,cue=0x106000,allocate=1,manual=1,debug=0,x=0,y=0x40,flags=0,camera_x=0,camera_y=0,offset_x=0,offset_y=0,count=4,depth=0,original=0x106100,node=0x100400,successor=0x100800,stream=0x106200,phase=0,gates=[0,1,2,0x7fff,0xffff],producer=0,consumer=0x100,prepared=0x80,normal=0,offset=12,pending=False);c.update(kw);cases.append(c)
    for tag,profile in itertools.product(range(256),range(2)):add('all256-tags-exact32-allocation-index',tag=tag,profile=profile,count=0 if profile==0 else 4)
    for flags,xy,camera,count in itertools.product(range(4),((0,0),(0x7fff,0x8000),(0xffff,1)),((0,0),(1,0xffff)),(0,4)):add('allocated-XY-flags-WORD-wrap-fallback',flags=flags,x=xy[0],y=xy[1],camera_x=camera[0],camera_y=camera[1],count=count,debug=0)
    for original,node,depth in itertools.product((0x106101,0x100400,0x1003a6,0x100396),(0x100400,),(0,0xffff)):add('original-A6-allocation-field-live-alias',original=original,node=node,depth=depth)
    for root in roots:
        for allocate,debug in ((0,0),(1,0),(0,1),(1,1)):add('all42-canonical-catalog-cue-heads',cue=root['cpu_address'],allocate=allocate,debug=debug)
    for cue,debug,manual,stream,phase in ((0,0,1,0,0),(0,1,1,0,0),(0x106000,0,0,0,0),(0xe89e4,1,1,0,0),(0xe89e4,0,0,0xe89ec,0),(0x106000,0,0,0x106200,2),(0x106000,1,0,0x106200,0)):
        add('null-default-auto-cue-stream',cue=cue,allocate=0,debug=debug,manual=manual,stream=stream,phase=phase)
    for x,y in itertools.product((0xfe9f,0xfea0,0,0x29f,0x2a0),(0x3f,0x40,0x1df,0x1e0,0x2bf,0x2c0)):add('debug-both-clips-packed-unsigned-Y',allocate=0,debug=1,x=x,y=y)
    for allocation,flags,vector in itertools.product((0,1),range(4),((1,0x41,3,5,7,9),(0xffff,0xffff,1,2,3,4),(0x7fff,0x8000,0x8000,0x7fff,0xffff,1),(0x29f,0x2bf,0xffff,0xffff,1,1))):
        x,y,cx,cy,ox,oy=vector;add('debug-camera-and-offset-adds-WORD-wrap',allocate=allocation,debug=1,flags=flags,x=x,y=y,camera_x=cx,camera_y=cy,offset_x=ox,offset_y=oy)
    for allocation,x,y in itertools.product((0,1),(0,0x29f),(0x40,0x2bf)):
        add('whole-frame-begin-wait-hold-ready',allocate=allocation,debug=1,x=x,y=y,consumer=2,prepared=4,pending=True)
    for status in ('full','normal'):
        add('debug-queue-'+status,allocate=1,debug=1,consumer=2 if status=='full' else 0x100,prepared=2)
    for pointer,phase in ((0x10de1e,0),(0x10de1e,16),(0x10de22,0)):
        add('auto-stream-live-publication-overlap',allocate=0,manual=0,stream=pointer,phase=phase,gates=[0,0xffff,0xffff])
    for step in range(4):add('actual-full-frame-output-chain',sequence='allocation-once',sequence_position=step,allocate=1,manual=0,debug=1)
    assert len(cases)==822
    return cases

def fixture(c):
    ram=bytearray(hashlib.shake_256(b'stage-cue-frame'+bytes([c['profile']])).digest(65536));regs=[0]*14 if not c['profile'] else [(0x89abcdef+i*0x1020304)&0xffffffff for i in range(14)];regs[13]=c['original']
    struct.pack_into('>II',ram,0xde26,c['cue'],c['stream']);ram[0xde2e]=c['manual'];ram[0xde2f]=c['allocate'];ram[0xf001]=2*c['debug'];struct.pack_into('>H',ram,0xd418,c['phase'])
    for at,value in ((0xd3bc,c['camera_x']),(0xd3c0,c['camera_y']),(0xd3a2,c['offset_x']),(0xd3a6,c['offset_y'])):struct.pack_into('>H',ram,at,value)
    # Parent coordinate LONGs share debug offset WORDs by the native layout.
    struct.pack_into('>II',ram,0xd3a2,(c['offset_x']<<16)|0x1234,(c['offset_y']<<16)|0x5678);ram[0xd3b3]=0x40;ram[0xd494]=0x81
    if BASE<=c['stream']<BASE+65536:
        for i,g in enumerate(c['gates']):
            at=c['stream']-BASE+12*i;struct.pack_into('>HHB',ram,at,g,0,0);struct.pack_into('>HHB',ram,at+4,c['x'],c['y'],c['flags'])
        struct.pack_into('>I',ram,0xde2a,c['stream'])
    if BASE<=c['cue']<=BASE+65528:struct.pack_into('>HHBBBB',ram,c['cue']-BASE,c['x'],c['y'],c['flags'],8,0,c['tag'])
    # Stream payload may overlap control bytes; explicit final host control seed
    # is part of the fixture and changes the live gate, never normalized later.
    ram[0xde2e]=c['manual'];ram[0xde2f]=c['allocate']
    struct.pack_into('>IH',ram,0x4c9c,c['node'],c['count']);struct.pack_into('>I',ram,0xbfc,c['successor']);struct.pack_into('>H',ram,0xc04,c['depth']);ram[0xc5e]=0xa5
    for i in range(4):struct.pack_into('>I',ram,c['node']-BASE+i*0x100+8,c['node']+(i+1)*0x100)
    struct.pack_into('>I',ram,c['successor']-BASE+4,0x100bf4)
    if c['original'] not in (0x100400,0x1003a6,0x100396):ram[c['original']+0x6a-BASE]=0x5a
    struct.pack_into('>I',ram,0x9152,0xcd50)
    for i in range(256):struct.pack_into('>H',ram,0x8b34+2*i,12*i)
    struct.pack_into('>4H',ram,0x8d34,c['consumer'],c['prepared'],c['normal'],c['producer']);struct.pack_into('>H',ram,0x8b34+((c['producer']+2)&0x1fe),c['offset']);struct.pack_into('>H',ram,0x914e,0)
    return ram,regs
class Observer:
    def __init__(self,program):
        self.program=program;self.cpu=MusashiOracle();self.cpu.load(0,program[:BASE]);self.pcs=[];self.writes=[];self.copies=[];self.debug_adds=[]
        def code(pc):
            self.pcs.append(pc)
            if pc==0xcd5c:assert self.cpu.get_reg('a0')==0xcd50
            if pc in (0xe8b2e,0xe8b32,0xe8b36):self.debug_adds.append(dict(pc=pc,d0=self.cpu.get_reg('d0'),d1=self.cpu.get_reg('d1'),offset_x=int.from_bytes(self.cpu.read(0x10d3a2,2),'big'),offset_y=int.from_bytes(self.cpu.read(0x10d3a6,2),'big')))
            if pc==0x2992:self.copies.append(dict(source=self.cpu.get_reg('a6')+0x6a,destination=self.cpu.get_reg('a0')+0x6a,value=self.cpu.read(self.cpu.get_reg('a6')+0x6a,1)[0]))
            op=int.from_bytes(self.cpu.read(pc,2),'big');assert op!=0x4afc and not 0x4e40<=op<=0x4e4f,(pc,op)
        def write(pc,address,size,value):
            assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(pc,address,size,value)
            if BASE<=address<BASE+65536:self.writes.append(dict(pc=pc,address=address,size=size,value=value))
        self.cpu.set_instruction_hook(code);self.cpu.set_write_hook(write)
    def prepare(self,ram,regs):
        cpu=self.cpu;cpu.reset();cpu.load(BASE,ram);cpu.set_reg('sr',0x2000);cpu.set_reg('a5',0x108000);cpu.set_reg('a7',STACK);cpu.load(STACK,RETURN.to_bytes(4,'big'))
        for k,v in zip(KEYS,regs):cpu.set_reg(k,v)
        cpu.set_reg('pc',0xe8a48)
    def run(self,stop=RETURN,budget=20000):
        self.pcs.clear();self.writes.clear();self.copies.clear();self.debug_adds.clear();status=self.cpu.run(budget,stop);assert status['status'] in ('sentinel','budget_exhausted'),status;assert self.cpu.read(0,BASE)==self.program[:BASE]
        return status,self.cpu.read(BASE,65536),{k:self.cpu.get_reg(k) for k in KEYS},self.pcs.copy(),self.writes.copy(),self.copies.copy()
    def mutate(self,changes):
        for w in changes:self.cpu.load(w['address'],bytes.fromhex(w['raw_hex']))
def branch_counts(rows):
    counts=collections.defaultdict(collections.Counter)
    for r in rows:
        for phase in r['phases']:
            pcs=phase['pcs']+[phase['native']['pc']]
            for p,n in zip(pcs,pcs[1:]):
                if p in BRANCHES:counts[p][n]+=1
    return {hex(p):{hex(n):v for n,v in b.items()} for p,b in counts.items()}
def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;inputs,oracle=provenance(root),oracle_provenance(root);folder=root/'artifacts/stage_cue_frame';folder.mkdir(parents=True,exist_ok=True);observer=Observer(program);cases=build_cases(root);rows=[];previous=None
    for i,c in enumerate(cases):
        ram,regs=fixture(c) if c.get('sequence_position',0)==0 else (bytearray(previous[0]),list(previous[1]));observer.prepare(ram,regs);result,out,values,pcs,writes,copies=observer.run(WAIT_PC if c['pending'] else RETURN)
        assert result['status']=='sentinel' and observer.cpu.get_reg('a7')==(STACK-4 if c['pending'] else STACK+4),(i,c,result)
        status=3 if c['pending'] else (0 if 0xcdaa in pcs else 2 if 0xcd82 in pcs else 1 if 0xcd58 in pcs else 2)
        phases=[]
        def save(name,inp,inregs,waiting_in,status_in,result,out,values,pcs,writes,copies,changes,waiting,status):
            file='native_%04d_%s.bin'%(i,name);(folder/file).write_bytes(out);phases.append(dict(phase=name,input_ram_sha256=sha(inp),incoming=inregs,waiting_in=waiting_in,status_in=status_in,result=values,waiting=waiting,status=status,native=result,final_a7=observer.cpu.get_reg('a7'),pcs=pcs,RAM_writes=writes,byte_copies=copies,debug_add_snapshots=observer.debug_adds.copy(),external_RAM_writes=changes,ram_file=file,ram_sha256=sha(out),mmio_writes=0))
        save('begin',ram,dict(zip(KEYS,regs)),False,2,result,out,values,pcs,writes,copies,[],c['pending'],status)
        if c['pending']:
            captured=values.copy();changes=[dict(address=0x109152,raw_hex='00106000'),dict(address=0x108d36,raw_hex='dead'),dict(address=0x108d3a,raw_hex='beef'),dict(address=0x10de2f,raw_hex='ff'),dict(address=0x10de26,raw_hex='00106001')];observer.mutate(changes);hold_input=observer.cpu.read(BASE,65536);held,holdout,holdregs,holdpcs,holdwrites,holdcopies=observer.run(RETURN,2);assert held['status']=='budget_exhausted' and held['pc']==WAIT_PC and holdpcs==[WAIT_PC,0xcda8] and holdregs==captured and holdout==hold_input and not holdwrites
            save('hold',hold_input,captured,True,3,held,holdout,holdregs,holdpcs,holdwrites,holdcopies,changes,True,3)
            changes=[dict(address=0x108d34,raw_hex=(captured['d4']&65535).to_bytes(2,'big').hex())];observer.mutate(changes);ready_input=observer.cpu.read(BASE,65536);done,readyout,readyregs,readypcs,readywrites,readycopies=observer.run();assert done['status']=='sentinel' and observer.cpu.get_reg('a7')==STACK+4 and 0xe8a48 not in readypcs and 0x2986 not in readypcs and 0xe8af4 not in readypcs and 0xcd58 not in readypcs and readyout[0xde2f]==0xff and readyout[0xde26:0xde2a]==bytes.fromhex('00106001')
            save('ready',ready_input,holdregs,True,3,done,readyout,readyregs,readypcs,readywrites,readycopies,changes,False,0)
        if 'sequence'in c:previous=(out,[values[k] for k in KEYS])
        rows.append(dict(case_index=i,fixture=c,phases=phases))
    assert provenance(root)==inputs and oracle_provenance(root)==oracle and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report=dict(source=source,oracle=oracle,inputs=inputs,cases=len(cases),phases=sum(len(r['phases']) for r in rows),results=rows,branch_successor_counts=branch_counts(rows),program_code_modified=False,failure=None,scope='Whole unmodifiede8a48 through original helpers/defaultcd50; fullRAM14registers/ordered writes. Actual pending cda4 retains sameCPU and original frame return stack (A7STACK-4), hold executes CMP/BNE, ready returns through e8b58 to outerRTS(A7STACK+4). Explicit external writes only between pendingphases; no ROM patch/stub/in-callreset/hookSRread. Controlled fixtures do not claim natural scheduler reachability.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),phases=report['phases'],sha256=sha(path.read_bytes()))))
if __name__=='__main__':main()
