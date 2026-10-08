"""Native five-entry region differential and transactional CLI/API negatives."""
import os
import subprocess
import sys
import tempfile
from verify_scene_motion_bounds import container
from observe_stage_region_frame import *
BINARY_SHA256='5bf69cc5ad55e73bd130f2519792389fe950cf38cf337aef83fd188d36c77e09'
def invoke(exe,entry,regs,bank,carry,inp,out,files):return subprocess.run([str(exe),str(entry)]+list(map(str,regs))+[str(bank),str(int(carry)) if isinstance(carry,bool) else str(carry),str(inp),str(out)]+list(map(str,files)),capture_output=True,text=True)
def negative_checks(root,cases,rs,files):
    folder=root/'artifacts/stage_region_frame';exe=root/'build/step_stage_region_frame';rows=[];c=next(c for c in cases if c['entry']==0xb4a2a and c['activity']==3 and c['active']==[1,1] and not any(c['source_null']));base,regs=fixture(c,rs)
    with tempfile.TemporaryDirectory(dir=folder) as temp:
        work=Path(temp);inp,out,path,other=(work/n for n in ('in.bin','out.bin','window.ms5d','other.ms5d'))
        def reject(label,ram=base,values=regs,entry=0xb4a2a,bank=2,carry=1,windows=files,destination=out):
            inp.write_bytes(ram)
            if destination!=inp and not(destination.exists() and os.path.samefile(inp,destination)):destination.write_bytes(b'preserved-region-output\0\xff')
            watched={p:p.read_bytes() for p in set((inp,out,destination,*windows)) if p.exists() and p.is_file()};actual=invoke(exe,entry,values,bank,carry,inp,destination,windows);assert actual.returncode and not actual.stdout and all(p.read_bytes()==v for p,v in watched.items()),(label,actual.stdout,actual.stderr);rows.append(dict(failure=label,input_output_resources_preserved=True,native_bad_fixture_executed=False,error=actual.stderr.strip()))
        for size in (0,65535,65537):reject('RAM-size',bytes(size))
        for index in range(14):
            for text in ('-1','4294967296','0x','1x',''):
                values=regs.copy();values[index]=text;reject('register-parser-%d'%index,values=values)
        for entry in (0,0xb4a2b,0x4d7a6,'-1','4294967296','0x',''):reject('unsupported-entry',entry=entry)
        for bank in (0,1,4,'-1','4294967296','0x',''):reject('invalid-bank',bank=bank)
        for carry in (2,'-1','4294967296','0x',''):reject('invalid-carry',carry=carry)
        for pointer in (1,0x106001,0x10fffa,0x110000,0xffffffff):
            for at in (0xdcc2,0xdcee):
                data=base.copy();struct.pack_into('>I',data,at,pointer);reject('late-first-or-second-source-read',data)
        for low in (1,0xffba,0xfffe):
            data=base.copy();struct.pack_into('>H',data,0xdcec,low);reject('late-second-coordinate-after-first-publication',data)
        for a6 in (0,0xffff1234,0xff000000):
            values=regs.copy();values[13]=a6;reject('used-A6-highword-address',values=values)
        for role in ('fixed','bank2','bank3'):
            case=next(c for c in cases if role in c['source_roles']);ram,values=fixture(case,rs);r=next(r for r in rs if r['role']==role);raw=bytes.fromhex(r['raw_hex']);cpu,rom,kind=r['source_cpu_address'],r['source_rom_offset'],r['kind'];reject('missing-'+role+'-source',ram,values,bank=case['bank'],windows=())
            for size in (1,2,3,4,5,6,7):
                path.write_bytes(container(raw[:size],cpu=cpu,rom=rom,kind=kind));reject('partial-'+role+'-MOVEMsource',ram,values,bank=case['bank'],windows=(path,))
            path.write_bytes(container(raw,cpu=cpu,rom=rom,kind=kind));other.write_bytes(path.read_bytes());reject('ambiguous-'+role+'-complete',ram,values,bank=case['bank'],windows=(path,other));other.write_bytes(container(raw[2:3],cpu=cpu+2,rom=rom+2,kind=kind));reject('ambiguous-'+role+'-partial',ram,values,bank=case['bank'],windows=(path,other))
            if role.startswith('bank'):reject('wrong-active-bank-for-source',ram,values,bank=5-case['bank'],windows=(path,))
        for packed,label in ((b'bad','header'),(container(b'abcdefgh')[:-1],'truncated'),(container(b'abcdefgh',version=2),'version'),(container(b'abcdefgh',kind=3),'kind'),(container(b'abcdefgh',reserved=1),'reserved'),(container(b'abcdefgh')+b'x','extra')):
            path.write_bytes(packed);reject('loader-'+label,windows=(path,))
        bad=bytearray(container(b'abcdefgh'));bad[-1]^=1;path.write_bytes(bad);reject('CRC',windows=(path,));reject('missing-resource-file',windows=(work/'missing.ms5d',))
        for label in ('same-path','hardlink','symlink'):
            inp.write_bytes(base);dest=inp if label=='same-path' else work/label
            if label=='hardlink':os.link(inp,dest)
            if label=='symlink':dest.symlink_to(inp)
            reject('input-output-'+label,destination=dest)
        reject('resource-input-alias',windows=(inp,));reject('resource-output-alias',windows=(out,));path.write_bytes(files[0].read_bytes());alias=work/'resource-alias.ms5d';os.link(path,alias);reject('resource-hardlink-duplicate',windows=(path,alias))
    return rows
ATOMIC_SOURCE=r'''
#include "ms5/stage_region_frame.h"
#include <iostream>
void put(std::vector<std::uint8_t>& r,unsigned int a,unsigned int v,unsigned int n=2){for(unsigned int i=0;i<n;++i)r[a+i]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
bool same(const ms5::SceneMapTransferState& a,const ms5::SceneMapTransferState& b){for(unsigned int i=0;i<8;++i)if(a.d[i]!=b.d[i])return false;for(unsigned int i=0;i<5;++i)if(a.a[i]!=b.a[i])return false;return true;}
int main(){for(unsigned int test=0;test<5;++test){std::vector<std::uint8_t> ram(65536,0x5a);ram[0xd68e]=3;put(ram,0xdcba,1);put(ram,0xdce6,1);put(ram,0xdcc0,0xcb8);put(ram,0xdcec,0xda8);put(ram,0xdcc2,0x106000,4);put(ram,0xdcee,0x106010,4);ms5::SceneMapTransferState s;for(unsigned int i=0;i<8;++i)s.d[i]=0xabcd0000+i;for(unsigned int i=0;i<5;++i)s.a[i]=0x12340000+i;unsigned int entry=0xb4a2a,bank=2;
if(test==0)put(ram,0xdcee,0x110000,4); // secondsource failure after firstpublication
if(test==1)put(ram,0xdcec,0xffc0); // secondcoordinate after fourWORD source reads
if(test==2)put(ram,0xdcc2,0x106001,4); // firstMOVEM after sentinelwrite
if(test==3)entry=0;
if(test==4)bank=4;
const std::vector<std::uint8_t> old=ram;const ms5::SceneMapTransferState saved=s;bool carry=true;std::vector<ms5::FixedDataResource> windows;std::string e;if(ms5::step_stage_region_frame(ram,entry,windows,s,0x106f01,bank,carry,e)||ram!=old||!same(s,saved)||!carry||e.empty())return 1;}
std::cout<<"5 API RAM/register/carry atomic errors passed\n";}
'''
def atomic_check(root):
    folder=root/'artifacts/stage_region_frame';path=folder/'atomic_probe.cpp';exe=folder/'atomic_probe';path.write_text(ATOMIC_SOURCE);p=subprocess.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(root/'engine/include'),str(path),str(root/'engine/src/stage_region_frame.cpp'),'-o',str(exe)],capture_output=True,text=True);assert p.returncode==0,p.stderr;p=subprocess.run([str(exe)],capture_output=True,text=True);assert p.returncode==0,(p.returncode,p.stdout,p.stderr);return dict(cases=5,source_sha256=sha(path.read_bytes()),binary_sha256=sha(exe.read_bytes()),compiler=subprocess.run(['c++','--version'],capture_output=True,text=True).stdout,stdout=p.stdout.strip())
def evidence(c,ram,regs,out,result,row):
    assert result['a6']==regs[13] and result['bank']==c['bank']
    if c['entry']==0x49392:
        bit=regs[0]&1;assert result['carry']==bool(ram[0xd68e]&(1<<bit)) and result['d0']==((regs[0]&0xffff0000)|bit) and result['a0']==0x100cb8+bit*0xf0 and out==ram
    else:assert result['carry']==bool(c['carry'])
    if c['entry'] in (0x4d9d6,0x1c028):
        selected=int(bool(regs[0]&255));at=0xdcba+selected*0x2c;assert result['a4']==BASE+at
        active=int.from_bytes(ram[at:at+2],'big');low=int.from_bytes(ram[at+6:at+8],'big');high=regs[13]&0xffff0000
        if c['entry']==0x4d9d6:
            assert result['d0']==((high|low) if active else regs[0]);assert result['a0']==(high|low if active and low else 0)
        else:
            fallback=not(active and low);assert result['a0']==(0x100cb8+(regs[0]&1)*0xf0 if fallback else high|low)
            assert result['d0']==((high if active else regs[0]&0xffff0000)|((regs[0]&1) if fallback else regs[0]&65535))
        assert out==ram
    if c['entry'] in (0xb481e,0xb4a2a):
        parity=int.from_bytes(ram[0xe:0x10],'big')&1;start=0x10dd98 if parity else 0x10dd5c;writes=[w for w in row['RAM_writes'] if w['pc']==0xb4846];assert [w['address'] for w in writes]==list(range(start,start+60,10)) and all(w['size']==2 and w['value']==0 for w in writes);assert result['d0']==0 and result['a1']==result['a2']==start+60
    for snap in row['MOVEM_W_snapshots']:
        assert all(v==(v&65535 if not v&0x8000 else (v&65535)|0xffff0000) for v in snap['registers'])
    if c['entry']==0xb4a2a:
        assert result['a0']==0x10dd5c
        for at in (0xdd58,0xdd5a):assert out[at]==max(0,ram[at]-1)
    if c['alias']=='second-source-own-sentinel':
        second=next(s for s in row['MOVEM_W_snapshots'] if s['pc']==0xb4a84);assert second['source']==0x10dd50 and second['registers'][0]==0xffff8000
    if c['alias']=='second-source-first-publication':
        second=next(s for s in row['MOVEM_W_snapshots'] if s['pc']==0xb4a84);assert second['source']==0x10dd48 and second['registers']==[int.from_bytes(out[at:at+2],'big')| (0xffff0000 if out[at]&0x80 else 0) for at in range(0xdd48,0xdd50,2)]
    if c['alias']=='second-coordinates-first-publication':
        second=next(s for s in row['MOVEM_W_snapshots'] if s['pc']==0xb4a84);assert second['coordinate_words']==[int.from_bytes(out[at:at+2],'big') for at in (0xdd48,0xdd4c)]

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;exe=root/'build/step_stage_region_frame';assert sha(exe.read_bytes())==BINARY_SHA256;cases,rs=build_cases(),resources(root);files=tuple(root/r['file'] for r in rs);folder=root/'artifacts/stage_region_frame';folder.mkdir(parents=True,exist_ok=True);negative=negative_checks(root,cases,rs,files);atomic=atomic_check(root)
    if '--negative-only'in sys.argv:print(json.dumps(dict(negative_cases=len(negative),API_atomic_cases=atomic['cases'])));return
    inputs,oracle,secondary=provenance(root),oracle_provenance(root),unicorn_provenance();path=folder/'observation.json';raw=path.read_bytes();native=json.loads(raw);assert native['source']==source and native['inputs']==inputs and native['oracle']==oracle and native['banked_oracle']==secondary and native['failure'] is None and not native['program_code_modified'] and not native['physical_bank_payload_modified'] and not native['in_call_SR_read'];assert native['cases']==len(cases)==len(native['results'])==801
    inp,out=folder/'input.bin',folder/'cpp.bin';rows=[];previous=None;oracles=collections.Counter();omission={};signextended=0;fallback_mismatch=0
    for i,(c,row) in enumerate(zip(cases,native['results'])):
        assert row['fixture']==c and row['case_index']==i;ram,regs=fixture(c,rs) if not c.get('sequence_position',0) else (bytearray(previous[0]),list(previous[1]));assert row['input_ram_sha256']==sha(ram) and row['incoming']==dict(zip(KEYS,regs)) and row['final_pc']==RETURN and row['final_a7']==STACK+4 and row['mmio_writes']==0
        expected=(folder/row['ram_file']).read_bytes();assert sha(expected)==row['ram_sha256'];evidence(c,ram,regs,expected,row['result'],row)
        inp.write_bytes(ram);p=invoke(exe,c['entry'],regs,c['bank'],c['carry'],inp,out,files);assert p.returncode==0 and inp.read_bytes()==ram,(i,c,p.stderr);parsed=json.loads(p.stdout);cpp=out.read_bytes();assert isinstance(parsed['carry'],bool) and parsed==row['result'] and cpp==expected,(i,c,parsed,row['result'])
        for player,role in enumerate(c['source_roles']):
            if role!='RAM':
                r=next(r for r in rs if r['role']==role);snapshot=next(s for s in row['MOVEM_W_snapshots'] if s['pc']==(0xb4a50 if player==0 else 0xb4a84));words=struct.unpack('>4H',bytes.fromhex(r['raw_hex']));assert snapshot['source']==r['source_cpu_address'] and snapshot['registers']==[w|(0xffff0000 if w&0x8000 else 0) for w in words]
                if role.startswith('bank'):assert row['oracle']=='Unicorn2.1.4' and {x['address'] for x in row['banked_reads']}==set(range(r['source_cpu_address'],r['source_cpu_address']+8,2)) and all(x['bank']==c['bank'] for x in row['banked_reads'])
        oracles[row['oracle']]+=1;signextended+=sum(any(v&0xffff0000 for v in s['registers']) for s in row['MOVEM_W_snapshots'])
        if c['entry']==0x1c028 and regs[0]&255 and not(regs[0]&1) and parsed['a0']==0x100cb8:fallback_mismatch+=1
        if c['entry'] not in omission and not any(role!='RAM' for role in c['source_roles']):
            inp.write_bytes(ram);p=invoke(exe,c['entry'],regs,c['bank'],c['carry'],inp,out,());assert p.returncode==0 and out.read_bytes()==cpp and json.loads(p.stdout)==parsed;omission[c['entry']]=i
        if 'sequence'in c:previous=(cpp,[parsed[k] for k in KEYS])
        rows.append(dict(case_index=i,entry=c['entry'],family=c['family'],oracle=row['oracle'],result=parsed,ram_sha256=sha(cpp)))
    assert len(omission)==5 and fallback_mismatch and signextended and native['branch_successor_counts']==branch_counts(native['results']) and oracles=={'pinnedMusashiM68000':797,'Unicorn2.1.4':4}
    both=[p for p in BRANCHES if p!=0x49398];assert all(len(native['branch_successor_counts'][hex(p)])==2 for p in both);assert native['branch_successor_counts']['0x49398']=={'0x4939e':sum(1 for row in native['results'] for pc in row['pcs'] if pc==0x49398)}
    directories=[]
    for role in ('fixed','bank2','bank3'):
        i=next(i for i,c in enumerate(cases) if role in c['source_roles']);c=cases[i];ram,regs=fixture(c,rs);inp.write_bytes(ram);r=next(r for r in rs if r['role']==role);p=invoke(exe,c['entry'],regs,c['bank'],c['carry'],inp,out,((root/r['file']).parent,));assert p.returncode==0 and inp.read_bytes()==ram and out.read_bytes()==(folder/native['results'][i]['ram_file']).read_bytes() and json.loads(p.stdout)==native['results'][i]['result'];directories.append(dict(role=role,case_index=i))
    assert provenance(root)==inputs and oracle_provenance(root)==oracle and unicorn_provenance()==secondary and sha(exe.read_bytes())==BINARY_SHA256 and path.read_bytes()==raw and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report=dict(source=source,oracle=oracle,banked_oracle=secondary,inputs=inputs,binary_sha256=BINARY_SHA256,native_observation_sha256=sha(raw),cases=len(cases),negative_cases=len(negative),direct_API_atomicity=atomic,oracles=dict(oracles),native_branch_successor_counts=native['branch_successor_counts'],both_outcomes_branches=both,A5_trap_branch_excluded=True,MOVEM_signed_register_snapshots=signextended,byte_selector_bit0_fallback_disagreement_cases=fallback_mismatch,unused_resource_omissions=omission,directory_checks=directories,actual_output_fullframe_chain_calls=6,chain_prior_output_calls=5,chain_host_updates=[],full_RAM_14_registers_bank_activity_carry_equal=True,positive_input_RAM_preserved=True,original_ROM_resources_core_binary_tools_unchanged=True,mmio_writes=0,results=rows,negative_results=negative,scope=native['scope']+' All15supportedconditionalbranches have bothactualsuccessors;49398A5-mismatchTRAP is unsupported. RawsourceMOVEM.W snapshotsprove32bitsignextension beforecoordinates/publication; publication/source/coordinatealiases are live. Eight source-verified rawbank/fixedtests are readfixtures, notrecordmeaningclaims. DirectAPIlateerrorspreserveRAM13registers/carry; A6/bankreadonly inputs.')
    path=folder/'verification.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),negative_cases=len(negative),API_atomic_cases=atomic['cases'],sha256=sha(path.read_bytes()))))
if __name__=='__main__':main()
