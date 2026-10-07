"""Full19802 resource/call boundary differential, strict authoritative corpus guard."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib
from disassemble_program import load_verified_program
from observe_scene_motion_time import build_cases, fixture, incoming, sha, KEYS, HIGHS, STACK, RETURN, FIXED
from verify_stage_catalog import SOURCE_SHA256

def optional_resource_checks(root, native):
    folder=root/'artifacts/scene_motion_time';exe=root/'build/resolve_scene_motion_time'
    inp,out=folder/'optional_input.bin',folder/'optional_output.bin'
    active=native['results'][0];ram=fixture(active['fixture']);inp.write_bytes(ram)
    sentinel=b'optional-resource-output-preserved';out.write_bytes(sentinel)
    result=subprocess.run([str(exe)]+list(map(str,active['incoming']))+list(map(str,(inp,out))),capture_output=True,text=True)
    assert result.returncode and out.read_bytes()==sentinel and inp.read_bytes()==ram
    null=next(r for r in native['results'] if r['fixture']['family']=='null' and r['fixture']['profile']==1)
    ram=fixture(null['fixture']);inp.write_bytes(ram)
    result=subprocess.run([str(exe)]+list(map(str,null['incoming']))+list(map(str,(inp,out))),capture_output=True,text=True)
    assert result.returncode==0 and json.loads(result.stdout)==null['result'] and out.read_bytes()==(folder/null['ram_file']).read_bytes() and inp.read_bytes()==ram
    return dict(failure='active-resource-omitted',output_preserved=True,native_executed=False),dict(fixture='null-resource-omitted',matches_native_case_index=null['case_index'],full_ram_registers_equal=True)

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    incoming.program=program;manifest_path=root/'extracted/runtime/scene_scripts/manifest.json';manifest_bytes=manifest_path.read_bytes();manifest=json.loads(manifest_bytes)
    resources={item['file']:sha((manifest_path.parent/item['file']).read_bytes()) for item in manifest['dependencies'] if item['file'].startswith('motion_')}
    assert len(resources)==37
    folder=root/'artifacts/scene_motion_time';native_path=folder/'observation.json';native_bytes=native_path.read_bytes();native=json.loads(native_bytes)
    expected=build_cases(program,root)
    assert native['source']==source and not native['smoke'] and native['fixed_rom_immutable']
    assert native['cases']==native['completed_cases']==len(native['results'])==len(expected)
    for index,(case,row) in enumerate(zip(expected,native['results'])):
        assert row['case_index']==index and row['fixture']==case and row['final_pc']==RETURN and row['final_a7']==STACK+4
    exe=root/'build/resolve_scene_motion_time';binary=sha(exe.read_bytes());rows=[];previous={};negatives=[]
    inp,out=folder/'input.bin',folder/'cpp.bin';synthetic=folder/'synthetic.ms5d'
    for row in native['results']:
        case=row['fixture'];prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None
        ram=fixture(case) if prior is None else bytearray(prior[0]);values=incoming(case,ram,None if prior is None else prior[1])
        assert sha(ram)==row['input_ram_sha256'] and values==row['incoming']
        if case['relocated']:
            body=bytes.fromhex(case['payload_hex']);synthetic.write_bytes(struct.pack('<4s7I',b'MS5D',1,1,FIXED,FIXED,len(body),zlib.crc32(body),0)+body);resource=synthetic
        else:resource=root/case['path_file']
        inp.write_bytes(ram);actual=subprocess.run([str(exe)]+list(map(str,values))+list(map(str,(inp,out,resource))),capture_output=True,text=True)
        assert actual.returncode==0 and inp.read_bytes()==ram,(row['case_index'],actual.stderr)
        parsed=json.loads(actual.stdout);cpp=out.read_bytes();original=(folder/row['ram_file']).read_bytes()
        assert sha(original)==row['ram_sha256'] and cpp==original and parsed==row['result'],(row['case_index'],parsed,row['result'],[(hex(i),a,b) for i,(a,b) in enumerate(zip(cpp,original)) if a!=b][:15])
        rows.append(dict(case_index=row['case_index'],family=case['family'],result=parsed,ram_sha256=sha(cpp),mmio_writes=0))
        if 'sequence'in case:previous[case['sequence']]=(cpp,tuple(parsed[k] for k in KEYS))
    sentinel=b'preserved-motion-time-output\0\xff';case=expected[0];resource=root/case['path_file'];ram=fixture(case)
    def reject(data,values,path,label):
        inp.write_bytes(data);out.write_bytes(sentinel);actual=subprocess.run([str(exe)]+list(map(str,values))+list(map(str,(inp,out,path))),capture_output=True,text=True)
        assert actual.returncode and inp.read_bytes()==data and out.read_bytes()==sentinel,(label,actual.stderr)
        negatives.append(dict(failure=label,output_preserved=True,native_executed=False))
    for size in (0,65535,65537):reject(bytes(size),HIGHS[1],resource,'RAM-size')
    for index in range(12):
        for text in ('-1','4294967296','0x','1x',''):
            values=list(HIGHS[1]);values[index]=text;reject(ram,values,resource,'register-parser')
    for cursor in (case['cpu']-1,case['cpu']+1,0xffffffff):
        bad=bytearray(ram);struct.pack_into('>I',bad,0xd3b4,cursor);reject(bad,HIGHS[1],resource,'invalid-cursor')
    with tempfile.TemporaryDirectory(dir=folder) as temp:
        path=Path(temp)/'malformed.ms5d';path.write_bytes(b'bad');reject(ram,HIGHS[1],path,'malformed-resource')
    inp.write_bytes(ram);actual=subprocess.run([str(exe)]+list(map(str,HIGHS[1]))+list(map(str,(inp,inp,resource))),capture_output=True,text=True)
    assert actual.returncode and inp.read_bytes()==ram;negatives.append(dict(failure='input-output-alias',output_preserved=True,native_executed=False))
    optional_negative,optional_positive=optional_resource_checks(root,native)
    negatives.append(optional_negative)
    assert sha(exe.read_bytes())==binary and native_path.read_bytes()==native_bytes
    assert manifest_path.read_bytes()==manifest_bytes and all(sha((manifest_path.parent/name).read_bytes())==digest for name,digest in resources.items())
    backward_only=sum(bool(r['calls'].get('0x196de')) and r['calls'].get('0x19812')==1 and not r['calls'].get('0x1982a') for r in native['results']);assert backward_only>0
    canonical=sum(not r['fixture']['relocated'] for r in native['results']);carry=sum(r['fixture']['family']=='canonical-cli-carry' for r in native['results'])
    report=dict(source=source,binary_sha256=binary,resources_sha256=resources,script_manifest_sha256=sha(manifest_bytes),resource_inputs_unchanged=True,positive_input_RAM_preserved=True,backward_only_early_publication_cases=backward_only,native_observation_sha256=sha(native_bytes),cases=len(rows),canonical_cases=canonical,relocated_synthetic_cases=len(rows)-canonical,negative_cases=len(negatives),cli_carry_calls=carry,cli_carry_sequences=len(previous),cli_calls_consuming_previous_outputs=carry-len(previous),mmio_writes=0,results=rows,negative_results=negatives,optional_resource_positive=optional_positive,
        scope='Original19802 toRTS compared whole64KiBRAM and full12 exposed registers, A7+4, zeroMMIO. Canonical strict no normalization. Synthetic raw paths nativeRAM106000/CPPfixed60000 normalize only outgoingA1 andRAMd3b4. ActualCLI outputs feed next controlledXY call in74sequences. HostXY updates/call boundary CPUstack reset explicit, no natural motion scheduling. Native corpus guard regenerates allfixtures and rejects smoke/truncation.')
    report_path=folder/'verification.json';report_path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),sha256=sha(report_path.read_bytes()))))
if __name__=='__main__':main()
