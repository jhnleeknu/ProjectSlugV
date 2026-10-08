"""Pack reviewed raw control read windows as existing MS5D v1 kind1."""
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
CONTRACT = 'docs/analysis/animation-control-resource-spans.md'
OPERAND_BASES = (0x6431a,0x6432e,0x64342,0x64356,0x6436a,0x643ae,0x643f2,0x64436)
SPECS = (
    dict(cpu=0x4276c,end=0x5276c,file='control_04276c.ms5d',id='animation-control-selector-and-dispatch',
         crc32=0xe902dbdc,payload_sha256='00fd4b3f850678709eb4da84d61addd145491b9a6f0afc5637b8bd273ad32bd4',
         container_sha256='0e110324fa9a7d039c91f3c9a44b11a9ea60e0bbd7a73376166f91983beef0c2'),
    dict(cpu=0x6431a,end=0x64836,file='operands_06431a.ms5d',id='animation-control-known-operand-byte-union',
         crc32=0xd614ec87,payload_sha256='a76fce25d6879fa72a1f6eb8b44266c31ec83d3343ad11c875f652ae356e5c5d',
         container_sha256='832681dcfe9f037a2e1fa069c8327b9c1d15a144e5132fbfced8ada668e773b2'),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition,message):
    if not condition:
        raise ValueError(message)


def spec_for(cpu):
    for spec in SPECS:
        if spec['cpu'] == cpu:
            return spec
    raise ValueError('Unknown animation control CPU address')


def validate_payload(payload,spec):
    require(len(payload) == spec['end']-spec['cpu'],'Pinned payload extent differs')
    require(sha(payload) == spec['payload_sha256'],'Pinned payload SHA256 differs')


def wrap(payload,cpu):
    spec = spec_for(cpu)
    payload = bytes(payload)
    validate_payload(payload,spec)
    require(zlib.crc32(payload) == spec['crc32'],'Pinned payload CRC differs')
    packed = struct.pack('<4s7I',b'MS5D',1,1,cpu,cpu,len(payload),zlib.crc32(payload),0)+payload
    require(sha(packed) == spec['container_sha256'],'Pinned container SHA256 differs')
    return packed


def validate_container(packed):
    require(len(packed) >= 32,'Truncated animation control header')
    magic,version,kind,cpu,rom,size,crc,reserved = struct.unpack_from('<4s7I',packed)
    spec = spec_for(cpu)
    require((magic,version,kind,cpu,rom,size,reserved) ==
            (b'MS5D',1,1,spec['cpu'],spec['cpu'],spec['end']-spec['cpu'],0),
            'Invalid animation control header')
    require(len(packed) == 32+size,'Animation control container length differs')
    payload = bytes(packed[32:])
    require(zlib.crc32(payload) == crc,'Animation control CRC mismatch')
    validate_payload(payload,spec)
    require(crc == spec['crc32'] and sha(packed) == spec['container_sha256'],
            'Pinned container CRC or SHA256 differs')
    return payload


def roles(spec):
    if spec['cpu'] == 0x4276c:
        return [dict(id='animation-control-opcode0c-field-selector',opcode=0x0c,
            source_cpu_address=0x4a76c,source_rom_offset=0x4a76c,
            read_size=2,byte_order='big',selector_bits=16,selector_count=65536,
            distinct_read_positions=32768,signed_offset_min=-32768,signed_offset_max=32766,
            raw_span_start=0x4276c,raw_span_end_exclusive=0x5276c,
            formula='4a76c + sign16((selector*2)&ffff)',
            alias_rule='selector and selector+8000 modulo65536 read the same WORD'),
            dict(id='animation-control-opcode14-callback-dispatch',opcode=0x14,
            source_cpu_address=0x4a500,source_rom_offset=0x4a500,
            read_size=4,byte_order='big',selector_bits=8,selector_count=256,
            stride=4,raw_span_start=0x4a500,raw_span_end_exclusive=0x4a900,
            formula='4a500 + zero_extended_BYTE*4',
            scope='Raw callback dispatch bytes; not256 supported function pointers')]
    return [dict(id='animation-control-known-callback-operand:%02d'%i,
                 source_cpu_address=base,source_rom_offset=base,read_size=4,byte_order='big',
                 index_bits=8,index_count=256,stride=4,raw_span_start=base,
                 raw_span_end_exclusive=base+1024,
                 known_callback_selector=0x1e if i<4 else 0x1d,
                 scope='Full BYTE-domain LONG reads for this known script operand, not a logical table extent')
            for i,base in enumerate(OPERAND_BASES)]


def build(root):
    program,source = load_verified_program(root)
    require(source.get('sha256') == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical source')
    require(source.get('size') == len(program) and source.get('byte_order') == 'big',
            'Canonical source metadata differs')
    names = ('tools/pack_animation_control.py','tools/disassemble_program.py',CONTRACT)
    inputs = {name:sha((root/name).read_bytes()) for name in names}
    files = {}
    resources = []
    previous_end = 0
    for spec in SPECS:
        require(0 <= spec['cpu'] < spec['end'] <= 0x100000 and spec['cpu'] >= previous_end,
                'Raw fixed windows must be complete and nonoverlapping')
        previous_end = spec['end']
        payload = bytes(program[spec['cpu']:spec['end']])
        packed = wrap(payload,spec['cpu'])
        require(validate_container(packed) == payload,'Packed payload differs from source')
        files[spec['file']] = packed
        resources.append(dict(id=spec['id'],file=spec['file'],format='MS5D',version=1,kind=1,
            source_cpu_address=spec['cpu'],source_rom_offset=spec['cpu'],
            end_cpu_address_exclusive=spec['end'],end_rom_offset_exclusive=spec['end'],
            size=len(packed),payload_size=len(payload),payload_crc32=zlib.crc32(payload),
            payload_sha256=sha(payload),sha256=sha(packed),roles=roles(spec),
            scope='Immutable raw read window; includes bytes of other data/code, not a logical table or natural-use claim'))
    manifest = dict(schema_version=1,id='animation-control',source=source,
        provenance=dict(contract=CONTRACT,mapping='Fixed CPU address equals canonical BE ROM file offset',inputs=inputs),
        counts=dict(resources=2,total_payload_bytes=sum(r['payload_size'] for r in resources),
                    total_container_bytes=sum(r['size'] for r in resources),
                    opcode0c_selector_inputs=65536,opcode0c_distinct_word_positions=32768,
                    opcode14_callback_positions=256,known_operand_bases=8),
        resources=resources,
        scope='Nonoverlapping raw windows for full0c signed-WORD selector and14 BYTE dispatch, plus eight known operand BYTE domains. '
              'No logical table, arbitrary callback support, natural reachability or C++ consumption claim.')
    files['manifest.json'] = (json.dumps(manifest,indent=2)+'\n').encode()
    fresh,fresh_source = load_verified_program(root)
    require(fresh == program and fresh_source == source,'Canonical source changed during packing')
    require(all(sha((root/name).read_bytes()) == digest for name,digest in inputs.items()),
            'Provenance input changed during packing')
    return files,manifest


def main():
    root = Path(__file__).resolve().parents[1]
    files,manifest = build(root)
    output = root/'extracted/runtime/animation_control'
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as staging:
        staging = Path(staging)
        for name,data in files.items():
            (staging/name).write_bytes(data)
        for spec in SPECS:
            validate_container((staging/spec['file']).read_bytes())
        require(json.loads((staging/'manifest.json').read_text()) == manifest,'Staged metadata differs')
        for name in files:
            (staging/name).replace(output/name)
    require(all((output/name).read_bytes() == data for name,data in files.items()),'Published files differ')
    print(json.dumps(dict(counts=manifest['counts'],manifest_sha256=sha(files['manifest.json']),
        resources=[dict(file=s['file'],payload_sha256=s['payload_sha256'],sha256=s['container_sha256'],crc32=s['crc32']) for s in SPECS])))


if __name__ == '__main__':
    main()
