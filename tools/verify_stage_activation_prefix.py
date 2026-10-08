"""Actual prefix CLI differential against frozen, unpatched native104 evidence."""
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib
from observe_stage_activation_prefix import (BASE,STACK,STACK_START,RETURN,KEYS,
    ENTRY,STOP,SOURCE_SHA256,sha,build_cases,fixture,assert_predictions,
    load_verified_program,oracle_provenance,Observer)
from pack_stage_block_draw import validate_container


def invoke(exe,registers,inp,out,ports,resources=()):
    return subprocess.run([str(exe)]+[str(registers[key]) for key in KEYS]+
        list(map(str,(inp,out,ports)))+list(map(str,resources)),
        capture_output=True,text=True,timeout=3)


def audit(root,program,source):
    folder=root/'artifacts/stage_activation_prefix';path=folder/'observation.json'
    raw=path.read_bytes();native=json.loads(raw);cases=build_cases()
    assert native['source']==source and native['oracle']==oracle_provenance()
    assert native['cases']==native['completed_cases']==len(cases)==len(native['results'])==104
    assert native['prediction_mismatches']==[] and native['total_native_ports']==6576
    assert native['entry_pc']==ENTRY and native['stop_before_pc']==STOP
    assert native['full_RAM_15_registers_ordered_ports_observed']
    assert not native['original_program_modified'] and not native['in_call_SR_read'] and not native['Cpp_comparison_performed'] and not native['callback_returned']
    for name,digest in native['inputs'].items():assert sha((root/name).read_bytes())==digest,name
    static=json.loads((root/'artifacts/stage_activation_static.json').read_bytes())
    assert static['source']==source
    for row in static['instructions']:
        at=row['rom_offset'];assert bytes.fromhex(row['raw'])==program[at:at+row['size']]
    artifacts={str(path.relative_to(root)):sha(raw)};branches={}
    for index,(case,row) in enumerate(zip(cases,native['results'])):
        assert row['case_index']==index and row['fixture']==case
        assert row['stopped_at_partial_boundary'] and not row['callback_returned']
        assert row['final_pc']==STOP and row['final_a7']==STACK and not row['unexpected_reads']
        for key,digest in (('input_ram_file','input_ram_sha256'),('ram_file','ram_sha256'),('ports_file','ports_sha256'),('trace_file','trace_sha256')):
            p=folder/row[key];assert sha(p.read_bytes())==row[digest];artifacts[str(p.relative_to(root))]=row[digest]
        ram=fixture(case);assert (folder/row['input_ram_file']).read_bytes()==ram
        output=(folder/row['ram_file']).read_bytes();ports=(folder/row['ports_file']).read_bytes()
        trace=json.loads((folder/row['trace_file']).read_bytes());pcs=trace['pcs']
        assert pcs[0]==ENTRY and pcs[-1]==STOP and pcs.count(STOP)==1 and RETURN not in pcs
        assert len(pcs)-1==row['instructions']
        replay=bytearray(ram);encoded=[];stack=[];writes=[]
        for event in trace['writes']:
            address,size,value=event['address'],event['size'],event['value']
            assert size in (1,2,4) and 0<=value<1<<(8*size) and event['pc'] in pcs[:-1]
            if event['kind']=='ports':
                assert address==0x3c0000 and size in (2,4)
                encoded.append(struct.pack('>BII',size,address,value))
            elif event['kind']=='ram':
                assert BASE<=address and address+size<=BASE+65536
                replay[address-BASE:address-BASE+size]=value.to_bytes(size,'big');writes.append(event)
            else:
                assert event['kind']=='stack' and STACK_START<=address and address+size<=STACK
                stack.append(event)
        assert bytes(replay)==output and b''.join(encoded)==ports and len(encoded)==row['port_count']
        assert writes==row['RAM_writes'] and len(stack)==row['stack_write_count']
        assert min([e['address'] for e in stack]+[STACK])==row['lowest_stack_write']
        assert row['boundaries'][-1]['pc']==STOP and row['boundaries'][-1]['registers']==row['result']
        before=next(b for b in row['boundaries'] if b['pc']==0x47c48)
        after=next(b for b in row['boundaries'] if b['pc']==0x47c4c)
        evidence=row['parent_read_evidence']
        assert evidence['pc']==0x47c48 and evidence['address']==before['registers']['a6']+0x7c
        assert evidence['effective_byte']==after['registers']['d0']&255
        if case.get('parent_helper_alias'):
            assert evidence['earlier_helper_clear'] in writes and evidence['earlier_helper_clear']['pc']==0x4e25e
            assert evidence['earlier_helper_clear']['address']==0x100a42 and evidence['earlier_helper_clear']['value']==0
            assert pcs.index(0x4e25e)<pcs.index(0x47c48) and evidence['effective_byte']==0
        actual_branches=[dict(pc=pc,next_pc=pcs[i+1]) for i,pc in enumerate(pcs[:-1]) if pc in (0x47c08,0x47c24,0x47c32,0x47c50,0xc3c4)]
        assert actual_branches==row['branches']
        for b in actual_branches:branches[(b['pc'],b['next_pc'])]=branches.get((b['pc'],b['next_pc']),0)+1
        assert_predictions(case,ram,output,row['result'],ports,row)
    assert native['branch_coverage']==[dict(pc=pc,next_pc=next_pc,count=count) for (pc,next_pc),count in sorted(branches.items())]
    return native,raw,cases,artifacts


def negatives(exe,folder,sample,resource):
    rows=[];case_alias={}
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp,out,ports=(work/name for name in ('in.bin','out.bin','ports.bin'))
        regs=sample['incoming'];base=fixture(sample);sentinel=b'unchanged-prefix-output'
        def reject(label,state=regs,ram=base,resources=None,outputs=None,source=None,command=None):
            sources=[resource] if resources is None else resources
            destinations=(out,ports) if outputs is None else outputs
            inp.write_bytes(ram);out.write_bytes(sentinel);ports.write_bytes(sentinel)
            watched={p:p.read_bytes() for p in (inp,out,ports)+tuple(sources)+tuple(destinations) if p.exists() and p.is_file()}
            p=subprocess.run(command,capture_output=True,text=True,timeout=3) if command is not None else invoke(exe,state,inp if source is None else source,*destinations,sources)
            assert p.returncode and not p.stdout,(label,p.stdout,p.stderr)
            assert all(p.read_bytes()==data for p,data in watched.items()),label
            rows.append(dict(label=label,input_resources_outputs_preserved=True,error=p.stderr.strip()))
        for size in (0,65535,65537):reject('RAM-size-'+str(size),ram=bytes(size))
        for key in KEYS:
            for bad in ('-1','0x','4294967296','0x100000000','1x',''):
                reject('parse-'+key+'-'+bad,state=dict(regs,**{key:bad}))
        for a5 in (0,0x107698,0x10a97c,0x110000,0xffffffff):reject('invalid-A5-'+hex(a5),state=dict(regs,a5=a5))
        late=bytearray(base);late[0x10a800+0x5684-BASE]=0
        reject('late-A5-helper-destination-outside-RAM',state=dict(regs,a5=0x10a800),ram=bytes(late))
        for a6 in (0,0x100001,0x10ff82,0x10ff84,0xfffffffe,0xffffffff):reject('invalid-or-late-A6-'+hex(a6),state=dict(regs,a6=a6))
        reject('missing-table',resources=[])
        duplicate=work/'duplicate.ms5d';duplicate.write_bytes(resource.read_bytes())
        reject('duplicate-table-distinct-files',resources=[resource,duplicate])
        original=resource.read_bytes()
        for offset in (0,4,8,12,16,20,24,28,32):
            corrupted=bytearray(original);corrupted[offset]^=1;p=work/('bad-%d.ms5d'%offset);p.write_bytes(corrupted)
            reject('resource-corruption-'+str(offset),resources=[p])
        for start in (0xddfa4,0xddfa5):
            partial=work/('partial-%x.ms5d'%start);payload=original[32+start-0xddfa4:33+start-0xddfa4]
            partial.write_bytes(struct.pack('<4s7I',b'MS5D',1,1,start,start,1,zlib.crc32(payload),0)+payload)
            reject('partial-overlap-'+hex(start),resources=[resource,partial])
        reject('missing-input',source=work/'missing-input');reject('input-directory',source=work)
        reject('missing-resource',resources=[work/'missing-resource']);reject('resource-directory',resources=[work])
        reject('RAM-output-directory',outputs=(work,ports));reject('port-output-directory',outputs=(out,work))
        reject('RAM-output-missing-parent',outputs=(work/'missing'/'out',ports));reject('port-output-missing-parent',outputs=(out,work/'missing'/'ports'))
        reject('input-RAM-output-alias',outputs=(inp,ports));reject('input-port-output-alias',outputs=(out,inp));reject('two-output-alias',outputs=(out,out))
        reject('resource-RAM-output-alias',outputs=(resource,ports));reject('resource-port-output-alias',outputs=(out,resource))
        for kind in ('hardlink','symlink'):
            for target,label in ((inp,'input'),(resource,'resource'),(out,'output')):
                alias=work/(label+'-'+kind)
                if kind=='hardlink':os.link(target,alias)
                else:alias.symlink_to(target)
                reject(label+'-RAM-output-'+kind,outputs=(alias,ports)) if label!='output' else reject('two-output-'+kind,outputs=(out,alias))
                if label!='output':reject(label+'-port-output-'+kind,outputs=(out,alias))
        reject('missing-arguments',command=[str(exe)])
        fifo=work/'fifo';os.mkfifo(fifo)
        reject('FIFO-input',source=fifo);reject('FIFO-resource',resources=[fifo])
        reject('FIFO-RAM-output',outputs=(fifo,ports));reject('FIFO-port-output',outputs=(out,fifo))
        fresh=work/'fresh';reject('new-placeholder-cleanup',outputs=(fresh,fifo));assert not fresh.exists()
        probe=work/'CaseProbe';probe.write_bytes(b'probe');folded=work/'caseprobe'
        insensitive=folded.exists() and os.path.samefile(probe,folded)
        case_alias=dict(case_insensitive_filesystem=insensitive,applicable=insensitive)
        if insensitive:
            first,second=work/'NewOutput',work/'newoutput'
            reject('case-alias-new',outputs=(first,second));assert not first.exists() and not second.exists()
            first.write_bytes(b'');reject('case-alias-existing-empty',outputs=(first,second));assert first.read_bytes()==b''
            case_alias.update(new_alias_placeholders_removed=True,existing_zero_length_preserved=True)
    return rows,case_alias


def supplemental(exe,folder,resource,program,cases):
    observer=Observer(program);rows=[]
    for index,a5 in enumerate((0x108001,0x108002)):
        original=cases[index+1];case=dict(original)
        case['incoming']=dict(original['incoming'],a5=a5)
        case.update(supplemental_family='shifted-A5-live-host-writes',parent_byte=5,signed_previous_byte=128)
        case['host_writes']=[dict(address=a5+0x5684,size=1,value=0),
            dict(address=case['incoming']['a6']+0x7c,size=1,value=5),dict(address=a5-0xcf,size=1,value=128)]
        ram=fixture(case);output,result,ports,trace,info=observer.run(case,ram)
        assert info['final_pc']==STOP and info['final_a7']==STACK and info['parent_read_evidence']['effective_byte']==5
        stem='supplemental-%d'%index
        files=dict(input_ram_file=stem+'-input.bin',native_ram_file=stem+'-native.bin',
            native_ports_file=stem+'-native.ports.bin',trace_file=stem+'-native.trace.json')
        payloads=dict(input_ram_file=ram,native_ram_file=output,native_ports_file=ports,trace_file=(json.dumps(trace,indent=2)+'\n').encode())
        for key,data in payloads.items():(folder/files[key]).write_bytes(data)
        inp,out,pout=(folder/(stem+suffix) for suffix in ('-input.bin','-cpp.bin','-cpp.ports.bin'))
        out.write_bytes(b'old');pout.write_bytes(b'old')
        p=invoke(exe,case['incoming'],inp,out,pout,[resource])
        assert not p.returncode,(case,p.stderr)
        assert json.loads(p.stdout)==result and inp.read_bytes()==ram and out.read_bytes()==output and pout.read_bytes()==ports
        rows.append(dict(fixture=case,result=result,port_count=len(ports)//9,native_info=info,
            files=files,hashes={key:sha(data) for key,data in payloads.items()}))
    return rows


def main():
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/stage_activation_prefix'
    report=folder/'verification.json';report.unlink(missing_ok=True)
    exe=root/'build/initialize_stage_activation_prefix';resource=root/'extracted/runtime/stage_block_draw/block_table.ms5d'
    names=('tools/verify_stage_activation_prefix.py','tools/pack_stage_block_draw.py','build/initialize_stage_activation_prefix',
        'engine/tools/initialize_stage_activation_prefix.cpp','engine/src/stage_activation_prefix.cpp','engine/include/ms5/stage_activation_prefix.h',
        'engine/src/stage_block_draw.cpp','engine/include/ms5/stage_block_draw.h','engine/src/fixed_data_resource.cpp',
        'engine/include/ms5/fixed_data_resource.h','engine/include/ms5/object_restart_execution.h','engine/include/ms5/video_port.h',
        'Makefile','extracted/runtime/stage_block_draw/block_table.ms5d','extracted/runtime/stage_block_draw/manifest.json')
    inputs={name:sha((root/name).read_bytes()) for name in names}
    program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    native,raw,cases,artifacts=audit(root,program,source)
    assert validate_container(resource.read_bytes())==program[0xddfa4:0xddfdc]
    inp,out,ports=(folder/name for name in ('cpp-input.bin','cpp.bin','cpp.ports.bin'));rows=[]
    for case,row in zip(cases,native['results']):
        ram=fixture(case);inp.write_bytes(ram);out.write_bytes(b'old');ports.write_bytes(b'old')
        p=invoke(exe,case['incoming'],inp,out,ports,[resource])
        assert not p.returncode,(row['case_index'],case,p.stderr)
        parsed=json.loads(p.stdout)
        assert parsed==row['result'] and inp.read_bytes()==ram and out.read_bytes()==(folder/row['ram_file']).read_bytes() and ports.read_bytes()==(folder/row['ports_file']).read_bytes(),row['case_index']
        rows.append(dict(case_index=row['case_index'],fixture=case,result=parsed,ram_sha256=sha(out.read_bytes()),ports_sha256=sha(ports.read_bytes()),port_count=row['port_count']))
    # Omitted table is legal only when the native branch does not reach drawing.
    bypass=[]
    for index in (0,3,24,96,102):
        case,row=cases[index],native['results'][index];assert not case['flag']&1
        ram=fixture(case);inp.write_bytes(ram);p=invoke(exe,case['incoming'],inp,out,ports,[])
        assert not p.returncode and json.loads(p.stdout)==row['result'] and inp.read_bytes()==ram
        assert out.read_bytes()==(folder/row['ram_file']).read_bytes() and ports.read_bytes()==(folder/row['ports_file']).read_bytes()
        bypass.append(index)
    extra=supplemental(exe,folder,resource,program,cases)
    for row in extra:
        for key,name in row['files'].items():
            artifacts[str((folder/name).relative_to(root))]=row['hashes'][key]
    sample=next(c for c in cases if c['flag']==1 and not c['parent_flag_alias'])
    rejected,case_alias=negatives(exe,folder,sample,resource)
    for name,digest in dict(inputs,**native['inputs'],**artifacts).items():assert sha((root/name).read_bytes())==digest,name
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256 and oracle_provenance()==native['oracle']
    report.write_text(json.dumps(dict(source=source,oracle=native['oracle'],inputs=inputs,native_inputs=native['inputs'],native_artifacts=artifacts,
        native_observation_sha256=sha(raw),cases=len(rows),negative_cases=rejected,case_alias_regression=case_alias,
        no_table_bypass_native_cases=bypass,supplemental_native_cases=extra,total_ordered_ports=sum(row['port_count'] for row in rows),
        full_RAM_15_registers_ordered_ports_equal=True,native_helper_alias_read_evidence_audited=True,source_and_inputs_unchanged=True,
        callback_returned=False,stop_before_pc=STOP,results=rows,
        scope='Original104 unpatched47c04 prefixes stopped before47c6c versus actualCLI, plus two separately recorded original-CPU shifted-A5 cases. Full64KiBRAM15regs/6576ports, complete native write replay and live helper-alias reads audited. No whole callback return, downstream frame, CCR/cycle, physical RAM mirror, scheduler or rendered pixel equivalence claim.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negative_cases=len(rejected),ports=sum(row['port_count'] for row in rows),sha256=sha(report.read_bytes()))))


if __name__=='__main__':main()
