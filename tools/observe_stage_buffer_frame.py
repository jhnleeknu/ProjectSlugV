"""Original4aa88 full RAM/register/ports snapshots and same-CPU pending resumes."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ,UC_HOOK_MEM_INVALID,UC_HOOK_INTR,m68k_const as m
from verify_object_reset import make_cpu
from disassemble_program import load_verified_program
from observe_scene_frame_execution import oracle_provenance
from observe_scene_motion_pair import oracle_provenance as musashi_provenance
from musashi_oracle import MusashiOracle
from inventory_stage_buffer_frame import inventory
from pack_stage_input import SOURCE_SHA256
BASE,STACK,RETURN,WAIT_PC=0x100000,0x1feffc,0xff000,0xcda4
KEYS=tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(5))+('a6',)
REGS=tuple(getattr(m,'UC_M68K_REG_'+k.upper()) for k in KEYS)
BRANCHES=(0x4aa90,0x4aaa8,0x4aab0,0x4aabe,0x4aafa,0x4ab2a,0x4ab56,0x4ab6a,0x4ab82,0x4b790,0x4b7a0,0x4b7b4,0x4b7f0,0x4b7fc,0xcd66,0xcd78,0xcd94,0xcda0,0xcda8,0xcdb2)
SAVED=('saved_a0','saved_d0','saved_d1','saved_d7','saved_slot_a4','saved_slot_d7','saved_a6')
def sha(data):return hashlib.sha256(data).hexdigest()
def audited(root):
    report=inventory(root);path=root/'artifacts/stage_buffer_frame_inventory.json';assert json.loads(path.read_text())==json.loads(json.dumps(report));return report
def provenance(root):
    audit=audited(root);names=('build/step_stage_buffer_frame','engine/src/stage_buffer_frame.cpp','engine/include/ms5/stage_buffer_frame.h','engine/tools/step_stage_buffer_frame.cpp','engine/src/sprite_submit_execution.cpp','engine/include/ms5/sprite_submit_execution.h','engine/include/ms5/sprite_producer.h','engine/include/ms5/scene_map_transfer.h','engine/include/ms5/video_port.h','engine/src/fixed_data_resource.cpp','engine/include/ms5/fixed_data_resource.h','tools/observe_stage_buffer_frame.py','tools/verify_stage_buffer_frame.py','tools/inventory_stage_buffer_frame.py','artifacts/stage_buffer_frame_inventory.json')
    rows=[dict(file=n,sha256=sha((root/n).read_bytes())) for n in names]
    for r in audit['resource_audit']['resource_read_fixtures']:rows.append(dict(file=r['file'],sha256=sha((root/r['file']).read_bytes())));assert rows[-1]['sha256']==r['container_sha256']
    return rows

def build_cases(root):
    resources=audited(root)['resource_audit']['resource_read_fixtures'];cases=[]
    def add(family,**kw):
        c=dict(family=family,profile=1,bank=2,debug=0,flags=0,pressed=[0,0],toggle=0,ring=0x10db88,slot_set=[],slot_null_object=[],slot_null_source=[],slot_mismatch=[],object_flags=0,xy=[0,0x100],dims=[16,32],position=[0,0],normal=0,producer=0,consumer=0x100,prepared=0x80,offset=12,source_role='RAM',pending=False,both_wait=False);c.update(kw);cases.append(c)
    for ring,flags,pressed,toggle,profile in itertools.product((0x100000,0x10db88,0x10dc68,0x10dc70,0x10dc88,0x10d744,0x10db84),(0,1,0x7f),(0,0x80), (0,0x7f,0x80,0xff),range(2)):
        add('normal-LSR-ring-live-alias-byte-flags-toggle',ring=ring,flags=flags,pressed=[pressed,0],toggle=toggle,profile=profile)
    add('second-player-pressed-byte80',flags=1,pressed=[0,0x80],toggle=0x80)
    for slot,object_flags,profile in itertools.product(range(16),range(8),range(2)):add('all16-slots-flags-low3-highbits',debug=1,slot_set=[slot],object_flags=object_flags|(0xf8 if profile else 0),profile=profile)
    for selection in ('null-object','null-source','mismatch'):
        add('all16-filter-'+selection,debug=1,slot_set=list(range(16)),**{'slot_'+selection.replace('-','_') :list(range(16))} if selection!='mismatch' else dict(slot_mismatch=list(range(16))))
    for slots in ([0,3,15],list(range(16))):add('multiple-and-all16-live-loop',debug=1,slot_set=slots)
    for role,bank,flags in itertools.product(('RAM','fixed','bank2','bank3'),(2,3),(0,1,2,3,7)):
        if role in ('bank2','bank3') and bank!=int(role[-1]):continue
        add('source-window-visible-first-sprite',debug=1,slot_set=[0],source_role=role,bank=bank,object_flags=flags)
    for xy,prepared,consumer in itertools.product(([0,0x3f],[0x2a0,0x40],[0,0x40],[0,0x2bf]),(2,0x80),(2,0x100)):
        if consumer==2 and prepared!=2:continue
        add('debug-clip-full-normal',debug=1,slot_set=[0],xy=xy,consumer=consumer,prepared=prepared,dims=[0,0])
    for slot,bank,both in itertools.product((0,15),(2,3),(False,True)):
        add('actual-first-wait-both-sprites-live-resume',debug=1,slot_set=[slot],consumer=2,prepared=4,pending=True,both_wait=both,bank=bank)
    for slot,bank in itertools.product((0,15),(2,3)):
        add('fresh-second-sprite-only-wait',debug=1,slot_set=[slot],consumer=4,prepared=6,pending=True,initial_phase=2,bank=bank)
    for bank in (2,3):add('second-slot-first-wait-after-previous-ports',debug=1,slot_set=[0,1],consumer=6,prepared=8,pending=True,bank=bank)
    # First call full exits immediately; second nextD6 remains2 and can wait
    # only if consumer/prepared change outside the call, so phase2 is reached
    # naturally after a first accepted submission in the two-wait histories.
    add('mixed-bank3-reset-then-bank2-live-slots',debug=1,slot_set=[0,1],bank=3,source_roles=['bank3','bank2'])
    for step in range(4):add('actual-output-normal-frame-chain',sequence='normal',sequence_position=step,flags=1,pressed=[0x80,0],toggle=0x7f)
    assert len(cases)==659
    return cases,resources

def fixture(c,resources):
    ram=bytearray(hashlib.shake_256(b'stage-buffer-frame'+bytes([c['profile']])).digest(65536));regs=[0]*14 if not c['profile'] else [(0x89abcdef+i*0x1020304)&0xffffffff for i in range(14)];regs[13]=0x106f01
    struct.pack_into('>H',ram,0x10,0x1234) # Deliberately disagrees with actualbankstate.
    ram[0xf001]=c['flags']|(0x80 if c['debug'] else 0);ram[0x4cab],ram[0x4cb1]=c['pressed'];ram[0xd744]=c['toggle'];ram[0xdb84:0xdb88]=bytes((0x11,0xa5,0x22,0x5a));struct.pack_into('>I',ram,0xdc88,c['ring'])
    ram[0xdaf8:0xdb78]=bytes(128);struct.pack_into('>I',ram,0x9152,0xcd50)
    for i in range(256):struct.pack_into('>H',ram,0x8b34+2*i,i*12)
    struct.pack_into('>4H',ram,0x8d34,c['consumer'],c['prepared'],c['normal'],c['producer']);struct.pack_into('>H',ram,0x8b34+((c['producer']+2)&0x1fe),c['offset']);struct.pack_into('>H',ram,0x914e,0)
    for slot in c['slot_set']:
        obj=0x102000+slot*0x100;source=0x106000+slot*0x10;raw=struct.pack('>4H',*c['xy'],*c['dims']);position=c['position'].copy()
        role=c['source_roles'][slot] if 'source_roles'in c else c['source_role']
        if role!='RAM':
            r=next(r for r in resources if r['role']==role);source=r['source_cpu_address'];raw=bytes.fromhex(r['raw_hex']);x,y=struct.unpack('>HH',raw[:4]);flags=c['object_flags'];position=[(-(-x if flags&1 else x))&65535,(0x40-(-y if flags&2 else y))&65535]
        else:
            ram[source-BASE:source-BASE+8]=raw
            if c['family']=='source-window-visible-first-sprite':
                x,y=struct.unpack('>HH',raw[:4]);flags=c['object_flags'];position=[(-(-x if flags&1 else x))&65535,(0x40-(-y if flags&2 else y))&65535]
        at=obj-BASE;ram[at+0x15]=c['object_flags'];ram[at+0x6d]=(slot+1 if slot in c['slot_mismatch'] else slot)|0xf0;struct.pack_into('>H',ram,at+0x42,position[0]);struct.pack_into('>H',ram,at+0x46,position[1]);struct.pack_into('>II',ram,0xdaf8+8*slot,0 if slot in c['slot_null_object'] else obj,0 if slot in c['slot_null_source'] else source-4)
    return ram,regs
class Observer:
    def __init__(self,program):
        self.program=program;self.cpu=make_cpu(program);self.cpu.mem_map(0x200000,0x100000);self.baseline=self.cpu.context_save();self.bank=2;self.stop=RETURN;self.skip_initial_stop=False;self.error=None;self.pcs=[];self.writes=[];self.ports=[];self.sprite_inputs=[];self.reads=[];self.mmio_reads=[]
        def code(cpu,pc,size,user):
            if pc==self.stop:
                if self.skip_initial_stop:self.skip_initial_stop=False
                else:cpu.emu_stop();return
            self.pcs.append(pc)
            if pc==0xcd5c and cpu.reg_read(m.UC_M68K_REG_A0)!=0xcd50:self.error=('unsupported-callback',pc);cpu.emu_stop();return
            if pc==0xcd58:self.sprite_inputs.append(dict(pc=pc,d0=cpu.reg_read(m.UC_M68K_REG_D0)&0xffffffff,d1=cpu.reg_read(m.UC_M68K_REG_D1)&0xffffffff,a6=cpu.reg_read(m.UC_M68K_REG_A6)&0xffffffff))
            op=int.from_bytes(cpu.mem_read(pc,2),'big')
            if op==0x4afc or 0x4e40<=op<=0x4e4f:self.error=('trap',pc,op);cpu.emu_stop()
        def write(cpu,access,address,size,value,user):
            pc=cpu.reg_read(m.UC_M68K_REG_PC);value&=(1<<(size*8))-1
            if BASE<=address and address+size<=BASE+65536:self.writes.append(dict(pc=pc,address=address,size=size,value=value));return
            if STACK-4096<=address and address+size<=STACK+4:return
            if address not in (0x2ffff2,0x2ffff0) or size!=2:self.error=('unexpected-write',pc,address,size,value);cpu.emu_stop();return
            self.ports.append((size,address,value))
            if address==0x2ffff2:
                if value not in (0x1000,0x2000):self.error=('unsupported-bank',value);cpu.emu_stop();return
                self.bank=2 if value==0x1000 else 3;cpu.mem_write(0x200000,program[self.bank*0x100000:self.bank*0x100000+0xffff0])
        def read(cpu,access,address,size,value,user):
            if address+size>0x2ffff0 and address<0x300000:self.mmio_reads.append((address,size))
            if 0x200000<=address<0x2ffff0:self.reads.append(dict(pc=cpu.reg_read(m.UC_M68K_REG_PC),address=address,size=size,bank=self.bank))
        def invalid(cpu,access,address,size,value,user):self.error=('invalid-memory',access,address,size);return False
        def intr(cpu,number,user):self.error=('exception',number,cpu.reg_read(m.UC_M68K_REG_PC));cpu.emu_stop()
        self.cpu.hook_add(UC_HOOK_CODE,code);self.cpu.hook_add(UC_HOOK_MEM_WRITE,write);self.cpu.hook_add(UC_HOOK_MEM_READ,read);self.cpu.hook_add(UC_HOOK_MEM_INVALID,invalid);self.cpu.hook_add(UC_HOOK_INTR,intr)
    def prepare(self,ram,regs,bank):
        cpu=self.cpu;cpu.context_restore(self.baseline);cpu.mem_write(BASE,bytes(ram));self.bank=bank;cpu.mem_write(0x200000,self.program[bank*0x100000:bank*0x100000+0xffff0]);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        for reg,value in zip(REGS,regs):cpu.reg_write(reg,value)
        cpu.reg_write(m.UC_M68K_REG_PC,0x4aa88)
    def metadata(self,phase):
        if not phase:return {k:0 for k in SAVED}
        cpu=self.cpu;sp=cpu.reg_read(m.UC_M68K_REG_A7)
        def long(off):return int.from_bytes(cpu.mem_read(sp+off,4),'big')
        def word(off):return int.from_bytes(cpu.mem_read(sp+off,2),'big')
        assert long(0)==(0x4b7da if phase==1 else 0x4b814)
        assert long(20 if phase==1 else 8)==0x4aad4
        return dict(saved_a0=long(4),saved_d0=long(16) if phase==1 else 0,saved_d1=long(12) if phase==1 else 0,saved_d7=long(8) if phase==1 else 0,saved_slot_d7=word(24 if phase==1 else 12),saved_slot_a4=long(26 if phase==1 else 14),saved_a6=long(30 if phase==1 else 18))
    def run(self,stop=RETURN,budget=50000):
        self.stop=stop;self.skip_initial_stop=self.cpu.reg_read(m.UC_M68K_REG_PC)==stop;self.error=None;self.pcs.clear();self.writes.clear();self.ports.clear();self.sprite_inputs.clear();self.reads.clear();self.mmio_reads.clear();cpu=self.cpu
        cpu.emu_start(cpu.reg_read(m.UC_M68K_REG_PC),0xffffff,count=budget);pc=cpu.reg_read(m.UC_M68K_REG_PC);assert not self.error and not self.mmio_reads,(self.error,self.mmio_reads)
        assert bytes(cpu.mem_read(0,BASE))==self.program[:BASE] and bytes(cpu.mem_read(0x200000,0xffff0))==self.program[self.bank*0x100000:self.bank*0x100000+0xffff0]
        phase=0
        if pc==WAIT_PC:phase=1 if int.from_bytes(cpu.mem_read(cpu.reg_read(m.UC_M68K_REG_A7),4),'big')==0x4b7da else 2
        assert pc in (RETURN,WAIT_PC),hex(pc)
        assert cpu.reg_read(m.UC_M68K_REG_A7)==(STACK+4 if not phase else STACK-(34 if phase==1 else 22))
        state={k:cpu.reg_read(r)&0xffffffff for k,r in zip(KEYS,REGS)};state.update(bank=self.bank,phase=phase,**self.metadata(phase));ports=b''.join(struct.pack('>BII',*p) for p in self.ports)
        return bytes(cpu.mem_read(BASE,65536)),state,ports,dict(final_pc=pc,final_a7=cpu.reg_read(m.UC_M68K_REG_A7),pcs=self.pcs.copy(),RAM_writes=self.writes.copy(),sprite_inputs=self.sprite_inputs.copy(),banked_reads=self.reads.copy(),mmio_reads=0)
    def mutate(self,changes):
        for w in changes:self.cpu.mem_write(w['address'],bytes.fromhex(w['raw_hex']))
def branch_counts(rows):
    counts=collections.defaultdict(collections.Counter)
    for row in rows:
        for phase in row['phases']:
            pcs=phase['pcs']+[phase['final_pc']]
            for p,n in zip(pcs,pcs[1:]):
                if p in BRANCHES:counts[p][n]+=1
    return {hex(p):{hex(n):v for n,v in b.items()} for p,b in counts.items()}
def musashi_normal_comparison(root,program,cases,resources,rows,folder):
    oracle=musashi_provenance(root);cpu=MusashiOracle();cpu.load(0,program[:BASE]);proofs=[]
    def write(pc,address,size,value):
        assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(pc,address,size)
    cpu.set_write_hook(write)
    for i,c in enumerate(cases):
        if c['debug'] or 'sequence'in c:continue
        ram,regs=fixture(c,resources);cpu.reset();cpu.load(BASE,ram);cpu.set_reg('sr',0x2000);cpu.set_reg('a5',0x108000);cpu.set_reg('a7',STACK);cpu.load(STACK,RETURN.to_bytes(4,'big'))
        for k,v in zip(KEYS,regs):cpu.set_reg(k,v)
        cpu.set_reg('pc',0x4aa88);status=cpu.run(20000,RETURN);assert status['status']=='sentinel' and cpu.get_reg('a7')==STACK+4,status
        phase=rows[i]['phases'][0];expected=(folder/phase['ram_file']).read_bytes();result={k:cpu.get_reg(k) for k in KEYS};assert cpu.read(BASE,65536)==expected and result=={k:phase['result'][k] for k in KEYS}
        assert cpu.read(0,BASE)==program[:BASE] and not phase['port_count'];proofs.append(dict(case_index=i,input_ram_sha256=sha(ram),ram_sha256=sha(expected),result=result,final_pc=RETURN,final_a7=STACK+4))
    assert musashi_provenance(root)==oracle and len(proofs)==337
    return dict(oracle=oracle,cases=len(proofs),results=proofs,scope='Independent original full4aa88 calls taking debug-off/nonMMIO path, fullRAM14regs; no stub/patch/checkpoint replacement, Musashi limited2MiB never used for MMIO paths.')
def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;inputs,oracle=provenance(root),oracle_provenance();cases,resources=build_cases(root);folder=root/'artifacts/stage_buffer_frame';folder.mkdir(parents=True,exist_ok=True);observer=Observer(program);rows=[];previous=None
    for i,c in enumerate(cases):
        ram,regs=fixture(c,resources) if not c.get('sequence_position',0) else (bytearray(previous[0]),list(previous[1]));observer.prepare(ram,regs,c['bank'] if not c.get('sequence_position',0) else previous[2]);phases=[]
        def save(name,inp,incoming,out,state,ports,info,changes):
            file='native_%04d_%s.bin'%(i,name);pfile='native_%04d_%s.ports.bin'%(i,name);(folder/file).write_bytes(out);(folder/pfile).write_bytes(ports);phases.append(dict(phase_name=name,input_ram_sha256=sha(inp),incoming=incoming,result=state,ram_file=file,ram_sha256=sha(out),ports_file=pfile,ports_sha256=sha(ports),port_count=len(ports)//9,external_RAM_writes=changes,**info))
        incoming=dict(zip(KEYS,regs),bank=observer.bank,phase=0,**{k:0 for k in SAVED});out,state,ports,info=observer.run(WAIT_PC if c['pending'] else RETURN);save('begin',ram,incoming,out,state,ports,info,[])
        if c['pending']:
            assert state['phase']==c.get('initial_phase',1);obj=0x102000+state['saved_slot_d7']*0x100
            if state['phase']==1:
                changes=[dict(address=obj+0x15,raw_hex='03'),dict(address=state['saved_a0'],raw_hex='00100020'),dict(address=0x109152,raw_hex='00106001'),dict(address=0x108d36,raw_hex='0006'),dict(address=0x108d3a,raw_hex='beef')]
                observer.mutate(changes);holdin=bytes(observer.cpu.mem_read(BASE,65536));holdout,held,hports,hi=observer.run(RETURN,2);assert held==state and holdout==holdin and not hports and not hi['RAM_writes'] and hi['pcs']==[WAIT_PC,0xcda8];save('first_hold',holdin,state,holdout,held,hports,hi,changes)
                changes=[dict(address=0x108d34,raw_hex=(held['d4']&65535).to_bytes(2,'big').hex()),dict(address=0x109152,raw_hex='0000cd50')]
                if not c['both_wait']:changes.append(dict(address=0x108d36,raw_hex=(held['d4']&65535).to_bytes(2,'big').hex()))
                observer.mutate(changes);readyin=bytes(observer.cpu.mem_read(BASE,65536));done,nextstate,nports,ni=observer.run(WAIT_PC if c['both_wait'] else RETURN);save('first_ready',readyin,held,done,nextstate,nports,ni,changes)
                assert 0x4aa88 not in ni['pcs'] and 0x4b798 not in ni['pcs'] and 0x4b7e2 in ni['pcs']
                if c['both_wait']:assert nextstate['phase']==2 and not nports
            else:nextstate=state
            if nextstate['phase']==2:
                changes=[dict(address=obj+0x15,raw_hex='ff'),dict(address=nextstate['saved_a0']-4,raw_hex='7fff7fff'),dict(address=0x109152,raw_hex='00106001'),dict(address=0x108d36,raw_hex='dead'),dict(address=0x108d3a,raw_hex='abcd')];observer.mutate(changes);holdin=bytes(observer.cpu.mem_read(BASE,65536));holdout,held,hports,hi=observer.run(RETURN,2);assert held==nextstate and holdout==holdin and not hports and not hi['RAM_writes'] and hi['pcs']==[WAIT_PC,0xcda8];save('second_hold',holdin,nextstate,holdout,held,hports,hi,changes)
                changes=[dict(address=0x108d34,raw_hex=(held['d4']&65535).to_bytes(2,'big').hex())];observer.mutate(changes);readyin=bytes(observer.cpu.mem_read(BASE,65536));done,nextstate,nports,ni=observer.run();assert 0x4b7e2 not in ni['pcs'] and 0xcd58 not in ni['pcs'];save('second_ready',readyin,held,done,nextstate,nports,ni,changes)
        if 'sequence'in c:previous=(out,[state[k] for k in KEYS],state['bank'])
        rows.append(dict(case_index=i,fixture=c,phases=phases))
    assert provenance(root)==inputs and oracle_provenance()==oracle and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    musashi=musashi_normal_comparison(root,program,cases,resources,rows,folder)
    report=dict(branch_successor_counts=branch_counts(rows),musashi_normal_comparison=musashi,source=source,oracle=oracle,inputs=inputs,cases=len(cases),phases=sum(len(r['phases']) for r in rows),results=rows,program_code_modified=False,physical_bank_payload_modified=False,in_call_SR_read=False,failure=None,scope='Whole original4aa88 and callees in Unicorn2.1.4 with PC/register-only hooks; immutablefixedROM/physicalbanks and exactPVCmapping. Same nativeCPU/stack preserved across actualfirst/secondspritewaits; eachphase retains only newly emitted orderedports. Explicit betweenphaseRAMchanges recorded. FullRAM14regs/bank/phase/savedmetadata, noROMpatch/stub/calleereset/SRhookread; no natural IRQ/scheduler timing claim.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),phases=report['phases'],sha256=sha(path.read_bytes()))))
if __name__=='__main__':main()
