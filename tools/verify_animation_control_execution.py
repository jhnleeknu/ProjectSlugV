"""Actual animation0c/14(1d,1e) CLI versus immutable178-case original evidence."""
import collections
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib

import observe_animation_control_commands as original
from verify_animation_execution import initial, invoke, parse
from pack_animation_control import build as pack_resources
import observe_activation_animation_scripts as activation
from pack_activation_animation import build as pack_activation_resources

NATIVE_SHA = '0590de05828d8639340843f06a33417aa32e0370196512bf5a4d17e97165a885'


def digest(path):
    return original.sha(path.read_bytes())


def expected(row):
    return dict(initial(row['result']), carry=row['carry'])


def audit(root, program, source):
    folder = root/'artifacts/animation_control_commands'
    path = folder/'observation.json'
    native = json.loads(path.read_text())
    assert digest(path) == NATIVE_SHA
    assert native['source'] == source and native['oracle'] == original.oracle_provenance()
    assert native['failure'] is None and not native['original_program_modified']
    assert not native['in_call_SR_read'] and not native['Cpp_comparison_performed']
    hashes = {str(path.relative_to(root)): digest(path)}
    for name, value in native['inputs'].items():
        assert digest(root/name) == value, name
        hashes[name] = value
    static = json.loads((folder/'source.json').read_text())
    assert static['source'] == source and static['ranges'] == [list(x) for x in original.RANGES]
    branches = set()
    for start, end in static['ranges']:
        cursor = start
        for row in static['instructions']:
            if start <= row['cpu_address'] < end:
                assert row['cpu_address'] == row['rom_offset'] == cursor
                assert bytes.fromhex(row['raw']) == program[cursor:cursor+row['size']]
                cursor += row['size']
                if row['mnemonic'].startswith('b') and not row['mnemonic'].startswith(('bra','bsr','btst','bclr')):
                    branches.add(row['cpu_address'])
        assert cursor == end
    for region in static['data_ranges']:
        assert region['cpu_address'] == region['rom_offset']
        assert original.sha(program[region['rom_offset']:region['rom_offset']+region['size']]) == region['sha256']
    cases = original.cases()
    assert len(cases) == len(native['results']) == native['cases'] == 178
    observer = original.Observer(program, branches)
    count = 0
    for index, (case, row) in enumerate(zip(cases, native['results'])):
        ram, registers = original.fixture(case, index, program)
        assert row['case_index'] == index and row['fixture'] == case and row['incoming'] == registers
        output, ports, info, trace = observer.run(ram, registers)
        assert all(row[key] == value for key, value in info.items()), index
        assert ram == (folder/row['input_ram_file']).read_bytes()
        assert output == (folder/row['ram_file']).read_bytes()
        assert ports == (folder/row['ports_file']).read_bytes()
        assert trace == json.loads((folder/row['trace_file']).read_text())
        for name, value in row['files'].items():
            path = folder/name
            assert digest(path) == value, name
            hashes[str(path.relative_to(root))] = value
        assert row['final_pc'] == original.RETURN and row['final_a7'] == original.STACK+4
        count += len(ports)//9
    assert count == native['total_native_ports'] == 912
    assert native['cases_by_opcode'] == {'0xc':128, '0x14':50}
    assert len(native['excluded_fixtures']) == 2
    assert all(not row['native_executed'] and not row['success'] for row in native['excluded_fixtures'])
    return native, hashes


def raw_window(cpu, payload):
    return struct.pack('<4s7I', b'MS5D', 1, 1, cpu, cpu, len(payload), zlib.crc32(payload), 0)+payload


def mixed_resource_supplements(root, folder, program, exe, resources):
    packed, manifest=pack_activation_resources(root)
    runtime=root/'extracted/runtime/activation_animation'
    for name,data in packed.items():assert (runtime/name).read_bytes()==data,name
    ms5a=runtime/'animation_048980.ms5a'
    saved_ranges=activation.CODE_RANGES
    rows=[];hashes={}
    try:
        activation.CODE_RANGES=saved_ranges+((0x4a3b8,0x4a3de),(0x4a408,0x4a46c),(0x2b3e8,0x2b40c))
        branches=set()
        for start,end in activation.CODE_RANGES:
            for instruction in activation.disassemble_range(program,start,end-start,start):
                if instruction['mnemonic'].startswith('b') and not instruction['mnemonic'].startswith(('bra','bsr','btst','bclr')):
                    branches.add(instruction['cpu_address'])
        observer=activation.Observer(program,branches)
        for index,(label,script) in enumerate((
                ('RAM0c-MS5D-selector-to-original-MS5A',bytes.fromhex('0c01000000048980')),
                ('RAM14-MS5D-callback-and-operand-then-MS5A',bytes.fromhex('141d0006431a080000048980')))):
            ram,regs=activation.fixture(activation.cases()[0],index)
            data=bytearray(ram)
            original.put(data,0x102026,4,0x106000)
            original.put(data,0x102056,1,1)
            original.put(data,0x10207c,1,0)
            data[0x6000:0x6000+len(script)]=script
            ram=bytes(data)
            observer.prepare(ram,regs)
            info,before,native_ram,native_ports=observer.run()
            assert before==ram and not info['waiting']
            trace=info.pop('trace')
            # Actual read records establish both resource kinds were consumed.
            assert any(read['address']==0x4a76c and read['size']==2 for read in trace['reads']) if index==0 else \
                any(read['address']==0x4a574 and read['size']==4 for read in trace['reads'])
            if index==1:assert any(read['address']==0x6431a and read['size']==4 for read in trace['reads'])
            assert any(opcode['address']==0x48980 and opcode['value']==4 for opcode in trace['opcodes'])
            rr=resources[:1]+[ms5a] if index==0 else resources+[ms5a]
            prefix='mixed_%02d'%index
            inp=folder/(prefix+'_input.bin');out=folder/(prefix+'_cpp.bin');ports=folder/(prefix+'_cpp_ports.bin')
            inp.write_bytes(ram);out.write_bytes(b'old');ports.write_bytes(b'old')
            result=invoke(exe,initial(regs),inp,out,ports,rr)
            assert not result.returncode,(label,result.stderr)
            actual=parse(result.stdout)
            assert actual==dict(initial(info['result']),carry=info['carry']),label
            assert out.read_bytes()==native_ram and ports.read_bytes()==native_ports and inp.read_bytes()==ram,label
            payloads={prefix+'_native.bin':native_ram,prefix+'_native_ports.bin':native_ports,
                prefix+'_trace.json':(json.dumps(trace,indent=2)+'\n').encode(),
                prefix+'_native_state.json':(json.dumps(info,indent=2)+'\n').encode(),
                prefix+'_cpp_state.json':result.stdout.encode()}
            for name,value in payloads.items():(folder/name).write_bytes(value)
            files={str(path.relative_to(root)):digest(path) for path in [inp,out,ports]+[folder/name for name in payloads]}
            hashes.update(files)
            rows.append(dict(label=label,synthetic_RAM_script=script.hex(),script_address=0x106000,
                result=actual,port_count=len(native_ports)//9,files=files,
                resource_files=[str(path.relative_to(root)) for path in rr],
                source_scope='Unpatched whole49fc6, synthetic liveRAM prefix followed by actual48980 fixed script'))
    finally:
        activation.CODE_RANGES=saved_ranges
    return rows,hashes


def negatives(root, folder, program, exe, resources, native):
    base = native['results'][0]
    ram = (root/'artifacts/animation_control_commands'/base['input_ram_file']).read_bytes()
    state = initial(base['incoming'])
    callback = next(row for row in native['results'] if row['fixture']['opcode'] == 0x14 and
                    row['fixture']['selector'] == 0x1d and row['fixture']['profile'] == 'RAM' and
                    row['fixture']['requested_index'] == 0)
    callback_ram = (root/'artifacts/animation_control_commands'/callback['input_ram_file']).read_bytes()
    callback_state = initial(callback['incoming'])
    fixed_callback = next(row for row in native['results'] if row['fixture']['opcode'] == 0x14 and
                          row['fixture']['profile'] == 'fixed6431a' and row['fixture']['requested_index'] == 0)
    fixed_ram = (root/'artifacts/animation_control_commands'/fixed_callback['input_ram_file']).read_bytes()
    rows = []
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work = Path(temporary)
        inp, out, ports = (work/name for name in ('input', 'output', 'ports'))
        sentinel = b'preserved-output'

        def reject(label, payload=ram, registers=state, windows=None, source=None, destinations=None, error_contains=None):
            inp.write_bytes(payload)
            out.write_bytes(sentinel)
            ports.write_bytes(sentinel)
            rr = resources if windows is None else windows
            src = inp if source is None else source
            dst = (out,ports) if destinations is None else destinations
            watched = {p:p.read_bytes() for p in [inp,out,ports,src]+list(dst)+list(rr)
                       if p.exists() and p.is_file()}
            result = invoke(exe,registers,src,*dst,rr)
            assert result.returncode and not result.stdout, (label,result.stdout,result.stderr)
            if error_contains is not None:
                assert error_contains in result.stderr,(label,result.stderr,error_contains)
            assert all(path.read_bytes() == data for path,data in watched.items()), label
            rows.append(dict(label=label,files_preserved=True,error=result.stderr.strip()))

        def window(name,cpu,size):
            path=work/name
            path.write_bytes(raw_window(cpu,program[cpu:cpu+size]))
            return path

        reject('missing0c-selector-window',windows=[])
        reject('missing14-dispatch-window',payload=callback_ram,registers=callback_state,windows=[])
        reject('missing14-fixed-operand',payload=fixed_ram,registers=initial(fixed_callback['incoming']),windows=resources[:1])
        duplicate=work/'distinct-copy-control';duplicate.write_bytes(resources[0].read_bytes())
        reject('ambiguous0c-distinct-file-same-span',windows=[resources[0],duplicate])
        overlap=window('overlap0c',0x4a76c,2)
        reject('ambiguous0c-overlap',windows=[resources[0],overlap])
        partial=window('partial0c',0x4a76c,1)
        reject('partial0c-WORD',windows=[partial])
        adjacent=window('adjacent0c',0x4a76d,1)
        reject('split0c-WORD-across-adjacent-windows',windows=[partial,adjacent])
        partial_dispatch=window('partial14-dispatch',0x4a574,3)
        reject('partial14-dispatch-LONG',payload=callback_ram,registers=callback_state,windows=[partial_dispatch])
        partial_operand=window('partial14-operand',0x6431a,3)
        reject('partial14-operand-LONG',payload=fixed_ram,registers=initial(fixed_callback['incoming']),windows=[resources[0],partial_operand])
        for selector in (0,0x1c,0x1f,0xff):
            data=bytearray(callback_ram);original.put(data,0x105001,1,selector)
            reject('unsupported14-selector-'+hex(selector),payload=bytes(data),registers=callback_state)
        for operand in (0x106001,0x10fffe,0x110000):
            data=bytearray(callback_ram);original.put(data,0x105002,4,operand)
            reason={0x106001:'unaligned or overflowing animation data read',
                0x10fffe:'aligned complete reached RAM span',
                0x110000:'fixed animation data read'}[operand]
            reject('late14-source-LONG-'+hex(operand),payload=bytes(data),registers=callback_state,error_contains=reason)
        # All callback operations are valid; next dispatch is outside RAM after
        # callback write, bank/register restoration and pointer publication.
        data=bytearray(callback_ram)
        original.put(data,0x108026,4,0x10fffa)
        data[0xfffa:0x10000]=callback_ram[0x5000:0x5006]
        reject('late14-completed-then-next-fetch110000',payload=bytes(data),registers=callback_state,
            error_contains='fixed animation script read')
        for excluded in native['excluded_fixtures']:
            data=bytearray(ram);a6=excluded['a6']
            original.put(data,a6+0x26,4,0x105000)
            original.put(data,a6+0x2a,2,0)
            original.put(data,a6+0x2c,2,0x100)
            original.put(data,a6+0x17,1,0)
            original.put(data,0x105002,2,excluded['selector'])
            reject('reached0c-field-outside-RAM-'+hex(a6),payload=bytes(data),registers=dict(state,a6=a6),
                error_contains='aligned complete reached RAM span')
        for at in (0,4,8,12,16,20,24,28,32):
            bad=bytearray(resources[0].read_bytes());bad[at]^=1
            path=work/('corrupt-'+str(at));path.write_bytes(bad)
            reject('resource-corruption-'+str(at),windows=[path])
        for source_index,resource in enumerate(resources):
            for output_role in (0,1):
                destinations=(resource,ports) if output_role==0 else (out,resource)
                reject('resource%d-output-role%d-alias'%(source_index,output_role),destinations=destinations)
        reject('missing-input',source=work/'missing')
        reject('input-directory',source=work)
        reject('output-directory',destinations=(work,ports))
        reject('ports-directory',destinations=(out,work))
        reject('input-output-alias',destinations=(inp,ports))
        reject('input-ports-alias',destinations=(out,inp))
        reject('same-outputs',destinations=(out,out))
        for kind in ('hardlink','symlink'):
            alias=work/kind
            if kind=='hardlink':os.link(inp,alias)
            else:alias.symlink_to(inp)
            reject('input-output-'+kind,destinations=(alias,ports))
        fifo=work/'fifo';os.mkfifo(fifo)
        reject('FIFO-input',source=fifo)
        reject('FIFO-output',destinations=(fifo,ports))
        reject('FIFO-ports',destinations=(out,fifo))
        reject('FIFO-resource',windows=[fifo])
        fresh=work/'fresh'
        reject('second-output-failure-cleans-new-first',destinations=(fresh,fifo))
        assert not fresh.exists()
        folded=work/'INPUT'
        insensitive=folded.exists() and os.path.samefile(inp,folded)
        if insensitive:
            reject('casefold-input-output-alias',destinations=(folded,ports))
            first,second=work/'new-output',work/'NEW-OUTPUT'
            reject('casefold-two-new-outputs',destinations=(first,second))
            assert not first.exists() and not second.exists()
        case_probe=dict(case_insensitive_filesystem=insensitive,
            casefold_alias_tests='passed' if insensitive else 'not applicable')
    return rows,case_probe


def main():
    root=Path(__file__).resolve().parents[1]
    folder=root/'artifacts/animation_control_execution';folder.mkdir(parents=True,exist_ok=True)
    report=folder/'verification.json';report.unlink(missing_ok=True)
    program,source=original.load_verified_program(root)
    assert original.sha(program)==original.SOURCE_SHA256
    native,artifacts=audit(root,program,source)
    packed,manifest=pack_resources(root)
    runtime=root/'extracted/runtime/animation_control'
    for name,data in packed.items():assert (runtime/name).read_bytes()==data,name
    resources=[runtime/'control_04276c.ms5d',runtime/'operands_06431a.ms5d']
    exe=root/'build/step_animation_execution'
    names=['tools/verify_animation_control_execution.py','tools/verify_animation_execution.py',
        'tools/pack_animation_control.py','tools/inspect_activation_animation_scripts.py',
        'tools/observe_activation_animation_scripts.py','tools/pack_activation_animation.py',
        'engine/src/animation_execution.cpp','engine/include/ms5/animation_execution.h',
        'engine/tools/step_animation_execution.cpp','engine/src/sprite_submit_execution.cpp',
        'engine/include/ms5/sprite_submit_execution.h','engine/include/ms5/sprite_producer.h',
        'engine/include/ms5/scene_map_transfer.h','engine/include/ms5/video_port.h',
        'engine/src/animation_resource.cpp','engine/include/ms5/animation_resource.h',
        'engine/src/fixed_data_resource.cpp','engine/include/ms5/fixed_data_resource.h',
        'Makefile','build/step_animation_execution','docs/analysis/animation-control-resource-spans.md',
        'docs/analysis/animation-control-full-contract.md',
        'docs/analysis/animation-execution-initial-contract.md',
        'docs/analysis/animation-draw-full-contract.md']
    names.extend(str((runtime/name).relative_to(root)) for name in packed)
    names.extend('extracted/runtime/activation_animation/'+name for name in
        ('animation_048980.ms5a','animation_0489c2.ms5a','lookup_048a12.ms5d','manifest.json'))
    inputs={name:digest(root/name) for name in names}
    rows=[]
    for row in native['results']:
        index=row['case_index'];inp=folder/('case_%03d_input.bin'%index)
        out=folder/('case_%03d_cpp.bin'%index);ports=folder/('case_%03d_ports.bin'%index)
        ram=(root/'artifacts/animation_control_commands'/row['input_ram_file']).read_bytes()
        inp.write_bytes(ram);out.write_bytes(b'old');ports.write_bytes(b'old')
        rr=resources if row['fixture']['opcode']==0x14 and row['fixture']['profile']=='fixed6431a' else resources[:1]
        result=invoke(exe,initial(row['incoming']),inp,out,ports,rr)
        assert not result.returncode,(index,result.stderr)
        actual=parse(result.stdout)
        assert actual==expected(row),(index,actual,expected(row))
        assert out.read_bytes()==(root/'artifacts/animation_control_commands'/row['ram_file']).read_bytes(),index
        assert ports.read_bytes()==(root/'artifacts/animation_control_commands'/row['ports_file']).read_bytes(),index
        assert inp.read_bytes()==ram,index
        state_file=folder/('case_%03d_state.json'%index);state_file.write_text(result.stdout)
        files={str(path.relative_to(root)):digest(path) for path in (inp,out,ports,state_file)}
        artifacts.update(files)
        rows.append(dict(case_index=index,fixture=row['fixture'],result=actual,files=files,port_count=row['port_count'],
            resource_files=[str(path.relative_to(root)) for path in rr]))
    mixed,mixed_hashes=mixed_resource_supplements(root,folder,program,exe,resources)
    artifacts.update(mixed_hashes)
    rejected,case_probe=negatives(root,folder,program,exe,resources,native)
    for name,value in {**inputs,**artifacts}.items():assert digest(root/name)==value,name
    assert original.sha((root/source['path']).read_bytes())==original.SOURCE_SHA256
    assert original.oracle_provenance()==native['oracle']
    result=dict(source=source,oracle=native['oracle'],inputs=inputs,native_and_CPP_artifacts=artifacts,
        native_observation_sha256=NATIVE_SHA,cases=len(rows),cases_by_opcode=native['cases_by_opcode'],
        primary_ordered_ports=sum(row['port_count'] for row in rows),
        returned_carry_counts={str(key):value for key,value in collections.Counter(row['result']['carry'] for row in rows).items()},
        original_cases_reexecuted=178,results=rows,negative_cases=rejected,case_alias_probe=case_probe,
        mixed_resource_supplements=mixed,
        full_RAM_15_registers_carry_ports_inactive_state_equal=True,
        scope='Actual178 original49fc6 liveRAM control fixtures:128opcode0c selector/desired/field cases and50opcode14 callbacks1d/1e. '
            'WholeRAM15registersRTScarryorderedPVC and cleared continuation metadata equal. CanonicalMS5D raw windows consumed by actualCLI. '
            'Two separate syntheticRAMprefix supplements consumeMS5D then actualMS5A48980 in one wholeoriginal call. '
            'Two native out-of-RAM fixtures remain excluded; actualCLI checks them as errors, not native successes. '
            'No naturalallselector/allcallback/1f/pending/C++otheropcode/IRQ/cycle/physicalmirror/fullgame equivalence claim.')
    report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),ports=result['primary_ordered_ports'],mixed_resource_cases=len(mixed),negative_cases=len(rejected),sha256=digest(report))))


if __name__=='__main__':
    main()
