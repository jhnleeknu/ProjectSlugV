"""Full e8a48 CLI comparison, actual pending output carry and error preservation."""
import os
import subprocess
import sys
import tempfile
from verify_scene_motion_bounds import container
from observe_stage_cue_frame import *
BINARY_SHA256='b97a6a7cf8fcde8ad4e543ead1523ef44d22f823e363fe287d92d45279e97690'
def invoke(exe,regs,waiting,status,inp,out,files):
    return subprocess.run([str(exe)]+list(map(str,regs))+[str(int(waiting)) if isinstance(waiting,bool) else str(waiting),str(status),str(inp),str(out)]+list(map(str,files)),capture_output=True,text=True)
def negative_checks(root,cases,files):
    exe=root/'build/step_stage_cue_frame';folder=root/'artifacts/stage_cue_frame';rows=[];sample=next(c for c in cases if c['tag']==0x1c and c['count']==4 and c['debug']==0);base,regs=fixture(sample)
    with tempfile.TemporaryDirectory(dir=folder) as temp:
        work=Path(temp);inp,out,path,other=(work/n for n in ('in.bin','out.bin','window.ms5d','other.ms5d'))
        def reject(label,ram=base,values=regs,windows=files,waiting=0,status=2,destination=out):
            inp.write_bytes(ram)
            if destination!=inp and not(destination.exists() and os.path.samefile(inp,destination)):destination.write_bytes(b'preserved-cue-frame-output\0\xff')
            watched={p:p.read_bytes() for p in set((inp,out,destination,*windows)) if p.exists() and p.is_file()}
            actual=invoke(exe,values,waiting,status,inp,destination,windows);assert actual.returncode and not actual.stdout and all(p.read_bytes()==v for p,v in watched.items()),(label,actual.stdout,actual.stderr)
            rows.append(dict(failure=label,input_output_resources_preserved=True,native_bad_fixture_executed=False,error=actual.stderr.strip()))
        for size in (0,65535,65537):reject('RAM-size',bytes(size))
        for index in range(14):
            for text in ('-1','4294967296','0x100000000','0x','1x',''):
                values=regs.copy();values[index]=text;reject('register-parser-%d'%index,values=values)
        for v in ('-1','2','0x',''):reject('waiting-parser',waiting=v)
        for v in ('-1','4','0x',''):reject('status-parser',status=v)
        for pointer in (0,0x10fffa,0x110000,0xfffffff9,0xffffffff):
            data=base.copy();struct.pack_into('>I',data,0xde26,pointer);reject('late-cue-tag-after-request-clear',data)
        # Odd BYTE tag can be read, but eligible odd cue WORD coordinates fail later.
        data=base.copy();struct.pack_into('>I',data,0xde26,0x106001);data[0x6008]=0x1c;reject('late-odd-cue-coordinate-after-tag',data)
        for pointer in (0,0x100001,0x10ff96,0x110000,0xffffffff):
            data=base.copy();struct.pack_into('>I',data,0x4c9c,pointer);reject('late-freehead-after-cue-request-clear',data)
        for pointer in (0x100001,0x10fffa,0xffffffff):
            data=base.copy();struct.pack_into('>I',data,0xbfc,pointer);reject('late-allocator-successor',data)
        for pointer in (0x110000,0xffffffff):
            values=regs.copy();values[13]=pointer;reject('late-original-A6-after-allocator-writes',values=values)
        lookup=next(p for p in files if p.name=='indexed_lookup.ms5d');rest=tuple(p for p in files if p!=lookup)
        reject('late-missing-indexed-lookup-after-positioning',windows=rest)
        source=(root/'extracted/program/maincpu.decrypted.be.bin').read_bytes()[0xe8a0c:0xe8a8c]
        for size in (1,2,3):
            path.write_bytes(container(source[:size],cpu=0xe8a0c,rom=0xe8a0c));reject('late-partial-indexed-first-or-second-copy',windows=rest+(path,))
        path.write_bytes(container(source,cpu=0xe8a0c,rom=0xe8a0c));other.write_bytes(path.read_bytes());reject('ambiguous-indexed-window-after-positioning',windows=rest+(path,other))
        other.write_bytes(container(source[2:3],cpu=0xe8a0e,rom=0xe8a0e));reject('partial-overlap-second-lookup-copy',windows=rest+(path,other))
        for pointer in (1,0x106201,0x10fff4,0x110000,0xfffffff8,0xffffffff):
            data=base.copy();data[0xde2e]=0;struct.pack_into('>I',data,0xde2a,pointer);reject('late-stream-read-after-allocation-position-copy',data)
        data=base.copy();data[0xde2e]=0;struct.pack_into('>I',data,0xde2a,0xe89ec);struct.pack_into('>H',data,0xd418,0xffff);reject('default-stream-ffff-beyond14byte',data)
        data=base.copy();data[0xde2e]=0;data[0xf001]=2;struct.pack_into('>I',data,0xde2a,0);reject('null-stream-publishes4-then-debug-read-fails',data)
        for callback in (0,0x106000,0xffffffff):
            data=base.copy();data[0xf001]=2;struct.pack_into('>I',data,0x9152,callback);reject('late-debug-unsupported-callback-after-allocation',data)
        for offset in (1,0x8000,0x80ca):
            data=base.copy();data[0xf001]=2;struct.pack_into('>H',data,0x8b36,offset);reject('late-debug-record-after-allocation-and-queue-writes',data)
        for normal in (1,0x74cc):
            data=base.copy();data[0xf001]=2;struct.pack_into('>H',data,0x8d38,normal);reject('late-debug-normal-destination',data)
        # A genuine native-captured pending snapshot is used in the full comparison;
        # these malformed synthetic resumes test rejection only, without native execution.
        data=base.copy();struct.pack_into('>H',data,0x8d34,0);values=regs.copy();values[4]&=0xffff0000;values[9]=0x108b34
        for d6,a1 in ((1,0x108b34),(0,0x110000),(0,0xffffffff)):
            bad=values.copy();bad[6]=d6;bad[9]=a1;reject('synthetic-pending-late-source',data,bad,waiting=1,status=3)
        for packed,label in ((b'bad','header'),(container(source)[:-1],'truncated'),(container(source,version=2),'version'),(container(source,kind=2),'kind'),(container(source,reserved=1),'reserved'),(container(source)+b'x','extra')):
            path.write_bytes(packed);reject('loader-'+label,windows=(path,))
        bad=bytearray(container(source));bad[-1]^=1;path.write_bytes(bad);reject('CRC',windows=(path,));reject('missing-file',windows=(work/'missing.ms5d',))
        for label in ('same-path','hardlink','symlink'):
            inp.write_bytes(base);dest=inp if label=='same-path' else work/label
            if label=='hardlink':os.link(inp,dest)
            if label=='symlink':dest.symlink_to(inp)
            reject('input-output-'+label,destination=dest)
        reject('resource-input-alias',windows=(inp,));reject('resource-output-alias',windows=(out,))
        path.write_bytes(lookup.read_bytes());alias=work/'alias.ms5d';os.link(path,alias);reject('resource-hardlink-duplicate',windows=(path,alias))
    return rows

def main():
    root=Path(__file__).resolve().parents[1];exe=root/'build/step_stage_cue_frame';assert sha(exe.read_bytes())==BINARY_SHA256;program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;cases=build_cases(root);files=tuple(sorted((root/'extracted/runtime/stage_cue_frame').glob('*.ms5d')))+tuple(sorted((root/'extracted/runtime/stage_cue_control').glob('*.ms5d')));assert len(files)==45
    folder=root/'artifacts/stage_cue_frame';folder.mkdir(parents=True,exist_ok=True);negatives=negative_checks(root,cases,files)
    if '--negative-only'in sys.argv:print(json.dumps(dict(negative_cases=len(negatives))));return
    inputs,oracle=provenance(root),oracle_provenance(root);path=folder/'observation.json';raw=path.read_bytes();native=json.loads(raw);assert native['source']==source and native['inputs']==inputs and native['oracle']==oracle and native['failure'] is None and not native['program_code_modified'];assert native['cases']==len(native['results'])==len(cases)==822 and native['phases']==838
    inp,out=folder/'input.bin',folder/'cpp.bin';rows=[];previous=None;lookup_indexes=set();canonical=set();calls=collections.Counter();live=[];omission=[];debug_nonzero=0;debug_wrap=0
    for i,(c,row) in enumerate(zip(cases,native['results'])):
        assert row['case_index']==i and row['fixture']==c;ram,regs=fixture(c) if c.get('sequence_position',0)==0 else (bytearray(previous[0]),list(previous[1]));waiting=False;status=2
        for phase in row['phases']:
            for w in phase['external_RAM_writes']:ram[w['address']-BASE:w['address']-BASE+len(bytes.fromhex(w['raw_hex']))]=bytes.fromhex(w['raw_hex'])
            assert phase['input_ram_sha256']==sha(ram) and phase['incoming']==dict(zip(KEYS,regs)) and phase['waiting_in']==waiting and phase['status_in']==status
            assert phase['mmio_writes']==0 and phase['final_a7']==(STACK-4 if phase['waiting'] else STACK+4)
            assert phase['native']['pc']==(WAIT_PC if phase['waiting'] else RETURN)
            expected=(folder/phase['ram_file']).read_bytes();assert sha(expected)==phase['ram_sha256'];inp.write_bytes(ram);p=invoke(exe,regs,waiting,status,inp,out,files);assert p.returncode==0 and inp.read_bytes()==ram,(i,c,phase['phase'],p.stderr)
            parsed=json.loads(p.stdout);cpp=out.read_bytes();assert cpp==expected and parsed==dict(phase['result'],waiting=phase['waiting'],status=phase['status']),(i,c,phase['phase'],parsed,phase['result'])
            calls.update(hex(pc) for pc in phase['pcs'])
            snapshots=phase['debug_add_snapshots']
            if snapshots:
                assert [s['pc'] for s in snapshots]==[0xe8b2e,0xe8b32,0xe8b36];a,b,d=snapshots
                assert b['d0']==((a['d0']&0xffff0000)|((a['d0']+a['offset_x'])&65535)) and b['d1']==a['d1']
                assert d['d1']==((b['d1']&0xffff0000)|((b['d1']+b['offset_y'])&65535)) and d['d0']==b['d0']
                debug_nonzero+=int(bool(a['offset_x'] and b['offset_y']));debug_wrap+=int((a['d0']&65535)+a['offset_x']>65535 or (b['d1']&65535)+b['offset_y']>65535)
            if phase['phase']=='begin' and ram[0xde2f] and c['allocate'] and 0x1c<=c['tag']<0x3c and c['cue']==0x106000:
                idx=c['tag']-0x1c;lookup_indexes.add(idx);ws=[w for w in phase['RAM_writes'] if w['pc'] in (0xe8aaa,0xe8aac)];assert len(ws)==2 and [w['value'] for w in ws]==[int.from_bytes(program[0xe8a0c+idx*4+j:0xe8a0e+idx*4+j],'big') for j in (0,2)]
                allocated=c['node'] if 0x2908 in phase['pcs'] else 0x100e98;assert [w['address'] for w in ws]==[allocated+0x76,allocated+0x78]
            for copy in phase['byte_copies']:
                old=ram[copy['source']-BASE]
                if old!=copy['value']:live.append(dict(case_index=i,source=copy['source'],input_byte=old,live_byte=copy['value']))
            if phase['phase']=='begin' and c['family']=='all42-canonical-catalog-cue-heads':canonical.add(c['cue'])
            if phase['phase']!='begin':assert not set((0xe8a48,0x2986,0xe8af4,0xcd58))&set(phase['pcs']) and cpp[0xde2f]==0xff and cpp[0xde26:0xde2a]==bytes.fromhex('00106001')
            if len(omission)<5 and (phase['phase']!='begin' or not c['allocate'] and c['manual'] and not c['debug']):
                inp.write_bytes(ram);q=invoke(exe,regs,waiting,status,inp,out,());assert q.returncode==0 and out.read_bytes()==cpp and json.loads(q.stdout)==parsed;omission.append(dict(case_index=i,phase=phase['phase']))
            ram,regs,waiting,status=bytearray(cpp),[parsed[k] for k in KEYS],parsed['waiting'],parsed['status'];rows.append(dict(case_index=i,phase=phase['phase'],ram_sha256=sha(cpp),result=parsed,external_RAM_writes=phase['external_RAM_writes']))
        if 'sequence'in c:previous=(bytes(ram),regs.copy())
    assert debug_nonzero>=32 and debug_wrap>0
    assert len(rows)==838 and lookup_indexes==set(range(32)) and len(canonical)==42 and live and len(omission)==5
    assert native['branch_successor_counts']==branch_counts(native['results'])
    # Exact branches with both outcomes under this whole-frame support contract.
    two=(0xe8a4c,0xe8a66,0xe8ab2,0xe8aca,0xe8b26,0xe8b42,0xe8ad8,0xe8ae4,0xe8b00,0xe8b0e,0x28ba,0xcd66,0xcd78,0xcd94,0xcda0,0xcda8)
    assert all(len(native['branch_successor_counts'][hex(p)])==2 for p in two)
    # Debug computes D1=ffff0000|0/2, so bit6 is always clear: whole-frame
    # fresh/pending paths cannot naturally select deferred submission.
    assert native['branch_successor_counts']['0xcdb2']=={'0xcdb6':calls['0xcdb2']}
    c=next(c for c in cases if c['family']=='all42-canonical-catalog-cue-heads' and c['debug'] and not c['allocate']);i=cases.index(c);ram,regs=fixture(c);inp.write_bytes(ram);p=invoke(exe,regs,False,2,inp,out,(files[0].parent,files[-1].parent));assert p.returncode==0 and out.read_bytes()==(folder/native['results'][i]['phases'][0]['ram_file']).read_bytes()
    bypass=next(c for c in cases if not c['allocate'] and c['manual'] and not c['debug']);ram,regs=fixture(bypass);status_preserved=[]
    for status in range(4):
        inp.write_bytes(ram);p=invoke(exe,regs,False,status,inp,out,());assert p.returncode==0 and out.read_bytes()==ram and json.loads(p.stdout)==dict(zip(KEYS,regs),waiting=False,status=status);status_preserved.append(status)
    assert provenance(root)==inputs and oracle_provenance(root)==oracle and sha(exe.read_bytes())==BINARY_SHA256 and path.read_bytes()==raw and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report=dict(source=source,oracle=oracle,inputs=inputs,binary_sha256=BINARY_SHA256,native_observation_sha256=sha(raw),cases=len(cases),phases=len(rows),negative_cases=len(negatives),native_branch_successor_counts=native['branch_successor_counts'],both_outcomes_branches=list(two),all32_allocation_indexes=sorted(lookup_indexes),canonical_cue_heads=len(canonical),native_call_counts=dict(calls),original_A6_live_sources=live,pending_chains=8,pending_phases=24,debug_nonzero_offset_cases=debug_nonzero,debug_WORD_add_wrap_cases=debug_wrap,actual_full_frame_output_chain_calls=4,chain_prior_output_calls=3,chain_host_updates=[],resource_omission_checks=omission,directory_case_index=i,unused_debug_status_values_preserved=status_preserved,full_RAM_14_registers_waiting_status_equal=True,positive_input_RAM_preserved=True,source_resource_core_binary_tools_unchanged=True,mmio_writes=0,results=rows,negative_results=negatives,scope=native['scope']+' Native ordered writes retained as source-order evidence; C++ exposes finalRAM only. All256tags/32eligibleindexes and42catalog8-byte heads supplied; wider lookup128 includes raw code bytes without treating them as32logicalrecords. Four full-frameCLI calls carry priorRAM14registers with no host rewrites; de2f allocation requested only firstcall. Eightpendingchains carry actualCLIoutputs with recorded externalRAMchanges; invalidnewcue/requestff staysunconsumed onresume. Whole-frame debug clearsD1.bit6, so deferredspritepath belongs standalone verifiedunit, not claimedhere. Supporteddefaultcd50 only; defensiveunsupported reads are transactionalerrors, no natural scheduler claim.')
    path=folder/'verification.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),phases=len(rows),negative_cases=len(negatives),sha256=sha(path.read_bytes()))))
if __name__=='__main__':main()
