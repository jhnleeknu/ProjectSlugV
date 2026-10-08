"""Actual animation14/1f CLI versus unpatched same-CPU nested sound evidence."""
import collections
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib

import observe_animation_sound_callback as original
from verify_animation_execution import FIELDS as OLD_FIELDS, apply_changes
from pack_animation_control import build as pack_resources

NATIVE_SHA = '5f8b3d3a71532bd3c99d930ad4e61d9c490cc90036669cd872f9169294043108'
CALLBACK_FIELDS = ('callback_saved_a0','callback_sound_phase','callback_saved_low','callback_waiting')
FIELDS = tuple(OLD_FIELDS)+CALLBACK_FIELDS+('external',)
OUTPUT = (set(FIELDS)-{'external'})|{'carry','external_reads'}


def digest(path):
    return original.sha(path.read_bytes())


def initial(registers):
    return dict(registers,phase=0,saved_a0=0,saved_a1=0,saved_bank=0,waiting=False,saved_list_end=0,
        callback_saved_a0=0,callback_sound_phase=0,callback_saved_low=0,callback_waiting=False)


def expected(info, trace):
    result=initial(info['result'])
    if info['waiting']:
        pending=info['pending']
        result.update(phase=2,saved_a0=pending['outer_a0'],saved_a1=pending['outer_a1'],saved_bank=pending['bank'],
            callback_saved_a0=pending['inner_a0'],callback_sound_phase=pending['sound_phase'],
            callback_saved_low=pending['saved_low'],callback_waiting=True)
    result.update(carry=info['carry'],external_reads=sum(read['kind']=='external' for read in trace['reads']))
    return result


def invoke(exe,state,external,inp,out,ports,resources):
    values=dict(state,external=external)
    args=[str(int(values[key])) if type(values[key]) is bool else str(values[key]) for key in FIELDS]
    return subprocess.run([str(exe)]+args+list(map(str,(inp,out,ports)))+list(map(str,resources)),
        capture_output=True,text=True,timeout=5)


def parse(text):
    def unique(pairs):
        result={}
        for key,value in pairs:
            assert key not in result,key
            result[key]=value
        return result
    result=json.loads(text,object_pairs_hook=unique)
    assert type(result) is dict and set(result)==OUTPUT
    for key in ('waiting','callback_waiting'):assert type(result[key]) is bool
    for key,value in result.items():
        if key not in ('waiting','callback_waiting','carry'):
            assert type(value) is int and 0<=value<=0xffffffff,key
    assert result['phase'] in (0,1,2,3) and result['saved_bank']<=65535
    assert result['callback_sound_phase'] in (0,1,2) and result['callback_saved_low']<=255
    assert result['carry'] is None if result['phase'] else type(result['carry']) is bool
    assert result['waiting']==(result['phase'] in (1,3))
    assert result['callback_waiting']==(result['phase']==2)
    assert result['saved_list_end']==0 if result['phase']!=3 else True
    if result['phase']!=2:
        assert all(result[k]==0 for k in ('callback_saved_a0','callback_sound_phase','callback_saved_low'))
    if result['phase']==0:assert all(result[k]==0 for k in ('saved_a0','saved_a1','saved_bank'))
    return result


def audit(root,program,source):
    folder=root/'artifacts/animation_sound_callback';path=folder/'observation.json'
    native=json.loads(path.read_text());assert digest(path)==NATIVE_SHA
    assert native['source']==source and native['oracle']==original.oracle_provenance()
    assert not native['original_program_modified'] and not native['in_call_SR_read']
    assert not native['Cpp_comparison_performed']
    hashes={str(path.relative_to(root)):digest(path)}
    for name,value in native['inputs'].items():assert digest(root/name)==value;hashes[name]=value
    cases=original.cases();assert len(cases)==len(native['results'])==native['cases']==22
    observer=original.Observer(program);count=0;port_count=0;resumes=0
    for index,(case,row) in enumerate(zip(cases,native['results'])):
        assert row['case_index']==index and row['fixture']==case
        ram,regs=original.fixture(case,index);observer.prepare(ram,regs,case['external'])
        for position,phase in enumerate(row['phases']):
            if position:observer.mutate(phase['host_changes']);resumes+=1
            else:assert not phase['host_changes']
            info,before,output,ports=observer.run();trace=info.pop('trace')
            assert all(phase[key]==value for key,value in info.items()),(index,phase['phase'])
            assert before==(folder/phase['input_ram_file']).read_bytes()
            assert output==(folder/phase['ram_file']).read_bytes()
            assert ports==(folder/phase['ports_file']).read_bytes()
            assert trace==json.loads((folder/phase['trace_file']).read_text())
            for name,value in phase['files'].items():
                path=folder/name;assert digest(path)==value,name;hashes[str(path.relative_to(root))]=value
            assert phase['port_count']==len(ports)//9
            if phase['waiting']:
                assert phase['final_pc']==original.WAIT and phase['carry'] is None
            else:assert phase['final_pc']==original.RETURN and phase['final_a7']==original.STACK+4
            count+=1;port_count+=len(ports)//9
    assert count==native['phases']==30 and resumes==8 and port_count==176
    return native,hashes,port_count


def raw_window(cpu,payload):
    return struct.pack('<4s7I',b'MS5D',1,1,cpu,cpu,len(payload),zlib.crc32(payload),0)+payload


def negatives(root,folder,program,exe,resources,native):
    native_folder=root/'artifacts/animation_sound_callback'
    first=native['results'][0]['phases'][0]
    ram=(native_folder/first['input_ram_file']).read_bytes();state=initial(first['incoming'])
    chain=next(row for row in native['results'] if row['fixture']['wait']==1)
    held=next(phase for phase in chain['phases'] if phase['phase']=='hold')
    trace=json.loads((native_folder/held['trace_file']).read_text())
    pending=expected(held,trace);pending.pop('carry');pending.pop('external_reads')
    pending_ram=(native_folder/held['ram_file']).read_bytes()
    ready=bytearray(pending_ram);original.put(ready,0x104d74,2,0xffff);ready=bytes(ready)
    final_trace=json.loads((native_folder/chain['phases'][-1]['trace_file']).read_text())
    lookup=next(read for read in final_trace['reads'] if read['pc']==0x476aa)
    rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp,out,ports=(work/name for name in ('input','output','ports'))
        sentinel=b'preserved-output'

        def reject(label,st=state,payload=ram,rr=None,external=0,source=None,destinations=None,error_contains=None):
            inp.write_bytes(payload);out.write_bytes(sentinel);ports.write_bytes(sentinel)
            rr=resources if rr is None else rr;source=inp if source is None else source
            destinations=(out,ports) if destinations is None else destinations
            watched={path:path.read_bytes() for path in [inp,out,ports,source]+list(destinations)+list(rr)
                     if path.exists() and path.is_file()}
            result=invoke(exe,st,external,source,*destinations,rr)
            assert result.returncode and not result.stdout,(label,result.stdout,result.stderr)
            if error_contains is not None:assert error_contains in result.stderr,(label,result.stderr)
            assert all(path.read_bytes()==data for path,data in watched.items()),label
            rows.append(dict(label=label,files_preserved=True,error=result.stderr.strip()))

        for key in CALLBACK_FIELDS:
            for value in ('-1','4294967296','0x','1x'):
                reject('parser-'+key+'-'+value,st=dict(state,**{key:value}))
        for value in (-1,256,'0x','1x'):reject('parser-external-'+str(value),external=value)
        for key,value in (('phase',4),('callback_sound_phase',3),('callback_saved_low',256),('callback_waiting',2)):
            reject('range-'+key,st=dict(state,**{key:value}))
        for changes in ({'phase':2},{'callback_saved_a0':1},{'callback_sound_phase':1},
                {'callback_saved_low':1},{'callback_waiting':True},{'saved_list_end':1}):
            reject('inactive-metadata-'+str(changes),st=dict(state,**changes))
        for changes in ({'waiting':True},{'callback_sound_phase':0},{'callback_waiting':False},{'phase':0},{'phase':1}):
            reject('pending-metadata-'+str(changes),st=dict(pending,**changes),payload=pending_ram,rr=[])
        reject('pending-noncanonical-A5',st=dict(pending,a5=0x108002),payload=pending_ram,rr=[])
        reject('late-inner-lookup-missing',st=pending,payload=ready,rr=[],error_contains='fixed object lookup WORD')
        partial=work/'partial-inner-lookup'
        address=lookup['address'];partial.write_bytes(raw_window(address,program[address:address+1]))
        reject('late-inner-lookup-partial-WORD',st=pending,payload=ready,rr=[partial],error_contains='fixed object lookup WORD')
        reject('late-after-outer-restore-next-fetch',st=dict(pending,saved_a1=0x110000),payload=ready,
            error_contains='fixed animation script read')
        reject('late-inner-source-WORD-unaligned',st=dict(pending,callback_saved_a0=0x10095d),payload=ready,
            error_contains='aligned complete reached RAM spans')
        reject('late-inner-object-destination',st=dict(pending,a6=0xffffffff),payload=ready,
            error_contains='aligned complete reached RAM spans')
        reject('fresh-dispatch-missing',rr=[])
        for at in (0,4,8,12,16,20,24,28,32):
            data=bytearray(resources[0].read_bytes());data[at]^=1
            path=work/('bad-resource-'+str(at));path.write_bytes(data)
            reject('bad-resource-'+str(at),rr=[path])
        reject('supplied-corrupt-resource-during-hold',st=pending,payload=pending_ram,rr=[path])
        for size in (0,65535,65537):reject('RAM-size-'+str(size),payload=bytes(size))
        reject('missing-input',source=work/'missing')
        reject('input-directory',source=work)
        reject('output-directory',destinations=(work,ports))
        reject('ports-directory',destinations=(out,work))
        reject('input-output-alias',destinations=(inp,ports))
        reject('input-ports-alias',destinations=(out,inp))
        reject('same-outputs',destinations=(out,out))
        reject('resource-output-alias',destinations=(resources[0],ports))
        reject('resource-ports-alias',destinations=(out,resources[0]))
        for kind in ('hardlink','symlink'):
            alias=work/kind
            if kind=='hardlink':os.link(inp,alias)
            else:alias.symlink_to(inp)
            reject('input-output-'+kind,destinations=(alias,ports))
        fifo=work/'fifo';os.mkfifo(fifo)
        reject('FIFO-input',source=fifo);reject('FIFO-output',destinations=(fifo,ports))
        reject('FIFO-ports',destinations=(out,fifo));reject('FIFO-resource',rr=[fifo])
        fresh=work/'fresh';reject('second-reservation-cleanup',destinations=(fresh,fifo));assert not fresh.exists()
        folded=work/'INPUT';insensitive=folded.exists() and os.path.samefile(inp,folded)
        if insensitive:
            reject('casefold-input-output',destinations=(folded,ports))
            a,b=work/'new-output',work/'NEW-OUTPUT'
            reject('casefold-two-new-outputs',destinations=(a,b));assert not a.exists() and not b.exists()
        case_probe=dict(case_insensitive_filesystem=insensitive,
            casefold_alias_tests='passed' if insensitive else 'not applicable')
    return rows,case_probe


def main():
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/animation_sound_execution'
    folder.mkdir(parents=True,exist_ok=True);report=folder/'verification.json';report.unlink(missing_ok=True)
    program,source=original.load_verified_program(root);assert original.sha(program)==original.SOURCE_SHA256
    native,artifacts,native_ports=audit(root,program,source)
    packed,manifest=pack_resources(root);runtime=root/'extracted/runtime/animation_control'
    for name,data in packed.items():assert (runtime/name).read_bytes()==data,name
    resources=[runtime/'control_04276c.ms5d'];exe=root/'build/step_animation_sound_execution'
    names=['tools/verify_animation_sound_execution.py','tools/verify_animation_execution.py','tools/pack_animation_control.py',
        'engine/tools/step_animation_sound_execution.cpp','engine/src/animation_execution.cpp','engine/include/ms5/animation_execution.h',
        'engine/src/object_sound_lookup.cpp','engine/include/ms5/object_sound_lookup.h',
        'engine/src/sound_word_execution.cpp','engine/include/ms5/sound_word_execution.h',
        'engine/src/sound_byte_execution.cpp','engine/include/ms5/sound_byte_execution.h',
        'engine/src/sprite_submit_execution.cpp','engine/include/ms5/sprite_submit_execution.h',
        'engine/include/ms5/sprite_producer.h','engine/include/ms5/scene_map_transfer.h','engine/include/ms5/video_port.h',
        'engine/src/fixed_data_resource.cpp','engine/include/ms5/fixed_data_resource.h',
        'engine/src/animation_resource.cpp','engine/include/ms5/animation_resource.h','Makefile','build/step_animation_sound_execution']
    names.extend(str((runtime/name).relative_to(root)) for name in packed)
    names.extend(manifest['provenance']['inputs'])
    inputs={name:digest(root/name) for name in names};rows=[];resumes=0
    for row in native['results']:
        index=row['case_index'];case=row['fixture'];ram,regs=original.fixture(case,index);state=initial(regs)
        for position,phase in enumerate(row['phases']):
            if position:ram=apply_changes(ram,phase['host_changes']);resumes+=1
            assert ram==(root/'artifacts/animation_sound_callback'/phase['input_ram_file']).read_bytes()
            prefix='case_%03d_%s'%(index,phase['phase'])
            inp=folder/(prefix+'_input.bin');out=folder/(prefix+'_cpp.bin');ports=folder/(prefix+'_ports.bin')
            inp.write_bytes(ram);out.write_bytes(b'old');ports.write_bytes(b'old')
            rr=[] if phase['phase'] in ('hold','low_hold','high_to_low') else resources
            result=invoke(exe,state,case['external'],inp,out,ports,rr)
            assert not result.returncode,(index,phase['phase'],result.stderr)
            actual=parse(result.stdout)
            trace=json.loads((root/'artifacts/animation_sound_callback'/phase['trace_file']).read_text())
            assert actual==expected(phase,trace),(index,phase['phase'],actual,expected(phase,trace))
            assert out.read_bytes()==(root/'artifacts/animation_sound_callback'/phase['ram_file']).read_bytes()
            assert ports.read_bytes()==(root/'artifacts/animation_sound_callback'/phase['ports_file']).read_bytes()
            assert inp.read_bytes()==ram
            state_file=folder/(prefix+'_state.json');state_file.write_text(result.stdout)
            files={str(path.relative_to(root)):digest(path) for path in (inp,out,ports,state_file)};artifacts.update(files)
            rows.append(dict(case_index=index,phase=phase['phase'],result=actual,files=files,
                host_changes=phase['host_changes'],external_status=case['external'],
                previous_actual_CPP_output_carried=bool(position),resource_files=[str(path.relative_to(root)) for path in rr],
                port_count=len(ports.read_bytes())//9))
            state=dict(actual);state.pop('carry');state.pop('external_reads');ram=out.read_bytes()
    assert len(rows)==native['phases'] and resumes==8
    rejected,case_probe=negatives(root,folder,program,exe,resources,native)
    for name,value in {**inputs,**artifacts}.items():assert digest(root/name)==value,name
    assert original.sha((root/source['path']).read_bytes())==original.SOURCE_SHA256
    assert original.oracle_provenance()==native['oracle']
    result=dict(source=source,oracle=native['oracle'],inputs=inputs,native_and_CPP_artifacts=artifacts,
        native_observation_sha256=NATIVE_SHA,cases=native['cases'],phases=native['phases'],
        original_phases_reexecuted=len(rows),previous_actual_CPP_output_resumes=resumes,
        primary_ordered_ports=sum(row['port_count'] for row in rows),native_ordered_ports=native_ports,
        external_reads=sum(row['result']['external_reads'] for row in rows),
        returned_carry_counts={str(key):value for key,value in collections.Counter(row['result']['carry'] for row in rows).items()},
        results=rows,negative_cases=rejected,case_alias_probe=case_probe,
        full_RAM_15_registers_nested_pending_carry_ports_external_reads_equal=True,
        scope='Whole unpatched49fc6 controlled liveRAM14/1f scripts and actual nested3af8 waits. '
            'Every nativephase reexecuted;8resumes use onlypreviousactualCPP RAM/registers/metadata pluslistedhostRAMchanges. '
            'FixedMS5Ddispatch/lookup actuallyconsumed; holds/high-to-low omitresources. '
            'No naturalallcallbacks/fullgame/IRQ/cycle/physicalmirror/fullCCR or syntheticlateerror native-success claim.')
    report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=result['cases'],phases=len(rows),resumes=resumes,ports=result['primary_ordered_ports'],
        external_reads=result['external_reads'],negative_cases=len(rejected),sha256=digest(report))))


if __name__=='__main__':
    main()
