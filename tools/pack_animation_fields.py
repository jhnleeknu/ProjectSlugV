"""Pack the caller-backed3e808 field-write loop as existing MS5A v1 kind1."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import zlib

try:
    from .disassemble_program import load_verified_program
except ImportError:
    from disassemble_program import load_verified_program

SOURCE_SHA256 = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
SPEC = dict(cpu=0x3e808, end=0x3e854, file='animation_03e808.ms5a',
    payload_sha256='cbc72554fb13051c10e05639ad8a898472f1e7fde919eeff51b617ae8b7893ad',
    crc32=0x1e1cfb2f,
    container_sha256='806f465a3e2bdeb831fc356350ce3fa18c4b03da6e3dce8a0574d9cc6e0e5bc7')
CALLER = 0x3d2e2
CALLER_RAW = bytes.fromhex('227c0003e808303c01004eb900049f8c')
COMMANDS = ((0x3e808,0x0c),(0x3e810,0x18),(0x3e814,4),(0x3e81c,0),
    (0x3e81e,0x18),(0x3e822,4),(0x3e82a,0),(0x3e82c,8),
    (0x3e832,0x18),(0x3e836,4),(0x3e83e,0),(0x3e840,0x18),
    (0x3e844,4),(0x3e84c,0),(0x3e84e,8))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def validate_payload(payload):
    require(len(payload) == SPEC['end']-SPEC['cpu'], 'Pinned payload extent differs')
    require(sha(payload) == SPEC['payload_sha256'], 'Pinned payload SHA256 differs')
    require(zlib.crc32(payload) == SPEC['crc32'], 'Pinned payload CRC differs')


def wrap(payload):
    payload = bytes(payload)
    validate_payload(payload)
    packed = struct.pack('<4s7I', b'MS5A', 1, 1, SPEC['cpu'], SPEC['cpu'],
                         len(payload), zlib.crc32(payload), 0)+payload
    require(sha(packed) == SPEC['container_sha256'], 'Pinned container SHA256 differs')
    return packed


def validate_container(packed):
    require(len(packed) >= 32, 'Truncated animation field header')
    magic, version, kind, cpu, rom, size, crc, reserved = struct.unpack_from('<4s7I', packed)
    require((magic,version,kind,cpu,rom,size,reserved) ==
        (b'MS5A',1,1,SPEC['cpu'],SPEC['cpu'],SPEC['end']-SPEC['cpu'],0),
        'Invalid animation field header')
    require(len(packed) == 32+size, 'Animation field container length differs')
    payload = bytes(packed[32:])
    require(zlib.crc32(payload) == crc, 'Animation field CRC mismatch')
    validate_payload(payload)
    require(sha(packed) == SPEC['container_sha256'], 'Pinned container SHA256 differs')
    return payload


def extract(program):
    require(program[CALLER:CALLER+len(CALLER_RAW)] == CALLER_RAW, 'Reviewed caller changed')
    cursor = SPEC['cpu']
    rows = []
    for address, opcode in COMMANDS:
        require(cursor == address and program[cursor] == opcode, 'Reviewed command boundary changed')
        row = dict(id='animation-field-%06x-command:%02d' % (SPEC['cpu'],len(rows)),
                   cpu_address=address, rom_offset=address, opcode=opcode)
        if opcode == 0x0c:
            size = 8
            row.update(desired=program[cursor+1],selector=int.from_bytes(program[cursor+2:cursor+4],'big'),
                       target=int.from_bytes(program[cursor+4:cursor+8],'big'))
            require((row['desired'],row['selector'],row['target']) == (255,0x2f,0x3e832),
                    'Reviewed branch changed')
        elif opcode == 0x18:
            size = 4
            row.update(value=program[cursor+1],selector=int.from_bytes(program[cursor+2:cursor+4],'big'))
            require(row['selector'] == 0x34 and row['value'] == (0x35 if cursor<0x3e832 else 0x49),
                    'Reviewed field write changed')
        elif opcode == 4:
            size = 8
            row.update(control=program[cursor+1],x_byte=program[cursor+2],y_byte=program[cursor+3],
                       identifier_operand=int.from_bytes(program[cursor+4:cursor+8],'big'),
                       identifier_binding='Operand OR live object+20; group and palette not bound here')
        elif opcode == 0:
            size = 2
            row['duration'] = program[cursor+1]
            require(row['duration'] == 1, 'Reviewed duration changed')
        else:
            size = 6
            row.update(skipped_byte=program[cursor+1],target=int.from_bytes(program[cursor+2:cursor+6],'big'))
            require(row['target'] == (0x3e810 if cursor<0x3e832 else 0x3e832), 'Reviewed jump changed')
        require(cursor+size <= SPEC['end'], 'Command extends beyond reviewed script')
        row.update(size=size,raw=program[cursor:cursor+size].hex())
        rows.append(row)
        cursor += size
    require(cursor == SPEC['end'], 'Reviewed script extent changed')
    boundaries = {row['cpu_address'] for row in rows}
    require(all(row['target'] in boundaries for row in rows if 'target' in row),
            'Branch/jump target is not a command boundary')
    payload = bytes(program[SPEC['cpu']:SPEC['end']])
    validate_payload(payload)
    return payload, rows


def build(root):
    program, source = load_verified_program(root)
    require(source.get('sha256') == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical source')
    require(source.get('size') == len(program) and source.get('byte_order') == 'big',
            'Canonical source metadata differs')
    names = ('tools/pack_animation_fields.py','tools/disassemble_program.py')
    inputs = {name:sha((root/name).read_bytes()) for name in names}
    payload, commands = extract(program)
    packed = wrap(payload)
    require(validate_container(packed) == payload, 'Packed payload differs from source')
    manifest = dict(schema_version=1,id='animation-fields-03e808',source=source,
        provenance=dict(mapping='Fixed CPU address equals canonical BE ROM file offset',inputs=inputs),
        caller=dict(source_cpu_address=CALLER,source_rom_offset=CALLER,raw=CALLER_RAW.hex(),
                    call_cpu_address=0x3d2ec,initializer=0x49f8c,speed_word=0x100),
        counts=dict(resources=1,commands=len(commands),field_writes=4,draw_commands=4,
                    payload_bytes=len(payload),container_bytes=len(packed)),
        resources=[dict(id='animation-field-script-03e808',file=SPEC['file'],format='MS5A',version=1,kind=1,
            source_cpu_address=SPEC['cpu'],source_rom_offset=SPEC['cpu'],
            end_cpu_address_exclusive=SPEC['end'],end_rom_offset_exclusive=SPEC['end'],
            payload_size=len(payload),size=len(packed),payload_crc32=SPEC['crc32'],
            payload_sha256=SPEC['payload_sha256'],sha256=SPEC['container_sha256'],commands=commands)],
        fixed_data_dependency=dict(file='animation_control/control_04276c.ms5d',
            raw_reads=[dict(opcode=0x0c,selector=0x2f,source_cpu_address=0x4a7ca,source_rom_offset=0x4a7ca,size=2),
                       dict(opcode=0x18,selector=0x34,source_cpu_address=0x4a7d4,source_rom_offset=0x4a7d4,size=2)]),
        scope='Caller-backed complete two-way0c/18/04/00/08 loop. Excludes next script at3e854; no2c/composition-group/palette/naturalgameplay/C++consumption claim.')
    files = {SPEC['file']:packed,'manifest.json':(json.dumps(manifest,indent=2)+'\n').encode()}
    fresh, fresh_source = load_verified_program(root)
    require(fresh == program and fresh_source == source, 'Canonical source changed during packing')
    require(all(sha((root/name).read_bytes()) == value for name,value in inputs.items()),
            'Provenance input changed during packing')
    return files, manifest


def main():
    root = Path(__file__).resolve().parents[1]
    files, manifest = build(root)
    output = root/'extracted/runtime/animation_fields'
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as staging:
        staging = Path(staging)
        for name,data in files.items():
            (staging/name).write_bytes(data)
        validate_container((staging/SPEC['file']).read_bytes())
        require(json.loads((staging/'manifest.json').read_text()) == manifest, 'Staged metadata differs')
        for name in files:
            (staging/name).replace(output/name)
    require(all((output/name).read_bytes() == data for name,data in files.items()), 'Published files differ')
    print(json.dumps(dict(counts=manifest['counts'],manifest_sha256=sha(files['manifest.json']),
                          payload_sha256=SPEC['payload_sha256'],sha256=SPEC['container_sha256'])))


if __name__ == '__main__':
    main()
