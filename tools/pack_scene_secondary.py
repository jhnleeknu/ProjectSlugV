"""Pack only union-covered bank2 secondary bytes as existing MS5D v1 kind2."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import zlib
from disassemble_program import load_verified_program
from inventory_scene_secondary import inventory


def sha(data):return hashlib.sha256(data).hexdigest()


def merge_intervals(intervals):
    ordered=sorted(intervals)
    merged=[]
    for start,end in ordered:
        if start&1 or start<0x200000 or end<=start or end>0x2ffff0:raise ValueError('Invalid nonempty bank2 interval')
        if merged and start<=merged[-1][1]:merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
        else:merged.append((start,end))
    return merged


def coverage(report):
    root=report['root'];origins=[dict(kind='root',start=root['cpu_address'],end=root['cpu_address']+4)]
    if report['column_bounds_error_count']:raise ValueError('Secondary candidate bounds errors')
    for row in report['descriptors']:
        base=dict(descriptor_cpu_address=row['descriptor_cpu_address'],secondary_selector_word=row['secondary_selector_word'])
        origins.append(dict(kind='lookup',start=row['lookup_cpu_address'],end=row['lookup_cpu_address']+4,**base))
        candidates=row['column_candidates']
        if candidates['status']=='sentinel':continue
        if candidates['status']!='candidate_windows':raise ValueError('Unsupported secondary candidates')
        origins.append(dict(kind='offset_candidate',start=candidates['offset_candidate_start_cpu_address'],end=candidates['offset_candidate_end_cpu_address_exclusive'],**base))
        for column in candidates['columns']:
            if not column['bounds_valid']:raise ValueError('Invalid cell candidate')
            origins.append(dict(kind='cell_candidate',start=column['cell_start_cpu_address'],end=column['cell_end_cpu_address_exclusive'],column_index=column['column_index'],offset_entry_cpu_address=column['offset_entry_cpu_address'],**base))
    merged=merge_intervals((o['start'],o['end'])for o in origins)
    return merged,origins


def wrap(data,address):
    merge_intervals([(address,address+len(data))])
    return struct.pack('<4s7I',b'MS5D',1,2,address,address,len(data),zlib.crc32(data),0)+data


def validate_container(packed,address):
    if len(packed)<32:raise ValueError('Truncated header')
    magic,version,kind,cpu,rom,size,crc,reserved=struct.unpack('<4s7I',packed[:32]);data=packed[32:]
    if (magic,version,kind,cpu,rom,reserved)!=(b'MS5D',1,2,address,address,0)or size!=len(data):raise ValueError('Header/mapping/length mismatch')
    if zlib.crc32(data)!=crc:raise ValueError('CRC mismatch')
    if wrap(data,address)!=packed:raise ValueError('Invalid container')
    return data


def build(program,report):
    intervals,origins=coverage(report);files={};resources=[]
    for start,end in intervals:
        data=bytes(program[start:end])
        if len(data)!=end-start:raise ValueError('Truncated covered source')
        packed=wrap(data,start);assert validate_container(packed,start)==data
        name='secondary_%06x.ms5d'%start;id='scene-secondary:%08x'%start
        if name in files or any(r['id']==id for r in resources):raise ValueError('Duplicate output identity')
        files[name]=packed
        resources.append(dict(file=name,id=id,format='MS5D',version=1,kind=2,source_cpu_address=start,source_rom_offset=start,end_cpu_address_exclusive=end,end_rom_offset_exclusive=end,size=len(packed),payload_size=len(data),sha256=sha(packed),payload_sha256=sha(data),coverage_origins=[o for o in origins if start<=o['start'] and o['end']<=end]))
    return files,resources


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    input_bytes=(root/'artifacts/scene_paths/inventory.json').read_bytes();report_bytes=(root/'artifacts/scene_secondary/inventory.json').read_bytes();expected=json.loads(report_bytes)
    actual=inventory(program,source,json.loads(input_bytes),input_bytes)
    if actual!=expected:raise ValueError('Secondary inventory differs from source/raw/metadata')
    files,resources=build(program,actual)
    manifest=dict(schema_version=1,id='scene-secondary',format='MS5D',version=1,source=source,inventory_sha256=sha(report_bytes),resources=resources,scope='Bank2 CPU=ROM union of root/knownlookup/descriptor offset and valid cell candidate reads only. Overlap/adjacency merged; uncovered holes omitted. Not a complete logical table/data extent, collision interpretation or execution proof.')
    files['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    output=root/'extracted/runtime/scene_secondary';output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent)as staging:
        staging=Path(staging)
        for name,data in files.items():(staging/name).write_bytes(data)
        for name in sorted(files):(staging/name).replace(output/name)
    print(json.dumps(dict(resources=len(resources),payload_bytes=sum(r['payload_size']for r in resources),manifest_sha256=sha(files['manifest.json']))))

if __name__=='__main__':main()
