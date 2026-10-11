"""Original card-child (c250/de424/e7c16) native evidence vs the public machine API.

Controlled fixtures; no expected-register injection. The frozen native observation is an
immutable input (this verifier never invokes the observer main). C++ resumes only from
the previous actual C++ output plus the host changes declared in the native step record.
The BIOS (c00468) is never executed; a29c is only a stop here (the card menu core executes it in
verify_animation_machine_card_menu.py) and the opening frame a370 is executed by the card menu open core
(verify_animation_machine_card_menu_open.py); a406, 9e94 and c2c8 are the remaining unexecuted boundaries here;
frame re-entry is a declared PC change, not a scheduler.
"""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import verify_animation_machine as common
import verify_animation_machine_callers as helpers
import verify_animation_machine_fade_card as fade
from disassemble_program import load_verified_program

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/animation_machine_card_child_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_card_child_native'
NATIVE_SHA = '3e48b69e4827d5a25f7085aee1c81bf6bc0b41a64daa159a3232e690c16f3312'
NATIVE_TOOL_SHA = 'd9b229b7ecd79f1e412ccc55e78c2c57061e376bf32fbbed83237272cb03b7ae'
BIOS = 0xc00468
A29C = 0xa29c
MARKER = struct.pack('>BII', 1, 0xdeadbeef, 0x87)
CONTRACT_PCS = (0xc250, 0xc258, 0xc25e, 0xc264, 0xc266, 0xc26c, 0xc274, 0xc27a, 0xc286, 0xc28e, 0xc290,
                0xc2a2, 0xde424, 0xde42a, 0xde42e, 0xde444, 0xde450, 0xde456, 0xde45a, 0xde460,
                0xde466, 0xde46c, 0xde474, 0xde478, 0xde47e, 0xde484, 0xde48a, 0xe7c16, 0xe7c1a,
                0xe7c1e, 0xe7c24, 0xe7c30, 0x2ab8, 0x2ac2, 0x8c16)
BOUND_BRANCH_PCS = (0xc28a,)
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
    assert digest(ROOT / 'tools/observe_animation_machine_card_child.py') == NATIVE_TOOL_SHA
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
    assert static['source'] == source and static['boundary_stop_pc'] == A29C
    instructions = {}
    for instruction in static['instructions']:
        at, size = instruction['rom_offset'], instruction['size']
        assert bytes(bytearray.fromhex(instruction['raw'])) == program[at:at + size]
        instructions[instruction['cpu_address']] = instruction
    assert A29C not in instructions and BIOS not in instructions
    covered = set(report['covered_PCs'])
    missing = [hex(pc) for pc in CONTRACT_PCS if pc not in covered]
    assert not missing, missing
    declared_targets = {A29C, 0xa2b8, 0x92bdcb15}   # stop boundary / guard targets, never executed
    assert covered - declared_targets <= set(instructions)
    assert {A29C, 0xa2b8} <= covered
    rows = load_rows(report)
    assert len(rows) == report['cases'] + report['guarded_cases']
    split_count = sum(len(r['phases']) for r in rows)
    control_count = sum(len(r['continuous_control']) for r in rows)
    assert (split_count, control_count) == (report['total_split_phases'], report['total_control_phases'])
    assert report['fresh_CPU_runs'] == 4 * len(rows) + 2
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


STATE_NO_CARRY = ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'pc')
ALLOWED_INITIAL_DIFF = {'guard-odd-A6-child': ['a6'], 'guard-odd-A7-push-child': ['a7'],
                        'boundary-7e-0000-fields-76-7a-7c-80': ['d0', 'd1'],
                        'boundary-7e-0000-fields-76-7a-7c-zero-ff': ['d0', 'd1']}
DECLARED_INITIAL = {'boundary-7e-0000-fields-76-7a-7c-80': dict(d0=0xabcd1234, d1=0x5678ef01),
                    'boundary-7e-0000-fields-76-7a-7c-zero-ff': dict(d0=0x1111, d1=0xffffffff)}


def fade_chain_bios_output(exe, program, source, resources, instructions_unused=None):
    """Re-run the (reviewed) fade/card chain in actual C++ to obtain the c00468 stop output."""
    fade.OUT = OUT / 'fade_chain'
    fade.OUT.mkdir(parents=True, exist_ok=True)
    report, rows, _refs, instructions, _reads, _control = fade.audit_native(program, source)
    chain = next(r for r in rows if r['group'] == 'chain')
    _out, _totals, ends, _guards = fade.compare(exe, [chain], resources, instructions)
    candidates = [(key, value) for key, value in ends.items() if key[0] == chain['label'] and value[1]['pc'] == BIOS]
    assert len(candidates) == 1, [k for k, _ in candidates]
    return candidates[0][0], candidates[0][1]


def rd(ram, address, size):
    return int.from_bytes(bytes(ram[(address + i) & 0xffff] for i in range(size)), 'big')


def masked_pvc(pvc):
    """Raw native PVC ff8/ff9 storage (1ff0..1ff3) vs masked device storage is excluded, as in earlier verifiers."""
    return pvc[:0x1ff0] + pvc[0x1ff4:]


def start_of_row(row, cpp_out, sources, bios_start):
    """C++ start state is the previous actual C++ output (never native expected registers)."""
    fx = row['fixture']
    native_pvc = row['phases'][0]['_data']['pvc_before.bin']
    assert sha(native_pvc) == fx['initial_PVC_sha256']
    native_masked = sha(masked_pvc(native_pvc))
    state = dict({k: v for k, v in fx['initial_regs'].items() if k != 'a7'},
                 a7=fx['initial_a7'], pc=fx['entry_pc'], carry=0)
    if fx['entry_pc'] == BIOS:
        key, (ram, src_state, pvc, bank) = bios_start
        origin = 'actual C++ output of the fade/card chain %s step %d (stop c00468)' % (key[0], key[1])
        assert sha(ram) == fx['initial_RAM_sha256'] and sha(masked_pvc(pvc)) == native_masked
        assert (bank, ) == (fx['bank_state'][0], )
        assert {k: src_state[k] for k in STATE_NO_CARRY} == {k: state[k] for k in STATE_NO_CARRY}
        return ram, state, pvc, bank, origin
    found = [c for c in sources.get(fx['initial_RAM_sha256'], [])
             if c[2]['outgoing']['pc'] == fx['entry_pc']]
    assert found, row['label']
    allowed = ALLOWED_INITIAL_DIFF.get(row['label'], [])
    def regs_diff(candidate):
        out = candidate['outgoing']
        return sorted(k for k in STATE_NO_CARRY if out[k] != state[k])
    best = [c for c in found if regs_diff(c[2]) == allowed]
    assert best, (row['label'], [regs_diff(c[2]) for c in found])
    index, j, source_phase = best[0]
    for key, value in DECLARED_INITIAL.get(row['label'], {}).items():
        assert state[key] == value, (row['label'], key)
    ram, src_state, pvc, bank = cpp_out[(index, j)]
    assert sha(masked_pvc(pvc)) == native_masked and bank == fx['bank_state'][0]
    assert (source_phase['modeled_bank'], source_phase['ff8_after'], source_phase['ff9_after']) == tuple(fx['bank_state'])
    diff = sorted(k for k in STATE_NO_CARRY if src_state[k] != state[k])
    assert diff == ALLOWED_INITIAL_DIFF.get(row['label'], []), (row['label'], diff)
    origin = 'actual C++ output of row %d phase %d (%s)' % (index, j, source_phase['label'])
    return ram, state, pvc, bank, origin


def compare(exe, rows, resources, instructions, bios_start):
    return compare_all(exe, rows, resources, instructions, bios_start)


def compare_all(exe, rows, resources, instructions, bios_start):
    sources = {}
    cpp_out = {}
    out_rows = []
    totals = dict(cases=0, split=0, control=0, resumes=0, ports=0, reads=0, carry_checks=0, guard_rows=0)
    ends = {}
    guards = []
    carry_histogram = {0: 0, 1: 0, 2: 0}
    for row in rows:
        fx = row['fixture']
        ram, state, pvc, bank, origin = start_of_row(row, cpp_out, sources, bios_start)
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
            totals['reads'] += result['external_reads']
            totals['ports'] += len(portbytes) // 9
            if j:
                totals['resumes'] += 1
            results.append(dict(step=phase['step'], label=phase['label'], stop_pc=phase['stop_pc'],
                                carry=CARRY_NAME[result['carry']], actual_previous_outputs_used=bool(j),
                                full_RAM_16R_PC_PVC_bank_ports_status_reads_equal=True))
            ends[(row['label'], phase['step'])] = (ram, dict(state), pvc, bank)
            cpp_out[(row['index'], j)] = (ram, dict(state), pvc, bank)
            sources.setdefault(sha(phase['_data']['ram_after.bin']), []).append((row['index'], j, phase))
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
    # fresh child frames must equal the long-lived chain outputs in actual C++ (matched by native output identity)
    chain = next(r for r in rows if r['group'] == 'chain')
    by_identity = {}
    for j, phase in enumerate(chain['phases']):
        if phase['phase_in_step'] == 0 and False:
            continue
        key = (sha(phase['_data']['ram_after.bin']), sha(phase['_data']['pvc_after.bin']), tuple(sorted(phase['outgoing'].items())))
        by_identity.setdefault(key, []).append(cpp_out[(chain['index'], j)])
    strip = lambda e: (e[0], {k: v for k, v in e[1].items() if k != 'carry'}, e[2][:0x1ff0] + e[2][0x1ff4:], e[3])
    chain_matches = 0
    for row in rows:
        if row['group'] != 'fresh-frame':
            continue
        for j, phase in enumerate(row['phases']):
            if phase['guard'] is not None:
                continue
            key = (sha(phase['_data']['ram_after.bin']), sha(phase['_data']['pvc_after.bin']), tuple(sorted(phase['outgoing'].items())))
            if key in by_identity:
                assert strip(cpp_out[(row['index'], j)]) == strip(by_identity[key][0]), (row['label'], j)
                chain_matches += 1
    assert chain_matches > 100, chain_matches
    totals['fresh_vs_chain_C++_phases_equal'] = chain_matches
    totals['carry_histogram'] = {CARRY_NAME[k]: v for k, v in carry_histogram.items()}
    return out_rows, totals, ends, guards


def compare_guards(exe, guards, resources, guard_errors):
    rows, superseded = [], []
    for row, phase, ram, state, pvc, bank, step in guards:
        stop = phase['stop_pc']
        result, outgoing, out_pvc, ports, error = common.invoke(
            exe, OUT, 'guard_%s' % row['label'], ram, dict(state, carry=2), pvc, bank, resources,
            stop=stop, external=row['fixture']['external'])
        if row['label'] in SUPERSEDED_GUARDS:
            # The frozen native guard stopped where the card menu had no executor; the card menu core now runs
            # a29c/a2b8, so the same input is a checked positive stop (the genuine unsupported boundary is a370).
            want_pc, why = SUPERSEDED_GUARDS[row['label']]
            assert result['ok'] and not error and result['pc'] == want_pc and result['status'] == 0, (row['label'], error)
            superseded.append(dict(label=row['label'], native_guard=phase['guard'], CPP_now_ok_at_stop=hex(want_pc),
                                   reason=why))
            continue
        assert not result['ok'], row['label']
        assert error.strip() == guard_errors[row['label']], (row['label'], error)
        assert {k: result[k] for k in common.STATE_KEYS} == dict(state, carry=2)
        assert outgoing == ram and out_pvc == pvc and result['bank_base'] == bank
        assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1
        rows.append(dict(label=row['label'], native_guard=phase['guard'], checked_API_error=error.strip(),
                         all_API_outputs_preserved=True, native_fault_rollback_equivalence_claimed=False))
    return rows, superseded


def negatives(exe, rows, ends, resources, neg_errors):
    out = []
    chain = next(r for r in rows if r['group'] == 'chain')
    external = chain['fixture']['external']
    ram2, state2, pvc2, bank2 = ends[(chain['label'], 2)]      # stop 2ab8 (dispatch entered)
    ram3, state3, pvc3, bank3 = ends[(chain['label'], 3)]      # child c250 first callback -> 2ac2
    ram4, state4, pvc4, bank4 = ends[(chain['label'], 4)]      # c266 frame -> 2ac2
    assert state2['pc'] == 0x2ab8 and state3['pc'] == 0x2ac2 and state4['pc'] == 0x2ac2

    def reject(label, base, changes=None, memory=(), selected=None, stop=0xff000):
        r, s, p, b = base
        s = dict(s, carry=2)
        s.update(changes or {})
        r = bytearray(r)
        for address, size, value in memory:
            common.native.put(r, address, size, value)
        r = bytes(r)
        result, outgoing, out_pvc, ports, error = common.invoke(
            exe, OUT, 'negative_' + label, r, s, p, b, resources if selected is None else selected,
            stop=stop, external=external)
        assert not result['ok'], label
        assert error.strip() == neg_errors[label], (label, error)
        assert {k: result[k] for k in common.STATE_KEYS} == s
        assert outgoing == r and out_pvc == p and ports == MARKER and result['bank_base'] == b
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        out.append(dict(label=label, error=error.strip(), all_API_outputs_preserved=True,
                        native_exception_rollback_equivalence_claimed=False))

    base4 = (ram4, state4, pvc4, bank4)
    for pc in BOUND_BRANCH_PCS:
        reject('bound_branch_direct_entry_%06x' % pc, base4, {'pc': pc})
    reject('mid_block_direct_entry_de44a', base4, {'pc': 0xde44a})
    # c2a8 -> a2b8 -> c2ba -> a370 -> c2c0 -> c2c8 -> c2f8 are all executed now (card menu push/open/close cores);
    # the RTS of c2f8 pops a stale non-code word, an odd PC: whole transaction rolls back (inferred mechanism, the
    # stops c2ba c2c0 c2c8 c2f8 from this entry were checked ok in this verifier, see mechanism_c2a8_* below).
    reject('c2a8_flow_runs_to_c2f8_RTS_then_unaligned_PC', base4, {'pc': 0xc2a8})
    # a406..a5d0 (input core), 9e94 and c2c8 (close core) are executed now; these PCs still have no executor.
    reject('a63c_trap_pc_has_no_executor', base4, {'pc': 0xa63c})
    reject('e84d6_pc_has_no_executor', base4, {'pc': 0xe84d6})
    reject('c00468_bios_pc_has_no_executor', base4, {'pc': 0xc00468})
    for stop in (0xc2ba, 0xc2c0, 0xc2c8, 0xc2f8):
        result, _, _, _, error = common.invoke(exe, OUT, 'mechanism_c2a8_%06x' % stop, ram4,
                                               dict(state4, pc=0xc2a8, carry=2), pvc4, bank4, resources,
                                               stop=stop, external=external)
        assert result['ok'] and not error and result['pc'] == stop and result['status'] == 0, (hex(stop), error)
    # 7e=0 borrow reaches JSR a29c. a29c and the opening frame a370 are executed now (card menu cores): with the
    # a29c stop the push stops there, with stop 2ac2 the frame returns to the dispatcher (positive control below),
    # and with any other stop the dispatcher goes on to the next object and meets the odd JSR target: full rollback.
    zero7e = ((state4['a6'] + 0x7e, 2, 0),)
    reject('a29c_call_then_open_frame_with_stop_ff000_rolls_back', (ram4, dict(state4, pc=0x2ab8), pvc4, bank4), memory=zero7e)
    reject('a29c_call_then_open_frame_with_stop_a406_rolls_back', (ram4, dict(state4, pc=0x2ab8), pvc4, bank4), memory=zero7e, stop=0xa406)
    reject('c286_odd_A6_read', (ram4, dict(state4, pc=0xc286), pvc4, bank4), {'a6': state4['a6'] + 1})
    reject('odd_A6_dispatcher_read', (ram4, dict(state4, pc=0x2ab8), pvc4, bank4), {'a6': state4['a6'] + 1})
    reject('odd_callback_JSR_target', (ram4, dict(state4, pc=0x2ab8), pvc4, bank4),
           memory=((state4['a6'], 4, 0xc287),))
    # Mechanism (checked, not assumed): (A6)=2ab8 makes JSR (A0) recurse, pushing 2ac2 each time; the
    # 64KiB-mirrored stack reaches (A6) and overwrites it with 2ac2, the dispatcher leaves through 2ac2 with
    # A6=8(A6)=2ac2 (a ROM address, whose first LONG 2c6e0008 is code bytes), and JSR (A0) targets 2c6e0008,
    # an even address with no executor.
    r5 = bytearray(ram4)
    common.native.put(r5, state4['a6'], 4, 0x2ab8)
    probe = dict(state4, pc=0x2ab8, carry=2)
    r5, p5 = bytes(r5), pvc4
    for number, stop in enumerate((0x2ac2, 0x2ab8, 0x2ac0)):
        result, r5, p5, _, error = common.invoke(exe, OUT, 'mechanism_self_%d' % number, r5, probe, p5, bank4,
                                                 resources, stop=stop, external=external)
        assert result['ok'] and not error and result['pc'] == stop, (number, error)
        probe = {k: result[k] for k in common.STATE_KEYS}
        if number == 0:
            assert rd(r5, probe['a6'], 4) == 0x2ac2 and probe['a7'] == 0x1f47fc
    assert probe['a6'] == 0x2ac2 and probe['a0'] == 0x2c6e0008 and probe['a0'] & 1 == 0
    reject('dispatcher_self_callback_stack_alias_then_JSR_2c6e0008_unsupported_PC',
           (ram4, dict(state4, pc=0x2ab8), pvc4, bank4), memory=((state4['a6'], 4, 0x2ab8),))
    # Positive control for the a29c rollback cases: the same 7e=0 input succeeds when a29c is the stop.
    r6 = bytearray(ram4)
    common.native.put(r6, state4['a6'] + 0x7e, 2, 0)
    result, r6, _, _, error = common.invoke(exe, OUT, 'mechanism_a29c_stop', bytes(r6),
                                            dict(state4, pc=0x2ab8, carry=2), pvc4, bank4, resources,
                                            stop=A29C, external=external)
    assert result['ok'] and not error and result['pc'] == A29C and result['a7'] == state4['a7'] - 8
    assert rd(r6, result['a7'], 4) == 0xc2a8 and rd(r6, result['a7'] + 4, 4) == 0x2ac2
    r7 = bytearray(ram4)
    common.native.put(r7, state4['a6'] + 0x7e, 2, 0)
    result, _, _, _, error = common.invoke(exe, OUT, 'mechanism_open_frame_stop_2ac2', bytes(r7),
                                           dict(state4, pc=0x2ab8, carry=2), pvc4, bank4, resources,
                                           stop=0x2ac2, external=external)
    assert result['ok'] and not error and result['pc'] == 0x2ac2 and result['a7'] == state4['a7'], error
    reject('connected_child_without_ROM_chunks', (ram3, dict(state3, pc=0x2ab8), pvc3, bank3), selected=[], stop=0x2ac2)
    return out


def zero_step(exe, ends, rows, resources):
    chain = next(r for r in rows if r['group'] == 'chain')
    ram, state, pvc, bank = ends[(chain['label'], 4)]
    result_rows = []
    for pc in sorted(set(CONTRACT_PCS) | {A29C, BIOS, 0xc28a, 0xc2a8, 0x2ac6, 0x2abe, 0x2ac0}):
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


SUPERSEDED_GUARDS = {
    'guard-stop-c2a8-never-reached': (0xc2a8, 'a29c is executed by the card menu core, so stop c2a8 is reached'),
    'guard-callback-a2b8': (0x2ac2, 'a2b8/a2bc are executed by the card menu core (JSR (A0)=a2b8 returns to 2ac2)'),
    'guard-run-past-a29c': (0x2ac2, 'a370 is executed by the card menu open core; the opening frame returns to the 2ac2 stop')}
SUPERSEDED_NEGATIVES = [
    dict(label='a406_pc_has_no_executor', now='executed by the card menu input core'),
    dict(label='a662_pc_has_no_executor', now='executed by the card menu close core'),
    dict(label='9e94_pc_has_no_executor', now='executed by the card menu close core'),
    dict(label='c2c8_pc_has_no_executor', now='executed by the card menu close core'),
    dict(label='c2a8_return_has_no_executor', now='c2a8 is a card menu push block; renamed to the c2f8 RTS rollback negative')]
GUARD_ERRORS = {
    'guard-odd-A6-child': 'program bus requires even WORD/LONG address',
    'guard-odd-A7-push-child': 'program bus requires even WORD/LONG address',
    'guard-dispatch-continues-to-sibling': 'animation fade card odd JSR target'}
NEG_ERRORS = {
    'bound_branch_direct_entry_00c28a': 'unsupported animation card child PC',
    'mid_block_direct_entry_de44a': 'unsupported animation card child PC',
    'c2a8_flow_runs_to_c2f8_RTS_then_unaligned_PC': 'unaligned animation machine PC',
    'a63c_trap_pc_has_no_executor': 'unsupported animation machine PC',
    'e84d6_pc_has_no_executor': 'unsupported animation machine PC',
    'c00468_bios_pc_has_no_executor': 'unsupported animation machine PC',
    'a29c_call_then_open_frame_with_stop_ff000_rolls_back': 'animation fade card odd JSR target',
    'a29c_call_then_open_frame_with_stop_a406_rolls_back': 'animation fade card odd JSR target',
    'c286_odd_A6_read': 'program bus requires even WORD/LONG address',
    'odd_A6_dispatcher_read': 'program bus requires even WORD/LONG address',
    'odd_callback_JSR_target': 'animation fade card odd JSR target',
    'dispatcher_self_callback_stack_alias_then_JSR_2c6e0008_unsupported_PC': 'unsupported animation machine PC',
    'connected_child_without_ROM_chunks': 'missing or ambiguous physical program bus ROM byte'}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    report_path.unlink(missing_ok=True)
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_card_child.py', 'tools/observe_animation_machine_card_child.py',
                 'docs/analysis/animation-machine-card-child-contract.md',
                 'engine/src/animation_machine_card_child.cpp',
                 'engine/tests/animation_machine_card_child_test.cpp'):
        inputs[name] = digest(ROOT / name)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    exe, command = helpers.compile_harness(ROOT, OUT)
    bios_start = fade_chain_bios_output(exe, program, source, resources)
    report, rows, native_refs, instructions, program_reads, control_count = audit_native(program, source)
    refs.update(native_refs)
    matches, totals, ends, guards = compare(exe, rows, resources, instructions, bios_start)
    guarded, superseded = compare_guards(exe, guards, resources, GUARD_ERRORS)
    negative = negatives(exe, rows, ends, resources, NEG_ERRORS)
    zero = zero_step(exe, ends, rows, resources)
    for name, expected in list(inputs.items()) + list(refs.items()):
        assert digest(ROOT / name) == expected, name
    assert (digest(rom), rom.stat().st_mtime_ns) == rom_guard
    refs.update({str(path.resolve()): digest(path) for path in OUT.rglob('*')
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
                  native_guards_checked_API=guarded, native_guards_superseded_by_card_menu_core=superseded,
                  negatives_superseded_by_card_menu_cores=SUPERSEDED_NEGATIVES,
                  native_continuous_control_phases_replayed=control_count,
                  negatives=negative, negative_count=len(negative) + len(guarded), zero_step=zero,
                  bios_start=dict(chain_label=bios_start[0][0], step=bios_start[0][1],
                                  ram_sha256=sha(bios_start[1][0])),
                  carry_check='C++ carry equals source-opcode walk over native-executed PCs (ORI/ANDI CCR known, flow-only preserved, else Unknown); native SR never read; BCS at c28a carries no native evidence beyond the executed PC path',
                  normalized_reference_paths=len(unique), compile_command=command, failure=None,
                  ROM_unchanged=True,
                  limits=['Controlled fixtures; frame re-entry is a declared PC-only change (A6/A7 previous real outputs), not a natural scheduler, IRQ or VBlank; parent 480ac and other objects are not run per frame.',
                          'c00468 (BIOS) is never executed; its output state is the actual C++ fade/card chain output plus declared host changes (PC=c37c, A7+=4, BYTE 10fdc6, 28ae/parent fields). Other BIOS effects unmodeled/unknown.',
                          'a29c is used as a stop here only (it is executed by the card menu verifier) and the a370 opening frame is executed by the card menu open verifier; the stops a406, 9e94, c2c8 and the callbacks beyond them are out of scope and never executed.',
                          'Declared RAM fixtures (28ae pool/parent fields, 7e/76/7a/7c/80 boundary writes) are inputs, not original-measured preparation.',
                          'Native has no SR reads; carry is checked against source opcode classification only. No general CCR/timing/IRQ or hardware proof.',
                          'Video/watchdog are instruction-unit ordered register ports; no bus-cycle or rendered VRAM/pixel claim. PVC effects independently fold original ordered writes.',
                          'Resumes forward previous actual C++ outputs plus declared host changes; native incoming is only an assertion.',
                          'Native observation artifacts are audited by hash/trace consistency, not re-executed here.',
                          'Checked failures preserve API outputs, not original CPU fault rollback; c28a direct-entry rejection is API-only (no native guard).'])
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=totals['cases'], split=totals['split'], control=totals['control'],
                         negatives=result['negative_count'], zero_step=len(zero),
                         carry=totals['carry_histogram'], sha256=digest(report_path))))


if __name__ == '__main__':
    main()
