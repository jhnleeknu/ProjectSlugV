"""Compare immutableca9e/caf0 full RAM/registers and ordered hardware writes."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256
BASE,RETURN,STACK=0x100000,0xff000,0x1feffc


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert source['sha256']==SOURCE_SHA256
    folder=root/'artifacts/game_screen_reset';folder.mkdir(parents=True,exist_ok=True)
    inp,out,ports_path,report=[folder/name for name in ('input.bin','cpp.bin','cpp.ports.bin','verification.json')]
    report.unlink(missing_ok=True);executable=root/'build/reset_game_screen'
    cpu=make_cpu(program);cpu.mem_map(0x300000,0x100000)
    writes,paths,rows,negatives=[],[],[],[]
    def stop(cpu,address,size,user):
        if address==RETURN:cpu.emu_stop()
        elif address in (0xca9e,0xcaf0,0x35a2):paths.append(address)
    def write(cpu,access,address,size,value,user):
        if address in (0x300001,0x3c0000,0x3c0004):writes.append((size,address,value&((1<<(size*8))-1)))
        elif not (BASE<=address and address+size<=BASE+65536 or 0x1fe000<=address and address+size<=0x1ff000):
            raise ValueError('Unexpected native write '+hex(address))
    cpu.hook_add(UC_HOOK_CODE,stop);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    triples=((0,0,0),(0xffffffff,0xffffffff,0xffffffff),(0x12345678,0xabcd1234,0x87654321),
             (0xffff0000,0x0000ffff,0x80008000),(0x80000001,0x7fffffff,0x12340000))
    triples+=tuple((0x12345678,0xabcd1234,high|low) for high,low in itertools.product((0,0xabcd0000),(0,1,0x8000,0xffff)))
    patterns={'zero':bytes(65536),'ff':bytes([255])*65536,'incrementing':bytes(range(256))*256,
              'deterministic-random':hashlib.shake_256(b'game-screen-reset-fixture').digest(65536)}
    def command(entry,values,target=out,port_target=ports_path):
        return [str(executable),str(entry),*(str(value) for value in values),str(inp),str(target),str(port_target)]
    for entry,(name,ram),values in itertools.product((0xca9e,0xcaf0),patterns.items(),triples):
        cpu.mem_write(BASE,ram);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
        for reg,value in ((m.UC_M68K_REG_SR,0x2000),(m.UC_M68K_REG_A5,0x108000),(m.UC_M68K_REG_A7,STACK)):
            cpu.reg_write(reg,value)
        for reg,value in zip((m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D3),values):cpu.reg_write(reg,value)
        writes.clear();paths.clear();cpu.emu_start(entry,0xffffff,count=100000)
        assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN
        expected=bytes(cpu.mem_read(BASE,65536));expected_ports=b''.join(struct.pack('>BII',*event) for event in writes)
        expected_json=dict(zip(('d0','d1','d3'),(cpu.reg_read(reg)&0xffffffff for reg in
            (m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D3))))
        expected_json['writes']=len(writes)
        assert len(writes)==(773 if entry==0xca9e else 2072)
        if entry==0xca9e:
            assert expected==ram and expected_json['d3']==values[2] and paths==[entry]
        else:
            changed=bytearray(ram);changed[0x966]=0;assert expected==changed
            assert paths==[entry,0xca9e]+[0x35a2]*5
            assert [event for event in writes if event[1]==0x300001]==[(1,0x300001,value) for value in (0x21,0x1f,0,0,0xe0)]
            assert [event for event in writes if event[1]==0x3c0004]==[(2,0x3c0004,0)]*5
        inp.write_bytes(ram);out.unlink(missing_ok=True);ports_path.unlink(missing_ok=True)
        actual=subprocess.run(command(entry,values),capture_output=True,text=True)
        assert not actual.returncode,actual.stderr
        parsed=json.loads(actual.stdout)
        if out.read_bytes()!=expected or ports_path.read_bytes()!=expected_ports or parsed!=expected_json:
            raise ValueError(repr((hex(entry),name,values,expected_json,parsed)))
        rows.append(dict(entry_cpu_address=entry,profile=name,input_d0_d1_d3=values,result=parsed,
            native_callee_sequence=paths.copy(),ram_sha256=hashlib.sha256(expected).hexdigest(),
            ports_sha256=hashlib.sha256(expected_ports).hexdigest()))
    sentinel_ram=b'previous-screen-ram';sentinel_ports=b'previous-screen-ports'
    def reject(ram,entry=0xcaf0,values=(1,2,3),label='invalid'):
        inp.write_bytes(ram);out.write_bytes(sentinel_ram);ports_path.write_bytes(sentinel_ports)
        actual=subprocess.run(command(entry,values),capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==ram and out.read_bytes()==sentinel_ram and ports_path.read_bytes()==sentinel_ports
        negatives.append(dict(failure=label,ram_ports_preserved=True))
    for size in (0,65535,65537):reject(bytes(size),label='invalid-size-'+str(size))
    for entry in (0,0x35a2,0xffffffff,-1,4294967296):reject(patterns['ff'],entry,label='invalid-entry-'+str(entry))
    for index,value in itertools.product(range(3),(-1,4294967296)):
        values=[1,2,3];values[index]=value;reject(patterns['ff'],values=values,label='invalid-register-'+str(index)+'-'+str(value))
    for pair,kind in itertools.product(('input-ram','input-ports','output-output'),('same','hardlink','symlink')):
        inp.write_bytes(patterns['ff']);out.write_bytes(sentinel_ram);ports_path.write_bytes(sentinel_ports)
        origin=out if pair=='output-output' else inp
        alias=origin
        if kind!='same':
            alias=folder/('alias-'+kind+'.bin');alias.unlink(missing_ok=True)
            if kind=='hardlink':alias.hardlink_to(origin)
            else:alias.symlink_to(origin)
        target=alias if pair=='input-ram' else out
        port_target=alias if pair!='input-ram' else ports_path
        before={path:path.read_bytes() for path in (inp,out,ports_path,alias)}
        actual=subprocess.run(command(0xcaf0,(1,2,3),target,port_target),capture_output=True,text=True)
        assert actual.returncode and all(path.read_bytes()==data for path,data in before.items())
        negatives.append(dict(failure=pair+'-'+kind+'-alias',ram_ports_preserved=True))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    report.write_text(json.dumps(dict(source=source,emulator='Unicorn '+unicorn.__version__,program_code_modified=False,
        native_cpp_cases=len(rows),negative_cases=len(negatives),whole_ram_full_d0_d1_d3_ports_equal=True,
        ca9e_writes_per_case=773,caf0_writes_per_case=2072,total_native_ports=sum(row['result']['writes'] for row in rows),
        results=rows,negative_results=negatives,
        scope='Direct originalca9e andcaf0 calls, including all five actual35a2 rectangle calls and their '
            'ordered watchdog/VRAM/control writes. Whole64KiB RAM and full D0/D1/D3 compare with current C++ '
            'CLI outputs; original fixed ROM remains unchanged. Other registers, CCR, stack equivalence, '
            'arbitrary35a2 rectangles/native TRAP behavior, rendering pixels, caller scheduling and hardware '
            'timing are excluded. Parser/entry/size/alias rejection paths preserve both CLI outputs.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negatives=len(negatives),ports=sum(row['result']['writes'] for row in rows),
        sha256=hashlib.sha256(report.read_bytes()).hexdigest())))


if __name__=='__main__':main()
