"""Actual c8c IRQ consumers release native main preparation waits; CLI state carry."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import zlib
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn import m68k_const as mc
from disassemble_program import load_verified_program
from pack_palettes import extract
from verify_object_reset import make_cpu
from verify_sprite_blocks import resolve_blocks
from verify_stage_catalog import SOURCE_SHA256, checked_resource

BASE, ENTRY, SOUND, SPRITE, DONE, RETURN, STACK = 0x100000,0xe74,0x3aea,0x16bd0,0xec4,0xff000,0x1feffc
OBJECTS=(0x109156,0x10b1d6,0x10d256,0x10d2d6)
D1,D3=mc.UC_M68K_REG_D1,mc.UC_M68K_REG_D3

def put(ram,at,value): struct.pack_into('>H',ram,at,value&65535)
def word(ram,at): return struct.unpack_from('>H',ram,at)[0]
def empty_sound(): return dict(kind=0,phase=0,low=0,cursor=0,waiting=False,command=0,tail=0,next=0)

def main():
    root=Path(__file__).resolve().parents[1]
    program,source=load_verified_program(root)
    assert source['sha256']==SOURCE_SHA256
    executable=root/'build/prepare_main_frame'
    palette=root/'extracted/runtime/palettes.ms5p'
    records,_=extract(program)
    payload=b''.join(struct.pack('<I',identifier)+records[identifier][0]+records[identifier][1] for identifier in sorted(records))
    assert palette.read_bytes()==struct.pack('<4s7I',b'MS5P',1,len(records),68,len(payload),zlib.crc32(payload)&0xffffffff,0,0)+payload
    identifiers=(0x2152,0x2952,0x2382a,0x2402a,0x2482a)
    resources=[root/'extracted/runtime'/('composition_%06x.ms5c'%identifier) for identifier in identifiers]
    hashes={'palettes':hashlib.sha256(palette.read_bytes()).hexdigest()}
    for identifier,path in zip(identifiers,resources):
        bank,offset,data,blocks=resolve_blocks(program,identifier)
        assert bank==0x400000
        assert path.read_bytes()==struct.pack('<4s7I',b'MS5C',1,1 if len(blocks)==1 else 2,identifier,offset,len(data),zlib.crc32(data)&0xffffffff,0)+data
        hashes[hex(identifier)]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'blocks':len(blocks),'rom_offset':offset}
    folder=root/'artifacts/main_prelude_irq';folder.mkdir(parents=True,exist_ok=True)
    inp,out,ports_out,bank_in,bank_out,regs_in,report=[folder/name for name in ('input.bin','cpp.bin','cpp.ports.bin','banks.bin','cpp.banks.bin','regs.bin','verification.json')]
    report.unlink(missing_ok=True)
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000);cpu.mem_map(0x400000,8192);cpu.mem_map(0xd00000,4096)
    current_bank=[0x200000]
    cpu.mem_write(0x200000,program[0x200000:0x300000])
    ports,reads,paths,rows,sequences,irq_rows=[],[],[],[],[],[]
    palette_state={'bank':0,'banks':[bytearray(8192),bytearray(8192)]}
    state={'mode':'setup','video':0,'blocked':0,'visits':0,'samples':[]}
    def write(cpu,access,address,size,value,user):
        if address in (0x3c0000,0x3c0004,0x2ffff0,0x2ffff2,0x300001,0x320000,0x3a000f,0x3a001f,0x3a0001,0x3a0011) or 0x400000<=address<0x402000:
            ports.append((size,address,value&((1<<(size*8))-1)))
            if address==0x2ffff2:
                assert size==2 and value in (0x1000,0x2000,0x3000)
                current_bank[0]=((value>>12)+1)*0x100000
                cpu.mem_write(0x200000,program[current_bank[0]:current_bank[0]+0xffff0])
            elif address in (0x3a000f,0x3a001f):
                assert size==1
                palette_state['bank']=int(address==0x3a001f)
                cpu.mem_write(0x400000,bytes(palette_state['banks'][palette_state['bank']]))
            elif 0x400000<=address<0x402000:
                assert size in (2,4)
                at=address-0x400000
                palette_state['banks'][palette_state['bank']][at:at+size]=(value&((1<<(size*8))-1)).to_bytes(size,'big')
        elif not (BASE<=address and address+size<=BASE+65536) and not (0x1f8000<=address and address+size<=0x1ff000):
            raise ValueError('Unexpected native write '+repr((hex(address),size,value)))
    def read(cpu,access,address,size,value,user):
        if address==0x3c0006:
            assert size==2;cpu.mem_write(address,state['video'].to_bytes(2,'big'));reads.append((size,address,state['video']))
        elif state['mode']=='irq' and address in (0x320000,0xd00046):
            assert size==1;sample=state['status'] if address==0x320000 else 0
            cpu.mem_write(address,bytes([sample]));reads.append((size,address,sample))
        elif state['mode']=='input' and address in (0x380000,0x300000,0x340000):
            index=sum(event[1]!=0x3c0006 for event in reads)
            assert index<len(state['samples']) and size==1
            sample=state['samples'][index];cpu.mem_write(address,bytes([sample]));reads.append((size,address,sample))
    def code(cpu,address,size,user):
        if address in (0x3c08,0x16bba,0xce02,0x166bc,0x1ae56,0x5728,0x4718,0x479e,0x4c40,0x504c): paths.append(address)
        if state['mode']=='prelude':
            if address in (SOUND,SPRITE):
                blocked=(word(cpu.mem_read(BASE,65536),0x4d74)==(cpu.reg_read(D1)&65535)) if address==SOUND else (word(cpu.mem_read(BASE,65536),0x8d34)==(cpu.reg_read(mc.UC_M68K_REG_D0)&65535))
                blocked=blocked if address==SOUND else not blocked
                if blocked:
                    state['visits']=state['visits']+1 if state['blocked']==address else 1;state['blocked']=address
                    if state['visits']==2: cpu.emu_stop()
                else: state['visits']=0;state['blocked']=0
            elif address==DONE: cpu.emu_stop()
        elif state['mode']=='input':
            if address==0xef2:
                state['visits']+=1
                if state['visits']==2: cpu.emu_stop()
            elif address==0xf3c: cpu.emu_stop()
        elif state['mode'] in ('setup','irq') and address==RETURN: cpu.emu_stop()
    cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_MEM_READ,read,begin=0x300000,end=0x3c0007);cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_READ,read,begin=0xd00046,end=0xd00046)
    cpu.mem_write(BASE,bytes(65536));cpu.reg_write(mc.UC_M68K_REG_A5,0x108000);cpu.reg_write(mc.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
    cpu.emu_start(0x3ef2,RETURN,count=10000)
    allocated=bytes(cpu.mem_read(BASE,65536))
    def fixture(count=0,forward=True,ready=True,identifier=0x2152,flip=0,cache=190,disabled=False):
        ram=bytearray(allocated)
        for slot in range(256):
            at=0x4d92+16*slot;put(ram,at+10,0x203);put(ram,at+12,0x203);ram[at+14:at+16]=bytes((0,2))
        ram[0x7dd4]=0;ram[0x7ded]=0
        for at in range(0x7dc2,0x7dd4,2): put(ram,at,0)
        put(ram,0x4d8a,0);put(ram,0x4d8c,0);put(ram,0x4d74,0);put(ram,0x4d76,0)
        for at in (0x4d7b,0x4d7e): ram[at]=0
        ram[0x8d3c]=0xa1 if forward else 0x21;ram[0x8d3d]=0x35
        for at,val in ((0x8d34,510 if ready else 0),(0x8d36,510),(0x8d38,(510+count*2)&510),(0x8d3a,(510+count*2)&510),(0x914e,0)): put(ram,at,val)
        for pool,lower,upper in ((0x8d3e,0,190),(0x8d46,190,380)):
            struct.pack_into('>4H',ram,pool,lower,upper,lower+cache,lower+cache)
            if disabled: ram[pool:pool+8]=b'\xff'*8
        for index in range(count):
            offset=12*(index+1);put(ram,0x8b34+((510+index*2)&510),offset)
            struct.pack_into('>III',ram,0x7f34+offset,((count-index)*17<<16)|(160<<6),0xffff1500|(4 if index&1 else 0)|((flip+index)&3),(384<<23)|identifier)
        for index,obj in enumerate(OBJECTS):
            at=obj-BASE;put(ram,at+0x14,0xffff-index);put(ram,at+0x18,index);ram[at+0x25]=index;ram[at+0x7a]=1;put(ram,at+0x7c,0);put(ram,at+0x7e,0)
        ram[0x1b]=0x35;ram[0x18]=0xa5
        return ram
    def args(ram_state,video,selected_palette=palette,selected_resources=resources):
        command=[str(executable),'--state',str(ram_state['next_pc']),str(ram_state['d1']),str(ram_state['d3'])]
        if ram_state['sound']['waiting']: command+=['--sound']+[str(ram_state['sound'][key]) for key in ('phase','low','cursor','command','tail','next')]
        if ram_state['sprite']['waiting']: command+=['--sprite',str(ram_state['sprite']['cursor'])]
        return command+[str(video),str(inp),str(out),str(ports_out),str(selected_palette)]+[str(path) for path in selected_resources]
    def initial_state(): return dict(next_pc=ENTRY,d1=0xabcdabff,d3=0x9876fedc,sound=empty_sound(),sprite=dict(waiting=False,cursor=0))
    def compare(ram,pending=None,context=None,video=0,profile='matrix'):
        pending=pending or initial_state();cpu.mem_write(BASE,bytes(ram))
        if context is None:
            for reg,value in ((mc.UC_M68K_REG_SR,0x2000),(mc.UC_M68K_REG_A5,0x108000),(mc.UC_M68K_REG_A6,0x100f5c),(mc.UC_M68K_REG_A7,STACK)):
                cpu.reg_write(reg,value)
            cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        else: cpu.context_restore(context)
        cpu.reg_write(D1,pending['d1']);cpu.reg_write(D3,pending['d3'])
        ports.clear();reads.clear();paths.clear();state.update(mode='prelude',video=video,blocked=0,visits=0)
        cpu.emu_start(pending['next_pc'],RETURN,count=2000000)
        pc=cpu.reg_read(mc.UC_M68K_REG_PC);assert pc in (SOUND,SPRITE,DONE),hex(pc)
        result=dict(next_pc=pc,d1=cpu.reg_read(D1)&0xffffffff,d3=cpu.reg_read(D3)&0xffffffff,writes=len(ports),sound=empty_sound(),sprite=dict(waiting=False,cursor=0))
        if pc==SOUND:
            sp=cpu.reg_read(mc.UC_M68K_REG_A7);ret=int.from_bytes(cpu.mem_read(sp,4),'big');assert ret in (0x3c2c,0x3c32),hex(ret)
            phase=1 if ret==0x3c2c else 2
            result['sound'].update(kind=2,phase=phase,low=cpu.mem_read(sp+4,1)[0] if phase==1 else cpu.reg_read(mc.UC_M68K_REG_D0)&255,cursor=int.from_bytes(cpu.mem_read(sp+(6 if phase==1 else 4),2),'big'),waiting=True,command=cpu.reg_read(mc.UC_M68K_REG_D0)&255,tail=cpu.reg_read(mc.UC_M68K_REG_A0)-BASE-0x4cf4,next=cpu.reg_read(D1)&65535)
        elif pc==SPRITE: result['sprite']=dict(waiting=True,cursor=cpu.reg_read(mc.UC_M68K_REG_D0)&65535)
        assert len(reads)==(1 if pc==DONE else 0)
        expected=bytes(cpu.mem_read(BASE,65536));expected_ports=b''.join(struct.pack('>BII',*event) for event in ports)
        inp.write_bytes(ram);actual=subprocess.run(args(pending,video),capture_output=True,text=True)
        assert not actual.returncode,(len(rows),profile,actual.stderr)
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes();actual_ports=ports_out.read_bytes()
        if actual_ram!=expected or actual_ports!=expected_ports or parsed!=result:
            diff=[(hex(at),expected[at],actual_ram[at]) for at in range(min(len(actual_ram),65536)) if expected[at]!=actual_ram[at]]
            raise ValueError(repr((len(rows),profile,pending['next_pc'],diff[:16],len(expected_ports),len(actual_ports),result,parsed)))
        rows.append(dict(profile=profile,input_pc=pending['next_pc'],result=parsed,paths=paths.copy(),reads=reads.copy(),ram_sha256=hashlib.sha256(expected).hexdigest(),ports_sha256=hashlib.sha256(expected_ports).hexdigest(),input_sha256=hashlib.sha256(ram).hexdigest()))
        return bytearray(actual_ram),parsed,cpu.context_save()
    regs=[getattr(mc,'UC_M68K_REG_'+kind+str(index)) for kind in ('D','A') for index in range(8)]
    def interrupt(ram,banks,main_context,status,profile):
        cpu.context_restore(main_context)
        main_registers=[cpu.reg_read(reg)&0xffffffff for reg in regs]
        cpu.mem_write(BASE,bytes(ram))
        palette_state['banks']=[bytearray(banks[:8192]),bytearray(banks[8192:])]
        # Every rendered fixture ends in logical display bank0; the CLI's begin default is0.
        assert palette_state['bank']==0
        cpu.mem_write(0x400000,bytes(palette_state['banks'][0]))
        irq_registers=list(struct.unpack('>16I',hashlib.shake_256(b'main-prelude-irq:'+len(irq_rows).to_bytes(4,'big')).digest(64)))
        irq_registers[0],irq_registers[13],irq_registers[15]=0xabcd0055,0x108000,0x1fcffc
        for reg,value in zip(regs,irq_registers): cpu.reg_write(reg,value)
        cpu.reg_write(mc.UC_M68K_REG_SR,0x2000);cpu.mem_write(irq_registers[15],RETURN.to_bytes(4,'big'))
        ports.clear();reads.clear();paths.clear();state.update(mode='irq',status=status)
        cpu.emu_start(0xc8c,RETURN,count=2000000)
        assert cpu.reg_read(mc.UC_M68K_REG_PC)==RETURN
        assert reads==[(1,0x320000,status)],reads
        expected=bytes(cpu.mem_read(BASE,65536));expected_banks=b''.join(palette_state['banks'])
        assert bytes(cpu.mem_read(0x400000,8192))==palette_state['banks'][palette_state['bank']]
        expected_ports=b''.join(struct.pack('>BII',*event) for event in ports)
        result={'service_phase':0,'display_bank':palette_state['bank'],'sound_reads':1,'task_registers':[0]*16,'task':{'next_pc':0,'restored':False,'stack_address':[0,0],'stack_value':[0,0]},'pending':dict.fromkeys(('kind','phase','low','cursor','command','tail','next'),0)}
        inp.write_bytes(ram);bank_in.write_bytes(banks);regs_in.write_bytes(struct.pack('>16I',*irq_registers))
        command=[str(root/'build/step_interrupt'),'begin',str(inp),str(bank_in),str(regs_in),str(out),str(bank_out),str(ports_out),'0',str(status)]+[str(path) for path in resources]
        actual=subprocess.run(command,capture_output=True,text=True)
        assert not actual.returncode,(profile,actual.stderr)
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes();actual_banks=bank_out.read_bytes()
        if actual_ram!=expected or actual_banks!=expected_banks or ports_out.read_bytes()!=expected_ports or parsed!=result:
            diff=[(hex(at),expected[at],actual_ram[at]) for at in range(min(len(actual_ram),65536)) if expected[at]!=actual_ram[at]]
            raise ValueError(repr((profile,'irq',diff[:16],result,parsed,len(expected_ports),len(ports_out.read_bytes()))))
        before_head,before_read=word(ram,0x4d74),word(ram,0x8d34)
        irq_rows.append(dict(profile=profile,status=status,result=parsed,ports=len(ports),reads=reads.copy(),sound_head_before=before_head,sound_head_after=word(actual_ram,0x4d74),sprite_read_before=before_read,sprite_read_after=word(actual_ram,0x8d34),direction_before=bool(ram[0x8d3c]&128),direction_after=bool(actual_ram[0x8d3c]&128),palette_changed=actual_banks!=banks,ram_sha256=hashlib.sha256(expected).hexdigest(),banks_sha256=hashlib.sha256(expected_banks).hexdigest(),ports_sha256=hashlib.sha256(expected_ports).hexdigest()))
        # Explicit host context restoration represents separately verified IRQ envelope register preservation.
        cpu.context_restore(main_context)
        assert [cpu.reg_read(reg)&0xffffffff for reg in regs]==main_registers
        return bytearray(actual_ram),actual_banks,main_context
    def setup_irq(ram):
        ram[0x1b],ram[0x19],ram[0x7dec],ram[0x7ded]=128,0,0,128
        put(ram,0x7dea,0);put(ram,0xd68c,0)
        struct.pack_into('>I',ram,0x81c,0x10081c)
        ram[0x5da2:0x7da2]=hashlib.shake_256(b'actual-irq-palette-work').digest(8192)
        for slot in range(256): ram[0x5da2+32*slot]&=127
        ram[0x5da2]|=128
        for index,obj in enumerate(OBJECTS):
            at=obj-BASE;ram[at+0x7a]=0x81;put(ram,at+0x26,index);put(ram,at+0x7c,160);put(ram,at+0x7e,384)
            ram[at+0x3a:at+0x7a]=hashlib.shake_256(b'irq-columns:'+bytes([index])).digest(64)
        palette_state['bank']=0
        return hashlib.shake_256(b'irq-physical-palette-banks').digest(16384)
    def run_sequence(ram,banks,profile,busy=False,priority=False,irq_appends=False):
        initial_heads=(word(ram,0x4d74),word(ram,0x8d34))
        first_main,first_irq=len(rows),len(irq_rows)
        palette_state['banks']=[bytearray(banks[:8192]),bytearray(banks[8192:])]
        cpu.mem_write(0x400000,banks[:8192])
        ram,pending,context=compare(ram,profile=profile)
        assert pending['next_pc'] in (SOUND,SPRITE)
        irqs=0
        while pending['next_pc']!=DONE:
            # Poll repeatedly with exactly the returned state, without advancing either consumer cursor.
            prior=bytes(ram);ram,pending,context=compare(ram,pending,context,profile='before-irq-unchanged-'+profile)
            assert ram==prior
            head,read_cursor=word(ram,0x4d74),word(ram,0x8d34)
            status=1 if busy and irqs==0 else 0
            ram,banks,context=interrupt(ram,banks,context,status,profile)
            if status==1: assert word(ram,0x4d74)==head
            if irq_appends and irqs==0:
                assert word(ram,0xd68c)==0 and word(ram,0x4d8c)==4 and word(ram,0x4d84)==0x19c0
            if priority and irqs==0: assert word(ram,0x4d74)==head and ram[0x4d7b]&128==0
            ram,pending,context=compare(ram,pending,context,video=0xffff,profile='irq-released-'+profile)
            irqs+=1;assert irqs<=8
        # Actual IRQ now consumes the newly prepared sprites and transfers prepared palettes.
        prepared=word(ram,0x8d36);before_read=word(ram,0x8d34)
        assert before_read!=prepared
        ram,banks,context=interrupt(ram,banks,context,0,'after-complete-'+profile)
        assert word(ram,0x8d34)==prepared
        sequences.append(dict(profile=profile,main_calls=len(rows)-first_main,irq_calls=len(irq_rows)-first_irq,initial_consumer_heads=list(initial_heads),actual_cli_ram_register_pending_palette_bank_carry=True,no_manual_sound_head_or_sprite_read_after_initial_fixture=True,post_completion_irq_consumed_new_preparation=True,actual_irq_timer_producer_appended_word=irq_appends))
    for tail,command,duplicates,forward in itertools.product((0,127),(0x0455,0x0355),(False,True),(False,True)):
        ram=fixture(4,forward,True,0x2402a)
        # A full initial byte ring blocks a producer at next=(tail+1)&127.
        head=(tail+1)&127;put(ram,0x4d74,head);put(ram,0x4d76,tail)
        for index in range(128): ram[0x4cf4+index]=0x66 if duplicates else (index//2)&255
        put(ram,0x4d82,command);put(ram,0x4d8c,2)
        banks=setup_irq(ram)
        run_sequence(ram,banks,'sound-wrap-duplicate-priority-'+str((tail,command,duplicates,forward)),busy=command==0x0455,priority=command==0x0355)
    for tail in (0,127):
        ram=fixture(4,True,True,0x2402a)
        put(ram,0x4d74,(tail+1)&127);put(ram,0x4d76,tail)
        for index in range(128): ram[0x4cf4+index]=(index//2)&255
        put(ram,0x4d82,0x0455);put(ram,0x4d8c,2)
        banks=setup_irq(ram);put(ram,0xd68c,16)
        run_sequence(ram,banks,'irq-timer-producer-live-word-append-'+str(tail),busy=True,irq_appends=True)
    for forward,old_count,new_count,flip,identifier in itertools.product((False,True),(1,4),(1,4),range(4),(0x2152,0x2402a)):
        # Separate old ready ring [0,prepared) and new producer range [prepared,end).
        ram=fixture(0,forward,True,identifier,flip,cache=95)
        put(ram,0x8d34,0);put(ram,0x8d36,old_count*2);put(ram,0x8d38,(old_count+new_count)*2);put(ram,0x8d3a,(old_count+new_count)*2)
        ram[0x8d3d]=128
        for index in range(old_count+new_count):
            offset=12*(index+1);put(ram,0x8b34+index*2,offset)
            struct.pack_into('>III',ram,0x7f34+offset,((old_count+new_count-index)*17<<16)|(160<<6),0xffff1500|(4 if index&1 else 0)|flip,(384<<23)|identifier)
        banks=setup_irq(ram)
        run_sequence(ram,banks,'old-ready-to-new-pending-sprites-'+str((forward,old_count,new_count,flip,identifier)))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    assert bytes(cpu.mem_read(0x200000,0xffff0))==program[current_bank[0]:current_bank[0]+0xffff0]
    assert any(row['status']==1 and row['sound_head_before']==row['sound_head_after'] for row in irq_rows)
    assert any(row['sprite_read_before']!=row['sprite_read_after'] and row['direction_before']!=row['direction_after'] for row in irq_rows)
    assert any(row['palette_changed'] for row in irq_rows)
    report.write_text(json.dumps(dict(source=source,emulator='Unicorn '+unicorn.__version__,program_code_modified=False,entry_cpu_addresses=[ENTRY,0xc8c],resource_hashes=hashes,main_calls=len(rows),irq_calls=len(irq_rows),main_boundaries={str(pc):sum(row['result']['next_pc']==pc for row in rows) for pc in (SOUND,SPRITE,DONE)},main_ports=sum(row['result']['writes'] for row in rows),irq_ports=sum(row['ports'] for row in irq_rows),main_video_reads=sum(len(row['reads']) for row in rows),irq_sound_reads=sum(len(row['reads']) for row in irq_rows),no_manual_sound_head_or_sprite_read_after_initial_fixtures=True,actual_cpp_ram_register_pending_and_palette_bank_carry=True,carry_sequences=sequences,main_results=rows,irq_results=irq_rows,scope='Native main CPU context and external stack remain suspended across explicit native c8c calls. Host restores all main registers afterward, representing separately verified IRQ envelope preservation without BIOS/SR/RTE or natural timing claims. Only native IRQ and equivalent CLI consumer outputs advance soundhead4d74 or sprite read8d34 after fixture setup. Full RAM, D1/D3 and pending state at main boundaries, both physical palette banks/logical display and all ordered MMIO at IRQ boundaries are compared. Fixtures keep empty task queue, initial timer0 or16 followed by native timer reset/advances below producer threshold, and display bank0; arbitrary callbacks and final IRQ scratch registers are excluded.'),indent=2)+'\n')
    print(json.dumps(dict(main_calls=len(rows),irq_calls=len(irq_rows),sequences=len(sequences),main_ports=sum(row['result']['writes'] for row in rows),irq_ports=sum(row['ports'] for row in irq_rows),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__': main()
