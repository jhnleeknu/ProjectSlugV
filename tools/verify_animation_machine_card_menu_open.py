"""Original card-menu opening frames (a370 -> a5d2/a348/9b58 -> a5ea first full draw, c1c4/bf94, c2c0) native evidence
vs the public machine API.

Controlled fixtures; no expected-register injection. The frozen native observation is an immutable input (this
verifier never invokes the observer main). C++ resumes only from the previous actual C++ output plus the host changes
and declared initial registers recorded in the native fixture. The BIOS-row start and the a370 stop output are the
actual C++ outputs of the reviewed fade/card, card-child and card-menu-push chains (re-run here); the fresh conditions
start from that a370 stop output plus their declared preparation. The boundary PCs 9e94 a2be a406 a662 a70a bd26 e84d6
a63c (TRAP #f) c2c8 and the hook targets are stop boundaries only: never executed.
"""
import json
from pathlib import Path
import re
import shutil
import sys
import verify_animation_machine as common
import verify_animation_machine_callers as helpers
import verify_animation_machine_card_child as cc
import verify_animation_machine_card_menu as cm
from disassemble_program import load_verified_program

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/animation_machine_card_menu_open_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_card_menu_open_native'
NATIVE_SHA = '154b4ed588a1bf7c9615bc7c6c3710492e4c0a711aca710b20f6bd21a7390ab4'
NATIVE_TOOL_SHA = '17dea0a98c5a8ca3aa34ccf7524d132872877774ffcfd39970037fa0f7d04316'
CONTRACT_SHA = '1eb6c80ebcbef6a2f8c6488c23342ee4a85dae1c0acbf9037ad3ccb280549c4b'
A370, A406, A662, A63C, C2C0, C2C8, B9B58 = 0xa370, 0xa406, 0xa662, 0xa63c, 0xc2c0, 0xc2c8, 0x9b58
MARKER = cc.MARKER
PUSH_CHAIN_LABEL, PUSH_CHAIN_STEP = 'chain-full-bios-resume-to-a370', 25
OPEN_CHAIN_LABEL, OPEN_FIRST_STEP = 'chain-full-bios-resume-to-open', 26
OPEN_BLOCK_TEXT = '''3650 3918 391a 391e 3926 3928 392a 9b26 9b3e 9b42 9b54 9b56 9b58 9b64 9b66 9b78 9b7a 9b82 9b8a 9b8e 9ba6 9baa 9bbc 9bc0 9bc8 9bcc 9bd0 9be2 9be6 9bea 9bee 9c00 9c08 9c10 9c14 9c26 9c2a 9c32 9c36 9c3a 9c4c 9c50 9c54 9c58 9c6a 9c6e 9c76 9c7a 9c8c 9c90 9c98 9c9c 9ca0 9cb2 9cb6 9cba 9cbe 9cd0 9cd4 9cd8 9cdc 9cee 9cf0 9cf8 9cfc 9d00 9d12 9d16 9d1e 9d22 9d26 9d38 9d3a 9d4a 9d4c 9d86 9d92 9d96 9d9a 9da0 9dae 9db6 9dba 9dc0 9dc4 9dce 9dd6 9dda 9de8 9dea 9df2 9df6 9dfe 9e02 9e08 9e14 9e1a 9e26 9e28 9e34 9e3a 9e5e 9e66 9e6e 9e72 9e78 9e7a 9e82 9e8a 9e92 9f7c 9f84 9f90 9f96 9fac 9fb8 9fbe a008 a00c a010 a016 a018 a03a a040 a04a a058 a066 a06c a076 a216 a21e a22c a236 a238 a23c a242 a246 a252 a258 a262 a26e a278 a348 a350 a36a a36e a370 a380 a388 a396 a3a0 a3a8 a3ac a3b4 a3b8 a3c6 a3c8 a3d0 a3de a3e2 a3f2 a3fa a402 a5d2 a5e2 a5e6 a5ea a5f4 a5fe a606 a614 a616 a61c a624 a628 a63e a64c a65e a73e a74a a754 bf94 bf9a bfa2 bfa8 bfb0 bfbc c1c4 c1ca c1d2 c1de c1e6 c1ee c1f4 c1fe c202 c208 c212 e84c8 e84d0 c2c0 c2c6'''
BLOCK_STARTS = tuple(int(x, 16) for x in OPEN_BLOCK_TEXT.split())
BLOCK_SET = frozenset(BLOCK_STARTS)
assert len(BLOCK_STARTS) == len(BLOCK_SET) == 202
# a018 callers' BCS blocks (consume the C left by a06c Clear / a076 Set) incl. the a008 BSR a018 return a00c.
CALLER_BCS = (0x9ba6, 0x9bcc, 0x9bea, 0x9c10, 0x9c36, 0x9c54, 0x9c76, 0x9c9c, 0x9cba, 0x9cd8, 0x9cfc, 0x9d22,
              0x9dc0, 0x9dd6, 0xa00c)
# Contract boundaries (no executor): the stop-reachable ones plus 9f36/a6da/a71a (only reachable through boundaries).
# Boundaries of the frozen native open observation. Later card menu cores execute most of them now (input: a406 a70a;
# close: 9e94 a2be a662 c2c8; save: 9f36 a71a bd26; nested: a6da), so a direct entry there is no unsupported-PC
# negative any more (the errors depend on the entry register state); they stay stop-only boundaries of the native rows
# and their rollback negatives are superseded (positive stop controls remain). 9fc4 (end of an open range) is an input block.
BOUNDARY_PCS = (0x9e94, 0x9f36, 0xa2be, A406, A662, 0xa6da, 0xa70a, 0xa71a, 0xbd26, 0xe84d6, A63C)
EXECUTED_BOUNDARIES = (0x9e94, 0x9f36, 0xa2be, A406, A662, 0xa6da, 0xa70a, 0xa71a, 0xbd26)
EXECUTED_RANGE_ENDS = (0x9fc4,)
NEGATIVE_BOUNDARY_PCS = (0xe84d6, A63C, 0xc00468, 0xc0046e)      # c00468/c0046e BIOS: no executor anywhere
SUPERSEDED_DIRECT_PCS = (0x1a73c,)      # routed by the scene core (U2) now: state-dependent bus error instead of an unsupported-PC rollback
DEVICE_ADDR = 'unsupported program bus device address'
SUPERSEDED_RECORDS = []
STOP_BOUNDARIES = (0x9e94, 0xa2be, A406, A662, 0xa70a, 0xbd26, 0xe84d6, A63C, C2C8)
OPEN_RANGES = ((0x9b26, 0x9b58), (0x9b58, 0x9bbc), (0x9bbc, 0x9cd4), (0x9cd4, 0x9d3a), (0x9d3a, 0x9e1a), (0x9e1a, 0x9e94),
               (0x9f7c, 0x9fc4), (0xa008, 0xa080), (0xa216, 0xa280), (0xa348, 0xa370), (0xa370, 0xa3e2),
               (0xa3e2, 0xa406), (0xa5d2, 0xa662), (0xa73e, 0xa75a), (0xbf94, 0xbfbe), (0xc1c4, 0xc214),
               (0xc2c0, 0xc2c8), (0x3918, 0x392c), (0x3650, 0x3670), (0xe84c8, 0xe84d6))
MENU_RANGES = cm.MENU_RANGES + OPEN_RANGES
# Row preparation: which declared initial registers differ from the a370 stop output (assert exact, per label).
DECLARED_INITIAL = {'callback-c1c4-d0-3-bd26': dict(d0=3), 'callback-bf94-d0-3-a70a': dict(d0=3),
                    'callback-c1c4-d0-0-sound': dict(d0=0), 'callback-bf94-d0-0-sound': dict(d0=0),
                    'callback-c1c4-d0-5': dict(d0=5), 'guard-odd-A7': dict(a7=0x1feff9)}
DECLARED_BANK_LABEL = 'bank-300000-same-address'
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNSUPPORTED_OPEN = 'unsupported animation card menu open PC'
UNSUPPORTED_MENU = 'unsupported animation card menu PC'
NEEDS_CARRY = 'card menu caller requires known carry'
WRITE_DEVICE = 'unsupported animation machine write device'
EVEN = 'program bus requires even WORD/LONG address'
FLOW_ONLY = cc.FLOW_ONLY
END_MNEMONICS = ('bra', 'jmp', 'rts', 'bsr', 'jsr', 'beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls',
                 'bge', 'blt', 'bgt', 'ble', 'dbra', 'dbf')
COND_BRANCH = ('beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble')
# Native guards that stopped at a406 / c2c8 (no executor then): the input / close cores execute them now, so they are
# recorded (observed C++ outcome), not counted as negatives.
SUPERSEDED_GUARDS = ('guard-e5-0-without-stop', 'guard-e5-3-c2c8-without-stop')
GUARD_ERRORS = {
    'guard-odd-f2-A2': EVEN, 'guard-odd-ee-direct-a348': EVEN, 'guard-odd-descriptor-A3-a3ba': EVEN,
    'guard-odd-descriptor-A3-9b58': EVEN, 'guard-odd-A7': EVEN,
    'guard-a63c-without-stop': UNSUPPORTED_MACHINE, 'guard-d1-ge-10-without-stop': UNSUPPORTED_MACHINE}
# Rows whose last step ends at a boundary stop (native stop_pc) -> used for the other-stop rollback negatives.
BOUNDARY_ROWS = {0x9e94: 'desc-flags-0001-9e94', 0xa2be: 'loop-older-f-bit0-byte4-a2be', A406: 'state-e5-0-a406',
                 A662: 'state-e5-2-a662', 0xa70a: 'callback-bf94-d0-3-a70a', 0xbd26: 'callback-c1c4-d0-3-bd26',
                 0xe84d6: 'desc-e84c8-d1-0x10-item', A63C: 'desc-zero-items-a63c', C2C8: 'state-e5-03-a402-rts-ff',
                 0xfff00: 'hook-a4-nonzero-fff00'}      # hook target 9000 is code of another unit: native row only


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


def load_static(program, source):
    static = json.loads((NATIVE_DIR / 'source.json').read_text())
    assert static['source'] == source
    instructions = {}
    for instruction in static['instructions']:
        at, size = instruction['rom_offset'], instruction['size']
        assert bytes(bytearray.fromhex(instruction['raw'])) == program[at:at + size]
        instructions[instruction['cpu_address']] = instruction
    return static, instructions


def mnemonic(instructions, pc):
    return instructions[pc]['mnemonic'].split('.')[0]


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
    """Blocks whose every instruction is flow-only: C is kept. Computed from the source opcodes only."""
    return sorted(pc for pc in BLOCK_STARTS
                  if all(mnemonic(instructions, p) in FLOW_ONLY for p in block_walk(instructions, pc)))


def cpp_preserving_cases():
    """The carry-preserving list of the open section in animation_machine.cpp (text parse, compared to the derivation)."""
    text = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    section = text.split('// Card menu open blocks')[1].split('// Card menu input blocks')[0].split('// BTST/BEQ')[0]
    return sorted(int(x, 16) for x in re.findall(r'case 0x([0-9a-f]+):', section))


def in_ranges(pc, ranges):
    return any(low <= pc < high for low, high in ranges)


def audit_native(program, source):
    path = NATIVE_DIR / 'observation.json'
    assert cc.digest(path) == NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_card_menu_open.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'docs/analysis/animation-machine-card-menu-open-contract.md') == CONTRACT_SHA
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
    static, instructions = load_static(program, source)
    assert tuple(static['block_starts']) == BLOCK_STARTS == tuple(report['block_starts'])
    assert tuple(static['boundary_stop_pcs']) == tuple(report['boundary_stop_pcs']) == (
        0x9e94, 0xa2be, A406, A662, 0xa70a, 0xbd26, 0xe84d6, A63C, C2C8)
    assert tuple(sorted(tuple(r) for r in report['new_ranges'])) == tuple(sorted(OPEN_RANGES))
    assert tuple(tuple(r) for r in static['open_ranges']) == tuple(tuple(r) for r in report['new_ranges'])
    covered = set(report['covered_PCs'])
    unobserved = sorted(set(BLOCK_STARTS) - covered)
    # Fact (source): c1ee..c208 follow BSR bd26 (stop boundary, never executed); a3ac/a3b4 follow BSR a2be/a6da
    # (boundaries); 9b78 is the RTS after BEQ 9b7a/BNE 9e94 on the same flags and is structurally unreachable.
    assert unobserved == [0x9b78, 0xa3ac, 0xa3b4, 0xc1ee, 0xc1f4, 0xc1fe, 0xc202, 0xc208], [hex(p) for p in unobserved]
    for search in report['bank_descriptor_search']:
        assert search['terminating_descriptors_found'] == 0 and not search['candidates']
    rows = load_rows(report)
    assert len(rows) == report['cases'] + report['guarded_cases'] == 88
    assert (report['cases'], report['guarded_cases']) == (79, 9)
    assert len(report['condition_table']) == 88
    split_count = sum(len(r['phases']) for r in rows)
    control_count = sum(len(r['continuous_control']) for r in rows)
    assert (split_count, control_count) == (report['total_split_phases'], report['total_control_phases'])
    assert report['fresh_CPU_runs'] == 445
    program_reads = dict(fixed_reads=0, bank_reads=0, PVC_writes=0)
    never_executed = {0x9e94, 0xa2be, A406, A662, 0xa70a, 0xbd26, 0xe84d6, A63C}
    for row in rows:
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
            assert phase['counts']['external_reads'] == sum(e['region'] == 'external'
                                                          for e in phase['_trace']['events'])
            ports = [e for e in phase['_trace']['events'] if e['region'] in ('pvc', 'video', 'watchdog')]
            assert phase['_data']['ports.bin'] == b''.join(
                cc.struct.pack('>BII', e['size'], e['address'], int(e['bytes'], 16)) for e in ports)
            executed = set(phase['_trace']['pcs'][:-1])
            assert not (executed & never_executed), (row['label'], hex(min(executed & never_executed)))
            assert instructions.keys() >= executed
    return report, rows, refs, instructions, static, program_reads, control_count, unobserved


def fresh_start(row, push_end):
    """Fresh condition: actual C++ a370 stop output (push chain step 25) + the declared preparation of the fixture."""
    fx = row['fixture']
    native_pvc = row['phases'][0]['_data']['pvc_before.bin']
    assert sha(native_pvc) == fx['initial_PVC_sha256']
    ram, base, pvc, bank = push_end
    assert sha(ram) == fx['initial_RAM_sha256'] and fx['entry_pc'] == A370 and base['pc'] == A370
    state = dict(base)
    declared = []
    allowed = DECLARED_INITIAL.get(row['label'], {})
    for key in cc.STATE_NO_CARRY:
        want = fx['initial_a7'] if key == 'a7' else (fx['entry_pc'] if key == 'pc' else fx['initial_regs'][key])
        if state[key] != want:
            assert allowed.get(key) == want and 'declared' in row['provenance'], (row['label'], key, hex(want))
            state[key] = want
            declared.append(key)
    assert sorted(declared) == sorted(allowed), (row['label'], declared)
    want_bank, ff8, ff9 = fx['bank_state']
    pvc = bytearray(pvc)
    declared_bank = (bank, bytes(pvc[0x1ff0:0x1ff4])) != (want_bank, ff8.to_bytes(2, 'big') + ff9.to_bytes(2, 'big'))
    pvc[0x1ff0:0x1ff2] = ff8.to_bytes(2, 'big')
    pvc[0x1ff2:0x1ff4] = ff9.to_bytes(2, 'big')
    pvc, bank = bytes(pvc), want_bank
    if declared_bank:
        assert row['label'] == DECLARED_BANK_LABEL and 'declared bank state' in row['provenance']
        declared.append('bank_state')
    assert sha(cc.masked_pvc(pvc)) == sha(cc.masked_pvc(native_pvc))
    origin = ('actual C++ a370 stop output of the card menu push chain step %d plus declared %s'
              % (PUSH_CHAIN_STEP, ','.join(declared) or 'nothing'))
    return ram, state, pvc, bank, origin, declared


def frame_check(report, label, steps, step_ram, step_end, step_ports, offset):
    """Per-frame C++ evidence vs the native open_frames record (ordered ports hash, counts, record fields)."""
    frames = report['open_frames'][label]
    assert len(frames) == len(steps)
    out = []
    for frame, step in zip(frames, steps):
        ports = step_ports[step]
        assert frame['step'] == step + offset
        assert sha(ports) == frame['ordered_ports_sha256'], (label, step)
        entries = [(ports[i], int.from_bytes(ports[i + 1:i + 5], 'big'), int.from_bytes(ports[i + 5:i + 9], 'big'))
                   for i in range(0, len(ports), 9)]
        video = [e for e in entries if e[1] in (0x3c0000, 0x3c0004)]
        assert len(entries) == frame['ordered_port_writes']
        assert sum(e[0] == 4 for e in video) == frame['video_long_writes']
        assert sum(e[0] == 2 for e in video) == frame['video_word_writes']
        assert sum(e[0] == 2 and e[2] == 0x8200 for e in video) == frame['video_word_8200_writes']
        ram0, ram1, state1 = step_ram[step], step_end[step][0], step_end[step][1]
        record, child = 0x107efe, state1['a6']
        assert cc.rd(ram0, record + 4, 2) == frame['word4_before'] and cc.rd(ram1, record + 4, 2) == frame['word4_after']
        assert cc.rd(ram1, record + 7, 1) == frame['field_7_after'] and cc.rd(ram1, record + 8, 1) == frame['field_8_after']
        assert cc.rd(ram1, record + 0xe, 1) == frame['field_e_after']
        assert cc.rd(ram1, child + 0x7e, 2) == frame['child_7e_after'] and cc.rd(ram1, child + 0x80, 1) == frame['child_80_after']
        assert hex(state1['pc']) == frame['outgoing_pc'] and hex(state1['a7']) == frame['outgoing_a7']
        out.append(dict(step=frame['step'], label=frame['label'], word4=[frame['word4_before'], frame['word4_after']],
                        ports=len(entries), ordered_ports_sha256=frame['ordered_ports_sha256'],
                        C_plus_plus_equal=True))
    return out


def compare(exe, rows, resources, instructions, push_end, bios_start, preserving):
    cpp_out, out_rows, guards = {}, [], []
    totals = dict(cases=0, split=0, control=0, resumes=0, ports=0, reads=0, carry_checks=0, carry_probes=0,
                  carry_probe_preserved=0, declared_register_rows=0,
                  declared_host_changes=dict(ram=0, pc=0, a7_add=0))
    ends, starts, step_info = {}, {}, {}
    single_block = {}
    carry_histogram = {0: 0, 1: 0, 2: 0}
    for row in rows:
        fx = row['fixture']
        if fx['entry_pc'] == cc.BIOS:
            ram, state, pvc, bank, origin, declared = cm.start_of_row(row, None, bios_start)
        else:
            ram, state, pvc, bank, origin, declared = fresh_start(row, push_end)
        if declared:
            totals['declared_register_rows'] += 1
        expected_pvc, expected_bank = pvc, bank
        ends[(row['label'], -1)] = (ram, dict(state), pvc, bank)
        results, step_starts = [], {}
        step_ports, step_ram = {}, {}
        for j, phase in enumerate(row['phases']):
            data = phase['_data']
            entry = dict(pc=state['pc'], a7=state['a7'])
            if phase['guard'] is not None:
                assert j == len(row['phases']) - 1 and row['guarded']
                ram, state2, kinds = cm.apply_changes(ram, state, phase['host_changes'], entry)
                assert ram == data['ram_before.bin']
                guards.append((row, phase, ram, state2, pvc, bank, phase['step']))
                break
            ram, state, kinds = cm.apply_changes(ram, state, phase['host_changes'], entry)
            for kind in kinds:
                totals['declared_host_changes'][kind] += 1
            assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming'], (row['label'], j)
            assert ram == data['ram_before.bin'], (row['label'], j)
            assert (bank, ) == (phase['bank_before'], ) and kinds == [c['kind'] for c in phase['host_changes']]
            if phase['phase_in_step'] == 0:
                step_starts[phase['step']] = (ram, dict(state), pvc, bank, expected_pvc, expected_bank)
                starts[(row['label'], phase['step'])] = (ram, dict(state), pvc, bank)
                step_ram[phase['step']] = ram
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
            want_carry = cc.classify_carry(instructions, state['carry'], executed)
            assert result['carry'] == want_carry, (row['label'], j, hex(phase['outgoing']['pc']),
                                                    result['carry'], want_carry)
            carry_histogram[result['carry']] += 1
            # Carry probes: the same phase with a known incoming C must give exactly the source classification and
            # otherwise identical outputs. A phase that begins at an a018-caller BCS consumes the incoming C, so its
            # path would change with the probe and it is not probed.
            probed = (bool(executed) and executed[0] not in CALLER_BCS and
                      all(in_ranges(pc, MENU_RANGES) for pc in executed))
            for probe in (1, 2) if probed else ():
                again = common.invoke(exe, OUT, 'c%03d_carry%d_%03d' % (row['index'], probe, j), data['ram_before.bin'],
                                      dict(phase_in, carry=probe), phase_pvc, phase_bank, resources,
                                      stop=phase['stop_pc'], external=fx['external'])
                assert again[0]['ok'] and not again[4]
                assert again[0]['carry'] == cc.classify_carry(instructions, probe, executed), (row['label'], j, probe)
                assert ({k: v for k, v in again[0].items() if k != 'carry'} ==
                        {k: v for k, v in result.items() if k != 'carry'})
                assert again[1] == ram and again[2] == pvc and again[3] == actual[3]
                totals['carry_probes'] += 1
                # exactly one contract block (the phase is the block's own instruction run)
                if executed[0] in BLOCK_SET and executed == block_walk(instructions, executed[0]):
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
            ends[(row['label'], phase['step'])] = (ram, dict(state), pvc, bank)
            cpp_out[(row['index'], j)] = (ram, dict(state), pvc, bank)
        step_info[row['label']] = (step_ram, step_ports)
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
    # Carry-preserving blocks observed as single-block phases with a known incoming C vs the source derivation.
    for pc, outcomes in single_block.items():
        walk = block_walk(instructions, pc)
        # a06c (ANDI CCR) and a076 (ORI CCR) leave a known C whatever came in, so only one of the two probes keeps it.
        assert outcomes == {cc.classify_carry(instructions, probe, walk) == probe for probe in (1, 2)}, (hex(pc), outcomes)
        assert (outcomes == {True}) == (pc in preserving), hex(pc)
    totals['single_block_carry_starts_checked'] = sorted(hex(pc) for pc in single_block)
    totals['carry_preserving_starts_observed'] = sorted(hex(pc) for pc in single_block if pc in preserving)
    totals['carry_histogram'] = {cc.CARRY_NAME[k]: v for k, v in carry_histogram.items()}
    return out_rows, totals, ends, starts, guards, cpp_out, step_info


def chain_consistency(report, rows, ends, cpp_out, step_info, push_end, totals):
    # Chain consistency: the chain row's step 24/25 are the reviewed card-child/push outputs; the fresh runs equal the
    # chain's open frames wherever the native observation matched them (matched by native output identity).
    chain = next(r for r in rows if r['label'] == OPEN_CHAIN_LABEL)
    assert sha(ends[(chain['label'], PUSH_CHAIN_STEP)][0]) == report['card_menu_push_crosscheck']['ram_after_sha256']
    assert ends[(chain['label'], PUSH_CHAIN_STEP)][0] == push_end[0]
    by_identity = {}
    for j, phase in enumerate(chain['phases']):
        key = (sha(phase['_data']['ram_after.bin']), sha(phase['_data']['pvc_after.bin']),
               tuple(sorted(phase['outgoing'].items())))
        by_identity.setdefault(key, []).append(cpp_out[(chain['index'], j)])
    strip = lambda e: (e[0], {k: v for k, v in e[1].items() if k != 'carry'}, e[2][:0x1ff0] + e[2][0x1ff4:], e[3])
    chain_matches, matched_rows = 0, 0
    for row in rows:
        if not row['compared_with_chain'] or row is chain:
            continue
        matched_rows += 1
        for j, phase in enumerate(row['phases']):
            key = (sha(phase['_data']['ram_after.bin']), sha(phase['_data']['pvc_after.bin']),
                   tuple(sorted(phase['outgoing'].items())))
            assert key in by_identity, (row['label'], 'phase not in chain', j)
            assert strip(cpp_out[(row['index'], j)]) == strip(by_identity[key][0]), (row['label'], j)
            chain_matches += 1
    assert chain_matches == report['chain_vs_fresh_phases_compared'], (chain_matches, report['chain_vs_fresh_phases_compared'])
    totals['fresh_vs_chain_C++_phases_equal'] = chain_matches
    totals['fresh_rows_compared_with_chain'] = matched_rows
    # Per-frame evidence of the open frames (chain steps 26.. and the connected run steps 0..)
    chain_steps = sorted({p['step'] for p in chain['phases'] if p['step'] >= OPEN_FIRST_STEP})
    chain_ram, chain_ports = step_info[chain['label']]
    frames = {OPEN_CHAIN_LABEL: frame_check(report, OPEN_CHAIN_LABEL, chain_steps, chain_ram,
                                            {s: ends[(chain['label'], s)] for s in chain_steps}, chain_ports, 0)}
    connected = next(r for r in rows if r['label'] == 'connected-a370-to-open')
    conn_steps = sorted({p['step'] for p in connected['phases']})
    conn_ram, conn_ports = step_info[connected['label']]
    frames[connected['label']] = frame_check(report, connected['label'], conn_steps, conn_ram,
                                             {s: ends[(connected['label'], s)] for s in conn_steps}, conn_ports, 0)
    return frames


def compare_guards(exe, guards, resources):
    rows = []
    superseded = []
    for row, phase, ram, state, pvc, bank, step in guards:
        stop = phase['stop_pc']
        result, outgoing, out_pvc, ports, error = common.invoke(
            exe, OUT, 'guard_%s' % row['label'], ram, dict(state, carry=2), pvc, bank, resources,
            stop=stop, external=row['fixture']['external'])
        if row['label'] in SUPERSEDED_GUARDS:
            assert error.strip() != UNSUPPORTED_MACHINE or result['pc'] != phase['outgoing']['pc'], row['label']
            if not result['ok']:
                assert {k: result[k] for k in common.STATE_KEYS} == dict(state, carry=2) and outgoing == ram
            superseded.append(dict(label=row['label'], native_guard=phase['guard'], CPP_now_ok=result['ok'],
                                   CPP_now_error=error.strip(), CPP_now_pc=hex(result['pc'])))
            continue
        assert not result['ok'], (row['label'], 'C++ accepted the native guard input', hex(result['pc']))
        assert error.strip() == GUARD_ERRORS[row['label']], (row['label'], error)
        assert {k: result[k] for k in common.STATE_KEYS} == dict(state, carry=2)
        assert outgoing == ram and out_pvc == pvc and result['bank_base'] == bank
        assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1
        rows.append(dict(label=row['label'], native_guard=phase['guard'], checked_API_error=error.strip(),
                         all_API_outputs_preserved=True, native_fault_rollback_equivalence_claimed=False))
    return rows, superseded


def expected_pc_error(instructions, pc):
    """Dispatch model: an instruction address inside an open range (a63c TRAP excluded) is routed to the open core
    (which accepts block starts only); anything else has no executor in the machine."""
    if pc in instructions and in_ranges(pc, OPEN_RANGES) and pc != A63C:
        return UNSUPPORTED_OPEN
    return UNSUPPORTED_MACHINE


def interior_pcs(instructions):
    pcs = []
    for pc in sorted(instructions):
        # c1ea (BCC after BSR bd26) is a block of the open core now (save unit): superseded, not an interior negative.
        if in_ranges(pc, OPEN_RANGES) and pc not in BLOCK_SET and pc != A63C and pc != 0xc1ea:
            pcs.append(pc)
    return pcs


def negatives(exe, rows, starts, instructions, push_end, resources):
    out = []
    base = push_end
    row_of = {r['label']: r for r in rows}

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

    interior = interior_pcs(instructions)
    branches = [pc for pc in interior if mnemonic(instructions, pc) in COND_BRANCH]
    for pc in interior:
        kind = 'bundled_branch' if pc in branches else 'interior'
        reject('%s_direct_entry_%06x' % (kind, pc), base, {'pc': pc}, expected=expected_pc_error(instructions, pc))
    for pc in sorted(NEGATIVE_BOUNDARY_PCS):
        reject('boundary_direct_entry_%06x' % pc, base, {'pc': pc}, expected=UNSUPPORTED_MACHINE)
    # 1a73c is routed by the scene core (U2) now: a direct entry runs its code and ends with a state-dependent bus error (device address) instead of an
    # unsupported-PC rollback. Checked as a failure with the observed error; former and observed errors are recorded (superseded, not deleted).
    for pc in SUPERSEDED_DIRECT_PCS:
        reject('boundary_direct_entry_%06x' % pc, base, {'pc': pc}, expected=DEVICE_ADDR)
        SUPERSEDED_RECORDS.append(dict(label='boundary_direct_entry_%06x' % pc, former_expected_API_error=UNSUPPORTED_MACHINE,
                                       observed_error=DEVICE_ADDR, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False))
    ends_outside = sorted({high for _low, high in OPEN_RANGES} - set(BLOCK_STARTS) - set(BOUNDARY_PCS) - {C2C8}
                          - set(EXECUTED_RANGE_ENDS))
    for pc in ends_outside:
        reject('outside_range_entry_%06x' % pc, base, {'pc': pc}, expected=UNSUPPORTED_MACHINE)
    # Each stop boundary reached from the native boundary row's final step with any other stop: full rollback.
    rollback = {}
    for boundary, label in sorted(BOUNDARY_ROWS.items()):
        row = row_of[label]
        last = max(p['step'] for p in row['phases'])
        assert row['phases'][-1]['stop_pc'] == boundary, (label, hex(boundary))
        start = starts[(label, last)]
        assert row['phases'][-1]['outgoing']['pc'] == boundary
        others = [0xff000, 0x2ac2] + [b for b in (A406, 0xbd26) if b != boundary]
        if boundary in EXECUTED_BOUNDARIES or boundary == C2C8:
            others = []     # executed by a later card menu core now: not an unsupported-PC rollback (superseded)
        for stop in others:
            reject('%06x_reached_via_%s_with_stop_%06x' % (boundary, label, stop), start, stop=stop,
                   expected=UNSUPPORTED_MACHINE)
        # Positive control: the same input is accepted when this boundary is the stop.
        r, s, p, b = start
        result, _, _, _, error = common.invoke(exe, OUT, 'control_%06x_%s' % (boundary, label), r, dict(s, carry=2), p, b,
                                               resources, stop=boundary)
        assert result['ok'] and not error and result['pc'] == boundary and result['status'] == 0, (label, error)
        rollback[boundary] = label
    # a018 caller BCS with an Unknown carry: checked error and full rollback
    for pc in CALLER_BCS:
        reject('unknown_carry_entry_%06x' % pc, base, {'pc': pc}, expected=NEEDS_CARRY, carry=0)
    return out, len(interior), len(branches), rollback


def bcs_known_carry_controls(exe, push_end, resources):
    """Known C at the BCS blocks moves PC to the Clear/Set target without touching anything else (stop == target)."""
    rows = []
    ram, state, pvc, bank = push_end
    targets = {0x9ba6: (0x9baa, 0x9bbc), 0x9bcc: (0x9bd0, 0x9be2), 0x9bea: (0x9bee, 0x9c00), 0x9c10: (0x9c14, 0x9c26),
               0x9c36: (0x9c3a, 0x9c4c), 0x9c54: (0x9c58, 0x9c6a), 0x9c76: (0x9c7a, 0x9c8c), 0x9c9c: (0x9ca0, 0x9cb2),
               0x9cba: (0x9cbe, 0x9cd0), 0x9cd8: (0x9cdc, 0x9cee), 0x9cfc: (0x9d00, 0x9d12), 0x9d22: (0x9d26, 0x9d38),
               0x9dc0: (0x9dc4, 0x9dce), 0x9dd6: (0x9dda, 0x9df2), 0xa00c: (0xa010, 0xa016)}
    assert tuple(sorted(targets)) == tuple(sorted(CALLER_BCS))
    for pc, (clear_pc, set_pc) in sorted(targets.items()):
        for carry, target in ((1, clear_pc), (2, set_pc)):
            s = dict(state, pc=pc, carry=carry)
            result, out_ram, out_pvc, ports, error = common.invoke(exe, OUT, 'bcs_%06x_%d' % (pc, carry), ram, s,
                                                                   pvc, bank, resources, stop=target)
            assert result['ok'] and not error and result['pc'] == target and result['carry'] == carry
            assert {k: result[k] for k in common.STATE_KEYS if k not in ('pc',)} == {k: s[k] for k in common.STATE_KEYS if k != 'pc'}
            assert out_ram == ram and out_pvc == pvc and not ports
            rows.append(dict(pc=pc, carry=cc.CARRY_NAME[carry], target=target))
    return rows


def zero_step(exe, push_end, resources):
    ram, state, pvc, bank = push_end
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


def boundary_zero_step(exe, push_end, resources):
    """stop == entry PC at the boundaries: observed behavior (not required by the contract)."""
    ram, state, pvc, bank = push_end
    rows = []
    for pc in sorted(set(BOUNDARY_PCS) | {C2C8}):
        s = dict(state, pc=pc, carry=2)
        result, out_ram, out_pvc, ports, error = common.invoke(exe, OUT, 'zero_boundary_%06x' % pc, ram, s,
                                                               pvc, bank, resources, stop=pc)
        assert result['ok'], (hex(pc), error)
        assert {k: result[k] for k in common.STATE_KEYS} == s and out_ram == ram and out_pvc == pvc and not ports
        rows.append(dict(pc=pc, ok=result['ok'], error=error.strip()))
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    report_path.unlink(missing_ok=True)
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_card_menu_open.py', 'tools/verify_animation_machine_card_menu.py',
                 'tools/verify_animation_machine_card_child.py', 'tools/observe_animation_machine_card_menu_open.py',
                 'tools/observe_animation_machine_card_menu.py', 'tools/observe_animation_machine_card_child.py',
                 'docs/analysis/animation-machine-card-menu-open-contract.md',
                 'docs/analysis/animation-machine-card-menu-push-contract.md',
                 'engine/src/animation_machine_card_menu_open.cpp', 'engine/src/animation_machine_card_menu.cpp',
                 'engine/src/animation_machine_card_child.cpp', 'engine/tests/animation_machine_card_menu_open_test.cpp'):
        inputs[name] = cc.digest(ROOT / name)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = cc.digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = cc.digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    exe, command = helpers.compile_harness(ROOT, OUT)
    # Reviewed chains re-run in actual C++: BIOS stop output, a29c stop output, then the a370 stop output (push chain).
    cc.OUT = OUT / 'card_child_chain'
    cm.OUT = OUT / 'card_menu_push_chain'
    cc.OUT.mkdir(parents=True, exist_ok=True)
    cm.OUT.mkdir(parents=True, exist_ok=True)
    cm.CARRY_PROBES = False       # the push verifier's own run already proves those; only the chain outputs are needed here
    bios_start = cc.fade_chain_bios_output(exe, program, source, resources)
    cc_report, cc_rows, cc_refs, cc_instructions, _reads, _control = cc.audit_native(program, source)
    _m, _t, cc_ends, _g = cc.compare(exe, cc_rows, resources, cc_instructions, bios_start)
    cc_chain = next(r for r in cc_rows if r['group'] == 'chain')
    a29c_start = cc_ends[(cc_chain['label'], cm.CARD_CHILD_CHAIN_STEP)]
    assert a29c_start[1]['pc'] == cm.A29C
    cm_report, cm_rows, cm_refs, cm_instructions, _cm_reads, _cm_control = cm.audit_native(program, source)
    _o, _tt, cm_ends, _s, _gg = cm.compare(exe, cm_rows, resources, cm_instructions, a29c_start, bios_start)
    push_end = cm_ends[(PUSH_CHAIN_LABEL, PUSH_CHAIN_STEP)]
    assert push_end[1]['pc'] == A370 and push_end[1]['a7'] == 0x1feff8
    (report, rows, native_refs, instructions, static, program_reads, control_count, unobserved) = audit_native(program, source)
    refs.update(cc_refs)
    refs.update(cm_refs)
    refs.update(native_refs)
    assert sha(a29c_start[0]) == report['card_child_crosscheck']['ram_after_sha256']
    assert sha(push_end[0]) == report['card_menu_push_crosscheck']['ram_after_sha256']
    preserving = derived_preserving(instructions)
    assert preserving == cpp_preserving_cases() and len(preserving) == 68
    matches, totals, ends, starts, guards, cpp_out, step_info = compare(
        exe, rows, resources, instructions, push_end, bios_start, set(preserving))
    frames = chain_consistency(report, rows, ends, cpp_out, step_info, push_end, totals)
    guarded, guards_superseded = compare_guards(exe, guards, resources)
    negative, interior_count, branch_count, rollback = negatives(exe, rows, starts, instructions, push_end, resources)
    bcs_known = bcs_known_carry_controls(exe, push_end, resources)
    zero = zero_step(exe, push_end, resources)
    boundary_zero = boundary_zero_step(exe, push_end, resources)
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
                  open_frames_C_plus_plus=frames,
                  original_program_read_audit=program_reads,
                  native_guards_checked_API=guarded, native_guards_superseded_by_later_card_menu_cores=guards_superseded,
                  negatives_superseded_by_scene_core_routing=SUPERSEDED_RECORDS,
                  negatives_superseded_by_later_card_menu_cores=dict(direct_entry_pcs=[hex(x) for x in sorted(set(EXECUTED_BOUNDARIES) | {C2C8})], range_end_pcs=[hex(x) for x in EXECUTED_RANGE_ENDS], boundary_rollback_with_other_stops=[hex(x) for x in sorted(set(EXECUTED_BOUNDARIES))]),
                  native_continuous_control_phases_replayed=control_count,
                  negatives=negative, negative_count=len(negative) + len(guarded),
                  interior_PCs_rejected=interior_count, bundled_branch_PCs_among_interior=branch_count,
                  boundary_rollback_rows=dict((hex(k), v) for k, v in sorted(rollback.items())),
                  BCS_known_carry_targets=bcs_known,
                  zero_step=zero, boundary_zero_step=boundary_zero,
                  block_starts=len(BLOCK_STARTS), unobserved_block_starts=[hex(p) for p in unobserved],
                  carry_preserving_blocks=[hex(p) for p in preserving],
                  card_menu_push_a370_start=dict(chain_label=PUSH_CHAIN_LABEL, step=PUSH_CHAIN_STEP,
                                                 ram_sha256=sha(push_end[0]), pc=push_end[1]['pc'], a7=push_end[1]['a7']),
                  card_child_a29c_start=dict(chain_label=cc_chain['label'], step=cm.CARD_CHILD_CHAIN_STEP,
                                             ram_sha256=sha(a29c_start[0]), pc=a29c_start[1]['pc']),
                  bios_start=dict(chain_label=bios_start[0][0], step=bios_start[0][1],
                                  ram_sha256=sha(bios_start[1][0])),
                  carry_check='C++ carry equals source-opcode walk over native-executed PCs (ORI #1,CCR = Set, ANDI #fe,CCR = Clear, flow-only preserved, else Unknown); native SR never read; the 68 carry-preserving blocks are derived from the source opcodes and equal the list in animation_machine.cpp',
                  normalized_reference_paths=len(unique), compile_command=command, failure=None,
                  ROM_unchanged=True,
                  limits=['Controlled fixtures; frame re-entry is a declared PC=2ab8 change on the previous actual output, not a natural scheduler, IRQ or VBlank; parent and other objects are not run per frame.',
                          'No banked descriptor exists in ROM (bank_descriptor_search of both 2/3 banks: 0 terminating descriptors); only banked strings read through the current bank are covered.',
                          'Carry is a source-opcode classification (native SR is never read), not a native C measurement; ADDA/SUBA and every non-flow instruction are conservatively Unknown.',
                          'Boundaries 9e94 a2be a406 a662 a70a bd26 e84d6 a63c (TRAP #f) c2c8 and the hook targets of JSR (A4) at a3c6 are stop boundaries only, never executed; blocks c1ee c1f4 c1fe c202 c208 (after BSR bd26) and a3ac a3b4 (after BSR a2be/a6da) are not observed natively, and 9b78 is structurally unreachable (RTS after BEQ/BNE on the same flags); they are covered only by zero-step and the source carry derivation.',
                          'Direct-entry conditions (a348, a61c, c1c4, bf94) and all descriptors, strings, newer-menu records, 5(A2)/b/c record fields and D0 values are declared fixtures, not original-measured preparation; the rest starts from the actual C++ push-chain a370 stop output.',
                          'Video/watchdog are instruction-unit ordered register ports; tile/palette meaning of the port values and rendered output are not interpreted.',
                          'Native observation artifacts are audited by hash/trace consistency, not re-executed here.',
                          'Checked failures preserve API outputs, not original CPU fault rollback; bundled-branch/interior direct entries have no native guard (API-only rejection).'])
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=totals['cases'], split=totals['split'], control=totals['control'],
                         resumes=totals['resumes'], negatives=result['negative_count'], interior=interior_count,
                         zero_step=len(zero), carry=totals['carry_histogram'],
                         probes=totals['carry_probes'], sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
