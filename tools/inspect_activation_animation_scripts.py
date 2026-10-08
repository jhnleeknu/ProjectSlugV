"""Inspect two reviewed fixed animation streams; no execution or composition extraction."""
import hashlib
import json
from pathlib import Path
import struct

from disassemble_program import load_verified_program, disassemble_range

SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
CALLERS = {
    0x47cd0: '7000102e007ed040d04041f900048a122e300000',
    0x47d0a: '227c000489c2303c01004eb900049f8c4eb900049fc6',
    0x47ed0: '3d7c00ea0020227c00048980303c01004eb900049f8c',
    0x4a118: '2e190c87007ff800660000044e758e6e0020',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inspect(program, source):
    if source['sha256'] != SOURCE_SHA256:
        raise ValueError('Unsupported canonical ROM')
    callers = []
    for address, raw in CALLERS.items():
        expected = bytes.fromhex(raw)
        if program[address:address+len(expected)] != expected:
            raise ValueError('Reviewed caller bytes changed at %x' % address)
        callers.extend(disassemble_range(program, address, len(expected), address))
    scripts = []
    for start, end, draws, terminal in ((0x48980, 0x489c1, 8, 0x28),
                                        (0x489c2, 0x48a12, 9, 0x08)):
        cursor = start
        commands = []
        for index in range(draws):
            if program[cursor] != 4:
                raise ValueError('Expected reviewed draw at %x' % cursor)
            control, x, y, operand = struct.unpack('>BBBI', program[cursor+1:cursor+8])
            commands.append(dict(id='activation-animation-%06x-draw:%02d' % (start,index),
                                 cpu_address=cursor, rom_offset=cursor, size=8,
                                 raw=program[cursor:cursor+8].hex(), opcode=4,
                                 control=control, x_byte=x, y_byte=y,
                                 identifier_operand=operand,
                                 identifier_binding='operand OR live WORD(object+20), not resolved here'))
            cursor += 8
        if terminal == 0x28:
            if program[cursor] != 0x28 or cursor+1 != end or program[end] != 0:
                raise ValueError('Expected reviewed one-BYTE terminal and separate zero padding')
            commands.append(dict(cpu_address=cursor,rom_offset=cursor,size=1,raw='28',opcode=0x28))
            padding = dict(cpu_address=end,rom_offset=end,size=1,raw='00',
                           classification='outside consumed stream; inferred inter-stream alignment padding')
        else:
            if program[cursor:cursor+8] != bytes.fromhex('00010800000489c2') or cursor+8 != end:
                raise ValueError('Expected reviewed wait1 and jumpback')
            commands.extend([dict(cpu_address=cursor,rom_offset=cursor,size=2,raw='0001',opcode=0,duration=1),
                             dict(cpu_address=cursor+2,rom_offset=cursor+2,size=6,raw='0800000489c2',opcode=8,
                                  skipped_byte=0,target=0x489c2)])
            padding = None
        scripts.append(dict(id='activation-animation-%06x' % start,source_cpu_address=start,
                            source_rom_offset=start,end_exclusive=end,size=end-start,
                            payload_sha256=sha(program[start:end]),commands=commands,padding=padding))
    table = program[0x48a12:0x48e12]
    rows = [dict(id='activation-object-byte-lookup:%03d' % index,index=index,
                 cpu_address=0x48a12+index*4,rom_offset=0x48a12+index*4,
                 raw=table[index*4:index*4+4].hex(),value=int.from_bytes(table[index*4:index*4+4],'big'))
            for index in range(256)]
    references = {}
    for value in (0x48980,0x489c2,0x48a12):
        needle = value.to_bytes(4,'big'); at = 0; hits = []
        while True:
            at = program.find(needle,at)
            if at < 0: break
            hits.append(at); at += 1
        references['%06x' % value] = dict(raw_BE32_occurrences=hits,
            scope='Byte occurrences only; decoded listed callers separately checked, no complete reference or reachability claim')
    return dict(source=source,inputs={'tools/inspect_activation_animation_scripts.py':sha(Path(__file__).read_bytes()),
                                     'tools/disassemble_program.py':sha(Path(__file__).with_name('disassemble_program.py').read_bytes())},
                callers=callers,scripts=scripts,raw_BE32_references=references,
                raw_lookup=dict(source_cpu_address=0x48a12,source_rom_offset=0x48a12,end_exclusive=0x48e12,
                    size=1024,payload_sha256=sha(table),index_domain='all BYTE values0..255; MOVEQ0,MOVE.B,two ADD.W, MOVE.L indexedD0.W',
                    rows=rows),
                program_unchanged=True,native_execution_performed=False,Cpp_comparison_performed=False,
                scope='Static checked bytes and established command formats only. No compositions extracted; live group unresolved for489c2; no natural reachability claim.')


def main():
    root = Path(__file__).resolve().parents[1]
    program,source = load_verified_program(root)
    report = inspect(program,source)
    if sha((root/source['path']).read_bytes()) != source['sha256']:
        raise ValueError('Source changed during inspection')
    destination = root/'artifacts/activation_animation_static'
    destination.mkdir(parents=True,exist_ok=True)
    output = destination/'inventory.json'
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(report=str(output.relative_to(root)),sha256=sha(output.read_bytes()),
                         scripts=2,draw_commands=17,raw_LONG_reads=256)))


if __name__ == '__main__':
    main()
