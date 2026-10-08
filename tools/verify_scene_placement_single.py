"""Unpatched continuous native1a442 versus single-record placement CLI.

Uses established placement fixtures; no SR reads during native execution.
"""
import json
from pathlib import Path
import struct
import subprocess

import unicorn
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ

from observe_scene_placement_execution import (BASE, STACK, RETURN, KEYS, SOURCE_SHA256, sha,
    load_verified_program, build_cases, fixture, values, Observer, assert_evidence, resources)

ENTRY = 0x1a442
CORE_FILES = ('engine/src/scene_placement_execution.cpp', 'engine/include/ms5/scene_placement_execution.h',
              'engine/tools/execute_scene_placement.cpp', 'tools/observe_scene_placement_execution.py',
              'tools/verify_object_reset.py', 'tools/verify_scene_command.py')


def cases_for_single(root, program):
    old, paths, manifests = build_cases(root, program)
    cases = []
    for case in old:
        if case.get('sequence'):
            continue
        if case['entry'] == 0x1a414 or case['family'].startswith('bounds-') or case['family'] == 'live-RAM-word-copy-overlap-global-alias':
            item = dict(case)
            item['entry'] = ENTRY
            cases.append(item)
    cases.append(dict(family='null-stream-zero-register-profile', entry=ENTRY, cursor=0,
                      phase=0, count=4, motion=0, profile=0))
    def synthetic(label, **changes):
        case = dict(family=label, entry=ENTRY, cursor=0x106000, phase=1, count=4,
            motion=0, profile=1, gate=0, x=0, y=0, bounds=0, callback=0x12345678,
            payload_hex='12345678abcdffff', synthetic=True)
        case.update(changes)
        cases.append(case)
    for gate, phase in ((1, 0), (0x8000, 0x7fff), (0xfffe, 0xfffd), (0xffff, 0xffff)):
        synthetic('single-terminal-wait-high-D7-preservation', gate=gate, phase=phase)
    synthetic('two-eligible-records-single-vs-loop', second_record=True)
    synthetic('actual-cli-single-carry', second_record=True, sequence='two-eligible', sequence_position=0)
    for step, cursor in ((1, 0x106018), (2, 0x106028)):
        synthetic('actual-cli-single-carry', cursor=cursor, sequence='two-eligible', sequence_position=step)
    synthetic('following-record-unmapped-never-read', cursor=0x10fff0, phase=0,
              payload_hex='', following_unmapped=True)
    return cases, paths, manifests


def prepare(case, prior=None):
    if prior is not None:
        ram = bytearray(prior[0])
        regs = list(prior[1])
        assert struct.unpack_from('>I', ram, 0xd40e)[0] == case['cursor']
        assert struct.unpack_from('>H', ram, 0xd418)[0] == case['phase']
        return ram, regs
    elif case.get('following_unmapped'):
        normal = dict(case)
        normal['synthetic'] = False
        ram = fixture(normal)
        raw = struct.pack('>4H2I', case['gate'], 0, case['x'], case['y'], 0, case['callback'])
        ram[-16:] = raw
        regs = values(case)
    else:
        ram = fixture(case)
        regs = values(case)
    # Explicit host fixture writes, shared identically by native and C++.
    # For global aliases these can also alter source-record bytes, intentionally.
    struct.pack_into('>I', ram, 0xd40e, case['cursor'])
    struct.pack_into('>H', ram, 0xd418, case['phase'])
    assert len(ram) == 65536
    return ram, regs


class SingleObserver(Observer):
    def __init__(self, program):
        super().__init__(program)
        # Following an end-of-RAM record reaches a genuinely unmapped page.
        self.cpu.mem_unmap(0x110000, 0x1000)
        self.single_calls = 0
        self.reads = []
        def code(cpu, address, size, user):
            if address == ENTRY:
                self.single_calls += 1
        def read(cpu, access, address, size, value, user):
            self.reads.append((address, size))
        self.cpu.hook_add(UC_HOOK_CODE, code)
        self.cpu.hook_add(UC_HOOK_MEM_READ, read)

    def run(self, case, ram, regs):
        self.single_calls = 0
        self.reads.clear()
        output, result, calls = super().run(case, ram, regs)
        calls['single_entry_calls'] = self.single_calls
        return output, result, calls


def first_gate(program, ram, cursor):
    if not cursor:
        return None
    if cursor < BASE:
        return struct.unpack_from('>H', program, cursor)[0]
    return struct.unpack_from('>H', ram, cursor-BASE)[0]


def check_single_evidence(program, case, ram, incoming, output, result, calls, reads):
    cursor = struct.unpack_from('>I', ram, 0xd40e)[0]
    phase = struct.unpack_from('>H', ram, 0xd418)[0]
    gate = first_gate(program, ram, cursor)
    eligible = gate is not None and gate != 0xffff and gate <= phase
    assert calls.get('0x1a470', 0) == (1 if eligible else 0), (case, gate, phase, calls)
    assert calls['single_entry_calls'] == 1
    assert result['a6'] == incoming[12]
    if not eligible:
        assert output == bytes(ram)
        expected = incoming[7] if gate is None else (incoming[7] & 0xffff0000) | gate
        assert result['d7'] == expected, (case, result['d7'], expected)
        assert result['a0'] == cursor
    if case['family'] != 'live-phase-update-between-records':
        assert_evidence(case, ram, output, calls)
    if case['family'] in ('two-eligible-records-single-vs-loop', 'actual-cli-single-carry'):
        if case.get('sequence_position', 0) == 0:
            assert result['a0'] == 0x106018 and struct.unpack_from('>I', output, 0xd40e)[0] == 0x106018
        elif case['sequence_position'] == 1:
            assert result['a0'] == 0x106028
        else:
            assert gate == 0xffff and not eligible
    if case['family'] == 'live-phase-update-between-records':
        assert calls.get('0x1a470') == 1
    if case.get('following_unmapped'):
        assert result['a0'] == 0x110000 and struct.unpack_from('>I', output, 0xd40e)[0] == 0x110000
        assert not any(address < 0x111000 and address+size > 0x110000 for address, size in reads)
    return eligible


def main():
    root = Path(__file__).resolve().parents[1]
    program, source = load_verified_program(root)
    assert sha(program) == SOURCE_SHA256
    cases, paths, manifests = cases_for_single(root, program)
    folder = root/'artifacts/scene_placement_single'
    folder.mkdir(parents=True, exist_ok=True)
    exe = root/'build/execute_scene_placement'
    binary = sha(exe.read_bytes())
    core = [dict(file=name, sha256=sha((root/name).read_bytes())) for name in CORE_FILES]
    dependencies = [root/item['file'] for item in paths]
    inp, out = folder/'input.bin', folder/'cpp.bin'
    report_path = folder/'verification.json'
    report_path.unlink(missing_ok=True)
    observer = SingleObserver(program)
    rows = []
    previous = {}
    comparisons = []
    def cli(entry, registers, windows=dependencies):
        return subprocess.run([str(exe), str(entry)]+list(map(str, registers))+
            [str(inp), str(out)]+list(map(str, windows)), capture_output=True, text=True)
    for index, case in enumerate(cases):
        prior = previous.get(case.get('sequence')) if case.get('sequence_position', 0) > 0 else None
        ram, incoming = prepare(case, prior)
        expected, native, calls = observer.run(case, ram, incoming)
        reads = list(observer.reads)
        eligible = check_single_evidence(program, case, ram, incoming, expected, native, calls, reads)
        inp.write_bytes(ram)
        actual = cli(ENTRY, incoming)
        assert not actual.returncode, (index, case, actual.stderr)
        result = json.loads(actual.stdout)
        assert result.pop('entry') == ENTRY
        cpp = out.read_bytes()
        assert inp.read_bytes() == ram
        if native != result or expected != cpp:
            failure = dict(case_index=index, fixture=case, incoming=incoming, native=native, cpp=result,
                differences=[(hex(BASE+i), a, b) for i, (a, b) in enumerate(zip(expected, cpp)) if a != b][:30])
            (folder/'failure.json').write_text(json.dumps(failure, indent=2)+'\n')
            raise AssertionError(failure)
        rows.append(dict(case_index=index, fixture=case, incoming=dict(zip(KEYS, incoming)),
            result=result, input_ram_sha256=sha(ram), ram_sha256=sha(cpp), eligible=eligible,
            native_calls=calls, native_data_read_count=len(reads), final_pc=RETURN,
            final_a7=STACK+4, mmio_writes=0))
        if case.get('following_unmapped'):
            rows[-1]['following_unmapped_page'] = dict(start=0x110000, size=0x1000, reads=0)
        if case['family'] == 'two-eligible-records-single-vs-loop':
            loop_case = dict(case)
            loop_case['entry'] = 0x1a414
            loop_ram, loop_regs, loop_calls = observer.run(loop_case, ram, incoming)
            assert loop_calls.get('0x1a470') == 2 and loop_regs['a0'] == 0x106028
            assert calls.get('0x1a470') == 1 and native['a0'] == 0x106018
            comparisons.append(dict(single_calls=1, loop_calls=2, single_cursor=native['a0'],
                loop_cursor=loop_regs['a0'], same_input_ram_sha256=sha(ram),
                single_ram_sha256=sha(expected), loop_ram_sha256=sha(loop_ram)))
        if 'sequence' in case:
            previous[case['sequence']] = (cpp, [result[k] for k in KEYS])
    negatives = []
    sample = next(c for c in cases if c['family'] == 'following-record-unmapped-never-read')
    ram, incoming = prepare(sample)
    sentinel = b'single-placement-output-preserved\0\xff'
    def reject(data, registers=incoming, windows=dependencies, label='invalid', expected_error=None):
        inp.write_bytes(data)
        out.write_bytes(sentinel)
        actual = cli(ENTRY, registers, windows)
        assert actual.returncode and inp.read_bytes() == data and out.read_bytes() == sentinel, (label, actual.stdout, actual.stderr)
        if expected_error is not None:
            assert expected_error in actual.stderr, (label, actual.stderr)
        negatives.append(dict(failure=label, input_output_preserved=True, native_executed=False,
                              stderr=actual.stderr.strip()))
    late = bytearray(ram)
    struct.pack_into('>H', late, 0xfff2, 2)
    reject(late, label='late-inline-read-after-allocation-unmapped-next-address-rollback',
           expected_error='missing, ambiguous or cross-window scene placement read')
    for length in (1, 3, 0x8000, 0xffff):
        data = bytearray(ram)
        struct.pack_into('>H', data, 0xfff2, length)
        reject(data, label='late-unsupported-inline-count-after-allocation-rollback',
               expected_error='unsupported scene placement payload length')
    for pointer in (0x10ff96, 0xffffffff):
        data = bytearray(ram)
        struct.pack_into('>I', data, 0x4c9c, pointer)
        reject(data, label='late-allocator-invalid-free-node-rollback')
    for pointer in (0, 0x100001, 0x10ff96, 0xffffffff):
        registers = list(incoming)
        registers[12] = pointer
        reject(ram, registers, label='late-allocator-invalid-parent-rollback')
    fixed = next(c for c in cases if c['family'] == 'canonical-record-cursor-gate-allocation-motion' and c['motion'] == 0 and c['phase'] == first_gate(program, bytes(65536), c['cursor']))
    fixed_ram, fixed_regs = prepare(fixed)
    reject(fixed_ram, fixed_regs, windows=[], label='missing-fixed-placement-window')
    for pointer in (1, 0x100001, 0x10fff2, 0xffffffff):
        data = bytearray(ram)
        struct.pack_into('>I', data, 0xd40e, pointer)
        reject(data, label='invalid-live-cursor')
    for size in (0, 65535, 65537):
        reject(bytes(size), label='invalid-RAM-size')
    for item in paths+manifests+core:
        assert sha((root/item['file']).read_bytes()) == item['sha256']
    assert sha(exe.read_bytes()) == binary and sha(program) == SOURCE_SHA256
    placement_manifest = json.loads((root/'extracted/runtime/scene_placements/manifest.json').read_text())
    expected_roots = {r['source_cpu_address'] for r in placement_manifest['resources']}
    expected_records = {r['cpu_address'] for item in placement_manifest['resources'] for r in item['records']}
    expected_terminals = {r['terminal_cpu_address'] for r in placement_manifest['resources']}
    covered_roots = {r['fixture']['cursor'] for r in rows if r['fixture']['family'] == 'canonical-root'}
    covered_records = {r['fixture']['cursor'] for r in rows if r['fixture']['family'] == 'canonical-record-cursor-gate-allocation-motion'}
    covered_terminals = {r['fixture']['cursor'] for r in rows if r['fixture']['family'] == 'canonical-terminal'}
    expected_motions = {r['cpu'] for r in paths if '/motion_' in r['file']}
    covered_motions = {r['fixture']['motion'] for r in rows if r['fixture']['family'] == 'all37-canonical-motion-input-fraction'}
    assert covered_roots == expected_roots and covered_records == expected_records
    assert covered_terminals == expected_terminals and covered_motions == expected_motions
    assert sha((root/source['path']).read_bytes()) == SOURCE_SHA256
    report = dict(source=source, binary_sha256=binary, native_core='Unicorn '+unicorn.__version__,
        core_source_files=core, verifier_sha256=sha(Path(__file__).read_bytes()),
        cases=len(rows), completed_cases=len(rows), negative_cases=len(negatives),
        full_ram_13_registers_equal=True, all_RTS_A7_valid=True, mmio_writes=0,
        original_rom_immutable=True, positive_input_RAM_preserved=True,
        canonical_roots=len(covered_roots), canonical_records=len(covered_records),
        canonical_terminals=len(covered_terminals), available_motion_resources=len(expected_motions),
        covered_root_cpu_addresses=sorted(covered_roots), covered_record_cpu_addresses=sorted(covered_records),
        covered_terminal_cpu_addresses=sorted(covered_terminals), covered_motion_cpu_addresses=sorted(covered_motions),
        resources=paths, manifests=manifests,
        single_vs_loop=comparisons, cli_carry_sequences=len(previous),
        cli_carry_calls=sum('sequence' in c for c in cases),
        cli_calls_consuming_previous_outputs=sum(c.get('sequence_position', 0) > 0 for c in cases),
        results=rows, negative_results=negatives,
        scope='Unpatched original1a442 continuously through1a470/19802/28ae/43e08 toRTS without in-call SR reads or callee resets. '
              'Full64KiB RAM and D0..D7/A0/A1/A2/A4/A6 equality; exact single helper-call evidence, all18roots/24records and37motion resources available. '
              'Controlled synthetic RAM aliases, phase inputs, allocation success/fallback and genuinely unmapped following page; no next record read or loop substitution. '
              'Three actualCLI carry calls consume previous RAM/registers; the two resumed calls make no host RAM/register writes. Initial controlled fixtures explicitly set cursor and phase, which can alias record bytes. Negative CLI cases reject unsupported/late errors atomically. '
              'Returned CCR, natural scheduling and callback execution are not claimed.')
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows), negative_cases=len(negatives),
        binary_sha256=binary, report_sha256=sha(report_path.read_bytes()))))


if __name__ == '__main__':
    main()
