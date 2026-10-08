"""Exercise readonly data-bank replacement with synthetic fixed CPU instructions.

This is a backend probe, NOT execution or modification of the game program.
The canonical program is borrowed only as immutable bank data. No banked-code,
shared-stack, general PVC, or full scene equivalence claim follows from it.
Run from any directory with the repository Python environment.
"""
import sys,pathlib,json,hashlib,ctypes
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import unicorn
from unicorn import m68k_const as m
from disassemble_program import load_verified_program
from address_map import pvc_bank_update
p,source=load_verified_program(ROOT)
rom=ROOT/source['path'];rom_before=(hashlib.sha256(rom.read_bytes()).hexdigest(),rom.stat().st_mtime_ns)
c=unicorn.Uc(unicorn.UC_ARCH_M68K,unicorn.UC_MODE_BIG_ENDIAN);c.ctl_set_cpu_model(m.UC_CPU_M68K_M68000)
code=bytes.fromhex('33fc2000002ffff233fc0000002ffff020390020000033fc1000002ffff233fc0000002ffff02239002000004e71')
c.mem_map(0,4096,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC);c.mem_write(0,code)
backing=(ctypes.c_ubyte*0xfe000).from_buffer_copy(p[0x200000:0x2fe000]);c._bank_backing=backing
c.mem_map_ptr(0x200000,0xfe000,unicorn.UC_PROT_READ,ctypes.addressof(backing))
c.mem_map(0x2fe000,8192);s={'bank':0x200000,'ff8':0xa0,'ff9':0x1000};events=[]
def write(cpu,access,a,n,v,user):
 assert n==2 and a in (0x2ffff0,0x2ffff2)
 s['ff8' if a==0x2ffff0 else 'ff9']=v
 s['bank'],s['ff8'],s['ff9']=pvc_bank_update(s['ff8'],s['ff9'])
 ctypes.memmove(ctypes.addressof(backing),p[s['bank']:s['bank']+0xfe000],0xfe000);events.append(dict(kind='PVCwrite',address=a,value=v,bank=s['bank']))
def read(cpu,access,a,n,v,user):
 events.append(dict(kind='ROMread',address=a,size=n,bank=s['bank'],data=bytes(cpu.mem_read(a,n)).hex()))
c.hook_add(unicorn.UC_HOOK_CODE,lambda cpu,pc,size,user:None)
c.hook_add(unicorn.UC_HOOK_MEM_WRITE,write,begin=0x2ffff0,end=0x2ffff3)
c.hook_add(unicorn.UC_HOOK_MEM_READ,read,begin=0x200000,end=0x2fdfff)
c.reg_write(m.UC_M68K_REG_SR,0x2000);c.reg_write(m.UC_M68K_REG_A7,0x1000)
c.emu_start(0,len(code)-2,count=50)
d0=c.reg_read(m.UC_M68K_REG_D0);d1=c.reg_read(m.UC_M68K_REG_D1)
assert d0==int.from_bytes(p[0x300000:0x300004],'big') and d1==int.from_bytes(p[0x200000:0x200004],'big')
assert bytes(c.mem_read(0x200000,0xfe000))==p[0x200000:0x2fe000]
assert (hashlib.sha256(rom.read_bytes()).hexdigest(),rom.stat().st_mtime_ns)==rom_before
assert [e['kind'] for e in events]==['PVCwrite','PVCwrite','ROMread','PVCwrite','PVCwrite','ROMread']
assert [e['bank'] for e in events]==[0x300000,0x300000,0x300000,0x200000,0x200000,0x200000]
print(json.dumps(dict(synthetic_code=code.hex(),source=source,unicorn=unicorn.__version__,events=events,d0=d0,d1=d1,passed=True),indent=2))
