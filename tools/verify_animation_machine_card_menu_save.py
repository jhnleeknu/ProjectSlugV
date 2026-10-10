"""Original card-menu YES save (bd26 + BIOS boundaries, bbb8/bb74/be0c/9f36/a71a, nested push a100, c1ea) native
evidence vs the public machine API.

Controlled fixtures; no expected-register injection. The frozen native observation is an immutable input (this
verifier never invokes the observer main). The chain start is the actual C++ output of the re-run prefix (fade/card
BIOS chain -> open-native chain steps 0..30 = card child, push, opening frames), the native save rows 31.. then resume only
from the previous actual C++ output plus the declared host changes recorded in the native fixture (asserted against the
record). Fresh rows start from the actual C++ output of the save chain step named in their fixture plus their declared
preparation. BIOS c00468 (bd5a, bd8a) and c0046e (be16) are stop boundaries only: never executed.
"""
import json
from pathlib import Path
import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import verify_animation_machine as common
import verify_animation_machine_callers as helpers
import verify_animation_machine_card_child as cc
import verify_animation_machine_card_menu as cm
from disassemble_program import load_verified_program

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/animation_machine_card_menu_save_execution'
WORK = OUT / 'work'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_card_menu_save_native'
OPEN_DIR = ROOT / 'artifacts/animation_machine_card_menu_open_native'
NATIVE_SHA = 'b0f9e26195f9a31181a6164f4ee15b93497515a7782dccc7f5a0e74ada142c0c'
NATIVE_TOOL_SHA = 'eaf7d1a91e1f1f082ddcca0acce417076e3dcf78686738f0de1723391131934c'
CONTRACT_SHA = 'd8d67ebb51671e4603cc8632268dedfb4e94bd0cb89fbd71354231f269b72a79'
OPEN_NATIVE_SHA = '154b4ed588a1bf7c9615bc7c6c3710492e4c0a711aca710b20f6bd21a7390ab4'
OPEN_TOOL_SHA = '17dea0a98c5a8ca3aa34ccf7524d132872877774ffcfd39970037fa0f7d04316'
OPEN_CHAIN_LABEL = 'chain-full-bios-resume-to-open'
SAVE_CHAIN_LABEL = 'chain-full-bios-resume-to-save'
MARKER = cc.MARKER
BIOS_A, BIOS_B = 0xc00468, 0xc0046e
BIOS_PCS = (BIOS_A, BIOS_B)
SAVE_BLOCK_TEXT = ('9f36 9f48 9f4e 9f50 a100 a71a a720 a72a bb74 bb76 bb82 bb84 bb8c bbb8 bbba bbc0 bbc4 bbca bbd0 '
                   'bd26 bd34 bd3c bd60 bd90 be0c be1c be2e be34 c1ea')
SAVE_BLOCKS = tuple(int(x, 16) for x in SAVE_BLOCK_TEXT.split())
SAVE_SET = frozenset(SAVE_BLOCKS)
assert len(SAVE_BLOCKS) == len(SAVE_SET) == 29
SAVE_RANGES = ((0x9f36, 0x9f78), (0xa71a, 0xa72c), (0xbb74, 0xbb8e), (0xbbb8, 0xbbd4), (0xbd26, 0xbd96), (0xbe0c, 0xbe3a))
# Router (animation_machine.cpp, inclusive upper bounds) of the save core; everything else is the machine router.
ROUTER_SAVE = ((0x9f36, 0x9f76), (0xa71a, 0xa72a), (0xbb74, 0xbb8c), (0xbbb8, 0xbbd2), (0xbd26, 0xbd92), (0xbe0c, 0xbe38))
CPP_PRESERVING = (0xa100, 0xa71a, 0xa72a, 0xbb8c, 0xbbd0, 0xbd90, 0xc1ea)     # contract / carry_preserving_pc comment
BIOS_SITES = {0xbd5a: (BIOS_A, 0xbd60), 0xbd8a: (BIOS_A, 0xbd90), 0xbe16: (BIOS_B, 0xbe1c)}
JSR_BYTES = {BIOS_A: '4eb900c00468', BIOS_B: '4eb900c0046e'}
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNSUPPORTED_SAVE = 'unsupported animation card menu save PC'
NEEDS_CARRY = 'card menu caller requires known carry'
EVEN = 'program bus requires even WORD/LONG address'
WRITE_ALIGN = 'invalid animation machine write size/alignment'
FLOW_ONLY = cc.FLOW_ONLY
CARRY_USERS = ('bcc', 'bcs', 'bhi', 'bls')
END_MNEMONICS = ('bra', 'jmp', 'rts', 'bsr', 'jsr', 'beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls',
                 'bge', 'blt', 'bgt', 'ble', 'dbra', 'dbf')
COND_BRANCH = ('beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble')
SOURCE_DIRS = ('animation_machine_fade_card_native', 'animation_machine_card_child_native', 'animation_machine_card_menu_native',
               'animation_machine_card_menu_open_native', 'animation_machine_card_menu_input_native',
               'animation_machine_card_menu_close_native', 'animation_machine_card_menu_save_native')
# Native guards whose native problem is fully reproduced by a checked C++ error (pinned from the guard's problem class).
GUARD_ERRORS = {
    'guard-nested-overflow-top-107e1c': UNSUPPORTED_MACHINE,    # a0c2 RTS pops 107e1c (RAM) as the return PC
    'guard-nested-overflow-top-107e0e': UNSUPPORTED_MACHINE,
    'guard-select-stop-2ac2': UNSUPPORTED_MACHINE,              # JSR c00468 reached with another stop
    'guard-select-stop-c0046e': UNSUPPORTED_MACHINE,
    'guard-resume1-stop-2ac2': UNSUPPORTED_MACHINE,
    'guard-resume1-stop-c0046e': UNSUPPORTED_MACHINE,
    'guard-resume2-stop-2ac2': UNSUPPORTED_MACHINE,
    'guard-resume2-stop-c00468': UNSUPPORTED_MACHINE,
    'guard-odd-ee-9f36': EVEN,                                  # LONG read at an odd address
    'guard-odd-descriptor-9f36': EVEN,                          # WORD read at an odd address
    'guard-odd-A5-direct-bd26': WRITE_ALIGN,                    # MOVE.W D0,-ce(A5) at odd 107f33
    'guard-odd-A7-direct-bd26': EVEN}                           # JSR/BSR push LONG at odd A7
# The native fetch of 9e94 is unmapped in the save observer (it has no close-unit ranges); the C++ machine now has the
# close executor for 9e94, so the native guard cannot be reproduced as an error: it is recorded, not claimed.
SUPERSEDED_GUARDS = ('guard-desc-flags-0001-9e94',)


def sha(data):
    return cc.sha(data)


def load_row_files(native_dir, row):
    """Payload files of one native row (hash checked against the report); released again by release_row."""
    for kind in ('phases', 'continuous_control'):
        for phase in row[kind]:
            data = {}
            for name, expected in phase['artifacts'].items():
                value = (native_dir / name).read_bytes()
                assert sha(value) == expected, name
                data[name.rsplit('phase_%03d_' % phase['index'], 1)[1]] = value
            phase['_data'] = data
            phase['_trace'] = json.loads(data['trace.json'])
            for snapshot in phase['snapshots']:
                snapshot['_ram'] = (native_dir / snapshot['artifacts']['ram']).read_bytes()
                snapshot['_pvc'] = (native_dir / snapshot['artifacts']['pvc']).read_bytes()
                assert sha(snapshot['_ram']) == phase['artifacts'][snapshot['artifacts']['ram']]
                assert sha(snapshot['_pvc']) == phase['artifacts'][snapshot['artifacts']['pvc']]


def release_row(row):
    for kind in ('phases', 'continuous_control'):
        for phase in row[kind]:
            for key in ('_data', '_trace'):
                phase.pop(key, None)
            for snapshot in phase['snapshots']:
                snapshot.pop('_ram', None)
                snapshot.pop('_pvc', None)


def mnemonic(instructions, pc):
    return instructions[pc]['mnemonic'].split('.')[0]


def load_instruction_union(program):
    """Source-opcode records of every unit's static decode (bytes checked against the ROM)."""
    union = {}
    for name in SOURCE_DIRS:
        static = json.loads((ROOT / 'artifacts' / name / 'source.json').read_text())
        for item in static['instructions']:
            at, size = item['rom_offset'], item['size']
            assert bytes(bytearray.fromhex(item['raw'])) == program[at:at + size], (name, hex(item['cpu_address']))
            old = union.get(item['cpu_address'])
            assert old is None or (old['raw'], old['mnemonic'], old['op_str']) == (item['raw'], item['mnemonic'], item['op_str'])
            union[item['cpu_address']] = item
    return union


def block_walk(instructions, start, block_set):
    pc, out = start, []
    while True:
        item = instructions[pc]
        out.append(pc)
        if mnemonic(instructions, pc) in END_MNEMONICS or pc + item['size'] in block_set:
            return out
        pc += item['size']


def consumes_incoming(instructions, executed):
    """True when a C-reading branch executes before any instruction in the phase has written/classified C."""
    modified = False
    for pc in executed:
        name = mnemonic(instructions, pc)
        if name in CARRY_USERS and not modified:
            return True
        if name not in FLOW_ONLY:
            modified = True
    return False


def audit_save_native(program, source, union):
    path = NATIVE_DIR / 'observation.json'
    assert cc.digest(path) == NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_card_menu_save.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'docs/analysis/animation-machine-card-menu-save-contract.md') == CONTRACT_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['sha256'] == CONTRACT_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase',
                'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['contract_discrepancies'] == [] and report['model_checks_all_equal'] is True
    assert report['rom_stat_start'] == report['rom_stat_end']
    refs = helpers.audit_references(ROOT, NATIVE_DIR, report)
    refs[str(path.resolve())] = NATIVE_SHA
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    assert cc.digest(report['oracle']['library']) == report['oracle']['library_sha256']
    static = json.loads((NATIVE_DIR / 'source.json').read_text())
    assert static['source'] == source
    assert tuple(report['save_block_starts']) == SAVE_BLOCKS
    assert tuple(sorted(tuple(r) for r in report['new_ranges'])) == tuple(sorted(SAVE_RANGES))
    assert tuple(sorted(tuple(r) for r in static['save_ranges'])) == tuple(sorted(SAVE_RANGES))
    assert set(report['block_starts']) == set(report['existing_block_starts']) | SAVE_SET
    assert tuple(report['boundary_stop_pcs']) == tuple(static['boundary_stop_pcs']) == BIOS_PCS
    assert static['boundary_stop_sites'] == {'0xc00468': {'0xbd5a': '0xbd60', '0xbd8a': '0xbd90', '0xc376': '0xc37c'},
                                             '0xc0046e': {'0xbe16': '0xbe1c'}}
    for item in static['instructions']:
        at, size = item['rom_offset'], item['size']
        assert bytes(bytearray.fromhex(item['raw'])) == program[at:at + size]
    covered = set(report['covered_PCs'])
    assert SAVE_SET <= covered, [hex(p) for p in SAVE_BLOCKS if p not in covered]
    assert BIOS_PCS[0] in covered and BIOS_PCS[1] in covered       # recorded as stop PCs, never executed (checked per phase)
    assert covered - set(BIOS_PCS) <= set(union), [hex(p) for p in sorted(covered - set(union))][:10]
    # contract byte rows: the ROM bytes at the decoded ranges
    for row in report['contract_byte_rows']:
        assert row['contract_bytes'] == row['rom_bytes'], row['range']
    assert (report['cases'], report['guarded_cases']) == (66, 13)
    rows = report['results'] + report['guarded_results']
    assert len(rows) == 79 == len(report['condition_table'])
    # The save chain row stores only steps 31..36; its steps 0..30 (445 split / 31 control phases) are the open-native chain.
    stored = (sum(len(r['phases']) for r in rows), sum(len(r['continuous_control']) for r in rows))
    assert stored == (4051, 129)
    assert (stored[0] + 445, stored[1] + 31) == (report['total_split_phases'], report['total_control_phases']) == (4496, 160)
    assert rows[0]['stored_from_step'] == 31
    assert report['fresh_CPU_runs'] == 398 and report['chain_vs_fresh_phases_compared'] == 823
    assert report['partial_chain_comparison'] == {'connected-input-f1-to-no-save': 165}
    return report, rows, refs, static, covered


def audit_open_prefix(program, source):
    """Open-native chain (steps 0..30) is the prefix; its recorded identity is cross-checked by the save observation."""
    path = OPEN_DIR / 'observation.json'
    assert cc.digest(path) == OPEN_NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_card_menu_open.py') == OPEN_TOOL_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None and report['tool_sha256'] == OPEN_TOOL_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase',
                'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    refs = helpers.audit_references(ROOT, OPEN_DIR, report)
    refs[str(path.resolve())] = OPEN_NATIVE_SHA
    chain = next(r for r in report['results'] if r['label'] == OPEN_CHAIN_LABEL)
    assert chain['group'] == 'chain' and sorted({p['step'] for p in chain['phases']}) == list(range(31))
    return report, chain, refs


def replay_prefix(exe, chain, bios_start, resources):
    """Actual C++ re-run of the open-native chain steps 0..30 (split phases, previous actual outputs only)."""
    load_row_files(OPEN_DIR, chain)
    fx = chain['fixture']
    ram, state, pvc, bank, origin, _ = cm.start_of_row(chain, None, bios_start)
    expected_pvc, expected_bank = pvc, bank
    ends, count, ports = {}, 0, 0
    for j, phase in enumerate(chain['phases']):
        data = phase['_data']
        entry = dict(pc=state['pc'], a7=state['a7'])
        assert phase['guard'] is None
        ram, state, kinds = cm.apply_changes(ram, state, phase['host_changes'], entry)
        assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming'], j
        assert ram == data['ram_before.bin'] and bank == phase['bank_before'], j
        events = phase['_trace']['events']
        expected_pvc, expected_bank, portbytes = cc.fold_outputs(expected_pvc, expected_bank, events)
        assert expected_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
        actual = common.invoke(exe, WORK, 'prefix', ram, state, pvc, bank, resources,
                               stop=phase['stop_pc'], external=fx['external'])
        assert actual[0]['ok'] and not actual[4], ('prefix', j, hex(phase['stop_pc']), actual[4])
        common.check_result(actual, dict(outgoing=phase['outgoing'], events=events, ram_after=data['ram_after.bin']),
                            expected_pvc, expected_bank, portbytes)
        assert actual[0]['status'] == 0
        result, ram, pvc, _, _ = actual
        state = {k: result[k] for k in common.STATE_KEYS}
        bank = result['bank_base']
        ends[phase['step']] = (ram, dict(state), pvc, bank)
        count += 1
        ports += len(portbytes) // 9
    release_row(chain)
    return ends, dict(origin=origin, phases=count, ports=ports)


def parse_source_step(row):
    found = re.search(r'\(step (\d+)[,)]', row['provenance'])
    assert found, row['label']
    return int(found.group(1))


def fresh_start(row, chain_ends):
    """Fresh row: actual C++ output of the save chain step named in the fixture + its declared preparation."""
    fx = row['fixture']
    native_pvc = row['phases'][0]['_data']['pvc_before.bin']
    assert sha(native_pvc) == fx['initial_PVC_sha256']
    step = parse_source_step(row)
    ram, base, pvc, bank = chain_ends[step]
    assert sha(ram) == fx['initial_RAM_sha256'], (row['label'], step)
    state = dict(base)
    declared = []
    for key in cc.STATE_NO_CARRY:
        want = fx['initial_a7'] if key == 'a7' else (fx['entry_pc'] if key == 'pc' else fx['initial_regs'][key])
        if state[key] != want:
            assert 'declared' in row['provenance'] and key != 'pc', (row['label'], key, hex(want))
            state[key] = want
            declared.append(key)
    want_bank, ff8, ff9 = fx['bank_state']
    pvc = bytearray(pvc)
    assert (bank, bytes(pvc[0x1ff0:0x1ff4])) == (want_bank, ff8.to_bytes(2, 'big') + ff9.to_bytes(2, 'big')), row['label']
    assert sha(cc.masked_pvc(bytes(pvc))) == sha(cc.masked_pvc(native_pvc))
    origin = 'actual C++ output of the save chain step %d plus declared %s' % (step, ','.join(declared) or 'nothing')
    return ram, state, bytes(pvc), bank, origin, declared


def row_identity(phase):
    return (sha(phase['_data']['ram_after.bin']), sha(phase['_data']['pvc_after.bin']),
            tuple(sorted(phase['outgoing'].items())))


def strip_carry(entry):
    return (entry[0], {k: v for k, v in entry[1].items() if k != 'carry'}, entry[2][:0x1ff0] + entry[2][0x1ff4:], entry[3])


def read_long(ram, address):
    return cc.rd(ram, address, 4)


def check_bios_resume(phase, entry_ram, entry_state):
    """Declared BIOS return: PC = the return LONG on the stack, A7 += 4, optional BYTE 10fdc6."""
    changes = phase['host_changes']
    assert entry_state['pc'] in BIOS_PCS and changes
    assert changes[0]['kind'] == 'pc' and changes[0]['to'] == read_long(entry_ram, entry_state['a7']), changes[0]
    assert changes[1]['kind'] == 'a7_add' and changes[1]['delta'] == 4
    for change in changes[2:]:
        assert change['kind'] == 'ram' and change['why'].startswith('declared'), change
        assert change['size'] in (1, 2, 4) and (change['address'] != 0x10fdc6 or change['size'] == 1)
    assert changes[0]['to'] in (0xbd60, 0xbd90, 0xbe1c)
    return changes[0]['to']


def check_bios_stop(phase, ram, state):
    """A BIOS stop is accepted only directly after the JSR at bd5a/bd8a/be16 with the return LONG and saved A6 on the stack."""
    evidence = phase['stop_evidence']
    pc = state['pc']
    assert pc in BIOS_PCS and phase['stop_pc'] == pc and evidence['is_step_stop'] is True
    site = evidence['previous_pc']
    assert site in BIOS_SITES and BIOS_SITES[site][0] == pc and evidence['previous_bytes'] == JSR_BYTES[pc], hex(site)
    assert read_long(ram, state['a7']) == BIOS_SITES[site][1]
    assert read_long(ram, state['a7'] + 4) == state['a6']
    return site


def run_row(exe, row, start, ctx, work, totals):
    """Split phases (previous actual C++ outputs + declared host changes), carry classification/probes, control replay."""
    fx = row['fixture']
    ram, state, pvc, bank, origin, declared = start
    instr = ctx['instr']
    expected_pvc, expected_bank = pvc, bank
    ends = {}
    results, step_starts, phase_starts, cpp_out = [], {}, {}, {}
    guard = None
    identities = []
    if declared:
        totals['declared_register_rows'] += 1
    for j, phase in enumerate(row['phases']):
        data = phase['_data']
        entry = dict(pc=state['pc'], a7=state['a7'])
        if state['pc'] in BIOS_PCS and phase['host_changes']:
            resume_pc = check_bios_resume(phase, ram, state)
            totals['bios_resumes_checked'] += 1
            totals['bios_resume_pcs'][hex(resume_pc)] = totals['bios_resume_pcs'].get(hex(resume_pc), 0) + 1
        if phase['guard'] is not None:
            assert j == len(row['phases']) - 1 and row['guarded']
            ram, state2, kinds = cm.apply_changes(ram, state, phase['host_changes'], entry)
            assert ram == data['ram_before.bin']
            guard = (row, phase, ram, state2, pvc, bank)
            break
        ram, state, kinds = cm.apply_changes(ram, state, phase['host_changes'], entry)
        for kind in kinds:
            totals['declared_host_changes'][kind] += 1
        assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming'], (row['label'], j)
        assert ram == data['ram_before.bin'] and bank == phase['bank_before'], (row['label'], j)
        assert kinds == [c['kind'] for c in phase['host_changes']]
        if phase['phase_in_step'] == 0:
            step_starts[phase['step']] = (ram, dict(state), pvc, bank, expected_pvc, expected_bank)
        if row['index'] == 0:
            phase_starts[j] = (ram, dict(state), pvc, bank)
        events = phase['_trace']['events']
        expected_pvc, expected_bank, portbytes = cc.fold_outputs(expected_pvc, expected_bank, events)
        assert expected_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
        phase_in, phase_pvc, phase_bank = dict(state), pvc, bank
        actual = common.invoke(exe, work, 'split', ram, state, pvc, bank, ctx['resources'],
                               stop=phase['stop_pc'], external=fx['external'])
        assert actual[0]['ok'] and not actual[4], (row['label'], j, hex(phase['stop_pc']), actual[4])
        common.check_result(actual, dict(outgoing=phase['outgoing'], events=events, ram_after=data['ram_after.bin']),
                            expected_pvc, expected_bank, portbytes)
        assert actual[0]['status'] == 0
        result, ram, pvc, _, _ = actual
        executed = phase['_trace']['pcs'][:-1]
        assert not (set(executed) & set(BIOS_PCS)) and set(executed) <= set(instr), (row['label'], j)
        if result['pc'] in BIOS_PCS:
            site = check_bios_stop(phase, ram, result)
            totals['bios_stops'][hex(site)] = totals['bios_stops'].get(hex(site), 0) + 1
        want_carry = cc.classify_carry(instr, state['carry'], executed)
        assert result['carry'] == want_carry, (row['label'], j, hex(phase['outgoing']['pc']), result['carry'], want_carry)
        totals['carry_histogram'][result['carry']] += 1
        # Known-C probes: the same phase with C = Clear/Set must give exactly the source classification and otherwise
        # identical outputs. A phase whose C-reading branch runs before any C write consumes the incoming C: not probed.
        if executed and not consumes_incoming(instr, executed):
            for probe in (1, 2):
                again = common.invoke(exe, work, 'probe', data['ram_before.bin'], dict(phase_in, carry=probe),
                                      phase_pvc, phase_bank, ctx['resources'], stop=phase['stop_pc'],
                                      external=fx['external'])
                assert again[0]['ok'] and not again[4]
                assert again[0]['carry'] == cc.classify_carry(instr, probe, executed), (row['label'], j, probe)
                assert ({k: v for k, v in again[0].items() if k != 'carry'} ==
                        {k: v for k, v in result.items() if k != 'carry'})
                assert again[1] == ram and again[2] == pvc and again[3] == actual[3]
                totals['carry_probes'] += 1
                if executed[0] in SAVE_SET and executed == block_walk(instr, executed[0], ctx['block_set']):
                    totals['single_block'][executed[0]] = totals['single_block'].get(executed[0], set()) | {again[0]['carry'] == probe}
                totals['carry_probe_preserved'] += again[0]['carry'] == probe
        else:
            totals['carry_probe_skipped_consumer'] += bool(executed)
        totals['carry_checks'] += 1
        state = {k: result[k] for k in common.STATE_KEYS}
        bank = result['bank_base']
        totals['reads'] += result['external_reads']
        totals['ports'] += len(actual[3]) // 9
        totals['split'] += 1
        if j:
            totals['resumes'] += 1
        results.append(dict(step=phase['step'], label=phase['label'], stop_pc=hex(phase['stop_pc']),
                            carry=cc.CARRY_NAME[result['carry']], actual_previous_outputs_used=bool(j)))
        ends[phase['step']] = (ram, dict(state), pvc, bank)
        cpp_out[j] = (ram, dict(state), pvc, bank)
        identities.append(row_identity(phase))
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
        actual = common.invoke(exe, work, 'control', c_ram, c_state, c_pvc, c_bank, ctx['resources'],
                               stop=phase['stop_pc'], external=fx['external'])
        assert actual[0]['ok'] and not actual[4], (row['label'], step, actual[4])
        common.check_result(actual, dict(outgoing=phase['outgoing'], events=phase['_trace']['events'],
                                         ram_after=data['ram_after.bin']), e_pvc, e_bank, portbytes)
        end = ends[step]
        assert (actual[1], {k: actual[0][k] for k in common.STATE_KEYS}, actual[2], actual[0]['bank_base']) == end, (row['label'], step)
        control_rows += 1
    totals['cases'] += 1
    totals['control'] += control_rows
    return dict(index=row['index'], label=row['label'], group=row['group'], origin=origin, declared_initial=declared,
                split_phases=len(results), control_steps=control_rows, phases=results), ends, guard, cpp_out, phase_starts, identities


def new_totals():
    return dict(cases=0, split=0, control=0, resumes=0, ports=0, reads=0, carry_checks=0, carry_probes=0,
                carry_probe_preserved=0, carry_probe_skipped_consumer=0, declared_register_rows=0,
                bios_resumes_checked=0, bios_resume_pcs={}, bios_stops={}, partial_rows={},
                declared_host_changes=dict(ram=0, pc=0, a7_add=0), carry_histogram={0: 0, 1: 0, 2: 0}, single_block={})


def merge_totals(total, part):
    for key, value in part.items():
        if key == 'single_block':
            for pc, outcomes in value.items():
                total[key][pc] = total[key].get(pc, set()) | outcomes
        elif key == 'partial_rows':
            total[key].update(value)
        elif isinstance(value, dict):
            for name, count in value.items():
                total[key][name] = total[key].get(name, 0) + count
        else:
            total[key] += value


def process_row(exe, row, ctx, prefix_ends, chain_ends):
    """One native row: files, audit, actual C++ replay (each row owns its work directory; rows are independent)."""
    began = time.time()
    work = WORK / ('r%03d' % row['index'])
    work.mkdir(parents=True)
    lt = new_totals()
    program_reads = dict(fixed_reads=0, bank_reads=0, PVC_writes=0)
    load_row_files(NATIVE_DIR, row)
    audit_row(row, ctx['program'], ctx['instr'], lt, program_reads)
    if row['index'] == 0:
        assert row['label'] == SAVE_CHAIN_LABEL and row['fixture']['entry_pc'] == cc.BIOS
        ram, state, pvc, bank = prefix_ends[30]
        origin = ('actual C++ output of the re-run prefix (fade/card BIOS chain, open-native chain steps 0..30, stop 2ac2)'
                  ' plus the declared host changes of step 31')
        assert sha(ram) == ctx['report']['card_menu_open_crosscheck']['ram_after_sha256']
        assert sha(cc.masked_pvc(pvc)) == sha(cc.masked_pvc(row['phases'][0]['_data']['pvc_before.bin']))
        start = (ram, dict(state), pvc, bank, origin, [])
    else:
        start = fresh_start(row, chain_ends)
    entry, ends, guard, cpp_out, phase_starts, identities = run_row(exe, row, start, ctx, work, lt)
    matches = 0
    if row['index'] and row['compared_with_chain']:
        matches = chain_compare(row, ctx['report'], cpp_out, ctx, lt, ctx['report']['partial_chain_comparison'])
    item = dict(index=row['index'], label=row['label'], entry=entry, guard=guard, totals=lt, program_reads=program_reads,
                declared=start[5], chain_matches=matches)
    if row['index'] == 0:
        item.update(ends=ends, cpp_out=cpp_out, phase_starts=phase_starts, identities=identities)
    release_row(row)
    shutil.rmtree(work, ignore_errors=True)
    print('row %d %s: %d split phases, %.1fs' % (row['index'], row['label'], entry['split_phases'], time.time() - began),
          file=sys.stderr, flush=True)
    return item


def audit_row(row, program, instr, totals, program_reads):
    assert row['reproduced_twice'] and row['continuous_split_equivalent']
    assert bool(row['guarded']) == (row['group'] == 'guard')
    fx = row['fixture']
    for kind in ('phases', 'continuous_control'):
        counts = cc.audit_program_reads(program, fx, row[kind])
        if kind == 'phases':
            for key, value in counts.items():
                program_reads[key] += value
    cc.audit_split_control(row)
    for phase in row['phases'] + row['continuous_control']:
        assert phase['carry'] is None and not phase['branch_evidence']
        assert phase['counts']['external_reads'] == sum(e['region'] == 'external' for e in phase['_trace']['events'])
        ports = [e for e in phase['_trace']['events'] if e['region'] in ('pvc', 'video', 'watchdog')]
        assert phase['_data']['ports.bin'] == b''.join(
            cc.struct.pack('>BII', e['size'], e['address'], int(e['bytes'], 16)) for e in ports)
        executed = set(phase['_trace']['pcs'][:-1])
        assert not (executed & set(BIOS_PCS)) and instr.keys() >= executed


def chain_compare(row, report, cpp_out, ctx, totals, partial):
    found = 0
    missing = []
    for j, phase in enumerate(row['phases']):
        if phase['guard'] is not None:
            continue
        key = row_identity(phase)
        if key not in ctx['chain_identity']:
            missing.append(j)
            continue
        assert strip_carry(cpp_out[j]) == strip_carry(ctx['chain_identity'][key]), (row['label'], j)
        found += 1
    if row['label'] in partial:
        assert found == partial[row['label']], (row['label'], found)
        assert missing and missing == list(range(missing[0], len(row['phases']))), 'partial rows diverge once and stay diverged'
        totals['partial_rows'][row['label']] = dict(matched=found, diverged_from_phase=missing[0], phases=len(row['phases']))
    else:
        assert not missing, (row['label'], missing[:5])
    return found


def check_error(label, exe, ram, state, pvc, bank, resources, stop, external, expected):
    result, outgoing, out_pvc, ports, error = common.invoke(exe, WORK, 'reject', ram, state, pvc, bank, resources,
                                                            stop=stop, external=external)
    assert not result['ok'], (label, 'C++ accepted', hex(result['pc']))
    assert error.strip() == expected, (label, error.strip(), expected)
    assert {k: result[k] for k in common.STATE_KEYS} == state
    assert outgoing == ram and out_pvc == pvc and result['bank_base'] == bank
    assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1
    return error.strip()


def compare_guards(exe, guards, resources):
    rows, superseded = [], []
    for row, phase, ram, state, pvc, bank in guards:
        stop = phase['stop_pc']
        state = dict(state, carry=2)
        if row['label'] in SUPERSEDED_GUARDS:
            result, outgoing, out_pvc, ports, error = common.invoke(exe, WORK, 'guard_sup', ram, state, pvc, bank, resources,
                                                                    stop=stop, external=row['fixture']['external'])
            superseded.append(dict(label=row['label'], native_guard=phase['guard'], stop_pc=hex(stop),
                                   C_plus_plus_ok=result['ok'], C_plus_plus_pc=hex(result['pc']),
                                   C_plus_plus_error=error.strip(), C_plus_plus_status=result['status'],
                                   claim='none: native fetch of 9e94 is unmapped in the save observer; the C++ machine has the close executor'))
            continue
        error = check_error(row['label'], exe, ram, state, pvc, bank, resources, stop, row['fixture']['external'],
                            GUARD_ERRORS[row['label']])
        rows.append(dict(label=row['label'], native_guard=phase['guard'], checked_API_error=error,
                         all_API_outputs_preserved=True, native_fault_rollback_equivalence_claimed=False))
    return rows, superseded


def expected_pc_error(pc):
    if any(low <= pc <= high for low, high in ROUTER_SAVE):
        return UNSUPPORTED_SAVE
    return UNSUPPORTED_MACHINE


def negatives(exe, base, bios_starts, instr, static, resources):
    out = []

    def reject(label, start, changes=None, stop=0xff000, expected=None, carry=2):
        r, s, p, b = start
        s = dict(s, carry=carry)
        s.update(changes or {})
        error = check_error(label, exe, r, s, p, b, resources, stop, 0, expected)
        out.append(dict(label=label, error=error, all_API_outputs_preserved=True,
                        native_exception_rollback_equivalence_claimed=False))

    interior = []
    for item in sorted(static['instructions'], key=lambda i: i['cpu_address']):
        pc = item['cpu_address']
        if any(low <= pc < high for low, high in SAVE_RANGES) and pc not in SAVE_SET:
            interior.append(pc)
    branches = [pc for pc in interior if mnemonic(instr, pc) in COND_BRANCH]
    for pc in interior:
        kind = 'bundled_branch' if pc in branches else 'interior'
        assert expected_pc_error(pc) == UNSUPPORTED_SAVE, hex(pc)
        reject('%s_direct_entry_%06x' % (kind, pc), base, {'pc': pc}, expected=UNSUPPORTED_SAVE)
    for pc in sorted({high for _low, high in SAVE_RANGES} | {0x9f34, 0xbd94}):
        if pc in SAVE_SET:
            continue
        reject('outside_range_entry_%06x' % pc, base, {'pc': pc}, expected=expected_pc_error(pc))
    # c1ea consumes C: Unknown is a checked error (full rollback), known C moves PC without touching anything else.
    reject('c1ea_unknown_carry', base, {'pc': 0xc1ea}, carry=0, expected=NEEDS_CARRY)
    reject('c1ea_unknown_carry_stop_c202', base, {'pc': 0xc1ea}, carry=0, stop=0xc202, expected=NEEDS_CARRY)
    # BIOS boundaries: the JSR blocks reached with any stop other than the declared BIOS PC roll back completely;
    # a BIOS PC entered directly with another stop is unsupported too.
    controls = []
    for pc, bios in ((0xbd3c, BIOS_A), (0xbd60, BIOS_A), (0xbe0c, BIOS_B)):
        start = bios_starts[pc]
        ret = {0xbd3c: 0xbd60, 0xbd60: 0xbd90, 0xbe0c: 0xbe1c}[pc]
        other = BIOS_B if bios == BIOS_A else BIOS_A
        for stop in (0xff000, 0x2ac2, other, ret):
            reject('%06x_bios_%06x_reached_with_stop_%06x' % (pc, bios, stop), start, stop=stop, expected=UNSUPPORTED_MACHINE)
        r, s, p, b = start
        result, rram, rpvc, rports, error = common.invoke(exe, WORK, 'bios_control', r, dict(s, carry=2), p, b, resources, stop=bios)
        assert result['ok'] and not error and result['pc'] == bios and result['status'] == 0
        assert read_long(rram, result['a7']) == ret and read_long(rram, result['a7'] + 4) == result['a6']
        controls.append(dict(entry=hex(pc), stop=hex(bios), return_on_stack=hex(ret), saved_A6_above=True))
    for pc, start in (('c00468#1', bios_starts['bios1']), ('c00468#2', bios_starts['bios2']), ('c0046e', bios_starts['bios3'])):
        bios = start[1]['pc']
        assert bios in BIOS_PCS
        for stop in (0xff000, 0x2ac2, BIOS_B if bios == BIOS_A else BIOS_A):
            reject('direct_bios_entry_%s_with_stop_%06x' % (pc.replace('#', '_'), stop), start, stop=stop,
                   expected=UNSUPPORTED_MACHINE)
    return out, len(interior), len(branches), controls


def known_carry_controls(exe, base, resources):
    ram, state, pvc, bank = base
    rows = []
    for carry, target in ((1, 0xc202), (2, 0xc1ee)):
        s = dict(state, pc=0xc1ea, carry=carry)
        result, out_ram, out_pvc, ports, error = common.invoke(exe, WORK, 'c1ea', ram, s, pvc, bank, resources, stop=target)
        assert result['ok'] and not error and result['pc'] == target and result['carry'] == carry and result['status'] == 0
        assert {k: result[k] for k in common.STATE_KEYS if k != 'pc'} == {k: s[k] for k in common.STATE_KEYS if k != 'pc'}
        assert out_ram == ram and out_pvc == pvc and not ports
        rows.append(dict(pc=0xc1ea, carry=cc.CARRY_NAME[carry], target=hex(target)))
    return rows


def zero_step(exe, base, resources):
    ram, state, pvc, bank = base
    rows = []
    for pc in SAVE_BLOCKS:
        for carry in (0, 1, 2):
            s = dict(state, pc=pc, carry=carry)
            result, out_ram, out_pvc, ports, error = common.invoke(exe, WORK, 'zero', ram, s, pvc, bank, resources, stop=pc)
            assert result['ok'] and not error and result['status'] == 0, (hex(pc), carry, error)
            assert {k: result[k] for k in common.STATE_KEYS} == s
            assert out_ram == ram and out_pvc == pvc and result['bank_base'] == bank
            assert result['external_reads'] == 0 and not ports
            rows.append(dict(pc=hex(pc), carry=carry, all_input_state_preserved=True))
    return rows


def boundary_zero_step(exe, base, resources):
    ram, state, pvc, bank = base
    rows = []
    for pc in BIOS_PCS:
        s = dict(state, pc=pc, carry=2)
        result, out_ram, out_pvc, ports, error = common.invoke(exe, WORK, 'zero_boundary', ram, s, pvc, bank, resources, stop=pc)
        assert result['ok'] and {k: result[k] for k in common.STATE_KEYS} == s and out_ram == ram and out_pvc == pvc
        rows.append(dict(pc=hex(pc), ok=result['ok'], error=error.strip()))
    return rows


def old_verifier_probe(exe, prefix_ends, resources):
    """Observed behavior (not a requirement) of the older verifiers' negative inputs under the current engine:
    the same state class (open a29c step 24 / a370 step 25 outputs of the actual C++ prefix), carry Set, stop ff000."""
    rows = []
    cases = [('push verifier base (a29c, step 24)', 24, (0xa100,)),
             ('open verifier base (a370, step 25)', 25, (0xbd26, 0x9f36, 0xa71a, 0xc1ea, 0xa100))]
    for name, step, pcs in cases:
        ram, state, pvc, bank = prefix_ends[step]
        for pc in pcs:
            s = dict(state, pc=pc, carry=2)
            result, out_ram, out_pvc, ports, error = common.invoke(exe, WORK, 'old', ram, s, pvc, bank, resources, stop=0xff000)
            rows.append(dict(base=name, entry_pc=hex(pc), stop='0xff000', ok=result['ok'], pc_after=hex(result['pc']),
                             error=error.strip(), outputs_preserved_on_error=(not result['ok'] and out_ram == ram and out_pvc == pvc)))
    return rows


def main():
    started = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    report_path = OUT / 'verification.json'
    report_path.unlink(missing_ok=True)
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_card_menu_save.py', 'tools/verify_animation_machine_card_menu.py',
                 'tools/verify_animation_machine_card_child.py', 'tools/observe_animation_machine_card_menu_save.py',
                 'tools/observe_animation_machine_card_menu_open.py',
                 'docs/analysis/animation-machine-card-menu-save-contract.md',
                 'engine/src/animation_machine_card_menu_save.cpp', 'engine/src/animation_machine_card_menu_open.cpp',
                 'engine/src/animation_machine_card_menu.cpp', 'engine/src/animation_machine_card_child.cpp',
                 'engine/tests/animation_machine_card_menu_save_test.cpp'):
        inputs[name] = cc.digest(ROOT / name)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = cc.digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = cc.digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    exe, command = helpers.compile_harness(ROOT, OUT)
    union = load_instruction_union(program)
    report, rows, native_refs, static, covered = audit_save_native(program, source, union)
    # --- prefix: actual C++ re-run of the reviewed chains (fade/card BIOS -> open-native steps 0..30) -------------------
    cc.OUT = OUT / 'card_child_chain'
    cc.OUT.mkdir(parents=True, exist_ok=True)
    bios_start = cc.fade_chain_bios_output(exe, program, source, resources)
    open_report, open_chain, open_refs = audit_open_prefix(program, source)
    prefix_ends, prefix_info = replay_prefix(exe, open_chain, bios_start, resources)
    for step, key in ((24, 'card_child_crosscheck'), (25, 'card_menu_push_crosscheck'), (30, 'card_menu_open_crosscheck')):
        cross = report[key]
        assert cross['step'] == step
        assert sha(prefix_ends[step][0]) == cross['ram_after_sha256'], key
        assert hex(prefix_ends[step][1]['pc']) == cross['outgoing_pc'], key
    assert report['card_menu_open_crosscheck']['reference_report_sha256'] == OPEN_NATIVE_SHA
    assert report['card_menu_open_crosscheck']['reference_tool_sha256'] == OPEN_TOOL_SHA
    # --- save rows --------------------------------------------------------------------------------------------------
    block_set = frozenset(report['block_starts'])
    ctx = dict(instr=union, resources=resources, block_set=block_set, chain_identity={}, report=report, program=program)
    totals = new_totals()
    program_reads = dict(fixed_reads=0, bank_reads=0, PVC_writes=0)
    first = process_row(exe, rows[0], ctx, prefix_ends, None)
    assert first['index'] == 0
    chain_ends = first['ends']
    for j, key in enumerate(first['identities']):
        ctx['chain_identity'].setdefault(key, first['cpp_out'][j])
    results = [first]
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(process_row, exe, row, ctx, prefix_ends, chain_ends) for row in rows[1:]]
        results += [future.result() for future in futures]
    out_rows, guards, fresh_declared, chain_matches = [], [], {}, 0
    for item in results:
        merge_totals(totals, item['totals'])
        for key, value in item['program_reads'].items():
            program_reads[key] += value
        out_rows.append(item['entry'])
        if item['guard']:
            guards.append(item['guard'])
        if item['index']:
            fresh_declared[item['label']] = item['declared']
        chain_matches += item['chain_matches']
    # chain start states for the BIOS negatives (row 0 phases)
    by_pc = {}
    for j, phase in enumerate(rows[0]['phases']):
        by_pc.setdefault(phase['incoming']['pc'], first['phase_starts'][j])
    bios_starts = {pc: by_pc[pc] for pc in (0xbd3c, 0xbd60, 0xbe0c, 0xbe1c)}
    bios_starts['bios1'], bios_starts['bios2'], bios_starts['bios3'] = chain_ends[33], chain_ends[34], chain_ends[35]
    assert [bios_starts[k][1]['pc'] for k in ('bios1', 'bios2', 'bios3')] == [BIOS_A, BIOS_A, BIOS_B]
    base_state = chain_ends[32]
    assert base_state[1]['pc'] == 0x2ac2
    assert chain_matches == report['chain_vs_fresh_phases_compared'] == 823, chain_matches
    totals['fresh_vs_chain_C++_phases_equal'] = chain_matches
    # contract carry-preserving list vs the source opcodes and the observed single-block phases
    preserving = sorted(pc for pc in SAVE_BLOCKS if all(mnemonic(union, p) in FLOW_ONLY
                                                      for p in block_walk(union, pc, block_set)))
    assert preserving == sorted(CPP_PRESERVING), [hex(p) for p in preserving]
    cpp_text = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    section = cpp_text.split('// Card menu save blocks')[1].split('// Card menu nested blocks')[0].split('// BTST/BEQ')[0]
    assert sorted(int(x, 16) for x in re.findall(r'case 0x([0-9a-f]+):', section)) == preserving
    for pc, outcomes in totals['single_block'].items():
        walk = block_walk(union, pc, block_set)
        assert outcomes == {cc.classify_carry(union, probe, walk) == probe for probe in (1, 2)}, (hex(pc), outcomes)
        assert (outcomes == {True}) == (pc in preserving), hex(pc)
    totals['single_block_carry_starts_checked'] = sorted(hex(pc) for pc in totals['single_block'])
    totals['carry_preserving_starts_observed'] = sorted(hex(pc) for pc in totals['single_block'] if pc in preserving)
    totals['carry_preserving_starts_not_observed_alone'] = sorted(hex(pc) for pc in preserving if pc not in totals['single_block'])
    totals['carry_known_set_clear_blocks_observed'] = sorted(hex(pc) for pc in (0xbe2e, 0xbe34) if pc in totals['single_block'])
    totals['carry_histogram'] = {cc.CARRY_NAME[k]: v for k, v in totals['carry_histogram'].items()}
    totals['single_block_carry_preserved_outcomes'] = {hex(pc): sorted(v) for pc, v in sorted(totals.pop('single_block').items())}
    guarded, superseded = compare_guards(exe, guards, resources)
    assert len(guarded) + len(superseded) == 13 == len(guards)
    negative, interior_count, branch_count, bios_controls = negatives(exe, base_state, bios_starts, union, static, resources)
    known = known_carry_controls(exe, base_state, resources)
    zero = zero_step(exe, base_state, resources)
    boundary_zero = boundary_zero_step(exe, base_state, resources)
    old = old_verifier_probe(exe, prefix_ends, resources)
    for name, expected in list(inputs.items()) + list(refs.items()):
        assert cc.digest(ROOT / name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    refs.update(native_refs)
    refs.update(open_refs)
    shutil.rmtree(WORK, ignore_errors=True)
    refs.update({str(path.resolve()): cc.digest(path) for path in OUT.rglob('*')
                 if path.is_file() and path != report_path})
    unique = {}
    for name, expected in list(inputs.items()) + list(refs.items()):
        key = str((ROOT / name).resolve())
        assert key not in unique or unique[key] == expected
        unique[key] = expected
    result = dict(schema_version=1, source=source, inputs=inputs, artifacts=refs,
                  native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA,
                  contract_sha256=CONTRACT_SHA, open_native_observation_sha256=OPEN_NATIVE_SHA,
                  actual_CPP=dict(totals, matches=out_rows),
                  prefix_C_plus_plus=dict(prefix_info, chain=OPEN_CHAIN_LABEL, steps='0..30',
                                          step24_ram_sha256=sha(prefix_ends[24][0]), step25_ram_sha256=sha(prefix_ends[25][0]),
                                          step30_ram_sha256=sha(prefix_ends[30][0]), step30_pc=hex(prefix_ends[30][1]['pc']),
                                          step30_a7=hex(prefix_ends[30][1]['a7'])),
                  original_program_read_audit=program_reads,
                  native_guards_checked_API=guarded, native_guards_superseded=superseded,
                  native_continuous_control_phases_replayed=totals['control'],
                  negatives=negative, negative_count=len(negative) + len(guarded),
                  interior_PCs_rejected=interior_count, bundled_branch_PCs_among_interior=branch_count,
                  BIOS_stop_controls=bios_controls, c1ea_known_carry_targets=known,
                  zero_step=zero, boundary_zero_step=boundary_zero,
                  block_starts=len(SAVE_BLOCKS), unobserved_block_starts=[hex(p) for p in SAVE_BLOCKS if p not in covered],
                  carry_preserving_blocks=[hex(p) for p in preserving],
                  fresh_row_declared_register_overrides={k: v for k, v in fresh_declared.items() if v},
                  older_verifier_negative_inputs_under_current_engine=old,
                  save_chain_C_plus_plus=dict(label=SAVE_CHAIN_LABEL, final_step=36,
                                              final_ram_sha256=sha(chain_ends[36][0]), final_pc=hex(chain_ends[36][1]['pc']),
                                              final_a7=hex(chain_ends[36][1]['a7'])),
                  carry_check=('C++ carry equals the source-opcode walk over native-executed PCs (ORI #1,CCR = Set at be2e,'
                               ' ANDI #fe,CCR = Clear at be34, flow-only preserved, else Unknown); native SR never read;'
                               ' the 7 carry-preserving blocks are derived from the source opcodes and equal the list in'
                               ' animation_machine.cpp'),
                  normalized_reference_paths=len(unique), compile_command=command, failure=None, ROM_unchanged=True,
                  limits=['Controlled fixtures; frame re-entry is a declared PC=2ab8 change on the previous actual output, not a natural scheduler, IRQ or VBlank.',
                          'BIOS c00468 (command 4 at bd5a, command 3 at bd8a) and c0046e (be16) are stop boundaries only, never executed: the card write, the BIOS register effects on 10fdc2..10fdd0 and the BYTE 10fdc6 answer are declared host inputs, not original-measured.',
                          'Declared resumes (PC = return LONG on the stack, A7 += 4, optional BYTE 10fdc6) are asserted against the native record; carry after a BIOS stop is whatever the C++ output carries (Unknown) and is not a BIOS measurement.',
                          'Direct entries bbb8, bb74, bd26, be0c, descriptor flags, nested-limit and tail fixtures are declared inputs on the actual C++ chain output; only the chain rows are connected end to end.',
                          'Carry is a source-opcode classification (native SR is never read), not a native C measurement; ADDA/SUBA and every non-flow instruction are conservatively Unknown.',
                          'Native guard guard-desc-flags-0001-9e94 (unmapped native fetch of 9e94) is superseded: the C++ machine has the close executor for 9e94; it is recorded, no equivalence is claimed.',
                          'Checked failures preserve API outputs, not original CPU fault rollback; interior/bundled-branch direct entries have no native guard (API-only rejection).',
                          'Native observation artifacts are audited by hash/trace consistency, not re-executed here.'])
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=totals['cases'], split=totals['split'], control=totals['control'], resumes=totals['resumes'],
                          negatives=result['negative_count'], interior=interior_count, zero_step=len(zero),
                          carry=totals['carry_histogram'], probes=totals['carry_probes'],
                          seconds=round(time.time() - started, 1), sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
