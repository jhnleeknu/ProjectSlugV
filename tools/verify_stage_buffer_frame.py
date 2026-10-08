"""Whole stage-buffer differential, two-stage actual output carry and atomic errors."""
import os
import subprocess
import sys
import tempfile
from verify_scene_motion_bounds import container
from observe_stage_buffer_frame import *
BINARY_SHA256='e7cb83ef01ec4e7c09171e545ec440628047b7d986eafdbd57c5d07819e8e21d'
ARGS=('bank','phase','saved_a6','saved_slot_a4','saved_slot_d7','saved_d0','saved_d1','saved_d7','saved_a0')
def invoke(exe,state,inp,out,ports,files):
    return subprocess.run([str(exe)]+[str(state[k]) for k in KEYS+ARGS]+list(map(str,(inp,out,ports)))+list(map(str,files)),capture_output=True,text=True)
def initial(regs,bank):return dict(zip(KEYS,regs),bank=bank,phase=0,**{k:0 for k in SAVED})
def negative_checks(root,cases,resources,files):
    folder=root/'artifacts/stage_buffer_frame';exe=root/'build/step_stage_buffer_frame';rows=[];sample=next(c for c in cases if c['debug'] and c['source_role']=='RAM' and not c['pending']);base,regs=fixture(sample,resources);state=initial(regs,sample['bank'])
    with tempfile.TemporaryDirectory(dir=folder) as temp:
        work=Path(temp);inp,out,ports,path,other=(work/n for n in ('in.bin','out.bin','ports.bin','window.ms5d','other.ms5d'))
        def reject(label,ram=base,values=state,windows=files,destination=out,portpath=ports):
            inp.write_bytes(ram)
            for p in (destination,portpath):
                if p!=inp and not(p.exists() and os.path.samefile(inp,p)):p.write_bytes(b'preserved-buffer-output\0\xff')
            watched={p:p.read_bytes() for p in set((inp,out,ports,destination,portpath,*windows)) if p.exists() and p.is_file()}
            actual=invoke(exe,values,inp,destination,portpath,windows);assert actual.returncode and not actual.stdout and all(p.read_bytes()==v for p,v in watched.items()),(label,actual.stdout,actual.stderr)
            rows.append(dict(failure=label,input_RAM_outputs_resources_preserved=True,native_bad_fixture_executed=False,error=actual.stderr.strip()))
        for size in (0,65535,65537):reject('RAM-size',bytes(size))
        for k in KEYS+ARGS:
            for text in ('-1','4294967296','0x','1x',''):
                values=state.copy();values[k]=text;reject('numeric-parser-'+k,values=values)
        for bank in (0,1,4):reject('bank-enum',values=dict(state,bank=bank))
        for phase in (3,4):reject('phase-enum',values=dict(state,phase=phase))
        pending=dict(state,phase=1,saved_slot_a4=0x10daf8,saved_slot_d7=0,saved_a6=state['a6'],saved_a0=0x106004)
        for phase in (1,2):
            for slot,index in ((0,0),(0x10daf9,0),(0x10db78,16),(0x10daf8,1),(0x10daf8,0x10000),(0x10db70,0xffff)):
                reject('invalid-pending-slot-metadata',values=dict(pending,phase=phase,saved_slot_a4=slot,saved_slot_d7=index))
        for pointer in (1,0x100001,0x10fff0,0x110000,0xffffffff):
            data=base.copy();struct.pack_into('>I',data,0xdc88,pointer);reject('late-normal-ring-after-debug-ports',data)
        for pointer in (0x110000,0xffffffff):
            data=base.copy();struct.pack_into('>I',data,0xdaf8,pointer);reject('slot-object-byte-range',data)
        for pointer in (0x105ffd,0x10fff8,0xfffffffd):
            data=base.copy();struct.pack_into('>I',data,0xdafc,pointer);reject('source-LONG-or-late-dimension-read',data)
        for callback in (0,0x106000,0xffffffff):
            data=base.copy();struct.pack_into('>I',data,0x9152,callback);reject('unsupported-sprite-callback',data)
        for offset in (1,0x8000,0x80ca):
            data=base.copy();struct.pack_into('>H',data,0x8b36,offset);reject('late-sprite-record-after-queue-writes',data)
        for normal in (1,0x74cc):
            data=base.copy();struct.pack_into('>H',data,0x8d38,normal);reject('late-normal-list-write',data)
        for role in ('fixed','bank2','bank3'):
            c=next(c for c in cases if c['source_role']==role);ram,regs=fixture(c,resources);values=initial(regs,c['bank']);r=next(r for r in resources if r['role']==role);raw=bytes.fromhex(r['raw_hex']);cpu=r['source_cpu_address'];rom=r['source_rom_offset'];kind=r['kind'];reject('missing-'+role+'-window',ram,values,())
            for size in (3,4,5,6,7):
                path.write_bytes(container(raw[:size],cpu=cpu,rom=rom,kind=kind));reject('partial-'+role+'-XY-or-late-dimensions',ram,values,(path,))
            path.write_bytes(container(raw,cpu=cpu,rom=rom,kind=kind));other.write_bytes(path.read_bytes());reject('ambiguous-'+role+'-window',ram,values,(path,other))
            other.write_bytes(container(raw[4:6],cpu=cpu+4,rom=rom+4,kind=kind));reject('partial-overlap-'+role+'-dimension',ram,values,(path,other))
        # Synthetic API pending snapshots are rejection tests, not native histories.
        data=base.copy();struct.pack_into('>H',data,0x8d34,0);ready=dict(pending,d4=0,a1=0x108b34)
        for d6,a1 in ((1,0x108b34),(0,0x110000),(0,0xffffffff)):
            reject('pending-late-source-read',data,dict(ready,d6=d6,a1=a1))
        for packed,label in ((b'bad','header'),(container(b'abcdefgh')[:-1],'truncated'),(container(b'abcdefgh',version=2),'version'),(container(b'abcdefgh',reserved=1),'reserved'),(container(b'abcdefgh')+b'x','extra')):
            path.write_bytes(packed);reject('loader-'+label,windows=(path,))
        bad=bytearray(container(b'abcdefgh'));bad[-1]^=1;path.write_bytes(bad);reject('CRC',windows=(path,));reject('missing-resource-file',windows=(work/'missing.ms5d',))
        for label in ('same-path','hardlink','symlink'):
            inp.write_bytes(base);dest=inp if label=='same-path' else work/label
            if label=='hardlink':os.link(inp,dest)
            if label=='symlink':dest.symlink_to(inp)
            reject('input-output-'+label,destination=dest)
        reject('input-ports-alias',portpath=inp);reject('RAM-output-ports-alias',portpath=out)
        reject('resource-input-alias',windows=(inp,));reject('resource-output-alias',windows=(out,));reject('resource-ports-alias',windows=(ports,))
        path.write_bytes(files[0].read_bytes());alias=work/'resource-alias.ms5d';os.link(path,alias);reject('duplicate-resource-hardlink',windows=(path,alias))
    return rows

ATOMIC_SOURCE=r'''
#include "ms5/stage_buffer_frame.h"
#include <iostream>
void put(std::vector<std::uint8_t>& r,unsigned int a,unsigned int v,unsigned int n=2){for(unsigned int i=0;i<n;++i)r[a+i]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));}
bool same(const ms5::StageBufferFrameState& a,const ms5::StageBufferFrameState& b){for(unsigned int i=0;i<8;++i)if(a.registers.d[i]!=b.registers.d[i])return false;for(unsigned int i=0;i<5;++i)if(a.registers.a[i]!=b.registers.a[i])return false;return a.a6==b.a6&&a.bank==b.bank&&a.phase==b.phase&&a.saved_a6==b.saved_a6&&a.saved_slot_a4==b.saved_slot_a4&&a.saved_slot_d7==b.saved_slot_d7&&a.saved_d0==b.saved_d0&&a.saved_d1==b.saved_d1&&a.saved_d7==b.saved_d7&&a.saved_a0==b.saved_a0;}
int main(){
for(unsigned int test=0;test<5;++test){std::vector<std::uint8_t> ram(65536,0);put(ram,0x9152,0xcd50,4);put(ram,0xdc88,0x10db88,4);ram[0xf001]=0x80;put(ram,0xdaf8,0x102000,4);put(ram,0xdafc,0x105ffc,4);put(ram,0x6000,0x00000100,4);put(ram,0x8d34,0x100);put(ram,0x8b36,12);
ms5::StageBufferFrameState s;s.bank=3;s.a6=0xabcdef01;for(unsigned int i=0;i<8;++i)s.registers.d[i]=0xabcd0000+i;for(unsigned int i=0;i<5;++i)s.registers.a[i]=0x12340000+i;
if(test==0)put(ram,0xdc88,0x10fff0,4); // after both debug submissions and four generated ports
if(test==1)put(ram,0xdafc,0x10fff8,4); // first LONG valid, dimensions fail after first submission
if(test==2)put(ram,0x9152,0,4);
if(test==3){s.phase=1;s.saved_slot_a4=0x10daf8;s.saved_slot_d7=0;s.saved_a6=0x98765432;s.saved_a0=0x110000;s.registers.d[4]=0;s.registers.d[6]=2;s.registers.a[1]=0x108b34;put(ram,0x8d34,0);}
if(test==4){s.phase=2;s.saved_slot_a4=0x10daf8;s.saved_slot_d7=0x10000;}
std::vector<ms5::VideoPortWrite> ports(1);ports[0].size=1;ports[0].address=0xabcdef01;ports[0].value=0x23456789;const std::vector<std::uint8_t> old=ram;const ms5::StageBufferFrameState saved=s;std::vector<ms5::FixedDataResource> windows;std::string error;
if(ms5::step_stage_buffer_frame(ram,windows,s,ports,error)||ram!=old||!same(s,saved)||ports.size()!=1||ports[0].size!=1||ports[0].address!=0xabcdef01||ports[0].value!=0x23456789||error.empty())return 1;}
// A successful port-free normal frame replaces the old ports vector.
std::vector<std::uint8_t> r(65536,0);put(r,0xdc88,0x10db88,4);ms5::StageBufferFrameState s;std::vector<ms5::FixedDataResource> w;std::vector<ms5::VideoPortWrite> p(1);std::string e;if(!ms5::step_stage_buffer_frame(r,w,s,p,e)||!p.empty())return 2;std::cout<<"5atomic errors and successful port replacement passed\n";}
'''
def atomic_check(root):
    folder=root/'artifacts/stage_buffer_frame';path=folder/'atomic_probe.cpp';exe=folder/'atomic_probe';path.write_text(ATOMIC_SOURCE);command=['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(root/'engine/include'),str(path),str(root/'engine/src/stage_buffer_frame.cpp'),str(root/'engine/src/sprite_submit_execution.cpp'),'-o',str(exe)];p=subprocess.run(command,capture_output=True,text=True);assert p.returncode==0,p.stderr;p=subprocess.run([str(exe)],capture_output=True,text=True);assert p.returncode==0,(p.returncode,p.stdout,p.stderr);return dict(cases=5,success_port_replacement=True,source_sha256=sha(path.read_bytes()),binary_sha256=sha(exe.read_bytes()),compiler=subprocess.run(['c++','--version'],capture_output=True,text=True).stdout,stdout=p.stdout.strip())

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256;exe=root/'build/step_stage_buffer_frame';assert sha(exe.read_bytes())==BINARY_SHA256;cases,resources=build_cases(root);files=tuple(root/r['file'] for r in resources);folder=root/'artifacts/stage_buffer_frame';folder.mkdir(parents=True,exist_ok=True);negative=negative_checks(root,cases,resources,files);atomic=atomic_check(root)
    if '--negative-only'in sys.argv:print(json.dumps(dict(negative_cases=len(negative),direct_API_atomic_cases=atomic['cases'])));return
    inputs,oracle=provenance(root),oracle_provenance();path=folder/'observation.json';raw=path.read_bytes();native=json.loads(raw);assert native['source']==source and native['inputs']==inputs and native['oracle']==oracle and native['failure'] is None and not native['program_code_modified'] and not native['physical_bank_payload_modified'] and not native['in_call_SR_read'];assert native['cases']==len(cases)==len(native['results'])==659 and native['phases']==695
    assert musashi_provenance(root)==native['musashi_normal_comparison']['oracle'] and native['musashi_normal_comparison']['cases']==337
    proof_indexes=[]
    for proof in native['musashi_normal_comparison']['results']:
        i=proof['case_index'];c=cases[i];assert not c['debug'] and 'sequence'not in c;ram,regs=fixture(c,resources);phase=native['results'][i]['phases'][0]
        assert proof['input_ram_sha256']==sha(ram) and proof['ram_sha256']==phase['ram_sha256'] and proof['result']=={k:phase['result'][k] for k in KEYS} and proof['final_pc']==RETURN and proof['final_a7']==STACK+4 and not phase['port_count'];proof_indexes.append(i)
    assert proof_indexes==[i for i,c in enumerate(cases) if not c['debug'] and 'sequence'not in c] and len(proof_indexes)==337
    inp,out,ports=(folder/n for n in ('input.bin','cpp.bin','cpp.ports.bin'));previous=None;rows=[];calls=collections.Counter();phasecounts=collections.Counter();visible_sources=collections.Counter();omissions=[];toggle_alias=0;pointer_alias=0;first_live=0;second_no_reread=0
    for i,(c,row) in enumerate(zip(cases,native['results'])):
        assert row['fixture']==c and row['case_index']==i;ram,regs=fixture(c,resources) if not c.get('sequence_position',0) else (bytearray(previous[0]),list(previous[1]));state=initial(regs,c['bank'] if not c.get('sequence_position',0) else previous[2])
        for phase in row['phases']:
            for w in phase['external_RAM_writes']:rawbytes=bytes.fromhex(w['raw_hex']);ram[w['address']-BASE:w['address']-BASE+len(rawbytes)]=rawbytes
            assert phase['incoming']==state and phase['input_ram_sha256']==sha(ram) and phase['mmio_reads']==0
            expected=(folder/phase['ram_file']).read_bytes();expectedports=(folder/phase['ports_file']).read_bytes();assert sha(expected)==phase['ram_sha256'] and sha(expectedports)==phase['ports_sha256'] and len(expectedports)==9*phase['port_count']
            inp.write_bytes(ram);ports.write_bytes(b'previous ports must be replaced');p=invoke(exe,state,inp,out,ports,files);assert p.returncode==0 and inp.read_bytes()==ram,(i,c,phase['phase_name'],p.stderr);parsed=json.loads(p.stdout);cpp=out.read_bytes();cppports=ports.read_bytes();assert cpp==expected and cppports==expectedports and parsed==dict(phase['result'],port_count=phase['port_count']),(i,c,phase['phase_name'],parsed,phase['result'])
            phasecounts[parsed['phase']]+=1;calls.update(hex(pc) for pc in phase['pcs']);pending=parsed['phase'];assert phase['final_a7']==(STACK+4 if not pending else STACK-(34 if pending==1 else 22)) and phase['final_pc']==(WAIT_PC if pending else RETURN)
            events=[struct.unpack_from('>BII',cppports,a) for a in range(0,len(cppports),9)];assert events==[(2,0x2ffff2,0x1000),(2,0x2ffff0,0)]*(len(events)//2)
            if pending:assert parsed['saved_slot_a4']==0x10daf8+8*parsed['saved_slot_d7'] and parsed['saved_a6']==0x106f01
            else:assert not any(parsed[k] for k in SAVED) and parsed['a6']==0x106f01 and all(parsed['d'+str(k)]==0 for k in range(8))
            if c['family']=='source-window-visible-first-sprite' and phase['phase_name']=='begin':assert phase['sprite_inputs'][0]['d0']==0x40 and any(w['pc']==0xcdfc for w in phase['RAM_writes']);visible_sources[c['source_role']]+=1
            if c['family']=='mixed-bank3-reset-then-bank2-live-slots':assert phase['banked_reads'] and {r['bank'] for r in phase['banked_reads']}=={2,3} and phase['sprite_inputs'][0]['d0']==0x40 and phase['sprite_inputs'][2]['d0']==0x40
            if phase['phase_name']=='first_ready':
                assert 0x4b7e2 in phase['pcs'] and 0x4b798 not in phase['pcs'];assert phase['sprite_inputs'][0]['d0']==0xfff000e0;first_live+=1
            if phase['phase_name']=='second_ready':assert 0x4b7e2 not in phase['pcs'] and 0xcd58 not in phase['pcs'];second_no_reread+=1
            if not pending:
                shifts=[w for w in phase['RAM_writes'] if 0x4ab04<=w['pc']<=0x4ab22];assert len(shifts)==16 and [w['address'] for w in shifts]==list(range(int.from_bytes(ram[0xdc88:0xdc8c],'big'),int.from_bytes(ram[0xdc88:0xdc8c],'big')+32,2));assert len([w for w in phase['RAM_writes'] if w['pc']==0x4ab32])==1
                if c['ring']==0x10d744 and ram[0xd744]&0x80:assert cpp[0xd744]&0x80;toggle_alias+=1
                if c['ring']==0x10dc88:assert any(w['address']==0x10dc88 for w in shifts);pointer_alias+=1
            if not c['debug'] and len(omissions)<4:
                inp.write_bytes(ram);p=invoke(exe,state,inp,out,ports,());assert p.returncode==0 and out.read_bytes()==cpp and ports.read_bytes()==cppports and json.loads(p.stdout)==parsed;omissions.append(i)
            state={k:parsed[k] for k in KEYS+ARGS};ram=bytearray(cpp);rows.append(dict(case_index=i,phase_name=phase['phase_name'],ram_sha256=sha(cpp),ports_sha256=sha(cppports),port_count=phase['port_count'],result=parsed,external_RAM_writes=phase['external_RAM_writes']))
        if 'sequence'in c:previous=(bytes(ram),[state[k] for k in KEYS],state['bank'])
    assert len(rows)==695 and first_live==10 and second_no_reread==8 and toggle_alias and pointer_alias and set(visible_sources)=={'RAM','fixed','bank2','bank3'} and phasecounts[1]==20 and phasecounts[2]==16
    assert native['branch_successor_counts']==branch_counts(native['results'])
    both=[p for p in BRANCHES if p!=0xcdb2];assert all(len(native['branch_successor_counts'][hex(p)])==2 for p in both)
    directory_checks=[]
    for role in ('fixed','bank2','bank3'):
        i=next(i for i,c in enumerate(cases) if c['family']=='source-window-visible-first-sprite' and c['source_role']==role);c=cases[i];ram,regs=fixture(c,resources);state=initial(regs,c['bank']);inp.write_bytes(ram);resource=next(r for r in resources if r['role']==role);p=invoke(exe,state,inp,out,ports,((root/resource['file']).parent,));phase=native['results'][i]['phases'][0]
        assert p.returncode==0 and inp.read_bytes()==ram and out.read_bytes()==(folder/phase['ram_file']).read_bytes() and ports.read_bytes()==(folder/phase['ports_file']).read_bytes() and json.loads(p.stdout)==dict(phase['result'],port_count=phase['port_count']),(role,p.stderr);directory_checks.append(dict(role=role,case_index=i))
    assert provenance(root)==inputs and oracle_provenance()==oracle and musashi_provenance(root)==native['musashi_normal_comparison']['oracle'] and sha(exe.read_bytes())==BINARY_SHA256 and path.read_bytes()==raw and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report=dict(source=source,oracle=oracle,musashi_normal_comparison=native['musashi_normal_comparison'],inputs=inputs,binary_sha256=BINARY_SHA256,native_observation_sha256=sha(raw),cases=len(cases),phases=len(rows),negative_cases=len(negative),direct_API_atomicity=atomic,native_call_counts=dict(calls),native_branch_successor_counts=native['branch_successor_counts'],both_outcomes_branches=both,phase_counts=dict(phasecounts),source_visible_first_submission_counts=dict(visible_sources),toggle_changed_by_prior_LSR_cases=toggle_alias,pointer_self_alias_cases=pointer_alias,first_resume_live_dims_flags=first_live,second_resume_skips_dims_flags=second_no_reread,resource_omission_cases=omissions,directory_checks=directory_checks,full_RAM_14_registers_bank_phase_savedmetadata_orderedports_equal=True,positive_input_RAM_preserved=True,source_resources_core_binary_tools_unchanged=True,pending_chains=14,two_wait_chains=4,fresh_second_only_wait_chains=4,later_slot_pending_chains=2,actual_output_normal_chain_calls=4,normal_chain_prior_output_calls=3,normal_chain_host_updates=[],results=rows,negative_results=negative,scope=native['scope']+' Three existing source-verified literal8-byte resource probes are consumed with offsetcancellation to forcevisiblefirstsubmission. They are not logicalsource-record extent claims. RAM0010shadow intentionally1234 independenthardwarebank. Mixedslots readbank3,reset2,thenbank2. IndependentMusashi337fullnormalcalls agree, never usedforMMIO. DirectAPIerrorspreserveRAM/allstate/priorports and successreplacesports. Firstholdcallbackunknownisrestoredbeforesecondfreshsubmission; secondholdunknownretainedwithnootheractiveslots. No natural scheduling/IRQ support claim.')
    path=folder/'verification.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),phases=len(rows),negative_cases=len(negative),direct_API_atomic_cases=atomic['cases'],sha256=sha(path.read_bytes()))))
if __name__=='__main__':main()
