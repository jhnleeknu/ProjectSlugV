"""Compare whole C++ scene updates with uninterrupted native observations."""
import base64,hashlib,json,struct,subprocess,tempfile,zlib
from pathlib import Path
from observe_scene_update import fixture,NAMES,NODES,METADATA,mutate_host,build_cases,RETURN,STACK
from disassemble_program import load_verified_program
from verify_stage_catalog import SOURCE_SHA256

def sha(data):return hashlib.sha256(data).hexdigest()
def main():
 root=Path(__file__).resolve().parents[1];binary=root/'build/step_scene_update';binary_hash=sha(binary.read_bytes())
 observation=root/'artifacts/scene_update/observation.json';observed=observation.read_bytes();native=json.loads(observed);program,source=load_verified_program(root);assert source==native['source'] and source['sha256']==SOURCE_SHA256;assert not native['failure'] and not native['smoke']
 expected_cases=build_cases(program,root);assert len(native['results'])==native['cases']==native['completed_cases']==len(expected_cases)
 for index,(row,expected_case) in enumerate(zip(native['results'],expected_cases)):
  assert row['case_index']==index and row['fixture']==expected_case
  assert row['returned'] and row['final_pc']==RETURN and row['final_registers']['a7']==STACK+4
 dirs=[root/'extracted/runtime/scene_maps',root/'extracted/runtime/scene_secondary',root/'extracted/runtime/scene_debug.ms5d'];sources={str(p.relative_to(root)):sha(p.read_bytes()) for d in dirs for p in (d.glob('*') if d.is_dir() else (d,)) if p.is_file()}
 report=root/'artifacts/scene_update/verification.json'
 rows=[];start_index=0;negative=[];names=NAMES[:13]
 with tempfile.TemporaryDirectory(prefix='scene-map-transfer-') as td:
  folder=Path(td);inp=folder/'input';out=folder/'output';ports=folder/'ports'
  def args(row,values=None):return [str(binary),str(row['fixture']['entry'])]+[str(row['incoming'][k] if values is None else values[k]) for k in names]+[str(inp),str(out),str(ports)]+list(map(str,dirs))
  for row in native['results'][start_index:]:
   c=row['fixture']
   if 'carry_from' in c:
    assert c['carry_from']==row['case_index']-1;ram=mutate_host(bytearray(last_actual_ram),c);values={k:last_parsed[k] for k in names};assert values=={k:row['incoming'][k] for k in names}
   else:ram=fixture(row['case_index'],c);values=None
   assert sha(ram)==row['input_ram_sha256'];expected=bytearray(ram)
   for delta in row['ram_delta']:
    at=delta['ram_offset'];before=bytes.fromhex(delta['before_hex']);after=bytes.fromhex(delta['after_hex']);assert expected[at:at+len(before)]==before;expected[at:at+len(after)]=after
   assert sha(expected)==row['output_ram_sha256'];inp.write_bytes(ram)
   result=subprocess.run(args(row,values),capture_output=True,text=True);assert result.returncode==0,(row['case_index'],result.stderr)
   parsed=json.loads(result.stdout);expected_result={k:row['final_registers'][k] for k in names};expected_result.update(entry=c['entry'],writes=row['port_count'])
   assert parsed==expected_result,(row['case_index'],parsed,expected_result)
   actual=out.read_bytes();assert actual==expected,(row['case_index'],[(i,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b][:12])
   trace=zlib.decompress(base64.b64decode(row['ports_zlib_base64']));assert ports.read_bytes()==trace and sha(trace)==row['ports_sha256'];assert inp.read_bytes()==ram
   last_actual_ram=actual;last_parsed=parsed
   rows.append(dict(case_index=row['case_index'],label=c['label'],entry=c['entry'],actual_cli_carry_from=c.get('carry_from'),writes=parsed['writes'],ram_sha256=sha(actual),ports_sha256=sha(trace)))
  row=native['results'][0];c=row['fixture'];ram=fixture(row['case_index'],c)
  def reject(label,mutate):
   inp.write_bytes(ram);out.write_bytes(b'RAM-output-sentinel');ports.write_bytes(b'port-output-sentinel');command=args(row);mutate(command)
   watched={p:p.read_bytes() for p in (inp,out,ports)};result=subprocess.run(command,capture_output=True,text=True);assert result.returncode!=0,label
   assert all(p.read_bytes()==data for p,data in watched.items()),label;negative.append(dict(label=label,returncode=result.returncode,error=result.stderr.strip()))
  for position in (1,2,10,11,14):
   for value in ('-1','4294967296','0x100000000','0x','1x',''):
    reject('invalid-register-%d-%s'%(position,value),lambda a,p=position,v=value:a.__setitem__(p,v))
  for size in (0,65535,65537):reject('wrong-RAM-size-%d'%size,lambda a,n=size:inp.write_bytes(bytes(n)))
  def late_parent(command,target):
   data=bytearray(inp.read_bytes());struct.pack_into('>I',data,NODES[-1]+0x10,target);inp.write_bytes(data)
  full_row=next(r for r in native['results'] if r['fixture']['label']=='full-canonical-path-on-original-referenced-node')
  row=full_row;c=row['fixture'];ram=fixture(row['case_index'],c)
  for target in (1,0x100001,0x10fff0,0xffffffff):reject('late-last-node-invalid-parent-output-preserved',lambda a,v=target:late_parent(a,v))
  def bad_stream(command):
   data=bytearray(inp.read_bytes());struct.pack_into('>I',data,METADATA[0],0x106000);data[0x6000:0x600a]=struct.pack('>HHHHH',0,0,0,0x20,0xffff);inp.write_bytes(data)
  reject('late-unsupported-RAM-path-output-preserved',bad_stream)
  reject('late-missing-path-resources-after-coordinate-prefix',lambda a:a.__setitem__(slice(18,None),[str(dirs[-1])]))
  for i,j in ((15,16),(15,17),(16,17)):reject('file-alias-%d-%d'%(i,j),lambda a,i=i,j=j:a.__setitem__(j,a[i]))
  empty=folder/'empty';empty.mkdir();reject('missing-resource-windows',lambda a:a.__setitem__(slice(18,None),[str(empty)]))
  malformed=folder/'malformed';malformed.mkdir();(malformed/'bad.ms5d').write_bytes(b'bad');reject('malformed-resource',lambda a:a.__setitem__(slice(18,None),[str(malformed)]))
 assert binary_hash==sha(binary.read_bytes()) and observed==observation.read_bytes()
 assert all(sha((root/p).read_bytes())==h for p,h in sources.items())
 report=root/'artifacts/scene_update/verification.json';report.write_text(json.dumps(dict(native_observation_sha256=sha(observed),execution_method='Fullpositiveandnegativecomparison',binary_sha256=binary_hash,resources_sha256=sources,cases=len(rows),negative_cases=len(negative),ports=sum(r['writes'] for r in rows),results=rows,negative_results=negative,scope='Preserved native continuous whole1afda/1a7a8 observations compared against actual C++ CLI fullRAM,13regs,all ordered9byteMMIO at two native RTS endpoints. Explicitcoordinate/parent/mask/debugcache fixtures and canonicalpathmetadata ontheoriginalnode selector associations are controlled fixtures. No natural mapstreaming, scheduler, or secondaryFFFFFFFF execution claim. Nativeinitialbank2 and PVCdynamic2/3mapping matchC++sourceidentity. Original source/resources immutable. Short sequences carry actualCLI RAM/13regs;host history snapshots anddebugflagchanges areexplicitfixtures,with standaloneentry stack/SR resets only.'),indent=2)+'\n');print(json.dumps(dict(cases=len(rows),negative_cases=len(negative),ports=sum(r['writes'] for r in rows),sha256=sha(report.read_bytes()))))
if __name__=='__main__':main()
