"""Nativec610 restart through actual callees and host-released producer waits."""
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
from verify_stage_catalog import SOURCE_SHA256,checked_resource
from verify_game_prelude import empty_word,empty_byte
BASE,ENTRY,WAIT,RETURN,STACK=0x100000,0xc610,0x3aea,0xff000,0x1feffc
REGS=(m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D3)
CALLS=(0x49a1a,0xc4cc,0xcaf0,0x47570,0x475a4,0x4823a,0x3162,0x299c,0x35a2,0x481de,0x1bcfe,0x1bd12)
def put(ram,at,value):struct.pack_into('>H',ram,at,value&65535)
def word(ram,at):return struct.unpack_from('>H',ram,at)[0]
def initial(values=(0x12345678,0xabcd1234,0x87654321),a6=0x100820):
    return dict(outer_phase=0,a6=a6,next_pc=0x47570,d0=values[0],d1=values[1],d3=values[2],phase=0,word=empty_word(),byte=empty_byte(),returned=False,external_reads=0,writes=0)

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
    records=root/'extracted/runtime/game_records.ms5d';streams=root/'extracted/runtime/input_streams.ms5d'
    hashes=dict(records=checked_resource(records,program,0x4cf64,0x4d0a4),streams=checked_resource(streams,program,0xf01fe,0xf1a0e))
    folder=root/'artifacts/game_restart';folder.mkdir(parents=True,exist_ok=True)
    inp,out,portfile,report=[folder/name for name in ('input.bin','cpp.bin','ports.bin','verification.json')];report.unlink(missing_ok=True)
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000);cpu.mem_map(0xd00000,4096)
    cpu.mem_write(0x200000,program[0x200000:0x300000])
    rows,negatives,sequences,ports,reads,paths=[],[],[],[],[],[];state=dict(external=0,waits=0)
    def code(cpu,address,size,user):
        if address in CALLS:paths.append(address)
        if address==RETURN:cpu.emu_stop()
        elif address==WAIT:
            if int.from_bytes(cpu.mem_read(BASE+0x4d74,2),'big')==(cpu.reg_read(REGS[1])&65535):
                state['waits']+=1
                if state['waits']==2:cpu.emu_stop()
            else:state['waits']=0
    def write(cpu,access,address,size,value,user):
        if address in (0x300001,0x3c0000,0x3c0004):ports.append((size,address,value&((1<<(8*size))-1)))
        else:assert BASE<=address and address+size<=BASE+65536 or 0x1f8000<=address and address+size<=0x1ff000,(hex(address),size,value)
    def read(cpu,access,address,size,value,user):
        assert address==0xd00046 and size==1;cpu.mem_write(address,bytes([state['external']]));reads.append((size,address,state['external']))
    cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_MEM_READ,read,begin=0xd00046,end=0xd00046)
    # Actual runtime object list initializer produces every initial pointer.
    cpu.mem_write(BASE,bytes(65536));call(cpu,0x2790);native_boot=bytes(cpu.mem_read(BASE,65536));inp.write_bytes(bytes(65536))
    boot=root/'extracted/runtime/object_boot.ms5i';bootrun=subprocess.run([str(root/'build/init_objects'),str(boot),str(inp),str(out)],capture_output=True,text=True)
    assert not bootrun.returncode and out.read_bytes()==native_boot,bootrun.stderr
    call(cpu,0x3ef2);base_fixture=bytes(cpu.mem_read(BASE,65536))
    def fixture(children=0,mode=0,a6=0x100820):
        ram=bytearray(base_fixture);cpu.mem_write(BASE,bytes(ram))
        for index in range(children):
            cpu.reg_write(m.UC_M68K_REG_A6,a6);cpu.reg_write(m.UC_M68K_REG_A0,0x1234+index*2);cpu.reg_write(REGS[0],0);call(cpu,0x28ae)
        ram=bytearray(cpu.mem_read(BASE,65536))
        for at in (0x4d8a,0x4d8c,0x4d74,0x4d76):put(ram,at,0)
        ram[0x12]=mode;ram[0xfd82]=1;ram[0xfe80]=0
        return ram
    def arguments(pending,external=0,recordpath=records,streampath=streams):
        args=[str(root/'build/restart_game'),'--phase',str(pending['outer_phase']),'--a6',str(pending['a6']),'--state']+[str(pending[key]) for key in ('next_pc','d0','d1','d3','phase')]
        if pending['word']['waiting']:args+=['--word']+[str(pending['word'][key]) for key in ('phase','low','cursor','command','tail','next')]
        if pending['byte']['waiting']:args+=['--byte']+[str(pending['byte'][key]) for key in ('command','tail','next')]
        return args+[str(external),str(inp),str(out),str(portfile),str(recordpath),str(streampath)]
    def compare(ram,pending=None,context=None,external=0,label='matrix'):
        pending=pending or initial();cpu.mem_write(BASE,bytes(ram))
        if context is None:
            cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        else:cpu.context_restore(context)
        for reg,key in zip(REGS,('d0','d1','d3')):cpu.reg_write(reg,pending[key])
        cpu.reg_write(m.UC_M68K_REG_A6,pending['a6'])
        ports.clear();reads.clear();paths.clear();state.update(external=external,waits=0)
        cpu.emu_start(ENTRY if pending['outer_phase']==0 else WAIT,0xffffff,count=300000)
        pc=cpu.reg_read(m.UC_M68K_REG_PC);assert pc in (RETURN,WAIT),(label,hex(pc))
        result=initial(tuple(cpu.reg_read(reg)&0xffffffff for reg in REGS),cpu.reg_read(m.UC_M68K_REG_A6)&0xffffffff)
        result.update(outer_phase=2 if pc==RETURN else 1,next_pc=0x475a4 if pc==RETURN else WAIT,phase=4,returned=pc==RETURN,external_reads=len(reads),writes=len(ports))
        if pc==WAIT:
            sp=cpu.reg_read(m.UC_M68K_REG_A7);ret=int.from_bytes(cpu.mem_read(sp,4),'big')
            captured=dict(waiting=True,command=cpu.reg_read(REGS[0])&255,tail=cpu.reg_read(m.UC_M68K_REG_A0)-BASE-0x4cf4,next=cpu.reg_read(REGS[1])&65535)
            if ret in (0x3c00,0x4759e):
                phase=1 if ret==0x3c00 else 2;result['phase']=1
                result['word'].update(captured,kind=1,phase=phase,low=cpu.mem_read(sp+4,1)[0] if phase==1 else captured['command'])
            else:
                assert ret in (0x3d4c,0x3d42),hex(ret);result['phase']=2 if ret==0x3d4c else 3;result['byte']=captured
        expected=bytes(cpu.mem_read(BASE,65536));inp.write_bytes(ram)
        actual=subprocess.run(arguments(pending,external),capture_output=True,text=True)
        assert not actual.returncode,(label,actual.stderr)
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes();data=portfile.read_bytes()
        actual_ports=[struct.unpack('>BII',data[at:at+9]) for at in range(0,len(data),9)]
        if parsed!=result or actual_ram!=expected or actual_ports!=ports:
            diff=[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b]
            raise ValueError(repr((label,diff[:16],result,parsed,len(ports),len(actual_ports))))
        if pending['outer_phase']==0:assert {0x49a1a,0xc4cc,0xcaf0,0x47570}<=set(paths)
        else:assert not ports and not ({0x49a1a,0xc4cc,0xcaf0,0x47570}&set(paths))
        if pc==RETURN:
            assert 0x3162 in paths and 0x475a4 in paths
            assert result['d0']&65535==0 and int.from_bytes(expected[result['a6']-BASE:result['a6']-BASE+4],'big')==0xc654
            assert expected[0xd680]==6+(word(expected,0xf02a)&1)
        rows.append(dict(profile=label,incoming=pending,result=parsed,ports=ports.copy(),reads=reads.copy(),native_calls=paths.copy(),ram_sha256=hashlib.sha256(expected).hexdigest()))
        return bytearray(actual_ram),parsed,cpu.context_save()
    for children,mode,external,values,a6 in itertools.product((0,1,3),(0,1),(0,255),((0,0,0),(0xffffffff,0xabcd1234,0x87654321)),(0x100820,0x1008e4)):
        compare(fixture(children,mode,a6),initial(values,a6),external=external,label='actual-runtime-list-fresh-completion')
    for waitkind,tail,live in itertools.product(('wordhigh','wordlow','byte8','byte20'),(0,127),(0,1,2,0xffff)):
        ram=fixture(1,1,0x1008e4);ram[0xfd8d]=1;put(ram,0x4d76,tail)
        if waitkind.startswith('word'):
            put(ram,0x4d8a,0);put(ram,0x4d8c,6);put(ram,0x4d82,0x0455)
            head=(tail+(1 if waitkind=='wordhigh' else 2))&127
        else:head=(tail+(1 if waitkind=='byte8' else 2))&127
        put(ram,0x4d74,head);first=len(rows)
        ram,pending,context=compare(ram,initial(a6=0x1008e4),label='producer-wait-'+waitkind)
        assert pending['outer_phase']==1
        observed=(pending['phase'],pending['word']['phase'])
        assert observed=={'wordhigh':(1,1),'wordlow':(1,2),'byte8':(2,0),'byte20':(3,0)}[waitkind],(waitkind,observed)
        ram,pending,context=compare(ram,pending,context,label='repeated-wait-no-prefix')
        put(ram,0xf02a,live) # Explicit host fixture tests resumed LIVE selector.
        releases=[]
        for iteration in range(8):
            release=(pending['word']['next'] if pending['word']['waiting'] else pending['byte']['next'])+16
            put(ram,0x4d74,release&127);releases.append(release&127)
            ram,pending,context=compare(ram,pending,context,external=255,label='host-head-release-live-selector')
            if pending['outer_phase']==2:break
        assert pending['outer_phase']==2
        assert word(ram,0xf02a)==live&1 and ram[0xd680]==6+(live&1)
        assert int.from_bytes(ram[0x4cc4:0x4cc8],'big')==int.from_bytes(program[0xf0dfe+4*(live&1):0xf0e02+4*(live&1)],'big')
        sequences.append(dict(calls=len(rows)-first,kind=waitkind,live_f02a_host_value=live,head_releases=releases,actual_cli_ram_registers_pending_carried=True,native_cpu_context_preserved=True))
    sentinel=b'previous-restart-output\0\xff'
    def reject(ram,pending=None,label='invalid',recordpath=records,streampath=streams,alter=None):
        inp.write_bytes(ram);out.write_bytes(sentinel);portfile.write_bytes(sentinel)
        args=arguments(pending or initial(),recordpath=recordpath,streampath=streampath)
        if alter is not None:args=alter(args)
        actual=subprocess.run(args,capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel and portfile.read_bytes()==sentinel,(label,actual.stderr)
        negatives.append(dict(failure=label,outputs_preserved=True,native_executed=False))
    for size in (0,65535,65537):reject(bytes(size),label='invalid-ram-size')
    for phase in (2,3,255):
        pending=initial();pending['outer_phase']=phase;reject(fixture(),pending,label='invalid-or-returned-outer-phase')
    pending=initial();pending['outer_phase']=1;reject(fixture(),pending,label='wait-without-pending')
    actual_wait=next(row['result'] for row in rows if row['result']['word']['waiting'])
    for badfield,badvalue in (('phase',0),('tail',128),('next',128)):
        pending=json.loads(json.dumps(actual_wait));pending['word'][badfield]=badvalue
        reject(fixture(),pending,label='invalid-captured-word-'+badfield)
    pending=json.loads(json.dumps(actual_wait));pending['byte']=dict(waiting=True,command=8,tail=0,next=1)
    reject(fixture(),pending,label='contradictory-word-and-byte-waits')
    pending=json.loads(json.dumps(actual_wait));pending['phase']=2
    reject(fixture(),pending,label='inner-phase-pending-mismatch')
    for bad in (0,0x100001,0x10ff3e,0xffffffff):
        pending=initial(a6=bad);reject(fixture(),pending,label='invalid-main-object')
    for index in (8,127):
        ram=fixture();ram[0x1000+0x6c]=index
        # Choose a guaranteed runtime static node from sentinel next.
        node=int.from_bytes(ram[0x828:0x82c],'big')-BASE;ram[node+0x6c]=index
        reject(ram,label='late-removal-coordinate-trap')
    badresource=folder/'wrong-window.ms5d';data=bytearray(records.read_bytes());struct.pack_into('<II',data,12,0x4cf62,0x4cf62);badresource.write_bytes(data)
    reject(fixture(),recordpath=badresource,label='late-record-resource-after-prefix')
    data=bytearray(streams.read_bytes());struct.pack_into('<II',data,12,0xf01fc,0xf01fc);badresource.write_bytes(data)
    reject(fixture(),streampath=badresource,label='late-input-resource-after-initialization')
    for flag in ('--phase','--a6','--state'):
        for bad in ('-1','4294967296','0x','1x',''):
            def alter(args,flag=flag,bad=bad):
                args=args.copy();args[args.index(flag)+1]=bad;return args
            reject(fixture(),label='invalid-state-parser',alter=alter)
    for kind in ('same','hardlink','symlink'):
        ram=fixture();inp.write_bytes(ram);alias=inp if kind=='same' else folder/('alias-'+kind+'.bin')
        if kind!='same':
            alias.unlink(missing_ok=True)
            if kind=='hardlink':alias.hardlink_to(inp)
            else:alias.symlink_to(inp)
        portfile.write_bytes(sentinel);args=arguments(initial());args[args.index(str(out))]=str(alias)
        actual=subprocess.run(args,capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==ram and portfile.read_bytes()==sentinel
        negatives.append(dict(failure='input-output-'+kind+'-alias',outputs_preserved=True,native_executed=False))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    assert program[0x180:0x182]==bytes(2)
    report.write_text(json.dumps(dict(source=source,resources_sha256=hashes,emulator='Unicorn '+unicorn.__version__,program_code_modified=False,entry_cpu_address=ENTRY,entry_rom_offset=ENTRY,cases=len(rows),negative_cases=len(negatives),ports=sum(len(row['ports']) for row in rows),external_reads=sum(len(row['reads']) for row in rows),full_ram_d0_d1_d3_a6_ports_pending_equal=True,carry_sequences=sequences,results=rows,negative_results=negatives,scope='Nativec610 throughc652 RTS executes all nested original callees. Runtime lists are actual2790/MS5I outputs with optional actual28ae children; palette initialized by original3ef2. Native waits preserve CPU context/stack and actual CLI outputs carry full RAM/registers/pending. Host explicitly changes sound head and f02a while waiting; resumed cleanup/screen/seed prefix never reruns. Original3162 executes, nativeROM180 remains0. IRQ, natural timing, callbackc654 execution, other registers/CCR and stack equivalence excluded.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negatives=len(negatives),sequences=len(sequences),ports=sum(len(row['ports']) for row in rows),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__':main()
