"""480bc frame helper bundle U2 (scene core 1a73c and its callees) native evidence vs the public machine API.

Controlled fixtures; no expected-register injection. The frozen native observation is an immutable input (this verifier never invokes the observer
main). Start states are rebuilt here: scene_frame_execution inputs from artifacts/scene_general_initialization (+ the case host writes / previous
recorded outputs) and stage_frame inputs from artifacts/stage_frame, each asserted equal to the SHA recorded in the observation's seed_provenance and
to the fixture RAM SHA; the 154 stage_entry_body / re-entry fixtures are declared native states whose SHA256-pinned RAM is taken from the native
artifacts (they are not rebuildable without re-running the original code and are reported as declared). C++ resumes only from the previous actual C++
output plus the host changes recorded in the native step. 1a0b6, 1a470, 1a7a8, 19812, 19844, 19910 are stop boundaries only in the frozen native observation (never executed by it); in the final state later units execute them (see superseded_guards / superseded_negatives).
Native SR is never read: C is a source-opcode classification (1a2e0 is the computed known carry of CMP.W + EORI #1,CCR).
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
import verify_stage_frame as vsf
import observe_scene_frame_execution as sfe
from disassemble_program import load_verified_program

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/animation_machine_scene_core_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_scene_core_native'
NATIVE_SHA = '2d52a025d243dc0b97777110aa79939bbd618fa73a6998bb2bb79e1de8d4661d'
NATIVE_TOOL_SHA = 'b106db99361028c225dfd2a18570604638a88c6c2e9641abd580caac1d2602cb'
CONTRACT_SHA = 'f71a0727a4e09290f257bc93ef72a5ac426ba82d2ebf0cc825b7aaa14111097a'
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
SCENE_OBS_SHA = 'fc060d8c4d74b43d8bdb424f07d99478da6534f86db1426d4d7e3bd93ddac9f2'
SCENE_SEED_SHA = '7cf8f965dd1b774eafff1ad73400eab54dca1a8373f8a75ce6cb14557ddffa6e'
STAGE_FRAME_SHA = '47645dd39e0df8241cb504cd637a99cdc751544b4ac47c9e1227d8d5705f53b5'
MARKER = cc.MARKER
M32 = 0xffffffff
S = 0x1feffc
A5V = 0x108000
ENTRY_1A73C = 0x1a73c
RETURN_FF000 = 0xff000
BOUNDARY_PCS = (0x19812, 0x19844, 0x19910, 0x1a0b6, 0x1a470, 0x1a7a8)
CONSUMERS_ALL = frozenset((0x1a756, 0x1a2c6, 0x1a302, 0x1a30e, 0x1a320, 0x1a32c, 0x1a344, 0x1a352, 0x4765c, 0xb4a38, 0xb4a6c))
CONSUMERS_U2 = (0x1a756, 0x1a2c6, 0x1a302, 0x1a30e, 0x1a320, 0x1a32c, 0x1a344, 0x1a352)
PRODUCERS = (0x1a2cc, 0x1a2e0, 0x1a356, 0x1a39a, 0x1a3a0)
EORI_1A2E0 = 0x1a2ec
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNSUPPORTED_CORE = 'unsupported animation scene core PC'
UNKNOWN_CARRY = 'scene core caller requires known carry'
WRITE_DEVICE = 'unsupported animation machine write device'
EVEN = 'program bus requires even WORD/LONG address'
EVEN_WRITE = 'invalid animation machine write size/alignment'
RAM_MIRROR = 'program bus write requires RAM mirror units'
UNALIGNED_PC = 'unaligned animation machine PC'
FLOW_ONLY = cc.FLOW_ONLY
CARRY_NAME = cc.CARRY_NAME
sha = cc.sha
# Native split stops that fall inside one C++ block merge into the next phase: the reviewed 289e executor returns its C from the entry block (28a8, 28ac)
# and the contract folds the BMI fall-through blocks 19c7e / 19cb6 into the preceding blocks 19c72 / 19caa (native leaders list still contains them).
ATOMIC_INTERNAL_STOPS = (0x28a8, 0x28ac, 0x19c7e, 0x19cb6)
GUARD_ERRORS = {
    'guard-odd-A1-condition-pointer': EVEN, 'guard-odd-A1-script-pointer': EVEN, 'guard-odd-A1-motion-record': EVEN,
    'guard-odd-A0-placement-pointer': EVEN, 'guard-odd-A5-first-write': EVEN_WRITE, 'guard-odd-A7-bsr-push': EVEN,
    'guard-odd-A7-rts': EVEN, 'guard-rom-write-A5': WRITE_DEVICE, 'guard-rom-write-A7-push': RAM_MIRROR,
    'guard-cond-index-2000': UNSUPPORTED_MACHINE, 'guard-cond-index-odd-0001': UNALIGNED_PC,
    'guard-cond-index-negative-8000': 'unsupported animation frame head h4 PC',
    'guard-bad-stop-19844-on-full-path-seed': UNSUPPORTED_MACHINE, 'guard-bad-stop-1a0b6-on-full-path-seed': UNSUPPORTED_MACHINE,
    'guard-bad-stop-1a470-on-full-path-seed': UNSUPPORTED_MACHINE}
# Superseded by later units (final state): the 19844 seed now runs on through the later cores and reaches these stops without error (observed: ok, pc == stop).
# The native guard records are unchanged; the former expectation is kept here and recorded in the report (superseded_guards), not silently deleted.
SUPERSEDED_GUARDS = {'guard-bad-stop-1a7a8-on-19844-seed': UNSUPPORTED_MACHINE, 'guard-bad-stop-19812-on-19844-seed': UNSUPPORTED_MACHINE}
SUPERSEDED_RECORDS = []
SUPERSEDED_NEGATIVES = []
OUTSIDE_EXECUTED_NOW = (0x19830, 0x19850, 0x1a40e, 0x1a7a8, 0x199d4, 0x19b50, 0x19b94, 0x19dee, 0x1a3c8, 0x1a5a4,
                        0x199d6, 0x1a440, 0x1a73a)    # beyond the first four, F1a executes them (stage controller scene / init blocks); the last three end in the stage entry executor's checked error (OUTSIDE_STAGE_ENTRY)
OUTSIDE_STAGE_ENTRY = (0x199d6, 0x1a440, 0x1a73a)      # observed final-state error 'unsupported animation stage entry PC' (F1a stage entry executor)
OUTSIDE_NEW_ERRORS = {0x19820: 'unsupported animation motion walk PC', 0x198ec: 'unsupported animation motion walk PC', 0x19920: 'unsupported animation motion walk PC'}
VERIFIED_ARTIFACTS = set()
RUN_DIR = None
WORKERS = 8
DEBUG_ROWS = int(os.environ.get('SCENE_CORE_DEBUG_ROWS', '0'))     # development switch only: the reported run is always the full set


def in_ranges(pc, ranges):
    return any(low <= pc < high for low, high in ranges)


def inv(label, *args, **kwargs):
    """common.invoke in a private scratch folder; the per-call files are removed (only the verdicts are reported)."""
    result = common.invoke(*((args[0], RUN_DIR, label) + args[1:]), **kwargs)
    for suffix in ('_input.bin', '_pvc_input.bin', '_ram.bin', '_pvc.bin', '_ports.bin', '_state.json'):
        (RUN_DIR / (label + suffix)).unlink()
    return result


# ----------------------------------------------------------------------------------------------------------------- contract text
def contract_text():
    return (ROOT / 'docs/analysis/animation-machine-scene-core-u2-contract.md').read_text()


def pc_list(line):
    return [int(x, 16) for x in re.findall(r'`([0-9a-f]{5})`', line)]


def parse_contract(program):
    lines = contract_text().splitlines()
    ranges, table = [], []
    for line in lines:
        if line.startswith('| `') and '..' in line:
            cells = [c.strip().strip('`') for c in line.strip('|').split('|')]
            low, high = (int(x, 16) for x in cells[0].split('..'))
            assert program[low:high].hex() == cells[1], cells[0]
            ranges.append((low, high))
            table.append(dict(range='%x..%x' % (low, high), size=high - low))
    assert len(ranges) == 20 and sum(h - l for l, h in ranges) == 1724
    starts = bundled = preserving = None
    for i, line in enumerate(lines):
        if line.startswith('- **Block 시작 PC (215개)**'):
            starts = pc_list(lines[i + 2])
        if line.startswith('- **묶인 조건분기 PC (84개'):
            bundled = pc_list(lines[i + 2])
        if line.startswith('- **Carry 보존(FLOW_ONLY-only) block (52개)**'):
            preserving = pc_list(line)
    assert starts and bundled and preserving and (len(starts), len(bundled), len(preserving)) == (215, 84, 52)
    assert len(set(starts)) == 215 and len(set(bundled)) == 84 and len(set(preserving)) == 52
    return tuple(ranges), table, starts, bundled, preserving


def static_blocks(instructions, starts):
    """Block extents from the original opcodes: a block ends at RTS/BRA/JMP, a conditional branch, JSR/BSR or the next start."""
    blocks = {}
    for start in starts:
        pcs, pc = [], start
        while True:
            item = instructions[pc]
            pcs.append(pc)
            name = item['mnemonic'].split('.')[0]
            end = name in ('rts', 'bra', 'jmp', 'jsr', 'bsr') or (name.startswith('b') and name not in ('btst', 'bset', 'bclr', 'bchg'))
            following = pc + item['size']
            if end or following in starts or following not in instructions:
                break
            pc = following
        blocks[start] = pcs
    return blocks


def derive_leaders(instructions, ranges):
    derived = set(low for low, _ in ranges)
    for pc, item in instructions.items():
        if not in_ranges(pc, ranges):
            continue
        name = item['mnemonic'].split('.')[0]
        target = re.search(r'\$([0-9a-f]+)$', item['op_str'])
        if name in ('beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble', 'bra', 'bsr', 'jsr') and target:
            derived.add(int(target.group(1), 16))
        if name in ('beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble', 'bsr', 'jsr',
                    'rts', 'bra', 'jmp'):
            derived.add(pc + item['size'])
    return set(pc for pc in derived if in_ranges(pc, ranges))


def branch_destinations(item):
    """(clear_pc, set_pc) of a BCC/BCS instruction, or None."""
    name = item['mnemonic'].split('.')[0]
    if name not in ('bcc', 'bcs'):
        return None
    target = int(re.search(r'\$([0-9a-f]+)$', item['op_str']).group(1), 16)
    fall = item['cpu_address'] + item['size']
    return (target, fall) if name == 'bcc' else (fall, target)


# ----------------------------------------------------------------------------------------------------------------- carry
def classify_carry(instructions, carry, pcs, computed):
    """Source-opcode C classification (no native SR): ORI/ANDI CCR known, EORI #1,CCR after the CMP.W of 1a2e0 is the computed known carry
    (`computed`), the 289e equal-compare branch is Clear and the ORI path Set, flow-only opcodes preserve, anything else makes C Unknown."""
    for index, pc in enumerate(pcs):
        item = instructions[pc]
        name = item['mnemonic'].split('.')[0]
        if name == 'ori' and item['op_str'] == '#$1, ccr':
            carry = 2
        elif name == 'andi' and item['op_str'] == '#$fe, ccr':
            carry = 1
        elif name == 'eori' and item['op_str'] == '#$1, ccr':
            assert pc == EORI_1A2E0 and computed is not None
            carry = computed
        elif pc == 0x289e:
            carry = 0
        elif pc == 0x28a4 and index + 1 < len(pcs) and pcs[index + 1] == 0x28ac and carry == 0:
            carry = 1
        elif name in FLOW_ONLY:
            pass
        else:
            carry = 0
    return carry


def computed_carry(pcs, ram, regs):
    """C after `CMP.W 541e(A5),D0 ; EORI #1,CCR` at 1a2e0 from the native incoming RAM: D0.W = WORD 5418(A5) (phase), borrow = phase < WORD 541e(A5)
    unsigned, EORI inverts it. Known: 2 = Set, 1 = Clear."""
    if EORI_1A2E0 not in pcs:
        return None
    assert pcs[0] == 0x1a2e0, pcs[:3]
    word = lambda disp: int.from_bytes(ram[(regs['a5'] + disp) & 0xffff:((regs['a5'] + disp) & 0xffff) + 2], 'big')
    borrow = word(0x5418) < word(0x541e)
    return 1 if borrow else 2


# ----------------------------------------------------------------------------------------------------------------- native rows
def load_row(row):
    """Read and hash-check the saved payload files of one row (the report's hashes), stored beside each phase."""
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


def audit_row(row, program, instructions):
    assert row['reproduced_twice'] and row['continuous_split_equivalent']
    assert bool(row['guarded']) == (row['group'] == 'guard' or row['label'].startswith('guard-'))
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
        executed = set(phase['_trace']['pcs'][:-1])
        assert not (executed & set(BOUNDARY_PCS)) and instructions.keys() >= executed, sorted(executed - set(instructions))[:5]
    return counts_split


def audit_report(program, source):
    path = NATIVE_DIR / 'observation.json'
    assert cc.digest(path) == NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_scene_core.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'docs/analysis/animation-machine-scene-core-u2-contract.md') == CONTRACT_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None and source['sha256'] == ROM_SHA
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['sha256'] == CONTRACT_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase', 'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['declared_register_changes_at_step_boundaries'] == []
    assert report['rom_stat_start'] == report['rom_stat_end'] and report['contract_discrepancies'] == []
    assert (report['cases'], report['guarded_cases'], report['split_steps'], report['control_steps']) == (393, 17, 18814, 393)
    assert (report['total_split_phases'], report['total_control_phases'], report['fresh_CPU_runs']) == (19184, 410, 2852)
    assert sorted(report['boundary_stop_pcs']) == sorted(BOUNDARY_PCS)
    inputs = {}
    for name, expected in report['inputs'].items():
        assert cc.digest(name) == expected, name
        inputs[name] = expected
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    assert cc.digest(report['oracle']['library']) == report['oracle']['library_sha256']
    return report, inputs


def audit_static(report, program, source):
    assert cc.digest(NATIVE_DIR / 'source.json') == report['artifacts']['source.json']
    VERIFIED_ARTIFACTS.add('source.json')
    static = json.loads((NATIVE_DIR / 'source.json').read_text())
    assert static['source'] == source
    ranges, table, starts, bundled, preserving = parse_contract(program)
    assert sorted(tuple(r) for r in static['u2_ranges']) == sorted(ranges)
    assert sorted(tuple(r) for r in report['new_ranges']) == sorted(ranges)
    assert sorted(tuple(r) for r in static['u1_entry_ranges']) == [(0x47642, 0x47672), (0x480bc, 0x480f2)]
    assert [tuple(r) for r in static['existing_ranges']] == [(0x289e, 0x28ae)] == [tuple(r) for r in report['existing_ranges']]
    instructions = {}
    for instruction in static['instructions']:
        at, size = instruction['rom_offset'], instruction['size']
        assert bytes(bytearray.fromhex(instruction['raw'])) == program[at:at + size]
        assert at == instruction['cpu_address']          # fixed CPU address == file offset
        instructions[at] = instruction
    for pc in BOUNDARY_PCS:
        assert pc not in instructions
    start_set = set(starts)
    assert all(in_ranges(pc, ranges) for pc in starts)
    covered = set(report['covered_PCs'])
    assert report['uncovered_u2_block_starts'] == [] and start_set <= covered
    assert start_set <= set(report['block_starts'])
    derived = derive_leaders(instructions, ranges)
    derived_not_contract = sorted(derived - start_set)
    contract_not_derived = sorted(start_set - derived)
    assert contract_not_derived == [] and derived_not_contract == [0x19c7e, 0x19cb6], (derived_not_contract, contract_not_derived)
    blocks = static_blocks(instructions, start_set)
    preserving_derived = sorted(pc for pc in starts if all(instructions[p]['mnemonic'].split('.')[0] in FLOW_ONLY for p in blocks[pc]))
    assert preserving_derived == sorted(preserving)
    consumers = sorted(pc for pc in starts if len(blocks[pc]) == 1 and branch_destinations(instructions[pc]) is not None)
    assert consumers == sorted(CONSUMERS_U2), [hex(p) for p in consumers]
    producers = sorted(pc for pc in starts if any(
        instructions[p]['mnemonic'].split('.')[0] in ('ori', 'andi', 'eori') and instructions[p]['op_str'].endswith('ccr') for p in blocks[pc]))
    assert producers == sorted(PRODUCERS), [hex(p) for p in producers]
    # every U2 instruction is in exactly one block or is a bundled conditional branch or an interior instruction
    inside = [pc for pc in instructions if in_ranges(pc, ranges)]
    bundled_set = set(bundled)
    assert bundled_set <= set(inside) and not (bundled_set & start_set)
    assert all(branch_destinations(instructions[pc]) is None or pc not in start_set or pc in CONSUMERS_U2 for pc in inside)
    return dict(static=static, ranges=ranges, table=table, starts=starts, bundled=bundled, preserving=preserving, instructions=instructions,
                blocks=blocks, derived_not_contract=derived_not_contract, consumers=consumers, producers=producers, inside=inside)


# ----------------------------------------------------------------------------------------------------------------- seeds
def apply_initial_writes(ram, writes):
    ram = bytearray(ram)
    for w in writes:
        raw = bytes.fromhex(w['hex']) if 'hex' in w else w['value'].to_bytes(w['size'], 'big')
        at = w['address'] & 0xffff
        assert at + len(raw) <= 0x10000
        ram[at:at + len(raw)] = raw
    return bytes(ram)


def rebuild_scene_inputs():
    """The 594 scene_frame_execution input states rebuilt from artifacts/scene_general_initialization + the case host writes (sfe.prepare) or the
    previous recorded native output; each checked against the recorded input_ram_sha256."""
    files = {}

    def pin(path, expect=None):
        data = Path(path).read_bytes()
        digest = sha(data)
        if expect is not None:
            assert digest == expect, str(path)
        files[str(path)] = digest
        return data

    obs_path = ROOT / 'artifacts/scene_frame_execution/observation.json'
    seed_path = ROOT / 'artifacts/scene_general_initialization/observation.json'
    obs = json.loads(pin(obs_path, SCENE_OBS_SHA))
    seeds = json.loads(pin(seed_path, SCENE_SEED_SHA))
    assert obs['cases'] == obs['completed_cases'] == len(obs['results']) == 594 and obs['failure'] is None
    out = []
    for index, row in enumerate(obs['results']):
        case = row['fixture']
        assert row['case_index'] == index and row['returned']
        if case.get('sequence_position', 0) > 0:
            prev = obs['results'][index - 1]
            assert prev['fixture'].get('sequence') == case['sequence']
            ram = bytearray(pin(obs_path.parent / prev['ram_file'], prev['ram_sha256']))
        else:
            seed = seeds['results'][case['seed_index']]
            ram = bytearray(pin(seed_path.parent / seed['ram_file'], seed['ram_sha256']))
        sfe.prepare(case, ram)
        assert sha(ram) == row['input_ram_sha256'] and len(ram) == 0x10000, index
        out.append((row, bytes(ram), {k: row['incoming'][k] for k in vsf.KEYS}))
    return out, files


def rebuild_stage_inputs():
    """Stage-0 cases of artifacts/stage_frame/verification.json whose trace enters 1a73c, rebuilt from the smoke() seeds / host writes or the
    previous recorded native output; each checked against input_sha256."""
    path = ROOT / 'artifacts/stage_frame/verification.json'
    assert cc.digest(path) == STAGE_FRAME_SHA
    files = {str(path): STAGE_FRAME_SHA}
    ver = json.loads(path.read_text())
    rows = ver['results']
    assert len(rows) == 96
    seed_rams, out = {}, {}
    for index, row in enumerate(rows):
        if row['incoming']['stage'] != 0 or not any(b['pc'] == ENTRY_1A73C for b in row['boundaries']):
            continue
        want = row['input_sha256']
        ram = None
        if index > 0 and rows[index - 1]['ram_sha256'] == want:
            data = (path.parent / rows[index - 1]['ram_file']).read_bytes()
            assert sha(data) == want
            files[str(path.parent / rows[index - 1]['ram_file'])] = want
            ram = data
        else:
            for seed in (0, 4, 25, 34):
                if seed not in seed_rams:
                    seed_rams[seed] = sfe.fixture(ROOT, dict(seed_index=seed))
                base = bytearray(seed_rams[seed][0])
                for w in row['host_writes']:
                    at = w['address'] - 0x100000
                    raw = bytes.fromhex(w['hex'])
                    base[at:at + len(raw)] = raw
                if sha(base) == want:
                    ram = bytes(base)
                    break
        assert ram is not None, row['label']
        out[row['label']] = (row, ram)
    assert len(out) == 64
    return out, files


def pvc_page(ff8, ff9):
    page = bytearray(8192)
    page[0x1ff0:0x1ff2] = ff8.to_bytes(2, 'big')
    page[0x1ff2:0x1ff4] = ff9.to_bytes(2, 'big')
    return bytes(page)


def build_pvc(fx):
    base, ff8, ff9 = fx['bank_state']
    candidates = [pvc_page(ff8, ff9), pvc_page(0, ff9)]
    hits = [i for i, page in enumerate(candidates) if sha(page) == fx['initial_PVC_sha256']]
    assert len(hits) >= 1, fx['label']
    return candidates[hits[0]], base, ('raw ff8/ff9' if hits[0] == 0 else 'ff8=0 after 1a74a')


def hexint(x):
    return int(x, 16) if isinstance(x, str) else x


def start_of_row(row, scene_in, stage_in, base_rams):
    """C++ start: independently rebuilt seed (scene_frame / stage_frame) or the pinned declared native state, plus the declared initial writes."""
    fx = row['fixture']
    seed = fx['seed']
    kind = seed['kind']
    regs_prov = None
    if kind == 'scene_frame_execution case':
        record, ram0, regs14 = scene_in[seed['case']]
        assert sha(ram0) == seed['input_ram_sha256'] == seed['recorded_input_ram_sha256'] == record['input_ram_sha256']
        assert seed['observation_sha256'] == SCENE_OBS_SHA and seed['initializer_observation_sha256'] == SCENE_SEED_SHA
        ram = apply_initial_writes(ram0, fx['initial_host_writes'])
        regs_prov = dict(regs14)
        how = 'rebuilt scene_frame input %d' % seed['case']
    elif kind == 'stage-frame verifier case':
        record, ram0 = stage_in[seed['verification_label']]
        assert sha(ram0) == seed['input_sha256'] == record['input_sha256'] and seed['verification_sha256'] == STAGE_FRAME_SHA
        ram = apply_initial_writes(ram0, fx['initial_host_writes'])
        regs_prov = dict(zip(vsf.KEYS, (hexint(x) for x in seed['registers'])))
        assert regs_prov == {k: record['incoming'][k] for k in vsf.KEYS}
        how = 'rebuilt stage_frame input %s' % seed['verification_label']
    else:
        assert kind in ('stage_entry_body case', 'declared re-entry from the original full-frame run'), kind
        ram = base_rams(fx['initial_RAM_sha256'])
        if kind != 'stage_entry_body case':
            regs_prov = {k: hexint(v) for k, v in seed['registers'].items()}
        how = 'declared native state (SHA-pinned native artifact)'
    assert sha(ram) == fx['initial_RAM_sha256'], row['label']
    pvc, bank, pvc_how = build_pvc(fx)
    assert fx['checkpoints'] == []
    regs = dict(fx['initial_regs'])
    assert set(regs) == set(vsf.KEYS) | {'a5'}
    declared = []
    if regs_prov is not None:
        regs_prov['a5'] = A5V
        declared = sorted(k for k in regs if regs_prov[k] != regs[k])
    expected_a7 = hexint(seed['a7']) if 'a7' in seed else (S - 4 if kind == 'stage_entry_body case' else S)
    if fx['initial_a7'] != expected_a7:
        declared.append('a7')
    state = dict(regs, a7=fx['initial_a7'], pc=fx['entry_pc'], carry=0)
    return ram, state, pvc, bank, declared, how, pvc_how


def native_base_rams(rows):
    """sha -> path of the phase-0 RAM image of a row without host changes (the declared base states of re-entry / stage_entry fixtures)."""
    table = {}
    for row in rows:
        phase = row['phases'][0]
        if not phase['host_changes']:
            name = [n for n in phase['artifacts'] if n.endswith('_ram_before.bin')][0]
            table[phase['artifacts'][name]] = NATIVE_DIR / name

    def get(want):
        data = table[want].read_bytes()
        assert sha(data) == want
        return data
    return get


# ----------------------------------------------------------------------------------------------------------------- phases
def apply_changes(ram, state, changes, entry):
    ram = bytearray(ram)
    state = dict(state)
    kinds = []
    for change in changes:
        assert change['kind'] == 'ram'
        assert change['pc_before'] == entry['pc'] and change['a7_before'] == entry['a7'], change
        at, size = change['address'] & 65535, change['size']
        assert 0 <= at <= 65536 - size
        common.native.put(ram, change['address'], size, change['value'])
        kinds.append('ram')
    return bytes(ram), state, kinds


def merge_phases(phases):
    groups, pending = [], []
    for phase in phases:
        pending.append(phase)
        if phase['stop_pc'] in ATOMIC_INTERNAL_STOPS and phase['guard'] is None:
            continue
        if len(pending) == 1:
            groups.append(phase)
        else:
            first, last = pending[0], pending[-1]
            merged = dict(first, stop_pc=last['stop_pc'], outgoing=last['outgoing'], modeled_bank=last['modeled_bank'],
                          guard=last['guard'], ff8_after=last['ff8_after'], ff9_after=last['ff9_after'])
            pcs, events = [], []
            for part in pending:
                pcs.extend(part['_trace']['pcs'][:-1])
                events.extend(part['_trace']['events'])
            pcs.append(last['_trace']['pcs'][-1])
            merged['_trace'] = dict(last['_trace'], pcs=pcs, events=events)
            merged['_data'] = dict(first['_data'], **{k: last['_data'][k] for k in ('ram_after.bin', 'pvc_after.bin')})
            merged['_data']['ports.bin'] = b''.join(part['_data']['ports.bin'] for part in pending)
            groups.append(merged)
        pending = []
    assert not pending
    return groups


def check_result(actual, n, pvc, bank, portbytes):
    result, ram, device, ports, error = actual
    assert result['ok'] and not error
    assert {k: result[k] for k in common.REGS + ('pc',)} == n['outgoing'], {
        k: (n['outgoing'][k], result[k]) for k in common.REGS + ('pc',) if result[k] != n['outgoing'][k]}
    assert result['status'] == 0
    reads = sum(e['access'] == 'read' and e['address'] == 0xd00046 and e['size'] == 1 for e in n['events'])
    assert result['external_reads'] == reads == 0 and result['bank_base'] == bank, (reads, result['external_reads'], bank, result['bank_base'])
    assert ram == n['ram_after'], [(i, n['ram_after'][i], ram[i]) for i in range(len(ram)) if ram[i] != n['ram_after'][i]][:20]
    assert device == pvc, 'PVC mismatch'
    assert ports == portbytes, ('ports', ports.hex(), portbytes.hex())


def run_row(row, ctx):
    """One native row against the C++ API (independent of every other row; rows run concurrently, phases inside a row sequentially)."""
    exe, resources, st, scene_in, stage_in, base_rams, program, instructions = ctx
    start_set = set(st['starts'])
    acc = dict(totals=collections.Counter(), program_reads=collections.Counter(), carry_hist=collections.Counter(), preserved={},
               first_pcs=collections.Counter(), consumer_seen=collections.Counter(), computed_seen=collections.Counter(), guards=[], start=None)
    totals = acc['totals']
    load_row(row)
    counts = audit_row(row, program, instructions)
    acc['program_reads'].update(counts)
    fx = row['fixture']
    ram, state, pvc, bank, declared, how, pvc_how = start_of_row(row, scene_in, stage_in, base_rams)
    if declared:
        totals['declared_register_rows'] += 1
    expected_pvc, expected_bank = pvc, bank
    merged = merge_phases(row['phases'])
    totals['native_phases_merged_into_atomic_callee_returns'] += len(row['phases']) - len(merged)
    step_start = None
    digest = hashlib.sha256()
    stops = []
    last = None
    carry_row = collections.Counter()
    for j, phase in enumerate(merged):
        data = phase['_data']
        entry = dict(pc=state['pc'], a7=state['a7'])
        ram, state, kinds = apply_changes(ram, state, phase['host_changes'], entry)
        totals['declared_host_ram_changes'] += len(kinds)
        if j == 0:
            step_start = (ram, dict(state), pvc, bank)
            acc['start'] = step_start
        else:
            assert not phase['host_changes']
        assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming'], (row['label'], j)
        assert ram == data['ram_before.bin'], (row['label'], j)
        if phase['guard'] is not None:
            assert j == len(merged) - 1 and row['guarded']
            acc['guards'].append((row, phase, ram, dict(state), pvc, bank, step_start))
            break
        assert bank == phase['bank_before']
        events = phase['_trace']['events']
        expected_pvc, expected_bank, portbytes = cc.fold_outputs(expected_pvc, expected_bank, events)
        assert expected_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
        phase_in, phase_pvc, phase_bank = dict(state), pvc, bank
        executed = phase['_trace']['pcs'][:-1]
        actual = inv('c%03d_split_%03d' % (row['index'], j), exe, ram, state, pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
        assert actual[0]['ok'] and not actual[4], (row['label'], j, hex(phase['stop_pc']), actual[4])
        check_result(actual, dict(outgoing=phase['outgoing'], events=events, ram_after=data['ram_after.bin']), expected_pvc, expected_bank, portbytes)
        result, ram, pvc, _, _ = actual
        computed = computed_carry(executed, data['ram_before.bin'], phase_in)
        if computed is not None:
            acc['computed_seen'][CARRY_NAME[computed]] += 1
        want_carry = classify_carry(instructions, state['carry'], executed, computed)
        assert result['carry'] == want_carry, (row['label'], j, hex(phase['outgoing']['pc']), result['carry'], want_carry)
        acc['carry_hist'][result['carry']] += 1
        carry_row[CARRY_NAME[result['carry']]] += 1
        first = executed[0] if executed else None
        if first is not None and first in start_set:
            acc['first_pcs'][first] += 1
        dest = branch_destinations(instructions[first]) if first in CONSUMERS_ALL else None
        if dest is not None:
            # a BCC/BCS consumer block reads the modeled C: the known C selects the native branch, the flipped one the other, nothing else changes
            assert phase_in['carry'] in (1, 2), (row['label'], j, hex(first))
            assert dest[phase_in['carry'] - 1] == phase['_trace']['pcs'][1], (row['label'], j)
            flipped = 3 - phase_in['carry']
            other = dest[flipped - 1]
            again = inv('c%03d_flip_%03d' % (row['index'], j), exe, data['ram_before.bin'], dict(phase_in, carry=flipped), phase_pvc,
                        phase_bank, resources, stop=other, external=fx['external'])
            assert again[0]['ok'] and not again[4] and again[0]['pc'] == other, (row['label'], j)
            assert again[1] == data['ram_before.bin'] and again[2] == phase_pvc and again[0]['carry'] == flipped
            assert {k: again[0][k] for k in common.REGS} == {k: phase_in[k] for k in common.REGS}
            assert again[0]['bank_base'] == phase_bank and again[0]['status'] == 0 and again[0]['external_reads'] == 0
            acc['consumer_seen'][first] += 1
            totals['consumer_flip_checks'] += 1
        elif any(i > 0 and pc in CONSUMERS_ALL and classify_carry(instructions, 1, executed[:i], computed) != classify_carry(instructions, 2, executed[:i], computed)
                 for i, pc in enumerate(executed)):
            totals['carry_probe_phases_skipped_path_dependent'] += 1      # a later consumer in the same phase would read the probed C: the probe changes the path
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
                if len(blocks) == 1 and blocks[0] == first:
                    slot = acc['preserved'].setdefault(first, {1: True, 2: True})
                    slot[probe] = slot[probe] and again[0]['carry'] == probe
        totals['carry_checks'] += 1
        state = {k: result[k] for k in common.STATE_KEYS}
        bank = result['bank_base']
        totals['reads'] += result['external_reads']
        totals['ports'] += len(portbytes) // 9
        totals['resumes'] += 1 if j else 0
        digest.update(struct.pack('>IIB', phase['stop_pc'], state['pc'], result['carry']) + hashlib.sha256(ram).digest() + hashlib.sha256(pvc).digest() +
                      struct.pack('>I', len(portbytes)))
        stops.append(phase['stop_pc'])
        if j == len(merged) - 1:
            last = (ram, dict(state), pvc, bank)
    control_rows = 0
    for phase in row['continuous_control']:
        if phase['guard'] is not None:
            continue
        c_ram, c_state, c_pvc, c_bank = step_start
        data = phase['_data']
        assert {k: c_state[k] for k in common.REGS + ('pc',)} == phase['incoming']
        e_pvc, e_bank, portbytes = cc.fold_outputs(c_pvc, c_bank, phase['_trace']['events'])
        assert e_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
        actual = inv('c%03d_control' % row['index'], exe, c_ram, c_state, c_pvc, c_bank, resources, stop=phase['stop_pc'], external=fx['external'])
        assert actual[0]['ok'] and not actual[4], (row['label'], actual[4])
        check_result(actual, dict(outgoing=phase['outgoing'], events=phase['_trace']['events'], ram_after=data['ram_after.bin']), e_pvc, e_bank, portbytes)
        assert (actual[1], {k: actual[0][k] for k in common.STATE_KEYS}, actual[2], actual[0]['bank_base']) == last
        control_rows += 1
    totals['cases'] += 1
    totals['split'] += len(stops)
    totals['control'] += control_rows
    acc['out_row'] = dict(index=row['index'], label=row['label'], group=row['group'], seed=seed_kinds_key(fx['seed']), seed_start=how, pvc_page=pvc_how,
                          declared_initial_registers=declared, entry_pc=hex(fx['entry_pc']), step_stop_pc=hex(row['steps'][0]['stop_pc']),
                          split_phases=len(stops), control_steps=control_rows, carry=dict(sorted(carry_row.items())),
                          guarded=bool(row['guarded']), C_phase_digest_sha256=digest.hexdigest())
    acc['seed_kind'] = how.split(' ')[0] + ' ' + how.split(' ')[1]
    unload_row(row)
    return acc


def compare(exe, rows, resources, st, scene_in, stage_in, base_rams, program, instructions):
    ctx = (exe, resources, st, scene_in, stage_in, base_rams, program, instructions)
    totals = collections.Counter()
    program_reads = collections.Counter(fixed_reads=0, bank_reads=0, PVC_writes=0)
    carry_hist = collections.Counter({0: 0, 1: 0, 2: 0})
    preserved = {}
    first_pcs, consumer_seen, computed_seen, seed_kinds = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    out_rows, guards, starts_by_label = [], [], {}
    for key in ('guard_rows', 'carry_checks'):
        totals[key] += 0
    start_set = set(st['starts'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        def guarded_run(r):
            try:
                return run_row(r, ctx)
            except Exception:
                return dict(error=traceback.format_exc())
        results = list(pool.map(guarded_run, rows))
        failures = [(row['label'], acc['error']) for row, acc in zip(rows, results) if 'error' in acc]
        if failures:
            for label, text in failures:
                print('ROW FAILED', label, text.strip().splitlines()[-1])
            raise AssertionError('%d rows failed' % len(failures))
        for row, acc in zip(rows, results):
            totals.update(acc['totals'])
            program_reads.update(acc['program_reads'])
            carry_hist.update(acc['carry_hist'])
            first_pcs.update(acc['first_pcs'])
            consumer_seen.update(acc['consumer_seen'])
            computed_seen.update(acc['computed_seen'])
            seed_kinds[acc['seed_kind']] += 1
            for pc, slots in acc['preserved'].items():
                slot = preserved.setdefault(pc, {1: True, 2: True})
                for probe in (1, 2):
                    slot[probe] = slot[probe] and slots[probe]
            guards.extend(acc['guards'])
            out_rows.append(acc['out_row'])
            r, s, p, b = acc['start']
            starts_by_label[row['label']] = (r, s, p, b)
    for pc, slots in preserved.items():
        assert pc in start_set and all(slots.values()) == (pc in st['preserving']), (hex(pc), slots)
    if not DEBUG_ROWS:
        assert set(st['consumers']) <= set(consumer_seen), sorted(hex(p) for p in set(st['consumers']) - set(consumer_seen))
        assert start_set <= set(first_pcs), sorted(hex(p) for p in start_set - set(first_pcs))
    totals = dict(sorted(totals.items()))
    totals['carry_histogram'] = {CARRY_NAME[k]: v for k, v in sorted(carry_hist.items())}
    totals['guard_rows'] = len(guards)
    totals['u2_block_starts_run_as_first_pc_of_actual_cpp_phases'] = len(start_set & set(first_pcs))
    totals['single_block_u2_starts_probed'] = len(preserved)
    totals['single_block_u2_starts_carry_preserving'] = sum(all(s.values()) for s in preserved.values())
    totals['consumer_flips_by_block'] = {hex(k): v for k, v in sorted(consumer_seen.items())}
    totals['computed_carry_1a2e0_phases'] = dict(sorted(computed_seen.items()))
    totals['seed_start_kinds'] = dict(sorted(seed_kinds.items()))
    return out_rows, totals, guards, starts_by_label, dict(program_reads)


def seed_kinds_key(seed):
    kind = seed['kind']
    if kind == 'scene_frame_execution case':
        return 'scene_frame case %d' % seed['case']
    if kind == 'stage-frame verifier case':
        return 'stage_frame %s' % seed['verification_label']
    if kind == 'stage_entry_body case':
        return 'stage_entry_body case %d' % seed['case']
    return 're-entry case %d %s hit %d' % (seed['case'], seed['pc'], seed['hit'])


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
            if label in SUPERSEDED_GUARDS:
                assert result['ok'] and not error.strip() and result['pc'] == stp and result['status'] == 0, (label, kind, error.strip())
                entry[kind] = dict(ok=True, pc=hex(result['pc']), error='')
                continue
            assert not result['ok'], (label, kind)
            if error.strip() != GUARD_ERRORS[label]:
                mismatches.append((label, kind, error.strip()))
            assert {k: result[k] for k in common.STATE_KEYS} == s
            assert outgoing == r and out_pvc == p and result['bank_base'] == b
            assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1
            entry[kind] = error.strip()
        if label in SUPERSEDED_GUARDS:
            SUPERSEDED_RECORDS.append(dict(label=label, native_guard=phase['guard'], former_expected_API_error=SUPERSEDED_GUARDS[label],
                                           observed_final_state=entry, native_fault_rollback_equivalence_claimed=False))
            continue
        rows.append(dict(label=label, native_guard=phase['guard'], checked_API_errors=entry, all_API_outputs_preserved=True,
                         native_fault_rollback_equivalence_claimed=False))
    assert not mismatches, mismatches
    assert sorted(GUARD_ERRORS) == sorted(r['label'] for r in rows)
    assert sorted(SUPERSEDED_GUARDS) == sorted(r['label'] for r in SUPERSEDED_RECORDS)
    return rows


def negatives(exe, base, starts_by_label, st, resources):
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

    # interior instruction addresses and operand words inside the 20 contract ranges: every even PC that is not a block start
    interior = [pc for pc in st['inside'] if pc not in start_set]
    for pc in interior:
        reject('interior_direct_entry_%06x' % pc, base, {'pc': pc}, error_expected=UNSUPPORTED_CORE)
    operand = [pc for low, high in st['ranges'] for pc in range(low, high, 2) if pc not in instructions and pc not in start_set]
    for pc in operand:
        reject('operand_word_direct_entry_%06x' % pc, base, {'pc': pc}, error_expected=UNSUPPORTED_CORE)
    def supersede(label, start, changes, former, stop=0xff000):
        # superseded negative (later units execute this PC now): pin and record the observed final-state result instead of a failure
        r, s, p, b = start
        s = dict(s, carry=2)
        s.update(changes)
        changes_pc = changes.get('pc')
        result, outgoing, out_pvc, ports, error = inv('superseded_' + label, exe, r, s, p, b, resources, stop=stop, external=0)
        expected_error = 'unsupported animation stage entry PC' if changes_pc in OUTSIDE_STAGE_ENTRY else None
        if expected_error is not None:
            assert not result['ok'], (label, 'expected rejection')
            # F1a executes this PC too, but the run ends in a state-dependent checked error (another executor's message / a bus error): pin the observed string, require full preservation
            assert error.strip() == 'unsupported animation stage entry PC', (label, error.strip())
            assert changes_pc not in OUTSIDE_STAGE_ENTRY or error.strip() == 'unsupported animation stage entry PC', (label, error.strip())
            assert {k: result[k] for k in common.STATE_KEYS} == s and outgoing == r and out_pvc == p and ports == MARKER and result['bank_base'] == b
            assert result['external_reads'] == 0x12345678 and result['status'] == 1
            SUPERSEDED_NEGATIVES.append(dict(label=label, former_expected_API_error=former, observed_final_state_error=error.strip(), all_API_outputs_preserved=True,
                                             native_exception_rollback_equivalence_claimed=False, API_only_control=True, native_execution_equivalence_claimed=False))
            return
        assert result['ok'] and not error.strip() and result['pc'] == stop and result['status'] == 0, (label, error.strip())
        SUPERSEDED_NEGATIVES.append(dict(label=label, former_expected_API_error=former, observed_final_state=dict(ok=True, pc=hex(result['pc'])),
                                         native_exception_rollback_equivalence_claimed=False, API_only_control=True, native_execution_equivalence_claimed=False))

    for pc in BOUNDARY_PCS:
        supersede('boundary_direct_entry_%06x' % pc, base, {'pc': pc}, UNSUPPORTED_MACHINE)
    outside = (0x19820, 0x19830, 0x19850, 0x198ec, 0x19920, 0x199d4, 0x199d6, 0x19a3e, 0x19b50, 0x19b94, 0x19dee, 0x1a3a6, 0x1a3ac, 0x1a3c8,
               0x1a40e, 0x1a440, 0x1a5a4, 0x1a73a, 0x1a7a8)
    for pc in outside:
        if not in_ranges(pc, st['ranges']):
            if pc in OUTSIDE_EXECUTED_NOW:
                supersede('outside_range_entry_%06x' % pc, base, {'pc': pc}, UNSUPPORTED_MACHINE)
            else:
                # 19820/198ec/19920 are routed to the motion walk executor now (checked error with that executor's message)
                reject('outside_range_entry_%06x' % pc, base, {'pc': pc}, error_expected=OUTSIDE_NEW_ERRORS.get(pc, UNSUPPORTED_MACHINE))
    # unknown carry at the eight consumers (stop at the clear branch target: the error comes first)
    for pc in sorted(CONSUMERS_U2):
        r, s, p, b = base
        s2 = dict(s, pc=pc, carry=0)
        dest = branch_destinations(instructions[pc])
        result, outgoing, out_pvc, ports, error = inv('negative_unknown_carry_%06x' % pc, exe, r, s2, p, b, resources, stop=dest[0], external=0)
        assert not result['ok'] and error.strip() == UNKNOWN_CARRY, (hex(pc), error)
        assert {k: result[k] for k in common.STATE_KEYS} == s2 and outgoing == r and out_pvc == p and ports == MARKER
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        out.append(dict(label='unknown_carry_consumer_%06x' % pc, error=error.strip(), all_API_outputs_preserved=True,
                        native_exception_rollback_equivalence_claimed=False))
    # known carry at the same consumers must succeed in both directions (API controls)
    controls = []
    for pc in sorted(CONSUMERS_U2):
        dest = branch_destinations(instructions[pc])
        for carry in (1, 2):
            r, s, p, b = base
            s2 = dict(s, pc=pc, carry=carry)
            result, out_ram, out_pvc, ports, error = inv('control_consumer_%06x_%d' % (pc, carry), exe, r, s2, p, b, resources, stop=dest[carry - 1])
            assert result['ok'] and not error and result['pc'] == dest[carry - 1] and result['carry'] == carry and out_ram == r and out_pvc == p
            controls.append(dict(pc=pc, carry=CARRY_NAME[carry], to=dest[carry - 1]))
    # non-boundary stops on the full-path start (reaches 1a7a8): full rollback
    full = starts_by_label['natural-scene-full-path-0036']
    for stop in (0xff000, 0x19812, 0x19844, 0x19910, 0x1a0b6, 0x1a470, 0x1a73e, 0x1a2c2):
        if stop == 0xff000:
            # superseded: with no reachable stop the full path now runs through the later cores and reaches PC ff000 without error
            supersede('full_path_start_with_stop_%06x' % stop, full, {}, UNSUPPORTED_MACHINE, stop=stop)
        else:
            reject('full_path_start_with_stop_%06x' % stop, full, stop=stop, error_expected=UNSUPPORTED_MACHINE)
    # positive control: the same start with the matching boundary stop
    s = dict(full[1], carry=0)
    result, out_ram, out_pvc, ports, error = inv('control_full_path_stop_1a7a8', exe, full[0], s, full[2], full[3], resources, stop=0x1a7a8)
    assert result['ok'] and not error and result['pc'] == 0x1a7a8
    controls.append(dict(entry=hex(ENTRY_1A73C), stop='0x1a7a8', ok=True, a7=result['a7']))
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
    for pc in BOUNDARY_PCS:
        s = dict(state, pc=pc, carry=2)
        result, out_ram, out_pvc, ports, error = inv('zero_boundary_%06x' % pc, exe, ram, s, pvc, bank, resources, stop=pc)
        assert {k: result[k] for k in common.STATE_KEYS} == s and out_ram == ram and out_pvc == pvc
        rows.append(dict(pc=hex(pc), ok=result['ok'], error=error.strip()))
    return rows


def main():
    global RUN_DIR
    assert OUT.resolve() == (ROOT / 'artifacts/animation_machine_scene_core_execution').resolve()
    if OUT.exists():
        shutil.rmtree(OUT)          # only this verifier's own output folder
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    RUN_DIR = Path(tempfile.mkdtemp(prefix='scene_core_verify_'))
    try:
        run(report_path)
    finally:
        shutil.rmtree(RUN_DIR, ignore_errors=True)


def run(report_path):
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_scene_core.py', 'tools/verify_animation_machine_card_child.py', 'tools/verify_stage_frame.py',
                 'tools/observe_animation_machine_scene_core.py', 'tools/observe_scene_frame_execution.py',
                 'docs/analysis/animation-machine-scene-core-u2-contract.md', 'engine/src/animation_machine_scene_core.cpp',
                 'engine/src/animation_machine_internal.h', 'engine/tests/animation_machine_scene_core_test.cpp'):
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
    instructions = st['instructions']
    rows = report['results'] + report['guarded_results']
    assert len(rows) == 410
    if DEBUG_ROWS:
        rows = rows[:DEBUG_ROWS] + report['guarded_results']
    scene_in, scene_files = rebuild_scene_inputs()
    stage_in, stage_files = rebuild_stage_inputs()
    prov = report['seed_provenance']
    for path, expected in list(scene_files.items()) + list(stage_files.items()):
        assert prov['files'][path.replace(str(ROOT), '/Users/start/Workspce/metalslug')] == expected, path
    assert prov['scene_frame']['observation_sha256'] == SCENE_OBS_SHA and prov['scene_frame']['initializer_observation_sha256'] == SCENE_SEED_SHA
    assert prov['stage_frame']['verification_sha256'] == STAGE_FRAME_SHA and prov['stage_frame']['rebuilt_cases'] == 64
    base_rams = native_base_rams(rows)
    matches, totals, guards, starts_by_label, program_reads = compare(exe, rows, resources, st, scene_in, stage_in, base_rams, program, instructions)
    assert DEBUG_ROWS or VERIFIED_ARTIFACTS == set(report['artifacts']), (len(VERIFIED_ARTIFACTS), len(report['artifacts']))
    guarded = compare_guards(exe, guards, resources)
    base = starts_by_label['natural-scene-full-path-0036']
    base = (base[0], dict(base[1]), base[2], base[3])
    negative, interior_count, operand_count, controls = negatives(exe, base, starts_by_label, st, resources)
    zero = zero_step(exe, base, resources, st['starts'])
    boundary_zero = boundary_zero_step(exe, base, resources)
    cpp_text = (ROOT / 'engine/src/animation_machine_scene_core.cpp').read_text()
    cpp_cases = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', cpp_text))
    start_set = set(st['starts'])
    cpp_not_contract = sorted(cpp_cases - start_set)
    contract_not_cpp = sorted(start_set - cpp_cases)
    for name, expected in list(inputs.items()) + list(native_inputs.items()):
        assert cc.digest(ROOT / name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    manifest = '\n'.join('%s %s' % (k, report['artifacts'][k]) for k in sorted(report['artifacts']))
    refs = dict(refs)
    refs.update(scene_files)
    refs.update(stage_files)
    for path in (OUT / 'harness.cpp', OUT / 'compile.log'):
        refs[str(path.resolve())] = cc.digest(path)
    result = dict(
        schema_version=1, source=source, inputs=inputs, native_inputs_checked=len(native_inputs), artifacts=refs,
        native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA, contract_sha256=CONTRACT_SHA,
        native_artifact_manifest=dict(count=len(report['artifacts']), every_file_read_and_hash_checked=True,
                                      sorted_name_hash_lines_sha256=sha(manifest.encode())),
        contract_ranges=st['table'], block_start_count=len(st['starts']), block_starts=[hex(p) for p in st['starts']],
        bundled_branch_count=len(st['bundled']), carry_preserving_blocks=[hex(p) for p in st['preserving']],
        carry_preserving_count=len(st['preserving']), carry_consumer_blocks=[hex(p) for p in st['consumers']],
        carry_producer_blocks=[hex(p) for p in st['producers']],
        opcode_leader_derivation=dict(contract_not_derived=[], derived_not_contract=[hex(p) for p in st['derived_not_contract']],
                                      note='the two derived-only PCs 19c7e and 19cb6 are the contract-folded BMI fallthroughs'),
        cpp_case_labels=dict(cpp_not_in_contract_block_starts=[hex(p) for p in cpp_not_contract],
                             contract_block_starts_without_cpp_case=[hex(p) for p in contract_not_cpp]),
        actual_CPP=dict(totals, matches=matches), original_program_read_audit=program_reads,
        native_guards_checked_API=guarded, superseded_guards=SUPERSEDED_RECORDS, superseded_negatives=SUPERSEDED_NEGATIVES, native_continuous_control_phases_replayed=totals['control'],
        negatives=negative, negative_count=len(negative) + len(guarded), interior_PCs_rejected=interior_count,
        operand_word_PCs_rejected=operand_count, API_controls=controls,
        zero_step_count=len(zero), zero_step_blocks=len(st['starts']), zero_step_carries=[0, 1, 2], boundary_zero_step=boundary_zero,
        carry_check='C++ carry equals the source-opcode walk over native-executed PCs (ORI/ANDI CCR known, 1a2e0 CMP.W+EORI computed known from the '
                    'native incoming RAM, 289e equal-branch Clear, flow-only preserved, else Unknown); native SR never read',
        compile_command=command, failure=None, ROM_unchanged=True,
        limits=['Controlled fixtures (rebuilt scene_frame / stage_frame seeds, declared stage_entry_body and re-entry states, declared RAM/register/PC/'
                'return-LONG variants), not natural scheduler, IRQ or gameplay reachability.',
                'The 154 stage_entry_body (42) and declared re-entry (112) start states are native states SHA-pinned in the native artifacts; they are '
                'not rebuilt here (they need the original code run).',
                '1a0b6, 1a470, 1a7a8, 19812, 19844, 19910 are stop boundaries of the native observation, never executed there; later units (U3..U7) execute them in the final state and are verified by their own verifiers (direct entries and no-stop negatives are recorded as superseded).',
                'Carry is a source-opcode classification (native SR is never read).',
                'Checked failures preserve API outputs, not original CPU fault rollback; interior / operand / boundary direct entries and the Unknown-carry '
                'consumer entries have no native counterpart (API-only rejection).',
                'Native observation artifacts are audited by hash/trace consistency, not re-executed here.'],
        normalized_reference_paths=len(refs))
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=totals['cases'], split=totals['split'], control=totals['control'], resumes=totals['resumes'],
                          negatives=result['negative_count'], interior=interior_count, operand=operand_count, zero_step=len(zero),
                          carry=totals['carry_histogram'], sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
