"""Seven field opcode whole-original/native versus actual animation CLI verification."""
import collections
import itertools
import json
import os
from pathlib import Path
import tempfile

import observe_animation_field_execution as original
import observe_animation_indexed_execution as draw_native
from verify_animation_execution import initial,invoke,parse
from verify_animation_control_execution import raw_window
from pack_animation_control import build as pack_control
from pack_animation_fields import build as pack_fields,SPEC,CALLER,CALLER_RAW

NATIVE_SHA='8ce1f6051cd06310e7e3e321f8ad9bbb879714ceee4381e8662883b936f3e508'
native=original.native

def digest(path):return native.sha(path.read_bytes())
def expected(info):return dict(initial(info['result']),carry=info['carry'])

def audit(root,program,source):
    folder=root/'artifacts/animation_field_native';path=folder/'observation.json';report=json.loads(path.read_text())
    assert digest(path)==NATIVE_SHA and report['source']==source and report['oracle']==native.oracle_provenance()
    assert report['failure'] is None and not any(report[k] for k in ('original_program_modified','in_call_SR_read','Cpp_comparison_performed'))
    hashes={str(path.relative_to(root)):digest(path)}
    for name,value in report['inputs'].items():assert digest(root/name)==value,name;hashes[name]=value
    saved_ranges,saved_boundaries=native.RANGES,native.BOUNDARIES
    try:
        native.RANGES+=original.EXTRA_RANGES;native.BOUNDARIES+=original.EXTRA_BOUNDARIES
        static=json.loads((folder/'source.json').read_text());assert static['source']==source
        assert static['ranges']==[list(x) for x in native.RANGES] and static['boundaries']==list(native.BOUNDARIES)
        instructions=[]
        for a,b in native.RANGES:instructions.extend(native.disassemble_range(program,a,b-a,a))
        assert instructions==static['instructions']
        for region in static['data_ranges']:
            assert region['cpu_address']==region['rom_offset']
            assert native.sha(program[region['rom_offset']:region['rom_offset']+region['size']])==region['sha256']
        branches={r['cpu_address'] for r in instructions if r['mnemonic'].startswith('b') and not r['mnemonic'].startswith(('bra','bsr','btst','bclr'))}
        observer=native.Observer(program,branches);row_index=0;excluded=[];ports_count=0
        for index,case in enumerate(original.cases(program)):
            try:ram,regs,details=original.fixture(program,case,index)
            except ValueError as error:
                excluded.append(dict(case_index=index,fixture=case,reason=str(error),native_executed=False,success=False));continue
            row=report['results'][row_index];assert row['case_index']==index and row['fixture']==case and row['details']==details and row['incoming']==regs
            output,ports,info,trace=observer.run(ram,regs);original.validate(case,details,trace)
            assert all(row[k]==value for k,value in info.items()),index
            assert ram==(folder/row['input_ram_file']).read_bytes()
            assert output==(folder/row['ram_file']).read_bytes() and ports==(folder/row['ports_file']).read_bytes()
            assert trace==json.loads((folder/row['trace_file']).read_text())
            for name,value in row['files'].items():
                p=folder/name;assert digest(p)==value,name;hashes[str(p.relative_to(root))]=value
            row_index+=1;ports_count+=len(ports)//9
        assert row_index==report['cases']==818 and report['excluded_fixtures']==excluded and len(excluded)==173
        assert ports_count==report['total_native_ports']==3272
    finally:native.RANGES,native.BOUNDARIES=saved_ranges,saved_boundaries
    return report,hashes,branches

def compare(root,folder,exe,report,resources):
    rows=[];hashes={};src=root/'artifacts/animation_field_native'
    for row in report['results']:
        index=row['case_index'];inp=folder/('primary_%04d_input.bin'%index);out=folder/('primary_%04d_cpp.bin'%index)
        ports=folder/('primary_%04d_ports.bin'%index);stdout=folder/('primary_%04d_state.json'%index)
        ram=(src/row['input_ram_file']).read_bytes();inp.write_bytes(ram);out.write_bytes(b'old');ports.write_bytes(b'old')
        rr=[] if row['fixture']['opcode'] in (0x34,0x38) else resources
        result=invoke(exe,initial(row['incoming']),inp,out,ports,rr);assert not result.returncode,(index,result.stderr)
        actual=parse(result.stdout);assert actual==expected(row),(index,actual,expected(row))
        assert out.read_bytes()==(src/row['ram_file']).read_bytes()
        assert ports.read_bytes()==(src/row['ports_file']).read_bytes() and inp.read_bytes()==ram
        stdout.write_text(result.stdout);files={str(p.relative_to(root)):digest(p) for p in (inp,out,ports,stdout)};hashes.update(files)
        rows.append(dict(case_index=index,result=actual,files=files,resource_files=[str(p.relative_to(root)) for p in rr],port_count=len(ports.read_bytes())//9))
    return rows,hashes

def save_supplement(root,folder,exe,label,ram,regs,info,trace,output,ports,resources,fixture):
    inp,out,pout,stdout=(folder/(label+suffix) for suffix in ('_input.bin','_cpp.bin','_cpp_ports.bin','_state.json'))
    inp.write_bytes(ram);out.write_bytes(b'old');pout.write_bytes(b'old')
    result=invoke(exe,initial(regs),inp,out,pout,resources);assert not result.returncode,(label,result.stderr)
    actual=parse(result.stdout);assert actual==expected(info),(label,actual,expected(info))
    assert out.read_bytes()==output and pout.read_bytes()==ports and inp.read_bytes()==ram
    stdout.write_text(result.stdout)
    payloads={label+'_native.bin':output,label+'_native_ports.bin':ports,label+'_trace.json':(json.dumps(trace,indent=2)+'\n').encode()}
    for name,data in payloads.items():(folder/name).write_bytes(data)
    files={str(p.relative_to(root)):digest(p) for p in [inp,out,pout,stdout]+[folder/name for name in payloads]}
    return dict(label=label,fixture=fixture,result=actual,native_info=info,files=files,port_count=len(ports)//9),files

def length_one_supplement(root,folder,program,branches,exe,resources):
    case=dict(original.cases(program)[0],opcode=0x2c,selector=0x1e,length=2,field=0,relative=0,alias='none')
    ram,regs,details=original.fixture(program,case,0);data=bytearray(ram)
    native.put(data,case['script']+2,2,1);native.put(data,case['script']+4,3,0);ram=bytes(data)
    saved_ranges,saved_boundaries=native.RANGES,native.BOUNDARIES
    try:
        native.RANGES+=original.EXTRA_RANGES;native.BOUNDARIES+=original.EXTRA_BOUNDARIES
        observer=native.Observer(program,branches);output,ports,info,trace=observer.run(ram,regs)
        selected=next(r for r in trace['reads'] if r['pc']==0x4a3fc)
        assert selected['address']==case['script']+4 and selected['size']==2 and selected['value']==0
        publication=next(w for w in trace['ordered_writes'] if w['pc']==0x4a278)
        assert publication['value']==case['script']+5
    finally:native.RANGES,native.BOUNDARIES=saved_ranges,saved_boundaries
    return save_supplement(root,folder,exe,'length_one_selected_WORD',ram,regs,info,trace,output,ports,resources,
        dict(opcode=0x2c,length=1,relative=0,terminal_overlaps_selected_low_zero_BYTE=True,scope='Legal overlap deliberately excluded by primary controlledfixture builder, not impossible native behavior.'))

def fixed_script_supplements(root,folder,program,exe,resources):
    assert program[CALLER:CALLER+len(CALLER_RAW)]==CALLER_RAW
    script=program[SPEC['cpu']:SPEC['end']];assert native.sha(script)==SPEC['payload_sha256']
    saved_ranges,saved_boundaries=draw_native.CODE_RANGES,draw_native.BOUNDARIES
    rows=[];hashes={}
    try:
        draw_native.CODE_RANGES+=((0x4a3b8,0x4a3de),)+original.EXTRA_RANGES
        draw_native.BOUNDARIES+=(0x4a27e,0x4a28e,0x4a276)
        instructions=[]
        for a,b in draw_native.CODE_RANGES:instructions.extend(native.disassemble_range(program,a,b-a,a))
        branches={r['cpu_address'] for r in instructions if r['mnemonic'].startswith('b') and not r['mnemonic'].startswith(('bra','bsr','btst','bclr'))}
        observer=draw_native.Observer(program,branches)
        for index,(field,timer) in enumerate(itertools.product((0,1,0x80,0xff),(0,0x100,0xffff))):
            case=dict(draw_native.cases()[0],timer=timer,index=0)
            ram,regs,details=draw_native.fixture(program,case,index);data=bytearray(ram)
            for address,size,value in ((0x102026,4,SPEC['cpu']),(0x102020,2,0xf2),(0x1020a0,1,field)):
                native.put(data,address,size,value)
            ram=bytes(data);observer.prepare(ram,regs);info,before,output,ports=observer.run();trace=info.pop('trace')
            assert before==ram and not info['waiting'];draw_native.validate_restore(trace)
            assert any(r['kind']=='fixed' and r['address']==SPEC['cpu'] for r in trace['reads'])
            writes=[w for w in trace['ordered_writes'] if w['pc']==0x4a28e]
            assert writes and all(w['address']==0x1020b0 and w['size']==1 and w['value'] in (0x35,0x49) for w in writes)
            assert any(b['pc']==0x4a10c for b in trace['boundaries'])
            row,files=save_supplement(root,folder,exe,'known_script_%02d'%index,ram,regs,info,trace,output,ports,resources,
                dict(live_object_a0=field,timer=timer,controlled_group=0xf2,script_cpu=SPEC['cpu'],script_payload_sha256=SPEC['payload_sha256'],
                    caller_cpu=CALLER,caller_raw=CALLER_RAW.hex(),scope='Actualimmutablefixedscript withsyntheticcanonicalobject/validqueue andcontrolledgroup; no naturalgroupbinding claim.'))
            rows.append(row);hashes.update(files)
    finally:draw_native.CODE_RANGES,draw_native.BOUNDARIES=saved_ranges,saved_boundaries
    return rows,hashes

def negatives(root,folder,program,exe,resources,report):
    base=next(r for r in report['results'] if r['fixture']['opcode']==0x18 and r['fixture']['selector']==0)
    src=root/'artifacts/animation_field_native';ram=(src/base['input_ram_file']).read_bytes();state=initial(base['incoming']);rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp,out,ports=(work/x for x in ('input','output','ports'))
        def reject(label,payload=ram,st=state,rr=None,source=None,destinations=None,reason=None):
            inp.write_bytes(payload);out.write_bytes(b'preserved-output');ports.write_bytes(b'preserved-ports')
            rr=resources if rr is None else rr;source=inp if source is None else source;destinations=(out,ports) if destinations is None else destinations
            watched={p:p.read_bytes() for p in [inp,out,ports,source]+list(destinations)+list(rr) if p.exists() and p.is_file()}
            result=invoke(exe,st,source,*destinations,rr);assert result.returncode and not result.stdout,(label,result.stderr)
            if reason is not None:assert reason in result.stderr,(label,result.stderr)
            assert all(p.read_bytes()==data for p,data in watched.items()),label
            rows.append(dict(label=label,files_preserved=True,error=result.stderr.strip()))
        for op in (0x18,0x1c,0x20,0x24,0x2c):
            row=next(r for r in report['results'] if r['fixture']['opcode']==op)
            payload=(src/row['input_ram_file']).read_bytes();st=initial(row['incoming'])
            reject('missing-table-'+hex(op),payload=payload,st=st,rr=[],reason='fixed animation data read')
            table=row['details']['table_address'];partial=work/('partial-'+str(op));partial.write_bytes(raw_window(table,program[table:table+1]))
            reject('partial-table-WORD-'+hex(op),payload=payload,st=st,rr=[partial],reason='fixed animation data read')
        seen=set()
        for excluded in report['excluded_fixtures']:
            case=excluded['fixture'];key=(case['opcode'],excluded['reason'])
            if case['opcode'] not in (0x1c,0x20) or key in seen:continue
            seen.add(key);data=bytearray(ram);body=bytes((case['opcode'],case['selector']))+case['value'].to_bytes(2 if case['opcode']==0x1c else 4,'big')
            native.put(data,case['script'],len(body),int.from_bytes(body,'big'));native.put(data,case['script']+len(body),2,0)
            reject('reached-invalid-destination-'+hex(case['opcode'])+'-'+excluded['reason'],payload=bytes(data),reason='aligned complete reached RAM span')
        data=bytearray(ram);native.put(data,0x100026,4,0x104000);native.put(data,0x100017,1,0)
        native.put(data,0x104000,4,int.from_bytes(bytes.fromhex('1c960001'),'big'))
        reject('reached-destination-below-RAM',payload=bytes(data),st=dict(state,a6=0x100000),reason='aligned complete reached RAM span')
        for op,body in ((0x18,bytes.fromhex('18800000')),(0x1c,bytes.fromhex('1c008001')),(0x20,bytes.fromhex('200081234567')),
                        (0x24,bytes.fromhex('2400')),(0x34,bytes.fromhex('34ff8001')),(0x38,bytes.fromhex('38ff8001'))):
            data=bytearray(ram);start=0x110000-len(body);native.put(data,0x108026,4,start);native.put(data,start,len(body),int.from_bytes(body,'big'))
            reject('late-write-then-next-fetch110000-'+hex(op),payload=bytes(data),reason='fixed animation script read')
        data=bytearray(ram);native.put(data,0x108026,4,0x10fff8);native.put(data,0x10fff8,6,int.from_bytes(bytes.fromhex('2c1e00020002'),'big'))
        native.put(data,0x10807d,1,0)
        reject('late2c-publication-then-next-fetch110000',payload=bytes(data),reason='fixed animation script read')
        for op,body in ((0x18,bytes.fromhex('18800000')),(0x1c,bytes.fromhex('1c000001')),(0x20,bytes.fromhex('200000000001')),
                        (0x34,bytes.fromhex('34ff0001')),(0x38,bytes.fromhex('38ff0001')),(0x2c,bytes.fromhex('2c1e0002'))):
            data=bytearray(ram);native.put(data,0x108026,4,0x104001);native.put(data,0x104001,len(body),int.from_bytes(body,'big'))
            reject('unaligned-source-WORD-LONG-'+hex(op),payload=bytes(data),reason='unaligned or overflowing animation script read')
        duplicate=work/'duplicate';duplicate.write_bytes(resources[0].read_bytes());reject('ambiguous-data-window',rr=[resources[0],duplicate])
        overlap=work/'overlap';overlap.write_bytes(raw_window(0x4a76c,program[0x4a76c:0x4a76e]));reject('overlap-data-window',rr=[resources[0],overlap])
        for at in (0,4,8,12,16,20,24,28,32):
            data=bytearray(resources[0].read_bytes());data[at]^=1;bad=work/('corrupt-'+str(at));bad.write_bytes(data)
            reject('corrupt-resource-'+str(at),rr=[bad])
        for patch in ({'phase':4},{'saved_list_end':1},{'phase':3},{'saved_a0':1}):reject('metadata-'+str(patch),st=dict(state,**patch))
        for size in (0,65535,65537):reject('RAM-size-'+str(size),payload=bytes(size))
        reject('missing-input',source=work/'missing');reject('input-directory',source=work)
        reject('output-directory',destinations=(work,ports));reject('ports-directory',destinations=(out,work))
        reject('input-output-alias',destinations=(inp,ports));reject('input-ports-alias',destinations=(out,inp));reject('same-outputs',destinations=(out,out))
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
            reject('casefold-input-output',destinations=(folded,ports));a,b=work/'new-output',work/'NEW-OUTPUT'
            reject('casefold-two-new-outputs',destinations=(a,b));assert not a.exists() and not b.exists()
    return rows,dict(case_insensitive_filesystem=insensitive,casefold_alias_tests='passed' if insensitive else 'not applicable')

def main():
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/animation_field_execution';folder.mkdir(parents=True,exist_ok=True)
    report_path=folder/'verification.json';report_path.unlink(missing_ok=True)
    program,source=native.load_verified_program(root);assert native.sha(program)==native.SOURCE_SHA256
    report,artifacts,branches=audit(root,program,source)
    files,manifest=pack_control(root);control=root/'extracted/runtime/animation_control'
    for name,data in files.items():assert (control/name).read_bytes()==data
    field_files,field_manifest=pack_fields(root);runtime=root/'extracted/runtime/animation_fields'
    for name,data in field_files.items():assert (runtime/name).read_bytes()==data
    resources=[control/'control_04276c.ms5d',runtime/SPEC['file']];exe=root/'build/step_animation_execution'
    names=['tools/verify_animation_field_execution.py','tools/observe_animation_indexed_execution.py','tools/verify_animation_execution.py','tools/verify_animation_control_execution.py',
        'tools/pack_animation_control.py','tools/pack_animation_fields.py','engine/tools/step_animation_execution.cpp',
        'engine/src/animation_execution.cpp','engine/include/ms5/animation_execution.h','engine/src/object_sound_lookup.cpp','engine/include/ms5/object_sound_lookup.h',
        'engine/src/sound_word_execution.cpp','engine/include/ms5/sound_word_execution.h','engine/src/sound_byte_execution.cpp','engine/include/ms5/sound_byte_execution.h',
        'engine/src/sprite_submit_execution.cpp','engine/include/ms5/sprite_submit_execution.h','engine/include/ms5/sprite_producer.h',
        'engine/include/ms5/scene_map_transfer.h','engine/include/ms5/video_port.h','engine/src/animation_resource.cpp','engine/include/ms5/animation_resource.h',
        'engine/src/fixed_data_resource.cpp','engine/include/ms5/fixed_data_resource.h','Makefile','build/step_animation_execution']
    names.extend(manifest['provenance']['inputs']);names.extend(field_manifest['provenance']['inputs'])
    names.extend(str((control/name).relative_to(root)) for name in files);names.extend(str((runtime/name).relative_to(root)) for name in field_files)
    inputs={name:digest(root/name) for name in names}
    primary,cpp_hashes=compare(root,folder,exe,report,resources[:1]);artifacts.update(cpp_hashes)
    one,one_hashes=length_one_supplement(root,folder,program,branches,exe,resources[:1]);artifacts.update(one_hashes)
    known,known_hashes=fixed_script_supplements(root,folder,program,exe,resources);artifacts.update(known_hashes)
    rejected,case_probe=negatives(root,folder,program,exe,resources,report)
    for name,value in {**inputs,**artifacts}.items():assert digest(root/name)==value,name
    assert native.sha((root/source['path']).read_bytes())==native.SOURCE_SHA256 and native.oracle_provenance()==report['oracle']
    result=dict(source=source,oracle=report['oracle'],inputs=inputs,native_and_CPP_artifacts=artifacts,native_observation_sha256=NATIVE_SHA,
        primary_cases=len(primary),primary_original_cases_reexecuted=818,primary_ordered_ports=sum(r['port_count'] for r in primary),
        cases_by_opcode=report['cases_by_opcode'],primary_excluded_fixtures=report['excluded_fixtures'],
        length_one_selected_WORD_supplement=one,known_fixed_script_cases=len(known),known_fixed_script_results=known,
        known_fixed_script_ordered_ports=sum(r['port_count'] for r in known),primary_results=primary,negative_cases=rejected,case_alias_probe=case_probe,
        full_RAM_15_registers_metadata_carry_ports_equal=True,
        scope='Originalwhole49fc6 sevenfieldopcodes on818controlledliveRAM fixtures,reexecutedbeforeactualCLIcomparison. '
            'Separatelegal length1/index0selectedWORD overlap and12actualfixed3e808 script cases compareoriginalRAM15RcarryPVCtraces. '
            'MS5Dwide rawtable andMS5Afixedscript actuallyconsumed;fixedscript object/group/queue remaincontrolledsyntheticinputs. '
            'Primaryexclusionsdescribe invalidspans/alignment orcontrolledfixturelimitations,notallnativeimpossibility. '
            'No otheropcodecompletion/allselector-relative-address combinations/naturalgroupbinding/gameplay/IRQ/physicalmirror/fullCCR/native-success claimforcheckederrors.')
    report_path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(primary_cases=len(primary),known_script_cases=len(known),length_one_supplements=1,negative_cases=len(rejected),sha256=digest(report_path))))

if __name__=='__main__':main()
