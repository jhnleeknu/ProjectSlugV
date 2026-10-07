"""Python-only immutable MS5D bank2 bytes/origin-union verification."""
import hashlib
import json
from pathlib import Path
import struct
import zlib
from disassemble_program import load_verified_program
from inventory_scene_secondary import inventory
from pack_scene_scripts import SOURCE_SHA256


def sha(data):return hashlib.sha256(data).hexdigest()


def union(intervals):
    # Independent endpoint sweep; coverage count must stay positive through each span.
    events={}
    for start,end in intervals:
        if start&1 or start<0x200000 or end<=start or end>0x2ffff0:raise ValueError('Invalid coverage interval')
        events[start]=events.get(start,0)+1;events[end]=events.get(end,0)-1
    output=[];count=0;begin=None
    for address,delta in sorted(events.items()):
        old=count;count+=delta
        if old==0 and count>0:begin=address
        if old>0 and count==0:output.append((begin,address));begin=None
        if count<0:raise ValueError('Invalid sweep balance')
    if count:raise ValueError('Unterminated sweep')
    return output


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    if source['sha256']!=SOURCE_SHA256:raise ValueError('Wrong source')
    folder=root/'extracted/runtime/scene_secondary';manifest_bytes=(folder/'manifest.json').read_bytes();manifest=json.loads(manifest_bytes)
    report_bytes=(root/'artifacts/scene_secondary/inventory.json').read_bytes();report=json.loads(report_bytes)
    pb=(root/'artifacts/scene_paths/inventory.json').read_bytes()
    if inventory(program,source,json.loads(pb),pb)!=report or manifest['source']!=source or manifest['inventory_sha256']!=sha(report_bytes):raise ValueError('Inventory/source identity differs')
    origins=[dict(kind='root',start=report['root']['cpu_address'],end=report['root']['cpu_address']+4)]
    for row in report['descriptors']:
        base=dict(descriptor_cpu_address=row['descriptor_cpu_address'],secondary_selector_word=row['secondary_selector_word'])
        origins.append(dict(kind='lookup',start=row['lookup_cpu_address'],end=row['lookup_cpu_address']+4,**base))
        candidates=row['column_candidates']
        if candidates['status']=='sentinel':continue
        if candidates['errors']:raise ValueError('Candidate errors')
        origins.append(dict(kind='offset_candidate',start=candidates['offset_candidate_start_cpu_address'],end=candidates['offset_candidate_end_cpu_address_exclusive'],**base))
        for column in candidates['columns']:
            if not column['bounds_valid']:raise ValueError('Invalid column')
            origins.append(dict(kind='cell_candidate',start=column['cell_start_cpu_address'],end=column['cell_end_cpu_address_exclusive'],column_index=column['column_index'],offset_entry_cpu_address=column['offset_entry_cpu_address'],**base))
    expected_union=union((o['start'],o['end'])for o in origins);rows=[];actual=[];names=set();ids=set();before={}
    for resource in manifest['resources']:
        name=resource['file'];id=resource['id'];address=resource['source_cpu_address']
        if name in names or id in ids or Path(name).name!=name:raise ValueError('Duplicate/invalid file identity')
        names.add(name);ids.add(id);packed=(folder/name).read_bytes();before[name]=sha(packed)
        if len(packed)<32:raise ValueError('Short header')
        magic,version,kind,cpu,rom,size,crc,reserved=struct.unpack('<4s7I',packed[:32]);payload=packed[32:];end=cpu+size
        if (magic,version,kind,cpu,rom,reserved)!=(b'MS5D',1,2,address,address,0)or not size or len(payload)!=size or zlib.crc32(payload)!=crc:raise ValueError('Header/CRC mismatch')
        if payload!=program[cpu:end]or (resource['source_rom_offset'],resource['end_cpu_address_exclusive'],resource['end_rom_offset_exclusive'],resource['size'],resource['payload_size'],resource['sha256'],resource['payload_sha256'])!=(cpu,end,end,len(packed),size,sha(packed),sha(payload)):raise ValueError('Raw/metadata mismatch')
        if name!='secondary_%06x.ms5d'%cpu or id!='scene-secondary:%08x'%cpu:raise ValueError('Stable identity mismatch')
        expected=[o for o in origins if cpu<=o['start']and o['end']<=end]
        if resource['coverage_origins']!=expected:raise ValueError('Origin metadata mismatch')
        actual.append((cpu,end));rows.append(dict(file=name,cpu_address=cpu,rom_offset=rom,size=size,sha256=sha(packed),payload_sha256=sha(payload),coverage_origin_count=len(expected)))
    if sorted(actual)!=expected_union:raise ValueError('Covered resource intervals include holes/missing/overlap')
    if any(sha((folder/name).read_bytes())!=digest for name,digest in before.items())or (folder/'manifest.json').read_bytes()!=manifest_bytes:raise ValueError('Resources changed during read')
    output=dict(source=source,manifest_sha256=sha(manifest_bytes),inventory_sha256=sha(report_bytes),resource_files=len(rows),payload_bytes=sum(r['size']for r in rows),origin_count=len(origins),union_intervals=[dict(start=a,end_exclusive=b)for a,b in expected_union],all_headers_crc_raw_metadata_and_origin_union_equal=True,resources_unchanged=True,results=rows,scope='Python-only container/source/raw metadata and independently swept coverage union comparison. No added holes. No C++loader/transfer/interpreter effects, collision meaning or natural reachability verification.')
    path=root/'artifacts/scene_secondary/resource_verification.json';path.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(files=len(rows),payload_bytes=output['payload_bytes'],origins=len(origins),report_sha256=sha(path.read_bytes()))))

if __name__=='__main__':main()
