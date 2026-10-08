"""Whole ca9e/caf0 actual CLI differential against audited native32 cases."""
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
from observe_screen_reset_full import (BASE,STACK,STACK_START,RETURN,KEYS,PORTS,
    SOURCE_SHA256,sha,build_cases,fixture,assert_contract,load_verified_program,
    oracle_provenance)


def invoke(exe,entry,registers,inp,out,ports,timeout=3):
    return subprocess.run([str(exe),str(entry)]+[str(registers[key]) for key in KEYS]+list(map(str,(inp,out,ports))),capture_output=True,text=True,timeout=timeout)


def audit_native(root,program,source):
    folder=root/'artifacts/screen_reset_full';path=folder/'observation.json'
    raw=path.read_bytes();native=json.loads(raw);cases=build_cases()
    assert native['source']==source and native['oracle']==oracle_provenance()
    assert native['cases']==native['completed_cases']==len(cases)==len(native['results'])==32
    assert native['contract_mismatches']==[] and native['total_native_ports']==45520
    assert not native['source_program_modified'] and not native['in_call_SR_read'] and not native['Cpp_comparison_performed']
    assert native['full_RAM_15_registers_ordered_ports_observed']
    for name,digest in native['inputs'].items():assert sha((root/name).read_bytes())==digest,(name,'native provenance changed')
    static=json.loads((root/'artifacts/screen_reset_full_static.json').read_bytes())
    def validate_bytes(value):
        if isinstance(value,dict):
            if 'raw' in value and 'rom_offset' in value:
                encoded=bytes.fromhex(value['raw']);offset=value['rom_offset']
                assert encoded==program[offset:offset+len(encoded)]
            for item in value.values():validate_bytes(item)
        elif isinstance(value,list):
            for item in value:validate_bytes(item)
    validate_bytes(static)
    artifacts={str(path.relative_to(root)):sha(raw)}
    for index,(case,row) in enumerate(zip(cases,native['results'])):
        assert row['case_index']==index and row['fixture']==case and row['returned']
        assert row['final_pc']==RETURN and row['final_a7']==STACK+4 and not row['unexpected_reads']
        for key,digest in (('input_ram_file','input_ram_sha256'),('ram_file','ram_sha256'),('ports_file','ports_sha256'),('writes_file','writes_sha256')):
            p=folder/row[key];assert sha(p.read_bytes())==row[digest]
            artifacts[str(p.relative_to(root))]=row[digest]
        ram=fixture(case);assert (folder/row['input_ram_file']).read_bytes()==ram
        assert sha(ram)==row['input_ram_sha256']
        expected=(folder/row['ram_file']).read_bytes();ports=(folder/row['ports_file']).read_bytes()
        events=json.loads((folder/row['writes_file']).read_bytes());replay=bytearray(ram);encoded=[];ram_writes=[];stack_writes=[]
        for event in events:
            address,size,value=event['address'],event['size'],event['value']
            assert size in (1,2,4) and 0<=value<1<<(size*8)
            assert 0xca9e<=event['pc']<=0xcb62 or 0x35a2<=event['pc']<=0x35ee
            if event['kind']=='ram':
                assert BASE<=address and address+size<=BASE+65536
                ram_writes.append(event);replay[address-BASE:address-BASE+size]=value.to_bytes(size,'big')
            elif event['kind']=='ports':
                assert address in PORTS
                encoded.append(struct.pack('>BII',size,address,value))
            else:
                assert event['kind']=='stack' and STACK_START<=address and address+size<=STACK+4
                stack_writes.append(event)
        assert bytes(replay)==expected and b''.join(encoded)==ports and len(encoded)==row['port_count']
        assert ram_writes==row['RAM_writes'] and len(stack_writes)==row['stack_write_count']
        assert min([event['address'] for event in stack_writes]+[STACK])==row['lowest_stack_write']
        assert_contract(case,ram,expected,row['result'],ports,row)
    return native,raw,cases,artifacts


def negatives(exe,folder,cases):
    rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp,out,ports=(work/name for name in ('input.bin','output.bin','ports.bin'))
        sample=next(case for case in cases if case['entry']==0xcaf0)
        base=fixture(sample);registers=sample['incoming'];sentinel=b'preserved-screen-reset-output\0\xff'
        def reject(label,ram=base,entry=0xcaf0,state=registers,source=inp,outputs=None,command=None):
            destinations=(out,ports) if outputs is None else outputs
            inp.write_bytes(ram)
            for path in (out,ports)+destinations:
                if path.parent.exists() and path!=inp and not(path.exists() and os.path.samefile(path,inp)) and not(path.exists() and path.is_dir()):path.write_bytes(sentinel)
            watched={path:path.read_bytes() for path in set((inp,out,ports)+destinations) if path.exists() and path.is_file()}
            p=subprocess.run(command,capture_output=True,text=True,timeout=2) if command is not None else invoke(exe,entry,state,source,destinations[0],destinations[1],timeout=2)
            assert p.returncode and not p.stdout and all(path.read_bytes()==before for path,before in watched.items()),(label,p.stdout,p.stderr)
            rows.append(dict(label=label,input_outputs_preserved=True,native_bad_fixture_executed=False,error=p.stderr.strip()))
        for size in (0,65535,65537):reject('RAM-size-%d'%size,ram=bytes(size))
        for entry in (0,0xca9f,0xcaef,0xcaf1,0xffffffff):reject('unsupported-entry',entry=entry)
        for entry in ('-1','4294967296','0x100000000','0x','1x',''):reject('entry-parser',entry=entry)
        for key in KEYS:
            for value in ('-1','4294967296','0x100000000','0x','1x',''):
                reject('register-parser-'+key,state=dict(registers,**{key:value}))
        for a5 in (0,1,0x107698,0x107699,0x11769a,0x11769b,0x7fffffff,0x80000000,0xffffffff):
            reject('caf0-destination-outside-RAM',state=dict(registers,a5=a5))
        reject('missing-input',source=work/'absent.bin')
        reject('input-directory',source=work)
        reject('RAM-output-directory',outputs=(work,ports));reject('port-output-directory',outputs=(out,work))
        reject('RAM-output-missing-parent',outputs=(work/'absent'/'output.bin',ports))
        reject('port-output-missing-parent',outputs=(out,work/'absent'/'ports.bin'))
        reject('input-RAM-output-alias',outputs=(inp,ports));reject('input-port-output-alias',outputs=(out,inp))
        reject('RAM-port-output-alias',outputs=(out,out))
        for kind in ('hardlink','symlink'):
            inp.write_bytes(base);alias=work/('input-'+kind)
            if kind=='hardlink':os.link(inp,alias)
            else:alias.symlink_to(inp)
            reject('input-RAM-output-'+kind,outputs=(alias,ports))
            reject('input-port-output-'+kind,outputs=(out,alias))
            out.write_bytes(sentinel);other=work/('outputs-'+kind)
            if kind=='hardlink':os.link(out,other)
            else:other.symlink_to(out)
            reject('RAM-port-output-'+kind,outputs=(out,other))
        values=[str(registers[key]) for key in KEYS]
        reject('missing-arguments',command=[str(exe)])
        reject('extra-argument',command=[str(exe),'0xcaf0']+values+list(map(str,(inp,out,ports)))+['extra'])
        fifo=work/'fifo';os.mkfifo(fifo)
        for role in ('input','RAM-output','port-output'):
            inp.write_bytes(base);out.write_bytes(sentinel);ports.write_bytes(sentinel)
            p=invoke(exe,0xcaf0,registers,fifo if role=='input' else inp,fifo if role=='RAM-output' else out,fifo if role=='port-output' else ports,timeout=2)
            assert p.returncode and not p.stdout and inp.read_bytes()==base and out.read_bytes()==sentinel and ports.read_bytes()==sentinel
            rows.append(dict(label='FIFO-'+role,rejected_without_blocking=True,input_outputs_preserved=True,native_bad_fixture_executed=False,error=p.stderr.strip()))
        probe=work/'CaseSensitivity.probe';probe.write_bytes(b'case probe');folded=work/'casesensitivity.probe'
        insensitive=folded.exists() and os.path.samefile(probe,folded)
        case_alias=dict(case_insensitive_filesystem=insensitive,applicable=insensitive)
        if insensitive:
            first,second=work/'NewScreen.bin',work/'newscreen.bin';assert not first.exists() and not second.exists();inp.write_bytes(base)
            p=invoke(exe,0xcaf0,registers,inp,first,second,timeout=2)
            assert p.returncode and not p.stdout and inp.read_bytes()==base and not first.exists() and not second.exists()
            case_alias.update(absent_output_alias_rejected=True,input_and_absent_outputs_preserved=True,error=p.stderr.strip())
            first.write_bytes(b'');assert os.path.samefile(first,second)
            p=invoke(exe,0xcaf0,registers,inp,first,second,timeout=2)
            assert p.returncode and not p.stdout and inp.read_bytes()==base and first.read_bytes()==second.read_bytes()==b''
            case_alias['existing_zero_length_alias_outputs_preserved']=True
        # A failed second reservation must remove only its new first placeholder.
        fresh=work/'fresh-output.bin';assert not fresh.exists();inp.write_bytes(base)
        p=invoke(exe,0xcaf0,registers,inp,fresh,fifo,timeout=2)
        assert p.returncode and not p.stdout and inp.read_bytes()==base and not fresh.exists()
        rows.append(dict(label='second-reservation-failure-cleans-only-new-first-placeholder',input_outputs_preserved=True,native_bad_fixture_executed=False,error=p.stderr.strip()))
    return rows,case_alias


def main():
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/screen_reset_full'
    report=folder/'verification.json';report.unlink(missing_ok=True)
    names=('tools/verify_screen_reset_full.py','build/reset_game_screen_full','engine/tools/reset_game_screen_full.cpp','engine/src/game_screen_reset.cpp','engine/include/ms5/game_screen_reset.h','engine/include/ms5/game_screen_reset_execution.h','engine/include/ms5/object_restart_execution.h','engine/include/ms5/video_port.h','Makefile')
    inputs={name:sha((root/name).read_bytes()) for name in names}
    program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    native,raw,cases,artifacts=audit_native(root,program,source)
    exe=root/'build/reset_game_screen_full';inp,out,ports=(folder/name for name in ('input.bin','cpp.bin','cpp.ports.bin'))
    rows=[]
    for index,(case,row) in enumerate(zip(cases,native['results'])):
        ram=fixture(case);expected=(folder/row['ram_file']).read_bytes();expected_ports=(folder/row['ports_file']).read_bytes()
        inp.write_bytes(ram);out.write_bytes(b'old-output');ports.write_bytes(b'old-ports')
        p=invoke(exe,case['entry'],case['incoming'],inp,out,ports)
        assert p.returncode==0,(index,case,p.stderr)
        parsed=json.loads(p.stdout)
        assert inp.read_bytes()==ram and out.read_bytes()==expected and ports.read_bytes()==expected_ports and parsed==row['result'],(index,case,parsed,row['result'])
        rows.append(dict(case_index=index,fixture=case,result=parsed,input_ram_sha256=sha(ram),ram_sha256=sha(expected),ports_sha256=sha(expected_ports),port_count=row['port_count'],native_writes_sha256=row['writes_sha256']))
    rejected,case_alias=negatives(exe,folder,cases)
    assert inputs=={name:sha((root/name).read_bytes()) for name in names}
    assert native['oracle']==oracle_provenance() and sha((root/source['path']).read_bytes())==SOURCE_SHA256
    for name,digest in native['inputs'].items():assert sha((root/name).read_bytes())==digest
    for name,digest in artifacts.items():assert sha((root/name).read_bytes())==digest
    report.write_text(json.dumps(dict(source=source,oracle=native['oracle'],inputs=inputs,native_inputs=native['inputs'],native_artifacts=artifacts,native_observation_sha256=sha(raw),cases=len(rows),negative_cases=rejected,case_alias_regression=case_alias,total_ordered_ports=sum(row['port_count'] for row in rows),full_RAM_15_registers_ordered_ports_equal=True,positive_input_RAM_preserved=True,original_source_native_artifacts_binary_tools_unchanged=True,source_program_modified=False,in_call_SR_read=False,results=rows,scope='Whole unpatchedca9e/caf0 native32focusedcases throughoriginal35a2 versus actualCLI. Full64KiBRAM15regs/45520orderedwatchdog+videoports; auditedlosslessnativeRAM/port/stackwrites andsourceprovenance. Fourregisterprofiles, caf0validA5bytebounds/odd destinations, ca9earbitraryA5; malformedinputs/invalidspans/pathaliases/FIFOs rejectpreservingoutputs. IsolatedoracleSTACK1feffc outsidecompared64KiBRAM; A7/stack/CCR notCLIstate, noRAMmirror/physicalvideo/rendering/cycle/scheduler equivalence claim.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negative_cases=len(rejected),ports=sum(row['port_count'] for row in rows),sha256=sha(report.read_bytes()))))


if __name__=='__main__':main()
