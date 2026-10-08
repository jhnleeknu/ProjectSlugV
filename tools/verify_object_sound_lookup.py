"""Compare actual47672 CLI/resource loader against unpatched native continuations."""
import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from observe_object_sound_lookup import (Observer, cases, fixture, load_verified_program,
    oracle_provenance, SOURCE_SHA256, KEYS, BASE, RAW_START, RAW_END, RAW_SHA)

NATIVE_SHA='42f093ee7d31dbd3e70b986dd7d7edd7fc409eeb543892ff5c3c6d4494e99f5d'
FIELDS=tuple(KEYS)+('phase','saved_a0','sound_phase','saved_low','waiting','external')
OUTPUT=set(KEYS)|{'phase','saved_a0','sound_phase','saved_low','waiting','external_reads'}

def sha(data):return hashlib.sha256(data).hexdigest()
def digest(path):return sha(path.read_bytes())
def apply_changes(data,changes):
    result=bytearray(data)
    for change in changes:
        at=change['address']-BASE;size=change['size']
        assert 0<=at and at+size<=65536
        result[at:at+size]=change['value'].to_bytes(size,'big')
    return bytes(result)
def expected(phase):
    return dict(phase['result'],phase=int(phase['waiting']),saved_a0=phase['saved_a0'],
        sound_phase=phase['sound_phase'],saved_low=phase['saved_low'],waiting=phase['waiting'],
        external_reads=sum(r['kind']=='external' for r in phase['reads']))
def initial(regs,external):
    return dict(regs,phase=0,saved_a0=0,sound_phase=0,saved_low=0,waiting=False,external=external)
def invoke(exe,state,inp,out,resources):
    args=[str(int(state[k])) if type(state[k]) is bool else str(state[k]) for k in FIELDS]
    return subprocess.run([str(exe)]+args+[str(inp),str(out)]+list(map(str,resources)),
                          capture_output=True,text=True,timeout=3)
def parsed(text):
    def unique(pairs):
        d={}
        for k,v in pairs:assert k not in d;d[k]=v
        return d
    r=json.loads(text,object_pairs_hook=unique)
    assert type(r) is dict and set(r)==OUTPUT
    assert type(r['waiting']) is bool
    assert all(type(v) is int and 0<=v<=0xffffffff for k,v in r.items() if k!='waiting')
    assert r['phase'] in (0,1) and r['sound_phase'] in (0,1,2) and r['saved_low']<=255
    assert r['waiting']==(r['phase']==1)==(r['sound_phase']!=0) and r['external_reads']<=1
    return r

def audit(root,program,source):
    folder=root/'artifacts/object_sound_lookup';path=folder/'observation.json'
    native=json.loads(path.read_text());assert digest(path)==NATIVE_SHA
    assert native['source']==source and native['oracle']==oracle_provenance()
    assert not native['original_program_modified'] and not native['in_call_SR_read'] and native['failure'] is None
    hashes={str(path.relative_to(root)):digest(path)}
    for name,value in native['inputs'].items():assert digest(root/name)==value;hashes[name]=value
    static=json.loads((folder/'source.json').read_text());branches=set()
    for start,end in static['ranges']:
        cursor=start
        for row in static['instructions']:
            if start<=row['cpu_address']<end:
                assert row['cpu_address']==row['rom_offset']==cursor
                assert bytes.fromhex(row['raw'])==program[cursor:cursor+row['size']]
                cursor+=row['size']
                if row['mnemonic'].startswith('b') and row['mnemonic'] not in ('btst.b','bsr.w','bra.b','bra.w'):branches.add(row['cpu_address'])
        assert cursor==end
    observer=Observer(program,branches);phase_count=0;lookups=[];outcomes=collections.defaultdict(collections.Counter)
    for index,(case,row) in enumerate(zip(cases(),native['results'])):
        assert row['case_index']==index and row['fixture']==case
        ram,regs=fixture(case,index);observer.prepare(ram,regs,case['external'])
        for position,phase in enumerate(row['phases']):
            if position:observer.mutate(phase['host_changes'],external=255)
            else:assert not phase['host_changes']
            info,before,output,ports=observer.run()
            assert all(phase[k]==value for k,value in info.items()),(index,phase['phase'])
            assert before==(folder/phase['input_ram_file']).read_bytes()
            assert output==(folder/phase['ram_file']).read_bytes() and ports==(folder/phase['ports_file']).read_bytes()
            for name,value in phase['files'].items():
                p=folder/name;assert digest(p)==value;hashes[str(p.relative_to(root))]=value
            for event in info['reads']:
                if event['kind']=='raw-lookup':lookups.append(event)
            for branch in info['branches']:outcomes[hex(branch['pc'])][hex(branch['next_pc'])]+=1
            phase_count+=1
    assert native['cases']==len(native['results'])==len(cases())==277
    assert native['phases']==phase_count==291 and native['pending_chains']==6
    assert native['observed_branch_successors']=={k:dict(v) for k,v in outcomes.items()}
    assert {r['address'] for r in lookups}==set(range(RAW_START,RAW_END,2)) and len(lookups)==277
    assert sha(program[RAW_START:RAW_END])==RAW_SHA
    for row in lookups:assert row['size']==2 and row['value']==int.from_bytes(program[row['address']:row['address']+2],'big')
    return native,hashes

def negative_checks(root,exe,folder,resource,native):
    rows=[];base,regs=fixture(cases()[0],0);state=initial(regs,0)
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp=work/'input';out=work/'output';marker=b'prior-output'
        def reject(label,st=state,ram=base,resources=None,source=None,destination=None,command=None):
            inp.write_bytes(ram);out.write_bytes(marker)
            src=inp if source is None else source;dst=out if destination is None else destination
            rr=[resource] if resources is None else resources
            watched={p:p.read_bytes() for p in [inp,out,src,dst]+rr if p.exists() and p.is_file()}
            p=invoke(exe,st,src,dst,rr) if command is None else subprocess.run(command,capture_output=True,text=True,timeout=3)
            assert p.returncode and not p.stdout,(label,p.stdout,p.stderr)
            assert all(path.read_bytes()==data for path,data in watched.items()),label
            rows.append(dict(label=label,error=p.stderr.strip(),files_preserved=True))
        for key in FIELDS:
            for bad in ('-1','4294967296','0x','1x',''):
                reject('parser-'+key+'-'+repr(bad),st=dict(state,**{key:bad}))
        for key,bad in (('phase',2),('sound_phase',3),('saved_low',256),('waiting',2),('external',256)):
            reject('range-'+key,st=dict(state,**{key:bad}))
        for size in (0,65535,65537):reject('RAM-size-'+str(size),ram=bytes(size))
        for changes in ({'saved_a0':1},{'sound_phase':1},{'saved_low':1},{'waiting':True},{'phase':1}):
            reject('inconsistent-continuation-'+str(changes),st=dict(state,**changes))
        for a5 in (0,0xffffffff):reject('initial-source-BYTE-span-'+hex(a5),st=dict(state,a5=a5))
        for a5 in (0x108001,0x1176a3):
            payload=bytearray(base)
            payload[regs['a6']+0x7e-BASE]=payload[a5-0x76a4-BASE]
            reject('late-source-WORD-alignment-or-span-'+hex(a5),st=dict(state,a5=a5),ram=bytes(payload))
        payload=bytearray(base);payload[0x1e]=payload[0x95c]
        reject('late-final-output-BYTE-span',st=dict(state,a6=0xfffa0),ram=bytes(payload))
        for a6 in (0,0xffffffff,0x10ff82):reject('object-span-'+hex(a6),st=dict(state,a6=a6))
        sound_case=next((i,c) for i,c in enumerate(cases()) if c['sound'] and c['mode']==0 and not c['wait'])
        sound_ram,sound_regs=fixture(sound_case[1],sound_case[0])
        shifted=bytearray(sound_ram);shifted[0x95e:0x960]=sound_ram[0x95c:0x95e]
        reject('noncanonical-A5-sound',st=initial(dict(sound_regs,a5=0x108002),0),ram=bytes(shifted))
        reject('missing-reached-lookup',resources=[])
        for size in (0,31,32,287,289):
            bad=work/('bad-'+str(size));raw=resource.read_bytes();bad.write_bytes((raw+bytes(300))[:size]);reject('resource-size-'+str(size),resources=[bad])
        for at in (0,4,8,12,16,20,24,28,32,287):
            raw=bytearray(resource.read_bytes());raw[at]^=1;bad=work/('corrupt-'+str(at));bad.write_bytes(raw)
            reject('resource-corruption-'+str(at),resources=[bad])
        # A captured wait permits unavailable lookup until sound finishes.
        pending=next(row for row in native['results'] if row['fixture']['wait'])
        phase=pending['phases'][0];wait_state=expected(phase);wait_state.pop('external_reads');wait_state['external']=255
        pending_ram=(root/'artifacts/object_sound_lookup'/phase['ram_file']).read_bytes()
        for a5 in (0,0x108002,0xffffffff):reject('pending-A5-'+hex(a5),st=dict(wait_state,a5=a5),ram=pending_ram)
        ready=bytearray(pending_ram);ready[0x4d74:0x4d76]=b'\xff\xff'
        reject('post-sound-missing-lookup-rollback',st=wait_state,ram=bytes(ready),resources=[])
        reject('post-sound-source-failure-rollback',st=dict(wait_state,saved_a0=0xffffffff),ram=bytes(ready))
        reject('post-sound-destination-failure-rollback',st=dict(wait_state,a6=0xffffffff),ram=bytes(ready))
        reject('missing-arguments',command=[str(exe)])
        reject('missing-input',source=work/'absent');reject('input-directory',source=work)
        reject('output-directory',destination=work);reject('output-missing-parent',destination=work/'absent'/'out')
        reject('same-RAM-path',destination=inp);reject('output-resource-alias',destination=resource)
        for kind in ('hardlink','symlink'):
            alias=work/kind
            if kind=='hardlink':os.link(inp,alias)
            else:alias.symlink_to(inp)
            reject('RAM-'+kind,destination=alias)
        fifo=work/'fifo';os.mkfifo(fifo)
        reject('FIFO-input',source=fifo);reject('FIFO-output',destination=fifo);reject('FIFO-resource',resources=[fifo])
        fresh=work/'fresh';reject('latefailure-no-new-output',resources=[],destination=fresh);assert not fresh.exists()
        alias=work/'INPUT'
        if alias.exists() and os.path.samefile(alias,inp):reject('case-insensitive-RAM-alias',destination=alias)
    return rows

def main():
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/object_sound_lookup_execution';folder.mkdir(parents=True,exist_ok=True)
    report=folder/'verification.json';report.unlink(missing_ok=True)
    program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    native,artifacts=audit(root,program,source)
    from pack_object_sound_lookup import build,validate_container
    files,manifest=build(root);resource=root/'extracted/runtime/object_sound_lookup/lookup.ms5d'
    for name,data in files.items():assert (resource.parent/name).read_bytes()==data
    assert validate_container(resource.read_bytes())==program[RAW_START:RAW_END]
    exe=root/'build/execute_object_sound_lookup'
    names=['tools/verify_object_sound_lookup.py','tools/pack_object_sound_lookup.py',
        'engine/include/ms5/object_sound_lookup.h','engine/src/object_sound_lookup.cpp','engine/tools/execute_object_sound_lookup.cpp',
        'engine/src/sound_word_execution.cpp','engine/src/sound_byte_execution.cpp','engine/src/fixed_data_resource.cpp',
        'engine/include/ms5/sound_word_execution.h','engine/include/ms5/sound_byte_execution.h','engine/include/ms5/fixed_data_resource.h',
        'engine/include/ms5/scene_map_transfer.h','engine/include/ms5/video_port.h',
        'Makefile','docs/analysis/stage-object-output-wrappers-contract.md','build/execute_object_sound_lookup']
    names.extend(str((resource.parent/name).relative_to(root)) for name in files)
    inputs={name:digest(root/name) for name in names}
    rows=[];resumes=0;no_resource_waits=0;inp=folder/'input.bin';out=folder/'cpp.bin'
    for index,(case,row) in enumerate(zip(cases(),native['results'])):
        ram,regs=fixture(case,index);state=initial(regs,case['external'])
        for position,phase in enumerate(row['phases']):
            if position:
                ram=apply_changes(ram,phase['host_changes']);state['external']=255;resumes+=1
            assert ram==(root/'artifacts/object_sound_lookup'/phase['input_ram_file']).read_bytes()
            inp.write_bytes(ram);out.write_bytes(b'prior')
            rr=[] if phase['waiting'] else [resource]
            process=invoke(exe,state,inp,out,rr);assert not process.returncode,(index,phase['phase'],process.stderr)
            actual=parsed(process.stdout);output=out.read_bytes()
            assert actual==expected(phase),(index,phase['phase'],actual,expected(phase))
            assert output==(root/'artifacts/object_sound_lookup'/phase['ram_file']).read_bytes() and inp.read_bytes()==ram
            path=folder/('cpp_%03d_%s.bin'%(index,phase['phase']));path.write_bytes(output);artifacts[str(path.relative_to(root))]=digest(path)
            rows.append(dict(case_index=index,phase=phase['phase'],result=actual,cpp_ram_file=str(path.relative_to(root)),cpp_ram_sha256=digest(path),
                previous_actual_CPP_output_carried=bool(position),external_status=state['external'],host_changes=phase['host_changes'],lookup_resource_supplied=bool(rr)))
            ram=output;state=dict(actual);state.pop('external_reads');state['external']=case['external'] if not position else 255
            no_resource_waits+=not bool(rr)
    assert len(rows)==291 and resumes==14 and no_resource_waits==14
    rejected=negative_checks(root,exe,folder,resource,native)
    for name,value in {**inputs,**artifacts}.items():assert digest(root/name)==value,name
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256 and oracle_provenance()==native['oracle']
    result=dict(source=source,oracle=native['oracle'],inputs=inputs,native_and_CPP_artifacts=artifacts,
        cases=277,phases=291,previous_actual_CPP_output_resumes=resumes,waiting_without_lookup_resource=no_resource_waits,
        raw_lookup=native['raw_lookup'],negative_cases=rejected,results=rows,full_RAM_15_registers_continuations_external_reads_equal=True,
        source_and_inputs_unchanged=True,scope='Actual CLI loads real MS5D256byte lookup. Unpatched47672/ca70/3af8 fully reexecuted. '
        'Six sameCPU native chains and14C++resumes use previousactual outputs with onlyrecordedRAMwrites and explicitEXTERNAL255. '
        'No resource required on14waitingphases. Checkedfailures preservefiles, not nativeTRAPequivalence. '
        'No fullsoundgatecoverage/naturalIRQ/scheduler/physicalmirror/fullCCR/cycles/wholegame claim.')
    report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=277,phases=291,resumes=resumes,negative_cases=len(rejected),sha256=digest(report))))

if __name__=='__main__':main()
