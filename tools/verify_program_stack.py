"""Synthetic M68000 stack primitives versus C++ program_stack; no ROM used.

Fresh subprocess/CPU per repeat. This is backend primitive evidence, not whole
animation frames, real hardware CCR/timing, return targets or MMIO equivalence.
"""
import argparse
import ctypes
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import shutil
import sys
import unicorn
from unicorn import m68k_const as m
from unicorn.unicorn_py3.unicorn import uclib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/program_stack_execution'
CODE = 0x4000
OPCODES = {'push': {1: '1f00', 2: '3f00', 4: '2f00'},
           'pop': {1: '101f', 2: '301f', 4: '201f'}}
HARNESS = r'''#include "ms5/program_stack.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <cstdlib>
static std::vector<std::uint8_t> load(const char* path) {
    std::ifstream in(path,std::ios::binary);
    return std::vector<std::uint8_t>((std::istreambuf_iterator<char>(in)),std::istreambuf_iterator<char>());
}
int main(int argc,char** argv) {
    if(argc!=7 && argc!=8)return 2;
    const bool push=std::string(argv[1])=="push";
    unsigned int size=static_cast<unsigned int>(std::strtoul(argv[2],NULL,0));
    std::uint32_t sp=static_cast<std::uint32_t>(std::strtoul(argv[3],NULL,0));
    std::uint32_t value=static_cast<std::uint32_t>(std::strtoul(argv[4],NULL,0));
    std::vector<std::uint8_t> ram=load(argv[5]);
    std::vector<ms5::FixedDataResource> windows;ms5::ProgramBusState bus;
    if(argc==8) {ms5::FixedDataResource w;w.source_cpu_address=0x200100;
        w.source_rom_offset=0x200100;w.data=load(argv[7]);windows.push_back(w);}
    std::string error;
    bool ok=push?ms5::push_program_stack(ram,sp,size,value,error):
        ms5::pop_program_stack(ram,windows,bus,sp,size,value,error);
    std::ofstream out(argv[6],std::ios::binary);
    if(!ram.empty())out.write(reinterpret_cast<const char*>(&ram[0]),ram.size());
    out.close();if(!out)return 3;
    std::cout<<"{\"ok\":"<<(ok?"true":"false")<<",\"a7\":"<<sp
        <<",\"value\":"<<value<<",\"error_nonempty\":"<<(!error.empty()?"true":"false")<<"}\n";
    return 0;
}
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fixture(case):
    ram=bytearray((i*37+(i>>8)*11+0x5a)&255 for i in range(65536))
    # Explicit incoming fixture mutation, before either native or C++ runs.
    if case.get('live_mutation'):
        at=case['sp']&65535
        for i in range(case['size']):ram[(at+i)&65535]=(0xe1+i*7)&255
    return bytes(ram)


def cases():
    rows=[]
    for mirror in range(16):
        for op in ('push','pop'):
            for size in (1,2,4):
                rows.append(dict(label='%s-%d-mirror-%02d'%(op,size,mirror),op=op,size=size,
                                 sp=0x100104+mirror*65536,d0=0xa1b2c3d4))
    for op in ('push','pop'):
        for size in (1,2,4):
            rows.append(dict(label='%s-%d-internal-boundary'%(op,size),op=op,size=size,
                             sp=0x110002 if op=='push' else 0x10fffe,d0=0xfedcba98))
        rows.append(dict(label=op+'-byte-odd-padding',op=op,size=1,sp=0x1feffd,d0=0x789abcde))
    for size in (1,2,4):
        rows.append(dict(label='pop-%d-live-incoming-mutation'%size,op='pop',size=size,
                         sp=0x108200,d0=0x81234567,live_mutation=True))
    for size in (1,2,4):
        rows.append(dict(label='pop-%d-declared-bank-ROM'%size,op='pop',size=size,
                         sp=0x200100,d0=0xcafebabe,bank=True))
    return rows


def native(case):
    ram=fixture(case)
    backing=(ctypes.c_ubyte*65536).from_buffer_copy(ram)
    cpu=unicorn.Uc(unicorn.UC_ARCH_M68K,unicorn.UC_MODE_BIG_ENDIAN)
    cpu._stack_ram_backing=backing
    cpu.ctl_set_cpu_model(m.UC_CPU_M68K_M68000)
    for mirror in range(16):
        cpu.mem_map_ptr(0x100000+mirror*65536,65536,
                        unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE,ctypes.addressof(backing))
    code=bytes.fromhex(OPCODES[case['op']][case['size']])
    cpu.mem_map(CODE,4096,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
    cpu.mem_write(CODE,code)
    cpu.mem_protect(CODE,4096,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC)
    if case.get('bank'):
        cpu.mem_map(0x200000,4096,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE)
        cpu.mem_write(0x200100,bytes.fromhex('91827364'))
        cpu.mem_protect(0x200000,4096,unicorn.UC_PROT_READ)
    reads=[];writes=[];instructions=[]
    def read(c,access,address,size,value,user):
        reads.append(dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,
                          bytes=bytes(c.mem_read(address,size)).hex()))
    def write(c,access,address,size,value,user):
        writes.append(dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=value))
    def instruction(c,address,size,user):instructions.append(dict(pc=address,size=size))
    cpu.hook_add(unicorn.UC_HOOK_MEM_READ,read)
    cpu.hook_add(unicorn.UC_HOOK_MEM_WRITE,write)
    cpu.hook_add(unicorn.UC_HOOK_CODE,instruction)
    # All register writes precede execution; no SR read in hooks or afterward.
    cpu.reg_write(m.UC_M68K_REG_SR,0x2000)
    cpu.reg_write(m.UC_M68K_REG_A7,case['sp'])
    cpu.reg_write(m.UC_M68K_REG_D0,case['d0'])
    cpu.emu_start(CODE,CODE+len(code),count=1)
    after=dict(a7=cpu.reg_read(m.UC_M68K_REG_A7),d0=cpu.reg_read(m.UC_M68K_REG_D0),
               pc=cpu.reg_read(m.UC_M68K_REG_PC))
    assert bytes(cpu.mem_read(CODE,len(code)))==code
    assert instructions==[dict(pc=CODE,size=2)],instructions
    width=case['size'];mask=(1<<(width*8))-1
    stride=4 if width==4 else 2
    assert after['a7']==case['sp']+(-stride if case['op']=='push' else stride)
    if case['op']=='push':assert after['d0']==case['d0']
    else:assert after['d0']&(~mask&0xffffffff)==case['d0']&(~mask&0xffffffff)
    after_ram=bytes(backing)
    if case['op']=='pop':assert after_ram==ram and not writes
    if width==1:
        at=(case['sp']-stride if case['op']=='push' else case['sp'])&65535
        assert after_ram[(at+1)&65535]==ram[(at+1)&65535] # BYTE padding untouched
    return dict(after=after,reads=reads,writes=writes,instructions=instructions,
                code=code.hex(),ram_hex=after_ram.hex())


def cpp(binary,case,input_path,output_path,bank_path):
    args=[str(binary),case['op'],str(case['size']),hex(case['sp']),hex(case['d0']),
          str(input_path),str(output_path)]
    if case.get('bank'):args.append(str(bank_path))
    result=subprocess.run(args,capture_output=True,text=True,check=True,timeout=10)
    value=json.loads(result.stdout)
    assert set(value)=={'ok','a7','value','error_nonempty'}
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child')
    args=parser.parse_args()
    if args.child:
        print(json.dumps(native(json.loads(args.child))));return
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/'verification.json';path.unlink(missing_ok=True)
    inputs=[Path(__file__).resolve(),ROOT/'engine/include/ms5/program_stack.h',ROOT/'engine/src/program_stack.cpp',
            ROOT/'engine/include/ms5/program_bus.h',ROOT/'engine/src/program_bus.cpp',
            ROOT/'engine/include/ms5/fixed_data_resource.h',ROOT/'engine/include/ms5/physical_rom_resource.h',
            Path(inspect.getfile(unicorn.Uc)),Path(unicorn.__file__),Path(m.__file__),
            Path(uclib._name),Path(sys.executable).resolve(),Path(shutil.which('clang++')).resolve()]
    input_hashes={str(p):sha(p) for p in inputs}
    harness=OUT/'harness.cpp';harness.write_text(HARNESS)
    binary=OUT/'program_stack_harness'
    command=['clang++','-std=c++11','-Wall','-Wextra','-pedantic','-I'+str(ROOT/'engine/include'),
             str(ROOT/'engine/src/program_bus.cpp'),str(ROOT/'engine/src/program_stack.cpp'),
             str(harness),'-o',str(binary)]
    build=subprocess.run(command,capture_output=True,text=True,timeout=60)
    (OUT/'build.log').write_text(build.stdout+build.stderr)
    assert build.returncode==0 and not build.stdout and not build.stderr,(build.returncode,build.stderr)
    bank=OUT/'declared_bank.bin';bank.write_bytes(bytes.fromhex('91827364'))
    results=[]
    for index,case in enumerate(cases()):
        prefix=OUT/('case_%03d'%index)
        incoming=prefix.with_suffix('.input.bin');incoming.write_bytes(fixture(case))
        captures=[]
        for repeat in range(2):
            child=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--child',json.dumps(case)],
                                 capture_output=True,text=True,timeout=15,check=True)
            captures.append(json.loads(child.stdout))
        assert captures[0]==captures[1],case
        capture=captures[0];native_ram=bytes.fromhex(capture.pop('ram_hex'))
        native_path=prefix.with_suffix('.native.bin');native_path.write_bytes(native_ram)
        trace_path=prefix.with_suffix('.trace.json');trace_path.write_text(json.dumps(capture,indent=2)+'\n')
        output=prefix.with_suffix('.cpp.bin')
        actual=cpp(binary,case,incoming,output,bank)
        assert actual['ok'] and not actual['error_nonempty'],(case,actual)
        assert actual['a7']==capture['after']['a7'] and output.read_bytes()==native_ram,(case,actual)
        mask=(1<<(case['size']*8))-1
        if case['op']=='pop':assert actual['value']==capture['after']['d0']&mask,(case,actual)
        else:assert actual['value']==case['d0']
        results.append(dict(case=case,native=capture,cpp=actual,repeat_equal=True,passed=True))
    # Checked failures are C++ API tests, not assertions about native faults.
    negatives=[]
    specs=[('push',4,0x200002,65536),('push',2,0x100003,65536),('pop',4,0x100001,65536),
           ('push',4,0,65536),('push',1,1,65536),('pop',4,0xfffffffe,65536),
           ('pop',2,0x2fe000,65536),('pop',4,0,65536),('pop',2,0x300000,65536),('pop',4,0x1ffffe,65536),
           ('push',3,0x108000,65536),('pop',0,0x108000,65536),
           ('push',1,0x108000,65535),('pop',1,0x108000,65535)]
    for index,(op,size,sp,length) in enumerate(specs):
        case=dict(label='checked-%02d'%index,op=op,size=size,sp=sp,d0=0xdeadbeef)
        incoming=OUT/('negative_%02d.input.bin'%index);incoming.write_bytes(fixture(case)[:length])
        output=OUT/('negative_%02d.cpp.bin'%index)
        actual=cpp(binary,case,incoming,output,bank)
        assert not actual['ok'] and actual['error_nonempty']
        assert actual['a7']==sp and actual['value']==case['d0'] and output.read_bytes()==incoming.read_bytes()
        negatives.append(dict(case=case,cpp=actual,passed=True))
    compiler=subprocess.run(['clang++','--version'],capture_output=True,text=True,check=True).stdout
    api=inspect.getsource(unicorn.Uc.mem_map_ptr)
    artifacts=[p for p in OUT.iterdir() if p.is_file() and p.name!='verification.json']
    report=dict(synthetic_only=True,original_ROM_used=False,model='UC_CPU_M68K_M68000',
                native_cases=len(results),native_executions=len(results)*2,checked_failures=len(negatives),
                passed=True,results=results,negative_results=negatives,build_command=command,
                compiler_version=compiler,unicorn_version=unicorn.__version__,python=sys.version,
                mem_map_ptr_source_sha256=hashlib.sha256(api.encode()).hexdigest(),
                inputs=[dict(path=str(p),sha256=input_hashes[str(p)]) for p in inputs],
                artifacts=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in sorted(artifacts)],
                limitations='Synthetic instructions only; no ROM, whole animation frames, MOVEM/JSR/RTS, CCR/timing or hardware proof. High logical addresses are excluded from native comparison because this Unicorn backend does not automatically mask to24bits. Hooks describe backend accesses, not physical16-bit bus cycles. Native faults are not compared with checked C++ failures. Borrowed RAM backing is retained on each CPU owner; each repeat runs in a fresh isolated process.')
    for p,digest in input_hashes.items():assert sha(p)==digest,p
    path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(native_cases=len(results),native_executions=len(results)*2,
                         checked_failures=len(negatives),report=str(path),sha256=sha(path))))


if __name__=='__main__':main()
