"""Unmodified stage transition entries/callbacks to scheduler or clear boundaries."""
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
from verify_palette_state import call
from verify_stage_catalog import SOURCE_SHA256
BASE,STACK=0x100000,0x1feffc
REGS=(m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D2,m.UC_M68K_REG_D3,m.UC_M68K_REG_A6)
KEYS=('d0','d1','d2','d3','a6')
ENTRIES=(0x478c4,0x478f0,0x4791c,0x47934,0x4794c,0x47964,0x478de,0x4790a,0x4798e)

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
    folder=root/'artifacts/stage_transition';folder.mkdir(parents=True,exist_ok=True)
    inp,out,portfile,report=[folder/name for name in ('input.bin','cpp.bin','ports.bin','verification.json')];report.unlink(missing_ok=True)
    executable=root/'build/step_stage_transition';binary_sha=hashlib.sha256(executable.read_bytes()).hexdigest()
    cpu=make_cpu(program);cpu.mem_map(0x300000,0x100000)
    rows,negatives,sequences,ports,reads,paths=[],[],[],[],[],[];state=dict(loop_entries=0,entry=0)
    def code(cpu,address,size,user):
        if address in (0x480bc,0x479b0):cpu.emu_stop()
        elif address==0x478de:
            state['loop_entries']+=1
            if state['loop_entries']==2:cpu.emu_stop()
        if address in (0x8c16,0x28ae,0x72f0,0xca8a,0xcaf0):paths.append(address)
    def write(cpu,access,address,size,value,user):
        if address in (0x300001,0x3c0000,0x3c0004):ports.append((size,address,value&((1<<(size*8))-1)))
        else:assert BASE<=address and address+size<=BASE+65536 or 0x1f8000<=address and address+size<=0x1ff000,(hex(address),size,value)
    def read(cpu,access,address,size,value,user):
        if 0x300000<=address<0x400000:reads.append((size,address))
    cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_MEM_READ,read)
    cpu.mem_write(BASE,bytes(65536));call(cpu,0x2790);call(cpu,0x3ef2);base_fixture=bytes(cpu.mem_read(BASE,65536))
    def fixture(a6=0x100b30,currents=(0,0,0),count=80,depth=0):
        ram=bytearray(base_fixture);at=a6-BASE
        struct.pack_into('>3H',ram,0x7dc2,*currents);struct.pack_into('>H',ram,0x4ca0,count);struct.pack_into('>H',ram,at+0x10,depth)
        ram[at+0x62]=0;struct.pack_into('>HH',ram,0xd690,0x1234,0xabcd)
        return ram
    def compare(ram,entry,values,label,context=None):
        cpu.mem_write(BASE,bytes(ram))
        if context is None:
            cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK,(0xff000).to_bytes(4,'big'))
        else:cpu.context_restore(context)
        for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
        ports.clear();reads.clear();paths.clear();state.update(loop_entries=0,entry=entry)
        cpu.emu_start(entry,0xffffff,count=100000)
        pc=cpu.reg_read(m.UC_M68K_REG_PC);assert pc in (0x480bc,0x479b0,0x478de),(label,hex(pc))
        assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK
        if pc==0x478de:assert state['loop_entries']==2 and paths.count(0x72f0)==1
        expected=bytes(cpu.mem_read(BASE,65536));result=dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)));result.update(next_pc=pc,writes=len(ports))
        inp.write_bytes(ram);actual=subprocess.run([str(executable),str(entry)]+[str(value) for value in values]+[str(inp),str(out),str(portfile)],capture_output=True,text=True)
        assert not actual.returncode,(label,actual.stderr)
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes();data=portfile.read_bytes()
        if parsed!=result or actual_ram!=expected or data!=b''.join(struct.pack('>BII',*event) for event in ports):
            diff=[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b]
            raise ValueError(repr((label,entry,values,diff[:16],result,parsed,len(ports),len(data)//9)))
        assert not reads and result['a6']==values[4]
        rows.append(dict(profile=label,entry=entry,incoming=dict(zip(KEYS,values)),result=parsed,native_calls=paths.copy(),loop_entries=state['loop_entries'],ram_sha256=hashlib.sha256(expected).hexdigest(),ports_sha256=hashlib.sha256(data).hexdigest(),port_examples=ports[:4]+ports[-4:] if ports else []))
        return bytearray(actual_ram),parsed,cpu.context_save()
    highs=((0,0,0,0),(0xabcd1234,0x87654321,0xfedcba98,0x1234abcd),(0xffffffff,0xffffffff,0xffffffff,0xffffffff))
    currents=((0,0,0),(0xe100,0xe100,0xe100),(0x1f00,0x1f00,0x1f00),(0x7fff,0x8000,0xffff),(0xfffe,1,0x8001),(0x1234,0xfedc,0xabcd))
    for entry,a6,current,values in itertools.product((0x478c4,0x478f0,0x4791c),(0x100820,0x100b30),currents,highs):
        first=len(rows);compare(fixture(a6,current),entry,values+(a6,),'durations-target-equality-signed-divs-remainders')
        if entry==0x4791c:assert rows[first]['result']['writes']==2072
        if current==((0x1f00,)*3 if entry==0x4791c else (0xe100,)*3):
            assert rows[first]['result']['d0']==(0 if entry==0x4791c else 0xffff0000)
            assert rows[first]['result']['d3']==(0 if entry==0x4791c else values[3]&0xffff0000)
    for entry,current,values in itertools.product((0x478f0,0x4791c),currents,highs):
        compare(fixture(0x107d48,current),entry,values+(0x107d48,),'controlled-counter-field-aliases-live-palette-current')
    for entry,a6,count,depth,values in itertools.product((0x47934,0x4794c,0x47964),(0x100820,0x100b30),(0,1,80),(0,1,0x7fff,0xffff),highs):
        ram=fixture(a6,(0x1234,0xfedc,0xabcd),count,depth)
        if count==0:struct.pack_into('>I',ram,0x4c9c,0xdeadbeef)
        compare(ram,entry,values+(a6,),'allocation-success-failure-parent-depth-and-linked-runtime')
    for entry in (0x47964,):
        ram=fixture();node=0xd61c;struct.pack_into('>I',ram,0x4c9c,BASE+node);struct.pack_into('>I',ram,node+8,0x101800)
        ram,state_out,context=compare(ram,entry,(0xabcd1234,0x87654321,0xfedcba98,0x1234abcd,0x100b30),'controlled-live-copy-first-write-aliases-second-source')
        assert ram[node+0x76:node+0x78]==bytes.fromhex('1234') and ram[node+0x78:node+0x7a]==bytes.fromhex('1234')
    for gate,values in itertools.product(range(256),highs):
        ram=fixture();ram[0x7ded]=gate;first=len(rows)
        compare(ram,0x478de,values+(0x100b30,),'all256-palette-transfer-status-single-helper-loopback')
        assert rows[first]['result']['next_pc']==(0x479b0 if gate<128 else 0x478de)
        assert rows[first]['result']['writes']==(1283 if gate<128 else 0)
    for a6,counter,values in itertools.product((0x100820,0x100b30),(0,1,0xffff),highs):
        ram=fixture(a6);struct.pack_into('>H',ram,a6-BASE+0x7a,counter);first=len(rows)
        compare(ram,0x4790a,values+(a6,),'countdown-underflow-not-zero')
        assert rows[first]['result']['next_pc']==(0x479b0 if counter==0 else 0x480bc)
    for flag,values in itertools.product((0,1,127,128,255),highs):
        ram=fixture();ram[0xb92]=flag
        compare(ram,0x4798e,values+(0x100b30,),'allocated-child-completion-flag')
    for entry in (0x478c4,0x478f0,0x4791c,0x47934,0x4794c,0x47964):
        ram=fixture();first=len(rows);ram,parsed,context=compare(ram,entry,highs[1]+(0x100b30,),'actual-cli-entry-to-recorded-callback')
        callback=int.from_bytes(ram[0xb30:0xb34],'big')
        if callback==0x478de:
            ram[0x7ded]=255
            ram,parsed,context=compare(ram,callback,tuple(parsed[key] for key in KEYS),'host-scheduled-callback-waits',context)
            ram[0x7ded]=0
            ram,parsed,context=compare(ram,callback,tuple(parsed[key] for key in KEYS),'host-scheduled-callback-ready',context)
        elif callback==0x4790a:
            for iteration in range(62):
                ram,parsed,context=compare(ram,callback,tuple(parsed[key] for key in KEYS),'host-scheduled-countdown-callback',context)
                if parsed['next_pc']==0x479b0:break
            assert parsed['next_pc']==0x479b0
        else:
            assert callback==0x4798e;ram[0xb92]=255
            ram,parsed,context=compare(ram,callback,tuple(parsed[key] for key in KEYS),'host-scheduled-completion-flag-callback',context)
            assert int.from_bytes(ram[0xb30:0xb34],'big')==0x479b0
        sequences.append(dict(calls=len(rows)-first,actual_cli_ram_full_registers_carried=True,native_context_preserved=True,host_inputs='explicit scheduling of installed callback; gate/child flag fixtures, never execute480bc scheduler'))
    sentinel=b'old-stage-transition-output\0\xff'
    def reject(ram,entry='0x478c4',values=('0','0','0','0','0x100b30'),label='invalid'):
        inp.write_bytes(ram);out.write_bytes(sentinel);portfile.write_bytes(sentinel)
        actual=subprocess.run([str(executable),entry]+list(values)+[str(inp),str(out),str(portfile)],capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel and portfile.read_bytes()==sentinel,(label,actual.stderr)
        negatives.append(dict(failure=label,outputs_preserved=True,native_executed=False))
    for size in (0,65535,65537):reject(bytes(size),label='invalid-ram-size')
    for entry in ('0','0x480bc','0x479b0'):reject(fixture(),entry,label='unsupported-entry')
    for bad in (0,0x100001,0x10ff3e,0xffffffff):reject(fixture(),values=('0','0','0','0',str(bad)),label='invalid-object-pointer')
    for pointer in (0,0x100001,0x10ff96,0x110000,0xffffffff):
        ram=fixture();struct.pack_into('>I',ram,0x4c9c,pointer);reject(ram,entry='0x47964',label='late-invalid-allocation-freehead')
    ram=fixture();struct.pack_into('>I',ram,0xb38,0xdeadbeef);reject(ram,entry='0x47934',label='late-invalid-allocation-successor')
    for field,bad in itertools.product(range(6),('-1','4294967296','0x','1x','')):
        args=['0x478c4','0','0','0','0','0x100b30'];args[field]=bad;reject(fixture(),entry=args[0],values=args[1:],label='invalid-uint32-parser')
    for kind in ('same','hardlink','symlink'):
        ram=fixture();inp.write_bytes(ram);alias=inp if kind=='same' else folder/('alias-'+kind+'.bin')
        if kind!='same':
            alias.unlink(missing_ok=True)
            if kind=='hardlink':alias.hardlink_to(inp)
            else:alias.symlink_to(inp)
        portfile.write_bytes(sentinel);actual=subprocess.run([str(executable),'0x478c4','0','0','0','0','0x100b30',str(inp),str(alias),str(portfile)],capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==ram and portfile.read_bytes()==sentinel
        negatives.append(dict(failure='input-output-'+kind+'-alias',outputs_preserved=True,native_executed=False))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    assert hashlib.sha256(executable.read_bytes()).hexdigest()==binary_sha
    assert {row['result']['next_pc'] for row in rows}=={0x480bc,0x479b0,0x478de}
    report.write_text(json.dumps(dict(source=source,cpp_executable_sha256=binary_sha,cpp_binary_unchanged_during_verification=True,program_code_modified=False,emulator='Unicorn '+unicorn.__version__,entries_cpu_and_rom_offsets=list(ENTRIES),cases=len(rows),negative_cases=len(negatives),ports=sum(row['result']['writes'] for row in rows),mmio_reads=0,full_ram_d0_d1_d2_d3_a6_ordered_ports_equal=True,carry_sequences=sequences,results=rows,negative_results=negatives,scope='All native transition/callback instructions execute to480bc/479b0 beforebody;478de wait recorded only after72f0 has run once and actualloopback. Exact RAM/full exposed registers/orderedports, including packedDIVS remainders and unchanged-delta highwords. Runtime2790/3ef2 RAM fixture with controlledcurrentpalette/queuecounts/depth/livealias. ActualCLI RAM/registers carry across explicitly hostscheduled installed callbacks while nativeCPUcontext preserved;480bc scheduler and callbackbodiesoutsideentryset not executed. Gate/child flag changes are hostfixtures, no hardwaretiming/IRQ claim. Otherregisters/CCR/stack equivalence excluded; invalidpointer originalnotrun.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negatives=len(negatives),ports=sum(row['result']['writes'] for row in rows),sequences=len(sequences),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__':main()
