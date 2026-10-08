"""Compare actual C++/MS5D execution with unmodified native block drawing."""
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib
from observe_stage_block_draw import (BASE, STACK, STACK_START, RETURN, KEYS,
    SOURCE_SHA256, sha, build_cases, fixture, assert_contract,
    load_verified_program, oracle_provenance)


def invoke(exe, entry, registers, inp, out, ports, resources=()):
    return subprocess.run([str(exe), str(entry)]+[str(registers[key]) for key in KEYS]+
        list(map(str, (inp, out, ports)))+list(map(str, resources)),
        capture_output=True, text=True, timeout=5)


def audit(root, program, source):
    folder=root/'artifacts/stage_block_draw'; path=folder/'observation.json'
    raw=path.read_bytes(); native=json.loads(raw); cases=build_cases(program)
    assert native['source']==source and native['oracle']==oracle_provenance()
    assert native['cases']==native['completed_cases']==len(cases)==len(native['results'])==40
    assert native['full_RAM_15_registers_ordered_ports_observed']
    assert native['contract_mismatches']==[] and native['total_native_ports']==2840
    assert not native['original_program_modified'] and not native['in_call_SR_read'] and not native['Cpp_comparison_performed']
    for name,digest in native['inputs'].items(): assert sha((root/name).read_bytes())==digest
    artifacts={str(path.relative_to(root)):sha(raw)}
    for index,(case,row) in enumerate(zip(cases,native['results'])):
        assert row['case_index']==index and row['fixture']==case and row['returned']
        assert row['final_pc']==RETURN and row['final_a7']==STACK+4 and not row['unexpected_reads']
        for key,digest in (('input_ram_file','input_ram_sha256'),('ram_file','ram_sha256'),('ports_file','ports_sha256'),('trace_file','trace_sha256')):
            p=folder/row[key];assert sha(p.read_bytes())==row[digest];artifacts[str(p.relative_to(root))]=row[digest]
        ram=fixture(case);assert (folder/row['input_ram_file']).read_bytes()==ram
        output=(folder/row['ram_file']).read_bytes();ports=(folder/row['ports_file']).read_bytes()
        trace=json.loads((folder/row['trace_file']).read_bytes());encoded=[];stack=[]
        for event in trace['writes']:
            address,size,value=event['address'],event['size'],event['value']
            assert size in (1,2,4) and 0<=value<1<<(8*size)
            assert 0x35f0<=event['pc']<=0x364e
            if event['kind']=='ports':
                assert address==0x3c0000
                encoded.append(struct.pack('>BII',size,address,value))
            else:
                assert event['kind']=='stack' and STACK_START<=address and address+size<=STACK+4
                stack.append(event)
        assert output==ram and b''.join(encoded)==ports and len(encoded)==row['port_count']
        assert not row['RAM_writes'] and len(stack)==row['stack_write_count']
        assert min([e['address'] for e in stack]+[STACK])==row['lowest_stack_write']
        saved_checks=dict(row.get('observed_width_checks',{}))
        assert_contract(case,ram,output,row['result'],ports,trace,row)
        assert row.get('observed_width_checks',{})==saved_checks
    return native,raw,cases,artifacts


def negatives(exe, folder, sample, resource):
    rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp,out,ports=(work/name for name in ('in.bin','out.bin','ports.bin'))
        regs=sample['incoming'];base=fixture(sample);sentinel=b'unchanged-block-output'
        def reject(label,entry=0x477a2,state=regs,ram=base,resources=None,outputs=None,source=None):
            sources=[resource] if resources is None else resources
            destinations=(out,ports) if outputs is None else outputs
            inp.write_bytes(ram);out.write_bytes(sentinel);ports.write_bytes(sentinel)
            watched={p:p.read_bytes() for p in (inp,out,ports)+tuple(sources)+tuple(destinations) if p.exists() and p.is_file()}
            p=invoke(exe,entry,state,inp if source is None else source,*destinations,sources)
            assert p.returncode and not p.stdout,(label,p.stdout,p.stderr)
            assert all(p.read_bytes()==data for p,data in watched.items()),label
            rows.append(dict(label=label,preserved=True,error=p.stderr.strip()))
        for size in (0,65535,65537):reject('RAM-size-'+str(size),ram=bytes(size))
        for entry in (0,0x35f1,0x364e,0xffffffff,'-1','0x','4294967296'):reject('entry-'+str(entry),entry=entry)
        for key in KEYS:
            for bad in ('-1','0x','4294967296','1x'):
                reject('parse-'+key+'-'+bad,state=dict(regs,**{key:bad}))
        reject('missing-table',resources=[])
        duplicate=work/'duplicate.ms5d';duplicate.write_bytes(resource.read_bytes())
        reject('duplicate-table-distinct-files',resources=[resource,duplicate])
        for address in (1,0xffffe,0x10ffff,0x110000,0xffffffff):
            reject('stream-address-'+hex(address),entry=0x362a,state=dict(regs,a0=address),resources=[])
        for width,height,coord in ((0,1,0),(1,0,0),(1,1,0x7500),(2,1,0x74f0),(1,2,0x74ff)):
            reject('rectangle-invalid-%d-%d-%x'%(width,height,coord),entry=0x35f0,state=dict(regs,d0=coord,d2=width,d3=height),resources=[])
        for payload in (b'\x00\x00',struct.pack('>HHBB',0,0x1234,1,1),struct.pack('>HHBBHHBBH',0,0x1234,1,1,0,0x1234,0,1,0xffff)):
            modified=bytearray(base);at=65536-len(payload);modified[at:]=payload
            reject('incomplete-or-late-invalid-stream',entry=0x362a,state=dict(regs,a0=BASE+at,d0=0x7000),ram=bytes(modified),resources=[])
        original=resource.read_bytes()
        for offset in (0,4,8,12,16,20,24,28,32):
            corrupted=bytearray(original);corrupted[offset]^=1;p=work/('bad-%d.ms5d'%offset);p.write_bytes(corrupted)
            reject('resource-corruption-'+str(offset),resources=[p])
        # A partial intersecting window must not become invisible to span ambiguity checks.
        partial=work/'partial.ms5d';payload=original[33:34];cpu=0xddfa4
        partial.write_bytes(struct.pack('<4s7I',b'MS5D',1,1,cpu,cpu,len(payload),zlib.crc32(payload),0)+payload)
        reject('partial-overlapping-window',resources=[resource,partial])
        odd=work/'odd-partial.ms5d';cpu=0xddfa5
        odd.write_bytes(struct.pack('<4s7I',b'MS5D',1,1,cpu,cpu,len(payload),zlib.crc32(payload),0)+payload)
        reject('odd-partial-overlapping-window',resources=[resource,odd])
        reject('missing-input',source=work/'missing-input')
        reject('input-directory',source=work)
        reject('RAM-output-directory',outputs=(work,ports))
        reject('port-output-directory',outputs=(out,work))
        reject('RAM-output-missing-parent',outputs=(work/'missing'/'out',ports))
        reject('port-output-missing-parent',outputs=(out,work/'missing'/'ports'))
        reject('input-port-output-alias',outputs=(out,inp))
        for kind in ('hardlink','symlink'):
            link=work/('input-'+kind)
            if kind=='hardlink':os.link(inp,link)
            else:link.symlink_to(inp)
            reject('input-RAM-output-'+kind,outputs=(link,ports))
            reject('input-port-output-'+kind,outputs=(out,link))
        reject('input-output-alias',outputs=(inp,ports));reject('two-output-alias',outputs=(out,out))
        reject('resource-RAM-output-alias',outputs=(resource,ports));reject('resource-port-output-alias',outputs=(out,resource))
        alias=work/'resource-hardlink';os.link(resource,alias)
        reject('resource-output-hardlink',outputs=(alias,ports))
        alias.unlink();alias.symlink_to(resource)
        reject('resource-output-symlink',outputs=(out,alias))
        fifo=work/'fifo';os.mkfifo(fifo)
        reject('FIFO-input',source=fifo);reject('FIFO-resource',resources=[fifo])
        reject('FIFO-RAM-output',outputs=(fifo,ports));reject('FIFO-port-output',outputs=(out,fifo))
        fresh=work/'fresh';reject('new-placeholder-cleanup',outputs=(fresh,fifo));assert not fresh.exists()
        probe=work/'CaseProbe';probe.write_bytes(b'probe');folded=work/'caseprobe'
        insensitive=folded.exists() and os.path.samefile(probe,folded)
        if insensitive:
            first,second=work/'NewOutput',work/'newoutput'
            reject('case-alias-new',outputs=(first,second));assert not first.exists() and not second.exists()
            first.write_bytes(b'');reject('case-alias-existing-empty',outputs=(first,second));assert first.read_bytes()==b''
    return rows


def main():
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/stage_block_draw'
    report=folder/'verification.json';report.unlink(missing_ok=True)
    exe=root/'build/execute_stage_block_draw';resource=root/'extracted/runtime/stage_block_draw/block_table.ms5d'
    names=('tools/verify_stage_block_draw.py','tools/pack_stage_block_draw.py','build/execute_stage_block_draw',
        'engine/tools/execute_stage_block_draw.cpp','engine/src/stage_block_draw.cpp','engine/include/ms5/stage_block_draw.h',
        'engine/src/fixed_data_resource.cpp','engine/include/ms5/fixed_data_resource.h','engine/include/ms5/object_restart_execution.h',
        'engine/include/ms5/video_port.h','Makefile','extracted/runtime/stage_block_draw/block_table.ms5d','extracted/runtime/stage_block_draw/manifest.json')
    inputs={name:sha((root/name).read_bytes()) for name in names}
    program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    native,raw,cases,artifacts=audit(root,program,source)
    packed=resource.read_bytes();payload=program[0xddfa4:0xddfdc]
    assert packed==struct.pack('<4s7I',b'MS5D',1,1,0xddfa4,0xddfa4,len(payload),zlib.crc32(payload),0)+payload
    inp,out,ports=(folder/name for name in ('cpp-input.bin','cpp.bin','cpp.ports.bin'));rows=[]
    for case,row in zip(cases,native['results']):
        ram=fixture(case);inp.write_bytes(ram);out.write_bytes(b'old');ports.write_bytes(b'old')
        resources=[resource] if case['entry'] in (0x477a2,0xddf9a) else []
        p=invoke(exe,case['entry'],case['incoming'],inp,out,ports,resources)
        assert not p.returncode,(case,p.stderr)
        parsed=json.loads(p.stdout)
        assert parsed==row['result'] and inp.read_bytes()==ram and out.read_bytes()==(folder/row['ram_file']).read_bytes() and ports.read_bytes()==(folder/row['ports_file']).read_bytes(),case
        rows.append(dict(case_index=row['case_index'],fixture=case,result=parsed,ram_sha256=sha(out.read_bytes()),ports_sha256=sha(ports.read_bytes()),port_count=row['port_count']))
    # Feed the same actual stream through raw windows split at an odd BYTE.
    # The expected result remains the original CPU result, not a new algorithm.
    split=[]
    for start,end in ((0,5),(5,6),(6,len(payload))):
        data=payload[start:end];cpu=0xddfa4+start;p=folder/('split-%d.ms5d'%start)
        p.write_bytes(struct.pack('<4s7I',b'MS5D',1,1,cpu,cpu,len(data),zlib.crc32(data),0)+data);split.append(p)
    case,row=cases[0],native['results'][0];inp.write_bytes(fixture(case))
    p=invoke(exe,case['entry'],case['incoming'],inp,out,ports,split)
    assert not p.returncode,p.stderr
    assert json.loads(p.stdout)==row['result'] and out.read_bytes()==(folder/row['ram_file']).read_bytes() and ports.read_bytes()==(folder/row['ports_file']).read_bytes()
    rejected=negatives(exe,folder,cases[0],resource)
    for name,digest in dict(inputs,**native['inputs'],**artifacts).items():assert sha((root/name).read_bytes())==digest,name
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256 and oracle_provenance()==native['oracle']
    report.write_text(json.dumps(dict(source=source,oracle=native['oracle'],inputs=inputs,native_inputs=native['inputs'],native_artifacts=artifacts,
        native_observation_sha256=sha(raw),cases=len(rows),negative_cases=rejected,total_ordered_ports=sum(row['port_count'] for row in rows),
        full_RAM_15_registers_ordered_ports_equal=True,odd_base_split_windows_native_equal=True,source_and_inputs_unchanged=True,results=rows,
        scope='Unmodified native40 focused cases versus C++ CLI using MS5D fixed data or live RAM. Isolated oracle stack; no CCR/cycle/physical mirror/pixels/scheduler equivalence claim. Invalid streams and TRAP inputs are checked errors, not native successful outcomes.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negative_cases=len(rejected),ports=sum(row['port_count'] for row in rows),sha256=sha(report.read_bytes()))))


if __name__=='__main__':main()
