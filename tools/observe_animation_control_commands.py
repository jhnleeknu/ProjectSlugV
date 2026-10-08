"""Immutable original49fc6 on liveRAM0c/14(1d,1e) control fixtures."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ,UC_HOOK_MEM_INVALID,UC_HOOK_INTR,m68k_const as m
from disassemble_program import load_verified_program,disassemble_range
from verify_object_reset import make_cpu
from observe_scene_frame_execution import oracle_provenance
from observe_screen_reset_full import BASE,STACK,STACK_START,RETURN,KEYS,REGS
from verify_stage_catalog import SOURCE_SHA256

ENTRY=0x49fc6
RANGES=((ENTRY,0x4a0e4),(0x4a0e4,0x4a104),(0x4a276,0x4a27e),
    (0x4a3b8,0x4a3de),(0x4a408,0x4a46c),(0x2b3e8,0x2b40c))
BOUNDARIES=(ENTRY,0x4a3b8,0x4a408,0x2b3e8,0x2b3fa,0x4a43e,0x4a460,0x4a464,0x4a466,0x4a468,0x4a276)
SELECTORS=(0,1,0x90,0x3fff,0x4000,0x7fff,0x8000,0xffff)
def sha(data):return hashlib.sha256(data).hexdigest()
def signed_word(value):return value if value<0x8000 else value-0x10000
def put(ram,address,size,value):
    assert BASE<=address and address+size<=BASE+65536,(address,size)
    ram[address-BASE:address-BASE+size]=value.to_bytes(size,'big')
def cases():
    rows=[]
    for selector,desired,live in itertools.product(SELECTORS,(0,1,0x80,0xff),(0,1,0x80,0xff)):
        rows.append(dict(family='0c-signed-selector-wrap-live-BYTE',opcode=0x0c,selector=selector,desired=desired,requested_live=live))
    for selector,index,profile in itertools.product((0x1d,0x1e),(0,1,0x7f,0x80,0xff),('RAM','fixed6431a','overlap+76','overlap+78','overlap+7a')):
        rows.append(dict(family='14-'+profile,opcode=0x14,selector=selector,requested_index=index,profile=profile))
    assert len(rows)==178;return rows
def fixture(case,index,program):
    ram=bytearray(hashlib.shake_256(b'animation-control-'+bytes([index%4])).digest(65536))
    regs={key:(0x89abcdef+i*0x1020304+index*0x101)&0xffffffff for i,key in enumerate(KEYS)}
    regs.update(a5=0x108000,a6=0x108000)
    for address,size,value in ((0x108026,4,0x105000),(0x10802a,2,0),(0x10802c,2,0x100),(0x108017,1,0),
        (0x100010,2,0xbeef),(0x105020,1,0x28)):
        put(ram,address,size,value)
    if case['opcode']==0x0c:
        doubled=(case['selector']*2)&65535;lookup=0x4a76c+signed_word(doubled)
        raw=int.from_bytes(program[lookup:lookup+2],'big');field=regs['a6']+signed_word(raw)
        put(ram,0x105000,1,0x0c);put(ram,0x105001,1,case['desired']);put(ram,0x105002,2,case['selector']);put(ram,0x105004,4,0x105020)
        put(ram,0x105008,2,0);put(ram,field,1,case['requested_live'])
        case.update(table_address=lookup,raw_offset=raw,field_address=field,live_field=ram[field-BASE],
            live_desired=ram[0x5001],branch_target=0x105020,fallthrough=0x105008)
        assert not (0x108026<=field<0x10802e or 0x105000<=field<0x10500a),'unexpected field/setup alias'
    else:
        field=regs['a6']+(0x7c if case['selector']==0x1d else 0x7d)
        put(ram,field,1,case['requested_index']);profile=case['profile']
        source=None
        if profile.startswith('overlap'):
            source=regs['a6']+int(profile[-2:],16)
            put(ram,source,4,0xa1b2c3d4) # May overwrite the index: use its actual live value below.
        live_index=ram[field-BASE]
        if profile=='RAM':
            operand=0x106000;source=operand+live_index*4;put(ram,source,4,0x81230000|(live_index<<8)|case['selector'])
        elif profile=='fixed6431a':operand=0x6431a;source=operand+live_index*4
        else:operand=source-live_index*4
        put(ram,0x105000,1,0x14);put(ram,0x105001,1,case['selector']);put(ram,0x105002,4,operand);put(ram,0x105006,2,0)
        assert ram[field-BASE]==live_index
        value=int.from_bytes(program[source:source+4] if source<BASE else ram[source-BASE:source-BASE+4],'big')
        case.update(index_address=field,live_index=live_index,index_changed_by_overlap=live_index!=case['requested_index'],
            operand=operand,source_address=source,source_value=value,callback_table_address=0x4a500+case['selector']*4,
            callback=int.from_bytes(program[0x4a500+case['selector']*4:0x4a504+case['selector']*4],'big'))
    return bytes(ram),regs

class Observer:
    def __init__(self,program,branches):
        self.program=program;self.cpu=make_cpu(program);self.cpu.mem_map(0x2ff000,4096);self.baseline=self.cpu.context_save();self.branch_pcs=branches
        self.pcs=[];self.events=[];self.reads=[];self.boundaries=[];self.error=None
        def code(c,pc,size,user):
            self.pcs.append(pc)
            if pc==RETURN:c.emu_stop();return
            if pc in BOUNDARIES:
                sp=c.reg_read(m.UC_M68K_REG_A7)
                self.boundaries.append(dict(pc=pc,a7=sp,registers=self.regs(),stack_at_sp=bytes(c.mem_read(sp,min(26,STACK+4-sp))).hex()))
            if not any(start<=pc<end for start,end in RANGES):self.error=dict(kind='unsupported-code',pc=pc);c.emu_stop()
            opcode=int.from_bytes(c.mem_read(pc,2),'big')
            if opcode==0x4afc or 0x4e40<=opcode<=0x4e4f:self.error=dict(kind='trap',pc=pc);c.emu_stop()
        def write(c,access,address,size,value,user):
            kind='ports' if address in (0x2ffff0,0x2ffff2) and size==2 else 'ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK else None
            event=dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=value&((1<<(8*size))-1),kind=kind);self.events.append(event)
            if kind is None:self.error=dict(kind='unexpected-write',event=event);c.emu_stop()
        def read(c,access,address,size,value,user):
            kind='ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK+4 else 'fixed' if address+size<=BASE else None
            event=dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=int.from_bytes(c.mem_read(address,size),'big'),kind=kind);self.reads.append(event)
            if kind is None:self.error=dict(kind='unexpected-read',event=event);c.emu_stop()
        def invalid(c,access,address,size,value,user):self.error=dict(kind='invalid-memory',address=address,size=size);return False
        def intr(c,number,user):self.error=dict(kind='exception',number=number,pc=c.reg_read(m.UC_M68K_REG_PC));c.emu_stop()
        for hook,callback in ((UC_HOOK_CODE,code),(UC_HOOK_MEM_WRITE,write),(UC_HOOK_MEM_READ,read),(UC_HOOK_MEM_INVALID,invalid),(UC_HOOK_INTR,intr)):
            self.cpu.hook_add(hook,callback)
    def regs(self):return {key:self.cpu.reg_read(reg)&0xffffffff for key,reg in zip(KEYS,REGS)}
    def run(self,ram,regs):
        c=self.cpu;c.context_restore(self.baseline);c.mem_write(BASE,ram);c.mem_write(STACK_START,b'\x5a'*4100);c.mem_write(STACK,RETURN.to_bytes(4,'big'))
        c.reg_write(m.UC_M68K_REG_SR,0x2000);c.reg_write(m.UC_M68K_REG_A7,STACK)
        for key,reg in zip(KEYS,REGS):c.reg_write(reg,regs[key])
        self.pcs.clear();self.events.clear();self.reads.clear();self.boundaries.clear();self.error=None
        c.emu_start(ENTRY,0xffffff,count=10000);pc=c.reg_read(m.UC_M68K_REG_PC);sp=c.reg_read(m.UC_M68K_REG_A7)
        assert self.error is None and pc==RETURN and sp==STACK+4,(self.error,hex(pc),hex(sp))
        carry=bool(c.reg_read(m.UC_M68K_REG_SR)&1);result=self.regs()
        assert bytes(c.mem_read(STACK,4))==RETURN.to_bytes(4,'big') and bytes(c.mem_read(0,BASE))==self.program[:BASE]
        lowest=min([e['address'] for e in self.events if e['kind']=='stack']+[STACK])
        assert bytes(c.mem_read(STACK_START,lowest-STACK_START))==b'\x5a'*(lowest-STACK_START)
        replay=bytearray(ram);ports=[]
        for event in self.events:
            if event['kind']=='ram':replay[event['address']-BASE:event['address']-BASE+event['size']]=event['value'].to_bytes(event['size'],'big')
            if event['kind']=='ports':ports.append(struct.pack('>BII',event['size'],event['address'],event['value']))
        output=bytes(c.mem_read(BASE,65536));assert output==bytes(replay)
        trace=dict(pcs=self.pcs.copy(),ordered_writes=self.events.copy(),reads=self.reads.copy(),boundaries=self.boundaries.copy(),
            branches=[dict(pc=a,next_pc=b) for a,b in zip(self.pcs,self.pcs[1:]) if a in self.branch_pcs])
        return output,b''.join(ports),dict(result=result,carry=carry,final_pc=pc,final_a7=sp,lowest_stack_write=lowest,instructions=len(self.pcs)-1),trace

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    folder=root/'artifacts/animation_control_commands';folder.mkdir(parents=True,exist_ok=True);report_path=folder/'observation.json';report_path.unlink(missing_ok=True)
    instructions=[]
    for start,end in RANGES:instructions.extend(disassemble_range(program,start,end-start,start))
    for row in instructions:
        at=row['rom_offset'];assert bytes.fromhex(row['raw'])==program[at:at+row['size']]
    branches={r['cpu_address'] for r in instructions if r['mnemonic'].startswith('b') and not r['mnemonic'].startswith(('bra','bsr','btst','bclr'))}
    (folder/'source.json').write_text(json.dumps(dict(source=source,ranges=RANGES,instructions=instructions,
        data_ranges=[dict(cpu_address=a,rom_offset=a,size=size,sha256=sha(program[a:a+size])) for a,size in ((0x4276c,65536),(0x6431a,1024))]),indent=2)+'\n')
    names=('tools/observe_animation_control_commands.py','tools/disassemble_program.py','tools/verify_object_reset.py',
        'tools/observe_scene_frame_execution.py','tools/observe_screen_reset_full.py','artifacts/animation_control_commands/source.json')
    inputs={name:sha((root/name).read_bytes()) for name in names};oracle=oracle_provenance();observer=Observer(program,branches);rows=[];outcomes=collections.defaultdict(collections.Counter)
    for index,case in enumerate(cases()):
        ram,regs=fixture(case,index,program);output,ports,info,trace=observer.run(ram,regs)
        if case['opcode']==0x0c:
            truth=bool(case['live_field'])==bool(case['live_desired'])
            assert info['carry']==truth
            branch=next(b for b in trace['branches'] if b['pc']==0x4a3d4)
            assert branch['next_pc']==(0x4a3d8 if truth else 0x4a276)
            field=next(r for r in trace['reads'] if r['pc']==0x4a3cc)
            assert (field['address'],field['size'],field['value'])==(case['field_address'],1,case['live_field'])
            table=next(r for r in trace['reads'] if r['pc']==0x4a3c6)
            assert (table['address'],table['size'],table['value'])==(case['table_address'],2,case['raw_offset'])
        else:
            assert not info['carry']
            callback=next(b for b in trace['boundaries'] if b['pc']==case['callback']);sp=callback['a7'];raw=bytes.fromhex(callback['stack_at_sp'])
            assert sp==STACK-14 and int.from_bytes(raw[:4],'big')==0x4a43e
            assert int.from_bytes(raw[4:6],'big')==0 and int.from_bytes(raw[6:10],'big')==0x105006 and int.from_bytes(raw[10:14],'big')==0x108026
            source_read=next(r for r in trace['reads'] if r['pc'] in (0x2b3f2,0x2b404))
            assert (source_read['address'],source_read['size'],source_read['value'])==(case['source_address'],4,case['source_value'])
            written=next(w for w in trace['ordered_writes'] if w['pc'] in (0x2b3f2,0x2b404))
            assert (written['address'],written['size'],written['value'])==(0x108078,4,case['source_value'])
            before=next(b for b in trace['boundaries'] if b['pc']==0x4a460);after=next(b for b in trace['boundaries'] if b['pc']==0x4a464)
            words=bytes.fromhex(before['stack_at_sp'])
            for key,at in (('d0',0),('d7',2)):
                value=int.from_bytes(words[at:at+2],'big');expected=value if value<0x8000 else value|0xffff0000
                assert after['registers'][key]==expected
            restored=next(b for b in trace['boundaries'] if b['pc']==0x4a468)
            assert restored['registers']['a0']==0x108026 and restored['registers']['a1']==0x105006
            assert info['result']['d0']==case['live_index']*4
        for branch in trace['branches']:outcomes[branch['pc']][branch['next_pc']]+=1
        prefix='case_%03d'%index;payloads={prefix+'_input.bin':ram,prefix+'_native.bin':output,prefix+'_ports.bin':ports,
            prefix+'_trace.json':(json.dumps(trace,indent=2)+'\n').encode()}
        for name,data in payloads.items():(folder/name).write_bytes(data)
        rows.append(dict(case_index=index,fixture=case,incoming=regs,port_count=len(ports)//9,input_ram_file=prefix+'_input.bin',
            ram_file=prefix+'_native.bin',ports_file=prefix+'_ports.bin',trace_file=prefix+'_trace.json',files={name:sha(data) for name,data in payloads.items()},**info))
    excluded=[]
    for a6,selector in ((0x100000,0x7fff),(0x10ffd0,0)):
        table=0x4a76c+signed_word((selector*2)&65535);offset=int.from_bytes(program[table:table+2],'big');field=a6+signed_word(offset)
        assert not BASE<=field<BASE+65536
        excluded.append(dict(opcode=0x0c,a6=a6,selector=selector,table_address=table,raw_offset=offset,field_address=field,
            classification='unsupported fixture: reached field outside contract RAM',native_executed=False,success=False))
    assert oracle==oracle_provenance() and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    assert all(sha((root/name).read_bytes())==digest for name,digest in inputs.items())
    report=dict(source=source,oracle=oracle,inputs=inputs,entry_pc=ENTRY,cases=len(rows),cases_by_opcode=dict(collections.Counter(hex(r['fixture']['opcode']) for r in rows)),
        total_native_ports=sum(r['port_count'] for r in rows),excluded_fixtures=excluded,
        observed_branch_successors={hex(pc):{hex(target):n for target,n in sorted(counts.items())} for pc,counts in sorted(outcomes.items())},
        results=rows,original_program_modified=False,in_call_SR_read=False,Cpp_comparison_performed=False,failure=None,
        scope='Immutable original49fc6 with synthetic liveRAM scripts0c and14 selectors1d/1e only; actualfixed lookup/callback tables and fixed6431a data. '
        'Full64KiB RAM/15registers/RTS carry/orderedRAM-stack-PVC writes and reads retained; source/object overlaps use recorded live index after final fixture writes. '
        'OriginalMOVEM.W D0/D7 signextension and A0/A1 restoration asserted. SR set beforeA7 and never read/modified inhooks; stackguard/RAMreplay/immutablefixedcode checked. '
        'Two out-of-RAM field fixtures explicitly excluded without native execution, not successful observations. No1f/pending/allcallbacks/fullgame/naturalreachability/IRQ/cycle/physicalmirror claim.')
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),cases_by_opcode=report['cases_by_opcode'],ports=report['total_native_ports'],excluded=len(excluded),sha256=sha(report_path.read_bytes()))))

if __name__=='__main__':main()
