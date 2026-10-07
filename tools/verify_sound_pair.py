"""Unmodified3d58/3d64 pair producer, captured waits and actual IRQ release."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256
BASE,RETURN,STACK,WAIT=0x100000,0xff000,0x1feffc,0x3aea
REGS=(m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D3)
ALLREGS=[getattr(m,'UC_M68K_REG_D'+str(i)) for i in range(8)]+[getattr(m,'UC_M68K_REG_A'+str(i)) for i in range(8)]
def word(ram,at):return int.from_bytes(ram[at:at+2],'big')
def put(ram,at,value):struct.pack_into('>H',ram,at,value&65535)
def initial(entry,values):return dict(entry=entry,next_pc=entry,d0=values[0],d1=values[1],d3=values[2],phase=0,saved=0,byte=dict(waiting=False,command=0,tail=0,next=0))

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
    folder=root/'artifacts/sound_pair';folder.mkdir(parents=True,exist_ok=True)
    inp,out,report,bankin,bankout,regfile,portfile=[folder/name for name in ('input.bin','cpp.bin','verification.json','banks.bin','cpp.banks.bin','regs.bin','irq.ports.bin')];report.unlink(missing_ok=True)
    executable=root/'build/step_sound_pair';binary_sha=hashlib.sha256(executable.read_bytes()).hexdigest()
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000)
    rows,negatives,sequences,irqrows,ports,reads=[],[],[],[],[],[];state=dict(waits=0,mode='pair',status=0)
    def code(cpu,address,size,user):
        if address==RETURN:cpu.emu_stop()
        elif address==WAIT:
            if int.from_bytes(cpu.mem_read(BASE+0x4d74,2),'big')==(cpu.reg_read(REGS[1])&65535):
                state['waits']+=1
                if state['waits']==2:cpu.emu_stop()
            else:state['waits']=0
    def write(cpu,access,address,size,value,user):
        if address in (0x320000,0x3a0001,0x3a0011,0x300001,0x2ffff0,0x2ffff2):
            assert state['mode']=='irq';ports.append((size,address,value&((1<<(size*8))-1)))
        else:assert BASE<=address and address+size<=BASE+65536 or 0x1f8000<=address and address+size<=0x1ff000,(hex(address),size,value)
    def read(cpu,access,address,size,value,user):
        assert state['mode']=='irq' and address==0x320000 and size==1
        cpu.mem_write(address,bytes([state['status']]));reads.append((size,address,state['status']))
    cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_MEM_READ,read,begin=0x320000,end=0x320000)
    def fixture(tail=0,slots='empty'):
        ram=bytearray(hashlib.shake_256(b'soundpair-fixture').digest(65536))
        put(ram,0x4d76,tail);put(ram,0x4d74,tail if slots=='empty' else (tail+(2 if slots=='one' else 1))&127)
        return ram
    def arguments(pending,target=out):
        return [str(executable)]+[str(pending[key]) for key in ('entry','d0','d1','d3','phase','saved')]+[str(pending['byte'][key]) for key in ('command','tail','next')]+[str(inp),str(target)]
    def compare(ram,pending,context=None,label='matrix'):
        cpu.mem_write(BASE,bytes(ram))
        if context is None:
            cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        else:cpu.context_restore(context)
        for reg,key in zip(REGS,('d0','d1','d3')):cpu.reg_write(reg,pending[key])
        ports.clear();reads.clear();state.update(waits=0,mode='pair')
        cpu.emu_start(pending['entry'] if pending['phase']==0 else WAIT,0xffffff,count=10000)
        pc=cpu.reg_read(m.UC_M68K_REG_PC);assert pc in (RETURN,WAIT)
        result=initial(pending['entry'],tuple(cpu.reg_read(reg)&0xffffffff for reg in REGS))
        result['saved']=pending['d0']&255 if pending['phase']==0 else pending['saved']
        if pc==WAIT:
            sp=cpu.reg_read(m.UC_M68K_REG_A7);ret=int.from_bytes(cpu.mem_read(sp,4),'big')
            phase=1 if ret==0x3d6e else 2;assert ret in (0x3d6e,RETURN),hex(ret)
            result.update(next_pc=WAIT,phase=phase)
            if phase==1:assert result['saved']==cpu.mem_read(sp+4,1)[0]
            result['byte']=dict(waiting=True,command=result['d0']&255,tail=cpu.reg_read(m.UC_M68K_REG_A0)-BASE-0x4cf4,next=result['d1']&65535)
        else:result.update(next_pc=0x3af6,phase=3)
        expected=bytes(cpu.mem_read(BASE,65536));inp.write_bytes(ram)
        actual=subprocess.run(arguments(pending),capture_output=True,text=True)
        assert not actual.returncode,(label,actual.stderr)
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes()
        if parsed!=result or actual_ram!=expected:
            diff=[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b]
            raise ValueError(repr((label,pending,diff[:16],result,parsed)))
        assert result['d3']==pending['d3'] and not ports and not reads
        rows.append(dict(profile=label,incoming=pending,result=parsed,native_final_pc=pc,ram_sha256=hashlib.sha256(expected).hexdigest()))
        return bytearray(actual_ram),parsed,cpu.context_save()
    for entry,saved,tail,high in itertools.product((0x3d58,0x3d64),range(256),(0,127),(0,0xabcd1200)):
        ram=fixture(tail);pending=initial(entry,(high|saved,0x87654321,0xfedcba98))
        compare(ram,pending,label='all-saved-bytes-upper-registers-empty-and-wrap')
    for entry,tail,slots,saved in itertools.product((0x3d58,0x3d64),(0,127),('one','full'),(0,0xdf,0xe0,0xff)):
        ram=fixture(tail,slots);pending=initial(entry,(0xabcd1200|saved,0x87654321,0xfedcba98));first=len(rows)
        ram,pending,context=compare(ram,pending,label='prefix-or-suffix-full')
        assert pending['phase']==(1 if slots=='full' else 2)
        ram,pending,context=compare(ram,pending,context,label='repeat-wait-no-writes')
        original_next=pending['byte']['next'];put(ram,0x4d76,73) # Explicit live-tail mutation; captured write slot wins.
        releases=[]
        for iteration in range(4):
            head=(pending['byte']['next']+16)&127;put(ram,0x4d74,head);releases.append(head)
            ram,pending,context=compare(ram,pending,context,label='host-release-captured-tail')
            if pending['phase']==3:break
        assert pending['phase']==3
        sequences.append(dict(calls=len(rows)-first,actual_cli_ram_registers_pending_carried=True,native_context_stack_preserved=True,host_inputs='head release and artificial live tail73',head_releases=releases,captured_next=original_next))
    # IRQ contexts restore host-side only, while shared RAM changes come solely from c8c.
    def irq(ram,main_context,status):
        cpu.mem_write(BASE,bytes(ram));cpu.context_restore(main_context)
        values=[0]*16;values[13]=0x108000;values[15]=0x1fef00
        for reg,value in zip(ALLREGS,values):cpu.reg_write(reg,value)
        cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(0x1fef00,RETURN.to_bytes(4,'big'))
        ports.clear();reads.clear();state.update(mode='irq',status=status,waits=0)
        cpu.emu_start(0xc8c,0xffffff,count=100000);assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN
        expected=bytes(cpu.mem_read(BASE,65536));inp.write_bytes(ram);bankin.write_bytes(bytes(16384));regfile.write_bytes(struct.pack('>16I',*values))
        actual=subprocess.run([str(root/'build/step_interrupt'),'begin',str(inp),str(bankin),str(regfile),str(out),str(bankout),str(portfile),'0',str(status)],capture_output=True,text=True)
        assert not actual.returncode,actual.stderr
        parsed=json.loads(actual.stdout);data=portfile.read_bytes()
        assert parsed['service_phase']==0 and parsed['sound_reads']==1
        assert out.read_bytes()==expected and bankout.read_bytes()==bytes(16384)
        assert data==b''.join(struct.pack('>BII',*event) for event in ports) and reads==[(1,0x320000,status)]
        irqrows.append(dict(status=status,ports=ports.copy(),ram_sha256=hashlib.sha256(expected).hexdigest()))
        cpu.context_restore(main_context)
        return bytearray(out.read_bytes())
    for entry,tail,priority in itertools.product((0x3d58,0x3d64),(0,127),(False,True)):
        ram=bytearray(65536);ram[0x4cf4:0x4d74]=bytes(range(128));put(ram,0x4d76,tail);put(ram,0x4d74,(tail+1)&127)
        struct.pack_into('>I',ram,0x81c,0x10081c);ram[0x4d7b]=0x80 if priority else 0
        first=len(rows);irqfirst=len(irqrows)
        pending=initial(entry,(0xabcd12e0,0x87654321,0xfedcba98))
        ram,pending,context=compare(ram,pending,label='irq-only-release-initial-wait')
        for status in ([0,1,0,0] if priority else [1,0,0]):
            ram=irq(ram,context,status)
            ram,pending,context=compare(ram,pending,context,label='irq-only-release-carried-producer')
            if pending['phase']==3:break
        assert pending['phase']==3
        sequences.append(dict(calls=len(rows)-first,irq_calls=len(irqrows)-irqfirst,actual_cli_ram_registers_pending_carried=True,head_changed_only_by_actual_irq=True,host_context_restore_not_irq_envelope=True,priority=priority))
    sentinel=b'previous-sound-pair-output\0\xff'
    def reject(ram,pending=None,label='invalid',alter=None):
        inp.write_bytes(ram);out.write_bytes(sentinel);args=arguments(pending or initial(0x3d58,(0,0,0)))
        if alter:args=alter(args)
        actual=subprocess.run(args,capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel,(label,actual.stderr)
        negatives.append(dict(failure=label,output_preserved=True,native_executed=False))
    for size in (0,65535,65537):reject(bytes(size),label='wrong-ram-size')
    for entry in (0,0x3d6a,0xffffffff):
        pending=initial(entry,(0,0,0));reject(fixture(),pending,label='unsupported-entry')
    for phase in (1,2,3,255):
        pending=initial(0x3d58,(0,0,0));pending['phase']=phase;reject(fixture(),pending,label='invalid-phase-without-pending')
    for at in (0x4d74,0x4d76):
        for value in (128,0xffff):
            ram=fixture();put(ram,at,value);reject(ram,label='invalid-used-byte-index')
    waiting=next(row['result'] for row in rows if row['result']['phase']==1)
    for key,value in (('command',3),('tail',128),('next',128),('next',55)):
        pending=json.loads(json.dumps(waiting));pending['byte'][key]=value;reject(fixture(),pending,label='forged-captured-pending')
    pending=initial(0x3d58,(0,0,0));pending['saved']=1;reject(fixture(),pending,label='fresh-nonzero-saved')
    for at,bad in itertools.product(range(1,10),('-1','4294967296','0x','1x','')):
        def alter(args,at=at,bad=bad):args=args.copy();args[at]=bad;return args
        reject(fixture(),label='invalid-parser',alter=alter)
    for kind in ('same','hardlink','symlink'):
        ram=fixture();inp.write_bytes(ram);alias=inp if kind=='same' else folder/('alias-'+kind+'.bin')
        if kind!='same':
            alias.unlink(missing_ok=True)
            if kind=='hardlink':alias.hardlink_to(inp)
            else:alias.symlink_to(inp)
        actual=subprocess.run(arguments(initial(0x3d58,(0,0,0)),alias),capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==ram
        negatives.append(dict(failure='input-output-'+kind+'-alias',output_preserved=True,native_executed=False))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    assert hashlib.sha256(executable.read_bytes()).hexdigest()==binary_sha
    report.write_text(json.dumps(dict(source=source,cpp_executable_sha256=binary_sha,program_code_modified=False,entries_cpu_and_rom_offsets=[0x3d58,0x3d64],emulator='Unicorn '+unicorn.__version__,cases=len(rows),negative_cases=len(negatives),irq_calls=len(irqrows),irq_ports=sum(len(row['ports']) for row in irqrows),full_ram_d0_d1_d3_pending_equal=True,producer_mmio_writes=0,carry_sequences=sequences,results=rows,negative_results=negatives,irq_results=irqrows,scope='Both original pair entries run through actual prefix byte producer, arithmetic and suffix producer to callerRTS or second3aea wait. Completed3af6 is lastnativeRTS marker, not callerPC. Prefix savedbyte independently captured from native stack; savedbyte retained as sideband after its original native stack pop. ActualCLI state/RAM carried with nativecontext/stack. Explicit hostrelease/live-tail mutation fixtures distinguished from8 IRQ-onlyrelease sequences where only actualc8c changeshead; IRQregister context restored host-side, not BIOS/SR/RTE/scheduler equivalence. Otherregisters/CCR/timing excluded; malformedstate original notrun.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negatives=len(negatives),irq_calls=len(irqrows),sequences=len(sequences),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__':main()
