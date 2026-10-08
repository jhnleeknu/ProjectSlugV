"""Synthetic Unicorn primitive probe; NOT original ROM execution or hardware proof.

Each pointer-backed experiment runs in a separate process. The ctypes RAM
buffer is retained on the Uc object for the lifetime of its mapped memory.
"""
import ctypes
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import unicorn
from unicorn import m68k_const as m
from unicorn.unicorn_py3.unicorn import uclib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/m68k_bus_alias_probe'
CODE = 0x4000


def cases():
    rows = [dict(label='mirror-read-%x' % i, code='2010', a0=0x100120+i*0x10000,
                 d0=0, d1=0, expected=0x12345678) for i in range(16)]
    rows += [dict(label='mirror-cpu-write', code='2080', a0=0x1f0120,
                  d0=0xaabbccdd, d1=0, expected=0xaabbccdd),
             dict(label='stack-alias-read', code='2017', a0=0, d0=0, d1=0, expected=0x11223344),
             dict(label='stack-alias-push', code='2f00', a0=0, d0=0xdeadbeef, d1=0, expected=0xdeadbeef),
             dict(label='long-internal-mirror-wrap', code='2010', a0=0x10fffe, d0=0, d1=0, expected=0xaabbccdd),
             dict(label='long-mirror-bank-boundary', code='2010', a0=0x1ffffe, d0=0, d1=0, expected=0xaabb5566),
             dict(label='indexed-word-negative-mixed', code='20301000', a0=0x200000, d0=0, d1=0x1234fffe, expected=0xaabb5566),
             dict(label='indexed-long-negative-mixed', code='20301800', a0=0x200000, d0=0, d1=0xfffffffe, expected=0xaabb5566),
             dict(label='logical-high-address-distinct-mapping', code='2010', a0=0x1200000, d0=0, d1=0, expected=0x99887766),
             dict(label='indexed-word-32bit-wrap', code='20301000', a0=0xfffffff0, d0=0, d1=0x12340020, expected=0x76543210),
             dict(label='indexed-long-32bit-wrap', code='20301800', a0=0xfffffff0, d0=0, d1=0x20, expected=0x76543210),
             dict(label='high-address-unmapped-no24bit-fallback', code='2010', a0=0x2200000, d0=0, d1=0, expected_error=True)]
    return rows


def child(case):
    backing = (ctypes.c_ubyte * 65536)()  # explicit keepalive owner
    cpu = unicorn.Uc(unicorn.UC_ARCH_M68K, unicorn.UC_MODE_BIG_ENDIAN)
    cpu._probe_ram_backing = backing  # retain owner with the mapped CPU object
    cpu.ctl_set_cpu_model(m.UC_CPU_M68K_M68000)
    cpu.mem_map(0, 0x10000)
    pointer = ctypes.addressof(backing)
    for i in range(16):
        cpu.mem_map_ptr(0x100000+i*0x10000,65536,unicorn.UC_PROT_ALL,pointer)
    cpu.mem_map(0x200000,0x1000)
    cpu.mem_map(0x1200000,0x1000)
    cpu.mem_write(CODE,bytes.fromhex(case['code']))
    cpu.mem_write(0x100120,bytes.fromhex('12345678'))
    # Verify host/API writes through every alias, then restore the tested value.
    host_alias=[]
    for i in range(16):
        address=0x100200+i*0x10000
        cpu.mem_write(address,bytes([i]))
        values=[bytes(cpu.mem_read(0x100200+j*0x10000,1)).hex() for j in range(16)]
        assert values==[bytes([i]).hex()]*16
        assert backing[0x200]==i
        host_alias.append(dict(write=address,value=i,all16_equal=True))
    cpu.mem_write(0x10fffe,bytes.fromhex('aabb'))
    cpu.mem_write(0x100000,bytes.fromhex('ccdd'))
    cpu.mem_write(0x200000,bytes.fromhex('55667788'))
    cpu.mem_write(0x1200000,bytes.fromhex('99887766'))
    cpu.mem_write(0x10effc,bytes.fromhex('11223344'))
    cpu.mem_write(0x10eff8,bytes.fromhex('cafebabe'))
    cpu.mem_write(0x10,bytes.fromhex('76543210'))
    reads=[];writes=[];invalid=[];instructions=[]
    def read(c,access,address,size,value,user):
        reads.append(dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,
                          bytes=bytes(c.mem_read(address,size)).hex()))
    def write(c,access,address,size,value,user):
        writes.append(dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=value))
    def bad(c,access,address,size,value,user):
        invalid.append(dict(access=access,address=address,size=size));return False
    def code(c,address,size,user):
        instructions.append(dict(pc=address,size=size))
    cpu.hook_add(unicorn.UC_HOOK_MEM_READ,read)
    cpu.hook_add(unicorn.UC_HOOK_MEM_WRITE,write)
    cpu.hook_add(unicorn.UC_HOOK_MEM_INVALID,bad)
    cpu.hook_add(unicorn.UC_HOOK_CODE,code)
    # SR before A7, never read or mutated inside a hook; no injected registers
    # after emu_start begins.
    cpu.reg_write(m.UC_M68K_REG_SR,0x2000)
    cpu.reg_write(m.UC_M68K_REG_A7,0x1feffc)
    for name in ('a0','d0','d1'):
        cpu.reg_write(getattr(m,'UC_M68K_REG_'+name.upper()),case[name])
    before={n:cpu.reg_read(getattr(m,'UC_M68K_REG_'+n.upper())) for n in ('a0','a7','d0','d1')}
    error=None
    try:cpu.emu_start(CODE,CODE+len(bytes.fromhex(case['code'])),count=1)
    except unicorn.UcError as exc:error=str(exc)
    after={n:cpu.reg_read(getattr(m,'UC_M68K_REG_'+n.upper())) for n in ('a0','a7','d0','d1','pc')}
    if case.get('expected_error'):
        assert error is not None and invalid and invalid[0]['address']==case['a0']
    else:
        assert error is None,(case,error)
        if case['label']=='mirror-cpu-write':
            assert all(int.from_bytes(cpu.mem_read(0x100120+i*0x10000,4),'big')==case['expected'] for i in range(16))
        elif case['label']=='stack-alias-push':
            assert after['a7']==0x1feff8 and int.from_bytes(cpu.mem_read(0x10eff8,4),'big')==case['expected']
        else:assert after['d0']==case['expected'],(case,after)
    return dict(case=case,before=before,after=after,reads=reads,writes=writes,invalid=invalid,
                instructions=instructions,error=error,host_alias_checks=host_alias,
                canonical_efff_window=bytes(cpu.mem_read(0x10eff8,8)).hex(),passed=True)


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--child':
        print(json.dumps(child(json.loads(sys.argv[2]))));return
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[]
    for case in cases():
        result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--child',json.dumps(case)],
                              capture_output=True,text=True,timeout=10)
        assert result.returncode==0,(case,result.returncode,result.stderr)
        rows.append(json.loads(result.stdout))
    api=inspect.getsource(unicorn.Uc.mem_map_ptr)
    report=dict(synthetic_only=True,original_ROM_used=False,model='UC_CPU_M68K_M68000',
                unicorn_version=unicorn.__version__,python=sys.version,
                tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                api_source_path=inspect.getfile(unicorn.Uc),
                api_file_sha256=hashlib.sha256(Path(inspect.getfile(unicorn.Uc)).read_bytes()).hexdigest(),
                native_library_path=uclib._name,
                native_library_sha256=hashlib.sha256(Path(uclib._name).read_bytes()).hexdigest(),
                mem_map_ptr_source=api,
                mem_map_ptr_source_sha256=hashlib.sha256(api.encode()).hexdigest(),
                cases=len(rows),passed=len(rows),results=rows,
                conclusion='Shared ctypes backing coheres16RAM mirrors including stack alias. Synthetic LONG reads return expected concatenated bytes across internal mirror and RAM/bank boundaries. Hooks report logical backend accesses; this is not proof of actual16-bit hardware bus cycles. M68000 backend retains high effective-address bits and wraps indexed additions at32bits; no automatic24-bit bus masking in tested reads.',
                limitations='Synthetic primitives only, not original49fc6/opcode40 proof. No MMIO side effects, instruction timing, native nested stack, IRQ or arbitrary alignment proof. High-address mapping is deliberately backend-only; real68000 external bus has a separate24-bit mapping contract. All cases run in isolated subprocesses; ctypes buffer is retained on Uc as _probe_ram_backing.')
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),passed=len(rows),report=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())))


if __name__=='__main__':main()
