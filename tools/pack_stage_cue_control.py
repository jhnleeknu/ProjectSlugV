"""Pack exact confirmed default cue/control data as fixed MS5D v1 windows."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import zlib

try:
    from .disassemble_program import load_verified_program
    from .pack_scene_scripts import SOURCE_SHA256
except ImportError:
    from disassemble_program import load_verified_program
    from pack_scene_scripts import SOURCE_SHA256

CONTRACT = 'docs/analysis/stage-cue-frame.md'
RESOURCES = (
    ('default_cue.ms5d',0xe89e4,bytes.fromhex('0000000003000000'),'default_cue'),
    ('default_stream.ms5d',0xe89ec,bytes.fromhex('00000000006001000308000bffff'),'default_stream'))
RAW_BY_CPU = {cpu:raw for name,cpu,raw,role in RESOURCES}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition,message):
    if not condition:
        raise ValueError(message)


def wrap(payload,cpu):
    require(cpu in RAW_BY_CPU and payload == RAW_BY_CPU[cpu],
            'Cue control requires the exact confirmed source address and bytes')
    return struct.pack('<4s7I',b'MS5D',1,1,cpu,cpu,len(payload),zlib.crc32(payload),0)+payload


def validate_container(packed,cpu):
    require(cpu in RAW_BY_CPU,'Unsupported default cue control resource address')
    raw = RAW_BY_CPU[cpu]
    require(len(packed)==32+len(raw),'Default cue control container length mismatch')
    require(struct.unpack('<4s7I',packed[:32]) ==
            (b'MS5D',1,1,cpu,cpu,len(raw),zlib.crc32(raw),0),
            'Default cue control header, mapping, size, CRC or reserved mismatch')
    payload = packed[32:]
    require(payload == raw and wrap(payload,cpu)==packed,
            'Default cue control payload or canonical container mismatch')
    return payload


def build(root):
    program,source = load_verified_program(root)
    require(source['sha256']==SOURCE_SHA256 and sha(program)==SOURCE_SHA256,
            'Unsupported canonical original source')
    files,resources = {},[]
    for name,cpu,raw,role in RESOURCES:
        payload = bytes(program[cpu:cpu+len(raw)])
        require(payload==raw,'Original default cue control bytes differ from confirmed source')
        packed = wrap(payload,cpu)
        require(validate_container(packed,cpu)==program[cpu:cpu+len(raw)],
                'Packed default cue control bytes differ from original source')
        metadata = dict(id='stage-cue-control:'+role,file=name,role=role,
            format='MS5D',version=1,kind=1,source_cpu_address=cpu,source_rom_offset=cpu,
            end_cpu_address_exclusive=cpu+len(raw),end_rom_offset_exclusive=cpu+len(raw),
            size=len(packed),payload_size=len(payload),payload_crc32=zlib.crc32(payload),
            sha256=sha(packed),payload_sha256=sha(payload),raw_hex=payload.hex(),
            provenance=dict(confirmed_contract=CONTRACT,
                source_mapping='Fixed first1MiB CPU address equals canonical program ROM offset'))
        if role=='default_stream':
            require(payload[-2:]==b'\xff\xff' and len(payload)==14,'Default stream terminal WORD changed')
            metadata.update(record_bytes=12,terminal_word=0xffff,terminal_word_cpu_address=cpu+12,
                terminal_word_rom_offset=cpu+12,
                scope='Exact default stream12-byte record plus terminal WORD; no surrounding bytes included.')
        else:
            metadata['scope']='Exact confirmed eight-byte default cue DATA; no surrounding code/data extent claim.'
        files[name]=packed;resources.append(metadata)
    counts = dict(resources=len(resources),total_payload_bytes=sum(r['payload_size'] for r in resources),
                  total_container_bytes=sum(r['size'] for r in resources))
    require(counts==dict(resources=2,total_payload_bytes=22,total_container_bytes=86),
            'Default cue control resource counts changed')
    manifest = dict(schema_version=1,id='stage-cue-control',format='MS5D',version=1,
        source=source,counts=counts,resources=resources,
        scope='Only two exact confirmed default DATA windows. The default stream is12-byte record plus terminal WORD; no runtime/callee/reachability or larger resource extent claim.')
    files['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    fresh,fresh_source = load_verified_program(root)
    require(fresh==program and fresh_source==source,'Canonical source changed during packing')
    return files,manifest


def main():
    root = Path(__file__).resolve().parents[1]
    files,manifest = build(root)
    output = root/'extracted/runtime/stage_cue_control'
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as staging:
        staging = Path(staging)
        for name,data in files.items():
            (staging/name).write_bytes(data)
        for name,cpu,raw,role in RESOURCES:
            validate_container((staging/name).read_bytes(),cpu)
            (staging/name).replace(output/name)
        (staging/'manifest.json').replace(output/'manifest.json')
    for name,data in files.items():
        require((output/name).read_bytes()==data,'Published bytes differ from staged resource')
    require(json.loads((output/'manifest.json').read_text())==manifest,
            'Published manifest metadata differs from regenerated metadata')
    print(json.dumps(dict(counts=manifest['counts'],manifest_sha256=sha(files['manifest.json']),
        resources=[dict(file=r['file'],sha256=r['sha256'],payload_crc32=r['payload_crc32']) for r in manifest['resources']])))


if __name__=='__main__':main()
