"""Immutable native debug and477e4 scene-prefix differential boundaries."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE,m68k_const as m
from disassemble_program import load_verified_program
from verify_stage_catalog import SOURCE_SHA256,checked_resource
from verify_object_reset import make_cpu
from verify_palette_state import call
BASE,RETURN,STACK=0x100000,0xff000,0x1feffc
REGS=(m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D3)
KEYS=('d0','d1','d3')
NODES=(0x9156,0xb1d6)

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
    resource=root/'extracted/runtime/scene_debug.ms5d';resource_hash=checked_resource(resource,program,0x1af12,0x1b112)
    folder=root/'artifacts/scene_initialization';folder.mkdir(parents=True,exist_ok=True)
    inp,out,portfile,report=[folder/name for name in ('input.bin','cpp.bin','ports.bin','verification.json')];report.unlink(missing_ok=True)
    executable=root/'build/step_scene_initialization';binary_sha=hashlib.sha256(executable.read_bytes()).hexdigest()
    cpu=make_cpu(program);cpu.mem_map(0x200000,0x300000);cpu.mem_write(0x200000,program[0x200000:0x300000])
    rows,negatives,sequences,ports,reads,paths,rendernodes=[],[],[],[],[],[],[];table_indices=set();flag_indices=set();lookup_keys=set();state={'bank':0x200000}
    def code(cpu,address,size,user):
        if address in (RETURN,0x477ee):cpu.emu_stop()
        elif address in (0x1a5a4,0x1afda,0xcaf0,0x17292,0x1a7a8):paths.append(address)
        elif address==0x1b0e0:rendernodes.append(cpu.reg_read(m.UC_M68K_REG_A0))
        elif address==0x1b110:
            index=(cpu.reg_read(m.UC_M68K_REG_D6)&65535)//2
            table_indices.add(index);lookup_keys.add((index,(cpu.reg_read(m.UC_M68K_REG_D7)>>14)&3))
        elif address==0x1b122:flag_indices.add(cpu.reg_read(m.UC_M68K_REG_D7)&65535)
    def write(cpu,access,address,size,value,user):
        value&=(1<<(size*8))-1
        if address in (0x2ffff0,0x2ffff2,0x300001,0x3c0000,0x3c0004):
            ports.append((size,address,value))
            if address==0x2ffff2:
                assert size==2 and value in (0x1000,0x2000)
                offset=0x200000 if value==0x1000 else 0x300000
                cpu.mem_write(0x200000,program[offset:offset+0xffff0]);state['bank']=offset
        else:assert BASE<=address and address+size<=BASE+65536 or 0x1f8000<=address and address+size<=0x1ff000,(hex(address),size,value)
    def read(cpu,access,address,size,value,user):
        if 0x2ffff0<=address<0x500000 and not 0x200000<=address<0x2ffff0:reads.append((size,address))
    cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_MEM_READ,read)
    def debugfixture(bits=24,oldflag=0,history='equal',tile=0,upper=0):
        ram=bytearray(hashlib.shake_256(b'scene-debug-fixture').digest(65536));ram[0xf000]=(ram[0xf000]&~24)|bits;ram[0xd44e]=oldflag
        for index,node in enumerate(NODES):
            value=upper|((tile+index)&255)
            ram[node+0x80:node+0x2080]=struct.pack('>H',value)*4096
            x,y=0x00180000,0xfff80000;oldx,oldy=x,y
            if history=='x-borrow' and index==0:oldx=(x-1)&0xffffffff
            elif history=='x-positive-only' and index==0:oldx=(x+1)&0xffffffff
            elif history=='y-difference' and index==0:oldy=(y+1)&0xffffffff
            elif history=='second-only' and index==1:oldy=(y+1)&0xffffffff
            struct.pack_into('>4I',ram,node+0x14,x,y,oldx,oldy)
        return ram
    def command(values,debug,path=resource):
        return [str(root/'build/step_scene_initialization')]+(['--debug'] if debug else [])+[str(value) for value in values]+[str(inp),str(out),str(portfile),str(path)]
    def compare(ram,values,label,debug=True):
        cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.reg_write(m.UC_M68K_REG_A5,0x108000)
        cpu.reg_write(m.UC_M68K_REG_A6,0x100b30);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        cpu.reg_write(m.UC_M68K_REG_A0,0xdeadbeef)
        for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
        ports.clear();reads.clear();paths.clear();rendernodes.clear();table_indices.clear();flag_indices.clear();lookup_keys.clear()
        cpu.emu_start(0x1afda if debug else 0x477e4,0xffffff,count=300000)
        pc=cpu.reg_read(m.UC_M68K_REG_PC);assert pc==(RETURN if debug else 0x477ee)
        expected=bytes(cpu.mem_read(BASE,65536));result=dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)));result['writes']=len(ports)
        if not debug:result['next_pc']=0x477ee
        inp.write_bytes(ram);actual=subprocess.run(command(values,debug),capture_output=True,text=True)
        assert not actual.returncode,(label,actual.stderr)
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes();data=portfile.read_bytes()
        expected_ports=b''.join(struct.pack('>BII',*event) for event in ports)
        if parsed!=result or actual_ram!=expected or data!=expected_ports:
            diff=[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b]
            raise ValueError(repr((label,debug,diff[:16],result,parsed,len(ports),len(data)//9)))
        assert not reads
        assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
        assert bytes(cpu.mem_read(0x200000,0xffff0))==program[state['bank']:state['bank']+0xffff0]
        first=rendernodes.count(BASE+NODES[0]);second=rendernodes.count(BASE+NODES[1])
        rows.append(dict(profile=label,debug=debug,incoming_d0_d1_d3=values,result=parsed,native_final_pc=pc,native_calls=paths.copy(),first_node_render_calls=first,second_node_render_calls=second,native_table_indices=sorted(table_indices),native_upper_flag_indices=sorted(flag_indices),native_lookup_keys=sorted(lookup_keys),mmio_reads=0,ram_sha256=hashlib.sha256(expected).hexdigest(),ports_sha256=hashlib.sha256(data).hexdigest(),port_examples=ports[:4]+ports[-4:] if ports else []))
        return bytearray(actual_ram),tuple(parsed[key] for key in KEYS)
    highs=((0,0,0),(0xabcd1234,0xfedcba98,0x87654321),(0xffffffff,0xffffffff,0xffffffff))
    for bits,oldflag,history,values in itertools.product((0,8,16,24),(0,1,255),('equal','x-borrow','x-positive-only','y-difference','second-only'),highs):
        first=len(rows);compare(debugfixture(bits,oldflag,history),values,'flags-history-first-vs-second-debug-gate')
        if bits and oldflag and history in ('equal','second-only'):assert rows[first]['result']['writes']==0
    def mixedgrid(ram):
        for index,node in enumerate(NODES):
            for col in range(64):
                for row in range(64):
                    key=col*32+row+index*137
                    adjusted=key&255;upper=((key//256)&3)<<14
                    struct.pack_into('>H',ram,node+0x80+col*128+row*2,upper|((adjusted-0x58)&255))
        return ram
    for bits,x,y in itertools.product((8,16,24),(0,8,0x7ff8,0x8000,0xfff8),(0,8,0x7ff8,0x8000,0xfff8)):
        ram=mixedgrid(debugfixture(bits,0))
        for index,node in enumerate(NODES):
            struct.pack_into('>4I',ram,node+0x14,(x<<16)&0xffffffff,(y<<16)&0xffffffff,(x<<16)&0xffffffff,(y<<16)&0xffffffff)
        compare(ram,(0xabcd1234,0xfedcba98,0x87654321),'mixed-all256-indices-four-upper-flags-signed-tile-wrap')
    # Uniform tiles independently prove every table entry controls priority.
    for adjusted in range(256):
        tile=(adjusted-0x58)&255;first=len(rows)
        compare(debugfixture(24,0,tile=tile,upper=(adjusted&3)<<14),(0xabcd1234,0xfedcba98,0x87654321),'uniform-every-table-entry-priority-skip')
        sentinel=struct.unpack_from('>H',program,0x1af12+adjusted*2)[0]==0x320
        assert rows[first]['second_node_render_calls']==(1280 if sentinel else 0)
    patterns=(('zero',bytes(65536)),('seeded',hashlib.shake_256(b'scene-init-seeded-fixture').digest(65536)))
    initialized=[]
    for name,payload in patterns:
        initialized.append((name,payload))
        cpu.mem_write(BASE,payload);call(cpu,0x2790);call(cpu,0x3ef2)
        initialized.append((name+'-actual2790-3ef2',bytes(cpu.mem_read(BASE,65536))))
    for (name,payload),bits,values in itertools.product(initialized,(0,8,16,24),highs):
        ram=bytearray(payload);ram[0xf000]=(ram[0xf000]&~24)|bits
        compare(ram,values,'477e4-prefix-'+name,False)
    for bits in (8,16,24):
        first=len(rows);ram,values=compare(debugfixture(bits,0),(0xabcd1234,0xfedcba98,0x87654321),'actual-cli-debug-toggle-on')
        for node in NODES:ram[node+0x1c:node+0x24]=ram[node+0x14:node+0x1c]
        # Explicit host history update makes stable gate; no draw replay assumed.
        ram,values=compare(ram,values,'actual-cli-debug-stable-after-host-history')
        assert rows[-1]['result']['writes']==0
        ram[0xf000]&=~24
        ram,values=compare(ram,values,'actual-cli-debug-toggle-off-screen-clear')
        assert 0xcaf0 in rows[-1]['native_calls']
        sequences.append(dict(calls=len(rows)-first,actual_cli_ram_registers_carried=True,host_inputs='history snapshots, then f000 bits3/4 clear'))
    for bits in (0,8,16,24):
        ram=bytearray(patterns[1][1]);ram[0xf000]=(ram[0xf000]&~24)|bits;first=len(rows)
        ram,values=compare(ram,(0xabcd1234,0xfedcba98,0x87654321),'actual-cli-initializer-to-debug',False)
        ram,values=compare(ram,values,'actual-cli-debug-after-initializer')
        sequences.append(dict(calls=len(rows)-first,actual_cli_ram_registers_carried=True,host_inputs='none'))
    sentinel=b'old-scene-initialization-output\0\xff'
    def reject(ram,values=('0','0','0'),debug=False,path=resource,label='invalid'):
        inp.write_bytes(ram);out.write_bytes(sentinel);portfile.write_bytes(sentinel)
        actual=subprocess.run(command(values,debug,path),capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel and portfile.read_bytes()==sentinel,(label,actual.stderr)
        negatives.append(dict(failure=label,outputs_preserved=True,native_executed=False))
    for size in (0,65535,65537):reject(bytes(size),label='invalid-ram-size')
    for field,bad in itertools.product(range(3),('-1','4294967296','0x','1x','')):
        values=['0','0','0'];values[field]=bad;reject(debugfixture(),values,label='invalid-uint32-parser')
    wrong=folder/'wrong-window.ms5d';data=bytearray(resource.read_bytes());struct.pack_into('<II',data,12,0x1af10,0x1af10);wrong.write_bytes(data)
    reject(debugfixture(),debug=True,path=wrong,label='debug-invalid-table-window')
    reject(debugfixture(),path=wrong,label='initializer-invalid-table-window-output-preserved')
    malformed=folder/'malformed.ms5d';malformed.write_bytes(resource.read_bytes()[:-1])
    reject(debugfixture(),path=malformed,label='truncated-resource')
    for kind in ('same','hardlink','symlink'):
        ram=debugfixture();inp.write_bytes(ram);alias=inp if kind=='same' else folder/('alias-'+kind+'.bin')
        if kind!='same':
            alias.unlink(missing_ok=True)
            if kind=='hardlink':alias.hardlink_to(inp)
            else:alias.symlink_to(inp)
        portfile.write_bytes(sentinel);args=command((0,0,0),False);args[args.index(str(out))]=str(alias)
        actual=subprocess.run(args,capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==ram and portfile.read_bytes()==sentinel
        negatives.append(dict(failure='input-output-'+kind+'-alias',outputs_preserved=True,native_executed=False))
    assert any(row['second_node_render_calls']==0 and row['first_node_render_calls']==1280 for row in rows)
    assert any(row['second_node_render_calls']==1280 and row['first_node_render_calls']==1280 for row in rows)
    assert set(range(256))=={index for row in rows for index in row['native_table_indices']}
    assert set(itertools.product(range(256),range(4)))=={tuple(key) for row in rows for key in row['native_lookup_keys']}
    assert {0,2,4,6}=={index for row in rows for index in row['native_upper_flag_indices']}
    assert hashlib.sha256(executable.read_bytes()).hexdigest()==binary_sha,'CLI binary changed during verification'
    report.write_text(json.dumps(dict(source=source,cpp_executable_sha256=binary_sha,cpp_binary_unchanged_during_verification=True,resource_sha256=resource_hash,emulator='Unicorn '+unicorn.__version__,program_code_modified=False,entries_cpu_and_rom_offsets=[0x1afda,0x477e4],cases=len(rows),negative_cases=len(negatives),ports=sum(row['result']['writes'] for row in rows),mmio_reads=0,full_ram_d0_d1_d3_ordered_ports_equal=True,carry_sequences=sequences,results=rows,negative_results=negatives,mapping_scope='PVC observedwords2000/1000 map source3MiB/2MiB physical200000..2fffef; MMIOtail excluded. No general PVC mapping equivalence claimed.',scope='Original1afda toRTS and actual477e4 prefix to477ee before first callback-body copy. Every native helper executes withoutpatches/stubs. All256 table indexes use exactoriginal512-byte resource including its intentional code overlap. Priority skips second node except first tile0320; repeated-first-node history check observed. Controlled synthetic buffers/history and hosttoggles are fixtures, not scheduler/timing. Initializer zero/seeded and actual2790/3ef2 RAM fixtures. ActualCLI full RAM/D0D1D3 carries across boundaries. Other registers/CCR/callback suffix not claimed.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negatives=len(negatives),ports=sum(row['result']['writes'] for row in rows),sequences=len(sequences),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__':main()
