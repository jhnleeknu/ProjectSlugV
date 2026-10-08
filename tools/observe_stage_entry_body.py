"""Whole immutable original47a94 initialization body and tail480bc observations.
Pre-entry RAM starts from actual2790/3ef2. No callee patches or in-call resets.
"""
import collections
import json
from pathlib import Path
import struct
import zlib
import gzip
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ, UC_HOOK_MEM_INVALID, UC_HOOK_INTR, m68k_const as m
from verify_stage_frame import BASE, STACK, RETURN, KEYS, REGS, ARGS, SAVED, ENTRY, SPRITE_WAIT, SOUND_WAIT, EXTERNAL, CALLEES, sha, put, initial
from verify_object_reset import make_cpu
from disassemble_program import load_verified_program
from observe_scene_general_initialization import fixture as initializer_fixture, PORTS
from observe_scene_frame_execution import oracle_provenance
from verify_stage_catalog import SOURCE_SHA256, verify_resources
BODY_ENTRY=0x47a94
PREFIX=(BODY_ENTRY,0x1a5a4,0xe8a1c,0x48398,0x30f4,0x4839e,0x47aca,0x47adc,0xe905c,0x47ae6,ENTRY)
STATE_KEYS=KEYS+ARGS+('a5','body_phase')


def build_cases(program,groups):
    records=[r['source_cpu_address'] for g in groups for r in g['records']]
    assert len(records)==len(set(records))==59
    cases=[dict(family='actual59-catalog-records',record=record,profile=profile,lookup=0,bank=2) for record in records for profile in (0,1)]
    null=next(record for record in records if int.from_bytes(program[record+10:record+14],'big')==0)
    nonnull=next(record for record in records if int.from_bytes(program[record+10:record+14],'big')!=0)
    for record in (null,nonnull):
        for lookup in range(8):cases.append(dict(family='lookup8-null-and-nonnull-event',record=record,profile=1,lookup=lookup,bank=2))
        cases.append(dict(family='initial-physical-bank3',record=record,profile=1,lookup=7,bank=3))
    for rising in (False,True):
        for target in range(1,3 if rising else 4):
            cases.append(dict(family='wholebody-sound-wait',record=nonnull,profile=1,lookup=7,bank=2,rising=rising,target=target))
    cases.append(dict(family='live-RAM-record-reread',record=nonnull,profile=1,lookup=7,bank=2))
    return cases


def prepare_case(root,program,case):
    ram,state,metadata=fixture(root,program,case['record'],case['profile'],case['lookup'])
    state['bank']=case['bank']
    if case['family']=='wholebody-sound-wait':
        for at in (0x12,0xfd82,0xfe80,0xfd8d,0x4d7e,0x4d7b):metadata['host_writes'].append(put(ram,at,1,0))
        for at,size,value in ((0xd490,1,int(case['rising'])),(0xd491,1,int(not case['rising'])),(0x4d82,2,0x455),(0x4d84,2,0x566),(0x4d86,2,0x677),(0x4d88,2,0x788),(0x4d8a,2,0),(0x4d8c,2,6),(0x4d74,2,case['target']),(0x4d76,2,0)):
            metadata['host_writes'].append(put(ram,at,size,value))
    if case['family']=='live-RAM-record-reread':
        for at,size,value in ((0xba6,4,0x10d420),(0xd422,4,0),(0xd426,4,0x106000),(0xd42a,4,0x106100),(0xd42e,2,0),(0x6100,4,0x106200),(0x6200,2,0)):
            metadata['host_writes'].append(put(ram,at,size,value))
    return ram,state,metadata


def provenance(root):
    names=['tools/'+n+'.py' for n in ('observe_stage_entry_body','verify_stage_frame','observe_scene_general_initialization','observe_scene_frame_execution','observe_stage_cue_frame','verify_stage_event_initialization','verify_stage_catalog','verify_object_reset','disassemble_program','pack_stage_cue_frame','pack_stage_cue_control')]
    return {n:sha((root/n).read_bytes()) for n in names}


def resources(root,program):
    from observe_scene_general_initialization import resources as scene_resources
    from observe_stage_cue_frame import resource_audit
    from verify_stage_event_initialization import resources as event_resources
    scene,metadata=scene_resources(root,program)
    events,event_metadata=event_resources(root,program)
    extras=resource_audit(root)
    groups=verify_resources(root/'extracted/runtime/stages',program,dict(path='extracted/program/maincpu.decrypted.be.bin',size=len(program),sha256=SOURCE_SHA256,byte_order='big'))
    files=[root/r['file'] for r in scene+events+extras if r['file'].endswith('.ms5d')]
    files += [root/'extracted/runtime/stages'/g['file'] for g in groups]
    files += [root/'extracted/runtime'/n for n in ('stage_input/default_masks.ms5d','player_record_lookup.ms5d','game_records.ms5d')]
    result=[];identities={}
    for path in files:
        data=path.read_bytes();magic,version,kind,cpu,rom,size,crc,reserved=struct.unpack('<4s7I',data[:32])
        assert magic==b'MS5D' and version==1 and kind in (1,2) and reserved==0 and len(data)==size+32 and zlib.crc32(data[32:])==crc
        assert data[32:]==program[rom:rom+size]
        identity=(kind,cpu,rom,size)
        if identity in identities:assert identities[identity]==data;continue
        identities[identity]=data
        result.append(dict(file=str(path.relative_to(root)),sha256=sha(data),kind=kind,cpu=cpu,rom=rom,size=size))
    metadata += event_metadata+[r for r in extras if not r['file'].endswith('.ms5d')]
    return result,metadata,groups


def fixture(root, program, record, profile=0, lookup=0):
    # The initializer fixture runs immutable original2790 and3ef2, not1a5a4.
    script=int.from_bytes(program[record+2:record+6], 'big')
    target=int.from_bytes(program[record+14:record+16], 'big')
    ram=initializer_fixture(program,dict(script=script,target=target,profile=profile,debug=0,available=True))
    base_sha=sha(ram); changes=[]
    for at in (0xcb8,0xda8): changes.append(put(ram,at,4,0x270e))
    for at in (0xd734,0xd738): changes.append(put(ram,at,4,0))
    changes += [put(ram,0xf001,1,0),put(ram,0xdc88,4,0x10db88)]
    for slot in range(8):
        at=0xd61a-0x2c*slot
        changes += [put(ram,at+0x26,4,0x80000000),put(ram,at+0x2a,2,0)]
    changes += [put(ram,0xd490,1,0),put(ram,0xd491,1,0),put(ram,0xba6,4,record),put(ram,0xfd8c,1,lookup)]
    regs=[0]*14 if profile==0 else [(0xabcd1234+i*0x1020304)&0xffffffff for i in range(14)]
    regs[-1]=0x100b30
    state=initial(regs); state.update(a5=0x108000,body_phase=0)
    return ram,state,dict(base_ram_sha256=base_sha,host_writes=changes,record=record,script=script,target=target,profile=profile,lookup=lookup)


class Observer:
    def __init__(self, program):
        self.program = program
        self.cpu = make_cpu(program)
        self.cpu.mem_map(0x200000, 0x200000)
        self.cpu.mem_map(0xd00000, 4096)
        self.baseline = self.cpu.context_save()
        self.bank = 2
        self.section = 0
        self.cue_status = 0
        self.external = 0
        self.pcs, self.writes, self.ports, self.reads, self.bank_reads, self.boundaries = [], [], [], [], [], []
        self.prefix=[]
        self.error = None
        self.wait_visits = 0

        def code(cpu, pc, size, user):
            self.pcs.append(pc)
            if pc == RETURN: cpu.emu_stop(); return
            if pc in PREFIX:
                self.prefix.append(dict(pc=pc,a5=cpu.reg_read(m.UC_M68K_REG_A5),a7=cpu.reg_read(m.UC_M68K_REG_A7),registers={k:cpu.reg_read(r)&0xffffffff for k,r in zip(KEYS,REGS)},live_record=int.from_bytes(cpu.mem_read(0x100ba6,4),'big'),port_count=len(self.ports)))
                if pc==0x48398:assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK-4
                if pc==0x30f4:assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK-8
            if pc in CALLEES:
                self.section = pc
                self.boundaries.append(dict(pc=pc, a7=cpu.reg_read(m.UC_M68K_REG_A7), a6=cpu.reg_read(m.UC_M68K_REG_A6)))
                assert cpu.reg_read(m.UC_M68K_REG_A7) == STACK-4
            if self.section == 0xe8a48:
                if pc == 0xcd58: self.cue_status = 1
                elif pc == 0xcdaa: self.cue_status = 0
                elif pc == 0xcd82: self.cue_status = 2
            if pc in (SPRITE_WAIT, SOUND_WAIT):
                address, reg = (0x108d34, m.UC_M68K_REG_D4) if pc == SPRITE_WAIT else (0x104d74, m.UC_M68K_REG_D1)
                equal = int.from_bytes(cpu.mem_read(address, 2), 'big') == (cpu.reg_read(reg)&65535)
                blocked = not equal if pc == SPRITE_WAIT else equal
                self.wait_visits = self.wait_visits+1 if blocked else 0
                if blocked and self.wait_visits == 2:
                    if pc == SPRITE_WAIT and self.section == 0xe8a48: self.cue_status = 3
                    cpu.emu_stop(); return
            word = int.from_bytes(cpu.mem_read(pc, 2), 'big')
            if word == 0x4afc or 0x4e40 <= word <= 0x4e4f:
                self.error = ('trap', pc, word); cpu.emu_stop()

        def write(cpu, access, address, size, value, user):
            value &= (1 << (size*8))-1
            if BASE <= address and address+size <= BASE+65536:
                self.writes.append(dict(pc=cpu.reg_read(m.UC_M68K_REG_PC), address=address, size=size, value=value)); return
            if STACK-4096 <= address and address+size <= STACK+4: return
            if address not in PORTS or (address in (0x2ffff2, 0x2ffff0) and size != 2):
                self.error = ('unexpected-write', address, size, value); cpu.emu_stop(); return
            self.ports.append((size, address, value))
            if address == 0x2ffff2:
                if value not in (0x1000, 0x2000): self.error = ('bank', value); cpu.emu_stop(); return
                self.bank = 2 if value == 0x1000 else 3
                cpu.mem_write(0x200000, program[self.bank*0x100000:self.bank*0x100000+0xffff0])

        def read(cpu, access, address, size, value, user):
            if address == EXTERNAL:
                assert size == 1
                cpu.mem_write(address, bytes([self.external]))
                self.reads.append(dict(address=address, size=size, value=self.external))
            elif 0x200000 <= address < 0x2ffff0:
                self.bank_reads.append(dict(pc=cpu.reg_read(m.UC_M68K_REG_PC), address=address, size=size, bank=self.bank))
            elif address < 0x400000 and address+size > 0x2ffff0:
                self.error = ('unexpected-MMIO-read', address, size); cpu.emu_stop()

        def invalid(cpu, access, address, size, value, user): self.error = ('invalid-memory', access, address, size); return False
        def intr(cpu, number, user): self.error = ('exception', number, cpu.reg_read(m.UC_M68K_REG_PC)); cpu.emu_stop()
        self.cpu.hook_add(UC_HOOK_CODE, code)
        self.cpu.hook_add(UC_HOOK_MEM_WRITE, write)
        self.cpu.hook_add(UC_HOOK_MEM_READ, read)
        self.cpu.hook_add(UC_HOOK_MEM_INVALID, invalid)
        self.cpu.hook_add(UC_HOOK_INTR, intr)

    def prepare(self, ram, state):
        cpu = self.cpu
        cpu.context_restore(self.baseline)
        cpu.mem_write(BASE, bytes(ram))
        self.bank, self.cue_status, self.section = state['bank'], state['cue_status'], 0
        cpu.mem_write(0x200000, self.program[self.bank*0x100000:self.bank*0x100000+0xffff0])
        cpu.reg_write(m.UC_M68K_REG_SR, 0x2000)
        cpu.reg_write(m.UC_M68K_REG_A5, state['a5'])
        cpu.reg_write(m.UC_M68K_REG_A7, STACK)
        cpu.mem_write(STACK-128, bytes(128)+RETURN.to_bytes(4, 'big'))
        for key, reg in zip(KEYS, REGS): cpu.reg_write(reg, state[key])
        cpu.reg_write(m.UC_M68K_REG_PC, BODY_ENTRY)

    def run(self, incoming, external):
        cpu = self.cpu
        self.external, self.wait_visits, self.error = external, 0, None
        for values in (self.pcs, self.writes, self.ports, self.reads, self.bank_reads, self.boundaries,self.prefix): values.clear()
        cpu.emu_start(cpu.reg_read(m.UC_M68K_REG_PC), 0xffffff, count=2000000)
        pc, sp = cpu.reg_read(m.UC_M68K_REG_PC), cpu.reg_read(m.UC_M68K_REG_A7)
        assert self.error is None and pc in (RETURN, SPRITE_WAIT, SOUND_WAIT), (self.error, hex(pc))
        state = initial([cpu.reg_read(r)&0xffffffff for r in REGS], self.bank, self.cue_status)
        def long(off): return int.from_bytes(cpu.mem_read(sp+off, 4), 'big')
        def word(off): return int.from_bytes(cpu.mem_read(sp+off, 2), 'big')
        if pc == SPRITE_WAIT:
            ret = long(0)
            if ret in (0x4b7da, 0x4b814):
                phase = 1 if ret == 0x4b7da else 2
                state.update(stage=1, buffer_phase=phase,
                    saved_a0=long(4), saved_d0=long(16) if phase == 1 else 0,
                    saved_d1=long(12) if phase == 1 else 0, saved_d7=long(8) if phase == 1 else 0,
                    saved_slot_d7=word(24 if phase == 1 else 12), saved_slot_a4=long(26 if phase == 1 else 14), saved_a6=long(30 if phase == 1 else 18))
                assert long(20 if phase == 1 else 8) == 0x4aad4
                assert long(34 if phase == 1 else 22) == 0x480d2
                assert sp == STACK-(38 if phase == 1 else 26)
            else:
                assert ret == 0xe8b58 and long(4) == 0x480ea, hex(ret)
                assert sp == STACK-8
                state.update(stage=2, cue_status=3)
        elif pc == SOUND_WAIT:
            kind, phase = {0x3c00: (1, 1), 0x2efc8: (1, 2), 0x3c70: (2, 1), 0x3c76: (2, 2), 0x2efda: (2, 3)}[long(0)]
            stacked = kind == 1 and phase == 1 or kind == 2 and phase < 3
            saved = cpu.mem_read(sp+4, 1)[0] if kind == 1 and stacked else word(4) if stacked else state['d0'] & (255 if kind == 1 else 65535)
            assert sp == STACK-(14 if stacked else 8)
            assert int.from_bytes(cpu.mem_read(STACK-8, 4), 'big') == {1: 0x2efc8, 2: 0x2efda}[kind]
            assert int.from_bytes(cpu.mem_read(STACK-4, 4), 'big') == 0x480f0
            state.update(stage=3, sound_kind=kind, sound_phase=phase, sound_saved=saved)
        else:
            assert sp == STACK+4
            assert int.from_bytes(cpu.mem_read(STACK, 4), 'big') == RETURN
        assert cpu.reg_read(m.UC_M68K_REG_A5) == 0x108000
        assert bytes(cpu.mem_read(0, BASE)) == self.program[:BASE]
        assert bytes(cpu.mem_read(0x200000, 0xffff0)) == self.program[self.bank*0x100000:self.bank*0x100000+0xffff0]
        if incoming['stage']:
            assert not any(p in self.pcs for p in CALLEES[:CALLEES.index({1: 0x4aa88, 2: 0xe8a48, 3: 0x2efa6}[incoming['stage']])+1])
            assert not self.reads
        state['external_reads'] = len(self.reads)
        state['a5'] = cpu.reg_read(m.UC_M68K_REG_A5)&0xffffffff
        state['body_phase'] = 1 if state['stage'] else 2
        ports = b''.join(struct.pack('>BII', *p) for p in self.ports)
        info = dict(final_pc=pc, final_a7=sp, final_a5=cpu.reg_read(m.UC_M68K_REG_A5), stack_hex=bytes(cpu.mem_read(STACK-64, 68)).hex(), pcs=self.pcs.copy(), boundaries=self.boundaries.copy(), prefix=self.prefix.copy(), RAM_writes=self.writes.copy(), physical_bank_reads=self.bank_reads.copy(), external_reads=self.reads.copy())
        return bytes(cpu.mem_read(BASE, 65536)), state, ports, info


def main():
    root=Path(__file__).resolve().parents[1]
    inputs=provenance(root);program,source=load_verified_program(root)
    assert sha(program)==SOURCE_SHA256
    rs,metadata,groups=resources(root,program)
    cases=build_cases(program,groups);oracle=oracle_provenance();observer=Observer(program)
    folder=root/'artifacts/stage_entry_body';folder.mkdir(parents=True,exist_ok=True)
    path=folder/'observation.json';path.unlink(missing_ok=True)
    rows=[];failure=None;pending=set()
    for index,case in enumerate(cases):
        ram,state,fixture_metadata=prepare_case(root,program,case);observer.prepare(ram,state);phases=[]
        def run(name,host_writes=None,external=0):
            nonlocal ram,state
            incoming=dict(state)
            for write in host_writes or []:observer.cpu.mem_write(write['address'],bytes.fromhex(write['hex']))
            assert bytes(observer.cpu.mem_read(BASE,65536))==ram
            output,result,ports,info=observer.run(incoming,external)
            replay=bytearray(ram)
            for write in info['RAM_writes']:replay[write['address']-BASE:write['address']-BASE+write['size']]=write['value'].to_bytes(write['size'],'big')
            assert bytes(replay)==output
            if incoming['body_phase']==0:
                assert [p['pc'] for p in info['prefix']]==list(PREFIX)
                after_lookup=next(p for p in info['prefix'] if p['pc']==0x47aca)
                assert after_lookup['registers']['d0']&255==program[0x30ec+case['lookup']]
                assert output[0xd67e:0xd680]==bytes((program[0x30ec+case['lookup']],255))
                assert output[0xb30:0xb34]==(0x47af0).to_bytes(4,'big')
                before_lookup=next(p for p in info['prefix'] if p['pc']==0x30f4)
                assert before_lookup['registers']['d0']&0xffff0000==after_lookup['registers']['d0']&0xffff0000
                flags=[w for w in info['RAM_writes'] if w['pc'] in (0x47ab4,0x47aba,0x47ac0)]
                assert [w['pc'] for w in flags]==[0x47ab4,0x47aba,0x47ac0]
                assert flags[1]['value']==flags[0]['value']|8 and flags[2]['value']==flags[1]['value']|32 and flags[2]['value']&0x2a==0x2a
                assert len([w for w in info['RAM_writes'] if w['pc']==0x47ae6 and w['address']==0x100b30])==1
                if case['family']=='live-RAM-record-reread':
                    cue=next(p for p in info['prefix'] if p['pc']==0xe8a1c)
                    events=next(p for p in info['prefix'] if p['pc']==0xe905c)
                    assert cue['registers']['a0']==0x00a00080
                    assert events['registers']['a0']==0 and events['registers']['d0']&65535==65535
            else:
                assert not info['prefix'] and not any(w['address'] in (0x100b30,0x10d683,0x10d67e,0x10d67f) for w in info['RAM_writes'])
            stem='native_%04d_%s'%(index,name);rfile=stem+'.bin';pfile=stem+'.ports.bin'
            (folder/rfile).write_bytes(output);(folder/pfile).write_bytes(ports)
            tracefile=stem+'.trace.json.gz'
            trace=dict(schema_version=1,pcs=info.pop('pcs'),RAM_writes=info.pop('RAM_writes'),physical_bank_reads=info.pop('physical_bank_reads'))
            packed=gzip.compress(json.dumps(trace,separators=(',',':')).encode(),mtime=0)
            (folder/tracefile).write_bytes(packed)
            info.update(trace_file=tracefile,trace_sha256=sha(packed),trace_schema_version=1,trace_format='gzip JSON pcs/RAM_writes/physical_bank_reads',instructions=len(trace['pcs']),RAM_write_count=len(trace['RAM_writes']),physical_bank_read_count=len(trace['physical_bank_reads']))
            phases.append(dict(name=name,incoming=incoming,host_writes=host_writes or [],external=external,input_ram_sha256=sha(ram),result=result,ram_file=rfile,ram_sha256=sha(output),ports_file=pfile,ports_sha256=sha(ports),port_count=len(ports)//9,**info))
            ram=bytearray(output);state={k:result[k] for k in STATE_KEYS}
        try:
            run('begin')
            if case['family']=='wholebody-sound-wait':
                assert (state['body_phase'],state['stage'],state['sound_kind'],state['sound_phase'])==(1,3,1 if case['rising'] else 2,case['target'])
                pending.add((state['sound_kind'],state['sound_phase']))
                saved=dict(state)
                writes=[put(ram,0xba6,4,0xffffffff),put(ram,0xb30,4,0xdeadbeef),put(ram,0xfd8c,1,0),put(ram,0xd683,1,0),put(ram,0xd67e,2,0x1234),put(ram,0xd491,1,0x71),put(ram,0x4d76,2,0x8000),put(ram,0x4d8a,2,0x8001)]
                run('hold-poisoned-prefix',writes,255);assert state==saved
                writes=[put(ram,0x4d74,2,0xffff)]
                run('release-poisoned-prefix',writes,255)
                assert state['body_phase']==2 and ram[0xb30:0xb34]==bytes.fromhex('deadbeef') and ram[0xd67e:0xd680]==bytes.fromhex('1234')
            else:assert state['body_phase']==2
        except Exception as error:
            failure=dict(case_index=index,fixture=case,error=repr(error),pc=observer.cpu.reg_read(m.UC_M68K_REG_PC),last_pcs=observer.pcs[-20:]);rows.append(dict(case_index=index,fixture=case,fixture_metadata=fixture_metadata,phases=phases));break
        rows.append(dict(case_index=index,fixture=case,fixture_metadata=fixture_metadata,phases=phases))
    assert inputs==provenance(root) and oracle==oracle_provenance()
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256
    for item in rs+metadata:assert sha((root/item['file']).read_bytes())==item['sha256']
    report=dict(source=source,inputs=inputs,oracle=oracle,resources=rs,metadata=metadata,cases=len(cases),completed_cases=len(rows) if failure is None else len(rows)-1,phases=sum(len(r['phases']) for r in rows),failure=failure,pending_sound_states=sorted(pending),program_code_modified=False,physical_bank_payload_modified=False,in_call_SR_read=False,results=rows,scope='Whole original47a94 initialization andtail480bc toRTS/actualsoundwait. Actual2790/3ef2 pre-entryRAM; no initializedhelper merges, no ROMpatch/calleestub/in-callreset. Full64KiBRAM15regs/physicalbank/orderedwatchdog+video+PVC/externalreads andnativewaitstack. SameCPU/CCR/stack onresume, explicitlistedhostbytesonly. Oracle stack0x1feffc is isolated outside compared64KiBRAM; no addressmasking/RAMmirror/hardwarestack equivalence claimed. A7/stack/CCR are native-only evidence outsideCLIstatecontract. CanonicalnoIRQsceneinitializerresets spriteconsumer/prepared/producer atcce0/cce8; these fixtures do not establish wholebodybuffer/cuewait reachability. Existing480bc component coverage is separate. No47af0callbackexecution/naturalscheduler/IRQ/play/CCRcycle/audiovisualequivalence claim.')
    path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(cases),completed_cases=report['completed_cases'],phases=report['phases'],failure=failure,sha256=sha(path.read_bytes()))))
    if failure:raise SystemExit(1)


if __name__=='__main__':main()
