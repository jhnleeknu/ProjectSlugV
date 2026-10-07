"""Original-only1a5a4 observations; this does not establish C++ equivalence."""
import hashlib
import json
from pathlib import Path
import struct
import capstone
import unicorn
from unicorn import Uc,UC_ARCH_M68K,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn import m68k_const as m
from disassemble_program import load_verified_program
from verify_stage_catalog import SOURCE_SHA256
ENTRY,BASE,RETURN,STACK=0x1a5a4,0x100000,0xff000,0x1feffc
REGS=[getattr(m,'UC_M68K_REG_D'+str(i)) for i in range(8)]+[getattr(m,'UC_M68K_REG_A'+str(i)) for i in range(8)]
NAMES=['d'+str(i) for i in range(8)]+['a'+str(i) for i in range(8)]

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
    folder=root/'artifacts/stage_initialization';folder.mkdir(parents=True,exist_ok=True)
    report=folder/'probe.json';report.unlink(missing_ok=True)
    decoder=capstone.Cs(capstone.CS_ARCH_M68K,capstone.CS_MODE_BIG_ENDIAN|capstone.CS_MODE_M68K_000)
    def make_cpu():
        cpu=Uc(UC_ARCH_M68K,UC_MODE_BIG_ENDIAN);cpu.ctl_set_cpu_model(m.UC_CPU_M68K_M68000)
        cpu.mem_map(0,0x500000);cpu.mem_map(0xd00000,0x1000)
        cpu.mem_write(0,program[:0x100000]);cpu.mem_write(0x200000,program[0x200000:0x300000])
        cpu.reg_write(m.UC_M68K_REG_SR,0x2000)
        return cpu
    fixtures=[]
    for name,ram in (('zero',bytes(65536)),('seeded',hashlib.shake_256(b'stage-initialization-original-probe').digest(65536))):
        fixtures.append((name,ram))
        cpu=make_cpu();cpu.mem_write(BASE,ram)
        for init in (0x2790,0x3ef2):
            cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'));cpu.emu_start(init,RETURN,count=100000)
            assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN
        fixtures.append((name+'-native2790-3ef2',bytes(cpu.mem_read(BASE,65536))))
    rows=[]
    for name,fixture in fixtures:
        for bits in (0,8,16,24):
            cpu=make_cpu();ram=bytearray(fixture);ram[0xf000]=(ram[0xf000]&~24)|bits;cpu.mem_write(BASE,bytes(ram))
            for reg in REGS:cpu.reg_write(reg,0)
            for reg,value in ((m.UC_M68K_REG_A5,0x108000),(m.UC_M68K_REG_A6,0x100b30),(m.UC_M68K_REG_A7,STACK),(m.UC_M68K_REG_SR,0x2000)):
                cpu.reg_write(reg,value)
            cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
            ports,reads,calls,bank_changes=[],[],[],[];pc_counts={};decode_cache={};state=dict(bank_offset=0x200000,instructions=0,returned=False,rom_write=None)
            def registers():return dict(zip(NAMES,(cpu.reg_read(reg)&0xffffffff for reg in REGS)))
            initial_regs=registers()
            def write(cpu,access,address,size,value,user):
                value&=(1<<(size*8))-1
                if address<0x100000:
                    state['rom_write']=[size,address,value];cpu.emu_stop();return
                if 0x2ffff0<=address and address+size<=0x300000 or 0x300000<=address and address+size<=0x500000 or 0xd00000<=address and address+size<=0xd01000:
                    ports.append([size,address,value])
                    if address==0x2ffff2 and size==2:
                        assert value in (0x1000,0x2000),'Unobserved PVC mapping word'
                        offset=0x200000 if value==0x1000 else 0x300000
                        if offset+0x100000>len(program):raise ValueError('PVC requested source bank beyond original program')
                        # Preserve PVC/MMIO tail; physical window only. Source bytes unchanged.
                        cpu.mem_write(0x200000,program[offset:offset+0xffff0]);state['bank_offset']=offset
                        bank_changes.append(dict(bank_word=value,source_file_offset=offset,cpu_window=0x200000,size=0xffff0))
                elif not (BASE<=address and address+size<=BASE+65536 or 0x1f8000<=address and address+size<=0x1ff000):
                    raise ValueError('Unexpected native non-MMIO write '+repr((hex(address),size,value)))
            def read(cpu,access,address,size,value,user):
                if 0x2ffff0<=address and address+size<=0x300000 or 0x300000<=address and address+size<=0x500000 or 0xd00000<=address and address+size<=0xd01000:
                    reads.append([size,address,int.from_bytes(cpu.mem_read(address,size),'big')])
            def code(cpu,address,size,user):
                if address==RETURN:state['returned']=True;cpu.emu_stop();return
                state['instructions']+=1;pc_counts[address]=pc_counts.get(address,0)+1
                # Unicorn M68K hook size may be2; decode a full real window,
                # never a truncated branch extension or padded fabricated operand.
                window=bytes(cpu.mem_read(address,24));key=(address,window)
                if key not in decode_cache:
                    decoded=next(decoder.disasm(window,address,count=1),None)
                    decode_cache[key]=(decoded.mnemonic,decoded.op_str,decoded.size) if decoded else ('undecoded','',2)
                mnemonic,operand,instruction_size=decode_cache[key]
                raw=window[:instruction_size]
                if address<0x100000:source_offset=address
                elif 0x200000<=address<0x2ffff0:source_offset=state['bank_offset']+address-0x200000
                else:raise ValueError('Executed code outside original mapped ROM '+hex(address))
                assert raw==program[source_offset:source_offset+instruction_size]
                if mnemonic.startswith(('jsr','bsr')):
                    calls.append(dict(call_pc=address,source_file_offset=source_offset,instruction_size=instruction_size,raw=raw.hex(),source_bytes_verified=True,mnemonic=mnemonic,operand=operand,stack_pointer=cpu.reg_read(m.UC_M68K_REG_A7),d0=cpu.reg_read(m.UC_M68K_REG_D0)&0xffffffff,a0=cpu.reg_read(m.UC_M68K_REG_A0)&0xffffffff,a6=cpu.reg_read(m.UC_M68K_REG_A6)&0xffffffff))
            cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_MEM_READ,read);cpu.hook_add(UC_HOOK_CODE,code)
            error=None
            try:cpu.emu_start(ENTRY,0xffffff,count=500000)
            except Exception as exc:error=type(exc).__name__+': '+str(exc)
            final_ram=bytes(cpu.mem_read(BASE,65536));pc=cpu.reg_read(m.UC_M68K_REG_PC)
            fixed_unchanged=bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
            assert fixed_unchanged
            bank_unchanged=bytes(cpu.mem_read(0x200000,0xffff0))==program[state['bank_offset']:state['bank_offset']+0xffff0]
            changed=[index for index,(before,after) in enumerate(zip(ram,final_ram)) if before!=after]
            prefix=name+'-f000-'+str(bits)
            (folder/(prefix+'.ram.bin')).write_bytes(final_ram)
            rows.append(dict(fixture=name,f000_bits_3_4=bits,input_ram_sha256=hashlib.sha256(ram).hexdigest(),initial_registers=initial_regs,returned=state['returned'],final_pc=pc,final_registers=registers(),final_sr=cpu.reg_read(m.UC_M68K_REG_SR),instructions=state['instructions'],error=error,attempted_fixed_rom_write=state['rom_write'],fixed_rom_unchanged=fixed_unchanged,bank_source_unchanged=bank_unchanged,final_ram_sha256=hashlib.sha256(final_ram).hexdigest(),changed_ram_offsets=changed,mmio_writes=ports,mmio_reads=reads,calls=calls,visited_pc_counts=[dict(pc=address,count=count) for address,count in sorted(pc_counts.items())],pvc_bank_changes=bank_changes))
    report.write_text(json.dumps(dict(source=source,emulator='Unicorn '+unicorn.__version__,entry_cpu_address=ENTRY,entry_rom_offset=ENTRY,cases=len(rows),returned_cases=sum(row['returned'] for row in rows),program_code_modified=False,cpp_equivalence_claimed=False,mapping=dict(fixed_rom_cpu=0,fixed_rom_file_offset=0,fixed_rom_size=0x100000,initial_bank_cpu=0x200000,initial_bank_file_offset=0x200000,pvc_bank_rule='Observed words2000/1000 map source3MiB/2MiB respectively; this probe mapping does not establish general PVC behavior; window200000..2fffef; PVCtail excluded',mapped_ranges=['000000..4fffff','d00000..d00fff'],mmio_initial_values='zero; writes retained; no fabricated device reads',external_stack=STACK),results=rows,scope='Original-only bounded observations. No ROM patches, stubs, callback replacements or C++ comparison. Fixture f000 bits3/4 explicitly selected; other fixture bytes retained. Some fixtures use actual2790 and3ef2 before entry. Call mnemonic decoding is an execution trace annotation, not completed semantic analysis. Returned=true requires exact sentinel reached after actual RTS; failure/instruction-budget outcomes retained. Device timing and hardware behavior not modeled.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),returned=sum(row['returned'] for row in rows),failures=[dict(fixture=row['fixture'],bits=row['f000_bits_3_4'],pc=hex(row['final_pc']),error=row['error']) for row in rows if not row['returned']],sha256=hashlib.sha256(report.read_bytes()).hexdigest())))

if __name__=='__main__':main()
