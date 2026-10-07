"""Typed scene path/tilemap C++ loaders against canonical raw source bytes."""
import hashlib,json,struct,subprocess,zlib
from pathlib import Path
from disassemble_program import load_verified_program
from verify_stage_catalog import SOURCE_SHA256
PAYLOAD={0:4,4:12,8:12,12:12,16:12,20:12,24:6,28:4}

def sha(data):return hashlib.sha256(data).hexdigest()
def main():
 root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
 resources=root/'extracted/runtime/scene_maps';manifest_path=resources/'manifest.json';manifest_bytes=manifest_path.read_bytes();manifest=json.loads(manifest_bytes);assert manifest['source']==source and manifest['schema_version']==1 and manifest['format']=='MS5D' and manifest['version']==1 and len(manifest['resources'])==151
 folder=root/'artifacts/scene_map_resources';folder.mkdir(parents=True,exist_ok=True);report=folder/'verification.json';report.unlink(missing_ok=True)
 exe_path=root/'build/inspect_scene_path';exe_map=root/'build/inspect_scene_tilemap';binaries={p.name:sha(p.read_bytes()) for p in (exe_path,exe_map)}
 raw_resources=[];path_rows=[];map_rows=[];negatives=[];decoded={};maps={};unique={};cells=0
 for item in manifest['resources']:
  path=resources/item['file'];raw=path.read_bytes();assert len(raw)==item['size'] and sha(raw)==item['sha256'];h=struct.unpack('<4s7I',raw[:32]);payload=raw[32:]
  expected=(b'MS5D',1,item['kind'],item['source_cpu_address'],item['source_rom_offset'],item['payload_size'],zlib.crc32(payload)&0xffffffff,0);assert h==expected and len(payload)==h[5] and sha(payload)==item['payload_sha256'] and payload==program[h[4]:h[4]+h[5]]
  assert item['end_cpu_address_exclusive']==h[3]+h[5] and item['end_rom_offset_exclusive']==h[4]+h[5]
  if h[2]==1:assert h[3]==h[4] and h[3]%2==0 and h[3]+h[5]<=0x100000
  else:assert h[2]==2 and h[4]==h[3]+0x100000 and h[3]%2==0 and 0x200000<=h[3] and h[3]+h[5]<=0x2ffff0
  raw_resources.append(dict(file=path.name,kind=h[2],cpu=h[3],rom=h[4],payload_size=h[5],container_sha256=sha(raw),payload_sha256=sha(payload),crc32=h[6]))
  decoded[path.name]=(h,payload)
  if path.name.startswith('path_'):
   commands=[];cursor=0;terminal=None
   while cursor<len(payload):
    opcode=struct.unpack_from('>H',payload,cursor)[0]
    if opcode&0x8000:terminal=(h[3]+cursor,opcode);assert cursor+2==len(payload);break
    assert opcode in PAYLOAD and cursor+2+PAYLOAD[opcode]<=len(payload)
    end=cursor+2+PAYLOAD[opcode];commands.append(dict(source_cpu_address=h[3]+cursor,next_cpu_address=h[3]+end,opcode=opcode,operand_hex=payload[cursor+2:end].hex()));cursor=end
   assert terminal is not None
   result=subprocess.run([str(exe_path),str(path)],capture_output=True,text=True);assert result.returncode==0,(path.name,result.stderr);parsed=json.loads(result.stdout)
   expected_json=dict(source_cpu_address=h[3],source_rom_offset=h[4],commands=commands,terminal_cpu_address=terminal[0],terminal_opcode=terminal[1]);assert parsed==expected_json
   reassembled=b''.join(struct.pack('>H',c['opcode'])+bytes.fromhex(c['operand_hex']) for c in parsed['commands'])+struct.pack('>H',parsed['terminal_opcode']);assert reassembled==payload
   for command in commands:unique[command['source_cpu_address']]=struct.pack('>H',command['opcode'])+bytes.fromhex(command['operand_hex'])
   unique[terminal[0]]=struct.pack('>H',terminal[1]);path_rows.append(dict(file=path.name,decoded=parsed,reassembled_sha256=sha(reassembled),all_bytes_equal=True))
  elif path.name.startswith('tilemap_'):
   width,height=struct.unpack_from('>HH',payload);assert width==item['width'] and height==item['height'] and width and height and len(payload)==4+width*height*4
   result=subprocess.run([str(exe_map),str(path)],capture_output=True,text=True);assert result.returncode==0,(path.name,result.stderr);parsed=json.loads(result.stdout)
   assert {k:parsed[k] for k in ('source_cpu_address','source_rom_offset','width','height')}==dict(source_cpu_address=h[3],source_rom_offset=h[4],width=width,height=height) and len(parsed['cells'])==width*height
   words=[]
   for index,cell in enumerate(parsed['cells']):
    column,row=divmod(index,height);offset=4+index*4;word0,word1=struct.unpack_from('>HH',payload,offset);assert cell==[column,row,h[3]+offset,h[4]+offset,word0,word1],(path.name,index,cell)
    assert struct.pack('>HH',cell[4],cell[5])==program[cell[3]:cell[3]+4];words.append(struct.pack('>HH',cell[4],cell[5]))
   reassembled=struct.pack('>HH',parsed['width'],parsed['height'])+b''.join(words);assert reassembled==payload;cells+=len(parsed['cells']);maps[item['selector_word']]=h[3]
   map_rows.append(dict(file=path.name,width=width,height=height,cells=len(parsed['cells']),cpp_json_sha256=sha(result.stdout.encode()),reassembled_sha256=sha(reassembled),all_column_row_cpu_rom_be16_cells_equal=True))
 assert len(path_rows)==72 and len(map_rows)==77 and cells==190707 and len(unique)==218
 paths_inventory=json.loads((root/'artifacts/scene_paths/inventory.json').read_text());inventory_rows={row['cpu_address']:bytes.fromhex(row['raw_hex']) for path in paths_inventory['paths'] for row in path['rows']};assert unique==inventory_rows
 root_h,root_data=decoded['primary_root.ms5d'];lookup_h,lookup_data=decoded['primary_lookup.ms5d'];assert struct.unpack('>I',root_data)[0]==lookup_h[3] and len(lookup_data)==308
 for selector,address in enumerate(struct.unpack('>77I',lookup_data)):assert maps[selector]==address
 for name,path in [('paths',root/'artifacts/scene_paths/inventory.json'),('tilemaps',root/'artifacts/scene_tilemaps/inventory.json')]:assert sha(path.read_bytes())==manifest['inventory_sha256'][name]
 temp=folder/'invalid.ms5d'
 def reject(exe,data,label):
  temp.write_bytes(data);before=temp.read_bytes();actual=subprocess.run([str(exe),str(temp)],capture_output=True,text=True);assert actual.returncode and not actual.stdout and temp.read_bytes()==before,(label,actual.stdout,actual.stderr);negatives.append(dict(failure=label,read_only_input_preserved=True,stderr=actual.stderr.strip(),handler_execution=False))
 good_path=(resources/path_rows[0]['file']).read_bytes();good_map=(resources/map_rows[0]['file']).read_bytes()
 def changed(raw,payload=None,**fields):
  header=list(struct.unpack('<4s7I',raw[:32]));body=raw[32:] if payload is None else payload
  for key,value in fields.items():header[{'magic':0,'version':1,'kind':2,'cpu':3,'rom':4,'size':5,'crc':6,'reserved':7}[key]]=value
  if payload is not None:header[5]=len(body);header[6]=zlib.crc32(body)&0xffffffff
  return struct.pack('<4s7I',*header)+body
 for exe,good in ((exe_path,good_path),(exe_map,good_map)):
  for length in (0,1,31):reject(exe,good[:length],'truncated-header')
  for field,value in (('magic',b'BAD!'),('version',2),('reserved',1),('size',len(good)),('crc',0)):
   reject(exe,changed(good,**{field:value}),'header-'+field+'-error')
  bad=bytearray(good);bad[-1]^=1;reject(exe,bytes(bad),'payload-crc-error')
  reject(exe,good[:-1],'truncated-payload');reject(exe,good+b'\0','unadvertised-trailing-byte')
 reject(exe_path,changed(good_path,kind=2,cpu=0x200000,rom=0x300000),'path-wrong-kind-valid-banked-mapping')
 reject(exe_map,changed(good_map,kind=1,cpu=0x60000,rom=0x60000),'tilemap-wrong-kind-valid-fixed-mapping')
 reject(exe_map,changed(good_map,rom=struct.unpack_from('<I',good_map,12)[0]),'tilemap-wrong-bank2-mapping')
 reject(exe_map,changed(good_map,cpu=0x2ffff0,rom=0x3ffff0),'tilemap-pvc-tail-span')
 body=good_path[32:]
 reject(exe_path,changed(good_path,payload=struct.pack('>H',0x20)+body[2:]),'unsupported-path-opcode')
 reject(exe_path,changed(good_path,payload=body[:-2]),'missing-path-terminal')
 reject(exe_path,changed(good_path,payload=body[:-2]+b'\0\0'),'positive-word-instead-of-terminal')
 reject(exe_path,changed(good_path,payload=body+b'\0\0'),'data-after-path-terminal')
 reject(exe_path,changed(good_path,payload=b'\0\4\0\0'),'truncated-path-operands')
 body=good_map[32:]
 for width,height in ((0,1),(1,0),(0xffff,0xffff),(1,1)):
  reject(exe_map,changed(good_map,payload=struct.pack('>HH',width,height)+body[4:]),'tilemap-invalid-dimensions-or-extent')
 reject(exe_map,changed(good_map,payload=body[:-1]),'tilemap-truncated-cell-valid-container')
 reject(exe_map,changed(good_map,payload=body+b'\0\0\0\0'),'tilemap-extra-cell-valid-container')
 for exe in (exe_path,exe_map):
  actual=subprocess.run([str(exe)],capture_output=True,text=True);assert actual.returncode and not actual.stdout;negatives.append(dict(failure='missing-cli-path',read_only_input_preserved=True))
 assert manifest_path.read_bytes()==manifest_bytes and all(sha((resources/item['file']).read_bytes())==item['sha256'] for item in manifest['resources']) and all(sha(p.read_bytes())==binaries[p.name] for p in (exe_path,exe_map))
 report.write_text(json.dumps(dict(source=source,manifest_sha256=sha(manifest_bytes),binary_sha256=binaries,resource_files=len(raw_resources),path_files=len(path_rows),path_rows=len(unique),positive_path_rows=sum(not struct.unpack_from('>H',data)[0]&0x8000 for data in unique.values()),terminal_path_rows=sum(bool(struct.unpack_from('>H',data)[0]&0x8000) for data in unique.values()),tilemap_files=len(map_rows),tilemap_cells=cells,negative_cases=len(negatives),resources=raw_resources,path_results=path_rows,tilemap_results=map_rows,negative_results=negatives,all_headers_crc_payload_metadata_cpp_decoding_equal=True,original_source_and_resources_unchanged=True,scope='C++typedMS5D resource reading/decoding only.72fixedkind1 paths reassemble all218rows including146positive/72terminals;77bank3kind2 maps compare every190707 column-major cell,column,row,CPU/ROMaddress,twoBE16words/sourcebytes. Root4/lookup308 independently connect all77mapresources. No183c6/19e64handler execution/effects, hardwareports/naturalreachability/unused-data claim. Negative inputs are temporary copies, CLIs read-only; APIcaller-output atomicity belongs to separate unit tests.'),indent=2)+'\n')
 print(json.dumps(dict(resources=len(raw_resources),paths=len(path_rows),path_rows=len(unique),tilemaps=len(map_rows),cells=cells,negative_cases=len(negatives),sha256=sha(report.read_bytes()))))
if __name__=='__main__':main()
