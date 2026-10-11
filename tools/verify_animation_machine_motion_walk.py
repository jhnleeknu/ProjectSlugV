"""480bc frame helper bundle U3 (motion walk 18c06..19768, 19812, 19844, 19910) native evidence vs the public machine API.

Controlled fixtures; no expected-register injection. The frozen native observation is an immutable input (this verifier never invokes the observer
main). Start states: scene_frame_execution inputs are rebuilt from artifacts/scene_general_initialization (+ the case host writes / previous recorded
outputs), stage_frame inputs from artifacts/stage_frame, the 911 declared unit fixtures from the rebuilt scene_frame case 182 input RAM + the declared
stack writes; each is asserted equal to the SHA recorded in the observation. The stage_entry_body and the captured full-frame re-entry states are
declared native states whose SHA256-pinned RAM is taken from the native artifacts (not rebuildable without re-running the original code). C++ resumes
only from the previous actual C++ output plus the host changes recorded in the native step. Native SR is never read: C is a source-opcode
classification (1a2e0 is the computed known carry of CMP.W + EORI #1,CCR; U3: TST.W at 19710/1971c and AND.W at 1938e/19596 give known Clear).
19938..19978 (an extra range observed outside the contract, U5 caller) is expected-unsupported in C++ and is not part of the comparison.
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
MAIN = '/Users/start/Workspce/metalslug/'
OUT = ROOT / 'artifacts/animation_machine_motion_walk_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_motion_walk_native'
NATIVE_SHA = '411f3444d365d487dc2e5e8fca861c2117dd9aa21733af7f8537e514e9708968'
NATIVE_TOOL_SHA = 'c3112b04fbbeb54f76a77e8063099bdbe9231ce3cd2f2a95267368c922ae2d0b'
CONTRACT_SHA = 'fe5db3bd8d160296e71a82e5ddace169b9dd61b6dd15c0e61fd0b96f0fc6793d'
U2_CONTRACT_SHA = 'f71a0727a4e09290f257bc93ef72a5ac426ba82d2ebf0cc825b7aaa14111097a'
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
SCENE_OBS_SHA = 'fc060d8c4d74b43d8bdb424f07d99478da6534f86db1426d4d7e3bd93ddac9f2'
SCENE_SEED_SHA = '7cf8f965dd1b774eafff1ad73400eab54dca1a8373f8a75ce6cb14557ddffa6e'
STAGE_FRAME_SHA = '47645dd39e0df8241cb504cd637a99cdc751544b4ac47c9e1227d8d5705f53b5'
MARKER = cc.MARKER
S = 0x1feffc
A5V = 0x108000
ENTRY_1A73C = 0x1a73c
U2_BOUNDARY_PCS = (0x1a0b6, 0x1a470, 0x1a7a8)
FORMER_BOUNDARY_PCS = (0x19812, 0x19844, 0x19910)
EXTRA_RANGE = (0x19938, 0x19978)
CONSUMERS_U2 = (0x1a756, 0x1a2c6, 0x1a302, 0x1a30e, 0x1a320, 0x1a32c, 0x1a344, 0x1a352)
CONSUMERS_OTHER = (0x4765c, 0xb4a38, 0xb4a6c)
CONSUMERS_U3 = (0x196c0, 0x196e2, 0x19924, 0x19734, 0x198b8, 0x1974e, 0x19874, 0x19894, 0x198d8)
CONSUMERS_ALL = frozenset(CONSUMERS_U2 + CONSUMERS_OTHER + CONSUMERS_U3)
SET_PRODUCERS_U3 = (0x18c9e, 0x19394, 0x1959c, 0x196d8, 0x19716, 0x19724)
CLEAR_PRODUCERS_U3 = (0x18ca4,)
COMPUTED_CLEAR_BLOCKS = (0x19710, 0x1971c, 0x19372, 0x1957a)
TST_CLEAR_PCS = (0x19710, 0x1971c)
AND_CLEAR_PCS = (0x1938e, 0x19596)
CARRY_RETURN_BLOCKS = (0x1971a, 0x19728, 0x19398, 0x195a0)
PRODUCERS_U2 = (0x1a2cc, 0x1a2e0, 0x1a356, 0x1a39a, 0x1a3a0)
EORI_1A2E0 = 0x1a2ec
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNSUPPORTED_WALK = 'unsupported animation motion walk PC'
UNKNOWN_CARRY = 'motion walk caller requires known carry'
WRITE_DEVICE = 'unsupported animation machine write device'
EVEN = 'program bus requires even WORD/LONG address'
EVEN_WRITE = 'invalid animation machine write size/alignment'
RAM_MIRROR = 'program bus write requires RAM mirror units'
UNALIGNED_PC = 'unaligned animation machine PC'
API_STOP_PC = 'invalid animation machine RAM/PVC/stop PC'
FLOW_ONLY = cc.FLOW_ONLY
CARRY_NAME = cc.CARRY_NAME
sha = cc.sha
# Native split stops that fall inside one C++ block (the U2 reviewed rules; U3 has none: native stops in 18c06..19768 are exactly block starts or
# the computed out-of-table PCs of the out-of-range fixtures).
ATOMIC_INTERNAL_STOPS = (0x28a8, 0x28ac, 0x19c7e, 0x19cb6)
ODD_A1_LABELS = ('guard-odd-A1-18c06', 'guard-odd-A1-18caa', 'guard-odd-A1-18efa', 'guard-odd-A1-18fd2', 'guard-odd-A1-192c4', 'guard-odd-A1-19710',
                 'guard-odd-A1-1971c', 'guard-odd-A1-1972a', 'guard-odd-A1-19910', 'guard-odd-A1-196ac', 'guard-odd-A1-196de', 'guard-odd-A1-19812',
                 'guard-odd-A1-19844')
GUARD_ERRORS = dict((label, EVEN) for label in ODD_A1_LABELS)
GUARD_ERRORS.update({
    'guard-odd-A7-19812': EVEN, 'guard-odd-A7-rts': EVEN, 'guard-odd-A5-196b0': EVEN,
    'guard-rom-write-A5-196b0': WRITE_DEVICE, 'guard-rom-write-A7-19812': RAM_MIRROR,
    'guard-bad-stop-19758-unit': UNSUPPORTED_MACHINE, 'guard-bad-stop-1a0b6-unit': UNSUPPORTED_MACHINE,
    'guard-bad-stop-1a0b6-on-scene-0000': UNSUPPORTED_MACHINE, 'guard-bad-stop-1a7a8-on-scene-0237': UNSUPPORTED_MACHINE,
    'guard-bad-stop-1a470-on-scene-0000': UNSUPPORTED_MACHINE, 'guard-bad-stop-19758-on-scene-0000': UNSUPPORTED_MACHINE})
GUARD_OOR_PCS = {'guard-oor-18c06-type0001': 0x18c0f, 'guard-oor-18caa-type0002': 0x18cb4, 'guard-oor-18efa-type7ffe': 0x20f00,
                 'guard-oor-18fd2-type8000': 0x10fda, 'guard-oor-192c4-typeffff': 0x192cb, 'guard-oor-18c06-type00fe': 0x18d0c}
VERIFIED_ARTIFACTS = set()
RUN_DIR = None
WORKERS = 8
DEBUG_ROWS = int(os.environ.get('MOTION_WALK_DEBUG_ROWS', '0'))     # development switch only: the reported run is always the full set


def in_ranges(pc, ranges):
    return any(low <= pc < high for low, high in ranges)


def inv(label, *args, **kwargs):
    """common.invoke in a private scratch folder; the per-call files are removed (only the verdicts are reported)."""
    result = common.invoke(*((args[0], RUN_DIR, label) + args[1:]), **kwargs)
    for suffix in ('_input.bin', '_pvc_input.bin', '_ram.bin', '_pvc.bin', '_ports.bin', '_state.json'):
        (RUN_DIR / (label + suffix)).unlink()
    return result


def local(path):
    """Observation paths are absolute paths of the main checkout; read the same relative file through this worktree."""
    path = str(path)
    return ROOT / path[len(MAIN):] if path.startswith(MAIN) else Path(path)


# ----------------------------------------------------------------------------------------------------------------- contract text
def contract_text():
    return (ROOT / 'docs/analysis/animation-machine-motion-walk-u3-contract.md').read_text()


def pc_list(text):
    return [int(x, 16) for x in re.findall(r'`([0-9a-f]{5})`', text)]


def parse_contract(program):
    lines = contract_text().splitlines()
    ranges = []
    for line in lines:
        if line.startswith('| `') and '..' in line:
            cells = [c.strip().strip('`') for c in line.strip('|').split('|')]
            low, high = (int(x, 16) for x in cells[0].split('..'))
            assert program[low:high].hex() == cells[2], cells[0]
            assert int(cells[1]) == high - low
            ranges.append((low, high))
    assert len(ranges) == 9 and sum(h - l for l, h in ranges) == 3156, (len(ranges), sum(h - l for l, h in ranges))
    sel_s = sel_f = bundled = None
    producers_line = consumers_line = preserving_line = None
    for line in lines:
        if line.startswith('  - 선택 S(170개)'):
            sel_s = pc_list(line)
        elif line.startswith('  - 선택 F 추가(200개'):
            sel_f = pc_list(line)
        elif line.startswith('- **묶인 조건분기 PC (14개'):
            bundled = pc_list(line)
        elif line.startswith('- **Carry 소비 block (9개)**'):
            consumers_line = line
        elif line.startswith('- **Known carry 생산 block**'):
            producers_line = line
        elif line.startswith('- **Carry 보존(FLOW_ONLY) block**'):
            preserving_line = line
    assert sel_s and sel_f and bundled and consumers_line and producers_line and preserving_line
    assert (len(sel_s), len(sel_f), len(bundled)) == (170, 200, 14)
    assert len(set(sel_s)) == 170 and len(set(sel_f)) == 200 and not (set(sel_s) & set(sel_f))
    starts = sorted(set(sel_s) | set(sel_f))
    assert len(starts) == 370
    for pc in CONSUMERS_U3:
        assert '`%05x`' % pc in consumers_line, hex(pc)
    for pc in SET_PRODUCERS_U3 + CLEAR_PRODUCERS_U3 + COMPUTED_CLEAR_BLOCKS + CARRY_RETURN_BLOCKS:
        assert '`%05x`' % pc in producers_line, hex(pc)
    assert 'TST.W' in producers_line and 'AND.W' in producers_line
    after = preserving_line.split('선택 S 86개:')[1].split('선택 F는')[0]
    preserving_s = pc_list(after)
    assert len(preserving_s) == 86 and len(set(preserving_s)) == 86 and '211개' in preserving_line
    return tuple(ranges), starts, sorted(sel_s), sorted(sel_f), sorted(bundled), sorted(preserving_s)


SLOT_TABLES = ((0x18c0e, 0x18c9e), (0x18cb2, 0x18d42), (0x18f02, 0x18f92), (0x18fda, 0x1906a), (0x192cc, 0x1935c))


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


def consumer_info(instructions, pc):
    """(clear_pc, set_pc, instructions_before_target) of a carry-consuming block: BCC/BCS alone or MOVEM.L (A7)+ then BCC/BCS."""
    item = instructions[pc]
    dest = branch_destinations(item)
    if dest is not None:
        return dest + (1,)
    assert item['mnemonic'].split('.')[0] == 'movem', hex(pc)
    nxt = instructions[pc + item['size']]
    dest = branch_destinations(nxt)
    assert dest is not None, hex(pc)
    return dest + (2,)


# ----------------------------------------------------------------------------------------------------------------- carry
def classify_carry(instructions, carry, pcs, computed):
    """Source-opcode C classification (no native SR): ORI/ANDI CCR known, EORI #1,CCR after the CMP.W of 1a2e0 is the computed known carry
    (`computed`), U3: TST.W at 19710/1971c and AND.W at 1938e/19596 (blocks 19710, 1971c, 19372, 1957a) are known Clear, the 289e equal-compare
    branch is Clear and the ORI path Set, flow-only opcodes preserve, anything else makes C Unknown."""
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
        elif name == 'tst' and pc in TST_CLEAR_PCS:
            carry = 1
        elif name == 'and' and pc in AND_CLEAR_PCS:
            carry = 1
        elif name in FLOW_ONLY:
            pass
        else:
            carry = 0
    return carry


def computed_carry(pcs, ram, regs):
    """C after `CMP.W 541e(A5),D0 ; EORI #1,CCR` at 1a2e0 from the native incoming RAM (U2 rule)."""
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
        assert not (executed & set(U2_BOUNDARY_PCS)) and instructions.keys() >= executed, sorted(executed - set(instructions))[:5]
    return counts_split


def audit_report(program, source):
    path = NATIVE_DIR / 'observation.json'
    assert cc.digest(path) == NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_motion_walk.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'docs/analysis/animation-machine-motion-walk-u3-contract.md') == CONTRACT_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None and source['sha256'] == ROM_SHA
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['sha256'] == CONTRACT_SHA
    assert report['contract']['u2_contract_sha256'] == U2_CONTRACT_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase', 'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['declared_register_changes_at_step_boundaries'] == []
    assert report['rom_stat_start'] == report['rom_stat_end']
    assert (report['cases'], report['guarded_cases'], report['split_steps'], report['control_steps']) == (1333, 30, 45197, 1333)
    assert (report['total_split_phases'], report['total_control_phases']) == (45653, 1363)
    assert len(report['results']) == 1333 and len(report['guarded_results']) == 30
    assert report['u3']['block_start_count'] == 370 and report['u3']['uncovered_u3_block_starts'] == []
    inputs = {}
    for name, expected in report['inputs'].items():
        assert cc.digest(local(name)) == expected, name
        inputs[name] = expected
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    assert cc.digest(local(report['oracle']['library'])) == report['oracle']['library_sha256']
    return report, inputs


def audit_static(report, program, source):
    assert cc.digest(NATIVE_DIR / 'source.json') == report['artifacts']['source.json']
    VERIFIED_ARTIFACTS.add('source.json')
    static = json.loads((NATIVE_DIR / 'source.json').read_text())
    assert static['source'] == source
    ranges, starts, sel_s, sel_f, bundled, preserving_s = parse_contract(program)
    assert sorted(tuple(r) for r in static['u3_ranges']) == sorted(ranges)
    assert sorted(tuple(r) for r in report['new_ranges']) == sorted(ranges)
    assert [tuple(static['extra_range_outside_contract'])] == [EXTRA_RANGE]
    instructions = {}
    for instruction in static['instructions']:
        at, size = instruction['rom_offset'], instruction['size']
        assert bytes(bytearray.fromhex(instruction['raw'])) == program[at:at + size]
        assert at == instruction['cpu_address']          # fixed CPU address == file offset
        instructions[at] = instruction
    start_set = set(starts)
    assert all(in_ranges(pc, ranges) for pc in starts)
    assert start_set == set(report['u3']['block_starts']), 'observer vs contract block starts'
    # no byte gap: the U3 ranges decode into contiguous instructions
    inside = sorted(pc for pc in instructions if in_ranges(pc, ranges))
    assert inside[0] == 0x18c06
    for low, high in ranges:
        pcs = [pc for pc in inside if low <= pc < high]
        assert pcs[0] == low and pcs[-1] + instructions[pcs[-1]]['size'] == high
        for a, b in zip(pcs, pcs[1:]):
            assert a + instructions[a]['size'] == b, hex(a)
    derived = derive_leaders(instructions, ranges)
    assert derived == start_set, ([hex(p) for p in sorted(derived - start_set)], [hex(p) for p in sorted(start_set - derived)])
    blocks = static_blocks(instructions, start_set)
    # every instruction is in exactly one block, or is a bundled conditional branch
    covered = collections.Counter(pc for pcs in blocks.values() for pc in pcs)
    assert all(v == 1 for v in covered.values())
    bundled_set = set(bundled)
    assert set(inside) == set(covered) and bundled_set <= set(covered) and not (bundled_set & start_set)
    assert bundled_set == set(pcs[-1] for pcs in blocks.values() if len(pcs) > 1 and instructions[pcs[-1]]['mnemonic'].split('.')[0] in (
        'beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble')), 'bundled conditional branches = last instruction of multi-instruction blocks'
    for pc in bundled:
        name = instructions[pc]['mnemonic'].split('.')[0]
        assert name.startswith('b') and name not in ('bra', 'bsr', 'btst', 'bset', 'bclr', 'bchg')
    # derived classification
    preserving_derived = sorted(pc for pc in starts if all(instructions[p]['mnemonic'].split('.')[0] in FLOW_ONLY for p in blocks[pc]))
    slot_starts = sorted(pc for pc in sel_f if any(low <= pc < high for low, high in SLOT_TABLES))
    assert len(slot_starts) == 125, len(slot_starts)
    assert preserving_derived == sorted(preserving_s + slot_starts) and len(preserving_derived) == 211
    consumers = sorted(pc for pc in starts if instructions[blocks[pc][-1]]['mnemonic'].split('.')[0] in ('bcc', 'bcs') and
                       all(instructions[p]['mnemonic'].split('.')[0] in ('movem',) for p in blocks[pc][:-1]))
    assert consumers == sorted(CONSUMERS_U3), [hex(p) for p in consumers]
    producers = sorted(pc for pc in starts if any(
        instructions[p]['mnemonic'].split('.')[0] in ('ori', 'andi', 'eori') and instructions[p]['op_str'].endswith('ccr') for p in blocks[pc]))
    assert producers == sorted(SET_PRODUCERS_U3 + CLEAR_PRODUCERS_U3), [hex(p) for p in producers]
    computed = sorted(pc for pc in starts if any(instructions[p]['mnemonic'].split('.')[0] in ('tst', 'and') for p in blocks[pc]))
    assert computed == sorted(COMPUTED_CLEAR_BLOCKS)
    assert [p for pc in computed for p in blocks[pc] if instructions[p]['mnemonic'].split('.')[0] in ('tst', 'and')] == sorted(TST_CLEAR_PCS + AND_CLEAR_PCS)
    for pc in CARRY_RETURN_BLOCKS:
        assert pc in preserving_derived and blocks[pc] == [pc] and instructions[pc]['mnemonic'] == 'rts'
    return dict(static=static, ranges=ranges, starts=starts, sel_s=sel_s, sel_f=sel_f, bundled=bundled, preserving=preserving_derived,
                instructions=instructions, blocks=blocks, consumers=consumers, producers=producers, computed=computed, inside=inside,
                slot_starts=slot_starts)


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


def start_of_row(row, scene_in, stage_in, base_rams, base182):
    """C++ start: independently rebuilt seed or the pinned declared native state, plus the declared initial writes."""
    fx = row['fixture']
    seed = fx['seed']
    kind = seed['kind']
    regs_prov = None
    expected_a7 = S
    if kind == 'scene_frame_execution case':
        record, ram0, regs14 = scene_in[seed['case']]
        assert sha(ram0) == seed['input_ram_sha256'] == record['input_ram_sha256']
        assert seed['observation_sha256'] == SCENE_OBS_SHA and seed['initializer_observation_sha256'] == SCENE_SEED_SHA
        ram = apply_initial_writes(ram0, fx['initial_host_writes'])
        regs_prov = dict(regs14)
        how = 'rebuilt scene_frame input'
    elif kind == 'stage-frame verifier case':
        record, ram0 = stage_in[seed['verification_label']]
        assert sha(ram0) == seed['input_sha256'] == record['input_sha256'] and seed['verification_sha256'] == STAGE_FRAME_SHA
        ram = apply_initial_writes(ram0, fx['initial_host_writes'])
        regs_prov = dict(zip(vsf.KEYS, (hexint(x) for x in seed['registers'])))
        assert regs_prov == {k: record['incoming'][k] for k in vsf.KEYS}
        how = 'rebuilt stage_frame input'
    elif kind == 'declared unit fixture':
        assert seed['base_ram_sha256'] == sha(base182) and 'case 182' in seed['base_state']
        ram = apply_initial_writes(base182, fx['initial_host_writes'])
        how = 'rebuilt unit fixture (scene_frame case 182 input + declared stack writes)'
    elif kind == 'declared U3 entry captured from the original full-frame run':
        ram = base_rams(fx['initial_RAM_sha256'])
        regs_prov = {k: hexint(v) for k, v in seed['registers'].items()}
        expected_a7 = hexint(seed['a7'])
        parent = scene_in[seed['case']]
        assert sha(parent[1]) == seed['scene_input_ram_sha256'] == parent[0]['input_ram_sha256'] and seed['observation_sha256'] == SCENE_OBS_SHA
        stack = bytes.fromhex(seed['stack_hex'])
        at = expected_a7 & 0xffff
        assert ram[at:at + len(stack)] == stack and [w for w in fx['initial_host_writes'] if w['address'] == expected_a7 and w['hex'] == seed['stack_hex']]
        how = 'declared native state (SHA-pinned native artifact; parent scene_frame input rebuilt and matched)'
    else:
        assert kind == 'stage_entry_body case', kind
        ram = base_rams(fx['initial_RAM_sha256'])
        expected_a7 = S - 4
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
    if fx['initial_a7'] != expected_a7 and kind != 'declared unit fixture':
        declared.append('a7')
    state = dict(regs, a7=fx['initial_a7'], pc=fx['entry_pc'], carry=0)
    return ram, state, pvc, bank, declared, how, pvc_how


def native_base_rams(rows):
    """sha -> path of the phase-0 RAM image of a row without host changes (the declared base states of captured / stage_entry fixtures)."""
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


def expected_pc_error(pc, st):
    """Exact error for a run that reaches `pc` as the next block with no stop there (model of the routing + block start set)."""
    if pc & 1:
        return UNALIGNED_PC
    if pc in st['start_set']:
        return None
    if in_ranges(pc, st['ranges']):
        return UNSUPPORTED_WALK
    return UNSUPPORTED_MACHINE


def run_row(row, ctx):
    """One native row against the C++ API (independent of every other row; rows run concurrently, phases inside a row sequentially)."""
    exe, resources, st, scene_in, stage_in, base_rams, base182, program, instructions = ctx
    start_set = st['start_set']
    acc = dict(totals=collections.Counter(), program_reads=collections.Counter(), carry_hist=collections.Counter(), preserved={},
               first_pcs=collections.Counter(), executed_starts=collections.Counter(), consumer_seen=collections.Counter(),
               computed_seen=collections.Counter(), guards=[], start=None, extra=None, oor=None, visited=None)
    totals = acc['totals']
    load_row(row)
    counts = audit_row(row, program, instructions)
    acc['program_reads'].update(counts)
    fx = row['fixture']
    ram, state, pvc, bank, declared, how, pvc_how = start_of_row(row, scene_in, stage_in, base_rams, base182)
    if declared:
        totals['declared_register_rows'] += 1
    if row['group'] == 'fixture-flow-19938':
        # 19938..19978 is outside the contract: expected-unsupported. The C++ API must refuse the declared entry with the exact error and preserve
        # every output; the native phases (which execute the extra range) are audited but never compared.
        phase0 = row['phases'][0]
        entry = dict(pc=state['pc'], a7=state['a7'])
        ram2, state2, kinds = apply_changes(ram, state, phase0['host_changes'], entry)
        result, out_ram, out_pvc, ports, error = inv('c%05d_extra' % row['_uid'], exe, ram2, dict(state2, carry=2), pvc, bank, resources,
                                                     stop=row['steps'][0]['stop_pc'], external=fx['external'])
        assert not result['ok'] and error.strip() == UNSUPPORTED_MACHINE, (row['label'], error)
        assert {k: result[k] for k in common.STATE_KEYS} == dict(state2, carry=2) and out_ram == ram2 and out_pvc == pvc
        assert ports == MARKER and result['bank_base'] == bank and result['external_reads'] == 0x12345678 and result['status'] == 1
        executed = [pc for ph in row['phases'] for pc in ph['_trace']['pcs'][:-1]]
        assert any(EXTRA_RANGE[0] <= pc < EXTRA_RANGE[1] for pc in executed)
        totals['extra_range_rows_expected_unsupported'] += 1
        acc['extra'] = dict(index=row['index'], label=row['label'], entry_pc=hex(fx['entry_pc']), error=error.strip(), all_API_outputs_preserved=True,
                            native_phases_executing_extra_range=len(row['phases']))
        unload_row(row)
        return acc
    expected_pvc, expected_bank = pvc, bank
    merged = merge_phases(row['phases'])
    totals['native_phases_merged_into_atomic_callee_returns'] += len(row['phases']) - len(merged)
    step_start = None
    digest = hashlib.sha256()
    stops = []
    last = None
    carry_row = collections.Counter()
    visited = set()
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
        visited.update(phase['_trace']['pcs'])
        if phase['stop_pc'] & 1:
            # the native run stopped directly after the dispatcher JMP at an odd computed PC. The API refuses an odd stop PC, and running on reaches the
            # odd PC as the next block: both are exact checked errors with every output preserved (the dispatcher's own partial effect, D4.W only, is
            # not observable through the API).
            assert j == len(merged) - 1 and row['group'].startswith('fixture-out-of-range') and phase['outgoing']['pc'] == phase['stop_pc']
            assert executed and executed[0] in (0x18c06, 0x18caa, 0x18efa, 0x18fd2, 0x192c4) and len(executed) == 2 and instructions[executed[1]]['mnemonic'] == 'jmp'
            for stop, want in ((phase['stop_pc'], API_STOP_PC), (0xff000, UNALIGNED_PC)):
                odd_state = dict(state, carry=2)
                result, o_ram, o_pvc, o_ports, err = inv('c%05d_odd_%06x' % (row['_uid'], stop), exe, ram, odd_state, pvc, bank, resources, stop=stop,
                                                         external=fx['external'])
                assert not result['ok'] and err.strip() == want, (row['label'], hex(stop), err)
                assert {k: result[k] for k in common.STATE_KEYS} == odd_state and o_ram == ram and o_pvc == pvc and o_ports == MARKER
                assert result['bank_base'] == bank and result['external_reads'] == 0x12345678 and result['status'] == 1
            totals['odd_computed_pc_rows'] += 1
            acc['odd'] = True
            break
        actual = inv('c%05d_split_%03d' % (row['_uid'], j), exe, ram, state, pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
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
        for pc in executed:
            if pc in start_set:
                acc['executed_starts'][pc] += 1
        if any(pc in TST_CLEAR_PCS for pc in executed):
            totals['phases_with_TST_W_known_Clear_19710_1971c'] += 1
        if any(pc in AND_CLEAR_PCS for pc in executed):
            totals['phases_with_AND_W_known_Clear_1938e_19596'] += 1
        if first in CONSUMERS_ALL:
            # a BCC/BCS consumer block reads the modeled C: the known C selects the native branch, the flipped one the other, nothing else changes
            clear_pc, set_pc, n_before = consumer_info(instructions, first)
            dest = (clear_pc, set_pc)
            assert phase_in['carry'] in (1, 2), (row['label'], j, hex(first))
            assert dest[phase_in['carry'] - 1] == phase['_trace']['pcs'][n_before], (row['label'], j)
            flipped = 3 - phase_in['carry']
            other = dest[flipped - 1]
            again = inv('c%05d_flip_%03d' % (row['_uid'], j), exe, data['ram_before.bin'], dict(phase_in, carry=flipped), phase_pvc,
                        phase_bank, resources, stop=other, external=fx['external'])
            assert again[0]['ok'] and not again[4] and again[0]['pc'] == other, (row['label'], j)
            assert again[1] == data['ram_before.bin'] and again[2] == phase_pvc and again[0]['carry'] == flipped
            if n_before == 1:
                assert {k: again[0][k] for k in common.REGS} == {k: phase_in[k] for k in common.REGS}      # BCC/BCS alone changes only the PC
            else:
                # MOVEM.L (A7)+,D6-D7 then BCC/BCS: D6 = LONG (A7), D7 = LONG 4(A7), A7 += 8; nothing else changes
                at = phase_in['a7'] & 0xffff
                assert again[0]['d6'] == int.from_bytes(data['ram_before.bin'][at:at + 4], 'big')
                assert again[0]['d7'] == int.from_bytes(data['ram_before.bin'][at + 4:at + 8], 'big') and again[0]['a7'] == phase_in['a7'] + 8
                assert {k: again[0][k] for k in common.REGS if k not in ('d6', 'd7', 'a7')} == {
                    k: phase_in[k] for k in common.REGS if k not in ('d6', 'd7', 'a7')}
            assert again[0]['bank_base'] == phase_bank and again[0]['status'] == 0 and again[0]['external_reads'] == 0
            acc['consumer_seen'][first] += 1
            totals['consumer_flip_checks'] += 1
        elif any(i > 0 and pc in CONSUMERS_ALL and classify_carry(instructions, 1, executed[:i], computed) != classify_carry(instructions, 2, executed[:i], computed)
                 for i, pc in enumerate(executed)):
            totals['carry_probe_phases_skipped_path_dependent'] += 1      # a later consumer in the same phase would read the probed C: the probe changes the path
        else:
            for probe in (1, 2):
                again = inv('c%05d_carry%d_%03d' % (row['_uid'], probe, j), exe, data['ram_before.bin'], dict(phase_in, carry=probe), phase_pvc,
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
        if phase['guard'] is not None or phase['stop_pc'] & 1:
            continue
        c_ram, c_state, c_pvc, c_bank = step_start
        data = phase['_data']
        assert {k: c_state[k] for k in common.REGS + ('pc',)} == phase['incoming']
        e_pvc, e_bank, portbytes = cc.fold_outputs(c_pvc, c_bank, phase['_trace']['events'])
        assert e_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
        actual = inv('c%05d_control' % row['_uid'], exe, c_ram, c_state, c_pvc, c_bank, resources, stop=phase['stop_pc'], external=fx['external'])
        assert actual[0]['ok'] and not actual[4], (row['label'], actual[4])
        check_result(actual, dict(outgoing=phase['outgoing'], events=phase['_trace']['events'], ram_after=data['ram_after.bin']), e_pvc, e_bank, portbytes)
        assert (actual[1], {k: actual[0][k] for k in common.STATE_KEYS}, actual[2], actual[0]['bank_base']) == last
        control_rows += 1
    if row['group'].startswith('fixture-out-of-range') and merged and merged[-1]['guard'] is None:
        final_pc = merged[-1]['outgoing']['pc']
        # a computed target that is not a block start was only reached as the stop directly after the JMP; running on must fail with the exact error
        if final_pc not in start_set and not final_pc & 1:
            acc['oor'] = (row['label'], step_start, final_pc, fx['external'])
    acc['visited'] = visited if row['label'] in st['visited_wanted'] else None
    totals['cases'] += 1
    totals['split'] += len(stops)
    totals['control'] += control_rows
    acc['out_row'] = dict(index=row['index'], label=row['label'], group=row['group'], seed=seed_kinds_key(fx['seed']), seed_start=how, pvc_page=pvc_how,
                          declared_initial_registers=declared, entry_pc=hex(fx['entry_pc']), step_stop_pc=hex(row['steps'][0]['stop_pc']),
                          split_phases=len(stops), control_steps=control_rows, carry=dict(sorted(carry_row.items())),
                          guarded=bool(row['guarded']), C_phase_digest_sha256=digest.hexdigest())
    acc['seed_kind'] = how.split(' (')[0]
    unload_row(row)
    return acc


def seed_kinds_key(seed):
    kind = seed['kind']
    if kind == 'scene_frame_execution case':
        return 'scene_frame case %d' % seed['case']
    if kind == 'stage-frame verifier case':
        return 'stage_frame %s' % seed['verification_label']
    if kind == 'stage_entry_body case':
        return 'stage_entry_body case %d' % seed['case']
    if kind == 'declared unit fixture':
        return 'unit %s' % seed['entry']
    return 'captured case %d %s hit %d' % (seed['case'], seed['pc'], seed['hit'])


def compare(exe, rows, resources, st, scene_in, stage_in, base_rams, base182, program, instructions):
    ctx = (exe, resources, st, scene_in, stage_in, base_rams, base182, program, instructions)
    totals = collections.Counter()
    program_reads = collections.Counter(fixed_reads=0, bank_reads=0, PVC_writes=0)
    carry_hist = collections.Counter({0: 0, 1: 0, 2: 0})
    preserved = {}
    first_pcs, executed_starts, consumer_seen, computed_seen, seed_kinds = (collections.Counter() for _ in range(5))
    out_rows, guards, starts_by_label, extras, oors, visited = [], [], {}, [], [], {}
    for key in ('guard_rows', 'carry_checks'):
        totals[key] += 0
    start_set = st['start_set']
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        def guarded_run(r):
            try:
                return run_row(r, ctx)
            except Exception:
                return dict(error=traceback.format_exc())
        results = list(pool.map(guarded_run, rows))
        failures = [(row['label'], acc['error']) for row, acc in zip(rows, results) if 'error' in acc]
        if failures:
            for label, text in failures[:20]:
                print('ROW FAILED', label, '\n'.join(text.strip().splitlines()[-6:]), flush=True)
            raise AssertionError('%d rows failed' % len(failures))
        for row, acc in zip(rows, results):
            totals.update(acc['totals'])
            program_reads.update(acc['program_reads'])
            if acc['extra'] is not None:
                extras.append(acc['extra'])
                continue
            carry_hist.update(acc['carry_hist'])
            first_pcs.update(acc['first_pcs'])
            executed_starts.update(acc['executed_starts'])
            consumer_seen.update(acc['consumer_seen'])
            computed_seen.update(acc['computed_seen'])
            seed_kinds[acc['seed_kind']] += 1
            for pc, slots in acc['preserved'].items():
                slot = preserved.setdefault(pc, {1: True, 2: True})
                for probe in (1, 2):
                    slot[probe] = slot[probe] and slots[probe]
            guards.extend(acc['guards'])
            out_rows.append(acc['out_row'])
            if acc['oor'] is not None:
                oors.append(acc['oor'])
            if acc['visited'] is not None:
                visited[row['label']] = acc['visited']
            r, s, p, b = acc['start']
            starts_by_label[row['label']] = (r, s, p, b)
    for pc, slots in preserved.items():
        if pc in start_set:
            assert all(slots.values()) == (pc in st['preserving']), (hex(pc), slots)
    if not DEBUG_ROWS:
        u3_consumers = set(CONSUMERS_U3)
        assert u3_consumers <= set(consumer_seen), sorted(hex(p) for p in u3_consumers - set(consumer_seen))
        assert start_set <= set(executed_starts), sorted(hex(p) for p in start_set - set(executed_starts))
    totals = dict(sorted(totals.items()))
    totals['carry_histogram'] = {CARRY_NAME[k]: v for k, v in sorted(carry_hist.items())}
    totals['guard_rows'] = len(guards)
    totals['u3_block_starts_executed_in_actual_cpp_phases'] = len(start_set & set(executed_starts))
    totals['u3_block_starts_run_as_first_pc_of_actual_cpp_phases'] = len(start_set & set(first_pcs))
    totals['u3_starts_probed_single_block'] = sum(1 for pc in preserved if pc in start_set)
    totals['u3_single_block_starts_carry_preserving'] = sum(all(s.values()) for pc, s in preserved.items() if pc in start_set)
    totals['u3_single_block_starts_carry_clobbering_or_producing'] = sum(not all(s.values()) for pc, s in preserved.items() if pc in start_set)
    totals['consumer_flips_by_block'] = {hex(k): v for k, v in sorted(consumer_seen.items())}
    totals['computed_carry_1a2e0_phases'] = dict(sorted(computed_seen.items()))
    totals['seed_start_kinds'] = dict(sorted(seed_kinds.items()))
    never_first = sorted(start_set - set(first_pcs))
    probed = set(pc for pc in preserved if pc in start_set)
    totals['preserving_blocks_checked_by_single_block_probe'] = len(set(st['preserving']) & probed)
    totals['preserving_blocks_checked_by_consumer_flip'] = len(set(st['preserving']) & set(consumer_seen) & set(CONSUMERS_U3))
    covered_pres = (set(st['preserving']) & probed) | (set(st['preserving']) & set(CONSUMERS_U3))
    totals['preserving_blocks_only_inside_multi_block_phases'] = [hex(p) for p in sorted(set(st['preserving']) - covered_pres)]
    totals['non_preserving_blocks_checked_by_single_block_probe'] = len((start_set - set(st['preserving'])) & probed)
    totals['non_preserving_blocks_only_inside_multi_block_phases'] = [hex(p) for p in sorted(start_set - set(st['preserving']) - probed)]
    return out_rows, totals, guards, starts_by_label, dict(program_reads), extras, oors, visited, never_first


SUPERSEDED_GUARDS = ('guard-bad-stop-1a7a8-on-scene-0237',)
SUPERSEDED_RECORDS = []
SUPERSEDED_NEGATIVES = []


def compare_guards(exe, guards, resources, st):
    rows, mismatches = [], []
    for row, phase, ram, state, pvc, bank, step_start in guards:
        fx = row['fixture']
        label = row['label']
        want = GUARD_ERRORS[label] if label in GUARD_ERRORS else expected_pc_error(GUARD_OOR_PCS[label], st)
        cases = [('phase', ram, state, pvc, bank, phase['stop_pc'])]
        if (ram, state, pvc, bank) != (step_start[0], step_start[1], step_start[2], step_start[3]):
            cases.append(('whole_step', step_start[0], step_start[1], step_start[2], step_start[3], phase['step_stop_pc']))
        entry = {}
        for kind, r, s, p, b, stp in cases:
            s = dict(s, carry=2)
            result, outgoing, out_pvc, ports, error = inv('guard_%s_%s' % (label, kind), exe, r, s, p, b, resources, stop=stp, external=fx['external'])
            if label in SUPERSEDED_GUARDS:
                # superseded: the 1a7a8 stop is reached without error in the final state (executed by later units); former expectation recorded
                assert result['ok'] and not error.strip() and result['pc'] == stp and result['status'] == 0, (label, kind, error.strip())
                entry[kind] = dict(ok=True, pc=hex(result['pc']), error='')
                continue
            assert not result['ok'], (label, kind)
            if error.strip() != want:
                mismatches.append((label, kind, error.strip(), want))
            assert {k: result[k] for k in common.STATE_KEYS} == s
            assert outgoing == r and out_pvc == p and result['bank_base'] == b
            assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1
            entry[kind] = error.strip()
        if label in SUPERSEDED_GUARDS:
            SUPERSEDED_RECORDS.append(dict(label=label, native_guard=phase['guard'], former_expected_API_error=want, observed_final_state=entry,
                                           native_fault_rollback_equivalence_claimed=False))
            continue
        rows.append(dict(label=label, native_guard=phase['guard'], expected_error=want, checked_API_errors=entry, all_API_outputs_preserved=True,
                         native_fault_rollback_equivalence_claimed=False))
    assert not mismatches, mismatches
    assert len(rows) + len(SUPERSEDED_RECORDS) == 30 and len(set(r['label'] for r in rows)) == len(rows)
    assert set(r['label'] for r in rows) | set(SUPERSEDED_GUARDS) == set(GUARD_ERRORS) | set(GUARD_OOR_PCS)
    return rows


def negatives(exe, base, starts_by_label, st, resources, oors, visited):
    out = []
    r0, s0, p0, b0 = base
    instructions = st['instructions']
    start_set = st['start_set']

    def reject(label, start, changes=None, stop=0xff000, external=0, error_expected=None):
        r, s, p, b = start
        s = dict(s, carry=2)
        s.update(changes or {})
        result, outgoing, out_pvc, ports, error = inv('negative_' + label, exe, r, s, p, b, resources, stop=stop, external=external)
        assert not result['ok'], label
        assert error.strip() == error_expected, (label, error.strip(), error_expected)
        assert {k: result[k] for k in common.STATE_KEYS} == s
        assert outgoing == r and out_pvc == p and ports == MARKER and result['bank_base'] == b
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        out.append(dict(label=label, error=error.strip(), all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False))

    def supersede(label, start, former, stop=0xff000, changes=None):
        # superseded negative (later units execute this path now): pin and record the observed final-state result instead of a failure
        r, s, p, b = start
        s = dict(s, carry=2)
        s.update(changes or {})
        result, outgoing, out_pvc, ports, error = inv('superseded_' + label, exe, r, s, p, b, resources, stop=stop, external=0)
        assert result['ok'] and not error.strip() and result['pc'] == stop and result['status'] == 0, (label, error.strip())
        SUPERSEDED_NEGATIVES.append(dict(label=label, former_expected_API_error=former, observed_final_state=dict(ok=True, pc=hex(result['pc'])),
                                         native_exception_rollback_equivalence_claimed=False))

    # interior instruction addresses and operand words inside the nine contract ranges: every even PC that is not a block start
    interior = [pc for pc in st['inside'] if pc not in start_set]
    for pc in interior:
        reject('interior_direct_entry_%06x' % pc, base, {'pc': pc}, error_expected=UNSUPPORTED_WALK)
    operand = [pc for low, high in st['ranges'] for pc in range(low, high, 2) if pc not in st['instructions'] and pc not in start_set]
    for pc in operand:
        reject('operand_word_direct_entry_%06x' % pc, base, {'pc': pc}, error_expected=UNSUPPORTED_WALK)
    # outside the nine ranges: the extra range 19938..19978 (U5 caller, outside the contract), the U5 callers 19768/19772, and range edges
    outside = (0x18c04, 0x19768, 0x19772, 0x197d8, 0x19938, 0x1993c, 0x19944, 0x1996e, 0x19976)
    for pc in outside:
        assert not in_ranges(pc, st['ranges'])
        if pc == 0x19772:
            supersede('outside_range_entry_%06x' % pc, base, UNSUPPORTED_MACHINE, changes={'pc': pc})      # executed by a later unit now
        else:
            # 197d8 is routed to the script placement executor now (its checked error); the others still have no executor
            reject('outside_range_entry_%06x' % pc, base, {'pc': pc},
                   error_expected='unsupported animation script placement PC' if pc == 0x197d8 else UNSUPPORTED_MACHINE)
    # former boundary PCs are ordinary block starts now: stop == entry is a zero-step, any other run executes (checked in the native comparison)
    # computed out-of-range types: running on from the dispatcher (no stop at the computed PC) fails with the exact error
    computed = 0
    for label, step_start, final_pc, external in oors:
        want = expected_pc_error(final_pc, st)
        assert want is not None, label
        reject('computed_pc_run_on_%s' % label, step_start, error_expected=want, external=external)
        computed += 1
    # unknown carry at the nine U3 consumers (stop at the clear branch target: the error comes first)
    for pc in sorted(CONSUMERS_U3):
        r, s, p, b = base
        s2 = dict(s, pc=pc, carry=0)
        clear_pc, set_pc, n_before = consumer_info(instructions, pc)
        result, outgoing, out_pvc, ports, error = inv('negative_unknown_carry_%06x' % pc, exe, r, s2, p, b, resources, stop=clear_pc, external=0)
        assert not result['ok'] and error.strip() == UNKNOWN_CARRY, (hex(pc), error)
        assert {k: result[k] for k in common.STATE_KEYS} == s2 and outgoing == r and out_pvc == p and ports == MARKER
        assert result['external_reads'] == 0x12345678 and result['status'] == 1
        out.append(dict(label='unknown_carry_consumer_%06x' % pc, error=error.strip(), all_API_outputs_preserved=True,
                        native_exception_rollback_equivalence_claimed=False))
    # known carry at the same consumers must succeed in both directions (API controls)
    controls = []
    for pc in sorted(CONSUMERS_U3):
        clear_pc, set_pc, n_before = consumer_info(instructions, pc)
        for carry in (1, 2):
            r, s, p, b = base
            s2 = dict(s, pc=pc, carry=carry)
            dest = (clear_pc, set_pc)[carry - 1]
            result, out_ram, out_pvc, ports, error = inv('control_consumer_%06x_%d' % (pc, carry), exe, r, s2, p, b, resources, stop=dest)
            assert result['ok'] and not error and result['pc'] == dest and result['carry'] == carry and out_ram == r and out_pvc == p
            controls.append(dict(pc=hex(pc), carry=CARRY_NAME[carry], to=hex(dest)))
    # full U2+U3 path start (natural, reaches 1a7a8): stops that are never reached fail with a full rollback, reached boundaries stop
    label = 'natural-scene-u3-19844-0000'
    full = starts_by_label[label]
    seen = visited[label]
    for stop in (0xff000, 0x1a0b6, 0x1a470, 0x19758, 0x1a73e, 0x1a2c2, 0x18c9a):
        assert stop not in seen, hex(stop)
        if stop == 0xff000:
            supersede('full_path_start_with_unreached_stop_%06x' % stop, full, UNSUPPORTED_MACHINE, stop=stop)      # now runs on and reaches ff000
        else:
            reject('full_path_start_with_unreached_stop_%06x' % stop, full, stop=stop, error_expected=UNSUPPORTED_MACHINE)
    s = dict(full[1], carry=0)
    for stop in (0x19812, 0x19844, 0x19910, 0x1972a, 0x19764, 0x1a7a8):
        assert stop in seen, hex(stop)
        result, out_ram, out_pvc, ports, error = inv('control_full_path_stop_%06x' % stop, exe, full[0], s, full[2], full[3], resources, stop=stop)
        assert result['ok'] and not error and result['pc'] == stop, (hex(stop), error)
        controls.append(dict(entry=hex(ENTRY_1A73C), stop=hex(stop), ok=True, a7=result['a7']))
    # fallthrough boundary: the native observer refuses a stop directly after a non-transfer (1972a SWAP -> 1972c, 19370 EXG -> 19372); the
    # C++ block API stops at any block start, so the same stops are accepted as API-only controls
    for label2, stop in (('boundary-zero-step', 0x1972c),):
        if DEBUG_ROWS and label2 not in starts_by_label:
            continue
        b2 = starts_by_label[label2]
        result, out_ram, out_pvc, ports, error = inv('control_fallthrough_stop_%06x' % stop, exe, b2[0], dict(b2[1], carry=0), b2[2], b2[3], resources, stop=stop)
        assert result['ok'] and not error and result['pc'] == stop and result['a7'] == b2[1]['a7']
        assert result['d7'] == ((b2[1]['d7'] << 16) | (b2[1]['d7'] >> 16)) & 0xffffffff and out_ram == b2[0]
        controls.append(dict(entry=hex(b2[1]['pc']), stop=hex(stop), ok=True, note='API-only; native refuses this stop (not directly after a transfer)'))
    return out, len(interior), len(operand), controls, computed


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
    for pc in U2_BOUNDARY_PCS + FORMER_BOUNDARY_PCS:
        s = dict(state, pc=pc, carry=2)
        result, out_ram, out_pvc, ports, error = inv('zero_boundary_%06x' % pc, exe, ram, s, pvc, bank, resources, stop=pc)
        assert {k: result[k] for k in common.STATE_KEYS} == s and out_ram == ram and out_pvc == pvc
        rows.append(dict(pc=hex(pc), ok=result['ok'], error=error.strip()))
    return rows


def cpp_audit(st, program):
    """Static comparison of the C++ tables / case labels with the contract (independent of the dynamic comparison)."""
    walk = (ROOT / 'engine/src/animation_machine_motion_walk.cpp').read_text()
    machine = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    cases = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', walk))
    slots = set()
    for table in re.findall(r'\{(0x[0-9a-f]+),\{', walk):
        slots.update(int(table, 16) + 4 * k for k in range(36))
    handler_pcs = set(int(x, 16) for x in re.findall(r'\{(0x1[0-9a-f]{4}),\d,\d,WALK_\w+,\d,-?\d\}', walk))
    pair_pcs = set(int(x, 16) for x in re.findall(r'\{(0x1[0-9a-f]{4}),\d,-?\d,\d\}', walk))
    # the 5x36 slot target tables against the original BRA.W slots (opcode 6000, 16-bit displacement from slot+2)
    slot_checked = 0
    for table, body in re.findall(r'\{(0x[0-9a-f]+),\{([^}]*)\}\}', walk):
        targets = [int(x, 16) for x in re.findall(r'0x[0-9a-f]+', body)]
        assert len(targets) == 36
        for k, target in enumerate(targets):
            slot = int(table, 16) + 4 * k
            assert program[slot:slot + 2] == b'\x60\x00'
            disp = struct.unpack('>h', program[slot + 2:slot + 4])[0]
            assert slot + 2 + disp == target, (hex(slot), hex(target))
            slot_checked += 1
    labels = cases | slots | handler_pcs | pair_pcs
    start_set = st['start_set']
    body = machine.split('bool carry_preserving_pc', 1)[1].split('default:return false', 1)[0]
    preserving_cpp = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', body))
    preserving_cpp_u3 = set(pc for pc in preserving_cpp if in_ranges(pc, st['ranges']))
    walk_route = machine.split('ok=animation_scene_core_block(c);', 1)[1].split('animation_motion_walk_block', 1)[0]
    routed = sorted((int(a, 16), int(b, 16)) for a, b in re.findall(r'next\.pc>=(0x[0-9a-f]+) && next\.pc<(0x[0-9a-f]+)', walk_route))
    merged_ranges = []
    for low, high in sorted(st['ranges']):
        if merged_ranges and merged_ranges[-1][1] == low:
            merged_ranges[-1] = (merged_ranges[-1][0], high)
        else:
            merged_ranges.append((low, high))
    assert routed == merged_ranges, (routed, merged_ranges)
    return dict(cpp_labels_not_in_contract_block_starts=[hex(p) for p in sorted(labels - start_set)],
                contract_block_starts_without_cpp_label=[hex(p) for p in sorted(start_set - labels)],
                cpp_carry_preserving_u3_not_in_contract=[hex(p) for p in sorted(preserving_cpp_u3 - set(st['preserving']))],
                contract_preserving_not_in_cpp=[hex(p) for p in sorted(set(st['preserving']) - preserving_cpp_u3)],
                cpp_routed_ranges=[(hex(a), hex(b)) for a, b in routed], contract_ranges=[(hex(a), hex(b)) for a, b in st['ranges']],
                case_label_count=len(cases), slot_pc_count=len(slots), handler_pc_count=len(handler_pcs), pair_pc_count=len(pair_pcs),
                slot_targets_checked_against_ROM_BRA_W=slot_checked)


def main():
    global RUN_DIR
    assert OUT.resolve() == (ROOT / 'artifacts/animation_machine_motion_walk_execution').resolve()
    if OUT.exists():
        shutil.rmtree(OUT)          # only this verifier's own output folder
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    RUN_DIR = Path(tempfile.mkdtemp(prefix='motion_walk_verify_'))
    try:
        run(report_path)
    finally:
        shutil.rmtree(RUN_DIR, ignore_errors=True)


def run(report_path):
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_motion_walk.py', 'tools/verify_animation_machine_card_child.py', 'tools/verify_stage_frame.py',
                 'tools/observe_animation_machine_motion_walk.py', 'tools/observe_scene_frame_execution.py',
                 'docs/analysis/animation-machine-motion-walk-u3-contract.md', 'engine/src/animation_machine_motion_walk.cpp',
                 'engine/src/animation_machine.cpp', 'engine/src/animation_machine_internal.h', 'engine/tests/animation_machine_motion_walk_test.cpp'):
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
    st['start_set'] = set(st['starts'])
    st['visited_wanted'] = set()
    instructions = st['instructions']
    rows = report['results'] + report['guarded_results']
    assert len(rows) == 1363
    labels = [r['label'] for r in rows]
    assert len(set(labels)) == len(labels)
    for uid, r in enumerate(rows):
        r['_uid'] = uid
    st['visited_wanted'] = set(['natural-scene-u3-19844-0000'])
    if os.environ.get('MOTION_WALK_DEBUG_LABELS'):      # development switch only
        wanted = os.environ['MOTION_WALK_DEBUG_LABELS'].split(',')
        rows = [r for r in rows if r['label'] in wanted]
    elif DEBUG_ROWS:
        rows = rows[:DEBUG_ROWS] + report['guarded_results']
    scene_in, scene_files = rebuild_scene_inputs()
    stage_in, stage_files = rebuild_stage_inputs()
    prov = report['seed_provenance']
    for path, expected in list(scene_files.items()) + list(stage_files.items()):
        assert prov['files'][path.replace(str(ROOT), MAIN.rstrip('/'))] == expected, path
    assert prov['scene_frame']['observation_sha256'] == SCENE_OBS_SHA and prov['scene_frame']['initializer_observation_sha256'] == SCENE_SEED_SHA
    assert prov['stage_frame']['verification_sha256'] == STAGE_FRAME_SHA and prov['stage_frame']['rebuilt_cases'] == 64
    base182 = scene_in[182][1]
    base_rams = native_base_rams(rows)
    matches, totals, guards, starts_by_label, program_reads, extras, oors, visited, never_first = compare(
        exe, rows, resources, st, scene_in, stage_in, base_rams, base182, program, instructions)
    assert DEBUG_ROWS or VERIFIED_ARTIFACTS == set(report['artifacts']), (len(VERIFIED_ARTIFACTS), len(report['artifacts']))
    guarded = compare_guards(exe, guards, resources, st)
    base = starts_by_label['natural-scene-u3-19844-0000']
    base = (base[0], dict(base[1]), base[2], base[3])
    negative, interior_count, operand_count, controls, computed_count = negatives(exe, base, starts_by_label, st, resources, oors, visited)
    zero = zero_step(exe, base, resources, st['starts'])
    boundary_zero = boundary_zero_step(exe, base, resources)
    audit = cpp_audit(st, program)
    assert not audit['cpp_labels_not_in_contract_block_starts'] and not audit['contract_block_starts_without_cpp_label'], audit
    assert not audit['cpp_carry_preserving_u3_not_in_contract'] and not audit['contract_preserving_not_in_cpp'], audit
    assert audit['slot_targets_checked_against_ROM_BRA_W'] == 180 and audit['handler_pc_count'] == 72 and audit['pair_pc_count'] == 32, audit
    for name, expected in list(inputs.items()) + list(native_inputs.items()):
        assert cc.digest(local(name) if name.startswith(MAIN) else ROOT / name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    manifest = '\n'.join('%s %s' % (k, report['artifacts'][k]) for k in sorted(report['artifacts']))
    refs = dict(refs)
    for path, digest in list(scene_files.items()) + list(stage_files.items()):
        refs[str(Path(path).relative_to(ROOT))] = digest
    for path in (OUT / 'harness.cpp', OUT / 'compile.log'):
        refs[str(path.relative_to(ROOT))] = cc.digest(path)
    result = dict(
        schema_version=1, source=source, inputs=inputs, native_inputs_checked=len(native_inputs), artifacts=refs,
        native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA, contract_sha256=CONTRACT_SHA,
        native_artifact_manifest=dict(count=len(report['artifacts']), every_file_read_and_hash_checked=True,
                                      sorted_name_hash_lines_sha256=sha(manifest.encode())),
        contract_ranges=[dict(range='%x..%x' % r, size=r[1] - r[0]) for r in st['ranges']], block_start_count=len(st['starts']),
        block_starts=[hex(p) for p in st['starts']], bundled_branch_count=len(st['bundled']), bundled_branches=[hex(p) for p in st['bundled']],
        carry_preserving_blocks=[hex(p) for p in st['preserving']], carry_preserving_count=len(st['preserving']),
        carry_consumer_blocks=[hex(p) for p in st['consumers']],
        carry_producer_blocks=dict(ORI_set=[hex(p) for p in SET_PRODUCERS_U3], ANDI_clear=[hex(p) for p in CLEAR_PRODUCERS_U3],
                                   computed_clear_TST_AND=[hex(p) for p in st['computed']],
                                   computed_clear_instructions=[hex(p) for p in TST_CLEAR_PCS + AND_CLEAR_PCS]),
        opcode_leader_derivation=dict(derived_equals_contract=True, derived_not_contract=[], contract_not_derived=[]),
        cpp_static_audit=audit,
        actual_CPP=dict(totals, matches=matches), original_program_read_audit=program_reads,
        extra_range_19938_19978=dict(role='declared extra range outside the contract (U5 caller); expected-unsupported in C++', rows=extras),
        native_guards_checked_API=guarded, superseded_guards=SUPERSEDED_RECORDS, superseded_negatives=SUPERSEDED_NEGATIVES, native_continuous_control_phases_replayed=totals['control'],
        negatives=negative, negative_count=len(negative) + len(guarded), interior_PCs_rejected=interior_count,
        operand_word_PCs_rejected=operand_count, computed_pc_run_on_rejected=computed_count, API_controls=controls,
        zero_step_count=len(zero), zero_step_blocks=len(st['starts']), zero_step_carries=[0, 1, 2], boundary_zero_step=boundary_zero,
        u3_block_starts_never_first_pc_of_a_phase=[hex(p) for p in never_first],
        carry_check='C++ carry equals the source-opcode walk over native-executed PCs (ORI/ANDI CCR known, TST.W 19710/1971c and AND.W 1938e/19596 '
                    'known Clear, 1a2e0 CMP.W+EORI computed known from the native incoming RAM, 289e equal-branch Clear, flow-only preserved, else '
                    'Unknown); native SR never read',
        compile_command=command, failure=None, ROM_unchanged=True,
        limits=['Controlled fixtures (rebuilt scene_frame / stage_frame seeds, rebuilt declared unit fixtures on scene case 182, declared stage_entry_body '
                'and captured re-entry states, declared RAM/register/PC/return-LONG variants), not natural scheduler, IRQ or gameplay reachability.',
                'The stage_entry_body (120) and captured full-frame re-entry (152) start states are native states SHA-pinned in the native artifacts; '
                'they are not rebuilt here (they need the original code run). Their registers / A7 / stack bytes are asserted equal to the recorded '
                'provenance.',
                '1a0b6, 1a470, 1a7a8 are stop boundaries only, never executed; their bodies (U4, U5) are unverified. 19938..19978 and 19768/19772 are '
                'outside the contract: the 4 flow-19938 rows are expected-unsupported (API refuses with the exact error), never compared.',
                'Carry is a source-opcode classification (native SR is never read).',
                'Checked failures preserve API outputs, not original CPU fault rollback; interior / operand / computed-PC run-on / Unknown-carry '
                'consumer entries and fallthrough-stop controls have no native counterpart (API-only).',
                'Native observation artifacts are audited by hash/trace consistency, not re-executed here.'],
        normalized_reference_paths=len(refs))
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=totals['cases'], split=totals['split'], control=totals['control'], resumes=totals['resumes'],
                          negatives=result['negative_count'], interior=interior_count, operand=operand_count, zero_step=len(zero),
                          carry=totals['carry_histogram'], sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
