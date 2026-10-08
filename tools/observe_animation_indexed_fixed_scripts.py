"""Unpatched49fc6 on the existing verified65f56 fixed script inventory."""
import collections
import itertools
import json
from pathlib import Path

import observe_animation_indexed_execution as native
from pack_animation_branch import extract, GROUP, GROUP_SETUP_ADDRESSES

EXTRA_RANGES = ((0x4a3b8, 0x4a3de), (0x4a408, 0x4a46c),
                (0x2b3e8, 0x2b40c))
SCRIPT_SHA = '63a1c8e3de2e5d196144c4ea51f1030bd67a06527871fd6fc44ce0e496029e9e'


def cases():
    return [dict(index=index, timer=timer, field_7e=field)
            for index, timer, field in itertools.product(
                (0, 4, 16, 17, 255), (0, 0x100, 0xffff), (0, 1))]


def fixture(program, case, index):
    base = dict(selector=0x1e, index=case['index'], timer=case['timer'],
                length=40, a6=0x102000, queue='normal', pending=False,
                flags=0, x=160, y=384, flash_flag=0, flash_phase=0,
                sentinel=False)
    ram, registers, unused = native.fixture(program, base, index)
    ram = bytearray(ram)
    changes = ((0x2026, 4, 0x65f56), (0x2020, 2, GROUP),
               (0x207c, 1, case['index']), (0x207d, 1, case['index']),
               (0x207e, 1, case['field_7e']))
    for address, size, value in changes:
        native.put(ram, address, size, value)
    return bytes(ram), registers


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = native.load_verified_program(root)
    assert native.sha(program) == native.SOURCE_SHA256
    script_base, script, commands = extract(program)
    assert script_base == 0x65f56 and native.sha(script) == SCRIPT_SHA
    folder = root/'artifacts/animation_indexed_fixed_scripts'
    folder.mkdir(parents=True, exist_ok=True)
    report_path = folder/'observation.json'
    report_path.unlink(missing_ok=True)
    oracle = native.oracle_provenance()
    names = ('tools/observe_animation_indexed_fixed_scripts.py',
             'tools/observe_animation_indexed_execution.py',
             'tools/pack_animation_branch.py', 'tools/disassemble_program.py',
             'tools/verify_object_reset.py', 'tools/observe_scene_frame_execution.py',
             'tools/observe_screen_reset_full.py', 'tools/verify_stage_catalog.py')
    inputs = {name: native.sha((root/name).read_bytes()) for name in names}
    original_ranges = native.CODE_RANGES
    rows = []
    outcomes = collections.defaultdict(collections.Counter)
    indexed_commands = collections.Counter()
    try:
        native.CODE_RANGES = original_ranges + EXTRA_RANGES
        instructions = []
        for start, end in native.CODE_RANGES:
            instructions.extend(native.disassemble_range(program, start, end-start, start))
        branches = {row['cpu_address'] for row in instructions
                    if row['mnemonic'].startswith('b') and
                    not row['mnemonic'].startswith(('bra', 'bsr', 'btst', 'bclr'))}
        source_info = dict(source=source, ranges=native.CODE_RANGES,
            instructions=instructions,
            fixed_script=dict(cpu_address=script_base, rom_offset=script_base,
                size=len(script), sha256=SCRIPT_SHA, commands=commands),
            caller=dict(cpu_address=0x2bb06, rom_offset=0x2bb06,
                raw=program[0x2bb06:0x2bb16].hex()),
            group=GROUP, group_evidence=[dict(cpu_address=at, rom_offset=at,
                raw=program[at:at+6].hex()) for at in GROUP_SETUP_ADDRESSES],
            resource_note='Known eight operand bases fullBYTE union6431a..64836 is already packed; no C++ consumption claim.')
        source_path = folder/'source.json'
        source_path.write_text(json.dumps(source_info, indent=2)+'\n')
        inputs[str(source_path.relative_to(root))] = native.sha(source_path.read_bytes())
        observer = native.Observer(program, branches)
        for index, case in enumerate(cases()):
            ram, registers = fixture(program, case, index)
            observer.prepare(ram, registers)
            info, before, output, ports = observer.run()
            trace = info.pop('trace')
            native.validate_restore(trace)
            indexed_commands.update(item['address'] for item in trace['opcodes']
                                    if item['value'] == 0x10)
            # This matrix requests immediate completion; report rather than
            # synthesize a queue release if the original unexpectedly waits.
            assert not info['waiting'], (index, case, info['pending'])
            prefix = 'case_%03d' % index
            payloads = {prefix+'_input.bin': before,
                prefix+'_native.bin': output, prefix+'_ports.bin': ports,
                prefix+'_trace.json': (json.dumps(trace, indent=2)+'\n').encode()}
            for name, data in payloads.items():
                (folder/name).write_bytes(data)
            for branch in trace['branches']:
                outcomes[branch['pc']][branch['next_pc']] += 1
            rows.append(dict(case_index=index, fixture=case,
                input_ram_file=prefix+'_input.bin', ram_file=prefix+'_native.bin',
                ports_file=prefix+'_ports.bin', trace_file=prefix+'_trace.json',
                files={name: native.sha(data) for name, data in payloads.items()}, **info))
    finally:
        native.CODE_RANGES = original_ranges
    assert native.oracle_provenance() == oracle
    assert native.sha((root/source['path']).read_bytes()) == native.SOURCE_SHA256
    assert all(native.sha((root/name).read_bytes()) == value for name, value in inputs.items())
    report = dict(source=source, oracle=oracle, inputs=inputs,
        cases=len(rows), phases=len(rows), total_native_ports=sum(row['port_count'] for row in rows),
        returned_carry_counts=dict(collections.Counter(str(row['carry']) for row in rows)),
        reached_indexed_commands={hex(address): count for address, count in sorted(indexed_commands.items())},
        observed_branch_successors={hex(pc): {hex(target): count for target, count in sorted(counts.items())}
            for pc, counts in sorted(outcomes.items())},
        max_phase_instructions=max(row['instructions'] for row in rows),
        instruction_cap=native.CAP, results=rows, failure=None,
        original_program_modified=False, in_call_SR_read=False,
        Cpp_comparison_performed=False,
        scope='Unpatched whole49fc6 on immutable known65f56..662c2 script, actual fixed tables and1d/1e callback data. '
              'Synthetic canonicalA5/object102000 and valid normal queue; indices0/4/16/17/255, timers0/0100/ffff, field7e0/1. '
              'WholeRAM15R/RTS carry/PVC and read-write-stack traces. Only first indexed command of each selected loop reached, not all eight known commands. '
              'No pending/C++/newresource/naturalgameplay/allselector-length/group-binding claim.')
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(cases=report['cases'], ports=report['total_native_ports'],
        max_instructions=report['max_phase_instructions'], sha256=native.sha(report_path.read_bytes()))))


if __name__ == '__main__':
    main()
