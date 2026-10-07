"""Pack verified raw scene paths and bank3 tilemap windows as existing MS5D v1."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import zlib
from disassemble_program import load_verified_program
from pack_scene_scripts import SOURCE_SHA256
from inventory_scene_paths import walk
from inventory_scene_tilemaps import inventory as tile_inventory, rom_offset


def sha(data):return hashlib.sha256(data).hexdigest()


def wrap(payload,cpu,rom,kind):
    if not payload:raise ValueError('Empty MS5D payload')
    if kind==1:
        if cpu!=rom or cpu&1 or cpu<0 or cpu+len(payload)>0x100000:raise ValueError('Invalid fixed mapping')
    elif kind==2:
        if cpu&1 or rom!=cpu+0x100000 or cpu<0x200000 or cpu+len(payload)>0x2ffff0:raise ValueError('Invalid bank3 mapping')
    else:raise ValueError('Unsupported kind')
    return struct.pack('<4s7I',b'MS5D',1,kind,cpu,rom,len(payload),zlib.crc32(payload),0)+payload


def validate_container(packed,cpu,rom,kind):
    if len(packed)<32:raise ValueError('Truncated header')
    magic,version,k,c,r,size,crc,reserved=struct.unpack('<4s7I',packed[:32]);payload=packed[32:]
    if (magic,version,k,c,r,reserved)!=(b'MS5D',1,kind,cpu,rom,0)or size!=len(payload):raise ValueError('Invalid header or length')
    if zlib.crc32(payload)!=crc:raise ValueError('CRC mismatch')
    if wrap(payload,cpu,rom,kind)!=packed:raise ValueError('Mapping mismatch')
    return payload


def path_payload(program,path):
    address=path['root_cpu_address'];actual=walk(program,address)
    expected=dict(path);expected.pop('references',None)
    if actual!=expected or actual['errors']or actual['cycle_edges']:raise ValueError('Path inventory mismatch/error/cycle')
    rows=actual['rows'];cursor=address
    for i,row in enumerate(rows):
        if row['cpu_address']!=cursor:raise ValueError('Path is not contiguous')
        if row['terminal']!=(i==len(rows)-1):raise ValueError('Path terminal extent mismatch')
        cursor+=row['size']
    if not rows or not rows[-1]['terminal']:raise ValueError('Missing path terminal')
    return bytes(program[address:cursor])


def map_payload(program,entry):
    cpu=entry['source_cpu_address'];rom=rom_offset(cpu,4)
    if rom!=entry['source_rom_offset']or rom+4>len(program):raise ValueError('Map source mapping/truncation')
    width,height=struct.unpack_from('>HH',program,rom);size=4+4*width*height
    if not width or not height or (width,height,size)!=(entry['width'],entry['height'],entry['raw_span_size']):raise ValueError('Map dimension/extent mismatch')
    rom_offset(cpu,size)
    payload=bytes(program[rom:rom+size])
    if len(payload)!=size or sha(payload)!=entry['sha256']or entry['end_cpu_address']!=cpu+size or entry['end_rom_offset']!=rom+size:raise ValueError('Map raw extent/hash mismatch')
    return payload


def validate_references(program,paths):
    roots=[p['root_cpu_address']for p in paths['paths']]
    if len(roots)!=len(set(roots)):raise ValueError('Duplicate path roots')
    if set(roots)!={r['pointer_long']for r in paths['references']if r['pointer_long']}:raise ValueError('Root/reference pointer sets differ')
    for ref in paths['references']:
        address=ref['command_cpu_address'];raw=bytes.fromhex(ref['operand_raw_hex'])
        if len(raw)!=6 or program[address+2:address+8]!=raw:raise ValueError('Script reference raw mismatch')
        if struct.unpack('>HI',raw)!=(ref['selector_word'],ref['pointer_long']):raise ValueError('Reference selector/pointer metadata differs')
    for path in paths['paths']:
        if path['references']!=[r for r in paths['references']if r['pointer_long']==path['root_cpu_address']]:raise ValueError('Path references/root pointer mismatch')


def build(program,source,paths,tiles,path_bytes):
    if source['sha256']!=SOURCE_SHA256 or sha(program)!=SOURCE_SHA256:raise ValueError('Unsupported canonical source')
    if paths['source']!=source or paths.get('error_count') or paths.get('cycle_edge_count'):raise ValueError('Invalid path inventory source/status')
    if tile_inventory(program,source,paths,path_bytes)!=tiles:raise ValueError('Tilemap inventory differs from raw source/metadata')
    if len(paths['paths'])!=72 or len(tiles['entries'])!=77:raise ValueError('Unexpected canonical counts')
    validate_references(program,paths)
    files={};metadata=[];ids=set()
    def add(name,id,cpu,rom,kind,payload,extra):
        if name in files or id in ids:raise ValueError('Duplicate resource file/ID')
        ids.add(id)
        packed=wrap(payload,cpu,rom,kind);assert validate_container(packed,cpu,rom,kind)==payload
        files[name]=packed;metadata.append(dict(file=name,id=id,format='MS5D',version=1,kind=kind,source_cpu_address=cpu,source_rom_offset=rom,end_cpu_address_exclusive=cpu+len(payload),end_rom_offset_exclusive=rom+len(payload),size=len(packed),payload_size=len(payload),sha256=sha(packed),payload_sha256=sha(payload),**extra))
    for path in paths['paths']:
        cpu=path['root_cpu_address'];add('path_%06x.ms5d'%cpu,'scene-path:%08x'%cpu,cpu,cpu,1,path_payload(program,path),dict(references=path['references']))
    add('primary_root.ms5d','scene-tilemap-root:00300004',0x200004,0x300004,2,program[0x300004:0x300008],dict(references=['primary lookup base']))
    add('primary_lookup.ms5d','scene-tilemap-lookup:00300008',0x200008,0x300008,2,program[0x300008:0x30013c],dict(entry_count=77,references=['primary selector lookup']))
    for entry in tiles['entries']:
        cpu=entry['source_cpu_address'];rom=entry['source_rom_offset']
        add('tilemap_%06x.ms5d'%cpu,'scene-tilemap:%08x'%rom,cpu,rom,2,map_payload(program,entry),dict(selector_word=entry['selector_word'],width=entry['width'],height=entry['height'],references=entry['references'],known_reference_count=len(entry['references'])))
    return files,metadata


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    path_bytes=(root/'artifacts/scene_paths/inventory.json').read_bytes();tile_bytes=(root/'artifacts/scene_tilemaps/inventory.json').read_bytes()
    files,metadata=build(program,source,json.loads(path_bytes),json.loads(tile_bytes),path_bytes)
    manifest=dict(schema_version=1,id='scene-maps',format='MS5D',version=1,source=source,resources=metadata,inventory_sha256=dict(paths=sha(path_bytes),tilemaps=sha(tile_bytes)),scope='72 contiguous raw path windows and77 bank3 tilemap header/cell windows. No natural reachability/unused-data claim, interpreter completion or secondary bank2 extraction. Kind1 fixed CPU=ROM; kind2 bank3 ROM=CPU+100000, PVC tail excluded.')
    files['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    output=root/'extracted/runtime/scene_maps';output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent)as staging:
        staging=Path(staging)
        for name,data in files.items():(staging/name).write_bytes(data)
        for name in sorted(files):(staging/name).replace(output/name)
    print(json.dumps(dict(resources=len(metadata),payload_bytes=sum(r['payload_size']for r in metadata),manifest_sha256=sha(files['manifest.json']))))

if __name__=='__main__':main()
