"""Native scene-node primitives: exact RAM/register differential boundaries."""
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
REGS=(m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D3,m.UC_M68K_REG_A0,m.UC_M68K_REG_A1)
KEYS=('d0','d1','d3','a0','a1')
ENTRIES=(0x43dda,0x16fac,0x43e22,0x16fee,0x43e38,0x43ea8,0x1728c,0x1724c,0x1726c,0x17292)

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
    folder=root/'artifacts/scene_node';folder.mkdir(parents=True,exist_ok=True)
    inp,out,report=[folder/name for name in ('input.bin','cpp.bin','verification.json')];report.unlink(missing_ok=True)
    cpu=make_cpu(program);rows,negatives,sequences,paths=[],[],[],[]
    def code(cpu,address,size,user):
        if address==RETURN:cpu.emu_stop()
        elif address in (0x43dda,0x43e22,0x43e38,0x43ea8):paths.append(address)
    def write(cpu,access,address,size,value,user):
        assert BASE<=address and address+size<=BASE+65536 or STACK-64<=address and address+size<=STACK+4,(hex(address),size,value)
    cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    def fixture(node=0x1000,parent=0,stamp=0,current=1):
        ram=bytearray(hashlib.shake_256(b'scene-node'+len(rows).to_bytes(4,'big')).digest(65536))
        struct.pack_into('>5I',ram,node,0xffff0001,0x7fffffff,0x00010001,0x80000001,parent)
        struct.pack_into('>4I',ram,node+0x14,0x12345678,0x87654321,0x11223344,0x55667788)
        ram[node+0x24]=stamp;ram[node+0x25]=0xa0;ram[0xd494]=current
        if parent:
            at=parent-BASE;struct.pack_into('>II',ram,at+0x14,0x00010001,0x80000001);ram[at+0x25]=0x40
        return ram
    def compare(ram,entry,values,label):
        cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.reg_write(m.UC_M68K_REG_A7,STACK)
        cpu.mem_write(STACK,RETURN.to_bytes(4,'big'));cpu.reg_write(m.UC_M68K_REG_A5,0x108000)
        for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
        paths.clear();cpu.emu_start(entry,0xffffff,count=30000)
        assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN and cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4
        expected=bytes(cpu.mem_read(BASE,65536));result=dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)))
        inp.write_bytes(ram);actual=subprocess.run([str(root/'build/step_scene_node'),str(entry)]+[str(value) for value in values]+[str(inp),str(out)],capture_output=True,text=True)
        assert not actual.returncode,(label,actual.stderr)
        parsed=json.loads(actual.stdout);actual_ram=out.read_bytes()
        if actual_ram!=expected or parsed!=result:
            diff=[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b]
            raise ValueError(repr((label,hex(entry),values,diff[:16],result,parsed)))
        assert result['a0']==values[3]
        rows.append(dict(profile=label,entry_cpu_address=entry,entry_rom_offset=entry,incoming=dict(zip(KEYS,values)),result=parsed,native_calls=paths.copy(),ram_sha256=hashlib.sha256(expected).hexdigest()))
        return bytearray(actual_ram),parsed
    highs=((0,0,0),(0xabcd1234,0xfedcba98,0x87654321),(0xffffffff,0xffffffff,0xffffffff))
    for entry,node,values in itertools.product((0x43dda,0x16fac),(0,0x9156,0xb1d6,0xd256,0xd2d6),highs):
        compare(fixture(node),entry,values+(BASE+node,0xdeadbeef),'initialization-real-nodes-and-unused-a1')
    for entry,high,low,factor,fraction in itertools.product((0x1724c,0x1726c),(0,1,0x7fff,0x8000,0xffff),(0,1,0xff,0x100,0x8000,0xffff),(0,1,0x100,0x7fff,0x8000,0xffff),(0,1,255)):
        ram=fixture();struct.pack_into('>HH',ram,0x1028,factor,factor);ram[0x102c]=fraction;ram[0x102d]=fraction
        compare(ram,entry,((high<<16)|low,(high<<16)|low,0x87654321,0x101000,0xffffffff),'unsigned-first-mul-asr32-signed-second-mul-fraction-carry')
    for entry,parent,stamp,current,carry in itertools.product((0x43e22,0x16fee,0x43e38,0x43ea8,0x1728c),(0,0x102000,0x101000,0x101004),(0,1,255),(0,1,255),range(4)):
        ram=fixture(parent=parent,stamp=stamp,current=current)
        x=0xffff0000|(0xffff if carry&1 else 0);y=0x7fff0000|(0xffff if carry&2 else 0)
        struct.pack_into('>II',ram,0x1000,x,y)
        compare(ram,entry,(x,y,0xabcd1234,0x101000,parent),'set-update-advance-parent-overlap-stamp-and-lowword-carry')
    for entry in ENTRIES:
        span=0x7b if entry==0x16fac else 0x2080 if entry==0x17292 else 0x2e if entry in (0x16fee,0x1724c,0x1726c) else 0x26
        last=(0x10000-span)&~1
        for node in (0,last):
            ram=fixture(node);compare(ram,entry,(0x8000ffff,0x7fffffff,0x87654321,BASE+node,0),'aligned-node-span-boundaries')
    for node in (0,0x9156,0xb1d6,0xd256,0xd2d6,0xdf80):
        compare(fixture(node),0x17292,(0xabcd1234,0xfedcba98,0x87654321,BASE+node,0xffffffff),'8192-byte-clear-real-nodes-and-boundary')
    for node,parent in itertools.product((0x9156,0xb1d6,0xd256,0xd2d6),(0,0x102000)):
        ram=fixture(node,parent);state=dict(d0=0xabcd1234,d1=0xfedcba98,d3=0x87654321,a0=BASE+node,a1=parent);first=len(rows)
        ram,state=compare(ram,0x16fac,tuple(state[key] for key in KEYS),'actual-cli-init-carry')
        # Host supplies positions/parent; all subsequent RAM/data output carries.
        state.update(d0=0xffff00ff,d1=0x800000ff,a1=parent)
        for entry in (0x16fee,0x1724c,0x1726c,0x1728c,0x1728c):
            ram,state=compare(ram,entry,tuple(state[key] for key in KEYS),'actual-cli-set-scale-advance-carry')
        sequences.append(dict(calls=len(rows)-first,actual_cli_ram_registers_carried=True,host_input='positions and parent at set boundary',node=BASE+node,parent=parent))
    sentinel=b'old-scene-node-output\0\xff'
    def reject(ram,entry='0x43e38',values=('0','0','0','0x101000','0'),label='invalid'):
        inp.write_bytes(ram);out.write_bytes(sentinel)
        actual=subprocess.run([str(root/'build/step_scene_node'),entry]+list(values)+[str(inp),str(out)],capture_output=True,text=True)
        assert actual.returncode and out.read_bytes()==sentinel,(label,actual.stderr)
        negatives.append(dict(failure=label,output_preserved=True,native_executed=False))
    for entry in ENTRIES:
        span=0x7b if entry==0x16fac else 0x2080 if entry==0x17292 else 0x2e if entry in (0x16fee,0x1724c,0x1726c) else 0x26
        for pointer in (0,0x100001,0x110000-span+2,0x110000,0xffffffff):reject(fixture(),str(entry),('0','0','0',str(pointer),'0'),label='invalid-node-span')
    for pointer in (0x100001,0x10ffe8,0x110000,0xffffffff):
        ram=fixture();struct.pack_into('>I',ram,0x1010,pointer);reject(ram,label='late-invalid-parent-pointer')
        reject(fixture(),entry='0x16fee',values=('1','2','3','0x101000',str(pointer)),label='set-parent-error-after-local-writes')
    for size in (0,65535,65537):reject(bytes(size),label='invalid-ram-size')
    for field,bad in itertools.product(range(6),('-1','4294967296','0x','1x','')):
        args=['0x43dda','0','0','0','0x101000','0'];args[field]=bad
        reject(fixture(),entry=args[0],values=args[1:],label='invalid-uint32-parser')
    for kind in ('same','hardlink','symlink'):
        ram=fixture();inp.write_bytes(ram);alias=inp if kind=='same' else folder/('alias-'+kind+'.bin')
        if kind!='same':
            alias.unlink(missing_ok=True)
            if kind=='hardlink':alias.hardlink_to(inp)
            else:alias.symlink_to(inp)
        actual=subprocess.run([str(root/'build/step_scene_node'),'0x43dda','0','0','0','0x101000','0',str(inp),str(alias)],capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==ram
        negatives.append(dict(failure='input-output-'+kind+'-alias',output_preserved=True,native_executed=False))
    assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
    report.write_text(json.dumps(dict(source=source,emulator='Unicorn '+unicorn.__version__,program_code_modified=False,entries_cpu_and_rom_offsets=list(ENTRIES),cases=len(rows),negative_cases=len(negatives),full_ram_d0_d1_d3_a0_a1_equal=True,mmio_writes=0,carry_sequences=sequences,results=rows,negative_results=negatives,scope='Native exact primitive entry-to-RTS comparisons without patches/stubs. Full64KiB RAM and exposed registers compared; lowword carry, unsigned first multiply/ASR32/signed second multiply, stamp updates and controlled overlapping parents are fixture observations. Actual CLI output carries init/set/scale/advance with explicit host positions/parent at set. Real scene-node addresses tested, not scene initialization/scheduler equivalence. Other scratch registers/CCR/timing excluded; invalid pointer original execution excluded.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negatives=len(negatives),sequences=len(sequences),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__':main()
