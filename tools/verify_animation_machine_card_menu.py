"""Original card-menu push (a29c/a0a0/386e/38e8/c2a8/a2b8) native evidence vs the public machine API.

Controlled fixtures; no expected-register injection. The frozen native observation is an
immutable input (this verifier never invokes the observer main). C++ resumes only from the
previous actual C++ output plus the host changes and declared initial registers/bank state
recorded in the native fixture. The a29c start state is the actual C++ output of the reviewed
card-child chain (re-run here), not native registers. 38c8/38e2 (TRAP #f) are stop boundaries only: never executed.
a370 (opening frame), 9b58 and c2c0 are executed by the card menu open core and verified in
verify_animation_machine_card_menu_open.py; here they are normal stops. a63c (TRAP #f), e84d6 and the BIOS call c00468 are the still unexecuted
boundaries used for the unsupported-PC negatives.
"""
import json
from pathlib import Path
import shutil
import sys
import verify_animation_machine as common
import verify_animation_machine_callers as helpers
import verify_animation_machine_card_child as cc
from disassemble_program import load_verified_program

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/animation_machine_card_menu_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_card_menu_native'
NATIVE_SHA = 'da76f4643efafafdc8929a9cd73a24a1e3a434e49275e5babcadd53e5c45bfbc'
NATIVE_TOOL_SHA = 'adb3e9cb65175ebcb3c76347601755f951c033df673ada43533245b238951322'
CONTRACT_SHA = '0a4d095f741e151f509364118663c6470e527ea7535c1058e8d93161398a81ea'
A29C, A370, B9B58, T38C8, T38E2 = 0xa29c, 0xa370, 0x9b58, 0x38c8, 0x38e2
MARKER = cc.MARKER
BLOCK_STARTS = (0xa29c, 0xa0a0, 0xa0c2, 0xa0c4, 0xa0f8, 0xa104, 0xa158, 0xa15e, 0xa166, 0xa17e, 0xa184, 0xa18a,
                0xa18c, 0xa198, 0xa1a6, 0xa1ac, 0xa1ae, 0xa1ba, 0xa1be, 0xa1cc, 0xa1d0, 0x386e, 0x3878, 0x387a,
                0x38a4, 0x38a6, 0x38b6, 0x38be, 0x38ca, 0x38ce, 0x38e4, 0x38e8, 0x38ee, 0x38f4, 0x38fa, 0x38fe,
                0xc2a8, 0xa2b8, 0xa2bc, 0xc2b4, 0xc2ba)
BOUND_BRANCH_PCS = (0xa0be, 0xa0f4, 0xa154, 0xa16a, 0xa172, 0xa17a, 0xa186, 0xa1a2, 0xa1b6, 0xa1c8,
                    0x3874, 0x3880, 0x38c4, 0x38de, 0x38f0, 0x38fc)
A63C, E84D6, BIOS_C00468 = 0xa63c, 0xe84d6, 0xc00468
BOUNDARY_PCS = (T38C8, T38E2, A63C, E84D6, BIOS_C00468)       # no executor (a370/9b58/c2c0 open core, a406.. input core, 9e94/a2be/a662/c2c8 close core, bd26/9f36/a71a save core, a698.. nested core)
MENU_RANGES = ((0xa0a0, 0xa1e2), (0xa29c, 0xa2be), (0x386e, 0x3902), (0xc2a8, 0xc2c0))
CARRY_PRESERVING = (0xa0c2, 0xa158, 0xa17e, 0x3878, 0x38a4, 0xc2a8, 0xa2bc, 0xc2ba)
CARD_CHILD_CHAIN_STEP = 24      # 'child-frame-borrow-c290+after-c2a2' -> stop a29c
CARRY_PROBES = True          # the open-unit verifier re-runs this chain without the (already proven) carry probes
DECLARED_REG_KEYS = ('d0', 'd1', 'd3', 'd7', 'a0', 'a5', 'a7')
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNSUPPORTED_MENU = 'unsupported animation card menu PC'
ODD_JSR = 'animation fade card odd JSR target'
WRITE_DEVICE = 'unsupported animation machine write device'
EVEN = 'program bus requires even WORD/LONG address'


def sha(data):
    return cc.sha(data)


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


def audit_native(program, source):
    path = NATIVE_DIR / 'observation.json'
    assert cc.digest(path) == NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_card_menu.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'docs/analysis/animation-machine-card-menu-push-contract.md') == CONTRACT_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['sha256'] == CONTRACT_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase',
                'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['rom_stat_start'] == report['rom_stat_end']
    refs = helpers.audit_references(ROOT, NATIVE_DIR, report)
    refs[str(path.resolve())] = NATIVE_SHA
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    assert cc.digest(report['oracle']['library']) == report['oracle']['library_sha256']
    static = json.loads((NATIVE_DIR / 'source.json').read_text())
    assert static['source'] == source
    assert tuple(static['block_starts']) == BLOCK_STARTS == tuple(report['block_starts'])
    assert tuple(static['boundary_stop_pcs']) == (0xa370, 0x9b58, 0x38c8, 0x38e2) == tuple(report['boundary_stop_pcs'])
    assert sorted(MENU_RANGES) == sorted(tuple(r) for r in report['new_ranges'])
    instructions = {}
    for instruction in static['instructions']:
        at, size = instruction['rom_offset'], instruction['size']
        assert bytes(bytearray.fromhex(instruction['raw'])) == program[at:at + size]
        instructions[instruction['cpu_address']] = instruction
    assert A370 not in instructions and B9B58 not in instructions
    covered = set(report['covered_PCs'])
    assert set(BLOCK_STARTS) <= covered, [hex(p) for p in BLOCK_STARTS if p not in covered]
    # Bank-descriptor search: no banked descriptor exists in ROM; only banked strings are covered.
    for search in report['bank_descriptor_search']:
        assert search['terminating_descriptors_found'] == 0 and not search['candidates']
    rows = load_rows(report)
    assert len(rows) == report['cases'] + report['guarded_cases'] == 95
    split_count = sum(len(r['phases']) for r in rows)
    control_count = sum(len(r['continuous_control']) for r in rows)
    assert (split_count, control_count) == (report['total_split_phases'], report['total_control_phases'])
    assert report['fresh_CPU_runs'] == 478
    program_reads = dict(fixed_reads=0, bank_reads=0, PVC_writes=0)
    for row in rows:
        assert row['reproduced_twice'] and row['continuous_split_equivalent']
        assert bool(row['guarded']) == (row['group'] == 'guard' or row['label'].startswith('guard-'))
        fx = row['fixture']
        for kind in ('phases', 'continuous_control'):
            counts = cc.audit_program_reads(program, fx, row[kind])
            if kind == 'phases':
                for key, value in counts.items():
                    program_reads[key] += value
        cc.audit_split_control(row)
        for phase in row['phases'] + row['continuous_control']:
            assert phase['carry'] is None and not phase['branch_evidence']
            assert phase['counts']['external_reads'] == sum(e['region'] == 'external'
                                                          for e in phase['_trace']['events'])
            ports = [e for e in phase['_trace']['events'] if e['region'] in ('pvc', 'video', 'watchdog')]
            assert phase['_data']['ports.bin'] == b''.join(
                cc.struct.pack('>BII', e['size'], e['address'], int(e['bytes'], 16)) for e in ports)
            executed = set(phase['_trace']['pcs'][:-1])
            assert not (executed & {A370, B9B58, T38C8, T38E2}) and instructions.keys() >= executed
    return report, rows, refs, instructions, program_reads, control_count


def apply_changes(ram, state, changes, entry):
    """Declared host changes on top of previous actual C++ outputs only; each must match its record."""
    ram = bytearray(ram)
    state = dict(state)
    kinds = []
    for change in changes:
        kind = change['kind']
        assert change['pc_before'] == entry['pc'] and change['a7_before'] == entry['a7'], change
        if kind == 'ram':
            at, size = change['address'] & 65535, change['size']
            assert 0 <= at <= 65536 - size
            common.native.put(ram, change['address'], size, change['value'])
        elif kind == 'pc':
            state['pc'] = change['to']
        elif kind == 'a7_add':
            state['a7'] = (state['a7'] + change['delta']) & 0xffffffff
        else:
            raise AssertionError(kind)
        kinds.append(kind)
    return bytes(ram), state, kinds


def start_of_row(row, connected_start, bios_start):
    """C++ start state: previous actual C++ output (BIOS chain / a29c stop) plus declared initial registers/bank."""
    fx = row['fixture']
    native_pvc = row['phases'][0]['_data']['pvc_before.bin']
    assert sha(native_pvc) == fx['initial_PVC_sha256']
    native_masked = sha(cc.masked_pvc(native_pvc))
    if fx['entry_pc'] == cc.BIOS:
        key, (ram, src_state, pvc, bank) = bios_start
        state = dict({k: v for k, v in fx['initial_regs'].items() if k != 'a7'},
                     a7=fx['initial_a7'], pc=fx['entry_pc'], carry=0)
        origin = 'actual C++ output of the fade/card chain %s step %d (stop c00468)' % (key[0], key[1])
        assert sha(ram) == fx['initial_RAM_sha256'] and sha(cc.masked_pvc(pvc)) == native_masked
        assert bank == fx['bank_state'][0]
        assert {k: src_state[k] for k in cc.STATE_NO_CARRY} == {k: state[k] for k in cc.STATE_NO_CARRY}
        return ram, state, pvc, bank, origin, []
    assert fx['entry_pc'] == A29C
    ram, base_state, pvc, bank = connected_start
    assert sha(ram) == fx['initial_RAM_sha256']
    state = dict(base_state)
    declared = []
    for key in cc.STATE_NO_CARRY:
        want = fx['initial_a7'] if key == 'a7' else (fx['entry_pc'] if key == 'pc' else fx['initial_regs'][key])
        if state[key] != want:
            assert key in DECLARED_REG_KEYS, (row['label'], key)
            assert 'declared' in row['provenance'], row['label']
            state[key] = want
            declared.append(key)
    # declared bank state (modeled bank, ff8, ff9) is part of the fixture; device storage holds the masked words
    want_bank, ff8, ff9 = fx['bank_state']
    pvc = bytearray(pvc)
    declared_bank = (bank, pvc[0x1ff0:0x1ff4]) != (want_bank, ff8.to_bytes(2, 'big') + ff9.to_bytes(2, 'big'))
    pvc[0x1ff0:0x1ff2] = ff8.to_bytes(2, 'big')
    pvc[0x1ff2:0x1ff4] = ff9.to_bytes(2, 'big')
    pvc, bank = bytes(pvc), want_bank
    if declared_bank:
        assert row['label'] == 'bank-300000-same-address' and 'declared bank state' in row['provenance']
        declared.append('bank_state')
    assert sha(cc.masked_pvc(pvc)) == native_masked
    origin = 'actual C++ a29c stop output of the card child chain step %d plus declared %s' % (
        CARD_CHILD_CHAIN_STEP, ','.join(declared) or 'nothing')
    return ram, state, pvc, bank, origin, declared


def compare(exe, rows, resources, instructions, connected_start, bios_start):
    cpp_out = {}
    out_rows = []
    totals = dict(cases=0, split=0, control=0, resumes=0, ports=0, reads=0, carry_checks=0, carry_probes=0, carry_probe_preserved=0, declared_register_rows=0,
                  declared_host_changes=dict(ram=0, pc=0, a7_add=0))
    ends = {}
    starts = {}
    guards = []
    single_block = {}
    carry_histogram = {0: 0, 1: 0, 2: 0}
    for row in rows:
        fx = row['fixture']
        ram, state, pvc, bank, origin, declared = start_of_row(row, connected_start, bios_start)
        if declared:
            totals['declared_register_rows'] += 1
        expected_pvc, expected_bank = pvc, bank
        ends[(row['label'], -1)] = (ram, dict(state), pvc, bank)
        results = []
        step_starts = {}
        for j, phase in enumerate(row['phases']):
            data = phase['_data']
            entry = dict(pc=state['pc'], a7=state['a7'])
            if phase['guard'] is not None:
                assert j == len(row['phases']) - 1 and row['guarded']
                ram, state2, kinds = apply_changes(ram, state, phase['host_changes'], entry)
                assert ram == data['ram_before.bin']
                guards.append((row, phase, ram, state2, pvc, bank, phase['step']))
                break
            ram, state, kinds = apply_changes(ram, state, phase['host_changes'], entry)
            for kind in kinds:
                totals['declared_host_changes'][kind] += 1
            assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming'], (row['label'], j)
            assert ram == data['ram_before.bin'], (row['label'], j)
            assert (bank, ) == (phase['bank_before'], ) and kinds == [c['kind'] for c in phase['host_changes']]
            if phase['phase_in_step'] == 0:
                step_starts[phase['step']] = (ram, dict(state), pvc, bank, expected_pvc, expected_bank)
                starts[(row['label'], phase['step'])] = (ram, dict(state), pvc, bank)
            events = phase['_trace']['events']
            expected_pvc, expected_bank, portbytes = cc.fold_outputs(expected_pvc, expected_bank, events)
            assert expected_bank == phase['modeled_bank']
            assert portbytes == data['ports.bin']
            phase_in, phase_pvc, phase_bank = dict(state), pvc, bank
            actual = common.invoke(exe, OUT, 'c%03d_split_%03d' % (row['index'], j), ram, state,
                                   pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
            assert actual[0]['ok'] and not actual[4], (row['label'], j, phase['stop_pc'], actual[4])
            common.check_result(actual, dict(outgoing=phase['outgoing'], events=events,
                                             ram_after=data['ram_after.bin']),
                                expected_pvc, expected_bank, portbytes)
            assert actual[0]['status'] == 0
            result, ram, pvc, _, _ = actual
            executed = phase['_trace']['pcs'][:-1]
            want_carry = cc.classify_carry(instructions, state['carry'], executed)
            assert result['carry'] == want_carry, (row['label'], j, hex(phase['outgoing']['pc']),
                                                    result['carry'], want_carry)
            carry_histogram[result['carry']] += 1
            # Carry probes: the same phase with a known incoming C must yield exactly the source classification
            # and otherwise identical outputs (preserving blocks keep it, all other blocks make it Unknown).
            menu_only = CARRY_PROBES and bool(executed) and all(any(low <= pc < high for low, high in MENU_RANGES) for pc in executed)
            for probe in (1, 2) if menu_only else ():
                again = common.invoke(exe, OUT, 'c%03d_carry%d_%03d' % (row['index'], probe, j), data['ram_before.bin'],
                                      dict(phase_in, carry=probe), phase_pvc, phase_bank, resources,
                                      stop=phase['stop_pc'], external=fx['external'])
                assert again[0]['ok'] and not again[4]
                assert again[0]['carry'] == cc.classify_carry(instructions, probe, executed), (row['label'], j, probe)
                assert ({k: v for k, v in again[0].items() if k != 'carry'} ==
                        {k: v for k, v in result.items() if k != 'carry'})
                assert again[1] == ram and again[2] == pvc and again[3] == actual[3]
                totals['carry_probes'] += 1
                blocks = [pc for pc in executed if pc in BLOCK_STARTS]
                if len(blocks) == 1 and blocks[0] == executed[0]:
                    single_block[blocks[0]] = single_block.get(blocks[0], set()) | {again[0]['carry'] == probe}
                totals['carry_probe_preserved'] += again[0]['carry'] == probe
            totals['carry_checks'] += 1
            state = {k: result[k] for k in common.STATE_KEYS}
            bank = result['bank_base']
            totals['reads'] += result['external_reads']
            totals['ports'] += len(portbytes) // 9
            if j:
                totals['resumes'] += 1
            results.append(dict(step=phase['step'], label=phase['label'], stop_pc=phase['stop_pc'],
                                carry=cc.CARRY_NAME[result['carry']], actual_previous_outputs_used=bool(j),
                                full_RAM_16R_PC_PVC_bank_ports_status_reads_equal=True))
            ends[(row['label'], phase['step'])] = (ram, dict(state), pvc, bank)
            cpp_out[(row['index'], j)] = (ram, dict(state), pvc, bank)
        control_rows = 0
        for phase in row['continuous_control']:
            if phase['guard'] is not None:
                continue
            step = phase['step']
            c_ram, c_state, c_pvc, c_bank, e_pvc, e_bank = step_starts[step]
            data = phase['_data']
            assert {k: c_state[k] for k in common.REGS + ('pc',)} == phase['incoming']
            e_pvc, e_bank, portbytes = cc.fold_outputs(e_pvc, e_bank, phase['_trace']['events'])
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
                             declared_initial=declared, split_phases=len(results), control_steps=control_rows,
                             phases=results))
    # the connected fresh run must equal the long-lived chain tail in actual C++ (matched by native output identity)
    chain = next(r for r in rows if r['group'] == 'chain')
    by_identity = {}
    for j, phase in enumerate(chain['phases']):
        key = (sha(phase['_data']['ram_after.bin']), sha(phase['_data']['pvc_after.bin']),
               tuple(sorted(phase['outgoing'].items())))
        by_identity.setdefault(key, []).append(cpp_out[(chain['index'], j)])
    strip = lambda e: (e[0], {k: v for k, v in e[1].items() if k != 'carry'}, e[2][:0x1ff0] + e[2][0x1ff4:], e[3])
    connected = next(r for r in rows if r['group'] == 'connected')
    chain_matches = 0
    for j, phase in enumerate(connected['phases']):
        key = (sha(phase['_data']['ram_after.bin']), sha(phase['_data']['pvc_after.bin']),
               tuple(sorted(phase['outgoing'].items())))
        assert key in by_identity, ('connected phase not in chain', j)
        assert strip(cpp_out[(connected['index'], j)]) == strip(by_identity[key][0]), j
        chain_matches += 1
    assert chain_matches == len(connected['phases'])
    totals['connected_vs_chain_C++_phases_equal'] = chain_matches
    # Contract list of carry-preserving blocks vs the observed single-block phases with a known incoming C.
    for pc, outcomes in single_block.items():
        assert outcomes == {pc in CARRY_PRESERVING}, (hex(pc), outcomes)
    totals['single_block_carry_starts_checked'] = sorted(hex(pc) for pc in single_block)
    totals['carry_preserving_starts_observed'] = sorted(hex(pc) for pc in single_block if pc in CARRY_PRESERVING)
    totals['carry_histogram'] = {cc.CARRY_NAME[k]: v for k, v in carry_histogram.items()}
    return out_rows, totals, ends, starts, guards


def compare_guards(exe, guards, resources, guard_errors):
    rows, superseded = [], []
    for row, phase, ram, state, pvc, bank, step in guards:
        stop = phase['stop_pc']
        result, outgoing, out_pvc, ports, error = common.invoke(
            exe, OUT, 'guard_%s' % row['label'], ram, dict(state, carry=2), pvc, bank, resources,
            stop=stop, external=row['fixture']['external'])
        if row['label'] in SUPERSEDED_GUARDS:
            # The frozen native guard stopped where the menu push had no executor; the card menu open core now
            # runs 9b58 / a370 / c2c0, so the same input is a checked positive stop (not counted as a negative).
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


def menu_interior_pcs(instructions):
    # a100 (BSR 9e1a, nested push return) is a block of the card menu core now: superseded, no longer an interior negative.
    skip = set(BLOCK_STARTS) | set(BOUND_BRANCH_PCS) | set(BOUNDARY_PCS) | {0xa100}
    pcs = []
    for pc in sorted(instructions):
        if any(low <= pc < high for low, high in MENU_RANGES) and pc not in skip:
            pcs.append(pc)
    return pcs


U03_PREFIX_RECORDS = []


def glyph_entry_prefix(exe, folder, base, resources):
    """Pin the original first U03 block from the actual legacy chain state."""
    program, _source = load_verified_program(ROOT)
    assert program[0xe84d6:0xe84e4].hex() == '48e77f7e1e100c0700de6600004e'
    ram, state, pvc, bank = base
    address = state['a0'] & 0xffffff
    assert address < 0x100000 or 0x100000 <= address < 0x200000
    byte = program[address] if address < 0x100000 else ram[address & 0xffff]
    stop = 0xe84e4 if byte == 0xde else 0xe8530
    incoming = dict(state, pc=0xe84d6, carry=2)
    expected = dict(incoming, pc=stop, a7=(state['a7'] - 52) & 0xffffffff,
                    d7=(state['d7'] & 0xffffff00) | byte, carry=0)
    want_ram = bytearray(ram)
    for index, register in enumerate(['d%d' % i for i in range(1, 8)] + ['a%d' % i for i in range(1, 7)]):
        common.native.put(want_ram, expected['a7'] + index * 4, 4, state[register])
    result, outgoing, out_pvc, ports, error = common.invoke(
        exe, folder, 'superseded_u03_e84d6_prefix', ram, incoming, pvc, bank, resources, stop=stop)
    assert result['ok'] and not error and result['status'] == 0
    assert {key: result[key] for key in common.STATE_KEYS} == expected
    assert outgoing == bytes(want_ram) and out_pvc == pvc and result['bank_base'] == bank
    assert not ports and result['external_reads'] == 0
    return dict(label='boundary_direct_entry_0e84d6_prefix',
                former_expected_API_error='unsupported animation machine PC', original_cpu_pc='0xe84d6',
                original_file_offset='0xe84d6', original_block_raw=program[0xe84d6:0xe84e4].hex(),
                executed_prefix_stop=hex(stop), full_prefix_state_checked=True,
                native_exception_rollback_equivalence_claimed=False)


def negatives(exe, starts, instructions, resources, neg_errors):
    out = []
    base = starts[('connected-a29c-to-a370', 0)]
    U03_PREFIX_RECORDS.append(glyph_entry_prefix(exe, OUT, base, resources))

    def reject(label, start, changes=None, stop=0xff000, external=0):
        r, s, p, b = start
        s = dict(s, carry=2)
        s.update(changes or {})
        result, outgoing, out_pvc, ports, error = common.invoke(
            exe, OUT, 'negative_' + label, r, s, p, b, resources, stop=stop, external=external)
        assert not result['ok'], label
        assert error.strip() == neg_errors[label], (label, error.strip())
        assert {k: result[k] for k in common.STATE_KEYS} == s
        assert outgoing == r and out_pvc == p and ports == MARKER and result['bank_base'] == b
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        out.append(dict(label=label, error=error.strip(), all_API_outputs_preserved=True,
                        native_exception_rollback_equivalence_claimed=False))

    for pc in BOUND_BRANCH_PCS:
        reject('bound_branch_direct_entry_%06x' % pc, base, {'pc': pc})
    interior = menu_interior_pcs(instructions)
    for pc in interior:
        reject('interior_direct_entry_%06x' % pc, base, {'pc': pc})
    for pc in BOUNDARY_PCS:
        reject('boundary_direct_entry_%06x' % pc, base, {'pc': pc})
    for pc in (0xa1e2, 0x3902, 0xa09e):      # a2be is executed by the close core now (superseded)
        reject('outside_range_entry_%06x' % pc, base, {'pc': pc})
    # a370 executes now (open core): with a stop that is never reached the opening frame returns to the dispatcher,
    # which continues into the odd JSR target of the next object; the whole transaction rolls back.
    reject('a370_runs_then_dispatcher_continues_with_stop_ff000', base)
    reject('a370_runs_then_dispatcher_continues_with_stop_38c8', base, stop=T38C8)
    reject('a370_runs_then_dispatcher_continues_with_stop_38e2', base, stop=T38E2)
    reject('38c8_reached_with_stop_ff000', starts[('trap-38c8-d3-74ff-item', 0)])
    reject('38c8_reached_with_stop_a370', starts[('trap-38c8-d3-74ff-item', 0)], stop=A370)
    reject('38c8_reached_with_stop_38e2', starts[('trap-38c8-d3-74ff-item', 0)], stop=T38E2)
    reject('38e2_reached_with_stop_ff000', starts[('trap-38e2-l-7500', 0)])
    reject('38e2_reached_with_stop_38c8', starts[('trap-38e2-l-7500', 0)], stop=T38C8)
    reject('38e2_reached_with_stop_a370', starts[('trap-38e2-l-7500', 0)], stop=A370)
    # Positive controls: the same inputs succeed when the matching boundary is the stop.
    for label, stop in (('connected-a29c-to-a370', A370), ('connected-a29c-to-a370', 0xc2c0),
                        ('connected-a29c-to-a370', B9B58), ('direct-a0a0-nested-9b58', B9B58),
                        ('direct-a0a0-overflow-a370', A370),
                        ('trap-38c8-d3-74ff-item', T38C8), ('trap-38e2-l-7500', T38E2)):
        r, s, p, b = starts[(label, 0)]
        result, _, _, _, error = common.invoke(exe, OUT, 'control_%s_%06x' % (label, stop), r, dict(s, carry=2), p, b, resources, stop=stop)
        assert result['ok'] and not error and result['pc'] == stop and result['status'] == 0, (label, hex(stop))
    return out, len(interior)


def zero_step(exe, connected_start, resources):
    ram, state, pvc, bank = connected_start
    rows = []
    for pc in BLOCK_STARTS:
        for carry in (0, 1, 2):
            s = dict(state, pc=pc, carry=carry)
            result, out_ram, out_pvc, ports, error = common.invoke(
                exe, OUT, 'zero_%06x_%d' % (pc, carry), ram, s, pvc, bank, resources, stop=pc)
            assert result['ok'] and not error and result['status'] == 0, (hex(pc), carry, error)
            assert {k: result[k] for k in common.STATE_KEYS} == s
            assert out_ram == ram and out_pvc == pvc and result['bank_base'] == bank
            assert result['external_reads'] == 0 and not ports
            rows.append(dict(pc=pc, carry=carry, all_input_state_preserved=True))
    return rows


def boundary_zero_step(exe, connected_start, resources, expected):
    """stop == entry PC at the boundaries: recorded as observed behavior (not required by the contract)."""
    ram, state, pvc, bank = connected_start
    rows = []
    for pc in BOUNDARY_PCS:
        s = dict(state, pc=pc, carry=2)
        result, out_ram, out_pvc, ports, error = common.invoke(exe, OUT, 'zero_boundary_%06x' % pc, ram, s,
                                                               pvc, bank, resources, stop=pc)
        assert result['ok'] == expected[pc], (hex(pc), error)
        assert {k: result[k] for k in common.STATE_KEYS} == s and out_ram == ram and out_pvc == pvc
        rows.append(dict(pc=pc, ok=result['ok'], error=error.strip()))
    return rows


GUARD_ERRORS = {
    'guard-A5-in-ROM': WRITE_DEVICE,
    'guard-A5-in-bank': WRITE_DEVICE,
    'guard-odd-descriptor-A0': EVEN,
    'guard-odd-A7': EVEN,
    'guard-odd-A2-record': 'invalid animation machine write size/alignment',
    'guard-overflow-rts-unsupported-target': UNSUPPORTED_MACHINE,
    'guard-trap-reached-without-stop': UNSUPPORTED_MACHINE,
    # a370 executes now: the frame returns to the dispatcher, which meets the odd JSR target (was: unsupported a370)
    'guard-stop-38c8-never-reached': ODD_JSR}
SUPERSEDED_GUARDS = {
    'guard-stop-9b58-never-reached': (B9B58, '9b58 is executed by the card menu open core, so stop 9b58 is reached'),
    'guard-run-past-a370': (0xc2c0, 'a370 is executed by the card menu open core; the frame reaches the c2c0 stop')}


class Errors(dict):
    """Exact pinned error strings; unknown labels fall back to the class expected for the label prefix."""
    def __missing__(self, label):
        if label == 'boundary_direct_entry_0e84d6':
            return ODD_JSR  # U03 executes the glyph entry; this fixture then reaches an odd dispatcher callback.

        if label == 'interior_direct_entry_003900':
            # RTS of block 38fe: the router range ends at 38fe, so the outer router (not the menu core) rejects it.
            return UNSUPPORTED_MACHINE
        for prefix, error in (('bound_branch_direct_entry_', UNSUPPORTED_MENU),
                              ('interior_direct_entry_', UNSUPPORTED_MENU),
                              ('boundary_direct_entry_', UNSUPPORTED_MACHINE),
                              ('outside_range_entry_', UNSUPPORTED_MACHINE),
                              ('a370_runs_then_dispatcher_continues_', ODD_JSR),
                              ('38c8_', UNSUPPORTED_MACHINE), ('38e2_', UNSUPPORTED_MACHINE)):
            if label.startswith(prefix):
                return error
        raise KeyError(label)


NEG_ERRORS = Errors()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    report_path.unlink(missing_ok=True)
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_card_menu.py', 'tools/verify_animation_machine_card_child.py',
                 'tools/observe_animation_machine_card_menu.py', 'tools/observe_animation_machine_card_child.py',
                 'docs/analysis/animation-machine-card-menu-push-contract.md',
                 'engine/src/animation_machine_card_menu.cpp', 'engine/src/animation_machine_card_child.cpp',
                 'engine/tests/animation_machine_card_menu_test.cpp'):
        inputs[name] = cc.digest(ROOT / name)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = cc.digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = cc.digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    exe, command = helpers.compile_harness(ROOT, OUT)
    # Reviewed card-child chain re-run in actual C++: gives the BIOS stop output and the a29c stop output.
    cc.OUT = OUT / 'card_child_chain'
    cc.OUT.mkdir(parents=True, exist_ok=True)
    bios_start = cc.fade_chain_bios_output(exe, program, source, resources)
    cc_report, cc_rows, cc_refs, cc_instructions, _reads, _control = cc.audit_native(program, source)
    _m, _t, cc_ends, _g = cc.compare(exe, cc_rows, resources, cc_instructions, bios_start)
    cc_chain = next(r for r in cc_rows if r['group'] == 'chain')
    connected_start = cc_ends[(cc_chain['label'], CARD_CHILD_CHAIN_STEP)]
    assert connected_start[1]['pc'] == A29C
    report, rows, native_refs, instructions, program_reads, control_count = audit_native(program, source)
    refs.update(cc_refs)
    refs.update(native_refs)
    assert sha(connected_start[0]) == report['card_child_crosscheck']['ram_after_sha256']
    # PVC: raw native 1ff0..1ff3 vs masked device storage is excluded; the other bytes are compared in start_of_row.
    matches, totals, ends, starts, guards = compare(exe, rows, resources, instructions, connected_start, bios_start)
    guarded, superseded = compare_guards(exe, guards, resources, GUARD_ERRORS)
    negative, interior_count = negatives(exe, starts, instructions, resources, NEG_ERRORS)
    zero = zero_step(exe, connected_start, resources)
    boundary_zero = boundary_zero_step(exe, connected_start, resources, {pc: True for pc in BOUNDARY_PCS})
    for name, expected in list(inputs.items()) + list(refs.items()):
        assert cc.digest(ROOT / name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    refs.update({str(path.resolve()): cc.digest(path) for path in OUT.rglob('*')
                 if path.is_file() and path != report_path})
    unique = {}
    for name, expected in list(inputs.items()) + list(refs.items()):
        key = str((ROOT / name).resolve())
        assert key not in unique or unique[key] == expected
        unique[key] = expected
    result = dict(schema_version=1, source=source, inputs=inputs, artifacts=refs,
                  native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA,
                  contract_sha256=CONTRACT_SHA,
                  actual_CPP=dict(totals, matches=matches),
                  original_program_read_audit=program_reads,
                  native_guards_checked_API=guarded, native_guards_superseded_by_card_menu_open_core=superseded,
                  negatives_superseded_by_later_card_menu_cores=dict(u03_entry_prefix=U03_PREFIX_RECORDS, interior_direct_entry_a100='block of the card menu core (BSR 9e1a) now', outside_range_entry_a2be='executed by the close core', boundary_direct_entry_e84d6='executed by U03; this fixture later reaches an odd dispatcher callback (exact error and full rollback checked)', boundary_direct_entry_a662_9e94_c2c8_a406='executed by the input/close cores'),
                  native_continuous_control_phases_replayed=control_count,
                  negatives=negative, negative_count=len(negative) + len(guarded),
                  interior_PCs_rejected=interior_count, zero_step=zero, boundary_zero_step=boundary_zero,
                  card_child_a29c_start=dict(chain_label=cc_chain['label'], step=CARD_CHILD_CHAIN_STEP,
                                             ram_sha256=sha(connected_start[0]), pc=connected_start[1]['pc']),
                  bios_start=dict(chain_label=bios_start[0][0], step=bios_start[0][1],
                                  ram_sha256=sha(bios_start[1][0])),
                  carry_check='C++ carry equals source-opcode walk over native-executed PCs (ORI/ANDI CCR known, flow-only preserved, else Unknown); native SR never read',
                  normalized_reference_paths=len(unique), compile_command=command, failure=None,
                  ROM_unchanged=True,
                  limits=['Controlled fixtures; frame re-entry is a declared PC-only change, not a natural scheduler, IRQ or VBlank.',
                          'No banked descriptor exists in ROM (bank_descriptor_search of both 2/3 banks: 0 terminating descriptors); only banked strings (title/item pointers read through the current bank) are covered.',
                          'Carry is a source-opcode classification (native SR is never read), not a native C measurement; ADDA/SUBA are conservatively Unknown.',
                          '38c8/38e2 (TRAP #f) are stop boundaries only, never executed; a370 (opening frame), 9b58 and c2c0 execute in the card menu open core (verify_animation_machine_card_menu_open.py) and are only normal stops here; a406..a5d0 (input), 9e94/a2be/a662/c2c8 (close), bd26/9f36/a71a (save) and a698.. (nested) are executed by later card menu cores; a63c and c00468 have no executor; e84d6 executes in U03, while the frozen native prefix retains its original stop.',
                          'Declared initial registers (A0/A5/A7/D0/D1/D3/D7), declared bank state and declared RAM fixtures are inputs, not original-measured preparation; the rest starts from the actual C++ card-child output.',
                          'Native observation artifacts are audited by hash/trace consistency, not re-executed here.',
                          'Checked failures preserve API outputs, not original CPU fault rollback; bundled-branch/interior direct entries have no native guard (API-only rejection).'])
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=totals['cases'], split=totals['split'], control=totals['control'],
                         resumes=totals['resumes'], negatives=result['negative_count'], interior=interior_count,
                         zero_step=len(zero), carry=totals['carry_histogram'],
                         sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
