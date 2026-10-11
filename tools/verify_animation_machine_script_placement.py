"""480bc frame helper bundle U5 (script opcodes 1a0b6, placement 1a470 and their callees) native evidence vs the public machine API.

Controlled fixtures; no expected-register injection. The frozen native observation (artifacts/animation_machine_script_placement_native) is an
immutable input: this verifier never invokes the observer main. Every start state is rebuilt or pinned here:
  * the 19 natural chain rows (1a73c -> 1a0b6/1a470 -> ... -> ff000, three steps) start from the scene_frame_execution input rebuilt from
    artifacts/scene_general_initialization + the case host writes (sha-checked) and run as consecutive actual C++ steps;
  * all other rows start from declared native states (captured hits of the original runs plus declared RAM/register/stack variants) that are
    SHA-pinned to the native artifacts (the 11 rows whose pre-write image is not stored start from the phase-0 image after the declared writes);
    where an actual C++ chain output reproduces the same state this is counted and reported.
C++ resumes only from the previous actual C++ output plus the host changes recorded in the native step.
Integration: all 594 scene_frame seeds are run 1a73c -> RTS(ff000) in C++ (U2..U5 and the existing executors) and compared with the recorded
original runs and with the native full-frame records on instruction-independent fields.
Native SR is never read: C is a source-opcode classification (the only consumer is the BCC at 197a2; U5 has no C producer).
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
import verify_animation_machine_scene_update as u4
import verify_stage_frame as vsf
from disassemble_program import load_verified_program

ROOT = Path(__file__).resolve().parents[1]
MAIN_ROOT = '/Users/start/Workspce/metalslug'
OUT = ROOT / 'artifacts/animation_machine_script_placement_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_script_placement_native'
NATIVE_SHA = 'cbe215f0a9803ad9f49fc067a3fdbf66e20cef031c8651d3b41a8bdfecabcf13'
NATIVE_TOOL_SHA = 'f05a7d1117b4d2612f517b491da4619ba8f5c7c0b57a06991e3533137659ae03'
CONTRACT_SHA = '08f3f1ea9bd6e7344d97fd9bb7a2fa3cd776f40b2d46c1e305f5688ef6c1ff4c'
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
FF000 = 0xff000
CONDITIONAL = u4.CONDITIONAL
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNSUPPORTED_SP = 'unsupported animation script placement PC'
UNKNOWN_CARRY = 'script placement caller requires known carry'
EVEN = 'program bus requires even WORD/LONG address'
EVEN_WRITE = 'invalid animation machine write size/alignment'
WRITE_DEVICE = 'unsupported animation machine write device'
RAM_MIRROR = 'program bus write requires RAM mirror units'
UNALIGNED_PC = 'unaligned animation machine PC'
CODE_RANGES = ((0x1a0b6, 0x1a26a), (0x19772, 0x197da), (0x1a40e, 0x1a414), (0x1a470, 0x1a526), (0x1a086, 0x1a08e), (0x1a09e, 0x1a0a6),
               (0x19e60, 0x19e64), (0x16fee, 0x16ff8), (0x3d7e, 0x3db2), (0xe89fa, 0xe8a0c), (0x43e08, 0x43e34))
DATA_RANGES = ((0x1a08e, 0x1a09e), (0x1a0a6, 0x1a0b6))
# routing of animation_machine.cpp (animation_script_placement_block); 43e08/43e22 are cases of the existing cleanup executor (43e08..43e34 is cleanup)
ROUTED = ((0x3d7e, 0x3db2), (0x16fee, 0x16fef), (0x19772, 0x197da), (0x19e60, 0x19e64), (0x1a086, 0x1a26a), (0x1a40e, 0x1a414), (0x1a470, 0x1a526),
          (0xe89fa, 0xe8a0c))
CLEANUP_STARTS = (0x43e08, 0x43e22)
CONSUMER = 0x197a2
VERIFIED_ARTIFACTS = set()
RUN_DIR = None
WORKERS = 8
DEBUG_ROWS = int(os.environ.get('SCRIPT_PLACEMENT_DEBUG_ROWS', '0'))     # development switch only: the reported run is always the full set
DEBUG_FRAMES = int(os.environ.get('SCRIPT_PLACEMENT_DEBUG_FRAMES', '0'))


CONSUMERS_ALL = frozenset(u2.CONSUMERS_ALL | {0x196c0, 0x196e2, 0x19924, 0x19734, 0x198b8, 0x1974e, 0x19874, 0x19894, 0x198d8, CONSUMER})   # U2 + U3 + U5 BCC-after-call blocks
U3_CLEAR_PCS = (0x19710, 0x1971c, 0x19372, 0x1957a)     # U3 contract main decision 2: TST.W / AND.W leave the 68000 C flag known Clear


def classify_carry(instructions, carry, pcs, computed):
    """Source-opcode C classification (no native SR): ORI/ANDI CCR known, the U3 TST.W/AND.W producers known Clear, EORI #1,CCR after the CMP.W of
    1a2e0 is the computed known carry, the 289e / 28a4 rules of the fade_card executor, flow-only opcodes preserve, anything else makes C Unknown."""
    for index, pc in enumerate(pcs):
        item = instructions[pc]
        name = item['mnemonic'].split('.')[0]
        if name == 'ori' and item['op_str'] == '#$1, ccr':
            carry = 2
        elif name == 'andi' and item['op_str'] == '#$fe, ccr':
            carry = 1
        elif name == 'eori' and item['op_str'] == '#$1, ccr':
            assert pc == u2.EORI_1A2E0 and computed is not None
            carry = computed
        elif pc in U3_CLEAR_PCS:
            assert name in ('tst', 'and'), hex(pc)
            carry = 1
        elif pc == 0x289e:
            carry = 0
        elif pc == 0x28a4 and index + 1 < len(pcs) and pcs[index + 1] == 0x28ac and carry == 0:
            carry = 1
        elif name in FLOW_ONLY:
            pass
        else:
            carry = 0
    return carry


def compile_harness(root, folder):
    """Same command as helpers.compile_harness (warnings are errors for this check) with a 10 minute timeout (shared machine)."""
    import subprocess
    path = folder / 'harness.cpp'
    path.write_text(common.HARNESS)
    exe = folder / 'animation_machine_callers_harness'
    compiler = shutil.which('clang++')
    assert compiler
    command = [compiler, '-std=c++11', '-O2', '-Wall', '-Wextra', '-pedantic', '-I' + str(root / 'engine/include')]
    command += [str(root / 'engine/src' / name) for name in common.SOURCES]
    command += [str(path), '-o', str(exe)]
    run = subprocess.run(command, capture_output=True, text=True, timeout=600)
    (folder / 'compile.log').write_text(run.stdout + run.stderr)
    assert run.returncode == 0 and not run.stdout and not run.stderr, run.stderr
    return exe, command


def fold_outputs(pvc, bank, events):
    """Independent PVC effects plus native video/watchdog writes in total order (as the card-child fold, plus the WORD port write at 3c0006 that the
    U5 contract records as one video port event)."""
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
            assert ((address == 0x3c0000 and size in (2, 4)) or (address == 0x3c0004 and size == 2) or (address == 0x300001 and size == 1) or
                    (address == 0x3c0006 and size == 2))
            raw = bytes.fromhex(event['bytes'])
            assert len(raw) == size
            ports.append(struct.pack('>BII', size, address, int.from_bytes(raw, 'big')))
    return pvc, bank, b''.join(ports)


def localize(name):
    return str(ROOT) + name[len(MAIN_ROOT):] if name.startswith(MAIN_ROOT + '/') else name


def in_ranges(pc, ranges):
    return any(low <= pc < high for low, high in ranges)


def inv(label, *args, **kwargs):
    result = common.invoke(*((args[0], RUN_DIR, label) + args[1:]), **kwargs)
    for suffix in ('_input.bin', '_pvc_input.bin', '_ram.bin', '_pvc.bin', '_ports.bin', '_state.json'):
        (RUN_DIR / (label + suffix)).unlink()
    return result


# ----------------------------------------------------------------------------------------------------------------- contract
def pc_list(text):
    return [int(x, 16) for x in re.findall(r'`([0-9a-f]{3,5}|e[0-9a-f]{4})`', text)]


def parse_contract(program):
    text = (ROOT / 'docs/analysis/animation-machine-script-placement-u5-contract.md').read_text()
    lines = text.splitlines()
    table = []
    for line in lines:
        if line.startswith('| `') and '..' in line:
            cells = [c.strip() for c in line.strip('|').split('|')]
            match = re.match(r'`([0-9a-f]+)\.\.([0-9a-f]+)`(.*)', cells[0])
            low, high = int(match.group(1), 16), int(match.group(2), 16)
            assert high - low == int(cells[1]), cells[0]
            assert program[low:high].hex() == cells[2].strip('`'), cells[0]
            table.append(dict(range='%x..%x' % (low, high), size=high - low, note=match.group(3), bytes_equal_to_rom=True))
    got = sorted((int(t['range'].split('..')[0], 16), int(t['range'].split('..')[1], 16)) for t in table)
    for item in CODE_RANGES + DATA_RANGES:
        assert item in got, item
    assert len(table) == 13 and sum(h - l for l, h in CODE_RANGES) == 872 and sum(h - l for l, h in DATA_RANGES) == 32
    starts = bundled = preserving = None
    for i, line in enumerate(lines):
        if line.startswith('- **Block 시작 PC (88개)**'):
            starts = pc_list(lines[i + 2])
        if line.startswith('- **묶인 분기 PC (13개'):
            bundled = pc_list(line.split('거부)**:', 1)[1])
        if line.startswith('- **Carry 보존(FLOW_ONLY) block (35개)**'):
            preserving = pc_list(line.split('조건분기).', 1)[1].split('그 밖은 Unknown', 1)[0])
    assert starts and bundled and preserving
    assert (len(starts), len(bundled), len(preserving)) == (88, 13, 35), (len(starts), len(bundled), len(preserving))
    assert len(set(starts)) == 88 and len(set(bundled)) == 13 and len(set(preserving)) == 35 and not (set(starts) & set(bundled))
    assert set(preserving) <= set(starts) and CONSUMER in starts
    return table, starts, bundled, preserving


def derive_leaders(instructions, ranges):
    derived = set(low for low, _ in ranges)
    for pc, item in instructions.items():
        if not in_ranges(pc, ranges):
            continue
        name = item['mnemonic'].split('.')[0]
        target = re.search(r'\$([0-9a-f]+)$', item['op_str'])
        if name in CONDITIONAL + ('bra', 'bsr', 'jsr', 'jmp') and target:
            derived.add(int(target.group(1), 16))
        if name in CONDITIONAL + ('bsr', 'jsr', 'rts', 'bra', 'jmp', 'dbra'):
            derived.add(pc + item['size'])
        if name == 'dbra' and target:
            derived.add(int(target.group(1), 16))
    return set(pc for pc in derived if in_ranges(pc, ranges))


def audit_static(report, program, source):
    assert cc.digest(NATIVE_DIR / 'source.json') == report['artifacts']['source.json']
    VERIFIED_ARTIFACTS.add('source.json')
    static = json.loads((NATIVE_DIR / 'source.json').read_text())
    assert static['source'] == source
    table, starts, bundled, preserving = parse_contract(program)
    # observer ranges: the ten non-cleanup code ranges plus 43e08..43e34 (11), data ranges 2
    assert sorted(tuple(r) for r in static['u5_ranges']) == sorted(CODE_RANGES), (static['u5_ranges'])
    assert sorted(tuple(r) for r in report['new_ranges']) == sorted(CODE_RANGES)
    assert sorted(tuple(r) for r in static['data_ranges']) == sorted(DATA_RANGES)
    instructions = {}
    for instruction in static['instructions']:
        at, size = instruction['rom_offset'], instruction['size']
        assert bytes(bytearray.fromhex(instruction['raw'])) == program[at:at + size] and at == instruction['cpu_address']
        instructions[at] = instruction
    inside = sorted(pc for pc in instructions if in_ranges(pc, CODE_RANGES))
    tiled = 0
    for low, high in CODE_RANGES:
        pc = low
        while pc < high:
            assert pc in instructions, hex(pc)
            pc += instructions[pc]['size']
        assert pc == high
        tiled += high - low
    assert tiled == 872 and len(inside) == 258 == len(instructions), (tiled, len(inside), len(instructions))
    start_set = set(starts)
    assert all(in_ranges(pc, CODE_RANGES) and pc in instructions for pc in starts)
    derived = derive_leaders(instructions, CODE_RANGES)
    contract_not_derived = sorted(start_set - derived)
    derived_not_contract = sorted(derived - start_set)
    assert contract_not_derived == [] and derived_not_contract == [], ([hex(p) for p in contract_not_derived], [hex(p) for p in derived_not_contract])
    blocks = u4.static_blocks(instructions, start_set)
    in_block = collections.Counter(pc for pcs in blocks.values() for pc in pcs)
    assert max(in_block.values()) == 1 and sorted(in_block) == inside
    bundled_derived = sorted(pc for pcs in blocks.values() for pc in pcs if pc not in start_set and
                             instructions[pc]['mnemonic'].split('.')[0] in CONDITIONAL + ('dbra',))
    assert bundled_derived == sorted(bundled), ([hex(p) for p in bundled_derived], [hex(p) for p in bundled])
    assert all(pcs[-1] == pc for pcs in blocks.values() for pc in pcs if pc in bundled)
    preserving_derived = sorted(pc for pc in starts if all(instructions[p]['mnemonic'].split('.')[0] in FLOW_ONLY for p in blocks[pc]))
    assert preserving_derived == sorted(preserving), ([hex(p) for p in preserving_derived], [hex(p) for p in preserving])
    producers = sorted(pc for pc in inside if instructions[pc]['mnemonic'].split('.')[0] in ('ori', 'andi', 'eori', 'move') and
                       instructions[pc]['op_str'].endswith(('ccr', 'sr')))
    assert producers == []
    x_users = sorted(pc for pc in inside if instructions[pc]['mnemonic'].split('.')[0] in u4.X_USERS)
    assert x_users == []
    # carry consumer: the only block that starts with a conditional branch (it reads C produced before the block)
    consumers = sorted(pc for pc in starts if instructions[blocks[pc][0]]['mnemonic'].split('.')[0] in CONDITIONAL)
    assert consumers == [CONSUMER], [hex(p) for p in consumers]
    # in-block C producers feeding bundled branches (SUBQ at 3d7e, CMP at 1a484): consumed inside the block, not an input
    return dict(static=static, table=table, starts=starts, bundled=bundled, preserving=preserving, instructions=instructions, blocks=blocks, inside=inside,
                derived_not_contract=derived_not_contract)


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
    assert bool(row['guarded']) == any(p['guard'] for p in row['phases'])
    counts_split = None
    for kind in ('phases', 'continuous_control'):
        counts = cc.audit_program_reads(program, row['fixture'], row[kind])
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
    assert cc.digest(ROOT / 'tools/observe_animation_machine_script_placement.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'docs/analysis/animation-machine-script-placement-u5-contract.md') == CONTRACT_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None and source['sha256'] == ROM_SHA
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['sha256'] == CONTRACT_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase', 'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['declared_register_changes_at_step_boundaries'] == [] and report['contract_discrepancies'] == []
    assert report['rom_stat_start'] == report['rom_stat_end']
    assert (report['cases'], report['guarded_cases'], report['split_steps'], report['control_steps']) == (626, 32, 5479, 664)
    assert (report['total_split_phases'], report['total_control_phases'], report['fresh_CPU_runs']) == (5511, 696, 8929)
    assert report['contract']['contract_block_starts'] == 88 and report['contract']['contract_bundled_branches'] == 13
    assert report['uncovered_u5_block_starts'] == [] and report['uncovered_u4_block_starts'] == [] and report['uncovered_u2_block_starts'] == []
    assert report['full_frame']['cases'] == report['full_frame']['ok'] == 594 and len(report['natural_chains']) == 19
    assert all(c['ok'] for c in report['natural_chains']) and all(f['ok'] and not f['error'] for f in report['full_frame']['rows'])
    assert report['census_model_checks']['runs'] == 5634 == report['census_model_checks']['equal'] and report['first_boundary_census']['states'] == 5624
    ext = report['observer_extension']
    assert '3c0006' in ext['condition_added'] and ext['files_edited'] == []
    inputs = {}
    for name, expected in report['inputs'].items():
        local = localize(name)
        assert cc.digest(local) == expected, name
        inputs[local] = expected
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    assert cc.digest(localize(report['oracle']['library'])) == report['oracle']['library_sha256']
    return report, inputs


def native_tables(report):
    """sha -> native RAM image path (every *_ram_before/_ram_after artifact of the observation)."""
    table = {}
    for name, digest in report['artifacts'].items():
        if name.endswith('_ram_before.bin') or name.endswith('_ram_after.bin'):
            table.setdefault(digest, NATIVE_DIR / name)

    def get(want):
        if want not in table:
            return None
        data = table[want].read_bytes()
        assert sha(data) == want
        VERIFIED_ARTIFACTS.add(table[want].name)
        return data
    return get


# ----------------------------------------------------------------------------------------------------------------- starts
def start_of_row(row, scene_in, base_rams):
    """(ram, state, pvc, bank, declared_register_diffs, how, pvc_how)"""
    fx = row['fixture']
    seed = fx['seed']
    regs = dict(fx['initial_regs'])
    assert set(regs) == set(vsf.KEYS) | {'a5'}
    pvc, bank, pvc_how = u2.build_pvc(fx)
    assert fx['bank_state'][0] == bank
    declared = []
    if seed['kind'] == 'scene_frame_execution case':
        record, ram0, regs14 = scene_in[seed['case']]
        assert sha(ram0) == seed['input_ram_sha256'] == seed['recorded_input_ram_sha256'] == record['input_ram_sha256']
        assert seed['observation_sha256'] == SCENE_OBS_SHA and seed['initializer_observation_sha256'] == SCENE_SEED_SHA
        ram = u2.apply_initial_writes(ram0, fx['initial_host_writes'])
        assert dict(regs14, a5=A5V) == regs and fx['entry_pc'] == 0x1a73c
        how = 'rebuilt scene_frame input %d' % seed['case']
        kind = 'rebuilt'
    else:
        ram = base_rams(fx['initial_RAM_sha256'])
        if ram is not None:
            how, kind = 'declared native state (SHA-pinned native artifact)', 'pinned'
        else:
            # the pre-write image is not an artifact: the phase-0 image after the declared host writes (host_changes are then idempotent)
            phase0 = row['phases'][0]
            ram = phase0['_data']['ram_before.bin']
            for change in phase0['host_changes']:
                at, size = change['address'] & 0xffff, change['size']
                assert int.from_bytes(ram[at:at + size], 'big') == change['value'], row['label']
            how, kind = 'declared native state (phase-0 image after the declared host writes; pre-write image not stored)', 'phase0'
        prov = {k: int(v, 16) for k, v in seed['registers'].items()}
        declared = sorted(k for k in prov if prov[k] != regs[k]) + (['a5'] if regs['a5'] != A5V else [])
    assert kind == 'phase0' or sha(ram) == fx['initial_RAM_sha256'], row['label']
    state = dict(regs, a7=fx['initial_a7'], pc=fx['entry_pc'], carry=0)
    return ram, state, pvc, bank, declared, how, pvc_how, kind


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


def interior_target(executed, st, instructions):
    """First executed PC reached by a control transfer (not by falling through) that is inside a routed range but not a block start."""
    start_set = set(st['starts'])
    for i in range(1, len(executed)):
        pc, prev = executed[i], executed[i - 1]
        if pc != prev + instructions[prev]['size'] and in_ranges(pc, ROUTED) and pc not in start_set:
            return pc
    return None


def run_row(row, ctx):
    exe, resources, st, scene_in, base_rams, program, instructions = ctx
    start_set = set(st['starts'])
    acc = dict(totals=collections.Counter(), program_reads=collections.Counter(), carry_hist=collections.Counter(), first_pcs=collections.Counter(),
               guards=[], start=None, outputs=[], preserved={}, consumer_probes=[], chain=None, ports_all=[], policy=[])
    totals = acc['totals']
    load_row(row)
    counts = audit_row(row, program)
    acc['program_reads'].update(counts)
    fx = row['fixture']
    ram, state, pvc, bank, declared, how, pvc_how, kind = start_of_row(row, scene_in, base_rams)
    if declared:
        totals['declared_register_rows'] += 1
    expected_pvc, expected_bank = pvc, bank
    digest = hashlib.sha256()
    stops = []
    step_ends = {}
    step_starts = {}
    carry_row = collections.Counter()
    phases = row['phases']
    policy_step = None
    all_ports = bytearray()
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
            assert j == len(phases) - 1
            acc['guards'].append((row, phase, ram, dict(state), pvc, bank, step_starts[step]))
            break
        assert bank == phase['bank_before']
        expected_pvc, expected_bank, portbytes = fold_outputs(expected_pvc, expected_bank, events)
        assert expected_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
        phase_in, phase_pvc, phase_bank = dict(state), pvc, bank
        mid = interior_target(executed, st, instructions)
        if mid is not None:
            # computed-PC policy: the native fixture lands in the middle of a block (not a block start); C++ must reject it with the exact checked
            # error and full preservation. Later native phases/steps of this row run from the interior and have no C++ counterpart.
            r0, o0, p0, po0, e0 = inv('c%03d_policy_%03d' % (row['index'], j), exe, ram, dict(state, carry=2), pvc, bank, resources, stop=phase['stop_pc'],
                                      external=fx['external'])
            assert not r0['ok'] and e0.strip() == UNSUPPORTED_SP, (row['label'], j, hex(mid), e0)
            assert {k: r0[k] for k in common.STATE_KEYS} == dict(state, carry=2) and o0 == ram and p0 == pvc and po0 == MARKER and r0['bank_base'] == bank
            assert r0['external_reads'] == 0x12345678 and r0['status'] == 1
            acc['policy'].append(dict(label=row['label'], phase=j, native_interior_target=hex(mid), error=e0.strip(), native_phases_not_continued=len(phases) - j,
                                      all_API_outputs_preserved=True))
            totals['computed_pc_policy_rejections'] += 1
            policy_step = step
            break
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
        all_ports += portbytes
        if first == CONSUMER:
            # the carry consumer: Unknown incoming C is a checked error with full rollback; the matching Set/Clear reproduce the native path
            r0, o0, p0, po0, e0 = inv('c%03d_unk_%03d' % (row['index'], j), exe, data['ram_before.bin'], dict(phase_in, carry=0), phase_pvc, phase_bank,
                                      resources, stop=phase['stop_pc'], external=fx['external'])
            assert not r0['ok'] and e0.strip() == UNKNOWN_CARRY, (row['label'], j, e0)
            assert {k: r0[k] for k in common.STATE_KEYS} == dict(phase_in, carry=0) and o0 == data['ram_before.bin'] and p0 == phase_pvc
            assert po0 == MARKER and r0['bank_base'] == phase_bank and r0['external_reads'] == 0x12345678 and r0['status'] == 1
            taken = phase['_trace']['pcs'][1]
            outcomes = {}
            for probe in (1, 2):
                again = inv('c%03d_cons%d_%03d' % (row['index'], probe, j), exe, data['ram_before.bin'], dict(phase_in, carry=probe), phase_pvc, phase_bank,
                            resources, stop=phase['stop_pc'], external=fx['external'])
                outcomes[probe] = again
            clear_pc, set_pc = 0x197b2, 0x197a6
            matching = 1 if taken == clear_pc else 2
            assert taken in (clear_pc, set_pc)
            assert outcomes[matching][0]['ok'] and outcomes[matching][1] == ram and outcomes[matching][2] == pvc, (row['label'], j)
            other = outcomes[3 - matching]
            # the other carry value takes the other BCC arm: reported (the native did not execute it)
            acc['consumer_probes'].append(dict(label=row['label'], phase=j, native_arm=hex(taken), matching_C=CARRY_NAME[matching],
                                               unknown_error=e0.strip(), other_arm_ok=other[0]['ok'], other_arm_differs=other[1] != ram))
            totals['consumer_probes'] += 1
        else:
            if first in CONSUMERS_ALL or any(i > 0 and pc in CONSUMERS_ALL and classify_carry(instructions, 1, executed[:i], computed) !=
                   classify_carry(instructions, 2, executed[:i], computed) for i, pc in enumerate(executed)):
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
                    if len(blocks) == 1 and blocks[0] == first and all(pc in st['instructions'] for pc in executed):
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
        acc['outputs'].append((sha(ram), tuple(state[k] for k in common.REGS + ('pc',)), sha(pvc), bank))
    control_rows = 0
    for phase in row['continuous_control']:
        if phase['guard'] is not None:
            continue
        step = phase['step']
        if policy_step is not None and step >= policy_step:
            if step == policy_step:
                c_ram, c_state, c_pvc, c_bank = step_starts[step]
                r0, o0, p0, po0, e0 = inv('c%03d_policy_control_%d' % (row['index'], step), exe, c_ram, dict(c_state, carry=2), c_pvc, c_bank, resources,
                                          stop=phase['stop_pc'], external=fx['external'])
                assert not r0['ok'] and e0.strip() == UNSUPPORTED_SP and o0 == c_ram and p0 == c_pvc and po0 == MARKER, (row['label'], e0)
                totals['computed_pc_policy_control_rejections'] += 1
            continue
        c_ram, c_state, c_pvc, c_bank = step_starts[step]
        data = phase['_data']
        e_pvc, e_bank, portbytes = fold_outputs(c_pvc, c_bank, phase['_trace']['events'])
        assert e_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
        assert {k: c_state[k] for k in common.REGS + ('pc',)} == phase['incoming']
        actual = inv('c%03d_control_%d' % (row['index'], step), exe, c_ram, c_state, c_pvc, c_bank, resources, stop=phase['stop_pc'], external=fx['external'])
        assert actual[0]['ok'] and not actual[4], (row['label'], actual[4])
        u2.check_result(actual, dict(outgoing=phase['outgoing'], events=phase['_trace']['events'], ram_after=data['ram_after.bin']), e_pvc, e_bank, portbytes)
        assert (actual[1], {k: actual[0][k] for k in common.STATE_KEYS}, actual[2], actual[0]['bank_base']) == step_ends[step], (row['label'], step)
        control_rows += 1
    if row['group'] == 'natural-chain':
        assert row['steps'][-1]['stop_pc'] == FF000 and state['pc'] == FF000 and state['a7'] == S + 4
        acc['chain'] = dict(case=fx['seed']['case'], ram=ram, state=dict(state), bank=bank, ports=bytes(all_ports), pvc=pvc)
    totals['cases'] += 1
    totals['split'] += len(stops)
    totals['control'] += control_rows
    acc['out_row'] = dict(index=row['index'], label=row['label'], group=row['group'], seed=fx['seed']['kind'], seed_start=how, start_kind=kind,
                          pvc_page=pvc_how, declared_initial_registers=declared, entry_pc=hex(fx['entry_pc']),
                          step_stop_pcs=[hex(s['stop_pc']) for s in row['steps']], split_phases=len(stops), control_steps=control_rows,
                          steps=len(row['steps']), carry=dict(sorted(carry_row.items())), guarded=bool(row['guarded']),
                          C_phase_digest_sha256=digest.hexdigest())
    acc['seed_kind'] = kind
    acc['declared_start'] = (sha(acc['start'][0]), tuple(acc['start'][1][k] for k in common.REGS + ('pc',)), sha(acc['start'][2]), acc['start'][3])
    unload_row(row)
    return acc


def compare(exe, rows, resources, st, scene_in, base_rams, program, instructions):
    totals = collections.Counter()
    program_reads = collections.Counter(fixed_reads=0, bank_reads=0, PVC_writes=0)
    carry_hist = collections.Counter({0: 0, 1: 0, 2: 0})
    preserved = {}
    first_pcs, seed_kinds = collections.Counter(), collections.Counter()
    out_rows, guards, starts_by_label, outputs = [], [], {}, set()
    declared_starts, consumer_probes, chains, policy = [], [], {}, []
    start_set = set(st['starts'])
    ctx = (exe, resources, st, scene_in, base_rams, program, instructions)

    def guarded_run(r):
        try:
            return run_row(r, ctx)
        except Exception:
            return dict(error=traceback.format_exc())
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(guarded_run, rows))
    failures = [(row['label'], acc['error']) for row, acc in zip(rows, results) if 'error' in acc]
    if failures:
        for n, (label, text) in enumerate(failures[:25]):
            print('ROW FAILED', label, text.strip().splitlines()[-1])
            if n < 3:
                print(text)
        raise AssertionError('%d rows failed' % len(failures))
    for row, acc in zip(rows, results):
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
        starts_by_label[row['label']] = acc['start']
        outputs.update(acc['outputs'])
        declared_starts.append((row['label'], row['group'], acc['declared_start'], acc['seed_kind']))
        consumer_probes.extend(acc['consumer_probes'])
        policy.extend(acc['policy'])
        if acc['chain'] is not None:
            chains[row['label']] = acc['chain']
    reproduced, not_reproduced = [], []
    for label, group, start, kind in declared_starts:
        if kind == 'rebuilt':
            continue
        (reproduced if start in outputs else not_reproduced).append(label)
    for pc, slots in preserved.items():
        assert pc in start_set and all(slots.values()) == (pc in st['preserving']), (hex(pc), slots)
    totals = dict(sorted(totals.items()))
    totals['carry_histogram'] = {CARRY_NAME[k]: v for k, v in sorted(carry_hist.items())}
    totals['guard_rows'] = len(guards)
    totals['u5_block_starts_run_as_first_pc_of_actual_cpp_phases'] = len(start_set & set(first_pcs))
    totals['single_block_u5_starts_probed'] = len(preserved)
    totals['single_block_u5_starts_carry_preserving'] = sum(all(s.values()) for s in preserved.values())
    totals['start_kinds'] = dict(sorted(seed_kinds.items()))
    totals['declared_native_starts_reproduced_by_actual_cpp_chain'] = len(reproduced)
    totals['declared_native_starts_not_reproduced'] = len(not_reproduced)
    return out_rows, totals, guards, starts_by_label, dict(program_reads), sorted(not_reproduced), sorted(reproduced), consumer_probes, chains, first_pcs, policy


# ----------------------------------------------------------------------------------------------------------------- guards
def expected_guard_error(label, guard):
    """Exact C++ checked error derived from the native guard record (problem class + access kind + target), not from the C++ output."""
    problem = guard['problem']
    if problem == 'unsupported_code_target':
        target = guard['target']
        if target & 1:
            return UNALIGNED_PC
        if in_ranges(target, ROUTED):
            return UNSUPPORTED_SP
        return UNSUPPORTED_MACHINE
    address = guard['address']
    if problem == 'unsupported_odd_data_access':
        if guard['access'] == 'read':
            return EVEN
        return EVEN if 0x1f0000 <= address < 0x200000 and 'push' in label else EVEN_WRITE
    assert problem == 'unmapped_or_protected'
    # writes to read-only / non-RAM addresses (label rom-write, odd copy overrunning into the 200000 window)
    if 'rom-write-A7-push' in label:
        return RAM_MIRROR
    if 'rom-write' in label or 'copy-length-odd' in label:
        return WRITE_DEVICE
    return None


def compare_guards(exe, guards, resources):
    rows, mismatches, divergences = [], [], []
    for row, phase, ram, state, pvc, bank, step_start in guards:
        fx = row['fixture']
        label = row['label']
        want = expected_guard_error(label, phase['guard'])
        cases = [('phase', ram, state, pvc, bank, phase['stop_pc'])]
        if (ram, state, pvc, bank) != (step_start[0], step_start[1], step_start[2], step_start[3]):
            cases.append(('whole_step', step_start[0], step_start[1], step_start[2], step_start[3], phase['step_stop_pc']))
        entry = {}
        diverged = False
        for kind, r, s, p, b, stp in cases:
            s = dict(s, carry=2)
            result, outgoing, out_pvc, ports, error = inv('guard_%s_%s' % (label, kind), exe, r, s, p, b, resources, stop=stp, external=fx['external'])
            if result['ok']:
                diverged = True
                entry[kind] = 'ok (no error)'
                continue
            if want is not None and error.strip() != want:
                mismatches.append((label, kind, error.strip(), want))
            assert {k: result[k] for k in common.STATE_KEYS} == s
            assert outgoing == r and out_pvc == p and result['bank_base'] == b
            assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1
            entry[kind] = error.strip()
        if diverged or want is None:
            divergences.append(dict(label=label, native_guard=phase['guard'], checked_API_result=entry))
        rows.append(dict(label=label, native_guard=phase['guard'], expected_error=want, checked_API_errors=entry, all_API_outputs_preserved=not diverged,
                         native_fault_rollback_equivalence_claimed=False))
    assert not mismatches, mismatches
    return rows, divergences


# ----------------------------------------------------------------------------------------------------------------- full frames
def frame_window(compare_record):
    lo = int(compare_record['stack_window'][0], 16) - 0x100000
    hi = int(compare_record['stack_window'][1], 16) - 0x100000
    assert 0xe000 <= lo <= 0xeffc and hi == 0xf000
    return lo, hi


def run_frame(i, ctx):
    exe, resources, scene_in, native_frame, bank_state = ctx
    record, ram0, regs14 = scene_in[i]
    pvc, bank = u2.pvc_page(bank_state[1], bank_state[2]), bank_state[0]
    ram = u2.apply_initial_writes(ram0, [dict(address=S, size=4, hex='000ff000')])
    state = dict(regs14, a5=A5V, a7=S, pc=0x1a73c, carry=0)
    result, out_ram, out_pvc, ports, error = inv('frame%04d' % i, exe, ram, state, pvc, bank, resources, stop=FF000)
    assert result['ok'] and not error and result['status'] == 0 and result['external_reads'] == 0, (i, error)
    res = dict(case=i, family=native_frame['family'], final_pc=result['pc'], final_a7=result['a7'], bank=result['bank_base'], a5=result['a5'])
    # 1. recorded original (flat map) run
    out = {}
    assert result['pc'] == FF000 == record['final_pc'] and result['a7'] == record['final_a7'] == S + 4 and result['bank_base'] == record['final_bank']
    assert all(result[k] == record['result'][k] for k in vsf.KEYS), (i, [k for k in vsf.KEYS if result[k] != record['result'][k]])
    orig_ram = (ROOT / 'artifacts/scene_frame_execution' / record['ram_file']).read_bytes()
    orig_ports = (ROOT / 'artifacts/scene_frame_execution' / record['ports_file']).read_bytes()
    assert sha(orig_ram) == record['ram_sha256'] and sha(orig_ports) == record['ports_sha256']
    lo, hi = frame_window(native_frame['compare'])
    diff = [k for k in range(0x10000) if out_ram[k] != orig_ram[k] and not lo <= k < hi]
    assert not diff, (i, [(hex(k), out_ram[k], orig_ram[k]) for k in diff[:6]])
    assert ports == orig_ports and len(ports) // 9 == record['port_count'] == native_frame['compare']['port_count'], i
    # 2. native machine-style full-frame record (full 64 KiB image incl. the stack window, ports)
    assert sha(out_ram) == native_frame['outgoing_ram_sha256'] and sha(ports) == native_frame['ports_sha256'], i
    res.update(window=(lo, hi), window_bytes=hi - lo, ports=len(ports) // 9, ram_sha256=sha(out_ram), ports_sha256=sha(ports))
    # 3. continuous == split at the U4 entry stop 1a7a8 (resume only from the previous actual C++ output)
    split = None
    if '0x1a7a8' in record['calls']:
        r1, ram1, pvc1, ports1, e1 = inv('frame%04d_a' % i, exe, ram, state, pvc, bank, resources, stop=0x1a7a8)
        assert r1['ok'] and r1['pc'] == 0x1a7a8 and not e1, (i, e1)
        s1 = {k: r1[k] for k in common.STATE_KEYS}
        r2, ram2, pvc2, ports2, e2 = inv('frame%04d_b' % i, exe, ram1, s1, pvc1, r1['bank_base'], resources, stop=FF000)
        assert r2['ok'] and not e2
        assert ram2 == out_ram and pvc2 == out_pvc and ports1 + ports2 == ports and r2['bank_base'] == result['bank_base']
        assert {k: r2[k] for k in common.STATE_KEYS} == {k: result[k] for k in common.STATE_KEYS}
        split = True
    res['split_at_1a7a8_equal'] = split
    return res, dict(ram=out_ram, ports=ports, state={k: result[k] for k in common.STATE_KEYS}, bank=result['bank_base'])


def full_frames(exe, resources, scene_in, report, chains, chain_rows):
    frames = report['full_frame']['rows']
    assert [f['case'] for f in frames] == list(range(594))
    bank_states = set(tuple(r['fixture']['bank_state']) for r in chain_rows)
    assert len(bank_states) == 1
    bank_state = list(bank_states.pop())
    assert bank_state == [0x200000, 160, 4096]
    sample = chain_rows[0]['fixture']
    assert sha(u2.pvc_page(bank_state[1], bank_state[2])) == sample['initial_PVC_sha256']
    ctx = (exe, resources, scene_in, None, bank_state)
    indices = list(range(594)) if not DEBUG_FRAMES else list(range(DEBUG_FRAMES))

    def one(i):
        try:
            return run_frame(i, (exe, resources, scene_in, frames[i], bank_state))
        except Exception:
            return dict(error=traceback.format_exc()), None
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(one, indices))
    failures = [(i, r[0]['error']) for i, r in zip(indices, results) if 'error' in r[0]]
    if failures:
        for n, (i, text) in enumerate(failures[:10]):
            print('FRAME FAILED', i, text.strip().splitlines()[-1])
            if n < 2:
                print(text)
        raise AssertionError('%d frames failed' % len(failures))
    rows = [r[0] for r in results]
    outs = {i: r[1] for i, r in zip(indices, results)}
    # the 19 natural chains (three actual C++ steps) end in exactly the full-frame result of their case
    chain_match = []
    for label, chain in sorted(chains.items()):
        i = chain['case']
        if i not in outs:
            continue
        o = outs[i]
        assert chain['ram'] == o['ram'] and chain['ports'] == o['ports'] and chain['bank'] == o['bank'] and chain['state'] == o['state'], label
        chain_match.append(label)
    fam = collections.Counter(f['family'] for f in rows)
    entries = dict(script=0, placement=0)
    for f, n in zip(rows, frames):
        entries['script'] += n['u5_entries']['script']
        entries['placement'] += n['u5_entries']['placement']
    summary = dict(frames=len(rows), families=dict(sorted(fam.items())), registers_equal=len(rows), ports_equal=len(rows), bank_equal=len(rows),
                   final_a7_equal=len(rows), ram_equal_outside_stack_window=len(rows), ram_full_image_equal_native_record=len(rows),
                   split_at_1a7a8_equal=sum(1 for f in rows if f['split_at_1a7a8_equal']), total_ports=sum(f['ports'] for f in rows),
                   chains_equal_full_frame=len(chain_match), window_min_bytes=min(f['window_bytes'] for f in rows),
                   window_max_bytes=max(f['window_bytes'] for f in rows), windows=sorted(set('%x..%x' % f['window'] for f in rows)),
                   native_u5_script_entries=entries['script'], native_u5_placement_entries=entries['placement'])
    return rows, summary


# ----------------------------------------------------------------------------------------------------------------- API-only checks
SUPERSEDED_NEGATIVES = []      # negatives whose PC is executed by a later unit in the final state (recorded, not silently deleted)


def negatives(exe, base, st, resources, cpp_text, instructions):
    out = []
    r0, s0, p0, b0 = base
    start_set = set(st['starts'])

    def reject(label, start, changes=None, stop=FF000, external=0, error_expected=None):
        r, s, p, b = start
        s = dict(s, carry=2)
        s.update(changes or {})
        result, outgoing, out_pvc, ports, error = inv('negative_' + label, exe, r, s, p, b, resources, stop=stop, external=external)
        assert not result['ok'], label
        assert error_expected is None or error.strip() == error_expected, (label, error.strip(), error_expected)
        assert error.strip().startswith(('unsupported animation', 'program bus', 'invalid animation', 'animation machine', 'unaligned', 'script placement'))
        assert {k: result[k] for k in common.STATE_KEYS} == s
        assert outgoing == r and out_pvc == p and ports == MARKER and result['bank_base'] == b
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        out.append(dict(label=label, error=error.strip(), all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False))

    # interior PCs of the routed ranges: bundled branches, mid-block instructions, operand words, the two PC-relative data tables
    interior = [pc for low, high in ROUTED for pc in range(low, high, 2) if pc not in start_set]
    for pc in interior:
        reject('interior_direct_entry_%06x' % pc, base, {'pc': pc}, error_expected=UNSUPPORTED_SP)
    bundled_rejected = [pc for pc in st['bundled'] if pc in interior]
    assert sorted(bundled_rejected) == sorted(st['bundled'])
    data_rejected = [pc for low, high in DATA_RANGES for pc in range(low, high, 2) if pc in interior]
    assert len(data_rejected) == 16
    # interior PCs of the two cleanup cases (existing executor): reported with their own checked error
    cleanup_interior = []
    for pc in range(0x43e08, 0x43e34, 2):
        if pc in start_set:
            continue
        r, s, p, b = base
        s = dict(s, carry=2, pc=pc)
        result, outgoing, out_pvc, ports, error = inv('negative_cleanup_interior_%06x' % pc, exe, r, s, p, b, resources, stop=FF000)
        assert not result['ok'] and outgoing == r and out_pvc == p and ports == MARKER and result['bank_base'] == b
        cleanup_interior.append((pc, error.strip()))
    # neighbours just outside every routed range (own executors or none) and the unrouted gaps
    outside = (0x3db2, 0x3db4, 0x16ff0, 0x19768, 0x1976a, 0x1a07a, 0x1a414, 0x1a416, 0xe89f8, 0xe8a0c, 0xe8a0e, 0x1a5a4)
    # API-only controls for these frozen inputs; no native execution equality claim.
    successful_outside = (0x1a07a, 0x1a414)
    outside_errors = {0x1976a: 'unsupported animation stage entry PC', 0x1a416: 'unsupported animation stage entry PC', 0x19768: 'program bus requires even WORD/LONG address', 0x1a5a4: 'unaligned animation machine PC'}
    for pc in outside:
        if pc not in successful_outside and pc not in outside_errors:
            reject('outside_range_entry_%06x' % pc, base, {'pc': pc}, error_expected=UNSUPPORTED_MACHINE)
            continue
        state = dict(s0, carry=2, pc=pc)
        result, outgoing, out_pvc, ports, error = inv('superseded_outside_range_entry_%06x' % pc, exe, r0, state, p0, b0, resources, stop=0xff000, external=0)
        row = dict(label='outside_range_entry_%06x' % pc, former_expected_API_error=UNSUPPORTED_MACHINE,
                   API_only_control=True, native_execution_equivalence_claimed=False, native_exception_rollback_equivalence_claimed=False)
        if pc in outside_errors:
            assert not result['ok'] and error.strip() == outside_errors[pc], (hex(pc), error.strip(), result)
            assert {k: result[k] for k in common.STATE_KEYS} == state
            assert outgoing == r0 and out_pvc == p0 and ports == MARKER and result['bank_base'] == b0
            assert result['external_reads'] == 0x12345678 and result['status'] == 1
            row.update(observed_final_state_error=error.strip(), all_API_outputs_preserved=True)
        else:
            assert result['ok'] and not error.strip() and result['pc'] == 0xff000 and result['status'] == 0, (hex(pc), error.strip(), result)
            row.update(observed_final_state=dict(ok=True, pc=hex(result['pc'])))
        SUPERSEDED_NEGATIVES.append(row)
    # odd PCs (alignment is checked before routing)
    for pc in (0x1a0b7, 0x1a471, 0x3d7f, 0x16fef, 0x19773, 0xe89fb, 0x43e09, 0x1a0bd):
        reject('odd_pc_entry_%06x' % pc, base, {'pc': pc}, error_expected=UNALIGNED_PC)
    # unknown carry at the single consumer block
    reject('consumer_197a2_unknown_carry', base, {'pc': CONSUMER, 'carry': 0}, error_expected=UNKNOWN_CARRY)
    # stops that the unit never reaches (interior PCs / unrouted PCs, the entry runs to the RTS first)
    for stop, pc in ((0x1a0b8, 0x1a0b6), (0x1a1ec, 0x1a1d0), (0x3d80, 0x3d7e), (0x1a4a0, 0x1a470)):
        reject('unreachable_stop_%06x_from_%06x' % (stop, pc), base, {'pc': pc}, stop=stop, error_expected=None)   # the run ends in a checked error before the stop; the string depends on the state
    return out, len(interior), cleanup_interior


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


def former_unsupported(exe, base, resources):
    """The five PCs used as 'unsupported' stops/entries by the older verifiers are routed now: report what a direct entry does."""
    ram, state, pvc, bank = base
    rows = []
    for pc in (0x1a0b6, 0x1a470, 0x16fee, 0x3d7e, 0xe89fa):
        s = dict(state, pc=pc, carry=2)
        zero = inv('former_zero_%06x' % pc, exe, ram, s, pvc, bank, resources, stop=pc)
        assert zero[0]['ok'] and zero[1] == ram
        run = inv('former_run_%06x' % pc, exe, ram, s, pvc, bank, resources, stop=FF000)
        assert run[4].strip() != UNSUPPORTED_MACHINE, hex(pc)      # no longer an unsupported PC (the state is a natural script state, not a placement/16fee state)
        rows.append(dict(pc=hex(pc), zero_step_ok=True, run_ok=run[0]['ok'], run_error=run[4].strip()))
    return rows


def older_verifier_negatives():
    found = []
    pat = re.compile(r'0x1a0b6|0x1a470|0x16fee|0x3d7e|0xe89fa|1a0b6|1a470|16fee|3d7e|e89fa')
    for path in sorted((ROOT / 'tools').glob('verify_animation_machine_*.py')):
        if path.name in ('verify_animation_machine_script_placement.py',):
            continue
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if pat.search(line) and ('UNSUPPORTED' in line or 'unsupported' in line or 'outside' in line or 'stop' in line or 'BOUNDARY' in line or
                                      'for stop' in line):
                found.append('%s:%d %s' % (path.name, number, line.strip()[:170]))
    return found


# ----------------------------------------------------------------------------------------------------------------- main
def main():
    global RUN_DIR
    assert OUT.resolve() == (ROOT / 'artifacts/animation_machine_script_placement_execution').resolve()
    if OUT.exists():
        shutil.rmtree(OUT)          # only this verifier's own output folder
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    RUN_DIR = Path(tempfile.mkdtemp(prefix='script_placement_verify_'))
    try:
        run(report_path)
    finally:
        shutil.rmtree(RUN_DIR, ignore_errors=True)


def run(report_path):
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_script_placement.py', 'tools/verify_animation_machine_scene_update.py',
                 'tools/verify_animation_machine_scene_core.py', 'tools/verify_animation_machine_card_child.py',
                 'tools/verify_stage_frame.py', 'tools/observe_animation_machine_script_placement.py', 'tools/observe_scene_frame_execution.py',
                 'docs/analysis/animation-machine-script-placement-u5-contract.md', 'engine/src/animation_machine_script_placement.cpp',
                 'engine/src/animation_machine_cleanup.cpp', 'engine/src/animation_machine.cpp', 'engine/src/animation_machine_internal.h',
                 'engine/tests/animation_machine_script_placement_test.cpp'):
        inputs[name] = cc.digest(ROOT / name)
    for path in (Path(sys.executable).resolve(), Path(shutil.which('clang++')).resolve()):
        inputs[str(path)] = cc.digest(path)
    program, source = load_verified_program(ROOT)
    rom = ROOT / source['path']
    rom_guard = cc.digest(rom), rom.stat().st_mtime_ns
    resources, refs = common.resource_audit(ROOT, program)
    exe, command = compile_harness(ROOT, OUT)
    report, native_inputs = audit_report(program, source)
    st = audit_static(report, program, source)
    instructions = u4.RomInstructions(program)
    rows = report['results'] + report['guarded_results']
    assert len(rows) == 658
    only = os.environ.get('SCRIPT_PLACEMENT_ONLY')
    if only:
        rows = [r for r in rows if any(s in r['label'] for s in only.split(','))]
    elif DEBUG_ROWS:
        rows = rows[:DEBUG_ROWS] + report['guarded_results'] + [r for r in report['results'] if r['group'] == 'natural-chain'][:2]
    scene_in, scene_files = u2.rebuild_scene_inputs()
    prov = report['seed_provenance']
    for path, expected in scene_files.items():
        assert prov['files'][path.replace(str(ROOT), MAIN_ROOT)] == expected, path
    base_rams = native_tables(report)
    (matches, totals, guards, starts_by_label, program_reads, not_reproduced, reproduced, consumer_probes, chains,
     first_pcs, policy) = compare(exe, rows, resources, st, scene_in, base_rams, program, instructions)
    start_set = set(st['starts'])
    # block starts executed as the first PC of an actual C++ phase; the two cleanup cases and the unreached ones are covered by the zero-step run
    assert DEBUG_ROWS or set(report['artifacts']) <= VERIFIED_ARTIFACTS, len(set(report['artifacts']) - VERIFIED_ARTIFACTS)
    guarded, divergences = compare_guards(exe, guards, resources)
    chain_rows = [r for r in rows if r['group'] == 'natural-chain']
    frame_rows, frame_summary = full_frames(exe, resources, scene_in, report, chains, chain_rows)
    base = starts_by_label['natural-scene-script-237-1a0b6-1']
    base = (base[0], dict(base[1]), base[2], base[3])
    cpp_text = (ROOT / 'engine/src/animation_machine_script_placement.cpp').read_text()
    negative, interior_count, cleanup_interior = negatives(exe, base, st, resources, cpp_text, instructions)
    zero = zero_step(exe, base, resources, st['starts'])
    former = former_unsupported(exe, base, resources)
    cpp_cases = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', cpp_text))
    cleanup_cases = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', (ROOT / 'engine/src/animation_machine_cleanup.cpp').read_text()))
    sp_starts = start_set - set(CLEANUP_STARTS)
    cpp_not_contract = sorted(cpp_cases - sp_starts)
    contract_not_cpp = sorted(sp_starts - cpp_cases)
    assert cpp_not_contract == [] and contract_not_cpp == [], ([hex(p) for p in cpp_not_contract], [hex(p) for p in contract_not_cpp])
    assert set(CLEANUP_STARTS) <= cleanup_cases
    for name, expected in list(inputs.items()) + list(native_inputs.items()):
        assert cc.digest(ROOT / name if not name.startswith('/') else name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    manifest = '\n'.join('%s %s' % (k, report['artifacts'][k]) for k in sorted(report['artifacts']))
    refs = dict(refs)
    refs.update(scene_files)
    for path in (OUT / 'harness.cpp', OUT / 'compile.log'):
        refs[str(path.resolve())] = cc.digest(path)
    census = report['first_boundary_census']
    result = dict(
        schema_version=1, source=source, inputs=inputs, native_inputs_checked=len(native_inputs), artifacts=refs,
        native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA, contract_sha256=CONTRACT_SHA,
        native_artifact_manifest=dict(count=len(report['artifacts']), every_file_read_and_hash_checked=DEBUG_ROWS == 0,
                                      sorted_name_hash_lines_sha256=sha(manifest.encode())),
        contract_ranges=st['table'], block_start_count=len(st['starts']), block_starts=[hex(p) for p in st['starts']],
        bundled_branch_count=len(st['bundled']), bundled_branches=[hex(p) for p in st['bundled']],
        carry_preserving_blocks=[hex(p) for p in st['preserving']], carry_preserving_count=len(st['preserving']),
        carry_consumer_blocks=[hex(CONSUMER)], carry_producer_blocks=[],
        opcode_leader_derivation=dict(contract_not_derived=[], derived_not_contract=[hex(p) for p in st['derived_not_contract']]),
        cpp_case_labels=dict(script_placement_not_in_contract_block_starts=[hex(p) for p in cpp_not_contract],
                             contract_block_starts_without_script_placement_case=[hex(p) for p in contract_not_cpp],
                             cleanup_cases_for_43e08_43e22=sorted(hex(p) for p in cleanup_cases & set(CLEANUP_STARTS))),
        actual_CPP=dict(totals, matches=matches), original_program_read_audit=program_reads,
        declared_native_starts_not_reproduced_by_cpp_chain=len(not_reproduced), declared_native_starts_reproduced_by_cpp_chain=len(reproduced),
        declared_native_starts_reproduced_labels=reproduced[:50],
        consumer_197a2_probes=dict(count=len(consumer_probes), rows=consumer_probes[:20],
                                   all_unknown_carry_errors=all(p['unknown_error'] == UNKNOWN_CARRY for p in consumer_probes),
                                   other_arm_ok_count=sum(1 for p in consumer_probes if p['other_arm_ok']),
                                   other_arm_differs_count=sum(1 for p in consumer_probes if p['other_arm_differs'])),
        computed_pc_policy_rejections=policy, native_guards_checked_API=guarded, native_vs_cpp_guard_divergences=divergences,
        native_continuous_control_phases_replayed=totals['control'],
        full_frame_integration=dict(summary=frame_summary, rows=frame_rows,
                                    compared_fields='ordered port stream (bytes), 14 result registers, final PC/A7, final bank, RAM outside the stack window vs the recorded '
                                                    'original flat-map run; full 64KiB image and ports vs the native machine-style full-frame record'),
        superseded_negatives=SUPERSEDED_NEGATIVES, negatives=negative, negative_count=len(negative) + len(guarded), interior_PCs_rejected=interior_count,
        cleanup_interior_PCs_checked_errors=cleanup_interior,
        zero_step_count=len(zero), zero_step_blocks=len(st['starts']), zero_step_carries=[0, 1, 2],
        former_unsupported_PCs_now_routed=former, older_verifier_negatives_using_these_PCs_not_changed=older_verifier_negatives(),
        census=dict(states=census['states'], model_equal_runs=report['census_model_checks']['runs'], model_equal=report['census_model_checks']['equal'],
                    replayed_in_cpp=False),
        carry_check='C++ carry equals the source-opcode walk over native-executed PCs (ORI/ANDI CCR known, flow-only preserved incl. the BCC at 197a2, else Unknown; '
                    'U2 rules incl. the computed 1a2e0 carry); the only consumer is 197a2 (Unknown -> checked error); native SR never read',
        compile_command=command, failure=None, ROM_unchanged=True,
        limits=['Controlled fixtures (rebuilt scene_frame chain seeds, declared SHA-pinned native states, declared RAM/register/stack variants), not natural '
                'scheduler, IRQ or gameplay reachability; U5 is not reached by a natural 480bc frame (stage_entry/stage_frame).',
                'Captured 1a0b6/1a470 hit states and the variant fixtures are native states SHA-pinned in the native artifacts; only those listed as reproduced were '
                're-derived by an actual C++ chain output.',
                'Existing executors 18c06, 197da, 19802, 8da2, 43ffc, 17012, 1701a, 28ae, 43e38 run as whole results (RAM/regs/ports/bank); their interiors are not modelled here.',
                'Carry is a source-opcode classification (native SR is never read); the not-taken BCC arm at 197a2 has no native counterpart.',
                'Checked failures preserve API outputs, not original CPU fault rollback; interior / data / odd / outside direct entries have no native counterpart.',
                'The 5624-state census of the native observation is native model-vs-original evidence only; its states are not stored, so it is not replayed in C++.',
                'Stack window of the full-frame RAM comparison: the machine image mirrors the work RAM, the live stack (A7 starts at 1feffc) lives at image offsets '
                'effc downward, the flat-map original keeps it elsewhere; offsets [lo, f000) with lo from the native record are excluded vs the original (included in '
                'the full-image comparison with the native record).',
                'Native observation artifacts are audited by hash/trace consistency, not re-executed here.'],
        normalized_reference_paths=len(refs))
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=totals['cases'], split=totals['split'], control=totals['control'], resumes=totals['resumes'],
                          negatives=result['negative_count'], interior=interior_count, zero_step=len(zero), frames=frame_summary['frames'],
                          divergences=len(divergences), carry=totals['carry_histogram'], sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
