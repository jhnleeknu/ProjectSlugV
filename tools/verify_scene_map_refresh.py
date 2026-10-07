"""Compare C++ transfer with preserved independent continuous native observations."""
import argparse,base64,copy,hashlib,json,struct,subprocess,tempfile,zlib
from pathlib import Path
from observe_scene_map_refresh import fixture,NAMES
from disassemble_program import load_verified_program

def sha(data):return hashlib.sha256(data).hexdigest()
def validate_previous(previous,native,binary_hash,sources):
 assert previous['binary_sha256']==binary_hash
 assert previous['resources_sha256']==sources
 count=previous['cases'];assert count==len(previous['results']) and 0<=count<=len(native['results'])
 assert native['cases']==len(native['results'])==native['completed_cases'] and not native['smoke'] and not native['failure']
 prefix=copy.deepcopy(native);prefix['results']=prefix['results'][:count];prefix['cases']=count
 prefix['completed_cases']=sum(r['returned'] for r in prefix['results']);prefix['ports']=sum(r['port_count'] for r in prefix['results'])
 assert sha((json.dumps(prefix,indent=2)+'\n').encode())==previous['native_observation_sha256']
 for index,(compared,observed) in enumerate(zip(previous['results'],prefix['results'])):
  assert compared['case_index']==observed['case_index']==index
  assert compared['entry']==observed['fixture']['entry'] and compared['label']==observed['fixture']['label']
  assert compared['ram_sha256']==observed['output_ram_sha256'] and compared['ports_sha256']==observed['ports_sha256']
  assert compared['writes']==observed['port_count']
 assert previous['ports']==sum(r['writes'] for r in previous['results'])

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--additional',action='store_true');options=parser.parse_args()
 root=Path(__file__).resolve().parents[1];binary=root/'build/refresh_scene_map';binary_hash=sha(binary.read_bytes())
 observation=root/'artifacts/scene_map_refresh/observation.json';observed=observation.read_bytes();native=json.loads(observed);program,source=load_verified_program(root);assert source==native['source'];assert not native['failure'] and native['cases']==native['completed_cases']
 dirs=[root/'extracted/runtime/scene_maps',root/'extracted/runtime/scene_secondary'];sources={str(p.relative_to(root)):sha(p.read_bytes()) for d in dirs for p in d.glob('*') if p.is_file()}
 report=root/'artifacts/scene_map_refresh/verification.json';previous=json.loads(report.read_text()) if options.additional else None
 if previous:validate_previous(previous,native,binary_hash,sources)
 rows=previous['results'] if previous else [];start_index=len(rows);negative=[];names=NAMES[:13]
 with tempfile.TemporaryDirectory(prefix='scene-map-transfer-') as td:
  folder=Path(td);inp=folder/'input';out=folder/'output';ports=folder/'ports'
  def args(row):return [str(binary),str(row['fixture']['entry'])]+[str(row['incoming'][k]) for k in names]+[str(inp),str(out),str(ports)]+list(map(str,dirs))
  for row in native['results'][start_index:]:
   c=row['fixture'];ram=fixture(row['case_index'],c)
   assert sha(ram)==row['input_ram_sha256'];expected=bytearray(ram)
   for delta in row['ram_delta']:
    at=delta['ram_offset'];before=bytes.fromhex(delta['before_hex']);after=bytes.fromhex(delta['after_hex']);assert expected[at:at+len(before)]==before;expected[at:at+len(after)]=after
   assert sha(expected)==row['output_ram_sha256'];inp.write_bytes(ram)
   result=subprocess.run(args(row),capture_output=True,text=True);assert result.returncode==0,(row['case_index'],result.stderr)
   parsed=json.loads(result.stdout);expected_result={k:row['final_registers'][k] for k in names};expected_result.update(entry=c['entry'],writes=row['port_count'])
   assert parsed==expected_result,(row['case_index'],parsed,expected_result)
   actual=out.read_bytes();assert actual==expected,(row['case_index'],[(i,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b][:12])
   trace=zlib.decompress(base64.b64decode(row['ports_zlib_base64']));assert ports.read_bytes()==trace and sha(trace)==row['ports_sha256'];assert inp.read_bytes()==ram
   rows.append(dict(case_index=row['case_index'],label=c['label'],entry=c['entry'],writes=parsed['writes'],ram_sha256=sha(actual),ports_sha256=sha(trace)))
  row=native['results'][0];c=row['fixture'];ram=fixture(row['case_index'],c)
  def reject(label,mutate):
   inp.write_bytes(ram);out.write_bytes(b'RAM-output-sentinel');ports.write_bytes(b'port-output-sentinel');command=args(row);mutate(command)
   watched={p:p.read_bytes() for p in (inp,out,ports)};result=subprocess.run(command,capture_output=True,text=True);assert result.returncode!=0,label
   assert all(p.read_bytes()==data for p,data in watched.items()),label;negative.append(dict(label=label,returncode=result.returncode,error=result.stderr.strip()))
  for position in (1,2,10,11):
   for value in ('-1','4294967296','0x100000000','0x','1x',''):
    reject('invalid-register-%d-%s'%(position,value),lambda a,p=position,v=value:a.__setitem__(p,v))
  reject('wrong-RAM-size',lambda a:inp.write_bytes(b'short'))
  for target in (0x0ffffe,0x10fffe,0x109157):reject('invalid-node-%x'%target,lambda a,v=target:a.__setitem__(10,str(v)))
  def invalid_descriptor(command,target):
   command[11]=str(target);data=bytearray(inp.read_bytes());struct.pack_into('>I',data,0x9156+0x2e,target);inp.write_bytes(data)
  for target in (0x100001,0x10fffc):reject('invalid-descriptor-%x'%target,lambda a,v=target:invalid_descriptor(a,v))
  for i,j in ((15,16),(15,17),(16,17)):reject('file-alias-%d-%d'%(i,j),lambda a,i=i,j=j:a.__setitem__(j,a[i]))
  empty=folder/'empty';empty.mkdir();reject('missing-resource-windows',lambda a:a.__setitem__(slice(18,None),[str(empty)]))
  malformed=folder/'malformed';malformed.mkdir();(malformed/'bad.ms5d').write_bytes(b'bad');reject('malformed-resource',lambda a:a.__setitem__(slice(18,None),[str(malformed)]))
 assert binary_hash==sha(binary.read_bytes()) and observed==observation.read_bytes()
 assert all(sha((root/p).read_bytes())==h for p,h in sources.items())
 report=root/'artifacts/scene_map_refresh/verification.json';report.write_text(json.dumps(dict(native_observation_sha256=sha(observed),previous_native_observation_sha256=previous['native_observation_sha256'] if previous else None,execution_method='Preserved previouspositivecomparison rows;onlyappendednativecases compared;negatives rerun' if previous else 'Fullpositiveandnegativecomparison',binary_sha256=binary_hash,resources_sha256=sources,cases=len(rows),negative_cases=len(negative),ports=sum(r['writes'] for r in rows),results=rows,negative_results=negative,scope='Preserved native continuous16f0e/18702/1861a/18656 observations compared against actual C++ CLI fullRAM,13regs,all ordered9byteMMIO at four native RTS endpoints. Canonicalfixed descriptors,explicitworld/origin/wrap/count fixtures and syntheticRAMcolumnrecords are controlled fixtures. No natural mapstreaming, scheduler, or secondaryFFFFFFFF execution claim. Nativeinitialbank2 and PVCdynamic2/3mapping matchC++sourceidentity. Original source/resources immutable. No actual CLI multi-call state carry claimed.'),indent=2)+'\n');print(json.dumps(dict(cases=len(rows),negative_cases=len(negative),ports=sum(r['writes'] for r in rows),sha256=sha(report.read_bytes()))))
if __name__=='__main__':main()
