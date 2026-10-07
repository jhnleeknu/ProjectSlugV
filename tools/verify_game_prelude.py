"""Native47570 sound prefix and IRQ-released3aea continuations, immutable ROM."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn import m68k_const as mc
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256,checked_resource

BASE,ENTRY,WAIT,DONE,RETURN,STACK=0x100000,0x47570,0x3aea,0x475a4,0xff000,0x1feffc
REGS=(mc.UC_M68K_REG_D0,mc.UC_M68K_REG_D1,mc.UC_M68K_REG_D3)
def put(ram,at,value): struct.pack_into('>H',ram,at,value&65535)
def word(ram,at): return struct.unpack_from('>H',ram,at)[0]
def empty_byte(): return dict(waiting=False,command=0,tail=0,next=0)
def empty_word(): return dict(kind=0,phase=0,low=0,cursor=0,waiting=False,command=0,tail=0,next=0)

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert source['sha256']==SOURCE_SHA256
    executable=root/'build/prepare_game';binary_sha=hashlib.sha256(executable.read_bytes()).hexdigest()
    folder=root/'artifacts/game_prelude';folder.mkdir(parents=True,exist_ok=True)
    inp,out,bank_in,bank_out,regs_in,ports_out,report=[folder/name for name in ('input.bin','cpp.bin','banks.bin','cpp.banks.bin','regs.bin','cpp.ports.bin','verification.json')]
    report.unlink(missing_ok=True)
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000);cpu.mem_map(0xd00000,4096)
    cpu.mem_write(0x200000,program[0x200000:0x300000])
    state={'mode':'prelude','external':0,'status':0,'waits':0}
    reads,ports,paths,rows,irq_rows,sequences,negatives,integrations=[],[],[],[],[],[],[],[]
    def write(cpu,access,address,size,value,user):
        if address in (0x320000,0x300001,0x2ffff0,0x2ffff2,0x3a0001,0x3a0011):
            ports.append((size,address,value&((1<<(size*8))-1)))
        elif not (BASE<=address and address+size<=BASE+65536) and not (0x1f8000<=address and address+size<=0x1ff000):
            raise ValueError('Unexpected native write '+repr((hex(address),size,value)))
    def read(cpu,access,address,size,value,user):
        assert size==1 and address in (0x320000,0xd00046)
        sample=state['external'] if address==0xd00046 else state['status']
        cpu.mem_write(address,bytes([sample]));reads.append((size,address,sample))
    def code(cpu,address,size,user):
        if address in (ENTRY,0x3af8,0x3d3a,0x3d44): paths.append(address)
        if state['mode']=='startup' and address==0xc584: cpu.emu_stop()
        elif state['mode']=='handoff' and address==ENTRY: cpu.emu_stop()
        elif state['mode']=='prelude':
            if address==WAIT:
                if word(cpu.mem_read(BASE,65536),0x4d74)==(cpu.reg_read(mc.UC_M68K_REG_D1)&65535):
                    state['waits']+=1
                    if state['waits']==2: cpu.emu_stop()
                else: state['waits']=0
            elif address==DONE: cpu.emu_stop()
        elif address==RETURN: cpu.emu_stop()
    cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_CODE,code)
    cpu.hook_add(UC_HOOK_MEM_READ,read,begin=0x320000,end=0x320000);cpu.hook_add(UC_HOOK_MEM_READ,read,begin=0xd00046,end=0xd00046)
    def fixture(head=0,tail=0,bytehead=0,bytetail=0,oldest=0x0455):
        ram=bytearray(hashlib.shake_256(b'game-prelude-fixture:'+len(rows).to_bytes(4,'big')).digest(65536))
        put(ram,0x4d8a,head);put(ram,0x4d8c,tail);put(ram,0x4d74,bytehead);put(ram,0x4d76,bytetail)
        struct.pack_into('>4H',ram,0x4d82,oldest,0x0566,0x0677,0x0888)
        for at in (0x12,0xfd82,0xfe80,0xfd8d,0x4d7e,0xf001,0x4d7b,0xf003,0x1b,0x19,0x14): ram[at]=0
        put(ram,0xd68c,0);struct.pack_into('>I',ram,0x81c,0x10081c)
        for index in range(128): ram[0x4cf4+index]=index//2
        return ram
    def initial(entry=ENTRY,d0=0xffffffff): return dict(next_pc=entry,d0=d0,d1=0xabcd1234,d3=0x9876fedc,phase=0,word=empty_word(),byte=empty_byte())
    def arguments(pending,external):
        command=[str(executable),'--state']+[str(pending[key]) for key in ('next_pc','d0','d1','d3','phase')]
        if pending['word']['waiting']: command+=['--word']+[str(pending['word'][key]) for key in ('phase','low','cursor','command','tail','next')]
        if pending['byte']['waiting']: command+=['--byte']+[str(pending['byte'][key]) for key in ('command','tail','next')]
        return command+[str(external),str(inp),str(out)]
    def compare(ram,pending=None,context=None,external=0,profile='matrix'):
        pending=pending or initial();cpu.mem_write(BASE,bytes(ram))
        if context is None:
            for reg,value in ((mc.UC_M68K_REG_SR,0x2000),(mc.UC_M68K_REG_A5,0x108000),(mc.UC_M68K_REG_A6,0x1008e4),(mc.UC_M68K_REG_A7,STACK)):
                cpu.reg_write(reg,value)
            cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        else: cpu.context_restore(context)
        entry_sp=cpu.reg_read(mc.UC_M68K_REG_A7)
        if pending['next_pc']==WAIT:
            stack_ret=int.from_bytes(cpu.mem_read(entry_sp,4),'big');entry_sp+={0x3c00:10,0x4759e:4,0x3d4c:12,0x3d42:8}[stack_ret]
        for reg,key in zip(REGS,('d0','d1','d3')): cpu.reg_write(reg,pending[key])
        state.update(mode='prelude',external=external,waits=0);reads.clear();ports.clear();paths.clear()
        cpu.emu_start(pending['next_pc'],RETURN,count=100000)
        pc=cpu.reg_read(mc.UC_M68K_REG_PC);assert pc in (WAIT,DONE),hex(pc)
        result=dict(next_pc=pc,d0=cpu.reg_read(REGS[0])&0xffffffff,d1=cpu.reg_read(REGS[1])&0xffffffff,d3=cpu.reg_read(REGS[2])&0xffffffff,phase=4,external_reads=len(reads),word=empty_word(),byte=empty_byte())
        assert not ports and result['d3']==pending['d3'] and result['d1']>>16==pending['d1']>>16
        expected_reads=int(pending['phase']==0 and ram[0x12]==1 and ram[0xfd82]!=0 and ram[0xfe80]==0)
        assert reads==([(1,0xd00046,external)] if expected_reads else [])
        if pc==WAIT:
            sp=cpu.reg_read(mc.UC_M68K_REG_A7);ret=int.from_bytes(cpu.mem_read(sp,4),'big')
            assert sp==entry_sp-{0x3c00:10,0x4759e:4,0x3d4c:12,0x3d42:8}[ret]
            captured=dict(waiting=True,command=cpu.reg_read(REGS[0])&255,tail=cpu.reg_read(mc.UC_M68K_REG_A0)-BASE-0x4cf4,next=cpu.reg_read(REGS[1])&65535)
            if ret in (0x3c00,0x4759e):
                phase=1 if ret==0x3c00 else 2
                result['phase']=1
                result['word'].update(captured,kind=1,phase=phase,low=cpu.mem_read(sp+4,1)[0] if phase==1 else captured['command'],cursor=0)
            else:
                assert ret in (0x3d4c,0x3d42),hex(ret)
                result['phase']=2 if ret==0x3d4c else 3;result['byte']=captured
            assert state['waits']==2
        else:
            assert result['d0']&65535==0x720
            assert cpu.reg_read(mc.UC_M68K_REG_A7)==entry_sp
        if pending['next_pc']==0x47594:
            assert all(expected_byte==cpu.mem_read(BASE+at,1)[0] for at,expected_byte in ((at,ram[at]) for at in (0xd683,0xd694,0xd69c)))
        expected_high=0 if pending['next_pc']==ENTRY else pending['d0']&0xffff0000
        assert result['d0']&0xffff0000==expected_high
        expected=bytes(cpu.mem_read(BASE,65536))
        inp.write_bytes(ram);actual=subprocess.run(arguments(pending,external),capture_output=True,text=True)
        assert not actual.returncode,(len(rows),profile,actual.stderr)
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes()
        if actual_ram!=expected or parsed!=result:
            diff=[(hex(at),expected[at],actual_ram[at]) for at in range(min(len(actual_ram),65536)) if expected[at]!=actual_ram[at]]
            raise ValueError(repr((len(rows),profile,diff[:16],result,parsed)))
        rows.append(dict(profile=profile,input_pc=pending['next_pc'],input_d0=pending['d0'],input_phase=pending['phase'],result=parsed,read_events=reads.copy(),native_paths=paths.copy(),ram_sha256=hashlib.sha256(expected).hexdigest(),input_sha256=hashlib.sha256(ram).hexdigest()))
        return bytearray(actual_ram),parsed,cpu.context_save()
    for mode,fd82,fe80,fd8d,external in itertools.product((0,1),(0,1),(0,1),(0,1),(0,1)):
        ram=fixture();ram[0x12],ram[0xfd82],ram[0xfe80],ram[0xfd8d]=mode,fd82,fe80,fd8d
        compare(ram,external=external,profile='word-filter-conditional-external-read')
    for head,tail in itertools.product((0,2,4,6),repeat=2):
        ram=fixture(head,tail);put(ram,0x4d82+head,0x0720)
        compare(ram,profile='duplicate-one-following-slot-and-word-ring')
    for oldest,bytehead,bytetail in itertools.product((0,0x0303,0x0355,0x5503,0x0455),(0,1,2),(0,127)):
        ram=fixture(0,6,bytehead=(bytetail+bytehead)&127,bytetail=bytetail,oldest=oldest)
        compare(ram,profile='word-overflow-zero-special-high-low-and-byte-ring-wrap')
    for bytetail,headstep in itertools.product((0,127),(1,2)):
        compare(fixture(bytehead=(bytetail+headstep)&127,bytetail=bytetail),profile='byte8-or-byte20-wait')
    # Direct47594 deliberately bypasses every earlier prefix helper and clear.
    for high,mode,external in itertools.product((0,1,0x7fff,0x8000,0xffff),(0,1),(0,1)):
        ram=fixture();ram[0x12]=mode;ram[0xfd82]=1;ram[0xfd8d]=1
        compare(ram,initial(0x47594,(high<<16)|0xabcd),external=external,profile='direct47594-prefix-fields-preserved-high-d0')
    direct_wait_kinds=set()
    for high,oldest,step in itertools.product((0x1234,0xffff),(0x0455,0x0355,0x5503),(1,2)):
        ram=fixture(0,6,bytehead=step,oldest=oldest);ram[0x12],ram[0xfd82],ram[0xfd8d]=1,1,1
        first=len(rows);ram,pending,context=compare(ram,initial(0x47594,(high<<16)|0x1234),profile='direct47594-carried-word-overflow-wait')
        rounds=0
        while pending['next_pc']==WAIT:
            direct_wait_kinds.add((pending['phase'],pending['word']['phase']))
            prior=bytes(ram);ram,pending,context=compare(ram,pending,context,external=255,profile='direct47594-repeated-wait-no-prefix-or-external-resample');assert ram==prior and pending['external_reads']==0
            captured=pending['word'] if pending['phase']==1 else pending['byte']
            put(ram,0x4d74,(captured['next']+10)&127) # Controlled host release, separate from IRQ sequences.
            ram,pending,context=compare(ram,pending,context,external=255,profile='direct47594-host-released-cli-carry')
            rounds+=1;assert rounds<=6
        sequences.append(dict(main_calls=len(rows)-first,irq_calls=0,entry=0x47594,actual_cli_ram_full_d0_d1_d3_pending_carry=True,host_sound_head_release=True))
    for high,step in itertools.product((0x1234,0xffff),(1,2)):
        ram=fixture(bytehead=step);first=len(rows);ram,pending,context=compare(ram,initial(0x47594,high<<16),profile='direct47594-byte-wait-carry')
        while pending['next_pc']==WAIT:
            direct_wait_kinds.add((pending['phase'],pending['word']['phase']));captured=pending['word'] if pending['phase']==1 else pending['byte'];put(ram,0x4d74,(captured['next']+10)&127)
            ram,pending,context=compare(ram,pending,context,external=255,profile='direct47594-byte-host-release')
        sequences.append(dict(main_calls=len(rows)-first,irq_calls=0,entry=0x47594,actual_cli_ram_full_d0_d1_d3_pending_carry=True,host_sound_head_release=True))
    assert {(1,1),(1,2),(2,0),(3,0)}<=direct_wait_kinds,direct_wait_kinds
    all_regs=[getattr(mc,'UC_M68K_REG_'+kind+str(index)) for kind in ('D','A') for index in range(8)]
    def interrupt(ram,context,status):
        cpu.context_restore(context);saved=[cpu.reg_read(reg)&0xffffffff for reg in all_regs];cpu.mem_write(BASE,bytes(ram))
        irq_regs=list(struct.unpack('>16I',hashlib.shake_256(b'game-prelude-irq:'+len(irq_rows).to_bytes(4,'big')).digest(64)))
        irq_regs[0],irq_regs[13],irq_regs[15]=0x12345678,0x108000,0x1fcffc
        for reg,value in zip(all_regs,irq_regs): cpu.reg_write(reg,value)
        cpu.reg_write(mc.UC_M68K_REG_SR,0x2000);cpu.mem_write(0x1fcffc,RETURN.to_bytes(4,'big'))
        state.update(mode='irq',external=0,status=status);reads.clear();ports.clear();cpu.emu_start(0xc8c,RETURN,count=100000)
        assert cpu.reg_read(mc.UC_M68K_REG_PC)==RETURN and reads==[(1,0x320000,status)]
        expected=bytes(cpu.mem_read(BASE,65536));expected_ports=b''.join(struct.pack('>BII',*event) for event in ports)
        banks=hashlib.shake_256(b'game-prelude-unused-palette-banks').digest(16384)
        result=dict(service_phase=0,display_bank=0,sound_reads=1,task_registers=[0]*16,task=dict(next_pc=0,restored=False,stack_address=[0,0],stack_value=[0,0]),pending=dict.fromkeys(('kind','phase','low','cursor','command','tail','next'),0))
        inp.write_bytes(ram);bank_in.write_bytes(banks);regs_in.write_bytes(struct.pack('>16I',*irq_regs))
        command=[str(root/'build/step_interrupt'),'begin',str(inp),str(bank_in),str(regs_in),str(out),str(bank_out),str(ports_out),'0',str(status)]
        actual=subprocess.run(command,capture_output=True,text=True);assert not actual.returncode,actual.stderr
        parsed=json.loads(actual.stdout)
        assert out.read_bytes()==expected and bank_out.read_bytes()==banks and ports_out.read_bytes()==expected_ports and parsed==result,(result,parsed)
        irq_rows.append(dict(status=status,head_before=word(ram,0x4d74),head_after=word(expected,0x4d74),ports=ports.copy(),ram_sha256=hashlib.sha256(expected).hexdigest(),ports_sha256=hashlib.sha256(expected_ports).hexdigest()))
        cpu.context_restore(context);assert [cpu.reg_read(reg)&0xffffffff for reg in all_regs]==saved
        return bytearray(out.read_bytes()),context
    for oldest,bytetail,headstep in itertools.product((0x0455,0x0355,0x5503),(0,127),(1,2)):
        ram=fixture(0,6,bytehead=(bytetail+headstep)&127,bytetail=bytetail,oldest=oldest)
        ram[0x12],ram[0xfd82],ram[0xfd8d]=1,1,1
        first_main,first_irq=len(rows),len(irq_rows)
        ram,pending,context=compare(ram,external=0,profile='actual-irq-released-producer')
        rounds=0
        while pending['next_pc']==WAIT:
            before=bytes(ram);ram,pending,context=compare(ram,pending,context,external=255,profile='unchanged-wait-no-prefix-no-external-resample')
            assert ram==before and rows[-1]['native_paths']==[]
            ram,context=interrupt(ram,context,1 if rounds==0 else 0)
            ram,pending,context=compare(ram,pending,context,external=255,profile='native-irq-released-word-or-byte')
            rounds+=1;assert rounds<=12
        sequences.append(dict(main_calls=len(rows)-first_main,irq_calls=len(irq_rows)-first_irq,actual_cli_ram_full_d0_d1_d3_pending_carry=True,no_host_sound_head_writes=True,main_cpu_context_stack_preserved_around_irq=True))
    # Actual c584 JSR enters this prefix; the saved c58a return is never executed.
    bindings=root/'extracted/runtime/main_startup.ms5d';fill=root/'extracted/runtime/palette_fill.ms5p'
    checked_resource(bindings,program,0xe7b58,0xe7bc0)
    from pack_palette_fill import extract as extract_fill
    import zlib
    fill_records,_,_=extract_fill(program)
    fill_payload=b''.join(struct.pack('<I',identifier)+fill_records[identifier][0]+fill_records[identifier][1] for identifier in sorted(fill_records))
    assert fill.read_bytes()==struct.pack('<4s7I',b'MS5P',1,len(fill_records),68,len(fill_payload),zlib.crc32(fill_payload)&0xffffffff,0,0)+fill_payload
    for incoming in ((0xabcd1234,0xbeef7654,0x98767000),(0xffffffff,0xffffffff,0xffffffff)):
        cpu.mem_write(BASE,bytes(65536));state['mode']='setup'
        cpu.reg_write(mc.UC_M68K_REG_A5,0x108000);cpu.reg_write(mc.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        cpu.emu_start(0x3ef2,RETURN,count=10000);assert cpu.reg_read(mc.UC_M68K_REG_PC)==RETURN
        ram=bytearray(cpu.mem_read(BASE,65536))
        struct.pack_into('>I',ram,0x8e4,0xc560)
        for at in (0x4d8a,0x4d8c,0x4d74,0x4d76,0x7dea): put(ram,at,0)
        wait_fixture=incoming[0]==0xffffffff
        if wait_fixture:
            put(ram,0x4d74,1)
            ram[0x4cf4:0x4d74]=bytes([0x55])*128
        cpu.mem_write(BASE,bytes(ram))
        for reg,value in ((mc.UC_M68K_REG_SR,0x2000),(mc.UC_M68K_REG_A5,0x108000),(mc.UC_M68K_REG_A6,0x1008e4),(mc.UC_M68K_REG_A7,STACK)):
            cpu.reg_write(reg,value)
        for reg,value in zip(REGS,incoming): cpu.reg_write(reg,value)
        cpu.mem_write(STACK,RETURN.to_bytes(4,'big'));state['mode']='startup';ports.clear();reads.clear()
        cpu.emu_start(0xc560,RETURN,count=100000)
        assert cpu.reg_read(mc.UC_M68K_REG_PC)==0xc584
        expected=bytes(cpu.mem_read(BASE,65536));native_regs=[cpu.reg_read(reg)&0xffffffff for reg in REGS]
        expected_ports=b''.join(struct.pack('>BII',*event) for event in ports)
        result=dict(zip(('d0','d1','d3'),native_regs));result.update(next_pc=0xc584,writes=len(ports))
        inp.write_bytes(ram)
        command=[str(root/'build/step_game_startup'),'0xc560','0x8e4']+[str(value) for value in incoming]+[str(inp),str(out),str(ports_out),str(fill),str(bindings)]
        actual=subprocess.run(command,capture_output=True,text=True);assert not actual.returncode,actual.stderr
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes()
        assert actual_ram==expected and ports_out.read_bytes()==expected_ports and parsed==result,(result,parsed)
        for reg,key in zip(REGS,('d0','d1','d3')): cpu.reg_write(reg,parsed[key])
        state['mode']='handoff';cpu.mem_write(BASE,actual_ram);cpu.emu_start(0xc584,RETURN,count=10)
        assert cpu.reg_read(mc.UC_M68K_REG_PC)==ENTRY and cpu.reg_read(mc.UC_M68K_REG_A7)==STACK-4
        assert bytes(cpu.mem_read(STACK-4,4))==(0xc58a).to_bytes(4,'big')
        pending=initial();pending.update(d0=parsed['d0'],d1=parsed['d1'],d3=parsed['d3'])
        ram,pending,context=compare(bytearray(actual_ram),pending,cpu.context_save(),profile='actual-ready-startup-jsr-to-game-prelude')
        assert pending['next_pc']==(WAIT if wait_fixture else DONE)
        assert pending['phase']==(2 if wait_fixture else 4)
        integrations.append(dict(startup_result=parsed,prelude_result=pending,actual_cli_ram_full_d0_d1_d3_carried=True,native_c584_jsr_executed=True,saved_return=0xc58a,suffix_not_executed=True,startup_ports=len(expected_ports)//9,full_byte_queue_wait_fixture=wait_fixture))
    sentinel=b'previous-game-prelude-output\0\xff'
    def reject(ram,pending=None,external=0,label='invalid',command=None):
        inp.write_bytes(ram);out.write_bytes(sentinel)
        actual=subprocess.run(command or arguments(pending or initial(),external),capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel,(label,actual.stdout,actual.stderr)
        negatives.append(dict(failure=label,output_preserved=True,original_executed=False))
    for size in (0,65535,65537): reject(bytes(size),label='wrong-ram-size')
    for at,value in ((0x4d8a,1),(0x4d8c,8),(0x4d74,128),(0x4d76,65535)):
        ram=fixture();put(ram,at,value);reject(ram,label='invalid-used-index')
    for key,invalid in itertools.product(('next_pc','d0','d1','d3','phase'),('-1','4294967296','0x','1x','')):
        pending=initial();pending[key]=invalid;reject(fixture(),pending,label='invalid-state-parser')
    for invalid in ('-1','256','0x100','0x','1x',''): reject(fixture(),external=invalid,label='invalid-external-byte-parser')
    for pc,phase in ((WAIT,0),(ENTRY,1),(WAIT,4),(DONE,4)):
        pending=initial();pending.update(next_pc=pc,phase=phase);reject(fixture(),pending,label='missing-inconsistent-pending')
    ram,pending,context=compare(fixture(bytehead=1),profile='negative-live-state-fixture')
    bad=bytearray(ram);put(bad,0x4d74,128);reject(bad,pending,label='invalid-live-head-on-resume')
    inconsistent=dict(pending);inconsistent['d1']^=1;reject(ram,inconsistent,label='captured-next-register-inconsistency')
    for alias_kind in ('same','hardlink','symlink'):
        good=fixture();inp.write_bytes(good)
        alias=inp if alias_kind=='same' else folder/('alias-'+alias_kind+'.bin')
        if alias_kind!='same':
            alias.unlink(missing_ok=True)
            if alias_kind=='hardlink': alias.hardlink_to(inp)
            else: alias.symlink_to(inp)
        command=arguments(initial(),0);command[-1]=str(alias)
        actual=subprocess.run(command,capture_output=True,text=True);assert actual.returncode and inp.read_bytes()==good
        negatives.append(dict(failure='input-output-'+alias_kind+'-alias',output_preserved=True,original_executed=False))
    for at in (0x4d74,0x4d76):
        ram=fixture();put(ram,at,128);reject(ram,initial(0x47594,0xabcd1234),label='direct47594-invalid-used-byte-index-rollback')
    bad=initial(0x47594);bad['phase']=1;reject(fixture(),bad,label='direct47594-inconsistent-phase')
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    assert {1,2,3,4}.issubset({row['result']['phase'] for row in rows})
    assert {1,2}.issubset({row['result']['word']['phase'] for row in rows})
    assert hashlib.sha256(executable.read_bytes()).hexdigest()==binary_sha
    report.write_text(json.dumps(dict(source=source,binary_sha256=binary_sha,emulator='Unicorn '+unicorn.__version__,program_code_modified=False,entry_cpu_address=ENTRY,additional_direct_entry_cpu_address=0x47594,direct47594_wait_kinds=sorted(direct_wait_kinds),direct47594_cases=sum(row['profile'].startswith('direct47594') for row in rows),legacy_cases=sum(not row['profile'].startswith('direct47594') for row in rows),native_a7_wait_and_completion_offsets_verified=True,stop_before_cpu_address=DONE,cases=len(rows),phases={str(phase):sum(row['result']['phase']==phase for row in rows) for phase in (1,2,3,4)},external_reads=sum(row['result']['external_reads'] for row in rows),prefix_mmio_writes=0,irq_calls=len(irq_rows),irq_ports=sum(len(row['ports']) for row in irq_rows),negative_cases=len(negatives),negative_results=negatives,carry_sequences=sequences,startup_integrations=integrations,results=rows,irq_results=irq_rows,scope='Direct47594 bypasses the earlier prefix, preserves its three clear bytes and D0high16, with separately marked host releases and full CLI carry. Unmodified47570 executes its clear/set helpers, word0720 enqueue and byte8/20 sequence; stops at3aea waits or475a4 before the suffix. Full RAM/D0/D1/D3 and independently extracted stack-return pending phases are compared. Actual CLI RAM/register/pending outputs are carried across waits; native main context/stack is restored around actual c8c services. No host soundhead writes occur in IRQ-release sequences. IRQ rendering is disabled, timer stays below producer threshold and banks are unchanged; sound status1/0 comes from explicit host samples. BIOS/RTE, natural scheduling, callback execution and475a4 suffix are excluded.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),external_reads=sum(row['result']['external_reads'] for row in rows),irq_calls=len(irq_rows),irq_ports=sum(len(row['ports']) for row in irq_rows),negative_cases=len(negatives),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__': main()
