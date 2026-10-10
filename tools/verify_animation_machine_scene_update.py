"""480bc frame helper bundle U4 (scene update 1a7a8 and its callees) native evidence vs the public machine API.

Controlled fixtures; no expected-register injection. The frozen native observation (artifacts/animation_machine_scene_update_native) is an immutable
input: this verifier never invokes the observer main. Every start state is rebuilt or pinned here:
  * scene_frame_execution inputs (22 natural 1a73c rows) are rebuilt from artifacts/scene_general_initialization + the case host writes and asserted
    equal to the SHA recorded in the observation's seed_provenance and to the fixture RAM SHA; they run U2 (1a73c -> 1a7a8) and U4 as two consecutive
    actual C++ steps (step 2 resumes only from the actual C++ output of step 1);
  * the fixtures that start from a state of another row's actual C++ chain (1afda / 1a8ce bases of scene case 36 with declared host RAM writes) are
    taken from that row's ACTUAL C++ output (RAM, 16 registers, PC, PVC, bank), asserted against the recorded base SHA / registers / A7 / PVC / bank;
  * all other starts (stage_entry 1a73c states, captured 1a7a8 / 1a69e states, declared register/stack variants) are declared native states
    SHA-pinned to the native artifacts; where an independent actual C++ chain output reproduces the same state this is counted and reported.
C++ resumes only from the previous actual C++ output plus the host changes recorded in the native step. The BSR.W at 1a69e is not part of any C++
range: its native phase is replaced by an independently checked host-side BSR (push of 1a6a2, PC 1a7a8) and C++ runs from there.
Native SR is never read: C is a source-opcode classification (U4 has no C producer/consumer; X is block local).
"""
import collections
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import tempfile
import traceback
import verify_animation_machine as common
import verify_animation_machine_callers as helpers
import verify_animation_machine_card_child as cc
import verify_animation_machine_scene_core as u2
import verify_stage_frame as vsf
from disassemble_program import load_verified_program, disassemble_range

ROOT = Path(__file__).resolve().parents[1]
MAIN_ROOT = '/Users/start/Workspce/metalslug'
OUT = ROOT / 'artifacts/animation_machine_scene_update_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_scene_update_native'
NATIVE_SHA = 'fdceb7710a9c73ca6ceb7459475ac6f6d05ebd26529510e7b516ab8cc1f9a063'
NATIVE_TOOL_SHA = '8ea6a0a9881bd48f262c15bff341822d10a9617d4f5b590ab8060a0132f9b981'
CONTRACT_SHA = '68855b9567d285c4bcd6d3ae3e1024d304384ed03e4b1fc3401dfe0b5a1637dc'
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
SCENE_OBS_SHA = u2.SCENE_OBS_SHA
SCENE_SEED_SHA = u2.SCENE_SEED_SHA
MARKER = cc.MARKER
sha = cc.sha
CARRY_NAME = cc.CARRY_NAME
FLOW_ONLY = cc.FLOW_ONLY
M32 = 0xffffffff
S = 0x1feffc
A5V = 0x108000
BSR_1A69E = 0x1a69e
RET_1A78C = 0x1a78c
RET_1A6A2 = 0x1a6a2
ENTRY_1A7A8 = 0x1a7a8
ENTRY_1A73C = 0x1a73c
EXECUTOR_ENTRIES = (0x43e38, 0x16ff8, 0x1861a, 0x18702, 0xcaf0)
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNSUPPORTED_UPDATE = 'unsupported animation scene update PC'
UNSUPPORTED_CORE = 'unsupported animation scene core PC'
EVEN = 'program bus requires even WORD/LONG address'
WRITE_DEVICE = 'unsupported animation machine write device'
RAM_MIRROR = 'program bus write requires RAM mirror units'
UNALIGNED_PC = 'unaligned animation machine PC'
UPDATE_RANGES = ((0x1a7a8, 0x1a910), (0x1724c, 0x17292), (0x43ea8, 0x43eb8), (0x1afda, 0x1b016), (0x19e64, 0x1a07a), (0x18656, 0x18702), (0x1b016, 0x1b128))
DATA_RANGES = ((0x1af12, 0x1afd2), (0x1afd2, 0x1afda))
CONDITIONAL = ('beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble')
X_USERS = ('addx', 'subx', 'negx', 'roxl', 'roxr', 'abcd', 'sbcd', 'nbcd')
GUARD_ERRORS = {
    'guard-odd-A5-first-read': EVEN, 'guard-odd-A7-push': EVEN, 'guard-odd-A7-rts': EVEN, 'guard-rom-write-A5': WRITE_DEVICE,
    'guard-rom-write-A7-push': RAM_MIRROR, 'guard-odd-A2-cursor': EVEN, 'guard-odd-A3-descriptor': EVEN, 'guard-odd-A1-path-state': EVEN,
    'guard-odd-A0-node': EVEN, 'guard-odd-A0-scale': EVEN, 'guard-odd-A0-debug-lookup': EVEN,
    'guard-path-index-0002-mid-instruction': UNSUPPORTED_UPDATE,      # 19e8c: operand word of the 19e8a slot (not a block start)
    'guard-path-index-0001-odd': UNALIGNED_PC,                        # 19e8b
    'guard-path-index-0006-mid-slot': UNSUPPORTED_UPDATE,             # 19e90: displacement word of the 19e8e slot
    'guard-path-index-7ffe-far': UNSUPPORTED_MACHINE,                 # 21e88: outside every executor range
    'guard-path-index-7fff-odd-far': UNALIGNED_PC,                    # 21e89
    'guard-bad-stop-1a6a2-on-frame-seed': UNSUPPORTED_MACHINE,        # RTS to 1a78c runs the U2 tail to the RTS into ff000 (no executor)
    'guard-bad-stop-1a78c-on-init-entry': UNSUPPORTED_MACHINE}        # RTS to 1a6a2 (no executor)
VERIFIED_ARTIFACTS = set()
RUN_DIR = None
WORKERS = 8
DEBUG_ROWS = int(os.environ.get('SCENE_UPDATE_DEBUG_ROWS', '0'))     # development switch only: the reported run is always the full set


def localize(name):
    return str(ROOT) + name[len(MAIN_ROOT):] if name.startswith(MAIN_ROOT + '/') else name


def in_ranges(pc, ranges):
    return any(low <= pc < high for low, high in ranges)


def inv(label, *args, **kwargs):
    result = common.invoke(*((args[0], RUN_DIR, label) + args[1:]), **kwargs)
    for suffix in ('_input.bin', '_pvc_input.bin', '_ram.bin', '_pvc.bin', '_ports.bin', '_state.json'):
        (RUN_DIR / (label + suffix)).unlink()
    return result


# ----------------------------------------------------------------------------------------------------------------- instructions
class RomInstructions(dict):
    """Instruction decoded from the original bytes on demand (executed PCs of every row, including the existing executors and U2/U3)."""
    def __init__(self, program):
        dict.__init__(self)
        self.program = program

    def __missing__(self, pc):
        rows = disassemble_range(self.program, pc, 10, pc)
        item = rows[0]
        assert item['classification'] == 'candidate_instruction' and item['cpu_address'] == pc, hex(pc)
        self[pc] = item
        return item


def classify_carry(instructions, carry, pcs, computed):
    return u2.classify_carry(instructions, carry, pcs, computed)


# ----------------------------------------------------------------------------------------------------------------- contract
def contract_text():
    return (ROOT / 'docs/analysis/animation-machine-scene-update-u4-contract.md').read_text()


def pc_list(text):
    return [int(x, 16) for x in re.findall(r'`([0-9a-f]{5})`', text)]


def parse_contract(program):
    lines = contract_text().splitlines()
    table = []
    for line in lines:
        if line.startswith('| `') and '..' in line:
            cells = [c.strip() for c in line.strip('|').split('|')]
            match = re.match(r'`([0-9a-f]+)\.\.([0-9a-f]+)`(.*)', cells[0])
            low, high = int(match.group(1), 16), int(match.group(2), 16)
            assert high - low == int(cells[1]), cells[0]
            assert program[low:high].hex() == cells[2].strip('`'), cells[0]
            table.append(dict(range='%x..%x' % (low, high), size=high - low, note=match.group(3), bytes_equal_to_rom=True))
    code = [(low, high) for low, high in UPDATE_RANGES]
    got = sorted((int(t['range'].split('..')[0], 16), int(t['range'].split('..')[1], 16)) for t in table)
    for item in code + list(DATA_RANGES):
        assert item in got, item
    assert sum(h - l for l, h in code) == 1486 and sum(h - l for l, h in DATA_RANGES) == 200
    starts_g = starts_d = bundled = preserving = None
    for line in lines:
        if line.strip().startswith('- 선택 G(102개):'):
            starts_g = pc_list(line)
        if line.strip().startswith('- 선택 D 추가(16개):'):
            starts_d = pc_list(line)
        if line.startswith('- **묶인 분기 PC'):
            pass
        if line.startswith('  - 선택 G') or line.startswith('- **Carry 보존'):
            pass
    for i, line in enumerate(lines):
        if line.startswith('- **묶인 분기 PC'):
            bundled = pc_list(lines[i + 0].split('선택 G 37개', 1)[1])
        if line.startswith('- **Carry 보존(FLOW_ONLY) block'):
            preserving = pc_list(line.split('선택 G 49개', 1)[1].split('그 밖은 Unknown', 1)[0])
    assert starts_g and starts_d and bundled and preserving, (starts_g and len(starts_g), starts_d and len(starts_d))
    assert (len(starts_g), len(starts_d), len(bundled), len(preserving)) == (102, 16, 46, 55), (len(starts_g), len(starts_d), len(bundled), len(preserving))
    starts = starts_g + starts_d
    assert len(set(starts)) == 118 and len(set(bundled)) == 46 and len(set(preserving)) == 55 and not (set(starts) & set(bundled))
    return table, starts, bundled, preserving


def derive_leaders(instructions, ranges):
    derived = set(low for low, _ in ranges)
    for pc, item in instructions.items():
        if not in_ranges(pc, ranges):
            continue
        name = item['mnemonic'].split('.')[0]
        target = re.search(r'\$([0-9a-f]+)$', item['op_str'])
        if name in CONDITIONAL + ('bra', 'bsr', 'jsr') and target:
            derived.add(int(target.group(1), 16))
        if name in CONDITIONAL + ('bsr', 'jsr', 'rts', 'bra', 'jmp', 'dbra'):
            derived.add(pc + item['size'])
        if name == 'dbra' and target:
            derived.add(int(target.group(1), 16))
    return set(pc for pc in derived if in_ranges(pc, ranges))


def static_blocks(instructions, starts):
    blocks = {}
    for start in starts:
        pcs, pc = [], start
        while True:
            item = instructions[pc]
            pcs.append(pc)
            name = item['mnemonic'].split('.')[0]
            end = name in ('rts', 'bra', 'jmp', 'jsr', 'bsr', 'dbra') or name in CONDITIONAL
            following = pc + item['size']
            if end or following in starts or following not in instructions:
                break
            pc = following
        blocks[start] = pcs
    return blocks


def audit_static(report, program, source):
    assert cc.digest(NATIVE_DIR / 'source.json') == report['artifacts']['source.json']
    VERIFIED_ARTIFACTS.add('source.json')
    static = json.loads((NATIVE_DIR / 'source.json').read_text())
    assert static['source'] == source
    table, starts, bundled, preserving = parse_contract(program)
    assert sorted(tuple(r) for r in static['u4_ranges']) == sorted(UPDATE_RANGES)
    assert sorted(tuple(r) for r in report['new_ranges']) == sorted(UPDATE_RANGES)
    instructions = {}
    for instruction in static['instructions']:
        at, size = instruction['rom_offset'], instruction['size']
        assert bytes(bytearray.fromhex(instruction['raw'])) == program[at:at + size] and at == instruction['cpu_address']
        instructions[at] = instruction
    inside = sorted(pc for pc in instructions if in_ranges(pc, UPDATE_RANGES))
    # coverage: the instruction list of the observer tiles the seven code ranges without a gap and every instruction is decoded
    tiled = 0
    for low, high in UPDATE_RANGES:
        pc = low
        while pc < high:
            assert pc in instructions, hex(pc)
            pc += instructions[pc]['size']
        assert pc == high
        tiled += high - low
    assert tiled == 1486 and len(inside) == 405, len(inside)
    start_set = set(starts)
    assert all(in_ranges(pc, UPDATE_RANGES) and pc in instructions for pc in starts)
    derived = derive_leaders(instructions, UPDATE_RANGES)
    contract_not_derived = sorted(start_set - derived)
    derived_not_contract = sorted(derived - start_set)
    assert contract_not_derived == [] and derived_not_contract == [], ([hex(p) for p in contract_not_derived], [hex(p) for p in derived_not_contract])
    blocks = static_blocks(instructions, start_set)
    # every instruction of the seven ranges is in exactly one block or is a bundled conditional branch / DBRA (interior)
    in_block = collections.Counter(pc for pcs in blocks.values() for pc in pcs)
    assert max(in_block.values()) == 1
    assert sorted(in_block) == inside
    bundled_derived = sorted(pc for pcs in blocks.values() for pc in pcs if pc not in start_set and
                             instructions[pc]['mnemonic'].split('.')[0] in CONDITIONAL + ('dbra',))
    assert bundled_derived == sorted(bundled), ([hex(p) for p in bundled_derived], [hex(p) for p in bundled])
    assert all(pcs[-1] == pc for pcs in blocks.values() for pc in pcs if pc in bundled)
    for pc in bundled:
        name = instructions[pc]['mnemonic'].split('.')[0]
        assert name in CONDITIONAL + ('dbra',), hex(pc)
    preserving_derived = sorted(pc for pc in starts if all(instructions[p]['mnemonic'].split('.')[0] in FLOW_ONLY for p in blocks[pc]))
    assert preserving_derived == sorted(preserving)
    # no C producer / consumer: no ORI/ANDI/EORI/MOVE to CCR/SR, no block that starts with a flag consumer, X users only inside blocks 1724c 1726c 1b042 1b05e
    producers = sorted(pc for pc in inside if instructions[pc]['mnemonic'].split('.')[0] in ('ori', 'andi', 'eori', 'move') and
                       instructions[pc]['op_str'].endswith(('ccr', 'sr')))
    assert producers == []
    consumers = sorted(pc for pc in starts if instructions[pc]['mnemonic'].split('.')[0] in CONDITIONAL and len(blocks[pc]) == 1 and pc not in
                       {p for p in starts if blocks[p] and instructions[blocks[p][0]]['mnemonic'].split('.')[0] not in CONDITIONAL})
    assert consumers == [], [hex(p) for p in consumers]
    x_users = sorted(pc for pc in inside if instructions[pc]['mnemonic'].split('.')[0] in X_USERS)
    x_blocks = sorted(set(next(s for s, pcs in blocks.items() if pc in pcs) for pc in x_users))
    assert x_users == [0x17258, 0x17278, 0x1b058, 0x1b074] and x_blocks == [0x1724c, 0x1726c, 0x1b042, 0x1b05e], (x_users, x_blocks)
    # the X producer precedes the X user inside the same block
    x_producer = {0x17258: 0x17254, 0x17278: 0x17274, 0x1b058: 0x1b056, 0x1b074: 0x1b072}
    for user, producer in x_producer.items():
        block = next(pcs for pcs in blocks.values() if user in pcs)
        assert producer in block and block.index(producer) < block.index(user)
    assert contract_not_derived == [] and static['boundary_stop_pcs'] == [RET_1A78C, RET_1A6A2]
    return dict(static=static, table=table, starts=starts, bundled=bundled, preserving=preserving, instructions=instructions, blocks=blocks,
                inside=inside, x_users=x_users, x_blocks=x_blocks, derived_not_contract=derived_not_contract)


# ----------------------------------------------------------------------------------------------------------------- native rows
def load_row(row):
    for kind in ('phases', 'continuous_control'):
        for phase in row[kind]:
            data = {}
            for name, expected in phase['artifacts'].items():
                value = (NATIVE_DIR / name).read_bytes()
                assert sha(value) == expected, name
                VERIFIED_ARTIFACTS.add(name)
                data[re.search(r'_phase_\d+_(.*)$', name).group(1)] = value
            phase['_data'] = data
            phase['_trace'] = json.loads(data['trace.json'])
            for snapshot in phase['snapshots']:
                snapshot['_ram'] = (NATIVE_DIR / snapshot['artifacts']['ram']).read_bytes()
                snapshot['_pvc'] = (NATIVE_DIR / snapshot['artifacts']['pvc']).read_bytes()
                assert sha(snapshot['_ram']) == phase['artifacts'][snapshot['artifacts']['ram']]
                assert sha(snapshot['_pvc']) == phase['artifacts'][snapshot['artifacts']['pvc']]


def unload_row(row):
    for kind in ('phases', 'continuous_control'):
        for phase in row[kind]:
            for key in ('_data', '_trace'):
                phase.pop(key, None)
            for snapshot in phase['snapshots']:
                snapshot.pop('_ram', None)
                snapshot.pop('_pvc', None)


def audit_row(row, program):
    assert row['reproduced_twice'] and row['continuous_split_equivalent']
    assert bool(row['guarded']) == (row['group'] == 'guard')
    fx = row['fixture']
    counts_split = None
    for kind in ('phases', 'continuous_control'):
        counts = cc.audit_program_reads(program, fx, row[kind])
        if kind == 'phases':
            counts_split = counts
    cc.audit_split_control(row)
    for phase in row['phases'] + row['continuous_control']:
        assert phase['carry'] is None and not phase['branch_evidence'] and phase['carry_in'] is None
        assert phase['counts']['external_reads'] == sum(e['region'] == 'external' for e in phase['_trace']['events'])
        ports = [e for e in phase['_trace']['events'] if e['region'] in ('pvc', 'video', 'watchdog')]
        assert phase['_data']['ports.bin'] == b''.join(struct.pack('>BII', e['size'], e['address'], int(e['bytes'], 16)) for e in ports)
    return counts_split


def audit_report(program, source):
    path = NATIVE_DIR / 'observation.json'
    assert cc.digest(path) == NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_scene_update.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'docs/analysis/animation-machine-scene-update-u4-contract.md') == CONTRACT_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None and source['sha256'] == ROM_SHA
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['sha256'] == CONTRACT_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase', 'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['declared_register_changes_at_step_boundaries'] == [] and report['contract_discrepancies'] == []
    assert report['rom_stat_start'] == report['rom_stat_end']
    assert (report['cases'], report['guarded_cases'], report['split_steps'], report['control_steps']) == (325, 18, 12171, 369)
    assert (report['total_split_phases'], report['total_control_phases'], report['fresh_CPU_runs']) == (12189, 387, 2764)
    assert report['contract']['contract_block_starts'] == 118 and report['contract']['contract_bundled_branches'] == 46
    assert report['uncovered_u4_block_starts'] == [] and report['uncovered_u2_block_starts'] == []
    assert report['boundary_stop_pcs'] == [RET_1A78C, RET_1A6A2]
    inputs = {}
    for name, expected in report['inputs'].items():
        local = localize(name)
        assert cc.digest(local) == expected, name
        inputs[local] = expected
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    assert cc.digest(localize(report['oracle']['library'])) == report['oracle']['library_sha256']
    return report, inputs


def native_tables(rows):
    """sha -> path of native RAM images (ram_before without host changes, any ram_after): the SHA-pinned declared native states."""
    table = {}
    for row in rows:
        for phase in row['phases']:
            for name, digest in phase['artifacts'].items():
                if name.endswith('_ram_after.bin') or (name.endswith('_ram_before.bin') and not phase['host_changes']):
                    table.setdefault(digest, NATIVE_DIR / name)

    def get(want):
        data = table[want].read_bytes()
        assert sha(data) == want
        return data
    return get


# ----------------------------------------------------------------------------------------------------------------- starts
def pvc_of(fx):
    return u2.build_pvc(fx)


def derived_key(fx):
    return fx['preparation'].get('ram_sha256')


def start_of_row(row, scene_in, base_rams, registry):
    """(ram, state, pvc, bank, declared_register_diffs, how)"""
    fx = row['fixture']
    seed = fx['seed']
    regs = dict(fx['initial_regs'])
    assert set(regs) == set(vsf.KEYS) | {'a5'}
    pvc, bank, pvc_how = pvc_of(fx)
    assert fx['bank_state'][0] == bank
    declared = []
    want_derived = derived_key(fx)
    if seed['kind'] == 'scene_frame_execution case':
        record, ram0, regs14 = scene_in[seed['case']]
        assert sha(ram0) == seed['input_ram_sha256'] == seed['recorded_input_ram_sha256'] == record['input_ram_sha256']
        assert seed['observation_sha256'] == SCENE_OBS_SHA and seed['initializer_observation_sha256'] == SCENE_SEED_SHA
        ram = u2.apply_initial_writes(ram0, fx['initial_host_writes'])
        prov = dict(regs14, a5=A5V)
        declared = sorted(k for k in regs if prov[k] != regs[k])
        how = 'rebuilt scene_frame input %d' % seed['case']
    elif want_derived is not None:
        entry = [e for e in registry.get(want_derived, []) if e['state_regs'] == regs and e['a7'] == fx['initial_a7'] and e['pc'] == fx['entry_pc'] and
                 sha(e['pvc']) == fx['initial_PVC_sha256'] and e['bank'] == bank]
        assert entry, (row['label'], len(registry.get(want_derived, [])))
        e = entry[0]
        ram = e['ram']
        how = 'actual C++ output of %s phase %d (stop %x)' % (e['label'], e['phase'], e['pc'])
        pvc = e['pvc']
        row['_derived_from'] = (e['label'], e['phase'])
    else:
        ram = base_rams(fx['initial_RAM_sha256'])
        how = 'declared native state (SHA-pinned native artifact)'
    assert sha(ram) == fx['initial_RAM_sha256'], row['label']
    state = dict(regs, a7=fx['initial_a7'], pc=fx['entry_pc'], carry=0)
    return ram, state, pvc, bank, declared, how, pvc_how


def bsr_emulate(ram, state):
    """Host-side BSR.W at 1a69e (no C++ range): push the return LONG 1a6a2 at A7-4, PC = 1a7a8; everything else unchanged."""
    assert state['pc'] == BSR_1A69E
    a7 = (state['a7'] - 4) & M32
    ram2 = bytearray(ram)
    ram2[a7 & 0xffff:(a7 & 0xffff) + 4] = RET_1A6A2.to_bytes(4, 'big')
    return bytes(ram2), dict(state, a7=a7, pc=ENTRY_1A7A8)


def host_bsr_1a69e(phase, ram, state, pvc, bank):
    """Independent check of the native BSR.W phase at 1a69e against the host-side emulation (registers, RAM, PVC, bank, trace)."""
    assert phase['incoming']['pc'] == BSR_1A69E and phase['stop_pc'] == ENTRY_1A7A8 and phase['guard'] is None
    assert phase['_trace']['pcs'] == [BSR_1A69E, ENTRY_1A7A8]
    ev = phase['_trace']['events']
    assert len(ev) == 1 and (ev[0]['access'], ev[0]['region'], ev[0]['size'], ev[0]['address'], ev[0]['bytes']) == \
        ('write', 'ram', 4, (state['a7'] - 4) & M32, '0001a6a2'), ev
    ram2, new = bsr_emulate(ram, state)
    ram2 = bytearray(ram2)
    a7 = new['a7']
    assert {k: new[k] for k in common.REGS + ('pc',)} == phase['outgoing'], 'host BSR registers'
    assert bytes(ram2) == phase['_data']['ram_after.bin'] and pvc == phase['_data']['pvc_after.bin'] and bank == phase['modeled_bank']
    return bytes(ram2), new


def apply_changes(ram, state, changes, entry):
    ram = bytearray(ram)
    kinds = []
    for change in changes:
        assert change['kind'] == 'ram'
        assert change['pc_before'] == entry['pc'] and change['a7_before'] == entry['a7'], change
        at, size = change['address'] & 65535, change['size']
        assert 0 <= at <= 65536 - size
        common.native.put(ram, change['address'], size, change['value'])
        kinds.append('ram')
    return bytes(ram), dict(state), kinds


def run_row(row, ctx):
    """One native row against the C++ API (rows run concurrently, phases and steps inside a row sequentially)."""
    exe, resources, st, scene_in, base_rams, program, instructions, registry, wanted = ctx
    start_set = set(st['starts'])
    acc = dict(totals=collections.Counter(), program_reads=collections.Counter(), carry_hist=collections.Counter(), first_pcs=collections.Counter(),
               guards=[], start=None, outputs=[], registry=[], preserved={})
    totals = acc['totals']
    load_row(row)
    counts = audit_row(row, program)
    acc['program_reads'].update(counts)
    fx = row['fixture']
    ram, state, pvc, bank, declared, how, pvc_how = start_of_row(row, scene_in, base_rams, registry)
    if declared:
        totals['declared_register_rows'] += 1
    expected_pvc, expected_bank = pvc, bank
    digest = hashlib.sha256()
    stops = []
    step_ends = {}
    step_starts = {}
    carry_row = collections.Counter()
    phases = row['phases']
    for j, phase in enumerate(phases):
        data = phase['_data']
        entry = dict(pc=state['pc'], a7=state['a7'])
        ram, state, kinds = apply_changes(ram, state, phase['host_changes'], entry)
        totals['declared_host_ram_changes'] += len(kinds)
        step = phase['step']
        if phase['phase_in_step'] == 0:
            step_starts[step] = (ram, dict(state), pvc, bank)
            if acc['start'] is None:
                acc['start'] = step_starts[step]
        else:
            assert not phase['host_changes']
        assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming'], (row['label'], j)
        assert ram == data['ram_before.bin'], (row['label'], j)
        events = phase['_trace']['events']
        executed = phase['_trace']['pcs'][:-1]
        if phase['guard'] is not None:
            assert j == len(phases) - 1 and row['guarded']
            g_ram, g_state, g_start = ram, dict(state), step_starts[step]
            if g_state['pc'] == BSR_1A69E:       # bad-stop guard of an 1a69e entry: the host-side BSR first, C++ from 1a7a8
                g_ram, g_state = bsr_emulate(ram, state)
                g_start = (g_ram, dict(g_state), pvc, bank) if g_start[1]['pc'] == BSR_1A69E and j == 0 else g_start
                totals['host_side_bsr_1a69e_guard_rows'] += 1
            acc['guards'].append((row, phase, g_ram, g_state, pvc, bank, g_start))
            break
        assert bank == phase['bank_before']
        expected_pvc, expected_bank, portbytes = cc.fold_outputs(expected_pvc, expected_bank, events)
        assert expected_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
        if state['pc'] == BSR_1A69E and phase['stop_pc'] != BSR_1A69E:
            ram, state = host_bsr_1a69e(phase, ram, state, pvc, bank)
            totals['host_side_bsr_1a69e_phases'] += 1
            result = None
            carry_row['Unknown'] += 1
            step_ends[step] = (ram, dict(state), pvc, bank)
            stops.append(phase['stop_pc'])
            digest.update(struct.pack('>IIB', phase['stop_pc'], state['pc'], 0) + hashlib.sha256(ram).digest() + hashlib.sha256(pvc).digest() + b'\0\0\0\0')
            continue
        phase_in, phase_pvc, phase_bank = dict(state), pvc, bank
        actual = inv('c%03d_split_%03d' % (row['index'], j), exe, ram, state, pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
        assert actual[0]['ok'] and not actual[4], (row['label'], j, hex(phase['stop_pc']), actual[4])
        u2.check_result(actual, dict(outgoing=phase['outgoing'], events=events, ram_after=data['ram_after.bin']), expected_pvc, expected_bank, portbytes)
        result, ram, pvc, _, _ = actual
        computed = u2.computed_carry(executed, data['ram_before.bin'], phase_in)
        want_carry = classify_carry(instructions, state['carry'], executed, computed)
        assert result['carry'] == want_carry, (row['label'], j, hex(phase['outgoing']['pc']), result['carry'], want_carry)
        acc['carry_hist'][result['carry']] += 1
        carry_row[CARRY_NAME[result['carry']]] += 1
        first = executed[0] if executed else None
        if first is not None and first in start_set:
            acc['first_pcs'][first] += 1
        # carry probes: the incoming known C (Set / Clear) is preserved or replaced by exactly the source-opcode classification
        if any(i > 0 and pc in u2.CONSUMERS_ALL and classify_carry(instructions, 1, executed[:i], computed) != classify_carry(instructions, 2, executed[:i], computed)
               for i, pc in enumerate(executed)) or first in u2.CONSUMERS_ALL:
            totals['carry_probe_phases_skipped_path_dependent'] += 1
        else:
            for probe in (1, 2):
                again = inv('c%03d_carry%d_%03d' % (row['index'], probe, j), exe, data['ram_before.bin'], dict(phase_in, carry=probe), phase_pvc,
                            phase_bank, resources, stop=phase['stop_pc'], external=fx['external'])
                assert again[0]['ok'] and not again[4], (row['label'], j, probe)
                assert again[0]['carry'] == classify_carry(instructions, probe, executed, computed), (row['label'], j, probe, again[0]['carry'])
                assert {k: v for k, v in again[0].items() if k != 'carry'} == {k: v for k, v in result.items() if k != 'carry'}
                assert again[1] == ram and again[2] == pvc and again[3] == actual[3]
                totals['carry_probes'] += 1
                totals['carry_probe_preserved'] += again[0]['carry'] == probe
                blocks = [pc for pc in executed if pc in start_set]
                if len(blocks) == 1 and blocks[0] == first and not any(pc not in instructions_u4 for pc in executed):
                    slot = acc['preserved'].setdefault(first, {1: True, 2: True})
                    slot[probe] = slot[probe] and again[0]['carry'] == probe
        totals['carry_checks'] += 1
        state = {k: result[k] for k in common.STATE_KEYS}
        bank = result['bank_base']
        totals['reads'] += result['external_reads']
        totals['ports'] += len(portbytes) // 9
        totals['resumes'] += 1 if phase['phase_in_step'] else 0
        digest.update(struct.pack('>IIB', phase['stop_pc'], state['pc'], result['carry']) + hashlib.sha256(ram).digest() + hashlib.sha256(pvc).digest() +
                      struct.pack('>I', len(portbytes)))
        stops.append(phase['stop_pc'])
        step_ends[step] = (ram, dict(state), pvc, bank)
        if sha(ram) in wanted:
            acc['registry'].append((sha(ram), dict(ram=ram, state_regs={k: state[k] for k in vsf.KEYS + ('a5',)}, a7=state['a7'], pc=state['pc'],
                                                  pvc=pvc, bank=bank, label=row['label'], phase=j)))
        acc['outputs'].append((sha(ram), tuple(state[k] for k in common.REGS + ('pc',)), sha(pvc), bank))
    control_rows = 0
    for phase in row['continuous_control']:
        if phase['guard'] is not None:
            continue
        step = phase['step']
        c_ram, c_state, c_pvc, c_bank = step_starts[step]
        data = phase['_data']
        e_pvc, e_bank, portbytes = cc.fold_outputs(c_pvc, c_bank, phase['_trace']['events'])
        assert e_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
        if phase['incoming']['pc'] == BSR_1A69E and phase['stop_pc'] != BSR_1A69E:
            # control spans the BSR.W at 1a69e: C++ continues from the host-side BSR state (the first split phase) to the same stop
            c_ram, c_state = host_bsr_1a69e(row['phases'][0], c_ram, c_state, c_pvc, c_bank)
            assert row['phases'][0]['step'] == step
            assert phase['_trace']['pcs'][:2] == [BSR_1A69E, ENTRY_1A7A8]
        else:
            assert {k: c_state[k] for k in common.REGS + ('pc',)} == phase['incoming']
        actual = inv('c%03d_control_%d' % (row['index'], step), exe, c_ram, c_state, c_pvc, c_bank, resources, stop=phase['stop_pc'], external=fx['external'])
        assert actual[0]['ok'] and not actual[4], (row['label'], actual[4])
        u2.check_result(actual, dict(outgoing=phase['outgoing'], events=phase['_trace']['events'], ram_after=data['ram_after.bin']), e_pvc, e_bank, portbytes)
        assert (actual[1], {k: actual[0][k] for k in common.STATE_KEYS}, actual[2], actual[0]['bank_base']) == step_ends[step], (row['label'], step)
        control_rows += 1
    totals['cases'] += 1
    totals['split'] += len(stops)
    totals['control'] += control_rows
    acc['out_row'] = dict(index=row['index'], label=row['label'], group=row['group'], seed=row['fixture']['seed']['kind'], seed_start=how,
                          pvc_page=pvc_how, declared_initial_registers=declared, entry_pc=hex(fx['entry_pc']),
                          step_stop_pcs=[hex(s['stop_pc']) for s in row['steps']], split_phases=len(stops), control_steps=control_rows,
                          steps=len(row['steps']), carry=dict(sorted(carry_row.items())), guarded=bool(row['guarded']),
                          C_phase_digest_sha256=digest.hexdigest())
    acc['seed_kind'] = how.split(' ')[0] + ' ' + how.split(' ')[1]
    acc['derived'] = row.get('_derived_from')
    acc['declared_start'] = (sha(acc['start'][0]), tuple(acc['start'][1][k] for k in common.REGS + ('pc',)), sha(acc['start'][2]), acc['start'][3]) \
        if acc['start'] else None
    unload_row(row)
    return acc


instructions_u4 = set()


def compare(exe, rows, resources, st, scene_in, base_rams, program, instructions):
    totals = collections.Counter()
    program_reads = collections.Counter(fixed_reads=0, bank_reads=0, PVC_writes=0)
    carry_hist = collections.Counter({0: 0, 1: 0, 2: 0})
    preserved = {}
    first_pcs, seed_kinds = collections.Counter(), collections.Counter()
    out_rows, guards, starts_by_label, outputs = [], [], {}, set()
    declared_starts = []
    registry = {}
    start_set = set(st['starts'])
    wanted = set(derived_key(r['fixture']) for r in rows if derived_key(r['fixture']) is not None)

    def phase_run(subset, store):
        ctx = (exe, resources, st, scene_in, base_rams, program, instructions, registry, wanted)
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            def guarded_run(r):
                try:
                    return run_row(r, ctx)
                except Exception:
                    return dict(error=traceback.format_exc())
            results = list(pool.map(guarded_run, subset))
        failures = [(row['label'], acc['error']) for row, acc in zip(subset, results) if 'error' in acc]
        if failures:
            for n, (label, text) in enumerate(failures[:25]):
                print('ROW FAILED', label, text.strip().splitlines()[-1])
                if n < 3:
                    print(text)
            raise AssertionError('%d rows failed' % len(failures))
        store.extend(zip(subset, results))

    base_rows = [r for r in rows if derived_key(r['fixture']) is None]
    derived_rows = [r for r in rows if derived_key(r['fixture']) is not None]
    done = []
    phase_run(base_rows, done)
    for _, acc in done:
        for key, entry in acc['registry']:
            registry.setdefault(key, []).append(entry)
    phase_run(derived_rows, done)
    by_label = {row['label']: (row, acc) for row, acc in done}
    for row in rows:
        row_, acc = by_label[row['label']]
        totals.update(acc['totals'])
        program_reads.update(acc['program_reads'])
        carry_hist.update(acc['carry_hist'])
        first_pcs.update(acc['first_pcs'])
        seed_kinds[acc['seed_kind']] += 1
        for pc, slots in acc['preserved'].items():
            slot = preserved.setdefault(pc, {1: True, 2: True})
            for probe in (1, 2):
                slot[probe] = slot[probe] and slots[probe]
        guards.extend(acc['guards'])
        out_rows.append(acc['out_row'])
        r, s, p, b = acc['start']
        starts_by_label[row['label']] = (r, s, p, b)
        outputs.update(acc['outputs'])
        declared_starts.append((row['label'], row['group'], acc['declared_start'], acc['derived']))
    # declared native starts independently reproduced by another row's actual C++ chain output (RAM sha, 16R, PC, PVC sha, bank)
    reproduced, not_reproduced = [], []
    for label, group, start, derived in declared_starts:
        if derived is not None or start is None:
            continue
        if (start[0], start[1], start[2], start[3]) in outputs:
            reproduced.append(label)
        else:
            not_reproduced.append(label)
    for pc, slots in preserved.items():
        assert pc in start_set and all(slots.values()) == (pc in st['preserving']), (hex(pc), slots)
    if not DEBUG_ROWS:
        assert start_set <= set(first_pcs) | set(), sorted(hex(p) for p in start_set - set(first_pcs))
    totals = dict(sorted(totals.items()))
    totals['carry_histogram'] = {CARRY_NAME[k]: v for k, v in sorted(carry_hist.items())}
    totals['guard_rows'] = len(guards)
    totals['u4_block_starts_run_as_first_pc_of_actual_cpp_phases'] = len(start_set & set(first_pcs))
    totals['single_block_u4_starts_probed'] = len(preserved)
    totals['single_block_u4_starts_carry_preserving'] = sum(all(s.values()) for s in preserved.values())
    totals['seed_start_kinds'] = dict(sorted(seed_kinds.items()))
    totals['derived_rows_started_from_actual_cpp_output'] = sum(1 for _, _, _, d in declared_starts if d is not None)
    totals['declared_native_starts_reproduced_by_actual_cpp_chain'] = len(reproduced)
    totals['declared_native_starts_not_reproduced'] = len(not_reproduced)
    return out_rows, totals, guards, starts_by_label, dict(program_reads), sorted(not_reproduced), sorted(reproduced)


def compare_guards(exe, guards, resources):
    rows, mismatches = [], []
    for row, phase, ram, state, pvc, bank, step_start in guards:
        fx = row['fixture']
        label = row['label']
        cases = [('phase', ram, state, pvc, bank, phase['stop_pc'])]
        if (ram, state, pvc, bank) != (step_start[0], step_start[1], step_start[2], step_start[3]):
            cases.append(('whole_step', step_start[0], step_start[1], step_start[2], step_start[3], phase['step_stop_pc']))
        entry = {}
        for kind, r, s, p, b, stp in cases:
            s = dict(s, carry=2)
            result, outgoing, out_pvc, ports, error = inv('guard_%s_%s' % (label, kind), exe, r, s, p, b, resources, stop=stp, external=fx['external'])
            assert not result['ok'], (label, kind)
            if error.strip() != GUARD_ERRORS[label]:
                mismatches.append((label, kind, error.strip()))
            assert {k: result[k] for k in common.STATE_KEYS} == s
            assert outgoing == r and out_pvc == p and result['bank_base'] == b
            assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1
            entry[kind] = error.strip()
        rows.append(dict(label=label, native_guard=phase['guard'], checked_API_errors=entry, all_API_outputs_preserved=True,
                         native_fault_rollback_equivalence_claimed=False))
    assert not mismatches, mismatches
    assert sorted(GUARD_ERRORS) == sorted(r['label'] for r in rows)
    return rows


# ----------------------------------------------------------------------------------------------------------------- API-only checks
def negatives(exe, base, st, resources):
    out = []
    r0, s0, p0, b0 = base
    instructions = st['instructions']
    start_set = set(st['starts'])

    def reject(label, start, changes=None, stop=0xff000, external=0, error_expected=None):
        r, s, p, b = start
        s = dict(s, carry=2)
        s.update(changes or {})
        result, outgoing, out_pvc, ports, error = inv('negative_' + label, exe, r, s, p, b, resources, stop=stop, external=external)
        assert not result['ok'], label
        assert error.strip() == error_expected, (label, error.strip())
        assert {k: result[k] for k in common.STATE_KEYS} == s
        assert outgoing == r and out_pvc == p and ports == MARKER and result['bank_base'] == b
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        out.append(dict(label=label, error=error.strip(), all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False))

    interior = [pc for pc in st['inside'] if pc not in start_set]
    for pc in interior:
        reject('interior_direct_entry_%06x' % pc, base, {'pc': pc}, error_expected=UNSUPPORTED_UPDATE)
    operand = [pc for low, high in UPDATE_RANGES for pc in range(low, high, 2) if pc not in instructions and pc not in start_set]
    for pc in operand:
        reject('operand_word_direct_entry_%06x' % pc, base, {'pc': pc}, error_expected=UNSUPPORTED_UPDATE)
    # the PC-relative debug tables are data: no executor, even PCs inside the data windows
    data_pcs = [pc for low, high in DATA_RANGES for pc in range(low, high, 2)]
    for pc in (data_pcs[0], data_pcs[1], data_pcs[47], data_pcs[95], data_pcs[96], data_pcs[99]):
        reject('data_table_entry_%06x' % pc, base, {'pc': pc}, error_expected=UNSUPPORTED_MACHINE)
    # neighbours just outside the seven code ranges (own executors or none)
    outside = (0x17290 + 4, 0x172a0, 0x1a910, 0x1a912, 0x1a07a, 0x1a07c, 0x18702 + 0x2000, 0x43eb8, 0x43eba, 0x1b128, 0x1b12a, 0x1a470, 0x1a6a2, 0x1a69e)
    for pc in outside:
        reject('outside_range_entry_%06x' % pc, base, {'pc': pc}, error_expected=UNSUPPORTED_MACHINE)
    # odd PCs (alignment is checked before routing)
    for pc in (0x1a7a9, 0x19e8b, 0x1b0e1, 0x18657):
        reject('odd_pc_entry_%06x' % pc, base, {'pc': pc}, error_expected=UNALIGNED_PC)
    # stops that the unit never reaches
    for stop in (0x1a6a2, 0x1a7a6, 0x1a912, 0x1b128):
        reject('frame_start_with_unreached_stop_%06x' % stop, base, stop=stop, error_expected=UNSUPPORTED_MACHINE)
    # positive controls: the reachable stops of the same start
    controls = []
    for stop in (0x1a7d2, 0x1a8ce, 0x1afda, 0x1a90e, 0x1a78c):
        s = dict(s0, carry=0)
        result, out_ram, out_pvc, ports, error = inv('control_stop_%06x' % stop, exe, r0, s, p0, b0, resources, stop=stop)
        assert result['ok'] and not error and result['pc'] == stop, (stop, error)
        controls.append(dict(entry=hex(s0['pc']), stop=hex(stop), ok=True, a7=result['a7'], carry=CARRY_NAME[result['carry']]))
    # computed path opcode index: 20 (0x14 words) reaches handler 00 (19eaa) -> positive control through the public API
    return out, len(interior), len(operand), controls


def zero_step(exe, base, resources, starts):
    ram, state, pvc, bank = base
    rows = []
    for pc in starts:
        for carry in (0, 1, 2):
            s = dict(state, pc=pc, carry=carry)
            result, out_ram, out_pvc, ports, error = inv('zero_%06x_%d' % (pc, carry), exe, ram, s, pvc, bank, resources, stop=pc)
            assert result['ok'] and not error and result['status'] == 0, (hex(pc), carry, error)
            assert {k: result[k] for k in common.STATE_KEYS} == s
            assert out_ram == ram and out_pvc == pvc and result['bank_base'] == bank
            assert result['external_reads'] == 0 and not ports
            rows.append((pc, carry))
    return rows


def boundary_zero_step(exe, base, resources):
    ram, state, pvc, bank = base
    rows = []
    for pc in (RET_1A78C, RET_1A6A2, BSR_1A69E, ENTRY_1A7A8):
        s = dict(state, pc=pc, carry=2)
        result, out_ram, out_pvc, ports, error = inv('zero_boundary_%06x' % pc, exe, ram, s, pvc, bank, resources, stop=pc)
        assert {k: result[k] for k in common.STATE_KEYS} == s and out_ram == ram and out_pvc == pvc
        rows.append(dict(pc=hex(pc), ok=result['ok'], error=error.strip()))
    return rows


# ----------------------------------------------------------------------------------------------------------------- main
def main():
    global RUN_DIR
    assert OUT.resolve() == (ROOT / 'artifacts/animation_machine_scene_update_execution').resolve()
    if OUT.exists():
        shutil.rmtree(OUT)          # only this verifier's own output folder
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    RUN_DIR = Path(tempfile.mkdtemp(prefix='scene_update_verify_'))
    try:
        run(report_path)
    finally:
        shutil.rmtree(RUN_DIR, ignore_errors=True)


def run(report_path):
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_scene_update.py', 'tools/verify_animation_machine_scene_core.py', 'tools/verify_animation_machine_card_child.py',
                 'tools/verify_stage_frame.py', 'tools/observe_animation_machine_scene_update.py', 'tools/observe_scene_frame_execution.py',
                 'docs/analysis/animation-machine-scene-update-u4-contract.md', 'engine/src/animation_machine_scene_update.cpp',
                 'engine/src/animation_machine.cpp', 'engine/src/animation_machine_internal.h', 'engine/tests/animation_machine_scene_update_test.cpp'):
        inputs[name] = cc.digest(ROOT / name)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = cc.digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = cc.digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    exe, command = helpers.compile_harness(ROOT, OUT)
    report, native_inputs = audit_report(program, source)
    st = audit_static(report, program, source)
    instructions = RomInstructions(program)
    global instructions_u4
    instructions_u4 = set(st['instructions'])
    rows = report['results'] + report['guarded_results']
    assert len(rows) == 343
    if DEBUG_ROWS:
        rows = rows[:DEBUG_ROWS] + report['guarded_results']
    scene_in, scene_files = u2.rebuild_scene_inputs()
    prov = report['seed_provenance']
    for path, expected in scene_files.items():
        assert prov['files'][path.replace(str(ROOT), MAIN_ROOT)] == expected, path
    assert prov['scene_frame']['observation_sha256'] == SCENE_OBS_SHA and prov['scene_frame']['initializer_observation_sha256'] == SCENE_SEED_SHA
    captured = {c['case']: c for c in prov['scene_frame']['captured_1a7a8_states']}
    for row in rows:
        seed = row['fixture']['seed']
        if seed['kind'].startswith('declared 1a7a8 re-entry'):
            assert captured[seed['case']]['ram_sha256'] == seed['ram_at_1a7a8_sha256'], row['label']
    base_rams = native_tables(rows)
    matches, totals, guards, starts_by_label, program_reads, not_reproduced, reproduced = compare(exe, rows, resources, st, scene_in, base_rams, program,
                                                                                                  instructions)
    assert DEBUG_ROWS or VERIFIED_ARTIFACTS == set(report['artifacts']), (len(VERIFIED_ARTIFACTS), len(report['artifacts']))
    guarded = compare_guards(exe, guards, resources)
    base = starts_by_label['captured-scene-1a7a8-0036']
    base = (base[0], dict(base[1]), base[2], base[3])
    negative, interior_count, operand_count, controls = negatives(exe, base, st, resources)
    zero = zero_step(exe, base, resources, st['starts'])
    boundary_zero = boundary_zero_step(exe, base, resources)
    cpp_text = (ROOT / 'engine/src/animation_machine_scene_update.cpp').read_text()
    cpp_cases = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', cpp_text))
    start_set = set(st['starts'])
    cpp_not_contract = sorted(cpp_cases - start_set)
    contract_not_cpp = sorted(start_set - cpp_cases)
    assert cpp_not_contract == [] and contract_not_cpp == [], ([hex(p) for p in cpp_not_contract], [hex(p) for p in contract_not_cpp])
    for name, expected in list(inputs.items()) + list(native_inputs.items()):
        assert cc.digest(ROOT / name if not name.startswith('/') else name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    manifest = '\n'.join('%s %s' % (k, report['artifacts'][k]) for k in sorted(report['artifacts']))
    refs = dict(refs)
    refs.update(scene_files)
    for path in (OUT / 'harness.cpp', OUT / 'compile.log'):
        refs[str(path.resolve())] = cc.digest(path)
    result = dict(
        schema_version=1, source=source, inputs=inputs, native_inputs_checked=len(native_inputs), artifacts=refs,
        native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA, contract_sha256=CONTRACT_SHA,
        native_artifact_manifest=dict(count=len(report['artifacts']), every_file_read_and_hash_checked=True,
                                      sorted_name_hash_lines_sha256=sha(manifest.encode())),
        contract_ranges=st['table'], block_start_count=len(st['starts']), block_starts=[hex(p) for p in st['starts']],
        bundled_branch_count=len(st['bundled']), carry_preserving_blocks=[hex(p) for p in st['preserving']],
        carry_preserving_count=len(st['preserving']), carry_consumer_blocks=[], carry_producer_blocks=[],
        x_flag_users=[hex(p) for p in st['x_users']], x_flag_blocks=[hex(p) for p in st['x_blocks']],
        opcode_leader_derivation=dict(contract_not_derived=[], derived_not_contract=[hex(p) for p in st['derived_not_contract']]),
        cpp_case_labels=dict(cpp_not_in_contract_block_starts=[hex(p) for p in cpp_not_contract],
                             contract_block_starts_without_cpp_case=[hex(p) for p in contract_not_cpp]),
        actual_CPP=dict(totals, matches=matches), original_program_read_audit=program_reads,
        declared_native_starts_not_reproduced_by_cpp_chain=not_reproduced, declared_native_starts_reproduced_by_cpp_chain=reproduced,
        native_guards_checked_API=guarded, native_continuous_control_phases_replayed=totals['control'],
        negatives=negative, negative_count=len(negative) + len(guarded), interior_PCs_rejected=interior_count,
        operand_word_PCs_rejected=operand_count, API_controls=controls,
        zero_step_count=len(zero), zero_step_blocks=len(st['starts']), zero_step_carries=[0, 1, 2], boundary_zero_step=boundary_zero,
        carry_check='C++ carry equals the source-opcode walk over native-executed PCs (ORI/ANDI CCR known, flow-only preserved, else Unknown; the U2 '
                    'steps of the natural rows use the U2 rules incl. the computed 1a2e0 carry); U4 itself has no C producer / consumer; native SR never read',
        compile_command=command, failure=None, ROM_unchanged=True,
        limits=['Controlled fixtures (rebuilt scene_frame seeds, actual-C++-derived bases, declared SHA-pinned native states, declared RAM/register/'
                'stack variants), not natural scheduler, IRQ or gameplay reachability.',
                'Stage_entry 1a73c states, captured 1a7a8 / 1a69e states are native states SHA-pinned in the native artifacts; only those listed as '
                'reproduced were independently re-derived by an actual C++ chain output.',
                'The BSR.W at 1a69e has no C++ range: its native phase is checked as an independent host-side BSR; the code behind the stops 1a78c / '
                '1a6a2 (U2 tail, U5) is only run where the bad-stop guards say so.',
                'Existing executors 43e38, 16ff8, 1861a, 18702, caf0 are compared as whole results (RAM/regs/ports/bank); their interiors are not modelled here.',
                'Carry is a source-opcode classification (native SR is never read); X is block local and not observable through the API.',
                'Checked failures preserve API outputs, not original CPU fault rollback; interior / operand / data / odd / outside direct entries have no '
                'native counterpart (API-only rejection).',
                'Native observation artifacts are audited by hash/trace consistency, not re-executed here.'],
        normalized_reference_paths=len(refs))
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=totals['cases'], split=totals['split'], control=totals['control'], resumes=totals['resumes'],
                          negatives=result['negative_count'], interior=interior_count, operand=operand_count, zero_step=len(zero),
                          carry=totals['carry_histogram'], sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
