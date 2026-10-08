"""Original whole49fc6 opcode10 versus actual full-state CLI, including same-CPU waits."""
import collections
import json
import os
from pathlib import Path
import tempfile

import observe_animation_indexed_execution as original
import observe_animation_indexed_fixed_scripts as fixed
from verify_animation_execution import FIELDS, initial, invoke, parse, apply_changes
from pack_animation_control import build as pack_control
from pack_animation_branch import extract, pack
from verify_animation_sound_execution import initial as sound_initial, invoke as sound_invoke, parse as sound_parse
from verify_animation_control_execution import raw_window

NATIVE_SHA='db3247ceba5327719b84882b7d1abe006f0e30c87d28642ed7c2f9a9f75a6508'
FIXED_SHA='7f50c9d4ddf4023e47dd22abc6849cbd6322bd4916f2e620a04a2ca78b61fd37'
def digest(path):return original.sha(path.read_bytes())
def expected(info):
    result=initial(info['result'])
    if info['waiting']:
        p=info['pending'];result.update(phase=3,waiting=True,saved_a0=p['saved_a0'],saved_a1=p['saved_a1'],
            saved_bank=p['saved_bank'],saved_list_end=p['list_end'])
    result['carry']=info['carry'];return result

def audit(root,program,source,is_fixed=False):
    native_folder=root/('artifacts/animation_indexed_fixed_scripts' if is_fixed else 'artifacts/animation_indexed_execution_native')
    report_path=native_folder/'observation.json';native=json.loads(report_path.read_text())
    assert digest(report_path)==(FIXED_SHA if is_fixed else NATIVE_SHA)
    assert native['source']==source and native['oracle']==original.oracle_provenance()
    assert native['failure'] is None and not any(native[k] for k in ('original_program_modified','in_call_SR_read','Cpp_comparison_performed'))
    hashes={str(report_path.relative_to(root)):digest(report_path)}
    for name,value in native['inputs'].items():assert digest(root/name)==value,name;hashes[name]=value
    static=json.loads((native_folder/'source.json').read_text());assert static['source']==source
    saved=original.CODE_RANGES
    try:
        if is_fixed:original.CODE_RANGES=saved+fixed.EXTRA_RANGES
        assert static['ranges']==[list(x) for x in original.CODE_RANGES]
        instructions=[]
        for a,b in original.CODE_RANGES:instructions.extend(original.disassemble_range(program,a,b-a,a))
        assert static['instructions']==instructions
        branches={r['cpu_address'] for r in instructions if r['mnemonic'].startswith('b') and not r['mnemonic'].startswith(('bra','bsr','btst','bclr'))}
        if is_fixed:
            base,script,commands=extract(program);s=static['fixed_script']
            assert s['cpu_address']==s['rom_offset']==base==0x65f56 and s['size']==len(script)==876
            assert s['commands']==commands and s['sha256']==original.sha(script)==fixed.SCRIPT_SHA
            assert static['group']==fixed.GROUP
            for row in [static['caller']]+static['group_evidence']:
                raw=bytes.fromhex(row['raw']);assert raw==program[row['rom_offset']:row['rom_offset']+len(raw)]
        else:
            s=static['raw_fixed_table'];data=program[s['rom_offset']:s['rom_offset']+s['size']]
            assert s['cpu_address']==s['rom_offset']==0x4a76c and s['size']==512
            assert data.hex()==s['raw'] and original.sha(data)==s['sha256']
        cases=fixed.cases() if is_fixed else original.cases();assert len(cases)==len(native['results'])==native['cases']==(30 if is_fixed else 846)
        observer=original.Observer(program,branches);phase_count=port_count=0
        for index,(case,row) in enumerate(zip(cases,native['results'])):
            assert row['case_index']==index and row['fixture']==case
            values=fixed.fixture(program,case,index) if is_fixed else original.fixture(program,case,index)
            ram,regs=values[:2];observer.prepare(ram,regs)
            for position,phase in enumerate([row] if is_fixed else row['phases']):
                if position:observer.mutate(phase['host_changes'])
                info,before,output,ports=observer.run();trace=info.pop('trace');original.validate_restore(trace)
                assert all(phase[k]==value for k,value in info.items()),(index,position)
                assert before==(native_folder/phase['input_ram_file']).read_bytes()
                assert output==(native_folder/phase['ram_file']).read_bytes()
                assert ports==(native_folder/phase['ports_file']).read_bytes()
                assert trace==json.loads((native_folder/phase['trace_file']).read_text())
                for name,value in phase['files'].items():
                    path=native_folder/name;assert digest(path)==value,name;hashes[str(path.relative_to(root))]=value
                phase_count+=1;port_count+=len(ports)//9
        assert phase_count==native['phases']==(30 if is_fixed else 854)
        assert port_count==native['total_native_ports']==(300 if is_fixed else 3564)
    finally:original.CODE_RANGES=saved
    return native,hashes,branches

def compare(root,folder,program,exe,native,resources,is_fixed=False):
    src=root/('artifacts/animation_indexed_fixed_scripts' if is_fixed else 'artifacts/animation_indexed_execution_native')
    rows=[];artifacts={};resumes=0
    for row in native['results']:
        index=row['case_index'];case=row['fixture']
        values=fixed.fixture(program,case,index) if is_fixed else original.fixture(program,case,index)
        ram,regs=values[:2];state=initial(regs)
        for position,phase in enumerate([row] if is_fixed else row['phases']):
            if position:ram=apply_changes(ram,phase['host_changes']);resumes+=1
            assert ram==(src/phase['input_ram_file']).read_bytes()
            label='fixed' if is_fixed else phase['phase'];prefix='%s_%03d_%s'%('fixed' if is_fixed else 'primary',index,label)
            inp,out,ports,state_path=(folder/(prefix+s) for s in ('_input.bin','_cpp.bin','_ports.bin','_state.json'))
            inp.write_bytes(ram);out.write_bytes(b'old');ports.write_bytes(b'old')
            rr=[] if label=='hold' else resources
            result=invoke(exe,state,inp,out,ports,rr);assert not result.returncode,(prefix,result.stderr)
            actual=parse(result.stdout);assert actual==expected(phase),(prefix,actual,expected(phase))
            assert out.read_bytes()==(src/phase['ram_file']).read_bytes()
            assert ports.read_bytes()==(src/phase['ports_file']).read_bytes() and inp.read_bytes()==ram
            state_path.write_text(result.stdout)
            files={str(p.relative_to(root)):digest(p) for p in (inp,out,ports,state_path)};artifacts.update(files)
            rows.append(dict(case_index=index,phase=label,result=actual,files=files,previous_actual_CPP_output_carried=bool(position),
                host_changes=[] if is_fixed else phase['host_changes'],resource_files=[str(p.relative_to(root)) for p in rr],port_count=len(ports.read_bytes())//9))
            state=dict(actual);state.pop('carry');ram=out.read_bytes()
    assert resumes==(0 if is_fixed else 8)
    return rows,artifacts

def supplements(root,folder,program,branches,exe,resources):
    observer=original.Observer(program,branches);rows=[];artifacts={}
    for index,(selector,field) in enumerate((s,i) for s in (0x92,0xa7,0xac) for i in (0,4)):
        case=dict(original.cases()[0],selector=selector,index=field,length=0xfff8,a6=0x108000)
        ram,regs,details=original.fixture(program,case,index);data=bytearray(ram)
        # Keep all signed selected addresses in supported RAM; source canonical
        # fixtures intentionally have a lower script base suitable for skips.
        header=0x10e000;record=bytes(data[0x5804:0x580c])
        data[header-original.BASE:header-original.BASE+4]=data[0x5800:0x5804]
        original.put(data,case['a6']+0x26-original.BASE,4,header)
        details.update(list_base=header+4,list_end=header-4)
        original.put(data,details['list_end']-original.BASE,2,0)
        shaped=(((details['field_offset']&0xff00)|details['live_field_byte'])<<3)&65535
        displacement=shaped if shaped<0x8000 else shaped-65536
        assert shaped<case['length'] and displacement<0
        target=details['list_base']+displacement;assert original.BASE<=target and target+8<=original.BASE+65536
        original.put(data,target-original.BASE,8,int.from_bytes(record,'big'))
        assert data[details['field_address']-original.BASE]==details['live_field_byte']
        ram=bytes(data);observer.prepare(ram,regs);info,before,output,ports=observer.run();trace=info.pop('trace')
        original.validate_restore(trace);assert not info['waiting'] and before==ram
        draw=next(b for b in trace['boundaries'] if b['pc']==0x4a10c);assert draw['registers']['a1']==target+1
        prefix='supplement_%02d'%index;inp=folder/(prefix+'_input.bin');out=folder/(prefix+'_cpp.bin');pout=folder/(prefix+'_cpp_ports.bin')
        inp.write_bytes(ram);out.write_bytes(b'old');pout.write_bytes(b'old')
        result=invoke(exe,initial(regs),inp,out,pout,resources);assert not result.returncode,(prefix,result.stderr)
        actual=parse(result.stdout);assert actual==expected(info)
        assert out.read_bytes()==output and pout.read_bytes()==ports and inp.read_bytes()==ram
        payloads={prefix+'_native.bin':output,prefix+'_native_ports.bin':ports,prefix+'_trace.json':(json.dumps(trace,indent=2)+'\n').encode(),prefix+'_state.json':result.stdout.encode()}
        for name,content in payloads.items():(folder/name).write_bytes(content)
        files={str(p.relative_to(root)):digest(p) for p in [inp,out,pout]+[folder/name for name in payloads]};artifacts.update(files)
        rows.append(dict(fixture=case,details=details,shaped_offset=shaped,selected_address=target,result=actual,files=files,port_count=len(ports)//9,
            scope='Separate syntheticRAM negative signed selectedaddress fixture; immutableoriginalcode andactualfixedselector table.'))
    return rows,artifacts

def sound_cli_chains(root,folder,program,exe,native,resources):
    rows=[];hashes={};resumes=0
    src=root/'artifacts/animation_indexed_execution_native'
    for row in native['results']:
        if not row['fixture']['pending']:continue
        index=row['case_index'];ram,regs,details=original.fixture(program,row['fixture'],index);state=sound_initial(regs)
        for position,phase in enumerate(row['phases']):
            if position:ram=apply_changes(ram,phase['host_changes']);resumes+=1
            assert ram==(src/phase['input_ram_file']).read_bytes()
            prefix='sound_cli_%03d_%s'%(index,phase['phase'])
            inp,out,ports,stdout=(folder/(prefix+suffix) for suffix in ('_input.bin','_cpp.bin','_ports.bin','_state.json'))
            inp.write_bytes(ram);out.write_bytes(b'old');ports.write_bytes(b'old')
            rr=[] if phase['phase']=='hold' else resources
            result=sound_invoke(exe,state,0,inp,out,ports,rr);assert not result.returncode,(prefix,result.stderr)
            actual=sound_parse(result.stdout)
            wanted=dict(expected(phase),callback_saved_a0=0,callback_sound_phase=0,callback_saved_low=0,callback_waiting=False,external_reads=0)
            assert actual==wanted,(prefix,actual,wanted)
            assert out.read_bytes()==(src/phase['ram_file']).read_bytes()
            assert ports.read_bytes()==(src/phase['ports_file']).read_bytes() and inp.read_bytes()==ram
            stdout.write_text(result.stdout)
            files={str(p.relative_to(root)):digest(p) for p in (inp,out,ports,stdout)};hashes.update(files)
            rows.append(dict(case_index=index,phase=phase['phase'],result=actual,files=files,host_changes=phase['host_changes'],
                previous_actual_CPP_output_carried=bool(position),resource_files=[str(p.relative_to(root)) for p in rr],port_count=len(ports.read_bytes())//9))
            ram=out.read_bytes();state=dict(actual);state.pop('carry');state.pop('external_reads')
    assert len(rows)==12 and resumes==8
    return rows,hashes

def negatives(root,folder,program,exe,resources,native):
    ram,regs,details=original.fixture(program,original.cases()[0],0);state=initial(regs);rows=[]
    held=next(r for r in native['results'] if r['fixture']['pending'])['phases'][1]
    pending=expected(held);pending.pop('carry')
    pending_ram=(root/'artifacts/animation_indexed_execution_native'/held['ram_file']).read_bytes()
    ready=bytearray(pending_ram);original.put(ready,0x8d34,2,pending['d4']&65535);ready=bytes(ready)
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp,out,ports=(work/x for x in ('input','output','ports'))
        def reject(label,payload=ram,st=state,rr=None,source=None,destinations=None,reason=None):
            inp.write_bytes(payload);out.write_bytes(b'preserved-output');ports.write_bytes(b'preserved-ports')
            rr=resources if rr is None else rr;src=inp if source is None else source;dst=(out,ports) if destinations is None else destinations
            watched={p:p.read_bytes() for p in [inp,out,ports,src]+list(dst)+list(rr) if p.exists() and p.is_file()}
            result=invoke(exe,st,src,*dst,rr);assert result.returncode and not result.stdout,(label,result.stderr)
            if reason is not None:assert reason in result.stderr,(label,reason,result.stderr)
            assert all(p.read_bytes()==data for p,data in watched.items()),label
            rows.append(dict(label=label,files_preserved=True,error=result.stderr.strip()))
        for value in ('-1','4294967296','0x','1x',''):reject('parser-saved-list-end-'+repr(value),st=dict(state,saved_list_end=value))
        for changes in ({'saved_list_end':1},{'phase':3},{'phase':1,'waiting':True,'saved_list_end':1},{'phase':4}):reject('bad-fresh-metadata-'+str(changes),st=dict(state,**changes))
        for changes in ({'phase':0},{'phase':1},{'waiting':False},{'a5':0x108002}):reject('bad-pending-'+str(changes),payload=pending_ram,st=dict(pending,**changes),rr=[])
        reject('missing-selector-table',rr=[])
        table=0x4a76c+0x1e*2;partial=work/'partial';partial.write_bytes(raw_window(table,program[table:table+1]))
        reject('partial-selector-WORD',rr=[partial]);adjacent=work/'adjacent';adjacent.write_bytes(raw_window(table+1,program[table+1:table+2]))
        reject('split-selector-WORD',rr=[partial,adjacent])
        duplicate=work/'duplicate';duplicate.write_bytes(resources[0].read_bytes());reject('distinct-file-duplicate-window',rr=[resources[0],duplicate])
        overlap=work/'overlap';overlap.write_bytes(raw_window(table,program[table:table+2]));reject('overlapping-selector-window',rr=[resources[0],overlap])
        data=bytearray(ram);data[0x5804]=0x18;reject('selected-opcode-not04',payload=bytes(data))
        data=bytearray(ram);original.put(data,0x2026,4,0x105801);data[0x5801:0x5805]=bytes.fromhex('101e0028');reject('unaligned-length-WORD',payload=bytes(data))
        data=bytearray(ram);original.put(data,0x2026,4,0x10fffc);data[0xfffc:]=bytes.fromhex('101e0028');reject('selected-opcode-outside-RAM',payload=bytes(data))
        data=bytearray(ram);a6=0x100000
        original.put(data,0x26,4,0x105800);original.put(data,0x17,1,0);data[0x5801]=0x96
        assert int.from_bytes(program[0x4a898:0x4a89a],'big')&0x8000
        reject('reached-field-below-RAM',payload=bytes(data),st=dict(state,a6=a6))
        data=bytearray(ram);original.put(data,0x9152,4,0);reject('late-producer-callback-invalid',payload=bytes(data))
        reject('late-resume-list-end-next-fetch110000',payload=ready,st=dict(pending,saved_list_end=0x110000),rr=[],reason='fixed animation script read')
        reject('late-resume-restored-A0-invalid',payload=ready,st=dict(pending,saved_a0=0xffffffff),rr=[],reason='aligned complete reached RAM span')
        for i in (0,4,8,12,16,20,24,28,32):
            data=bytearray(resources[0].read_bytes());data[i]^=1;bad=work/('corrupt-'+str(i));bad.write_bytes(data)
            reject('resource-corruption-'+str(i),rr=[bad])
        reject('bad-supplied-resource-on-resourcefree-hold',payload=pending_ram,st=pending,rr=[bad])
        for size in (0,65535,65537):reject('RAM-size-'+str(size),payload=bytes(size))
        reject('missing-input',source=work/'missing');reject('input-directory',source=work)
        reject('output-directory',destinations=(work,ports));reject('ports-directory',destinations=(out,work))
        reject('same-input-output',destinations=(inp,ports));reject('same-input-ports',destinations=(out,inp));reject('same-outputs',destinations=(out,out))
        for resource in resources:
            reject('resource-output-alias-'+resource.name,destinations=(resource,ports))
            reject('resource-ports-alias-'+resource.name,destinations=(out,resource))
        for kind in ('hardlink','symlink'):
            alias=work/kind
            if kind=='hardlink':os.link(inp,alias)
            else:alias.symlink_to(inp)
            reject('input-output-'+kind,destinations=(alias,ports))
        fifo=work/'fifo';os.mkfifo(fifo)
        reject('FIFO-input',source=fifo);reject('FIFO-output',destinations=(fifo,ports));reject('FIFO-ports',destinations=(out,fifo));reject('FIFO-resource',rr=[fifo])
        fresh=work/'fresh';reject('second-output-failure-cleanup',destinations=(fresh,fifo));assert not fresh.exists()
        folded=work/'INPUT';insensitive=folded.exists() and os.path.samefile(inp,folded)
        if insensitive:
            reject('casefold-input-output',destinations=(folded,ports))
            a,b=work/'new-output',work/'NEW-OUTPUT';reject('casefold-two-new-outputs',destinations=(a,b));assert not a.exists() and not b.exists()
    return rows,dict(case_insensitive_filesystem=insensitive,casefold_alias_tests='passed' if insensitive else 'not applicable')

def main():
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/animation_indexed_execution';folder.mkdir(parents=True,exist_ok=True)
    report=folder/'verification.json';report.unlink(missing_ok=True)
    program,source=original.load_verified_program(root);assert original.sha(program)==original.SOURCE_SHA256
    native,artifacts,branches=audit(root,program,source);fixed_native,fixed_hashes,unused=audit(root,program,source,True);artifacts.update(fixed_hashes)
    packed,manifest=pack_control(root);runtime=root/'extracted/runtime/animation_control'
    for name,data in packed.items():assert (runtime/name).read_bytes()==data
    base,script,commands=extract(program);ms5a=root/'extracted/runtime/animation_065f56.ms5a'
    assert ms5a.read_bytes()==pack(b'MS5A',base,script)
    resources=[runtime/'control_04276c.ms5d',runtime/'operands_06431a.ms5d',ms5a];exe=root/'build/step_animation_execution'
    names=['tools/verify_animation_indexed_execution.py','tools/verify_animation_execution.py','tools/verify_animation_control_execution.py','tools/verify_animation_sound_execution.py',
        'tools/pack_animation_control.py','tools/pack_animation_branch.py','engine/tools/step_animation_execution.cpp','engine/tools/step_animation_sound_execution.cpp','build/step_animation_sound_execution',
        'engine/src/animation_execution.cpp','engine/include/ms5/animation_execution.h','engine/src/object_sound_lookup.cpp','engine/include/ms5/object_sound_lookup.h',
        'engine/src/sound_word_execution.cpp','engine/include/ms5/sound_word_execution.h','engine/src/sound_byte_execution.cpp','engine/include/ms5/sound_byte_execution.h',
        'engine/src/sprite_submit_execution.cpp','engine/include/ms5/sprite_submit_execution.h','engine/include/ms5/sprite_producer.h',
        'engine/include/ms5/scene_map_transfer.h','engine/include/ms5/video_port.h','engine/src/animation_resource.cpp','engine/include/ms5/animation_resource.h',
        'engine/src/fixed_data_resource.cpp','engine/include/ms5/fixed_data_resource.h','Makefile','build/step_animation_execution']
    names.extend(manifest['provenance']['inputs']);names.extend(str((runtime/name).relative_to(root)) for name in packed);names.append(str(ms5a.relative_to(root)))
    inputs={name:digest(root/name) for name in names}
    primary,cpp_hashes=compare(root,folder,program,exe,native,resources[:1]);artifacts.update(cpp_hashes)
    real,cpp_hashes=compare(root,folder,program,exe,fixed_native,resources,True);artifacts.update(cpp_hashes)
    extra,extra_hashes=supplements(root,folder,program,branches,exe,resources[:1]);artifacts.update(extra_hashes)
    sound_rows,sound_hashes=sound_cli_chains(root,folder,program,root/'build/step_animation_sound_execution',native,resources[:1]);artifacts.update(sound_hashes)
    rejected,case_probe=negatives(root,folder,program,exe,resources,native)
    for name,value in {**inputs,**artifacts}.items():assert digest(root/name)==value,name
    assert original.sha((root/source['path']).read_bytes())==original.SOURCE_SHA256 and original.oracle_provenance()==native['oracle']
    result=dict(source=source,oracle=native['oracle'],inputs=inputs,native_and_CPP_artifacts=artifacts,
        primary_observation_sha256=NATIVE_SHA,fixed_observation_sha256=FIXED_SHA,
        primary_cases=846,primary_phases=len(primary),previous_actual_CPP_output_resumes=8,
        fixed_script_cases=len(real),signed_selected_address_supplements=extra,sound_CLI_phase3_phases=len(sound_rows),sound_CLI_results=sound_rows,
        sound_CLI_previous_actual_CPP_output_resumes=8,sound_CLI_ordered_ports=sum(r['port_count'] for r in sound_rows),
        primary_ordered_ports=sum(r['port_count'] for r in primary),fixed_ordered_ports=sum(r['port_count'] for r in real),
        supplement_ordered_ports=sum(r['port_count'] for r in extra),primary_results=primary,fixed_results=real,negative_cases=rejected,case_alias_probe=case_probe,
        full_RAM_15_registers_metadata_carry_ports_equal=True,
        scope='Original846syntheticRAM indexed cases/854phases plus30known fixed65f56 script cases and6separate negative-signed-selected-address cases. '
            'Allprimary/fixednativephases reexecuted;8CPPresumes carrypreviousactualoutputs plusonlylistedhostRAMchanges. '
            'Phase3hold isresourcefree;MS5A/MS5D actuallyconsumed inknownfixedscript. BothCLIs compareall4waitchains; soundCLI12phases/8resumes keepcallbackmetadata/externalreads0. '
            'No naturalgameplay/allselector-length/all8fixedlists/IRQ/physicalmirror/fullCCR or native-success claim forcheckederrors.')
    report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(primary_cases=846,primary_phases=len(primary),fixed_cases=len(real),supplements=len(extra),resumes=8,
        sound_CLI_phases=len(sound_rows),negative_cases=len(rejected),sha256=digest(report))))

if __name__=='__main__':main()
