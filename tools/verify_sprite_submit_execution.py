"""Actual sprite-submit CLI snapshots, same-output resumes and atomic failures."""
import collections
import json
import os
from pathlib import Path
import subprocess
import tempfile

from disassemble_program import load_verified_program
from observe_sprite_submit_execution import (BASE,STACK,RETURN,WAIT_PC,KEYS,SOURCE_SHA256,
    build_cases,fixture,sha,provenance,oracle_provenance,assert_native_writes,branch_counts)


def invoke(exe,regs,waiting,status,inp,out):
    return subprocess.run([str(exe)]+list(map(str,regs))+[str(int(waiting)) if isinstance(waiting,bool) else str(waiting),str(status),str(inp),str(out)],capture_output=True,text=True)


def negative_checks(root):
    exe=root/'build/execute_sprite_submit';case=build_cases()[0]
    case=dict(case,x=0,y=0x40)
    rows=[]
    with tempfile.TemporaryDirectory(dir=root/'artifacts/sprite_submit_execution') as directory:
        work=Path(directory);inp,out=work/'in.bin',work/'out.bin'
        def reject(label,current=None,regs_override=None,waiting=0,status=2,ram_override=None,input_bytes=None):
            ram,regs=fixture(case if current is None else current)
            if regs_override is not None:regs=regs_override
            if ram_override is not None:ram=ram_override
            if input_bytes is not None:ram=input_bytes
            inp.write_bytes(ram);out.write_bytes(b'existing-output-preserved')
            before=out.read_bytes()
            result=invoke(exe,regs,waiting,status,inp,out)
            assert result.returncode and not result.stdout,(label,result.stdout,result.stderr)
            assert inp.read_bytes()==ram and out.read_bytes()==before,label
            rows.append(dict(failure=label,input_output_preserved=True,native_executed=False,error=result.stderr.strip()))
        ram,regs=fixture(case)
        for index,value in ((0,-1),(1,'0x'),(4,'4294967296'),(8,' 1'),(13,'1x')):
            bad=regs.copy();bad[index]=value;reject('bad-register-'+str(index),regs_override=bad)
        for value in (-1,2,'0x'):reject('bad-waiting-'+str(value),waiting=value)
        for value in (-1,4,'0x'):reject('bad-status-'+str(value),status=value)
        for size in (0,65535,65537):reject('RAM-size-'+str(size),input_bytes=bytes(size))
        for unknown in (0,0x106000,0xffffffff):
            ram,regs=fixture(case);ram[0x9152:0x9156]=unknown.to_bytes(4,'big')
            reject('unknown-begin-callback-'+hex(unknown),ram_override=ram)
        clipped=dict(case,y=0)
        ram,regs=fixture(clipped);ram[0x9152:0x9156]=(0x106000).to_bytes(4,'big')
        reject('unknown-callback-even-before-clipping',current=clipped,ram_override=ram)
        for normal in (1,0x74cc):reject('late-normal-invalid-index-'+hex(normal),current=dict(case,normal=normal))
        for count in (1,0x70b2):reject('late-deferred-invalid-index-'+hex(count),current=dict(case,deferred=True,count=count))
        for offset in (1,0x8000,0x80ca):reject('late-record-write-invalid-'+hex(offset),current=dict(case,offset=offset))
        # Synthetic public resume snapshots are error checks, not captured native histories.
        ram,regs=fixture(case);ram[0x8d34:0x8d36]=bytes(2);regs[4]&=0xffff0000
        for d6,a1,label in ((1,0x108b34,'odd-source-index'),(0,0x110000,'out-of-RAM-source'),(0,0xffffffff,'overflow-source')):
            bad=regs.copy();bad[6]=d6;bad[9]=a1
            reject('synthetic-resume-'+label,regs_override=bad,waiting=1,status=3,ram_override=ram)
        for label in ('same-path','hardlink','symlink'):
            ram,regs=fixture(case);inp.write_bytes(ram)
            dest=inp if label=='same-path' else work/label
            if label=='hardlink':os.link(inp,dest)
            if label=='symlink':dest.symlink_to(inp)
            result=invoke(exe,regs,False,2,inp,dest)
            assert result.returncode and inp.read_bytes()==ram and dest.read_bytes()==ram,label
            rows.append(dict(failure='input-output-'+label,input_output_preserved=True,native_executed=False))
    return rows


ATOMIC_SOURCE = r'''
#include "ms5/sprite_submit_execution.h"
#include <iostream>
void put(std::vector<std::uint8_t>& r,unsigned int a,unsigned int v) { r[a]=static_cast<std::uint8_t>(v>>8);r[a+1]=static_cast<std::uint8_t>(v); }
bool same(const ms5::SpriteSubmitExecutionState& a,const ms5::SpriteSubmitExecutionState& b) {
    if(a.waiting!=b.waiting)return false;
    for(unsigned int i=0;i<8;++i)if(a.registers.d[i]!=b.registers.d[i])return false;
    for(unsigned int i=0;i<5;++i)if(a.registers.a[i]!=b.registers.a[i])return false;
    return true;
}
int main() {
    for(unsigned int test=0;test<6;++test) {
        std::vector<std::uint8_t> ram(65536,0x55);
        ram[0x9152]=0;ram[0x9153]=0;ram[0x9154]=0xcd;ram[0x9155]=0x50;
        put(ram,0x8d34,0);put(ram,0x8d36,0);put(ram,0x8d38,0);put(ram,0x8d3a,0);
        put(ram,0x914e,0);put(ram,0x8b36,12);
        ms5::SpriteSubmitExecutionState state;
        for(unsigned int i=0;i<8;++i)state.registers.d[i]=0xabcd0000+i;
        for(unsigned int i=0;i<5;++i)state.registers.a[i]=0xdead0000+i;
        state.registers.d[0]=0x40;state.registers.d[1]=0;
        if(test==0)ram[0x9155]=0x52;
        if(test==1)put(ram,0x8b36,1);
        if(test==2)put(ram,0x8d38,0x74cc);
        if(test==3) { state.registers.d[1]=0x40;put(ram,0x914e,0x70b2); }
        if(test==4) { state.waiting=true;state.registers.d[4]=0;state.registers.d[6]=1;state.registers.a[1]=0x108b34; }
        if(test==5)put(ram,0x8b36,0x8000);
        const std::vector<std::uint8_t> before=ram;
        const ms5::SpriteSubmitExecutionState saved=state;
        ms5::SpriteSubmitStatus status=ms5::SpriteFull;std::string error;
        if(ms5::execute_sprite_submit(ram,state,status,error) || error.empty() || ram!=before || !same(state,saved) || status!=ms5::SpriteFull)return 1;
    }
    std::cout << "6 direct API failure transactions preserve RAM/13regs/waiting/status\n";
}
'''


def atomic_api_checks(root):
    folder=root/'artifacts/sprite_submit_execution';source=folder/'atomic_api_check.cpp';exe=folder/'atomic_api_check'
    source.write_text(ATOMIC_SOURCE)
    command=['c++','-std=c++11','-O2','-Wall','-Wextra','-pedantic','-I'+str(root/'engine/include'),
        str(root/'engine/src/sprite_submit_execution.cpp'),str(source),'-o',str(exe)]
    compiled=subprocess.run(command,capture_output=True,text=True)
    assert compiled.returncode==0 and not compiled.stderr,compiled.stderr
    result=subprocess.run([str(exe)],capture_output=True,text=True)
    assert result.returncode==0,(result.stdout,result.stderr)
    return dict(cases=6,source_file=str(source.relative_to(root)),source_sha256=sha(source.read_bytes()),
        binary_file=str(exe.relative_to(root)),binary_sha256=sha(exe.read_bytes()),compiler_command=command,
        warnings=0,stdout=result.stdout.strip(),scope='Independent direct API failure-state equality, including late queue writes and synthetic caller-provided waiting snapshot; no native invalid access executed.')


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert sha(program)==SOURCE_SHA256
    inputs,oracle=provenance(root),oracle_provenance(root.resolve())
    folder=root/'artifacts/sprite_submit_execution';path=folder/'observation.json';data=path.read_bytes();native=json.loads(data)
    cases=build_cases()
    assert native['source']==source and native['oracle']==oracle and native['inputs']==inputs
    assert native['cases']==len(cases)==len(native['results']) and native['failure'] is None and not native['program_code_modified']
    negatives=negative_checks(root);atomic=atomic_api_checks(root)
    exe=root/'build/execute_sprite_submit';rows=[];resumes=0;statuses=collections.Counter()
    with tempfile.TemporaryDirectory(dir=folder) as directory:
        work=Path(directory);inp,out=work/'in.bin',work/'out.bin'
        for index,(case,expected) in enumerate(zip(cases,native['results'])):
            assert expected['case_index']==index and expected['fixture']==case
            ram,regs=fixture(case);prior=None
            for phase in expected['phases']:
                if prior is not None:
                    ram=bytearray(prior[0]);regs=[prior[1][k] for k in KEYS];resumes+=1
                    for change in phase['external_RAM_writes']:
                        at=change['address']-BASE;raw=bytes.fromhex(change['raw_hex']);assert 0<=at and at+len(raw)<=65536
                        ram[at:at+len(raw)]=raw
                else:assert not phase['external_RAM_writes']
                assert sha(ram)==phase['input_ram_sha256'] and dict(zip(KEYS,regs))==phase['incoming']
                assert phase['mmio_writes']==0
                if phase['waiting']:
                    assert phase['native']['pc']==WAIT_PC and phase['final_a7']==STACK and phase['status']==3
                else:assert phase['native']['pc']==RETURN and phase['final_a7']==STACK+4
                assert_native_writes(phase['status'],phase['RAM_writes'],case['deferred'])
                inp.write_bytes(ram)
                actual=invoke(exe,regs,phase['waiting_in'],phase['status_in'],inp,out)
                assert actual.returncode==0,(index,phase['phase'],case,actual.stderr)
                result=json.loads(actual.stdout)
                expected_json=dict(phase['result'],waiting=phase['waiting'],status=phase['status'])
                original=(folder/phase['ram_file']).read_bytes()
                assert sha(original)==phase['ram_sha256'] and out.read_bytes()==original
                assert result==expected_json,(index,phase['phase'],case,result,expected_json)
                assert inp.read_bytes()==ram
                prior=(out.read_bytes(),result)
                statuses[phase['status']]+=1
                rows.append(dict(case_index=index,phase=phase['phase'],status=phase['status'],waiting=phase['waiting'],
                    full_RAM_14_registers_equal=True,ram_sha256=sha(original)))
    assert dict(sorted(statuses.items()))=={int(k):v for k,v in native['counts_by_status'].items()}
    assert len(rows)==native['phases'] and resumes==2*native['pending_chains']
    rebuilt_branches=branch_counts(native['results'])
    assert rebuilt_branches==native['branch_successor_counts']
    assert provenance(root)==inputs and oracle_provenance(root.resolve())==oracle
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256 and sha(path.read_bytes())==sha(data)
    report=dict(source=source,oracle=oracle,inputs=inputs,native_observation_sha256=sha(data),cases=len(cases),
        phases=len(rows),pending_chains=native['pending_chains'],actual_CLI_resumes=resumes,
        negative_cases=len(negatives),negative_results=negatives,atomic_API_checks=atomic,
        counts_by_status=dict(sorted(statuses.items())),branch_successor_counts=rebuilt_branches,full_RAM_14_registers_equal=True,results=rows,
        scope='ActualCLI fullRAM/14regs/waiting/status equals pinned original Musashi for clip/full/accepted and actual begin-wait-hold-ready chains. '
              'Native wait chains reuse sameCPU without reset; CLI carries its own preceding outputRAM/14regs with only recorded external consumer/callback/prepared/producer RAM changes. '
              'CapturedD4/D6 retained; callback and initial cursor calculation are not replayed after waiting. '
              'Ordered native writes are source-order evidence and alias-sensitive finalRAM is compared; no independent C++write-event trace equality claimed. '
              'Invalid indices/late writes/unknown callbacks preserve existing CLIoutput/input;6 independent directAPI tests check RAM/13regs/waiting/status failure atomicity. '
              'Unsupported memory/callback behavior is rejected only in C++negative tests, never executed on originalROM; no natural callback closure/scheduler/cycle/CCR-equivalence claim.')
    dest=folder/'verification.json';dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(cases),phases=len(rows),pending_chains=native['pending_chains'],actual_CLI_resumes=resumes,
        negative_cases=len(negatives),atomic_API_cases=atomic['cases'],full_RAM_14_registers_equal=True,sha256=sha(dest.read_bytes()))))


if __name__=='__main__':main()
