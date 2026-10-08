"""Original whole49fc6 with a real coherent work-RAM stack, synthetic scripts.

All16 work-RAM mirrors share one retained ctypes owner. No scratch stack, ROM
patch, SR reads at any phase, or register injection after begin. Eight fixtures
observe40 reading residual S-8/S-4 slots after actual supported prefix paths.
PVC writes are native; the independently folded device bank is metadata. These
scripts retain bank2 at completed pairs and do not read bank ROM during pairs.
"""
import ctypes
import hashlib
import inspect
import json
from pathlib import Path
import struct
import sys
import unicorn
from unicorn import m68k_const as m
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_banked_handler as isolated
from address_map import pvc_bank_update
from disassemble_program import load_verified_program,disassemble_range

ENTRY,RETURN,S=0x49fc6,0xff000,0x1feffc
A5,A6,SCRIPT=0x108000,0x102000,0x106000
RAM,SIZE,PVC=0x100000,65536,0x2fe000
RANGES=((ENTRY,0x4a104),(0x4a104,0x4a126),(0x4a22c,0x4a27e),
        (0x4a2da,0x4a2f2),(0x4a382,0x4a3ac),(0x4a408,0x4a46c),
        (0x3679e,0x367a0),(0x3ac8,0x3c08))
BOUNDARIES=(ENTRY,0x3679e,0x4a43e,0x4a464,0x3af8,0x3b06,0x4a2ec,
    0x4a23e,0x4a270,0x4a104,0x4a124,0x4a382,0x4a39a,0x4a39e,0x4a3a0,0x4a3a4,0x4a276,0x4a0e2)
WAIT,HEAD,TAIL=0x3aea,0x104d74,0x104d76
CAP=5000
sha=isolated.sha
REG_IDS=isolated.REG_IDS


def canonical(address):return RAM|(address&65535)


def put(ram,address,size,value):
    for i,b in enumerate(value.to_bytes(size,'big')):ram[(address+i)&65535]=b


def cases():
    return [dict(prefix=prefix,first=first,label=prefix+'-first-%04x'%first)
        for prefix in ('14-03-RTS','30-early-sound','10-skip-draw','04-early-sentinel')
        for first in (0xeff0,0xeff4)]


def fixture(program,case):
    assert program[0x3679e:0x367a0]==bytes.fromhex('4e75')
    assert int.from_bytes(program[0x4a50c:0x4a510],'big')==0x3679e
    assert program[0x4a76c:0x4a770]==bytes.fromhex('00560000')
    ram=bytearray(hashlib.shake_256(b'animation-shared-stack-common').digest(SIZE))
    regs={key:(0x89abcdef+i*0x1020304)&0xffffffff for i,key in enumerate(isolated.REG_NAMES)}
    regs.update(a5=A5,a6=A6)
    setup=[(A6+0x26,4,SCRIPT),(A6+0x2a,2,0),(A6+0x2c,2,0x100),(A6+0x17,1,0),
        (A6,1,1),(A5-0x7ff0,2,0xbeef),(S,4,RETURN),(S-8,4,0x104800),(S-4,4,0x104900),
        (0x104800,4,0x12345678),(0x104900,4,0x9abcdef0)]
    prefix={
        '14-03-RTS':bytes.fromhex('140300000000'),
        '30-early-sound':bytes.fromhex('30002000'),
        '10-skip-draw':bytes.fromhex('1001000804000000007ff800'),
        '04-early-sentinel':bytes.fromhex('04000000007ff800')}[case['prefix']]
    body=bytes([0x40,0])+case['first'].to_bytes(2,'big')+bytes.fromhex('000028')
    script=prefix+body
    for address,size,value in setup:put(ram,address,size,value)
    for i,b in enumerate(script):put(ram,SCRIPT+i,1,b)
    details=dict(script_address=SCRIPT,script_raw=script.hex(),script_end_exclusive=SCRIPT+len(script),
        prefix_raw=prefix.hex(),opcode40_address=SCRIPT+len(prefix),terminal_address=SCRIPT+len(script)-1,
        first_effective_address=(0x200004+isolated.s16(case['first']))&0xffffffff,
        first_stack_slot='S-8' if case['first']==0xeff0 else 'S-4',
        field_selector=0,field_WORD_address=0x4a76c,field_WORD=0x56,destination=A6+0x56,
        outer_return=dict(logical=S,canonical=canonical(S),value=RETURN),configured_initial_SR=0x2000,
        initial_stack_slots=[dict(logical=a,canonical=canonical(a),size=n,value=v) for a,n,v in setup if S-8<=a<=S],
        initial_setup=[dict(address=a,size=n,value=v) for a,n,v in setup],synthetic_script=True,natural_reachability='unknown')
    pvc=bytearray(8192);pvc[0x1ff0:0x1ff4]=bytes.fromhex('00a01000')
    return dict(ram=bytes(ram),pvc=bytes(pvc),regs=regs,sr=0x2000,bank_base=0x200000,details=details)


class Observer:
    def __init__(self,program):self.program=program;self.cpu=None;self.backing=None
    def prepare(self,fx):
        self.fx=fx;self.backing=(ctypes.c_ubyte*SIZE).from_buffer_copy(fx['ram'])
        c=unicorn.Uc(unicorn.UC_ARCH_M68K,unicorn.UC_MODE_BIG_ENDIAN);c.ctl_set_cpu_model(m.UC_CPU_M68K_M68000)
        c._ram_backing=self.backing
        c.mem_map(0,RAM,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC);c.mem_write(0,self.program[:RAM])
        for i in range(16):c.mem_map_ptr(RAM+i*SIZE,SIZE,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE,ctypes.addressof(self.backing))
        c.mem_map(0x200000,0xfe000,unicorn.UC_PROT_READ);c.mem_write(0x200000,self.program[0x200000:0x2fe000])
        c.mem_map(PVC,8192,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE);c.mem_write(PVC,fx['pvc'])
        allowed=set()
        for a,b in RANGES:allowed.update(r['cpu_address'] for r in disassemble_range(self.program,a,b-a,a))
        self.pcs=[];self.events=[];self.boundaries=[];self.invalid=[];self.interrupts=[];self.guard=None;self.pc=None
        def stop(problem,**fields):self.guard=dict(problem=problem,pc=self.pc,**fields);c.emu_stop()
        def code(cpu,pc,size,user):
            self.pc=pc;self.pcs.append(pc)
            if pc==RETURN:cpu.emu_stop();return
            if pc==WAIT and self.allow_wait:
                if int.from_bytes(cpu.mem_read(HEAD,2),'big')==(cpu.reg_read(REG_IDS['d1'])&65535):
                    self.wait_visits+=1
                    if self.wait_visits==2:cpu.emu_stop();return
                else:self.wait_visits=0
            if pc not in allowed:stop('unsupported_code_target',target=pc);return
            if pc==0x4a43c and cpu.reg_read(REG_IDS['a1'])!=0x3679e:
                stop('unsupported_callback_before_JSR',target=cpu.reg_read(REG_IDS['a1']));return
            opcode=int.from_bytes(cpu.mem_read(pc,2),'big')
            if opcode==0x4afc or 0x4e40<=opcode<=0x4e4f:stop('unsupported_TRAP',opcode=opcode);return
            if pc in BOUNDARIES:
                self.boundaries.append(dict(pc=pc,registers=self.regs(),a7=cpu.reg_read(REG_IDS['a7']),
                    stack_window_address=S-32,stack_window=bytes(cpu.mem_read(S-32,36)).hex()))
            for at,access,width in isolated.ACCESS:
                if pc!=at:continue
                if pc in (0x4a384,0x4a392,0x4a39e):address=cpu.reg_read(REG_IDS['a1'])
                else:
                    index='d0' if pc in (0x4a38e,0x4a3a4) else 'd7'
                    base='a6' if pc==0x4a3a4 else 'a2'
                    address=(cpu.reg_read(REG_IDS[base])+isolated.s16(cpu.reg_read(REG_IDS[index])))&0xffffffff
                units,problem=isolated.classify(access,address,width,0x200000,len(self.program))
                if problem:stop(problem,address=address,size=width,access=access,units=units)
        def access(kind,address,size,value=None):
            region=isolated.region(address,0x200000,len(self.program))
            if region['kind'] not in isolated.READABLE:stop('unsupported_data_address',address=address,size=size);return
            if kind=='write' and not(RAM<=address and address+size<=0x200000) and not(PVC<=address and address+size<=0x300000):
                stop('unsupported_write_address',address=address,size=size);return
            before=bytes(c.mem_read(address,size))
            data=before if kind=='read' else (value&((1<<(size*8))-1)).to_bytes(size,'big')
            self.events.append(dict(pc=self.pc,hook_pc=c.reg_read(REG_IDS['pc']),access=kind,address=address,size=size,
                bytes=data.hex(),before=before.hex(),region=region,
                stack_overlap=any(0x10efb0<=canonical(address+i)<0x10f000 for i in range(size)) if RAM<=address<0x200000 else False))
        def read(cpu,kind,address,size,value,user):access('read',address,size)
        def write(cpu,kind,address,size,value,user):access('write',address,size,value)
        def invalid(cpu,kind,address,size,value,user):
            self.invalid.append(dict(pc=self.pc,access=kind,address=address,size=size));stop('unmapped_or_protected_access',address=address,size=size);return False
        def interrupt(cpu,number,user):self.interrupts.append(dict(pc=self.pc,number=number));stop('CPU_interrupt',number=number)
        for hook,callback in ((unicorn.UC_HOOK_CODE,code),(unicorn.UC_HOOK_MEM_READ,read),(unicorn.UC_HOOK_MEM_WRITE,write),
                             (unicorn.UC_HOOK_MEM_INVALID,invalid),(unicorn.UC_HOOK_INTR,interrupt)):c.hook_add(hook,callback)
        self.cpu=c
        c.reg_write(REG_IDS['sr'],fx['sr'])
        c.reg_write(REG_IDS['a7'],S)
        for key in isolated.REG_NAMES:c.reg_write(REG_IDS[key],fx['regs'][key])
        c.reg_write(REG_IDS['pc'],ENTRY)
        self.incoming=self.regs();return self
    def regs(self):
        keys=isolated.REG_NAMES+('a7','pc')
        return {key:self.cpu.reg_read(REG_IDS[key]) for key in keys}
    def run(self,allow_wait=False):
        self.pcs=[];self.events=[];self.boundaries=[];self.invalid=[];self.interrupts=[];self.guard=None;self.pc=None
        self.wait_visits=0;self.allow_wait=allow_wait
        self.incoming=self.regs();before=bytes(self.backing);pvc_before=bytes(self.cpu.mem_read(PVC,8192))
        start=self.cpu.reg_read(REG_IDS['pc']);error=None
        try:self.cpu.emu_start(start,0xffffff,count=CAP)
        except unicorn.UcError as exc:error=str(exc)
        result=dict(incoming=self.incoming,outgoing=self.regs(),pcs=self.pcs,events=self.events,boundaries=self.boundaries,
            invalid=self.invalid,interrupts=self.interrupts,guard=self.guard,error=error,ram_after=bytes(self.backing),
            ram_before=before,pvc_before=pvc_before,wait_visits=self.wait_visits,
            pvc_after=bytes(self.cpu.mem_read(PVC,8192)),mirrors_coherent=all(bytes(self.cpu.mem_read(RAM+i*SIZE,SIZE))==bytes(self.backing) for i in range(16)),
            fixed_ROM_unchanged=bytes(self.cpu.mem_read(0,RAM))==self.program[:RAM],
            bank2_ROM_unchanged=bytes(self.cpu.mem_read(0x200000,0xfe000))==self.program[0x200000:0x2fe000])
        return result
    def close(self):self.cpu=None;self.backing=None


def check(program,case,fx,native):
    assert native['guard'] is None and native['error'] is None and not native['invalid'] and not native['interrupts'],(case,native['guard'],native['error'])
    assert native['outgoing']['pc']==RETURN and native['outgoing']['a7']==S+4
    assert all(native[k] for k in ('mirrors_coherent','fixed_ROM_unchanged','bank2_ROM_unchanged'))
    replay=bytearray(fx['ram']);pvc=bytearray(fx['pvc']);ports=[];bank=0x200000;ff8=0xa0;ff9=0x1000
    first=None;second=None;stack_writes=[]
    for event in native['events']:
        a,n=event['address'],event['size'];data=bytes.fromhex(event['bytes'])
        assert event['pc']==event['hook_pc']
        if RAM<=a and a+n<=0x200000:
            before=bytes(replay[(a+i)&65535] for i in range(n))
            assert before.hex()==event['before'],event
            if event['access']=='write':
                for i,b in enumerate(data):replay[(a+i)&65535]=b
            else:assert data==before
        elif a<PVC and a>=0x200000:
            assert event['access']=='read' and bank==0x200000
            assert data==program[bank+a-0x200000:bank+a-0x200000+n]
        elif a<RAM:
            assert event['access']=='read' and data==program[a:a+n]
        else:
            assert event['access']=='write' and n==2 and a in (0x2ffff0,0x2ffff2),event
            assert bytes(pvc[a-PVC:a-PVC+n]).hex()==event['before'];pvc[a-PVC:a-PVC+n]=data
            v=int.from_bytes(data,'big')
            if a==0x2ffff0:ff8=v
            else:ff9=v
            bank,ff8,ff9=pvc_bank_update(ff8,ff9)
            ports.append(dict(pc=event['pc'],address=a,size=n,value=v,bank_after=bank,ff8_after=ff8,ff9_after=ff9))
        if event['access']=='write' and event['stack_overlap']:stack_writes.append(event)
        if event['pc']==0x4a39a and event['access']=='read':
            assert a==fx['details']['first_effective_address'] and n==4;first=event
        if event['pc']==0x4a3a0 and event['access']=='read':second=event
    assert bytes(replay)==native['ram_after'] and bytes(pvc)==native['pvc_after']
    assert first is not None and second is not None and bank==0x200000
    assert len(ports)%2==0
    for first_port,second_port in zip(ports[0::2],ports[1::2]):
        assert first_port['address']==0x2ffff2 and second_port['address']==0x2ffff0 and second_port['value']==0
        assert second_port['bank_after']==0x200000
    pointer=int.from_bytes(bytes.fromhex(first['bytes']),'big')
    assert second['address']==pointer
    after_first=next(b for b in native['boundaries'] if b['pc']==0x4a39e)
    assert after_first['registers']['a2']==pointer
    slot=first['address'];canon=canonical(slot)
    earlier=[e for e in native['events'][:native['events'].index(first)] if e['access']=='write' and RAM<=e['address']<0x200000 and
        set(canonical(e['address']+i) for i in range(e['size']))&set(canon+i for i in range(4))]
    initial=fx['ram'][canon&65535:(canon&65535)+4].hex()
    aliases=[]
    if SCRIPT<=pointer<fx['details']['script_end_exclusive']:aliases.append('synthetic script bytes')
    if A6<=pointer<A6+0x100:aliases.append('object bytes')
    if pointer==0x4a108:aliases.append('original fixed ROM instruction bytes read as data')
    if pointer==0x104800:aliases.append('declared initial RAM data')
    assert len(aliases)==1,(case,pointer)
    required={'14-03-RTS':0x3679e,'30-early-sound':0x3b06,'10-skip-draw':0x4a270,'04-early-sentinel':0x4a124}
    assert required[case['prefix']] in native['pcs']
    if case['prefix']=='10-skip-draw':assert 0x4a26c not in native['pcs']
    if case['prefix']=='04-early-sentinel':assert 0x4a1dc not in native['pcs']
    return dict(first_read=first,first_pointer=pointer,second_read=second,pointer_alias=aliases,
        slot_initial_bytes=initial,slot_prior_writes=earlier,stack_writes=stack_writes,ports=ports,
        final_modeled_bank=bank,final_A7=native['outgoing']['a7'],returned=True,
        stack_window_after=dict(logical=S-32,canonical=canonical(S-32),bytes=native['ram_after'][(S-32)&65535:(S+4)&65535].hex()))


def run_case(program,case):
    fx=fixture(program,case);observer=Observer(program)
    try:native=observer.prepare(fx).run()
    finally:observer.close()
    evidence=check(program,case,fx,native)
    return fx,native,evidence


def replay_phase(program,native):
    """Full phase memory replay from actual incoming RAM and ordered native events."""
    ram=bytearray(native['ram_before']);pvc=bytearray(native['pvc_before'])
    for e in native['events']:
        a,n=e['address'],e['size'];data=bytes.fromhex(e['bytes'])
        assert e['pc']==e['hook_pc']
        if RAM<=a and a+n<=0x200000:
            before=bytes(ram[(a+i)&65535] for i in range(n))
            assert e['before']==before.hex()
            if e['access']=='read':assert data==before
            else:
                for i,b in enumerate(data):ram[(a+i)&65535]=b
        elif a<RAM:
            assert e['access']=='read' and data==program[a:a+n]
        elif PVC<=a and a+n<=0x300000:
            assert e['access']=='write' and a in (0x2ffff0,0x2ffff2) and n==2
            assert e['before']==bytes(pvc[a-PVC:a-PVC+n]).hex();pvc[a-PVC:a-PVC+n]=data
        else:raise AssertionError(e)
    assert bytes(ram)==native['ram_after'] and bytes(pvc)==native['pvc_after']
    assert native['guard'] is None and native['error'] is None and not native['invalid'] and not native['interrupts']
    assert all(native[k] for k in ('mirrors_coherent','fixed_ROM_unchanged','bank2_ROM_unchanged'))


def run_wait_chain(program):
    case=dict(prefix='30-early-sound',first=0xeff0,label='30-highwait-host-modifies-shared-stack')
    fx=fixture(program,case);ram=bytearray(fx['ram'])
    # Explicit setup equivalent to existing direct-sound high wait: full WORD
    # ring flushes0455 while newly requested04a0 is appended. No external read.
    setup=[(SCRIPT+2,2,0x04a0),(HEAD,2,1),(TAIL,2,0),(0x104d7b,1,0),
        (0x104d8a,2,0),(0x104d8c,2,6),(0x104d82,2,0x0455),(0x104d84,2,0x0566),
        (0x104d86,2,0x0677),(0x104d88,2,0x0788),(0x100012,1,0),(0x10fd82,1,0),
        (0x10fe80,1,0),(0x10fd8d,1,1),(0x104d7e,1,0),(0x10f001,1,0),
        (0x104904,2,0),(0x104906,2,0x100)]
    for a,n,v in setup:put(ram,a,n,v)
    fx=dict(fx,ram=bytes(ram),details=dict(fx['details'],script_raw=bytes(ram[SCRIPT&65535:(fx['details']['script_end_exclusive'])&65535]).hex(),
        prefix_raw=bytes(ram[SCRIPT&65535:(SCRIPT+4)&65535]).hex(),wait_setup=[dict(address=a,size=n,value=v) for a,n,v in setup]))
    obs=Observer(program)
    try:
        obs.prepare(fx);begin=obs.run(allow_wait=True);replay_phase(program,begin)
        assert begin['outgoing']['pc']==WAIT and begin['outgoing']['a7']==S-18 and begin['wait_visits']==2
        assert int.from_bytes(begin['ram_after'][(S-18)&65535:(S-14)&65535],'big')==0x3c00
        assert int.from_bytes(begin['ram_after'][(S-12)&65535:(S-8)&65535],'big')==0x4a2ec
        assert begin['ram_after'][(S-14)&65535]==0x55
        before_regs=obs.regs();padding=begin['ram_after'][(S-13)&65535]
        changes=[dict(address=canonical(S-14),size=1,value=0x77,purpose='savedlow live BYTE pop'),
                 dict(address=canonical(S-8),size=4,value=0x104900,purpose='savedouterA0 live LONG restore'),
                 dict(address=HEAD,size=2,value=0x40,purpose='release native high-byte polling')]
        changed=bytearray(begin['ram_after'])
        for e in changes:
            a,n,v=e['address'],e['size'],e['value'];e['before']=changed[a&65535:(a&65535)+n].hex()
            raw=v.to_bytes(n,'big');obs.cpu.mem_write(a,raw);put(changed,a,n,v)
        assert obs.regs()==before_regs  # no register/PC/SP mutation between phases
        assert obs.cpu.mem_read(canonical(S-13),1)[0]==padding
        release=obs.run();replay_phase(program,release)
        assert release['ram_before']==bytes(changed)
        assert release['incoming']==begin['outgoing']
        assert release['outgoing']['pc']==RETURN and release['outgoing']['a7']==S+4
        low_pop=[e for e in release['events'] if e['pc']==0x3c00 and e['access']=='read']
        assert len(low_pop)==1 and low_pop[0]['address']==S-14 and low_pop[0]['size']==1 and low_pop[0]['bytes']=='77'
        boundary=next(e for e in release['boundaries'] if e['pc']==0x4a2ec)
        restored=next(e for e in release['boundaries'] if e['pc']==0x4a276)
        assert restored['registers']['a0']==0x104900
        publications=[e for e in release['events'] if e['pc']==0x4a278 and e['access']=='write']
        assert [e['address'] for e in publications]==[0x104900,0x104900]
        assert [e['bytes'] for e in publications]==['00106004','0010600a']
        first=next(e for e in release['events'] if e['pc']==0x4a39a and e['access']=='read')
        second=next(e for e in release['events'] if e['pc']==0x4a3a0 and e['access']=='read')
        assert first['address']==S-8 and first['bytes']=='00104900'
        assert second['address']==0x104900 and second['bytes']=='00106004'
        enqueues=[e for e in release['events'] if e['pc']==0x3af0 and e['access']=='write']
        assert [e['bytes'] for e in enqueues]==['04','77']
        assert release['ram_after'][(S-13)&65535]==padding
        bank=0x200000;ff8=0xa0;ff9=0x1000;device_ports=[]
        for phase_name,phase in (('begin-highwait',begin),('release-mutated-stack',release)):
            for e in phase['events']:
                if e['access']!='write' or e['address'] not in (0x2ffff0,0x2ffff2):continue
                value=int(e['bytes'],16)
                if e['address']==0x2ffff0:ff8=value
                else:ff9=value
                bank,ff8,ff9=pvc_bank_update(ff8,ff9)
                device_ports.append(dict(phase=phase_name,pc=e['pc'],address=e['address'],size=e['size'],value=value,bank_after=bank,ff8_after=ff8,ff9_after=ff9))
        assert len(device_ports)==4 and bank==0x200000
        for first_port,second_port in zip(device_ports[0::2],device_ports[1::2]):
            assert first_port['address']==0x2ffff2 and second_port['address']==0x2ffff0 and second_port['bank_after']==0x200000
        evidence=dict(actual_PVC_fold=device_ports,final_modeled_bank=bank,wait_PC=WAIT,wait_A7=S-18,host_changes=changes,padding_byte_before_and_after=padding,
            resumed_same_CPU=True,registers_unchanged_between_phases=True,actual_low_pop=low_pop[0],
            actual_enqueues=enqueues,outer_restore_before_MOVEM=boundary,restored_A0=restored['registers']['a0'],
            alternate_publication=publications[0],first_read=first,second_read=second,
            metadata_difference='Original pops mutated shared-RAM savedlow and A0. Existing host-only continuation metadata does not consume these stack addresses.')
        return fx,[begin,release],evidence
    finally:obs.close()


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert sha(program)==isolated.SOURCE_SHA256
    program=bytes(program);rom=root/source['path'];rom_before=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    folder=root/'artifacts/animation_shared_stack_native';folder.mkdir(parents=True,exist_ok=True)
    report_path=folder/'observation.json';report_path.unlink(missing_ok=True)
    instructions=[]
    for a,b in RANGES:instructions.extend(disassemble_range(program,a,b-a,a))
    for row in instructions:assert bytes.fromhex(row['raw'])==program[row['rom_offset']:row['rom_offset']+row['size']]
    (folder/'source.json').write_text(json.dumps(dict(source=source,entry=ENTRY,outer_return=RETURN,initial_A7=S,ranges=RANGES,
        instructions=instructions,callback_slot=dict(cpu=0x4a50c,ROM_offset=0x4a50c,target=0x3679e,target_raw=program[0x3679e:0x367a0].hex()),
        field_table=dict(cpu=0x4a76c,ROM_offset=0x4a76c,first_two_WORDs=program[0x4a76c:0x4a770].hex()),pinned_reference=isolated.pinned_reference(root)),indent=2)+'\n')
    names={'tools/observe_animation_shared_stack.py','tools/address_map.py','tools/observe_animation_banked_handler.py','tools/disassemble_program.py',
        'docs/analysis/animation-stack-access-inventory.md','artifacts/animation_shared_stack_native/source.json','extracted/program/manifest.json',source['path']}
    for module in tuple(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.suffix=='.py' and root/'tools' in path.parents:names.add(str(path.relative_to(root)))
    pinned=isolated.pinned_reference(root)
    names.update('artifacts/reference/'+name for name in pinned['files'])
    inputs={name:sha((root/name).read_bytes()) for name in sorted(names)}
    rows=[];artifacts={}
    for index,case in enumerate(cases()):
        fx,native,evidence=run_case(program,case);fx2,native2,evidence2=run_case(program,case)
        assert (fx,native,evidence)==(fx2,native2,evidence2),case
        stem='case_%04d'%index
        trace={k:native[k] for k in ('pcs','events','boundaries','guard','invalid','interrupts','error')}
        portbytes=b''.join(struct.pack('>BII',p['size'],p['address'],p['value']) for p in evidence['ports'])
        payloads={stem+'_ram_before.bin':fx['ram'],stem+'_ram_after.bin':native['ram_after'],stem+'_pvc_before.bin':fx['pvc'],
            stem+'_pvc_after.bin':native['pvc_after'],stem+'_ports.bin':portbytes,stem+'_trace.json':(json.dumps(trace,indent=2)+'\n').encode()}
        for name,data in payloads.items():(folder/name).write_bytes(data);artifacts[name]=sha(data)
        rows.append(dict(case_index=index,case=case,fixture=fx['details'],incoming=native['incoming'],outgoing=native['outgoing'],
            evidence=evidence,reproduced_twice=True,checks={k:native[k] for k in ('mirrors_coherent','fixed_ROM_unchanged','bank2_ROM_unchanged')},
            artifacts={name:sha(data) for name,data in payloads.items()}))
    wait_fx,wait_phases,wait_evidence=run_wait_chain(program)
    wait_fx2,wait_phases2,wait_evidence2=run_wait_chain(program)
    assert (wait_fx,wait_phases,wait_evidence)==(wait_fx2,wait_phases2,wait_evidence2)
    wait_rows=[]
    for label,native in zip(('begin-highwait','release-mutated-stack'),wait_phases):
        stem='wait_'+label
        trace={k:native[k] for k in ('pcs','events','boundaries','guard','invalid','interrupts','error')}
        ports=[e for e in native['events'] if e['access']=='write' and e['address'] in (0x2ffff0,0x2ffff2)]
        payloads={stem+'_ram_before.bin':native['ram_before'],stem+'_ram_after.bin':native['ram_after'],
            stem+'_pvc_before.bin':native['pvc_before'],stem+'_pvc_after.bin':native['pvc_after'],
            stem+'_ports.bin':b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in ports),
            stem+'_trace.json':(json.dumps(trace,indent=2)+'\n').encode()}
        for name,data in payloads.items():(folder/name).write_bytes(data);artifacts[name]=sha(data)
        wait_rows.append(dict(phase=label,incoming=native['incoming'],outgoing=native['outgoing'],
            artifacts={name:sha(data) for name,data in payloads.items()}))
    wait_group=dict(chains=1,phases=2,fresh_CPU_chains=2,reproduced_twice=True,fixture=wait_fx['details'],
        evidence=wait_evidence,rows=wait_rows)
    for name,value in inputs.items():assert sha((root/name).read_bytes())==value,name
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_before
    library=Path(uclib._name)
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,cases=len(rows),nonwait_fresh_CPU_runs=len(rows)*2,total_fresh_CPU_runs=len(rows)*2+2,total_phase_executions=len(rows)*2+4,rows=rows,shared_stack_wait_group=wait_group,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,cpu='UC_CPU_M68K_M68000',library=str(library),library_sha256=sha(library.read_bytes()),
            wrapper_sha256=sha(Path(inspect.getfile(unicorn.Uc)).read_bytes())),
        original_ROM_unchanged=True,register_injection_after_begin=False,in_hook_SR_access=False,SR_read_at_any_phase=False,configured_initial_SR=0x2000,scratch_stack=False,
        RAM_mapping='100000..1fffff16mirrors share retained ctypes64KiB backing; outer return is part of incoming RAM',
        PVC_mapping='Writable8192byte fixture; native writes recorded. Side-effectful MAME bank fold is metadata, not CPU read substitution.',
        CCR_observed=False,Cpp_comparison_performed=False,whole40_claim=False,failure=None,
        limitations=['Synthetic controlled scripts/object/registers, not natural caller or game reachability.',
            'Unmodified whole49fc6 executes through actual outer RTS, with shared RAM stack effects included in full RAM.',
            'Four nonwait prefix paths and two residual stack slots plus one declared same-CPU highwait host-mutation chain; no arbitrary callback coverage.',
            'Cart vector view assumed; no BIOS selection, genericMMIO,24-bit alias adapter,address-error exception or timing proof.',
            'Fixed bank2 mapping only; all completed actual PVC pairs fold to bank2. Raw writablePVC bytes do not emulate side effects for reads; these fixtures have no PVC reads.',
            'SR is configured once before A7; no SR read occurs before, during, between or after phases. No observed system-SR/CCR/carry equivalence claim.'])
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(nonwait_cases=len(rows),wait_chains=1,wait_phases=2,total_fresh_CPU_runs=len(rows)*2+2,artifacts=len(artifacts),sha256=sha(report_path.read_bytes()))))


if __name__=='__main__':main()
