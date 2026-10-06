"""Reproduce and execute the reviewed ROM-to-RAM rotate loop at 0x1046."""
import hashlib
import json
from pathlib import Path

from unicorn.m68k_const import UC_M68K_REG_PC
from disassemble_program import load_verified_program, disassemble_range
from verify_object_reset import make_cpu


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported program revision')
    source_offset, word_count, cpu_base = 0x1342, 0x8eb, 0x100000
    raw = program[source_offset:source_offset+word_count*2]
    decoded = bytearray()
    for offset in range(0,len(raw),2):
        word = int.from_bytes(raw[offset:offset+2],'big')
        decoded.extend(((word>>3)|((word&7)<<13)).to_bytes(2,'big'))
    cpu = make_cpu(program)
    cpu.mem_map(0x300000,0x1000)  # Watchdog writes are stored; no watchdog device modeled.
    cpu.emu_start(0x1046,0x1066,count=20000)
    if cpu.reg_read(UC_M68K_REG_PC) != 0x1066:
        raise ValueError('RAM decode loop did not reach JSR boundary')
    actual = bytes(cpu.mem_read(cpu_base,len(decoded)))
    if actual != decoded:
        raise ValueError('ROR reconstruction differs from original loop execution')
    destination = root/'extracted/program'
    path = destination/'ram100000.decoded.be.bin'
    path.write_bytes(decoded)
    rows = disassemble_range(decoded,0,len(decoded),cpu_base)
    report = {'schema_version':1,'source_program_sha256':source['sha256'],
              'source_rom_offset':source_offset,'size':len(decoded),'word_count':word_count,
              'transform':'ROR16(word,3)','cpu_base':cpu_base,
              'sha256':hashlib.sha256(decoded).hexdigest(),
              'original_cpu_loop_full_byte_match':True,
              'scope':'Loop output only; transformed code has not been executed. Watchdog device not modeled.',
              'rows':rows}
    output=root/'artifacts/disassembly/ram100000.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    output.with_suffix('.asm').write_text('\n'.join('%06x %s %s [%s]' %
        (r['cpu_address'],r['mnemonic'],r['op_str'],r['classification']) for r in rows)+'\n')
    print('RAM code:',len(decoded),'bytes match original 68000 decode loop; sha256',report['sha256'])


if __name__ == '__main__':
    main()
