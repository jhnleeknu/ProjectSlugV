"""Immutable native e74..ec4, retaining suspended sound/sprite CPU contexts."""
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
    folder=root/'artifacts/main_prelude';folder.mkdir(parents=True,exist_ok=True)
    inp,out,ports_out,report=[folder/name for name in ('input.bin','cpp.bin','cpp.ports.bin','verification.json')]
    report.unlink(missing_ok=True)
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000)
    current_bank=[0x200000]
    cpu.mem_write(0x200000,program[0x200000:0x300000])
    ports,reads,paths,rows,sequences,negatives,integrations=[],[],[],[],[],[],[]
    state={'mode':'setup','video':0,'blocked':0,'visits':0,'samples':[]}
    def write(cpu,access,address,size,value,user):
        if address in (0x3c0000,0x3c0004,0x2ffff0,0x2ffff2,0x300001):
            ports.append((size,address,value&((1<<(size*8))-1)))
            if address==0x2ffff2:
                assert size==2 and value in (0x1000,0x2000,0x3000)
                current_bank[0]=((value>>12)+1)*0x100000
                cpu.mem_write(0x200000,program[current_bank[0]:current_bank[0]+0xffff0])
        elif not (BASE<=address and address+size<=BASE+65536) and not (0x1f8000<=address and address+size<=0x1ff000):
            raise ValueError('Unexpected native write '+repr((hex(address),size,value)))
    def read(cpu,access,address,size,value,user):
        if address==0x3c0006:
            assert size==2;cpu.mem_write(address,state['video'].to_bytes(2,'big'));reads.append((size,address,state['video']))
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
        elif state['mode']=='setup' and address==RETURN: cpu.emu_stop()
    cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_MEM_READ,read,begin=0x300000,end=0x3c0007);cpu.hook_add(UC_HOOK_CODE,code)
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
    for forward,count,identifier,flip in itertools.product((False,True),(0,1,4),(0x2152,0x2402a),range(4)):
        ram=fixture(count,forward,True,identifier,flip)
        compare(ram,video=(len(rows)*0x137)&65535,profile='complete-sound-empty-sprites-columns-palette')
    for timer,pending,effect,weight in itertools.product((0,1,2,255),(0,128),(False,True),(0,15,31)):
        ram=fixture(1,True)
        ram[0x7dd4],ram[0x7ded]=timer,pending
        for channel in range(3):
            put(ram,0x7dc2+2*channel,0x700+channel*0x800 if effect else 0);put(ram,0x7dc8+2*channel,0xf000);put(ram,0x7dce+2*channel,0x100)
        for slot in (0,255):
            at=0x4d92+16*slot;put(ram,at+10,0x203);put(ram,at+12,0x87a);ram[at+14:at+16]=bytes((weight,128|((slot&1)*2)))
        compare(ram,video=0xffff,profile='composed-timer-pending-effect-direct-blend')
    for command in (0,0x0303,0x0355,0x5503,0x0455):
        for forward in (False,True):
            ram=fixture(4,forward,False,0x2402a)
            put(ram,0x4d82,command);put(ram,0x4d8c,2);put(ram,0x4d74,1)
            first=len(rows);ram,pending,context=compare(ram,profile='sound-then-sprite-waits');appended=False
            while pending['next_pc']!=DONE:
                # Explicit host consumer progress, not a claim about natural IRQ timing.
                if pending['next_pc']==SOUND:
                    ram,pending,context=compare(ram,pending,context,profile='unchanged-sound-wait')
                    put(ram,0x4d74,(pending['sound']['next']+1)&127)
                    if not appended:
                        put(ram,0x4d84,0x0355);put(ram,0x4d8c,4);appended=True
                else:
                    ram,pending,context=compare(ram,pending,context,profile='unchanged-sprite-wait')
                    put(ram,0x8d34,pending['sprite']['cursor'])
                ram,pending,context=compare(ram,pending,context,video=0x8080,profile='host-released-wait')
                assert len(rows)-first<=9
            sequences.append(dict(calls=len(rows)-first,actual_cli_ram_register_pending_carry=True,host_queue_progress_explicit=True,word_command_appended_while_sound_blocked=appended))
    for video,old in itertools.product((0,0x7fff,0x8000,0x807f,0x8080,0xffff),(0,1,127,255)):
        ram=fixture();ram[0x18]=old;compare(ram,video=video,profile='video-delta-byte-wrap')
    runtime=root/'extracted/runtime'
    streams,status,menu,pause,debug,font=[runtime/name for name in ('input_streams.ms5d','input_status.ms5d','control_menu_tree.ms5d','control_pause.ms5d','main_debug.ms5d','menu_fonts.ms5d')]
    for name,path,start,end in (('streams',streams,0xf01fe,0xf1a0e),('status',status,0xb58,0xc58),('menu',menu,0x937e,0x9aa8),('pause',pause,0x9068,0x9086),('debug',debug,0xd56,0xe40),('font',font,0xe80c8,0xe84c8)):
        hashes[name]=checked_resource(path,program,start,end)
    for ready,weight in itertools.product((False,True),(0,15)):
        ram=fixture(4,False,True,0x2402a)
        ram[0xf000]=0;ram[0x4cd4]=0;ram[0x16]=1 if ready else 0;ram[0x17]=1
        struct.pack_into('>II',ram,0xf5c+0x76,0x3dcc,0xdeadbeef)
        at=0x4d92+255*16;put(ram,at+10,0x203);put(ram,at+12,0x87a);ram[at+14:at+16]=bytes((weight,128))
        ram,pending,context=compare(ram,video=0x8080,profile='prelude-before-carried-main')
        assert pending['next_pc']==DONE
        cpu.context_restore(context)
        incoming_a5,incoming_a6,incoming_a7=[cpu.reg_read(reg)&0xffffffff for reg in (mc.UC_M68K_REG_A5,mc.UC_M68K_REG_A6,mc.UC_M68K_REG_A7)]
        assert (incoming_a5,incoming_a6,incoming_a7)==(0x108000,0x100f5c,STACK),tuple(hex(value) for value in (incoming_a5,incoming_a6,incoming_a7))
        cpu.mem_write(BASE,bytes(ram));cpu.reg_write(D1,pending['d1']);cpu.reg_write(D3,pending['d3'])
        ports.clear();reads.clear();paths.clear();samples=[0xff,0xef,0xdf,0x7f,0xbf]
        state.update(mode='input',video=0xffff,visits=0,samples=samples)
        cpu.emu_start(DONE,RETURN,count=500000)
        pc=cpu.reg_read(mc.UC_M68K_REG_PC);assert pc==(0xf3c if ready else 0xef2),hex(pc)
        expected_ram=bytes(cpu.mem_read(BASE,65536));expected_ports=b''.join(struct.pack('>BII',*event) for event in ports)
        input_reads=sum(event[1]!=0x3c0006 for event in reads)
        assert input_reads==(5 if ready else 0) and sum(event[1]==0x3c0006 for event in reads)==int(ready)
        result=dict(next_pc=pc,callback=0x3dcc if ready else 0,callback_context=0xdeadbeef if ready else 0,style=cpu.reg_read(D1)&65535,read_count=input_reads,d1=cpu.reg_read(D1)&0xffffffff,d3=cpu.reg_read(D3)&0xffffffff)
        inp.write_bytes(ram)
        command=[str(root/'build/step_input_control'),'--main',str(DONE),str(debug),'65535','--registers',str(pending['d1']),str(pending['d3']),str(inp),str(streams),str(status),str(menu),str(pause),str(palette),str(out),str(ports_out),str(incoming_a6),str(pending['d1']&65535),str(pending['d3']&65535),str(incoming_a7)]+[str(value) for value in samples]+[str(font),str(runtime/'stages')]
        actual=subprocess.run(command,capture_output=True,text=True)
        assert not actual.returncode,actual.stderr
        parsed=json.loads(actual.stdout)
        assert out.read_bytes()==expected_ram and ports_out.read_bytes()==expected_ports and parsed==result,(result,parsed)
        integrations.append(dict(ready=ready,weight=weight,incoming_cpp_d1_d3=[pending['d1'],pending['d3']],result=parsed,ports=len(ports),reads=reads.copy(),native_a5_a6_a7_preserved_across_preparation=True,actual_cpp_ram_full_d1_d3_carried=True,ram_sha256=hashlib.sha256(expected_ram).hexdigest(),ports_sha256=hashlib.sha256(expected_ports).hexdigest()))
    sentinel=b'previous-main-prelude-output\0\xff'
    def reject(ram,pending,label,video=0,selected_palette=palette,selected_resources=resources,command=None):
        inp.write_bytes(ram);out.write_bytes(sentinel);ports_out.write_bytes(sentinel)
        actual=subprocess.run(command or args(pending,video,selected_palette,selected_resources),capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel and ports_out.read_bytes()==sentinel,(label,actual.stdout,actual.stderr)
        negatives.append(dict(failure=label,outputs_preserved=True,original_executed=False))
    for size in (0,65535,65537): reject(bytes(size),initial_state(),'wrong-ram-size')
    bad=fixture();put(bad,0x4d8c,1);reject(bad,initial_state(),'invalid-sound-after-video-init')
    bad=fixture(4);put(bad,0x7f34+36+6,0x1508);reject(bad,initial_state(),'late-sprite-style')
    bad=fixture(1);at=0x4d92+255*16;put(bad,at+10,0xfffe);put(bad,at+12,0xfffe);bad[at+15]=128
    reject(bad,initial_state(),'late-palette-id-after-render-and-columns')
    for key,invalid in itertools.product(('next_pc','d1','d3'),('-1','4294967296','0x','1x','')):
        values=initial_state();values[key]=invalid;reject(fixture(),values,'invalid-state-'+key)
    for invalid in ('-1','65536','0x10000','1x',''): reject(fixture(),initial_state(),'invalid-video',invalid)
    for pc in (SOUND,SPRITE):
        values=initial_state();values['next_pc']=pc
        reject(fixture(),values,'missing-pending-for-resume-boundary')
    values=initial_state();values['sound'].update(kind=2,phase=1,low=0x55,cursor=0,waiting=True,command=4,tail=0,next=1)
    reject(fixture(),values,'sound-pending-at-fresh-entry')
    values=initial_state();values['next_pc']=SPRITE;values['sprite']=dict(waiting=True,cursor=0);values['sound'].update(kind=2,phase=1,low=0x55,cursor=0,waiting=True,command=4,tail=0,next=1)
    reject(fixture(),values,'simultaneous-inconsistent-pending')
    for alias_kind in ('same','hardlink','symlink'):
        good=fixture();inp.write_bytes(good);ports_out.write_bytes(sentinel)
        alias=inp if alias_kind=='same' else folder/('alias-'+alias_kind+'.bin')
        if alias_kind!='same':
            alias.unlink(missing_ok=True)
            if alias_kind=='hardlink': alias.hardlink_to(inp)
            else: alias.symlink_to(inp)
        command=args(initial_state(),0);command[command.index(str(out))]=str(alias)
        actual=subprocess.run(command,capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==good and ports_out.read_bytes()==sentinel
        negatives.append(dict(failure='input-output-'+alias_kind+'-alias',outputs_preserved=True,original_executed=False))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    assert bytes(cpu.mem_read(0x200000,0xffff0))==program[current_bank[0]:current_bank[0]+0xffff0]
    assert any(row['result']['sound']['phase']==1 for row in rows) and any(row['result']['sound']['phase']==2 for row in rows)
    assert any(row['result']['sprite']['waiting'] for row in rows)
    report.write_text(json.dumps(dict(source=source,emulator='Unicorn '+unicorn.__version__,program_code_modified=False,entry_cpu_address=ENTRY,resource_hashes=hashes,cases=len(rows),boundaries={str(pc):sum(row['result']['next_pc']==pc for row in rows) for pc in (SOUND,SPRITE,DONE)},ports=sum(row['result']['writes'] for row in rows),video_reads=sum(len(row['reads']) for row in rows),negative_cases=len(negatives),negative_results=negatives,carry_sequences=sequences,main_integrations=integrations,results=rows,scope='Native continuous e74..ec4 includes real sound drain, merge/radix, sprite emission, column preparation and palette processing. Suspended sound/sprite native CPU context and external stack are retained; actual CLI RAM/full D1/D3/pending outputs are carried. Host byte-head/word-tail/sprite-read changes are explicit controlled fixtures, not natural concurrency or IRQ timing. All ordered PVC/VRAM/watchdog writes and video read count are compared. Other scratch registers, hardware timing, rasterization, BIOS, callbacks and RTE are excluded.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),ports=sum(row['result']['writes'] for row in rows),negative_cases=len(negatives),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__': main()
