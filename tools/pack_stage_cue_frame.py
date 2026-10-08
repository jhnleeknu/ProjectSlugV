"""Pack verified cue prefixes and the exact raw indexed cue-frame lookup window."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import zlib

try:
    from .disassemble_program import load_verified_program
    from .inventory_stage_cue_frame import inventory, SOURCE_SHA256
    from .pack_stage_cue_control import build as default_build
except ImportError:
    from disassemble_program import load_verified_program
    from inventory_stage_cue_frame import inventory, SOURCE_SHA256
    from pack_stage_cue_control import build as default_build

LOOKUP_CPU, LOOKUP_SIZE = 0xe8a0c, 128
CONTRACT = 'docs/analysis/stage-cue-frame.md'
LOOKUP_SCOPE = ('Exact128-byte raw addressable window for index0..31 atbase+index*4, two WORD reads. '
    'Only the first16 bytes are separately confirmed DATA; later bytes include original code. '
    'This is not a claim of32 logical records, larger logical table extent or natural index reachability.')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition,message):
    if not condition:
        raise ValueError(message)


def wrap(payload,cpu):
    require(isinstance(cpu,int) and cpu >= 0 and cpu%2==0 and payload
            and cpu+len(payload) <= 0x100000,
            'Resource must be a nonempty even-addressed fixed-ROM span')
    return struct.pack('<4s7I',b'MS5D',1,1,cpu,cpu,len(payload),zlib.crc32(payload),0)+payload


def validate_container(packed,cpu,payload_size=None):
    require(len(packed)>=32,'Truncated MS5D header')
    magic,version,kind,c,r,size,crc,reserved = struct.unpack('<4s7I',packed[:32])
    require((magic,version,kind,c,r,reserved)==(b'MS5D',1,1,cpu,cpu,0)
            and size==len(packed)-32 and (payload_size is None or size==payload_size),
            'MS5D identity, mapping, size or reserved mismatch')
    payload = packed[32:]
    require(zlib.crc32(payload)==crc,'MS5D payload CRC mismatch')
    require(wrap(payload,cpu)==packed,'Noncanonical fixed MS5D container')
    return payload


def overlaps(resources):
    result=[]
    for i,left in enumerate(resources):
        for right in resources[i+1:]:
            start=max(left['source_cpu_address'],right['source_cpu_address'])
            end=min(left['end_cpu_address_exclusive'],right['end_cpu_address_exclusive'])
            if start < end:
                result.append(dict(left_id=left['id'],right_id=right['id'],
                    start_cpu_address=start,end_cpu_address_exclusive=end))
    return result


def build(root):
    # Regenerate source/catalog evidence in memory; cached JSON is only a
    # reproducibility comparison and never the source of resource definitions.
    report = inventory(root)
    regenerated = (json.dumps(report,indent=2)+'\n').encode()
    inventory_path = root/'artifacts/stage_cue_frame_inventory.json'
    require(inventory_path.read_bytes()==regenerated,'Existing cue-frame inventory differs from regenerated source evidence')
    program,source = load_verified_program(root)
    require(source==report['source'] and source['sha256']==SOURCE_SHA256 and sha(program)==SOURCE_SHA256,
            'Canonical cue-frame inventory/source mismatch')
    catalog = report['catalog_cue_pointer_inventory']
    require(catalog['distinct_nonnull_roots']==42 and catalog['record_count']==59,
            'Canonical catalog cue counts changed')
    default_files,default_manifest = default_build(root)
    reused=[]
    for name,data in default_files.items():
        path=root/'extracted/runtime/stage_cue_control'/name
        require(path.read_bytes()==data,'Existing default cue/stream resources differ from original source')
        reused.append(dict(file=str(path.relative_to(root)),sha256=sha(data)))
    files,resources={},[]
    def add(name,cpu,payload,role,references,scope,**extra):
        require(name not in files and payload==program[cpu:cpu+len(payload)],'Duplicate resource or source payload mismatch')
        packed=wrap(payload,cpu)
        require(validate_container(packed,cpu,len(payload))==payload,'Packed bytes/source mismatch')
        metadata=dict(id='stage-cue-frame:'+role+':%06x'%cpu,file=name,role=role,
            format='MS5D',version=1,kind=1,source_cpu_address=cpu,source_rom_offset=cpu,
            end_cpu_address_exclusive=cpu+len(payload),end_rom_offset_exclusive=cpu+len(payload),
            payload_size=len(payload),size=len(packed),payload_crc32=zlib.crc32(payload),
            sha256=sha(packed),payload_sha256=sha(payload),references=references,
            provenance=dict(confirmed_contract=CONTRACT,source_mapping='Fixed first1MiB CPU address equals original ROM offset'),scope=scope)
        metadata.update(extra)
        resources.append(metadata);files[name]=packed
    seen=set()
    for item in catalog['roots']:
        cpu=item['cpu_address']
        require(cpu not in seen and cpu!=0 and item['rom_offset']==cpu and item['byte_count']==8
            and item['end_cpu_address_exclusive']==cpu+8,'Cue root prefix identity mismatch')
        seen.add(cpu)
        payload=bytes(program[cpu:cpu+8])
        require(payload.hex()==item['raw_hex'] and sha(payload)==item['raw_sha256'],'Cue prefix differs from inventory/source')
        refs=[dict(group=r['group'],area=r['area'],record_cpu_address=r['record_cpu_address'],
            record_rom_offset=r['record_rom_offset'],cue_pointer_field_offset=6,
            cue_pointer_field_cpu_address=r['cue_pointer_field_cpu_address'],
            cue_pointer_field_rom_offset=r['cue_pointer_field_rom_offset'],cue_pointer_raw_hex=r['cue_pointer_raw_hex'])
            for r in catalog['records'] if r['cue_pointer_long']==cpu]
        require(refs and len(refs)==len(item['references']),'Cue prefix catalog reference mismatch')
        add('cue_%06x.ms5d'%cpu,cpu,payload,'cue_prefix',refs,
            'Exact first8 bytes of a distinct nonnull catalog LONG+6 root; no larger logical resource extent inferred.')
    lookup=bytes(program[LOOKUP_CPU:LOOKUP_CPU+LOOKUP_SIZE])
    data=next(r for r in report['data_regions'] if r['start_cpu_address']==LOOKUP_CPU)
    require(data['byte_count']==16 and lookup[:16].hex()==data['raw_hex'],
            'Raw lookup first16 confirmed DATA bytes mismatch')
    add('indexed_lookup.ms5d',LOOKUP_CPU,lookup,'indexed_lookup',[],LOOKUP_SCOPE,
        index_range=[0,31],stride_bytes=4,reads_per_index=2,read_width_bytes=2,
        separately_confirmed_data_prefix_bytes=16,
        separately_confirmed_data_prefix_sha256=sha(lookup[:16]),
        final_read_cpu_address=LOOKUP_CPU+31*4+2,
        final_read_rom_offset=LOOKUP_CPU+31*4+2)
    collisions=overlaps(resources)
    require(not collisions,'Unexpected overlap among cue prefix/raw lookup resources')
    counts=dict(resources=len(resources),cue_prefixes=len(seen),indexed_lookups=1,
        catalog_records=catalog['record_count'],nonnull_catalog_references=catalog['nonnull_pointer_records'],
        total_payload_bytes=sum(r['payload_size'] for r in resources),
        total_container_bytes=sum(r['size'] for r in resources),overlaps=len(collisions))
    require((counts['resources'],counts['cue_prefixes'],counts['total_payload_bytes'],counts['total_container_bytes'])
        ==(43,42,464,1840),'Cue-frame canonical resource counts changed')
    manifest=dict(schema_version=1,id='stage-cue-frame',format='MS5D',version=1,source=source,
        counts=counts,resources=resources,overlaps=collisions,
        regenerated_inventory_sha256=sha(regenerated),
        inventory_file=str(inventory_path.relative_to(root)),
        stage_catalog_manifest_sha256=catalog['stage_catalog_manifest_sha256'],
        reused_default_resources=reused,
        null_catalog_references=[dict(group=r['group'],area=r['area'],record_cpu_address=r['record_cpu_address'],
            record_rom_offset=r['record_rom_offset']) for r in catalog['records'] if r['null_pointer']],
        scope='42 distinct nonnull catalog cue roots retain only first8 bytes and all53 catalog references. '
              'Separate128-byte raw indexed lookup includes code after first16 DATA bytes, not32 logical records. '
              'Existing stage_cue_control defaults are verified and reused without duplication. No runtime/callback closure or natural reachability claim.')
    files['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    for item in reused:require(sha((root/item['file']).read_bytes())==item['sha256'],'Reused default resource changed')
    require(inventory_path.read_bytes()==regenerated,'Inventory changed while packing')
    fresh,fresh_source=load_verified_program(root)
    require(fresh==program and fresh_source==source,'Original source changed during packing')
    return files,manifest


def main():
    root=Path(__file__).resolve().parents[1]
    files,manifest=build(root)
    output=root/'extracted/runtime/stage_cue_frame';output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        staging=Path(directory)
        for name,data in files.items():(staging/name).write_bytes(data)
        for item in manifest['resources']:
            name=item['file'];validate_container((staging/name).read_bytes(),item['source_cpu_address'],item['payload_size'])
            (staging/name).replace(output/name)
        (staging/'manifest.json').replace(output/'manifest.json')
    for name,data in files.items():require((output/name).read_bytes()==data,'Published file differs from staged bytes')
    print(json.dumps(dict(counts=manifest['counts'],manifest_sha256=sha(files['manifest.json']),
        regenerated_inventory_sha256=manifest['regenerated_inventory_sha256'])))


if __name__=='__main__':main()
