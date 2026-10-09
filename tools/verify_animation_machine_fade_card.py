"""Original fade/timer/BIOS-card-boundary/dispatcher native evidence vs the public machine API.

Controlled fixtures; no expected-register injection. The frozen native observation is an
immutable input (this verifier never invokes the observer main). C++ resumes only from
the previous actual C++ output plus the host changes declared in the native step record.
The BIOS (c00468) is never executed; frame re-entry is a declared PC change, not a scheduler.
"""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import verify_animation_machine as common
import verify_animation_machine_callers as helpers
from disassemble_program import load_verified_program

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/animation_machine_fade_card_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_fade_card_native'
NATIVE_SHA = 'f53387b7122286eca94c55371a34a09f900489eb9ab2766f9c98e086da7f57fc'
NATIVE_TOOL_SHA = '01d932ba16a1ab16679b888d5b02b53b5ea071b194aaa1fcbd345f3a0672baf5'
BIOS = 0xc00468
MARKER = struct.pack('>BII', 1, 0xdeadbeef, 0x87)
CONTRACT_PCS = (0x4804e, 0x4805e, 0x4806a, 0x48074, 0x48084, 0x48090, 0x4809a, 0x480a0,
                0x480a6, 0x480ac, 0x480b6, 0xc364, 0xc37c, 0xc38e, 0xc3a2, 0xc3b8,
                0x28ae, 0x290e, 0x2a00, 0x2a02, 0x2ab8, 0x2ac2, 0x48072, 0x48098,
                0x480b4, 0x4806e, 0x48094, 0x480b0, 0xc38a, 0x28ba, 0x28c2, 0x28d6,
                0x8c16, 0xcaf0)
BOUND_BRANCH_PCS = (0x4806e, 0x48094, 0x480b0, 0xc38a, 0x28ba, 0x28c2, 0x28d6)
FLOW_ONLY = ('lea', 'movea', 'pea', 'jsr', 'jmp', 'bsr', 'bra', 'rts', 'movem', 'nop', 'btst', 'bset', 'bclr', 'bchg',
             'beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls',
             'bge', 'blt', 'bgt', 'ble')
CARRY_NAME = {0: 'Unknown', 1: 'Clear', 2: 'Set'}


def digest(path):
    return helpers.digest(path)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fold_outputs(pvc, bank, events):
    """Independent PVC effects plus native video/watchdog writes in total order."""
    ports = []
    for event in events:
        if event['access'] != 'write':
            continue
        address, size = event['address'], event['size']
        if 0x2fe000 <= address < 0x300000:
            pvc, bank, encoded = common.fold_device(pvc, bank, [event])
            assert len(encoded) == 9
            ports.append(encoded)
        elif event['region'] in ('video', 'watchdog'):
            assert ((address == 0x3c0000 and size in (2, 4)) or
                    (address == 0x3c0004 and size == 2) or
                    (address == 0x300001 and size == 1))
            raw = bytes.fromhex(event['bytes'])
            assert len(raw) == size
            ports.append(struct.pack('>BII', size, address, int.from_bytes(raw, 'big')))
    return pvc, bank, b''.join(ports)


def load_rows(report):
    """All native rows with their saved payload files (hash checked against the report)."""
    rows = []
    for row in report['results'] + report['guarded_results']:
        for kind in ('phases', 'continuous_control'):
            for phase in row[kind]:
                data = {}
                for name, expected in phase['artifacts'].items():
                    value = (NATIVE_DIR / name).read_bytes()
                    assert sha(value) == expected, name
                    data[name.rsplit('phase_%03d_' % phase['index'], 1)[1]] = value
                phase['_data'] = data
                phase['_trace'] = json.loads(data['trace.json'])
                for snapshot in phase['snapshots']:
                    snapshot['_ram'] = (NATIVE_DIR / snapshot['artifacts']['ram']).read_bytes()
                    snapshot['_pvc'] = (NATIVE_DIR / snapshot['artifacts']['pvc']).read_bytes()
                    assert sha(snapshot['_ram']) == phase['artifacts'][snapshot['artifacts']['ram']]
                    assert sha(snapshot['_pvc']) == phase['artifacts'][snapshot['artifacts']['pvc']]
        rows.append(row)
    return rows


def audit_program_reads(program, fx, phases):
    """Reconstruct each live bank from ordered writes, independently of tags."""
    bank = fx['bank_state'][0]
    ff8, ff9 = fx['bank_state'][1], fx['bank_state'][2]
    counts = dict(fixed_reads=0, bank_reads=0, PVC_writes=0)
    for phase in phases:
        assert (phase['bank_before'], phase['ff8_before'], phase['ff9_before']) == (bank, ff8, ff9)
        for event in phase['_trace']['events']:
            address, size = event['address'], event['size']
            raw = bytes.fromhex(event['bytes'])
            assert len(raw) == size
            if event['region'] == 'pvc':
                assert event['access'] == 'write' and size == 2
                if address == 0x2ffff0:
                    ff8 = int.from_bytes(raw, 'big')
                else:
                    assert address == 0x2ffff2
                    ff9 = int.from_bytes(raw, 'big')
                bank, ff8, ff9 = common.pvc_bank_update(ff8, ff9)
                assert (event['bank_after'], event['ff8_after'], event['ff9_after']) == (bank, ff8, ff9)
                counts['PVC_writes'] += 1
            elif event['region'] in ('fixed', 'bank'):
                assert event['access'] == 'read'
                if event['region'] == 'fixed':
                    assert 0 <= address <= 0x100000 - size
                    physical = address
                    counts['fixed_reads'] += 1
                else:
                    assert 0x200000 <= address <= 0x2fe000 - size
                    physical = bank + address - 0x200000
                    assert (event['bank_at_read'], event['physical_rom_offset']) == (bank, physical)
                    counts['bank_reads'] += 1
                assert 0 <= physical <= len(program) - size
                assert raw == program[physical:physical + size]
        assert (phase['modeled_bank'], phase['ff8_after'], phase['ff9_after']) == (bank, ff8, ff9)
    return counts


def audit_native(program, source):
    path = NATIVE_DIR / 'observation.json'
    assert NATIVE_SHA and NATIVE_TOOL_SHA, 'native freeze required'
    assert digest(path) == NATIVE_SHA
    assert digest(ROOT / 'tools/observe_animation_machine_fade_card.py') == NATIVE_TOOL_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None
    assert report['tool_sha256'] == NATIVE_TOOL_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase',
                'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['rom_stat_start'] == report['rom_stat_end']
    refs = helpers.audit_references(ROOT, NATIVE_DIR, report)
    refs[str(path.resolve())] = NATIVE_SHA
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    assert digest(report['oracle']['library']) == report['oracle']['library_sha256']
    static = json.loads((NATIVE_DIR / 'source.json').read_text())
    assert static['source'] == source and static['boundary_stop_pc'] == BIOS
    instructions = {}
    for instruction in static['instructions']:
        at, size = instruction['rom_offset'], instruction['size']
        assert bytes(bytearray.fromhex(instruction['raw'])) == program[at:at + size]
        instructions[instruction['cpu_address']] = instruction
    assert BIOS not in instructions
    covered = set(report['covered_PCs'])
    missing = [hex(pc) for pc in CONTRACT_PCS if pc not in covered]
    assert not missing, missing
    declared_targets = {0x4806b, 0x480bc, 0x4c3a2}   # guard targets, refused before execution
    assert covered - declared_targets <= set(instructions) | {BIOS}
    rows = load_rows(report)
    assert len(rows) == report['cases'] + report['guarded_cases']
    split_count = sum(len(r['phases']) for r in rows)
    control_count = sum(len(r['continuous_control']) for r in rows)
    assert (split_count, control_count) == (report['total_split_phases'], report['total_control_phases'])
    assert report['fresh_CPU_runs'] == 4 * len(rows)
    program_reads = dict(fixed_reads=0, bank_reads=0, PVC_writes=0)
    for row in rows:
        assert row['reproduced_twice'] and row['continuous_split_equivalent']
        assert bool(row['guarded']) == (row['group'] == 'guard' or row['label'].startswith('guard-'))
        fx = row['fixture']
        for kind in ('phases', 'continuous_control'):
            counts = audit_program_reads(program, fx, row[kind])
            if kind == 'phases':
                for key, value in counts.items():
                    program_reads[key] += value
        audit_split_control(row)
        for phase in row['phases'] + row['continuous_control']:
            assert phase['carry'] is None and not phase['branch_evidence']
            assert phase['counts']['external_reads'] == sum(e['region'] == 'external'
                                                          for e in phase['_trace']['events'])
            ports = [e for e in phase['_trace']['events'] if e['region'] in ('pvc', 'video', 'watchdog')]
            assert phase['_data']['ports.bin'] == b''.join(
                struct.pack('>BII', e['size'], e['address'], int(e['bytes'], 16)) for e in ports)
    return report, rows, refs, instructions, program_reads, control_count


def audit_split_control(row):
    """Split concatenation equals the continuous control; checkpoints equal snapshots."""
    split, control = row['phases'], row['continuous_control']
    steps = sorted({p['step'] for p in split})
    assert steps == sorted({p['step'] for p in control}) and len(control) == len(steps)
    for step in steps:
        parts = [p for p in split if p['step'] == step]
        whole = [p for p in control if p['step'] == step]
        assert len(whole) == 1
        whole = whole[0]
        assert parts[0]['host_changes'] == whole['host_changes']
        assert all(not p['host_changes'] for p in parts[1:])
        assert parts[0]['incoming'] == whole['incoming']
        pcs, events = [], []
        for p in parts:
            pcs.extend(p['_trace']['pcs'][:-1])
            events.extend(p['_trace']['events'])
        pcs.extend(parts[-1]['_trace']['pcs'][-1:])
        assert pcs == whole['_trace']['pcs']
        assert events == whole['_trace']['events']
        last = parts[-1]
        for key in ('outgoing', 'modeled_bank', 'guard'):
            assert last[key] == whole[key], (row['label'], step, key)
        assert last['_data']['ram_after.bin'] == whole['_data']['ram_after.bin']
        assert last['_data']['pvc_after.bin'] == whole['_data']['pvc_after.bin']
        checkpoints = {p['outgoing']['pc']: (p['outgoing'], p['_data']['ram_after.bin'],
                                             p['_data']['pvc_after.bin'])
                       for p in parts[:-1] if p['guard'] is None}
        seen = set()
        for snapshot in whole['snapshots']:
            pc = snapshot['registers']['pc']
            assert pc not in seen and checkpoints[pc] == (snapshot['registers'], snapshot['_ram'], snapshot['_pvc'])
            seen.add(pc)
        assert seen == set(checkpoints), (row['label'], step)


def initial_sources(rows):
    sources = {}
    for row in rows:
        for phase in row['phases']:
            sources.setdefault(sha(phase['_data']['ram_after.bin']), []).append(
                (row['label'], phase, 'ram'))
    return sources


def apply_changes(ram, state, changes):
    """Declared host changes on top of previous actual C++ outputs only."""
    ram = bytearray(ram)
    state = dict(state)
    for change in changes:
        kind = change['kind']
        if kind == 'ram':
            at, size = change['address'] & 65535, change['size']
            assert 0 <= at <= 65536 - size
            common.native.put(ram, change['address'], size, change['value'])
        elif kind == 'pc':
            assert state['pc'] == change['pc_before']
            state['pc'] = change['to']
        elif kind == 'a7_add':
            assert state['a7'] == change['a7_before']
            state['a7'] = (state['a7'] + change['delta']) & 0xffffffff
        else:
            raise AssertionError(kind)
    return bytes(ram), state


def start_of_row(row, sources):
    fx = row['fixture']
    first = row['phases'][0]
    state = dict({k: v for k, v in fx['initial_regs'].items() if k != 'a7'},
                 a7=fx['initial_a7'], pc=fx['entry_pc'], carry=0)
    if row['group'] in ('connected', 'chain'):
        assert not first['host_changes'] and first['step'] == 0
        ram, pvc = first['_data']['ram_before.bin'], first['_data']['pvc_before.bin']
        origin = 'fresh native 47fe8 prepared fixture'
    else:
        found = sources.get(fx['initial_RAM_sha256'])
        assert found, row['label']
        origin_label, source_phase, _ = found[0]
        ram = source_phase['_data']['ram_after.bin']
        pvc = source_phase['_data']['pvc_after.bin']
        out = source_phase['outgoing']
        assert (source_phase['modeled_bank'], source_phase['ff8_after'], source_phase['ff9_after']) == tuple(fx['bank_state'])
        assert out['pc'] == fx['entry_pc']
        assert (out['a7'] == fx['initial_a7']) == (row['label'] != 'guard-odd-A7-push')
        diff = sorted(k for k, v in fx['initial_regs'].items() if out[k] != v)
        if row['label'] == 'guard-odd-A7-push':
            assert fx['initial_a7'] == out['a7'] + 1
        assert diff == {'guard-odd-A6': ['a6'], 'transition-frame-127-D3-high-word': ['d3']}.get(row['label'], []), (row['label'], diff)
        origin = 'recorded native output of ' + origin_label
    assert sha(pvc) == fx['initial_PVC_sha256']
    return ram, state, pvc, fx['bank_state'][0], origin


def classify_carry(instructions, carry, pcs):
    """Source-opcode classification of C only (no native SR). Known only via ORI/ANDI CCR."""
    for pc in pcs:
        item = instructions[pc]
        name = item['mnemonic'].split('.')[0]
        if name == 'ori' and item['op_str'] == '#$1, ccr':
            carry = 2
        elif name == 'andi' and item['op_str'] == '#$fe, ccr':
            carry = 1
        elif name in FLOW_ONLY:
            pass
        else:
            carry = 0
    return carry


def compare(exe, rows, resources, instructions):
    sources = initial_sources(rows)
    out_rows = []
    totals = dict(cases=0, split=0, control=0, resumes=0, waits=0, ports=0, reads=0,
                  carry_checks=0, guard_rows=0)
    ends = {}
    guards = []
    carry_histogram = {0: 0, 1: 0, 2: 0}
    for row in rows:
        fx = row['fixture']
        ram, state, pvc, bank, origin = start_of_row(row, sources)
        expected_pvc, expected_bank = pvc, bank
        ends[(row['label'], -1)] = (ram, dict(state), pvc, bank)
        results = []
        step_starts = {}
        for j, phase in enumerate(row['phases']):
            data = phase['_data']
            if phase['guard'] is not None:
                assert j == len(row['phases']) - 1 and row['guarded']
                ram, state2 = apply_changes(ram, state, phase['host_changes'])
                assert ram == data['ram_before.bin']
                guards.append((row, phase, ram, state2, pvc, bank, phase['step']))
                break
            ram, state = apply_changes(ram, state, phase['host_changes'])
            if phase['host_changes']:
                totals['resumes'] += 0
            assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming'], (row['label'], j)
            assert ram == data['ram_before.bin'], (row['label'], j)
            if phase['phase_in_step'] == 0:
                step_starts[phase['step']] = (ram, dict(state), pvc, bank, expected_pvc, expected_bank)
            events = phase['_trace']['events']
            expected_pvc, expected_bank, portbytes = fold_outputs(expected_pvc, expected_bank, events)
            assert expected_bank == phase['modeled_bank']
            assert portbytes == data['ports.bin']
            actual = common.invoke(exe, OUT, 'c%03d_split_%03d' % (row['index'], j), ram, state,
                                   pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
            assert actual[0]['ok'] and not actual[4], (row['label'], j, phase['stop_pc'], actual[4])
            common.check_result(actual, dict(outgoing=phase['outgoing'], events=events,
                                             ram_after=data['ram_after.bin']),
                                expected_pvc, expected_bank, portbytes)
            assert actual[0]['status'] == 0
            result, ram, pvc, _, _ = actual
            executed = phase['_trace']['pcs'][:-1]
            want_carry = classify_carry(instructions, state['carry'], executed)
            assert result['carry'] == want_carry, (row['label'], j, hex(phase['outgoing']['pc']),
                                                    result['carry'], want_carry)
            carry_histogram[result['carry']] += 1
            totals['carry_checks'] += 1
            state = {k: result[k] for k in common.STATE_KEYS}
            bank = result['bank_base']
            totals['waits'] += 0
            totals['reads'] += result['external_reads']
            totals['ports'] += len(portbytes) // 9
            if j and phase['phase_in_step'] == 0:
                totals['resumes'] += 1
            elif j:
                totals['resumes'] += 1
            results.append(dict(step=phase['step'], label=phase['label'], stop_pc=phase['stop_pc'],
                                carry=CARRY_NAME[result['carry']], actual_previous_outputs_used=bool(j),
                                full_RAM_16R_PC_PVC_bank_ports_status_reads_equal=True))
            ends[(row['label'], phase['step'])] = (ram, dict(state), pvc, bank)
        # continuous control: one C++ call per step from the split step start
        control_rows = 0
        for phase in row['continuous_control']:
            if phase['guard'] is not None:
                continue
            step = phase['step']
            c_ram, c_state, c_pvc, c_bank, e_pvc, e_bank = step_starts[step]
            data = phase['_data']
            assert {k: c_state[k] for k in common.REGS + ('pc',)} == phase['incoming']
            e_pvc, e_bank, portbytes = fold_outputs(e_pvc, e_bank, phase['_trace']['events'])
            assert e_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
            actual = common.invoke(exe, OUT, 'c%03d_control_%03d' % (row['index'], step), c_ram, c_state,
                                   c_pvc, c_bank, resources, stop=phase['stop_pc'], external=fx['external'])
            assert actual[0]['ok'] and not actual[4], (row['label'], step, actual[4])
            common.check_result(actual, dict(outgoing=phase['outgoing'], events=phase['_trace']['events'],
                                             ram_after=data['ram_after.bin']), e_pvc, e_bank, portbytes)
            end = ends[(row['label'], step)]
            assert (actual[1], {k: actual[0][k] for k in common.STATE_KEYS}, actual[2], actual[0]['bank_base']) == end
            control_rows += 1
        totals['cases'] += 1
        totals['split'] += len(results)
        totals['control'] += control_rows
        out_rows.append(dict(index=row['index'], label=row['label'], group=row['group'], origin=origin,
                             split_phases=len(results), control_steps=control_rows, phases=results))
    # fresh frame rows must equal the long-lived chain frames in actual C++ too
    chain = next(r for r in rows if r['group'] == 'chain')
    for row in rows:
        if row['group'] == 'fresh-frame':
            number = int(row['label'].rsplit('-', 1)[1])
            fresh_end = ends[(row['label'], 0)]
            chain_end = ends[(chain['label'], number)]
            strip = lambda e: (e[0], {k: v for k, v in e[1].items() if k != 'carry'}, e[2][:0x1ff0] + e[2][0x1ff4:], e[3])  # raw native PVC ff8/ff9 vs masked device storage excluded
            # Fresh rows declare incoming carry Unknown; chain carries C++ history.
            a, b = strip(fresh_end), strip(chain_end)
            assert a == b, (row['label'], a[0] == b[0], {k: (a[1][k], b[1][k]) for k in a[1] if a[1][k] != b[1][k]}, a[2] == b[2], a[3], b[3])
    totals['carry_histogram'] = {CARRY_NAME[k]: v for k, v in carry_histogram.items()}
    return out_rows, totals, ends, guards


def compare_guards(exe, guards, resources):
    rows = []
    for row, phase, ram, state, pvc, bank, step in guards:
        guard = phase['guard']
        expected = row['expected_guard']
        for key, value in expected.items():
            assert guard.get(key) == value, (row['label'], key)
        problem = guard['problem']
        if problem == 'unsupported_odd_data_access':
            causes = ('program bus requires even WORD/LONG address', 'even WORD/LONG')
        elif problem == 'unsupported_code_target' and guard['target'] & 1:
            causes = ('animation fade card odd JSR target',)
        elif problem == 'unsupported_code_target':
            causes = ('unsupported animation machine PC',)
        else:
            assert problem == 'unmapped_or_protected'
            causes = ('unsupported animation machine write device', 'unsupported program bus device address',
                      'program bus write requires', 'unmapped')
        stop = phase['stop_pc']
        result, outgoing, out_pvc, ports, error = common.invoke(
            exe, OUT, 'guard_%s' % row['label'], ram, dict(state, carry=2), pvc, bank, resources,
            stop=stop, external=row['fixture']['external'])
        assert not result['ok'] and any(c in error for c in causes), (row['label'], error)
        assert {k: result[k] for k in common.STATE_KEYS} == dict(state, carry=2)
        assert outgoing == ram and out_pvc == pvc and result['bank_base'] == bank
        assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1
        rows.append(dict(label=row['label'], native_guard=guard, checked_API_error=error,
                         all_API_outputs_preserved=True, native_fault_rollback_equivalence_claimed=False))
    return rows


def negatives(exe, rows, ends, resources):
    out = []
    chain = next(r for r in rows if r['group'] == 'chain')
    ram, state, pvc, bank = ends[(chain['label'], 0)]
    ram157, state157, pvc157, bank157 = ends[(chain['label'], 157)]
    external = chain['fixture']['external']

    def reject(label, changes, causes, memory=(), base=(None,), selected=None, stop=0xff000):
        r, s, p, b = base if base != (None,) else (ram, state, pvc, bank)
        s = dict(s, carry=2)
        s.update(changes)
        r = bytearray(r)
        for address, size, value in memory:
            common.native.put(r, address, size, value)
        r = bytes(r)
        result, outgoing, out_pvc, ports, error = common.invoke(
            exe, OUT, 'negative_' + label, r, s, p, b, resources if selected is None else selected,
            stop=stop, external=external)
        assert not result['ok'] and any(c in error for c in causes), (label, error)
        assert {k: result[k] for k in common.STATE_KEYS} == s
        assert outgoing == r and out_pvc == p and ports == MARKER and result['bank_base'] == b
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        out.append(dict(label=label, error=error, all_API_outputs_preserved=True,
                        native_exception_rollback_equivalence_claimed=False))

    for pc in BOUND_BRANCH_PCS:
        reject('bound_branch_direct_entry_%06x' % pc, {'pc': pc}, ('unsupported animation fade card PC',))
    reject('BIOS_pc_has_no_executor', {'pc': BIOS}, ('unsupported animation machine PC',))
    reject('frame_helper_480bc_unsupported', {'pc': 0x480bc}, ('unsupported animation machine PC',))
    reject('dispatcher_entry_2aac_unsupported', {'pc': 0x2aac}, ('unsupported animation machine PC',))
    reject('BIOS_call_with_other_stop_rolls_back', {}, ('unsupported animation machine PC',),
           base=(ram157, dict(state157, pc=0xc364), pvc157, bank157), stop=0xff000)
    reject('connected_47fe8_without_ROM_chunks', {}, ('missing or ambiguous physical program bus ROM byte',),
           base=ends[(chain['label'], -1)], selected=[], stop=0x2ac2)
    base = (ram, dict(state, pc=0x2ab8), pvc, bank)
    reject('odd_A6_dispatcher_read', {'a6': state['a6'] + 1}, ('even WORD/LONG',), base=base)
    reject('odd_callback_JSR_target', {}, ('animation fade card odd JSR target',), base=base,
           memory=((state['a6'], 4, 0x4806b),))
    # Recursive JSR (A0)=2ab8 pushes descend the mirrored64KiB RAM until a live push
    # overwrites (A6) with return2ac2; dispatch then leaves via 2ac2 to an unsupported PC.
    reject('dispatcher_self_callback_stack_alias_then_unsupported_PC', {}, ('unsupported animation machine PC',), base=base,
           memory=((state['a6'], 4, 0x2ab8),))
    return out


def zero_step(exe, ends, rows, resources):
    chain = next(r for r in rows if r['group'] == 'chain')
    ram, state, pvc, bank = ends[(chain['label'], 0)]
    result_rows = []
    for pc in sorted(set(CONTRACT_PCS) | {BIOS, 0x47fe8, 0x2ac6, 0x2abe, 0x2ac0}):
        for carry in (0, 1, 2):
            s = dict(state, pc=pc, carry=carry)
            result, out_ram, out_pvc, ports, error = common.invoke(
                exe, OUT, 'zero_%06x_%d' % (pc, carry), ram, s, pvc, bank, resources, stop=pc)
            assert result['ok'] and not error and result['status'] == 0
            assert {k: result[k] for k in common.STATE_KEYS} == s
            assert out_ram == ram and out_pvc == pvc and result['bank_base'] == bank
            assert result['external_reads'] == 0 and not ports
            result_rows.append(dict(pc=pc, carry=carry, all_input_state_preserved=True))
    return result_rows


def source_carry_writers(exe, ends, rows, resources, program):
    chain = next(r for r in rows if r['group'] == 'chain')
    ram, state, pvc, bank = ends[(chain['label'], 0)]
    out = []
    for pc, stop, raw, expected in ((0x2908, 0x290c, '003c0001', 2), (0x290e, 0x2916, '41ed8e98023c00fe', 1)):
        assert program[pc:pc + len(raw) // 2].hex() == raw
        for incoming in (0, 1, 2):
            s = dict(state, pc=pc, carry=incoming, a5=0x108000)
            result, out_ram, out_pvc, ports, error = common.invoke(
                exe, OUT, 'source_carry_%06x_%d' % (pc, incoming), ram, s, pvc, bank, resources, stop=stop)
            assert result['ok'] and not error and result['carry'] == expected
            assert out_ram == ram and out_pvc == pvc and not ports
            out.append(dict(pc=pc, stop=stop, original_raw=raw, incoming_carry=incoming,
                            source_classified_carry=CARRY_NAME[expected], native_CCR_observation=False))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    report_path.unlink(missing_ok=True)
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_fade_card.py', 'tools/observe_animation_machine_fade_card.py',
                 'docs/analysis/animation-machine-fade-card-contract.md',
                 'engine/src/animation_machine_fade_card.cpp',
                 'engine/tests/animation_machine_fade_card_test.cpp'):
        inputs[name] = digest(ROOT / name)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    report, rows, native_refs, instructions, program_reads, control_count = audit_native(program, source)
    refs.update(native_refs)
    exe, command = helpers.compile_harness(ROOT, OUT)
    matches, totals, ends, guards = compare(exe, rows, resources, instructions)
    guarded = compare_guards(exe, guards, resources)
    negative = negatives(exe, rows, ends, resources)
    zero = zero_step(exe, ends, rows, resources)
    carry_writers = source_carry_writers(exe, ends, rows, resources, program)
    for name, expected in list(inputs.items()) + list(refs.items()):
        assert digest(ROOT / name) == expected, name
    assert (digest(rom), rom.stat().st_mtime_ns) == rom_guard
    refs.update({str(path.resolve()): digest(path) for path in OUT.iterdir()
                 if path.is_file() and path != report_path})
    unique = {}
    for name, expected in list(inputs.items()) + list(refs.items()):
        key = str((ROOT / name).resolve())
        assert key not in unique or unique[key] == expected
        unique[key] = expected
    result = dict(schema_version=1, source=source, inputs=inputs, artifacts=refs,
                  native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA,
                  actual_CPP=dict(totals, matches=matches),
                  original_program_read_audit=program_reads,
                  native_guards_checked_API=guarded,
                  native_continuous_control_phases_replayed=control_count,
                  negatives=negative, negative_count=len(negative) + len(guarded), zero_step=zero,
                  source_classified_carry_writers=carry_writers,
                  carry_check='C++ carry equals source-opcode walk over native-executed PCs (ORI/ANDI CCR known, flow-only preserved, else Unknown); native SR never read',
                  normalized_reference_paths=len(unique), compile_command=command, failure=None,
                  ROM_unchanged=True,
                  limits=['Controlled fixtures; frame re-entry is a declared PC-only change (A6/A7 previous real outputs), not a natural scheduler, IRQ or VBlank; other objects not run.',
                          'c00468 (BIOS) is never executed; the BIOS resume is declared host changes only (PC=c37c, A7+=4, BYTE 10fdc6). Other BIOS effects are unmodeled/unknown.',
                          'Declared RAM fixtures (cleanup object fields, 28ae pool/parent, 104ca4 base) are inputs, not original-measured preparation.',
                          'Native has no SR reads; carry is checked against source opcode classification only. No general CCR/timing/IRQ or hardware proof.',
                          'Video/watchdog are instruction-unit ordered register ports; no bus-cycle or rendered VRAM/pixel claim. PVC effects independently fold original ordered writes.',
                          'Resumes forward previous actual C++ outputs plus declared host changes; native incoming is only an assertion.',
                          'Native observation artifacts are audited by hash/trace consistency, not re-executed here.',
                          'Checked failures preserve API outputs, not original CPU fault rollback.'])
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=totals['cases'], split=totals['split'], control=totals['control'],
                         negatives=result['negative_count'], zero_step=len(zero),
                         carry=totals['carry_histogram'], sha256=digest(report_path))))


if __name__ == '__main__':
    main()
