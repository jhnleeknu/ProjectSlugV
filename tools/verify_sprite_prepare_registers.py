"""Native sprite preparation D1/D3 and complete ordered PVC/VRAM differential."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import zlib
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_A7, UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D3, UC_M68K_REG_PC, UC_M68K_REG_SR
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_sprite_blocks import resolve_blocks
from verify_stage_catalog import SOURCE_SHA256
from analyze_sprite_sort import word, put

BASE, ENTRY, WAIT, RETURN, STACK = 0x100000, 0x16bba, 0x16bd0, 0xff000, 0x1feffc


def main():
    root=Path(__file__).resolve().parents[1]
    program,source=load_verified_program(root)
    assert source['sha256']==SOURCE_SHA256
    executable=root/'build/prepare_sprite_queue'
    identifiers=(0x2152,0x2952,0x2382a,0x2402a,0x2482a)
    resources=[root/'extracted/runtime'/('composition_%06x.ms5c'%identifier) for identifier in identifiers]
    resource_hashes=[]
    for identifier,path in zip(identifiers,resources):
        bank,offset,data,blocks=resolve_blocks(program,identifier)
        assert bank==0x400000
        packed=struct.pack('<4s7I',b'MS5C',1,1 if len(blocks)==1 else 2,identifier,offset,len(data),zlib.crc32(data),0)+data
        assert path.read_bytes()==packed
        resource_hashes.append({'identifier':identifier,'rom_bank':bank,'rom_offset':offset,'blocks':len(blocks),'sha256':hashlib.sha256(packed).hexdigest()})
    folder=root/'artifacts/sprite_prepare_registers'
    folder.mkdir(parents=True,exist_ok=True)
    inp,out,trace,ports,report=[folder/name for name in ('input.bin','cpp.bin','cpp.writes.bin','cpp.ports.bin','verification.json')]
    report.unlink(missing_ok=True)
    cpu=make_cpu(program)
    cpu.mem_map(0x200000,0x200000)
    cpu.mem_write(0x200000,program[0x400000:0x500000])
    video,pvc,all_ports,sort_calls,rows,sequences,negatives,scene_rows=[],[],[],[],[],[],[],[]
    state={'phase':'setup','visits':0}
    def write(cpu,access,address,size,value,user):
        if 0x3c0000<=address<0x3c0010:
            assert address==0x3c0000 and size==4
            video.append(value&0xffffffff)
            all_ports.append((size,address,value&0xffffffff))
        elif address in (0x2ffff0,0x2ffff2):
            assert size==2
            pvc.append((size,address,value&65535))
            all_ports.append((size,address,value&65535))
        elif not (BASE<=address and address+size<=BASE+65536) and not (0x1f8000<=address and address+size<=0x1ff000):
            raise ValueError('Unexpected native write: '+repr((address,size,value)))
    def code(cpu,address,size,user):
        if address in (0xce02,0x166bc): sort_calls.append(address)
        if address==WAIT:
            state['visits']+=1
            if state['phase']=='begin' or state['phase']=='wait' and state['visits']==2:
                cpu.emu_stop()
            elif state['phase']=='release' and state['visits']>1:
                raise ValueError('Released native consumer wait did not advance')
        elif address==RETURN: cpu.emu_stop()
    cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    cpu.hook_add(UC_HOOK_CODE,code)
    def fixture(forward,count,deferred,start,cache,disabled,flip=0,ready=False,record_identifiers=(0x2152,0x2952)):
        ram=bytearray(65536)
        ram[0x8d3c],ram[0x8d3d]=0x21|(128 if forward else 0),0x35
        put(ram,0x10,0xbeef)
        put(ram,0x8d34,start if ready else (start+2)&510)
        put(ram,0x8d36,start)
        put(ram,0x8d3a,(start+count*2)&510)
        put(ram,0x9150,0x1234)
        for index,(pool,lower,upper) in enumerate(((0x8d3e,0,190),(0x8d46,190,380))):
            ram[pool:pool+8]=struct.pack('>4H',lower,upper,lower+cache,lower+cache)
            if disabled&(1<<index): ram[pool:pool+8]=b'\xff'*8
        normal=delayed=0
        for index in range(count):
            offset=12*(index+1)
            if deferred and index%2==0:
                put(ram,0x8f4e+delayed*2,offset);delayed+=1
            else:
                put(ram,0x8b34+((start+normal*2)&510),offset);normal+=1
            identifier=record_identifiers[index%len(record_identifiers)]
            style=0xffff1500|(4 if index%2 else 0)|((flip+index)%4)
            key=(count-index)*17
            at=0x7f34+offset
            ram[at:at+12]=struct.pack('>III',(key<<16)|(160<<6),style,(384<<23)|identifier)
        put(ram,0x8d38,(start+normal*2)&510)
        put(ram,0x914e,delayed*2)
        return ram
    def compare(ram,phase,cursor=None,context=None,profile='matrix',selected_resources=None,register_inputs=None):
        register_inputs=register_inputs if register_inputs is not None else ((0xabcdef01 ^ len(rows)*0x1234567)&0xffffffff,(0x9876fedc ^ len(rows)*0x7341123)&0xffffffff)
        cpu.mem_write(BASE,bytes(ram))
        if context is None:
            cpu.reg_write(UC_M68K_REG_SR,0x2000)
            cpu.reg_write(UC_M68K_REG_A5,0xdeadbeef)
            cpu.reg_write(UC_M68K_REG_A7,STACK)
            cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        else: cpu.context_restore(context)
        for reg,value in zip((UC_M68K_REG_D1,UC_M68K_REG_D3),register_inputs): cpu.reg_write(reg,value)
        state.update(phase=phase,visits=0)
        video.clear();pvc.clear();all_ports.clear();sort_calls.clear()
        cpu.emu_start(ENTRY if phase in ('begin','sync') else WAIT,RETURN,count=2000000)
        pc=cpu.reg_read(UC_M68K_REG_PC)
        expected=bytes(cpu.mem_read(BASE,65536))
        if phase=='begin':
            assert pc==WAIT and sort_calls==[0xce02,0x166bc] and not video and not pvc
            expected_cursor=cpu.reg_read(UC_M68K_REG_D0)&65535
            assert expected_cursor==word(expected,0x8d36)
        elif phase=='wait':
            assert pc==WAIT and state['visits']==2 and not sort_calls and not video and not pvc and expected==ram
            expected_cursor=cursor
            assert cpu.reg_read(UC_M68K_REG_D0)&65535==cursor
        else:
            assert pc==RETURN and (sort_calls==[0xce02,0x166bc] if phase=='sync' else not sort_calls)
            expected_cursor=0 # API clears completed pending; CPU D0 is not exposed.
        expected_result={'waiting':phase!='release','cursor':expected_cursor,'d1':cpu.reg_read(UC_M68K_REG_D1)&0xffffffff,'d3':cpu.reg_read(UC_M68K_REG_D3)&0xffffffff,'ports':len(all_ports)}
        if phase=='sync':
            expected_result.pop('waiting');expected_result.pop('cursor')
        expected_ports=b''.join(struct.pack('>BII',*event) for event in all_ports)
        expected_video=b''.join(struct.pack('>I',value) for value in video)
        inp.write_bytes(ram)
        command=[str(executable)] if phase=='sync' else [str(executable),'--begin'] if phase=='begin' else [str(executable),'--resume',str(cursor)]
        command += ['--registers',str(register_inputs[0]),str(register_inputs[1]),'--ports',str(ports),str(inp),str(out),str(trace)]
        command += [str(path) for path in (resources if selected_resources is None and phase in ('release','sync') else [] if selected_resources is None else selected_resources)]
        actual=subprocess.run(command,capture_output=True,text=True)
        assert not actual.returncode,(profile,phase,actual.stderr)
        actual_ram,actual_video,actual_ports=out.read_bytes(),trace.read_bytes(),ports.read_bytes()
        parsed=json.loads(actual.stdout)
        if actual_ram!=expected or actual_video!=expected_video or actual_ports!=expected_ports or parsed!=expected_result:
            differences=[(hex(at),expected[at],actual_ram[at]) for at in range(min(len(actual_ram),65536)) if expected[at]!=actual_ram[at]]
            raise ValueError(repr((len(rows),profile,phase,differences[:16],len(video),len(actual_video)//4,expected_result,parsed)))
        rows.append({'profile':profile,'phase':phase,'direction':bool(ram[0x8d3c]&128),'initial_read_cursor':word(ram,0x8d34),'initial_prepared_cursor':word(ram,0x8d36),'native_sort_entries':sort_calls.copy(),'result':parsed,'video_writes':len(video),'ordered_ports':len(all_ports),'incoming_registers':list(register_inputs),'ports_sha256':hashlib.sha256(expected_ports).hexdigest(),'native_pvc_writes':len(pvc),'native_pvc_examples':pvc[:8],'native_pvc_sha256':hashlib.sha256(b''.join(struct.pack('>BII',*value) for value in pvc)).hexdigest(),'input_sha256':hashlib.sha256(ram).hexdigest(),'ram_sha256':hashlib.sha256(expected).hexdigest(),'video_sha256':hashlib.sha256(expected_video).hexdigest()})
        return bytearray(actual_ram),parsed.get('cursor',0),cpu.context_save(),(parsed['d1'],parsed['d3'])
    def sequence(ram,profile,mutation=None,register_mutation=None):
        begin=len(rows)
        ram,cursor,context,registers=compare(ram,'begin',profile=profile)
        if word(ram,0x8d34)!=cursor:
            ram,cursor,context,registers=compare(ram,'wait',cursor,context,profile,register_inputs=registers)
            if mutation is not None: mutation(ram)
            if register_mutation is not None: registers=register_mutation
            ram,cursor,context,registers=compare(ram,'wait',cursor,context,profile,register_inputs=registers)
        put(ram,0x8d34,cursor) # Explicit host consumer release of the captured cursor.
        ram,_,context,registers=compare(ram,'release',cursor,context,profile,register_inputs=registers)
        sequences.append({'profile':profile,'calls':len(rows)-begin,'cpp_ram_pending_cursor_and_full_d1_d3_carried':True,'same_native_wait_context_resumed':True,'host_releases_only_read_cursor':True,'controlled_wait_mutation':mutation is not None,'controlled_wait_register_mutation':register_mutation is not None})
        return ram,registers,context
    for forward,count,deferred,start,cache,disabled in itertools.product((False,True),(0,1,4,20),(False,True),(0,510),(0,95,190),(0,2,3)):
        sequence(fixture(forward,count,deferred,start,cache,disabled),'direction-ring-deferred-count-pools-cache')
    for forward,flip,disabled in itertools.product((False,True),range(4),(0,2,3)):
        sequence(fixture(forward,4,True,510,95,disabled,flip),'all-flip-styles')
    for forward,count,start in itertools.product((False,True),(0,4),(0,510)):
        sequence(fixture(forward,count,False,start,95,0,ready=True),'begin-stops-even-already-synchronized')
    for forward,mutation_name in itertools.product((False,True),('direction','cache','key','direction-cache-key')):
        def mutate(ram):
            if 'direction' in mutation_name: ram[0x8d3c]^=128
            if 'cache' in mutation_name:
                for pool,lower in ((0x8d3e,0),(0x8d46,190)):
                    put(ram,pool+4,lower+95);put(ram,pool+6,lower+95)
            if 'key' in mutation_name:
                for index in range(4): put(ram,0x7f34+12*(index+1),(index+1)*17)
        sequence(fixture(forward,4,False,510,190 if forward else 0,0),'controlled-live-'+mutation_name,mutate)
    for forward,disabled in itertools.product((False,True),(0,3)):
        sequence(fixture(forward,4,False,510,95,disabled),'controlled-nonzero-resume-register-highwords',register_mutation=(0xabcd1234,0x9876fedc))
    for forward,count,disabled in itertools.product((False,True),(0,4),(0,3)):
        compare(fixture(forward,count,True,510,95,disabled,ready=True),'sync',profile='synchronous-full-native-entry')
    for forward,x,flip in itertools.product((False,True),(0,1,159,320,383,511,1023),range(4)):
        ram=fixture(forward,4,True,510,95,0,flip)
        for index in range(4): put(ram,0x7f34+12*(index+1)+2,(x<<6)&65535)
        sequence(ram,'clipping-singleblock-all-flips-x-'+str(x))
    for forward,identifier,x,flip in itertools.product((False,True),(0x2382a,0x2402a,0x2482a),(0,160,511),range(4)):
        ram=fixture(forward,4,True,510,95,0,flip,record_identifiers=(identifier,))
        for index in range(4): put(ram,0x7f34+12*(index+1)+2,(x<<6)&65535)
        sequence(ram,'actual-multiblock-'+hex(identifier)+'-x-'+str(x))
    for forward,cache in itertools.product((False,True),(1,2,3)):
        sequence(fixture(forward,20,True,510,cache,0),'small-cached-limit-exhaustion')
    for forward,disabled in itertools.product((False,True),(0,3)):
        ram,registers,context=sequence(fixture(forward,4,True,510,95,disabled),'prepare-to-scene-coordinate-preparation')
        scene_objects=(0x109156,0x10b1d6,0x10d256,0x10d2d6)
        for index,obj in enumerate(scene_objects):
            at=obj-BASE
            put(ram,at+0x14,0xffff-index);put(ram,at+0x18,index)
            ram[at+0x25]=index;ram[at+0x7a]=index|1
            put(ram,at+0x7c,0);put(ram,at+0x7e,0)
        cpu.mem_write(BASE,bytes(ram));cpu.context_restore(context)
        d0=0x1234abcd
        for reg,value in ((UC_M68K_REG_A5,0x108000),(UC_M68K_REG_A7,STACK),(UC_M68K_REG_D0,d0),(UC_M68K_REG_D1,registers[0]),(UC_M68K_REG_D3,registers[1])): cpu.reg_write(reg,value)
        cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        all_ports.clear();video.clear();pvc.clear();sort_calls.clear()
        cpu.emu_start(0x1ae56,RETURN,count=10000)
        assert cpu.reg_read(UC_M68K_REG_PC)==RETURN
        expected_ram=bytes(cpu.mem_read(BASE,65536))
        expected_ports=b''.join(struct.pack('>BII',*event) for event in all_ports)
        expected_result={key:cpu.reg_read(reg)&0xffffffff for key,reg in zip(('d0','d1','d3'),(UC_M68K_REG_D0,UC_M68K_REG_D1,UC_M68K_REG_D3))}
        expected_result['writes']=len(all_ports)
        inp.write_bytes(ram)
        command=[str(root/'build/refresh_column_controls'),'--prepare',str(registers[0]),str(registers[1]),'--scene',str(inp),str(out),str(ports),str(d0)]
        actual=subprocess.run(command,capture_output=True,text=True)
        assert not actual.returncode,actual.stderr
        parsed=json.loads(actual.stdout)
        assert out.read_bytes()==expected_ram and ports.read_bytes()==expected_ports and parsed==expected_result,(expected_result,parsed)
        scene_rows.append({'incoming_cpp_d1_d3':list(registers),'result':parsed,'controlled_scene_object_fields_initialized':True,'ram_sha256':hashlib.sha256(expected_ram).hexdigest(),'ports_sha256':hashlib.sha256(expected_ports).hexdigest(),'ports':len(all_ports)})
    sentinel=b'prior-sprite-prepare-wait-output\0\xff'
    def reject(label,ram,mode='--begin',cursor='0',selected_resources=resources,command=None):
        inp.write_bytes(ram);out.write_bytes(sentinel);trace.write_bytes(sentinel);ports.write_bytes(sentinel)
        command=command or [str(executable),mode]+([cursor] if mode=='--resume' else [])+['--registers','2882400001','2557935324','--ports',str(ports),str(inp),str(out),str(trace)]+[str(path) for path in selected_resources]
        actual=subprocess.run(command,capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel and trace.read_bytes()==sentinel and ports.read_bytes()==sentinel,(label,actual.stdout,actual.stderr)
        negatives.append({'failure':label,'outputs_preserved':True,'original_executed':False})
    for invalid in ('-1','65536','0x10000','0x','1x','','1','511','512'):
        reject('invalid-pending-cursor',fixture(True,4,False,0,190,0),'--resume',invalid)
    for mode,size in itertools.product(('--begin','--resume'),(0,65535,65537)):
        reject('invalid-ram-size',bytes(size),mode)
    for at,value in ((0x8d34,1),(0x8d36,512),(0x8d38,3),(0x8d3a,1)):
        ram=fixture(True,4,False,0,190,0);put(ram,at,value)
        reject('invalid-begin-ring-index',ram)
    ram=fixture(True,4,False,0,190,0)
    ram,cursor,context,registers=compare(ram,'begin',profile='late-failure-prepared-fixture')
    put(ram,0x8d34,cursor)
    reject('missing-second-resource-after-first-emission',ram,'--resume',str(cursor),resources[1:])
    bad=bytearray(ram);put(bad,0x7f34+36+6,0x1508)
    reject('unsupported-late-record-style',bad,'--resume',str(cursor))
    for flag in ('d1','d3'):
        for invalid in ('-1','4294967296','0x100000000','0x','1x',''):
            inputs=[invalid,'2557935324'] if flag=='d1' else ['2882400001',invalid]
            command=[str(executable),'--registers']+inputs+['--ports',str(ports),'--begin',str(inp),str(out),str(trace)]
            reject('invalid-'+flag+'-uint32-parser',fixture(True,4,False,0,190,0),command=command)
    for alias_kind in ('same','hardlink','symlink'):
        good=fixture(True,4,False,0,190,0);inp.write_bytes(good);out.write_bytes(sentinel);trace.write_bytes(sentinel)
        alias=inp if alias_kind=='same' else folder/('ports-'+alias_kind+'.bin')
        if alias_kind!='same':
            alias.unlink(missing_ok=True)
            if alias_kind=='hardlink': alias.hardlink_to(inp)
            else: alias.symlink_to(inp)
        command=[str(executable),'--ports',str(alias),'--registers','2882400001','2557935324','--begin',str(inp),str(out),str(trace)]
        actual=subprocess.run(command,capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==good and out.read_bytes()==sentinel and trace.read_bytes()==sentinel
        negatives.append({'failure':'input-ports-'+alias_kind+'-alias','outputs_preserved':True,'original_executed':False})
    for mode,alias_kind in itertools.product(('--begin','--resume'),('same','hardlink','symlink')):
        good=fixture(True,4,False,0,190,0);inp.write_bytes(good);trace.write_bytes(sentinel);ports.write_bytes(sentinel)
        alias=inp if alias_kind=='same' else folder/(mode[2:]+'-'+alias_kind+'.bin')
        if alias_kind!='same':
            alias.unlink(missing_ok=True)
            if alias_kind=='hardlink': alias.hardlink_to(inp)
            else: alias.symlink_to(inp)
        command=[str(executable),mode]+(['0'] if mode=='--resume' else [])+['--registers','2882400001','2557935324','--ports',str(ports),str(inp),str(alias),str(trace)]+[str(path) for path in resources]
        actual=subprocess.run(command,capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==good and trace.read_bytes()==sentinel and ports.read_bytes()==sentinel
        negatives.append({'failure':'input-output-'+mode+'-'+alias_kind+'-alias','outputs_preserved':True,'original_executed':False})
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    assert bytes(cpu.mem_read(0x200000,0xffff0))==program[0x400000:0x4ffff0]
    assert any(row['phase']=='begin' and row['ram_sha256']!=row['input_sha256'] for row in rows)
    assert all(not row['native_sort_entries'] for row in rows if row['phase'] not in ('begin','sync'))
    report.write_text(json.dumps({'source':source,'emulator':'Unicorn '+unicorn.__version__,'program_code_modified':False,'entry_cpu_address':ENTRY,'wait_cpu_address':WAIT,'resource_hashes':resource_hashes,'cases':len(rows),'phase_counts':{phase:sum(row['phase']==phase for row in rows) for phase in ('begin','wait','release','sync')},'video_writes':sum(row['video_writes'] for row in rows),'ordered_hardware_writes':sum(row['ordered_ports'] for row in rows),'whole_ram_full_d1_d3_and_all_ordered_ports_equal':True,'native_captured_d0_word_pending_cursor_equal':True,'native_sort_only_at_begin_or_synchronous_entry_asserted':True,'actual_cpp_ram_pending_cursor_full_d1_d3_carry':True,'negative_cases':len(negatives),'negative_results':negatives,'output_carry_sequences':sequences,'scene_prepare_integrations':scene_rows,'results':rows,'scope':'Immutable native16bba through sort and boundary16bd0, then repeated waits and release using the same native CPU context. Full64KiB RAM, full D1/D3, ordered PVC word and VRAM long writes plus legacy BE16 VRAM pairs are compared. Incoming nonzero register highwords are explicit initial fixtures; subsequent values are actual CLI outputs. Host releases read8d34 to the captured cursor; controlled key/direction/cache and register changes are explicit fixtures, with no pending index mutation. Scene integrations consume actual preparation RAM/D1/D3 outputs and end at1ae56 return. D0 outside those scene boundary fixtures, other CPU registers/flags, natural concurrency, IRQ scheduling, rasterization and timing are excluded.'},indent=2)+'\n')
    print(json.dumps({'cases':len(rows),'sequences':len(sequences),'scene_prepare_integrations':len(scene_rows),'negative_cases':len(negatives),'ordered_ports':sum(row['ordered_ports'] for row in rows),'video_writes':sum(row['video_writes'] for row in rows),'report_sha256':hashlib.sha256(report.read_bytes()).hexdigest()}))

if __name__=='__main__': main()
