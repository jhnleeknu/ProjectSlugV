"""Original card-menu close (a662 -> a2be shrink / 9e94 -> c2c8 fade -> c2e0 timer -> 2a00 child cleanup -> parent 480ac -> 2a00)
native evidence vs the public machine API.

Controlled fixtures; no expected-register injection. The frozen native observations (close, and the input observation that
produced the 331-step prefix) are immutable inputs: this verifier never invokes an observer main. The chain start is NOT taken
from native registers: the 331 prefix steps (BIOS resume .. card child .. a29c .. a370 .. open frames .. 300 input frames) are
re-run in actual C++ from the actual C++ BIOS-stop output and compared step by step with the input observation; the close rows
then resume only from previous actual C++ outputs plus the declared host changes recorded in the step records (PC=2ab8 frame
re-entry, RAM fixtures, and the register write A6=parent at the parent re-entry step boundary, each asserted against the record).
a698 (nested menu return) is a stop boundary only: never executed.
"""
import json
from pathlib import Path
import re
import shutil
import sys
import verify_animation_machine as common
import verify_animation_machine_callers as helpers
import verify_animation_machine_card_child as cc
from disassemble_program import disassemble_range, load_verified_program

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/animation_machine_card_menu_close_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_card_menu_close_native'
INPUT_DIR = ROOT / 'artifacts/animation_machine_card_menu_input_native'
NATIVE_SHA = 'b5bd2164ab5badd5067b469d9d6c7d79b3cedeae2efca07d89ff18d4882a39dd'
NATIVE_TOOL_SHA = 'f38219e8734f45e1dc0389e222c64bb005b3d7493f5ecee29a006108fa554de8'
CONTRACT_SHA = '925c44c1fb66b9489be24073f598b83132d02936a5f0ab46e417fcb145274c38'
INPUT_SHA = '49c1ba52f7ec11dc1929022f7dc6b455b434681d472e9a39631c69ea98ce9b46'
INPUT_TOOL_SHA = 'cbd6fdf19fcc4c5ccec8126be1ab9f98501df5a393dd9805da3f1b7802e66104'
MARKER = cc.MARKER
A324, A698, A328, A332 = 0xa324, 0xa698, 0xa328, 0xa332
# BCS blocks that consume the C left by a018 (a06c Clear / a076 Set): a phase starting there depends on the incoming C.
CALLER_BCS = (0x9ba6, 0x9bcc, 0x9bea, 0x9c10, 0x9c36, 0x9c54, 0x9c76, 0x9c9c, 0x9cba, 0x9cd8, 0x9cfc, 0x9d22,
              0x9dc0, 0x9dd6, 0xa00c, A324)
CLOSE_BLOCK_TEXT = ('9e94 9eb0 9eb8 9ec2 9eca 9eda 9ee4 a2be a2d0 a2d6 a2ec a306 a30e a318 a320 a324 a328 a332 a33c a344 '
                    'a662 a672 a676 a67a a67e a694 c2c8 c2d6 c2e0 c2e8 c2f8')
BLOCK_STARTS = tuple(int(x, 16) for x in CLOSE_BLOCK_TEXT.split())
BLOCK_SET = frozenset(BLOCK_STARTS)
assert len(BLOCK_STARTS) == len(BLOCK_SET) == 31
CARRY_PRESERVING = (0x9ee4, 0xa320, 0xa324, 0xa672, 0xa67a, 0xc2f8)      # contract; a344 deliberately Unknown
CLOSE_RANGES = ((0x9e94, 0x9ee6), (0xa2be, 0xa348), (0xa662, 0xa698), (0xc2c8, 0xc2fa))
ROUTER_RANGES = ((0x9e94, 0x9ee4), (0xa2be, 0xa346), (0xa662, 0xa696), (0xc2c8, 0xc2f8))    # inclusive, animation_machine.cpp
END_MNEMONICS = ('bra', 'jmp', 'rts', 'bsr', 'jsr', 'beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls',
                 'bge', 'blt', 'bgt', 'ble', 'dbra', 'dbf')
PREFIX_LAST_STEP = 330
CHAIN_FIRST_STEP = 331
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNSUPPORTED_CLOSE = 'unsupported animation card menu close PC'
NEEDS_CARRY = 'card menu caller requires known carry'
EVEN = 'program bus requires even WORD/LONG address'
WRITE_ALIGN = 'invalid animation machine write size/alignment'
CHILD, PARENT = 0x104800, 0x102000
RECORD, F2, EE, E5 = 0x107efe, 0x107f0e, 0x107f12, 0x107f1b
DECLARED_REG = {'name': 'a6', 'value': PARENT}
PREFIX_CHECKS = (('card_child_crosscheck', 24), ('card_menu_push_crosscheck', 25), ('card_menu_open_crosscheck', 30),
                 ('card_menu_input_crosscheck', PREFIX_LAST_STEP))
NEG_STOPS = (0xff000, 0x2ac2, 0xc2c0)      # a370 is a legitimate stop inside the nested step (menu frame), so not a negative


def sha(data):
    return cc.sha(data)


def mnemonic(instructions, pc):
    return instructions[pc]['mnemonic'].split('.')[0]


def in_ranges(pc, ranges):
    return any(low <= pc < high for low, high in ranges)


def load_phase(directory, phase):
    """Payload files of one phase (hash checked against the report); returns the data and trace."""
    data = {}
    for name, expected in phase['artifacts'].items():
        value = (directory / name).read_bytes()
        assert sha(value) == expected, name
        data[name.rsplit('phase_%03d_' % phase['index'], 1)[1]] = value
    phase['_data'] = data
    phase['_trace'] = json.loads(data['trace.json'])
    for snapshot in phase['snapshots']:
        snapshot['_ram'] = (directory / snapshot['artifacts']['ram']).read_bytes()
        snapshot['_pvc'] = (directory / snapshot['artifacts']['pvc']).read_bytes()
        assert sha(snapshot['_ram']) == phase['artifacts'][snapshot['artifacts']['ram']]
        assert sha(snapshot['_pvc']) == phase['artifacts'][snapshot['artifacts']['pvc']]


def load_row(row):
    for kind in ('phases', 'continuous_control'):
        for phase in row[kind]:
            load_phase(NATIVE_DIR, phase)


def release_row(row):
    for kind in ('phases', 'continuous_control'):
        for phase in row[kind]:
            for key in ('_data', '_trace'):
                phase.pop(key, None)
            for snapshot in phase['snapshots']:
                snapshot.pop('_ram', None)
                snapshot.pop('_pvc', None)


def apply_changes(ram, state, changes, entry, registers=None):
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
        elif kind == 'reg':
            assert change['name'] == DECLARED_REG['name'] and change['value'] == DECLARED_REG['value'], change
            assert state[change['name']] != change['value'], 'declared register change must change the register'
            state[change['name']] = change['value']
            if registers is not None:
                registers.append(change)
        else:
            raise AssertionError(kind)
        kinds.append(kind)
    return bytes(ram), state, kinds


def block_walk(instructions, start):
    """Instruction run of a contract block: up to the first control transfer or the next block start."""
    pc, out = start, []
    while True:
        item = instructions[pc]
        out.append(pc)
        if mnemonic(instructions, pc) in END_MNEMONICS or pc + item['size'] in BLOCK_SET:
            return out
        pc += item['size']


def derived_preserving(instructions):
    """Blocks whose every instruction is flow-only (C kept), from the source opcodes only."""
    return sorted(pc for pc in BLOCK_STARTS
                  if all(mnemonic(instructions, p) in cc.FLOW_ONLY for p in block_walk(instructions, pc)))


CMP_KNOWN = 3
CLEANUP_CMP = (0x2886, 0x2a12)      # CMP.W 10(A0),D0 of the existing cleanup core: C known from the comparison (cleanup core models it)


def classify_carry(instructions, carry, pcs):
    """cc.classify_carry plus the cleanup core's compare rule: after CMP.W the C is known and the following BCS/BCC path
    (next executed PC) tells which; unresolved (phase ends inside) is CMP_KNOWN = either Clear or Set."""
    out = carry
    for i, pc in enumerate(pcs):
        name = mnemonic(instructions, pc)
        if pc in CLEANUP_CMP and name == 'cmp':
            out = CMP_KNOWN
        elif out == CMP_KNOWN and name in ('bcs', 'bcc') and i + 1 < len(pcs):
            taken = pcs[i + 1] != pc + instructions[pc]['size']
            out = (2 if taken else 1) if name == 'bcs' else (1 if taken else 2)
        elif out == CMP_KNOWN and name in cc.FLOW_ONLY:
            pass
        else:
            out = cc.classify_carry(instructions, out if out != CMP_KNOWN else 0, [pc])
    return out


def carry_equal(result, want):
    return result in (1, 2) if want == CMP_KNOWN else result == want


def collect_instructions(program, close_static):
    """All native source.json instruction tables (each checked against the ROM bytes), plus a ROM disassembly fallback."""
    instructions = {}
    for path in sorted((ROOT / 'artifacts').glob('animation_machine_*_native/source.json')):
        static = json.loads(path.read_text())
        for instruction in static['instructions']:
            at, size = instruction['rom_offset'], instruction['size']
            assert bytes(bytearray.fromhex(instruction['raw'])) == program[at:at + size]
            old = instructions.get(instruction['cpu_address'])
            assert old is None or old['raw'] == instruction['raw'], hex(instruction['cpu_address'])
            instructions[instruction['cpu_address']] = instruction
    for instruction in close_static['instructions']:
        assert instructions[instruction['cpu_address']]['raw'] == instruction['raw']
    return instructions


def audit_static(program, source):
    path = NATIVE_DIR / 'observation.json'
    assert cc.digest(path) == NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_card_menu_close.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'docs/analysis/animation-machine-card-menu-close-contract.md') == CONTRACT_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['sha256'] == CONTRACT_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase', 'register_injection_after_begin',
                'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['rom_stat_start'] == report['rom_stat_end']
    assert report['contract_discrepancies'] == []
    refs = helpers.audit_references(ROOT, NATIVE_DIR, report)
    refs[str(path.resolve())] = NATIVE_SHA
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    assert cc.digest(report['oracle']['library']) == report['oracle']['library_sha256']
    static = json.loads((NATIVE_DIR / 'source.json').read_text())
    assert static['source'] == source
    assert tuple(report['close_block_starts']) == BLOCK_STARTS
    assert tuple(static['boundary_stop_pcs']) == tuple(report['boundary_stop_pcs']) == (A698, )
    assert tuple(tuple(r) for r in static['close_ranges']) == tuple(tuple(r) for r in report['new_ranges']) == (
        (0x9e94, 0x9ee6), (0xa2be, 0xa348), (0xa662, 0xa698), (0xc2c8, 0xc2fa))
    assert sorted(tuple(r) for r in report['new_ranges']) == sorted(CLOSE_RANGES)
    covered = set(report['covered_PCs'])
    assert set(BLOCK_STARTS) <= covered, [hex(p) for p in BLOCK_STARTS if p not in covered]
    assert (report['cases'], report['guarded_cases']) == (71, 11) and len(report['condition_table']) == 82
    assert (report['total_split_phases'], report['total_control_phases']) == (20072, 588)
    assert report['fresh_CPU_runs'] == 503 and report['chain_vs_fresh_phases_compared'] == 812
    assert report['close_summary']['frames'] == 27 and report['close_summary']['final_stop_pc'] == '0x2ac2'
    assert len(report['declared_register_changes_at_step_boundaries']) == 13
    instructions = collect_instructions(program, static)
    close_instructions = {i['cpu_address']: i for i in static['instructions']}
    assert len(close_instructions) == 96 and set(BLOCK_STARTS) <= close_instructions.keys()
    assert all(in_ranges(pc, CLOSE_RANGES) for pc in close_instructions)
    assert A698 not in instructions or not in_ranges(A698, CLOSE_RANGES)
    rows = report['results'] + report['guarded_results']
    for row in rows:
        assert row['reproduced_twice'] and row['continuous_split_equivalent']
        assert bool(row['guarded']) == (row['group'] == 'guard')
    # Contract carry-preserving list == derived from source opcodes == C++ case list; a344 deliberately Unknown.
    derived = derived_preserving(close_instructions)
    assert derived == sorted(CARRY_PRESERVING) == cpp_preserving_cases_close(), (derived, cpp_preserving_cases_close())
    return report, static, rows, refs, instructions, close_instructions


def cpp_preserving_cases_close():
    text = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    section = text.split('// Card menu close blocks')[1].split('// Card menu save blocks')[0].split('// BTST/BEQ')[0]
    close_section = section.split('\n')
    cases = []
    for line in close_section:
        if line.strip().startswith('case '):
            cases += [int(x, 16) for x in re.findall(r'case 0x([0-9a-f]+):', line)]
    return sorted(cases)


def audit_row(program, row, instructions):
    """Per-row native consistency (loaded phases): trace/ports/reads/split-control + executed PCs known to the source tables."""
    fx = row['fixture']
    counts_total = dict(fixed_reads=0, bank_reads=0, PVC_writes=0)
    for kind in ('phases', 'continuous_control'):
        counts = cc.audit_program_reads(program, fx, row[kind])
        if kind == 'phases':
            for key, value in counts.items():
                counts_total[key] += value
    cc.audit_split_control(row)
    for phase in row['phases'] + row['continuous_control']:
        assert phase['carry'] is None and not phase['branch_evidence']
        assert phase['counts']['external_reads'] == sum(e['region'] == 'external' for e in phase['_trace']['events'])
        ports = [e for e in phase['_trace']['events'] if e['region'] in ('pvc', 'video', 'watchdog')]
        assert phase['_data']['ports.bin'] == b''.join(
            cc.struct.pack('>BII', e['size'], e['address'], int(e['bytes'], 16)) for e in ports)
        executed = phase['_trace']['pcs'][:-1]
        assert A698 not in executed
        for pc in executed:
            if pc not in instructions:      # not in any native source table: ROM disassembly (bytes are the ROM's own)
                instructions[pc] = disassemble_range(program, pc, 2, pc)[0]
                assert instructions[pc]['classification'] == 'candidate_instruction', hex(pc)
    return counts_total


def bios_row_start(row0, bios_start):
    """BIOS-row start (the card-child chain verifier rule): previous actual C++ BIOS-stop output + the fixture registers."""
    fx = row0['fixture']
    native_pvc = row0['phases'][0]['_data']['pvc_before.bin']
    assert sha(native_pvc) == fx['initial_PVC_sha256']
    key, (ram, src_state, pvc, bank) = bios_start
    state = dict({k: v for k, v in fx['initial_regs'].items() if k != 'a7'}, a7=fx['initial_a7'], pc=fx['entry_pc'], carry=0)
    assert fx['entry_pc'] == cc.BIOS
    assert sha(ram) == fx['initial_RAM_sha256'] and sha(cc.masked_pvc(pvc)) == sha(cc.masked_pvc(native_pvc))
    assert bank == fx['bank_state'][0]
    assert {k: src_state[k] for k in cc.STATE_NO_CARRY} == {k: state[k] for k in cc.STATE_NO_CARRY}
    return ram, state, pvc, bank


def replay_prefix(exe, program, resources, bios_start, input_report):
    """Re-run input-observation chain steps 0..330 in actual C++ (full RAM/16R/PC/PVC/bank/ports/reads per split phase)."""
    row = next(r for r in input_report['results'] if r['group'] == 'chain')
    assert row['label'] == 'chain-full-bios-resume-to-input'
    phases = [p for p in row['phases'] if p['step'] <= PREFIX_LAST_STEP]
    load_phase(INPUT_DIR, row['phases'][0])
    ram, state, pvc, bank = bios_row_start(row, bios_start)
    expected_pvc, expected_bank = pvc, bank
    fx = row['fixture']
    ends = {}
    totals = dict(phases=0, ports=0, reads=0, resumes=0, host_changes=0)
    for j, phase in enumerate(phases):
        if '_data' not in phase:
            load_phase(INPUT_DIR, phase)
        data = phase['_data']
        entry = dict(pc=state['pc'], a7=state['a7'])
        ram, state, kinds = apply_changes(ram, state, phase['host_changes'], entry)
        totals['host_changes'] += len(kinds)
        assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming'], j
        assert ram == data['ram_before.bin'] and bank == phase['bank_before'], j
        events = phase['_trace']['events']
        expected_pvc, expected_bank, portbytes = cc.fold_outputs(expected_pvc, expected_bank, events)
        assert expected_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
        actual = common.invoke(exe, OUT / 'prefix', 'p%05d' % j, ram, state, pvc, bank, resources,
                               stop=phase['stop_pc'], external=fx['external'])
        assert actual[0]['ok'] and not actual[4] and actual[0]['status'] == 0, (j, phase['stop_pc'], actual[4])
        common.check_result(actual, dict(outgoing=phase['outgoing'], events=events, ram_after=data['ram_after.bin']),
                            expected_pvc, expected_bank, portbytes)
        result, ram, pvc, _, _ = actual
        state = {k: result[k] for k in common.STATE_KEYS}
        bank = result['bank_base']
        totals['phases'] += 1
        totals['ports'] += len(portbytes) // 9
        totals['reads'] += result['external_reads']
        totals['resumes'] += j > 0
        ends[phase['step']] = (ram, dict(state), pvc, bank)
        for key in ('_data', '_trace'):
            phase.pop(key)
        for snapshot in phase['snapshots']:
            snapshot.pop('_ram', None)
            snapshot.pop('_pvc', None)
    assert phases[-1]['step'] == PREFIX_LAST_STEP and phases[-1]['outgoing']['pc'] == 0x2ac2
    return ends, totals


def fresh_start(row, prefix_end, chain_ends):
    """Start of a close row: the actual C++ output named by its provenance (+ declared A6/A7 only where recorded)."""
    fx = row['fixture']
    label = row['label']
    if row['group'] == 'chain':
        source, origin = prefix_end, 'actual C++ prefix output (input chain step %d, stop 2ac2)' % PREFIX_LAST_STEP
        native_ram = row['phases'][0]['_data']['ram_before.bin']
        assert source[0] == native_ram
        return source[0], dict(source[1]), source[2], source[3], origin, []
    match = re.search(r'close (?:chain )?frame (\d+)\b', row['provenance'])
    if match:
        n = int(match.group(1))
        source = prefix_end if n == 0 else chain_ends[PREFIX_LAST_STEP + n]
        origin = 'actual C++ output of the chain close frame %d (step %d)' % (n, PREFIX_LAST_STEP + n)
    else:
        assert 'input-unit final output' in row['provenance'], label
        source, origin = prefix_end, 'actual C++ prefix output (input chain step %d, stop 2ac2)' % PREFIX_LAST_STEP
    ram, base, pvc, bank = source
    native_pvc = row['phases'][0]['_data']['pvc_before.bin']
    assert sha(native_pvc) == fx['initial_PVC_sha256']
    assert sha(ram) == fx['initial_RAM_sha256'] and fx['entry_pc'] == base['pc'] == 0x2ac2, label
    state = dict(base)
    declared = []
    for key in cc.STATE_NO_CARRY:
        want = fx['initial_a7'] if key == 'a7' else (fx['entry_pc'] if key == 'pc' else fx['initial_regs'][key])
        if state[key] != want:
            if key == 'a7':
                assert 'declared' in row['provenance'] and ('A7' in row['provenance'] or 'direct entry' in row['provenance']), (label, 'a7')
            else:
                assert key == 'a6' and label == 'guard-odd-A6-child' and 'initial A6' in row['provenance'], (label, key)
            state[key] = want
            declared.append(key)
    want_bank, ff8, ff9 = fx['bank_state']
    assert bank == want_bank and bytes(pvc[0x1ff0:0x1ff4]) == ff8.to_bytes(2, 'big') + ff9.to_bytes(2, 'big'), label
    assert sha(cc.masked_pvc(pvc)) == sha(cc.masked_pvc(native_pvc))
    return ram, state, pvc, bank, origin + (' plus declared %s' % ','.join(declared) if declared else ''), declared


def frame_check(frames, steps, step_ram, step_end, step_ports, step_a6):
    """Per-frame C++ evidence vs the native close_frames record (ordered ports hash, record fields, outgoing registers)."""
    assert len(frames) == len(steps) == 27
    out = []
    for frame, step in zip(frames, steps):
        ports = step_ports[step]
        assert frame['step'] == step
        assert sha(ports) == frame['ordered_ports_sha256'], step
        entries = [(ports[i], int.from_bytes(ports[i + 1:i + 5], 'big'), int.from_bytes(ports[i + 5:i + 9], 'big'))
                   for i in range(0, len(ports), 9)]
        video = [e for e in entries if e[1] in (0x3c0000, 0x3c0004)]
        assert len(entries) == frame['ordered_port_writes']
        assert sum(e[0] == 4 for e in video) == frame['video_long_writes']
        assert sum(e[0] == 2 for e in video) == frame['video_word_writes']
        ram0, (ram1, state1) = step_ram[step], step_end[step][:2]
        assert cc.rd(ram0, RECORD + 4, 2) == frame['word4_record_107efe_before']
        assert cc.rd(ram1, RECORD + 4, 2) == frame['word4_record_107efe_after']
        assert hex(cc.rd(ram1, F2, 4)) == frame['f2_after'] and hex(cc.rd(ram1, EE, 4)) == frame['ee_after']
        assert cc.rd(ram1, E5, 1) == frame['e5_after']
        assert hex(cc.rd(ram0, step_a6[step], 4)) == frame['child_callback_before']
        assert hex(cc.rd(ram1, step_a6[step], 4)) == frame['child_callback_after']
        assert cc.rd(ram0, step_a6[step] + 0x7e, 2) == frame['child_7e_before']
        assert cc.rd(ram1, step_a6[step] + 0x7e, 2) == frame['child_7e_after']
        assert (hex(state1['pc']), hex(state1['a6']), hex(state1['a7'])) == (
            frame['outgoing_pc'], frame['outgoing_a6'], frame['outgoing_a7'])
        out.append(dict(step=step, label=frame['label'], word4=[frame['word4_record_107efe_before'],
                                                               frame['word4_record_107efe_after']],
                        ports=len(entries), ordered_ports_sha256=frame['ordered_ports_sha256'], C_plus_plus_equal=True))
    return out


def compare(exe, rows, report, resources, instructions, close_instructions, program, prefix_end, ranges):
    cpp_out, out_rows, guards, chain_ends = {}, [], [], {}
    totals = dict(cases=0, split=0, control=0, resumes=0, ports=0, reads=0, carry_checks=0, carry_probes=0,
                  carry_probe_preserved=0, declared_register_rows=0, declared_register_changes=0,
                  declared_host_changes=dict(ram=0, pc=0, a7_add=0, reg=0), cleanup_fixture_writes=0)
    program_reads = dict(fixed_reads=0, bank_reads=0, PVC_writes=0)
    carry_histogram = {0: 0, 1: 0, 2: 0}
    single_block = {}
    a698_starts = []
    registers_seen = []
    chain_info = {}
    ordered = sorted(rows, key=lambda r: r['index'])
    for row in ordered:
        fx = row['fixture']
        load_row(row)
        for key, value in audit_row(program, row, instructions).items():
            program_reads[key] += value
        ram, state, pvc, bank, origin, declared = fresh_start(row, prefix_end, chain_ends)
        if declared:
            totals['declared_register_rows'] += 1
        expected_pvc, expected_bank = pvc, bank
        a698_steps = set()
        for step in sorted({p['step'] for p in row['phases']}):
            last = [p for p in row['phases'] if p['step'] == step][-1]
            if last['guard'] is None and last['stop_pc'] == A698:
                a698_steps.add(step)
        results, step_starts, step_ports, step_ram, step_end = [], {}, {}, {}, {}
        for j, phase in enumerate(row['phases']):
            data = phase['_data']
            entry = dict(pc=state['pc'], a7=state['a7'])
            if phase['guard'] is not None:
                assert j == len(row['phases']) - 1 and row['guarded']
                ram, state2, kinds = apply_changes(ram, state, phase['host_changes'], entry)
                assert ram == data['ram_before.bin']
                guards.append((row, phase, ram, state2, pvc, bank))
                break
            changes_seen = []
            ram, state, kinds = apply_changes(ram, state, phase['host_changes'], entry, changes_seen)
            for change in changes_seen:
                registers_seen.append((row['label'], row['steps'][phase['step']]['label'], change['name'], change['value']))
                totals['declared_register_changes'] += 1
            for kind in kinds:
                totals['declared_host_changes'][kind] += 1
            for change in phase['host_changes']:
                if change['kind'] == 'ram' and ('cleanup fixture' in change['why'] or 'dispatcher base A7' in change['why']):
                    # cleanup fixture RAM of the object released by 2a00: only in the step that reaches 299c
                    control = [c for c in row['continuous_control'] if c['step'] == phase['step']][0]
                    assert 0x299c in control['_trace']['pcs'], (row['label'], phase['step'])
                    if 'dispatcher base A7' in change['why']:
                        assert change['address'] == 0x104ca4 and change['value'] == entry['a7'], change
                    totals['cleanup_fixture_writes'] += 1
            assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming'], (row['label'], j)
            assert ram == data['ram_before.bin'], (row['label'], j)
            assert (bank, ) == (phase['bank_before'], ) and kinds == [c['kind'] for c in phase['host_changes']]
            if phase['phase_in_step'] == 0:
                step_starts[phase['step']] = (ram, dict(state), pvc, bank, expected_pvc, expected_bank)
                step_ram[phase['step']] = ram
                if phase['step'] in a698_steps:
                    a698_starts.append((row['label'], phase['step'], (ram, dict(state), pvc, bank)))
            events = phase['_trace']['events']
            expected_pvc, expected_bank, portbytes = cc.fold_outputs(expected_pvc, expected_bank, events)
            assert expected_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
            phase_in, phase_pvc, phase_bank = dict(state), pvc, bank
            actual = common.invoke(exe, OUT, 'c%03d_split_%03d' % (row['index'], j), ram, state,
                                   pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
            assert actual[0]['ok'] and not actual[4], (row['label'], j, hex(phase['stop_pc']), actual[4])
            common.check_result(actual, dict(outgoing=phase['outgoing'], events=events,
                                             ram_after=data['ram_after.bin']),
                                expected_pvc, expected_bank, portbytes)
            assert actual[0]['status'] == 0
            result, ram, pvc, _, _ = actual
            step_ports[phase['step']] = step_ports.get(phase['step'], b'') + actual[3]
            executed = phase['_trace']['pcs'][:-1]
            want_carry = classify_carry(instructions, state['carry'], executed)
            assert carry_equal(result['carry'], want_carry), (row['label'], j, hex(phase['outgoing']['pc']), result['carry'], want_carry)
            carry_histogram[result['carry']] += 1
            # Carry probes: the same phase with a known incoming C gives exactly the source classification and otherwise
            # identical outputs. A phase that begins at the a324 BCS consumes the incoming C (probed separately).
            probed = bool(executed) and executed[0] not in CALLER_BCS and all(in_ranges(pc, ranges) for pc in executed)
            for probe in (1, 2) if probed else ():
                again = common.invoke(exe, OUT, 'c%03d_carry%d_%03d' % (row['index'], probe, j), data['ram_before.bin'],
                                      dict(phase_in, carry=probe), phase_pvc, phase_bank, resources,
                                      stop=phase['stop_pc'], external=fx['external'])
                assert again[0]['ok'] and not again[4], (row['label'], j, probe, hex(executed[0]), again[4])
                assert carry_equal(again[0]['carry'], classify_carry(instructions, probe, executed)), (row['label'], j, probe)
                assert ({k: v for k, v in again[0].items() if k != 'carry'} ==
                        {k: v for k, v in result.items() if k != 'carry'})
                assert again[1] == ram and again[2] == pvc and again[3] == actual[3]
                totals['carry_probes'] += 1
                if executed[0] in BLOCK_SET and executed == block_walk(close_instructions, executed[0]):
                    single_block[executed[0]] = single_block.get(executed[0], set()) | {again[0]['carry'] == probe}
                totals['carry_probe_preserved'] += again[0]['carry'] == probe
            totals['carry_checks'] += 1
            state = {k: result[k] for k in common.STATE_KEYS}
            bank = result['bank_base']
            totals['reads'] += result['external_reads']
            totals['ports'] += len(actual[3]) // 9
            if j:
                totals['resumes'] += 1
            results.append(dict(step=phase['step'], label=phase['label'], stop_pc=phase['stop_pc'],
                                carry=cc.CARRY_NAME[result['carry']], actual_previous_outputs_used=bool(j),
                                full_RAM_16R_PC_PVC_bank_ports_status_reads_equal=True))
            step_end[phase['step']] = (ram, dict(state), pvc, bank)
            cpp_out[(row['index'], j)] = (ram, dict(state), pvc, bank) if row['compared_with_chain'] or row['group'] == 'chain' else None
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
            assert (actual[1], {k: actual[0][k] for k in common.STATE_KEYS}, actual[2], actual[0]['bank_base']) == step_end[step]
            control_rows += 1
        if row['group'] == 'chain':
            chain_ends.update(step_end)
            chain_info = dict(row=row, a6={k: v[1]['a6'] for k, v in step_starts.items()}, ram=step_ram, ends=step_end, ports=step_ports)
        totals['cases'] += 1
        totals['split'] += len(results)
        totals['control'] += control_rows
        digest = sha(json.dumps(results, sort_keys=True).encode())
        out_rows.append(dict(index=row['index'], label=row['label'], group=row['group'], origin=origin,
                             declared_initial=declared, split_phases=len(results), control_steps=control_rows,
                             phases_sha256=digest, last=results[-1] if results else None))
        row['_results'] = results
        # keep the (small) native identities needed for the chain-vs-fresh comparison, drop the payloads
        row['_identity'] = [(sha(p['_data']['ram_after.bin']), sha(p['_data']['pvc_after.bin']),
                             tuple(sorted(p['outgoing'].items()))) for p in row['phases'] if p['guard'] is None]
        release_row(row)
    # declared register changes: exactly the recorded list (condition, step label, change)
    recorded = sorted((e['condition'], e['step'], e['change']['name'], e['change']['value'])
                      for e in report['declared_register_changes_at_step_boundaries'])
    assert sorted(registers_seen) == recorded, (sorted(registers_seen), recorded)
    totals['declared_host_changes_recorded_register_list_equal'] = True
    # chain-vs-fresh identity (connected + fresh-frame rows equal the chain close frames in actual C++)
    chain = chain_info['row']
    by_identity = {}
    for j, identity in enumerate(chain['_identity']):
        by_identity.setdefault(identity, []).append(cpp_out[(chain['index'], j)])
    strip = lambda e: (e[0], {k: v for k, v in e[1].items() if k != 'carry'}, e[2][:0x1ff0] + e[2][0x1ff4:], e[3])
    chain_matches, matched_rows = 0, 0
    for row in ordered:
        if not row['compared_with_chain'] or row is chain:
            continue
        matched_rows += 1
        for j, identity in enumerate(row['_identity']):
            assert identity in by_identity, (row['label'], 'phase not in chain', j)
            assert strip(cpp_out[(row['index'], j)]) == strip(by_identity[identity][0]), (row['label'], j)
            chain_matches += 1
    assert chain_matches == report['chain_vs_fresh_phases_compared']
    totals['fresh_vs_chain_C++_phases_equal'] = chain_matches
    totals['fresh_rows_compared_with_chain'] = matched_rows
    steps = sorted(chain_info['ends'])
    assert steps == list(range(CHAIN_FIRST_STEP, CHAIN_FIRST_STEP + 27))
    step_ram = dict(chain_info['ram'])
    frames = frame_check(report['close_frames'][chain['label']], steps, step_ram, chain_info['ends'], chain_info['ports'], chain_info['a6'])
    # Contract carry-preserving blocks observed as single-block phases with a known incoming C vs the source derivation.
    for pc, outcomes in single_block.items():
        walk = block_walk(close_instructions, pc)
        assert outcomes == {cc.classify_carry(close_instructions, probe, walk) == probe for probe in (1, 2)}, (hex(pc), outcomes)
        assert (outcomes == {True}) == (pc in CARRY_PRESERVING), (hex(pc), outcomes)
    totals['single_block_carry_starts_checked'] = sorted(hex(pc) for pc in single_block)
    totals['carry_preserving_starts_observed'] = sorted(hex(pc) for pc in single_block if pc in CARRY_PRESERVING)
    totals['carry_histogram'] = {cc.CARRY_NAME[k]: v for k, v in carry_histogram.items()}
    return out_rows, totals, guards, a698_starts, frames, program_reads, registers_seen


# a698 and the lower nested helpers (a6da..) are executed by the nested core now: these native guards (stopped where no
# executor existed) are recorded with the observed C++ outcome, not counted as negatives.
SUPERSEDED_GUARDS = ('guard-a698-without-stop', 'guard-a6da-lower-reaches-zero')
GUARD_ERRORS = {
    'guard-cleanup-without-fixture': 'animation cleanup original TRAP15: coordinate index',
    'guard-odd-f2-shrink': EVEN, 'guard-odd-ee-direct-a2be': EVEN, 'guard-odd-A7-reentry': EVEN,
    'guard-odd-A7-direct-a2d6': EVEN, 'guard-odd-A7-direct-a306': EVEN, 'guard-odd-A6-child': EVEN,
    'guard-parent-ptr-rom0': 'unsupported animation machine write device',
    'guard-parent-ptr-bank': 'unsupported animation machine write device'}


def compare_guards(exe, guards, resources, guard_errors):
    rows = []
    superseded = []
    for row, phase, ram, state, pvc, bank in guards:
        result, outgoing, out_pvc, ports, error = common.invoke(
            exe, OUT, 'guard_%s' % row['label'], ram, dict(state, carry=2), pvc, bank, resources,
            stop=phase['stop_pc'], external=row['fixture']['external'])
        if row['label'] in SUPERSEDED_GUARDS:
            if not result['ok']:
                assert {k: result[k] for k in common.STATE_KEYS} == dict(state, carry=2) and outgoing == ram
            superseded.append(dict(label=row['label'], native_guard=phase['guard'], CPP_now_ok=result['ok'],
                                   CPP_now_error=error.strip(), CPP_now_pc=hex(result['pc'])))
            continue
        assert not result['ok'], (row['label'], 'C++ accepted the native guard input', hex(result['pc']))
        assert error.strip() == guard_errors[row['label']], (row['label'], error.strip())
        assert {k: result[k] for k in common.STATE_KEYS} == dict(state, carry=2)
        assert outgoing == ram and out_pvc == pvc and result['bank_base'] == bank
        assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1
        rows.append(dict(label=row['label'], native_guard=phase['guard'], checked_API_error=error.strip(),
                         all_API_outputs_preserved=True, native_fault_rollback_equivalence_claimed=False))
    return rows, superseded


def expected_pc_error(close_instructions, pc):
    """Dispatch model: an instruction address inside the close router range that is not a contract block start is refused by the
    close core; every other address (a698 included) has no executor in the machine."""
    if in_ranges(pc, tuple((low, high + 1) for low, high in ROUTER_RANGES)) and pc not in BLOCK_SET:
        return UNSUPPORTED_CLOSE
    return UNSUPPORTED_MACHINE


DEVICE_ADDR = 'unsupported program bus device address'
SUPERSEDED_DIRECT_PCS = (0x1a73c,)
SUPERSEDED_RECORDS = []


def negatives(exe, base, a698_starts, close_instructions, resources):
    out = []

    def reject(label, start, changes=None, stop=0xff000, external=0, expected=None, carry=2):
        r, s, p, b = start
        s = dict(s, carry=carry)
        s.update(changes or {})
        result, outgoing, out_pvc, ports, error = common.invoke(
            exe, OUT, 'negative_' + label, r, s, p, b, resources, stop=stop, external=external)
        assert not result['ok'], label
        assert error.strip() == expected, (label, error.strip(), expected)
        assert {k: result[k] for k in common.STATE_KEYS} == s
        assert outgoing == r and out_pvc == p and ports == MARKER and result['bank_base'] == b
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        out.append(dict(label=label, error=error.strip(), all_API_outputs_preserved=True,
                        native_exception_rollback_equivalence_claimed=False))

    interior = sorted(pc for pc in close_instructions if pc not in BLOCK_SET)
    assert len(interior) == 65
    for pc in interior:
        assert expected_pc_error(close_instructions, pc) == UNSUPPORTED_CLOSE
        reject('interior_direct_entry_%06x' % pc, base, {'pc': pc}, expected=UNSUPPORTED_CLOSE)
    # a698/a69a/a6da are executed by the nested core now (superseded as unsupported-PC negatives); these still have none.
    for pc in (0xa63c, 0xe84d6, 0xc00468, 0xc0046e):
        reject('boundary_direct_entry_%06x' % pc, base, {'pc': pc}, expected=UNSUPPORTED_MACHINE)
    # 1a73c is routed by the scene core (U2) now: a direct entry runs its code and ends with a state-dependent bus error (device address) instead of an
    # unsupported-PC rollback. Checked as a failure with the observed error; former and observed errors are recorded (superseded, not deleted).
    for pc in SUPERSEDED_DIRECT_PCS:
        reject('boundary_direct_entry_%06x' % pc, base, {'pc': pc}, expected=DEVICE_ADDR)
        SUPERSEDED_RECORDS.append(dict(label='boundary_direct_entry_%06x' % pc, former_expected_API_error=UNSUPPORTED_MACHINE,
                                       observed_error=DEVICE_ADDR, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False))
    outside = (0x9ee6, 0xc2fa, 0xc2fc)
    for pc in outside:
        assert expected_pc_error(close_instructions, pc) == UNSUPPORTED_MACHINE
        reject('outside_range_entry_%06x' % pc, base, {'pc': pc}, expected=UNSUPPORTED_MACHINE)
    # a698 reached from the native nested rows' step start with any other stop: full rollback; positive control with stop a698.
    assert a698_starts
    for label, step, start in a698_starts:
        # reached with any other stop: a698 is executed by the nested core now, so no unsupported-PC rollback (superseded)
        r, s, p, b = start
        result, _, _, _, error = common.invoke(exe, OUT, 'control_a698_%s_%d' % (label, step), r, dict(s, carry=2), p, b,
                                               resources, stop=A698)
        assert result['ok'] and not error and result['pc'] == A698 and result['status'] == 0, (label, error)
    # a324 BCS with an Unknown carry: checked error and full rollback
    reject('unknown_carry_entry_%06x' % A324, base, {'pc': A324}, expected=NEEDS_CARRY, carry=0)
    return out, len(interior), len(outside)


def bcs_known_carry_controls(exe, base, resources):
    """Known C at a324 moves PC to a328 (Clear) / a332 (Set) without touching anything else; the carry is kept."""
    ram, state, pvc, bank = base
    rows = []
    for carry, target in ((1, A328), (2, A332)):
        s = dict(state, pc=A324, carry=carry)
        result, out_ram, out_pvc, ports, error = common.invoke(exe, OUT, 'bcs_a324_carry%d' % carry, ram, s, pvc, bank,
                                                               resources, stop=target)
        assert result['ok'] and not error and result['pc'] == target and result['status'] == 0, (carry, error)
        assert {k: result[k] for k in common.STATE_KEYS if k != 'pc'} == {k: s[k] for k in common.STATE_KEYS if k != 'pc'}
        assert out_ram == ram and out_pvc == pvc and not ports and result['external_reads'] == 0
        rows.append(dict(carry=cc.CARRY_NAME[carry], target=hex(target), carry_preserved=True))
    return rows


def zero_step(exe, base, resources):
    ram, state, pvc, bank = base
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


def boundary_zero_step(exe, base, resources):
    """stop == entry PC at the a698 boundary: recorded as observed behavior (not required by the contract)."""
    ram, state, pvc, bank = base
    s = dict(state, pc=A698, carry=2)
    result, out_ram, out_pvc, ports, error = common.invoke(exe, OUT, 'zero_boundary_%06x' % A698, ram, s, pvc, bank,
                                                           resources, stop=A698)
    assert {k: result[k] for k in common.STATE_KEYS} == s and out_ram == ram and out_pvc == pvc
    return [dict(pc=A698, ok=result['ok'], error=error.strip())]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'prefix').mkdir(exist_ok=True)
    report_path = OUT / 'verification.json'
    report_path.unlink(missing_ok=True)
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_card_menu_close.py', 'tools/verify_animation_machine_card_child.py',
                 'tools/observe_animation_machine_card_menu_close.py', 'tools/observe_animation_machine_card_menu_input.py',
                 'docs/analysis/animation-machine-card-menu-close-contract.md',
                 'engine/src/animation_machine_card_menu_close.cpp', 'engine/tests/animation_machine_card_menu_close_test.cpp'):
        inputs[name] = cc.digest(ROOT / name)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = cc.digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = cc.digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    exe, command = helpers.compile_harness(ROOT, OUT)
    report, static, rows, native_refs, instructions, close_instructions = audit_static(program, source)
    refs.update(native_refs)
    # Prefix: the input observation (hash pinned, tool pinned and equal to the close observation's crosscheck reference).
    input_path = INPUT_DIR / 'observation.json'
    assert cc.digest(input_path) == INPUT_SHA and cc.digest(ROOT / 'tools/observe_animation_machine_card_menu_input.py') == INPUT_TOOL_SHA
    input_report = json.loads(input_path.read_text())
    assert input_report['tool_sha256'] == INPUT_TOOL_SHA and input_report['failure'] is None and input_report['source'] == source
    for key in ('original_program_modified', 'SR_read_at_any_phase', 'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert input_report[key] is False
    check = report['card_menu_input_crosscheck']
    assert check['reference_report_sha256'] == INPUT_SHA and check['reference_tool_sha256'] == INPUT_TOOL_SHA and check['equal']
    refs.update(helpers.audit_references(ROOT, INPUT_DIR, input_report))
    refs[str(input_path.resolve())] = INPUT_SHA
    cc.OUT = OUT / 'card_child_chain'
    cc.OUT.mkdir(parents=True, exist_ok=True)
    bios_start = cc.fade_chain_bios_output(exe, program, source, resources)
    prefix_ends, prefix_totals = replay_prefix(exe, program, resources, bios_start, input_report)
    prefix_checks = []
    for name, step in PREFIX_CHECKS:
        want = report[name]
        assert want['equal'] if 'equal' in want else True
        ram, state = prefix_ends[step][:2]
        assert sha(ram) == (want['ram_after_sha256'] if 'ram_after_sha256' in want else want['final_ram_after_sha256']), name
        assert want['step' if 'step' in want else 'final_step'] == step
        assert hex(state['pc']) == (want['outgoing_pc'] if 'outgoing_pc' in want else want['final_outgoing_pc']), name
        # the crosscheck's PVC hash is the raw native image (ff8/ff9 raw words); the masked device PVC is compared per phase
        prefix_checks.append(dict(crosscheck=name, step=step, ram_sha256=sha(ram), pc=hex(state['pc']), C_plus_plus_equal=True))
    prefix_end = prefix_ends[PREFIX_LAST_STEP]
    del prefix_ends
    ranges = tuple(tuple(r) for r in static['ranges'])
    matches, totals, guards, a698_starts, frames, program_reads, registers_seen = compare(
        exe, rows, report, resources, instructions, close_instructions, program, prefix_end, ranges)
    guarded, guards_superseded = compare_guards(exe, guards, resources, GUARD_ERRORS)
    assert len(guarded) + len(guards_superseded) == 11 and len(guards_superseded) == 2
    base = prefix_end
    negative, interior_count, outside_count = negatives(exe, base, a698_starts, close_instructions, resources)
    bcs = bcs_known_carry_controls(exe, base, resources)
    zero = zero_step(exe, base, resources)
    assert len(zero) == 93
    boundary_zero = boundary_zero_step(exe, base, resources)
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
                  contract_sha256=CONTRACT_SHA, input_observation_sha256=INPUT_SHA, input_tool_sha256=INPUT_TOOL_SHA,
                  actual_CPP=dict(totals, matches=matches),
                  prefix_chain_actual_CPP=dict(prefix_totals, crosschecks=prefix_checks),
                  close_frames=frames,
                  original_program_read_audit=program_reads,
                  native_guards_checked_API=guarded, native_guards_superseded_by_nested_core=guards_superseded,
                  negatives_superseded_by_scene_core_routing=SUPERSEDED_RECORDS,
                  negatives_superseded_by_nested_core=['boundary_direct_entry_a698', 'outside_range_entry_a69a', 'outside_range_entry_a6da', 'a698_reached_via_*_with_other_stops'],
                  declared_register_changes_asserted_against_record=[list(x) for x in registers_seen],
                  negatives=negative, negative_count=len(negative) + len(guarded),
                  interior_PCs_rejected=interior_count, outside_range_entries_rejected=outside_count,
                  a324_known_carry_controls=bcs, zero_step=zero, boundary_zero_step=boundary_zero,
                  carry_preserving_blocks=dict(contract=[hex(p) for p in CARRY_PRESERVING],
                                               derived_from_source_opcodes=[hex(p) for p in derived_preserving(close_instructions)],
                                               a344_unknown=True),
                  carry_check='C++ carry equals source-opcode walk over native-executed PCs (ORI/ANDI CCR known, flow-only preserved, else Unknown); native SR never read',
                  normalized_reference_paths=len(unique), compile_command=command, failure=None, ROM_unchanged=True,
                  limits=['Controlled fixtures; frame re-entry is a declared PC-only change (plus the declared A6=parent register write at the parent re-entry step boundary), not a natural scheduler, IRQ or VBlank.',
                          'The cleanup fixture (1d/6c of the released object, LONG 104ca4 = dispatcher base A7) is a declared RAM fixture; without it 299c reaches TRAP #f (guard row).',
                          'Carry is a source-opcode classification (native SR is never read), not a native C measurement; ADDQ.W #2,A7 (a344) is deliberately Unknown.',
                          'a698 (nested menu return) is a stop boundary only, never executed; a6da, bd26 and later (save, parent/child successors) are out of scope.',
                          'The prefix (331 steps) is re-run in actual C++ from the actual C++ BIOS-stop output and compared with the input observation; declared A6/A7 fixture registers are inputs.',
                          'Native observation artifacts are audited by hash/trace consistency, not re-executed here.',
                          'Checked failures preserve API outputs, not original CPU fault rollback; interior direct entries have no native guard (API-only rejection).'])
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=totals['cases'], split=totals['split'], control=totals['control'],
                         resumes=totals['resumes'], negatives=result['negative_count'], interior=interior_count,
                         zero_step=len(zero), carry=totals['carry_histogram'], prefix=prefix_totals['phases'],
                         sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
