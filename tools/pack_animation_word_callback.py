"""Pack the reviewed non-overlapping 3c first-selector prefix and BYTE-index boundary operand windows as MS5D v1 kind1."""
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
CONTRACT = 'docs/analysis/animation-word-callback-contract.md'
OLD_WINDOW = (0x4276c,0x5276c)
SPEC = dict(cpu=0x42500,end=0x4276c,file='prefix_042500.ms5d',id='animation-word-callback-first-selector-prefix',
            crc32=0xca762b48,payload_sha256='d418ddaba698d044f4b0d570a5da75db9869ea074d357650105520295e4477e6',
            container_sha256='3d5d1bd37897a4cfaa69482c01aaf40c06fafb07877be018db7db4f7c9cb0082')
PREFIX_ROLE = 'prefix-dispatch-span'
OPERAND_ROLE = 'boundary-operand-byte-domain'
OPERAND_SPECS = (
    dict(cpu=0x0,end=0x400,file='operands_000000.ms5d',id='animation-word-callback-boundary-operand-000000',
         role=OPERAND_ROLE,crc32=0x23445b12,
         payload_sha256='426d45ab2591a3dfd27ea2c7323dd7a81e5bd0c5c4b2e9c34e51af24c893f4f6',
         container_sha256='b79f39fbba5302aeb07e898ef93d6d5f45a92206f3ea700a741d46b2f0cde2c3'),
    dict(cpu=0xffc00,end=0x100000,file='operands_0ffc00.ms5d',id='animation-word-callback-boundary-operand-0ffc00',
         role=OPERAND_ROLE,crc32=0xefb5af2e,
         payload_sha256='5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef',
         container_sha256='6b50440c0606e84fdc42cf9d4b4922416c8e1412b6eb07fd9e1f772dcf36580d'),
)
SPEC['role'] = PREFIX_ROLE
SPECS = (SPEC,)+OPERAND_SPECS
# Existing resources that the new windows must not duplicate: control_04276c and operands_06431a.
EXISTING_WINDOWS = (OLD_WINDOW,(0x6431a,0x64836))
# Original 3c instructions that justify base+WORD doubling (big-endian bytes at fixed CPU == ROM offset).
EVIDENCE_SPAN = (0x4a30c,0x4a354)
EVIDENCE_SHA256 = '472a949c7068f88f6ff6bc295e5321fad7272e4cf779e61287fd795f90311c6b'
EVIDENCE = (
    (0x4a312,'3019','MOVE.W (A1)+,D0 : first selector WORD, D0.high preserved'),
    (0x4a314,'d040d040','ADD.W D0,D0 twice : 16-bit wrapped selector*4'),
    (0x4a318,'41f90004a500','LEA 4a500.L,A0 : first lookup base'),
    (0x4a31e,'2e300000','MOVE.L (0,A0,D0.W),D7 : sign-extended WORD index, LONG read'),
    (0x4a322,'3019','MOVE.W (A1)+,D0 : second selector WORD'),
    (0x4a324,'d040','ADD.W D0,D0 once : 16-bit wrapped selector*2'),
    (0x4a326,'41f90004a76c','LEA 4a76c.L,A0 : second lookup base'),
    (0x4a32c,'32300000','MOVE.W (0,A0,D0.W),D1 : sign-extended WORD index, WORD read'),
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
    raise ValueError('Unknown animation word callback CPU address')


def validate_payload(payload,spec=None):
    spec = spec or SPECS[0]
    require(len(payload) == spec['end']-spec['cpu'],'Pinned payload extent differs')
    require(sha(payload) == spec['payload_sha256'],'Pinned payload SHA256 differs')


def wrap(payload,cpu=None):
    spec = spec_for(SPECS[0]['cpu'] if cpu is None else cpu)
    cpu = spec['cpu']
    payload = bytes(payload)
    validate_payload(payload,spec)
    require(zlib.crc32(payload) == spec['crc32'],'Pinned payload CRC differs')
    packed = struct.pack('<4s7I',b'MS5D',1,1,cpu,cpu,len(payload),zlib.crc32(payload),0)+payload
    require(sha(packed) == spec['container_sha256'],'Pinned container SHA256 differs')
    return packed


def validate_container(packed,expected_cpu=None):
    require(len(packed) >= 32,'Truncated animation word callback header')
    magic,version,kind,cpu,rom,size,crc,reserved = struct.unpack_from('<4s7I',packed)
    spec = spec_for(cpu)
    require((magic,version,kind,rom,size,reserved) ==
            (b'MS5D',1,1,spec['cpu'],spec['end']-spec['cpu'],0),
            'Invalid animation word callback header')
    require(expected_cpu is None or expected_cpu == spec['cpu'],'Animation word callback container is for a different window')
    require(len(packed) == 32+size,'Animation word callback container length differs')
    payload = bytes(packed[32:])
    require(zlib.crc32(payload) == crc,'Animation word callback CRC mismatch')
    validate_payload(payload,spec)
    require(crc == spec['crc32'] and sha(packed) == spec['container_sha256'],
            'Pinned container CRC or SHA256 differs')
    return payload


def verify_evidence(program):
    require(sha(bytes(program[EVIDENCE_SPAN[0]:EVIDENCE_SPAN[1]])) == EVIDENCE_SHA256,
            'Pinned 3c instruction span SHA256 differs')
    for cpu,hexbytes,_ in EVIDENCE:
        require(bytes(program[cpu:cpu+len(hexbytes)//2]).hex() == hexbytes,'3c instruction evidence differs')


def role(spec=None):
    spec = spec or SPECS[0]
    return [dict(id='animation-word-callback-first-selector-prefix',
        source_cpu_address=0x4a500,source_rom_offset=0x4a500,read_size=4,byte_order='big',
        selector_bits=16,selector_count=65536,distinct_long_slots=16384,selectors_per_slot=4,stride=4,
        signed_offset_min=-32768,signed_offset_max=32764,
        full_raw_span_start=0x42500,full_raw_span_end_exclusive=0x52500,
        raw_span_start=spec['cpu'],raw_span_end_exclusive=spec['end'],
        prefix_long_slots=(spec['end']-spec['cpu'])//4,
        formula='4a500 + sign16((selector*4)&ffff)',
        alias_rule='selector, selector+4000, +8000 and +c000 modulo65536 read the same LONG',
        companion_resource='control_04276c.ms5d',
        companion_raw_span_start=OLD_WINDOW[0],companion_raw_span_end_exclusive=OLD_WINDOW[1],
        second_selector_formula='4a76c + sign16((selector*2)&ffff)',
        second_selector_span_start=OLD_WINDOW[0],second_selector_span_end_exclusive=OLD_WINDOW[1],
        scope='Raw LONG read bytes under all first-selector aliases; not a logical function table, '
              'not supported callback pointers and not a natural reachability claim')]


def operand_role(spec):
    return [dict(id=spec['id'],resource_role=OPERAND_ROLE,read_size=4,byte_order='big',
        index_domain='full BYTE index 0..255 for selector 1d/1e (callee 2b3e8/2b3fa)',index_count=256,stride=4,
        source_formula='(operand_LONG + index*4) & ffffff, LONG read',
        operand_base_cpu_address=spec['cpu'],operand_base_rom_offset=spec['cpu'],
        raw_span_start=spec['cpu'],raw_span_end_exclusive=spec['end'],long_slots=(spec['end']-spec['cpu'])//4,
        semantic_basis=CONTRACT,
        source_kind='controlled native fixture operand; the original operand LONG is chosen by the independent observer',
        natural_use='not a known naturally used logical table; no natural script reference is claimed',
        cartridge_view=('[0,80) uses the canonical cartridge ROM view; BIOS/cart vector selection is not modeled'
                        if spec['cpu'] == 0 else 'canonical cartridge ROM bytes'),
        scope='Raw BYTE-index operand read window for boundary fixtures; not a logical table')]


def check_windows(program):
    require(len(SPECS) == 3 and [s['role'] for s in SPECS] == [PREFIX_ROLE,OPERAND_ROLE,OPERAND_ROLE],
            'Unexpected animation word callback resource set')
    require(len({s['file'] for s in SPECS}) == len(SPECS) and len({s['id'] for s in SPECS}) == len(SPECS),
            'Duplicate animation word callback resource')
    windows = sorted([(s['cpu'],s['end'],s['file']) for s in SPECS]+[(a,b,'existing') for a,b in EXISTING_WINDOWS])
    for spec in SPECS:
        require(0 <= spec['cpu'] < spec['end'] <= len(program),'Window outside canonical source')
    prefix = SPECS[0]
    require(prefix['end'] <= OLD_WINDOW[0],'Prefix must be complete and not overlap the existing control window')
    for spec in SPECS[1:]:
        require(spec['end']-spec['cpu'] == 1024,'Boundary operand window must cover 256 LONGs')
    for (a0,a1,_),(b0,b1,_) in zip(windows,windows[1:]):
        require(a1 <= b0,'Animation word callback windows overlap')
    for spec in SPECS:
        require((spec['end']-spec['cpu']) % 4 == 0,'Window is not a whole number of LONGs')


def build(root):
    program,source = load_verified_program(root)
    require(source.get('sha256') == SOURCE_SHA256 and sha(program) == SOURCE_SHA256,
            'Unsupported canonical source')
    require(source.get('size') == len(program) and source.get('byte_order') == 'big',
            'Canonical source metadata differs')
    check_windows(program)
    verify_evidence(program)
    names = ('tools/pack_animation_word_callback.py','tools/disassemble_program.py',CONTRACT)
    inputs = {name:sha((root/name).read_bytes()) for name in names}
    files = {}
    resources = []
    for spec in SPECS:
        payload = bytes(program[spec['cpu']:spec['end']])
        packed = wrap(payload,spec['cpu'])
        require(validate_container(packed,spec['cpu']) == payload,'Packed payload differs from source')
        is_prefix = spec['role'] == PREFIX_ROLE
        resources.append(dict(id=spec['id'],file=spec['file'],format='MS5D',version=1,kind=1,resource_role=spec['role'],
            source_cpu_address=spec['cpu'],source_rom_offset=spec['cpu'],
            end_cpu_address_exclusive=spec['end'],end_rom_offset_exclusive=spec['end'],
            size=len(packed),payload_size=len(payload),payload_crc32=zlib.crc32(payload),
            payload_sha256=sha(payload),sha256=sha(packed),
            roles=role(spec) if is_prefix else operand_role(spec),
            scope=('Immutable raw read window; includes bytes of other data/code, not a logical table or natural-use claim'
                   if is_prefix else
                   'Immutable raw operand read window for controlled boundary fixtures; includes bytes of other data/code, '
                   'not a logical table or natural-use claim')))
        files[spec['file']] = packed
    prefix_payload = (SPECS[0]['end']-SPECS[0]['cpu'])
    evidence = dict(span_cpu_address=EVIDENCE_SPAN[0],span_end_cpu_address_exclusive=EVIDENCE_SPAN[1],
        span_sha256=EVIDENCE_SHA256,
        instructions=[dict(cpu_address=c,rom_offset=c,bytes=b,meaning=m) for c,b,m in EVIDENCE])
    manifest = dict(schema_version=1,id='animation-word-callback',source=source,
        provenance=dict(contract=CONTRACT,mapping='Fixed CPU address equals canonical BE ROM file offset',
                        inputs=inputs,instruction_evidence=evidence),
        counts=dict(resources=len(resources),total_payload_bytes=sum(r['payload_size'] for r in resources),
                    total_container_bytes=sum(r['size'] for r in resources),
                    first_selector_inputs=65536,first_selector_distinct_long_slots=16384,
                    first_selector_aliases_per_slot=4,prefix_long_slots=prefix_payload//4,
                    prefix_dispatch_span_resources=1,boundary_operand_resources=len(SPECS)-1,
                    boundary_operand_byte_index_count=256,
                    boundary_operand_long_slots_per_window=256),
        resources=resources,
        scope='Nonoverlapping prefix [42500,4276c) of the first 3c WORD selector read span [42500,52500); '
              'the remainder and the whole second selector span [4276c,5276c) come from existing control_04276c.ms5d. '
              'Boundary operand windows [0,400) and [ffc00,100000) cover the full BYTE index*4 LONG domain for controlled '
              'native fixture operands 0 and ffc00; the operand 6431a range reuses the existing operands_06431a.ms5d. '
              'They are not known naturally used logical tables. Window [0,80) is the canonical cartridge ROM view; '
              'BIOS/cart vector selection is not modeled. '
              'No logical function table, arbitrary callback support, natural reachability or C++ consumption claim.')
    files['manifest.json'] = (json.dumps(manifest,indent=2)+'\n').encode()
    fresh,fresh_source = load_verified_program(root)
    require(fresh == program and fresh_source == source,'Canonical source changed during packing')
    require(all(sha((root/name).read_bytes()) == digest for name,digest in inputs.items()),
            'Provenance input changed during packing')
    return files,manifest


def main():
    root = Path(__file__).resolve().parents[1]
    files,manifest = build(root)
    output = root/'extracted/runtime/animation_word_callback'
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as staging:
        staging = Path(staging)
        for name,data in files.items():
            (staging/name).write_bytes(data)
        for spec in SPECS:
            validate_container((staging/spec['file']).read_bytes(),spec['cpu'])
        require(json.loads((staging/'manifest.json').read_text()) == manifest,'Staged metadata differs')
        for name in files:
            (staging/name).replace(output/name)
    require(all((output/name).read_bytes() == data for name,data in files.items()),'Published files differ')
    print(json.dumps(dict(counts=manifest['counts'],manifest_sha256=sha(files['manifest.json']),
        resources=[dict(file=x['file'],payload_sha256=x['payload_sha256'],sha256=x['container_sha256'],crc32=x['crc32'])
                   for x in SPECS])))


if __name__ == '__main__':
    main()
