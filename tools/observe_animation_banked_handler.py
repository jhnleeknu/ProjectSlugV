"""Isolated original opcode40 handler 4a382..4a3ac on the unpatched canonical program; stop BEFORE 4a276.

Native original CPU observation of the handler body only. This is NOT a whole-49fc6 run, NOT a bank-selection
proof, NOT natural-script reachability and NOT a C++ comparison. A1 points after an already consumed 40 byte
at BYTE field selector, WORD first offset, WORD second offset (synthetic controlled operands in RAM).

Bus model (host mapping, declared; distinct from CPU instruction execution):
  000000..0fffff  fixed cartridge ROM view program[0:100000] (000000..00007f: cart vectors assumed,
                  hardware may show BIOS vectors, neogeo.cpp:1689 banked_vectors_r)
  100000..1fffff  64KiB work RAM and its 15 mirrors (neogeo.cpp:1727 MVS / :1763 AES .mirror(0x0f0000));
                  one ctypes buffer mapped 16 times with mem_map_ptr, so every alias is the same storage
  200000..2fdfff  bank window program[bank_base + (address-200000)] (neogeo.cpp:1412 install_read_bank)
  2fe000..2fffff  PVC cartridge RAM (neogeo.cpp:1483 protection_r -> prot_pvc.cpp:79 m_cart_ram[offset]);
                  declared incoming bytes, read-only for this handler, no ROM behind the overlay
  everything else unmapped: MMIO/palette/BIOS/SRAM/memory card (300000..ffffff) and any effective address
                  >= 1000000 (Unicorn keeps 32-bit addresses; no 24-bit masking is assumed).
Guards stop BEFORE the instruction whose access would be odd (68000 address error not modeled by Unicorn),
outside the backed bank, in an unsupported device region, at a 32-bit-only address, or a write outside RAM.
Nothing patches code; no register/SR is written after emu_start begins; SR is written before A7 at preparation
and read only after the stop. Unicorn 2.1.4 reg_read(SR) does not fold lazily computed N/Z/V/C, so only the SR system
byte is compared; the final CCR is a model value, not a native observation (sr_backend_probe records the evidence).
"""
import ctypes
import hashlib
import inspect
import json
from pathlib import Path
import unicorn
from unicorn import m68k_const as m
from unicorn.unicorn_py3.unicorn import uclib
from disassemble_program import load_verified_program, disassemble_range

SOURCE_SHA256='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
ENTRY,END,STOP=0x4a382,0x4a3ac,0x4a276
HANDLER_SHA256='25ba0fc048cf7394c4e87c564766f4c980d113e18ef17aeb056a9356b54d530d'
FIELD_TABLE,BANK_ROOT=0x4a76c,0x200004
RAM,RAM_SIZE,MIRRORS=0x100000,0x10000,16
BANK,BANK_SIZE=0x200000,0xfe000
PVC,PVC_SIZE=0x2fe000,0x2000
A0,A5,A7,A1_DEFAULT,A6_DEFAULT=0x100036,0x108000,0x10f800,0x106001,0x100400
REG_NAMES=('d0','d1','d2','d3','d4','d5','d6','d7','a0','a1','a2','a3','a4','a5','a6')
# Every handler instruction that touches data memory, in execution order.
ACCESS=((0x4a384,'read',1),(0x4a38e,'read',2),(0x4a392,'read',2),(0x4a39a,'read',4),(0x4a39e,'read',2),(0x4a3a0,'read',4),(0x4a3a4,'write',4))
CAP=64
M32=0xffffffff

def sha(data):return hashlib.sha256(data).hexdigest()
def s16(value):value&=0xffff;return value-0x10000 if value&0x8000 else value
def canonical(address):return RAM|(address&0xffff)

# ---------------------------------------------------------------- independent bus model
def region(address,bank_base,program_size):
    """Host-mapping identity of one logical byte address (no 24-bit masking)."""
    if address>=1<<24:return dict(kind='unsupported_high_32bit',logical=address)
    if address<0x80:return dict(kind='fixed_vector_cart_view_assumed',logical=address,physical_rom=address)
    if address<RAM:return dict(kind='fixed_rom',logical=address,physical_rom=address)
    if address<BANK:return dict(kind='ram',logical=address,canonical_ram=canonical(address),mirror=(address>>16)&15)
    if address<PVC:
        physical=bank_base+address-BANK
        if bank_base+BANK_SIZE>program_size:return dict(kind='excluded_bank_outside_rom',logical=address,bank_base=bank_base)
        return dict(kind='bank_rom',logical=address,bank_base=bank_base,physical_rom=physical)
    if address<0x300000:return dict(kind='pvc_cart_ram',logical=address,pvc_word=(address-PVC)>>1)
    return dict(kind='unsupported_device_region',logical=address)

READABLE=('fixed_vector_cart_view_assumed','fixed_rom','ram','bank_rom','pvc_cart_ram')

def classify(access,address,size,bank_base,program_size):
    """Return (units, problem). A WORD/LONG is split into the 68000's WORD bus units; BYTE is one unit."""
    if size>1 and address&1:return [],'guard_odd_address_68000_address_error_not_modeled'
    step=1 if size==1 else 2
    units=[region(address+i,bank_base,program_size) for i in range(0,size,step)]
    for u in units:
        if u['kind']=='unsupported_high_32bit':return units,'unsupported_high_32bit_effective_address'
        if u['kind']=='excluded_bank_outside_rom':return units,'excluded_bank_outside_rom'
        if u['kind']=='unsupported_device_region':return units,'unsupported_device_region'
        if access=='write' and u['kind']!='ram':return units,'unsupported_write_target_'+u['kind']
    return units,None

class BusModel:
    def __init__(self,program,bank_base,ram,pvc):
        self.program=program;self.bank_base=bank_base;self.ram=bytearray(ram);self.pvc=bytes(pvc)
    def byte(self,address):
        u=region(address,self.bank_base,len(self.program));k=u['kind']
        if k=='ram':return self.ram[u['canonical_ram']-RAM]
        if k in ('fixed_rom','fixed_vector_cart_view_assumed','bank_rom'):return self.program[u['physical_rom']]
        if k=='pvc_cart_ram':return self.pvc[address-PVC]
        raise AssertionError(u)
    def read(self,address,size):return bytes(self.byte(address+i) for i in range(size))
    def write(self,address,data):
        for i,b in enumerate(data):self.ram[canonical(address+i)-RAM]=b

def model(program,fx):
    """Pure-Python handler semantics over the declared bus. Returns accesses and the state at the stop."""
    bus=BusModel(program,fx['bank_base'],fx['ram'],fx['pvc']);r=dict(fx['regs']);accesses=[];sr=fx['sr']
    def access(pc,kind,address,size,data=None):
        address&=M32;units,problem=classify(kind,address,size,bus.bank_base,len(program))
        if problem:return dict(pc=pc,access=kind,address=address,size=size,problem=problem,units=units)
        before=bus.read(address,size)
        accesses.append(dict(pc=pc,access=kind,address=address,size=size,bytes=(data if kind=='write' else before).hex(),
            before=before.hex(),units=units))
        if kind=='write':bus.write(address,data)
        return before
    def run():
        r['d0']=0
        v=access(0x4a384,'read',r['a1'],1)
        if isinstance(v,dict):return v,0x4a384
        r['d0']=(r['d0']&0xffffff00)|v[0];r['a1']=(r['a1']+1)&M32
        r['d0']=(r['d0']&0xffff0000)|((r['d0']*2)&0xffff)
        r['a2']=FIELD_TABLE
        v=access(0x4a38e,'read',r['a2']+s16(r['d0']),2)
        if isinstance(v,dict):return v,0x4a38e
        r['d0']=(r['d0']&0xffff0000)|int.from_bytes(v,'big')
        v=access(0x4a392,'read',r['a1'],2)
        if isinstance(v,dict):return v,0x4a392
        r['d7']=(r['d7']&0xffff0000)|int.from_bytes(v,'big');r['a1']=(r['a1']+2)&M32
        r['a2']=BANK_ROOT
        v=access(0x4a39a,'read',r['a2']+s16(r['d7']),4)
        if isinstance(v,dict):return v,0x4a39a
        r['a2']=int.from_bytes(v,'big')
        v=access(0x4a39e,'read',r['a1'],2)
        if isinstance(v,dict):return v,0x4a39e
        r['d7']=(r['d7']&0xffff0000)|int.from_bytes(v,'big');r['a1']=(r['a1']+2)&M32
        v=access(0x4a3a0,'read',r['a2']+s16(r['d7']),4)
        if isinstance(v,dict):return v,0x4a3a0
        r['d7']=int.from_bytes(v,'big')
        v=access(0x4a3a4,'write',r['a6']+s16(r['d0']),4,r['d7'].to_bytes(4,'big'))
        if isinstance(v,dict):return v,0x4a3a4
        return None,STOP
    guard,pc=run()
    expected_sr=None
    if guard is None:  # add.w (510 max) clears X/C; MOVE.L D7,(ea) sets N/Z and clears V/C.
        expected_sr=(sr&0xff00)|(8 if r['d7']&0x80000000 else 0)|(4 if r['d7']==0 else 0)
    return dict(stop_pc=pc,guard=guard,accesses=accesses,registers=r,ram_after=bytes(bus.ram),expected_sr=expected_sr)

# ---------------------------------------------------------------- cases and fixtures
def cases():
    rows=[]
    def add(label,family,bank,first,second,selector=0x00,expect='complete',**kw):
        row=dict(label=label,family=family,bank_base=bank<<20,selector=selector,first=first,second=second,
            a1=A1_DEFAULT,a6=A6_DEFAULT,sr=0x2000,ram_writes=[],destination_alias=[],expect=expect)
        row.update(kw);rows.append(row)
    # Actual banked ROM first pointers (never patched): bank2 0->22bd12, bank3 0->200008, bank4 0->205704, bank5 0->20011c.
    for second in (0x0000,0x0002,0x7ffe,0x8000,0xfffe,0xfffc):add('bank2-first0-second%04x'%second,'actual-bank-first',2,0,second)
    add('bank2-first0-second0001-odd','guard-odd',2,0,0x0001,expect='guard_odd_address_68000_address_error_not_modeled')
    for second in (0x0000,0x7ffc,0xfff8,0x8000):add('bank3-first0-second%04x'%second,'actual-bank-first',3,0,second)
    add('bank3-first0-secondfff4-ram-mirror-10fffc','actual-bank-first-second-ram',3,0,0xfff4)
    add('bank3-first0-secondfff6-mixed-ram10fffe-bank200000','actual-bank-first-second-mixed',3,0,0xfff6)
    for second in (0x0000,0x7ffe,0xfffe):add('bank4-first0-second%04x'%second,'actual-bank-first',4,0,second)
    add('bank4-first0-second8000-ram-mirror-1fd704','actual-bank-first-second-ram',4,0,0x8000)
    for second in (0x0000,0x7ffe,0xfee4):add('bank5-first0-second%04x'%second,'actual-bank-first',5,0,second)
    add('bank5-first0-secondfee0-ram-mirror-1ffffc','actual-bank-first-second-ram',5,0,0xfee0)
    add('bank5-first0-secondfee2-mixed-ram10fffe-bank200000','actual-bank-first-second-mixed',5,0,0xfee2)
    # First-offset boundaries inside the bank window (actual ROM pointer values).
    add('bank4-first7ffc-208000','actual-bank-first-boundary',4,0x7ffc,0x0000)
    add('bank5-first7ffc-208000-ptr101e07-second0001','actual-bank-first-boundary',5,0x7ffc,0x0001)
    add('bank3-first7ffc-ptr01000000-high','actual-bank-first-boundary',3,0x7ffc,0x0000,expect='unsupported_high_32bit_effective_address')
    add('bank2-first0001-odd','guard-odd',2,0x0001,0x0000,expect='guard_odd_address_68000_address_error_not_modeled')
    # Actual bank2 pointer 2022fe -> 10000e (RAM): RAM / fixed / mixed fixed-RAM second reads.
    for second,tag in ((0x0000,'ram10000e'),(0xfff2,'ram100000'),(0xffee,'fixed-ffffc'),(0xfff0,'mixed-fixed-ffffe-ram100000'),
                       (0x7ff0,'ram107ffe'),(0x8000,'fixed-f800e')):
        add('bank2-first22fa-second%04x-%s'%(second,tag),'actual-bank-first-ram-pointer',2,0x22fa,second)
    # Actual bank2 pointer 202bf6 -> 30002e: PVC, bank last, bank->PVC and unsupported.
    for second,tag,expect in ((0xffce,'pvc-2ffffc','complete'),(0xffc2,'pvc-ff8-ff9-2ffff0','complete'),(0xdfd2,'pvc-first-2fe000','complete'),
                              (0xdfce,'bank-last-2fdffc','complete'),(0xdfd0,'mixed-bank-2fdffe-pvc','complete'),(0x8000,'bank-2f802e','complete'),
                              (0xffd0,'mixed-pvc-2ffffe-unsupported300000','unsupported_device_region'),
                              (0x0000,'mmio-30002e','unsupported_device_region')):
        add('bank2-first2bf2-second%04x-%s'%(second,tag),'actual-bank-first-pvc-pointer',2,0x2bf2,second,expect=expect)
    # Banks 1/6/7 hold ffffffff roots (odd); bank8 is outside the 8MiB program.
    for bank in (1,6,7):add('bank%d-first0-ptrffffffff-odd'%bank,'guard-odd',bank,0,0x0000,expect='guard_odd_address_68000_address_error_not_modeled')
    add('bank1-first0-ptrffffffff-second0001-wrap-to-0','actual-bank-first-32bit-wrap',1,0,0x0001)
    add('bank7-first0-ptrffffffff-second0005-wrap-to-4','actual-bank-first-32bit-wrap',7,0,0x0005)
    add('bank8-first0-excluded','excluded-bank',8,0,0x0000,expect='excluded_bank_outside_rom')
    add('bank8-first8000-ram-then-pointer-104000','excluded-bank-ram-first',8,0x8000,0x0000,
        ram_writes=[dict(address=0x108004,size=4,value=0x104000,purpose='first LONG via mirror 1f8004')])
    # RAM-first: 200004+s16(first) below 200000 is a RAM mirror (pointer values are fixtured in live RAM).
    def ramfirst(label,pointer,second,expect='complete',source=0x108004,bank=2,**kw):
        writes=[dict(address=source,size=4,value=pointer,purpose='first LONG pointer at canonical %06x'%source)]+kw.pop('extra',[])
        add(label,'ram-first',bank,{0x108004:0x8000,0x10fffc:0xfff8}[source],second,expect=expect,ram_writes=writes,**kw)
    ramfirst('ram8000-ptr104000-second0010-ram',0x104000,0x0010)
    ramfirst('ram8000-ptr1a4100-mirror',0x1a4100,0x0000)
    ramfirst('ram8000-ptr10fffe-internal-wrap-110000',0x10fffe,0x0000)
    ramfirst('ram8000-ptr2fdffc-bank-last',0x2fdffc,0x0000)
    ramfirst('ram8000-ptr2fdffe-bank-to-pvc',0x2fdffe,0x0000)
    ramfirst('ram8000-ptr2fe000-pvc-first',0x2fe000,0x0000)
    ramfirst('ram8000-ptr2ffffc-pvc-last',0x2ffffc,0x0000)
    ramfirst('ram8000-ptr0000ff00-fixed',0x0000ff00,0x0000)
    ramfirst('ram8000-ptr2ffffe-pvc-to-300000',0x2ffffe,0x0000,expect='unsupported_device_region')
    ramfirst('ram8000-ptr3c0000-mmio',0x3c0000,0x0000,expect='unsupported_device_region')
    ramfirst('ram8000-ptrc00000-bios',0xc00000,0x0000,expect='unsupported_device_region')
    ramfirst('ram8000-ptr01000000-high',0x01000000,0x0000,expect='unsupported_high_32bit_effective_address')
    ramfirst('ram8000-ptr00000010-secondffe0-negative-32bit',0x10,0xffe0,expect='unsupported_high_32bit_effective_address')
    ramfirst('ram8000-ptr104001-odd',0x104001,0x0000,expect='guard_odd_address_68000_address_error_not_modeled')
    ramfirst('ram8000-ptr2fdffc-bank3',0x2fdffc,0x0000,bank=3)
    ramfirst('ramfff8-1ffffc-ptr104000',0x104000,0x0000,source=0x10fffc)
    ramfirst('ram8000-ptr104000-bank8-no-bank-read',0x104000,0x0000,bank=8)
    add('ramfffa-mixed-ram10fffe-bank200000-ptr00100000-second0100','ram-bank-mixed-first',2,0xfffa,0x0100,
        ram_writes=[dict(address=0x10fffe,size=2,value=0x0010,purpose='high WORD of mixed first LONG (bank2 200000 supplies low WORD)')])
    add('ramfffa-mixed-bank3-ptr00200000-second0000','ram-bank-mixed-first',3,0xfffa,0x0000,
        ram_writes=[dict(address=0x10fffe,size=2,value=0x0020,purpose='high WORD of mixed first LONG (bank3 200000 supplies low WORD)')])
    add('ramfffa-mixed-bank8-excluded','excluded-bank',8,0xfffa,0x0000,expect='excluded_bank_outside_rom')
    add('fffc-bank2-200000-ptr0-second0100-fixed','bank-200000-first',2,0xfffc,0x0100)
    add('fffc-bank2-200000-ptr0-second0040-vector','bank-200000-first',2,0xfffc,0x0040)
    add('fffc-bank3-200000-ptr1-odd','guard-odd',3,0xfffc,0x0000,expect='guard_odd_address_68000_address_error_not_modeled')
    add('fffc-bank3-200000-ptr1-second0001-vector','bank-200000-first',3,0xfffc,0x0001)
    # Actual field-table selectors (no fake table): BYTE boundaries, zero, large positive, negative, odd.
    for sel,a6,expect in ((0x01,A6_DEFAULT,'complete'),(0x02,A6_DEFAULT,'complete'),(0x49,A6_DEFAULT,'complete'),(0x4a,A6_DEFAULT,'complete'),
                          (0x90,A6_DEFAULT,'complete'),(0x92,A6_DEFAULT,'complete'),(0x96,0x10a000,'complete'),(0xd6,0x10a000,'complete'),
                          (0x96,A6_DEFAULT,'unsupported_write_target_fixed_rom'),(0x07,A6_DEFAULT,'guard_odd_address_68000_address_error_not_modeled'),
                          (0xff,0x10a000,'guard_odd_address_68000_address_error_not_modeled')):
        add('field-sel%02x-a6-%06x'%(sel,a6),'field-selector',2,0,0x0000,selector=sel,a6=a6,expect=expect)
    # Destinations: mirrors, internal wrap, live-RAM aliases demonstrating read-before-write.
    add('dest-a6-10fff0-sel00-mirror-110046','destination',2,0,0x0000,a6=0x10fff0)
    add('dest-a6-10ffe6-sel02-internal-wrap-10fffe','destination',2,0,0x0000,selector=0x02,a6=0x10ffe6)
    add('dest-a6-mirror-1a0400','destination',2,0,0x0000,a6=0x1a0400)
    add('dest-a6-1fffa8-ram-to-bank-write','destination',2,0,0x0000,a6=0x1fffa8,expect='unsupported_write_target_bank_rom')
    add('dest-alias-command-operands','destination-alias',2,0,0x0002,selector=0x01,a6=A1_DEFAULT+1,destination_alias=['command_operands'])
    ramfirst('dest-alias-first-pointer-source',0x104000,0x0000,selector=0x00,a6=0x108004-0x56,destination_alias=['first_pointer_source'])
    ramfirst('dest-alias-second-read-source',0x104000,0x0000,selector=0x00,a6=0x104000-0x56,destination_alias=['second_read_source'])
    ramfirst('dest-alias-second-source-via-mirror',0x1c4000,0x0000,selector=0x02,a6=0x104000-0x18,destination_alias=['second_read_source'])
    # Operand stream placement.
    add('a1-mirror-1f6001','operand-stream',2,0,0x0000,a1=0x1f6001)
    add('a1-10fffd-internal-wrap','operand-stream',2,0,0x0000,a1=0x10fffd)
    add('a1-even-106000-odd-word','guard-odd',2,0,0x0000,a1=0x106000,expect='guard_odd_address_68000_address_error_not_modeled')
    add('sr-271f-ccr-all-set','register-width',2,0,0x0000,sr=0x271f)
    add('sr-2700-negative-d7','register-width',2,0,0x8000,sr=0x2700)
    return rows

def pvc_incoming(case,index):
    """Declared incoming PVC cart RAM: deterministic filler plus ff8/ff9 as left by get_bank_base for this bank."""
    data=bytearray(hashlib.shake_256(b'animation-banked-handler-pvc-'+str(index).encode()).digest(PVC_SIZE))
    ff9=((case['bank_base']-0x100000)>>8)&0x7fff
    data[0x1ff0:0x1ff2]=(0x00a0).to_bytes(2,'big');data[0x1ff2:0x1ff4]=ff9.to_bytes(2,'big')
    return bytes(data)

def fixture(case,index,program):
    assert sha(program[ENTRY:END])==HANDLER_SHA256
    ram=bytearray(hashlib.shake_256(b'animation-banked-handler-'+str(index).encode()).digest(RAM_SIZE))
    regs={k:(0x89abcdef+i*0x1020304+index*0x10101)&M32 for i,k in enumerate(REG_NAMES)}
    regs.update(a0=A0,a1=case['a1'],a5=A5,a6=case['a6'],d7=0xa5a50000|((index*0x111)&0xffff))
    writes=[];spans=[]
    def put(address,size,value,purpose):
        data=value.to_bytes(size,'big')
        for i,b in enumerate(data):ram[canonical(address+i)-RAM]=b
        writes.append(dict(address=address,canonical=[canonical(address+i) for i in range(size)],size=size,value=value,purpose=purpose))
        spans.append((purpose,{canonical(address+i) for i in range(size)}))
    opcode=case['a1']-1
    put(opcode,6,(0x40<<40)|(case['selector']<<32)|(case['first']<<16)|case['second'],'command 40 selector first second')
    for w in case['ram_writes']:put(w['address'],w['size'],w['value'],w['purpose'])
    for i,(a,x) in enumerate(spans):
        for b,y in spans[i+1:]:assert not x&y,('unintended fixture overlap',a,b)
    # Destination alias intent is checked against the actual canonical bytes the store would cover.
    field=int.from_bytes(program[FIELD_TABLE+2*case['selector']:FIELD_TABLE+2*case['selector']+2],'big')
    destination=(case['a6']+s16(field))&M32
    dest_bytes={canonical(destination+i) for i in range(4)} if RAM<=destination<=0x1ffffc else set()
    aliases=[]
    if dest_bytes&{canonical(opcode+i) for i in range(1,6)}:aliases.append('command_operands')
    pointer_writes=[w for w in case['ram_writes'] if w['purpose'].startswith('first LONG')]
    if pointer_writes and dest_bytes&{canonical(pointer_writes[0]['address']+i) for i in range(4)}:aliases.append('first_pointer_source')
    if pointer_writes:
        second_ea=(pointer_writes[0]['value']+s16(case['second']))&M32
        if RAM<=second_ea<=0x1ffffc and dest_bytes&{canonical(second_ea+i) for i in range(4)}:aliases.append('second_read_source')
    assert aliases==case['destination_alias'],(case['label'],aliases)
    details=dict(opcode_address=opcode,selector_address=case['a1'],field_word_address=FIELD_TABLE+2*case['selector'],field_word=field,
        destination=destination,destination_canonical=sorted(dest_bytes),destination_alias=aliases,fixture_writes=writes,
        a7_reserved_never_accessed=A7,stack_used=False)
    return dict(ram=bytes(ram),pvc=pvc_incoming(case,index),regs=regs,sr=case['sr'],bank_base=case['bank_base'],details=details)

# ---------------------------------------------------------------- original CPU observer
REG_IDS={k:getattr(m,'UC_M68K_REG_'+k.upper()) for k in REG_NAMES+('a7','pc','sr')}

class Observer:
    """The Uc retains its shared RAM backing even when hook cycles delay finalization."""
    def __init__(self,program,guards=True):
        self.program=program;self.guards=guards;self.cpu=None;self.backing=None
    def prepare(self,fx):
        self.fx=fx;self.backing=(ctypes.c_ubyte*RAM_SIZE).from_buffer_copy(fx['ram'])
        cpu=unicorn.Uc(unicorn.UC_ARCH_M68K,unicorn.UC_MODE_BIG_ENDIAN);cpu.ctl_set_cpu_model(m.UC_CPU_M68K_M68000)
        cpu._ram_backing=self.backing  # hook callbacks can retain Uc until cyclic GC
        R,RX=unicorn.UC_PROT_READ,unicorn.UC_PROT_READ|unicorn.UC_PROT_EXEC
        cpu.mem_map(0,RAM,RX);cpu.mem_write(0,self.program[:RAM])
        for i in range(MIRRORS):cpu.mem_map_ptr(RAM+i*RAM_SIZE,RAM_SIZE,unicorn.UC_PROT_READ|unicorn.UC_PROT_WRITE,ctypes.addressof(self.backing))
        base=fx['bank_base'];self.bank_mapped=base+BANK_SIZE<=len(self.program)
        if self.bank_mapped:cpu.mem_map(BANK,BANK_SIZE,R);cpu.mem_write(BANK,self.program[base:base+BANK_SIZE])
        cpu.mem_map(PVC,PVC_SIZE,R);cpu.mem_write(PVC,fx['pvc'])
        self.pcs=[];self.reads=[];self.writes=[];self.invalid=[];self.interrupts=[];self.guard=None;self.pc=None
        def code(c,pc,size,user):
            self.pcs.append(pc);self.pc=pc
            if pc==STOP:c.emu_stop();return
            if not ENTRY<=pc<END:self.guard=dict(problem='left_handler',pc=pc);c.emu_stop();return
            for apc,kind,asize in ACCESS if self.guards else ():
                if pc!=apc:continue
                address=self.effective(c,pc)
                units,problem=classify(kind,address,asize,base,len(self.program))
                if problem:self.guard=dict(pc=pc,access=kind,address=address,size=asize,problem=problem,units=units);c.emu_stop()
        def read(c,access,address,size,value,user):
            self.reads.append(dict(pc=self.pc,hook_pc=c.reg_read(m.UC_M68K_REG_PC),access='read',address=address,size=size,
                bytes=bytes(c.mem_read(address,size)).hex()))
        def write(c,access,address,size,value,user):
            self.writes.append(dict(pc=self.pc,hook_pc=c.reg_read(m.UC_M68K_REG_PC),access='write',address=address,size=size,
                bytes=(value&((1<<(8*size))-1)).to_bytes(size,'big').hex(),before=bytes(c.mem_read(address,size)).hex()))
        def invalid(c,access,address,size,value,user):
            self.invalid.append(dict(pc=self.pc,access=access,address=address,size=size));return False
        def intr(c,number,user):self.interrupts.append(dict(pc=self.pc,number=number));c.emu_stop()
        cpu.hook_add(unicorn.UC_HOOK_CODE,code);cpu.hook_add(unicorn.UC_HOOK_MEM_READ,read);cpu.hook_add(unicorn.UC_HOOK_MEM_WRITE,write)
        cpu.hook_add(unicorn.UC_HOOK_MEM_INVALID,invalid);cpu.hook_add(unicorn.UC_HOOK_INTR,intr)
        cpu.reg_write(REG_IDS['sr'],fx['sr'])  # SR before A7 (S bit selects which stack pointer A7 names).
        cpu.reg_write(REG_IDS['a7'],A7)
        for k in REG_NAMES:cpu.reg_write(REG_IDS[k],fx['regs'][k])
        self.cpu=cpu;self.incoming=self.registers();return self
    def effective(self,c,pc):
        """Effective address from live registers at an access PC (host read only; nothing is written)."""
        R=lambda k:c.reg_read(REG_IDS[k])
        if pc in (0x4a384,0x4a392,0x4a39e):return R('a1')
        index={0x4a38e:'d0',0x4a39a:'d7',0x4a3a0:'d7',0x4a3a4:'d0'}[pc];base={0x4a3a4:'a6'}.get(pc,'a2')
        return (R(base)+s16(R(index)))&M32
    def registers(self):return {k:self.cpu.reg_read(REG_IDS[k]) for k in REG_NAMES+('a7','pc','sr')}
    def run(self):
        error=None
        try:self.cpu.emu_start(ENTRY,STOP,count=CAP)
        except unicorn.UcError as exc:error=str(exc)
        out=self.registers()
        mirrors_equal=all(bytes(self.cpu.mem_read(RAM+i*RAM_SIZE,RAM_SIZE))==bytes(self.backing) for i in range(MIRRORS))
        rom_ok=bytes(self.cpu.mem_read(0,RAM))==self.program[:RAM]
        if self.bank_mapped:rom_ok&=bytes(self.cpu.mem_read(BANK,BANK_SIZE))==self.program[self.fx['bank_base']:self.fx['bank_base']+BANK_SIZE]
        pvc_ok=bytes(self.cpu.mem_read(PVC,PVC_SIZE))==self.fx['pvc']
        result=dict(incoming=self.incoming,outgoing=out,pcs=self.pcs,reads=self.reads,writes=self.writes,invalid=self.invalid,
            interrupts=self.interrupts,guard=self.guard,error=error,mirrors_coherent=mirrors_equal,mapped_rom_unchanged=rom_ok,
            pvc_unchanged=pvc_ok,bank_window_mapped=self.bank_mapped,ram_after=bytes(self.backing))
        return result
    def close(self):
        self.cpu=None;self.backing=None  # Uc keeps the mapped owner until its own finalization

def run_case(program,case,index):
    fx=fixture(case,index,program);expected=model(program,fx);obs=Observer(program)
    try:native=obs.prepare(fx).run()
    finally:obs.close()
    # ---- native vs independent bus model (no expected value is ever written into the CPU)
    assert native['error'] is None and not native['invalid'] and not native['interrupts'],(case['label'],native['error'],native['invalid'])
    assert native['mirrors_coherent'] and native['mapped_rom_unchanged'] and native['pvc_unchanged'],case['label']
    assert native['outgoing']['pc']==expected['stop_pc'],(case['label'],hex(native['outgoing']['pc']),hex(expected['stop_pc']))
    problem=(expected['guard'] or {}).get('problem')
    assert (native['guard'] or {}).get('problem')==problem and (problem or 'complete')==case['expect'],(case['label'],native['guard'],problem)
    if problem:assert native['guard']['address']==expected['guard']['address'] and native['guard']['pc']==expected['guard']['pc']
    observed=[dict(pc=x['pc'],access=x['access'],address=x['address'],size=x['size'],bytes=x['bytes']) for x in native['reads']+native['writes']]
    observed.sort(key=lambda x:native['pcs'].index(x['pc']))
    wanted=[dict(pc=x['pc'],access=x['access'],address=x['address'],size=x['size'],bytes=x['bytes']) for x in expected['accesses']]
    assert observed==wanted,(case['label'],observed,wanted)
    for x in native['reads']+native['writes']:assert x['hook_pc']==x['pc'],x
    for w,e in zip(native['writes'],[x for x in expected['accesses'] if x['access']=='write']):assert w['before']==e['before'],(case['label'],w,e)
    for k in REG_NAMES:assert native['outgoing'][k]==expected['registers'][k],(case['label'],k,hex(native['outgoing'][k]),hex(expected['registers'][k]))
    assert native['outgoing']['a7']==A7 and native['ram_after']==expected['ram_after'],case['label']
    # Unicorn reg_read(SR) does not fold lazily computed N/Z/V/C (see sr_backend_probe); only the system byte is compared.
    assert native['outgoing']['sr']&0xff00==fx['sr']&0xff00,(case['label'],hex(native['outgoing']['sr']))
    if problem is None:
        # emu_start(until=4a276) halts before the code hook fires at 4a276; PC is checked above.
        assert native['pcs']==[0x4a382,0x4a384,0x4a386,0x4a388,0x4a38e,0x4a392,0x4a394,0x4a39a,0x4a39e,0x4a3a0,0x4a3a4,0x4a3a8]
        assert native['outgoing']['d6']==native['incoming']['d6']  # 4a276 MOVE.L A1,D6 did not execute
    changed=[i for i in range(RAM_SIZE) if fx['ram'][i]!=native['ram_after'][i]]
    assert all(RAM+i in fx['details']['destination_canonical'] for i in changed),(case['label'],changed)
    return fx,expected,native

def summarize(fx,expected,native,case):
    accesses=[]
    for x in expected['accesses']:
        accesses.append(dict(pc=x['pc'],access=x['access'],address=x['address'],size=x['size'],value=x['bytes'],before=x['before'],units=x['units']))
    return dict(label=case['label'],family=case['family'],outcome=(expected['guard'] or {}).get('problem','complete'),
        stop_pc=native['outgoing']['pc'],guard=native['guard'],error=native['error'],
        incoming=dict(registers15={k:native['incoming'][k] for k in REG_NAMES},a7=native['incoming']['a7'],sr=native['incoming']['sr'],pc=ENTRY),
        outgoing=dict(registers15={k:native['outgoing'][k] for k in REG_NAMES},a7=native['outgoing']['a7'],sr=native['outgoing']['sr'],pc=native['outgoing']['pc']),
        changed_registers=sorted(k for k in REG_NAMES if native['incoming'][k]!=native['outgoing'][k]),
        ordered_accesses=accesses,details=fx['details'],bank_base=fx['bank_base'],bank_window_mapped=native['bank_window_mapped'],
        mirrors_coherent=native['mirrors_coherent'],mapped_rom_unchanged=native['mapped_rom_unchanged'],pvc_unchanged=native['pvc_unchanged'],
        model_ccr_not_natively_observed=None if expected['expected_sr'] is None else expected['expected_sr']&0xff,model_equal=True)

def guard_controls(program,rows):
    """Re-run representative guarded cases with guards DISABLED to record raw backend behaviour (not hardware)."""
    labels=('bank2-first0001-odd','bank2-first0-second0001-odd','field-selff-a6-10a000','a1-even-106000-odd-word',
        'ram8000-ptr01000000-high','bank2-first2bf2-second0000-mmio-30002e','field-sel96-a6-100400','dest-a6-1fffa8-ram-to-bank-write')
    out=[]
    for index,case in enumerate(cases()):
        if case['label'] not in labels:continue
        fx=fixture(case,index,program);obs=Observer(program,guards=False)
        try:native=obs.prepare(fx).run()
        finally:obs.close()
        changed=[RAM+i for i in range(RAM_SIZE) if fx['ram'][i]!=native['ram_after'][i]]
        out.append(dict(label=case['label'],guarded_outcome=rows[index]['outcome'],guarded_stop_pc=rows[index]['stop_pc'],
            unguarded_final_pc=native['outgoing']['pc'],unguarded_error=native['error'],invalid=native['invalid'],interrupts=native['interrupts'],
            reads=native['reads'],writes=native['writes'],ram_changed_canonical=changed,mapped_rom_unchanged=native['mapped_rom_unchanged'],
            registers15={k:native['outgoing'][k] for k in REG_NAMES}))
    assert len(out)==len(labels),[o['label'] for o in out]
    return dict(not_hardware=True,purpose='shows what an unguarded Unicorn oracle would report for accesses this observer guards',controls=out)

def sr_backend_probe():
    """Synthetic (no ROM): flag-setting instruction then MOVE SR,D2; compares host reg_read(SR) with the CPU-visible SR."""
    rows=[]
    for name,code in (('cmp.w d1,d0 0<1','70007201b041'),('addq.l #1 of -1','70ff5280'),('moveq #0 then move.l d0,(a0)','70002080'),
                      ('ori.b #1,ccr','003c0001')):
        raw=bytes.fromhex(code+'40c2');cpu=unicorn.Uc(unicorn.UC_ARCH_M68K,unicorn.UC_MODE_BIG_ENDIAN);cpu.ctl_set_cpu_model(m.UC_CPU_M68K_M68000)
        cpu.mem_map(0,0x10000);cpu.mem_write(0x1000,raw);cpu.reg_write(REG_IDS['sr'],0x2000);cpu.reg_write(REG_IDS['a0'],0x8000)
        cpu.emu_start(0x1000,0x1000+len(raw))
        rows.append(dict(sequence=name,code=raw.hex(),host_reg_read_sr=cpu.reg_read(REG_IDS['sr']),cpu_move_sr_d2=cpu.reg_read(REG_IDS['d2'])&0xffff))
    return dict(synthetic_only=True,rows=rows,host_sr_ccr_reliable=all(r['host_reg_read_sr']==r['cpu_move_sr_d2'] for r in rows))

def pinned_reference(root):
    ref=root/'artifacts/reference';neogeo=(ref/'neogeo.cpp').read_text().splitlines();pvc=(ref/'prot_pvc.cpp').read_text().splitlines()
    checks=((neogeo,1727,'map(0x100000, 0x10ffff).mirror(0x0f0000).ram();'),(neogeo,1763,'map(0x100000, 0x10ffff).mirror(0x0f0000).ram();'),
        (neogeo,1412,'space.install_read_bank(0x200000, 0x2fffff, m_bank_cartridge);'),
        (neogeo,1483,'space.install_read_handler(0x2fe000, 0x2fffff, read16m_delegate(*m_slots[m_curr_slot], FUNC(neogeo_cart_slot_device::protection_r)));'),
        (neogeo,1726,'map(0x000000, 0x00007f).r(FUNC(ngarcade_base_state::banked_vectors_r));'),
        (pvc,81,'return m_cart_ram[offset];'))
    lines=[]
    for text,line,want in checks:
        assert text[line-1].strip()==want,(line,text[line-1]);lines.append(dict(file='neogeo.cpp' if text is neogeo else 'prot_pvc.cpp',line=line,text=want))
    return dict(revision=(ref/'revision.txt').read_text().strip(),lines=lines,
        files={n:sha((ref/n).read_bytes()) for n in ('neogeo.cpp','prot_pvc.cpp','revision.txt')})

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    program=bytes(program);folder=root/'artifacts/animation_banked_handler_native';folder.mkdir(parents=True,exist_ok=True)
    for old in folder.glob('case_*'):old.unlink()
    (folder/'observation.json').unlink(missing_ok=True)
    instructions=disassemble_range(program,ENTRY,END-ENTRY,ENTRY)+disassemble_range(program,STOP,4,STOP)
    for r in instructions:assert bytes.fromhex(r['raw'])==program[r['rom_offset']:r['rom_offset']+r['size']]
    table=[int.from_bytes(program[FIELD_TABLE+2*i:FIELD_TABLE+2*i+2],'big') for i in range(256)]
    probe=root/'artifacts/m68k_bus_alias_probe/observation.json'
    probe_info=dict(file=str(probe.relative_to(root)),sha256=sha(probe.read_bytes()),tool_sha256=json.loads(probe.read_text())['tool_sha256']) if probe.exists() else None
    pinned=pinned_reference(root)
    (folder/'source.json').write_text(json.dumps(dict(source=source,handler=dict(start=ENTRY,end=END,raw=program[ENTRY:END].hex(),sha256=HANDLER_SHA256,
        rom_offset_equals_cpu_address=True),stop_before=STOP,instructions=instructions,
        field_table=dict(cpu_address=FIELD_TABLE,rom_offset=FIELD_TABLE,selectors=256,raw=program[FIELD_TABLE:FIELD_TABLE+512].hex(),
            sha256=sha(program[FIELD_TABLE:FIELD_TABLE+512]),words=table,
            note='BYTE selector*2 reaches 4a76c..4a96b; words beyond about selector 90 are bytes of following code, read as-is'),
        bank_roots={str(b):program[(b<<20)+4:(b<<20)+8].hex() for b in range(1,8)},pinned_reference=pinned),indent=2)+'\n')
    tool=Path(__file__).resolve()
    inputs={n:sha((root/n).read_bytes()) for n in ('tools/observe_animation_banked_handler.py','tools/disassemble_program.py',
        'artifacts/reference/neogeo.cpp','artifacts/reference/prot_pvc.cpp','artifacts/animation_banked_handler_native/source.json')}
    library=Path(uclib._name);oracle=dict(engine='Unicorn M68000 (UC_CPU_M68K_M68000)',version=unicorn.__version__,library=str(library),
        library_sha256=sha(library.read_bytes()),wrapper_sha256=sha(Path(inspect.getfile(unicorn.Uc)).read_bytes()))
    rows=[];artifacts={}
    for index,case in enumerate(cases()):
        fx,expected,native=run_case(program,case,index)
        fx2,expected2,native2=run_case(program,case,index)  # independent fresh Uc and backing
        assert fx2==fx and expected2==expected and native2==native,case['label']
        row=summarize(fx,expected,native,case);row.update(case_index=index,case=case,reproduced_twice=True)
        payloads={'case_%04d_ram_before.bin'%index:fx['ram'],'case_%04d_ram_after.bin'%index:native['ram_after'],
            'case_%04d_pvc_incoming.bin'%index:fx['pvc'],
            'case_%04d_trace.json'%index:(json.dumps(dict(pcs=native['pcs'],reads=native['reads'],writes=native['writes'],invalid=native['invalid'],
                interrupts=native['interrupts'],guard=native['guard'],error=native['error']))+'\n').encode()}
        for n,data in payloads.items():(folder/n).write_bytes(data);artifacts[n]=sha(data)
        row.update(ram_before_sha256=sha(fx['ram']),ram_after_sha256=sha(native['ram_after']),pvc_incoming_sha256=sha(fx['pvc']))
        rows.append(row)
    assert sha(program)==SOURCE_SHA256 and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    assert all(sha((root/n).read_bytes())==h for n,h in inputs.items())
    outcomes={}
    for r in rows:outcomes[r['outcome']]=outcomes.get(r['outcome'],0)+1
    kinds={}
    for r in rows:
        for x in r['ordered_accesses']:
            k='+'.join(u['kind'] for u in x['units']);kinds[k]=kinds.get(k,0)+1
    report=dict(source=source,oracle=oracle,inputs=inputs,pinned_reference=pinned,bus_alias_probe=probe_info,sr_backend_probe=sr_backend_probe(),guard_controls=guard_controls(program,rows),
        handler=dict(start=ENTRY,end=END,sha256=HANDLER_SHA256,stop_before=STOP),
        bus_model=dict(fixed='000000..0fffff program[0:100000]; 000000..00007f cart vectors assumed',
            ram='100000..1fffff -> canonical 100000|(a&ffff); one ctypes buffer mem_map_ptr x16',
            bank='200000..2fdfff -> program[bank_base+a-200000]; unmapped and excluded when bank_base+fe000>program size',
            pvc='2fe000..2fffff declared incoming cart RAM, read-only here; ff8/ff9 words set as left by get_bank_base',
            unsupported='300000..ffffff and every effective address >=1000000 (no 24-bit masking assumed)',
            units='WORD/LONG accesses are classified per 68000 WORD bus unit; Unicorn hooks report one logical access'),
        cases=len(rows),outcomes=outcomes,access_unit_kinds=dict(sorted(kinds.items())),reproduced_twice=True,
        original_program_modified=False,register_injection_after_begin=False,in_hook_SR_access=False,fabricated_stack=False,
        fake_dispatch=False,Cpp_comparison_performed=False,opcode40_full_claim=False,failure=None,
        artifact_files=len(artifacts),artifact_manifest_sha256=sha(json.dumps(sorted(artifacts.items())).encode()),
        artifacts=dict(sorted(artifacts.items())),results=rows,
        limitations=['Isolated handler 4a382..4a3a8 only; stops before 4a276 (no A1 publication, dispatch or RTS). Not whole 49fc6, not bank selection, not natural reachability.',
            'Operands, A6, A1 and RAM pointer values are synthetic controlled fixtures; ROM pointers and the field table are actual and unpatched.',
            'PVC cart RAM contents are declared, not observed from a device. Vector area 0..7f uses the cartridge view; hardware may map BIOS vectors there.',
            'Unicorn does not raise 68000 address errors; odd WORD/LONG accesses are guarded before execution, not executed.',
            'Effective addresses >=1000000 and 300000..ffffff devices are unsupported and guarded; a real 68000 drives only A1..A23, which this observer does not model.',
            'Final CCR is not observed: Unicorn reg_read(SR) omits lazily computed N/Z/V/C (sr_backend_probe); only the SR system byte is compared.',
            'Hook accesses are logical CPU accesses; per-WORD bus cycles, timing, wait states and IRQ are not observed.',
            'Bank bases are whole-MiB 1..8 only; arbitrary PVC bank bases (256-byte granularity) are not exercised.'],
        scope='Unpatched original opcode40 handler: BYTE selector -> actual 4a76c field WORD -> first WORD -> LONG 200004+s16 -> second WORD -> '
            'LONG A2+s16 -> store LONG A6+s16(field); full 64KiB RAM, 15 registers + A7/SR, ordered read/write PCs with before values, twice per case.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),outcomes=outcomes,artifacts=len(artifacts),sha256=sha(path.read_bytes()))))

if __name__=='__main__':main()
