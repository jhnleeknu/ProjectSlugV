"""Cue-control full state differential and transactional CLI rejection checks."""
import collections
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from verify_scene_motion_bounds import container
from observe_stage_cue_control import *
BINARY_SHA256='04231d0f1ef04ed52a865e6e2bcc951e0ae82031d5f1e8ec01b06926cbdf4f5b'
def invoke(exe,c,ram,regs,carry,inp,out,files):
    inp.write_bytes(ram);p=subprocess.run([str(exe),str(c['entry'])]+list(map(str,regs))+[str(int(carry)),str(inp),str(out)]+list(map(str,files)),capture_output=True,text=True)
    assert p.returncode==0 and inp.read_bytes()==ram,p.stderr
    return out.read_bytes(),json.loads(p.stdout)
def negative_checks(root,cases):
    folder=root/'artifacts/stage_cue_control';folder.mkdir(parents=True,exist_ok=True);exe=root/'build/step_stage_cue_control';resources=root/'extracted/runtime/stage_cue_control';rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temp:
        work=Path(temp);inp,out,path,other=(work/n for n in ('input.bin','output.bin','window.ms5d','other.ms5d'));sentinel=b'preserved-cue-output\x00\xff';c=next(x for x in cases if x['entry']==0x2986 and x['count']==4 and x['request']==0 and x['callback']==1);ram,regs,carry=fixture(c)
        def reject(label,data=ram,values=regs,entry=0x2986,files=(),inputcarry=carry,destination=out):
            inp.write_bytes(data)
            if destination!=inp and not(destination.exists() and os.path.samefile(inp,destination)):destination.write_bytes(sentinel)
            watched={p:p.read_bytes() for p in set((inp,out,destination,*files)) if p.exists() and p.is_file()}
            p=subprocess.run([str(exe),str(entry)]+list(map(str,values))+[str(inputcarry),str(inp),str(destination)]+list(map(str,files)),capture_output=True,text=True)
            assert p.returncode and all(p.read_bytes()==before for p,before in watched.items()),(label,p.stdout,p.stderr)
            rows.append(dict(failure=label,entry=entry,input_output_resources_preserved=True,native_bad_fixture_executed=False,error=p.stderr.strip()))
        baseline,parsed=invoke(exe,c,ram,regs,carry,inp,out,());assert parsed['allocation_carry']
        for size in (0,65535,65537):reject('RAM-size',bytes(size))
        for index in range(14):
            for value in ('-1','4294967296','0x100000000','0x','1x',''):
                values=regs.copy();values[index]=value;reject('register-parser-%d'%index,values=values)
        for value in ('-1','2','4294967296','0x','x',''):reject('carry-parser',inputcarry=value)
        for entry in (0,0x28ae,0x2987,0xe89fc,'-1','4294967296','0x',''):reject('entry-parser-or-unsupported',entry=entry)
        for pointer in (1,0x100001,0x10ff96,0x110000,0xfffffffe,0xffffffff):
            values=regs.copy();values[9]=pointer;reject('allocation-parent',values=values)
        for at,pointer in ((0x4c9c,0),(0x4c9c,0x100001),(0x4c9c,0x10ff96),(0x4c9c,0x110000),(0x208,0x100001),(0x208,0x10fffa),(0x208,0xffffffff)):
            data=ram.copy();struct.pack_into('>I',data,at,pointer);reject('allocation-freehead-or-successor',data)
        for pointer in (0x110000,0xfffffffe,0xffffffff):
            values=regs.copy();values[13]=pointer;reject('late-original-A6-copy-after-allocation-writes',values=values)
        for pointer in (1,0x106001,0x10fffc,0x110000,0xfffffffe,0xffffffff):
            values=regs.copy();values[8]=pointer;reject('coordinate-read-alignment-range',values=values,entry=0xe8af4)
        for pointer in (1,0x106001,0x10fff4,0x110000,0xfffffff8,0xffffffff):
            data=ram.copy();struct.pack_into('>I',data,0xde2a,pointer);reject('stream-next-gate-read-alignment-range',data,entry=0xe8ad0)
        data=ram.copy();struct.pack_into('>IH',data,0xde2a,0xe89ec,0);struct.pack_into('>H',data,0xd418,0xffff)
        reject('default-stream-ffff-continues-beyond-window',data,entry=0xe8ad0,files=(resources/'default_stream.ms5d',))
        values=regs.copy();values[8]=0xe89e4;reject('missing-cue-window',values=values,entry=0xe8af4)
        raw=bytes.fromhex('0000000003000000')
        for size in (1,2,3,4):
            path.write_bytes(container(raw[:size],cpu=0xe89e4,rom=0xe89e4));reject('partial-cue-window',values=values,entry=0xe8af4,files=(path,))
        path.write_bytes(container(raw,cpu=0xe89e4,rom=0xe89e4));other.write_bytes(path.read_bytes());reject('ambiguous-cue-window',values=values,entry=0xe8af4,files=(path,other))
        other.write_bytes(container(raw[:1],cpu=0xe89e6,rom=0xe89e6));reject('ambiguous-partial-cue-window',values=values,entry=0xe8af4,files=(path,other))
        for packed,label in ((b'bad','header'),(container(raw)[:-1],'truncated'),(container(raw,version=2),'version'),(container(raw,kind=2),'kind'),(container(raw,reserved=1),'reserved'),(container(raw,cpu=0x60001,rom=0x60001),'odd-start'),(container(raw,cpu=BASE,rom=BASE),'RAM-window'),(container(raw,cpu=0x60000,rom=0x60002),'mapping'),(container(raw,cpu=0xffffe,rom=0xffffe),'window-overflow'),(container(raw)+b'x','extra')):
            path.write_bytes(packed);reject('loader-or-used-window-'+label,values=values,entry=0xe8af4,files=(path,))
        bad=bytearray(container(raw));bad[-1]^=1;path.write_bytes(bad);reject('CRC',files=(path,));reject('missing-file',files=(work/'missing.ms5d',))
        for label in ('same-path','hardlink','symlink'):
            inp.write_bytes(ram);target=inp if label=='same-path' else work/label
            if label=='hardlink':os.link(inp,target)
            if label=='symlink':target.symlink_to(inp)
            reject('input-output-'+label,destination=target)
        for resource,label in ((inp,'resource-input-alias'),(out,'resource-output-alias')):reject(label,files=(resource,))
        path.write_bytes((resources/'default_cue.ms5d').read_bytes());alias=work/'resource-alias.ms5d';os.link(path,alias);reject('duplicate-resource-hardlink',files=(path,alias))
    return rows

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;exe=root/'build/step_stage_cue_control';assert sha(exe.read_bytes())==BINARY_SHA256;cases=build_cases();negatives=negative_checks(root,cases)
    if '--negative-only'in sys.argv:print(json.dumps(dict(negative_cases=len(negatives))));return
    inputs,oracle=provenance(root),oracle_provenance(root);folder=root/'artifacts/stage_cue_control';path=folder/'observation.json';raw=path.read_bytes();native=json.loads(raw)
    assert native['source']==source and native['inputs']==inputs and native['oracle']==oracle and native['failure'] is None and not native['program_code_modified'];assert native['cases']==native['completed_cases']==len(native['results'])==len(cases)==555
    resources=tuple(root/'extracted/runtime/stage_cue_control'/n for n in ('default_cue.ms5d','default_stream.ms5d'));inp,out=folder/'input.bin',folder/'cpp.bin';rows=[];previous={};branches=collections.defaultdict(collections.Counter);calls=collections.Counter();omitted={};live=[]
    for i,(c,row) in enumerate(zip(cases,native['results'])):
        prior=previous.get(c.get('sequence')) if c.get('sequence_position',0)>0 else None;ram,regs,carry,changes=prepare(c,prior)
        assert row['fixture']==c and row['case_index']==i and row['input_ram_sha256']==sha(ram) and row['incoming']==dict(zip(KEYS,regs)) and row['input_carry']==bool(carry) and row['host_updates']==changes
        assert row['returned'] and row['final_pc']==RETURN and row['final_a7']==STACK+4 and row['mmio_writes']==0
        expected=(folder/row['ram_file']).read_bytes();assert sha(expected)==row['ram_sha256'];assert_evidence(c,ram,regs,carry,expected,row['result'],row)
        cpp,result=invoke(exe,c,ram,regs,carry,inp,out,resources);assert isinstance(result['allocation_carry'],bool) and result==row['result'] and cpp==expected,(i,c,result,row['result'])
        for b in row['branch_successors']:branches[b['pc']][b['next_pc']]+=1
        calls.update(row['calls'])
        if c['entry']==0x2986 and result['allocation_carry']:
            copy=row['byte_copies'][-1];old=ram[copy['source']-BASE]
            intervening=[w for w in row['RAM_writes'] if w['pc']!=0x2992 and w['address']<=copy['source']<w['address']+w['size']]
            if intervening and old!=copy['value']:live.append(dict(case_index=i,source=copy['source'],input_byte=old,live_byte=copy['value'],prior_writes=intervening))
        used_fixed=c['entry'] in (0xe8ad0,0xe8af4) and 0<c['pointer']<BASE
        if c['entry'] not in omitted and not used_fixed:
            other,parsed=invoke(exe,c,ram,regs,carry,inp,out,());assert other==cpp and parsed==result;omitted[c['entry']]=i
        if 'sequence'in c:previous[c['sequence']]=(cpp,[result[k] for k in KEYS],result['allocation_carry'])
        rows.append(dict(case_index=i,entry=c['entry'],family=c['family'],ram_sha256=sha(cpp),result=result,host_updates=changes))
    assert native['branch_successor_counts']=={hex(p):{hex(n):v for n,v in b.items()} for p,b in branches.items()}
    assert len(omitted)==5 and len(previous)==3 and live and all(len(branches[p])==2 for p in BRANCHES if p!=0x28d6) and set(branches[0x28d6])=={0x28da}
    i=next(i for i,c in enumerate(cases) if c['entry']==0xe8af4 and c['pointer']==0xe89e4);c=cases[i];ram,regs,carry=fixture(c);cpp,result=invoke(exe,c,ram,regs,carry,inp,out,(resources[0].parent,));assert cpp==(folder/native['results'][i]['ram_file']).read_bytes() and result==native['results'][i]['result']
    assert provenance(root)==inputs and oracle_provenance(root)==oracle and sha(exe.read_bytes())==BINARY_SHA256 and path.read_bytes()==raw and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report=dict(source=source,oracle=oracle,inputs=inputs,binary_sha256=BINARY_SHA256,native_observation_sha256=sha(raw),cases=len(rows),negative_cases=len(negatives),entry_addresses=list(ENTRIES),families=dict(collections.Counter(c['family'] for c in cases)),branch_paths=[dict(pc=p,next_pc=n,count=v) for p,b in branches.items() for n,v in b.items()],both_outcomes_conditional_branches=8,null_freehead_branch_excluded=True,original_A6_live_byte_observations=live,unused_resource_omission_cases=omitted,directory_case_index=i,cli_output_chains=3,chain_calls=12,calls_consuming_prior_outputs=9,full_RAM_14_registers_and_allocation_carry_equal=True,mmio_writes=0,original_ROM_resources_core_binary_tools_unchanged=True,positive_input_RAM_preserved=True,native_call_counts=dict(calls),results=rows,negative_results=negatives,scope=native['scope']+' Three actual CLI four-call sequences preserve previous RAM/registers/carry, except allocation chain reasserts callback A0 and allocation parent A1, and stream chain updates phase WORD10d418; cue chain has no host changes. Original A6 sources include odd bytes and allocator-written aliases; trace captures live byte after allocation. Default stream phaseffff is rejected for leaving supplied14-byte window, without claiming original native terminal-stop/fault. No artificial budget test: stream progression is monotonically+12 and supplied bounded windows exhaust first.')
    path=folder/'verification.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),live_aliases=len(live),sha256=sha(path.read_bytes()))))
if __name__=='__main__':main()
