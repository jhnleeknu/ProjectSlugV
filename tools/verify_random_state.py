"""Compare unchanged native random routines and carried CLI RAM/full D0/D1."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE, m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256

BASE, RETURN = 0x100000, 0xff000
ENTRIES = {'seed':0x49a1a,'next':0x49a58,'scale':0x49a84}


def main():
    root=Path(__file__).resolve().parents[1]
    program,source=load_verified_program(root)
    assert source['sha256']==SOURCE_SHA256
    folder=root/'artifacts/random_state';folder.mkdir(parents=True,exist_ok=True)
    inp,out,report=[folder/name for name in ('input.bin','cpp.bin','verification.json')]
    report.unlink(missing_ok=True)
    executable=root/'build/step_random'
    cpu=make_cpu(program)
    rows,negatives=[],[]
    def stop(cpu,address,size,user):cpu.emu_stop()
    def write(cpu,access,address,size,value,user):
        if not (BASE<=address and address+size<=BASE+65536 or 0x1fe000<=address and address+size<=0x1ff000):
            raise ValueError('Unexpected native random write: '+hex(address))
    cpu.hook_add(UC_HOOK_CODE,stop,begin=RETURN,end=RETURN)
    cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    def fixture():return bytearray(hashlib.shake_256(('random-fixture:'+str(len(rows))).encode()).digest(65536))
    def compare(ram,mode,d0,d1,label):
        cpu.mem_write(BASE,bytes(ram))
        for reg,value in ((m.UC_M68K_REG_SR,0x2000),(m.UC_M68K_REG_A5,0x108000),
                (m.UC_M68K_REG_A7,0x1feffc),(m.UC_M68K_REG_D0,d0),(m.UC_M68K_REG_D1,d1)):
            cpu.reg_write(reg,value)
        cpu.mem_write(0x1feffc,RETURN.to_bytes(4,'big'))
        cpu.emu_start(ENTRIES[mode],0xffffff,count=10000)
        assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN
        expected=bytes(cpu.mem_read(BASE,65536))
        registers={'d0':cpu.reg_read(m.UC_M68K_REG_D0)&0xffffffff,'d1':cpu.reg_read(m.UC_M68K_REG_D1)&0xffffffff}
        inp.write_bytes(ram);out.unlink(missing_ok=True)
        result=subprocess.run([str(executable),mode,str(d0),str(d1),str(inp),str(out)],capture_output=True,text=True)
        parsed=json.loads(result.stdout) if not result.returncode else None
        if result.returncode or not out.exists() or out.read_bytes()!=expected or parsed!=registers:
            raise ValueError('Random mismatch: '+repr((len(rows),mode,label,hex(d0),hex(d1),registers,parsed,result.stderr)))
        if mode=='next':assert registers['d0']&0xffff0000==d0&0xffff0000
        if mode!='seed':assert registers['d1']==d1
        rows.append({'mode':mode,'profile':label,'entry_cpu_address':ENTRIES[mode],
            'initial_d0':d0,'initial_d1':d1,'result':parsed,
            'initial_cursor':struct.unpack_from('>I',ram,0xd722)[0],
            'final_cursor':struct.unpack_from('>I',expected,0xd722)[0],
            'ram_sha256':hashlib.sha256(expected).hexdigest()})
        return bytearray(out.read_bytes()),parsed['d0'],parsed['d1']
    for seed,high,low,first_d1 in itertools.product((0,1,0xfffe,0xffff),
            (0,0x12340000,0xffff0000),(0,1,0xffff),(0,0xabcdab68,0xffffffff)):
        ram=fixture();struct.pack_into('>H',ram,0xf02c,seed)
        compare(ram,'seed',high|low,first_d1,'seed-counter-wrap-and-register-widths')
    for cursor,word in itertools.product(range(0x10d6b4,0x10d722,2),(0,1,0x8000,0xffff)):
        ram=fixture();struct.pack_into('>I',ram,0xd722,cursor)
        struct.pack_into('>H',ram,cursor-BASE,word)
        compare(ram,'next',0xabcd1234,0xdeadbeef,'all-cursor-positions-and-old-word-boundaries')
        for limit in (0,1,0xffff):
            compare(ram,'scale',0x12340000|limit,0xdeadbeef,'scaled-boundaries-all-cursors')
    ram=fixture();struct.pack_into('>H',ram,0xf02c,0xffff)
    ram,d0,d1=compare(ram,'seed',0x12340001,0xabcdef12,'carried-sequence-seed')
    for index in range(480):
        mode='next' if index<240 else 'scale'
        ram,d0,d1=compare(ram,mode,d0,d1,'actual-cli-register-ram-carry')
    ram=fixture()
    ram,d0,d1=compare(ram,'seed',0,0xabcdef12,'fixed-limit-sequence-seed')
    fixed_limit_nonzero=0
    for index in range(220):
        # The host supplies limitffff while retaining the preceding actual
        # output high word; RAM and D1 always come from the prior CLI result.
        ram,d0,d1=compare(ram,'scale',(d0&0xffff0000)|0xffff,d1,'host-fixed-ffff-limit-ram-register-carry')
        fixed_limit_nonzero+=int((d0&65535)!=0)
    assert fixed_limit_nonzero>110
    assert struct.unpack_from('>I',ram,0xd722)[0]==0x10d720
    sentinel=b'previous-random-output'
    def reject(ram,mode,d0,d1,label):
        inp.write_bytes(ram);out.write_bytes(sentinel)
        result=subprocess.run([str(executable),mode,str(d0),str(d1),str(inp),str(out)],capture_output=True,text=True)
        assert result.returncode and out.read_bytes()==sentinel and inp.read_bytes()==ram,(label,result.stdout,result.stderr)
        negatives.append({'failure':label,'outputs_preserved':True})
    for cursor,mode in itertools.product((0,0x10d6b2,0x10d6b5,0x10d722,0xffffffff),('next','scale')):
        ram=fixture();struct.pack_into('>I',ram,0xd722,cursor)
        reject(ram,mode,0x12345678,0xabcdef12,'invalid-cursor-'+hex(cursor)+'-'+mode)
    for size,mode in itertools.product((0,65535,65537),ENTRIES):
        reject(bytes(size),mode,0x12345678,0xabcdef12,'invalid-ram-size-'+str(size)+'-'+mode)
    for d0,d1 in ((-1,0),(4294967296,0),(0,-1),(0,4294967296)):
        reject(fixture(),'seed',d0,d1,'invalid-full-register-input')
    for alias_kind in ('same','hardlink','symlink'):
        ram=fixture();inp.write_bytes(ram)
        alias=inp if alias_kind=='same' else folder/(alias_kind+'.bin')
        if alias_kind!='same':
            alias.unlink(missing_ok=True)
            if alias_kind=='hardlink':alias.hardlink_to(inp)
            else:alias.symlink_to(inp)
        result=subprocess.run([str(executable),'seed','1','0',str(inp),str(alias)],capture_output=True,text=True)
        assert result.returncode and inp.read_bytes()==ram
        negatives.append({'failure':'input-output-'+alias_kind+'-alias','outputs_preserved':True})
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    report.write_text(json.dumps({'source':source,'emulator':'Unicorn '+unicorn.__version__,
        'program_code_modified':False,'entry_cpu_addresses':ENTRIES,'cases':len(rows),
        'carried_next_calls':240,'carried_scale_calls':240,
        'host_fixed_ffff_limit_scale_calls':220,'host_fixed_limit_nonzero_outputs':fixed_limit_nonzero,'negative_cases':len(negatives),
        'whole_ram_full_d0_d1_equal':True,'no_native_mmio_writes':True,
        'results':rows,'negative_results':negatives,
        'scope':'Unmodified fixed native seed/next/scaled random routines. All55 cursor positions, '
            'seed counter and old-word boundaries, high register bits, scale limits0/1/ffff and '
            '480 successive calls carrying actual CLI RAM/D0/D1 are compared. Another220 scaled '
            'calls carry actual RAM/D1/D0.high while the host explicitly supplies limitffff; '
            'nonzero output count and four cursor wraps are asserted. Invalid cursors '
            'are host transactional rejections, not native fault emulation. Other CPU registers, '
            'CCR/stack, statistical quality, natural callers and hardware timing are excluded.'},indent=2)+'\n')
    print('Random state:',len(rows),'native/C++ cases;',len(negatives),'transactional rejections;',hashlib.sha256(report.read_bytes()).hexdigest())


if __name__=='__main__':main()
