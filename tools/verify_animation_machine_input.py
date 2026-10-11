"""480bc frame helper bundle U6 (input 49b0c and the input callbacks) native evidence vs the public machine API.

Controlled fixtures; no expected-register injection. The frozen native observation (artifacts/animation_machine_input_native) is an immutable input: this
verifier never invokes the observer main. The observer module is only imported as a library for its declared-fixture builders (Items, stage input loop
corpus, rng seeds) and for the native Unicorn `probe`; every rebuilt fixture is checked against the SHA / register pins of the stored native rows.

Three comparison layers:
  * 658 stored native conditions (658 split + continuous rows, 27 guarded rows): per split phase the full 64 KiB RAM / 16 registers / PC / A7 / PVC / bank /
    ordered ports / external reads / status of the actual C++ output; resume only from the previous actual C++ output plus the declared host changes of the
    native step; continuous C++ run vs the split chain; carry = source-opcode classification (4836e / 48378 / 4837e producers, 289e known C) cross-checked at
    every carry consumer against the REAL native branch; carry probes 1 / 2 per phase; guards -> exact checked error + full preservation.
  * all 7527 normal conditions end-to-end: the 206 natural conditions through the stored rows (declared native entry state SHA pinned), the 7321 other
    conditions rebuilt from the observer fixture builders, run natively again (Unicorn probe, Python-model comparison) and compared with the actual C++ run:
    final full state (RAM / 16R / PC / PVC / bank / ports / reads / status), carry classification and the census row fields recorded in the observation.
  * API-only negatives: interior / folded / operand-word / odd / outside entries, Unknown-carry consumers, 4d7f0 stop-only boundary, zero-step at every
    executable block start x 3 carries.
Native SR is never read: C is a source-opcode classification.
"""
import collections
import concurrent.futures
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
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
OUT = ROOT / 'artifacts/animation_machine_input_execution'
NATIVE_DIR = ROOT / 'artifacts/animation_machine_input_native'
NATIVE_SHA = '311fb438bae1ff7aa013bf4e175302a7ba249cff5ef78eb45caa258308ec78b4'
NATIVE_TOOL_SHA = 'de302e9213e6946a2157fe7146d48561c053aed51eb9b4984a464e2a1f7f240a'
CONTRACT_SHA = '99ba39b26d652b48189f1ab55251c6a099bad4faa21abb2d5a387522636c98dc'
ROM_SHA = '29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
MARKER = cc.MARKER
sha = cc.sha
CARRY_NAME = cc.CARRY_NAME
FLOW_ONLY = cc.FLOW_ONLY
M32 = 0xffffffff
S = 0x1feffc
ENTRY = 0x49b0c
TRAP_PC = 0x4d7f0
RET_FRAME = 0x480cc
CONSUMERS = (0x49b28, 0x49b7e, 0x4d7c6, 0x1d5b2)
PRODUCERS = (0x48378, 0x4837e)
ENTRY_LEADERS = (0x49b0c, 0x49b2e, 0x49b84, 0x49e9c, 0x49eba, 0x49ef0, 0x49f2c)
FOLDED_NZ = (0x49dd4, 0x49e8a, 0x49f4a)
CONDITIONAL = ('beq', 'bne', 'bcc', 'bcs', 'bmi', 'bpl', 'bvc', 'bvs', 'bhi', 'bls', 'bge', 'blt', 'bgt', 'ble')
X_USERS = ('addx', 'subx', 'negx', 'roxl', 'roxr', 'abcd', 'sbcd', 'nbcd')
UNSUPPORTED_INPUT = 'unsupported animation input PC'
UNSUPPORTED_MACHINE = 'unsupported animation machine PC'
UNKNOWN_CARRY = 'input caller requires known carry'
EVEN = 'program bus requires even WORD/LONG address'
EVEN_WRITE = 'invalid animation machine write size/alignment'
WRITE_DEVICE = 'unsupported animation machine write device'
RAM_MIRROR = 'program bus write requires RAM mirror units'
UNALIGNED_PC = 'unaligned animation machine PC'
DEVICE_ADDR = 'unsupported program bus device address'
# Exact checked errors of the stored guards (derived from the C++ dispatch / bus rules, not from a first run):
#   JSR (A1) with an odd target -> the loop head rejects the odd PC; a target with a nonzero top BYTE, a RAM address or a ROM address outside every executor
#   matches no executor range (80000049 is odd: the loop head rejects it); 49b30 lies in the input range but is no block start; the bus rules give the odd / ROM write messages; the two bad-stop rows
#   and the TRAP row run on into the U1 code at 480cc (stop never reached). Aligned to the final state (480bc frame helpers U1..U7 executable): the two bad-stop rows now run through that
#   code and end with a device-address bus error (null-path state), the TRAP row still ends at the first PC without an executor; the rom-outside-unit rows (JSR (A1) with A1 = 4aa88, now an executed
#   boundary) execute the U7 code and end with an odd-address bus error (superseded negative: the native guard record is unchanged and no fault-rollback equivalence is claimed).
GUARD_ERRORS = {
    'guard-odd-target': UNALIGNED_PC, 'guard-top-byte-01049e34': UNSUPPORTED_MACHINE, 'guard-top-byte-ff049e34': UNSUPPORTED_MACHINE,
    'guard-top-byte-80000049': UNALIGNED_PC, 'guard-ram-target': UNSUPPORTED_MACHINE, 'guard-rom-outside-unit': EVEN,
    'guard-mid-instruction': UNSUPPORTED_INPUT,
    'guard-odd-A5': EVEN, 'guard-odd-A7-entry': EVEN, 'guard-rom-write-A7': RAM_MIRROR, 'guard-odd-A0-49de6': EVEN, 'guard-odd-A6-1d5e2': EVEN,
    'guard-odd-A1-49afe': EVEN, 'guard-odd-A1-49bb4': EVEN, 'guard-rom-write-49bb4': WRITE_DEVICE, 'guard-rom-write-49c20': WRITE_DEVICE,
    'guard-odd-slot-write-49c20': EVEN_WRITE, 'guard-bad-stop-49b2e-null-path': DEVICE_ADDR, 'guard-bad-stop-4d7f0-null-path': DEVICE_ADDR,
    'guard-trap-reached-without-stop': UNSUPPORTED_MACHINE}
SUBSTEP_BLOCKS = (0x49bb0, 0x49ad6)
VARIANT_PREFIX = 'target-non-block-start-49e36'      # native: executes the RTS inside the unit; C++: checked rejection (deliberate difference)
VERIFIED_ARTIFACTS = set()
RUN_DIR = None
WORKERS = 8
DEBUG_ROWS = int(os.environ.get('INPUT_DEBUG_ROWS', '0'))     # development switch only: the reported run is always the full set


def localize(name):
    return str(ROOT) + name[len(MAIN_ROOT):] if name.startswith(MAIN_ROOT + '/') else name


def in_ranges(pc, ranges):
    return any(low <= pc < high for low, high in ranges)


def invoke(exe, folder, label, ram, state, pvc, bank, resources, stop, external=0):
    """common.invoke with close_fds=False (posix_spawn): the census workers hold ~0.5 GB of fixture RAM images and a plain fork_exec of such a process is slow."""
    paths = [folder / (label + s) for s in ('_input.bin', '_pvc_input.bin', '_ram.bin', '_pvc.bin', '_ports.bin')]
    paths[0].write_bytes(ram)
    paths[1].write_bytes(pvc)
    args = [str(exe)] + [str(state[k]) for k in common.REGS] + [str(state['pc']), str(state['carry']), str(bank), str(stop), str(external)] + \
        list(map(str, paths)) + list(map(str, resources))
    run = subprocess.run(args, capture_output=True, text=True, timeout=120, close_fds=False)
    assert run.returncode == 0, (label, run.stderr)
    result = common.parse(run.stdout, expected_invalid_carry=state['carry'] if state['carry'] not in (0, 1, 2) else None)
    assert paths[0].read_bytes() == ram and paths[1].read_bytes() == pvc
    return result, paths[2].read_bytes(), paths[3].read_bytes(), paths[4].read_bytes(), run.stderr


def inv(label, *args, **kwargs):
    result = invoke(*((args[0], RUN_DIR, label) + args[1:]), **kwargs)
    for suffix in ('_input.bin', '_pvc_input.bin', '_ram.bin', '_pvc.bin', '_ports.bin'):
        (RUN_DIR / (label + suffix)).unlink()
    return result


def guard_error(label):
    for key in sorted(GUARD_ERRORS, key=len, reverse=True):
        if label == key or label.startswith(key + '-slot'):
            return GUARD_ERRORS[key]
    raise KeyError(label)


# ----------------------------------------------------------------------------------------------------------------- instructions
class RomInstructions(dict):
    """Instruction decoded from the original bytes on demand."""
    def __init__(self, program):
        dict.__init__(self)
        self.program = program

    def __missing__(self, pc):
        item = disassemble_range(self.program, pc, 10, pc)[0]
        assert item['classification'] == 'candidate_instruction' and item['cpu_address'] == pc, hex(pc)
        self[pc] = item
        return item


def classify_carry(instructions, carry, pcs):
    return u2.classify_carry(instructions, carry, pcs, None)


def branch_expect(item, carry):
    """Next PC of a consumer (BCC / BCS) for a known carry (1 Clear, 2 Set)."""
    name = item['mnemonic'].split('.')[0]
    target = int(re.search(r'\$([0-9a-f]+)$', item['op_str']).group(1), 16)
    fall = item['cpu_address'] + item['size']
    taken = (name == 'bcc' and carry == 1) or (name == 'bcs' and carry == 2)
    assert name in ('bcc', 'bcs') and carry in (1, 2)
    return target if taken else fall


# ----------------------------------------------------------------------------------------------------------------- contract
def contract_lines():
    return (ROOT / 'docs/analysis/animation-machine-input-u6-contract.md').read_text().splitlines()


def hexes(line):
    return [int(x, 16) for x in re.findall(r'`([0-9a-f]{4,6})`', line)]


def contract_section(lines, header, counts):
    i = next(k for k, line in enumerate(lines) if line.startswith(header))
    out = {}
    for line in lines[i + 1:i + 4]:
        match = re.match(r'\s+- (U6[abc]) (\d+)(?:\(.*?\))?:(.*)', line)
        assert match, line
        values = hexes(match.group(3))
        assert len(values) == int(match.group(2)) == counts[match.group(1)], (match.group(1), len(values))
        out[match.group(1)] = values
    return out


def parse_contract(program):
    lines = contract_lines()
    starts = contract_section(lines, '- **Block 시작 PC (151개)', dict(U6a=34, U6b=70, U6c=47))
    folded = contract_section(lines, '- **묶인 분기·접힌 PC (54개', dict(U6a=9, U6b=25, U6c=20))
    preserving = contract_section(lines, '- **Carry 보존(FLOW_ONLY) block (66개)', dict(U6a=21, U6b=25, U6c=20))
    table = []
    for line in lines:
        match = re.match(r'^\| `([0-9a-f]+)\.\.([0-9a-f]+)` \| (U6[abc]) \| (\d+) \| (\d+) \| `([0-9a-f]+)` \|$', line)
        if match:
            low, high = int(match.group(1), 16), int(match.group(2), 16)
            assert program[low:high].hex() == match.group(6) and high - low == int(match.group(4)), match.group(1)
            table.append(dict(range='%x..%x' % (low, high), unit=match.group(3), size=high - low, table_instruction_count=int(match.group(5)),
                              bytes_equal_to_rom=True))
    assert len(table) == 19 and sum(t['size'] for t in table) == 1288
    data_row = [line for line in lines if line.startswith('| `49ab0..49ab4`')]
    assert len(data_row) == 1 and program[0x49ab0:0x49ab4].hex() == '10204080' and '`10204080`' in data_row[0]
    all_starts = sum(starts.values(), [])
    all_folded = sum(folded.values(), [])
    all_preserving = sum(preserving.values(), [])
    assert (len(all_starts), len(all_folded), len(all_preserving)) == (151, 54, 66)
    assert len(set(all_starts)) == 151 and len(set(all_folded)) == 54 and len(set(all_preserving)) == 66
    assert not (set(all_starts) & set(all_folded)) and set(all_preserving) <= set(all_starts) and TRAP_PC in all_starts
    return table, all_starts, all_folded, all_preserving


def derive_leaders(instructions, ranges):
    derived = set(low for low, _ in ranges) | set(ENTRY_LEADERS)
    for pc, item in instructions.items():
        if not in_ranges(pc, ranges):
            continue
        name = item['mnemonic'].split('.')[0]
        target = re.search(r'\$([0-9a-f]+)$', item['op_str'])
        if name in CONDITIONAL + ('bra', 'bsr', 'jsr', 'dbra') and target:
            derived.add(int(target.group(1), 16))
        if name in CONDITIONAL + ('bsr', 'jsr', 'rts', 'bra', 'jmp', 'dbra'):
            derived.add(pc + item['size'])
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
    table, starts, folded, preserving = parse_contract(program)
    ranges = [tuple(int(x, 16) for x in t['range'].split('..')) for t in table]
    assert sorted(tuple(r) for r in static['u6_ranges']) == sorted(ranges) and sorted(tuple(r) for r in report['new_ranges']) == sorted(ranges)
    instructions = {}
    for instruction in static['instructions']:
        at, size = instruction['rom_offset'], instruction['size']
        assert bytes(bytearray.fromhex(instruction['raw'])) == program[at:at + size] and at == instruction['cpu_address']
        instructions[at] = instruction
    decoded = RomInstructions(program)
    tiled = 0
    for low, high in ranges:
        pc = low
        while pc < high:
            assert pc in instructions and decoded[pc]['size'] == instructions[pc]['size']
            pc += decoded[pc]['size']
            tiled += 1
        assert pc == high
    inside = sorted(pc for pc in decoded if in_ranges(pc, ranges))
    assert tiled == len(inside) == 368
    # table column nit: four rows list an instruction count that differs from the decoded count (sum 366 vs 368 decoded, unit text 368)
    column_nits = []
    for t in table:
        low, high = (int(x, 16) for x in t['range'].split('..'))
        count = sum(1 for pc in inside if low <= pc < high)
        if count != t['table_instruction_count']:
            column_nits.append(dict(range=t['range'], contract_table=t['table_instruction_count'], decoded=count))
    start_set = set(starts)
    assert all(in_ranges(pc, ranges) and pc in decoded for pc in starts)
    derived = derive_leaders(decoded, ranges)
    contract_not_derived = sorted(start_set - derived)
    derived_not_contract = sorted(derived - start_set)
    assert contract_not_derived == [] and sorted(derived_not_contract) == sorted(FOLDED_NZ), ([hex(p) for p in derived_not_contract])
    blocks = static_blocks(decoded, start_set)
    in_block = collections.Counter(pc for pcs in blocks.values() for pc in pcs)
    assert max(in_block.values()) == 1
    # every instruction is in exactly one block or is a folded / bundled PC (conditional branch or the folded SNE 49f4a)
    fold_expected = sorted(pc for pc in inside if pc not in start_set and
                           (decoded[pc]['mnemonic'].split('.')[0] in CONDITIONAL + ('dbra',) or pc == 0x49f4a))
    assert fold_expected == sorted(folded), ([hex(p) for p in set(fold_expected) ^ set(folded)])
    preserving_derived = sorted(pc for pc in starts if all(decoded[p]['mnemonic'].split('.')[0] in FLOW_ONLY for p in blocks[pc]))
    assert preserving_derived == sorted(preserving), ([hex(p) for p in set(preserving_derived) ^ set(preserving)])
    producers = sorted(pc for pc in inside if decoded[pc]['mnemonic'].split('.')[0] in ('ori', 'andi', 'eori', 'move') and decoded[pc]['op_str'].endswith(('ccr', 'sr')))
    assert producers == list(PRODUCERS), [hex(p) for p in producers]
    assert [next(s for s, pcs in blocks.items() if p in pcs) for p in producers] == list(PRODUCERS)
    consumers = sorted(pc for pc in starts if decoded[pc]['mnemonic'].split('.')[0] in ('bcc', 'bcs'))
    assert consumers == sorted(CONSUMERS), [hex(p) for p in consumers]
    x_users = [pc for pc in inside if decoded[pc]['mnemonic'].split('.')[0] in X_USERS]
    assert x_users == []
    # ROM data windows are not code (49ab0..49ab4 default mask, 4cf64..4df60 record table)
    assert not in_ranges(0x49ab0, ranges) and not in_ranges(0x4cf64, ranges) and static['boundary_stop_pcs'] == [RET_FRAME, TRAP_PC]
    return dict(static=static, table=table, starts=starts, folded=folded, preserving=preserving, instructions=decoded, blocks=blocks, inside=inside,
                ranges=ranges, column_nits=column_nits, derived_not_contract=derived_not_contract)


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
        assert not ports and phase['counts']['video'] == phase['counts']['watchdog'] == phase['counts']['pvc'] == phase['counts']['bank_reads'] == 0
    return counts_split


def audit_report(program, source):
    path = NATIVE_DIR / 'observation.json'
    assert cc.digest(path) == NATIVE_SHA
    assert cc.digest(ROOT / 'tools/observe_animation_machine_input.py') == NATIVE_TOOL_SHA
    assert cc.digest(ROOT / 'docs/analysis/animation-machine-input-u6-contract.md') == CONTRACT_SHA
    report = json.loads(path.read_text())
    assert report['source'] == source and report['failure'] is None and source['sha256'] == ROM_SHA
    assert report['tool_sha256'] == NATIVE_TOOL_SHA and report['contract']['sha256'] == CONTRACT_SHA
    for key in ('original_program_modified', 'SR_read_at_any_phase', 'register_injection_after_begin', 'Cpp_comparison_performed'):
        assert report[key] is False, key
    assert report['declared_register_changes_at_step_boundaries'] == [] and report['contract_discrepancies'] == []
    assert report['rom_stat_start'] == report['rom_stat_end']
    assert (report['cases'], report['guarded_cases'], report['split_steps'], report['control_steps']) == (658, 27, 11936, 658)
    assert (report['guard_split_steps'], report['guard_control_steps'], report['total_split_phases'], report['total_control_phases']) == (27, 27, 11963, 685)
    assert report['contract']['contract_block_starts'] == 151 and report['contract']['contract_bundled_branches'] == 54
    assert report['uncovered_u6_block_starts'] == [] and report['uncovered_leaders_incl_289e'] == []
    assert report['boundary_stop_pcs'] == [RET_FRAME, TRAP_PC]
    assert report['census_model_checks'] == dict(runs=7523, equal=7523, unequal=[], model_errors=[])
    assert len(report['first_boundary_census']['census']) == 7527 and sum(report['group_counts'].values()) == 7554
    inputs = {}
    for name, expected in report['inputs'].items():
        local = localize(name)
        assert cc.digest(local) == expected, name
        inputs[local] = expected
    import unicorn
    assert unicorn.__version__ == report['oracle']['version']
    assert cc.digest(localize(report['oracle']['library'])) == report['oracle']['library_sha256']
    return report, inputs


# ----------------------------------------------------------------------------------------------------------------- declared fixtures (observer library)
OBS = None
ITEMS = []
ITEM_BY_LABEL = {}
PROGRAM = None
CENSUS_BY_LABEL = {}
EXE = None
RESOURCES = None
INSTRUCTIONS = None
STORED_CONTROL = {}
START_SET = frozenset()


def build_items(program, scratch):
    """Rebuild the 7348 non-natural declared conditions with the observer's fixture builders (library use, no main)."""
    global OBS, PROGRAM
    import observe_animation_machine_input as obs
    OBS = obs
    PROGRAM = program
    out = Path(scratch) / 'observer_scratch'
    out.mkdir(parents=True, exist_ok=True)
    obs.configure(program, out)
    cases = obs.sil.build_cases()
    items = obs.Items()
    obs.loop_items(items, cases)
    obs.callback_direct_items(items, cases)
    obs.helper_corpus_items(items, cases)
    obs.random_callback_items(items, cases)
    obs.random_loop_items(items, cases)
    obs.mask_items(items, cases)
    obs.helper_direct_items(items, cases)
    obs.trap_items(items, cases, program)
    obs.guard_items(items, cases, program)
    return items.items


def item_start(it):
    fx = it['fx']
    regs = dict(fx['regs'])
    assert set(regs) == set(vsf.KEYS) | {'a5'}
    ram = bytearray(fx['ram'])
    for change in it['setup']:
        assert change['kind'] == 'ram'
        common.native.put(ram, change['address'], change['size'], change['value'])
    state = dict(regs, a7=fx['initial_a7'], pc=fx['entry_pc'], carry=0)
    return bytes(ram), state, fx['pvc'], fx['bank_state'][0]


# ----------------------------------------------------------------------------------------------------------------- stored rows
def apply_changes(ram, state, changes, entry):
    ram = bytearray(ram)
    kinds = []
    for change in changes:
        assert change['kind'] == 'ram'
        assert change['pc_before'] == entry['pc'] and change['a7_before'] == entry['a7'], change
        common.native.put(ram, change['address'], change['size'], change['value'])
        kinds.append('ram')
    return bytes(ram), dict(state), kinds


def start_of_row(row):
    """(ram_declared_initial, state, pvc, bank, how) : rebuilt from the observer builders for the non-natural rows, SHA-pinned native state for the natural rows."""
    fx = row['fixture']
    regs = dict(fx['initial_regs'])
    assert set(regs) == set(vsf.KEYS) | {'a5'}
    pvc0 = (NATIVE_DIR / [n for n in row['phases'][0]['artifacts'] if n.endswith('_pvc_before.bin')][0]).read_bytes()
    assert sha(pvc0) == fx['initial_PVC_sha256']
    it = ITEM_BY_LABEL.get(row['label'])
    if it is not None:
        ram, state, pvc, bank = item_start(dict(it, setup=[]))        # the declared host writes of the step are applied from the native phase record
        assert sha(ram) == fx['initial_RAM_sha256'] and sha(pvc) == fx['initial_PVC_sha256'] and fx['bank_state'][0] == bank
        assert {k: state[k] for k in regs} == regs and state['a7'] == fx['initial_a7'] and state['pc'] == fx['entry_pc']
        assert it['stop'] == row['steps'][0]['stop_pc']
        planned = [(c['address'], c['size'], c['value']) for c in it['setup']]
        recorded = [(c['address'], c['size'], c['value']) for c in row['phases'][0]['host_changes']]
        assert planned == recorded, row['label']
        return ram, state, pvc, bank, 'rebuilt declared fixture (observer builder), RAM/registers/PVC SHA-pinned to the native fixture summary'
    assert row['group'].startswith('natural') and not row['phases'][0]['host_changes']
    ram = (NATIVE_DIR / [n for n in row['phases'][0]['artifacts'] if n.endswith('_ram_before.bin')][0]).read_bytes()
    assert sha(ram) == fx['initial_RAM_sha256']
    state = dict(regs, a7=fx['initial_a7'], pc=fx['entry_pc'], carry=0)
    return ram, state, pvc0, fx['bank_state'][0], 'declared native state (SHA-pinned native artifact)'


def check_preserved(actual, ram, state, pvc, bank, expected_error):
    result, out_ram, out_pvc, ports, error = actual
    assert not result['ok'] and error.strip() == expected_error, (expected_error, error.strip())
    assert {k: result[k] for k in common.STATE_KEYS} == {k: state[k] for k in common.STATE_KEYS}
    assert out_ram == ram and out_pvc == pvc and result['bank_base'] == bank
    assert ports == MARKER and result['external_reads'] == 0x12345678 and result['status'] == 1


def consumer_checks(instructions, carry_in, executed, nexts, totals):
    """At every executed carry consumer: the classified C is known and the REAL native next PC equals the BCC / BCS outcome of that C."""
    for index, pc in enumerate(executed):
        if pc in CONSUMERS:
            carry = classify_carry(instructions, carry_in, executed[:index])
            if carry == 0:
                return False                 # the consumer is the first instruction of the phase: the carry arrives from the previous C++ output
            assert nexts[index] == branch_expect(instructions[pc], carry), (hex(pc), carry, hex(nexts[index]))
            totals['consumer_real_branch_checks'] += 1
    return True


def run_row(row, ctx):
    """One native row against the C++ API (rows run concurrently, phases and steps inside a row sequentially)."""
    exe, resources, st, program, instructions = ctx
    start_set = set(st['starts'])
    acc = dict(totals=collections.Counter(), program_reads=collections.Counter(), carry_hist=collections.Counter(), first_pcs=collections.Counter(),
               guards=[], preserved={}, rejected=[])
    totals = acc['totals']
    load_row(row)
    counts = audit_row(row, program)
    acc['program_reads'].update(counts)
    fx = row['fixture']
    ram, state, pvc, bank, how = start_of_row(row)
    expected_pvc, expected_bank = pvc, bank
    digest = hashlib.sha256()
    stops, step_ends, step_starts = [], {}, {}
    carry_row = collections.Counter()
    variant = row['label'].startswith(VARIANT_PREFIX)
    merged = u2.merge_phases(row['phases'])      # 28a8 / 28ac are interior to the existing atomic 289e executor
    totals['native_phases_merged_into_atomic_289e'] += len(row['phases']) - len(merged)
    for j, phase in enumerate(merged):
        data = phase['_data']
        entry = dict(pc=state['pc'], a7=state['a7'])
        ram, state, kinds = apply_changes(ram, state, phase['host_changes'], entry)
        totals['declared_host_ram_changes'] += len(kinds)
        step = phase['step']
        if j == 0:
            step_starts[step] = (ram, dict(state), pvc, bank)
        else:
            assert not phase['host_changes']
        assert {k: state[k] for k in common.REGS + ('pc',)} == phase['incoming'], (row['label'], j)
        assert ram == data['ram_before.bin'], (row['label'], j)
        events = phase['_trace']['events']
        executed = phase['_trace']['pcs'][:-1]
        if phase['guard'] is not None:
            assert j == len(merged) - 1 and row['guarded']
            acc['guards'].append((row, phase, ram, dict(state), pvc, bank))
            break
        assert bank == phase['bank_before']
        expected_pvc, expected_bank, portbytes = cc.fold_outputs(expected_pvc, expected_bank, events)
        assert expected_bank == phase['modeled_bank'] and portbytes == data['ports.bin'] == b''
        if variant and 0x49e36 in executed:
            # deliberate difference: natively the RTS inside the unit (49e36, no block start) executes; the C++ rejects the PC
            actual = inv('c%03d_split_%03d' % (row['index'], j), exe, ram, state, pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
            check_preserved(actual, ram, state, pvc, bank, UNSUPPORTED_INPUT)
            acc['rejected'].append(dict(label=row['label'], phase=j, error=UNSUPPORTED_INPUT, native_pcs_include_49e36=True))
            totals['deliberate_difference_rows'] += 1
            break
        phase_in, phase_pvc, phase_bank = dict(state), pvc, bank
        actual = inv('c%03d_split_%03d' % (row['index'], j), exe, ram, state, pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
        assert actual[0]['ok'] and not actual[4], (row['label'], j, hex(phase['stop_pc']), actual[4])
        u2.check_result(actual, dict(outgoing=phase['outgoing'], events=events, ram_after=data['ram_after.bin']), expected_pvc, expected_bank, portbytes)
        result, ram, pvc, _, _ = actual
        want_carry = classify_carry(instructions, state['carry'], executed)
        assert result['carry'] == want_carry, (row['label'], j, hex(phase['outgoing']['pc']), result['carry'], want_carry)
        acc['carry_hist'][result['carry']] += 1
        carry_row[CARRY_NAME[result['carry']]] += 1
        first = executed[0] if executed else None
        if first is not None and first in start_set:
            acc['first_pcs'][first] += 1
        path_independent = consumer_checks(instructions, state['carry'], executed, phase['_trace']['pcs'][1:], totals) if first not in CONSUMERS else False
        if first in CONSUMERS:
            # the consumer starts the phase: the carry arrives from the previous actual C++ output (known), the REAL native next PC must follow it;
            # the flipped C must select the other destination without changing anything else
            assert phase_in['carry'] in (1, 2), (row['label'], j)
            assert phase['_trace']['pcs'][1] == branch_expect(instructions[first], phase_in['carry']), (row['label'], j)
            flipped = 3 - phase_in['carry']
            other = branch_expect(instructions[first], flipped)
            again = inv('c%03d_flip_%03d' % (row['index'], j), exe, data['ram_before.bin'], dict(phase_in, carry=flipped), phase_pvc, phase_bank,
                        resources, stop=other, external=fx['external'])
            assert again[0]['ok'] and not again[4] and again[0]['pc'] == other and again[0]['carry'] == flipped, (row['label'], j)
            assert again[1] == data['ram_before.bin'] and again[2] == phase_pvc and again[0]['bank_base'] == phase_bank
            assert {k: again[0][k] for k in common.REGS} == {k: phase_in[k] for k in common.REGS}
            totals['consumer_first_pc_checks'] += 1
            totals['consumer_flip_checks'] += 1
            totals['consumer_flip_%06x_incoming_%s' % (first, CARRY_NAME[phase_in['carry']])] += 1
        if path_independent:
            for probe in (1, 2):
                again = inv('c%03d_carry%d_%03d' % (row['index'], probe, j), exe, data['ram_before.bin'], dict(phase_in, carry=probe), phase_pvc,
                            phase_bank, resources, stop=phase['stop_pc'], external=fx['external'])
                assert again[0]['ok'] and not again[4], (row['label'], j, probe)
                assert again[0]['carry'] == classify_carry(instructions, probe, executed), (row['label'], j, probe, again[0]['carry'])
                assert {k: v for k, v in again[0].items() if k != 'carry'} == {k: v for k, v in result.items() if k != 'carry'}
                assert again[1] == ram and again[2] == pvc and again[3] == actual[3]
                totals['carry_probes'] += 1
                totals['carry_probe_preserved'] += again[0]['carry'] == probe
                blocks = [pc for pc in executed if pc in start_set]
                if len(blocks) == 1 and blocks[0] == first and all(pc in st['instructions'] for pc in executed) and first not in CONSUMERS:
                    slot = acc['preserved'].setdefault(first, {1: True, 2: True})
                    slot[probe] = slot[probe] and again[0]['carry'] == probe
        else:
            totals['carry_probe_phases_skipped_consumer_first'] += 1
        if first in SUBSTEP_BLOCKS and phase['guard'] is None:
            # 49bb0 (falls through into 49bb4) and 49ad6 (loop block) never form a one-block phase in the native split: run the C++ only up to the next block start and
            # compare with the REAL native register file at that block start (no memory is written by either block)
            cut = next(i for i, pc in enumerate(executed) if i > 0 and pc in start_set)
            nxt = executed[cut]
            hit = [b for b in phase['_trace']['boundaries'] if b['pc'] == nxt][0]
            for carry in (0, 1, 2):
                sub = inv('c%03d_sub%d_%03d' % (row['index'], carry, j), exe, data['ram_before.bin'], dict(phase_in, carry=carry), phase_pvc, phase_bank,
                          resources, stop=nxt, external=fx['external'])
                assert sub[0]['ok'] and not sub[4] and sub[0]['pc'] == nxt, (row['label'], j, carry)
                assert {k: sub[0][k] for k in common.REGS} == {k: hit['registers'][k] for k in common.REGS}
                assert sub[1] == data['ram_before.bin'] and sub[2] == phase_pvc and sub[0]['bank_base'] == phase_bank
                assert sub[0]['carry'] == classify_carry(instructions, carry, executed[:cut]), (row['label'], j, carry)
                totals['substep_block_probes'] += 1
                if carry:
                    slot = acc['preserved'].setdefault(first, {1: True, 2: True})
                    slot[carry] = slot[carry] and sub[0]['carry'] == carry
        totals['carry_checks'] += 1
        state = {k: result[k] for k in common.STATE_KEYS}
        bank = result['bank_base']
        totals['reads'] += result['external_reads']
        totals['ports'] += len(portbytes) // 9
        totals['resumes'] += 1 if j else 0
        digest.update(struct.pack('>IIB', phase['stop_pc'], state['pc'], result['carry']) + hashlib.sha256(ram).digest() + hashlib.sha256(pvc).digest() +
                      struct.pack('>I', len(portbytes)))
        stops.append(phase['stop_pc'])
        step_ends[phase['step']] = (ram, dict(state), pvc, bank)
    control_rows = 0
    for phase in row['continuous_control']:
        if phase['guard'] is not None:
            continue
        step = phase['step']
        c_ram, c_state, c_pvc, c_bank = step_starts[step]
        data = phase['_data']
        e_pvc, e_bank, portbytes = cc.fold_outputs(c_pvc, c_bank, phase['_trace']['events'])
        assert e_bank == phase['modeled_bank'] and portbytes == data['ports.bin']
        assert {k: c_state[k] for k in common.REGS + ('pc',)} == phase['incoming']
        actual = inv('c%03d_control_%d' % (row['index'], step), exe, c_ram, c_state, c_pvc, c_bank, resources, stop=phase['stop_pc'], external=fx['external'])
        if variant:
            check_preserved(actual, c_ram, c_state, c_pvc, c_bank, UNSUPPORTED_INPUT)
            totals['deliberate_difference_control_rows'] += 1
            continue
        assert actual[0]['ok'] and not actual[4], (row['label'], actual[4])
        u2.check_result(actual, dict(outgoing=phase['outgoing'], events=phase['_trace']['events'], ram_after=data['ram_after.bin']), e_pvc, e_bank, portbytes)
        assert (actual[1], {k: actual[0][k] for k in common.STATE_KEYS}, actual[2], actual[0]['bank_base']) == step_ends[step], (row['label'], step)
        control_rows += 1
        if row['continuous_control'] and phase['step_stop_pc'] == phase['stop_pc']:
            acc['control_final'] = (sha(actual[1]), tuple(actual[0][k] for k in common.REGS + ('pc',)), actual[0]['carry'])
    totals['cases'] += 1
    totals['split'] += len(stops)
    totals['control'] += control_rows
    acc['out_row'] = dict(index=row['index'], label=row['label'], group=row['group'], seed=row['fixture']['seed']['kind'], seed_start=how,
                          entry_pc=hex(fx['entry_pc']), step_stop_pcs=[hex(s['stop_pc']) for s in row['steps']], split_phases=len(stops),
                          control_steps=control_rows, carry=dict(sorted(carry_row.items())), guarded=bool(row['guarded']), C_phase_digest_sha256=digest.hexdigest())
    acc['seed_kind'] = how.split(' ')[0] + ' ' + how.split(' ')[1]
    unload_row(row)
    return acc


def compare(exe, rows, resources, st, program, instructions):
    totals = collections.Counter()
    program_reads = collections.Counter(fixed_reads=0, bank_reads=0, PVC_writes=0)
    carry_hist = collections.Counter({0: 0, 1: 0, 2: 0})
    preserved, first_pcs, seed_kinds = {}, collections.Counter(), collections.Counter()
    out_rows, guards, rejected, starts_by_label = [], [], [], {}
    start_set = set(st['starts'])
    ctx = (exe, resources, st, program, instructions)
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        def guarded_run(r):
            try:
                return run_row(r, ctx)
            except Exception:
                return dict(error=traceback.format_exc())
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
        rejected.extend(acc['rejected'])
        out_rows.append(acc['out_row'])
        if 'control_final' in acc:
            STORED_CONTROL[row['label']] = acc['control_final']
    # carry-preserving classification observed through the actual C++ (single-block phases probed with an incoming known C)
    for pc, slots in preserved.items():
        assert pc in start_set and all(slots.values()) == (pc in st['preserving']), (hex(pc), slots)
    if not DEBUG_ROWS:
        for pc in CONSUMERS:
            assert any(k.startswith('consumer_flip_%06x_incoming_' % pc) for k in totals), hex(pc)
    observed_preserving = sorted(pc for pc, slots in preserved.items() if all(slots.values()))
    if not DEBUG_ROWS:
        assert start_set - {TRAP_PC} <= set(first_pcs), sorted(hex(p) for p in start_set - {TRAP_PC} - set(first_pcs))
        # every executable block start: carry preservation observed through the actual C++ (one-block phases / sub-step probes), consumers through the flip checks
        assert set(preserved) | set(CONSUMERS) == start_set - {TRAP_PC}, sorted(hex(p) for p in (start_set - {TRAP_PC}) ^ (set(preserved) | set(CONSUMERS)))
        assert set(observed_preserving) | set(CONSUMERS) == set(st['preserving'])
    totals = dict(sorted(totals.items()))
    totals['carry_histogram'] = {CARRY_NAME[k]: v for k, v in sorted(carry_hist.items())}
    totals['guard_rows'] = len(guards)
    totals['block_starts_run_as_first_pc_of_actual_cpp_phases'] = len(start_set & set(first_pcs))
    totals['block_starts_probed_for_carry_preservation'] = len(preserved)
    totals['block_starts_observed_carry_preserving'] = len(observed_preserving)
    totals['carry_consumer_starts_checked_by_flip'] = len(CONSUMERS) if not DEBUG_ROWS else 0
    totals['seed_start_kinds'] = dict(sorted(seed_kinds.items()))
    return out_rows, totals, guards, dict(program_reads), rejected, sorted(preserved)


def compare_guards(exe, guards, resources):
    rows, mismatches = [], []
    for row, phase, ram, state, pvc, bank in guards:
        fx = row['fixture']
        label = row['label']
        want = guard_error(label)
        s = dict(state, carry=2)
        actual = inv('guard_%s' % label, exe, ram, s, pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
        if actual[4].strip() != want:
            mismatches.append((label, actual[4].strip(), want))
        check_preserved(actual, ram, s, pvc, bank, actual[4].strip())
        # same error with the Unknown carry (no carry dependence of the failure)
        s0 = dict(state, carry=0)
        again = inv('guard0_%s' % label, exe, ram, s0, pvc, bank, resources, stop=phase['stop_pc'], external=fx['external'])
        assert again[4].strip() == actual[4].strip()
        check_preserved(again, ram, s0, pvc, bank, actual[4].strip())
        rows.append(dict(label=label, native_guard=phase['guard'], expected_API_error=want, checked_API_error=actual[4].strip(), all_API_outputs_preserved=True,
                         native_fault_rollback_equivalence_claimed=False))
    assert not mismatches, mismatches
    assert len(rows) == 27
    return rows


# ----------------------------------------------------------------------------------------------------------------- 7527 normal conditions end-to-end
def census_task(index):
    """One non-natural, non-guard declared condition: native recompute + Python model vs actual C++ full final state (runs in a forked worker)."""
    try:
        return census_run(index)
    except Exception:
        return dict(error=traceback.format_exc(), index=index)


def census_run(index):
    it = ITEMS[index]
    obs = OBS
    label = it['label']
    ram, state, pvc, bank = item_start(it)
    fx = it['fx']
    stop = it['stop']
    totals = collections.Counter()
    p = obs.probe(PROGRAM, fx, it['setup'], stop)
    assert p['ram_before'] == ram and {k: state[k] for k in common.REGS + ('pc',)} == p['incoming'], label
    events = p['events']
    pcs = p['pcs']
    executed = pcs[:-1]
    e_pvc, e_bank, portbytes = cc.fold_outputs(pvc, bank, events)
    assert e_bank == p['modeled_bank'] and portbytes == b''
    out = dict(index=index, label=label, group=it['group'])
    if label.startswith(VARIANT_PREFIX):
        actual = inv('i%05d_variant' % index, EXE, ram, state, pvc, bank, RESOURCES, stop=stop, external=fx['external'])
        check_preserved(actual, ram, state, pvc, bank, UNSUPPORTED_INPUT)
        assert 0x49e36 in executed and p['outgoing']['pc'] == stop
        totals['deliberate_difference_rows'] += 1
        out.update(totals=totals, digest=hashlib.sha256(label.encode() + b'reject').hexdigest())
        return out
    actual = inv('i%05d_run' % index, EXE, ram, state, pvc, bank, RESOURCES, stop=stop, external=fx['external'])
    assert actual[0]['ok'] and not actual[4], (label, hex(stop), actual[4])
    u2.check_result(actual, dict(outgoing=p['outgoing'], events=events, ram_after=p['ram_after']), e_pvc, e_bank, portbytes)
    result, c_ram, c_pvc, _, _ = actual
    want_carry = classify_carry(INSTRUCTIONS, 0, executed)
    assert result['carry'] == want_carry, (label, result['carry'], want_carry)
    totals['carry_' + CARRY_NAME[result['carry']]] += 1
    # recorded census row fields vs the fresh native run (the observation stores no RAM / registers for the census conditions)
    row = obs.census_row(PROGRAM, it, p)
    rec = CENSUS_BY_LABEL[label]
    assert (rec['entry'], rec['stop'], rec['final']) == (row['entry_pc'], row['stop_pc'], row['final_pc']), label
    assert rec['instructions'] == row['instructions'] and rec['a7_delta'] == row['a7_delta'] and rec['leaders'] == row['leaders'], label
    assert rec['slots_before'] == row['slots_before'] and rec['slots_after'] == row['slots_after'] and rec['jsr_targets'] == row['jsr_targets'], label
    assert rec['fixed_reads'] == json.loads(json.dumps(row['fixed_reads'])), label
    # the actual C++ slots after the run equal the recorded slots (stack-independent recorded field)
    slots = ['0x%x' % int.from_bytes(c_ram[0xd734:0xd738], 'big'), '0x%x' % int.from_bytes(c_ram[0xd738:0xd73c], 'big')]
    assert slots == rec['slots_after'], (label, slots, rec['slots_after'])
    assert ((result['a7'] - state['a7']) & M32) == rec['a7_delta'] & M32
    # real native consumer branches vs the classified C
    consumer_checks(INSTRUCTIONS, 0, executed, pcs[1:], totals)
    # Python model (independent of the C++): final registers / RAM / bank
    if it['model'] and stop != state['pc']:
        M = obs.run_model(PROGRAM, p, stop)
        assert {k: result[k] for k in M.r} == M.r and bytes(M.ram) == c_ram and M.bank == result['bank_base'], label
        totals['model_compared'] += 1
    # stored rows: the fresh native recompute equals the stored native artifact (determinism of the frozen evidence)
    if label in STORED_NATIVE:
        stored = STORED_NATIVE[label]
        assert p['ram_after'] == (NATIVE_DIR / stored['ram_after']).read_bytes() and p['outgoing'] == stored['outgoing'] and p['pcs'] == stored['pcs'], label
        totals['stored_native_recompute_equal'] += 1
    # carry probes (incoming known C): result identical except the classified carry
    skip = (executed and executed[0] in CONSUMERS) or any(
        pc in CONSUMERS and classify_carry(INSTRUCTIONS, 1, executed[:i]) != classify_carry(INSTRUCTIONS, 2, executed[:i]) for i, pc in enumerate(executed))
    if skip or index % 16:
        totals['carry_probes_skipped_consumer_first' if skip else 'carry_probes_not_sampled_here_covered_by_stored_rows'] += 1
    else:
        for probe in (1, 2):
            again = inv('i%05d_c%d' % (index, probe), EXE, ram, dict(state, carry=probe), pvc, bank, RESOURCES, stop=stop, external=fx['external'])
            assert again[0]['ok'] and not again[4], (label, probe)
            assert again[0]['carry'] == classify_carry(INSTRUCTIONS, probe, executed), (label, probe, again[0]['carry'])
            assert {k: v for k, v in again[0].items() if k != 'carry'} == {k: v for k, v in result.items() if k != 'carry'}
            assert again[1] == c_ram and again[2] == c_pvc and again[3] == actual[3]
            totals['carry_probes'] += 1
            totals['carry_probe_preserved'] += again[0]['carry'] == probe
    totals['conditions'] += 1
    totals['instructions'] += len(executed)
    totals['ram_writes'] += sum(1 for e in events if e['region'] == 'ram' and e['access'] == 'write')
    out.update(totals=totals, digest=hashlib.sha256(label.encode() + hashlib.sha256(c_ram).digest() + struct.pack('>II', result['pc'], result['carry']) +
                                                      b''.join(struct.pack('>I', result[k]) for k in common.REGS)).hexdigest())
    return out


STORED_NATIVE = {}


def stored_native_table(report):
    table = {}
    for row in report['results']:
        if row['label'] in ITEM_BY_LABEL and not row['label'].startswith(VARIANT_PREFIX):
            phase = row['continuous_control'][0]
            ram_after = [n for n in phase['artifacts'] if n.endswith('_ram_after.bin')][0]
            trace = json.loads((NATIVE_DIR / [n for n in phase['artifacts'] if n.endswith('_trace.json')][0]).read_text())
            table[row['label']] = dict(ram_after=ram_after, outgoing=phase['outgoing'], pcs=trace['pcs'])
    return table


def run_census(report):
    global STORED_NATIVE
    STORED_NATIVE = stored_native_table(report)
    indexes = [i for i, it in enumerate(ITEMS) if it['guard'] is None]
    if DEBUG_ROWS:
        indexes = indexes[:DEBUG_ROWS * 5]
    context = multiprocessing.get_context('fork')
    with context.Pool(WORKERS) as pool:
        results = pool.map(census_task, indexes, chunksize=16)
    failures = [r for r in results if 'error' in r]
    if failures:
        for r in failures[:5]:
            print('CENSUS FAILED', r['index'], r['error'].strip().splitlines()[-1])
        print(failures[0]['error'])
        raise AssertionError('%d census conditions failed' % len(failures))
    totals = collections.Counter()
    groups = collections.Counter()
    digest = hashlib.sha256()
    for r in results:
        totals.update(r['totals'])
        groups[r['group']] += 1
        digest.update(r['digest'].encode())
    return dict(sorted(totals.items())), dict(sorted(groups.items())), digest.hexdigest(), len(results)


# ----------------------------------------------------------------------------------------------------------------- API-only checks
def reject(exe, label, start, changes, stop, error_expected, out, resources, external=0):
    r, s, p, b = start
    s = dict(s, carry=2)
    s.update(changes or {})
    actual = inv('negative_' + label, exe, r, s, p, b, resources, stop=stop, external=external)
    check_preserved(actual, r, s, p, b, error_expected)
    out.append(dict(label=label, error=error_expected, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False))


def negatives(exe, base, st, resources):
    out = []
    start_set = set(st['starts'])
    instructions = st['instructions']
    ranges = st['ranges']
    interior = [pc for pc in st['inside'] if pc not in start_set]
    for pc in interior:
        reject(exe, 'interior_direct_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_INPUT, out, resources)
    operand = [pc for low, high in ranges for pc in range(low, high, 2) if pc not in instructions and pc not in start_set]
    for pc in operand:
        reject(exe, 'operand_word_direct_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_INPUT, out, resources)
    folded = sorted(st['folded'])
    assert set(folded) <= set(interior)
    for pc in (0x49dd4, 0x49e8a, 0x49f4a):
        assert pc in folded
    # 4d7f0: stop-only boundary (the TRAP #15 has no executor); the zero-step is checked in boundary_zero_step
    reject(exe, 'trap_4d7f0_direct_entry', base, {'pc': TRAP_PC}, 0xff000, UNSUPPORTED_MACHINE, out, resources)
    reject(exe, 'trap_4d7f0_direct_entry_stop_4d7f2', base, {'pc': TRAP_PC}, 0x4d7f2, UNSUPPORTED_MACHINE, out, resources)
    # data windows and the setter / initializer gap between the ranges: no executor
    for pc in (0x49ab0, 0x49ab2, 0x49bca, 0x49be0, 0x49c1e, 0x49c38, 0x49c6c, 0x4cf64, 0x4d81c, 0x1d8ce, 0xe73f8, 0x1bee4, 0x1d5c4, 0x1d5fc, 0x1d63a, 0x1d698,
               0x1d6fa, 0x1daba, 0x48384, 0x4d7a4, 0x49d86):
        assert not in_ranges(pc, ranges)
        reject(exe, 'outside_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNSUPPORTED_MACHINE, out, resources)
    # odd PCs (alignment is checked before routing)
    for pc in (0x49b0d, 0x49ab5, 0x4d7a7, 0x1d8cd, 0x49e35, 0x1d665, 0x4836f):
        reject(exe, 'odd_pc_entry_%06x' % pc, base, {'pc': pc}, 0xff000, UNALIGNED_PC, out, resources)
    # the four carry consumers need a known incoming C (Unknown -> checked error, full rollback)
    for pc in CONSUMERS:
        r, s, p, b = base
        actual = inv('unknown_carry_%06x' % pc, exe, r, dict(s, pc=pc, carry=0), p, b, resources, stop=0xff000)
        check_preserved(actual, r, dict(s, pc=pc, carry=0), p, b, UNKNOWN_CARRY)
        out.append(dict(label='unknown_carry_consumer_%06x' % pc, error=UNKNOWN_CARRY, all_API_outputs_preserved=True, native_exception_rollback_equivalence_claimed=False))
    # positive controls: a known incoming C is consumed and preserved
    controls = []
    for pc in CONSUMERS:
        for carry in (1, 2):
            want = branch_expect(instructions[pc], carry)
            r, s, p, b = base
            s2 = dict(s, pc=pc, carry=carry)
            res, out_ram, out_pvc, ports, error = inv('consumer_%06x_%d' % (pc, carry), exe, r, s2, p, b, resources, stop=want)
            assert res['ok'] and not error and res['pc'] == want and res['carry'] == carry and out_ram == r and out_pvc == p and not ports
            assert {k: res[k] for k in common.REGS} == {k: s2[k] for k in common.REGS}
            controls.append(dict(pc=hex(pc), carry=CARRY_NAME[carry], next_pc=hex(want), carry_preserved=True, API_state_unchanged=True))
    # producers: ANDI #fe,CCR -> Clear, ORI #1,CCR -> Set (from any incoming carry), stack return LONG consumed
    producers = []
    r, s, p, b = base
    for pc, want_carry in zip(PRODUCERS, (1, 2)):
        for carry in (0, 1, 2):
            a7 = (s['a7'] - 4) & M32
            ram2 = bytearray(r)
            ram2[a7 & 0xffff:(a7 & 0xffff) + 4] = (0x49b2e).to_bytes(4, 'big')
            res, out_ram, out_pvc, ports, error = inv('producer_%06x_%d' % (pc, carry), exe, bytes(ram2), dict(s, pc=pc, a7=a7, carry=carry), p, b, resources, stop=0x49b2e)
            assert res['ok'] and not error and res['pc'] == 0x49b2e and res['carry'] == want_carry and res['a7'] == s['a7'] and out_ram == bytes(ram2)
            producers.append(dict(pc=hex(pc), incoming=CARRY_NAME[carry], outgoing=CARRY_NAME[res['carry']]))
    # unreached stops: the run continues into the U1 code at 480cc and (final state, U1..U7 executable) still ends in an unsupported-PC rollback at the first PC without an executor; the stops stay unreached
    for stop in (0x49b0e, 0x49b2e, 0x4d7f0, 0x49e34):
        reject(exe, 'unreached_stop_%06x_from_49b0c' % stop, base, {}, stop, UNSUPPORTED_MACHINE, out, resources)
    return out, len(interior), len(operand), controls, producers


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
    for pc in (TRAP_PC, RET_FRAME, ENTRY, 0x49b2e, 0x49b84):
        for carry in (0, 1, 2):
            s = dict(state, pc=pc, carry=carry)
            result, out_ram, out_pvc, ports, error = inv('zero_boundary_%06x_%d' % (pc, carry), exe, ram, s, pvc, bank, resources, stop=pc)
            assert result['ok'] and not error and {k: result[k] for k in common.STATE_KEYS} == s and out_ram == ram and out_pvc == pvc and not ports
            rows.append(dict(pc=hex(pc), carry=CARRY_NAME[carry], ok=True))
    return rows


def older_verifier_49b0c_negatives():
    """Report only: older verifiers/tests that use 49b0c (now an executable block start) as an 'unsupported' entry."""
    found = []
    for path in sorted((ROOT / 'tools').glob('verify_animation_machine*.py')) + sorted((ROOT / 'tools').glob('verify_stage_frame*.py')):
        if path.name == Path(__file__).name:
            continue
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if re.search(r'(?<![0-9a-f])(0x)?49b0c(?![0-9a-f])', line):
                found.append(dict(file=str(path.relative_to(ROOT)), line=number, text=line.strip()[:200]))
    for path in sorted((ROOT / 'engine/tests').glob('animation_machine_*_test.cpp')):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if re.search(r'(?<![0-9a-f])0x49b0c(?![0-9a-f])', line) and path.name != 'animation_machine_input_test.cpp':
                found.append(dict(file=str(path.relative_to(ROOT)), line=number, text=line.strip()[:200]))
    return found


def cpp_static(st):
    text = (ROOT / 'engine/src/animation_machine_input.cpp').read_text()
    cases = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', text))
    start_set = set(st['starts'])
    expected = start_set - {TRAP_PC}
    machine = (ROOT / 'engine/src/animation_machine.cpp').read_text()
    body = machine[machine.index('bool carry_preserving_pc'):machine.index('default:', machine.index('bool carry_preserving_pc'))]
    table = set(int(x, 16) for x in re.findall(r'case (0x[0-9a-f]+):', body))
    in_unit = set(pc for pc in table if in_ranges(pc, st['ranges']))
    return cases, expected, in_unit


# ----------------------------------------------------------------------------------------------------------------- main
def main():
    global RUN_DIR
    assert OUT.resolve() == (ROOT / 'artifacts/animation_machine_input_execution').resolve()
    if OUT.exists():
        shutil.rmtree(OUT)          # only this verifier's own output folder
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / 'verification.json'
    RUN_DIR = Path(tempfile.mkdtemp(prefix='input_verify_'))
    try:
        run(report_path)
    finally:
        shutil.rmtree(RUN_DIR, ignore_errors=True)


def run(report_path):
    global EXE, RESOURCES, INSTRUCTIONS, START_SET
    inputs = helpers.dependencies(ROOT)
    for name in ('tools/verify_animation_machine_input.py', 'tools/verify_animation_machine_scene_core.py', 'tools/verify_animation_machine_card_child.py',
                 'tools/verify_stage_frame.py', 'tools/observe_animation_machine_input.py', 'tools/observe_stage_input_loop.py',
                 'docs/analysis/animation-machine-input-u6-contract.md', 'engine/src/animation_machine_input.cpp',
                 'engine/src/animation_machine.cpp', 'engine/src/animation_machine_internal.h', 'engine/tests/animation_machine_input_test.cpp'):
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
    for pc, item in st['instructions'].items():
        instructions[pc] = item
    EXE, RESOURCES, INSTRUCTIONS, START_SET = exe, resources, instructions, frozenset(st['starts'])
    items = build_items(program, str(RUN_DIR))
    global ITEMS
    ITEMS = items
    for it in items:
        ITEM_BY_LABEL[it['label']] = it
    assert len(items) == 7348 and len(ITEM_BY_LABEL) == 7348
    census = report['first_boundary_census']['census']
    for rec in census:
        CENSUS_BY_LABEL[rec['label']] = rec
    rows = report['results'] + report['guarded_results']
    assert len(rows) == 685
    census_totals, census_groups, census_digest, census_count = run_census(report)
    print('census done', census_count, flush=True)
    if DEBUG_ROWS:
        rows = [r for r in report['results'][:DEBUG_ROWS]] + [r for r in report['results'] if r['label'].startswith(VARIANT_PREFIX)][:1] + report['guarded_results']
    matches, totals, guards, program_reads, rejected, probed = compare(exe, rows, resources, st, program, instructions)
    assert DEBUG_ROWS or VERIFIED_ARTIFACTS == set(report['artifacts']), (len(VERIFIED_ARTIFACTS), len(report['artifacts']))
    guarded = compare_guards(exe, guards, resources)
    base_row = next(r for r in report['results'] if r['label'] == 'natural-stage-frame-0000')
    b_ram, b_state, b_pvc, b_bank, _ = start_of_row(base_row)
    base = (b_ram, dict(b_state), b_pvc, b_bank)
    negative, interior_count, operand_count, consumer_controls, producer_controls = negatives(exe, base, st, resources)
    zero = zero_step(exe, base, resources, [pc for pc in st['starts'] if pc != TRAP_PC])
    boundary_zero = boundary_zero_step(exe, base, resources)
    cpp_cases, cpp_expected, cpp_carry_table = cpp_static(st)
    assert cpp_cases == cpp_expected, ([hex(p) for p in cpp_cases ^ cpp_expected])
    carry_table_extra = sorted(cpp_carry_table - set(st['preserving']) - set(PRODUCERS))
    carry_table_missing = sorted(set(st['preserving']) - cpp_carry_table)
    assert carry_table_missing == [], [hex(p) for p in carry_table_missing]
    older = older_verifier_49b0c_negatives()
    for name, expected in list(inputs.items()) + list(native_inputs.items()):
        assert cc.digest(ROOT / name if not name.startswith('/') else name) == expected, name
    assert (cc.digest(rom), rom.stat().st_mtime_ns) == rom_guard
    manifest = '\n'.join('%s %s' % (k, report['artifacts'][k]) for k in sorted(report['artifacts']))
    refs = dict(refs)
    for path in (OUT / 'harness.cpp', OUT / 'compile.log'):
        refs[str(path.resolve())] = cc.digest(path)
    deliberate = [dict(label=r['label'], phase=r['phase'], error=r['error']) for r in rejected]
    top_byte = [b for b in report['bus_width_probe']]
    result = dict(
        schema_version=1, source=source, inputs=inputs, native_inputs_checked=len(native_inputs), artifacts=refs,
        native_observation_sha256=NATIVE_SHA, native_tool_sha256=NATIVE_TOOL_SHA, contract_sha256=CONTRACT_SHA,
        native_artifact_manifest=dict(count=len(report['artifacts']), every_file_read_and_hash_checked=True,
                                      sorted_name_hash_lines_sha256=sha(manifest.encode())),
        contract_ranges=st['table'], contract_table_instruction_count_nits=st['column_nits'], block_start_count=len(st['starts']),
        executable_block_start_count=len(st['starts']) - 1, block_starts=[hex(p) for p in st['starts']],
        folded_bundled_pc_count=len(st['folded']), folded_bundled_pcs=[hex(p) for p in sorted(st['folded'])],
        carry_preserving_blocks=[hex(p) for p in st['preserving']], carry_preserving_count=len(st['preserving']),
        carry_consumer_blocks=[hex(p) for p in CONSUMERS], carry_producer_blocks=[hex(p) for p in PRODUCERS],
        opcode_leader_derivation=dict(contract_not_derived=[], derived_not_contract=[hex(p) for p in st['derived_not_contract']]),
        cpp_case_labels=dict(cpp_not_in_contract_block_starts=[], contract_block_starts_without_cpp_case=[hex(TRAP_PC)], cpp_case_count=len(cpp_cases)),
        cpp_carry_preserving_table=dict(contract_preserving_missing=[hex(p) for p in carry_table_missing],
                                        table_entries_in_unit_not_flow_only_and_not_producer=[hex(p) for p in carry_table_extra]),
        actual_CPP=dict(totals, matches=matches), original_program_read_audit=program_reads,
        normal_conditions_end_to_end=dict(total=census_count + 206, natural_via_stored_rows=206, rebuilt_and_rerun_native=census_count,
                                          rebuilt_groups=census_groups, totals=census_totals, digest_sha256=census_digest,
                                          fields_compared='final 64 KiB RAM, 16 registers, PC, PVC image, bank, ordered ports (none), external reads, status, carry class, '
                                                          'recorded census fields (entry/stop/final PC, instruction count, A7 delta, leader counts, slots before/after, JSR targets, '
                                                          'fixed reads), Python model final state; the observation stores no RAM/registers for the census conditions'),
        native_guards_checked_API=guarded, native_continuous_control_phases_replayed=totals['control'],
        deliberate_differences=dict(rows=deliberate, folded_top_byte_targets='native Musashi probe executes 049e34; C++ rejects with a checked error (guard rows)',
                                    bus_width_probe=top_byte),
        negatives=negative, negative_count=len(negative) + len(guarded), interior_PCs_rejected=interior_count,
        operand_word_PCs_rejected=operand_count, consumer_controls=consumer_controls, producer_controls=producer_controls,
        zero_step_count=len(zero), zero_step_blocks=len(st['starts']) - 1, zero_step_carries=[0, 1, 2], boundary_zero_step=boundary_zero,
        older_verifier_and_test_references_to_49b0c_report_only=older,
        carry_check='C++ carry equals the source-opcode walk over native-executed PCs (ORI #1,CCR Set / ANDI #fe,CCR Clear / 289e known C / flow-only preserved / else Unknown); '
                    'at every executed consumer 49b28 49b7e 4d7c6 1d5b2 the classified C is checked against the REAL native next PC (Unicorn SR is never read); '
                    'incoming C probes 1 / 2 per phase; Unknown-carry consumers give the checked error',
        compile_command=command, failure=None, ROM_unchanged=True,
        limits=['Controlled fixtures (natural conditions are declared native entry states SHA-pinned to the stored artifacts; the others are rebuilt from the observer fixture '
                'builders and pinned by SHA to the stored rows), not natural scheduler, IRQ or gameplay reachability.',
                'The 6869 census-only conditions have no stored native RAM/registers; their native side is a fresh Unicorn run of the same pinned observer functions (determinism '
                'checked against the stored native artifacts of the stored subset) plus the Python model.',
                'Existing executor 289e is compared as a whole result; its interior is not modelled here.',
                'Carry is a source-opcode classification cross-checked at the four consumers against the real native branch; X is not used in U6.',
                'Checked failures preserve API outputs, not original CPU fault rollback; JSR (A1) targets with a nonzero top BYTE and the interior target 49e36 are deliberate '
                'differences (native runs the folded 049e34 callback / the RTS, C++ rejects); interior / folded / operand / odd / outside direct entries have no native counterpart.',
                'Native observation artifacts are audited by hash/trace consistency; the stored rows are replayed phase by phase on the C++ side.',
                'The contract table instruction-count column differs from the decoded count in four rows (sum 366 vs 368); the bytes and the unit totals are consistent.'],
        normalized_reference_paths=len(refs))
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(cases=totals['cases'], split=totals['split'], control=totals['control'], resumes=totals['resumes'], census=census_count,
                          negatives=result['negative_count'], interior=interior_count, operand=operand_count, zero_step=len(zero),
                          carry=totals['carry_histogram'], sha256=cc.digest(report_path))))


if __name__ == '__main__':
    main()
