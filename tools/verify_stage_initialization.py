"""Native477e4/477ee stage prefix, real catalog records and live sound resumes."""
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import struct
import subprocess
import zlib
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call
from verify_stage_catalog import SOURCE_SHA256,verify_resources,checked_resource
from verify_sound_pair import initial as pair_initial
BASE,STACK,WAIT=0x100000,0x1feffc,0x3aea
TARGETS=(0x478c4,0x478f0,0x4791c,0x47934,0x4794c,0x47964)
REGS=(m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D3)
KEYS=('d0','d1','d3')
def put(ram,at,value):struct.pack_into('>H',ram,at,value&65535)
def initial(pc=0x477ee,values=(0xabcd1234,0x87654321,0xfedcba98),a6=0x100b30):
    return dict(next_pc=pc,phase=0,d0=values[0],d1=values[1],d3=values[2],a6=a6,writes=0,sound=pair_initial(0x3d58,(0,0,0)))

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
    catalog=root/'extracted/runtime/stages';groups=verify_resources(catalog,program,source)
    records=[(group['index'],area,record['source_cpu_address']) for group in groups for area,record in enumerate(group['records'])];assert len(records)==59
    tables=root/'extracted/runtime/scene_debug.ms5d';table_sha=checked_resource(tables,program,0x1af12,0x1b112)
    folder=root/'artifacts/stage_initialization';folder.mkdir(parents=True,exist_ok=True)
    inp,out,portfile,report=[folder/name for name in ('input.bin','cpp.bin','ports.bin','verification.json')];report.unlink(missing_ok=True)
    executable=root/'build/step_stage_entry';binary_sha=hashlib.sha256(executable.read_bytes()).hexdigest()
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x300000);cpu.mem_write(0x200000,program[0x200000:0x300000])
    rows,negatives,sequences,ports,reads,paths,loopobservations,dispatchobservations=[],[],[],[],[],[],[],[]
    state=dict(bank=0x200000,waits=0,saved=None,sound_done=None,loop_budget=None,loop_count=0)
    def code(cpu,address,size,user):
        if address in TARGETS:cpu.emu_stop()
        if address in (0x1a5a4,0x474e2,0x47540,0xca48,0x1c5b0,0xca7e,0x4e24e,0x9056,0x3d58,0x4814e,0xca9e):paths.append(address)
        if address==0x477fa and state['loop_budget']:
            state['loop_count']+=1
            if state['loop_count']==state['loop_budget']:cpu.emu_stop()
        if address==0x47886:state['saved']=cpu.reg_read(REGS[0])&255
        if address==0x4788c:
            pair=pair_initial(0x3d58,tuple(cpu.reg_read(reg)&0xffffffff for reg in REGS))
            pair.update(next_pc=0x3af6,phase=3,saved=state['saved']);state['sound_done']=pair
        if address==WAIT:
            if int.from_bytes(cpu.mem_read(BASE+0x4d74,2),'big')==(cpu.reg_read(REGS[1])&65535):
                state['waits']+=1
                if state['waits']==2:cpu.emu_stop()
            else:state['waits']=0
    def write(cpu,access,address,size,value,user):
        value&=(1<<(8*size))-1
        if address in (0x2ffff0,0x2ffff2,0x300001,0x3c0000,0x3c0004):
            ports.append((size,address,value))
            if address==0x2ffff2:
                assert size==2 and value in (0x1000,0x2000);offset=0x200000 if value==0x1000 else 0x300000
                cpu.mem_write(0x200000,program[offset:offset+0xffff0]);state['bank']=offset
        else:assert BASE<=address and address+size<=BASE+65536 or 0x1f8000<=address and address+size<=0x1ff000,(hex(address),size,value)
    def read(cpu,access,address,size,value,user):
        if 0x2ffff0<=address<0x500000:reads.append((size,address))
    cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_MEM_READ,read)
    cpu.mem_write(BASE,bytes(65536));call(cpu,0x2790);call(cpu,0x3ef2);base_fixture=bytes(cpu.mem_read(BASE,65536))
    def fixture(stage=0,area=0,music_equal=True,callbacks=(0,0),bits=0):
        ram=bytearray(base_fixture);ram[0xd680]=stage;ram[0xd681]=area;ram[0xd683]=255;ram[0xf000]=bits
        actualgroup=stage if stage<19 else 0;actualarea=area if area<len(groups[actualgroup]['records']) else 0
        if groups[actualgroup]['records']:
            address=groups[actualgroup]['records'][actualarea]['source_cpu_address'];music=int.from_bytes(program[address+0x10:address+0x12],'big')
            put(ram,0xd686,music if music_equal else music^0xffff)
        for at,callback in zip((0xcb8,0xda8),callbacks):struct.pack_into('>I',ram,at,callback)
        for at in (0x4d74,0x4d76):put(ram,at,0)
        return ram
    def arguments(pending,cat=catalog,table=tables,target=out,porttarget=portfile):
        return [str(executable)]+[str(pending[key]) for key in ('next_pc','phase','d0','d1','d3','a6')]+[str(pending['sound'][key]) for key in ('phase','saved')]+[str(pending['sound']['byte'][key]) for key in ('command','tail','next')]+[str(inp),str(target),str(porttarget),str(cat),str(table)]
    def compare(ram,pending=None,context=None,label='catalog-record'):
        pending=pending or initial();cpu.mem_write(BASE,bytes(ram))
        if context is None:
            cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK,(0xff000).to_bytes(4,'big'))
        else:cpu.context_restore(context)
        for reg,key in zip(REGS,KEYS):cpu.reg_write(reg,pending[key])
        cpu.reg_write(m.UC_M68K_REG_A6,pending['a6']);ports.clear();reads.clear();paths.clear()
        state.update(waits=0,saved=pending['sound']['saved'] if pending['phase']==1 else None,sound_done=None,loop_budget=None,loop_count=0)
        cpu.emu_start(pending['next_pc'],0xffffff,count=300000)
        pc=cpu.reg_read(m.UC_M68K_REG_PC);assert pc in TARGETS+(WAIT,),hex(pc)
        result=initial(pc,tuple(cpu.reg_read(reg)&0xffffffff for reg in REGS),cpu.reg_read(m.UC_M68K_REG_A6)&0xffffffff)
        result.update(phase=1 if pc==WAIT else 2,writes=len(ports));result['sound']=state['sound_done'] or pending['sound']
        if pc==WAIT:
            sp=cpu.reg_read(m.UC_M68K_REG_A7);ret=int.from_bytes(cpu.mem_read(sp,4),'big');assert ret in (0x3d6e,0x4788c)
            phase=1 if ret==0x3d6e else 2;saved=state['saved'];assert saved is not None
            if phase==1:assert saved==cpu.mem_read(sp+4,1)[0]
            result['sound']=pair_initial(0x3d58,tuple(result[key] for key in KEYS))
            result['sound'].update(next_pc=WAIT,phase=phase,saved=saved,byte=dict(waiting=True,command=result['d0']&255,tail=cpu.reg_read(m.UC_M68K_REG_A0)-BASE-0x4cf4,next=result['d1']&65535))
        expected=bytes(cpu.mem_read(BASE,65536));inp.write_bytes(ram)
        actual=subprocess.run(arguments(pending),capture_output=True,text=True);assert not actual.returncode,(label,actual.stderr)
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes();data=portfile.read_bytes();expected_ports=b''.join(struct.pack('>BII',*event) for event in ports)
        if parsed!=result or actual_ram!=expected or data!=expected_ports:
            diff=[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b]
            raise ValueError(repr((label,pending,diff[:16],result,parsed,len(ports),len(data)//9)))
        assert not reads and result['a6']==pending['a6']
        if pending['phase']==1:
            assert not ({0x1a5a4,0x474e2,0x47540,0xca48,0x1c5b0,0xca7e,0x4e24e,0x9056,0x3d58}&set(paths))
            assert len(ports)==(773 if pc!=WAIT else 0)
        rows.append(dict(profile=label,incoming=pending,result=parsed,native_final_pc=pc,native_calls=paths.copy(),live_record_address=int.from_bytes(expected[pending['a6']-BASE+0x76:pending['a6']-BASE+0x7a],'big'),ram_sha256=hashlib.sha256(expected).hexdigest(),ports_sha256=hashlib.sha256(data).hexdigest(),ports_count=len(ports)))
        return bytearray(actual_ram),parsed,cpu.context_save()
    for (stage,area,address),equal,callbacks in itertools.product(records,(False,True),((0,0),(0x270e,0x270e),(0,0x270e),(0x270e,0))):
        compare(fixture(stage,area,equal,callbacks),label='all59-original-records-music-active-pair')
    for stage,area in itertools.product((0,3,8,16,18,19,255),(0,1,255)):
        compare(fixture(stage,area),label='area-fallback-stage-clamp-object-raw-stage-retained')
    for bits,equal in itertools.product((0,8,16,24),(False,True)):
        compare(fixture(3,2,equal,bits=bits),initial(0x477e4),label='full477e4-scene-prefix-composition')
    compare(fixture(3,255),initial(a6=0x10d608),label='live-stage-field-alias-global-header-d684')
    alternate=next(address for stage,area,address in records if program[address]==0x14)
    for phase,tail,change in itertools.product((1,2),(0,127),(False,True)):
        ram=fixture(0,0,False);put(ram,0x4d76,tail);put(ram,0x4d74,(tail+phase)&127);first=len(rows)
        ram,pending,context=compare(ram,label='native-sound-prefix-suffix-wait')
        assert pending['phase']==1 and pending['sound']['phase']==phase
        ram,pending,context=compare(ram,pending,context,label='native-repeated-wait-no-prefix')
        if change:struct.pack_into('>I',ram,0xb30+0x76,alternate)
        releases=[]
        for iteration in range(4):
            release=(pending['sound']['byte']['next']+16)&127;put(ram,0x4d74,release);releases.append(release)
            ram,pending,context=compare(ram,pending,context,label='actual-cli-resume-live-record-pointer')
            if pending['phase']==2:break
        assert pending['phase']==2
        if change:assert rows[-1]['live_record_address']==alternate and pending['next_pc']==TARGETS[5]
        sequences.append(dict(calls=len(rows)-first,actual_cli_ram_registers_pending_carried=True,native_context_stack_preserved=True,host_inputs='soundhead releases and optional LIVEobject+76 record replacement',record_replaced=change,replacement_address=alternate if change else None,head_releases=releases))
    sentinel=b'old-stage-entry-output\0\xff'
    def reject(ram,pending=None,label='invalid',cat=catalog,table=tables,alter=None):
        inp.write_bytes(ram);out.write_bytes(sentinel);portfile.write_bytes(sentinel);args=arguments(pending or initial(),cat,table)
        if alter:args=alter(args)
        actual=subprocess.run(args,capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel and portfile.read_bytes()==sentinel,(label,actual.stderr)
        negatives.append(dict(failure=label,outputs_preserved=True,native_executed=False))
    for group in groups:
        if group['records']:continue
        reject(fixture(group['index']),label='empty-group-bounded-api-rejection')
        ram=fixture(group['index']);cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A6,0x100b30);cpu.reg_write(m.UC_M68K_REG_A7,STACK)
        state.update(loop_budget=20,loop_count=0,waits=0);ports.clear();cpu.emu_start(0x477ee,0xffffff,count=10000)
        assert state['loop_count']==20 and cpu.mem_read(BASE+0xbad,1)==bytes(1)
        loopobservations.append(dict(stage=group['index'],observed477fa_entries=20,final_pc=cpu.reg_read(m.UC_M68K_REG_PC),area_fell_back_to_zero=True,scope='bounded repeated native fallback; no normal completion claimed'))
        state['loop_budget']=None
    for size in (0,65535,65537):reject(bytes(size),label='invalid-ram-size')
    for phase in (1,2,255):
        pending=initial();pending['phase']=phase;reject(fixture(),pending,label='invalid-outer-phase-state')
    for bad in (0,0x100001,0x10ff3e,0xffffffff):reject(fixture(),initial(a6=bad),label='invalid-object')
    actual_wait=next(row['result'] for row in rows if row['result']['phase']==1)
    for key,value in (('phase',0),('saved',256)):
        pending=json.loads(json.dumps(actual_wait));pending['sound'][key]=value;reject(fixture(),pending,label='invalid-inner-pair-state')
    pending=json.loads(json.dumps(actual_wait));pending['sound']['byte']['next']=55;reject(fixture(),pending,label='invalid-captured-byte-state')
    ram=fixture();struct.pack_into('>I',ram,0xb30+0x76,0xdeadbeef);pending=json.loads(json.dumps(actual_wait));put(ram,0x4d74,99)
    reject(ram,pending,label='late-live-record-pointer-error-after-producer')
    badtable=folder/'wrong-window.ms5d';data=bytearray(tables.read_bytes());struct.pack_into('<II',data,12,0x1af10,0x1af10);badtable.write_bytes(data)
    reject(fixture(),initial(0x477e4),table=badtable,label='invalid-initializer-table-window')
    altered=folder/'altered-catalog';altered.mkdir(exist_ok=True)
    for file in catalog.glob('*.ms5d'):shutil.copyfile(file,altered/file.name)
    group0=altered/'stage_group_00.ms5d';packed=bytearray(group0.read_bytes());firstaddr=records[0][2];sourceaddr=groups[0]['source_cpu_address'];at=32+firstaddr-sourceaddr
    packed[at]=3;struct.pack_into('<I',packed,24,zlib.crc32(packed[32:]));group0.write_bytes(packed)
    reject(fixture(),cat=altered,label='unsupported-selector-after-screen-output-rollback')
    for at,bad in itertools.product(range(1,12),('-1','4294967296','0x','1x','')):
        def alter(args,at=at,bad=bad):args=args.copy();args[at]=bad;return args
        reject(fixture(),label='invalid-uint32-parser',alter=alter)
    for kind in ('same','hardlink','symlink'):
        ram=fixture();inp.write_bytes(ram);alias=inp if kind=='same' else folder/('alias-'+kind+'.bin')
        if kind!='same':
            alias.unlink(missing_ok=True)
            if kind=='hardlink':alias.hardlink_to(inp)
            else:alias.symlink_to(inp)
        portfile.write_bytes(sentinel);actual=subprocess.run(arguments(initial(),target=alias),capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==ram and portfile.read_bytes()==sentinel
        negatives.append(dict(failure='input-output-'+kind+'-alias',outputs_preserved=True,native_executed=False))
    for selector,target in ((8,TARGETS[2]),(16,TARGETS[4])):
        cpu.reg_write(REGS[0],selector);ports.clear();cpu.emu_start(0x478a8,0xffffff,count=10)
        assert cpu.reg_read(m.UC_M68K_REG_PC)==target and not ports
        dispatchobservations.append(dict(selector=selector,target=target,synthetic_register_fixture=True,canonical_catalog_reached=False))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    assert hashlib.sha256(executable.read_bytes()).hexdigest()==binary_sha
    canonicaltargets={TARGETS[program[address]//4] for stage,area,address in records}
    assert canonicaltargets=={row['result']['next_pc'] for row in rows if row['result']['phase']==2}
    report.write_text(json.dumps(dict(source=source,cpp_executable_sha256=binary_sha,cpp_binary_unchanged_during_verification=True,table_sha256=table_sha,program_code_modified=False,emulator='Unicorn '+unicorn.__version__,entries_cpu_and_rom_offsets=[0x477e4,0x477ee],canonical_record_count=59,canonical_targets=sorted(canonicaltargets),cases=len(rows),negative_cases=len(negatives),ports=sum(row['ports_count'] for row in rows),mmio_reads=0,full_ram_d0_d1_d3_a6_sound_pending_ordered_ports_equal=True,carry_sequences=sequences,results=rows,negative_results=negatives,empty_group_native_observations=loopobservations,synthetic_dispatch_observations=dispatchobservations,scope='Actual477e4/477ee to soundwait3aea or canonical indexed dispatch targets beforebody. All59 originalcatalogrecords use exactMS5D sources; no ROM patches/callback/BIOS stubs. Sound pair state independently captured from native stack and completion boundary4788c. ActualCLI RAM/fullregs/pending carries with nativecontext; host releaseshead and optionally changes LIVErecordpointer whilewaiting, no prefix requery/reinit onresume. Sevenemptygroups onlybounded nativefallbackobservations plusAPIerror, not normal completion. Additionalselectors8/10hex testonly indexedBRA map with explicitregisterfixture, not canonicalcatalog paths. Scene debug mapping observedPVC2000/1000 only. Otherregisters/CCR/stack/scheduler/timing excluded.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negatives=len(negatives),ports=sum(row['ports_count'] for row in rows),sequences=len(sequences),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__':main()
