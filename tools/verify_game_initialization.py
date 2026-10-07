"""Whole original47570/suffix comparisons and explicitly host-released waits."""
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
from verify_stage_catalog import SOURCE_SHA256,checked_resource
from verify_game_prelude import empty_word,empty_byte
BASE,ENTRY,SUFFIX,WAIT,RETURN,STACK=0x100000,0x47570,0x475a4,0x3aea,0xff000,0x1feffc
REGS=(m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D3)
CALLS=(0xb7a20,0x4d126,0x1bcfe,0x481de,0x1bd12,0xe89fa,0x3d42,0x3dce,
       0x49a8e,0x4aa30,0xb4a24,0x2ef90,0x6f1c2,0x46f2e,0x4d13c,0x4ddb6)
def word(ram,at):return struct.unpack_from('>H',ram,at)[0]
def put(ram,at,value):struct.pack_into('>H',ram,at,value&65535)
def initial(values=(0x12345678,0xabcd1234,0x87654321),phase=0):
    return dict(next_pc=SUFFIX if phase==4 else ENTRY,d0=values[0],d1=values[1],d3=values[2],
                phase=phase,external_reads=0,word=empty_word(),byte=empty_byte(),returned=False)


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert source['sha256']==SOURCE_SHA256
    resource=root/'extracted/runtime/game_records.ms5d';checked_resource(resource,program,0x4cf64,0x4d0a4)
    folder=root/'artifacts/game_initialization';folder.mkdir(parents=True,exist_ok=True)
    inp,out,report=[folder/name for name in ('input.bin','cpp.bin','verification.json')]
    report.unlink(missing_ok=True)
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000);cpu.mem_map(0xd00000,4096)
    cpu.mem_write(0x200000,program[0x200000:0x300000])
    state={'external':0,'waits':0};reads,paths,rows,negatives,sequences=[],[],[],[],[]
    def read(cpu,access,address,size,value,user):
        assert address==0xd00046 and size==1
        cpu.mem_write(address,bytes([state['external']]));reads.append((size,address,state['external']))
    def write(cpu,access,address,size,value,user):
        if not (BASE<=address and address+size<=BASE+65536 or 0x1f8000<=address and address+size<=0x1ff000):
            raise ValueError('Unexpected native initialization write '+hex(address))
    def code(cpu,address,size,user):
        if address in CALLS:paths.append(address)
        if address==RETURN:cpu.emu_stop()
        elif address==WAIT:
            if word(cpu.mem_read(BASE,65536),0x4d74)==(cpu.reg_read(REGS[1])&65535):
                state['waits']+=1
                if state['waits']==2:cpu.emu_stop()
            else:state['waits']=0
    cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    cpu.hook_add(UC_HOOK_MEM_READ,read,begin=0xd00046,end=0xd00046)
    def fixture(selectors=(0,0),active=(True,True),pattern=0):
        ram=bytearray(bytes([255])*65536 if pattern==0 else hashlib.shake_256(b'game-initialization-fixture').digest(65536))
        for base,selector,is_active in zip((0xcb8,0xda8),selectors,active):
            struct.pack_into('>I',ram,base,0 if is_active else 0x270e)
            put(ram,base+0x78,selector)
        for at in (0x4d8a,0x4d8c,0x4d74,0x4d76):put(ram,at,0)
        ram[0x12]=0;return ram
    def arguments(pending,external,records=resource):
        command=[str(root/'build/initialize_game'),'--state']+[str(pending[key]) for key in ('next_pc','d0','d1','d3','phase')]
        if pending['word']['waiting']:command+=['--word']+[str(pending['word'][key]) for key in ('phase','low','cursor','command','tail','next')]
        if pending['byte']['waiting']:command+=['--byte']+[str(pending['byte'][key]) for key in ('command','tail','next')]
        if pending['returned']:command+=['--returned','1']
        return command+[str(external),str(inp),str(out),str(records)]
    def compare(ram,pending=None,context=None,external=0,label='matrix',direct=False):
        pending=pending or initial();cpu.mem_write(BASE,bytes(ram))
        if context is None:
            for reg,value in ((m.UC_M68K_REG_SR,0x2000),(m.UC_M68K_REG_A5,0x108000),
                    (m.UC_M68K_REG_A6,0x1008e4),(m.UC_M68K_REG_A7,STACK)):
                cpu.reg_write(reg,value)
            cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        else:cpu.context_restore(context)
        for reg,key in zip(REGS,('d0','d1','d3')):cpu.reg_write(reg,pending[key])
        reads.clear();paths.clear();state.update(external=external,waits=0)
        cpu.emu_start(SUFFIX if direct else pending['next_pc'],0xffffff,count=100000)
        pc=cpu.reg_read(m.UC_M68K_REG_PC);assert pc in (RETURN,WAIT),hex(pc)
        result=initial(tuple(cpu.reg_read(reg)&0xffffffff for reg in REGS),4)
        result['external_reads']=len(reads);result['returned']=pc==RETURN
        if pc==WAIT:
            result['next_pc']=WAIT
            sp=cpu.reg_read(m.UC_M68K_REG_A7);ret=int.from_bytes(cpu.mem_read(sp,4),'big')
            captured=dict(waiting=True,command=cpu.reg_read(REGS[0])&255,
                tail=cpu.reg_read(m.UC_M68K_REG_A0)-BASE-0x4cf4,next=cpu.reg_read(REGS[1])&65535)
            if ret in (0x3c00,0x4759e):
                result['phase']=1;phase=1 if ret==0x3c00 else 2
                result['word'].update(captured,kind=1,phase=phase,
                    low=cpu.mem_read(sp+4,1)[0] if phase==1 else captured['command'])
            else:
                assert ret in (0x3d4c,0x3d42),hex(ret)
                result['phase']=2 if ret==0x3d4c else 3;result['byte']=captured
        else:
            assert (result['d0'],result['d1'],result['d3'])==(0,0,0)
            for address in CALLS:assert address in paths,(label,hex(address),paths)
            assert paths.count(0x481de)==2
        expected=bytes(cpu.mem_read(BASE,65536));inp.write_bytes(ram);out.unlink(missing_ok=True)
        command=([str(root/'build/finish_game')]+[str(pending[key]) for key in ('d0','d1','d3')]+[str(inp),str(out),str(resource)]) if direct else arguments(pending,external)
        actual=subprocess.run(command,capture_output=True,text=True)
        assert not actual.returncode,(label,actual.stderr)
        parsed=json.loads(actual.stdout)
        expected_json={key:result[key] for key in ('d0','d1','d3')} if direct else result
        actual_ram=out.read_bytes()
        if actual_ram!=expected or parsed!=expected_json:
            diff=[(hex(index),a,b) for index,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b]
            raise ValueError(repr((label,diff[:16],expected_json,parsed)))
        assert reads==([(1,0xd00046,external)] if pending['phase']==0 and not direct and ram[0x12]==1 and ram[0xfd82]!=0 and ram[0xfe80]==0 else [])
        rows.append(dict(profile=label,direct_suffix=direct,native_final_pc=pc,result=result,
            reads=reads.copy(),native_call_boundaries=paths.copy(),ram_sha256=hashlib.sha256(expected).hexdigest()))
        return bytearray(actual_ram),result if direct else parsed,cpu.context_save()
    for selectors,active,pattern,values in itertools.product(itertools.product((0,1,2,65535),repeat=2),
            itertools.product((False,True),repeat=2),range(2),((0,0,0),(0xffffffff,0xabcd1234,0x87654321))):
        ram=fixture(selectors,active,pattern)
        compare(ram,initial(values,4),label='all-object-combinations-direct-suffix',direct=True)
        compare(ram,initial(values),label='all-object-combinations-whole47570')
    for external,mode,fd82,fe80,fd8d in itertools.product((0,1),(0,1),(0,1),(0,1),(0,1)):
        ram=fixture();ram[0x12],ram[0xfd82],ram[0xfe80],ram[0xfd8d]=mode,fd82,fe80,fd8d
        compare(ram,external=external,label='whole47570-conditional-status-word-filter')
    for overflow,head in itertools.product((False,True),(1,2)):
        ram=fixture((2,65535),(True,False),1);put(ram,0x4d74,head)
        if overflow:put(ram,0x4d8c,6);put(ram,0x4d82,0x0455)
        start=len(rows);ram,pending,context=compare(ram,label='carried-initial-wait')
        edits=[];rounds=0
        while not pending['returned']:
            prior=bytes(ram);ram,pending,context=compare(ram,pending,context,label='carried-unchanged-wait')
            assert ram==prior
            captured=pending['word'] if pending['phase']==1 else pending['byte']
            released=(captured['next']+(1 if rounds==0 else 10))&127
            edits.append(dict(offset=0x4d74,old=word(ram,0x4d74),new=released))
            put(ram,0x4d74,released)
            ram,pending,context=compare(ram,pending,context,label='carried-host-released-wait-to-return')
            rounds+=1;assert rounds<=6
        sequences.append(dict(calls=len(rows)-start,host_sound_head_edits=edits,actual_cli_ram_full_regs_pending_carried=True))
    sentinel=b'previous-game-initialization-output'
    def reject(ram,pending=None,records=resource,label='invalid',command=None):
        inp.write_bytes(ram);out.write_bytes(sentinel)
        actual=subprocess.run(command or arguments(pending or initial(),0,records),capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==ram and out.read_bytes()==sentinel,(label,actual.stderr)
        negatives.append(dict(failure=label,output_preserved=True))
    bad_resource=folder/'bad-records.ms5d'
    packed=bytearray(resource.read_bytes());packed[12:16]=(0x4cf66).to_bytes(4,'little');packed[16:20]=(0x4cf66).to_bytes(4,'little');bad_resource.write_bytes(packed)
    reject(fixture(),records=bad_resource,label='completed-prefix-then-invalid-record-window-rollback')
    reject(fixture(),initial(phase=4),bad_resource,'suffix-prefix-resets-before-invalid-record-window-rollback')
    for size in (0,65535,65537):reject(bytes(size),label='invalid-size-'+str(size))
    for pc,phase in ((ENTRY,4),(SUFFIX,0),(WAIT,4),(SUFFIX,5)):
        pending=initial();pending.update(next_pc=pc,phase=phase);reject(fixture(),pending,label='invalid-state-boundary')
    pending=initial(phase=4);pending['returned']=True;reject(fixture(),pending,label='already-returned')
    for at,value in ((0x4d8a,1),(0x4d8c,8),(0x4d74,128),(0x4d76,65535)):
        ram=fixture();put(ram,at,value);reject(ram,label='invalid-live-queue-index')
    for option in ('--state','--byte','--word','--returned'):
        command=arguments(initial(),0)
        added={'--state':['0']*5,'--byte':['0']*3,'--word':['0']*6,'--returned':['0']}[option]
        if option=='--state':command[1:1]=[option]+added
        else:command[1:1]=[option]+added+[option]+added
        reject(fixture(),label='duplicate-'+option,command=command)
    for kind in ('same','hardlink','symlink','record-alias'):
        ram=fixture();inp.write_bytes(ram)
        if kind=='record-alias':alias=resource;before=resource.read_bytes()
        elif kind=='same':alias=inp;before=ram
        else:
            alias=folder/('alias-'+kind+'.bin');alias.unlink(missing_ok=True)
            if kind=='hardlink':alias.hardlink_to(inp)
            else:alias.symlink_to(inp)
            before=ram
        command=arguments(initial(),0);command[-2]=str(alias)
        actual=subprocess.run(command,capture_output=True,text=True)
        assert actual.returncode and alias.read_bytes()==before
        negatives.append(dict(failure='output-'+kind+'-alias',output_preserved=True))
    # Exercise the independent suffix CLI rejection paths as well.
    for failure in ('size','resource','d0','d1','d3','same','hardlink','symlink','record-alias'):
        ram=fixture() if failure!='size' else bytes(65535)
        inp.write_bytes(ram);out.write_bytes(sentinel)
        values=['1','2','3'];selected_resource=bad_resource if failure=='resource' else resource
        target=out
        if failure in ('d0','d1','d3'):values[('d0','d1','d3').index(failure)]='4294967296'
        if failure=='same':target=inp
        if failure in ('hardlink','symlink'):
            target=folder/('suffix-'+failure+'.bin');target.unlink(missing_ok=True)
            if failure=='hardlink':target.hardlink_to(inp)
            else:target.symlink_to(inp)
        if failure=='record-alias':target=resource
        before=target.read_bytes()
        command=[str(root/'build/finish_game')]+values+[str(inp),str(target),str(selected_resource)]
        actual=subprocess.run(command,capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==ram and target.read_bytes()==before,(failure,actual.stderr)
        negatives.append(dict(failure='suffix-cli-'+failure,output_preserved=True))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    assert {1,2,3,4}.issubset({row['result']['phase'] for row in rows})
    report.write_text(json.dumps(dict(source=source,emulator='Unicorn '+unicorn.__version__,program_code_modified=False,
        entry_cpu_addresses=[ENTRY,SUFFIX],native_cpp_cases=len(rows),negative_cases=len(negatives),
        whole_ram_full_d0_d1_d3_equal=True,no_native_mmio_writes=True,
        external_reads=sum(len(row['reads']) for row in rows),carry_sequences=sequences,
        results=rows,negative_results=negatives,
        scope='Whole immutable47570 and475a4 suffix execute all nested original callees to RTS or actual3aea '
            'producer waits. Complete RAM and full D0/D1/D3 compared; pending state independently captured from '
            'native stack return addresses. Wait sequences carry actual CLI RAM/register/pending outputs and '
            'preserve native context/stack, but explicitly edit sound head word4d74 to release waits; this is '
            'a bounded host fixture, not IRQ/scheduler equivalence. Other CPU registers,CCR,stack equivalence, '
            'natural caller execution and hardware timing are excluded. Returned JSON keeps475a4/phase4 as '
            'last internal boundary rather than claiming it is the caller return PC.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negatives=len(negatives),sequences=len(sequences),
        external_reads=sum(len(row['reads']) for row in rows),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))


if __name__=='__main__':main()
