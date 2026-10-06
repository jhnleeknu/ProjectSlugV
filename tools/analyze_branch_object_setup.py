"""Record original initializer prefixes that bind group and acquire palettes."""
import hashlib
import json
from pathlib import Path
from unicorn.m68k_const import UC_M68K_REG_A5, UC_M68K_REG_A6, UC_M68K_REG_A7, UC_M68K_REG_PC
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    if source['sha256'] != '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f':
        raise ValueError('Unsupported ROM')
    cpu = make_cpu(program)
    cpu.mem_map(0x200000, 0x200000)
    cpu.mem_write(0x200000, program[0x200000:0x300000])
    cpu.reg_write(UC_M68K_REG_A5, 0x108000)
    rows = []
    for begin, end, ids in ((0x2b6e6, 0x2b726, (0x3d3, 0x39d, 0x203)),
                             (0x2b7ce, 0x2b80e, (0x87d, 0x39d, 0x87a))):
        cpu.mem_write(0x100000, bytes(65536))
        call(cpu, 0x3ef2)
        cpu.reg_write(UC_M68K_REG_A6, 0x102000)
        cpu.reg_write(UC_M68K_REG_A7, 0x1feffc)
        cpu.emu_start(begin, end, count=20000)
        if cpu.reg_read(UC_M68K_REG_PC) != end: raise ValueError('Initializer prefix did not reach boundary')
        ram = bytes(cpu.mem_read(0x100000, 65536))
        obj = ram[0x2000:0x20c4]
        slots = list(obj[0x19:0x1c])
        nodes = [ram[0x4d92+slot*16:0x4da2+slot*16] for slot in slots]
        if obj[0x20:0x22] != bytes.fromhex('00f2') or slots != [0, 1, 2] or obj[0x1d] != 3 or obj[0x14] != 2:
            raise ValueError('Group or palette slot observation changed')
        if tuple(int.from_bytes(node[10:12], 'big') for node in nodes) != ids:
            raise ValueError('Palette source IDs changed')
        rows.append({'entry': begin, 'stop_before': end, 'group': 0xf2,
                     'palette_ids': ids, 'object_slots': slots, 'current_style_palette': obj[0x14],
                     'palette_nodes_hex': [node.hex() for node in nodes],
                     'ram_sha256': hashlib.sha256(ram).hexdigest()})
    folder = root/'artifacts/branch_object_setup'
    folder.mkdir(parents=True, exist_ok=True)
    (folder/'verification.json').write_text(json.dumps({'source': source, 'results': rows,
        'scope': 'Original-only initializer prefixes with freshly initialized palette RAM. Stops before child-object creation; does not reconstruct allocator or prove natural entry/full object lifecycle. Slot numbers depend on empty allocation state.'}, indent=2)+'\n')
    print('Original setup prefixes verified:', len(rows), 'variants, group F2 and palette triples')


if __name__ == '__main__': main()
